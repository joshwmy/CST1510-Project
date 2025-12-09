import sqlite3
from pathlib import Path

DATA_DIR = Path("DATA")
DB_PATH = DATA_DIR / "intelligence_platform.db"

# Make sure the DATA folder actually exists. This avoids crashes when the DB tries to save.
DATA_DIR.mkdir(parents=True, exist_ok=True)

def connect_database(db_path: str | None = None) -> sqlite3.Connection:
    # If the caller does not specify another DB, we just point to the main one.
    path = str(DB_PATH if db_path is None else db_path)

    # Connect to SQLite. detect_types lets SQLite parse timestamps and other Python types properly.
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)

    # Every row returned will act like a dict, which makes things easier when reading from the DB.
    conn.row_factory = sqlite3.Row

    # Enable foreign key support for every connection. SQLite has it off by default.
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


if __name__ == "__main__":
    print("DB path:", DB_PATH.resolve())
