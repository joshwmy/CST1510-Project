# main.py
"""
Streamlit app (no matplotlib) — uses only native Streamlit charts for data representation.
Integrates user_service for auth/session management and backend modules:
csv_loader, datasets, incidents, tickets, users.
"""

import io
import os
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import time
from typing import Optional

# -------------------------
# Backend imports (adjust path if needed)
# -------------------------
try:
    from app.data import csv_loader as csv_loader_mod
    from app.data import datasets as datasets_mod
    from app.data import incidents as incidents_mod
    from app.data import tickets as tickets_mod
    from app.data import users as users_mod
    from app.services import user_service as user_service_mod
except Exception as e:
    st.error(f"Error importing backend modules: {e}")
    csv_loader_mod = datasets_mod = incidents_mod = tickets_mod = users_mod = user_service_mod = None

# -------------------------
# Page config & session
# -------------------------
st.set_page_config(page_title="Admin Portal", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "session_token" not in st.session_state:
    st.session_state.session_token = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"
if "current_domain" not in st.session_state:
    st.session_state.current_domain = "Datasets"

# -------------------------
# Helpers
# -------------------------
def safe_df(obj) -> pd.DataFrame:
    """Convert backend results to DataFrame safely."""
    try:
        if isinstance(obj, pd.DataFrame):
            return obj
        if isinstance(obj, (list, tuple)):
            return pd.DataFrame(obj)
        if isinstance(obj, dict):
            return pd.DataFrame([obj])
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def small_stat_col_layout(values, labels):
    cols = st.columns(len(values))
    for c, v, l in zip(cols, values, labels):
        c.metric(l, v)

# -------------------------
# CSV Upload Handlers
# -------------------------
def handle_csv_upload(uploaded_file, domain: str, username: str):
    """Process uploaded CSV files for different domains"""
    try:
        # Read the CSV file
        df = pd.read_csv(uploaded_file)
        
        # Process based on domain
        if domain == "Datasets":
            return handle_dataset_upload(df, username, uploaded_file.name)
        elif domain == "Cybersecurity":
            return handle_incident_upload(df, username, uploaded_file.name)
        elif domain == "IT Tickets":
            return handle_ticket_upload(df, username, uploaded_file.name)
        else:
            return False, f"Unknown domain: {domain}"
            
    except Exception as e:
        return False, f"Error reading CSV: {str(e)}"

def handle_dataset_upload(df, username, filename):
    """Create dataset entry from uploaded CSV"""
    try:
        dataset_name = os.path.splitext(filename)[0]  # Use filename as dataset name
        description = f"Uploaded from CSV: {filename}"
        
        created = datasets_mod.create_dataset(
            name=dataset_name,
            description=description,
            rows=len(df),
            columns=len(df.columns),
            uploaded_by=username
        )
        return True, f"Dataset '{dataset_name}' created with {len(df)} rows"
    except Exception as e:
        return False, f"Error creating dataset: {str(e)}"

def handle_incident_upload(df, username, filename):
    """Create incidents from uploaded CSV"""
    try:
        created_count = 0
        errors = []
        
        # Expected columns mapping (adjust based on your CSV structure)
        for idx, row in df.iterrows():
            try:
                incident_id = incidents_mod.create_incident(
                    timestamp=row.get('timestamp', time.strftime("%Y-%m-%d %H:%M:%S")),
                    incident_type=row.get('incident_type', 'Unknown'),
                    severity=row.get('severity', 'Medium'),
                    status=row.get('status', 'Open'),
                    description=row.get('description', f'Uploaded from {filename}'),
                    reported_by=row.get('reported_by', username)
                )
                created_count += 1
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")
        
        message = f"Created {created_count} incidents from CSV"
        if errors:
            message += f". Errors: {', '.join(errors[:3])}"  # Show first 3 errors
        return True, message
        
    except Exception as e:
        return False, f"Error processing incidents: {str(e)}"

def handle_ticket_upload(df, username, filename):
    """Create tickets from uploaded CSV"""
    try:
        created_count = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                ticket_id = tickets_mod.create_ticket(
                    title=row.get('title', f'Ticket from {filename}'),
                    description=row.get('description', ''),
                    priority=row.get('priority', 'Medium'),
                    assigned_to=row.get('assigned_to', ''),
                    reported_by=row.get('reported_by', username)
                )
                created_count += 1
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")
        
        message = f"Created {created_count} tickets from CSV"
        if errors:
            message += f". Errors: {', '.join(errors[:3])}"
        return True, message
        
    except Exception as e:
        return False, f"Error processing tickets: {str(e)}"
    
# -------------------------
# Create forms (incidents, tickets, datasets)
# -------------------------
def add_incident_form(default_reported_by: str = ""):
    if incidents_mod is None:
        return False, "Incidents backend unavailable."
    with st.expander("➕ Add new incident", expanded=False):
        with st.form("new_incident_form"):
            timestamp = st.text_input("Timestamp (ISO / human)", value=time.strftime("%Y-%m-%d %H:%M:%S"))
            incident_type = st.text_input("Incident type (e.g. Phishing, Malware)")
            severities = getattr(incidents_mod, "VALID_SEVERITIES", ["Low", "Medium", "High", "Critical"])
            statuses = getattr(incidents_mod, "VALID_STATUSES", ["Open", "In Progress", "Resolved", "Closed"])
            severity = st.selectbox("Severity", severities, index=min(2, len(severities)-1))
            status = st.selectbox("Status", statuses, index=0)
            reported_by = st.text_input("Reported by", value=default_reported_by)
            description = st.text_area("Description / details", height=120)
            submit = st.form_submit_button("Create incident")
            if submit:
                if not incident_type.strip():
                    st.error("Incident type is required.")
                    return False, "missing_type"
                try:
                    new_id = incidents_mod.create_incident(
                        timestamp=timestamp.strip(),
                        incident_type=incident_type.strip(),
                        severity=severity.strip(),
                        status=status.strip(),
                        description=description.strip(),
                        reported_by=reported_by.strip() or default_reported_by
                    )
                    st.success(f"Incident created (id {new_id}).")
                    return True, new_id
                except Exception as e:
                    st.error(f"Error creating incident: {e}")
                    return False, str(e)
    return False, "not_submitted"

def add_ticket_form(default_reported_by: str = ""):
    if tickets_mod is None:
        return False, "Tickets backend unavailable."
    with st.expander("➕ Add new ticket", expanded=False):
        with st.form("new_ticket_form"):
            title = st.text_input("Title")
            description = st.text_area("Description", height=120)
            priorities = getattr(tickets_mod, "VALID_PRIORITIES", ["Low", "Medium", "High", "Critical"])
            priority = st.selectbox("Priority", options=priorities)
            assigned_to = st.text_input("Assigned to (optional)")
            reported_by = st.text_input("Reported by", value=default_reported_by)
            submit = st.form_submit_button("Create ticket")
            if submit:
                if not title.strip():
                    st.error("Title is required.")
                    return False, "missing_title"
                try:
                    created = tickets_mod.create_ticket(
                        title=title.strip(),
                        description=description.strip(),
                        priority=priority.strip(),
                        assigned_to=assigned_to.strip(),
                        reported_by=reported_by.strip() or default_reported_by
                    )
                    st.success(f"Ticket created: {created}")
                    return True, created
                except Exception as e:
                    st.error(f"Error creating ticket: {e}")
                    return False, str(e)
    return False, "not_submitted"

def add_dataset_form(default_uploaded_by: str = ""):
    if datasets_mod is None:
        return False, "Datasets backend unavailable."
    with st.expander("➕ Add new dataset", expanded=False):
        with st.form("new_dataset_form"):
            name = st.text_input("Dataset name")
            description = st.text_area("Description", height=120)
            rows = st.number_input("Rows", min_value=0, value=0, step=1)
            columns = st.number_input("Columns", min_value=0, value=0, step=1)
            uploaded_by = st.text_input("Uploaded by", value=default_uploaded_by)
            submit = st.form_submit_button("Create dataset")
            if submit:
                if not name.strip():
                    st.error("Dataset name required.")
                    return False, "missing_name"
                try:
                    created = datasets_mod.create_dataset(
                        name=name.strip(),
                        description=description.strip(),
                        rows=int(rows),
                        columns=int(columns),
                        uploaded_by=uploaded_by.strip() or default_uploaded_by
                    )
                    st.success(f"Dataset created: {created}")
                    return True, created
                except Exception as e:
                    st.error(f"Error creating dataset: {e}")
                    return False, str(e)
    return False, "not_submitted"

# -------------------------
# Domain-specific views (Streamlit-native charts only)
# -------------------------
def datasets_view():
    st.subheader("Datasets")
    
    # Add CSV Upload Section
    with st.expander("📤 Upload CSV as New Dataset", expanded=False):
        st.markdown("Drag and drop a CSV file to create a new dataset")
        uploaded_file = st.file_uploader(
            "Choose CSV file", 
            type=['csv'],
            key="dataset_upload"
        )
        
        if uploaded_file is not None:
            # Show preview
            df_preview = pd.read_csv(uploaded_file)
            st.subheader("CSV Preview")
            st.dataframe(df_preview.head(5))
            st.caption(f"Total rows: {len(df_preview)}, Columns: {len(df_preview.columns)}")
            
            if st.button("Upload as Dataset", key="upload_dataset_btn"):
                with st.spinner("Processing CSV file..."):
                    success, message = handle_csv_upload(
                        uploaded_file, 
                        "Datasets", 
                        st.session_state.username
                    )
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
    
    default_uploader = st.session_state.username or ""
    add_dataset_form(default_uploaded_by=default_uploader)

    with st.expander("Dataset controls", expanded=False):
        uploader = st.text_input("Uploaded by (exact match)", value="")
        min_rows = st.number_input("Min rows", min_value=0, value=0, step=1)
        show_table = st.checkbox("Show raw data", value=True)
        if st.button("Reload CSVs -> DB"):
            if csv_loader_mod:
                try:
                    result = csv_loader_mod.load_all_csv_data(data_dir="DATA", clear_table=False)
                    st.success(f"CSV load: {result}")
                except Exception as e:
                    st.error(f"CSV load error: {e}")
            else:
                st.error("CSV loader not available.")

    try:
        if uploader or min_rows:
            df = datasets_mod.get_datasets_by_filters(
                uploaded_by=(uploader or None),
                min_rows=(min_rows if min_rows > 0 else None),
                as_dataframe=True
            )
        else:
            df = datasets_mod.get_all_datasets(as_dataframe=True)
    except Exception as e:
        st.error(f"Error fetching datasets: {e}")
        df = pd.DataFrame()

    df = safe_df(df)
    n_datasets = len(df)
    total_rows = int(df["rows"].sum()) if "rows" in df.columns and not df["rows"].isnull().all() else "N/A"
    small_stat_col_layout([n_datasets, total_rows], ["Datasets", "Total rows"])

    # Chart area: rows distribution (categorical/continuous) using st.bar_chart
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Rows distribution (top values)")
        if not df.empty and "rows" in df.columns:
            counts = df["rows"].value_counts().nlargest(20)
            chart_df = pd.DataFrame({"count": counts})
            st.bar_chart(chart_df)
        else:
            st.info("No 'rows' data to chart.")
    with col2:
        st.subheader("Numeric preview (area chart)")
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            st.area_chart(df[numeric_cols].head(200))
        else:
            st.info("No numeric columns available.")

    with st.expander("See data table"):
        if not df.empty and show_table:
            # Use data_editor so user can filter client-side
            st.caption("Use the table's search & filters (data editor).")
            st.data_editor(df, use_container_width=True)
        else:
            st.info("No datasets to show or 'Show raw data' unchecked.")

def cybersecurity_view():
    st.subheader("Cybersecurity — Incidents")
    
    # Add CSV Upload Section
    with st.expander("📤 Upload CSV of Incidents", expanded=False):
        st.markdown("""
        **Expected CSV columns:** 
        - `incident_type` (required), `severity`, `status`, `description`, `reported_by`, `timestamp`
        """)
        uploaded_file = st.file_uploader(
            "Choose CSV file with incidents", 
            type=['csv'],
            key="incident_upload"
        )
        
        if uploaded_file is not None:
            # Show preview
            df_preview = pd.read_csv(uploaded_file)
            st.subheader("CSV Preview")
            st.dataframe(df_preview.head(5))
            st.caption(f"Total rows: {len(df_preview)}, Columns: {len(df_preview.columns)}")
            
            if st.button("Upload Incidents", key="upload_incident_btn"):
                with st.spinner("Processing incidents..."):
                    success, message = handle_csv_upload(
                        uploaded_file, 
                        "Cybersecurity", 
                        st.session_state.username
                    )
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
    
    default_reporter = st.session_state.username or ""
    add_incident_form(default_reported_by=default_reporter)

    try:
        analytics = incidents_mod.get_all_incident_analytics()
    except Exception as e:
        st.error(f"Error getting analytics: {e}")
        analytics = {}

    total_inc = analytics.get("total_incidents", 0)
    open_inc = analytics.get("open_incidents", 0)
    by_sev = analytics.get("by_severity", {})
    by_status = analytics.get("by_status", {})

    small_stat_col_layout([total_inc, open_inc], ["Total incidents", "Open incidents"])

    # Replace prior "pie chart" with categorical bar chart (Option A)
    st.markdown("### Incidents by severity (bar chart)")
    if by_sev:
        sev_df = pd.DataFrame({"count": list(by_sev.values())}, index=list(by_sev.keys()))
        st.bar_chart(sev_df)
    else:
        st.info("No severity data available.")

    st.markdown("### Incidents by status (bar chart)")
    if by_status:
        status_df = pd.DataFrame({"count": list(by_status.values())}, index=list(by_status.keys()))
        st.bar_chart(status_df)
    else:
        st.info("No status data available.")

    st.markdown("### Filter incidents")
    fcol1, fcol2, fcol3 = st.columns(3)
    sev = fcol1.selectbox("Severity", options=[""] + (incidents_mod.VALID_SEVERITIES if hasattr(incidents_mod, "VALID_SEVERITIES") else []))
    stat = fcol2.selectbox("Status", options=[""] + (incidents_mod.VALID_STATUSES if hasattr(incidents_mod, "VALID_STATUSES") else []))
    inc_type = fcol3.text_input("Incident type (exact match)")

    try:
        df_inc = incidents_mod.get_incidents_by_filters(
            severity=(sev or None),
            status=(stat or None),
            incident_type=(inc_type or None),
            as_dataframe=True
        )
    except Exception as e:
        st.error(f"Error fetching incidents: {e}")
        df_inc = pd.DataFrame()

    df_inc = safe_df(df_inc)
    if not df_inc.empty:
        st.dataframe(df_inc)
    else:
        st.info("No incidents match the filters.")

def tickets_view():
    st.subheader("IT Tickets")
    
    # Add CSV Upload Section
    with st.expander("📤 Upload CSV of Tickets", expanded=False):
        st.markdown("""
        **Expected CSV columns:** 
        - `title` (required), `description`, `priority`, `assigned_to`, `reported_by`
        """)
        uploaded_file = st.file_uploader(
            "Choose CSV file with tickets", 
            type=['csv'],
            key="ticket_upload"
        )
        
        if uploaded_file is not None:
            # Show preview
            df_preview = pd.read_csv(uploaded_file)
            st.subheader("CSV Preview")
            st.dataframe(df_preview.head(5))
            st.caption(f"Total rows: {len(df_preview)}, Columns: {len(df_preview.columns)}")
            
            if st.button("Upload Tickets", key="upload_ticket_btn"):
                with st.spinner("Processing tickets..."):
                    success, message = handle_csv_upload(
                        uploaded_file, 
                        "IT Tickets", 
                        st.session_state.username
                    )
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
   
    default_reporter = st.session_state.username or ""
    add_ticket_form(default_reported_by=default_reporter)

    try:
        t_stats = tickets_mod.get_all_ticket_analytics()
    except Exception as e:
        st.error(f"Error fetching ticket analytics: {e}")
        t_stats = {}

    total_t = t_stats.get("total_tickets", 0)
    open_t = t_stats.get("open_tickets", 0)
    by_assigned = t_stats.get("by_assigned_to", {})
    by_priority = t_stats.get("by_priority", {})

    small_stat_col_layout([total_t, open_t], ["Total tickets", "Open tickets"])

    st.markdown("### Top assigned personnel (bar chart)")
    if by_assigned:
        assigned_df = pd.DataFrame({"count": list(by_assigned.values())}, index=list(by_assigned.keys()))
        st.bar_chart(assigned_df)
    else:
        st.info("No assigned-to data available.")

    st.markdown("### Tickets by priority (bar chart)")
    if by_priority:
        pr_df = pd.DataFrame({"count": list(by_priority.values())}, index=list(by_priority.keys()))
        st.bar_chart(pr_df)
    else:
        st.info("No priority data available.")

    st.markdown("### Recent tickets")
    try:
        recent = tickets_mod.get_recent_tickets(limit=20)
    except Exception as e:
        st.error(f"Error fetching recent tickets: {e}")
        recent = []
    df_recent = safe_df(recent)
    if not df_recent.empty:
        st.dataframe(df_recent)
    else:
        st.info("No recent tickets.")

# -------------------------
# Authentication UI (login / register)
# -------------------------
def show_home():
    st.title("Welcome — Sign in / Register")

    if user_service_mod is None:
        st.error("Authentication service unavailable.")
        return

    # If already logged in and session valid
    if st.session_state.logged_in and st.session_state.session_token:
        sess = user_service_mod.get_session(st.session_state.session_token)
        if sess:
            st.success(f"Signed in as **{st.session_state.username}**")
            left, right = st.columns([1, 1])
            with left:
                if st.button("Go to Dashboard"):
                    st.session_state.current_page = "dashboard"
                    return
            with right:
                if st.button("Logout"):
                    user_service_mod.invalidate_session(st.session_state.session_token)
                    st.session_state.logged_in = False
                    st.session_state.username = ""
                    st.session_state.session_token = None
                    st.success("Logged out.")
                    return
            st.markdown("---")
            return
        else:
            st.warning("Session expired; please sign in again.")
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.session_token = None

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        st.subheader("Sign in")
        login_user = st.text_input("Username", key="login_user")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        if st.button("Sign in"):
            if user_service_mod.is_account_locked(login_user):
                st.error("Account temporarily locked due to failed attempts.")
            else:
                status, role, token = user_service_mod.login_user(login_user, login_pass)
                if status == "success":
                    st.session_state.logged_in = True
                    st.session_state.username = login_user
                    st.session_state.session_token = token
                    st.success("Login successful.")
                    st.session_state.current_page = "dashboard"
                    return
                elif status == "wrong_password":
                    st.error("Incorrect password.")
                elif status == "locked":
                    st.error("Account locked.")
                else:
                    st.error("User not found.")

    with tab_register:
        st.subheader("Create account")
        reg_user = st.text_input("Choose a username", key="reg_user")
        reg_pass = st.text_input("Choose a password", type="password", key="reg_pass")
        reg_confirm = st.text_input("Confirm password", type="password", key="reg_confirm")

        st.markdown("**Password requirements:** 8-50 chars, 1 uppercase, 1 number, 1 special char.")
        if reg_pass:
            try:
                strength = user_service_mod.check_password_strength(reg_pass)
            except Exception:
                strength = "unknown"
            st.info(f"Password strength: {strength}")

        if st.button("Create account"):
            ok_user, user_msg = user_service_mod.validate_username(reg_user)
            if not ok_user:
                st.error(user_msg); return
            ok_pass, pass_msg = user_service_mod.validate_password(reg_pass)
            if not ok_pass:
                st.error(pass_msg); return
            if reg_pass != reg_confirm:
                st.error("Passwords do not match."); return
            created = user_service_mod.register_user(reg_user, reg_pass, role="user")
            if created:
                st.success("Account created.")
            else:
                st.error("Registration failed (username may exist).")

# -------------------------
# Dashboard main & sidebar
# -------------------------
def show_dashboard():
    if not st.session_state.logged_in or not st.session_state.session_token:
        st.error("Please sign in to view the dashboard.")
        if st.button("Go to sign in"):
            st.session_state.current_page = "home"
            return
        return

    sess = user_service_mod.get_session(st.session_state.session_token)
    if not sess:
        st.error("Session invalid/expired. Please sign in again.")
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.session_token = None
        if st.button("Go to sign in"):
            st.session_state.current_page = "home"
            return
        return

    domain = st.session_state.get("current_domain", "Datasets")
    st.title(f"{domain} Dashboard")
    st.caption(f"Signed in as {st.session_state.username}")

    left, right = st.columns([8, 2])
    with right:
        if st.button("Logout"):
            user_service_mod.invalidate_session(st.session_state.session_token)
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.session_token = None
            st.session_state.current_page = "home"
            return

    if domain == "Datasets":
        datasets_view()
    elif domain == "Cybersecurity":
        cybersecurity_view()
    elif domain == "IT Tickets":
        tickets_view()
    else:
        st.info("Select a valid domain in the sidebar.")

def render_sidebar():
    with st.sidebar:
        st.header("Navigation")
        main_page = st.selectbox("Go to:", ["Home", "Dashboard"], index=0 if st.session_state.current_page == "home" else 1)
        st.session_state.current_page = "home" if main_page == "Home" else "dashboard"

        if st.session_state.current_page == "dashboard":
            domain = st.selectbox("Domain", ["Datasets", "Cybersecurity", "IT Tickets"], index=["Datasets", "Cybersecurity", "IT Tickets"].index(st.session_state.current_domain))
            st.session_state.current_domain = domain

        st.markdown("---")
        if st.session_state.logged_in:
            st.write(f"**{st.session_state.username}**")
            if st.button("Sign out (sidebar)"):
                try:
                    user_service_mod.invalidate_session(st.session_state.session_token)
                except Exception:
                    pass
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.session_state.session_token = None
                st.session_state.current_page = "home"
                return
        else:
            st.write("Not signed in")

# -------------------------
# Main
# -------------------------
def main():
    render_sidebar()
    if st.session_state.current_page == "home":
        show_home()
    else:
        show_dashboard()

if __name__ == "__main__":
    main()
