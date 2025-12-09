# main.py
"""
Streamlit app main router for Multi-Domain Intelligence Platform.
FIXED: Added debug output for import failures
"""
import streamlit as st
import pandas as pd
import sys
import os
from importlib import import_module

# Make sure project root is on sys.path
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.append(ROOT)

# Backend module placeholders
csv_loader_mod = datasets_mod = incidents_mod = tickets_mod = users_mod = None
user_service_mod = None

# View & helper placeholders
datasets_view_func = tickets_view_func = cybersecurity_view_func = None
add_dataset_form_func = add_ticket_form_func = add_incident_form_func = None
admin_panel_func = is_user_admin_func = None
ai_insights_for = None

def try_import(module_path: str, attr: str = None):
    """Try to import a module or attribute; return (obj, None) on success else (None, err)."""
    try:
        if attr:
            mod = import_module(module_path)
            return getattr(mod, attr), None
        else:
            return import_module(module_path), None
    except Exception as e:
        return None, e

# Try canonical app.* paths first, then fallback to models/ services layout
candidates = [
    ("models.csv_loader", None),
    ("models.datasets", None),
    ("models.incidents", None),
    ("models.tickets", None),
    ("models.users", None),
    ("services.user_service", None),
]

# Map names to variables
import_map = {
    "models.csv_loader": "csv_loader_mod",
    "models.datasets": "datasets_mod",
    "models.incidents": "incidents_mod",
    "models.tickets": "tickets_mod",
    "models.users": "users_mod",
    "services.user_service": "user_service_mod",
}

# Perform imports WITH ERROR REPORTING
import_errors = []
for path, _ in candidates:
    obj, err = try_import(path)
    if obj:
        globals()[import_map[path]] = obj
        print(f"✅ Loaded: {path}")  # debug output
    else:
        error_msg = f"Failed to load {path}: {err}"
        import_errors.append(error_msg)
        print(f"❌ {error_msg}")  # debug output

# Try importing views and forms
views_to_try = [
    ("views.datasets_view", "datasets_view"),
    ("views.tickets_view", "tickets_view"),
    ("views.cybersecurity_view", "cybersecurity_view"),
    ("views.admin_view", "admin_panel"),
    ("views.admin_view", "is_user_admin"),
    ("views.forms", "add_dataset_form"),
    ("views.forms", "add_ticket_form"),
    ("views.forms", "add_incident_form"),
    ("services.ai_services", "ai_insights_for"),
]

for module_path, attr in views_to_try:
    obj, err = try_import(module_path, attr)
    if obj:
        if attr == "datasets_view":
            datasets_view_func = obj
        elif attr == "tickets_view":
            tickets_view_func = obj
        elif attr == "cybersecurity_view":
            cybersecurity_view_func = obj
        elif attr == "admin_panel":
            admin_panel_func = obj
        elif attr == "is_user_admin":
            is_user_admin_func = obj
        elif attr == "add_dataset_form":
            add_dataset_form_func = obj
        elif attr == "add_ticket_form":
            add_ticket_form_func = obj
        elif attr == "add_incident_form":
            add_incident_form_func = obj
        elif attr == "ai_insights_for":
            ai_insights_for = obj
        print(f"✅ Loaded: {module_path}.{attr}")
    else:
        print(f"⚠️ Could not load {module_path}.{attr}: {err}")

# -------------------------
# Page config & session setup
# -------------------------
st.set_page_config(
    page_title="Multi-Domain Intelligence Platform", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Show import errors in UI if any critical modules failed
if import_errors:
    with st.sidebar:
        with st.expander("⚠️ Import Issues", expanded=False):
            for err in import_errors:
                st.warning(err)
            st.info("Some features may not work correctly")

for k, default in [
    ("logged_in", False),
    ("username", ""),
    ("session_token", None),
    ("current_page", "home"),
    ("current_domain", "Datasets"),
    ("user_role", "user"),
]:
    if k not in st.session_state:
        st.session_state[k] = default

# -------------------------
# Helpers
# -------------------------
def safe_df(obj) -> pd.DataFrame:
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
    if not values or not labels:
        return
    cols = st.columns(len(values))
    for col, value, label in zip(cols, values, labels):
        col.metric(label, value)

def check_authentication():
    if not st.session_state.logged_in:
        return False
    if user_service_mod and st.session_state.session_token:
        try:
            session_info = user_service_mod.get_session(st.session_state.session_token)
            if not session_info:
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.session_state.session_token = None
                st.session_state.user_role = "user"
                return False
            return True
        except Exception:
            pass
    return st.session_state.logged_in

def get_user_role():
    """Helper function to get the current user's role from the database"""
    if not st.session_state.logged_in or not st.session_state.username:
        return "user"
    
    # First check session state
    if st.session_state.user_role and st.session_state.user_role != "user":
        return st.session_state.user_role
    
    # Then check database via users module
    if users_mod:
        try:
            user_data = users_mod.get_user_by_username(st.session_state.username)
            if user_data:
                role = user_data.get("role") if isinstance(user_data, dict) else user_data[3]
                st.session_state.user_role = role  # Update session state
                return role
        except Exception as e:
            print(f"Error getting user role: {e}")
    
    return "user"

# -------------------------
# UI pages
# -------------------------
def show_home_page():
    st.title("Welcome – Sign in / Register")

    if user_service_mod is None:
        st.warning("Authentication service is not available. Running in demo mode.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Login as Demo User"):
                st.session_state.logged_in = True
                st.session_state.username = "demo_user"
                st.session_state.user_role = "user"
                st.session_state.current_page = "dashboard"
                st.rerun()
        with col2:
            if st.button("Login as Demo Admin"):
                st.session_state.logged_in = True
                st.session_state.username = "demo_admin"
                st.session_state.user_role = "admin"
                st.session_state.current_page = "dashboard"
                st.rerun()
        return

    # If already logged in and session is valid
    if st.session_state.logged_in and st.session_state.session_token:
        try:
            sess = user_service_mod.get_session(st.session_state.session_token)
            if sess:
                st.success(f"Signed in as **{st.session_state.username}**")
                if st.button("Go to Dashboard"):
                    st.session_state.current_page = "dashboard"
                    st.rerun()
                if st.button("Logout"):
                    try:
                        user_service_mod.invalidate_session(st.session_state.session_token)
                    except:
                        pass
                    st.session_state.logged_in = False
                    st.session_state.username = ""
                    st.session_state.session_token = None
                    st.session_state.user_role = "user"
                    st.rerun()
                return
        except:
            pass

    tab1, tab2 = st.tabs(["Sign In", "Register"])

    with tab1:
        st.subheader("Sign In")
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")

        if st.button("Sign In"):
            if not (login_username and login_password):
                st.error("Both fields are required.")
            else:
                try:
                    result = user_service_mod.login_user(login_username, login_password)
                    if result["success"]:
                        st.session_state.logged_in = True
                        st.session_state.username = login_username
                        st.session_state.session_token = result["session_token"]
                        user_info = result.get("user_data", {})
                        st.session_state.user_role = user_info.get("role", "user")
                        st.session_state.current_page = "dashboard"
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error(result["message"])
                except Exception as e:
                    st.error(f"Login error: {e}")

    with tab2:
        st.subheader("Create Account")
        reg_username = st.text_input("Choose Username", key="reg_username")
        reg_password = st.text_input("Choose Password", type="password", key="reg_password")
        reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")

        st.markdown("**Password Requirements:** 8-50 chars, 1 uppercase, 1 number, 1 special char")
        if st.button("Create Account"):
            if not (reg_username and reg_password and reg_confirm):
                st.error("All fields are required.")
            elif reg_password != reg_confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    ok_user, user_msg = user_service_mod.validate_username(reg_username)
                    if not ok_user:
                        st.error(user_msg)
                        return
                    ok_pass, pass_msg = user_service_mod.validate_password(reg_password)
                    if not ok_pass:
                        st.error(pass_msg)
                        return
                    created = user_service_mod.register_user(reg_username, reg_password, role="user")
                    if created:
                        st.success("Account created. Please sign in.")
                        st.rerun()
                    else:
                        st.error("Registration failed (username may exist).")
                except Exception as e:
                    st.error(f"Registration error: {e}")

def show_fallback_view(domain):
    st.subheader(f"{domain} - Basic view")
    st.info("Full view not available.")
    st.write("Quick actions:")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button(f"Add {domain[:-1]}"):
            st.info("Add action placeholder")
    with c2:
        if st.button(f"View all {domain}"):
            st.info("View action placeholder")
    with c3:
        if st.button("Generate report"):
            st.info("Generate placeholder")
    sample_data = {"ID": [1,2,3], "Name": [f"Sample {domain[:-1]} A", "B", "C"]}
    st.dataframe(pd.DataFrame(sample_data))

def show_dashboard():
    if not check_authentication():
        st.error("Sign in required to access dashboard.")
        if st.button("Go to Sign In"):
            st.session_state.current_page = "home"
            st.rerun()
        return

    domain = st.session_state.current_domain
    st.title(f"{domain} Dashboard")
    st.caption(f"Welcome, {st.session_state.username} (Role: {st.session_state.user_role})")

    # Logout button
    _, _, c = st.columns([8, 1, 1])
    with c:
        if st.button("Logout"):
            try:
                if user_service_mod and st.session_state.session_token:
                    user_service_mod.invalidate_session(st.session_state.session_token)
            except Exception:
                pass
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.session_token = None
            st.session_state.user_role = "user"
            st.session_state.current_page = "home"
            st.rerun()

    # Route to domain view
    try:
        if domain == "Datasets":
            if datasets_view_func:
                datasets_view_func(
                    datasets_mod=datasets_mod,
                    csv_loader_mod=csv_loader_mod,
                    safe_df=safe_df,
                    small_stat_col_layout=small_stat_col_layout,
                    add_dataset_form_func=add_dataset_form_func,
                    ai_insights_for=ai_insights_for
                )
            else:
                show_fallback_view("Datasets")
        
        elif domain == "Cybersecurity":
            if cybersecurity_view_func:
                cybersecurity_view_func(
                    incidents_mod=incidents_mod,
                    csv_loader_mod=csv_loader_mod,
                    safe_df=safe_df,
                    small_stat_col_layout=small_stat_col_layout,
                    add_incident_form_func=add_incident_form_func,
                    ai_insights_for=ai_insights_for
                )
            else:
                show_fallback_view("Cybersecurity")
        
        elif domain == "IT Tickets":
            if tickets_view_func:
                tickets_view_func(
                    tickets_mod=tickets_mod,
                    csv_loader_mod=csv_loader_mod,
                    safe_df=safe_df,
                    small_stat_col_layout=small_stat_col_layout,
                    add_ticket_form_func=add_ticket_form_func,
                    ai_insights_for=ai_insights_for
                )
            else:
                show_fallback_view("IT Tickets")
        else:
            st.error(f"Unknown domain: {domain}")
    except Exception as e:
        st.error(f"Error loading {domain} view: {e}")
        import traceback
        with st.expander("Error details"):
            st.code(traceback.format_exc())

def render_sidebar():
    with st.sidebar:
        st.title("Intelligence Platform")
        st.markdown("---")
        
        if st.session_state.logged_in:
            pages = ["Dashboard", "Home"]
            
            # Check if user is main admin (only main admin can access admin panel)
            if st.session_state.get("user_role") == "admin":
                pages.append("Admin")
        else:
            pages = ["Home"]

        display = {"home": "Home", "dashboard": "Dashboard", "admin": "Admin"}
        curr_disp = display.get(st.session_state.current_page, "Home")
        if curr_disp not in pages:
            curr_disp = pages[0]
            st.session_state.current_page = {"Home":"home","Dashboard":"dashboard","Admin":"admin"}[curr_disp]

        selected = st.selectbox("Go to Page:", pages, index=pages.index(curr_disp))
        st.session_state.current_page = {"Home":"home","Dashboard":"dashboard","Admin":"admin"}[selected]

        if st.session_state.current_page == "dashboard":
            st.markdown("---")
            st.header("Domain")
            domains = ["Datasets", "Cybersecurity", "IT Tickets"]
            curr_dom = st.session_state.get("current_domain", "Datasets")
            sel = st.radio("Select Domain:", domains, index=domains.index(curr_dom) if curr_dom in domains else 0)
            st.session_state.current_domain = sel

        st.markdown("---")
        st.subheader("User")
        if st.session_state.logged_in:
            st.success(f"✅ Hello, {st.session_state.username}")
            st.caption(f"Role: {st.session_state.user_role}")
            
            # Better logout button
            if st.button("Sign Out", use_container_width=True, type="primary"):
                try:
                    if user_service_mod and st.session_state.session_token:
                        user_service_mod.invalidate_session(st.session_state.session_token)
                except Exception:
                    pass
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.session_state.user_role = "user"
                st.session_state.session_token = None
                st.session_state.current_page = "home"
                st.rerun()
        else:
            st.info("Not signed in")

# Main router
def main():
    render_sidebar()
    page = st.session_state.current_page
    
    if page == "home":
        show_home_page()
    elif page == "dashboard":
        show_dashboard()
    elif page == "admin":
        if not st.session_state.logged_in:
            st.error("Please sign in to access admin panel.")
            st.session_state.current_page = "home"
            st.rerun()
            return

        # Only main admin can access admin panel
        if st.session_state.get("user_role") != "admin":
            st.error("Access denied. Only main administrator can access this panel.")
            st.session_state.current_page = "dashboard"
            st.rerun()
            return

        if admin_panel_func:
            admin_panel_func(
                users_mod=users_mod,
                csv_loader_mod=csv_loader_mod,
                user_service_mod=user_service_mod,
                datasets_mod=datasets_mod,
                incidents_mod=incidents_mod,
                tickets_mod=tickets_mod
            )
        else:
            st.error("Admin panel not available.")
    else:
        st.error("Unknown page; returning home.")
        st.session_state.current_page = "home"
        st.rerun()

if __name__ == "__main__":
    main()
