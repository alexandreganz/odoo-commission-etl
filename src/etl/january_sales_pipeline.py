"""
January 2026 Sales ETL Pipeline — Comissões

Extracts sales data for January 2026 from Odoo:
- Filter: data_aprovacao in [2026-01-01, 2026-01-31] AND order type = Venda (PV-)
- Order fields: numero, vendedor, cliente, data_aprovacao, data_financeiro, vr_comissao
- Item fields:  produto_codigo, produto_id (name), quantidade, vr_nf
- Commission: al_comissao_vr_nf (rate %) applied per sped.documento item

Sign logic (via sped.documento.finalidade_nfe):
  1 = normal NF-e       → positive  (only etapa=60 orders)
  3 = estorno/reversal  → negative
  4 = return/devolução  → negative

Output: outputs/csv/january_sales.csv
"""

import csv
import time
from datetime import datetime
from pathlib import Path
import sys
from collections import defaultdict

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.etl.odoo_client import OdooClient
from config.settings import Config


def _clean_name(raw: str) -> str:
    """
    Normalize Odoo display names to match the benchmark.

    Odoo formats:
      "Name - ALIAS - Name"         -> "Name - ALIAS"   (name repeated at end)
      "Name [XX.XXX.XXX/XXXX-XX]"  -> "Name"            (CNPJ bracket suffix)
    """
    name = raw.split(' [')[0].strip()
    parts = name.split(' - ')
    if len(parts) >= 3 and parts[0].strip().lower() == parts[-1].strip().lower():
        name = ' - '.join(parts[:-1])
    return name.strip()


# finalidade_nfe values for sign determination
# NOTE: Odoo XML-RPC returns selection fields as strings, not integers
FINALIDADE_POSITIVA = {'1'}           # Normal sale NF-e
FINALIDADE_NEGATIVA = {'3', '4'}      # Estorno (3) or Devolucao (4)
SITUACAO_SKIP       = {'cancelada', 'denegada', 'inutilizada'}
ETAPA_APROVADO      = 60


def run_january_sales_pipeline():
    """Extract January 2026 sales with sign-aware commission from sped.documento."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting January Sales ETL Pipeline...")

    client = OdooClient()
    config  = Config()

    try:
        uid, _ = client.authenticate()
        print(f"Authenticated as user ID: {uid}")
    except Exception as e:
        print(f"Authentication failed: {e}")
        return

    # ── Fields ────────────────────────────────────────────────────────────────
    order_fields = [
        'numero',               # PV-0122/26
        'vendedor_id',          # Many2one
        'participante_id',      # Many2one
        'data_aprovacao',       # date
        'data_financeiro',      # date
        'al_comissao_vr_nf',    # Commission rate % on NF value
        'vr_comissao',          # Fallback total commission (proportional distribution)
        'etapa_tag_ids',        # Workflow stage IDs (filter finalidade=1 to etapa=60 only)
        'sped_documento_ids',   # All linked fiscal NF-e documents
    ]

    sped_fields = [
        'id',
        'finalidade_nfe',       # 1=normal, 3=estorno, 4=devolucao
        'situacao_nfe',         # autorizada / cancelada / denegada / inutilizada
        'item_ids',             # sped.documento.item IDs
        'vr_nf',                # Total NF value (for proportional fallback)
    ]

    item_fields = [
        'produto_codigo',   # Product code
        'produto_id',       # Product name (Many2one -> [ID, 'Name'])
        'quantidade',       # Quantity
        'vr_nf',            # Item NF value (BRL)
    ]

    headers = [
        'pedido', 'vendedor', 'cliente',
        'data_aprovacao', 'data_financeiro',
        'produto_codigo', 'produto_nome',
        'quantidade', 'valor', 'comissao',
    ]

    # ── Domain: ALL PV- January orders regardless of etapa ────────────────────
    # etapa filtering is handled per-sped-doc (finalidade=1 requires etapa=60)
    domain = [
        ('data_aprovacao', '>=', '2026-01-01'),
        ('data_aprovacao', '<=', '2026-01-31'),
        ('numero', 'like', 'PV-'),
    ]

    # ── Output setup ──────────────────────────────────────────────────────────
    output_dir  = Path(config.OUTPUT_DIR) / 'csv'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'january_sales.csv'

    print(f"Extracting to {output_file}...")
    print(f"   Filter: data_aprovacao 2026-01-01 to 2026-01-31, tipo=Venda (PV-)")
    print(f"   Sign logic: finalidade=1+etapa60 -> positive | finalidade=3,4 -> negative")

    total_orders   = 0
    total_items    = 0
    skipped_orders = 0
    start_time     = time.time()

    with open(output_file, mode='w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()

        offset     = 0
        batch_size = 50

        while True:
            # ── Fetch order batch ──────────────────────────────────────────────
            try:
                orders = client.execute_kw(
                    config.MAIN_MODEL,
                    'search_read',
                    [domain],
                    {'fields': order_fields, 'limit': batch_size, 'offset': offset},
                )
            except Exception as e:
                print(f"Error fetching orders at offset {offset}: {e}")
                break

            if not orders:
                break

            print(f"   Orders {offset} - {offset + len(orders) - 1} ({len(orders)} records)...")
            total_orders += len(orders)

            # ── Batch-read all sped.documentos for this order batch ────────────
            all_sped_ids  = []
            sped_to_order = {}  # sped_id -> order dict

            for order in orders:
                for sid in order.get('sped_documento_ids', []):
                    all_sped_ids.append(sid)
                    sped_to_order[sid] = order

            sped_docs_map = {}  # sped_id -> sped_doc dict
            if all_sped_ids:
                try:
                    sped_docs = client.execute_kw(
                        'sped.documento', 'read',
                        [all_sped_ids],
                        {'fields': sped_fields},
                    )
                    sped_docs_map = {d['id']: d for d in sped_docs}
                except Exception as e:
                    print(f"   sped.documento batch read error: {e}")

            # ── Group sped docs by order ───────────────────────────────────────
            speds_by_order = defaultdict(list)
            for sid, sped in sped_docs_map.items():
                order = sped_to_order.get(sid)
                if order:
                    speds_by_order[order['id']].append(sped)

            # ── Collect all item_ids that will be needed (for batch read) ──────
            included_sped_ids = []  # (sped_id, sign)
            for order in orders:
                etapas = order.get('etapa_tag_ids', [])
                for sped in speds_by_order.get(order['id'], []):
                    situacao   = sped.get('situacao_nfe') or ''
                    finalidade = str(sped.get('finalidade_nfe') or '')
                    if situacao in SITUACAO_SKIP:
                        continue
                    if finalidade in FINALIDADE_POSITIVA:
                        if ETAPA_APROVADO not in etapas:
                            continue
                        sign = 1
                    elif finalidade in FINALIDADE_NEGATIVA:
                        sign = -1
                    else:
                        continue
                    included_sped_ids.append((sped['id'], sign))

            all_item_ids = []
            for sid, _ in included_sped_ids:
                all_item_ids.extend(sped_docs_map[sid].get('item_ids', []))

            items_map = {}  # item_id -> item dict
            if all_item_ids:
                try:
                    items_batch = client.execute_kw(
                        config.ITEM_MODEL, 'read',
                        [all_item_ids],
                        {'fields': item_fields},
                    )
                    items_map = {i['id']: i for i in items_batch}
                except Exception as e:
                    print(f"   items batch read error: {e}")

            # ── Write rows ────────────────────────────────────────────────────
            for order in orders:
                etapas          = order.get('etapa_tag_ids', [])
                al_comissao     = float(order.get('al_comissao_vr_nf') or 0)
                vr_comissao_tot = float(order.get('vr_comissao') or 0)
                pedido          = order.get('numero', '')
                vendedor        = _clean_name(client.clean_value(order.get('vendedor_id')))
                cliente         = _clean_name(client.clean_value(order.get('participante_id')))
                data_aprovacao  = order.get('data_aprovacao') or ''
                data_financeiro = order.get('data_financeiro') or ''

                order_had_rows = False

                for sped in speds_by_order.get(order['id'], []):
                    situacao   = sped.get('situacao_nfe') or ''
                    finalidade = str(sped.get('finalidade_nfe') or '')

                    if situacao in SITUACAO_SKIP:
                        continue

                    if finalidade in FINALIDADE_POSITIVA:
                        if ETAPA_APROVADO not in etapas:
                            continue
                        sign = 1
                    elif finalidade in FINALIDADE_NEGATIVA:
                        sign = -1
                    else:
                        continue

                    item_ids_sped = sped.get('item_ids', [])
                    if not item_ids_sped:
                        continue

                    items = [items_map[iid] for iid in item_ids_sped if iid in items_map]
                    if not items:
                        continue

                    # Total vr_nf of this sped doc (proportional fallback)
                    total_vr_sped = sum(float(i.get('vr_nf') or 0) for i in items)

                    for item in items:
                        vr_nf      = float(item.get('vr_nf') or 0)
                        prod_cod   = item.get('produto_codigo', '') or ''
                        prod_nom   = client.clean_value(item.get('produto_id'))
                        quantidade = float(item.get('quantidade', 0) or 0)

                        # Commission: rate-based (preferred) or proportional fallback
                        if al_comissao > 0:
                            comissao_item = round(vr_nf * al_comissao / 100, 4)
                        elif total_vr_sped > 0:
                            comissao_item = round((vr_nf / total_vr_sped) * vr_comissao_tot, 4)
                        else:
                            comissao_item = 0.0

                        writer.writerow({
                            'pedido':          pedido,
                            'vendedor':        vendedor,
                            'cliente':         cliente,
                            'data_aprovacao':  data_aprovacao,
                            'data_financeiro': data_financeiro,
                            'produto_codigo':  prod_cod,
                            'produto_nome':    prod_nom,
                            'quantidade':      quantidade * sign,
                            'valor':           round(vr_nf * sign, 4),
                            'comissao':        round(comissao_item * sign, 4),
                        })
                        total_items   += 1
                        order_had_rows = True

                if not order_had_rows:
                    skipped_orders += 1

            offset += batch_size
            time.sleep(0.1)  # Respect API rate limit

    elapsed = time.time() - start_time
    print(f"\nJanuary Sales ETL Complete!")
    print(f"   Orders fetched:           {total_orders}")
    print(f"   Line items written:       {total_items}")
    print(f"   Orders skipped (no rows): {skipped_orders}")
    print(f"   Time elapsed:             {elapsed:.2f}s")
    print(f"   Output:                   {output_file}")
    return output_file


if __name__ == "__main__":
    run_january_sales_pipeline()
