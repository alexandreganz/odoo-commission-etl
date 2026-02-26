"""
Diagnostic: Fetch specific orders that appear as NEGATIVE in the benchmark.
Shows their operacao_id, etapa_tag_ids, vr_comissao, and item vr_nf totals.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.etl.odoo_client import OdooClient
from config.settings import Config

# The 18 orders that appear as negative in Teste.xlsx
NEGATIVE_ORDERS = [
    'PV-0152/26', 'PV-0166/26', 'PV-0483/26', 'PV-0497/26', 'PV-0525/26',
    'PV-0624/26', 'PV-0743/26', 'PV-0747/26', 'PV-0787/26', 'PV-0788/26',
    'PV-0965/26', 'PV-0968/26', 'PV-1373/26', 'PV-1460/26', 'PV-1649/26',
    'PV-1950/26', 'PV-2122/26', 'PV-2765/26',
]


def run():
    client = OdooClient()
    config = Config()
    uid, _ = client.authenticate()
    print(f"Authenticated as UID {uid}\n")

    fields = [
        'numero', 'vendedor_id', 'participante_id',
        'operacao_id', 'etapa_tag_ids',
        'vr_comissao', 'item_ids',
        'data_aprovacao',
    ]
    item_fields = ['vr_nf', 'produto_codigo']

    domain = [('numero', 'in', NEGATIVE_ORDERS)]
    orders = client.execute_kw(
        config.MAIN_MODEL, 'search_read', [domain],
        {'fields': fields},
    )

    print(f"Found {len(orders)} of {len(NEGATIVE_ORDERS)} expected orders\n")
    print(f"{'Pedido':<18} {'Etapa':<10} {'Operacao':<50} {'VrComissao':>10}  {'VrNF_total':>12}  {'Vendedor'}")
    print("-" * 130)

    for o in sorted(orders, key=lambda x: x['numero']):
        etapas  = o.get('etapa_tag_ids', [])
        op      = client.clean_value(o.get('operacao_id')) or '(none)'
        vend    = client.clean_value(o.get('vendedor_id')) or ''
        com     = float(o.get('vr_comissao') or 0)

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

        vend_short = vend.split(' [')[0][:30]
        print(f"{o['numero']:<18} {str(etapas):<10} {op:<50} {com:>10,.2f}  {nf_total:>12,.2f}  {vend_short}")

    # Check if any are etapa=60
    etapa60 = [o for o in orders if 60 in o.get('etapa_tag_ids', [])]
    print(f"\nOrders with etapa=60: {len(etapa60)}")
    for o in etapa60:
        op = client.clean_value(o.get('operacao_id')) or '(none)'
        print(f"  {o['numero']}  etapas={o['etapa_tag_ids']}  op={op}")

    # Show the unique operacao_ids among these negative orders
    ops = set(client.clean_value(o.get('operacao_id')) or '(none)' for o in orders)
    print(f"\nUnique operacao_ids in negative orders:")
    for op in sorted(ops):
        print(f"  '{op}'")


if __name__ == '__main__':
    run()
