"""
Centralized configuration management for Odoo ETL project.
Loads environment variables from .env file.
"""
from dotenv import load_dotenv
import os
from pathlib import Path

# Load .env file from project root
project_root = Path(__file__).parent.parent
load_dotenv(project_root / '.env')

class Config:
    """Configuration class for Odoo connection and project settings."""

    # Odoo connection settings
    ODOO_URL = os.getenv('ODOO_URL')
    ODOO_DB = os.getenv('ODOO_DB')
    ODOO_USERNAME = os.getenv('ODOO_USERNAME')
    ODOO_PASSWORD = os.getenv('ODOO_PASSWORD')

    # Model settings
    MAIN_MODEL = os.getenv('MAIN_MODEL', 'pedido.documento')
    ITEM_MODEL = os.getenv('ITEM_MODEL', 'sped.documento.item')

    # Output directory
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'outputs')

    @classmethod
    def validate(cls):
        """Validate that all required configuration values are present."""
        required = ['ODOO_URL', 'ODOO_DB', 'ODOO_USERNAME', 'ODOO_PASSWORD']
        missing = [key for key in required if not getattr(cls, key)]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        return True
