"""
Cybersecurity Incidents Model (OOP Refactored)
Manages cyber incident records with full CRUD operations and analytics
"""

import sqlite3
from typing import Optional, List, Dict, Any, Tuple, Union
from datetime import datetime
import pandas as pd
from database.db import connect_database
from models.base_model import BaseModel, BaseAnalytics, ValidationMixin


class IncidentModel(BaseModel, BaseAnalytics, ValidationMixin):      # model for managing cybersecurity incidents
    """
    Handles all database operations for cybersecurity incidents.
    Inherits common CRUD and analytics from base classes.
    """
    
    # these are the valid options for incident fields; used for validation
    VALID_SEVERITIES = ["Low", "Medium", "High", "Critical"]
    VALID_STATUSES = ["Open", "In Progress", "Resolved", "Closed"]
    VALID_CATEGORIES = ["Phishing", "Malware", "DDoS", "Unauthorized Access", "Misconfiguration"]
    
    def __init__(self):
        # initialize with the cyber_incidents table; inherits from multiple base classes
        BaseModel.__init__(self, table_name="cyber_incidents")
        BaseAnalytics.__init__(self, table_name="cyber_incidents")
    
    # ==================== CRUD OPERATIONS ====================
    
    def create(
        self,
        timestamp: str,
        category: str,
        severity: str,
        status: str,
        description: str = "",
        reported_by: str = ""
    ) -> int:
        """
        Create a new cybersecurity incident.
        Returns the ID of the created incident or -1 on failure.
        """
        # validate data before inserting; raises ValueError if invalid
        is_valid, error = self.validate_data(
            timestamp=timestamp,
            category=category,
            severity=severity,
            status=status
        )
        if not is_valid:
            raise ValueError(error)
        
        conn = connect_database()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO cyber_incidents
                (timestamp, category, severity, status, description, reported_by)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (timestamp, category, severity, status, description, reported_by)
            )
            new_id = cur.lastrowid      # get the id of the newly created incident
            conn.commit()
            return new_id
        
        except sqlite3.Error as err:
            conn.rollback()     # undo changes if something went wrong
            print(f"[IncidentModel] Error creating incident: {err}")
            return -1
        finally:
            conn.close()        # always close connection
    
    def get_by_id(self, incident_id: int) -> Optional[Dict[str, Any]]:
        """Get a single incident by ID"""
        conn = connect_database()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM cyber_incidents WHERE id = ?", (incident_id,))
            row = cur.fetchone()
            return dict(row) if row else None       # convert to dict or return None if not found
        except sqlite3.Error as err:
            print(f"[IncidentModel] Error fetching incident {incident_id}: {err}")
            return None
        finally:
            conn.close()
    
    def update(
        self,
        incident_id: int,
        timestamp: Optional[str] = None,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        description: Optional[str] = None,
        reported_by: Optional[str] = None
    ) -> bool:
        """Update an existing incident; only updates fields that are provided"""
        # build UPDATE query dynamically based on what fields are provided
        update_fields = []
        values = []
        
        if timestamp is not None:
            update_fields.append("timestamp = ?")
            values.append(timestamp)
        if category is not None:
            update_fields.append("category = ?")
            values.append(category)
        if severity is not None:
            update_fields.append("severity = ?")
            values.append(severity)
        if status is not None:
            update_fields.append("status = ?")
            values.append(status)
        if description is not None:
            update_fields.append("description = ?")
            values.append(description)
        if reported_by is not None:
            update_fields.append("reported_by = ?")
            values.append(reported_by)
        
        if not update_fields:       # nothing to update
            return False
        
        values.append(incident_id)      # add id for WHERE clause
        
        conn = connect_database()
        try:
            cur = conn.cursor()
            query = f"UPDATE cyber_incidents SET {', '.join(update_fields)} WHERE id = ?"
            cur.execute(query, values)
            conn.commit()
            return cur.rowcount > 0     # returns true if something was actually updated
        except sqlite3.Error as err:
            conn.rollback()
            print(f"[IncidentModel] Error updating incident {incident_id}: {err}")
            return False
        finally:
            conn.close()
    
    def validate_data(
        self,
        timestamp: str = None,
        category: str = None,
        severity: str = None,
        status: str = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate incident data before creating or updating.
        Returns (is_valid, error_message) tuple.
        """
        validations = []
        
        # check timestamp is not empty
        if timestamp is not None:
            validations.append(
                self.validate_not_empty(timestamp, "Timestamp")
            )
        
        # check category is valid
        if category is not None:
            validations.append(
                self.validate_in_list(category, self.VALID_CATEGORIES, "Category")
            )
        
        # check severity is valid
        if severity is not None:
            validations.append(
                self.validate_in_list(severity, self.VALID_SEVERITIES, "Severity")
            )
        
        # check status is valid
        if status is not None:
            validations.append(
                self.validate_in_list(status, self.VALID_STATUSES, "Status")
            )
        
        # return first error found or success
        return self.combine_validations(*validations)
    
    # ==================== FILTERING & SEARCH ====================
    
    def filter_by(
        self,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        as_dataframe: bool = False
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Filter incidents by category, severity, or status"""
        # build WHERE clause based on provided filters
        filters = {}
        if category:
            filters['category'] = category
        if severity:
            filters['severity'] = severity
        if status:
            filters['status'] = status
        
        # use the base class filter_by method
        return super().filter_by(as_dataframe=as_dataframe, **filters)
    
    def get_open_incidents(self, as_dataframe: bool = False) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get all incidents that are not closed"""
        conn = connect_database()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM cyber_incidents WHERE status != 'Closed' ORDER BY timestamp DESC"
            )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            
            data = [dict(zip(columns, row)) for row in rows]
            
            if as_dataframe:
                return pd.DataFrame(data)
            return data
        except sqlite3.Error as err:
            print(f"[IncidentModel] Error fetching open incidents: {err}")
            return pd.DataFrame() if as_dataframe else []
        finally:
            conn.close()
    
    def get_critical_incidents(self, as_dataframe: bool = False) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get all critical severity incidents"""
        return self.filter_by(severity="Critical", as_dataframe=as_dataframe)
    
    # ==================== ANALYTICS ====================
    
    def get_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive analytics for cybersecurity incidents.
        Returns counts and breakdowns by severity, status, and category.
        """
        conn = connect_database()
        try:
            cur = conn.cursor()
            
            # get total count
            cur.execute("SELECT COUNT(*) FROM cyber_incidents")
            total = cur.fetchone()[0]
            
            # count open incidents (anything not closed)
            cur.execute("SELECT COUNT(*) FROM cyber_incidents WHERE status != 'Closed'")
            open_count = cur.fetchone()[0]
            
            # group by severity
            cur.execute("""
                SELECT severity, COUNT(*) as count
                FROM cyber_incidents
                GROUP BY severity
            """)
            by_severity = {row[0]: row[1] for row in cur.fetchall()}
            
            # group by status
            cur.execute("""
                SELECT status, COUNT(*) as count
                FROM cyber_incidents
                GROUP BY status
            """)
            by_status = {row[0]: row[1] for row in cur.fetchall()}
            
            # group by category
            cur.execute("""
                SELECT category, COUNT(*) as count
                FROM cyber_incidents
                GROUP BY category
                ORDER BY count DESC
            """)
            by_category = {row[0]: row[1] for row in cur.fetchall()}
            
            # return everything as a dictionary
            return {
                'total_incidents': total,
                'open_incidents': open_count,
                'by_severity': by_severity,
                'by_status': by_status,
                'by_category': by_category
            }
        
        except sqlite3.Error as err:
            print(f"[IncidentModel] Error getting analytics: {err}")
            return {
                'total_incidents': 0,
                'open_incidents': 0,
                'by_severity': {},
                'by_status': {},
                'by_category': {}
            }
        finally:
            conn.close()
    
    def get_severity_distribution(self) -> Dict[str, int]:
        """Get count of incidents by severity level"""
        return self.get_count_by_field('severity')
    
    def get_category_distribution(self) -> Dict[str, int]:
        """Get count of incidents by category"""
        return self.get_count_by_field('category')
    
    def get_recent_incidents(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent incidents"""
        return self.get_recent_records(limit=limit, order_by="timestamp")
    
    def __str__(self):
        """String representation for user-friendly output"""
        total = self.count()
        return f"IncidentModel({total} incidents)"
    
    def __repr__(self):
        """String representation"""
        return f"<IncidentModel: {self.count()} incidents>"
