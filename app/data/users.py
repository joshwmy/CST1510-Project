'''
User CRUD Operations; this handles all functions for managing users.
'''

from typing import Optional
from app.data.db import connect_database

def get_user_by_username(username):
    """Retrieve user by username."""
    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    )
    user = cursor.fetchone()
    conn.close()
    return user

def insert_user(username, password_hash, role='user'):
    """Insert new user."""
    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, password_hash, role)
    )
    conn.commit()  # Added missing commit!
    conn.close()

def update_user(username: str, failed_attempts: Optional[int] = None, locked_until: Optional[str] = None) -> None:
    """
    Update user fields. Only updates columns provided (non-None).
    `locked_until` should be an ISO datetime string or None.
    """
    conn = connect_database()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if failed_attempts is not None:
        updates.append("failed_attempts = ?")
        params.append(failed_attempts)
    
    if locked_until is not None:
        updates.append("locked_until = ?")
        params.append(locked_until)
    
    if updates:
        params.append(username)
        cursor.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE username = ?",
            params
        )
        conn.commit()
    conn.close()