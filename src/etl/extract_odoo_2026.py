"""
Extracts all 2026 Odoo sales data at the NF-e level (sped.documento).

This approach queries authorized NF-e fiscal documents directly, matching the
exact logic used by Odoo's "Faturamento - Geral" report. Validated against
official reports for Feb and March 2026 with R$ 0.00 delta.

Query logic:
  sped.documento WHERE:
    operacao_id IN [1,2,29,38,40, 41,42,46]   (sales + devolução ops)
    empresa_id  IN (1, 2)                      (Santa Inês + Bacabal)
    data_emissao BETWEEN '2026-01-01' AND '2026-12-31'
    situacao_nfe = 'autorizada'
    pedido_id   != False                       (exclude orphan devoluções)

  Items: sped.documento.item via documento_id
  Vendedor: pedido.documento.vendedor_id via sped.documento.pedido_id
  Familia: sped.produto.familia_id via item produto_id

Classification:
  - Devolução: operacao_id in [41, 42, 46] → vr_nf stored NEGATIVE
  - OS: pedido_tipo = 'os' on sped.documento
  - Venda: everything else

Fiscal operations included:
  1   Venda de mercadoria
  2   Venda para Produtor Rural
  29  Venda Antecipada - Entrega Futura p/ Produtor Rural
  38  Venda de mercadoria (NFC-e)
  40  Venda Antecipada - Entrega Futura
  41  Devolução de venda
  42  Estorno de venda futura
  46  Devolução de Venda para Produtor Rural

Batching: 200 NF-es/page, 100 IDs/item batch, 100 IDs/familia batch, 0.25s sleep

Output:
  outputs/csv/sales_items_odoo_2026.csv  (one row per NF-e item)
"""

import os
import time
import xmlrpc.client
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent
ITEMS_CSV    = PROJECT_ROOT / 'outputs' / 'csv' / 'sales_items_odoo_2026.csv'

SALE_OP_IDS  = [1, 2, 29, 38, 40]
DEVOL_OP_IDS = [41, 42, 46]
ALL_OP_IDS   = SALE_OP_IDS + DEVOL_OP_IDS

NFE_FIELDS   = ['id', 'numero', 'operacao_id', 'pedido_id', 'pedido_tipo',
                'data_emissao', 'empresa_id']
ITEM_FIELDS  = ['id', 'documento_id', 'produto_id', 'produto_codigo',
                'produto_nome', 'ncm', 'quantidade', 'vr_unitario', 'vr_nf']

NFE_PAGE     = 200
ITEM_BATCH   = 100
PROD_BATCH   = 100
ORDER_BATCH  = 100
SLEEP        = 0.25


# ── Auth ──────────────────────────────────────────────────────────────────────

def authenticate():
    load_dotenv(PROJECT_ROOT / '.env')
    url  = os.environ['ODOO_URL']
    db   = os.environ['ODOO_DB']
    user = os.environ['ODOO_USERNAME']
    pwd  = os.environ['ODOO_PASSWORD']
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid    = common.authenticate(db, user, pwd, {})
    if not uid:
        raise RuntimeError('Odoo authentication failed')
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    print(f'Auth OK  uid={uid}')
    return db, uid, pwd, models


# ── Fetch NF-es ───────────────────────────────────────────────────────────────

def fetch_nfes(db, uid, pwd, models) -> list:
    """Fetch all authorized NF-es for 2026 matching report fiscal operations."""
    domain = [
        ('operacao_id', 'in', ALL_OP_IDS),
        ('empresa_id', 'in', [1, 2]),
        ('data_emissao', '>=', '2026-01-01'),
        ('data_emissao', '<=', '2026-12-31'),
        ('situacao_nfe', '=', 'autorizada'),
        ('pedido_id', '!=', False),
    ]
    total = models.execute_kw(db, uid, pwd, 'sped.documento', 'search_count', [domain])
    print(f'  Authorized NF-es matching filter: {total:,}')

    all_nfes = []
    offset = 0
    while offset < total:
        batch = models.execute_kw(
            db, uid, pwd, 'sped.documento', 'search_read',
            [domain],
            {'fields': NFE_FIELDS, 'limit': NFE_PAGE, 'offset': offset},
        )
        if not batch:
            break
        all_nfes.extend(batch)
        offset += len(batch)
        if offset % 500 == 0 or offset >= total:
            print(f'    {min(offset, total):,}/{total:,} NF-es fetched')
        time.sleep(SLEEP)

    return all_nfes


# ── Fetch NF-e items ──────────────────────────────────────────────────────────

def fetch_items(db, uid, pwd, models, nfe_ids: list) -> list:
    """Fetch all items for the given NF-e IDs."""
    all_items = []
    n_batches = (len(nfe_ids) + ITEM_BATCH - 1) // ITEM_BATCH

    for i, start in enumerate(range(0, len(nfe_ids), ITEM_BATCH)):
        batch_ids = nfe_ids[start:start + ITEM_BATCH]
        items = models.execute_kw(
            db, uid, pwd, 'sped.documento.item', 'search_read',
            [[['documento_id', 'in', batch_ids]]],
            {'fields': ITEM_FIELDS, 'limit': False},
        )
        all_items.extend(items)
        if (i + 1) % 20 == 0 or (i + 1) == n_batches:
            print(f'    Item batch {i+1}/{n_batches} — {len(all_items):,} items so far')
        time.sleep(SLEEP)

    return all_items


# ── Fetch vendedor from orders ────────────────────────────────────────────────

def fetch_vendedores(db, uid, pwd, models, pedido_ids: list) -> tuple:
    """Fetch vendedor_id and participante_id for original orders referenced by NF-es.
    Returns (vendedor_map, cliente_map) — both dict[int, str]."""
    vendedor_map = {}
    cliente_map = {}
    n_batches = (len(pedido_ids) + ORDER_BATCH - 1) // ORDER_BATCH

    for i, start in enumerate(range(0, len(pedido_ids), ORDER_BATCH)):
        batch = pedido_ids[start:start + ORDER_BATCH]
        orders = models.execute_kw(
            db, uid, pwd, 'pedido.documento', 'read',
            [batch], {'fields': ['id', 'vendedor_id', 'participante_id']},
        )
        for o in orders:
            v = o.get('vendedor_id')
            vendedor_map[o['id']] = v[1] if v and v is not False else ''
            p = o.get('participante_id')
            cliente_map[o['id']] = p[1] if p and p is not False else ''
        if (i + 1) % 20 == 0 or (i + 1) == n_batches:
            print(f'    Vendedor batch {i+1}/{n_batches}')
        time.sleep(SLEEP)

    return vendedor_map, cliente_map


# ── Fetch familia ─────────────────────────────────────────────────────────────

def fetch_familias(db, uid, pwd, models, prod_ids: list) -> dict:
    """Fetch familia_id for all unique products."""
    familia_map = {}
    n_batches = (len(prod_ids) + PROD_BATCH - 1) // PROD_BATCH

    for i, start in enumerate(range(0, len(prod_ids), PROD_BATCH)):
        batch = prod_ids[start:start + PROD_BATCH]
        prods = models.execute_kw(
            db, uid, pwd, 'sped.produto', 'read',
            [batch], {'fields': ['id', 'familia_id']},
        )
        for p in prods:
            fam = p.get('familia_id')
            familia_map[p['id']] = fam[1] if fam else 'OUTROS'
        if (i + 1) % 20 == 0 or (i + 1) == n_batches:
            print(f'    Familia batch {i+1}/{n_batches}')
        time.sleep(SLEEP)

    return familia_map


# ── Build DataFrame ───────────────────────────────────────────────────────────

def _m2o_name(val) -> str:
    return val[1] if val and val is not False else ''


def _m2o_id(val):
    return val[0] if val and val is not False else None


def build_items_df(items_raw: list, nfe_meta: dict,
                   vendedor_map: dict, familia_map: dict,
                   cliente_map: dict = None) -> pd.DataFrame:
    """Build one row per NF-e item with vendedor, tipo, operacao, familia, cliente."""
    if cliente_map is None:
        cliente_map = {}
    rows = []
    for item in items_raw:
        doc_m2o     = item.get('documento_id')
        doc_int     = _m2o_id(doc_m2o)
        produto_m2o = item.get('produto_id')
        produto_int = _m2o_id(produto_m2o)
        nfe         = nfe_meta.get(doc_int, {})

        op_id = _m2o_id(nfe.get('operacao_id'))
        op_name = _m2o_name(nfe.get('operacao_id'))
        is_devol = op_id in DEVOL_OP_IDS

        ped_int = _m2o_id(nfe.get('pedido_id'))
        vendedor = vendedor_map.get(ped_int, '')
        cliente = cliente_map.get(ped_int, '')

        # Classify tipo
        if is_devol:
            tipo = 'devolucao'
        elif nfe.get('pedido_tipo') == 'os':
            tipo = 'os'
        else:
            tipo = 'venda'

        data_emissao = nfe.get('data_emissao') or ''
        dt = pd.to_datetime(data_emissao, errors='coerce')
        mes = dt.month if pd.notna(dt) else None
        ano = dt.year if pd.notna(dt) else None

        nfe_numero = nfe.get('numero')
        numero_str = str(int(nfe_numero)) if nfe_numero else ''

        vr_nf = item.get('vr_nf') or 0
        if is_devol:
            vr_nf = -abs(vr_nf)

        rows.append({
            'item_id':        item['id'],
            'documento_id':   doc_int,
            'pedido_id':      ped_int,
            'numero':         numero_str,
            'tipo':           tipo,
            'vendedor':       vendedor,
            'operacao':       op_name,
            'ano':            ano,
            'mes':            mes,
            'empresa_id':     _m2o_id(nfe.get('empresa_id')),
            'empresa':        _m2o_name(nfe.get('empresa_id')),
            'produto_id':     produto_int,
            'produto_codigo': item.get('produto_codigo') or '',
            'produto_nome':   item.get('produto_nome') or '',
            'ncm':            item.get('ncm') or '',
            'quantidade':     item.get('quantidade') or 0,
            'vr_unitario':    item.get('vr_unitario') or 0,
            'vr_nf':          vr_nf,
            'familia':        familia_map.get(produto_int, 'OUTROS'),
            'cliente':        cliente,
        })

    return pd.DataFrame(rows)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    db, uid, pwd, models = authenticate()

    # ── Fetch authorized NF-es ───────────────────────────────────────────────
    print('\nFetching authorized NF-es...')
    nfes_raw = fetch_nfes(db, uid, pwd, models)
    nfe_meta = {n['id']: n for n in nfes_raw}
    nfe_ids = [n['id'] for n in nfes_raw]

    # ── Fetch NF-e items ─────────────────────────────────────────────────────
    print('\nFetching NF-e items...')
    items_raw = fetch_items(db, uid, pwd, models, nfe_ids)
    print(f'  Total items: {len(items_raw):,}')

    # ── Fetch vendedores from linked orders ──────────────────────────────────
    print('\nFetching vendedores...')
    ped_ids = list({_m2o_id(n.get('pedido_id'))
                    for n in nfes_raw if n.get('pedido_id')} - {None})
    print(f'  Unique orders: {len(ped_ids):,}')
    vendedor_map, cliente_map = fetch_vendedores(db, uid, pwd, models, ped_ids)

    # ── Fetch product familia ────────────────────────────────────────────────
    print('\nFetching product familia...')
    prod_ids = list({_m2o_id(i.get('produto_id'))
                     for i in items_raw if i.get('produto_id')} - {None})
    print(f'  Unique products: {len(prod_ids):,}')
    familia_map = fetch_familias(db, uid, pwd, models, prod_ids)

    # ── Build dataset ────────────────────────────────────────────────────────
    print('\nBuilding items dataset...')
    items_df = build_items_df(items_raw, nfe_meta, vendedor_map, familia_map, cliente_map)

    os.makedirs(ITEMS_CSV.parent, exist_ok=True)
    items_df.to_csv(ITEMS_CSV, index=False, encoding='utf-8-sig')
    print(f'  Saved {len(items_df):,} items → {ITEMS_CSV.name}')

    # ── Summary ──────────────────────────────────────────────────────────────
    print('\n── Summary ─────────────────────────────────────────────')
    print(f'NF-es    : {len(nfes_raw):,}')
    print(f'Items    : {len(items_df):,}')

    n_venda = len(items_df[items_df['tipo'] == 'venda'])
    n_os    = len(items_df[items_df['tipo'] == 'os'])
    n_devol = len(items_df[items_df['tipo'] == 'devolucao'])
    print(f'  venda    : {n_venda:,}')
    print(f'  os       : {n_os:,}')
    print(f'  devolução: {n_devol:,}')

    print('\nMes (R$ net revenue)')
    mes_sum = (items_df.groupby('mes')['vr_nf']
               .agg(vr_nf='sum', items='count')
               .sort_index())
    for mes, row in mes_sum.iterrows():
        print(f"  {int(mes):>2}  R$ {row['vr_nf']:>14,.2f}  ({int(row['items']):,} items)")

    print('\nTipo (R$ net revenue)')
    tipo_sum = (items_df.groupby('tipo')['vr_nf']
                .agg(vr_nf='sum', items='count')
                .sort_values('vr_nf', ascending=False))
    for tipo, row in tipo_sum.iterrows():
        print(f"  {tipo:<20}  R$ {row['vr_nf']:>14,.2f}  ({int(row['items']):,} items)")

    print('\nOperacao (R$ net revenue)')
    op_sum = (items_df.groupby('operacao')['vr_nf']
              .agg(vr_nf='sum', items='count')
              .sort_values('vr_nf', ascending=False))
    for op, row in op_sum.iterrows():
        print(f"  {op:<50}  R$ {row['vr_nf']:>14,.2f}  ({int(row['items']):,} items)")

    total = items_df['vr_nf'].sum()
    print(f'\n  TOTAL NET: R$ {total:,.2f}')


if __name__ == '__main__':
    main()
