"""
CSV loader; made this to facilitate csv implementations

Features include:
- Allowed table validation (prevents accidental writes)
- Header validation against DB table columns
- Batch inserts via executemany() inside a transaction
- Optional clearing of table before loading
- Simple type coercion for common numeric/date columns
- Verification helper to count rows
"""

from pathlib import Path
import csv
import sqlite3
from typing import List, Tuple, Optional, Any
from database.db import connect_database

# we start by defining the allowed target tables to avoid accidental SQL injection via table names
_ALLOWED_TABLES = {"cyber_incidents", "datasets_metadata", "it_tickets", "users"}


def _validate_table_name(table_name: str):
    if table_name not in _ALLOWED_TABLES:
        raise ValueError(f"Invalid table name: {table_name!r}. Allowed: {_ALLOWED_TABLES}")


def _get_table_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    """Return list of column names for a sqlite table (in DB order)."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(%s)" % table_name)  # table name safe after validation
    rows = cur.fetchall()
    return [row[1] for row in rows]  # row[1] = column name


# --- coercion helpers ---

def _coerce_value(col: str, raw: Optional[str]) -> Any:
    """Coerce a raw CSV string into an appropriate Python type.

    This is intentionally simple and based on expected column names in this
    project. If coercion fails we return the original string and print a
    gentle warning. That way the loader is helpful, not brittle.
    """
    if raw is None:
        return None
    raw = raw.strip()
    if raw == "":
        return None

    # known-int columns
    if col in ("record_count",):
        try:
            return int(raw)
        except ValueError:
            try:
                return int(float(raw))
            except Exception:
                print(f"[csv_loader] Warning: could not convert {col}={raw!r} to int; leaving as text")
                return raw

    # date-like columns
    if col in ("created_date", "resolved_date", "last_updated", "upload_date", "date"):
        normalized = _normalize_date(raw)
        if normalized != raw:
            return normalized
        # if the normalization didn't change the value, return normalized anyway
        return normalized

    # default: return the cleaned string
    return raw


def load_csv_to_table(csv_file_path: str,
                      table_name: str,
                      db_path: Optional[str] = None,
                      clear_table: bool = True) -> int:
    """
    Load data from a CSV file into a SQLite table using a single transaction and executemany.

    This update performs coercion so numeric columns become numbers
    and date columns are normalized, which avoids many subtle bugs later on.
    """
    _validate_table_name(table_name)
    csv_path = Path(csv_file_path)

    if not csv_path.exists():
        print(f"[csv_loader] CSV file not found: {csv_path}")
        return 0

    conn = connect_database(db_path)  # connect_database can accept optional path
    try:
        # fetch DB columns and verify
        db_cols = _get_table_columns(conn, table_name)
        if not db_cols:
            raise ValueError(f"Table {table_name!r} has no columns or does not exist.")

        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            csv_cols = reader.fieldnames or []
            if not csv_cols:
                print(f"[csv_loader] No header found in CSV: {csv_path}")
                return 0

            # keep columns in DB order, only those present in the CSV
            insert_cols = [col for col in db_cols if col in csv_cols]
            if not insert_cols:
                raise ValueError("No overlapping columns between CSV and table columns: "
                                 f"csv={csv_cols}, table={db_cols}")

            placeholders = ", ".join(["?"] * len(insert_cols))
            col_list_sql = ", ".join(insert_cols)
            insert_sql = f"INSERT INTO {table_name} ({col_list_sql}) VALUES ({placeholders})"

            cur = conn.cursor()
            if clear_table:
                cur.execute(f"DELETE FROM {table_name}")
                conn.commit()

            batch: List[Tuple] = []
            rows = 0
            for row in reader:
                cleaned = {}
                for c in insert_cols:
                    raw = row.get(c, None)
                    try:
                        cleaned[c] = _coerce_value(c, raw)
                    except Exception as e:
                        print(f"[csv_loader] Warning: failed to coerce column {c} value {raw!r}: {e}")
                        cleaned[c] = raw

                values = tuple(cleaned[c] for c in insert_cols)
                batch.append(values)

                if len(batch) >= 500:
                    cur.executemany(insert_sql, batch)
                    rows += len(batch)
                    batch.clear()

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
    """Load the expected CSVs into their respective tables.

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
    """Returns the number of records in a table."""
    _validate_table_name(table_name)
    conn = connect_database(db_path)
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        return int(cur.fetchone()[0])
    finally:
        conn.close()


# THIS IS LEFTOVER TEST CODE; IGNORE
# if __name__ == "__main__":
#     # initialize schema if available
#     try:
#         from .schema import init_schema
#         init_schema()
#     except Exception:
#         # schema may exist already; ignore errors here
#         pass

#     load_all_csv_data()
#     verify_data_loading()
