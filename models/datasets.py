"""
Datasets Model (OOP Refactored)
Manages dataset metadata with full CRUD operations and analytics
"""

import sqlite3
from typing import Optional, List, Dict, Any, Tuple, Union
from datetime import date
import pandas as pd
from database.db import connect_database
from models.base_model import BaseModel, BaseAnalytics, ValidationMixin


class DatasetModel(BaseModel, BaseAnalytics, ValidationMixin):      # model for managing dataset metadata
    """
    Handles all database operations for dataset metadata.
    Tracks uploaded datasets with their size and ownership info.
    """
    
    def __init__(self):
        # initialize with the datasets_metadata table; inherits from multiple base classes
        BaseModel.__init__(self, table_name="datasets_metadata")
        BaseAnalytics.__init__(self, table_name="datasets_metadata")
    
    # ==================== CRUD OPERATIONS ====================
    
    def create(
        self,
        name: str,
        rows: int,
        columns: int,
        uploaded_by: str,
        upload_date: str = ""
    ) -> int:
        """
        Create a new dataset metadata record.
        Returns the ID of the created dataset or -1 on failure.
        """
        # validate data before inserting; raises ValueError if invalid
        is_valid, error = self.validate_data(
            name=name,
            rows=rows,
            columns=columns,
            uploaded_by=uploaded_by,
            upload_date=upload_date
        )
        if not is_valid:
            raise ValueError(error)
        
        # default upload_date to today if not provided
        if not upload_date:
            upload_date = date.today().isoformat()
        
        conn = connect_database()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO datasets_metadata
                (name, rows, columns, uploaded_by, upload_date)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, rows, columns, uploaded_by, upload_date)
            )
            new_id = cur.lastrowid      # get the id of the newly created dataset
            conn.commit()
            return new_id
        
        except sqlite3.Error as err:
            conn.rollback()     # undo changes if something went wrong
            print(f"[DatasetModel] Error creating dataset: {err}")
            return -1
        finally:
            conn.close()        # always close the connection
    
    def get_by_id(self, dataset_id: int) -> Optional[Dict[str, Any]]:
        """Get a single dataset by ID"""
        conn = connect_database()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM datasets_metadata WHERE id = ?", (dataset_id,))
            row = cur.fetchone()
            return dict(row) if row else None       # convert to dict or return None if not found
        except sqlite3.Error as err:
            print(f"[DatasetModel] Error fetching dataset {dataset_id}: {err}")
            return None
        finally:
            conn.close()
    
    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a dataset by name; useful for checking if dataset already exists"""
        conn = connect_database()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM datasets_metadata WHERE name = ?", (name,))
            row = cur.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as err:
            print(f"[DatasetModel] Error fetching dataset '{name}': {err}")
            return None
        finally:
            conn.close()
    
    def update(
        self,
        dataset_id: int,
        name: Optional[str] = None,
        rows: Optional[int] = None,
        columns: Optional[int] = None,
        uploaded_by: Optional[str] = None,
        upload_date: Optional[str] = None
    ) -> bool:
        """Update an existing dataset; only updates fields that are provided"""
        # build UPDATE query dynamically
        updates: List[str] = []
        params: List[Any] = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if rows is not None:
            # validate that rows is a positive integer
            is_valid, error = self.validate_positive_number(rows, "rows", allow_zero=False)
            if not is_valid:
                raise ValueError(error)
            updates.append("rows = ?")
            params.append(rows)
        if columns is not None:
            # validate that columns is a positive integer
            is_valid, error = self.validate_positive_number(columns, "columns", allow_zero=False)
            if not is_valid:
                raise ValueError(error)
            updates.append("columns = ?")
            params.append(columns)
        if uploaded_by is not None:
            updates.append("uploaded_by = ?")
            params.append(uploaded_by)
        if upload_date is not None:
            updates.append("upload_date = ?")
            params.append(upload_date)
        
        if not updates:     # nothing to update
            return False
        
        params.append(dataset_id)       # add id for WHERE clause
        
        conn = connect_database()
        try:
            cur = conn.cursor()
            sql = f"UPDATE datasets_metadata SET {', '.join(updates)} WHERE id = ?"
            cur.execute(sql, params)
            conn.commit()
            return cur.rowcount > 0     # returns true if something was actually updated
        except sqlite3.Error as err:
            conn.rollback()
            print(f"[DatasetModel] Error updating dataset {dataset_id}: {err}")
            return False
        finally:
            conn.close()
    
    def validate_data(self, **kwargs) -> Tuple[bool, str]:
        """
        Validate dataset data before creating or updating.
        Returns (is_valid, error_message) tuple.
        """
        validations = []
        
        # check name is not empty
        if 'name' in kwargs:
            validations.append(
                self.validate_not_empty(kwargs['name'], "Name")
            )
        
        # check rows is a positive integer
        if 'rows' in kwargs:
            validations.append(
                self.validate_positive_number(kwargs['rows'], "Rows", allow_zero=False)
            )
        
        # check columns is a positive integer
        if 'columns' in kwargs:
            validations.append(
                self.validate_positive_number(kwargs['columns'], "Columns", allow_zero=False)
            )
        
        # check uploaded_by is not empty
        if 'uploaded_by' in kwargs:
            validations.append(
                self.validate_not_empty(kwargs['uploaded_by'], "Uploaded by")
            )
        
        # return first error found or success
        return self.combine_validations(*validations)
    
    # ==================== FILTERING & SEARCH ====================
    
    def filter_by(
        self,
        uploaded_by: Optional[str] = None,
        min_rows: Optional[int] = None,
        max_rows: Optional[int] = None,
        as_dataframe: bool = False
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Filter datasets by uploader or size range"""
        conn = connect_database()
        try:
            # build query with filters
            query = "SELECT * FROM datasets_metadata WHERE 1=1"
            params: List[Any] = []
            
            if uploaded_by:
                query += " AND uploaded_by = ?"
                params.append(uploaded_by)
            if min_rows is not None:
                query += " AND rows >= ?"
                params.append(min_rows)
            if max_rows is not None:
                query += " AND rows <= ?"
                params.append(max_rows)
            
            query += " ORDER BY upload_date DESC"       # most recent query is shown first
            
            if as_dataframe:
                return pd.read_sql_query(query, conn, params=params)
            
            cur = conn.cursor()
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]
        
        except sqlite3.Error as err:
            print(f"[DatasetModel] Error filtering datasets: {err}")
            return pd.DataFrame() if as_dataframe else []
        finally:
            conn.close()
    
    def search_by_name(self, search_term: str, as_dataframe: bool = False) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Search datasets by name; finds partial matches"""
        conn = connect_database()
        try:
            query = "SELECT * FROM datasets_metadata WHERE name LIKE ? ORDER BY upload_date DESC"
            search_pattern = f"%{search_term}%"     # wildcard search for partial matches
            
            if as_dataframe:
                return pd.read_sql_query(query, conn, params=[search_pattern])
            
            cur = conn.cursor()
            cur.execute(query, [search_pattern])
            return [dict(r) for r in cur.fetchall()]
        
        except sqlite3.Error as err:
            print(f"[DatasetModel] Error searching datasets: {err}")
            return pd.DataFrame() if as_dataframe else []
        finally:
            conn.close()
    
    def get_recent_uploads(self, limit: int = 10, as_dataframe: bool = False) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get most recently uploaded datasets; useful for dashboard"""
        conn = connect_database()
        try:
            query = f"SELECT * FROM datasets_metadata ORDER BY upload_date DESC LIMIT {limit}"
            
            if as_dataframe:
                return pd.read_sql_query(query, conn)
            
            cur = conn.cursor()
            cur.execute(query)
            return [dict(r) for r in cur.fetchall()]
        
        finally:
            conn.close()
    
    # ==================== ANALYTICS ====================
    
    def get_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive analytics for datasets.
        Returns counts, totals, and averages.
        """
        conn = connect_database()
        try:
            cur = conn.cursor()
            stats: Dict[str, Any] = {}
            
            # total count of datasets
            stats['total_datasets'] = self.get_total_count()
            
            # total rows across all datasets
            cur.execute("SELECT COALESCE(SUM(rows), 0) as total_rows FROM datasets_metadata")
            stats['total_rows'] = cur.fetchone()['total_rows']
            
            # group by uploader to see who uploaded what
            stats['by_uploaded_by'] = self.get_count_by_group('uploaded_by')
            
            # calculate averages
            cur.execute("""
                SELECT 
                    AVG(rows) as avg_rows,
                    AVG(columns) as avg_columns
                FROM datasets_metadata
            """)
            row = cur.fetchone()
            stats['avg_rows'] = row['avg_rows'] or 0
            stats['avg_columns'] = row['avg_columns'] or 0
            
            return stats
        
        finally:
            conn.close()
    
    def get_size_distribution(self) -> Dict[str, int]:
        """
        Get distribution of datasets by size category.
        Categorizes datasets as small, medium, or large based on row count.
        """
        conn = connect_database()
        try:
            cur = conn.cursor()
            
            # small datasets have less than 1000 rows
            cur.execute("SELECT COUNT(*) FROM datasets_metadata WHERE rows < 1000")
            small = cur.fetchone()[0]
            
            # medium datasets have between 1000 and 10000 rows
            cur.execute("SELECT COUNT(*) FROM datasets_metadata WHERE rows BETWEEN 1000 AND 10000")
            medium = cur.fetchone()[0]
            
            # large datasets have more than 10000 rows
            cur.execute("SELECT COUNT(*) FROM datasets_metadata WHERE rows > 10000")
            large = cur.fetchone()[0]
            
            return {
                'small': small,
                'medium': medium,
                'large': large
            }
        finally:
            conn.close()
    
    def __str__(self):
        """String representation for user-friendly output"""
        total = self.count()
        return f"DatasetModel({total} datasets)"
    
    def __repr__(self):
        """String representation"""
        return f"<DatasetModel: {self.count()} datasets>"