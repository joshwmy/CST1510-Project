import sqlite3
from pathlib import Path

DATA_DIR = Path("DATA")
DB_PATH = DATA_DIR / "intelligence_platform.db"

# Ensure DATA dir exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

def connect_database(db_path: str | None = None) -> sqlite3.Connection:
    """
    Open (or create) the SQLite database and return a Connection.
    Keep this file focused only on connecting.
    """
    path = str(DB_PATH if db_path is None else db_path)
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn

if __name__ == "__main__":
    print("DB path:", DB_PATH.resolve())
