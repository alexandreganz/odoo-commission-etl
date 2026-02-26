"""
Operations Page - Operation Type Deep-Dive

Detailed breakdown of sales by operation type.
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
    calculate_operation_metrics
)
from dashboard.components.filters import render_filters
from dashboard.components.charts import plot_operation_distribution

st.set_page_config(page_title="Operations", page_icon="🔄", layout="wide")

st.title("🔄 Operations Analysis")
st.markdown("Deep dive into sales breakdown by operation type")

# Load and filter data
df = load_sales_data()
operations, salespeople, years, value_range = render_filters(df)
filtered_df = filter_dataframe(df, operations, salespeople, years, value_range)

# Operation distribution chart
st.header("Revenue Distribution by Operation Type")
fig = plot_operation_distribution(filtered_df)
st.plotly_chart(fig)

st.markdown("---")

# Detailed metrics table
st.header("Detailed Metrics by Operation Type")
op_metrics = calculate_operation_metrics(filtered_df)

# Format currency columns
op_metrics['Total Revenue'] = op_metrics['Total Revenue'].apply(lambda x: f"R$ {x:,.2f}")
op_metrics['Avg Value'] = op_metrics['Avg Value'].apply(lambda x: f"R$ {x:,.2f}")

st.dataframe(
    op_metrics,
    hide_index=True,
)

# Download button
csv = op_metrics.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    label="📥 Download Operation Metrics",
    data=csv,
    file_name="operation_metrics.csv",
    mime="text/csv"
)

st.markdown("---")

# Operation-specific analysis
st.header("Analyze Specific Operation")

selected_operation = st.selectbox(
    "Select an operation type to analyze",
    options=filtered_df['operacao_id'].unique()
)

if selected_operation:
    op_data = filtered_df[filtered_df['operacao_id'] == selected_operation]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Revenue", f"R$ {op_data['vr_nf'].sum():,.2f}")

    with col2:
        st.metric("Total Orders", f"{op_data['numero'].nunique():,}")

    with col3:
        st.metric("Total Items", f"{len(op_data):,}")

    with col4:
        st.metric("Avg Order Value", f"R$ {op_data.groupby('numero')['vr_nf'].sum().mean():,.2f}")

    st.markdown("---")

    # Top performers for this operation
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top Salespeople")
        sp_performance = op_data.groupby('vendedor_id')['vr_nf'].sum().sort_values(ascending=False).head(10)
        st.dataframe(
            sp_performance.reset_index().rename(columns={'vendedor_id': 'Salesperson', 'vr_nf': 'Revenue'}),
            hide_index=True,
        )

    with col2:
        st.subheader("Top Products")
        prod_performance = op_data.groupby('produto_codigo')['vr_nf'].sum().sort_values(ascending=False).head(10)
        st.dataframe(
            prod_performance.reset_index().rename(columns={'produto_codigo': 'Product', 'vr_nf': 'Revenue'}),
            hide_index=True,
        )

    # Document type analysis
    st.markdown("---")
    st.subheader("Document Type Distribution")

    doc_types = op_data['doc_type'].value_counts().reset_index()
    doc_types.columns = ['Document Type', 'Count']

    col1, col2 = st.columns([1, 2])

    with col1:
        st.dataframe(doc_types, hide_index=True)

    with col2:
        st.bar_chart(doc_types.set_index('Document Type'))
