"""
Data module for cyber_incidents table operations. Provides CRUD operations, filtering, and analytics.
Uses csv_loader functions to reduce database connections.
"""

import sqlite3
from typing import Optional, List, Dict, Any
from database.db import connect_database
from models.csv_loader import load_csv_to_table, count_table_records
import pandas as pd

# established sets of allowed values; keeps inputs tidy and predictable
VALID_SEVERITIES = ["Low", "Medium", "High", "Critical"]
VALID_STATUSES = ["Open", "In Progress", "Resolved", "Closed"]


# ---------------------- CREATE ----------------------

def create_incident(
    timestamp: str,
    category: str,
    severity: str,
    status: str,
    description: str = "",
    reported_by: str = ""
) -> int:
    """
    Add a new incident and return its id. On error return -1.

    This function checks the basics first (makes sure required fields are
    present and that severity/status are recognized), then inserts the row.
    """
    # quick input checks so we fail fast and obviously if something is wrong
    if not all([timestamp, category, severity, status]):
        raise ValueError("timestamp, category, severity and status are required")

    if severity not in VALID_SEVERITIES:
        raise ValueError(f"Invalid severity — must be one of: {', '.join(VALID_SEVERITIES)}")

    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status — must be one of: {', '.join(VALID_STATUSES)}")

    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO cyber_incidents
            (timestamp, category, severity, status, description, reported_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (timestamp, category, severity, status, description, reported_by),
        )
        new_id = cur.lastrowid
        conn.commit()
        return new_id

    except sqlite3.Error as err:
        conn.rollback()
        # print a short, clear message so logs are readable
        print(f"[incidents] Error creating incident: {err}")
        return -1

    finally:
        conn.close()


# ---------------------- READ (single) ----------------------

def get_incident(incident_id: int) -> Optional[Dict[str, Any]]:
    """Return a single incident as a dict, or None if it doesn't exist."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM cyber_incidents WHERE id = ?", (incident_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as err:
        print(f"[incidents] Error fetching incident {incident_id}: {err}")
        return None
    finally:
        conn.close()


# ---------------------- READ (all) ----------------------

# ---------------------- READ (filtered) ----------------------

def get_incidents_by_filters(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    as_dataframe: bool = False
):
    """Fetch incidents using optional filters. Returns list[dict] or DataFrame."""
    conn = connect_database()
    try:
        query = "SELECT * FROM cyber_incidents WHERE 1=1"
        params: List[Any] = []

        if severity:
            query += " AND severity = ?"
            params.append(severity)
        if status:
            query += " AND status = ?"
            params.append(status)
        if category:
            query += " AND category = ?"
            params.append(category)
        if date_from:
            query += " AND timestamp >= ?"
            params.append(date_from)
        if date_to:
            query += " AND timestamp <= ?"
            params.append(date_to)

        query += " ORDER BY timestamp DESC"

        if as_dataframe:
            return pd.read_sql_query(query, conn, params=params)

        cur = conn.cursor()
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]

    except sqlite3.Error as err:
        print(f"[incidents] Error filtering incidents: {err}")
        return pd.DataFrame() if as_dataframe else []
    finally:
        conn.close()


# ---------------------- UPDATE ----------------------

def update_incident(
    incident_id: int,
    timestamp: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    description: Optional[str] = None,
    reported_by: Optional[str] = None
) -> bool:
    """Update fields for an incident. Returns True if something changed."""
    updates: List[str] = []
    params: List[Any] = []

    if timestamp is not None:
        updates.append("timestamp = ?")
        params.append(timestamp)
    if category is not None:
        updates.append("category = ?")
        params.append(category)
    if severity is not None:
        if severity not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity — must be one of: {', '.join(VALID_SEVERITIES)}")
        updates.append("severity = ?")
        params.append(severity)
    if status is not None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status — must be one of: {', '.join(VALID_STATUSES)}")
        updates.append("status = ?")
        params.append(status)
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if reported_by is not None:
        updates.append("reported_by = ?")
        params.append(reported_by)

    if not updates:
        # nothing to update — the caller didn't pass any fields
        return False

    params.append(incident_id)

    conn = connect_database()
    try:
        cur = conn.cursor()
        sql = f"UPDATE cyber_incidents SET {', '.join(updates)} WHERE id = ?"
        cur.execute(sql, params)
        conn.commit()
        return cur.rowcount > 0

    except sqlite3.Error as err:
        conn.rollback()
        print(f"[incidents] Error updating incident {incident_id}: {err}")
        return False

    finally:
        conn.close()


# ---------------------- DELETE ----------------------

def delete_incident(incident_id: int) -> bool:
    """Delete an incident row. Returns True if a row was removed."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM cyber_incidents WHERE id = ?", (incident_id,))
        conn.commit()
        return cur.rowcount > 0
    except sqlite3.Error as err:
        conn.rollback()
        print(f"[incidents] Error deleting incident {incident_id}: {err}")
        return False
    finally:
        conn.close()


# ---------------------- BULK (CSV loader) ----------------------

def get_total_incidents_count() -> int:
    """Return the total number of incidents using the csv loader helper."""
    return count_table_records("cyber_incidents")


# ---------------------- ANALYTICS ----------------------

def get_all_incident_analytics() -> Dict[str, Any]:
    """Return a small analytics bundle in one database connection."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        stats: Dict[str, Any] = {}

        cur.execute("SELECT COUNT(*) as total FROM cyber_incidents")
        stats['total_incidents'] = cur.fetchone()['total']

        cur.execute("SELECT COUNT(*) as open_count FROM cyber_incidents WHERE status IN ('Open', 'In Progress')")
        stats['open_incidents'] = cur.fetchone()['open_count']

        cur.execute("SELECT severity, COUNT(*) as count FROM cyber_incidents GROUP BY severity")
        stats['by_severity'] = {r['severity']: r['count'] for r in cur.fetchall()}

        cur.execute("SELECT status, COUNT(*) as count FROM cyber_incidents GROUP BY status")
        stats['by_status'] = {r['status']: r['count'] for r in cur.fetchall()}

        return stats

    finally:
        conn.close()


# ---------------------- SELF TEST ----------------------
# please ignore...old testing once again



# def _test_incidents_module():
#     """Small manual test to run from the command line."""
#     print("incidents module quick test")

#     inc_id = create_incident(
#         timestamp="2024-01-01",
#         category="Phishing",
#         severity="High",
#         status="Open",
#         description="Test phishing attempt",
#         reported_by="admin"
#     )
#     print("Created incident:", inc_id)

#     print("Fetch:", get_incident(inc_id))
#     print("Total incidents count (csv loader):", get_total_incidents_count())
#     print("Analytics bundle:", get_all_incident_analytics())
#     print("Update:", update_incident(inc_id, status="Resolved"))
#     print("Delete:", delete_incident(inc_id))


# if __name__ == "__main__":
#     _test_incidents_module()
