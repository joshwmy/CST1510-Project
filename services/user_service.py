import bcrypt
import re
from database.db import connect_database
from models.users import get_user_by_username, insert_user, update_user
import sqlite3
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

# Default Settings
# Centralized configuration so the lockout/session policy can be tweaked in one place.
LOCK_THRESHOLD = 3      # number of failed logins before locking the account
LOCK_MINUTES = 15       # how long the account stays locked (in minutes)
SESSION_HOURS = 24      # default session lifetime in hours


# -------------
# Password functions
# --------------
def hash_password(plain_text_password):
    '''
    Hashes a password using bcrypt with automatic salt generation.

    Why bcrypt:
    - It is slow by design, which helps resist brute force attacks.
    - gensalt() embeds the salt and cost factor into the final hash string,
      so we only need to store the hash itself.
    Returns:
        str: the bcrypt hash as a UTF-8 string ready for storage.
    '''
    password_bytes = plain_text_password.encode("utf-8")
    salt = bcrypt.gensalt()          # using a salt when hashing the password
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password.decode("utf-8")


def verify_password(plain_text_password, hashed_password):
    '''
    Verifies a plaintext password against a stored bcrypt hash.

    bcrypt.checkpw will extract the salt and cost from the stored hash and
    perform the comparison correctly. Return True if the password matches.
    '''
    password_bytes = plain_text_password.encode("utf-8")
    hash_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hash_bytes)


# ---------------
# Registration
# ----------------
def register_user(username, password, role="user"):
    '''
    Registers a new user:
    - rejects duplicates
    - hashes password with bcrypt
    - writes to DB via models.users.insert_user

    Returns:
        bool: True on success, False on failure (e.g. username exists or DB error)
    '''
    try:
        # Prevent duplicate usernames early to avoid IntegrityError
        if get_user_by_username(username):
            return False

        hashed_password = hash_password(password)
        insert_user(username, hashed_password, role)
        return True
    except sqlite3.Error as e:
        # Surface DB error to logs; caller can handle the False return.
        print(f"Database error during registration: {e}")
        return False


# --------------
# Session management
# -------------------
def create_session(username: str, hours: int = SESSION_HOURS) -> str:
    """
    Create a session token for the given username and store it in the sessions table.

    Implementation notes:
    - Uses secrets.token_urlsafe for URL-safe tokens usable in cookies/headers.
    - Stores ISO timestamps so comparisons are straightforward with datetime.fromisoformat.
    """
    token = secrets.token_urlsafe(32)  # this ensures a strong random token for the sessions
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
    Look up a session by token and return its row as a dict, or None if not found/expired.

    Behavior:
    - If the session is expired we delete it immediately and return None.
    - This keeps the session table compact and prevents reuse of expired tokens.
    """
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM sessions WHERE token = ?", (token,))
        row = cur.fetchone()
        if not row:
            return None

        # Support both named-row and index access for safety
        expires_at = row["expires_at"] if "expires_at" in row.keys() else row[4]
        if expires_at:
            exp_time = datetime.fromisoformat(expires_at)
            if exp_time < datetime.now():
                # cleanup expired session happens here
                cur.execute("DELETE FROM sessions WHERE token = ?", (token,))
                conn.commit()
                return None

        # Return a dict for easier use by callers
        return dict(row)
    finally:
        conn.close()


def invalidate_session(token: str) -> None:
    """Delete a session token (used for logout)."""
    conn = connect_database()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


def session_user_role(token: str) -> str | None:
    """
    Helper that resolves a token to the user's role.
    Returns None if token invalid or user missing.
    Useful for quick permission checks in the UI/backend.
    """
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
    """Return True if the session token belongs to a user with any role in allowed_roles."""
    role = session_user_role(token)
    return role in allowed_roles if role else False


# --------------------
# Account lock 
# -------------------
def is_account_locked(username: str) -> bool:
    """
    Check if an account is currently locked.

    The locking scheme uses a timestamp (locked_until). This avoids boolean flags
    and lets us expire locks naturally without sweeper jobs.
    """
    user = get_user_by_username(username)
    if not user:
        return False

    # Handle both dict-like rows and tuple rows for compatibility with different model implementations
    locked_until = user.get("locked_until") if isinstance(user, dict) else user[5]
    
    if not locked_until:
        return False

    lock_time = datetime.fromisoformat(locked_until)
    if datetime.now() < lock_time:
        return True
    else:
        # lock expired: clear counters so next login attempts start fresh
        update_user(username, failed_attempts=0, locked_until=None)
        return False


def record_failed_attempt(username: str) -> None:
    """
    Increment failed_attempts and lock the account if threshold reached.

    Notes:
    - We store the counter in the users table to survive restarts.
    - If the threshold is met we set locked_until to a future timestamp.
    """
    user = get_user_by_username(username)
    if not user:
        return

    failed = user.get("failed_attempts") if isinstance(user, dict) else user[4]
    new_attempts = (failed or 0) + 1

    if new_attempts >= LOCK_THRESHOLD:
        lock_until = (datetime.now() + timedelta(minutes=LOCK_MINUTES)).isoformat()
        update_user(username, failed_attempts=new_attempts, locked_until=lock_until)
    else:
        update_user(username, failed_attempts=new_attempts)


def clear_lock(username: str) -> None:
    """Reset failed_attempts and clear locked_until after successful login or lock expiry."""
    # Set locked_until to empty string to match some existing code paths expecting falsy value.
    update_user(username, failed_attempts=0, locked_until="")


# --------------
# Login
# ------------------
def user_exists(username):
    """
    Convenience wrapper to check user existence. Used in UIs or validation logic.
    """
    try:
        return get_user_by_username(username) is not None
    except sqlite3.Error as e:
        print(f"Database error checking user: {e}")
        return False


def login_user(username, password):
    '''
    Authenticate a user and return a simple status tuple:
        - status: "success", "wrong_password", "locked", or "user_not_found"
        - role: the user's role when successful, else None
        - token: session token when successful, else None

    Flow:
    1. Lookup user.
    2. If locked and still within lock window, return "locked".
    3. Verify password. On success create session and clear lock.
    4. On failure increment failed_attempts and possibly lock the user.
    '''
    try:
        user = get_user_by_username(username)
        
        if not user:
            return "user_not_found", None, None
        
        # Check lock before attempting verification to avoid revealing timing differences
        locked_until = user.get("locked_until") if isinstance(user, dict) else user[5]
        if locked_until:
            lock_time = datetime.fromisoformat(locked_until)
            if datetime.now() < lock_time:
                return "locked", None, None
            else:
                # expired lock = clear and reload user state
                clear_lock(username)
                user = get_user_by_username(username)

        # Extract hash and role in a way that works for both dict and tuple row types
        stored_hash = user.get("password_hash") if isinstance(user, dict) else user[2]
        stored_role = user.get("role") if isinstance(user, dict) else user[3]
        
        if verify_password(password, stored_hash):
            # Successful login: reset lock counters and create a session token
            clear_lock(username)
            token = create_session(username)
            return "success", stored_role, token
        else:
            # Wrong password: increment counter and possibly lock
            record_failed_attempt(username)
            return "wrong_password", None, None
            
    except sqlite3.Error as e:
        # In case of DB errors, do not leak details to caller; return user_not_found to keep UX simple.
        print(f"Database error during login: {e}")
        return "user_not_found", None, None


# ------------------
# Migration to SQL (not needed anymore, but keeping code to show)
# --------------------
def migrate_users_from_file(conn, filepath="DATA/users.txt"):
    """
    Migrate users from users.txt to the database.

    Kept for completeness and to help move legacy data during development.
    The function:
    - reads comma separated lines (username,hash,role optional)
    - inserts users only if they do not already exist
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
                    # Protect against duplicates during migration
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
    Enforce a small, safe username policy:
    - non-empty, length 3..20
    - letters, numbers, underscores only
    Returning a tuple (ok, message) is convenient for UI feedback.
    '''
    if not username:
        return False, "Username cannot be empty."
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters long."
    
    if len(username) > 20:
        return False, "Username must be no more than 20 characters long."

    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username may only contain letters, numbers, and underscores (no spaces or symbols)."

    return True, ""


def validate_password(password):
    '''
    Enforce a reasonably strong password policy:
    - 8..50 characters
    - at least one uppercase, one digit, one special char
    Use regex for concise checks and predictable results.
    '''
    if not password:
        return False, "Password cannot be empty"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 50:
        return False, "Password must be no more than 50 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*()\-_=+\[\]{}|;:,.<>?]', password):
        return False, "Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)"
    
    return True, ""


def check_password_strength(password):
    '''
    A small scoring helper to provide UX feedback (Weak / Medium / Strong).
    This does not replace the strict validate_password enforcement but helps users choose better passwords.
    '''
    score = 0

    # length contributes up to 2 points
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1

    # character variety; using regex to make things more dynamic
    if re.search(r'[a-z]', password):
        score += 1
    if re.search(r'[A-Z]', password):
        score += 1
    if re.search(r'\d', password):
        score += 1
    if re.search(r'[!@#$%^&*()\-_=+\[\]{}|;:,.<>?]', password):
        score += 1

    # convert numeric score into human label
    if score <= 2:
        return "Weak"
    elif score <= 4:
        return "Medium"
    else:
        return "Strong"


# ------------------
# Permission Checking (RBAC)
# ------------------

def check_permission(user_role, domain, action):
    """
    Centralized RBAC check.

    Policy summary:
      - admin: full access
      - user: view-only across the app
      - domain-specific admin roles: full access within their domain
      - domain admins may view other domains but not modify them
    Keep permission logic here so it is easy to reason about and change.
    """
    if user_role == "admin":
        return True
    
    if user_role == "user":
        # regular users can only view
        if action == "view":
            return True
        else:
            return False
    
    # domain-level admin shortcuts for maintainability
    if domain == "Datasets" and user_role == "datasets_admin":
        return True
    if domain == "Cybersecurity" and user_role == "cybersecurity_admin":
        return True
    if domain == "IT Tickets" and user_role == "it_admin":
        return True

    # domain admins are allowed to view other domains
    if action == "view" and user_role in ["datasets_admin", "cybersecurity_admin", "it_admin"]:
        return True

    # default deny: if a role or domain doesn't match our rules, block access
    return False


def can_create(user_role, domain):
    """Convenience wrapper for create checks."""
    return check_permission(user_role, domain, "create")


def can_edit(user_role, domain):
    """Convenience wrapper for edit checks."""
    return check_permission(user_role, domain, "edit")


def can_delete(user_role, domain):
    """Convenience wrapper for delete checks."""
    return check_permission(user_role, domain, "delete")


def can_view(user_role, domain):
    """Convenience wrapper for view checks."""
    return check_permission(user_role, domain, "view")
