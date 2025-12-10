# pages/tickets_view.py
"""
IT Tickets view 
Everything passed as parameters to avoid circular imports.
"""
import streamlit as st
import pandas as pd
import plotly.express as px


def tickets_view(
    tickets_mod=None,
    csv_loader_mod=None,
    safe_df=None,
    small_stat_col_layout=None,
    add_ticket_form_func=None,
    ai_insights_for=None
):
    """IT Tickets view that accepts ALL dependencies as parameters."""
    
    st.subheader("IT Tickets – Support Tracking")

    # check if required modules are available
    if tickets_mod is None:
        st.error("Tickets module not available")
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
    with st.expander("📤 Upload CSV of Tickets", expanded=False):
        st.markdown("""
        **Expected CSV columns:** 
        - `ticket_id` (required), `priority`, `status`, `description`, `assigned_to`, `created_at`, `resolution_time_hours`
        """)
        uploaded_file = st.file_uploader(
            "Choose CSV file with tickets", 
            type=['csv'],
            key="ticket_upload"
        )

        if uploaded_file is not None:
            df_preview = pd.read_csv(uploaded_file)
            st.subheader("CSV Preview")
            st.dataframe(df_preview.head(5))
            st.caption(f"Total rows: {len(df_preview)}, Columns: {len(df_preview.columns)}")

            if st.button("Upload Tickets", key="upload_ticket_btn"):
                with st.spinner("Processing tickets..."):
                    # import here to avoid circular dependency
                    from models.csv_loader import handle_csv_upload
                    success, message = handle_csv_upload(
                        uploaded_file, 
                        "IT Tickets", 
                        st.session_state.username
                    )
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

    # add ticket form
    if add_ticket_form_func:
        add_ticket_form_func(tickets_mod=tickets_mod)

    # fetch analytics using OOP model
    try:
        # create model instance and get analytics using new OOP style
        ticket_model = tickets_mod.TicketModel()
        analytics = ticket_model.get_analytics()
        resolution_stats = ticket_model.get_resolution_stats()
    except Exception as e:
        st.error(f"Error getting analytics: {e}")
        analytics = {}
        resolution_stats = {}

    total_tickets = analytics.get("total_tickets", 0)
    open_tickets = analytics.get("open_tickets", 0)
    by_priority = analytics.get("by_priority", {})
    by_status = analytics.get("by_status", {})
    avg_resolution = resolution_stats.get("avg_resolution_days", 0)

    # KPIs
    small_stat_col_layout(
        [total_tickets, open_tickets, f"{avg_resolution:.1f}d"], 
        ["Total Tickets", "Open Tickets", "Avg Resolution Time"]
    )

    # bar chart: tickets by priority
    st.markdown("### Tickets by Priority (bar chart)")
    if by_priority:
        priority_df = pd.DataFrame({
            "priority": list(by_priority.keys()), 
            "count": list(by_priority.values())
        })
        fig_bar = px.bar(
            priority_df.sort_values("count"), 
            x="count", 
            y="priority", 
            orientation="h",
            labels={"count": "Count", "priority": "Priority"}, 
            title="Tickets by Priority"
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No priority data available.")

    # pie chart: tickets by priority
    st.markdown("### Tickets by Priority (pie chart)")
    if by_priority:
        pie_df = pd.DataFrame({
            "priority": list(by_priority.keys()), 
            "count": list(by_priority.values())
        })
        fig_pie = px.pie(
            pie_df, 
            names="priority", 
            values="count", 
            title="Ticket Priority Distribution", 
            hole=0.0
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No priority data available.")

    # bar chart: tickets by status
    st.markdown("### Tickets by Status (bar chart)")
    if by_status:
        status_df = pd.DataFrame({
            "status": list(by_status.keys()), 
            "count": list(by_status.values())
        })
        fig_status = px.bar(
            status_df.sort_values("count"), 
            x="count", 
            y="status", 
            orientation="h",
            labels={"count": "Count", "status": "Status"}, 
            title="Tickets by Status"
        )
        st.plotly_chart(fig_status, use_container_width=True)
    else:
        st.info("No status data available.")

    # filters and ticket table
    st.markdown("### Filter Tickets")
    fcol1, fcol2 = st.columns(2)
    priority_filter = fcol1.selectbox(
        "Priority", 
        options=[""] + ticket_model.VALID_PRIORITIES
    )
    status_filter = fcol2.selectbox(
        "Status", 
        options=[""] + ticket_model.VALID_STATUSES
    )

    try:
        # use OOP model to filter tickets
        df_tickets = ticket_model.filter_by(
            priority=(priority_filter or None),
            status=(status_filter or None),
            as_dataframe=True
        )
    except Exception as e:
        st.error(f"Error fetching tickets: {e}")
        df_tickets = pd.DataFrame()

    df_tickets = safe_df(df_tickets)
    if not df_tickets.empty:
        st.dataframe(df_tickets)
        
        # delete functionality (only for admins and it_admins)
        user_role = st.session_state.get("user_role", "user")
        if user_role in ["admin", "it_admin"]:
            st.markdown("---")
            st.subheader("🗑️ Delete Ticket")
            ticket_ids = df_tickets['id'].tolist()
            selected_id = st.selectbox("Select ticket to delete", ticket_ids,
                                      format_func=lambda x: f"ID {x}: {df_tickets[df_tickets['id']==x]['ticket_id'].values[0]}")
            
            if st.button("🗑️ Delete Selected Ticket", type="secondary"):
                try:
                    # use OOP model to delete
                    if ticket_model.delete(selected_id):
                        st.success(f"Deleted ticket {selected_id}")
                        st.rerun()
                    else:
                        st.error("Failed to delete ticket")
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.info("No tickets match the filters.")

    # AI insights section
    if not df_tickets.empty and ai_insights_for:
        st.markdown("---")
        st.markdown("### 🤖 AI Analysis")
        
        # create ticket labels for dropdown
        labels = [
            f"{r.get('ticket_id', 'N/A')}: {str(r.get('description', ''))[:40]}... - {r.get('priority', '')}" 
            for _, r in df_tickets.iterrows()
        ]
        
        # selectbox to choose ticket
        sel_idx = st.selectbox(
            "Choose ticket for AI analysis", 
            options=list(range(len(labels))), 
            format_func=lambda i: labels[i], 
            key="ai_ticket_select"
        )
        
        # get the selected ticket as a dictionary
        selected_ticket = df_tickets.iloc[sel_idx].to_dict()
        
        # button to generate AI insights
        if st.button("🧠 Generate AI Insights", key=f"ai_ticket_btn_{sel_idx}"):
            with st.spinner("🔍 Analyzing ticket with AI..."):
                insights = ai_insights_for(selected_ticket, domain="IT Tickets")
                
                if insights:
                    st.markdown("#### 💡 AI Analysis Results")
                    st.info(insights)
                else:
                    st.warning("No insights generated.")
    
    elif not df_tickets.empty and ai_insights_for is None:
        st.info("💡 AI insights feature is not available.")
