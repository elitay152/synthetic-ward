import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
SYNTHEA_CSV_DIR = Path(os.environ.get("SYNTHEA_CSV_DIR", "data/synthea/csv"))
SCHEMA_SQL = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"

HISTORY_CUTOFF = datetime.fromisoformat(os.environ.get("HISTORY_CUTOFF", "2026-05-01T00:00:00+00:00"))