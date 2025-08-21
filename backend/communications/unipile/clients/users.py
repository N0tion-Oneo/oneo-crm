"""
UniPile Users Client
Handles user profile and search operations
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class UnipileUsersClient:
    """UniPile users client"""
    
    def __init__(self, client):
        self.client = client
    
    async def get_user_profile(self, user_id: str, account_id: str) -> Dict[str, Any]:
        """Get user profile information"""
        try:
            params = {'account_id': account_id}
            response = await self.client._make_request('GET', f'users/{user_id}', params=params)
            return response
        except Exception as e:
            logger.error(f"Failed to get user profile {user_id}: {e}")
            raise
    
    async def search_users(
        self, 
        query: str, 
        account_id: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Search for users"""
        try:
            params = {
                'query': query,
                'account_id': account_id,
                'limit': limit
            }
            response = await self.client._make_request('GET', 'users/search', params=params)
            return response
        except Exception as e:
            logger.error(f"Failed to search users: {e}")
            raise