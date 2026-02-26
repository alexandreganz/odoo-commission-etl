"""
Overview Page - Executive Summary

High-level overview of sales performance across all dimensions.
"""
import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dashboard.utils.data_loader import load_sales_data, get_data_summary
from dashboard.utils.data_processor import (
    filter_dataframe,
    calculate_salesperson_metrics,
    calculate_product_metrics,
    calculate_customer_metrics
)
from dashboard.components.filters import render_filters
from dashboard.components.metrics import render_kpis

st.set_page_config(page_title="Overview", page_icon="📈", layout="wide")

st.title("📈 Executive Overview")
st.markdown("High-level summary of sales performance")

# Load and filter data
df = load_sales_data()
operations, salespeople, years, value_range = render_filters(df)
filtered_df = filter_dataframe(df, operations, salespeople, years, value_range)

# KPIs
render_kpis(filtered_df)

st.markdown("---")

# Three column layout for top performers
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🏆 Top 5 Salespeople")
    sp_metrics = calculate_salesperson_metrics(filtered_df)
    st.dataframe(
        sp_metrics[['Salesperson', 'Total Revenue']].head(5),
        hide_index=True
    )

with col2:
    st.subheader("📦 Top 5 Products")
    prod_metrics = calculate_product_metrics(filtered_df)
    st.dataframe(
        prod_metrics[['Product Code', 'Total Revenue']].head(5),
        hide_index=True
    )

with col3:
    st.subheader("👥 Top 5 Customers")
    cust_metrics = calculate_customer_metrics(filtered_df)
    # Truncate customer names for display
    cust_display = cust_metrics.head(5).copy()
    cust_display['Customer'] = cust_display['Customer'].str[:30]
    st.dataframe(
        cust_display[['Customer', 'Total Revenue']],
        hide_index=True
    )

st.markdown("---")

# Data summary
summary = get_data_summary(filtered_df)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Orders", f"{summary['total_orders']:,}")

with col2:
    st.metric("Unique Products", f"{summary['total_products']:,}")

with col3:
    st.metric("Unique Customers", f"{summary['total_customers']:,}")

with col4:
    st.metric("Active Salespeople", f"{summary['total_salespeople']:,}")
