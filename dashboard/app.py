"""
Odoo Sales Analytics Dashboard - Main Entry Point

Interactive Streamlit dashboard for exploring Odoo sales data.
Run with: streamlit run dashboard/app.py
"""
import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dashboard.utils.data_loader import load_sales_data, get_data_summary
from dashboard.utils.data_processor import filter_dataframe
from dashboard.components.filters import render_filters, render_reset_button
from dashboard.components.metrics import render_kpis, render_secondary_metrics
from dashboard.components.charts import (
    plot_operation_distribution,
    plot_salesperson_performance,
    plot_customer_distribution,
    plot_value_distribution
)

# Page configuration
st.set_page_config(
    page_title="Odoo Sales Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main():
    """Main dashboard application."""

    # Header
    st.title("📊 Odoo Sales Analytics Dashboard")
    st.markdown("Interactive dashboard for exploring sales data from Odoo ERP")

    # Load data
    with st.spinner("Loading sales data..."):
        df = load_sales_data()
        summary = get_data_summary(df)

    # Sidebar filters
    st.sidebar.image("https://via.placeholder.com/250x80/1f77b4/ffffff?text=Odoo+Sales")
    operations, salespeople, years, value_range = render_filters(df)
    render_reset_button()

    # Apply filters
    filtered_df = filter_dataframe(df, operations, salespeople, years, value_range)

    # Show filter impact
    if len(filtered_df) < len(df):
        st.info(f"📊 Showing {len(filtered_df):,} of {len(df):,} rows ({len(filtered_df)/len(df)*100:.1f}%)")

    # Main KPIs
    st.header("Key Performance Indicators")
    render_kpis(filtered_df)

    st.markdown("---")

    # Secondary metrics
    render_secondary_metrics(filtered_df)

    st.markdown("---")

    # Visualizations
    st.header("Sales Analysis")

    # Row 1: Operation distribution and Salesperson performance
    col1, col2 = st.columns(2)

    with col1:
        with st.container():
            fig_ops = plot_operation_distribution(filtered_df)
            st.plotly_chart(fig_ops)

    with col2:
        with st.container():
            fig_sales = plot_salesperson_performance(filtered_df, top_n=15)
            st.plotly_chart(fig_sales)

    st.markdown("---")

    # Row 2: Customer and Value distribution
    col1, col2 = st.columns(2)

    with col1:
        with st.container():
            fig_customers = plot_customer_distribution(filtered_df, top_n=15)
            st.plotly_chart(fig_customers)

    with col2:
        with st.container():
            fig_dist = plot_value_distribution(filtered_df)
            st.plotly_chart(fig_dist)

    st.markdown("---")

    # Data table
    st.header("Raw Data Explorer")

    with st.expander("🔍 View Detailed Data Table", expanded=False):
        # Add search functionality
        search_term = st.text_input("Search in data", "")

        if search_term:
            mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
            display_df = filtered_df[mask]
            st.info(f"Found {len(display_df)} rows matching '{search_term}'")
        else:
            display_df = filtered_df

        # Display options
        col1, col2 = st.columns([1, 3])
        with col1:
            rows_to_show = st.selectbox("Rows to display", [100, 500, 1000, 5000, "All"], index=0)

        if rows_to_show == "All":
            st.dataframe(display_df, height=600)
        else:
            st.dataframe(display_df.head(rows_to_show), height=600)

        # Download button
        csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Download Filtered Data as CSV",
            data=csv,
            file_name="odoo_sales_filtered.csv",
            mime="text/csv"
        )

    # Footer with data summary
    st.markdown("---")
    st.caption(f"""
    📊 Dataset Summary: {summary['total_rows']:,} total rows |
    📦 {summary['total_orders']:,} orders |
    💰 R$ {summary['total_revenue']:,.2f} total revenue |
    📅 Years: {summary['date_range'][0]} - {summary['date_range'][1]}
    """)


if __name__ == "__main__":
    main()
