"""
-- CSV loader -- 
Features:
- Allowed table validation (this will prevent accidental writes)
- Header validation against DB table columns
- Batch inserts via executemany() inside a transaction
- Optional clearing of table before loading
- Verification helper to count rows
"""

from pathlib import Path
import csv
import sqlite3
from typing import List, Tuple, Optional
from app.data.db import connect_database
import pandas as pd

# Begin by defining the allowed target tables to avoid accidental SQL injection via table names
_ALLOWED_TABLES = {"cyber_incidents", "datasets_metadata", "it_tickets", "users"}


def _validate_table_name(table_name: str):
    if table_name not in _ALLOWED_TABLES:
        raise ValueError(f"Invalid table name: {table_name!r}. Allowed: {_ALLOWED_TABLES}")


def _get_table_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    """Return list of column names for a sqlite table (in DB order)."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(%s)" % table_name)  # table name safe after validation
    rows = cur.fetchall()
    return [row[1] for row in rows]  # row[1] is column name


def load_csv_to_table(csv_file_path: str,
                      table_name: str,
                      db_path: Optional[str] = None,
                      clear_table: bool = True) -> int:
    """
    Load data from a CSV file into a SQLite table using a single transaction and executemany.

    Args:
        csv_file_path: path to CSV file
        table_name: target DB table (must be in _ALLOWED_TABLES)
        db_path: optional custom DB path forwarded to connect_database()
        clear_table: if True, DELETE FROM table before inserting

    Returns:
        int: number of rows inserted
    """
    _validate_table_name(table_name)
    csv_path = Path(csv_file_path)

    if not csv_path.exists():
        print(f"[csv_loader] CSV file not found: {csv_path}")
        return 0

    conn = connect_database(db_path)  # your connect_database accepts optional path
    try:
        # Validate and fetch DB columns
        db_cols = _get_table_columns(conn, table_name)
        if not db_cols:
            raise ValueError(f"Table {table_name!r} has no columns or does not exist.")

        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            csv_cols = reader.fieldnames
            if not csv_cols:
                print(f"[csv_loader] No header found in CSV: {csv_path}")
                return 0

            # Ensure CSV columns are a subset of table columns OR exactly match required insert columns
            # We'll insert only columns that are present in both (in DB order) to be safe.
            insert_cols = [col for col in db_cols if col in csv_cols]
            if not insert_cols:
                raise ValueError("No overlapping columns between CSV and table columns: "
                                 f"csv={csv_cols}, table={db_cols}")

            placeholders = ", ".join(["?"] * len(insert_cols))
            col_list_sql = ", ".join(insert_cols)
            insert_sql = f"INSERT INTO {table_name} ({col_list_sql}) VALUES ({placeholders})"

            # Optionally clear table
            cur = conn.cursor()
            if clear_table:
                cur.execute(f"DELETE FROM {table_name}")
                conn.commit()

            # Prepare batch insert
            batch: List[Tuple] = []
            rows = 0
            for row in reader:
                # build values tuple in the same order as insert_cols
                values = tuple((row.get(c) if row.get(c, "") != "" else None) for c in insert_cols)
                batch.append(values)
                # flush in reasonable batches to keep memory usage low
                if len(batch) >= 500:
                    cur.executemany(insert_sql, batch)
                    rows += len(batch)
                    batch.clear()

            # final flush
            if batch:
                cur.executemany(insert_sql, batch)
                rows += len(batch)

            conn.commit()
            print(f"[csv_loader] Loaded {rows} rows from {csv_path.name} into {table_name}")
            return rows

    except sqlite3.IntegrityError as ie:
        conn.rollback()
        print(f"[csv_loader] Integrity error loading {csv_path.name} into {table_name}: {ie}")
        return 0
    except Exception as e:
        conn.rollback()
        print(f"[csv_loader] Error loading {csv_path.name} into {table_name}: {e}")
        return 0
    finally:
        conn.close()


def load_all_csv_data(data_dir: str = "DATA", db_path: Optional[str] = None, clear_table: bool = True):
    """
    Load the expected CSVs into their respective tables.

    Returns:
        dict: mapping table_name -> rows_loaded
    """
    data_dir = Path(data_dir)
    mappings = {
        "cyber_incidents": data_dir / "cyber_incidents.csv",
        "datasets_metadata": data_dir / "datasets_metadata.csv",
        "it_tickets": data_dir / "it_tickets.csv",
    }

    results = {}
    print("[csv_loader] Starting CSV data loading...")
    for table, csv_path in mappings.items():
        if csv_path.exists():
            rows = load_csv_to_table(str(csv_path), table, db_path=db_path, clear_table=clear_table)
            results[table] = rows
        else:
            print(f"[csv_loader] CSV not found: {csv_path}")
            results[table] = 0
    print("[csv_loader] Data loading complete.")
    return results


def count_table_records(table_name: str, db_path: Optional[str] = None) -> int:
    """Return number of records in a table."""
    _validate_table_name(table_name)
    conn = connect_database(db_path)
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        return int(cur.fetchone()[0])
    finally:
        conn.close()


def verify_data_loading(db_path: Optional[str] = None):
    """Print counts for the three Week-8 tables."""
    tables = ["cyber_incidents", "datasets_metadata", "it_tickets"]
    print("\n[csv_loader] Verifying data loading...")
    for t in tables:
        try:
            cnt = count_table_records(t, db_path=db_path)
            print(f"  {t}: {cnt} records")
        except Exception as e:
            print(f"  {t}: error ({e})")


if __name__ == "__main__":
    # initialize schema if available
    try:
        from .schema import init_schema
        init_schema()
    except Exception:
        # schema may exist already; ignore errors here
        pass

    load_all_csv_data()
    verify_data_loading()
