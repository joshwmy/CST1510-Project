# python -m app.schema

from typing import Optional
from app.data.db import connect_database

CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_CYBER_INCIDENTS = """
CREATE TABLE IF NOT EXISTS cyber_incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    incident_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    description TEXT,
    reported_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reported_by) REFERENCES users(username)
);
"""

CREATE_DATASETS_METADATA = """
CREATE TABLE IF NOT EXISTS datasets_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_name TEXT NOT NULL,
    category TEXT,
    source TEXT,
    last_updated TEXT,
    record_count INTEGER,
    file_size_mb REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_IT_TICKETS = """
CREATE TABLE IF NOT EXISTS it_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT UNIQUE NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL,
    category TEXT NOT NULL,
    subject TEXT NOT NULL,
    description TEXT,
    created_date TEXT NOT NULL,
    resolved_date TEXT,
    assigned_to TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def create_users_table(conn) -> None:
    """Create users table. Does not commit; caller manages transaction."""
    cur = conn.cursor()
    cur.execute(CREATE_USERS)


def create_cyber_incidents_table(conn) -> None:
    """Create cyber_incidents table."""
    cur = conn.cursor()
    cur.execute(CREATE_CYBER_INCIDENTS)


def create_datasets_metadata_table(conn) -> None:
    """Create datasets_metadata table."""
    cur = conn.cursor()
    cur.execute(CREATE_DATASETS_METADATA)


def create_it_tickets_table(conn) -> None:
    """Create it_tickets table."""
    cur = conn.cursor()
    cur.execute(CREATE_IT_TICKETS)


def create_all_tables(conn) -> None:
    """Create all database tables inside the given connection.

    This function does not commit; the caller should commit or rollback.
    It enables SQLite foreign key constraints for the connection.
    """
    # Ensure foreign keys are enforced for this connection
    conn.execute("PRAGMA foreign_keys = ON")

    # Order matters if you rely on foreign keys: users should exist
    create_users_table(conn)
    create_cyber_incidents_table(conn)
    create_datasets_metadata_table(conn)
    create_it_tickets_table(conn)


def init_schema(db_path: Optional[str] = None) -> None:
    """
    helper function: open DB, create tables, commit and close.

    Use this to one-shot CLI to initialize the schema.
    """
    conn = connect_database(db_path)
    try:
        create_all_tables(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    # Run with: python -m app.schema
    init_schema()
    print("Schema initialized.")
