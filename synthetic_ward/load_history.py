"""Load Synthea history (everything before HISTORY_CUTOFF) into Neon.

Runs as one transaction: it truncates the ehr tables and reloads them, so it
is safe to rerun, and a failure leaves the database unchanged.
"""
import csv
import itertools
from datetime import UTC, datetime

import psycopg
from psycopg import sql

from synthetic_ward.config import HISTORY_CUTOFF, SYNTHEA_CSV_DIR, database_url

REFERENCE_TABLES = ["organizations", "providers", "payers"]
CLINICAL_TABLES = ["conditions", "medications", "observations", "procedures", "immunizations", "allergies"]
ALL_TABLES = REFERENCE_TABLES + ["patients", "encounters"] + CLINICAL_TABLES


def parse_time(value):
    """Synthea uses plain dates (2018-04-17) and UTC timestamps (2018-04-17T05:05:43Z)."""
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def read_rows(table):
    """Yield CSV rows with lowercase column names and empty strings as None."""
    with open(SYNTHEA_CSV_DIR / f"{table}.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            yield {k.lower(): (v if v != "" else None) for k, v in row.items()}


def history_patients(rows, cutoff):
    """Patients born before the cutoff, with deaths after it removed."""
    for row in rows:
        if parse_time(row["birthdate"]) >= cutoff:
            continue
        if row["deathdate"] and parse_time(row["deathdate"]) >= cutoff:
            row = {**row, "deathdate": None}
        yield row


def history_encounters(rows, cutoff):
    """Encounters that started before the cutoff. Ones still open at the cutoff are in-progress."""
    for row in rows:
        if parse_time(row["start"]) >= cutoff:
            continue
        if row["stop"] and parse_time(row["stop"]) >= cutoff:
            yield {**row, "stop": None, "status": "in-progress"}
        else:
            yield {**row, "status": "finished"}


def history_events(rows, finished_encounters, cutoff):
    """Clinical rows whose encounter finished before the cutoff.

    Rows with no encounter are kept if they happened before the cutoff.
    """
    for row in rows:
        if row["encounter"]:
            if row["encounter"] in finished_encounters:
                yield row
        elif parse_time(row["start"] if "start" in row else row["date"]) < cutoff:
            yield row


def copy_rows(cur, table, rows):
    """COPY dict rows into ehr.<table>, using the first row's keys as the column list."""
    rows = iter(rows)
    first = next(rows, None)
    if first is None:
        return 0
    columns = list(first)
    stmt = sql.SQL("COPY {} ({}) FROM STDIN").format(
        sql.Identifier("ehr", table),
        sql.SQL(", ").join(map(sql.Identifier, columns)),
    )
    count = 0
    with cur.copy(stmt) as copy:
        for row in itertools.chain([first], rows):
            copy.write_row([row[c] for c in columns])
            count += 1
    return count


def main():
    cutoff = HISTORY_CUTOFF
    print(f"Loading history before {cutoff.isoformat()}")
    with psycopg.connect(database_url) as con, con.cursor() as cur:
        cur.execute(
            sql.SQL("TRUNCATE {} RESTART IDENTITY CASCADE").format(
                sql.SQL(", ").join(sql.Identifier("ehr", t) for t in ALL_TABLES)
            )
        )

        for table in REFERENCE_TABLES:
            print(f"  {table:<14} {copy_rows(cur, table, read_rows(table)):>7,}")

        n = copy_rows(cur, "patients", history_patients(read_rows("patients"), cutoff))
        print(f"  {'patients':<14} {n:>7,}")

        encounters = list(history_encounters(read_rows("encounters"), cutoff))
        finished = {e["id"] for e in encounters if e["status"] == "finished"}
        n = copy_rows(cur, "encounters", encounters)
        print(f"  {'encounters':<14} {n:>7,}  ({n - len(finished)} still in progress)")

        for table in CLINICAL_TABLES:
            n = copy_rows(cur, table, history_events(read_rows(table), finished, cutoff))
            print(f"  {table:<14} {n:>7,}")

        cur.execute(
            "INSERT INTO sim.state (id, sim_time) VALUES (1, %s) "
            "ON CONFLICT (id) DO UPDATE SET sim_time = EXCLUDED.sim_time, updated_at = now()",
            (cutoff,),
        )
        print(f"    sim clock reset to {cutoff.isoformat()}")
        
    print("Committed.")


if __name__ == "__main__":
    main()