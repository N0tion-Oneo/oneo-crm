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
    
    async def retrieve_profile(
        self,
        identifier: str,
        account_id: str,
        linkedin_sections: Optional[str] = None,
        notify: bool = False
    ) -> Dict[str, Any]:
        """
        Retrieve a user profile
        
        Args:
            identifier: LinkedIn username or provider ID
            account_id: Account ID to retrieve from
            linkedin_sections: Optional LinkedIn sections to retrieve
            notify: Whether to notify the profile owner
            
        Returns:
            Profile data including provider_id
        """
        try:
            params = {
                'account_id': account_id,
                'notify': str(notify).lower()  # Convert boolean to string
            }
            if linkedin_sections:
                params['linkedin_sections'] = linkedin_sections
                
            response = await self.client._make_request('GET', f'users/{identifier}', params=params)
            return response
        except Exception as e:
            logger.error(f"Failed to retrieve profile {identifier}: {e}")
            raise