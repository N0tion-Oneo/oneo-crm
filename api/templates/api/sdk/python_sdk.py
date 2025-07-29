"""
Oneo CRM Python SDK
Auto-generated client library for the Oneo CRM API

Usage:
    from oneo_crm_client import OneoCrmClient
    
    client = OneoCrmClient(
        base_url="https://api.your-domain.com",
        jwt_token="your-jwt-token"
    )
    
    # List pipelines
    pipelines = client.pipelines.list()
    
    # Create a pipeline
    pipeline = client.pipelines.create({
        "name": "Sales Pipeline",
        "pipeline_type": "crm"
    })
    
    # Create a record
    record = client.records.create(pipeline_id=pipeline['id'], data={
        "company_name": "Acme Corp",
        "deal_value": 50000
    })
"""

import requests
import json
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin


class OneoCrmAPIError(Exception):
    """Base exception for API errors."""
    
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class BaseResource:
    """Base class for API resources."""
    
    def __init__(self, client: 'OneoCrmClient'):
        self.client = client
    
    def _make_request(self, method: str, endpoint: str, data: dict = None, params: dict = None) -> dict:
        """Make HTTP request to API."""
        url = urljoin(self.client.base_url, f"/api/{{ api_version }}/{endpoint}")
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': f'oneo-crm-python-client/1.0.0',
        }
        
        if self.client.jwt_token:
            headers['Authorization'] = f'Bearer {self.client.jwt_token}'
        elif self.client.api_key:
            headers['X-API-Key'] = self.client.api_key
        
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=self.client.timeout
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                raise OneoCrmAPIError(
                    "Rate limit exceeded. Please wait before making more requests.",
                    status_code=429,
                    response_data=response.json() if response.content else {}
                )
            
            # Handle other errors
            if not response.ok:
                error_data = response.json() if response.content else {}
                error_message = error_data.get('error', f'HTTP {response.status_code} error')
                raise OneoCrmAPIError(
                    error_message,
                    status_code=response.status_code,
                    response_data=error_data
                )
            
            return response.json() if response.content else {}
            
        except requests.RequestException as e:
            raise OneoCrmAPIError(f"Request failed: {str(e)}")


class PipelinesResource(BaseResource):
    """Pipeline management resource."""
    
    def list(self, page: int = 1, page_size: int = 50, search: str = None, 
             pipeline_type: str = None, is_active: bool = None) -> Dict[str, Any]:
        """List pipelines with optional filtering."""
        params = {'page': page, 'page_size': page_size}
        
        if search:
            params['search'] = search
        if pipeline_type:
            params['pipeline_type'] = pipeline_type
        if is_active is not None:
            params['is_active'] = is_active
        
        return self._make_request('GET', 'pipelines/', params=params)
    
    def get(self, pipeline_id: str) -> Dict[str, Any]:
        """Get a specific pipeline by ID."""
        return self._make_request('GET', f'pipelines/{pipeline_id}/')
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new pipeline."""
        return self._make_request('POST', 'pipelines/', data=data)
    
    def update(self, pipeline_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing pipeline."""
        return self._make_request('PUT', f'pipelines/{pipeline_id}/', data=data)
    
    def delete(self, pipeline_id: str) -> Dict[str, Any]:
        """Delete a pipeline."""
        return self._make_request('DELETE', f'pipelines/{pipeline_id}/')
    
    def get_analytics(self, pipeline_id: str) -> Dict[str, Any]:
        """Get analytics data for a pipeline."""
        return self._make_request('GET', f'pipelines/{pipeline_id}/analytics/')
    
    def export_data(self, pipeline_id: str, format: str = 'csv') -> bytes:
        """Export pipeline data."""
        url = urljoin(self.client.base_url, f"/api/{{ api_version }}/pipelines/{pipeline_id}/export/")
        headers = {'Authorization': f'Bearer {self.client.jwt_token}'}
        
        response = requests.get(url, headers=headers, params={'format': format})
        response.raise_for_status()
        return response.content


class RecordsResource(BaseResource):
    """Record management resource."""
    
    def list(self, pipeline_id: str, page: int = 1, page_size: int = 50, 
             search: str = None, status: str = None) -> Dict[str, Any]:
        """List records in a pipeline."""
        params = {'page': page, 'page_size': page_size}
        
        if search:
            params['search'] = search
        if status:
            params['status'] = status
        
        return self._make_request('GET', f'pipelines/{pipeline_id}/records/', params=params)
    
    def get(self, pipeline_id: str, record_id: str) -> Dict[str, Any]:
        """Get a specific record."""
        return self._make_request('GET', f'pipelines/{pipeline_id}/records/{record_id}/')
    
    def create(self, pipeline_id: str, data: Dict[str, Any], status: str = 'active') -> Dict[str, Any]:
        """Create a new record."""
        payload = {
            'data': data,
            'status': status
        }
        return self._make_request('POST', f'pipelines/{pipeline_id}/records/', data=payload)
    
    def update(self, pipeline_id: str, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing record."""
        return self._make_request('PUT', f'pipelines/{pipeline_id}/records/{record_id}/', data={'data': data})
    
    def delete(self, pipeline_id: str, record_id: str) -> Dict[str, Any]:
        """Delete a record."""
        return self._make_request('DELETE', f'pipelines/{pipeline_id}/records/{record_id}/')
    
    def bulk_create(self, pipeline_id: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create multiple records at once."""
        return self._make_request('POST', f'pipelines/{pipeline_id}/records/bulk/', data={'records': records})
    
    def bulk_update(self, pipeline_id: str, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update multiple records at once."""
        return self._make_request('PUT', f'pipelines/{pipeline_id}/records/bulk/', data={'updates': updates})


class RelationshipsResource(BaseResource):
    """Relationship management resource."""
    
    def list(self, record_id: str) -> Dict[str, Any]:
        """List relationships for a record."""
        return self._make_request('GET', f'records/{record_id}/relationships/')
    
    def create(self, from_record_id: str, to_record_id: str, 
               relationship_type: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a relationship between records."""
        data = {
            'from_record_id': from_record_id,
            'to_record_id': to_record_id,
            'relationship_type': relationship_type,
            'metadata': metadata or {}
        }
        return self._make_request('POST', 'relationships/', data=data)
    
    def delete(self, relationship_id: str) -> Dict[str, Any]:
        """Delete a relationship."""
        return self._make_request('DELETE', f'relationships/{relationship_id}/')


class SearchResource(BaseResource):
    """Global search resource."""
    
    def search(self, query: str, pipeline_ids: List[str] = None, limit: int = 50) -> Dict[str, Any]:
        """Perform global search across records."""
        params = {
            'q': query,
            'limit': limit
        }
        
        if pipeline_ids:
            params['pipeline_ids'] = ','.join(pipeline_ids)
        
        return self._make_request('GET', 'search/', params=params)


class GraphQLResource(BaseResource):
    """GraphQL query resource."""
    
    def query(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a GraphQL query."""
        data = {
            'query': query,
            'variables': variables or {}
        }
        
        # GraphQL uses different endpoint
        url = urljoin(self.client.base_url, "/graphql/")
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.client.jwt_token}'
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=self.client.timeout)
        response.raise_for_status()
        
        result = response.json()
        
        if 'errors' in result:
            error_messages = [error['message'] for error in result['errors']]
            raise OneoCrmAPIError(f"GraphQL errors: {'; '.join(error_messages)}")
        
        return result


class OneoCrmClient:
    """Main client class for Oneo CRM API."""
    
    def __init__(self, base_url: str = "{{ base_url }}", jwt_token: str = None, 
                 api_key: str = None, timeout: int = 30):
        """
        Initialize the Oneo CRM client.
        
        Args:
            base_url: Base URL of the API
            jwt_token: JWT authentication token
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.jwt_token = jwt_token
        self.api_key = api_key
        self.timeout = timeout
        
        if not jwt_token and not api_key:
            raise ValueError("Either jwt_token or api_key must be provided")
        
        # Initialize resource endpoints
        self.pipelines = PipelinesResource(self)
        self.records = RecordsResource(self)
        self.relationships = RelationshipsResource(self)
        self.search = SearchResource(self)
        self.graphql = GraphQLResource(self)
    
    def set_jwt_token(self, token: str):
        """Update the JWT token."""
        self.jwt_token = token
    
    def set_api_key(self, api_key: str):
        """Update the API key."""
        self.api_key = api_key
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health status."""
        url = urljoin(self.base_url, "/api/health/")
        response = requests.get(url, timeout=self.timeout)
        return response.json()


# Convenience functions for common operations

def create_client_from_env() -> OneoCrmClient:
    """Create client using environment variables."""
    import os
    
    base_url = os.getenv('ONEO_CRM_BASE_URL', '{{ base_url }}')
    jwt_token = os.getenv('ONEO_CRM_JWT_TOKEN')
    api_key = os.getenv('ONEO_CRM_API_KEY')
    
    return OneoCrmClient(
        base_url=base_url,
        jwt_token=jwt_token,
        api_key=api_key
    )


# Example usage
if __name__ == "__main__":
    # Initialize client
    client = OneoCrmClient(
        base_url="https://api.your-domain.com",
        jwt_token="your-jwt-token-here"
    )
    
    try:
        # Health check
        health = client.health_check()
        print(f"API Status: {health['status']}")
        
        # List pipelines
        pipelines = client.pipelines.list(page_size=10)
        print(f"Found {pipelines['count']} pipelines")
        
        # Create a new pipeline
        new_pipeline = client.pipelines.create({
            "name": "Test Pipeline",
            "description": "A test pipeline created with Python SDK",
            "pipeline_type": "custom"
        })
        print(f"Created pipeline: {new_pipeline['id']}")
        
        # Create a record in the pipeline
        new_record = client.records.create(
            pipeline_id=new_pipeline['id'],
            data={
                "name": "Test Record",
                "description": "A test record",
                "value": 1000
            }
        )
        print(f"Created record: {new_record['id']}")
        
        # Search for records
        search_results = client.search.search("Test", limit=5)
        print(f"Search found {len(search_results['results'])} results")
        
        # GraphQL query example
        graphql_result = client.graphql.query("""
            query GetPipelines {
                pipelines {
                    id
                    name
                    recordCount
                }
            }
        """)
        print(f"GraphQL returned {len(graphql_result['data']['pipelines'])} pipelines")
        
    except OneoCrmAPIError as e:
        print(f"API Error: {e}")
        if e.response_data:
            print(f"Response: {e.response_data}")
    except Exception as e:
        print(f"Unexpected error: {e}")