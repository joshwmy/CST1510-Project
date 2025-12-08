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
from typing import List, Tuple, Optional, Any, Dict
import pandas as pd
import time
import os
from datetime import date
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


def _normalize_date(raw: str) -> str:
    """Try to normalize date strings to ISO format."""
    if not raw:
        return raw
    raw = raw.strip()
    
    # Already looks like ISO date
    if len(raw) >= 10 and raw[4] == '-' and raw[7] == '-':
        return raw
    
    # Try to parse common date formats
    import re
    from datetime import datetime
    
    # Try various formats
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%m/%d/%Y %H:%M:%S',
        '%d/%m/%Y %H:%M:%S',
        '%Y/%m/%d %H:%M:%S',
        '%d-%m-%Y %H:%M:%S',
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d/%m/%Y'
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.isoformat()
        except ValueError:
            continue
    
    # If we can't parse it, return as-is
    return raw

# --- coercion helpers ---

def _coerce_value(col: str, raw: Optional[str]) -> Any:
    """Coerce a raw CSV string into an appropriate Python type."""
    if raw is None:
        return None
    raw = raw.strip()
    if raw == "":
        return None

    # known-int columns
    if col in ("record_count", "rows", "columns"):
        try:
            return int(raw)
        except ValueError:
            try:
                return int(float(raw))
            except Exception:
                print(f"[csv_loader] Warning: could not convert {col}={raw!r} to int; leaving as text")
                return raw

    # date-like columns
    if col in ("created_date", "resolved_date", "last_updated", "upload_date", "date", "timestamp", "created_at"):
        normalized = _normalize_date(raw)
        if normalized != raw:
            return normalized
        return normalized

    # default: return the cleaned string
    return raw

def load_csv_to_table(csv_file_path: str,
                      table_name: str,
                      db_path: Optional[str] = None,
                      clear_table: bool = True) -> int:
    """
    Load data from a CSV file into a SQLite table using a single transaction and executemany.
    """
    _validate_table_name(table_name)
    csv_path = Path(csv_file_path)

    if not csv_path.exists():
        print(f"[csv_loader] CSV file not found: {csv_path}")
        return 0

    conn = connect_database(db_path)
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


# -------------------------
# CSV Upload Handlers
# -------------------------
# -------------------------
# CSV Upload Handlers - FIXED VERSION
# -------------------------
def handle_csv_upload(uploaded_file, domain: str, username: str):
    """
    Process uploaded CSV files for different domains.
    Import modules HERE to avoid circular imports.
    """
    try:
        # Read the CSV file
        df = pd.read_csv(uploaded_file)
        
        # Import modules locally to avoid circular dependency
        if domain == "Datasets":
            from models import datasets as datasets_mod
            return handle_dataset_upload(df, username, uploaded_file.name, datasets_mod)
        elif domain == "Cybersecurity":
            from models import incidents as incidents_mod
            return handle_incident_upload(df, username, uploaded_file.name, incidents_mod)
        elif domain == "IT Tickets":
            from models import tickets as tickets_mod
            return handle_ticket_upload(df, username, uploaded_file.name, tickets_mod)
        else:
            return False, f"Unknown domain: {domain}"
            
    except Exception as e:
        return False, f"Error reading CSV: {str(e)}"


def handle_dataset_upload(df, username, filename, datasets_mod):
    """Create dataset entry from uploaded CSV."""
    try:
        dataset_name = os.path.splitext(filename)[0]
        upload_date = date.today().isoformat()

        created = datasets_mod.create_dataset(
            name=dataset_name,
            rows=len(df),
            columns=len(df.columns),
            uploaded_by=username or "unknown",
            upload_date=upload_date
        )
        if created == -1:
            return False, f"Dataset creation failed for '{dataset_name}' (db error)."
        return True, f"Dataset '{dataset_name}' created with {len(df)} rows (id {created})"
    except Exception as e:
        return False, f"Error creating dataset: {str(e)}"


def handle_incident_upload(df, username, filename, incidents_mod):
    """Create incidents from uploaded CSV."""
    try:
        created_count = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                new_id = incidents_mod.create_incident(
                    timestamp=row.get('timestamp', time.strftime("%Y-%m-%d %H:%M:%S")),
                    category=row.get('category', 'Unknown'),
                    severity=row.get('severity', 'Medium'),
                    status=row.get('status', 'Open'),
                    description=row.get('description', f'Uploaded from {filename}'),
                    reported_by=row.get('reported_by', username)
                )
                if new_id != -1:
                    created_count += 1
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")
        
        message = f"Created {created_count} incidents from CSV"
        if errors:
            message += f". Errors: {', '.join(errors[:3])}"
        return True, message
    except Exception as e:
        return False, f"Error processing incidents: {str(e)}"


def handle_ticket_upload(df, username, filename, tickets_mod):
    """Create tickets from uploaded CSV."""
    try:
        created_count = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                ticket_id = f"CSV-{int(time.time())}-{idx}"
                priority = row.get('priority', 'Medium') or 'Medium'
                status = row.get('status', 'Open') or 'Open'
                category = row.get('category', 'General') or 'General'
                subject = row.get('title', f'Ticket from {filename}') or f'Ticket from {filename}'
                description = row.get('description', '') or ''
                created_at = row.get('created_at', date.today().isoformat()) or date.today().isoformat()
                resolved_date = row.get('resolved_date', None)
                assigned_to = row.get('assigned_to', None)

                new_db_id = tickets_mod.create_ticket(
                    ticket_id=ticket_id,
                    priority=priority,
                    status=status,
                    category=category,
                    subject=subject,
                    description=description,
                    created_at=created_at,
                    resolved_date=resolved_date,
                    assigned_to=assigned_to
                )
                if new_db_id == -1:
                    errors.append(f"Row {idx}: DB error")
                else:
                    created_count += 1
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")

        message = f"Created {created_count} tickets from CSV"
        if errors:
            message += f". Errors: {', '.join(errors[:5])}"
        return True, message
    except Exception as e:
        return False, f"Error processing tickets: {str(e)}"
    
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
