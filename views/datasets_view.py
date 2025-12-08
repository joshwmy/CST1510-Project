# pages/datasets_view.py
"""
Datasets view - NO top-level imports of other project modules.
Everything passed as parameters to avoid circular imports.
"""
import streamlit as st
import pandas as pd
import plotly.express as px


def datasets_view(
    datasets_mod=None,
    csv_loader_mod=None,
    safe_df=None,
    small_stat_col_layout=None,
    add_dataset_form_func=None,
    ai_insights_for=None
):
    """Datasets view that accepts ALL dependencies as parameters."""
    
    st.subheader("Datasets – Data Management")

    # Check if required modules are available
    if datasets_mod is None:
        st.error("Datasets module not available")
        return
    
    # Create default helpers if not provided
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
    
    # CSV Upload Section
    with st.expander("📤 Upload Dataset (CSV)", expanded=False):
        st.markdown("""
        **Upload any CSV file as a dataset**
        - The system will automatically detect columns and data types
        - Metadata will be stored for tracking
        """)
        uploaded_file = st.file_uploader(
            "Choose CSV file", 
            type=['csv'],
            key="dataset_upload"
        )

        if uploaded_file is not None:
            df_preview = pd.read_csv(uploaded_file)
            st.subheader("CSV Preview")
            st.dataframe(df_preview.head(10))
            st.caption(f"Total rows: {len(df_preview)}, Columns: {len(df_preview.columns)}")

            if st.button("Upload Dataset", key="upload_dataset_btn"):
                with st.spinner("Processing dataset..."):
                    # Import here to avoid circular dependency
                    from models.csv_loader import handle_csv_upload
                    success, message = handle_csv_upload(
                        uploaded_file, 
                        "Datasets", 
                        st.session_state.username
                    )
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

    # Add dataset form (if available)
    if add_dataset_form_func:
        add_dataset_form_func(datasets_mod=datasets_mod)

    # Fetch analytics from backend
    try:
        analytics = datasets_mod.get_all_analytics()
    except Exception as e:
        st.error(f"Error getting analytics: {e}")
        analytics = {}

    total_datasets = analytics.get("total_datasets", 0)
    total_rows = analytics.get("total_rows", 0)
    by_uploader = analytics.get("by_uploaded_by", {})

    # KPIs - removed total_columns as it's not in the analytics
    small_stat_col_layout(
        [total_datasets, total_rows], 
        ["Total Datasets", "Total Rows"]
    )

    # Bar chart: datasets by uploader
    st.markdown("### Datasets by Uploader")
    if by_uploader:
        uploader_df = pd.DataFrame({
            "uploader": list(by_uploader.keys()), 
            "count": list(by_uploader.values())
        })
        fig_bar = px.bar(
            uploader_df.sort_values("count"), 
            x="count", 
            y="uploader", 
            orientation="h",
            labels={"count": "Count", "uploader": "Uploader"}, 
            title="Datasets by Uploader"
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No uploader data available.")

    # Pie chart: datasets by uploader
    st.markdown("### Dataset Distribution by Uploader")
    if by_uploader:
        pie_df = pd.DataFrame({
            "uploader": list(by_uploader.keys()), 
            "count": list(by_uploader.values())
        })
        fig_pie = px.pie(
            pie_df, 
            names="uploader", 
            values="count", 
            title="Dataset Upload Distribution", 
            hole=0.0
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No uploader data available.")

    # All datasets table
    st.markdown("### All Datasets")
    try:
        df_datasets = datasets_mod.get_all_datasets(as_dataframe=True)
    except Exception as e:
        st.error(f"Error fetching datasets: {e}")
        df_datasets = pd.DataFrame()

    df_datasets = safe_df(df_datasets)
    if not df_datasets.empty:
        st.dataframe(df_datasets)
        
        # Delete functionality (only for admins and datasets_admins)
        user_role = st.session_state.get("user_role", "user")
        if user_role in ["admin", "datasets_admin"]:
            st.markdown("---")
            st.subheader(" Delete Dataset")
            dataset_ids = df_datasets['id'].tolist()
            selected_id = st.selectbox("Select dataset to delete", dataset_ids,
                                      format_func=lambda x: f"ID {x}: {df_datasets[df_datasets['id']==x]['name'].values[0]}")
            
            if st.button(" Delete Selected Dataset", type="secondary"):
                try:
                    if datasets_mod.delete_dataset(selected_id):
                        st.success(f"Deleted dataset {selected_id}")
                        st.rerun()
                    else:
                        st.error("Failed to delete dataset")
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.info("No datasets found.")

    # AI Insights (Datasets) - NEW SECTION
    if not df_datasets.empty and ai_insights_for:
        st.markdown("---")
        st.markdown("### 🤖 AI Analysis")
        
        # Create dataset labels for dropdown
        labels = [
            f"ID {r.get('id', 'N/A')}: {r.get('name', 'Unnamed')} ({r.get('rows', 0)} rows × {r.get('columns', 0)} cols)" 
            for _, r in df_datasets.iterrows()
        ]
        
        # Selectbox to choose dataset
        sel_idx = st.selectbox(
            "Choose dataset for AI analysis", 
            options=list(range(len(labels))), 
            format_func=lambda i: labels[i], 
            key="ai_dataset_select"
        )
        
        # Get the selected dataset as a dictionary
        selected_dataset = df_datasets.iloc[sel_idx].to_dict()
        
        # Display dataset details
        with st.expander("📋 Selected Dataset Details", expanded=False):
            st.write(selected_dataset)
        
        # Button to generate AI insights
        if st.button("🧠 Generate AI Insights", key=f"ai_dataset_btn_{sel_idx}"):
            with st.spinner("🔍 Analyzing dataset with AI..."):
                insights = ai_insights_for(selected_dataset, domain="Datasets")
                
                if insights:
                    st.markdown("#### 💡 AI Analysis Results")
                    st.info(insights)
                else:
                    st.warning("No insights generated.")
    
    elif not df_datasets.empty and ai_insights_for is None:
        st.info("💡 AI insights feature is not available.")