"""
Shared Odoo XML-RPC client for all ETL operations.
Handles authentication and provides common utilities for data extraction.
"""
import xmlrpc.client
from config.settings import Config


class OdooClient:
    """Client for interacting with Odoo via XML-RPC."""

    def __init__(self):
        """Initialize the Odoo client with configuration."""
        self.config = Config()
        self.config.validate()
        self.uid = None
        self.models = None

    def authenticate(self):
        """
        Authenticate with Odoo and return connection objects.

        Returns:
            tuple: (uid, models) - User ID and models proxy object

        Raises:
            Exception: If authentication fails
        """
        common = xmlrpc.client.ServerProxy(f'{self.config.ODOO_URL}/xmlrpc/2/common')
        self.uid = common.authenticate(
            self.config.ODOO_DB,
            self.config.ODOO_USERNAME,
            self.config.ODOO_PASSWORD,
            {}
        )

        if not self.uid:
            raise Exception("Authentication failed - check credentials in .env file")

        self.models = xmlrpc.client.ServerProxy(f'{self.config.ODOO_URL}/xmlrpc/2/object')
        return self.uid, self.models

    @staticmethod
    def clean_value(val):
        """
        Extract names from Odoo [ID, Name] tuples safely.

        Odoo returns Many2one and Many2many fields as [ID, Name] lists.
        This method extracts the human-readable name.

        Args:
            val: Value from Odoo field (could be list, bool, string, etc.)

        Returns:
            str: Cleaned string value
        """
        if isinstance(val, list) and len(val) > 0:
            # Handle [ID, Name] tuples
            if len(val) > 1 and not isinstance(val[0], list):
                return val[1]
            # Handle list of lists or other complex structures
            return ", ".join(map(str, val))
        # Handle False (Odoo's way of representing null)
        return str(val) if val is not False else ""

    def execute_kw(self, model, method, args, kwargs=None):
        """
        Wrapper for execute_kw with error handling.

        Args:
            model (str): Odoo model name (e.g., 'pedido.documento')
            method (str): Method to execute (e.g., 'search_read')
            args (list): Positional arguments for the method
            kwargs (dict, optional): Keyword arguments for the method

        Returns:
            Result from Odoo method execution

        Raises:
            Exception: If authentication hasn't been performed
        """
        if not self.uid or not self.models:
            raise Exception("Must call authenticate() before execute_kw()")

        return self.models.execute_kw(
            self.config.ODOO_DB,
            self.uid,
            self.config.ODOO_PASSWORD,
            model,
            method,
            args,
            kwargs or {}
        )
