"""
Generate DBML Schema from Odoo Data Model CSV

Converts the Odoo field metadata CSV into a DBML (Database Markup Language)
file that can be visualized on dbdiagram.io.

Input: outputs/metadata/odoo_datamodel.csv
Output: outputs/metadata/odoo_model_fixed.dbml
"""
import csv
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import Config


def generate_dbml_schema(csv_file):
    """
    Generate DBML schema from Odoo metadata CSV.

    Args:
        csv_file (Path): Path to the input CSV file
    """
    dbml_output = "// Odoo Data Model: pedido.documento\n\n"
    tables = {}
    relationships = []
    all_referred_models = set()

    try:
        with open(csv_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                model = row['Model']
                field = row['Field Name']
                ftype = row['Field Type']
                label = row['Field Label'].replace('"', "'")  # Escape quotes
                related = row['Related Model']

                if model not in tables:
                    tables[model] = []

                # Prevent duplicate ID column if it already exists in CSV
                if field.lower() == "id":
                    tables[model].append(f'  "{field}" "integer" [pk, note: "{label}"]')
                else:
                    tables[model].append(f'  "{field}" "{ftype}" [note: "{label}"]')

                # Handle relationships
                if related and related.strip():
                    clean_related = related.strip()
                    all_referred_models.add(clean_related)
                    relationships.append(f'Ref: "{model}"."{field}" > "{clean_related}"."id"')

        # 1. Write the Main Table(s)
        for model, fields in tables.items():
            dbml_output += f'Table "{model}" {{\n'
            # If 'id' wasn't in the fields, add it as a primary key
            if not any('"id"' in f for f in fields):
                dbml_output += '  "id" "integer" [pk]\n'

            dbml_output += "\n".join(fields)
            dbml_output += "\n}\n\n"

        # 2. Write Placeholder Tables for all external references
        for ext_model in sorted(all_referred_models):
            if ext_model not in tables:
                dbml_output += f'Table "{ext_model}" {{\n  "id" "integer" [pk]\n}}\n\n'

        # 3. Write Relationships
        dbml_output += "\n".join(relationships)

        # Setup output path
        config = Config()
        output_dir = Path(config.OUTPUT_DIR) / 'metadata'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / 'odoo_model_fixed.dbml'

        with open(output_file, "w", encoding='utf-8') as f:
            f.write(dbml_output)

        print("✅ DBML schema generated successfully!")
        print(f"📁 Output: {output_file}")
        print("📊 Copy the text from this file to dbdiagram.io for visualization")

    except Exception as e:
        print(f"⚠️ Error generating DBML: {e}")


if __name__ == "__main__":
    config = Config()
    input_file = Path(config.OUTPUT_DIR) / 'metadata' / 'odoo_datamodel.csv'

    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        print("   Please run the data model extraction first.")
        sys.exit(1)

    generate_dbml_schema(input_file)
