"""Replay Synthea events after HISTORY_CUTOFF into Neon, like a live EHR."""

import argparse
import bisect
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import psycopg
from psycopg import sql

from synthetic_ward.config import DATABASE_URL, HISTORY_CUTOFF
from synthetic_ward.load_history import CLINICAL_TABLES, parse_time, read_rows

# when events share a timestamp, do births before admits and discharges before deaths
RANK = {"birth": 0, "admit": 1, "discharge": 2, "chart": 3, "death": 4}

@dataclass(order=True)
class Event:
    time: datetime
    rank: int
    kind: str = field(compare=False)
    row: dict | None = field(compare=False)
    charts: list = field(default_factory=list, compare=False)

def build_events(patients, encounters, clinical, cutoff):
    """Everything that happens after the cutoff, sortedby time."""
    events = []

    for p in patients:
        if parse_time(p["birthdate"]) >= cutoff:
            events.append(Event(parse_time(p["birthdate"]), RANK["birth"], "birth", {**p, "deathdate": None}))
        if p["deathdate"] and parse_time(p["deathdate"]) >= cutoff:
            events.append(Event(parse_time(p["deathdate"]), RANK["death"], "death", p))

    discharges = {}
    for e in encounters:
        if parse_time(e["stop"]) < cutoff:
            continue # already loaded in history
        if parse_time(e["start"]) >= cutoff:
            admit_row = {**e, "stop": None, "status": "in-progress"}
            events.append(Event(parse_time(e["start"]), RANK["admit"], "admit", admit_row))
        discharge = Event(parse_time(e["stop"]), RANK["discharge"], "discharge", e)
        discharges[e["id"]] = discharge
        events.append(discharge)

    for table, rows in clinical.items():
        for r in rows:
            if r["encounter"]:
                if r["encounter"] in discharges:
                    discharges[r["encounter"]].charts.append((table, r))
                else:
                    t = parse_time(r["start"] if "start" in r else r["date"])
                    if t >= cutoff:
                        events.append(Event(t, RANK["chart"], "chart", None, [(table, r)]))

    events.sort()
    return events

def insert_rows(cur, table, rows):
    columns = list(rows[0])
    stmt = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier("ehr", table),
        sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(sql.Placeholder() * len(columns)),
    )
    cur.executemany(stmt, [[r[c] for c in columns] for r in rows])

def insert_charts(cur, charts):
    by_table = defaultdict(list)
    for table, row in charts:
        by_table[table].append(row)
    for table, rows in by_table.items():
        insert_rows(cur, table, rows)

def apply(cur, event):
    row = event.row
    if event.kind == "birth":
        insert_rows(cur, "patients", [row])
    elif event.kind == "admit":
        insert_rows(cur, "encounters", [row])
    elif event.kind == "discharge":
        cur.execute(
            "UPDATE ehr.encounters SET stop = %s, status = 'finished', updated_at = now() WHERE id = %s",
            (row["stop"], row["id"]),
        )
        if cur.rowcount != 1:
            raise RuntimeError(f"discharge for unknown encounter {row['id']}")
        insert_charts(cur, event.charts)
    elif event.kind == "chart":
        insert_charts(cur, event.charts)
    elif event.kind == "death":
        cur.execute(
            "UPDATE ehr.patients SET deathdate = %s, updated_at = now() WHERE id = %s",
            (row["deathdate"], row["id"])
        )

def load_sim_time(con):
    row = con.execute("SELECT sim_time FROM sim.state WHERE id = 1").fetchone()
    if row is None:
        raise SystemExit("No sim clock found. Run python -m synthetic_ward.load_history first.")
    return row[0]

def run(speed, tick_seconds):
    print("Building events from CSVs...")
    patients = list(read_rows("patients"))
    encounters = list(read_rows("encounters"))
    clinical = {t: read_rows(t) for t in CLINICAL_TABLES}
    events = build_events(patients, encounters, clinical, HISTORY_CUTOFF)
    times = [e.time for e in events]
    end = times[-1]
    print(f"{len(events):,} events, last at {end:%Y-%m-%d %H:%M}")

    with psycopg.connect(DATABASE_URL, autocommit=True) as con:
        sim_time = load_sim_time(con)
        print(f"Resuming at {sim_time:%Y-%m-%d %H:%M}, speed {speed}x")
        step = timedelta(seconds=tick_seconds * speed)

        while sim_time < end:
            new_time = min(sim_time + step, end)
            batch = events[bisect.bisect_right(times, sim_time):bisect.bisect_right(times, new_time)]

            with con.transaction(), con.cursor() as cur:
                for event in batch:
                    apply(cur, event)
                cur.execute("UPDATE sim.state SET sim_time = %s, updated_at = now() WHERE id = 1",
                            (new_time,),)

            sim_time = new_time
            if batch:
                counts = Counter(e.kind for e in batch)
                charted = sum(len(e.charts) for e in batch)
                summary = ", ".join(f"{k} {n}" for k, n in counts.items())
                print(f"{sim_time:%Y-%m-%d %H:%M} {summary}, {charted} clinical rows")
                time.sleep(tick_seconds)

    print(f"Replay finished at {end:%Y-%m-%d %H:%M}.")

def main():
    parser = argparse.ArgumentParser(description="Replay Synthea events into Neon.")
    parser.add_argument("--speed", type=float, default=1440, help="simulated seconds per real second")
    parser.add_argument("--tick", type=float, default=5, help="real seconds between ticks")
    args = parser.parse_args()
    try:
        run(args.speed, args.tick)
    except KeyboardInterrupt:
        print("\nStopped. Run again to resume from the last commited tick.")

if __name__ == "__main__":
    main()