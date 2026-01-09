"""
ENVY Database Tool
==================
Allows the agent to interact directly with Supabase/Postgres.
"""

from typing import Optional, List, Dict, Any
import httpx
from ..core.config import settings

class SupabaseTool:
    """
    Tool for interacting with Supabase database tables.
    Allows generic query execution via the PostgREST API.
    """
    
    def __init__(self):
        self.url = settings.supabase_url
        self.key = settings.supabase_anon_key
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
    
    def execute_query(self, table: str, operation: str, query_params: Dict = None, body: Dict = None) -> str:
        """
        Execute a database operation.
        
        Args:
            table: Table name
            operation: 'select', 'insert', 'update', 'delete'
            query_params: URL parameters for filtering (e.g. {"id": "eq.1"})
            body: JSON body for insert/update
            
        Returns:
            JSON string result or error message
        """
        try:
            endpoint = f"{self.url}/rest/v1/{table}"
            
            with httpx.Client() as client:
                if operation == 'select':
                    response = client.get(endpoint, headers=self.headers, params=query_params)
                elif operation == 'insert':
                    response = client.post(endpoint, headers=self.headers, json=body)
                elif operation == 'update':
                    response = client.patch(endpoint, headers=self.headers, params=query_params, json=body)
                elif operation == 'delete':
                    response = client.delete(endpoint, headers=self.headers, params=query_params)
                else:
                    return f"Error: Unknown operation '{operation}'"
                
                if response.status_code >= 400:
                    return f"Database Error ({response.status_code}): {response.text}"
                
                return str(response.json())
                
        except Exception as e:
            return f"Error executing database query: {str(e)}"

    def get_table_schema(self, table: str) -> str:
        """Get the schema/columns of a table"""
        # This is a bit hacky with PostgREST, often implied by options or openapi
        # For now, we'll just try to select 1 record to see structure
        return self.execute_query(table, 'select', {"limit": "1"})
