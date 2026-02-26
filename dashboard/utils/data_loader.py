"""
Data Loading Utilities for Streamlit Dashboard

Handles CSV loading with caching for optimal performance.
"""
import streamlit as st
import pandas as pd
from pathlib import Path


@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_sales_data():
    """
    Load sales data from CSV with data type conversions and cleaning.

    Returns:
        pd.DataFrame: Cleaned sales dataframe
    """
    # Construct path to data file
    data_file = Path(__file__).parent.parent.parent / 'outputs' / 'csv' / 'final_sales_export_top_down.csv'

    if not data_file.exists():
        st.error(f"Data file not found: {data_file}")
        st.info("Please run the ETL pipeline first: `python -m src.etl.main_pipeline`")
        st.stop()

    # Load CSV
    df = pd.read_csv(data_file, encoding='utf-8-sig')

    # Data type conversions
    df['quantidade'] = pd.to_numeric(df['quantidade'], errors='coerce')
    df['vr_nf'] = pd.to_numeric(df['vr_nf'], errors='coerce')

    # Extract year from order number (e.g., "INV-0001/26" → "26")
    df['year'] = df['numero'].str.extract(r'/(\d{2})$')

    # Extract document type prefix (e.g., "INV-0001/26" → "INV")
    df['doc_type'] = df['numero'].str.extract(r'^([A-Z]+)-')

    # Clean missing values
    df['vendedor_id'].fillna('Unknown', inplace=True)
    df['operacao_id'].fillna('Unknown', inplace=True)
    df['produto_codigo'].fillna('Unknown', inplace=True)

    # Remove rows with null invoice values for analytics
    df = df[df['vr_nf'].notna()]

    return df


def get_data_summary(df):
    """
    Get summary statistics about the dataset.

    Args:
        df (pd.DataFrame): Sales dataframe

    Returns:
        dict: Summary statistics
    """
    return {
        'total_rows': len(df),
        'total_orders': df['numero'].nunique(),
        'total_products': df['produto_codigo'].nunique(),
        'total_salespeople': df['vendedor_id'].nunique(),
        'total_customers': df['participante_id'].nunique(),
        'date_range': (df['year'].min(), df['year'].max()),
        'total_revenue': df['vr_nf'].sum(),
        'avg_order_value': df.groupby('numero')['vr_nf'].sum().mean()
    }
