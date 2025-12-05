"""
IT tickets module; same as incidents.py
"""

import sqlite3
from typing import Optional, List, Dict, Any
from datetime import date
from database.db import connect_database


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

# ---------------------- ANALYTICS ----------------------

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

def get_recent_tickets(limit: int = 10) -> List[Dict[str, Any]]:
    """Return recent tickets ordered by creation date."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM it_tickets ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

# ---------------------- SELF TEST ----------------------
# This was a test; it is now not needed
# def _test_tickets_module():
#     """Quick manual test to run from the command line."""
#     print("tickets module quick test")

#     db_id = create_ticket(
#         ticket_id="TEST-2024-001",
#         priority="Medium",
#         status="Open",
#         category="Software",
#         subject="Test ticket creation",
#         description="Testing the ticket creation function",
#         assigned_to="IT_Support_A"
#     )
#     print("Created ticket (db id):", db_id)

#     print("Fetch by db id:", get_ticket(db_id))
#     print("Fetch by ticket_id:", get_ticket_by_ticket_id("TEST-2024-001"))
#     print("Total tickets count:", get_total_tickets_count())
#     print("Analytics bundle:", get_all_ticket_analytics())
#     print("High priority open tickets:", len(get_high_priority_open_tickets()))
#     print("Delete:", delete_ticket(db_id))


# if __name__ == "__main__":
#     _test_tickets_module()
