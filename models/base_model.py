"""
Base Model Classes for OOP Architecture
Provides common CRUD operations and analytics for all domain models
"""

import sqlite3
from typing import Optional, List, Dict, Any, Tuple, Union
from abc import ABC, abstractmethod
import pandas as pd
from database.db import connect_database


class BaseModel(ABC):      # base class for all our models; handles common database stuff
    """
    Abstract base class for all domain models.
    Provides common CRUD operations and utilities.
    """
    
    def __init__(self, table_name: str):
        # initialize with the table name this model will work with
        self.table_name = table_name
        self._conn = None       # database connection will be created lazily when needed
    
    @property
    def conn(self) -> sqlite3.Connection:
        # get database connection; only creates it when first accessed (lazy loading)
        if self._conn is None:
            self._conn = connect_database()
        return self._conn
    
    def close(self):
        # close the database connection to free up resources
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def __enter__(self):
        # context manager entry; allows using 'with' statement
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # context manager exit; automatically closes connection when done
        self.close()
    
    # ==================== ABSTRACT METHODS ====================
    # these methods must be implemented by child classes
    
    @abstractmethod
    def create(self, **kwargs) -> int:
        # each model needs to implement its own create method
        pass
    
    @abstractmethod
    def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        # each model needs to implement its own get method
        pass
    
    @abstractmethod
    def update(self, id: int, **kwargs) -> bool:
        # each model needs to implement its own update method
        pass
    
    @abstractmethod
    def validate_data(self, **kwargs) -> Tuple[bool, Optional[str]]:
        # each model needs to validate its own data
        pass
    
    # ==================== COMMON CRUD OPERATIONS ====================
    
    def delete(self, id: int) -> bool:
        # delete a record by id; works for any table
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"DELETE FROM {self.table_name} WHERE id = ?", (id,))
            self.conn.commit()
            return cursor.rowcount > 0      # returns true if something was actually deleted
        except sqlite3.Error as e:
            print(f"Error deleting from {self.table_name}: {e}")
            return False
    
    def get_all(self, as_dataframe: bool = False) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        # get all records from the table; can return as list of dicts or pandas dataframe
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT * FROM {self.table_name}")
            columns = [description[0] for description in cursor.description]       # get column names
            rows = cursor.fetchall()
            
            # convert rows to list of dictionaries for easier access
            data = [dict(zip(columns, row)) for row in rows]
            
            if as_dataframe:
                return pd.DataFrame(data)       # convert to pandas if requested
            return data
        except sqlite3.Error as e:
            print(f"Error fetching from {self.table_name}: {e}")
            return pd.DataFrame() if as_dataframe else []
    
    def count(self) -> int:
        # count total number of records in the table
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            result = cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error as e:
            print(f"Error counting {self.table_name}: {e}")
            return 0
    
    def exists(self, id: int) -> bool:
        # check if a record with given id exists
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT 1 FROM {self.table_name} WHERE id = ? LIMIT 1", (id,))
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            print(f"Error checking existence in {self.table_name}: {e}")
            return False
    
    def filter_by(self, as_dataframe: bool = False, **filters) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        # filter records by any field; builds WHERE clause dynamically
        try:
            # build the WHERE clause from the filters provided
            where_clauses = []
            values = []
            for field, value in filters.items():
                if value is not None:       # only add filter if value is provided
                    where_clauses.append(f"{field} = ?")
                    values.append(value)
            
            # construct the full query
            query = f"SELECT * FROM {self.table_name}"
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            cursor = self.conn.cursor()
            cursor.execute(query, values)
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            # convert to list of dicts
            data = [dict(zip(columns, row)) for row in rows]
            
            if as_dataframe:
                return pd.DataFrame(data)
            return data
        except sqlite3.Error as e:
            print(f"Error filtering {self.table_name}: {e}")
            return pd.DataFrame() if as_dataframe else []
    
    def get_count_by_field(self, field: str) -> Dict[str, int]:
        # count records grouped by a specific field; useful for analytics
        try:
            cursor = self.conn.cursor()
            query = f"""
                SELECT {field}, COUNT(*) as count 
                FROM {self.table_name} 
                GROUP BY {field}
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            # convert to dictionary where key is field value, value is count
            return {str(row[0]): row[1] for row in rows}
        except sqlite3.Error as e:
            print(f"Error counting by {field} in {self.table_name}: {e}")
            return {}
    
    def __str__(self):
        # string representation for debugging
        total = self.count()
        return f"{self.__class__.__name__}({total} records)"
    
    def __repr__(self):
        # detailed string representation
        return f"<{self.__class__.__name__}: {self.count()} records in {self.table_name}>"


class BaseAnalytics:        # base class for analytics operations across all domains
    """
    Provides common analytics operations for domain models.
    Can be mixed into any model class.
    """
    
    def __init__(self, table_name: str):
        # initialize with table name for analytics queries
        self.table_name = table_name
        self._conn = None
    
    @property
    def conn(self) -> sqlite3.Connection:
        # get database connection; lazy loading like in BaseModel
        if self._conn is None:
            self._conn = connect_database()
        return self._conn
    
    def get_total_count(self) -> int:
        # get total number of records; basic analytics metric
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            result = cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error as e:
            print(f"Error getting count from {self.table_name}: {e}")
            return 0
    
    def get_count_by_group(self, group_field: str) -> Dict[str, int]:
        # count records grouped by any field; flexible grouping for analytics
        try:
            cursor = self.conn.cursor()
            query = f"""
                SELECT {group_field}, COUNT(*) as count 
                FROM {self.table_name} 
                GROUP BY {group_field}
                ORDER BY count DESC
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            return {str(row[0]): row[1] for row in rows}
        except sqlite3.Error as e:
            print(f"Error grouping by {group_field}: {e}")
            return {}
    
    def get_recent_records(self, limit: int = 10, order_by: str = "id") -> List[Dict[str, Any]]:
        # get the most recent records; useful for dashboards
        try:
            cursor = self.conn.cursor()
            query = f"""
                SELECT * FROM {self.table_name} 
                ORDER BY {order_by} DESC 
                LIMIT ?
            """
            cursor.execute(query, (limit,))
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        except sqlite3.Error as e:
            print(f"Error getting recent records: {e}")
            return []
    
    def get_aggregates(self, field: str) -> Dict[str, float]:
        # get statistical aggregates for numeric fields; min, max, avg, sum
        try:
            cursor = self.conn.cursor()
            query = f"""
                SELECT 
                    MIN({field}) as min,
                    MAX({field}) as max,
                    AVG({field}) as avg,
                    SUM({field}) as sum
                FROM {self.table_name}
            """
            cursor.execute(query)
            row = cursor.fetchone()
            if row:
                return {
                    'min': row[0] or 0,
                    'max': row[1] or 0,
                    'avg': row[2] or 0,
                    'sum': row[3] or 0
                }
            return {'min': 0, 'max': 0, 'avg': 0, 'sum': 0}
        except sqlite3.Error as e:
            print(f"Error calculating aggregates: {e}")
            return {'min': 0, 'max': 0, 'avg': 0, 'sum': 0}


class ValidationMixin:      # helper class with common validation methods
    """
    Common validation methods that can be used by any model.
    Mix this into model classes that need validation.
    """
    
    @staticmethod
    def validate_not_empty(value: Any, field_name: str) -> Tuple[bool, Optional[str]]:
        # check that a field is not empty or whitespace
        if value is None or (isinstance(value, str) and not value.strip()):
            return False, f"{field_name} cannot be empty"
        return True, None
    
    @staticmethod
    def validate_in_list(value: Any, valid_values: List[Any], field_name: str) -> Tuple[bool, Optional[str]]:
        # check that value is in a list of allowed values
        if value not in valid_values:
            return False, f"{field_name} must be one of: {', '.join(map(str, valid_values))}"
        return True, None
    
    @staticmethod
    def validate_positive_number(value: Any, field_name: str, allow_zero: bool = False) -> Tuple[bool, Optional[str]]:
        # check that a number is positive (optionally allowing zero)
        try:
            num = float(value)
            if allow_zero:
                if num < 0:
                    return False, f"{field_name} must be non-negative"
            else:
                if num <= 0:
                    return False, f"{field_name} must be greater than zero"
            return True, None
        except (ValueError, TypeError):
            return False, f"{field_name} must be a valid number"
    
    @staticmethod
    def validate_string_length(value: str, field_name: str, min_length: int = 0, max_length: int = None) -> Tuple[bool, Optional[str]]:
        # check string length is within bounds
        if not isinstance(value, str):
            return False, f"{field_name} must be a string"
        
        length = len(value.strip())
        if length < min_length:
            return False, f"{field_name} must be at least {min_length} characters"
        if max_length and length > max_length:
            return False, f"{field_name} must be at most {max_length} characters"
        
        return True, None
    
    @staticmethod
    def combine_validations(*validation_results: Tuple[bool, Optional[str]]) -> Tuple[bool, Optional[str]]:
        # combine multiple validation results; returns first error found
        for is_valid, error in validation_results:
            if not is_valid:
                return False, error
        return True, None
