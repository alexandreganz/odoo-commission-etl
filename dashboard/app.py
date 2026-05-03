"""
Sales Dashboard — Single-page Streamlit + Plotly app.

Reads combined_cigam_odoo.csv and renders:
  1. Time-series line chart (monthly sales 2024–2026)
  2. Horizontal bar chart — sales per vendedor
  3. Horizontal bar chart — sales per familia_grupo
  4. Treemap — produto_nome grouped by familia_grupo (top 20)
  5. Pivot table — months × (ano / vendedor / familia_grupo)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Sales Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "outputs" / "csv" / "combined_cigam_odoo.csv"

MONTH_MAP = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
             7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
MONTH_ORDER = list(MONTH_MAP.values())

# Color palette
COLORS = {
    "primary": "#0f4c81",
    "accent": "#2196F3",
    "positive": "#4CAF50",
    "negative": "#f44336",
    "neutral": "#78909C",
    "bg": "#fafbfc",
}
PALETTE = ["#0f4c81", "#2196F3", "#26A69A", "#FF7043", "#AB47BC",
           "#FFA726", "#66BB6A", "#EF5350", "#42A5F5", "#8D6E63"]

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* KPI cards */
    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e8ecf0;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    div[data-testid="stMetric"] label {
        font-size: 13px !important;
        color: #78909C !important;
        font-weight: 500 !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 22px !important;
        font-weight: 700 !important;
        color: #0f4c81 !important;
    }
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #f0f4f8;
    }
    section[data-testid="stSidebar"] h2 {
        color: #0f4c81;
        font-size: 15px;
        margin-bottom: 4px;
    }
    /* Main area */
    .block-container { padding-top: 1.5rem; }
    /* Header */
    .dash-header {
        background: linear-gradient(135deg, #0f4c81, #2196F3);
        color: white;
        padding: 20px 28px;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    .dash-header h1 { margin: 0; font-size: 26px; font-weight: 700; }
    .dash-header p  { margin: 4px 0 0; opacity: 0.85; font-size: 14px; }
    /* Pivot table */
    .pivot-wrap { overflow-x: auto; font-family: 'Segoe UI', sans-serif; font-size: 12px; }
    .pivot-wrap table { border-collapse: collapse; width: 100%; }
    .pivot-wrap th {
        background: #0f4c81; color: white; font-weight: 600;
        padding: 6px 8px; text-align: center; white-space: nowrap;
        position: sticky; top: 0; z-index: 2;
    }
    .pivot-wrap th.lbl { text-align: left; min-width: 140px; }
    .pivot-wrap td { padding: 4px 8px; border-bottom: 1px solid #e8ecf0; white-space: nowrap; }
    .pivot-wrap td.lbl { text-align: left; color: #444; padding-left: 12px; font-size: 12px; }
    .pivot-wrap td.num { text-align: right; color: #1a1a2e; font-size: 12px; }
    .pivot-wrap td.total-num { text-align: right; font-weight: 700; color: #0f4c81; font-size: 12px; }
    .year-row td { background: #1a5276 !important; color: white !important;
                   font-weight: 700; font-size: 13px; }
    .year-row td.lbl { padding-left: 8px; letter-spacing: 0.5px; }
    .pivot-wrap tr:not(.year-row):hover td { background: #e8f4fd !important; }
</style>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig", low_memory=False)
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce")
    df["mes"] = pd.to_numeric(df["mes"], errors="coerce")
    df["vr_nf"] = pd.to_numeric(df["vr_nf"], errors="coerce").fillna(0)
    df["quantidade"] = pd.to_numeric(df["quantidade"], errors="coerce").fillna(0)
    df["vendedor"] = df["vendedor"].fillna("").astype(str)
    df["vendedor"] = df["vendedor"].replace({"": "Vendedor CIGAM (em branco)", "(sem vendedor)": "Vendedor CIGAM (em branco)"})
    df["familia_grupo"] = df["familia_grupo"].fillna("Outros").astype(str)
    df["empresa"] = df["empresa"].fillna("Sem empresa").astype(str)
    df["tipo_norm"] = df["tipo_norm"].fillna("").astype(str)
    df["produto_nome"] = df["produto_nome"].fillna("").astype(str)
    df["cliente"] = df["cliente"].fillna("").astype(str)
    df["mes_nome"] = df["mes"].map(MONTH_MAP)
    df["trimestre"] = df["mes"].map(lambda m: f"Q{int((m - 1) // 3 + 1)}" if pd.notna(m) else "")
    df = df.dropna(subset=["ano"])
    df["ano"] = df["ano"].astype(int)
    # Date column for time series
    df["date"] = pd.to_datetime(
        df["ano"].astype(str) + "-" + df["mes"].astype(int).astype(str) + "-01",
        errors="coerce",
    )
    return df


if not CSV_PATH.exists():
    st.error("CSV not found. Run `python -m src.etl.cigam_append` first.")
    st.stop()

df = load_data()

# ── Sidebar Filters ───────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🔍 Filtros")

    # Operação (tipo_norm) — pill buttons
    tipo_options = sorted(df["tipo_norm"].unique().tolist())
    tipo_labels = {"venda": "Venda", "devolucao": "Devolução", "os": "Ordem de Serviço", "remessa": "Remessa"}
    tipo_defaults = [t for t in tipo_options if t != "remessa"]
    sel_tipo = st.pills(
        "Operação",
        options=tipo_options,
        default=tipo_defaults,
        format_func=lambda x: tipo_labels.get(x, x),
        selection_mode="multi",
    )
    if not sel_tipo:
        sel_tipo = tipo_options

    # Date filters — Ano, Trimestre, Mês
    st.markdown("##### Período")
    all_anos = sorted(df["ano"].dropna().unique().tolist())
    sel_anos = st.pills("Ano", all_anos, default=all_anos, selection_mode="multi")
    if not sel_anos:
        sel_anos = all_anos

    QUARTER_MAP = {"Q1": [1, 2, 3], "Q2": [4, 5, 6], "Q3": [7, 8, 9], "Q4": [10, 11, 12]}
    sel_quarters = st.pills("Trimestre", list(QUARTER_MAP.keys()), default=[], selection_mode="multi")
    quarter_months = set()
    if sel_quarters:
        for q in sel_quarters:
            quarter_months.update(QUARTER_MAP[q])

    all_meses = sorted(df["mes"].dropna().unique().tolist())
    mes_opts = [m for m in all_meses if m in quarter_months] if quarter_months else all_meses
    sel_meses = st.pills(
        "Mês",
        mes_opts,
        default=mes_opts if sel_quarters else [],
        format_func=lambda m: MONTH_MAP.get(m, m),
        selection_mode="multi",
    )
    if not sel_meses:
        sel_meses = mes_opts if mes_opts else all_meses

    st.markdown("##### Dimensões")

    # Empresa — pill buttons
    all_empresas = sorted(df["empresa"].dropna().unique().tolist())
    sel_empresas = st.pills("Empresa", all_empresas, default=all_empresas, selection_mode="multi")
    if not sel_empresas:
        sel_empresas = all_empresas

    # Vendedor — searchable multiselect
    all_vends = sorted(df["vendedor"].unique().tolist())
    vend_search = st.text_input("🔍 Buscar vendedor", placeholder="Filtrar...")
    vend_opts = [v for v in all_vends if vend_search.lower() in v.lower()] if vend_search else all_vends
    sel_vendedores = st.multiselect("Vendedor", vend_opts, default=[], placeholder="Todos")
    if not sel_vendedores:
        sel_vendedores = all_vends

    # Familia Grupo — searchable multiselect
    all_fams = sorted(df["familia_grupo"].unique().tolist())
    fam_search = st.text_input("🔍 Buscar família", placeholder="Filtrar...")
    fam_opts = [f for f in all_fams if fam_search.lower() in f.lower()] if fam_search else all_fams
    sel_familias = st.multiselect("Família / Grupo", fam_opts, default=[], placeholder="Todos")
    if not sel_familias:
        sel_familias = all_fams

    st.divider()
    st.caption("Fonte: Odoo + CIGAM consolidado")


# ── Apply filters ─────────────────────────────────────────────────────────────

fdf = df[
    df["tipo_norm"].isin(sel_tipo)
    & df["ano"].isin(sel_anos)
    & df["mes"].isin(sel_meses)
    & df["empresa"].isin(sel_empresas)
    & df["vendedor"].isin(sel_vendedores)
    & df["familia_grupo"].isin(sel_familias)
].copy()

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="dash-header">'
    "<h1>📊 Dashboard de Vendas</h1>"
    "</div>",
    unsafe_allow_html=True,
)

if fdf.empty:
    st.warning("Nenhum dado corresponde aos filtros selecionados.")
    st.stop()

# ── Cross-filter state (click on chart bar to filter everything) ──────────────

if "chart_filter_field" not in st.session_state:
    st.session_state["chart_filter_field"] = None
    st.session_state["chart_filter_value"] = None

chart_fdf = fdf.copy()
active_filter = None
if st.session_state["chart_filter_field"] and st.session_state["chart_filter_value"]:
    field = st.session_state["chart_filter_field"]
    value = st.session_state["chart_filter_value"]
    if field in fdf.columns:
        chart_fdf = fdf[fdf[field] == value].copy()
        active_filter = f"{value}"
    else:
        st.session_state["chart_filter_field"] = None
        st.session_state["chart_filter_value"] = None

if active_filter:
    fcol1, fcol2 = st.columns([6, 1])
    with fcol1:
        st.info(f"🔍 Filtro ativo: **{active_filter}** — todos os gráficos, cards e tabelas refletem este recorte")
    with fcol2:
        if st.button("✖ Limpar filtro"):
            st.session_state["chart_filter_field"] = None
            st.session_state["chart_filter_value"] = None
            st.rerun()

# ── KPI Cards ─────────────────────────────────────────────────────────────────

k1, k2, k3, k4, k5 = st.columns(5)
total_revenue = chart_fdf["vr_nf"].sum()
with k1:
    st.metric("Faturamento Total", f"R$ {total_revenue:,.0f}")
with k2:
    st.metric("Notas Fiscais", f"{chart_fdf['numero'].nunique():,}")
with k3:
    st.metric("Produtos Ativos", f"{chart_fdf['produto_nome'].nunique():,}")
with k4:
    st.metric("Vendedores", f"{chart_fdf['vendedor'].nunique():,}")
with k5:
    st.metric("Clientes", f"{chart_fdf['cliente'].nunique():,}")

st.markdown("")

# ── Chart 1 — Time Series Bar ─────────────────────────────────────────────────

ts = (
    chart_fdf.groupby(["date", "tipo_norm"])["vr_nf"]
    .sum()
    .reset_index()
    .sort_values("date")
)

# Also compute a cumulative total line
ts_total = chart_fdf.groupby("date")["vr_nf"].sum().reset_index().sort_values("date")
ts_total["acumulado"] = ts_total["vr_nf"].cumsum()

import plotly.graph_objects as go
fig_ts = go.Figure()

# Stacked bars by tipo_norm
tipo_color = {"venda": "#2196F3", "devolucao": "#f44336", "os": "#78909C", "remessa": "#FFA726"}
tipo_label = {"venda": "Venda", "devolucao": "Devolução", "os": "OS", "remessa": "Remessa"}
for tipo in ["venda", "os", "remessa", "devolucao"]:
    tdf = ts[ts["tipo_norm"] == tipo]
    if tdf.empty:
        continue
    fig_ts.add_trace(go.Bar(
        x=tdf["date"], y=tdf["vr_nf"],
        name=tipo_label.get(tipo, tipo),
        marker_color=tipo_color.get(tipo, "#999"),
        hovertemplate="<b>%{x|%b %Y}</b><br>R$ %{y:,.0f}<extra>" + tipo_label.get(tipo, tipo) + "</extra>",
    ))

# Cumulative line on secondary axis
fig_ts.add_trace(go.Scatter(
    x=ts_total["date"], y=ts_total["acumulado"],
    name="Acumulado",
    mode="lines+markers",
    line=dict(color="#0f4c81", width=2.5, dash="dot"),
    marker=dict(size=4),
    yaxis="y2",
    hovertemplate="<b>%{x|%b %Y}</b><br>Acumulado: R$ %{y:,.0f}<extra></extra>",
))

fig_ts.update_layout(
    title=dict(text="Faturamento Mensal", font=dict(size=18, color=COLORS["primary"])),
    plot_bgcolor="white",
    paper_bgcolor="white",
    hovermode="x unified",
    legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center",
                bgcolor="rgba(255,255,255,0.8)", font=dict(size=11)),
    margin=dict(l=50, r=50, t=50, b=50),
    yaxis=dict(
        title="Mensal (R$)", gridcolor="#eee", tickformat=",.0f",
        zeroline=True, zerolinecolor="#ccc",
    ),
    yaxis2=dict(
        title="Acumulado (R$)", overlaying="y", side="right",
        tickformat=",.0f", showgrid=False,
    ),
    xaxis=dict(
        gridcolor="#f0f0f0",
        dtick="M1", tickformat="%b\n%Y",
        tickangle=0,
    ),
    height=420,
    barmode="stack",
    bargap=0.15,
)
st.plotly_chart(fig_ts, use_container_width=True)

# ── Charts 2, 3 & 4 — Horizontal Bars side by side (cross-filter on click) ────

col_left, col_mid, col_right = st.columns(3)

# Chart 2 — Sales per Vendedor
with col_left:
    vend_data = (
        chart_fdf.groupby("vendedor")["vr_nf"].sum()
        .sort_values(ascending=True)
        .tail(15)
        .reset_index()
    )
    fig_vend = px.bar(
        vend_data, x="vr_nf", y="vendedor", orientation="h",
        labels={"vr_nf": "R$", "vendedor": ""},
        color_discrete_sequence=[COLORS["primary"]],
    )
    fig_vend.update_layout(
        title=dict(text="Top 15 Vendedores", font=dict(size=16, color=COLORS["primary"])),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=20, t=50, b=30),
        xaxis=dict(gridcolor="#eee", tickformat=",.0f"),
        height=450, showlegend=False,
    )
    fig_vend.update_traces(hovertemplate="<b>%{y}</b><br>R$ %{x:,.0f}<extra></extra>")
    event_vend = st.plotly_chart(fig_vend, use_container_width=True, on_select="rerun", key="vend_chart")
    if event_vend and event_vend.selection and event_vend.selection.points:
        clicked = event_vend.selection.points[0]
        val = clicked.get("y") or clicked.get("label")
        if val and (st.session_state["chart_filter_field"] != "vendedor" or st.session_state["chart_filter_value"] != val):
            st.session_state["chart_filter_field"] = "vendedor"
            st.session_state["chart_filter_value"] = val
            st.rerun()

# Chart 3 — Sales per Familia Grupo
with col_mid:
    fam_data = (
        chart_fdf.groupby("familia_grupo")["vr_nf"].sum()
        .sort_values(ascending=True)
        .tail(15)
        .reset_index()
    )
    fig_fam = px.bar(
        fam_data, x="vr_nf", y="familia_grupo", orientation="h",
        labels={"vr_nf": "R$", "familia_grupo": ""},
        color_discrete_sequence=[COLORS["accent"]],
    )
    fig_fam.update_layout(
        title=dict(text="Top 15 Família / Grupo", font=dict(size=16, color=COLORS["primary"])),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=20, t=50, b=30),
        xaxis=dict(gridcolor="#eee", tickformat=",.0f"),
        height=450, showlegend=False,
    )
    fig_fam.update_traces(hovertemplate="<b>%{y}</b><br>R$ %{x:,.0f}<extra></extra>")
    event_fam = st.plotly_chart(fig_fam, use_container_width=True, on_select="rerun", key="fam_chart")
    if event_fam and event_fam.selection and event_fam.selection.points:
        clicked = event_fam.selection.points[0]
        val = clicked.get("y") or clicked.get("label")
        if val and (st.session_state["chart_filter_field"] != "familia_grupo" or st.session_state["chart_filter_value"] != val):
            st.session_state["chart_filter_field"] = "familia_grupo"
            st.session_state["chart_filter_value"] = val
            st.rerun()

# Chart 4 — Top Clientes
with col_right:
    cliente_data = (
        chart_fdf[chart_fdf["cliente"] != ""].groupby("cliente")["vr_nf"].sum()
        .sort_values(ascending=True)
        .tail(15)
        .reset_index()
    )
    cliente_data["display"] = cliente_data["cliente"].str[:35]
    fig_cli = px.bar(
        cliente_data, x="vr_nf", y="display", orientation="h",
        labels={"vr_nf": "R$", "display": ""},
        color_discrete_sequence=["#26A69A"],
    )
    fig_cli.update_layout(
        title=dict(text="Top 15 Clientes", font=dict(size=16, color=COLORS["primary"])),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=20, t=50, b=30),
        xaxis=dict(gridcolor="#eee", tickformat=",.0f"),
        height=450, showlegend=False,
    )
    fig_cli.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>R$ %{x:,.0f}<extra></extra>",
        customdata=cliente_data[["cliente"]].values,
    )
    event_cli = st.plotly_chart(fig_cli, use_container_width=True, on_select="rerun", key="cli_chart")
    if event_cli and event_cli.selection and event_cli.selection.points:
        clicked = event_cli.selection.points[0]
        # Get full client name from customdata
        idx = clicked.get("point_index", clicked.get("pointIndex"))
        if idx is not None and idx < len(cliente_data):
            val = cliente_data.iloc[idx]["cliente"]
        else:
            val = clicked.get("y") or clicked.get("label")
        if val and (st.session_state["chart_filter_field"] != "cliente" or st.session_state["chart_filter_value"] != val):
            st.session_state["chart_filter_field"] = "cliente"
            st.session_state["chart_filter_value"] = val
            st.rerun()

# ── Chart 5 — Treemap ─────────────────────────────────────────────────────────

tree_data = (
    chart_fdf.groupby(["familia_grupo", "produto_nome"])["vr_nf"]
    .sum()
    .reset_index()
    .sort_values("vr_nf", ascending=False)
)
# Top 20 products
top_prods = tree_data.nlargest(20, "vr_nf")

fig_tree = px.treemap(
    top_prods,
    path=["familia_grupo", "produto_nome"],
    values="vr_nf",
    color="familia_grupo",
    color_discrete_sequence=PALETTE,
)
fig_tree.update_layout(
    title=dict(text="Top 20 Produtos por Família", font=dict(size=18, color=COLORS["primary"])),
    margin=dict(l=10, r=10, t=50, b=10),
    height=500,
)
fig_tree.update_traces(
    hovertemplate="<b>%{label}</b><br>R$ %{value:,.0f}<extra></extra>",
    textinfo="label+value",
    texttemplate="%{label}<br>R$ %{value:,.0f}",
)
st.plotly_chart(fig_tree, use_container_width=True)

# ── Chart 6 — Pivot Table ─────────────────────────────────────────────────────

st.markdown(
    f'<h3 style="color:{COLORS["primary"]}; margin-top:10px;">📋 Tabela Pivô</h3>',
    unsafe_allow_html=True,
)

pivot_tab1, pivot_tab2 = st.tabs(["🔧 Pivô Interativo", "📊 Tabela Rápida"])

with pivot_tab1:
    FIELD_OPTIONS = {
        "Ano": "ano",
        "Trimestre": "trimestre",
        "Mês": "mes_nome",
        "Operação": "tipo_norm",
        "Empresa": "empresa",
        "Vendedor": "vendedor",
        "Família/Grupo": "familia_grupo",
        "Cliente": "cliente",
        "Produto": "produto_nome",
    }

    # Initialize session_state defaults
    if "dyn_rows" not in st.session_state:
        st.session_state["dyn_rows"] = ["Ano", "Vendedor"]
    if "dyn_cols" not in st.session_state:
        st.session_state["dyn_cols"] = ["Trimestre"]
    if "dyn_value" not in st.session_state or st.session_state["dyn_value"] not in ("R$", "Qtd"):
        st.session_state["dyn_value"] = "R$"

    # Row 1: Structure
    r1c1, r1c2, r1c3 = st.columns([3, 3, 1])
    with r1c1:
        sel_rows = st.multiselect("📊 Linhas", list(FIELD_OPTIONS.keys()), default=st.session_state["dyn_rows"], key="dyn_rows")
    with r1c2:
        available_cols = [f for f in FIELD_OPTIONS if f not in sel_rows]
        default_cols = [c for c in st.session_state["dyn_cols"] if c in available_cols]
        sel_cols = st.multiselect("📊 Colunas", available_cols, default=default_cols, key="dyn_cols")
    with r1c3:
        sel_value = st.radio("Valor", ["R$", "Qtd"], horizontal=True, key="dyn_value")

    # Row 2: Search filters
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        all_prods = sorted(chart_fdf["produto_nome"].dropna().unique().tolist())
        sel_prods = st.multiselect("🔍 Filtrar Produto", all_prods, default=[], placeholder="Buscar produto...", key="dyn_prod")
    with r2c2:
        all_clis = sorted(chart_fdf["cliente"].dropna().unique().tolist())
        sel_clis = st.multiselect("🔍 Filtrar Cliente", all_clis, default=[], placeholder="Buscar cliente...", key="dyn_cli")

    # Apply product/client search filters
    dyn_df = chart_fdf.copy()
    if sel_prods:
        dyn_df = dyn_df[dyn_df["produto_nome"].isin(sel_prods)]
    if sel_clis:
        dyn_df = dyn_df[dyn_df["cliente"].isin(sel_clis)]

    value_col = "vr_nf" if sel_value == "R$" else "quantidade"
    agg_func = "sum"

    if not sel_rows:
        st.warning("Selecione pelo menos um campo para as linhas.")
    elif dyn_df.empty:
        st.info("Nenhum dado encontrado com os filtros aplicados.")
    else:
        row_fields = [FIELD_OPTIONS[f] for f in sel_rows]
        col_fields = [FIELD_OPTIONS[f] for f in sel_cols] if sel_cols else []

        if col_fields:
            grp_fields = row_fields + col_fields
            grp_result = dyn_df.groupby(grp_fields, dropna=False)[value_col].agg(agg_func).reset_index()

            # Pivot: rows × first col_field (only support one column dim for clean table)
            if len(col_fields) == 1:
                dyn_pivot = grp_result.pivot_table(
                    index=row_fields,
                    columns=col_fields[0],
                    values=value_col,
                    aggfunc="sum",
                    fill_value=0,
                )
            else:
                # Multiple column fields → use tuple column headers
                dyn_pivot = grp_result.pivot_table(
                    index=row_fields,
                    columns=col_fields,
                    values=value_col,
                    aggfunc="sum",
                    fill_value=0,
                )
        else:
            # No column dimension — simple groupby table
            dyn_pivot = dyn_df.groupby(row_fields, dropna=False)[value_col].agg(agg_func).reset_index()
            dyn_pivot = dyn_pivot.set_index(row_fields)
            dyn_pivot.columns = [sel_value]

        # Sort month columns if Mês is the column dimension
        if sel_cols and sel_cols[0] == "Mês" and len(col_fields) == 1:
            ordered = [m for m in MONTH_ORDER if m in dyn_pivot.columns]
            other = [c for c in dyn_pivot.columns if c not in MONTH_ORDER]
            dyn_pivot = dyn_pivot[ordered + other]

        # Add total column
        if isinstance(dyn_pivot.columns, pd.MultiIndex):
            pass  # skip total for multi-level columns
        else:
            dyn_pivot["Total"] = dyn_pivot.sum(axis=1)

        # Format values
        is_currency = (value_col == "vr_nf")

        def fmt_dyn(v):
            if v == 0:
                return "—"
            if is_currency:
                if v == int(v):
                    return f"R$ {int(v):,}"
                return f"R$ {v:,.2f}"
            if v == int(v):
                return f"{int(v):,}"
            return f"{v:,.2f}"

        # Build heatmap colors
        flat_vals = dyn_pivot.values.flatten()
        flat_max = max(abs(v) for v in flat_vals if v != 0) if any(v != 0 for v in flat_vals) else 1

        def dyn_cell_bg(val):
            if val == 0 or flat_max == 0:
                return ""
            ratio = min(abs(val) / flat_max, 1)
            if val < 0:
                r, g, b = 255, int(235 - 60 * ratio), int(235 - 60 * ratio)
            else:
                r, g, b = int(230 - 70 * ratio), int(235 - 40 * ratio), 255
            return f"background-color:rgb({r},{g},{b});"

        # Render HTML table with multi-level collapsible tree
        col_labels = [str(c) for c in dyn_pivot.columns]
        header_html = "".join(f"<th>{c}</th>" for c in col_labels)
        row_level_names = sel_rows if len(sel_rows) > 1 else [sel_rows[0]] if sel_rows else ["—"]
        # Single header column for tree-style labels
        row_header_html = '<th class="lbl">' + " / ".join(row_level_names) + '</th>'

        body_rows = []
        n_levels = len(row_level_names)
        tree_row_count = [0]

        if n_levels >= 2 and isinstance(dyn_pivot.index, pd.MultiIndex):
            all_indices = list(dyn_pivot.index)
            all_data = [dyn_pivot.loc[idx] for idx in all_indices]
            node_counter = [0]

            def make_id():
                node_counter[0] += 1
                return f"n{node_counter[0]}"

            def build_tree(indices_data, level, parent_id, parent_path):
                """Recursively build tree rows for each grouping level."""
                if level >= n_levels:
                    return

                # Group by current level value
                from collections import OrderedDict
                groups = OrderedDict()
                for idx_tuple, row_data in indices_data:
                    key = idx_tuple[level]
                    if key not in groups:
                        groups[key] = []
                    groups[key].append((idx_tuple, row_data))

                is_leaf_level = (level == n_levels - 1)

                for grp_key, grp_items in groups.items():
                    nid = make_id()
                    display = str(grp_key)
                    display = display[:50] + "…" if len(display) > 50 else display
                    indent = level * 20
                    child_class = f"child-{parent_id}" if parent_id else ""

                    if is_leaf_level:
                        # Leaf row: show actual data
                        row_data = grp_items[0][1]
                        cells = "".join(
                            f'<td class="num" style="{dyn_cell_bg(row_data[c])}">{fmt_dyn(row_data[c])}</td>'
                            for c in dyn_pivot.columns
                        )
                        body_rows.append(
                            f'<tr class="{child_class}" data-nid="{nid}">'
                            f'<td class="lbl" style="padding-left:{indent + 12}px; color:#444;">{display}</td>'
                            f'{cells}</tr>'
                        )
                        tree_row_count[0] += 1
                    else:
                        # Group row: show subtotal with toggle
                        subtotals = {}
                        for c in dyn_pivot.columns:
                            subtotals[c] = sum(item[1][c] for item in grp_items)

                        cells = "".join(
                            f'<td class="num" style="font-weight:600; background:#{"e8ecf0" if level == 0 else "f0f4f8"};">'
                            f'{fmt_dyn(subtotals[c])}</td>'
                            for c in dyn_pivot.columns
                        )

                        colors = ["#0f4c81", "#37474F", "#546E7A"]
                        bgs = ["#e8ecf0", "#f0f4f8", "#f5f7fa"]
                        color = colors[min(level, len(colors) - 1)]
                        bg = bgs[min(level, len(bgs) - 1)]
                        weight = 700 if level == 0 else 600

                        body_rows.append(
                            f'<tr class="grp-row {child_class}" data-nid="{nid}">'
                            f'<td class="lbl grp-toggle" data-nid="{nid}" '
                            f'style="padding-left:{indent + 8}px; font-weight:{weight}; '
                            f'background:{bg}; color:{color}; cursor:pointer; user-select:none; '
                            f'border-right:2px solid #cfd8dc;">'
                            f'<span class="icon-{nid}">▼</span> {display}</td>'
                            f'{cells}</tr>'
                        )
                        tree_row_count[0] += 1

                        # Recurse into children
                        build_tree(grp_items, level + 1, nid, parent_path + [grp_key])

            indices_data = list(zip(
                [idx if isinstance(idx, tuple) else (idx,) for idx in all_indices],
                all_data
            ))
            build_tree(indices_data, 0, None, [])

        else:
            # Single-level index — no collapsing
            for idx, row_data in dyn_pivot.iterrows():
                label = str(idx)
                display = label[:60] + "…" if len(label) > 60 else label
                cells = "".join(
                    f'<td class="num" style="{dyn_cell_bg(row_data[c])}">{fmt_dyn(row_data[c])}</td>'
                    for c in dyn_pivot.columns
                )
                body_rows.append(f'<tr><td class="lbl">{display}</td>{cells}</tr>')
                tree_row_count[0] += 1

        # Grand total row
        if not isinstance(dyn_pivot.columns, pd.MultiIndex):
            col_totals = dyn_pivot.sum()
            total_cells = "".join(
                f'<td class="total-num">{fmt_dyn(col_totals[c])}</td>' for c in dyn_pivot.columns
            )
            body_rows.append(f'<tr class="year-row"><td class="lbl" style="padding-left:8px;">📊 Total</td>{total_cells}</tr>')
            tree_row_count[0] += 1

        collapse_js = """
        <script>
        document.querySelectorAll('.grp-toggle').forEach(el => {
            el.addEventListener('click', function() {
                const nid = this.getAttribute('data-nid');
                const children = document.querySelectorAll('.child-' + nid);
                if (children.length === 0) return;
                const isExpanded = children[0].style.display !== 'none';

                // Toggle direct children
                children.forEach(r => r.style.display = isExpanded ? 'none' : '');

                // If collapsing, also hide all nested children recursively
                if (isExpanded) {
                    children.forEach(r => {
                        const childNid = r.getAttribute('data-nid');
                        if (childNid) {
                            const nested = document.querySelectorAll('.child-' + childNid);
                            nested.forEach(n => n.style.display = 'none');
                            // Update nested icons to collapsed
                            document.querySelectorAll('.icon-' + childNid).forEach(ic => ic.textContent = '▶');
                        }
                    });
                }

                // Update icon
                document.querySelectorAll('.icon-' + nid).forEach(ic => {
                    ic.textContent = isExpanded ? '▶' : '▼';
                });
            });
        });
        </script>
        """

        pivot_css = """
        <style>
        body { margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; font-size: 12px; }
        .pivot-wrap { overflow-x: auto; }
        .pivot-wrap table { border-collapse: collapse; width: 100%; }
        .pivot-wrap th {
            background: #0f4c81; color: white; font-weight: 600;
            padding: 6px 8px; text-align: center; white-space: nowrap;
            position: sticky; top: 0; z-index: 2;
        }
        .pivot-wrap th.lbl { text-align: left; min-width: 200px; }
        .pivot-wrap td { padding: 4px 8px; border-bottom: 1px solid #e8ecf0; white-space: nowrap; }
        .pivot-wrap td.lbl { text-align: left; font-size: 12px; }
        .pivot-wrap td.num { text-align: right; color: #1a1a2e; font-size: 12px; }
        .pivot-wrap td.total-num { text-align: right; font-weight: 700; color: #0f4c81; font-size: 12px; }
        .year-row td { background: #1a5276 !important; color: white !important;
                       font-weight: 700; font-size: 13px; }
        .pivot-wrap tr:not(.year-row):not(.grp-row):hover td { background: #e8f4fd !important; }
        .grp-toggle:hover { filter: brightness(0.95); }
        </style>
        """

        table_body = "".join(body_rows)
        estimated_height = min(max(tree_row_count[0] * 28 + 80, 200), 800)

        dyn_html = f"""
        {pivot_css}
        <div class="pivot-wrap">
        <table>
          <thead><tr>{row_header_html}{header_html}</tr></thead>
          <tbody>{table_body}</tbody>
        </table>
        </div>
        {collapse_js}
        """

        val_label = "Valor NF (R$)" if sel_value == "R$" else "Quantidade"
        st.markdown(f"📊 **{len(dyn_pivot):,}** linhas  ·  Soma de {val_label}  ·  💡 _Clique nos grupos para colapsar/expandir_")
        import streamlit.components.v1 as components
        components.html(dyn_html, height=estimated_height, scrolling=True)

        # Download
        csv_dyn = dyn_pivot.reset_index().to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            "⬇️ Download CSV",
            data=csv_dyn,
            file_name="pivot_dinamico.csv",
            mime="text/csv",
        )

with pivot_tab2:
    pivot_dim = st.radio(
        "Linhas da tabela:",
        ["Vendedor", "Família / Grupo", "Cliente"],
        horizontal=True,
        label_visibility="collapsed",
    )
    row_col_map = {"Vendedor": "vendedor", "Família / Grupo": "familia_grupo", "Cliente": "cliente"}
    row_col = row_col_map[pivot_dim]

    grp = (
        chart_fdf.groupby(["ano", row_col, "trimestre"])["vr_nf"]
        .sum()
        .reset_index()
    )

    pivot = grp.pivot_table(
        index=["ano", row_col],
        columns="trimestre",
        values="vr_nf",
        aggfunc="sum",
        fill_value=0,
    )
    quarter_order = ["Q1", "Q2", "Q3", "Q4"]
    present_quarters = [q for q in quarter_order if q in pivot.columns]
    pivot = pivot[present_quarters]
    pivot["Total"] = pivot.sum(axis=1)
    cols = present_quarters + ["Total"]

    year_totals = pivot.groupby(level="ano").sum()
    col_max = {c: max(pivot[c].max(), 1) for c in cols}

    def fmt(v):
        if v == 0:
            return "—"
        if v == int(v):
            return f"R$ {int(v):,}"
        return f"R$ {v:,.2f}"

    def cell_bg(val, col):
        if val == 0 or col_max[col] == 0:
            return ""
        ratio = min(abs(val) / col_max[col], 1)
        if val < 0:
            r, g, b = 255, int(235 - 60 * ratio), int(235 - 60 * ratio)
        else:
            r, g, b = int(230 - 70 * ratio), int(235 - 40 * ratio), 255
        return f"background-color:rgb({r},{g},{b});"

    rows_html = []
    for yr in sorted(pivot.index.get_level_values("ano").unique()):
        yr_vals = year_totals.loc[yr]
        yr_cells = "".join(
            f'<td class="num" style="color:white">{fmt(yr_vals[c])}</td>' for c in present_quarters
        )
        rows_html.append(
            f'<tr class="year-row">'
            f'<td class="lbl">📅 {yr}</td>'
            f'{yr_cells}'
            f'<td class="num" style="color:white">{fmt(yr_vals["Total"])}</td></tr>'
        )

        yr_df = pivot.loc[yr].sort_values("Total", ascending=False)
        for label, row in yr_df.iterrows():
            if row["Total"] == 0:
                continue
            q_cells = "".join(
                f'<td class="num" style="{cell_bg(row[c], c)}">{fmt(row[c])}</td>' for c in present_quarters
            )
            display = label[:40] + "…" if len(str(label)) > 40 else label
            rows_html.append(
                f"<tr>"
                f'<td class="lbl">{display}</td>'
                f"{q_cells}"
                f'<td class="total-num">{fmt(row["Total"])}</td></tr>'
            )

    q_headers = "".join(f"<th>{q}</th>" for q in present_quarters)
    html = f"""
    <div class="pivot-wrap">
    <table>
      <thead><tr>
        <th class="lbl">{pivot_dim}</th>
        {q_headers}
        <th>Total</th>
      </tr></thead>
      <tbody>{"".join(rows_html)}</tbody>
    </table>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    csv_out = pivot.reset_index().to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        "⬇️ Download pivot CSV",
        data=csv_out,
        file_name="pivot_sales.csv",
        mime="text/csv",
    )

st.caption(f"📊 {len(fdf):,} registros · R$ {total_revenue:,.0f} total filtrado")
