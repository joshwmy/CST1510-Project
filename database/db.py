import sqlite3
from pathlib import Path

DATA_DIR = Path("DATA")
DB_PATH = DATA_DIR / "intelligence_platform.db"

# Ensure DATA dir exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

def connect_database(db_path: str | None = None) -> sqlite3.Connection:
    path = str(DB_PATH if db_path is None else db_path)
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    # Foreign keys are enforced for every connection in this db
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


if __name__ == "__main__":
    print("DB path:", DB_PATH.resolve())
