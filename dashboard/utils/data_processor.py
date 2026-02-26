"""
Data Processing Utilities for Analytics

Handles filtering, aggregations, and transformations for dashboard visualizations.
"""
import pandas as pd


def filter_dataframe(df, operations=None, salespeople=None, years=None, value_range=None):
    """
    Apply filters to the dataframe.

    Args:
        df (pd.DataFrame): Input dataframe
        operations (list): List of operation types to include
        salespeople (list): List of salespeople to include
        years (list): List of years to include
        value_range (tuple): Min and max values for vr_nf

    Returns:
        pd.DataFrame: Filtered dataframe
    """
    filtered = df.copy()

    if operations:
        filtered = filtered[filtered['operacao_id'].isin(operations)]

    if salespeople:
        filtered = filtered[filtered['vendedor_id'].isin(salespeople)]

    if years:
        filtered = filtered[filtered['year'].isin(years)]

    if value_range:
        filtered = filtered[
            (filtered['vr_nf'] >= value_range[0]) &
            (filtered['vr_nf'] <= value_range[1])
        ]

    return filtered


def calculate_salesperson_metrics(df):
    """
    Calculate metrics by salesperson.

    Args:
        df (pd.DataFrame): Input dataframe

    Returns:
        pd.DataFrame: Aggregated metrics by salesperson
    """
    metrics = df.groupby('vendedor_id').agg({
        'vr_nf': ['sum', 'mean', 'count'],
        'numero': 'nunique',
        'produto_codigo': 'nunique',
        'participante_id': 'nunique'
    }).reset_index()

    # Flatten column names
    metrics.columns = [
        'Salesperson',
        'Total Revenue',
        'Avg Sale Value',
        'Total Items',
        'Unique Orders',
        'Unique Products',
        'Unique Customers'
    ]

    # Sort by revenue
    metrics = metrics.sort_values('Total Revenue', ascending=False)

    return metrics


def calculate_product_metrics(df):
    """
    Calculate metrics by product.

    Args:
        df (pd.DataFrame): Input dataframe

    Returns:
        pd.DataFrame: Aggregated metrics by product
    """
    metrics = df.groupby('produto_codigo').agg({
        'vr_nf': ['sum', 'mean'],
        'quantidade': 'sum',
        'numero': 'nunique'
    }).reset_index()

    # Flatten column names
    metrics.columns = [
        'Product Code',
        'Total Revenue',
        'Avg Sale Value',
        'Total Quantity',
        'Number of Orders'
    ]

    # Sort by revenue
    metrics = metrics.sort_values('Total Revenue', ascending=False)

    return metrics


def calculate_customer_metrics(df):
    """
    Calculate metrics by customer.

    Args:
        df (pd.DataFrame): Input dataframe

    Returns:
        pd.DataFrame: Aggregated metrics by customer
    """
    metrics = df.groupby('participante_id').agg({
        'vr_nf': ['sum', 'mean', 'count'],
        'numero': 'nunique',
        'produto_codigo': 'nunique'
    }).reset_index()

    # Flatten column names
    metrics.columns = [
        'Customer',
        'Total Revenue',
        'Avg Purchase Value',
        'Total Items',
        'Unique Orders',
        'Unique Products'
    ]

    # Sort by revenue
    metrics = metrics.sort_values('Total Revenue', ascending=False)

    return metrics


def calculate_operation_metrics(df):
    """
    Calculate metrics by operation type.

    Args:
        df (pd.DataFrame): Input dataframe

    Returns:
        pd.DataFrame: Aggregated metrics by operation
    """
    metrics = df.groupby('operacao_id').agg({
        'vr_nf': ['sum', 'mean', 'count'],
        'numero': 'nunique',
        'quantidade': 'sum'
    }).reset_index()

    # Flatten column names
    metrics.columns = [
        'Operation Type',
        'Total Revenue',
        'Avg Value',
        'Total Items',
        'Unique Orders',
        'Total Quantity'
    ]

    # Sort by revenue
    metrics = metrics.sort_values('Total Revenue', ascending=False)

    return metrics
