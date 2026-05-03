# CLAUDE.md — Odoo + CIGAM Sales ETL & Dashboard

This file provides guidance to Claude Code when working with this project.

---

## Overview

Sales analytics pipeline that combines two data sources into one unified dataset for a Streamlit dashboard:

| Source | Coverage | Row count | File |
|---|---|---|---|
| **Odoo** (live ERP) | 2026 NF-e level (authorized) | ~6,700 items | `sales_items_odoo_2026.csv` |
| **CIGAM** (legacy ERP Excel) | 2024–2025 historical | ~117,000 rows | `BI Cigam - Gestão de Resultado (RICHARD).xlsx` |
| **Combined** | All years, both sources | ~124,000 rows | `combined_cigam_odoo.csv` |

CIGAM is filtered to pre-2026 only (Odoo covers 2026). No duplication.

**Tech Stack:** Python 3.9 · Streamlit 1.28.0 · Pandas · rapidfuzz · XML-RPC

---

## Project Structure

```
odoo-commission-etl/
├── .env                                      # Odoo credentials (never commit)
├── BI Cigam - Gestão de Resultado (RICHARD).xlsx  # CIGAM source data
│
├── src/etl/
│   ├── extract_odoo_2026.py                 # Step 1: pulls from Odoo API (NF-e level)
│   ├── cigam_append.py                      # Step 2: merges Odoo + CIGAM
│   └── odoo_client.py                       # Shared Odoo connection class
│
├── dashboard/
│   └── app.py                               # Streamlit single-page dashboard
│
└── outputs/csv/                             # All generated files (gitignored)
    ├── sales_items_odoo_2026.csv            # NF-e item-level Odoo data
    ├── vendedor_mapping.csv                  # CIGAM ↔ Odoo rep name mapping
    ├── vendedores.csv                        # Odoo vendedor list
    └── combined_cigam_odoo.csv              # Final merged dataset
```

---

## How to Re-Run the Full Pipeline

```bash
cd odoo-commission-etl

# Step 1 — Extract from Odoo (~3 min, NF-e level, batched 0.25s/call)
python3 -m src.etl.extract_odoo_2026

# Step 2 — Merge with CIGAM Excel (~3 min)
python3 -m src.etl.cigam_append

# Step 3 — Launch dashboard
python3 -m streamlit run dashboard/app.py
# → http://localhost:8501
```

---

## Odoo Model Relationships

This is the most important section for future extraction work.

### Model Map

```
pedido.documento          (Sales Order header)
│
├─ operacao_id            → pedido.operacao       (order workflow type)
│   └─ tipo               = 'venda' | 'compra' | 'os' | 'romaneio' | ...
│
├─ operacao_produto_id    → sped.operacao         (FISCAL operation on products)
│   └─ display_name       = 'Venda de mercadoria', 'Venda para Produtor Rural', ...
│                           ← THIS is the correct field to filter sales type
│
├─ vendedor_id            → hr.employee / res.partner  (salesperson)
│   └─ name               = 'Pedro Pereira Monteiro - Pedro (Alessandro)'
│
├─ data_contabil          date  ← use for month/year accounting period
├─ data_orcamento         date  ← order creation date
└─ numero                 char  = 'PV-8151/26'  ← /YY suffix = year


sped.documento.item       (Sales Order line items)
│
├─ pedido_id              → pedido.documento      (parent order)
├─ produto_id             → sped.produto          (product)
│   └─ familia_id         → sped.produto.familia  ← product family / category
│       └─ display_name   = 'Pastagens » Sementes', 'Herbicidas » Químicos', ...
│
├─ produto_codigo         char  = '034082'  (6-digit zero-padded, matches CIGAM)
├─ produto_nome           char  = 'ROUNDUP TRANSORB R 5L'
├─ ncm                    char  = '38.08.93.22 - Herbicida...' (fiscal NCM code)
├─ quantidade, vr_unitario, vr_nf, vr_desconto
└─ numero                 char  = inherited from order


sped.produto              (Product master)
│
├─ codigo                 char  = '034082'  (matches CIGAM Material Cód)
└─ familia_id             → sped.produto.familia  (product family)
    └─ display_name       format: 'SubFamily » ParentGroup'
                          e.g.   'Pastagens » Sementes'


sped.operacao             (Fiscal operations / NF-e operation types)
│   referenced by operacao_produto_id on pedido.documento
│   and operacao_servico_id for service items
└─ display_name           = 'Venda de mercadoria', 'Devolução de venda', etc.


pedido.operacao           (Order workflow types — NOT the fiscal operation)
│   referenced by operacao_id on pedido.documento
│   DO NOT confuse with sped.operacao
└─ nome                   = 'Venda de Mercadoria (NF-e)', 'Venda a Consumidor (NFC-e)', ...
    tipo                  = 'venda' | 'compra' | 'os' | ...
```

### Key Distinction: pedido.operacao vs sped.operacao

| Field on pedido.documento | Model | What it means |
|---|---|---|
| `operacao_id` | `pedido.operacao` | Workflow type ("Venda de Mercadoria NF-e"). Controls stages, permissions, document flow. Has `nome` field (not `name`). |
| `operacao_produto_id` | `sped.operacao` | **Fiscal operation** for products — the NF-e CFOP type. This is what differentiates "Venda para Produtor Rural" from a standard sale. Filter extractions by this field. |
| `operacao_servico_id` | `sped.operacao` | Same but for service items on the order. |

### All sped.operacao (Fiscal Operations) — Sales-Relevant

| id | display_name | Use |
|---|---|---|
| 1 | Venda de mercadoria | Standard product sale |
| 2 | Venda para Produtor Rural | Sale to rural producer (different CFOP) |
| 38 | Venda de mercadoria (NFC-e) | Consumer sale via NFC-e |
| 40 | Venda Antecipada - Entrega Futura | Forward sale (future delivery) |
| 29 | Venda Antecipada - Entrega Futura p/ Produtor Rural | Forward sale to rural producer |
| 41 | Devolução de venda | Sales return |
| 46 | Devolução de Venda para Produtor Rural | Rural producer return |
| 42 | Estorno de venda futura | Reversal of forward sale |
| 30 | Remessa Bonificação, Doação ou Brinde | Bonus/donation remittance |
| 31 | Remessa de Venda Antecipada p/ Produtor Rural | Forward remittance — rural |
| 45 | Remessa de Venda Antecipada | Forward remittance |

### All pedido.operacao (Workflow Types) — Sales Relevant

| id | nome | tipo |
|---|---|---|
| 9 | Venda de Mercadoria (NF-e) | venda |
| 25 | Venda Antecipada - Entrega Futura (NF-e) | venda |
| 30 | Venda a Consumidor (NFC-e) | venda |
| 26 | Remessa de Venda Antecipada | venda |

The Faturamento - Geral report in Odoo filters on `operacao_id in [9, 25, 30]` (pedido.operacao).

### Useful Filter Patterns

```python
# Current extraction: NF-e level (sped.documento)
# This matches the Faturamento - Geral report exactly
domain = [
    ('operacao_id', 'in', [1, 2, 29, 38, 40, 41, 42, 46]),
    ('empresa_id', 'in', [1, 2]),
    ('data_emissao', '>=', '2026-01-01'),
    ('data_emissao', '<=', '2026-12-31'),
    ('situacao_nfe', '=', 'autorizada'),
    ('pedido_id', '!=', False),   # exclude orphan devoluções
]

# Completed deliveries only (etapa_tag_ids=60 = "Mercadoria Entregue")
domain = [
    ('etapa_tag_ids', '=', 60),
    ('numero', 'ilike', '/26'),
]
```

---

## ETL Script Details

### extract_odoo_2026.py

Extracts sales data at the **NF-e level** (`sped.documento`), matching the exact logic
used by Odoo's "Faturamento - Geral" report. Validated with R$ 0.00 delta for Feb and March 2026.

**NF-e-level approach (single pass):**
1. Query `sped.documento` (authorized NF-es) filtered by `operacao_id`, `empresa_id in [1,2]`, `data_emissao` in 2026, `situacao_nfe='autorizada'`, `pedido_id != False`
2. Fetch items via `sped.documento.item.documento_id`
3. Get vendedor from `pedido.documento.vendedor_id` via `sped.documento.pedido_id`
4. Get familia from `sped.produto.familia_id` via item `produto_id`

**Classification:**
- Devolução: `operacao_id in [41, 42, 46]` → `vr_nf` stored as **negative**
- OS: `pedido_tipo = 'os'` on `sped.documento`
- Venda: everything else

**Why NF-e level, not order level:**
- The Faturamento report queries `sped.documento` directly, not `pedido.documento`
- OS items have `pedido_id=False` on `sped.documento.item` — they're linked only via `documento_id`
- Only `autorizada` NF-es are included (excludes `inutilizada`, `em_digitacao`, `a_enviar`)
- Orphan devoluções (no `pedido_id`) are excluded — the report can't assign them to a vendedor

**Batching strategy (server-safe):**
- NF-es: paginated 200/call via `search_read` with `offset`
- Items: `documento_id in [batch of 100]` per call
- Vendedores: `pedido.documento read [batch of 100]` per call
- Familia: `sped.produto read [batch of 100]` per call
- Sleep: 0.25s between every API call

**Output:**

`sales_items_odoo_2026.csv` — one row per NF-e item:
```
item_id, documento_id, pedido_id, numero, tipo, vendedor, operacao,
ano, mes, empresa_id, empresa,
produto_id, produto_codigo, produto_nome, ncm,
quantidade, vr_unitario, vr_nf, familia
```

**To add new fiscal operations:** edit `SALE_OP_IDS` or `DEVOL_OP_IDS` at the top.

**To extract a different year:** change date range in `fetch_nfes()`.

### cigam_append.py

Merges the Odoo items CSV with the CIGAM Excel export.
CIGAM data is filtered to **pre-2026 only** (Odoo covers 2026).

**Key logic:**
1. Loads CIGAM Excel (sheet index 0 — name has NFD encoding, use index not name)
2. Loads Odoo items CSV (NF-e level, already has all fields from extract step)
3. Filters CIGAM to `ano < 2026` to avoid duplication
4. Fuzzy-matches CIGAM `Representante` → Odoo `vendedor` (3-pass: pre-mapped CSV → rapidfuzz ≥85 → no_match)
5. Adds `familia_grupo` column that normalises both sources to 9 common groups
6. Concatenates and writes `combined_cigam_odoo.csv`

**Vendedor matching:** pre-resolved pairs live in `vendedor_mapping.csv`. To add a new match, edit that CSV and set `match_type` to `exact` or `partial`.

---

## Combined Dataset Schema

`outputs/csv/combined_cigam_odoo.csv` — ~124,000 rows

| Column | Odoo value | CIGAM value | Notes |
|---|---|---|---|
| `source` | `'odoo'` | `'cigam'` | |
| `ano` | from `data_emissao` | from `Data` column | |
| `mes` | from `data_emissao` | from `Data` column | 1–12 |
| `tipo` | `venda`/`os`/`devolucao` | `Operação Resultado` | |
| `operacao` | `sped.operacao` display name | `Operação Resultado` from Excel | |
| `item_id` | `sped.documento.item` id | `Material Cód` | |
| `documento_id` | `sped.documento` id | *(empty)* | NF-e document ID |
| `numero` | NF-e number (integer string) | NF integer as string | |
| `vendedor_raw` | vendedor name | `Representante` original | |
| `vendedor` | vendedor name | fuzzy-matched to Odoo name | |
| `vendedor_match_type` | `'odoo'` | `exact`/`fuzzy`/`no_match` | |
| `vendedor_match_score` | `100` | rapidfuzz score 0–100 | |
| `produto_id` | Odoo internal int ID | `Material Cód` | different spaces |
| `produto_codigo` | 6-digit zero-padded code | `Material Cód` | matches across sources |
| `produto_nome` | product description | `Material` column | |
| `ncm` | fiscal NCM code string | CIGAM `Grupo` (reused column) | different semantics |
| `familia` | `sped.produto.familia_id` label | CIGAM `Grupo` (uppercase) | granular Odoo, flat CIGAM |
| `familia_grupo` | parent from `'X » ParentGroup'` | normalised CIGAM group | **unified for filtering** |
| `empresa_id` | 1 (Santa Inês) or 2 (Bacabal) | CIGAM `UN Cód` mapped | |
| `empresa` | `'AgroMáquinas Santa Inês'` / `'AgroMáquinas Bacabal'` | CIGAM `UN Cód` mapped | |
| `quantidade` | float | float | |
| `vr_unitario` | float | `Valor Total Item / Quantidade` | |
| `vr_nf` | float (negative for devoluções) | `Valor Total Item` | |

### familia_grupo Normalisation Map

Both sources converge to these 9 values:

| familia_grupo | Odoo familia examples | CIGAM Grupo |
|---|---|---|
| Sementes | Pastagens » Sementes | SEMENTES |
| Químicos | Herbicidas » Químicos, Adjuvantes » Químicos | QUIMICOS |
| Máquinas | Roçadeiras » Máquinas, Motosserras » Máquinas | MAQUINAS |
| Peças e Acessórios | Genérico » Peças e Acessórios, Filtros » Peças e Acessórios | PECAS E ACESSORIOS |
| Nutrição | Minerais » Nutrição, Proteinados » Nutrição | NUTRICAO |
| Serviços | *(rare in Odoo)* | SERVICOS |
| Ferragens e Acessórios | Ferragens » Ferragens e Acessórios, Epi » Ferragens e Acessórios | FERRAGENS E ACESSORIOS |
| Veterinária | Acessórios de Farmácia » Veterinária | VETERINARIA |
| Imobilizado | *(rare)* | IMOBILIZADO |

---

## Dashboard

**Entry point:** `python -m streamlit run dashboard/app.py`

**Single-page layout** (`dashboard/app.py`) with 5 charts:

1. **Time Series Line** — Monthly sales 2024–2026, colored by operação (venda/devolução/os)
2. **Horizontal Bar — Vendedores** — Top 15 vendedores by revenue
3. **Horizontal Bar — Família/Grupo** — Top 15 product families by revenue
4. **Treemap** — Top 20 produtos grouped by família/grupo
5. **Pivot Table** — Months × (Ano / Vendedor or Família), switchable via radio button

**KPI cards:** Faturamento Total, Notas Fiscais, Produtos Ativos, Vendedores, Clientes.

**Sidebar filters:**
- Operação (maps to `tipo_norm`: venda / devolução / os)
- Ano + Mês (multiselect)
- Vendedor (search + multiselect — leave empty = all)
- Família / Grupo (search + multiselect — leave empty = all)

**Pivot rendering:** uses raw HTML via `st.markdown(unsafe_allow_html=True)` — not `st.dataframe`. Year rows are dark blue headers; rows sorted by Total desc; cells have heat-tint proportional to column max.

**Streamlit 1.28.0 compatibility notes:**
- Use `use_column_width=True` (NOT `use_container_width`)
- No `st.switch_page` (not available in 1.28.0)
- Cache with `@st.cache_data(ttl=3600)`

---

## Configuration

`.env` file (never commit):
```env
ODOO_URL=https://agromaquinas.teste.tauga.online
ODOO_DB=teste_agromaquinas
ODOO_USERNAME=dashboard
ODOO_PASSWORD=@Dash#2026%
MAIN_MODEL=pedido.documento
ITEM_MODEL=sped.documento.item
OUTPUT_DIR=outputs
```

API auth: `uid=127` for the `dashboard` user.

---

## Known Quirks & Gotchas

| Issue | Detail |
|---|---|
| CIGAM Excel sheet name | Has NFD encoding — always use `sheet_name=0` (index), never the string name |
| `pedido.operacao.name` | Field is named `nome`, not `name`. Searching by `name` raises ValueError |
| `sped.operacao` empty names | `name`/`codigo` fields appear blank via API; use `display_name` instead |
| Vendedor on items | `vendedor_id` on `sped.documento.item` is often False. Look up from order via `pedido_id` mapping |
| 2025 orders in Odoo | Only 65 records (all Venda Antecipada placed in 2025). True 2025 data is CIGAM-only |
| **NF-e level, not order level** | The Faturamento report queries `sped.documento` directly. OS items have `pedido_id=False` on `sped.documento.item` — linked only via `documento_id`. Must query at NF-e level to match report totals. |
| **Only `autorizada` NF-es** | Report excludes `inutilizada`, `em_digitacao`, `a_enviar` NF-es |
| **Orphan devoluções excluded** | Devoluções with `pedido_id=False` can't be assigned to a vendedor and are excluded from the report |
| **No `devolucao_venda` pedido.documento** | Zero `pedido.documento` records have `tipo=devolucao_venda`. All returns are standalone `sped.documento` NF-es with `operacao_id in [41,46,42]` |
| Devolução vr_nf sign | `sped.documento.item.vr_nf` is stored positive even for returns. Apply `-abs(vr_nf)` to make devoluções reduce net revenue |
| `relatorio.executa.pedido.documento` | Report wizard/config model, not transactional data |

---

## Vendedor Mapping

`outputs/csv/vendedor_mapping.csv` — manually curated CIGAM ↔ Odoo rep name matches.

Columns: `cigam_representante`, `odoo_vendedor_id`, `match_type`

`match_type` values:
- `exact` — confirmed match, used in merge
- `partial` — confirmed match, used in merge
- `no_match` — CIGAM-only rep with no Odoo equivalent (kept as-is)

To add a new match: edit the CSV, set `match_type` to `exact`, re-run `cigam_append.py`.

---

## Performance

| Step | Records | Time | Batching |
|---|---|---|---|
| extract_odoo_2026.py NF-es | ~3,500 | ~3 min | 200/page, 0.25s |
| extract_odoo_2026.py items | ~6,700 | included | 100 NF-e IDs/call |
| extract_odoo_2026.py vendedores | ~3,450 | included | 100 order IDs/call |
| extract_odoo_2026.py familia | ~1,400 products | included | 100 products/call |
| cigam_append.py Excel load | 117,029 rows | ~60s | single read |
| cigam_append.py vendedor match | 31 unique reps | <1s | vectorised |
| Dashboard first load | ~124,000 rows | ~2s | cached 1h |
