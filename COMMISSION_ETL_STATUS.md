# Commission ETL — January 2026 — Status & Handover

> **Last updated:** 2026-02-26
> **Goal:** Exact match between `outputs/csv/january_sales.csv` (ETL) and `Teste.xlsx` (benchmark)
> **Current status:** ~2,369 / 2,378 benchmark rows matched — 6 vendedores still diverge

---

## 1. What Was Built

### ETL Pipeline
`src/etl/january_sales_pipeline.py`

Extracts January 2026 PV- sales with **sign-aware commission** from Odoo via XML-RPC.

**Key logic:**
1. Fetch all `pedido.documento` records where `data_aprovacao` in [2026-01-01, 2026-01-31] AND `numero` like `PV-`
2. For each order, batch-read its `sped_documento_ids` (fiscal NF-e documents via `sped.documento`)
3. For each sped doc, apply sign:
   - `finalidade_nfe = '1'` (normal sale) **AND** `etapa_tag_ids` contains `60` → **POSITIVE**
   - `finalidade_nfe = '3'` (estorno/reversal) → **NEGATIVE**
   - `finalidade_nfe = '4'` (devolução/return) → **NEGATIVE**
   - `situacao_nfe` in `{'cancelada', 'denegada', 'inutilizada'}` → **SKIP**
4. Commission = `vr_nf_item * al_comissao_vr_nf / 100` (rate-based) or proportional fallback

**Critical note:** Odoo XML-RPC returns `finalidade_nfe` as a **string** (`'1'`, `'3'`, `'4'`), NOT integer.

### Dashboard Page
`dashboard/pages/5_comissoes_janeiro.py`

4-tab Streamlit page:
- **Tab 1 – Odoo (ETL):** live data from `outputs/csv/january_sales.csv`
- **Tab 2 – Benchmark:** parsed from `Teste.xlsx`
- **Tab 3 – Comparação:** per-vendedor and per-pedido delta table
- **Tab 4 – Gráficos:** bar charts, scatter plot

### Diagnostic Scripts (`src/etl/diag_*.py`)
| Script | Purpose |
|---|---|
| `diag_bench_negatives.py` | Parse Teste.xlsx, find all negative rows (found 36 rows across 18 orders) |
| `diag_bench_orders.py` | Show ALL rows in benchmark for specific order numbers (with dates) |
| `diag_negative_orders.py` | Find all non-etapa-60 PV- orders in Odoo (found 263) |
| `diag_specific_orders.py` | Fetch the 18 benchmark-negative orders from Odoo API |
| `diag_sped_dates.py` | **NEXT STEP** — check `data_emissao` of sped docs for problem orders |

---

## 2. Current Match Status

### Vendedores with exact match (0 delta)
Most vendedores now match perfectly. The bulk of data is correct.

### Vendedores still diverging

| Vendedor | Δ Valor (ETL − Bench) | Problem | Specific Orders |
|---|---|---|---|
| Richard Feuerstein | **+83,081** | ETL *missing* negatives | PV-0743/26, PV-0747/26 |
| Ariadne Vecanandre | **−59,050** | ETL *adds wrong* negatives | PV-0511/26, PV-0520/26 |
| Tayro Ribeir Pancera | **+5,310** | ETL *missing* negative | PV-0968/26 |
| Alessandro Alves Dutra | **−3,739** | ETL *adds wrong* negatives | TBD — needs investigation |
| Henrique Dias | **−303** | ETL *adds wrong* negative | TBD |
| Jackson | **−50** | ETL *adds wrong* negative | TBD |

---

## 3. The Two Unsolved Problems

### Problem A — Missing negatives (Richard, Tayro)

**Orders:** PV-0743/26 (etapa=6, "V - Cancelado"), PV-0747/26 (etapa=108), PV-0968/26

**What happens:**
- These orders have **only `finalidade_nfe='1'`** (normal sale) sped docs — no estorno (fin=3) or return (fin=4) docs
- The benchmark shows them as **fully negative** with negative quantities
- The ETL currently skips fin=1 docs for non-etapa-60 orders (correct for active sales, wrong for canceled ones)

**Working hypothesis:**
> For **non-etapa-60 orders** with a fin=1 sped doc whose `data_emissao` is in January 2026, the commission report shows them as **NEGATIVE** (commission reversal). These are canceled/non-delivered orders that had commission previously counted, and January is when the reversal is recorded.

**Fix to implement (once server is up):**
1. Run `diag_sped_dates.py` to confirm: do PV-0743/26 and PV-0747/26 have a fin=1 doc with `data_emissao` in January?
2. If yes, add rule to ETL: `finalidade='1'` + **NOT** etapa=60 + `data_emissao` in January → include as **NEGATIVE**

---

### Problem B — Wrong negatives (Ariadne, Alessandro, Henrique, Jackson)

**Orders:** PV-0511/26, PV-0520/26 (Ariadne), plus TBD orders for others

**What happens:**
- These are etapa=60 orders that have a fin=4 (devolução/return) sped doc in January
- The ETL correctly includes their fin=1 sale as positive ✓
- The ETL **also** includes their fin=4 doc as negative ← this is WRONG for these specific orders
- The benchmark shows them as **positive only** (no negative return)

**Contrast with PV-0152/26 (Elivelton — correct):**
- PV-0152/26 also has fin=1 + fin=4 in January
- Benchmark shows **both** positive AND negative (net = 0)
- This IS in the ETL correctly

**Key question:** Why does PV-0511/26's fin=4 get excluded from the benchmark while PV-0152/26's fin=4 gets included?

**Working hypothesis:**
> The fin=4 return doc for PV-0511/26 and PV-0520/26 is likely **returning products from a previous period** (December 2025 NF-e), not from the January sale. The commission report excludes cross-period returns. For PV-0152/26, the fin=4 returns products that were sold in the **same period** (January), so both appear.

**How to verify (once server is up):**
1. Run `diag_sped_dates.py` — check `data_emissao` of the fin=4 docs for PV-0511/26 and PV-0520/26
2. Check if there is a **referenced NF-e field** on those fin=4 docs (e.g., `chave_referenciada`, `documento_referenciado`) pointing to a December 2025 NF-e
3. Compare with PV-0152/26's fin=4 doc — does it reference a January NF-e?

**If the fin=4 items are different products from PV-0511/26's fin=1 items**, that also confirms the cross-period theory.

---

## 4. Files Reference

```
Odoo/
├── Teste.xlsx                              # Benchmark file (DO NOT MODIFY)
├── src/
│   └── etl/
│       ├── odoo_client.py                  # Shared XML-RPC client
│       ├── january_sales_pipeline.py       # MAIN ETL — run this to regenerate CSV
│       ├── diag_bench_negatives.py         # Parse benchmark negative rows
│       ├── diag_bench_orders.py            # Show specific orders in benchmark
│       ├── diag_negative_orders.py         # Find non-etapa-60 orders in Odoo
│       ├── diag_specific_orders.py         # Fetch specific orders from Odoo
│       └── diag_sped_dates.py              # CHECK SPED DATES — run this first when server is up
├── dashboard/
│   ├── app.py                              # Streamlit entry point
│   └── pages/
│       └── 5_comissoes_janeiro.py          # Commission comparison dashboard
├── outputs/
│   └── csv/
│       └── january_sales.csv               # ETL output (gitignored)
└── config/
    └── settings.py                         # Loads .env credentials
```

---

## 5. How to Run

### Re-run ETL (after server comes back up)
```bash
cd Odoo
python -m src.etl.january_sales_pipeline
# Output: outputs/csv/january_sales.csv
```

### Run the diagnostic (PRIORITY when server returns)
```bash
cd Odoo
python -m src.etl.diag_sped_dates
# Shows data_emissao for sped docs of all problem orders
# Key orders to check: PV-0511/26, PV-0520/26, PV-0743/26, PV-0747/26, PV-0968/26
```

### Launch dashboard
```bash
cd Odoo
python -m streamlit run dashboard/app.py
# Open http://localhost:8501
# Navigate to "Comissões Janeiro 2026" in sidebar
```

---

## 6. Odoo Data Model (relevant fields)

### `pedido.documento` (sales orders)
| Field | Type | Notes |
|---|---|---|
| `numero` | str | e.g. "PV-0511/26" |
| `data_aprovacao` | date | ETL filter: Jan 2026 |
| `data_financeiro` | date | Financial closing date |
| `vendedor_id` | Many2one | [id, "Name [CNPJ]"] |
| `participante_id` | Many2one | customer |
| `etapa_tag_ids` | Many2many int | workflow stage IDs — **60** = "V - Mercadoria entregue" (approved) |
| `al_comissao_vr_nf` | float | Commission rate % on NF value |
| `vr_comissao` | float | Total commission (fallback) |
| `sped_documento_ids` | One2many int | Linked NF-e fiscal docs |

### `sped.documento` (NF-e fiscal documents)
| Field | Type | Notes |
|---|---|---|
| `finalidade_nfe` | **string** | `'1'`=normal, `'3'`=estorno, `'4'`=devolução — NOTE: returned as string |
| `situacao_nfe` | str | `'autorizada'`, `'cancelada'`, `'denegada'`, `'inutilizada'` |
| `data_emissao` | date | NF-e issue date — KEY for period filtering |
| `vr_nf` | float | Total NF value |
| `item_ids` | One2many int | Line items |

### `sped.documento.item`
| Field | Type | Notes |
|---|---|---|
| `produto_codigo` | str | Product code |
| `produto_id` | Many2one | [id, "Name"] |
| `quantidade` | float | Quantity |
| `vr_nf` | float | Item NF value (BRL) |

### Etapa values (etapa_tag_ids)
| ID | Name | Meaning |
|---|---|---|
| 60 | V - Mercadoria entregue | Order fully approved/delivered — INCLUDE as POSITIVE |
| 6 | V - Cancelado | Canceled — may need NEGATIVE reversal |
| 108 | VF - Gerar nota | Pending NF generation — may need NEGATIVE reversal |
| 111 | VF - Fracionamento concluido | Partial delivery complete |

---

## 7. Commission Calculation Logic

```python
# For each sped.documento item:
if al_comissao_vr_nf > 0:
    # Rate-based (preferred)
    comissao_item = vr_nf_item * al_comissao_vr_nf / 100
else:
    # Proportional fallback using order-level vr_comissao
    comissao_item = (vr_nf_item / total_vr_sped) * vr_comissao_order

# Apply sign
comissao_final = comissao_item * sign   # sign = +1 or -1
valor_final    = vr_nf_item * sign
```

---

## 8. Server Notes

- **URL:** `agromaquinas.teste.tauga.online` (Tauga-hosted test instance)
- **Authentication:** XML-RPC via `config/.env` (ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD)
- **Current status:** Server returned 502 Bad Gateway on 2026-02-26, then went to connection refused
- **Cause:** Almost certainly NOT due to our API calls (~150-250 total requests, trivial for Odoo)
- **Fix:** Restart the Tauga test instance from their admin panel, or wait for auto-restart
- **To check:** Open `https://agromaquinas.teste.tauga.online/web/login` in browser

---

## 9. Next Steps (when server returns)

1. **Run `diag_sped_dates.py`** — get `data_emissao` of all sped docs for problem orders
2. **Check referenced NF-e** on fin=4 docs for PV-0511/26, PV-0520/26 — is `data_emissao` of their referenced original sale in December or January?
3. **Implement ETL fix A** (if hypothesis holds): add negative rule for non-etapa-60 orders with January fin=1 docs
4. **Implement ETL fix B**: exclude fin=4 docs that reference a previous-period sale
5. **Re-run ETL** and verify comparison tab shows 0 delta for all vendedores
6. **Close out** Alessandro/Henrique/Jackson remaining deltas
