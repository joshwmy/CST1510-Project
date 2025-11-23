"""
IT tickets module; same as incidents,py
"""

import sqlite3
from typing import Optional, List, Dict, Any
from datetime import date
from app.data.db import connect_database
from app.data.csv_loader import load_csv_to_table, count_table_records
import pandas as pd

# established sets of allowed values — keeps inputs tidy and predictable
VALID_PRIORITIES = ["Low", "Medium", "High", "Critical"]
VALID_STATUSES = ["Open", "In Progress", "Resolved", "Closed", "Waiting for User"]


# ---------------------- CREATE ----------------------

def create_ticket(
    ticket_id: str,
    priority: str,
    status: str,
    category: str,
    subject: str,
    description: str = "",
    created_at: str = "",
    resolved_date: Optional[str] = None,
    assigned_to: Optional[str] = None,
) -> int:
    """
    Create a new IT ticket and return its DB id.

    This does some light validation (so data stays tidy), fills a sensible
    default for `created_at` if none is given, and inserts the ticket.
    On success it returns the newly-created row id; on failure it returns -1.
    """
    # basic required fields
    if not all([ticket_id, priority, status, category, subject]):
        raise ValueError("ticket_id, priority, status, category and subject are required")

    # ensure values are from the allowed lists
    if priority not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority — must be one of: {', '.join(VALID_PRIORITIES)}")

    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status — must be one of: {', '.join(VALID_STATUSES)}")

    # if caller didn't supply a created_at, use today's date (ISO format)
    if not created_at:
        created_at = date.today().isoformat()
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO it_tickets
            (ticket_id, priority, status, category, subject, description, created_at, resolved_date, assigned_to)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ticket_id, priority, status, category, subject, description, created_at, resolved_date, assigned_to),
        )
        new_id = cur.lastrowid
        conn.commit()
        return new_id

    except sqlite3.IntegrityError:
        conn.rollback()
        # common case: ticket_id unique constraint violation
        print(f"[tickets] Error: Ticket ID '{ticket_id}' already exists")
        return -1

    except sqlite3.Error as err:
        conn.rollback()
        print(f"[tickets] Error creating ticket: {err}")
        return -1

    finally:
        conn.close()


# ---------------------- READ (single) ----------------------

def get_ticket(db_id: int) -> Optional[Dict[str, Any]]:
    """Return a single ticket (by internal DB id) as a dict, or None if not found."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM it_tickets WHERE id = ?", (db_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as err:
        print(f"[tickets] Error fetching ticket {db_id}: {err}")
        return None
    finally:
        conn.close()


def get_ticket_by_ticket_id(ticket_id: str) -> Optional[Dict[str, Any]]:
    """Find a ticket by its external ticket id."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM it_tickets WHERE ticket_id = ?", (ticket_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as err:
        print(f"[tickets] Error fetching ticket '{ticket_id}': {err}")
        return None
    finally:
        conn.close()


# ---------------------- READ (all) ----------------------

def get_all_tickets(as_dataframe: bool = False):
    """Return every ticket, newest first. Dataframe use if user wants to."""
    conn = connect_database()
    try:
        if as_dataframe:
            return pd.read_sql_query("SELECT * FROM it_tickets ORDER BY created_at DESC", conn)

        cur = conn.cursor()
        cur.execute("SELECT * FROM it_tickets ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]

    except sqlite3.Error as err:
        print(f"[tickets] Error reading tickets: {err}")
        return pd.DataFrame() if as_dataframe else []
    finally:
        conn.close()


# ---------------------- READ (filtered) ----------------------

def get_tickets_by_filters(
    priority: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    assigned_to: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    as_dataframe: bool = False,
):
    """Finds tickets using optional filters. Returns a list of dicts or a DataFrame."""
    conn = connect_database()
    try:
        query = "SELECT * FROM it_tickets WHERE 1=1"
        params: List[Any] = []

        if priority:
            query += " AND priority = ?"
            params.append(priority)
        if status:
            query += " AND status = ?"
            params.append(status)
        if category:
            query += " AND category = ?"
            params.append(category)
        if assigned_to:
            query += " AND assigned_to = ?"
            params.append(assigned_to)
        if date_from:
            query += " AND created_at >= ?"
            params.append(date_from)
        if date_to:
            query += " AND created_at <= ?"
            params.append(date_to)

        query += " ORDER BY created_at DESC"

        if as_dataframe:
            return pd.read_sql_query(query, conn, params=params)

        cur = conn.cursor()
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]

    except sqlite3.Error as err:
        print(f"[tickets] Error filtering tickets: {err}")
        return pd.DataFrame() if as_dataframe else []
    finally:
        conn.close()


# ---------------------- UPDATE ----------------------

def update_ticket(
    db_id: int,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    subject: Optional[str] = None,
    description: Optional[str] = None,
    resolved_date: Optional[str] = None,
    assigned_to: Optional[str] = None,
) -> bool:
    """Updates fields for a ticket (using the DB id). Returns True if rows changed."""
    updates: List[str] = []
    params: List[Any] = []

    if priority is not None:
        if priority not in VALID_PRIORITIES:
            raise ValueError(f"Invalid priority — must be one of: {', '.join(VALID_PRIORITIES)}")
        updates.append("priority = ?")
        params.append(priority)
    if status is not None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status — must be one of: {', '.join(VALID_STATUSES)}")
        updates.append("status = ?")
        params.append(status)
    if category is not None:
        updates.append("category = ?")
        params.append(category)
    if subject is not None:
        updates.append("subject = ?")
        params.append(subject)
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if resolved_date is not None:
        updates.append("resolved_date = ?")
        params.append(resolved_date)
    if assigned_to is not None:
        updates.append("assigned_to = ?")
        params.append(assigned_to)

    if not updates:
        # nothing to update — caller passed no fields
        return False

    params.append(db_id)

    conn = connect_database()
    try:
        cur = conn.cursor()
        sql = f"UPDATE it_tickets SET {', '.join(updates)} WHERE id = ?"
        cur.execute(sql, params)
        conn.commit()
        return cur.rowcount > 0

    except sqlite3.Error as err:
        conn.rollback()
        print(f"[tickets] Error updating ticket {db_id}: {err}")
        return False

    finally:
        conn.close()


# ---------------------- DELETE ----------------------

def delete_ticket(db_id: int) -> bool:
    """Deletes a ticket row. Returns True if a row was removed."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM it_tickets WHERE id = ?", (db_id,))
        conn.commit()
        return cur.rowcount > 0
    except sqlite3.Error as err:
        conn.rollback()
        print(f"[tickets] Error deleting ticket {db_id}: {err}")
        return False
    finally:
        conn.close()


# ---------------------- BULK (CSV loader) ----------------------

def load_tickets_from_csv(csv_path: str, clear_table: bool = True) -> int:
    """Loads tickets from CSV using the shared csv_loader (this keeps the DB tidy)."""
    return load_csv_to_table(csv_path, "it_tickets", clear_table=clear_table)


def get_total_tickets_count() -> int:
    """Returns the total number of tickets using the csv loader helper."""
    return count_table_records("it_tickets")


# ---------------------- ANALYTICS ----------------------

def get_ticket_count_by_priority() -> Dict[str, int]:
    """Counts tickets grouped by priority level."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("SELECT priority, COUNT(*) AS count FROM it_tickets GROUP BY priority")
        return {row['priority']: row['count'] for row in cur.fetchall()}
    finally:
        conn.close()


def get_ticket_count_by_status() -> Dict[str, int]:
    """Counts tickets grouped by current status."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("SELECT status, COUNT(*) AS count FROM it_tickets GROUP BY status")
        return {row['status']: row['count'] for row in cur.fetchall()}
    finally:
        conn.close()


def get_ticket_count_by_assigned_to() -> Dict[str, int]:
    """Counts tickets grouped by assigned support person."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("SELECT assigned_to, COUNT(*) AS count FROM it_tickets GROUP BY assigned_to")
        return {row['assigned_to']: row['count'] for row in cur.fetchall()}
    finally:
        conn.close()


def get_all_ticket_analytics() -> Dict[str, Any]:
    """Return a complete analytics bundle in one database connection."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        stats: Dict[str, Any] = {}

        # Basic counts
        cur.execute("SELECT COUNT(*) as total FROM it_tickets")
        stats['total_tickets'] = cur.fetchone()['total']

        cur.execute("SELECT COUNT(*) as open_count FROM it_tickets WHERE status IN ('Open', 'In Progress', 'Waiting for User')")
        stats['open_tickets'] = cur.fetchone()['open_count']

        # Grouped counts
        cur.execute("SELECT priority, COUNT(*) as count FROM it_tickets GROUP BY priority")
        stats['by_priority'] = {r['priority']: r['count'] for r in cur.fetchall()}

        cur.execute("SELECT status, COUNT(*) as count FROM it_tickets GROUP BY status")
        stats['by_status'] = {r['status']: r['count'] for r in cur.fetchall()}

        cur.execute("SELECT assigned_to, COUNT(*) as count FROM it_tickets GROUP BY assigned_to")
        stats['by_assigned_to'] = {r['assigned_to']: r['count'] for r in cur.fetchall()}

        return stats

    finally:
        conn.close()


def get_open_tickets_count() -> int:
    """Return the number of open/in-progress tickets."""
    return get_all_ticket_analytics()['open_tickets']


def get_recent_tickets(limit: int = 10) -> List[Dict[str, Any]]:
    """Return recent tickets ordered by creation date."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM it_tickets ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_high_priority_open_tickets() -> List[Dict[str, Any]]:
    """Return all high/critical priority tickets that are still open."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM it_tickets 
            WHERE priority IN ('High', 'Critical') 
            AND status IN ('Open', 'In Progress')
            ORDER BY created_at DESC
            """
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ---------------------- SELF TEST ----------------------

def _test_tickets_module():
    """Quick manual test to run from the command line."""
    print("tickets module quick test")

    db_id = create_ticket(
        ticket_id="TEST-2024-001",
        priority="Medium",
        status="Open",
        category="Software",
        subject="Test ticket creation",
        description="Testing the ticket creation function",
        assigned_to="IT_Support_A"
    )
    print("Created ticket (db id):", db_id)

    print("Fetch by db id:", get_ticket(db_id))
    print("Fetch by ticket_id:", get_ticket_by_ticket_id("TEST-2024-001"))
    print("Total tickets count:", get_total_tickets_count())
    print("Analytics bundle:", get_all_ticket_analytics())
    print("High priority open tickets:", len(get_high_priority_open_tickets()))
    print("Delete:", delete_ticket(db_id))


if __name__ == "__main__":
    _test_tickets_module()
