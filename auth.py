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


# REMOVE LATER, SOME CODE CAN BE REUSED
# # Test hashing
# hashed = hash_password(test_password)
# print(f"Original password: {test_password}")
# print(f"Hashed password: {hashed}")
# print(f"Hash length: {len(hashed)} characters")

# # Test verification with correct password
# is_valid = verify_password(test_password, hashed)
# print(f"\nVerification with correct password: {is_valid}")

# # Test verification with incorrect password
# is_invalid = verify_password("WrongPassword", hashed)
# print(f"Verification with incorrect password: {is_invalid}")

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
    try:
        with open(USER_DATA_FILE, "r") as file:
            for line in file:
                stored_username = line.split(",")[0].strip()
                if stored_username == username:
                    return False
    except FileNotFoundError:
       # File doesn't exist yet, so no users to check against
        pass  #  Normal in the beginning, first user being registered


    # Hash password and save
    hashed_password = hash_password(password)
    
    with open(USER_DATA_FILE, "a") as file:
        file.write(f"{username},{hashed_password}\n")
    
    # Append the new user to the file
    # Format: username,hashed_password
    with open(USER_DATA_FILE, "a") as file:
        file.write(f"{username},{hashed_password}\n")
    
    return True