"""
Diagnostic: Parse Teste.xlsx and find all negative-value rows.

Shows which orders appear with negative valor/comissao in the benchmark
so we can understand the sign-inversion logic.
"""
import sys
from pathlib import Path
from collections import defaultdict

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import openpyxl

BENCH = project_root / "Teste.xlsx"

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

    print(f"Header row index: {header_row}\n")

    current_vend = None
    negative_rows = []
    all_rows = []

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

        pedido    = cell0
        data_apr  = row[1]
        cliente   = str(row[2]).strip() if row[2] is not None else ""
        data_fin  = row[3]
        prod_cod  = str(row[4]).strip() if row[4] is not None else ""
        prod_nom  = str(row[5]).strip() if row[5] is not None else ""
        qtd       = row[6]
        valor     = row[7]
        comissao  = row[8]

        try:
            valor_f    = float(valor)
            comissao_f = float(comissao) if comissao is not None else 0.0
        except (TypeError, ValueError):
            continue

        r = {
            'vendedor': current_vend,
            'pedido':   pedido,
            'produto':  prod_cod,
            'valor':    valor_f,
            'comissao': comissao_f,
        }
        all_rows.append(r)
        if valor_f < 0 or comissao_f < 0:
            negative_rows.append(r)

    print(f"Total rows in benchmark: {len(all_rows)}")
    print(f"Negative rows:           {len(negative_rows)}\n")

    # Group negative rows by vendedor
    by_vend = defaultdict(lambda: {'count': 0, 'valor': 0.0, 'comissao': 0.0, 'pedidos': []})
    for r in negative_rows:
        v = r['vendedor']
        by_vend[v]['count']    += 1
        by_vend[v]['valor']    += r['valor']
        by_vend[v]['comissao'] += r['comissao']
        if r['pedido'] not in by_vend[v]['pedidos']:
            by_vend[v]['pedidos'].append(r['pedido'])

    print("=== Negative rows per vendedor ===")
    print(f"{'Vendedor':<45} {'Rows':>5} {'Valor':>14} {'Comissao':>12}  Orders")
    print("-" * 100)
    for v, s in sorted(by_vend.items(), key=lambda x: x[1]['valor']):
        nums = ', '.join(s['pedidos'][:6])
        if len(s['pedidos']) > 6:
            nums += f"... (+{len(s['pedidos'])-6})"
        print(f"{v:<45} {s['count']:>5} {s['valor']:>14,.2f} {s['comissao']:>12,.4f}  [{nums}]")

    # Show full list of negative row order numbers
    print("\n=== All unique PV numbers with negative rows ===")
    neg_orders = sorted(set(r['pedido'] for r in negative_rows))
    for n in neg_orders:
        print(f"  {n}")


if __name__ == '__main__':
    run()
