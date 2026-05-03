# Odoo ETL & Sales Analytics Dashboard

Sales analytics pipeline that extracts NF-e-level data from Odoo ERP, combines it with CIGAM legacy data, and visualizes through a Streamlit dashboard.

## Features

### ETL Pipeline
- **NF-e-Level Extraction** — Queries authorized fiscal documents (`sped.documento`) directly, matching Odoo's Faturamento report with R$ 0.00 delta
- **CIGAM Integration** — Merges legacy ERP Excel data (pre-2026) with Odoo (2026)
- **Vendedor Matching** — 3-pass fuzzy matching (pre-mapped → rapidfuzz → fallback)
- **Secure Configuration** — Credentials via `.env` (never committed)

### Interactive Dashboard
- **Single-Page Layout** — All charts and filters on one scrollable page
- **5 Charts**: Time series line, vendedor bar, família bar, product treemap, pivot table
- **Sidebar Filters** — Operação (tipo_norm), date (ano+mês), vendedor, família/grupo
- **KPI Cards** — Faturamento, NF count, products, vendedores, clientes
- **Data Export** — Download pivot table as CSV

## Project Structure

```
odoo-commission-etl/
├── .env                                      # Odoo credentials (DO NOT COMMIT)
├── .env.example                              # Credential template
├── BI Cigam - Gestão de Resultado (RICHARD).xlsx  # CIGAM source data
│
├── src/etl/
│   ├── extract_odoo_2026.py                 # Step 1: Odoo NF-e extraction
│   ├── cigam_append.py                      # Step 2: merge Odoo + CIGAM
│   └── odoo_client.py                       # Shared connection class
│
├── dashboard/
│   └── app.py                               # Streamlit single-page dashboard
│
└── outputs/csv/                             # Generated files (gitignored)
    ├── sales_items_odoo_2026.csv            # NF-e item-level Odoo data
    ├── vendedor_mapping.csv                  # CIGAM ↔ Odoo rep mapping
    └── combined_cigam_odoo.csv              # Final merged dataset
```

## Setup

### Prerequisites
- Python 3.8+
- Access to an Odoo instance with XML-RPC enabled

### Installation

```bash
cd odoo-commission-etl
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Odoo credentials
```

## Usage

### Running the ETL Pipeline

```bash
# Step 1 — Extract from Odoo (~3 min)
python3 -m src.etl.extract_odoo_2026

# Step 2 — Merge with CIGAM Excel (~3 min)
python3 -m src.etl.cigam_append
```

### Launching the Dashboard

```bash
python3 -m streamlit run dashboard/app.py
# → http://localhost:8501
```

## Data Model

The extraction queries `sped.documento` (NF-e fiscal documents) at the item level, not `pedido.documento` (sales orders). This matches Odoo's official Faturamento report exactly.

Key filters:
- `operacao_id IN [1, 2, 29, 38, 40, 41, 42, 46]` — sales + devolução fiscal ops
- `situacao_nfe = 'autorizada'` — only authorized NF-es
- `empresa_id = 1` — Santa Inês
- `pedido_id != False` — exclude orphan devoluções

See `CLAUDE.md` for full model relationships and technical details.

## Security

- `.env` with credentials is in `.gitignore`
- `outputs/` directory is gitignored (may contain customer data)
- Dashboard runs on localhost only

---

**Last Updated:** 2026-05-03
