import bcrypt
# USER_DATA_FILE = "users.txt"  - migration completed
from database.db import connect_database
from models.users import get_user_by_username, insert_user, update_user
import sqlite3
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

# Default Settings
LOCK_THRESHOLD = 3      # it will lock after 3 failed attempts
LOCK_MINUTES = 15
SESSION_HOURS = 24     # Session will last for 24 hours

# -------------
# Password functions
# --------------
def hash_password(plain_text_password):
    '''
    Hashes a password using bcrypt with automatic salt generation.
     
     Args:
        plain_text_password (str): The plaintext password to hash

    Returns:
        str: The hashed password as a UTF-8 string
    '''
    # Encoding the password to bytes (as bcrypt requires byte strings)
    password_bytes = plain_text_password.encode("utf-8")
    
    # Generation of salt using bcrypt.gensalt()
    salt = bcrypt.gensalt()
    
    # Password hash using bcrypt.hashpw()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    
    # Decode the hash back to a string to store in a text file
    return hashed_password.decode("utf-8")

def verify_password(plain_text_password, hashed_password):
    '''
    Verifies a plaintext password against a stored bcrypt hash.
    This function extracts the salt from the hash and compares it.

    Args:
        plain_text_password (str): The password to verify
        hashed_password (str): The stored hash to check

    Returns:
        bool: True if the password matches, otherwise False
    '''
    # Encode both the plaintext password and the stored hash to byte
    password_bytes = plain_text_password.encode("utf-8")
    hash_bytes = hashed_password.encode("utf-8")

    # bcrypt.checkpw() to verify the password (if they match)
    return bcrypt.checkpw(password_bytes, hash_bytes)

# ---------------
# Registration
# ----------------
def register_user(username, password, role="user"):
    '''
    Registers a new user by hashing their password and storing credentials.

    Args:
        username (str): The username for the new account
        password (str): The plaintext password to hash and store
        role (str): The user's role on platform; different permissions allowed for each role

    Returns:
        bool: True if registration successful, False if username already exists
    '''
    try:
        # Check if username exists using the function from users.py
        if get_user_by_username(username):
            return False
        
        # Hash password and insert new user into db using function from users.py
        hashed_password = hash_password(password)
        insert_user(username, hashed_password, role)
        return True
    except sqlite3.Error as e:
        print(f"Database error during registration: {e}")
        return False

# --------------
# Session management
# -------------------
def create_session(username: str, hours: int = SESSION_HOURS) -> str:
    """
    Creates a session token for user.
    Returns the token string.
    """
    token = secrets.token_urlsafe(32)
    created_at = datetime.now().isoformat()
    expires_at = (datetime.now() + timedelta(hours=hours)).isoformat()

    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sessions (username, token, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (username, token, created_at, expires_at),
        )
        conn.commit()
        return token
    finally:
        conn.close()


def get_session(token: str) -> Optional[dict]:
    """
    Check if session is valid.
    Returns session data if valid, None if expired or missing.
    """
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM sessions WHERE token = ?", (token,))
        row = cur.fetchone()
        if not row:
            return None

        # Check if expired
        expires_at = row["expires_at"] if "expires_at" in row.keys() else row[4]
        if expires_at:
            exp_time = datetime.fromisoformat(expires_at)
            if exp_time < datetime.now():
                # Delete expired session
                cur.execute("DELETE FROM sessions WHERE token = ?", (token,))
                conn.commit()
                return None

        return dict(row)
    finally:
        conn.close()


def invalidate_session(token: str) -> None:
    """Remove a session (logout)"""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()

def session_user_role(token: str) -> str | None:
    if not token:
        return None
    sess = get_session(token)
    if not sess:
        return None
    username = sess.get("username")
    if not username:
        return None
    user = get_user_by_username(username)
    if not user:
        return None
    return user.get("role") or None

def require_role(token: str, allowed_roles: list[str]) -> bool:
    """Return True if session token belongs to user with role in allowed_roles."""
    role = session_user_role(token)
    return role in allowed_roles if role else False

# --------------------
# Account lock 
# -------------------
def is_account_locked(username: str) -> bool:
    """Checks if account is locked; it uses function from users.py"""
    user = get_user_by_username(username)
    if not user:
        return False

    locked_until = user["locked_until"] if "locked_until" in user.keys() else user[5]
    
    if not locked_until:
        return False

    # Check if lock time has passed
    lock_time = datetime.fromisoformat(locked_until)
    if datetime.now() < lock_time:
        return True
    else:
        # Lock expired, clear it
        update_user(username, failed_attempts=0, locked_until=None)
        return False


def record_failed_attempt(username: str) -> None:
    """Record failed attempts"""
    user = get_user_by_username(username)
    if not user:
        return

    failed = user["failed_attempts"] if "failed_attempts" in user.keys() else user[4]
    new_attempts = (failed or 0) + 1

    if new_attempts >= LOCK_THRESHOLD:
        # Lock account
        lock_until = (datetime.now() + timedelta(minutes=LOCK_MINUTES)).isoformat()
        update_user(username, failed_attempts=new_attempts, locked_until=lock_until)
    else:
        update_user(username, failed_attempts=new_attempts)


def clear_lock(username: str) -> None:
    """Reset failed attempts."""
    update_user(username, failed_attempts=0, locked_until=None)

# --------------
# Login
# ------------------

def user_exists(username):
    """
    Checks if a username already exists in the user database.

    Args:
        username (str): The username to check

    Returns:
        bool: True if the user exists, False otherwise
    """
    try:
        return get_user_by_username(username) is not None
    except sqlite3.Error as e:
        print(f"Database error checking user: {e}")
        return False

def login_user(username, password):
    '''
    Authenticates a user by verifying their username and password. If the wrong password is input 3 times, the user will be locked out for 5 minutes
    until next attempt.

    Args:
        username (str): The username to authenticate
        password (str): The plaintext password to verify

    Returns:
       tuple, where:
            - status (str): One of "success", "wrong_password", or "user_not_found".
            - role (str or None): The user's role if authentication succeeds, otherwise `None`.
            - token (str or None): string session token if login worked, otherwise None
    '''
    try:
        # Get user data using function from users.py
        user = get_user_by_username(username)       # connection no1
        
        if not user:
            return "user_not_found", None, None
        
        # Check if the account is locked
        locked_until = user["locked_until"] if "locked_until" in user.keys() else user[5]
        if locked_until:
            lock_time = datetime.fromisoformat(locked_until)
            if datetime.now() < lock_time:
                return "locked", None, None
            else:
                # Lock expired, clear it
                clear_lock(username)

        # Extract password_hash and role from user tuple
        # The tuple structure is: (id, username, password_hash, role)
        stored_hash = user["password_hash"] if "password_hash" in user.keys() else user[2]      # password_hash is at index 2
        stored_role = user["role"] if "role" in user.keys() else user[3]                    # role is at index 3
        
        # Verify the password using bcrypt function
        if verify_password(password, stored_hash):
            # when success; clear lock and create session
            clear_lock(username)  # Connection no 2
            token = create_session(username)  # Connection no3 (sessions table)
            return "success", stored_role, token
        else:
            # when incorrect; record attempt 
            record_failed_attempt(username)  # Connection no2
            return "wrong_password", None, None

            
    except sqlite3.Error as e:
        print(f"Database error during login: {e}")
        return "user_not_found", None, None

# ------------------
# Migration to SQL (not needed anymore, but keeping code to show)
# --------------------
def migrate_users_from_file(conn, filepath="DATA/users.txt"):
    """
    Migrate users from users.txt to the database.
    
    Args:
        conn: Database connection
        filepath: Path to users.txt file
    """ 
    filepath = Path(filepath)
    if not filepath.exists():
        print(f"File not found: {filepath}")
        print("No users to migrate.")
        return

    migrated_count = 0
    with filepath.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if len(parts) >= 2:
                username = parts[0].strip()
                password_hash = parts[1].strip()
                try:
                    # Using the functions from users.py
                    if not get_user_by_username(username):
                        insert_user(username, password_hash, 'user')
                        migrated_count += 1
                except sqlite3.Error as e:
                    print(f"Error migrating user {username}: {e}")

    print(f"Migrated {migrated_count} users from {filepath.name}")

# ------------------
# Validation
# ---------------------
def validate_username(username):
    '''
    Validates username format.

    Args:
        username (str): The username to validate
        
    Returns:
        tuple: A pair (is_valid, error_message) where:
            - is_valid (bool): True if the username is valid, otherwise False.
            - error_message (str): A message explaining why validation failed, or an empty string if valid.
    '''
    if not username:
        return False, "Username cannot be empty."
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters long."
    
    if len(username) > 20:
        return False, "Username must be no more than 20 characters long."

    # Only letters, numbers, underscores allowed
    if not all(char.isalnum() or char == "_" for char in username):
        return False, "Username may only contain letters, numbers, and underscores (no spaces or symbols)."

    return True, ""

def validate_password(password):
    '''
    Validates password strength.

     Args:
        password (str): The password to validate.

    Returns:
        tuple: A pair (is_valid, error_message) where:
            - is_valid (bool): True if password is valid, otherwise False.
            - error_message (str): A message explaining why validation failed, or an empty string if valid.
    '''
    # Checks if password is empty
    if not password:
        return False, "Password cannot be empty"
    
    # Checks minimum length (8+ for security)
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    # Checks maximum length
    if len(password) > 50:
        return False, "Password must be no more than 50 characters long"
    
    # Checks for at least one uppercase letter
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter"
    
    # Checks for at least one number
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one number"
    
    # Checks for at least one special character
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(char in special_chars for char in password):
        return False, "Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)"
    
    
    # All checks passed
    return True, ""

def check_password_strength(password):
    '''
    Evaluates password strength.

   Returns:
        str: "Weak", "Medium", or "Strong"
    '''
    score = 0

    # Length scoring
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1

    # Scoring for varied use of characters
    if any(c.islower() for c in password):
        score += 1
    if any(c.isupper() for c in password):
        score += 1
    if any(c.isdigit() for c in password):
        score += 1
    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        score += 1

    # Convert score into strength rating
    if score <= 2:
        return "Weak"
    elif score <= 4:
        return "Medium"
    else:
        return "Strong"

