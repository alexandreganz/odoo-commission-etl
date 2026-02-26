"""
Filter Components for Streamlit Dashboard

Provides sidebar filter widgets for data exploration.
"""
import streamlit as st


def render_filters(df):
    """
    Render sidebar filters and return selected values.

    Args:
        df (pd.DataFrame): Input dataframe

    Returns:
        tuple: (operations, salespeople, years, value_range)
    """
    st.sidebar.header("🔍 Filters")

    # Operation type filter
    all_operations = sorted(df['operacao_id'].unique().tolist())
    operations = st.sidebar.multiselect(
        "Operation Type",
        options=all_operations,
        default=all_operations,
        help="Select one or more operation types"
    )

    # Salesperson filter
    all_salespeople = sorted(df['vendedor_id'].unique().tolist())
    salespeople = st.sidebar.multiselect(
        "Salesperson",
        options=all_salespeople,
        default=all_salespeople,
        help="Select one or more salespeople"
    )

    # Year filter
    all_years = sorted(df['year'].dropna().unique().tolist())
    years = st.sidebar.multiselect(
        "Year",
        options=all_years,
        default=all_years,
        help="Filter by year from order number"
    )

    # Value range slider
    min_val = float(df['vr_nf'].min())
    max_val = float(df['vr_nf'].max())

    value_range = st.sidebar.slider(
        "Invoice Value Range",
        min_value=min_val,
        max_value=max_val,
        value=(min_val, max_val),
        format="R$ %.2f",
        help="Filter by invoice value"
    )

    # Show filter summary
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Filters applied: {len(operations)} operations, {len(salespeople)} salespeople, {len(years)} years")

    return operations, salespeople, years, value_range


def render_reset_button():
    """Render a reset filters button."""
    if st.sidebar.button("🔄 Reset All Filters"):
        st.rerun()
