"""
Datasets module
Same as incidents.py; slight adjustments to accomodate for the dataset
"""

import sqlite3
from typing import Optional, List, Dict, Any
from app.data.db import connect_database
from app.data.csv_loader import load_csv_to_table, count_table_records
import pandas as pd


# ---------------------- CREATE ----------------------

def create_dataset(
    name: str,
    rows: int,
    columns: int,
    uploaded_by: str,
    upload_date: str,
    description: str = "",
    file_path: str = "",
) -> int:
    """
    Creates a dataset record and return its new id.
    """
    # basic validation; keeps it short and clear
    if not (name and uploaded_by and upload_date):
        raise ValueError("name, uploaded_by and upload_date are required")

    if rows < 0 or columns < 0:
        raise ValueError("rows and columns must be non-negative")

    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO datasets_metadata
            (name, rows, columns, uploaded_by, upload_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, rows, columns, uploaded_by, upload_date),
        )
        new_id = cur.lastrowid
        conn.commit()
        return new_id

    except sqlite3.Error as err:
        conn.rollback()
        print(f"[datasets] Error creating dataset: {err}")
        return -1

    finally:
        conn.close()


# ---------------------- READ (single) ----------------------

def get_dataset(dataset_id: int) -> Optional[Dict[str, Any]]:
    """Return a single dataset as a dict, or None if it's not there."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM datasets_metadata WHERE id = ?", (dataset_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as err:
        print(f"[datasets] Error retrieving dataset {dataset_id}: {err}")
        return None
    finally:
        conn.close()


def get_dataset_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Fetch a dataset by its name (returns dict or None)."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM datasets_metadata WHERE name = ?", (name,))
        row = cur.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as err:
        print(f"[datasets] Error retrieving dataset '{name}': {err}")
        return None
    finally:
        conn.close()


# ---------------------- READ (all / filtered) ----------------------

def get_all_datasets(as_dataframe: bool = False):
    """Return every dataset, newest first. User can even have a DataFrame if they wish."""
    conn = connect_database()
    try:
        if as_dataframe:
            return pd.read_sql_query("SELECT * FROM datasets_metadata ORDER BY upload_date DESC", conn)

        cur = conn.cursor()
        cur.execute("SELECT * FROM datasets_metadata ORDER BY upload_date DESC")
        return [dict(r) for r in cur.fetchall()]

    except sqlite3.Error as err:
        print(f"[datasets] Error reading all datasets: {err}")
        return pd.DataFrame() if as_dataframe else []
    finally:
        conn.close()


def get_datasets_by_filters(
    uploaded_by: Optional[str] = None,
    min_rows: Optional[int] = None,
    max_rows: Optional[int] = None,
    as_dataframe: bool = False,
):
    """Fetch datasets using a few optional filters. Returns list[dict] or DataFrame."""
    conn = connect_database()
    try:
        query = "SELECT * FROM datasets_metadata WHERE 1=1"
        params: List = []

        if uploaded_by:
            query += " AND uploaded_by = ?"
            params.append(uploaded_by)
        if min_rows is not None:
            query += " AND rows >= ?"
            params.append(min_rows)
        if max_rows is not None:
            query += " AND rows <= ?"
            params.append(max_rows)

        query += " ORDER BY upload_date DESC"

        if as_dataframe:
            return pd.read_sql_query(query, conn, params=params)

        cur = conn.cursor()
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]

    except sqlite3.Error as err:
        print(f"[datasets] Error filtering datasets: {err}")
        return pd.DataFrame() if as_dataframe else []
    finally:
        conn.close()


# ---------------------- UPDATE ----------------------

def update_dataset(
    dataset_id: int,
    name: Optional[str] = None,
    rows: Optional[int] = None,
    columns: Optional[int] = None,
    uploaded_by: Optional[str] = None,
    upload_date: Optional[str] = None,
) -> bool:
    """Updates any provided fields on a dataset. Returns True on success."""
    updates: List[str] = []
    params: List[Any] = []

    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if rows is not None:
        if rows < 0:
            raise ValueError("rows must be non-negative")
        updates.append("rows = ?")
        params.append(rows)
    if columns is not None:
        if columns < 0:
            raise ValueError("columns must be non-negative")
        updates.append("columns = ?")
        params.append(columns)
    if uploaded_by is not None:
        updates.append("uploaded_by = ?")
        params.append(uploaded_by)
    if upload_date is not None:
        updates.append("upload_date = ?")
        params.append(upload_date)

    if not updates:
        # nothing to do; caller passed no fields
        return False

    params.append(dataset_id)

    conn = connect_database()
    try:
        cur = conn.cursor()
        sql = f"UPDATE datasets_metadata SET {', '.join(updates)} WHERE id = ?"
        cur.execute(sql, params)
        conn.commit()
        return cur.rowcount > 0

    except sqlite3.Error as err:
        conn.rollback()
        print(f"[datasets] Error updating dataset {dataset_id}: {err}")
        return False

    finally:
        conn.close()


# ---------------------- DELETE ----------------------

def delete_dataset(dataset_id: int) -> bool:
    """Deletes a dataset row. Returns True if a row was deleted."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM datasets_metadata WHERE id = ?", (dataset_id,))
        conn.commit()
        return cur.rowcount > 0
    except sqlite3.Error as err:
        conn.rollback()
        print(f"[datasets] Error deleting dataset {dataset_id}: {err}")
        return False
    finally:
        conn.close()


# ---------------------- BULK (CSV loader) ----------------------

def load_datasets_from_csv(csv_path: str, clear_table: bool = True) -> int:
    """Load datasets from CSV using shared csv_loader (helps to keep DB connections tidy)."""
    return load_csv_to_table(csv_path, "datasets_metadata", clear_table=clear_table)


def get_total_datasets_count() -> int:
    """Return the total number of dataset rows using the csv loader helper."""
    return count_table_records("datasets_metadata")


# ---------------------- ANALYTICS ----------------------

def get_dataset_count_by_uploaded_by() -> Dict[str, int]:
    """Count datasets grouped by uploader."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT uploaded_by, COUNT(*) AS count
            FROM datasets_metadata
            GROUP BY uploaded_by
            """
        )
        return {row['uploaded_by']: row['count'] for row in cur.fetchall()}
    finally:
        conn.close()


def get_all_analytics() -> Dict[str, Any]:
    """Return a small analytics bundle in one DB connection (fast and tidy)."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        stats: Dict[str, Any] = {}

        cur.execute("SELECT COUNT(*) as total FROM datasets_metadata")
        stats['total_datasets'] = cur.fetchone()['total']

        cur.execute("SELECT COALESCE(SUM(rows), 0) as total_rows FROM datasets_metadata")
        stats['total_rows'] = cur.fetchone()['total_rows']

        cur.execute("SELECT uploaded_by, COUNT(*) as count FROM datasets_metadata GROUP BY uploaded_by")
        stats['by_uploaded_by'] = {r['uploaded_by']: r['count'] for r in cur.fetchall()}

        return stats

    finally:
        conn.close()


def get_recent_datasets(limit: int = 10) -> List[Dict[str, Any]]:
    """Returns the most recently updated datasets as a list of dicts."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM datasets_metadata
            ORDER BY upload_date DESC
            LIMIT ?
            """,
            (limit,)
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ---------------------- SELF TEST ----------------------

def _test_datasets_module():
    """Quick manual test to  run from the command line."""
    print("datasets module quick test")

    dataset_id = create_dataset(
        name="Test_Dataset",
        rows=1000,
        columns=15,
        uploaded_by="test_user",
        upload_date="2024-01-15",
    )
    print("Created dataset:", dataset_id)

    print("Fetch:", get_dataset(dataset_id))
    print("Total datasets count (csv loader):", get_total_datasets_count())
    print("Analytics bundle:", get_all_analytics())
    print("Delete:", delete_dataset(dataset_id))


if __name__ == "__main__":
    _test_datasets_module()