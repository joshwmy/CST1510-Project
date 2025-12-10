# CST1510 — Multi-Domain Intelligence Platform

**Student Name:** Joshua Wang  
**Student ID:** M01083838

## Overview
This project implements a unified web-based intelligence platform designed for three operational domains:

1. **Cybersecurity Analysis** - Track and analyze security incidents
2. **IT Ticket Management** - Manage support tickets and track resolution times
3. **Data Science & Dataset Exploration** - Upload, analyze, and manage datasets

The platform provides secure authentication, role-based access control, domain-specific tooling, AI-powered insights, and an integrated Streamlit interface for analysts, administrators, and data scientists.

---

##  Key Features

### Authentication & Security
- ✅ Bcrypt password hashing
- ✅ Failed login tracking with automatic lockout (3 attempts)
- ✅ Session-based authentication with expiration
- ✅ Role-based access control (RBAC)
- ✅ Admin panel for user management

### Cybersecurity Module
- 🔒 Load and explore security incidents
- 🔍 Filter by severity, status, and category
- 📊 Analytics dashboards with charts
- 🤖 AI-powered incident analysis

### IT Ticketing Module
- 🎫 Create and track support tickets
- 📈 Priority and status management
- ⏱️ Resolution time tracking
- 🤖 AI-powered troubleshooting suggestions

### Dataset Intelligence Module
- 📁 CSV upload and management
- 📊 Statistical summaries and analytics
- 🔎 Dataset exploration tools
- 🤖 AI-powered data insights

---

## 📁 Project Structure
```
CST1510 CW2/
│
├── .streamlit/
│   ├── config.toml          # Streamlit UI configuration
│   └── secrets.toml         # API keys (DO NOT COMMIT!)
│
├── DATA/
│   ├── cyber_incidents.csv  # Sample cybersecurity data
│   ├── datasets_metadata.csv
│   ├── it_tickets.csv       # Sample IT tickets
│   ├── users.txt            # User credentials (DO NOT COMMIT!)
│   └── intelligence_platform.db  # SQLite database
│
├── database/
│   ├── db.py               # Database connection management
│   └── schema.py           # Database schema definitions
│
├── models/
│   ├── csv_loader.py       # CSV import utilities
│   ├── datasets.py         # Dataset CRUD operations
│   ├── incidents.py        # Incident management
│   ├── tickets.py          # Ticket management
│   └── users.py            # User data operations
│
├── services/
│   ├── ai_services.py      # AI insights using Gemini API
│   └── user_service.py     # Authentication & authorization
│
├── views/
│   ├── admin_view.py       # Admin panel
│   ├── cybersecurity_view.py
│   ├── datasets_view.py
│   ├── tickets_view.py
│   └── forms.py            # Reusable form components
│
├── docs/
│   └── README.md           # This file
│
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
└── .gitignore             # Git ignore rules
```

---

## 🚀 Installation & Setup

### Prerequisites
- **Python 3.10 or higher**
- **pip** (Python package manager)
- **Git** (for version control)
- **Google Gemini API key** (for AI features) - Get one at [Google AI Studio](https://makersuite.google.com/app/apikey)

---

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/intelligence-platform.git
cd intelligence-platform
```

---

### Step 2: Create Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux / WSL:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### Step 3: Install Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install all required packages
pip install -r requirements.txt
```

---

### Step 4: Configure Environment

#### Option A: Using `.env` file (Recommended)

1. Create a `.env` file in the project root:
```bash
# .env
GEMINI_API_KEY=your_actual_api_key_here
DATABASE_PATH=DATA/intelligence_platform.db
```

2. Never commit this file! It should be in `.gitignore`.

#### Option B: Using Streamlit Secrets

1. Create `.streamlit/secrets.toml`:
```toml
GEMINI_API_KEY = "your_actual_api_key_here"
```

2. Add this to `.gitignore` to keep it secure.

---

### Step 5: Initialize Database

The database will be created automatically on first run, but you can initialize it manually:

```bash
python -c "from database.schema import init_schema; init_schema()"
```

To load sample data:
```bash
python -c "from models.csv_loader import load_all_csv_data; load_all_csv_data()"
```

---

### Step 6: Run the Application

```bash
streamlit run main.py
```

The application will automatically open in your browser at:
```
http://localhost:8501
```

If it doesn't open automatically, manually navigate to the URL shown in the terminal.

---

## 👤 Default Login Credentials

### Admin Account
- **Username:** `admin`
- **Password:** (Use the registration form to create your admin account)

### For Testing
You can create test accounts through the registration page.

**⚠️ IMPORTANT:** Change default credentials immediately in production!

---

## 🔧 Configuration

### Streamlit UI Customization

Edit `.streamlit/config.toml` to customize colors and appearance:

```toml
[theme]
primaryColor = "#0B69A3"        # Accent color
backgroundColor = "#FFFFFF"      # Background
secondaryBackgroundColor = "#F4F6F8"  # Sidebar
textColor = "#0E1B2B"           # Text color
font = "sans serif"
```

### Database Configuration

The default SQLite database is stored at `DATA/intelligence_platform.db`.

To use a different location:
```python
# In database/db.py
DB_PATH = Path("your/custom/path/database.db")
```

---

## 🎯 Usage Guide

### Navigating the Platform

1. **Login/Register** - Start at the home page
2. **Select Domain** - Use the sidebar to switch between:
   - Datasets
   - Cybersecurity
   - IT Tickets
3. **Admin Panel** - Available only to admin users

### User Roles

| Role | Permissions |
|------|-------------|
| **user** | View-only access to all domains |
| **admin** | Full access to everything + user management |
| **datasets_admin** | Full access to datasets, view-only for others |
| **cybersecurity_admin** | Full access to cybersecurity, view-only for others |
| **it_admin** | Full access to IT tickets, view-only for others |

### Uploading CSV Data

Each domain accepts CSV uploads:

**Cybersecurity:**
```csv
incident_id,timestamp,severity,category,status,description
1,2024-01-01 10:00:00,High,Phishing,Open,Phishing attempt detected
```

**IT Tickets:**
```csv
ticket_id,priority,status,description,assigned_to,created_at
T-001,High,Open,Server down,IT_Support_A,2024-01-01
```

**Datasets:**
- Any CSV file will be accepted
- Metadata is automatically extracted

### AI Insights

To use AI-powered analysis:
1. Navigate to any domain dashboard
2. Select an item (incident/ticket/dataset)
3. Click "🧠 Generate AI Insights"
4. View the AI-generated analysis

---

## 🔒 Security Best Practices

### For Development

1. ✅ Never commit `.env` or `secrets.toml`
2. ✅ Never commit database files
3. ✅ Use `.gitignore` properly
4. ✅ Keep API keys secure
5. ✅ Change default passwords

### For Production

1. ⚠️ Use HTTPS (SSL/TLS)
2. ⚠️ Use a production database (PostgreSQL/MySQL)
3. ⚠️ Set up proper logging and monitoring
4. ⚠️ Enable rate limiting
5. ⚠️ Regular security audits
6. ⚠️ Use environment variables
7. ⚠️ Implement CSRF protection

---

## 🐛 Troubleshooting

### "Module not found" errors
```bash
# Make sure virtual environment is activated
# Then reinstall dependencies
pip install -r requirements.txt
```

### Database locked errors
```bash
# Close any other processes accessing the database
# Delete DATA/intelligence_platform.db and restart
```

### Streamlit not opening
```bash
# Manually navigate to the URL shown in terminal
# Usually: http://localhost:8501
```

### Account locked
- Wait 15 minutes, or
- Use admin panel to unlock the account

### API key errors
```bash
# Verify your .env or secrets.toml file
# Ensure GEMINI_API_KEY is set correctly
```

---

## 🧪 Testing

### Run Manual Tests
```bash
# Test database setup
python test.py

# Test individual modules
python -m models.users
python -m models.incidents
python -m models.tickets
python -m models.datasets
```

### Create Test Data
```bash
python -c "from models.csv_loader import load_all_csv_data; load_all_csv_data()"
```

---

## 📊 Database Management

### Backup Database
```bash
# Create backup
cp DATA/intelligence_platform.db DATA/backup_$(date +%Y%m%d).db
```

### Reset Database
```bash
# Delete existing database
rm DATA/intelligence_platform.db

# Reinitialize
python -c "from database.schema import init_schema; init_schema()"

# Load sample data
python -c "from models.csv_loader import load_all_csv_data; load_all_csv_data()"
```

### View Database
```bash
# Install sqlite3 if needed
sqlite3 DATA/intelligence_platform.db

# Run queries
.tables
SELECT * FROM users;
.quit
```

---

## 📦 Dependencies

Core dependencies (see `requirements.txt` for full list):
- `streamlit` - Web application framework
- `pandas` - Data manipulation
- `numpy` - Numerical computing
- `bcrypt` - Password hashing
- `plotly` - Interactive charts
- `google-generativeai` - AI insights
- `python-dotenv` - Environment variable management

---

## 🤝 Contributing

This is a student project for CST1510. For improvements:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📝 Development Notes

### Adding New Features

1. **New Domain**: Add module in `models/`, view in `views/`, update `main.py`
2. **New Role**: Update `user_service.py` RBAC functions
3. **New Database Table**: Update `schema.py`, create model in `models/`

### Code Style
- Follow PEP 8
- Use type hints where possible
- Add docstrings to functions
- Keep functions small and focused

---

## 🎓 Academic Information

**Course:** CST1510 - Programming for Data Communication and Networks  
**Institution:** Middlesex University Mauritius
**Semester:** Year 1, Semester 1 
**Student:** Joshua Wang (M01083838)

---

## 📄 License

This project is for educational purposes as part of CST1510 coursework.

---

## 🆘 Support

For issues or questions:
- Check the troubleshooting section above
- Review code comments and docstrings

---

## 🙏 Acknowledgments

- Streamlit for the web framework
- Google for Gemini AI API
- Course instructors and teaching assistants
- Open source community

---

## 📅 Version History

- **v1.0** (2025-12) - Initial release
  - Multi-domain architecture
  - Authentication & RBAC
  - AI-powered insights
  - CSV upload functionality
  - Admin panel

---

**Last Updated:** December 2025