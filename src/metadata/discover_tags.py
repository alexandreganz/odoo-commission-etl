"""
Discover Tags Model - Find the Model Name for etapa_tag_ids

Simple utility to discover the technical model name that the 'etapa_tag_ids'
field references in the pedido.documento model.
"""
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.etl.odoo_client import OdooClient
from config.settings import Config


def discover_tag_model():
    """Discover the model name for etapa_tag_ids field."""
    print("🔍 Discovering tag model information...")

    # Initialize client
    client = OdooClient()
    config = Config()

    try:
        uid, models = client.authenticate()
        print("✅ Authenticated successfully")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return

    # Get field information for etapa_tag_ids
    try:
        field_info = client.execute_kw(
            config.MAIN_MODEL,
            'fields_get',
            [['etapa_tag_ids']],
            {'attributes': ['relation', 'type', 'string']}
        )

        if 'etapa_tag_ids' in field_info:
            info = field_info['etapa_tag_ids']
            print(f"\n📊 Field Information for 'etapa_tag_ids':")
            print(f"   Label: {info.get('string', 'N/A')}")
            print(f"   Type: {info.get('type', 'N/A')}")
            print(f"   🎯 Related Model: {info.get('relation', 'N/A')}")
        else:
            print("⚠️ Field 'etapa_tag_ids' not found in model")

    except Exception as e:
        print(f"❌ Error fetching field information: {e}")


if __name__ == "__main__":
    discover_tag_model()
