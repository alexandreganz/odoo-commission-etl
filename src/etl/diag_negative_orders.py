"""
Diagnostic: Identify non-etapa-60 PV- orders for January 2026.

Shows what operacao_id, etapa, vendedor, and total values those
orders carry — so we know which ones the benchmark includes as
negative commission adjustments.
"""
import sys
from pathlib import Path
from collections import defaultdict

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.etl.odoo_client import OdooClient
from config.settings import Config

ETAPA_APROVADO = 60

def run():
    client = OdooClient()
    config  = Config()
    uid, _  = client.authenticate()
    print(f"Authenticated as UID {uid}\n")

    domain = [
        ('data_aprovacao', '>=', '2026-01-01'),
        ('data_aprovacao', '<=', '2026-01-31'),
        ('numero', 'like', 'PV-'),
    ]

    order_fields = [
        'numero', 'vendedor_id', 'participante_id',
        'operacao_id', 'etapa_tag_ids',
        'vr_comissao', 'item_ids',
    ]
    item_fields = ['vr_nf']

    # --- collect all non-etapa-60 orders ---
    non60 = []      # list of dicts
    offset = 0
    batch  = 100

    while True:
        orders = client.execute_kw(
            config.MAIN_MODEL, 'search_read', [domain],
            {'fields': order_fields, 'limit': batch, 'offset': offset},
        )
        if not orders:
            break

        for o in orders:
            etapas = o.get('etapa_tag_ids', [])
            if ETAPA_APROVADO in etapas:
                continue          # keep only non-60 orders
            non60.append(o)

        offset += batch

    print(f"Total non-etapa-60 PV- orders found: {len(non60)}\n")

    # --- summarise by operacao_id ---
    by_op = defaultdict(lambda: {'orders': 0, 'vr_comissao': 0.0, 'vr_nf': 0.0, 'etapas': set(), 'vendedores': set()})

    for o in non60:
        op     = client.clean_value(o.get('operacao_id')) or '(none)'
        etapas = str(o.get('etapa_tag_ids', []))
        vend   = client.clean_value(o.get('vendedor_id')) or ''
        com    = float(o.get('vr_comissao') or 0)

        # Get item total value
        item_ids = o.get('item_ids', [])
        nf_total = 0.0
        if item_ids:
            try:
                items = client.execute_kw(
                    config.ITEM_MODEL, 'read', [item_ids], {'fields': item_fields}
                )
                nf_total = sum(float(i.get('vr_nf') or 0) for i in items)
            except Exception:
                pass

        by_op[op]['orders']     += 1
        by_op[op]['vr_comissao'] += com
        by_op[op]['vr_nf']       += nf_total
        by_op[op]['etapas'].add(etapas)
        by_op[op]['vendedores'].add(vend.split(' [')[0][:40])

    print("=== Summary by operacao_id ===")
    print(f"{'Operacao':<45} {'Orders':>6} {'Valor NF':>14} {'Comissao':>12}  Etapas")
    print("-" * 100)
    for op, s in sorted(by_op.items(), key=lambda x: -x[1]['vr_nf']):
        print(f"{op:<45} {s['orders']:>6} {s['vr_nf']:>14,.2f} {s['vr_comissao']:>12,.2f}  {s['etapas']}")

    # --- per-vendedor breakdown ---
    print("\n=== Per-Vendedor breakdown (non-etapa-60) ===")
    by_vend = defaultdict(lambda: {'orders': 0, 'vr_nf': 0.0, 'vr_comissao': 0.0, 'nums': []})
    for o in non60:
        vend = client.clean_value(o.get('vendedor_id')) or '(none)'
        vend = vend.split(' [')[0][:40]
        by_vend[vend]['orders']     += 1
        by_vend[vend]['vr_comissao'] += float(o.get('vr_comissao') or 0)
        by_vend[vend]['nums'].append(o.get('numero', ''))

        item_ids = o.get('item_ids', [])
        if item_ids:
            try:
                items = client.execute_kw(
                    config.ITEM_MODEL, 'read', [item_ids], {'fields': item_fields}
                )
                by_vend[vend]['vr_nf'] += sum(float(i.get('vr_nf') or 0) for i in items)
            except Exception:
                pass

    print(f"{'Vendedor':<45} {'Orders':>6} {'Valor NF':>14} {'Comissao':>12}")
    print("-" * 80)
    for v, s in sorted(by_vend.items(), key=lambda x: -x[1]['vr_nf']):
        nums_str = ', '.join(s['nums'][:5])
        if len(s['nums']) > 5:
            nums_str += f"... (+{len(s['nums'])-5})"
        print(f"{v:<45} {s['orders']:>6} {s['vr_nf']:>14,.2f} {s['vr_comissao']:>12,.2f}  [{nums_str}]")

    # --- sample a few specific records ---
    print("\n=== First 10 non-etapa-60 orders (detail) ===")
    for o in non60[:10]:
        op    = client.clean_value(o.get('operacao_id')) or '(none)'
        vend  = client.clean_value(o.get('vendedor_id')) or ''
        vend  = vend.split(' [')[0][:35]
        com   = float(o.get('vr_comissao') or 0)
        etaps = o.get('etapa_tag_ids', [])
        print(f"  {o['numero']:<20}  op={op[:35]:<35}  etapa={etaps}  vend={vend}  com={com:,.2f}")


if __name__ == '__main__':
    run()
