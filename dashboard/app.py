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
    .pivot-wrap { overflow-x: auto; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
    .pivot-wrap table { border-collapse: collapse; width: 100%; }
    .pivot-wrap th {
        background: #0f4c81; color: white; font-weight: 600;
        padding: 8px 12px; text-align: center; white-space: nowrap;
        position: sticky; top: 0; z-index: 2;
    }
    .pivot-wrap th.lbl { text-align: left; min-width: 200px; }
    .pivot-wrap td { padding: 5px 10px; border-bottom: 1px solid #e8ecf0; white-space: nowrap; }
    .pivot-wrap td.lbl { text-align: left; color: #444; padding-left: 24px; }
    .pivot-wrap td.num { text-align: right; color: #1a1a2e; }
    .pivot-wrap td.total-num { text-align: right; font-weight: 700; color: #0f4c81; }
    .year-row td { background: #1a5276 !important; color: white !important;
                   font-weight: 700; font-size: 14px; }
    .year-row td.lbl { padding-left: 10px; letter-spacing: 0.5px; }
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

    # Operação (tipo_norm)
    tipo_options = sorted(df["tipo_norm"].unique().tolist())
    tipo_labels = {"venda": "Venda", "devolucao": "Devolução", "os": "Ordem de Serviço"}
    sel_tipo = st.multiselect(
        "Operação",
        options=tipo_options,
        default=tipo_options,
        format_func=lambda x: tipo_labels.get(x, x),
    )

    # Date filters — Ano, Trimestre, Mês
    st.markdown("##### Período")
    all_anos = sorted(df["ano"].dropna().unique().tolist())
    sel_anos = st.multiselect("Ano", all_anos, default=all_anos)

    QUARTER_MAP = {"Q1": [1, 2, 3], "Q2": [4, 5, 6], "Q3": [7, 8, 9], "Q4": [10, 11, 12]}
    sel_quarters = st.multiselect("Trimestre", list(QUARTER_MAP.keys()), default=[], placeholder="Todos")
    quarter_months = set()
    if sel_quarters:
        for q in sel_quarters:
            quarter_months.update(QUARTER_MAP[q])

    all_meses = sorted(df["mes"].dropna().unique().tolist())
    mes_opts = [m for m in all_meses if m in quarter_months] if quarter_months else all_meses
    sel_meses = st.multiselect(
        "Mês",
        mes_opts,
        default=mes_opts if sel_quarters else [],
        format_func=lambda m: MONTH_MAP.get(m, m),
        placeholder="Todos",
    )
    if not sel_meses:
        sel_meses = mes_opts if mes_opts else all_meses

    st.markdown("##### Dimensões")

    # Empresa (company)
    all_empresas = sorted(df["empresa"].dropna().unique().tolist())
    sel_empresas = st.multiselect("Empresa", all_empresas, default=all_empresas)

    # Vendedor
    all_vends = sorted(df["vendedor"].unique().tolist())
    vend_search = st.text_input("🔍 Buscar vendedor", placeholder="Filtrar...")
    vend_opts = [v for v in all_vends if vend_search.lower() in v.lower()] if vend_search else all_vends
    sel_vendedores = st.multiselect("Vendedor", vend_opts, default=[], placeholder="Todos")
    if not sel_vendedores:
        sel_vendedores = all_vends

    # Familia Grupo
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
    "<h1>📊 Sales Dashboard</h1>"
    "<p>Visão consolidada Odoo + CIGAM · Atualizado automaticamente</p>"
    "</div>",
    unsafe_allow_html=True,
)

if fdf.empty:
    st.warning("Nenhum dado corresponde aos filtros selecionados.")
    st.stop()

# ── KPI Cards ─────────────────────────────────────────────────────────────────

k1, k2, k3, k4, k5 = st.columns(5)
total_revenue = fdf["vr_nf"].sum()
with k1:
    st.metric("Faturamento Total", f"R$ {total_revenue:,.0f}")
with k2:
    st.metric("Notas Fiscais", f"{fdf['numero'].nunique():,}")
with k3:
    st.metric("Produtos Ativos", f"{fdf['produto_nome'].nunique():,}")
with k4:
    st.metric("Vendedores", f"{fdf['vendedor'].nunique():,}")
with k5:
    st.metric("Clientes", f"{fdf['cliente'].nunique():,}")

st.markdown("")

# ── Chart 1 — Time Series Line ────────────────────────────────────────────────

ts = (
    fdf.groupby(["date", "tipo_norm"])["vr_nf"]
    .sum()
    .reset_index()
    .sort_values("date")
)
fig_ts = px.line(
    ts,
    x="date",
    y="vr_nf",
    color="tipo_norm",
    labels={"date": "", "vr_nf": "R$", "tipo_norm": "Operação"},
    color_discrete_map={"venda": COLORS["primary"], "devolucao": COLORS["negative"], "os": COLORS["neutral"]},
)
fig_ts.update_layout(
    title=dict(text="Faturamento Mensal", font=dict(size=18, color=COLORS["primary"])),
    plot_bgcolor="white",
    paper_bgcolor="white",
    hovermode="x unified",
    legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
    margin=dict(l=40, r=20, t=50, b=40),
    yaxis=dict(gridcolor="#eee", tickformat=",.0f"),
    xaxis=dict(gridcolor="#eee"),
    height=380,
)
fig_ts.update_traces(line=dict(width=2.5), hovertemplate="R$ %{y:,.0f}")
st.plotly_chart(fig_ts, use_container_width=True)

# ── Charts 2, 3 & 4 — Horizontal Bars side by side ───────────────────────────

col_left, col_mid, col_right = st.columns(3)

# Chart 2 — Sales per Vendedor
with col_left:
    vend_data = (
        fdf.groupby("vendedor")["vr_nf"].sum()
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
    st.plotly_chart(fig_vend, use_container_width=True)

# Chart 3 — Sales per Familia Grupo
with col_mid:
    fam_data = (
        fdf.groupby("familia_grupo")["vr_nf"].sum()
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
    st.plotly_chart(fig_fam, use_container_width=True)

# Chart 4 — Top Clientes
with col_right:
    cliente_data = (
        fdf[fdf["cliente"] != ""].groupby("cliente")["vr_nf"].sum()
        .sort_values(ascending=True)
        .tail(15)
        .reset_index()
    )
    # Truncate long names for display
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
    st.plotly_chart(fig_cli, use_container_width=True)

# ── Chart 5 — Treemap ─────────────────────────────────────────────────────────

tree_data = (
    fdf.groupby(["familia_grupo", "produto_nome"])["vr_nf"]
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

pivot_tab1, pivot_tab2 = st.tabs(["📊 Tabela Rápida", "🔧 Pivô Interativo"])

with pivot_tab1:
    pivot_dim = st.radio(
        "Linhas da tabela:",
        ["Vendedor", "Família / Grupo", "Cliente"],
        horizontal=True,
        label_visibility="collapsed",
    )
    row_col_map = {"Vendedor": "vendedor", "Família / Grupo": "familia_grupo", "Cliente": "cliente"}
    row_col = row_col_map[pivot_dim]

    grp = (
        fdf.groupby(["ano", row_col, "mes_nome", "mes"])["vr_nf"]
        .sum()
        .reset_index()
    )

    pivot = grp.pivot_table(
        index=["ano", row_col],
        columns="mes_nome",
        values="vr_nf",
        aggfunc="sum",
        fill_value=0,
    )
    present_months = [m for m in MONTH_ORDER if m in pivot.columns]
    pivot = pivot[present_months]
    pivot["Total"] = pivot.sum(axis=1)
    cols = present_months + ["Total"]

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
            f'<td class="num" style="color:white">{fmt(yr_vals[c])}</td>' for c in present_months
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
            month_cells = "".join(
                f'<td class="num" style="{cell_bg(row[c], c)}">{fmt(row[c])}</td>' for c in present_months
            )
            display = label[:40] + "…" if len(str(label)) > 40 else label
            rows_html.append(
                f"<tr>"
                f'<td class="lbl">{display}</td>'
                f"{month_cells}"
                f'<td class="total-num">{fmt(row["Total"])}</td></tr>'
            )

    month_headers = "".join(f"<th>{m}</th>" for m in present_months)
    html = f"""
    <div class="pivot-wrap">
    <table>
      <thead><tr>
        <th class="lbl">{pivot_dim}</th>
        {month_headers}
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

with pivot_tab2:
    st.caption("Arraste os campos para linhas, colunas e valores. Use o seletor de renderização para alternar entre tabela, heatmap e gráficos.")

    include_detail = st.checkbox(
        "Incluir Cliente e Produto (carregamento mais lento)",
        value=False,
    )

    # Pre-aggregate to keep payload small
    if include_detail:
        grp_cols = ["ano", "mes_nome", "tipo_norm", "vendedor", "familia_grupo", "cliente", "produto_nome"]
    else:
        grp_cols = ["ano", "mes_nome", "tipo_norm", "vendedor", "familia_grupo"]

    pivot_df = (
        fdf.groupby(grp_cols, dropna=False)
        .agg({"vr_nf": "sum", "quantidade": "sum"})
        .reset_index()
    )

    col_rename = {
        "ano": "Ano", "mes_nome": "Mês", "tipo_norm": "Operação",
        "vendedor": "Vendedor", "familia_grupo": "Família/Grupo",
        "cliente": "Cliente", "produto_nome": "Produto",
        "vr_nf": "Valor NF (R$)", "quantidade": "Quantidade",
    }
    pivot_df = pivot_df.rename(columns=col_rename)
    st.info(f"📊 {len(pivot_df):,} linhas agregadas carregadas no pivô interativo")

    # Build pivottablejs HTML with chart renderers
    pivot_json = pivot_df.to_json(orient="records", force_ascii=False)

    pivotui_html = f"""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/pivottable/2.23.0/pivot.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jqueryui/1.13.2/jquery-ui.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pivottable/2.23.0/pivot.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.5/d3.min.js"></script>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pivottable/2.23.0/plotly_renderers.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pivottable/2.23.0/d3_renderers.min.js"></script>
    <style>
        body {{ margin: 0; padding: 8px; font-family: 'Segoe UI', -apple-system, sans-serif; }}

        /* Drag area styling */
        .pvtUi {{ font-size: 13px; }}
        .pvtAxisContainer {{
            background: linear-gradient(135deg, #f8f9fa, #e8ecf0);
            border: 1px dashed #b0bec5;
            border-radius: 8px;
            padding: 8px;
            min-height: 50px;
        }}
        .pvtAxisContainer li span.pvtAttr {{
            background: #0f4c81;
            color: white;
            border: none;
            border-radius: 16px;
            padding: 4px 12px;
            font-size: 12px;
            font-weight: 500;
            cursor: grab;
            box-shadow: 0 1px 3px rgba(0,0,0,0.15);
            transition: all 0.2s;
        }}
        .pvtAxisContainer li span.pvtAttr:hover {{
            background: #2196F3;
            box-shadow: 0 2px 6px rgba(33,150,243,0.3);
            transform: translateY(-1px);
        }}
        .pvtTriangle {{ color: white !important; }}

        /* Dropdowns */
        .pvtAggregator, .pvtRenderer {{
            font-size: 12px;
            padding: 5px 8px;
            border: 1px solid #cfd8dc;
            border-radius: 6px;
            background: white;
            color: #37474f;
        }}

        /* Table */
        table.pvtTable {{
            font-size: 12px;
            border-collapse: collapse;
            margin-top: 8px;
        }}
        table.pvtTable thead tr th {{
            background: #0f4c81;
            color: white;
            padding: 8px 12px;
            font-weight: 600;
            border: 1px solid #0d3d6b;
        }}
        table.pvtTable tbody tr th {{
            background: #f0f4f8;
            font-weight: 600;
            padding: 6px 10px;
            color: #37474f;
            border: 1px solid #e0e4e8;
        }}
        table.pvtTable tbody tr td {{
            padding: 6px 10px;
            text-align: right;
            border: 1px solid #e8ecf0;
            color: #1a1a2e;
        }}
        table.pvtTable tbody tr:hover td {{
            background: #e3f2fd !important;
        }}
        /* Grand total rows/cols */
        table.pvtTable .pvtTotalLabel {{
            font-weight: 700;
            background: #e8ecf0 !important;
        }}
        table.pvtTable .pvtTotal, table.pvtTable .pvtGrandTotal {{
            font-weight: 700;
            background: #e8ecf0 !important;
            color: #0f4c81;
        }}

        /* Heatmap colors */
        .pvtVal {{ transition: background 0.3s; }}

        /* Filter box */
        .pvtFilterBox {{
            font-size: 12px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        .pvtFilterBox button {{
            border-radius: 4px;
            font-size: 11px;
        }}
        .pvtSearch {{ border-radius: 4px; padding: 4px 8px; }}

        /* Plotly chart area */
        .pvtRendererArea {{ min-height: 400px; }}
    </style>
    <div id="pivotOutput"></div>
    <script>
        $(function(){{
            var data = {pivot_json};

            // Merge all renderers: table + plotly + d3
            var renderers = $.extend(
                $.pivotUtilities.renderers,
                $.pivotUtilities.plotly_renderers,
                $.pivotUtilities.d3_renderers
            );

            $("#pivotOutput").pivotUI(data, {{
                rows: ["Ano", "Vendedor"],
                cols: ["Mês"],
                vals: ["Valor NF (R$)"],
                aggregatorName: "Sum",
                rendererName: "Heatmap",
                renderers: renderers,
                sorters: {{
                    "Mês": $.pivotUtilities.sortAs(["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"])
                }},
                rendererOptions: {{
                    plotly: {{
                        width: 900,
                        height: 500
                    }},
                    heatmap: {{
                        colorScaleGenerator: function(values) {{
                            return d3.scale.linear()
                                .domain([0, d3.max(values)])
                                .range(["#f0f4f8", "#0f4c81"]);
                        }}
                    }}
                }}
            }});
        }});
    </script>
    """

    import streamlit.components.v1 as components
    components.html(pivotui_html, height=750, scrolling=True)

st.caption(f"📊 {len(fdf):,} registros · R$ {total_revenue:,.0f} total filtrado")
