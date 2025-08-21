"""
UniPile Request Client
Handles custom requests for unsupported endpoints
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class UnipileRequestClient:
    """UniPile custom request client for unsupported endpoints"""
    
    def __init__(self, client):
        self.client = client
    
    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make custom GET request"""
        return await self.client._make_request('GET', endpoint, params=params)
    
    async def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make custom POST request"""
        return await self.client._make_request('POST', endpoint, data=data)
    
    async def put(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make custom PUT request"""
        return await self.client._make_request('PUT', endpoint, data=data)
    
    async def patch(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make custom PATCH request"""
        return await self.client._make_request('PATCH', endpoint, data=data)
    
    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make custom DELETE request"""
        return await self.client._make_request('DELETE', endpoint)