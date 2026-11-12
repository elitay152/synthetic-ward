# Create EHR schema in Neon
import psycopg

from synthetic_ward.config import DATABASE_URL, SCHEMA_SQL


def main():
    with psycopg.connect(DATABASE_URL) as con:
        con.execute(SCHEMA_SQL.read_text())
        tables = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'ehr' ORDER BY 1"
        ).fetchall()

    print("ehr tables:", ", ".join(t for (t,) in tables))

if __name__ == "__main__":
    main()