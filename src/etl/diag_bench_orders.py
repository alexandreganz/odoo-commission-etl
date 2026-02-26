"""
Diagnostic: Show ALL rows in Teste.xlsx for specific PV- orders.

Helps understand:
  - Which orders appear positive vs negative in the benchmark
  - Whether PV-0511/26, PV-0520/26 appear at all
  - How Richard's PV-0743/26 / PV-0747/26 appear (they should be negative)
"""
import sys
from pathlib import Path
from collections import defaultdict

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import openpyxl

BENCH = project_root / "Teste.xlsx"

# Orders we want to inspect closely
TARGET_ORDERS = [
    # Ariadne - ETL adds negatives that benchmark doesn't have
    'PV-0511/26', 'PV-0520/26',
    # Richard/Tayro - benchmark has negatives that ETL misses
    'PV-0743/26', 'PV-0747/26', 'PV-0968/26',
    # A known-correct negative (Elivelton) for comparison
    'PV-0152/26',
    # Alessandro's problematic orders
    'PV-0166/26',
]


def run():
    wb = openpyxl.load_workbook(BENCH, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    # Find header row
    header_row = None
    for i, row in enumerate(rows):
        cells = [str(c).strip().lower() for c in row if c is not None]
        if any("pedido" in c for c in cells) and any("aprov" in c for c in cells):
            header_row = i
            break

    print(f"Header row index: {header_row}")
    print(f"Header: {[str(c) for c in rows[header_row] if c is not None]}\n")

    current_vend = None
    # order -> list of row dicts
    by_order = defaultdict(list)

    for i, row in enumerate(rows):
        if i <= header_row:
            continue

        cell0 = str(row[0]).strip() if row[0] is not None else ""

        if cell0.lower().startswith("vendedor:"):
            current_vend = cell0.split(":", 1)[1].strip()
            continue
        if cell0.lower().startswith("tipo:"):
            continue
        if not cell0.startswith("PV-"):
            continue

        pedido   = cell0
        data_apr = row[1]
        cliente  = str(row[2]).strip() if row[2] is not None else ""
        data_fin = row[3]
        prod_cod = str(row[4]).strip() if row[4] is not None else ""
        prod_nom = str(row[5]).strip() if row[5] is not None else ""
        qtd      = row[6]
        valor    = row[7]
        comissao = row[8]

        try:
            valor_f    = float(valor)
            comissao_f = float(comissao) if comissao is not None else 0.0
        except (TypeError, ValueError):
            continue

        by_order[pedido].append({
            'vendedor':  current_vend,
            'data_apr':  data_apr,
            'data_fin':  data_fin,
            'prod_cod':  prod_cod,
            'prod_nom':  prod_nom,
            'qtd':       qtd,
            'valor':     valor_f,
            'comissao':  comissao_f,
        })

    # Print details for target orders
    for order in TARGET_ORDERS:
        rows_for = by_order.get(order, [])
        total_val = sum(r['valor'] for r in rows_for)
        total_com = sum(r['comissao'] for r in rows_for)
        print(f"{'='*70}")
        print(f"  {order}  ({len(rows_for)} rows)  total_valor={total_val:,.2f}  total_comissao={total_com:,.4f}")
        if rows_for:
            vend = rows_for[0]['vendedor']
            print(f"  vendedor: {vend}")
        print(f"  {'prod_cod':<12} {'qtd':>8} {'valor':>12} {'comissao':>12}  {'data_apr':<12}  {'data_fin':<12}  prod_nom")
        for r in rows_for:
            print(f"  {r['prod_cod']:<12} {str(r['qtd']):>8} {r['valor']:>12,.2f} {r['comissao']:>12,.4f}  {str(r['data_apr']):<12}  {str(r['data_fin']):<12}  {r['prod_nom'][:40]}")
        if not rows_for:
            print("  *** NOT FOUND IN BENCHMARK ***")

    # Summary: which target orders exist
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    for order in TARGET_ORDERS:
        rows_for = by_order.get(order, [])
        total_val = sum(r['valor'] for r in rows_for)
        neg_rows  = [r for r in rows_for if r['valor'] < 0]
        pos_rows  = [r for r in rows_for if r['valor'] >= 0]
        print(f"{order:<18}  rows={len(rows_for):>3}  pos={len(pos_rows):>3}  neg={len(neg_rows):>3}  total={total_val:>12,.2f}")


if __name__ == '__main__':
    run()
