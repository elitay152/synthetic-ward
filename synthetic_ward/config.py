import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SYNTHEA_CSV_DIR = Path(os.environ.get("SYNTHEA_CSV_DIR", "data/synthea/csv"))
SCHEMA_SQL = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"

HISTORY_CUTOFF = datetime.fromisoformat(os.environ.get("HISTORY_CUTOFF", "2026-05-01T00:00:00+00:00"))

def database_url():
    """Read at connect time, so importing config (e.g. in tests) doesn't need a database."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set. Copy .env.example to .env and fill it in.")
    return url