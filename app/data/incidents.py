"""
Data-layer module for cyber_incidents table operations.
Provides CRUD operations, filtering, and analytics.
"""

import sqlite3
from typing import Optional, List, Dict, Any

import pandas as pd
from app.data.db import connect_database

# Valid value sets
VALID_SEVERITIES = ["Low", "Medium", "High", "Critical"]
VALID_STATUSES = ["Open", "In Progress", "Resolved", "Closed"]


# CREATE SECTION    

def create_incident(
    date: str,
    incident_type: str,
    severity: str,
    status: str,
    description: str = "",
    reported_by: str = ""
) -> int:
    """
    Insert a new incident into the database.
    Returns the new incident's ID or -1 on failure.
    """
    # Validation; if wrong variables are enetered
    if not all([date, incident_type, severity, status]):
        raise ValueError("date, incident_type, severity, and status are required.")

    if severity not in VALID_SEVERITIES:
        raise ValueError(f"Invalid severity. Must be: {', '.join(VALID_SEVERITIES)}")

    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status. Must be: {', '.join(VALID_STATUSES)}")

    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO cyber_incidents
            (date, incident_type, severity, status, description, reported_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (date, incident_type, severity, status, description, reported_by))

        incident_id = cur.lastrowid
        conn.commit()
        return incident_id

    except sqlite3.Error as e:
        conn.rollback()
        print(f"[incidents] Error creating incident: {e}")
        return -1
    finally:
        conn.close()


# READ SECTION (SINGLE)

def get_incident(incident_id: int) -> Optional[Dict[str, Any]]:
    """Return a single incident as a dict, or None if not found."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM cyber_incidents WHERE id = ?", (incident_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"[incidents] Error retrieving incident {incident_id}: {e}")
        return None
    finally:
        conn.close()


# READ SECTION (ALL)

def get_all_incidents(as_dataframe: bool = False):
    """
    Return all incidents sorted by date (newest first).
    """
    conn = connect_database()
    try:
        if as_dataframe:
            return pd.read_sql_query(
                "SELECT * FROM cyber_incidents ORDER BY date DESC", conn
            )

        cur = conn.cursor()
        cur.execute("SELECT * FROM cyber_incidents ORDER BY date DESC")
        return [dict(row) for row in cur.fetchall()]

    except sqlite3.Error as e:
        print(f"[incidents] Error reading all incidents: {e}")
        return pd.DataFrame() if as_dataframe else []
    finally:
        conn.close()


# READ SCETION (FILTERED)

def get_incidents_by_filters(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    incident_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    as_dataframe: bool = False
):
    """Retrieve incidents based on a set of optional filters."""
    conn = connect_database()
    try:
        query = "SELECT * FROM cyber_incidents WHERE 1=1"
        params = []

        if severity:
            query += " AND severity = ?"
            params.append(severity)
        if status:
            query += " AND status = ?"
            params.append(status)
        if incident_type:
            query += " AND incident_type = ?"
            params.append(incident_type)
        if date_from:
            query += " AND date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND date <= ?"
            params.append(date_to)

        query += " ORDER BY date DESC"

        if as_dataframe:
            return pd.read_sql_query(query, conn, params=params)

        cur = conn.cursor()
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]

    except sqlite3.Error as e:
        print(f"[incidents] Error filtering incidents: {e}")
        return pd.DataFrame() if as_dataframe else []
    finally:
        conn.close()


# UPDATE SECTION

def update_incident(
    incident_id: int,
    date: Optional[str] = None,
    incident_type: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    description: Optional[str] = None,
    reported_by: Optional[str] = None
) -> bool:
    """
    Update any combination of fields for an incident.
    Returns True on success.
    """
    updates = []
    params = []

    if date is not None:
        updates.append("date = ?")
        params.append(date)
    if incident_type is not None:
        updates.append("incident_type = ?")
        params.append(incident_type)
    if severity is not None:
        if severity not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity. Must be: {', '.join(VALID_SEVERITIES)}")
        updates.append("severity = ?")
        params.append(severity)
    if status is not None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status. Must be: {', '.join(VALID_STATUSES)}")
        updates.append("status = ?")
        params.append(status)
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if reported_by is not None:
        updates.append("reported_by = ?")
        params.append(reported_by)

    if not updates:
        return False

    params.append(incident_id)  # WHERE id = ?

    conn = connect_database()
    try:
        cur = conn.cursor()
        sql = f"UPDATE cyber_incidents SET {', '.join(updates)} WHERE id = ?"
        cur.execute(sql, params)
        conn.commit()
        return cur.rowcount > 0

    except sqlite3.Error as e:
        conn.rollback()
        print(f"[incidents] Error updating incident {incident_id}: {e}")
        return False
    finally:
        conn.close()


# DELETE SECTION

def delete_incident(incident_id: int) -> bool:
    """Delete an incident and return True if deletion was successful."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM cyber_incidents WHERE id = ?", (incident_id,))
        conn.commit()
        return cur.rowcount > 0

    except sqlite3.Error as e:
        conn.rollback()
        print(f"[incidents] Error deleting incident {incident_id}: {e}")
        return False
    finally:
        conn.close()


# ANALYTICS
def get_incident_count_by_severity() -> Dict[str, int]:
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT severity, COUNT(*) AS count
            FROM cyber_incidents
            GROUP BY severity
        """)
        return {row["severity"]: row["count"] for row in cur.fetchall()}
    finally:
        conn.close()


def get_incident_count_by_status() -> Dict[str, int]:
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT status, COUNT(*) AS count
            FROM cyber_incidents
            GROUP BY status
        """)
        return {row["status"]: row["count"] for row in cur.fetchall()}
    finally:
        conn.close()


def get_open_incidents_count() -> int:
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) AS count
            FROM cyber_incidents
            WHERE status IN ('Open', 'In Progress')
        """)
        row = cur.fetchone()
        return row["count"]
    finally:
        conn.close()


def get_recent_incidents(limit: int = 10) -> List[Dict[str, Any]]:
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM cyber_incidents
            ORDER BY date DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


# self test; this is only for a demo
def _test_incidents_module():
    print("Running incidents module test...")

    inc_id = create_incident(
        date="2024-01-01",
        incident_type="Phishing",
        severity="High",
        status="Open",
        description="Test phishing attempt",
        reported_by="admin"
    )
    print("Created incident:", inc_id)

    print("Fetching incident:")
    print(get_incident(inc_id))

    print("Updating incident:")
    print(update_incident(inc_id, status="Resolved"))

    print("Counts by severity:")
    print(get_incident_count_by_severity())

    print("Deleting incident:")
    print(delete_incident(inc_id))


if __name__ == "__main__":
    _test_incidents_module()
