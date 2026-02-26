"""
Comissões — Janeiro 2026
========================
Streamlit page comparing Odoo ETL output against the Teste.xlsx benchmark.

Columns displayed:
  Pedido · Vendedor · Cliente · Aprovação · Finalização
  Código · Produto · Qtd. · Valor (R$) · Comissão (R$)

Tabs:
  1 – Odoo (ETL)          → data from outputs/csv/january_sales.csv
  2 – Benchmark           → data parsed from Teste.xlsx
  3 – Comparação          → side-by-side diff per vendedor
  4 – Gráficos            → bar charts & product analysis
"""

import sys
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Path setup ────────────────────────────────────────────────────────────────
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

ODOO_CSV   = project_root / "outputs" / "csv" / "january_sales.csv"
BENCH_XLSX = project_root / "Teste.xlsx"

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Comissões Janeiro 2026",
    page_icon="💰",
    layout="wide",
)


# ── Data loaders ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_odoo_data() -> pd.DataFrame | None:
    """Load ETL output CSV (january_sales.csv)."""
    if not ODOO_CSV.exists():
        return None
    df = pd.read_csv(ODOO_CSV, encoding="utf-8-sig", dtype={"produto_codigo": str})
    for col in ("data_aprovacao", "data_financeiro"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    df["valor"]    = pd.to_numeric(df["valor"],    errors="coerce").fillna(0.0)
    df["comissao"] = pd.to_numeric(df["comissao"], errors="coerce").fillna(0.0)
    df["quantidade"] = pd.to_numeric(df["quantidade"], errors="coerce").fillna(0.0)
    return df


@st.cache_data(ttl=3600)
def load_benchmark_data() -> pd.DataFrame | None:
    """
    Parse Teste.xlsx which has a report structure:
        Row 1:     Title
        Row 7:     Column headers  (Pedido, Aprov., Cliente, Final., Código, Produto, Quant., Valor, Comissão)
        Row N:     'Vendedor: <name>'   ← section header
        Row N+1:   'Tipo: Venda'
        Row N+2+:  data rows starting with 'PV-'
    """
    if not BENCH_XLSX.exists():
        return None

    try:
        df_raw = pd.read_excel(BENCH_XLSX, header=None, engine="openpyxl")
    except Exception as e:
        st.warning(f"Erro ao ler Teste.xlsx: {e}")
        return None

    # Find header row (contains 'Pedido' and 'Aprov')
    header_row_idx = None
    for idx, row in df_raw.iterrows():
        vals = [str(v).strip().lower() for v in row.values if pd.notna(v)]
        if any("pedido" in v for v in vals) and any("aprov" in v for v in vals):
            header_row_idx = idx
            break

    if header_row_idx is None:
        st.warning("Não foi possível identificar o cabeçalho no Teste.xlsx.")
        return None

    # Walk through raw rows, track current vendedor, collect data rows
    current_vendedor = None
    data_rows = []

    for idx, row in df_raw.iterrows():
        if idx <= header_row_idx:
            continue

        cell0 = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""

        if cell0.lower().startswith("vendedor:"):
            current_vendedor = cell0.split(":", 1)[1].strip()
            continue

        if cell0.lower().startswith("tipo:"):
            continue  # skip type row

        # Data row: starts with 'PV-'
        if cell0.startswith("PV-"):
            data_rows.append({
                "vendedor":        current_vendedor,
                "pedido":          cell0,
                "data_aprovacao":  row.iloc[1],
                "cliente":         str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else "",
                "data_financeiro": row.iloc[3],
                "produto_codigo":  str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else "",
                "produto_nome":    str(row.iloc[5]).strip() if pd.notna(row.iloc[5]) else "",
                "quantidade":      row.iloc[6],
                "valor":           row.iloc[7],
                "comissao":        row.iloc[8],
            })

    if not data_rows:
        return None

    df = pd.DataFrame(data_rows)
    for col in ("data_aprovacao", "data_financeiro"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["valor"]    = pd.to_numeric(df["valor"],    errors="coerce").fillna(0.0)
    df["comissao"] = pd.to_numeric(df["comissao"], errors="coerce").fillna(0.0)
    df["quantidade"] = pd.to_numeric(df["quantidade"], errors="coerce").fillna(0.0)
    return df


# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt_brl(val: float) -> str:
    try:
        s = f"{float(val):,.2f}"                     # e.g. 1,234.56
        return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def pct(val: float) -> str:
    try:
        return f"{float(val):.2f}%"
    except Exception:
        return "0,00%"


def display_df(df: pd.DataFrame):
    """Render a clean formatted version of the data."""
    show = df.copy()
    for col in ("data_aprovacao", "data_financeiro"):
        if col in show.columns:
            show[col] = show[col].dt.strftime("%d/%m/%Y").fillna("")

    col_map = {
        "pedido":          "Pedido",
        "vendedor":        "Vendedor",
        "cliente":         "Cliente",
        "data_aprovacao":  "Aprovação",
        "data_financeiro": "Finalização",
        "produto_codigo":  "Código",
        "produto_nome":    "Produto",
        "quantidade":      "Qtd.",
        "valor":           "Valor (R$)",
        "comissao":        "Comissão (R$)",
    }
    show = show.rename(columns={k: v for k, v in col_map.items() if k in show.columns})

    col_cfg = {
        "Valor (R$)":    st.column_config.NumberColumn(format="R$ %.2f"),
        "Comissão (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "Qtd.":          st.column_config.NumberColumn(format="%.2f"),
    }
    st.dataframe(show, use_container_width=True, column_config=col_cfg)


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


# ── Load data ─────────────────────────────────────────────────────────────────
df_odoo  = load_odoo_data()
df_bench = load_benchmark_data()


# ── Header ────────────────────────────────────────────────────────────────────
st.title("💰 Comissões — Janeiro 2026")
st.caption("Vendas · Tipo: Venda (PV-) · Período: 01/01/2026 – 31/01/2026")

# ── ETL not run yet ────────────────────────────────────────────────────────────
if df_odoo is None:
    st.warning("⚠️  Dados do Odoo ainda não extraídos. Execute o pipeline ETL primeiro.")

    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("🔄 Executar ETL Agora", type="primary"):
            with st.spinner("Conectando ao Odoo e extraindo dados de janeiro..."):
                try:
                    from src.etl.january_sales_pipeline import run_january_sales_pipeline
                    run_january_sales_pipeline()
                    st.cache_data.clear()
                    st.success("✅ ETL concluído com sucesso!")
                    st.rerun()
                except Exception as exc:
                    st.error(f"❌ Erro no ETL: {exc}")
    with c2:
        st.code("python -m src.etl.january_sales_pipeline", language="bash")

    if df_bench is None:
        st.info("Também não foi encontrado o arquivo Teste.xlsx para benchmark.")
        st.stop()
    else:
        st.info("📋 Exibindo apenas o benchmark (Teste.xlsx) enquanto dados do Odoo não estão disponíveis.")


# ── Sidebar filters ───────────────────────────────────────────────────────────
st.sidebar.header("🔍 Filtros")

# Collect all unique vendedores from available sources
all_vendors: list[str] = []
for src in (df_odoo, df_bench):
    if src is not None:
        all_vendors += src["vendedor"].dropna().unique().tolist()
all_vendors = sorted(set(all_vendors))

selected_vendors = st.sidebar.multiselect(
    "Vendedor",
    options=all_vendors,
    default=all_vendors,
    help="Selecione um ou mais vendedores",
)


def filter_df(df: pd.DataFrame | None) -> pd.DataFrame | None:
    if df is None:
        return None
    if selected_vendors:
        return df[df["vendedor"].isin(selected_vendors)].copy()
    return df.copy()


df_odoo_f  = filter_df(df_odoo)
df_bench_f = filter_df(df_bench)

# ── KPIs ──────────────────────────────────────────────────────────────────────
st.subheader("📊 Resumo Geral")

# Use Odoo data as primary; fall back to benchmark
df_kpi = df_odoo_f if df_odoo_f is not None else df_bench_f

if df_kpi is not None and not df_kpi.empty:
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    total_valor    = df_kpi["valor"].sum()
    total_comissao = df_kpi["comissao"].sum()
    pct_com        = (total_comissao / total_valor * 100) if total_valor else 0

    k1.metric("Pedidos",        df_kpi["pedido"].nunique())
    k2.metric("Vendedores",     df_kpi["vendedor"].nunique())
    k3.metric("Itens",          len(df_kpi))
    k4.metric("Valor Total",    fmt_brl(total_valor))
    k5.metric("Comissão Total", fmt_brl(total_comissao))
    k6.metric("% Comissão",     pct(pct_com))

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🟢 Odoo (ETL)",
    "📋 Benchmark (Teste.xlsx)",
    "🔍 Comparação",
    "📈 Gráficos",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Odoo data
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    if df_odoo_f is None or df_odoo_f.empty:
        st.warning("Dados do Odoo não disponíveis. Execute o ETL.")
    else:
        n_pedidos = df_odoo_f["pedido"].nunique()
        st.caption(f"{len(df_odoo_f):,} itens em {n_pedidos:,} pedidos (fonte: Odoo)")

        # Optional per-vendedor drill-down
        if len(selected_vendors) > 1:
            pick = st.selectbox("Detalhar vendedor:", ["Todos"] + selected_vendors, key="drill_odoo")
            df_view = df_odoo_f[df_odoo_f["vendedor"] == pick] if pick != "Todos" else df_odoo_f
        else:
            df_view = df_odoo_f

        display_df(df_view)

        st.download_button(
            "⬇️ Baixar Excel (Odoo)",
            data=to_excel_bytes(df_view),
            file_name="comissoes_jan2026_odoo.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — Benchmark
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    if df_bench_f is None or df_bench_f.empty:
        st.warning("Arquivo Teste.xlsx não encontrado ou sem dados válidos.")
    else:
        n_pedidos_b = df_bench_f["pedido"].nunique()
        st.caption(f"{len(df_bench_f):,} itens em {n_pedidos_b:,} pedidos (fonte: Teste.xlsx)")

        if len(selected_vendors) > 1:
            pick_b = st.selectbox(
                "Detalhar vendedor:",
                ["Todos"] + [v for v in selected_vendors if v in df_bench_f["vendedor"].unique()],
                key="drill_bench",
            )
            df_view_b = df_bench_f[df_bench_f["vendedor"] == pick_b] if pick_b != "Todos" else df_bench_f
        else:
            df_view_b = df_bench_f

        display_df(df_view_b)

        st.download_button(
            "⬇️ Baixar Excel (Benchmark)",
            data=to_excel_bytes(df_view_b),
            file_name="comissoes_jan2026_benchmark.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — Comparison
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    if df_odoo_f is None or df_bench_f is None:
        st.info("Carregue dados de ambas as fontes (Odoo ETL + Teste.xlsx) para ver a comparação.")
    else:
        st.subheader("Comparação por Vendedor")
        st.caption("Diferença = Odoo − Benchmark")

        def agg_by_vendor(df: pd.DataFrame, label: str) -> pd.DataFrame:
            return (
                df.groupby("vendedor")
                .agg(
                    pedidos=("pedido", "nunique"),
                    itens=("pedido", "count"),
                    valor=("valor", "sum"),
                    comissao=("comissao", "sum"),
                )
                .reset_index()
                .rename(columns={
                    "pedidos":  f"pedidos_{label}",
                    "itens":    f"itens_{label}",
                    "valor":    f"valor_{label}",
                    "comissao": f"comissao_{label}",
                })
            )

        agg_o = agg_by_vendor(df_odoo_f,  "odoo")
        agg_b = agg_by_vendor(df_bench_f, "bench")

        comp = agg_o.merge(agg_b, on="vendedor", how="outer").fillna(0)
        comp["Δ Valor"]    = comp["valor_odoo"]    - comp["valor_bench"]
        comp["Δ Comissão"] = comp["comissao_odoo"] - comp["comissao_bench"]
        comp["Δ Valor %"]  = (
            (comp["Δ Valor"] / comp["valor_bench"].replace(0, float("nan"))) * 100
        ).round(2)

        comp_display = comp.rename(columns={
            "vendedor":        "Vendedor",
            "pedidos_odoo":    "Pedidos Odoo",
            "pedidos_bench":   "Pedidos Bench",
            "valor_odoo":      "Valor Odoo",
            "valor_bench":     "Valor Benchmark",
            "comissao_odoo":   "Comissão Odoo",
            "comissao_bench":  "Comissão Benchmark",
        })

        cols_show = [
            "Vendedor",
            "Pedidos Odoo", "Pedidos Bench",
            "Valor Odoo", "Valor Benchmark", "Δ Valor", "Δ Valor %",
            "Comissão Odoo", "Comissão Benchmark", "Δ Comissão",
        ]
        # Keep only columns that exist
        cols_show = [c for c in cols_show if c in comp_display.columns]

        st.dataframe(
            comp_display[cols_show],
            use_container_width=True,
            column_config={
                "Valor Odoo":          st.column_config.NumberColumn(format="R$ %.2f"),
                "Valor Benchmark":     st.column_config.NumberColumn(format="R$ %.2f"),
                "Δ Valor":             st.column_config.NumberColumn(format="R$ %.2f"),
                "Δ Valor %":           st.column_config.NumberColumn(format="%.2f%%"),
                "Comissão Odoo":       st.column_config.NumberColumn(format="R$ %.2f"),
                "Comissão Benchmark":  st.column_config.NumberColumn(format="R$ %.2f"),
                "Δ Comissão":          st.column_config.NumberColumn(format="R$ %.2f"),
            },
        )

        st.subheader("Comparação por Pedido")
        st.caption("Agrega itens ao nível do pedido para identificar divergências individuais.")

        def agg_by_order(df: pd.DataFrame) -> pd.DataFrame:
            return (
                df.groupby(["pedido", "vendedor"])
                .agg(valor=("valor", "sum"), comissao=("comissao", "sum"))
                .reset_index()
            )

        ord_o = agg_by_order(df_odoo_f).rename(
            columns={"valor": "valor_odoo", "comissao": "comissao_odoo"}
        )
        ord_b = agg_by_order(df_bench_f).rename(
            columns={"valor": "valor_bench", "comissao": "comissao_bench"}
        )

        ord_comp = ord_o.merge(ord_b, on=["pedido", "vendedor"], how="outer").fillna(0)
        ord_comp["Δ Valor"]    = ord_comp["valor_odoo"]    - ord_comp["valor_bench"]
        ord_comp["Δ Comissão"] = ord_comp["comissao_odoo"] - ord_comp["comissao_bench"]

        # Highlight divergent orders
        has_diff = (ord_comp["Δ Valor"].abs() > 0.01) | (ord_comp["Δ Comissão"].abs() > 0.01)
        st.caption(f"{has_diff.sum()} pedido(s) com divergência detectada.")

        ord_display = ord_comp.rename(columns={
            "pedido":          "Pedido",
            "vendedor":        "Vendedor",
            "valor_odoo":      "Valor Odoo",
            "valor_bench":     "Valor Benchmark",
            "comissao_odoo":   "Comissão Odoo",
            "comissao_bench":  "Comissão Benchmark",
        })
        st.dataframe(
            ord_display,
            use_container_width=True,
            column_config={
                "Valor Odoo":         st.column_config.NumberColumn(format="R$ %.2f"),
                "Valor Benchmark":    st.column_config.NumberColumn(format="R$ %.2f"),
                "Δ Valor":            st.column_config.NumberColumn(format="R$ %.2f"),
                "Comissão Odoo":      st.column_config.NumberColumn(format="R$ %.2f"),
                "Comissão Benchmark": st.column_config.NumberColumn(format="R$ %.2f"),
                "Δ Comissão":         st.column_config.NumberColumn(format="R$ %.2f"),
            },
        )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — Charts
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    # Use Odoo data preferably, else benchmark
    df_chart = df_odoo_f if (df_odoo_f is not None and not df_odoo_f.empty) else df_bench_f
    if df_chart is None or df_chart.empty:
        st.warning("Sem dados para gráficos.")
    else:
        source_label = "Odoo (ETL)" if df_odoo_f is not None else "Benchmark (Teste.xlsx)"
        st.caption(f"Fonte: {source_label}")

        # ── Row 1: Commission bar + Valor vs Comissão grouped ─────────────────
        col_a, col_b = st.columns(2)

        with col_a:
            agg_v = (
                df_chart.groupby("vendedor")
                .agg(valor=("valor", "sum"), comissao=("comissao", "sum"))
                .reset_index()
                .sort_values("comissao", ascending=True)
            )
            fig = px.bar(
                agg_v,
                x="comissao",
                y="vendedor",
                orientation="h",
                title="Comissão por Vendedor",
                labels={"comissao": "Comissão (R$)", "vendedor": "Vendedor"},
                color="comissao",
                color_continuous_scale="Greens",
                text_auto=".2f",
            )
            fig.update_traces(texttemplate="R$ %{x:,.2f}", textposition="outside")
            fig.update_layout(showlegend=False, height=420, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            agg_v2 = (
                df_chart.groupby("vendedor")
                .agg(valor=("valor", "sum"), comissao=("comissao", "sum"))
                .reset_index()
                .sort_values("valor", ascending=False)
            )
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                name="Valor", x=agg_v2["vendedor"], y=agg_v2["valor"],
                marker_color="#4C78A8",
            ))
            fig2.add_trace(go.Bar(
                name="Comissão", x=agg_v2["vendedor"], y=agg_v2["comissao"],
                marker_color="#54A24B",
            ))
            fig2.update_layout(
                title="Valor vs Comissão por Vendedor",
                barmode="group",
                height=420,
                yaxis_title="R$",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig2, use_container_width=True)

        # ── Row 2: Comparison bars (if both sources available) ─────────────────
        if df_odoo_f is not None and df_bench_f is not None:
            st.subheader("Odoo vs Benchmark")
            c1, c2 = st.columns(2)

            with c1:
                # Valor comparison
                agg_oo = df_odoo_f.groupby("vendedor")["valor"].sum().reset_index().rename(columns={"valor": "Odoo"})
                agg_bb = df_bench_f.groupby("vendedor")["valor"].sum().reset_index().rename(columns={"valor": "Benchmark"})
                cmp_v  = agg_oo.merge(agg_bb, on="vendedor", how="outer").fillna(0)
                fig_v  = go.Figure()
                fig_v.add_trace(go.Bar(name="Odoo",      x=cmp_v["vendedor"], y=cmp_v["Odoo"],      marker_color="#4C78A8"))
                fig_v.add_trace(go.Bar(name="Benchmark", x=cmp_v["vendedor"], y=cmp_v["Benchmark"], marker_color="#F58518"))
                fig_v.update_layout(title="Valor: Odoo vs Benchmark", barmode="group", height=380, yaxis_title="R$")
                st.plotly_chart(fig_v, use_container_width=True)

            with c2:
                # Comissão comparison
                agg_oc = df_odoo_f.groupby("vendedor")["comissao"].sum().reset_index().rename(columns={"comissao": "Odoo"})
                agg_bc = df_bench_f.groupby("vendedor")["comissao"].sum().reset_index().rename(columns={"comissao": "Benchmark"})
                cmp_c  = agg_oc.merge(agg_bc, on="vendedor", how="outer").fillna(0)
                fig_c  = go.Figure()
                fig_c.add_trace(go.Bar(name="Odoo",      x=cmp_c["vendedor"], y=cmp_c["Odoo"],      marker_color="#54A24B"))
                fig_c.add_trace(go.Bar(name="Benchmark", x=cmp_c["vendedor"], y=cmp_c["Benchmark"], marker_color="#E45756"))
                fig_c.update_layout(title="Comissão: Odoo vs Benchmark", barmode="group", height=380, yaxis_title="R$")
                st.plotly_chart(fig_c, use_container_width=True)

        # ── Row 3: Top products ─────────────────────────────────────────────────
        if "produto_nome" in df_chart.columns or "produto_codigo" in df_chart.columns:
            st.subheader("Top 20 Produtos por Valor")

            name_col = "produto_nome" if "produto_nome" in df_chart.columns else "produto_codigo"
            top = (
                df_chart.groupby(["produto_codigo", name_col])
                .agg(valor=("valor", "sum"), comissao=("comissao", "sum"), qtd=("quantidade", "sum"))
                .reset_index()
                .sort_values("valor", ascending=False)
                .head(20)
            )
            top["label"] = top["produto_codigo"] + " · " + top[name_col].str[:40]

            fig3 = px.bar(
                top.sort_values("valor"),
                x="valor",
                y="label",
                orientation="h",
                title="Top 20 Produtos — Valor Total",
                labels={"valor": "Valor (R$)", "label": "Produto"},
                color="valor",
                color_continuous_scale="Blues",
            )
            fig3.update_layout(showlegend=False, height=550, coloraxis_showscale=False)
            st.plotly_chart(fig3, use_container_width=True)

        # ── Row 4: Commission % per order (scatter) ────────────────────────────
        st.subheader("% Comissão por Pedido")
        order_agg = (
            df_chart.groupby(["pedido", "vendedor"])
            .agg(valor=("valor", "sum"), comissao=("comissao", "sum"))
            .reset_index()
        )
        order_agg["pct_comissao"] = (order_agg["comissao"] / order_agg["valor"].replace(0, float("nan")) * 100).round(2)

        fig4 = px.scatter(
            order_agg,
            x="valor",
            y="pct_comissao",
            color="vendedor",
            hover_data=["pedido", "comissao"],
            title="% Comissão vs Valor do Pedido",
            labels={"valor": "Valor do Pedido (R$)", "pct_comissao": "% Comissão", "vendedor": "Vendedor"},
            height=420,
        )
        fig4.update_traces(marker=dict(size=8, opacity=0.8))
        st.plotly_chart(fig4, use_container_width=True)
