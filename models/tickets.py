"""
IT Tickets Model (OOP Refactored)
Manages IT support ticket records with full CRUD operations and analytics
"""

import sqlite3
from typing import Optional, List, Dict, Any, Tuple, Union
from datetime import date
import pandas as pd
from database.db import connect_database
from models.base_model import BaseModel, BaseAnalytics, ValidationMixin


class TicketModel(BaseModel, BaseAnalytics, ValidationMixin):      # model for managing IT support tickets
    """
    Handles all database operations for IT support tickets.
    Inherits common CRUD and analytics from base classes.
    """
    
    # these are the valid options for ticket fields; used for validation
    VALID_PRIORITIES = ["Low", "Medium", "High", "Critical"]
    VALID_STATUSES = ["Open", "In Progress", "Resolved", "Closed"]
    
    def __init__(self):
        # initialize with the it_tickets table; inherits from multiple base classes
        BaseModel.__init__(self, table_name="it_tickets")
        BaseAnalytics.__init__(self, table_name="it_tickets")
    
    # ==================== CRUD OPERATIONS ====================
    
    def create(
        self,
        ticket_id: str,
        priority: str,
        status: str,
        category: str = "",
        subject: str = "",
        description: str = "",
        created_at: str = "",
        resolved_date: Optional[str] = None,
        assigned_to: Optional[str] = None
    ) -> int:
        """
        Create a new IT support ticket.
        Returns the ID of the created ticket or -1 on failure.
        """
        # validate data before inserting; raises ValueError if invalid
        is_valid, error = self.validate_data(
            ticket_id=ticket_id,
            priority=priority,
            status=status
        )
        if not is_valid:
            raise ValueError(error)
        
        # default created_at to today if not provided
        if not created_at:
            created_at = date.today().isoformat()
        
        conn = connect_database()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO it_tickets
                (ticket_id, priority, status, category, subject, description, 
                 created_at, resolved_date, assigned_to)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (ticket_id, priority, status, category, subject, description,
                 created_at, resolved_date, assigned_to)
            )
            new_id = cur.lastrowid      # get the database id of the newly created ticket
            conn.commit()
            return new_id
        
        except sqlite3.Error as err:
            conn.rollback()     # undo changes if something went wrong
            print(f"[TicketModel] Error creating ticket: {err}")
            return -1
        finally:
            conn.close()        # always close connection
    
    def get_by_id(self, db_id: int) -> Optional[Dict[str, Any]]:
        """Get a single ticket by database ID"""
        conn = connect_database()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM it_tickets WHERE id = ?", (db_id,))
            row = cur.fetchone()
            return dict(row) if row else None       # convert to dict or return None if not found
        except sqlite3.Error as err:
            print(f"[TicketModel] Error fetching ticket {db_id}: {err}")
            return None
        finally:
            conn.close()
    
    def get_by_ticket_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get a ticket by its ticket_id string (like 'T-001')"""
        conn = connect_database()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM it_tickets WHERE ticket_id = ?", (ticket_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as err:
            print(f"[TicketModel] Error fetching ticket '{ticket_id}': {err}")
            return None
        finally:
            conn.close()
    
    def update(
        self,
        db_id: int,
        ticket_id: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        subject: Optional[str] = None,
        description: Optional[str] = None,
        resolved_date: Optional[str] = None,
        assigned_to: Optional[str] = None
    ) -> bool:
        """Update an existing ticket; only updates fields that are provided"""
        # build UPDATE query dynamically based on what fields are provided
        update_fields = []
        values = []
        
        if ticket_id is not None:
            update_fields.append("ticket_id = ?")
            values.append(ticket_id)
        if priority is not None:
            update_fields.append("priority = ?")
            values.append(priority)
        if status is not None:
            update_fields.append("status = ?")
            values.append(status)
        if category is not None:
            update_fields.append("category = ?")
            values.append(category)
        if subject is not None:
            update_fields.append("subject = ?")
            values.append(subject)
        if description is not None:
            update_fields.append("description = ?")
            values.append(description)
        if resolved_date is not None:
            update_fields.append("resolved_date = ?")
            values.append(resolved_date)
        if assigned_to is not None:
            update_fields.append("assigned_to = ?")
            values.append(assigned_to)
        
        if not update_fields:       # nothing to update
            return False
        
        values.append(db_id)      # add id for WHERE clause
        
        conn = connect_database()
        try:
            cur = conn.cursor()
            query = f"UPDATE it_tickets SET {', '.join(update_fields)} WHERE id = ?"
            cur.execute(query, values)
            conn.commit()
            return cur.rowcount > 0     # returns true if something was actually updated
        except sqlite3.Error as err:
            conn.rollback()
            print(f"[TicketModel] Error updating ticket {db_id}: {err}")
            return False
        finally:
            conn.close()
    
    def validate_data(
        self,
        ticket_id: str = None,
        priority: str = None,
        status: str = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate ticket data before creating or updating.
        Returns (is_valid, error_message) tuple.
        """
        validations = []
        
        # check ticket_id is not empty
        if ticket_id is not None:
            validations.append(
                self.validate_not_empty(ticket_id, "Ticket ID")
            )
        
        # check priority is valid
        if priority is not None:
            validations.append(
                self.validate_in_list(priority, self.VALID_PRIORITIES, "Priority")
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
        priority: Optional[str] = None,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        as_dataframe: bool = False
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Filter tickets by priority, status, or assignment"""
        # build WHERE clause based on provided filters
        filters = {}
        if priority:
            filters['priority'] = priority
        if status:
            filters['status'] = status
        if assigned_to:
            filters['assigned_to'] = assigned_to
        
        # use the base class filter_by method
        return super().filter_by(as_dataframe=as_dataframe, **filters)
    
    def get_open_tickets(self, as_dataframe: bool = False) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get all tickets that are not closed"""
        conn = connect_database()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM it_tickets WHERE status != 'Closed' ORDER BY created_at DESC"
            )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            
            data = [dict(zip(columns, row)) for row in rows]
            
            if as_dataframe:
                return pd.DataFrame(data)
            return data
        except sqlite3.Error as err:
            print(f"[TicketModel] Error fetching open tickets: {err}")
            return pd.DataFrame() if as_dataframe else []
        finally:
            conn.close()
    
    def get_high_priority_tickets(self, as_dataframe: bool = False) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get all high or critical priority tickets"""
        conn = connect_database()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM it_tickets WHERE priority IN ('High', 'Critical') ORDER BY created_at DESC"
            )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            
            data = [dict(zip(columns, row)) for row in rows]
            
            if as_dataframe:
                return pd.DataFrame(data)
            return data
        except sqlite3.Error as err:
            print(f"[TicketModel] Error fetching high priority tickets: {err}")
            return pd.DataFrame() if as_dataframe else []
        finally:
            conn.close()
    
    # ==================== ANALYTICS ====================
    
    def get_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive analytics for IT tickets.
        Returns counts and breakdowns by priority, status, and category.
        """
        conn = connect_database()
        try:
            cur = conn.cursor()
            
            # get total count
            cur.execute("SELECT COUNT(*) FROM it_tickets")
            total = cur.fetchone()[0]
            
            # count open tickets (anything not closed)
            cur.execute("SELECT COUNT(*) FROM it_tickets WHERE status != 'Closed'")
            open_count = cur.fetchone()[0]
            
            # group by priority
            cur.execute("""
                SELECT priority, COUNT(*) as count
                FROM it_tickets
                GROUP BY priority
            """)
            by_priority = {row[0]: row[1] for row in cur.fetchall()}
            
            # group by status
            cur.execute("""
                SELECT status, COUNT(*) as count
                FROM it_tickets
                GROUP BY status
            """)
            by_status = {row[0]: row[1] for row in cur.fetchall()}
            
            # return everything as a dictionary 
            return {
                'total_tickets': total,
                'open_tickets': open_count,
                'by_priority': by_priority,
                'by_status': by_status
            }
        
        except sqlite3.Error as err:
            print(f"[TicketModel] Error getting analytics: {err}")
            return {
                'total_tickets': 0,
                'open_tickets': 0,
                'by_priority': {},
                'by_status': {}
            }
        
        finally:
            conn.close()
    
    def get_resolution_stats(self) -> Dict[str, Any]:
        """Get statistics about ticket resolution"""
        conn = connect_database()
        try:
            cur = conn.cursor()
            
            # count resolved tickets
            cur.execute("SELECT COUNT(*) FROM it_tickets WHERE status = 'Resolved'")
            resolved = cur.fetchone()[0]
            
            # count tickets with assigned staff
            cur.execute("""
                SELECT COUNT(*) FROM it_tickets 
                WHERE assigned_to IS NOT NULL AND assigned_to != ''
            """)
            assigned = cur.fetchone()[0]
            
            # average resolution time (using resolution_time_hours if available, convert to days)
            cur.execute("""
                SELECT AVG(resolution_time_hours / 24.0) as avg_days
                FROM it_tickets
                WHERE resolution_time_hours IS NOT NULL AND resolution_time_hours > 0
            """)
            row = cur.fetchone()
            avg_resolution_days = row[0] if row and row[0] else 0
            
            return {
                'resolved_count': resolved,
                'assigned_count': assigned,
                'avg_resolution_days': round(avg_resolution_days, 2)
            }
        
        except sqlite3.Error as err:
            print(f"[TicketModel] Error getting resolution stats: {err}")
            return {
                'resolved_count': 0,
                'assigned_count': 0,
                'avg_resolution_days': 0
            }
        finally:
            conn.close()
    
    def __str__(self):
        """String representation for user-friendly output"""
        total = self.count()
        return f"TicketModel({total} tickets)"
    
    def __repr__(self):
        """String representation"""
        return f"<TicketModel: {self.count()} tickets>"


# ==================== BACKWARD COMPATIBILITY ====================
# these functions maintain compatibility with old functional-style code

def get_all_ticket_analytics():
    """Legacy function for backward compatibility with old code"""
    model = TicketModel()
    return model.get_analytics()

def get_ticket(ticket_id: int):
    """Legacy function for backward compatibility"""
    model = TicketModel()
    return model.get_by_id(ticket_id)

def create_ticket(**kwargs):
    """Legacy function for backward compatibility"""
    model = TicketModel()
    return model.create(**kwargs)

def update_ticket(ticket_id: int, **kwargs):
    """Legacy function for backward compatibility"""
    model = TicketModel()
    return model.update(ticket_id, **kwargs)

def delete_ticket(ticket_id: int):
    """Legacy function for backward compatibility"""
    model = TicketModel()
    return model.delete(ticket_id)

def get_tickets_by_filters(**filters):
    """Legacy function for backward compatibility"""
    model = TicketModel()
    return model.filter_by(**filters)
