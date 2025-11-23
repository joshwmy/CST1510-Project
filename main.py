# streamlit_app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.user_service import login_user, register_user, get_session, invalidate_session
from app.data.incidents import get_all_incidents, get_incidents_by_filters
from app.data.tickets import get_all_tickets, get_tickets_by_filters
from app.data.datasets import get_all_datasets
from app.data.csv_loader import load_all_csv_data, verify_data_loading

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Intelligence Platform",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# HELPER: CHECK CURRENT SESSION
# --------------------------------------------------
def get_current_session():
    token = st.session_state.get("auth_token")
    if not token:
        return None
    return get_session(token)

# --------------------------------------------------
# DATA INITIALIZATION (Only after login)
# --------------------------------------------------
def initialize_sample_data():
    """Load sample data if tables are empty"""
    try:
        from app.data.incidents import get_total_incidents_count
        from app.data.tickets import get_total_tickets_count
        
        if get_total_incidents_count() == 0 and get_total_tickets_count() == 0:
            st.info("📊 Loading sample data for first-time setup...")
            results = load_all_csv_data()
            verify_data_loading()
            st.success("✅ Sample data loaded successfully!")
            st.rerun()
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")

# --------------------------------------------------
# AUTHENTICATION PAGES
# --------------------------------------------------
def show_login_page():
    # Simple centered login form without data loading
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🔐 Intelligence Platform")
        st.markdown("---")
        
        # Login/Register tabs
        tab1, tab2 = st.tabs(["🚀 Login", "📝 Register"])
        
        with tab1:
            st.subheader("Sign In to Your Account")
            
            with st.form("login_form"):
                username = st.text_input("👤 Username", placeholder="Enter your username")
                password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
                
                login_btn = st.form_submit_button("Login", use_container_width=True, type="primary")
                
                if login_btn:
                    if username and password:
                        with st.spinner("Authenticating..."):
                            status, role, token = login_user(username, password)
                            
                            if status == "success":
                                st.session_state["auth_token"] = token
                                st.session_state["username"] = username
                                st.session_state["role"] = role
                                st.success("✅ Logged in successfully!")
                                st.rerun()
                            elif status == "locked":
                                st.error("🔒 Your account is locked. Try again later.")
                            else:
                                st.error("❌ Invalid username or password.")
                    else:
                        st.warning("⚠️ Please enter both username and password.")
        
        with tab2:
            st.subheader("Create New Account")
            
            with st.form("registration_form"):
                new_username = st.text_input("New Username")
                new_password = st.text_input("New Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                
                register_btn = st.form_submit_button("Create Account", use_container_width=True)
                
                if register_btn:
                    if new_username and new_password:
                        if new_password == confirm_password:
                            if register_user(new_username, new_password):
                                st.success("✅ Account created successfully! Please login.")
                            else:
                                st.error("❌ Username already exists.")
                        else:
                            st.error("❌ Passwords do not match")
                    else:
                        st.warning("⚠️ Please fill all required fields")

# --------------------------------------------------
# LOGOUT
# --------------------------------------------------
def logout():
    token = st.session_state.get("auth_token")
    if token:
        invalidate_session(token)
    
    st.session_state.clear()
    st.success("👋 Logged out successfully!")
    st.rerun()

# --------------------------------------------------
# DATA PROCESSING HELPERS
# --------------------------------------------------
def process_incidents_data(df):
    """Process incidents data for display"""
    if df.empty:
        return df
    
    # Convert timestamp to datetime if needed
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    return df

def process_tickets_data(df):
    """Process tickets data for display"""
    if df.empty:
        return df
    
    # Convert timestamp to datetime if needed
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'])
    
    return df

def process_datasets_data(df):
    """Process datasets data for display"""
    if df.empty:
        return df
    
    return df

# --------------------------------------------------
# DASHBOARD: INCIDENTS
# --------------------------------------------------
def page_incidents():
    st.title("🚨 Cyber Incidents Dashboard")
    
    # Get all incidents and process the data
    raw_data = get_all_incidents()
    df = process_incidents_data(pd.DataFrame(raw_data))
    
    if df.empty:
        st.info("📊 No incidents found in the database.")
        if st.button("🔄 Load Sample Data"):
            initialize_sample_data()
        return
    
    # Calculates analytics
    total_incidents = len(df)
    open_incidents = len(df[df['status'].isin(['Open', 'In Progress'])])
    
    severity_counts = df['severity'].value_counts()
    high_critical = severity_counts.get('High', 0) + severity_counts.get('Critical', 0)
    
    status_counts = df['status'].value_counts()
    resolved_closed = status_counts.get('Resolved', 0) + status_counts.get('Closed', 0)
    
    # Analytics Overview
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Incidents", total_incidents)
    with col2:
        st.metric("Open Incidents", open_incidents)
    with col3:
        st.metric("High/Critical", high_critical)
    with col4:
        st.metric("Resolved/Closed", resolved_closed)
    
    # Filters
    st.subheader("🔍 Filters")
    col1, col2, col3 = st.columns(3)
    with col1:
        severity_filter = st.multiselect(
            "Severity",
            ["Low", "Medium", "High", "Critical"],
            default=["Low", "Medium", "High", "Critical"]
        )
    with col2:
        status_filter = st.multiselect(
            "Status",
            ["Open", "In Progress", "Closed", "Resolved"],
            default=["Open", "In Progress", "Resolved", "Closed"]
        )
    with col3:
        categories = df['incident_type'].unique().tolist() if 'incident_type' in df.columns else []
        category_filter = st.multiselect("Category", categories, default=categories)
    
    # Apply filters
    filtered_df = df.copy()
    
    if severity_filter:
        filtered_df = filtered_df[filtered_df['severity'].isin(severity_filter)]
    if status_filter:
        filtered_df = filtered_df[filtered_df['status'].isin(status_filter)]
    if category_filter and 'incident_type' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['incident_type'].isin(category_filter)]
    
    if filtered_df.empty:
        st.info("📊 No incidents found matching your filters.")
        return
    
    # Charts
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("Incidents by Severity")
        if "severity" in filtered_df.columns:
            severity_counts = filtered_df["severity"].value_counts()
            fig = px.pie(
                values=severity_counts.values,
                names=severity_counts.index,
                color=severity_counts.index,
                color_discrete_map={
                    'Critical': 'red',
                    'High': 'orange', 
                    'Medium': 'yellow',
                    'Low': 'green'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col_chart2:
        st.subheader("Incidents by Category")
        if "incident_type" in filtered_df.columns:
            category_counts = filtered_df["incident_type"].value_counts()
            fig = px.bar(
                x=category_counts.index,
                y=category_counts.values,
                color=category_counts.index
            )
            fig.update_layout(xaxis_title="Category", yaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)
    
    # Data Table
    with st.expander("📋 Incident Details", expanded=False):
        if not filtered_df.empty:
            display_df = filtered_df.copy()
            
            # Select columns for display
            display_columns = ['incident_id', 'timestamp', 'severity', 'category', 'status', 'description']
            display_columns = [col for col in display_columns if col in display_df.columns]
            
            display_df = display_df[display_columns]
            
            # Format date
            if 'timestamp' in display_df.columns:
                display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
            
            st.dataframe(display_df, use_container_width=True)
            
            # Export option
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="📥 Export to CSV",
                data=csv,
                file_name=f"incidents_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

# --------------------------------------------------
# DASHBOARD: TICKETS
# --------------------------------------------------
def page_tickets():
    st.title("🎫 IT Tickets Dashboard")
    
    # Get all tickets
    raw_data = get_all_tickets()
    df = process_tickets_data(pd.DataFrame(raw_data))
    
    if df.empty:
        st.info("📊 No tickets found in the database.")
        if st.button("🔄 Load Sample Data"):
            initialize_sample_data()
        return
    
    # Calculate analytics
    total_tickets = len(df)
    open_tickets = len(df[df['status'].isin(['Open', 'In Progress', 'Waiting for User'])])
    
    priority_counts = df['priority'].value_counts()
    high_critical = priority_counts.get('High', 0) + priority_counts.get('Critical', 0)
    
    assigned_count = df['assigned_to'].notna().sum()
    
    # Analytics Overview
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tickets", total_tickets)
    with col2:
        st.metric("Open Tickets", open_tickets)
    with col3:
        st.metric("High/Critical", high_critical)
    with col4:
        st.metric("Assigned Tickets", assigned_count)
    
    # Filters
    st.subheader("🔍 Filters")
    col1, col2, col3 = st.columns(3)
    with col1:
        priority_filter = st.multiselect(
            "Priority",
            ["Low", "Medium", "High", "Critical"],
            default=["Low", "Medium", "High", "Critical"]
        )
    with col2:
        status_filter = st.multiselect(
            "Status",
            ["Open", "In Progress", "Resolved", "Closed", "Waiting for User"],
            default=["Open", "In Progress", "Resolved", "Closed", "Waiting for User"]
        )
    with col3:
        assignees = df['assigned_to'].unique().tolist() if 'assigned_to' in df.columns else []
        assignee_filter = st.multiselect("Assigned To", assignees, default=assignees)
    
    # Apply filters
    filtered_df = df.copy()
    
    if priority_filter:
        filtered_df = filtered_df[filtered_df['priority'].isin(priority_filter)]
    if status_filter:
        filtered_df = filtered_df[filtered_df['status'].isin(status_filter)]
    if assignee_filter and 'assigned_to' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['assigned_to'].isin(assignee_filter)]
    
    if filtered_df.empty:
        st.info("📊 No tickets found matching your filters.")
        return
    
    # Charts
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("Tickets by Priority")
        if "priority" in filtered_df.columns:
            priority_counts = filtered_df["priority"].value_counts()
            fig = px.bar(
                x=priority_counts.index,
                y=priority_counts.values,
                color=priority_counts.index,
                color_discrete_map={
                    'Critical': 'red',
                    'High': 'orange',
                    'Medium': 'yellow',
                    'Low': 'green'
                }
            )
            fig.update_layout(xaxis_title="Priority", yaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)
    
    with col_chart2:
        st.subheader("Tickets by Status")
        if "status" in filtered_df.columns:
            status_counts = filtered_df["status"].value_counts()
            fig = px.pie(values=status_counts.values, names=status_counts.index)
            st.plotly_chart(fig, use_container_width=True)
    
    # Data Table
    with st.expander("📋 Ticket Details", expanded=False):
        if not filtered_df.empty:
            display_df = filtered_df.copy()
            
            # Select columns for display
            display_columns = ['ticket_id', 'priority', 'status', 'assigned_to', 'created_at', 'description', 'resolution_time_hours']
            display_columns = [col for col in display_columns if col in display_df.columns]
            
            display_df = display_df[display_columns]
            
            # Format date
            if 'created_at' in display_df.columns:
                display_df['created_at'] = display_df['created_at'].dt.strftime('%Y-%m-%d %H:%M')
            
            st.dataframe(display_df, use_container_width=True)
            
            # Export option
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="📥 Export to CSV",
                data=csv,
                file_name=f"tickets_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

# --------------------------------------------------
# DASHBOARD: DATASETS
# --------------------------------------------------
def page_datasets():
    st.title("📁 Datasets Overview")
    
    # Get all datasets
    raw_data = get_all_datasets()
    df = process_datasets_data(pd.DataFrame(raw_data))
    
    if df.empty:
        st.info("📊 No datasets found in the database.")
        if st.button("🔄 Load Sample Data"):
            initialize_sample_data()
        return
    
    # Calculate analytics
    total_datasets = len(df)
    total_rows = df['record_count'].sum() if 'record_count' in df.columns else 0
    categories = df['category'].nunique() if 'category' in df.columns else 0
    sources = df['source'].nunique() if 'source' in df.columns else 0
    
    # Analytics Overview
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Datasets", total_datasets)
    with col2:
        st.metric("Total Rows", f"{total_rows:,}")
    with col3:
        st.metric("Categories", categories)
    with col4:
        st.metric("Sources", sources)
    
    # Data Table
    with st.expander("📋 Dataset Details", expanded=True):
        if not df.empty:
            display_df = df.copy()
            
            # Select columns for display
            display_columns = ['name', 'rows', 'columns', 'uploaded_by', 'upload_date']
            display_columns = [col for col in display_columns if col in display_df.columns]
            
            display_df = display_df[display_columns]
            
            st.dataframe(display_df, use_container_width=True)
            
            # Export option
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="📥 Export to CSV",
                data=csv,
                file_name=f"datasets_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    # Charts
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("Datasets by Category")
        if "category" in df.columns:
            category_counts = df["category"].value_counts()
            fig = px.pie(values=category_counts.values, names=category_counts.index)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_chart2:
        st.subheader("Dataset Sizes")
        if "file_size_mb" in df.columns:
            # Show largest datasets
            size_df = df.nlargest(10, 'file_size_mb')[['dataset_name', 'file_size_mb']]
            fig = px.bar(
                size_df,
                x='dataset_name',
                y='file_size_mb',
                title="Largest Datasets (MB)"
            )
            fig.update_layout(xaxis_title="Dataset", yaxis_title="Size (MB)")
            st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# ADMIN PANEL
# --------------------------------------------------
def page_admin():
    st.title("⚙️ Admin Panel")
    
    if st.session_state.get("role") != "admin":
        st.warning("🔒 Admin access required")
        return
    
    tab1, tab2 = st.tabs(["Data Management", "System Info"])
    
    with tab1:
        st.subheader("Data Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Load Sample Data", use_container_width=True):
                try:
                    results = load_all_csv_data(clear_table=True)
                    st.success("✅ Data loaded successfully!")
                    for table, count in results.items():
                        st.write(f"{table}: {count} rows loaded")
                    verify_data_loading()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error loading data: {e}")
        
        with col2:
            if st.button("📊 Verify Data", use_container_width=True):
                try:
                    verify_data_loading()
                    st.success("✅ Data verification complete!")
                except Exception as e:
                    st.error(f"❌ Error verifying data: {e}")
    
    with tab2:
        st.subheader("System Information")
        
        # Display current data counts
        try:
            from app.data.incidents import get_total_incidents_count
            from app.data.tickets import get_total_tickets_count
            from app.data.datasets import get_total_datasets_count
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Incidents", get_total_incidents_count())
            with col2:
                st.metric("Tickets", get_total_tickets_count())
            with col3:
                st.metric("Datasets", get_total_datasets_count())
        except Exception as e:
            st.error(f"Error getting system info: {e}")

# --------------------------------------------------
# MAIN APP LOGIC
# --------------------------------------------------
def main():
    session = get_current_session()
    
    # NOT AUTHENTICATED - Show login page only
    if not session:
        show_login_page()
        st.stop()
    
    # AUTHENTICATED VIEW - Show dashboard with sidebar
    # Initialize data only after successful login
    if "data_initialized" not in st.session_state:
        initialize_sample_data()
        st.session_state.data_initialized = True
    
    # Sidebar Navigation
    with st.sidebar:
        st.title("🔍 Intelligence Platform")
        st.markdown(f"**Welcome,** `{session['username']}`")
        st.markdown(f"*Role:* `{session.get('role', 'User')}`")
        st.markdown("---")
        
        # Navigation
        st.subheader("Navigation")
        nav_options = ["🚨 Incidents", "🎫 Tickets", "📁 Datasets"]
        
        # Add admin panel for admin users
        if session.get("role") == "admin":
            nav_options.append("⚙️ Admin")
        
        nav_options.append("🚪 Logout")
        
        choice = st.radio(
            "Go to:",
            nav_options,
            index=0,
        )
        
        st.markdown("---")
        
        # Quick Stats (only show if we have data)
        st.subheader("Quick Stats")
        try:
            from app.data.incidents import get_open_incidents_count
            from app.data.tickets import get_open_tickets_count
            from app.data.datasets import get_total_datasets_count
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Open Incidents", get_open_incidents_count())
            with col2:
                st.metric("Open Tickets", get_open_tickets_count())
            
            st.metric("Total Datasets", get_total_datasets_count())
        except Exception:
            st.info("Load data to see stats")
    
    # Main content area based on navigation choice
    if choice == "🚨 Incidents":
        page_incidents()
    elif choice == "🎫 Tickets":
        page_tickets()
    elif choice == "📁 Datasets":
        page_datasets()
    elif choice == "⚙️ Admin":
        page_admin()
    elif choice == "🚪 Logout":
        logout()

if __name__ == "__main__":
    main()