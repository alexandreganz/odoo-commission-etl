# Investigation Context — Odoo Faturamento Report Logic

## Validated Query Logic

The Faturamento - Geral report queries at the **NF-e level** (`sped.documento`), NOT at the order level (`pedido.documento`). This was validated against official reports for February and March 2026 with **R$ 0.00 delta**.

### Query

```python
sped.documento WHERE:
    operacao_id   IN [1, 2, 29, 38, 40, 41, 42, 46]   # sales + devolução fiscal ops
    empresa_id    = 1                                    # Santa Inês
    data_emissao  BETWEEN '2026-01-01' AND '2026-12-31'
    situacao_nfe  = 'autorizada'
    pedido_id     != False                               # exclude orphan devoluções
```

Then:
- Items via `sped.documento.item.documento_id`
- Vendedor via `sped.documento.pedido_id` → `pedido.documento.vendedor_id`
- Familia via `sped.produto.familia_id`

### Classification
- **Devolução**: `operacao_id in [41, 42, 46]` → `vr_nf` stored as negative
- **OS**: `pedido_tipo = 'os'` on `sped.documento`
- **Venda**: everything else

---

## Validation Results

### March 2026 (empresa_id=1)
| Metric | Report | Our Query | Delta |
|---|---|---|---|
| Venda | R$ 1,084,071.53 | R$ 1,084,071.53 | R$ 0.00 |
| OS | R$ 8,618.70 | R$ 8,618.70 | R$ 0.00 |
| Devolução | −R$ 1,010,638.50 | −R$ 1,010,638.50 | R$ 0.00 |
| **NET** | **R$ 82,051.73** | **R$ 82,051.73** | **R$ 0.00** |

### February 2026 (empresa_id=1)
All 15 vendedores match exactly (R$ 0.00 delta each).
Report total: R$ 1,523,048.82 — matched.
One orphan devolução (NF-e #58881, R$ −19,004.30) exists in API but is excluded because `pedido_id=False`.

---

## Key Discoveries

1. **NF-e level, not order level** — The report queries `sped.documento` directly, not `pedido.documento`.
2. **Only `autorizada` NF-es** — Excludes `inutilizada`, `em_digitacao`, `a_enviar`.
3. **OS items linked via `documento_id` only** — OS items on `sped.documento.item` have `pedido_id=False`. They're connected to their order only via the NF-e's `pedido_id`.
4. **OS filtering by NF-e operation** — `op=7` (Assistência técnica) is NOT in the report's fiscal operation filter. Only ops 1,2 are included for OS NF-es, which is why OS totals differ when querying at order level vs NF-e level.
5. **No `devolucao_venda` on pedido.documento** — Zero records exist. All returns are standalone `sped.documento` NF-es.
6. **Orphan devoluções excluded** — Devoluções with `pedido_id=False` can't be assigned to a vendedor and don't appear in the report.
7. **vr_nf for devoluções is positive in DB** — Must apply `-abs(vr_nf)` in ETL.

---

## Odoo Model Relationships

```
pedido.documento          (Sales Order)
  ├─ tipo                 'venda' | 'os'   (NO 'devolucao_venda' exists)
  ├─ operacao_produto_id → sped.operacao   (fiscal op: 1=Venda, 2=Rural, etc.)
  ├─ operacao_id         → pedido.operacao (workflow: 9=Venda NF-e, 25=VendaAnt, 30=NFC-e)
  ├─ vendedor_id
  ├─ data_contabil
  ├─ empresa_id           1=Santa Inês, 2=Bacabal
  └─ sped_documento_ids  → sped.documento  (linked NF-es)

sped.documento            (NF-e Fiscal Document)
  ├─ operacao_id         → sped.operacao   (41=Devolução, 46=DevRural, 42=Estorno, 7=AssistTec)
  ├─ pedido_id           → pedido.documento (original order — vendedor lookup)
  ├─ pedido_tipo          'venda' | 'os' | None
  ├─ data_emissao         ← use for date filtering
  ├─ situacao_nfe         'autorizada' | 'inutilizada' | 'em_digitacao' | 'a_enviar'
  └─ empresa_id

sped.documento.item       (NF-e Line Item)
  ├─ pedido_id           → pedido.documento (False for OS and devolução items!)
  ├─ documento_id        → sped.documento   (the NF-e this item belongs to)
  ├─ produto_id, produto_codigo, produto_nome, ncm
  └─ quantidade, vr_unitario, vr_nf         (vr_nf always positive in DB)
```

---

## sped.operacao IDs Reference

| id | name | In report filter |
|---|---|---|
| 1 | Venda de mercadoria | ✅ |
| 2 | Venda para Produtor Rural | ✅ |
| 29 | Venda Antecipada - Entrega Futura p/ Produtor Rural | ✅ |
| 38 | Venda de mercadoria (NFC-e) | ✅ |
| 40 | Venda Antecipada - Entrega Futura | ✅ |
| 41 | Devolução de venda | ✅ |
| 42 | Estorno de venda futura | ✅ |
| 46 | Devolução de Venda para Produtor Rural | ✅ |
| 7 | Assistência técnica | ❌ |
| 30 | Remessa Bonificação, Doação ou Brinde | ❌ |
| 31 | Remessa de Venda Antecipada p/ Produtor Rural | ❌ |
| 45 | Remessa de Venda Antecipada | ❌ |
