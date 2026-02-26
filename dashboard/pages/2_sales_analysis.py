"""
Sales Analysis Page - Salesperson & Customer Insights

Detailed analysis of salesperson performance and customer segments.
"""
import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dashboard.utils.data_loader import load_sales_data
from dashboard.utils.data_processor import (
    filter_dataframe,
    calculate_salesperson_metrics,
    calculate_customer_metrics
)
from dashboard.components.filters import render_filters
from dashboard.components.charts import (
    plot_salesperson_performance,
    plot_customer_distribution,
    plot_stage_distribution
)

st.set_page_config(page_title="Sales Analysis", page_icon="🤝", layout="wide")

st.title("🤝 Sales Analysis")
st.markdown("Deep dive into salesperson performance and customer insights")

# Load and filter data
df = load_sales_data()
operations, salespeople, years, value_range = render_filters(df)
filtered_df = filter_dataframe(df, operations, salespeople, years, value_range)

# Tabs for different analyses
tab1, tab2, tab3 = st.tabs(["👤 Salesperson Performance", "👥 Customer Analysis", "🔄 Workflow Stages"])

with tab1:
    st.header("Salesperson Performance Metrics")

    # Chart
    top_n = st.slider("Number of salespeople to display", 5, 30, 15, key="sales_slider")
    fig = plot_salesperson_performance(filtered_df, top_n=top_n)
    st.plotly_chart(fig)

    # Detailed table
    st.subheader("Detailed Metrics by Salesperson")
    sp_metrics = calculate_salesperson_metrics(filtered_df)

    # Format currency columns
    sp_metrics['Total Revenue'] = sp_metrics['Total Revenue'].apply(lambda x: f"R$ {x:,.2f}")
    sp_metrics['Avg Sale Value'] = sp_metrics['Avg Sale Value'].apply(lambda x: f"R$ {x:,.2f}")

    st.dataframe(
        sp_metrics,
        hide_index=True,
        height=600
    )

    # Download button
    csv = sp_metrics.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Download Salesperson Metrics",
        data=csv,
        file_name="salesperson_metrics.csv",
        mime="text/csv"
    )

with tab2:
    st.header("Customer Segmentation Analysis")

    # Chart
    top_n_cust = st.slider("Number of customers to display", 10, 50, 20, key="cust_slider")
    fig = plot_customer_distribution(filtered_df, top_n=top_n_cust)
    st.plotly_chart(fig)

    # Detailed table
    st.subheader("Detailed Metrics by Customer")
    cust_metrics = calculate_customer_metrics(filtered_df)

    # Format currency columns
    cust_metrics['Total Revenue'] = cust_metrics['Total Revenue'].apply(lambda x: f"R$ {x:,.2f}")
    cust_metrics['Avg Purchase Value'] = cust_metrics['Avg Purchase Value'].apply(lambda x: f"R$ {x:,.2f}")

    # Truncate long customer names
    cust_metrics['Customer'] = cust_metrics['Customer'].str[:60]

    st.dataframe(
        cust_metrics,
        hide_index=True,
        height=600
    )

    # Download button
    csv = cust_metrics.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Download Customer Metrics",
        data=csv,
        file_name="customer_metrics.csv",
        mime="text/csv"
    )

with tab3:
    st.header("Workflow Stage Distribution")

    fig = plot_stage_distribution(filtered_df)
    st.plotly_chart(fig)

    # Stage summary table
    stage_summary = filtered_df.groupby('etapa_tag_ids').agg({
        'numero': 'nunique',
        'vr_nf': 'sum'
    }).reset_index()

    stage_summary.columns = ['Workflow Stage', 'Unique Orders', 'Total Revenue']
    stage_summary = stage_summary.sort_values('Total Revenue', ascending=False)
    stage_summary['Total Revenue'] = stage_summary['Total Revenue'].apply(lambda x: f"R$ {x:,.2f}")

    st.dataframe(
        stage_summary,
        hide_index=True,
    )
