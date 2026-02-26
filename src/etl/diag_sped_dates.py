"""
Diagnostic: Check sped.documento dates and fields for specific orders.

We need to understand:
  1. Why PV-0511/26, PV-0520/26 (Ariadne) - benchmark shows POSITIVE only,
     but ETL adds negative fin=4 rows. Are those fin=4 docs in a different month?
  2. Why PV-0743/26, PV-0747/26 (Richard) - benchmark shows NEGATIVE,
     but they only have fin=1 docs. What makes them appear as negative?
  3. Compare with PV-0152/26 (Elivelton) - benchmark has BOTH pos+neg correctly.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.etl.odoo_client import OdooClient
from config.settings import Config

ORDERS = [
    'PV-0511/26', 'PV-0520/26',   # Ariadne: benchmark pos-only, ETL adds wrong negatives
    'PV-0743/26', 'PV-0747/26',   # Richard: benchmark neg-only, ETL misses them
    'PV-0968/26',                  # Tayro: benchmark neg-only
    'PV-0152/26',                  # Elivelton: benchmark pos+neg (correct)
    'PV-0166/26',                  # Raimundo Vagner: benchmark neg-only
]

SPED_FIELDS = [
    'id', 'finalidade_nfe', 'situacao_nfe',
    'data_emissao',         # NF-e emission date
    'vr_nf',                # Total NF value
    'item_ids',
]

ORDER_FIELDS = [
    'numero', 'etapa_tag_ids', 'sped_documento_ids',
    'data_aprovacao', 'data_financeiro',
    'vendedor_id', 'al_comissao_vr_nf',
]


def run():
    client = OdooClient()
    config = Config()
    uid, _ = client.authenticate()
    print(f"Authenticated as UID {uid}\n")

    orders = client.execute_kw(
        config.MAIN_MODEL, 'search_read',
        [[ ('numero', 'in', ORDERS) ]],
        {'fields': ORDER_FIELDS},
    )

    for order in sorted(orders, key=lambda o: o['numero']):
        numero    = order['numero']
        etapas    = order.get('etapa_tag_ids', [])
        sped_ids  = order.get('sped_documento_ids', [])
        data_apr  = order.get('data_aprovacao', '')
        data_fin  = order.get('data_financeiro', '')
        rate      = float(order.get('al_comissao_vr_nf') or 0)

        print(f"{'='*70}")
        print(f"  {numero}  etapa={etapas}  data_apr={data_apr}  data_fin={data_fin}  al_com={rate}%")

        if not sped_ids:
            print(f"  *** NO sped_documento_ids ***")
            continue

        speds = client.execute_kw(
            'sped.documento', 'read',
            [sped_ids],
            {'fields': SPED_FIELDS},
        )

        for s in speds:
            fin  = s.get('finalidade_nfe', '?')
            sit  = s.get('situacao_nfe', '?')
            dt   = s.get('data_emissao', '?')
            vr   = float(s.get('vr_nf') or 0)
            n_it = len(s.get('item_ids', []))
            print(f"    sped={s['id']:>6}  fin={fin}  sit={sit:<15}  data_emissao={dt}  vr_nf={vr:>12,.2f}  items={n_it}")

    print()


if __name__ == '__main__':
    run()
