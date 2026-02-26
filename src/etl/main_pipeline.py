"""
Main ETL Pipeline - Hierarchical Order-Item Extraction

This script extracts sales data from Odoo using a top-down approach:
1. Fetch orders (Level 1: pedido.documento)
2. For each order, fetch associated items (Level 2: sped.documento.item)
3. Merge and write denormalized rows to CSV

Output: outputs/csv/final_sales_export_top_down.csv
"""
import csv
import time
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.etl.odoo_client import OdooClient
from config.settings import Config


def run_sync():
    """Execute the main ETL pipeline."""
    print(f"🚀 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Main ETL Pipeline...")

    # Initialize client
    client = OdooClient()
    config = Config()

    try:
        # Authenticate
        print(f"🔐 Connecting to Odoo at {config.ODOO_URL}...")
        uid, models = client.authenticate()
        print(f"✅ Authenticated successfully as user ID: {uid}")

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return

    # Define fields to extract
    order_fields = ['numero', 'operacao_id', 'etapa_tag_ids', 'vendedor_id', 'participante_id', 'item_ids']
    item_fields = ['produto_codigo', 'produto_ncm_id', 'quantidade', 'vr_nf']

    headers = ['numero', 'operacao_id', 'etapa_tag_ids', 'vendedor_id', 'participante_id',
               'produto_codigo', 'produto_ncm_id', 'quantidade', 'vr_nf']

    # Setup output file
    output_dir = Path(config.OUTPUT_DIR) / 'csv'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'final_sales_export_top_down.csv'

    print(f"📝 Starting extraction to {output_file}...")

    total_orders = 0
    total_items = 0
    start_time = time.time()

    with open(output_file, mode='w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()

        offset = 0
        batch_size = 50

        while True:
            # 1. Get a batch of Orders (Level 1)
            try:
                orders = client.execute_kw(
                    config.MAIN_MODEL,
                    'search_read',
                    [[]],
                    {'fields': order_fields, 'limit': batch_size, 'offset': offset}
                )
            except Exception as e:
                print(f"❌ Error fetching orders at offset {offset}: {e}")
                break

            if not orders:
                break

            print(f"📦 Processing orders {offset} to {offset + len(orders)}...")
            total_orders += len(orders)

            for order in orders:
                # 2. Get the specific Items for THIS Order (Level 2)
                item_ids = order.get('item_ids', [])
                if not item_ids:
                    continue

                # Fetch items for this single order to ensure correct linking
                try:
                    items = client.execute_kw(
                        config.ITEM_MODEL,
                        'read',
                        [item_ids],
                        {'fields': item_fields}
                    )
                except Exception as e:
                    print(f"⚠️ Error fetching items for order {order.get('numero')}: {e}")
                    continue

                # 3. Merge Order + Item data and Write
                for item in items:
                    writer.writerow({
                        'numero': order.get('numero'),
                        'operacao_id': client.clean_value(order.get('operacao_id')),
                        'etapa_tag_ids': client.clean_value(order.get('etapa_tag_ids')),
                        'vendedor_id': client.clean_value(order.get('vendedor_id')),
                        'participante_id': client.clean_value(order.get('participante_id')),
                        'produto_codigo': item.get('produto_codigo'),
                        'produto_ncm_id': client.clean_value(item.get('produto_ncm_id')),
                        'quantidade': item.get('quantidade'),
                        'vr_nf': item.get('vr_nf')
                    })
                    total_items += 1

            offset += batch_size
            time.sleep(0.1)  # Brief pause to keep the API happy

    elapsed_time = time.time() - start_time
    print(f"\n🏁 ETL Pipeline Complete!")
    print(f"   📊 Total Orders Processed: {total_orders}")
    print(f"   📦 Total Items Extracted: {total_items}")
    print(f"   ⏱️  Time Elapsed: {elapsed_time:.2f} seconds")
    print(f"   📁 Output File: {output_file}")


if __name__ == "__main__":
    run_sync()
