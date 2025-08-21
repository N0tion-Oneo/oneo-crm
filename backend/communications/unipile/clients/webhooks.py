"""
UniPile Webhook Management Client
Handles webhook creation, management, and deletion
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class UnipileWebhookClient:
    """UniPile webhook management client"""
    
    def __init__(self, client):
        self.client = client
    
    async def create_webhook(self, url: str, source: str = 'messaging', events: List[str] = None, name: str = None) -> Dict[str, Any]:
        """Create a webhook with proper UniPile format"""
        try:
            # Use proper UniPile webhook format
            data = {
                'request_url': url,  # UniPile uses 'request_url' not 'url'
                'source': source,    # Required: messaging, email, account_status, users, email_tracking
                'format': 'json',    # Default to JSON format
                'enabled': True      # Enable the webhook
            }
            
            if name:
                data['name'] = name
            
            # Set default events based on source type
            if events:
                data['events'] = events
            elif source == 'messaging':
                data['events'] = ['message_received', 'message_delivered', 'message_read']
            elif source == 'email':
                data['events'] = ['mail_received', 'mail_sent']
            elif source == 'account_status':
                data['events'] = ['creation_success', 'creation_fail', 'error', 'credentials', 'permissions']
            elif source == 'users':
                data['events'] = ['new_relation']
            elif source == 'email_tracking':
                data['events'] = ['mail_opened', 'mail_link_clicked']
            
            response = await self.client._make_request('POST', 'webhooks', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to create webhook: {e}")
            raise
    
    async def create_messaging_webhook(self, url: str, events: List[str] = None, name: str = None) -> Dict[str, Any]:
        """Create a messaging webhook specifically"""
        return await self.create_webhook(url, source='messaging', events=events, name=name)
    
    async def create_email_webhook(self, url: str, events: List[str] = None, name: str = None) -> Dict[str, Any]:
        """Create an email webhook specifically"""
        return await self.create_webhook(url, source='email', events=events, name=name)
    
    async def create_account_status_webhook(self, url: str, events: List[str] = None, name: str = None) -> Dict[str, Any]:
        """Create an account status webhook specifically"""
        return await self.create_webhook(url, source='account_status', events=events, name=name)
    
    async def list_webhooks(self) -> List[Dict[str, Any]]:
        """List all webhooks"""
        try:
            response = await self.client._make_request('GET', 'webhooks')
            return response if isinstance(response, list) else response.get('webhooks', [])
        except Exception as e:
            logger.error(f"Failed to list webhooks: {e}")
            raise
    
    async def delete_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """Delete a webhook"""
        try:
            response = await self.client._make_request('DELETE', f'webhooks/{webhook_id}')
            return response
        except Exception as e:
            logger.error(f"Failed to delete webhook {webhook_id}: {e}")
            raise