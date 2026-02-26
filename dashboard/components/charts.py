"""
Chart Components for Streamlit Dashboard

Provides Plotly chart generation functions for data visualization.
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def plot_operation_distribution(df):
    """
    Create a donut chart showing revenue distribution by operation type.

    Args:
        df (pd.DataFrame): Input dataframe

    Returns:
        plotly.graph_objects.Figure
    """
    operation_revenue = df.groupby('operacao_id')['vr_nf'].sum().reset_index()
    operation_revenue = operation_revenue.sort_values('vr_nf', ascending=False)

    fig = px.pie(
        operation_revenue,
        values='vr_nf',
        names='operacao_id',
        title='Revenue Distribution by Operation Type',
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set3
    )

    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Revenue: R$ %{value:,.2f}<br>Percentage: %{percent}<extra></extra>'
    )

    return fig


def plot_salesperson_performance(df, top_n=15):
    """
    Create a horizontal bar chart showing top salespeople by revenue.

    Args:
        df (pd.DataFrame): Input dataframe
        top_n (int): Number of top salespeople to show

    Returns:
        plotly.graph_objects.Figure
    """
    sales_by_person = df.groupby('vendedor_id')['vr_nf'].sum().sort_values(ascending=True).tail(top_n)

    fig = px.bar(
        x=sales_by_person.values,
        y=sales_by_person.index,
        orientation='h',
        title=f'Top {top_n} Salespeople by Revenue',
        labels={'x': 'Total Revenue (R$)', 'y': 'Salesperson'},
        color=sales_by_person.values,
        color_continuous_scale='Blues'
    )

    fig.update_traces(
        hovertemplate='<b>%{y}</b><br>Revenue: R$ %{x:,.2f}<extra></extra>'
    )

    fig.update_layout(
        showlegend=False,
        height=500
    )

    return fig


def plot_product_treemap(df, top_n=50):
    """
    Create a treemap showing top products by revenue.

    Args:
        df (pd.DataFrame): Input dataframe
        top_n (int): Number of top products to show

    Returns:
        plotly.graph_objects.Figure
    """
    product_revenue = df.groupby('produto_codigo')['vr_nf'].sum().sort_values(ascending=False).head(top_n).reset_index()

    fig = px.treemap(
        product_revenue,
        path=['produto_codigo'],
        values='vr_nf',
        title=f'Top {top_n} Products by Revenue',
        color='vr_nf',
        color_continuous_scale='Viridis'
    )

    fig.update_traces(
        hovertemplate='<b>%{label}</b><br>Revenue: R$ %{value:,.2f}<extra></extra>'
    )

    return fig


def plot_customer_distribution(df, top_n=20):
    """
    Create a bar chart showing top customers by revenue.

    Args:
        df (pd.DataFrame): Input dataframe
        top_n (int): Number of top customers to show

    Returns:
        plotly.graph_objects.Figure
    """
    customer_revenue = df.groupby('participante_id')['vr_nf'].sum().sort_values(ascending=False).head(top_n).reset_index()

    # Truncate long customer names for display
    customer_revenue['customer_display'] = customer_revenue['participante_id'].str[:50]

    fig = px.bar(
        customer_revenue,
        x='customer_display',
        y='vr_nf',
        title=f'Top {top_n} Customers by Revenue',
        labels={'vr_nf': 'Total Revenue (R$)', 'customer_display': 'Customer'},
        color='vr_nf',
        color_continuous_scale='Oranges'
    )

    fig.update_traces(
        hovertemplate='<b>%{x}</b><br>Revenue: R$ %{y:,.2f}<extra></extra>'
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        showlegend=False,
        height=500
    )

    return fig


def plot_value_distribution(df):
    """
    Create a histogram showing distribution of invoice values.

    Args:
        df (pd.DataFrame): Input dataframe

    Returns:
        plotly.graph_objects.Figure
    """
    fig = px.histogram(
        df,
        x='vr_nf',
        nbins=50,
        title='Distribution of Invoice Values',
        labels={'vr_nf': 'Invoice Value (R$)', 'count': 'Frequency'},
        color_discrete_sequence=['#1f77b4']
    )

    fig.update_traces(
        hovertemplate='Value Range: R$ %{x}<br>Count: %{y}<extra></extra>'
    )

    return fig


def plot_ncm_distribution(df, top_n=15):
    """
    Create a bar chart showing top NCM codes by count.

    Args:
        df (pd.DataFrame): Input dataframe
        top_n (int): Number of top NCM codes to show

    Returns:
        plotly.graph_objects.Figure
    """
    ncm_counts = df['produto_ncm_id'].value_counts().head(top_n).reset_index()
    ncm_counts.columns = ['NCM Code', 'Count']

    fig = px.bar(
        ncm_counts,
        x='NCM Code',
        y='Count',
        title=f'Top {top_n} NCM Codes by Frequency',
        color='Count',
        color_continuous_scale='Greens'
    )

    fig.update_traces(
        hovertemplate='<b>%{x}</b><br>Count: %{y}<extra></extra>'
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        showlegend=False
    )

    return fig


def plot_stage_distribution(df):
    """
    Create a bar chart showing distribution by workflow stage.

    Args:
        df (pd.DataFrame): Input dataframe

    Returns:
        plotly.graph_objects.Figure
    """
    stage_counts = df['etapa_tag_ids'].value_counts().head(20).reset_index()
    stage_counts.columns = ['Stage', 'Count']

    fig = px.bar(
        stage_counts,
        x='Stage',
        y='Count',
        title='Orders by Workflow Stage',
        color='Count',
        color_continuous_scale='Purples'
    )

    fig.update_traces(
        hovertemplate='<b>%{x}</b><br>Count: %{y}<extra></extra>'
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        showlegend=False
    )

    return fig
