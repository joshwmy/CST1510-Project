"""
User Management Module
Handles CRUD operations for user accounts with authentication support
"""

import sqlite3
from typing import Optional, Dict, Any
from database.db import connect_database

# ---------------------- CREATE ----------------------

def insert_user(username: str, password_hash: str, role: str = "user") -> bool:
    """
    Insert a new user into the database.
    Password should already be hashed before calling this function.
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
        # username already exists; sqlite will reject duplicate usernames
        conn.rollback()
        return False
    except sqlite3.Error as e:
        print(f"Error inserting user: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()        # always close connection

# ---------------------- READ ----------------------

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a user by username.
    Returns user data as dict or None if not found.
    """
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        return dict(row) if row else None       # convert to dict or return None if not found
    except sqlite3.Error as e:
        print(f"Error fetching user {username}: {e}")
        return None
    finally:
        conn.close()

def get_all_users() -> list:
    """
    Get all users from the database.
    Returns list of user dictionaries sorted by creation date.
    """
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users ORDER BY created_at DESC")       # most recent query is shown
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
    To explicitly set locked_until to NULL (unlock account), pass empty string "".
    """
    conn = connect_database()
    try:
        cur = conn.cursor()
        
        # build dynamic UPDATE query based on what fields are provided
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
        
        # special handling for locked_until to allow NULL (unlock account)
        if locked_until is not None:
            if locked_until == "":
                # empty string means clear the lock by setting to NULL
                updates.append("locked_until = NULL")
            else:
                updates.append("locked_until = ?")
                params.append(locked_until)
        
        if not updates:
            # nothing to update
            return False
        
        params.append(username)     # add username for WHERE clause
        
        query = f"UPDATE users SET {', '.join(updates)} WHERE username = ?"
        cur.execute(query, params)
        conn.commit()
        
        return cur.rowcount > 0     # returns true if something was actually updated
        
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
    This permanently removes the user account.
    """
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        return cur.rowcount > 0     # returns true if something was actually deleted
    except sqlite3.Error as e:
        print(f"Error deleting user {username}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()