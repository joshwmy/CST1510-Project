"""
Fixed users.py module - ensures locked_until can be set to NULL
"""
import sqlite3
from typing import Optional, Dict, Any
from database.db import connect_database

# ---------------------- CREATE ----------------------

def insert_user(username: str, password_hash: str, role: str = "user") -> bool:
    """
    Insert a new user into the database.
    
    Args:
        username: The username
        password_hash: The hashed password
        role: User role (default: "user")
    
    Returns:
        bool: True if successful, False otherwise
    """
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (username, password_hash, role, failed_attempts, locked_until)
            VALUES (?, ?, ?, 0, NULL)
            """,
            (username, password_hash, role)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Username already exists
        conn.rollback()
        return False
    except sqlite3.Error as e:
        print(f"Error inserting user: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# ---------------------- READ ----------------------

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a user by username.
    
    Args:
        username: The username to search for
    
    Returns:
        Dict with user data or None if not found
    """
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Error fetching user {username}: {e}")
        return None
    finally:
        conn.close()


def get_all_users() -> list:
    """
    Get all users from the database.
    
    Returns:
        List of user dictionaries
    """
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users ORDER BY created_at DESC")
        return [dict(row) for row in cur.fetchall()]
    except sqlite3.Error as e:
        print(f"Error fetching all users: {e}")
        return []
    finally:
        conn.close()


# ---------------------- UPDATE ----------------------

def update_user(
    username: str,
    password_hash: Optional[str] = None,
    role: Optional[str] = None,
    failed_attempts: Optional[int] = None,
    locked_until: Optional[str] = None
) -> bool:
    """
    Update user fields. Pass None to keep existing value.
    To explicitly set locked_until to NULL, pass empty string "".
    
    Args:
        username: The username to update
        password_hash: New password hash (or None to keep)
        role: New role (or None to keep)
        failed_attempts: New failed attempts count (or None to keep)
        locked_until: New lock timestamp (None to keep, "" to clear)
    
    Returns:
        bool: True if successful, False otherwise
    """
    conn = connect_database()
    try:
        cur = conn.cursor()
        
        # Build dynamic UPDATE query
        updates = []
        params = []
        
        if password_hash is not None:
            updates.append("password_hash = ?")
            params.append(password_hash)
        
        if role is not None:
            updates.append("role = ?")
            params.append(role)
        
        if failed_attempts is not None:
            updates.append("failed_attempts = ?")
            params.append(failed_attempts)
        
        # Special handling for locked_until to allow NULL
        if locked_until is not None:
            if locked_until == "":
                # Empty string means clear the lock (set to NULL)
                updates.append("locked_until = NULL")
            else:
                updates.append("locked_until = ?")
                params.append(locked_until)
        
        if not updates:
            # Nothing to update
            return False
        
        # Add username to params
        params.append(username)
        
        query = f"UPDATE users SET {', '.join(updates)} WHERE username = ?"
        cur.execute(query, params)
        conn.commit()
        
        return cur.rowcount > 0
        
    except sqlite3.Error as e:
        print(f"Error updating user {username}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# ---------------------- DELETE ----------------------

def delete_user(username: str) -> bool:
    """
    Delete a user from the database.
    
    Args:
        username: The username to delete
    
    Returns:
        bool: True if successful, False otherwise
    """
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        return cur.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error deleting user {username}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()