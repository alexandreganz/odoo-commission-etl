"""
Product Analysis Page - Product Performance & NCM Analysis

Detailed product-level analytics and classification insights.
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
    calculate_product_metrics
)
from dashboard.components.filters import render_filters
from dashboard.components.charts import (
    plot_product_treemap,
    plot_ncm_distribution,
    plot_value_distribution
)

st.set_page_config(page_title="Product Analysis", page_icon="📦", layout="wide")

st.title("📦 Product Analysis")
st.markdown("Product performance metrics and classification insights")

# Load and filter data
df = load_sales_data()
operations, salespeople, years, value_range = render_filters(df)
filtered_df = filter_dataframe(df, operations, salespeople, years, value_range)

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 Product Performance", "🏷️ NCM Classification", "🔍 Product Search"])

with tab1:
    st.header("Product Performance Metrics")

    # Treemap
    top_n = st.slider("Number of products in treemap", 20, 100, 50, key="treemap_slider")
    fig = plot_product_treemap(filtered_df, top_n=top_n)
    st.plotly_chart(fig)

    st.markdown("---")

    # Detailed table
    st.subheader("Detailed Metrics by Product")
    prod_metrics = calculate_product_metrics(filtered_df)

    # Format currency columns
    prod_metrics['Total Revenue'] = prod_metrics['Total Revenue'].apply(lambda x: f"R$ {x:,.2f}")
    prod_metrics['Avg Sale Value'] = prod_metrics['Avg Sale Value'].apply(lambda x: f"R$ {x:,.2f}")

    st.dataframe(
        prod_metrics,
        hide_index=True,
        height=600
    )

    # Download button
    csv = prod_metrics.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Download Product Metrics",
        data=csv,
        file_name="product_metrics.csv",
        mime="text/csv"
    )

with tab2:
    st.header("NCM Code Distribution")

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = plot_ncm_distribution(filtered_df, top_n=15)
        st.plotly_chart(fig)

    with col2:
        st.metric("Total Unique NCM Codes", filtered_df['produto_ncm_id'].nunique())
        st.metric("Most Common NCM", filtered_df['produto_ncm_id'].mode().iloc[0] if len(filtered_df) > 0 else "N/A")

    st.markdown("---")

    # NCM summary table
    st.subheader("NCM Code Summary")
    ncm_summary = filtered_df.groupby('produto_ncm_id').agg({
        'vr_nf': 'sum',
        'quantidade': 'sum',
        'produto_codigo': 'nunique'
    }).reset_index()

    ncm_summary.columns = ['NCM Code', 'Total Revenue', 'Total Quantity', 'Unique Products']
    ncm_summary = ncm_summary.sort_values('Total Revenue', ascending=False)
    ncm_summary['Total Revenue'] = ncm_summary['Total Revenue'].apply(lambda x: f"R$ {x:,.2f}")

    st.dataframe(
        ncm_summary,
        hide_index=True,
    )

with tab3:
    st.header("Product Search & Lookup")

    # Search bar
    search_product = st.text_input("🔍 Search by product code", "")

    if search_product:
        matching_products = filtered_df[
            filtered_df['produto_codigo'].str.contains(search_product, case=False, na=False)
        ]

        if len(matching_products) > 0:
            st.success(f"Found {len(matching_products)} line items for products matching '{search_product}'")

            # Product summary
            summary = matching_products.groupby('produto_codigo').agg({
                'vr_nf': ['sum', 'mean', 'count'],
                'quantidade': 'sum',
                'numero': 'nunique'
            }).reset_index()

            summary.columns = ['Product Code', 'Total Revenue', 'Avg Sale', 'Times Sold', 'Total Qty', 'Unique Orders']
            summary = summary.sort_values('Total Revenue', ascending=False)

            st.dataframe(summary)

            st.markdown("---")

            # Detailed transactions
            with st.expander("View All Transactions"):
                st.dataframe(
                    matching_products[['numero', 'produto_codigo', 'quantidade', 'vr_nf', 'vendedor_id', 'participante_id']],
                    height=400
                )
        else:
            st.warning(f"No products found matching '{search_product}'")
    else:
        st.info("Enter a product code above to search")

    st.markdown("---")

    # Value distribution
    st.subheader("Invoice Value Distribution")
    fig = plot_value_distribution(filtered_df)
    st.plotly_chart(fig)
