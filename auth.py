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
       str: "success" if authentication successful, 
            "wrong_password" if password is incorrect,
            "user_not_found" if username doesn't exist
    '''
    try:
        with open(USER_DATA_FILE, "r") as file:
            for line in file:
                parts = line.strip().split(",")
                if len(parts) == 2:
                    stored_username, stored_hash = parts
                    
                    if stored_username == username:
                        # Verify the password using bcrypt function
                        if verify_password(password, stored_hash):
                            return "success"
                        else:
                            return "wrong_password"
    
    except FileNotFoundError:
        # No users registered yet
        return "user_not_found"
    
    # Username was not found
    return "user_not_found"

def validate_username(username):
    '''
    Validates username format.

    Args:
        username (str): The username to validate
        
    Returns:
        tuple: (bool, str) - (is_valid, error_message)
    '''
    if not username:
        return False, "Username cannot be empty."
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters long."
    
    if len(username) > 20:
        return False, "Username must be no more than 20 characters long."

    # Allow only letters, numbers, underscores
    if not all(char.isalnum() or char == "_" for char in username):
        return False, "Username may only contain letters, numbers, and underscores (no spaces or symbols)."

    return True, ""

def validate_password(password):
    '''
    Validates password strength.

     Args:
        password (str): The password to validate.

    Returns:
        tuple: (bool, str) - (is_valid, error_message)
    '''
# Check if password is empty
    if not password:
        return False, "Password cannot be empty"
    
    # Check minimum length (8+ for security)
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    # Check maximum length
    if len(password) > 20:
        return False, "Password must be no more than 20 characters long"
    
    # Check for at least one uppercase letter
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter"
    
    # Check for at least one number
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one number"
    
    # Check for at least one special character
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(char in special_chars for char in password):
        return False, "Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)"
    
    
    # All checks passed
    return True, ""

def display_menu():
    """
    Displays the main menu options.
    """
    print("\n" + "="*50)
    print(" MULTI-DOMAIN INTELLIGENCE PLATFORM")
    print(" Secure Authentication System")
    print("="*50)
    print("\n[1] Register a new user")
    print("[2] Login")
    print("[3] Exit")
    print("-"*50)

def main():
    """
    Main program loop.
    """
    print("\nWelcome to the Week 7 Authentication System!")

    while True:
        display_menu()
        choice = input("\nPlease select an option (1-3): ").strip()
        
        if choice == '1':
            # Registration flow
            print("\n--- USER REGISTRATION ---")
            username = input("Enter a username: ").strip()

            # Validate username
            is_valid, error_msg = validate_username(username)
            if not is_valid:
                print(f"Error: {error_msg}")
                continue

            password = input("Enter a password: ").strip()
            # Validate password
            is_valid, error_msg = validate_password(password)
            if not is_valid:
                print(f"Error: {error_msg}")
                continue 

            # Confirm password
            password_confirm = input("Confirm password: ").strip()
            if password != password_confirm:
                print("Error: Passwords do not match.")
                continue

            # Register the user
            if register_user(username, password):
                print(f"Registration successful! User '{username}' created. You can now log in.")
            else:
                print(f"Error: Username '{username}' already exists.")
            
        elif choice == '2':
            # Login flow
            print("\n--- USER LOGIN ---")
            username = input("Enter your username: ").strip()
            password = input("Enter your password: ").strip()

            # Attempt login
            result = login_user(username, password)
    
            if result == "success":
                print("\nYou are now logged in.")
                print("(In a real application, you would now access the dashboard)")
            elif result == "wrong_password":
                print("Error: Invalid password.")
            elif result == "user_not_found":
                print("Error: Username not found.")
            
            # Optional: Ask if they want to logout or exit
            input("\nPress Enter to return to main menu...")

        elif choice == '3':
            # Exit
            print("\nThank you for using the authentication system.")
            print("Exiting...")
            break

        else:
            print("\nError: Invalid option. Please select 1, 2, or 3.")


if __name__ == "__main__":
    main()