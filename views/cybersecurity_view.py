# pages/cybersecurity_view.py
"""
Cybersecurity view - NO top-level imports of other project modules.
Everything passed as parameters to avoid circular imports.
"""
import streamlit as st
import pandas as pd
import plotly.express as px


def cybersecurity_view(
    incidents_mod=None,
    csv_loader_mod=None,
    safe_df=None,
    small_stat_col_layout=None,
    add_incident_form_func=None,
    ai_insights_for=None
):
    """Cybersecurity view that accepts ALL dependencies as parameters."""
    
    st.subheader("Cybersecurity – Incidents")

    # check if required modules are available
    if incidents_mod is None:
        st.error("Incidents module not available")
        return
    
    # create default helpers if not provided
    if safe_df is None:
        def safe_df(obj):
            try:
                return pd.DataFrame(obj) if obj is not None else pd.DataFrame()
            except:
                return pd.DataFrame()
    
    if small_stat_col_layout is None:
        def small_stat_col_layout(values, labels):
            if not values or not labels:
                return
            cols = st.columns(len(values))
            for col, value, label in zip(cols, values, labels):
                col.metric(label, value)
    
    # CSV upload section
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
                    # import here to avoid circular dependency
                    from models.csv_loader import handle_csv_upload
                    success, message = handle_csv_upload(
                        uploaded_file, 
                        "Cybersecurity", 
                        st.session_state.username
                    )
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

    # add incident form
    default_reporter = st.session_state.username or ""
    if add_incident_form_func:
        add_incident_form_func(default_reported_by=default_reporter, incidents_mod=incidents_mod)

    # fetch analytics using OOP model
    try:
        # create model instance and get analytics using new OOP style
        incident_model = incidents_mod.IncidentModel()
        analytics = incident_model.get_analytics()
    except Exception as e:
        st.error(f"Error getting analytics: {e}")
        analytics = {}

    total_inc = analytics.get("total_incidents", 0)
    open_inc = analytics.get("open_incidents", 0)
    by_sev = analytics.get("by_severity", {})
    by_status = analytics.get("by_status", {})

    # KPIs
    small_stat_col_layout([total_inc, open_inc], ["Total incidents", "Open incidents"])

    # bar chart: incidents by severity
    st.markdown("### Incidents by severity (bar chart)")
    if by_sev:
        sev_df = pd.DataFrame({"severity": list(by_sev.keys()), "count": list(by_sev.values())})
        fig_bar = px.bar(sev_df.sort_values("count"), x="count", y="severity", orientation="h",
                         labels={"count": "Count", "severity": "Severity"}, 
                         title="Incidents by Severity")
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No severity data available.")

    # pie chart: incidents by severity
    st.markdown("### Incidents by severity (pie chart)")
    if by_sev:
        pie_df = pd.DataFrame({"severity": list(by_sev.keys()), "count": list(by_sev.values())})
        fig_pie = px.pie(pie_df, names="severity", values="count", 
                        title="Incident Severity Distribution", hole=0.0)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No severity data available.")

    # bar chart: incidents by status
    st.markdown("### Incidents by status (bar chart)")
    if by_status:
        status_df = pd.DataFrame({"status": list(by_status.keys()), "count": list(by_status.values())})
        fig_status = px.bar(status_df.sort_values("count"), x="count", y="status", orientation="h",
                            labels={"count": "Count", "status": "Status"}, 
                            title="Incidents by Status")
        st.plotly_chart(fig_status, use_container_width=True)
    else:
        st.info("No status data available.")

    # filters and incident table
    st.markdown("### Filter incidents")
    fcol1, fcol2, fcol3 = st.columns(3)
    sev = fcol1.selectbox("Severity", options=[""] + incident_model.VALID_SEVERITIES)
    stat = fcol2.selectbox("Status", options=[""] + incident_model.VALID_STATUSES)
    inc_type = fcol3.text_input("Incident type (exact match)")

    try:
        # use OOP model to filter incidents
        df_inc = incident_model.filter_by(
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
        
        # delete functionality (only for admins and cybersecurity_admins)
        user_role = st.session_state.get("user_role", "user")
        if user_role in ["admin", "cybersecurity_admin"]:
            st.markdown("---")
            st.subheader("🗑️ Delete Incident")
            incident_ids = df_inc['id'].tolist()
            selected_id = st.selectbox("Select incident to delete", incident_ids, 
                                      format_func=lambda x: f"ID {x}: {df_inc[df_inc['id']==x]['category'].values[0]}")
            
            if st.button("🗑️ Delete Selected Incident", type="secondary"):
                try:
                    # use OOP model to delete
                    if incident_model.delete(selected_id):
                        st.success(f"Deleted incident {selected_id}")
                        st.rerun()
                    else:
                        st.error("Failed to delete incident")
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.info("No incidents match the filters.")

    # AI insights section
    if not df_inc.empty and ai_insights_for:
        st.markdown("---")
        st.markdown("### 🤖 AI Analysis")
        
        # create incident labels for dropdown
        labels = [f"{int(r['id'])}: {r.get('category','')[:30]} - {r.get('severity','')}" 
                 for _, r in df_inc.iterrows()]
        
        # selectbox to choose incident
        sel_idx = st.selectbox(
            "Choose incident for AI analysis", 
            options=list(range(len(labels))), 
            format_func=lambda i: labels[i], 
            key="ai_incident_select"
        )
        
        # get the selected incident as a dictionary
        selected_incident = df_inc.iloc[sel_idx].to_dict()
        
        # display incident details
        with st.expander("📋 Selected Incident Details", expanded=False):
            st.write(selected_incident)
        
        # button to generate AI insights
        if st.button("🧠 Generate AI Insights", key=f"ai_incident_btn_{sel_idx}"):
            with st.spinner("🔍 Analyzing incident with AI..."):
                insights = ai_insights_for(selected_incident, domain="Cybersecurity")
                
                if insights:
                    st.markdown("#### 💡 AI Analysis Results")
                    st.info(insights)
                else:
                    st.warning("No insights generated.")
    
    elif not df_inc.empty and ai_insights_for is None:
        st.info("💡 AI insights feature is not available.")
