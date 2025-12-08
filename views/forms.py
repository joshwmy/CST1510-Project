# forms.py
"""
Reusable form components for creating entities.
NO TOP-LEVEL IMPORTS of domain modules to avoid circular dependencies.
"""
import streamlit as st
import time
from datetime import date


def add_incident_form(default_reported_by: str = "", incidents_mod=None):
    """Form for creating incidents. Modules passed as parameters."""
    if incidents_mod is None:
        st.warning("Incidents backend unavailable.")
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


def add_ticket_form(default_reported_by: str = "", tickets_mod=None):
    """Form for creating IT tickets. Modules passed as parameters."""
    if tickets_mod is None:
        st.warning("Tickets backend unavailable.")
        return False, "Tickets backend unavailable."

    with st.expander("➕ Add new ticket", expanded=False):
        with st.form("new_ticket_form"):
            subject = st.text_input("Ticket subject/title")
            category = st.text_input("Category (e.g., Software, Hardware, Network)", value="General")
            priorities = getattr(tickets_mod, "VALID_PRIORITIES", ["Low", "Medium", "High", "Critical"])
            priority = st.selectbox("Priority", options=priorities)
            statuses = getattr(tickets_mod, "VALID_STATUSES", ["Open", "In Progress", "Resolved", "Closed"])
            status = st.selectbox("Status", options=statuses, index=0)
            description = st.text_area("Description", height=120)
            assigned_to = st.text_input("Assigned to (optional)")
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
                        st.error("Failed to create ticket (database error).")
                        return False, "db_error"
                    st.success(f"Ticket created successfully (ID {new_id}).")
                    return True, new_id
                except Exception as e:
                    st.error(f"Error creating ticket: {e}")
                    return False, str(e)
    return False, "not_submitted"


def add_dataset_form(default_uploaded_by: str = "", datasets_mod=None):
    """Form for creating datasets. Modules passed as parameters."""
    if datasets_mod is None:
        st.warning("Datasets backend unavailable.")
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