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
import plotly.express as px
from typing import Optional

# -------------------------
# Backend imports (adjust path if needed)
# -------------------------
try:
    from models import csv_loader as csv_loader_mod
    from models import datasets as datasets_mod
    from models import incidents as incidents_mod
    from models import tickets as tickets_mod
    from models import users as users_mod
    from services import user_service as user_service_mod
except Exception as e:
    st.error(f"Error importing backend modules: {e}")
    csv_loader_mod = datasets_mod = incidents_mod = tickets_mod = users_mod = user_service_mod = None

# -------------------------
# Page config & session
# -------------------------
st.set_page_config(page_title="Multi-Domain Intelligence Platform", layout="wide")

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

def is_user_admin():
    """Check if current user has admin role."""
    if not st.session_state.logged_in:
        return False
    
    session_token = st.session_state.get("session_token")
    username = st.session_state.username
    
    if not session_token or not username:
        return False
    
    try:
        # Try to get role through user_service first
        if user_service_mod and hasattr(user_service_mod, "session_user_role"):
            role = user_service_mod.session_user_role(session_token)
            return role == "admin"
        
        # Fallback to direct user lookup
        if users_mod:
            user = users_mod.get_user_by_username(username)
            if user:
                # Handle sqlite3.Row object
                try:
                    user_dict = dict(user)
                    return user_dict.get("role") == "admin"
                except:
                    # Access by index if dict conversion fails
                    return user[3] == "admin" if len(user) > 3 else False
    except Exception:
        return False
    
    return False
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
    """Create dataset entry from uploaded CSV.

    Backend expects: name, rows, columns, uploaded_by, upload_date
    """
    from datetime import date
    try:
        dataset_name = os.path.splitext(filename)[0]  # Use filename as dataset name
        # Using today's date as upload_date (backend requires it)
        upload_date = date.today().isoformat()

        created = datasets_mod.create_dataset(
            name=dataset_name,
            rows=len(df),
            columns=len(df.columns),
            uploaded_by=username or "unknown",
            upload_date=upload_date
        )
        if created == -1:
            return False, f"Dataset creation failed for '{dataset_name}' (db error)."
        return True, f"Dataset '{dataset_name}' created with {len(df)} rows (id {created})"
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
                new_id = incidents_mod.create_incident(
                    timestamp=row.get('timestamp', time.strftime("%Y-%m-%d %H:%M:%S")),
                    category=row.get('category', 'Unknown'),
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
    """Create tickets from uploaded CSV

    Map CSV fields to backend create_ticket parameters:
      - ticket_id: generated unique id (CSV row index + timestamp)
      - priority: use CSV priority or default "Medium"
      - status: default "Open" (backend requires status)
      - category: CSV 'category' or 'General'
      - subject: CSV 'title' or filename-based title
      - description: CSV 'description'
      - created_at: CSV 'created_at' or today
      - assigned_to: CSV 'assigned_to'
    """
    from datetime import date
    try:
        created_count = 0
        errors = []
        for idx, row in df.iterrows():
            try:
                ticket_id = f"CSV-{int(time.time())}-{idx}"
                priority = row.get('priority', 'Medium') or 'Medium'
                status = row.get('status', 'Open') or 'Open'
                category = row.get('category', 'General') or 'General'
                subject = row.get('title', f'Ticket from {filename}') or f'Ticket from {filename}'
                description = row.get('description', '') or ''
                created_at = row.get('created_at', date.today().isoformat()) or date.today().isoformat()
                resolved_date = row.get('resolved_date', None)
                assigned_to = row.get('assigned_to', None)

                new_db_id = tickets_mod.create_ticket(
                    ticket_id=ticket_id,
                    priority=priority,
                    status=status,
                    category=category,
                    subject=subject,
                    description=description,
                    created_at=created_at,
                    resolved_date=resolved_date,
                    assigned_to=assigned_to
                )
                if new_db_id == -1:
                    errors.append(f"Row {idx}: DB error (possible duplicate ticket_id)")
                else:
                    created_count += 1
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")

        message = f"Created {created_count} tickets from CSV"
        if errors:
            message += f". Errors: {', '.join(errors[:5])}"
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
            category = st.text_input("Incident type (e.g. Phishing, Malware)")
            severities = getattr(incidents_mod, "VALID_SEVERITIES", ["Low", "Medium", "High", "Critical"])
            statuses = getattr(incidents_mod, "VALID_STATUSES", ["Open", "In Progress", "Resolved", "Closed"])
            severity = st.selectbox("Severity", severities, index=min(2, len(severities)-1))
            status = st.selectbox("Status", statuses, index=0)
            reported_by = st.text_input("Reported by", value=default_reported_by)
            description = st.text_area("Description / details", height=120)
            submit = st.form_submit_button("Create incident")
            if submit:
                if not category.strip():
                    st.error("Incident type is required.")
                    return False, "missing_type"
                try:
                    new_id = incidents_mod.create_incident(
                        timestamp=timestamp.strip(),
                        category=category.strip(),
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
    """
    Form for creating a new IT ticket.
    Matches backend signature in tickets.py exactly.
    """
    if tickets_mod is None:
        return False, "Tickets backend unavailable."

    with st.expander("➕ Add new ticket", expanded=False):
        with st.form("new_ticket_form"):
            # Required fields
            subject = st.text_input("Ticket subject/title")
            category = st.text_input("Category (e.g., Software, Hardware, Network)", value="General")

            priorities = getattr(tickets_mod, "VALID_PRIORITIES", ["Low", "Medium", "High", "Critical"])
            priority = st.selectbox("Priority", options=priorities)

            statuses = getattr(tickets_mod, "VALID_STATUSES", ["Open", "In Progress", "Resolved", "Closed"])
            status = st.selectbox("Status", options=statuses, index=0)  # default "Open"

            # Optional fields
            description = st.text_area("Description", height=120)
            assigned_to = st.text_input("Assigned to (optional)")

            # Backend requires ticket_id, so we auto-generate one
            import time
            from datetime import date
            generated_ticket_id = f"T-{int(time.time())}"

            submitted = st.form_submit_button("Create Ticket")

            if submitted:
                if not subject.strip():
                    st.error("Subject/title is required.")
                    return False, "missing_subject"

                try:
                    created_at = date.today().isoformat()

                    new_id = tickets_mod.create_ticket(
                        ticket_id=generated_ticket_id,
                        priority=priority.strip(),
                        status=status.strip(),
                        category=category.strip() or "General",
                        subject=subject.strip(),
                        description=description.strip(),
                        created_at=created_at,
                        resolved_date=None,
                        assigned_to=assigned_to.strip() or None
                    )

                    if new_id == -1:
                        st.error("Failed to create ticket (database error or duplicate ticket_id).")
                        return False, "db_error"

                    st.success(f"Ticket created successfully (ID {new_id}).")
                    return True, new_id

                except Exception as e:
                    st.error(f"Error creating ticket: {e}")
                    return False, str(e)
    return False, "not_submitted"

def add_dataset_form(default_uploaded_by: str = ""):
    """
    Dataset creation form that matches datasets.create_dataset signature.
    (No 'description' field is passed to the backend because datasets_metadata
    schema does not include it.)
    """
    if datasets_mod is None:
        return False, "Datasets backend unavailable."

    with st.expander("➕ Add new dataset", expanded=False):
        with st.form("new_dataset_form"):
            name = st.text_input("Dataset name")
            rows = st.number_input("Rows", min_value=0, value=0, step=1)
            columns = st.number_input("Columns", min_value=0, value=0, step=1)
            uploaded_by = st.text_input("Uploaded by", value=default_uploaded_by)

            submit = st.form_submit_button("Create dataset")
            if submit:
                if not name.strip():
                    st.error("Dataset name required.")
                    return False, "missing_name"
                try:
                    from datetime import date
                    upload_date = date.today().isoformat()

                    created = datasets_mod.create_dataset(
                        name=name.strip(),
                        rows=int(rows),
                        columns=int(columns),
                        uploaded_by=uploaded_by.strip() or default_uploaded_by or "unknown",
                        upload_date=upload_date
                    )
                    if created == -1:
                        st.error("Failed to create dataset (database error).")
                        return False, "db_error"

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

    # Upload section (unchanged)
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

    # Add dataset form (keeps previous behaviour)
    default_uploader = st.session_state.username or ""
    add_dataset_form(default_uploaded_by=default_uploader)

    # Controls
    with st.expander("Dataset controls", expanded=False):
        uploader = st.text_input("Uploaded by (exact match)", value="")
        min_rows = st.number_input("Min rows", min_value=0, value=0, step=1)
        show_table = st.checkbox("Show raw data", value=True)
        if st.button("Reload CSVs -> DB"):
            if csv_loader_mod:
                try:
                    result = csv_loader_mod.load_all_csv_data(data_dir="DATA", clear_table=True)
                    st.success(f"CSV load: {result}")
                except Exception as e:
                    st.error(f"CSV load error: {e}")
            else:
                st.error("CSV loader not available.")

    # Fetch datasets (dataframe)
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

    # Basic KPIs
    n_datasets = len(df)
    total_rows = int(df["rows"].sum()) if "rows" in df.columns and not df["rows"].isnull().all() else 0
    avg_rows = int(df["rows"].mean()) if "rows" in df.columns and not df["rows"].isnull().all() else 0
    largest = None
    smallest = None
    if not df.empty and "rows" in df.columns:
        sorted_by_rows = df.sort_values("rows", ascending=False)
        largest = sorted_by_rows.iloc[0]["name"] if "name" in df.columns else sorted_by_rows.index[0]
        smallest = sorted_by_rows.iloc[-1]["name"] if "name" in df.columns else sorted_by_rows.index[-1]

    small_stat_col_layout([n_datasets, total_rows, avg_rows], ["Datasets", "Total rows", "Average rows"])

    # If we have name & rows, show horizontal bar (dataset size) — clear comparison
    st.markdown("### Dataset sizes (rows)")
    if not df.empty and "rows" in df.columns and "name" in df.columns:
        size_df = df[["name", "rows"]].dropna().sort_values("rows", ascending=True)
        # Plotly horizontal bar (top 50 to avoid clutter)
        top_n = min(len(size_df), 50)
        fig = px.bar(size_df.tail(top_n), x="rows", y="name", orientation="h",
                     labels={"rows": "Rows", "name": "Dataset"}, title=f"Dataset size (top {top_n})")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No 'name'+'rows' data to show. Consider reloading CSVs or adding datasets.")

    # Scatter: rows vs columns (if both numeric columns exist)
    st.markdown("### Structural view: rows vs columns (scatter)")
    if not df.empty and "rows" in df.columns and "columns" in df.columns:
        scatter_df = df[["name", "rows", "columns"]].dropna()
        fig_scatter = px.scatter(scatter_df, x="rows", y="columns", hover_name="name",
                                 labels={"rows": "Rows", "columns": "Columns"},
                                 title="Rows vs Columns per Dataset")
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("Need numeric 'rows' and 'columns' to show scatter plot.")

    # Sorted area chart for trend (only makes sense when sorted)
    st.markdown("### Sorted dataset size trend (area chart)")
    if not df.empty and "rows" in df.columns:
        df_sorted = df.sort_values("rows").reset_index(drop=True)
        # Use a simple index axis (datasets ordered by size)
        trend_df = pd.DataFrame({
            "index": df_sorted.index + 1,
            "rows": df_sorted["rows"]
        })
        fig_area = px.area(trend_df, x="index", y="rows", labels={"index": "Dataset Rank (by rows)", "rows": "Rows"},
                           title="Dataset sizes (sorted ascending)")
        st.plotly_chart(fig_area, use_container_width=True)
    else:
        st.info("Not enough numeric 'rows' data to show area chart.")

    # Data table / editor
    with st.expander("See data table"):
        if not df.empty and show_table:
            st.caption("Use the table's search & filters (data editor).")
            st.data_editor(df, use_container_width=True)
        else:
            st.info("No datasets to show or 'Show raw data' unchecked.")

def cybersecurity_view():
    st.subheader("Cybersecurity — Incidents")

    # Add CSV Upload Section (unchanged behavior)
    with st.expander("📤 Upload CSV of Incidents", expanded=False):
        st.markdown("""
        **Expected CSV columns:** 
        - `category` (required), `severity`, `status`, `description`, `reported_by`, `timestamp`
        """)
        uploaded_file = st.file_uploader(
            "Choose CSV file with incidents", 
            type=['csv'],
            key="incident_upload"
        )

        if uploaded_file is not None:
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

    # Fetch analytics from backend
    try:
        analytics = incidents_mod.get_all_incident_analytics()
    except Exception as e:
        st.error(f"Error getting analytics: {e}")
        analytics = {}

    total_inc = analytics.get("total_incidents", 0)
    open_inc = analytics.get("open_incidents", 0)
    by_sev = analytics.get("by_severity", {})
    by_status = analytics.get("by_status", {})

    # KPIs
    small_stat_col_layout([total_inc, open_inc], ["Total incidents", "Open incidents"])

    # Bar chart: incidents by severity (still useful)
    st.markdown("### Incidents by severity (bar chart)")
    if by_sev:
        sev_df = pd.DataFrame({"severity": list(by_sev.keys()), "count": list(by_sev.values())})
        # horizontal bar to show categories cleanly
        fig_bar = px.bar(sev_df.sort_values("count"), x="count", y="severity", orientation="h",
                         labels={"count": "Count", "severity": "Severity"}, title="Incidents by Severity")
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No severity data available.")

    # PIE CHART: incidents by severity (proportions)
    st.markdown("### Incidents by severity (pie chart)")
    if by_sev:
        pie_df = pd.DataFrame({"severity": list(by_sev.keys()), "count": list(by_sev.values())})
        fig_pie = px.pie(pie_df, names="severity", values="count", title="Incident Severity Distribution", hole=0.0)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No severity data available.")

    # Bar chart: incidents by status
    st.markdown("### Incidents by status (bar chart)")
    if by_status:
        status_df = pd.DataFrame({"status": list(by_status.keys()), "count": list(by_status.values())})
        fig_status = px.bar(status_df.sort_values("count"), x="count", y="status", orientation="h",
                            labels={"count": "Count", "status": "Status"}, title="Incidents by Status")
        st.plotly_chart(fig_status, use_container_width=True)
    else:
        st.info("No status data available.")

    # Filters and incident table
    st.markdown("### Filter incidents")
    fcol1, fcol2, fcol3 = st.columns(3)
    sev = fcol1.selectbox("Severity", options=[""] + (incidents_mod.VALID_SEVERITIES if hasattr(incidents_mod, "VALID_SEVERITIES") else []))
    stat = fcol2.selectbox("Status", options=[""] + (incidents_mod.VALID_STATUSES if hasattr(incidents_mod, "VALID_STATUSES") else []))
    inc_type = fcol3.text_input("Incident type (exact match)")

    try:
        df_inc = incidents_mod.get_incidents_by_filters(
            severity=(sev or None),
            status=(stat or None),
            category=(inc_type or None),
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
        recent = tickets_mod.get_recent_tickets(limit=200)
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
        
        # Simple page selection first
        nav_options = ["Home"]
        
        # Add Dashboard if logged in
        if st.session_state.logged_in:
            nav_options.append("Dashboard")
            
            # Try to determine if user is admin (with error handling)
            is_admin = False
            admin_role_checked = False

            try:
                # Simple check: get user from database
                if users_mod and st.session_state.username:
                    user = users_mod.get_user_by_username(st.session_state.username)
                    if user:
                        admin_role_checked = True
                        
                        # Handle sqlite3.Row object
                        if hasattr(user, '_fields'):
                            # Get index of 'role' column
                            if 'role' in user._fields:
                                idx = user._fields.index('role')
                                is_admin = user[idx] == "admin"
                            else:
                                # Try common column indices if role not found by name
                                # Common order: id, username, password_hash, role, ...
                                if len(user) >= 4:
                                    is_admin = user[3] == "admin"  # 4th column is often role
                        else:
                            # Try as dict
                            try:
                                user_dict = dict(user) if not isinstance(user, dict) else user
                                is_admin = user_dict.get("role") == "admin"
                            except:
                                # Last resort: check username
                                is_admin = st.session_state.username.lower() == "admin"
            except Exception as e:
                # Don't show error in sidebar to avoid breaking UI
                is_admin = False

            # DEBUG: Show admin status in sidebar (temporary)
            if admin_role_checked:
                st.sidebar.caption(f"Admin check: {'✅ YES' if is_admin else '❌ NO'}")
                
                # Add Admin option if user is admin
                if is_admin:
                    nav_options.append("Admin")
        
        # Page selection
        try:
            # Find current page index
            current_page_name = st.session_state.current_page
            page_to_name = {
                "home": "Home",
                "dashboard": "Dashboard",
                "admin": "Admin"
            }
            current_nav_name = page_to_name.get(current_page_name, "Home")
            
            if current_nav_name not in nav_options:
                current_nav_name = nav_options[0]
            
            main_page = st.selectbox(
                "Go to:",
                nav_options,
                index=nav_options.index(current_nav_name)
            )
            
            # Update session state
            name_to_page = {
                "Home": "home",
                "Dashboard": "dashboard",
                "Admin": "admin"
            }
            st.session_state.current_page = name_to_page[main_page]
            
        except Exception as e:
            st.error(f"Navigation error: {e}")
            main_page = "Home"
            st.session_state.current_page = "home"
        
        # Domain selection for dashboard
        if st.session_state.current_page == "dashboard":
            try:
                domain = st.selectbox(
                    "Domain",
                    ["Datasets", "Cybersecurity", "IT Tickets"],
                    index=["Datasets", "Cybersecurity", "IT Tickets"].index(
                        st.session_state.current_domain
                    ) if st.session_state.current_domain in ["Datasets", "Cybersecurity", "IT Tickets"] else 0
                )
                st.session_state.current_domain = domain
            except Exception:
                st.session_state.current_domain = "Datasets"
        
        st.markdown("---")
        
        # User info section
        if st.session_state.logged_in:
            st.write(f"**{st.session_state.username}** (logged in)")
            if st.button("Sign out"):
                try:
                    if user_service_mod and st.session_state.session_token:
                        user_service_mod.invalidate_session(st.session_state.session_token)
                except:
                    pass
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.session_state.session_token = None
                st.session_state.current_page = "home"
                st.rerun()
        else:
            st.write("Not signed in")
               

def admin_panel():
    """Admin-only panel: user list, change role, lock/unlock, delete user, run CSV reload."""
    # Ensure we have services
    if user_service_mod is None or users_mod is None:
        st.error("Admin tools unavailable.")
        return
    
    # Check if user is logged in
    if not st.session_state.logged_in:
        st.warning("Please sign in to access admin panel.")
        if st.button("Go to sign in"):
            st.session_state.current_page = "home"
            st.rerun()
        return
    
    # Get user's role
    username = st.session_state.username
    user = users_mod.get_user_by_username(username)
    
    if not user:
        st.warning("User not found in database.")
        return
    
    # Extract role from sqlite3.Row
    try:
        # Try to convert to dict first
        user_dict = dict(user)
        user_role = user_dict.get("role")
    except:
        # Fallback to index access
        user_role = user[3] if len(user) > 3 else "unknown"
    
    if user_role != "admin":
        st.warning("You do not have admin privileges.")
        st.info(f"Your role: {user_role}")
        return
    
    # ---- HEADER WITH STYLING ----
    st.markdown("""
    <style>
    .admin-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
    }
    .user-card {
        background: white;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 5px solid #667eea;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    .user-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    }
    .role-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        margin-left: 10px;
    }
    .role-admin { background: #ff6b6b; color: white; }
    .role-datasets_admin { background: #4ecdc4; color: white; }
    .role-cyber_admin { background: #45b7d1; color: white; }
    .role-tickets_admin { background: #96ceb4; color: white; }
    .role-user { background: #ffeaa7; color: #333; }
    .action-btn {
        margin-top: 5px;
        margin-bottom: 5px;
    }
    .stats-card {
        background: white;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="admin-header"><h1> Admin Panel</h1><p>User Management & System Control</p></div>', unsafe_allow_html=True)
    
    # ---- QUICK STATS ----
    users = users_mod.get_all_users()
    if not users:
        st.info("No users in the system.")
        return
    
    # Calculate stats
    total_users = len(users)
    admin_count = 0
    locked_count = 0
    
    for u in users:
        try:
            u_dict = dict(u)
            role = u_dict.get("role", "user")
            locked_until = u_dict.get("locked_until")
        except:
            role = u[3] if len(u) > 3 else "user"
            locked_until = u[5] if len(u) > 5 else None
        
        if role == "admin":
            admin_count += 1
        if locked_until:
            locked_count += 1
    
    # Display stats in cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="stats-card">
            <h3>👥 Total Users</h3>
            <h1 style="color: #667eea;">{total_users}</h1>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stats-card">
            <h3>👑 Admins</h3>
            <h1 style="color: #ff6b6b;">{admin_count}</h1>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="stats-card">
            <h3>🔒 Locked Accounts</h3>
            <h1 style="color: #f39c12;">{locked_count}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    # ---- SEARCH AND FILTER ----
    st.markdown("### 🔍 User Management")
    
    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        search_query = st.text_input("Search users by username", placeholder="Type to search...")
    with search_col2:
        role_filter = st.selectbox("Filter by role", ["All", "admin", "user", "datasets_admin", "cyber_admin", "tickets_admin"])
    
    # ---- USER CARDS ----
    st.markdown("### 📋 User List")
    
    # Process and filter users
    filtered_users = []
    for u in users:
        try:
            u_dict = dict(u)
            current_username = u_dict.get("username", "")
            current_role = u_dict.get("role", "user")
            failed_attempts = u_dict.get("failed_attempts", 0)
            locked_until = u_dict.get("locked_until")
            created_at = u_dict.get("created_at", "Unknown")
        except:
            current_username = u[1] if len(u) > 1 else "unknown"
            current_role = u[3] if len(u) > 3 else "user"
            failed_attempts = u[4] if len(u) > 4 else 0
            locked_until = u[5] if len(u) > 5 else None
            created_at = u[6] if len(u) > 6 else "Unknown"
        
        # Apply filters
        if search_query and search_query.lower() not in current_username.lower():
            continue
        if role_filter != "All" and current_role != role_filter:
            continue
        
        filtered_users.append({
            "username": current_username,
            "role": current_role,
            "failed_attempts": failed_attempts,
            "locked_until": locked_until,
            "created_at": created_at,
            "row_obj": u
        })
    
    if not filtered_users:
        st.info("No users match your search criteria.")
        return
    
    # Display each user in a nice card
    for user_data in filtered_users:
        current_username = user_data["username"]
        current_role = user_data["role"]
        failed_attempts = user_data["failed_attempts"]
        locked_until = user_data["locked_until"]
        created_at = user_data["created_at"]
        u = user_data["row_obj"]
        
        # Determine role badge color
        badge_class = f"role-{current_role}"
        
        # Check if account is locked
        is_locked = locked_until is not None
        
        st.markdown(f"""
        <div class="user-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h4 style="margin: 0; display: inline;">👤 {current_username}</h4>
                    <span class="role-badge {badge_class}">{current_role}</span>
                    {"🔒" if is_locked else "🔓"}
                </div>
                <div style="font-size: 12px; color: #666;">
                    Created: {str(created_at)[:19] if created_at else "Unknown"}
                </div>
            </div>
            <div style="margin-top: 10px; font-size: 14px; color: #666;">
                Failed attempts: {failed_attempts} | 
                Status: <strong style="color: {'#e74c3c' if is_locked else '#27ae60'}">
                {"🔒 Locked" if is_locked else "✅ Active"}</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # User actions in columns
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        
        with col1:
            # Role selector
            new_role = st.selectbox(
                "Change Role",
                options=["user", "datasets_admin", "cyber_admin", "tickets_admin", "admin"],
                index=["user", "datasets_admin", "cyber_admin", "tickets_admin", "admin"].index(current_role) 
                if current_role in ["user", "datasets_admin", "cyber_admin", "tickets_admin", "admin"] else 0,
                key=f"role_select_{current_username}_{id(u)}",
                label_visibility="collapsed"
            )
        
        with col2:
            # Save role button
            if st.button("💾 Save Role", key=f"save_{current_username}_{id(u)}", use_container_width=True):
                if current_role != new_role:
                    try:
                        if users_mod.set_user_role(current_username, new_role):
                            st.success(f"✅ Role updated: {current_username} → {new_role}")
                            st.rerun()
                        else:
                            st.error("❌ Failed to update role")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.info("Role unchanged")
        
        with col3:
            # Lock/Unlock button
            if is_locked:
                if st.button("🔓 Unlock", key=f"unlock_{current_username}_{id(u)}", use_container_width=True, type="secondary"):
                    try:
                        users_mod.update_user(current_username, failed_attempts=0, locked_until=None)
                        st.success(f"✅ Unlocked {current_username}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                if st.button("🔒 Lock", key=f"lock_{current_username}_{id(u)}", use_container_width=True, type="secondary"):
                    try:
                        from datetime import datetime, timedelta
                        locked_until = (datetime.now() + timedelta(hours=24)).isoformat()
                        users_mod.update_user(current_username, locked_until=locked_until)
                        st.success(f"✅ Locked {current_username} for 24 hours")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        with col4:
            # Delete button (cannot delete self)
            if current_username == st.session_state.username:
                st.button("❌ Delete", key=f"del_{current_username}_{id(u)}", disabled=True, use_container_width=True,
                         help="Cannot delete your own account")
            else:
                if st.button("🗑️ Delete", key=f"del_{current_username}_{id(u)}", type="primary", use_container_width=True):
                    try:
                        if users_mod.delete_user_by_username(current_username):
                            st.success(f"✅ Deleted user {current_username}")
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete user")
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        st.markdown("---")
    
    # ---- SYSTEM ACTIONS SECTION ----
    st.markdown("### ⚙️ System Actions")
    
    sys_col1, sys_col2, sys_col3 = st.columns(3)
    
    with sys_col1:
        if st.button("🔄 Refresh All Data", use_container_width=True):
            try:
                if csv_loader_mod:
                    result = csv_loader_mod.load_all_csv_data(data_dir="DATA", clear_table=True)
                    st.success(f"✅ Data refreshed: {result}")
                else:
                    st.error("CSV loader not available")
            except Exception as e:
                st.error(f"Error: {e}")
    
    with sys_col2:
        if st.button("📊 View Database Stats", use_container_width=True):
            try:
                from database.db import connect_database
                conn = connect_database()
                
                # Get table counts
                tables = ["users", "sessions", "datasets_metadata", "incidents", "tickets"]
                for table in tables:
                    try:
                        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                        st.info(f"📋 {table}: {count} records")
                    except:
                        st.warning(f"Table '{table}' not found")
                
                conn.close()
            except Exception as e:
                st.error(f"Error: {e}")
    
    with sys_col3:
        if st.button("🧹 Clear All Sessions", use_container_width=True, type="secondary"):
            try:
                from database.db import connect_database
                conn = connect_database()
                conn.execute("DELETE FROM sessions")
                conn.commit()
                conn.close()
                st.success("✅ All sessions cleared")
                st.session_state.session_token = None
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    
    # ---- QUICK USER CREATION ----
    with st.expander("➕ Quick Create New User", expanded=False):
        create_col1, create_col2, create_col3 = st.columns([2, 2, 1])
        
        with create_col1:
            new_username = st.text_input("Username", key="new_user_username")
        with create_col2:
            new_role = st.selectbox("Role", ["user", "admin"], key="new_user_role")
        with create_col3:
            if st.button("Create", use_container_width=True):
                if new_username:
                    try:
                        # Generate a temporary password
                        import random
                        import string
                        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                        
                        # Register the user
                        created = user_service_mod.register_user(new_username, temp_password, role=new_role)
                        if created:
                            st.success(f"✅ User '{new_username}' created")
                            st.info(f"Temporary password: `{temp_password}`")
                            st.rerun()
                        else:
                            st.error("❌ User creation failed")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Please enter a username")

# -------------------------
# Main
# -------------------------
def main():
    render_sidebar()
    page = st.session_state.current_page
    
    if page == "home":
        show_home()
    elif page == "dashboard":
        show_dashboard()
    elif page == "admin":
        # Check if user is logged in
        if not st.session_state.logged_in:
            st.error("Please sign in to access admin panel.")
            if st.button("Go to sign in"):
                st.session_state.current_page = "home"
                st.rerun()
            return
        
        # Get user's role from database
        username = st.session_state.username
        try:
            user = users_mod.get_user_by_username(username)
            if not user:
                st.error("User not found in database.")
                return
            
            # Extract role
            try:
                user_dict = dict(user)
                user_role = user_dict.get("role")
            except:
                user_role = user[3] if len(user) > 3 else "unknown"
            
            # Check if admin
            if user_role != "admin":
                st.error("Admin access required.")
                st.info(f"Your role: {user_role}")
                if st.button("Go to dashboard"):
                    st.session_state.current_page = "dashboard"
                    st.rerun()
                return
                
        except Exception as e:
            st.error(f"Error checking admin access: {e}")
            if st.button("Go to dashboard"):
                st.session_state.current_page = "dashboard"
                st.rerun()
            return

        # If OK, show admin panel
        admin_panel()
    else:
        st.info("Unknown page; returning to home.")
        st.session_state.current_page = "home"
        show_home()


if __name__ == "__main__":
    main()
