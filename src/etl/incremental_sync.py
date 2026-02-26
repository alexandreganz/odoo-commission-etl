"""
Incremental Sync Pipeline - Delta Updates Only

This script performs incremental syncs of order data by tracking write_date.
Only fetches records that were created or modified since the last sync.

Output: outputs/csv/sales_data.json
"""
import json
import os
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.etl.odoo_client import OdooClient
from config.settings import Config


def sync_data():
    """Execute incremental data synchronization."""
    print(f"🔄 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Incremental Sync...")

    # Initialize client
    client = OdooClient()
    config = Config()

    try:
        # Authenticate
        uid, models = client.authenticate()
        print(f"✅ Authenticated successfully")

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return

    # Setup data file path
    output_dir = Path(config.OUTPUT_DIR) / 'csv'
    output_dir.mkdir(parents=True, exist_ok=True)
    data_file = output_dir / 'sales_data.json'

    # Load existing data to find the last sync date
    existing_data = {}
    last_sync = "2000-01-01 00:00:00"

    if data_file.exists():
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data_list = json.load(f)
                existing_data = {str(item['id']): item for item in data_list}

                # Find the most recent 'write_date' in our local file
                if existing_data:
                    last_sync = max(
                        item.get('write_date', '2000-01-01 00:00:00')
                        for item in existing_data.values()
                    )
                    print(f"📅 Last sync date: {last_sync}")
        except Exception as e:
            print(f"⚠️ Could not load existing data: {e}")

    print(f"🔍 Fetching records modified after: {last_sync}")

    # Extract: Fetch only new/modified records
    # Odoo standard fields: 'write_date' tracks the last update
    fields = ['numero', 'participante_id', 'vr_nf', 'data_orcamento', 'write_date']
    domain = [['write_date', '>', last_sync]]

    try:
        new_records = client.execute_kw(
            config.MAIN_MODEL,
            'search_read',
            [domain],
            {'fields': fields}
        )
    except Exception as e:
        print(f"❌ Error fetching records: {e}")
        return

    if not new_records:
        print("✅ Already up to date - no new records found.")
        return

    print(f"📥 Found {len(new_records)} new/modified records")

    # Transform & Merge
    for rec in new_records:
        # Clean up Many2one (convert [id, "Name"] to just "Name")
        rec['cliente_nome'] = (
            rec['participante_id'][1] if rec['participante_id'] else "N/A"
        )
        # Update or add to our local dictionary
        existing_data[str(rec['id'])] = rec

    # Save back to JSON
    try:
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(list(existing_data.values()), f, indent=4, ensure_ascii=False)

        print(f"🚀 Sync complete!")
        print(f"   📝 Updated: {len(new_records)} records")
        print(f"   📊 Total local records: {len(existing_data)}")
        print(f"   📁 Output: {data_file}")

    except Exception as e:
        print(f"❌ Error saving data: {e}")


if __name__ == "__main__":
    sync_data()
