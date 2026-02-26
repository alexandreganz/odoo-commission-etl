"""
Field Value Mapper - Extract Unique Values for Each Field

Extracts unique values from Odoo fields to create a lookup/reference CSV.
Useful for understanding data distributions and valid field values.

Output: outputs/metadata/odoo_unique_values_map.csv
"""
import csv
import itertools
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.etl.odoo_client import OdooClient
from config.settings import Config


def export_field_value_map():
    """Extract and export unique values for each field in the model."""
    print("🔍 Starting field value mapping...")

    # Initialize client
    client = OdooClient()
    config = Config()

    try:
        uid, models = client.authenticate()
        print("✅ Authenticated successfully")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return

    print(f"📥 Fetching field metadata and sample records...")

    # Get field information
    try:
        fields_info = client.execute_kw(
            config.MAIN_MODEL,
            'fields_get',
            [],
            {'attributes': ['type', 'string']}
        )
    except Exception as e:
        print(f"❌ Error fetching field metadata: {e}")
        return

    # Get sample records (1000 for better coverage)
    try:
        records = client.execute_kw(
            config.MAIN_MODEL,
            'search_read',
            [[]],
            {'limit': 1000}
        )
        print(f"📊 Analyzing {len(records)} sample records...")
    except Exception as e:
        print(f"❌ Error fetching records: {e}")
        return

    columns_data = {}

    for field_name, info in fields_info.items():
        try:
            # Extract raw values from records
            raw_values = [r.get(field_name) for r in records if r.get(field_name) is not None]
            clean_values = []

            for v in raw_values:
                # Check if it's a list with at least 2 elements [ID, Name]
                if isinstance(v, list):
                    if len(v) > 1:
                        clean_values.append(str(v[1]))
                    elif len(v) == 1:
                        clean_values.append(str(v[0]))
                    else:
                        clean_values.append("Empty List")
                else:
                    clean_values.append(str(v))

            unique_vals = sorted(list(set(clean_values)))

            # Only include fields with significant but manageable variety
            if 1 < len(unique_vals) < 150:
                column_header = f"{info['string']} ({field_name})"
                columns_data[column_header] = unique_vals

        except Exception as e:
            print(f"⚠️ Skipping field {field_name} due to error: {e}")

    # Transpose data for CSV output
    rows = itertools.zip_longest(*columns_data.values(), fillvalue="")

    # Setup output path
    output_dir = Path(config.OUTPUT_DIR) / 'metadata'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'odoo_unique_values_map.csv'

    try:
        with open(output_file, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(columns_data.keys())
            writer.writerows(rows)

        print(f"✅ Field value map generated successfully!")
        print(f"   📊 Columns included: {len(columns_data)}")
        print(f"   📁 Output: {output_file}")

    except Exception as e:
        print(f"❌ Error writing output file: {e}")


if __name__ == "__main__":
    export_field_value_map()
