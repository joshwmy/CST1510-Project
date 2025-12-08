# views/admin_view.py
"""
Admin panel for user management and system overview
FIXED: Delete and unlock buttons now work properly
"""
import streamlit as st
from datetime import datetime


def is_user_admin(users_mod=None, user_service_mod=None):
    """Check if current user is admin"""
    return st.session_state.get("user_role") == "admin"


def admin_panel(
    users_mod=None,
    csv_loader_mod=None,
    user_service_mod=None,
    datasets_mod=None,
    incidents_mod=None,
    tickets_mod=None
):
    """Main admin panel view"""
    
    # Header with better styling
    st.markdown("### 🔧 Admin Panel")
    st.caption(f"Welcome back, **{st.session_state.username}**")
    st.markdown("---")
    
    # Tabs for different admin sections
    tab1, tab2, tab3 = st.tabs(["👥 User Management", "📊 System Overview", "🗄️ Database Info"])
    
    with tab1:
        show_user_management(users_mod, user_service_mod)
    
    with tab2:
        show_system_overview(datasets_mod, incidents_mod, tickets_mod)
    
    with tab3:
        show_database_info(csv_loader_mod)


def show_user_management(users_mod, user_service_mod):
    """User management section"""
    
    st.subheader("🔍 User Management")
    
    # Search and filter in cleaner layout
    col1, col2 = st.columns([2, 1])
    with col1:
        search_term = st.text_input("🔎 Search users", placeholder="Type username...", key="user_search")
    with col2:
        role_filter = st.selectbox("Filter by role", 
                                   ["All", "admin", "datasets_admin", "cybersecurity_admin", "it_admin", "user"])
    
    st.markdown("")  # Small spacing
    
    # Get all users
    if users_mod:
        try:
            all_users = users_mod.get_all_users()
        except Exception as e:
            st.error(f"Error fetching users: {e}")
            all_users = []
    else:
        st.error("Users module not available")
        all_users = []
    
    # Filter users based on search and role
    filtered_users = []
    for user in all_users:
        username = user.get('username') if isinstance(user, dict) else user[1]
        role = user.get('role') if isinstance(user, dict) else user[3]
        
        # Apply search filter
        if search_term and search_term.lower() not in username.lower():
            continue
        
        # Apply role filter
        if role_filter != "All" and role != role_filter:
            continue
        
        filtered_users.append(user)
    
    st.markdown(f"**{len(filtered_users)} users found**")
    st.markdown("")  # Small spacing
    
    # Display users
    if not filtered_users:
        st.info("No users found matching the filters.")
    else:
        for user in filtered_users:
            display_user_card(user, users_mod, user_service_mod)


def display_user_card(user, users_mod, user_service_mod):
    """Display a single user card with actions"""
    
    # Extract user data
    user_id = user.get('id') if isinstance(user, dict) else user[0]
    username = user.get('username') if isinstance(user, dict) else user[1]
    role = user.get('role') if isinstance(user, dict) else user[3]
    failed_attempts = user.get('failed_attempts') if isinstance(user, dict) else user[4]
    locked_until = user.get('locked_until') if isinstance(user, dict) else user[5]
    created_at = user.get('created_at') if isinstance(user, dict) else user[6]
    
    # Check if account is locked
    is_locked = False
    if locked_until:
        try:
            lock_time = datetime.fromisoformat(locked_until)
            if datetime.now() < lock_time:
                is_locked = True
        except:
            pass
    
    # Create container for user card with simple Streamlit styling
    with st.container():
        # User header
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"**👤 {username}**")
            st.caption(f"Failed attempts: {failed_attempts or 0} | Created: {created_at}")
        
        with col2:
            # Lock status badge
            if is_locked:
                st.markdown('<span style="background-color: #dc3545; color: white; padding: 4px 10px; border-radius: 8px; font-size: 12px;">🔒 Locked</span>', 
                           unsafe_allow_html=True)
            else:
                st.markdown('<span style="background-color: #28a745; color: white; padding: 4px 10px; border-radius: 8px; font-size: 12px;">✅ Active</span>', 
                           unsafe_allow_html=True)
        
        # Role badge
        role_colors = {
            "admin": "#dc3545",
            "datasets_admin": "#007bff",
            "cybersecurity_admin": "#fd7e14",
            "it_admin": "#6f42c1",
            "user": "#28a745"
        }
        color = role_colors.get(role, "gray")
        st.markdown(f'<span style="background-color: {color}; color: white; padding: 3px 10px; border-radius: 8px; font-size: 11px; margin-top: 5px; display: inline-block;">{role}</span>', 
                   unsafe_allow_html=True)
        
        if is_locked:
            st.caption(f"⚠️ Locked until: {locked_until}")
        
        st.markdown("")  # Small spacing
        
        # Action buttons in a cleaner layout
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Role dropdown
            new_role = st.selectbox(
                "Change Role",
                ["user", "admin", "datasets_admin", "cybersecurity_admin", "it_admin"],
                index=["user", "admin", "datasets_admin", "cybersecurity_admin", "it_admin"].index(role),
                key=f"role_{username}"
            )
        
        with col2:
            # Save role button
            st.markdown("<br>", unsafe_allow_html=True)  # Align with dropdown
            if st.button("💾 Save Role", key=f"save_{username}", use_container_width=True):
                if users_mod.update_user(username, role=new_role):
                    st.success(f"Updated role to {new_role}")
                    st.rerun()
                else:
                    st.error("Failed to update role")
        
        with col3:
            # Unlock or Lock button
            st.markdown("<br>", unsafe_allow_html=True)  # Align with dropdown
            if is_locked:
                if st.button("🔓 Unlock", key=f"unlock_{username}", use_container_width=True):
                    if users_mod.update_user(username, failed_attempts=0, locked_until=""):
                        st.success(f"Unlocked {username}")
                        st.rerun()
                    else:
                        st.error("Failed to unlock user")
            else:
                # Show Lock button only if not current user
                if username != st.session_state.get("username"):
                    if st.button("🔒 Lock", key=f"lock_{username}", use_container_width=True):
                        from datetime import timedelta
                        lock_until = (datetime.now() + timedelta(hours=24)).isoformat()
                        if users_mod.update_user(username, locked_until=lock_until):
                            st.success(f"Locked {username} for 24 hours")
                            st.rerun()
                        else:
                            st.error("Failed to lock user")
                else:
                    st.info("Your account")
        
        # Delete button on its own row (only if not current user and not locked)
        if username != st.session_state.get("username") and not is_locked:
            st.markdown("")  # Small spacing
            if st.button("🗑️ Delete User", key=f"delete_{username}", type="secondary", use_container_width=True):
                if users_mod.delete_user(username):
                    st.success(f"Deleted user {username}")
                    st.rerun()
                else:
                    st.error("Failed to delete user")
        
        # Simple separator between users
        st.markdown("---")


def show_system_overview(datasets_mod, incidents_mod, tickets_mod):
    """System overview section"""
    
    st.header("📊 System Overview")
    
    # Get counts from each domain
    total_datasets = 0
    total_incidents = 0
    total_tickets = 0
    
    if datasets_mod:
        try:
            analytics = datasets_mod.get_all_analytics()
            total_datasets = analytics.get('total_datasets', 0)
        except:
            pass
    
    if incidents_mod:
        try:
            analytics = incidents_mod.get_all_incident_analytics()
            total_incidents = analytics.get('total_incidents', 0)
        except:
            pass
    
    if tickets_mod:
        try:
            analytics = tickets_mod.get_all_ticket_analytics()
            total_tickets = analytics.get('total_tickets', 0)
        except:
            pass
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("📁 Total Datasets", total_datasets)
    col2.metric("🔒 Total Incidents", total_incidents)
    col3.metric("🎫 Total Tickets", total_tickets)
    
    st.markdown("---")
    st.info("💡 Use the domain dashboards for detailed analytics and visualizations.")


def show_database_info(csv_loader_mod):
    """Database information section"""
    
    st.header("🗄️ Database Information")
    
    if csv_loader_mod:
        try:
            # Show table record counts
            st.subheader("Table Record Counts")
            
            tables = ["users", "datasets_metadata", "cyber_incidents", "it_tickets", "sessions"]
            
            for table in tables:
                try:
                    count = csv_loader_mod.count_table_records(table)
                    st.write(f"**{table}**: {count} records")
                except:
                    st.write(f"**{table}**: Unable to count")
        
        except Exception as e:
            st.error(f"Error fetching database info: {e}")
    else:
        st.error("CSV loader module not available")