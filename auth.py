import bcrypt
import os
USER_DATA_FILE = "users.txt"

def hash_password(plain_text_password):
    '''
    Hashes a password using bcrypt with automatic salt generation.

    Args:
        plain_text_password (str): The plaintext password to hash

    Returns:
        str: The hashed password as a UTF-8 string
    '''
    # Encode the password to bytes (bcrypt requires byte strings)
    password_bytes = plain_text_password.encode("utf-8")
    
    # Generate a salt using bcrypt.gensalt()
    salt = bcrypt.gensalt()
    
    # Hash the password using bcrypt.hashpw()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    
    # Decode the hash back to a string to store in a text file
    return hashed_password.decode("utf-8")


def verify_password(plain_text_password, hashed_password):
    '''
    Verifies a plaintext password against a stored bcrypt hash.
    This function extracts the salt from the hash and compares

    Args:
        plain_text_password (str): The password to verify
        hashed_password (str): The stored hash to check

    Returns:
        bool: True if the password matches, otherwise False
    '''
# Encode both the plaintext password and the stored hash to byte
    password_bytes = plain_text_password.encode("utf-8")
    hash_bytes = hashed_password.encode("utf-8")

# Use bcrypt.checkpw() to verify the password
    return bcrypt.checkpw(password_bytes, hash_bytes)


def register_user(username, password):
    '''
    Registers a new user by hashing their password and storing credentials.

    Args:
        username (str): The username for the new account
        password (str): The plaintext password to hash and store

    Returns:
        bool: True if registration successful, False if username already exists
    '''
    # Check if the username already exists
    if user_exists(username):
        return False

    # Hash the password and save
    hashed_password = hash_password(password)
    
    with open(USER_DATA_FILE, "a") as file:
        file.write(f"{username},{hashed_password}\n")
    
    return True


def user_exists(username):
    """
    Checks if a username already exists in the user database.

    Args:
        username (str): The username to check

    Returns:
        bool: True if the user exists, False otherwise
    """
    # Handle the case where the file doesn't exist yet
    try:
        # Read the file and check each line for the username
        with open(USER_DATA_FILE, "r") as file:
            for line in file:
                stored_username = line.split(",")[0].strip()
                if stored_username == username:
                    return True
    except FileNotFoundError:
        # File doesn't exist yet, so no users exist
        return False
    
    return False


def login_user(username, password):
    '''
    Authenticates a user by verifying their username and password.

    Args:
        username (str): The username to authenticate
        password (str): The plaintext password to verify

    Returns:
        bool: True if authentication successful, False otherwise
    '''
    try:
        with open(USER_DATA_FILE, "r") as file:
            for line in file:
                parts = line.strip().split(",")
                if len(parts) == 2:
                    stored_username, stored_hash = parts
                    
                    if stored_username == username:
                        # Verify the password using bcrypt function
                        return verify_password(password, stored_hash)
    
    except FileNotFoundError:
        # No users registered yet
        return False
    
    # Username was not found
    return False


