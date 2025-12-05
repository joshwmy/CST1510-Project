# CST1510 — Multi-Domain Intelligence Platform

**Student Name:** Joshua Wang  
**Student ID:** M01083838

## Overview
This project implements a unified web-based intelligence platform designed for three operational domains:

1. Cybersecurity analysis  
2. IT ticket management  
3. Data science and dataset exploration  

The platform provides secure authentication, role-based access, domain-specific tooling, and an integrated Streamlit interface that allows Analysts, Administrators, and Data Scientists to work within a single cohesive environment.

The system includes:
- Secure login, session tokens, bcrypt-based authentication, and account lockout handling.
- An Admin Panel for viewing users, unlocking accounts, and managing roles.
- Dashboards for cyber incidents, IT tickets, and datasets.
- CSV ingestion tools, dataset summarisation, and data filtering utilities.
- A structured backend with clear separation of concerns in modules such as `users.py`, `user_service.py`, `tickets.py`, `incidents.py`, and `datasets.py`.

---

## Features

### Authentication & Security
- Bcrypt password hashing  
- Failed login tracking  
- Automatic temporary lockout  
- Session-based login system  
- Admin controls for unlocking accounts  

### Cybersecurity Module
- Load and explore cybersecurity incidents  
- Filter, search, and analyse incident data  
- Summaries and domain insights  

### IT Ticketing Module
- Ticket creation and lookup  
- Filtering tools for status, priority, and category  
- Administrative ticket overviews  

### Dataset Intelligence Module
- Upload and load CSV datasets  
- View statistics and summaries  
- Perform lightweight data analysis  

---

## Project Structure
```text
CST1510 CW2/
│
├── DATA/
│   ├── cyber_incidents.csv
│   ├── datasets_metadata.csv
│   ├── intelligence_platform.db
│   ├── it_tickets.csv
│   └── users.txt
│
├── database/
│   ├── db.py
│   └── schema.py
│
├── docs/
│   └── README.md
│
├── models/
│   ├── csv_loader.py
│   ├── datasets.py
│   ├── incidents.py
│   ├── tickets.py
│   └── users.py
│
├── pages/                      # Streamlit pages ; REMINDER: CHANGE THIS LATER
│
├── services/
│   └── user_service.py
│
├── main.py
├── requirements.txt
└── test.py
```

## How to Run the Project

This project runs as a local Streamlit web application.
Follow the steps below to install dependencies, set up the environment, and launch the platform.

### 1. Requirements

You need:
- Python 3.10 or higher
- pip (Python package manager)
- Ability to run commands in Terminal / PowerShell

No external database server is required.
All data is stored locally inside the DATA/ folder (CSV files + SQLite DB).

### 2. Step-by-Step Installation Instructions
Step 1 — Navigate to the project folder

Open a terminal in the root directory:
CST1510 CW2/


This folder contains:
main.py
requirements.txt
models/
services/
database/
pages/
DATA/

Step 2 — Create a virtual environment

This keeps dependencies isolated.

Windows (PowerShell):

python -m venv .venv
.\.venv\Scripts\Activate.ps1


macOS / Linux / WSL:

python3 -m venv .venv
source .venv/bin/activate

Step 3 — Install the required libraries

With the environment activated:

pip install --upgrade pip
pip install -r requirements.txt


This installs:
-Streamlit
-Pandas, NumPy
-bcrypt
-dateutil
-and any other required libraries

### 3. Run the Application

Start the platform by running:

streamlit run main.py


Streamlit will automatically open the web interface in your browser at:

http://localhost:8501


If it does not auto-open, you can manually visit the URL.

### 4. Logging In

You may log in using:
-A user from DATA/users.txt, or
-A newly registered user (if registration is enabled).

The platform includes:
-Account lockout protection
-Role-based access control
-Admin features such as unlocking users

### 5. Navigating the Application

Once logged in, use the sidebar to navigate between modules:
-Dashboard / Home
-Cyber Incidents Intelligence
-IT Ticket Management
-Dataset Upload & Exploration
-(Admin Only) User List, Role Management, Unlock Users

### 6. Troubleshooting
Sidebar not updating after login:

Close the browser tab and reopen, or refresh.
The system uses st.session_state to track login status.

Account stays locked after correct login:

Try unlocking through the Admin User List.
Your backend includes lockout logic that resets failed_attempts and locked_until.

Module import errors:

Ensure you are running Streamlit from the project root, not from inside a subfolder.

### 7. Shutting Down

To stop the app:
Press CTRL + C in the terminal.

To deactivate the environment:
[bash] deactivate

