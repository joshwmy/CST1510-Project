# schema.py
from typing import Optional
from database.db import connect_database

# Tables are defined in raw SQL below. Keeping them in one place makes the schema easy to track.
CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    failed_attempts INTEGER DEFAULT 0,
    locked_until TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Basic structure for cybersecurity incident logs.
# Keeping fields generic so future analytics features do not need a schema change.
CREATE_CYBER_INCIDENTS = """
CREATE TABLE IF NOT EXISTS cyber_incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id INTEGER,
    timestamp TEXT NOT NULL,
    severity TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Metadata for any dataset someone uploads. 
CREATE_DATASETS_METADATA = """
CREATE TABLE IF NOT EXISTS datasets_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER,
    name TEXT NOT NULL,
    rows INTEGER,
    columns INTEGER,
    uploaded_by TEXT,
    upload_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# IT ticket table. 
CREATE_IT_TICKETS = """
CREATE TABLE IF NOT EXISTS it_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT UNIQUE NOT NULL,
    priority TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,
    assigned_to TEXT,
    created_at TEXT NOT NULL,
    resolution_time_hours INTEGER,
    created_at_db TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Sessions table keeps track of who is logged in using tokens.
# Token expiry is handled by the service layer.
CREATE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    expires_at TEXT,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);
"""

def create_all_tables(conn) -> None:
    """
    Creates all database tables inside the given connection.

    Keeping this in one function avoids having to worry about the order.
    Foreign keys are enabled before this runs, so the DB is consistent from the start.
    """
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    
    # Run the SQL definitions above. If the tables already exist, SQLite just ignores the creation.
    cur.execute(CREATE_USERS)
    cur.execute(CREATE_CYBER_INCIDENTS)
    cur.execute(CREATE_DATASETS_METADATA)
    cur.execute(CREATE_IT_TICKETS)
    cur.execute(CREATE_SESSIONS)

def init_schema(db_path: Optional[str] = None) -> None:
    """
    This function simplifies schema creation:
    open DB, create tables, commit, close.
    Good to run when setting up the app for the first time.
    """
    conn = connect_database(db_path)

    try:
        create_all_tables(conn)
        conn.commit()
        print("Database tables created successfully")
    
    except Exception as e:
        # If something goes wrong, roll back so the DB does not end up half-created.
        conn.rollback()
        print(f"Error creating tables: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    # Running schema.py directly will set up the database.
    init_schema()
    print("Schema initialization complete")
