"""
KPI Metrics Components

Displays key performance indicator cards in the dashboard.
"""
import streamlit as st


def render_kpis(df):
    """
    Render KPI cards with key metrics.

    Args:
        df (pd.DataFrame): Filtered dataframe
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_revenue = df['vr_nf'].sum()
        st.metric(
            label="💰 Total Revenue",
            value=f"R$ {total_revenue:,.2f}",
            help="Sum of all invoice values"
        )

    with col2:
        total_orders = df['numero'].nunique()
        st.metric(
            label="📦 Total Orders",
            value=f"{total_orders:,}",
            help="Number of unique order documents"
        )

    with col3:
        total_products = df['produto_codigo'].nunique()
        st.metric(
            label="📊 Active Products",
            value=f"{total_products:,}",
            help="Number of unique product codes"
        )

    with col4:
        avg_order_value = df.groupby('numero')['vr_nf'].sum().mean()
        st.metric(
            label="📈 Avg Order Value",
            value=f"R$ {avg_order_value:,.2f}",
            help="Average total value per order"
        )


def render_secondary_metrics(df):
    """
    Render secondary metrics row.

    Args:
        df (pd.DataFrame): Filtered dataframe
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_items = len(df)
        st.metric(
            label="📋 Total Line Items",
            value=f"{total_items:,}",
            help="Total number of order line items"
        )

    with col2:
        total_quantity = df['quantidade'].sum()
        st.metric(
            label="🔢 Total Quantity",
            value=f"{total_quantity:,.0f}",
            help="Sum of all item quantities"
        )

    with col3:
        total_customers = df['participante_id'].nunique()
        st.metric(
            label="👥 Unique Customers",
            value=f"{total_customers:,}",
            help="Number of unique customers"
        )

    with col4:
        total_salespeople = df[df['vendedor_id'] != 'Unknown']['vendedor_id'].nunique()
        st.metric(
            label="🤝 Active Salespeople",
            value=f"{total_salespeople:,}",
            help="Number of unique salespeople"
        )
