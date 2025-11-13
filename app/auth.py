import bcrypt
USER_DATA_FILE = "users.txt"

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
    # Checks if the username already exists
    if user_exists(username):
        return False
    # Hashing the password and save
    hashed_password = hash_password(password)
    
    with open(USER_DATA_FILE, "a") as file:
        file.write(f"{username},{hashed_password},{role}\n")
    
    return True

def user_exists(username):
    """
    Checks if a username already exists in the user database.

    Args:
        username (str): The username to check

    Returns:
        bool: True if the user exists, False otherwise
    """
    # try except used if the file doesn't exist yet
    try:
        # Reads the file and checks each line for the username with for loop
        with open(USER_DATA_FILE, "r") as file:
            for line in file:
                stored_username = line.split(",")[0].strip()
                if stored_username == username:
                    return True
    except FileNotFoundError:  # File doesn't exist yet, so no users exist
        return False
    
    return False    # Handles case where file exists but username doesn't exist.

def login_user(username, password):
    '''
    Authenticates a user by verifying their username and password.

    Args:
        username (str): The username to authenticate
        password (str): The plaintext password to verify

    Returns:
       tuple: A pair (status, role) where:
            - status (str): One of "success", "wrong_password", or "user_not_found".
            - role (str or None): The user's role if authentication succeeds, otherwise `None`.
    '''
    try:
        with open(USER_DATA_FILE, "r") as file:
            for line in file:
                parts = [p.strip() for p in line.strip().split(",")]
                # I implemented a user role option, this allows compatibility of the new and old format
                # Old format has 2 parameters, new format has 3
                if len(parts) == 3:
                    stored_username, stored_hash, stored_role = parts[0], parts[1], parts[2]
                elif len(parts) == 2:   # If user had no role
                    stored_username, stored_hash = parts
                    stored_role = "user"    # Defaulted to role of user
                else:
                    continue
                    
                if stored_username == username:
                    # Verify the password using bcrypt function
                    if verify_password(password, stored_hash):
                        return "success", stored_role
                    else:
                        return "wrong_password", None
    
    except FileNotFoundError:
        # No users registered yet
        return "user_not_found", None
    
    # Username was not found
    return "user_not_found", None

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
    while True:
        display_menu()
        choice = input("\nPlease select an option (1-3): ").strip()
        
        # REGISTRATION BLOCK
        if choice == '1':
            # Registration flow
            print("\n--- USER REGISTRATION ---")
            username = input("Enter a username: ").strip()

            # Validate username
            is_valid, error_msg = validate_username(username)
            if not is_valid:
                print(f"Error: {error_msg}")
                continue

            
            print("\nPassword Requirements:")
            print("- At least 8 characters")
            print("- Must include: uppercase letter, number, and special character")
            password = input("Enter a password: ").strip()

            # Check strength and display feedback
            strength = check_password_strength(password)
            print(f"Password Strength: {strength}")

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
            role = "user"  # default role
            if register_user(username, password, role="user"):
                print(f"Registration successful! User '{username}' with role {role} created. You can now log in.")
            else:
                print(f"Error: Username '{username}' already exists.")
            
        # LOGIN BLOCK
        elif choice == '2':
            # Login flow
            print("\n--- USER LOGIN ---")
            username = input("Enter your username: ").strip()
            password = input("Enter your password: ").strip()

            # Attempt login
            result, role = login_user(username, password)
    
            if result == "success":
                print(f"\nSuccess! Welcome, {username}. You are now logged in.")
                if role == "admin":
                    print(">>> You are logged in as an ADMIN.")
                    # NB: Put admin menu here in the future
                else:
                    print("(In a real application, you would now access the dashboard)")
                input("\nPress Enter to return to main menu...")

            # Conditional statement for when errors occur    
            elif result == "wrong_password":
                print("Error: Invalid password.")
            elif result == "user_not_found":
                print("Error: Username not found.")
            else:
                print("Error: Unexpected login result. Please contact admin")

        # EXIT BLOCK    
        elif choice == '3':
            print("\nThank you for using the authentication system.")
            print("Exiting...")
            break

        else:
            print("\nError: Invalid option. Please select 1, 2, or 3.")

if __name__ == "__main__":
    main()