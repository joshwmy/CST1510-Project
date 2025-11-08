# CST1510-Project
A unified web application built with Python and Streamlit that provides combined tooling for Cybersecurity Analysts, Data Scientists, and IT Administrators. The platform delivers domain-specific insights, analysis workflows, and operational capabilities through a single, integrated interface.


# Week 7: Secure Authentication System
Student Name: Joshua Wang
Student ID: M01083838
Course: CST1510 -CW2 - Multi-Domain Intelligence Platform
## Project Description
A command-line authentication system implementing secure password hashing.
This system allows users to register accounts and log in with thier username and password.
## Features
- Secure password hashing using bcrypt with automatic salt generation
- User registration with duplicate username prevention
- User login with password verification
- Input validation for usernames and passwords
- File-based user data persistence
- Clear separation of authentication logic into functions
## Technical Implementation
- Hashing Algorithm: bcrypt with automatic salting
- Salt Handling: Automatically generated per password (bcrypt.gensalt())
- Data Storage: Plain text file (`users.txt`) with comma-separated values
- Password Security: One-way hashing, no plaintext storage
- Validation: Username: 3–20 chars, letters/numbers/underscores only
Password: 8–20 chars, must include uppercase letter, number, and special character