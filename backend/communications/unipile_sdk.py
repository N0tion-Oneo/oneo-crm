"""
UniPile SDK Service for Phase 8 - Python implementation following UniPile SDK patterns
Provides unified interface for multi-channel messaging via UniPile API
"""
import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone

import aiohttp
from django.conf import settings
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class UnipileConnectionError(Exception):
    """Raised when UniPile connection fails"""
    pass


class UnipileAuthenticationError(Exception):
    """Raised when UniPile authentication fails"""
    pass


class UnipileRateLimitError(Exception):
    """Raised when UniPile rate limit is exceeded"""
    pass


class UnipileClient:
    """
    Python implementation of UniPile SDK client
    Follows Node.js SDK patterns for consistency
    """
    
    def __init__(self, dsn: str, access_token: str):
        """Initialize UniPile client with DSN and access token"""
        self.dsn = dsn.rstrip('/')
        self.access_token = access_token
        self.base_url = f"{self.dsn}/api/v1"
        
        # Initialize sub-clients
        self.account = UnipileAccountClient(self)
        self.messaging = UnipileMessagingClient(self)
        self.users = UnipileUsersClient(self)
        self.webhooks = UnipileWebhookClient(self)
        self.request = UnipileRequestClient(self)
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to UniPile API"""
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_headers = {
            'X-API-KEY': self.access_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        if headers:
            request_headers.update(headers)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=request_headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    response_data = await response.json()
                    
                    if response.status in [200, 201]:  # Accept both 200 OK and 201 Created
                        return response_data
                    elif response.status == 401:
                        raise UnipileAuthenticationError(
                            f"Authentication failed: {response_data.get('message', 'Invalid access token')}"
                        )
                    elif response.status == 429:
                        raise UnipileRateLimitError(
                            f"Rate limit exceeded: {response_data.get('message', 'Too many requests')}"
                        )
                    else:
                        raise UnipileConnectionError(
                            f"API request failed ({response.status}): {response_data.get('message', 'Unknown error')}"
                        )
                        
        except aiohttp.ClientError as e:
            raise UnipileConnectionError(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            raise UnipileConnectionError(f"Invalid JSON response: {str(e)}")


class UnipileAccountClient:
    """UniPile account management client"""
    
    def __init__(self, client: UnipileClient):
        self.client = client
    
    async def get_accounts(self) -> List[Dict[str, Any]]:
        """Get all connected accounts"""
        try:
            response = await self.client._make_request('GET', 'accounts')
            # UniPile returns a list directly, not wrapped in 'accounts' key
            return response if isinstance(response, list) else response.get('accounts', [])
        except Exception as e:
            logger.error(f"Failed to get accounts: {e}")
            raise
    
    async def request_hosted_link(self, 
                                  providers: Union[str, List[str]], 
                                  success_redirect_url: Optional[str] = None,
                                  failure_redirect_url: Optional[str] = None,
                                  name: Optional[str] = None,
                                  notify_url: Optional[str] = None,
                                  account_id: Optional[str] = None) -> Dict[str, Any]:
        """Request hosted authentication link with proper UniPile format"""
        try:
            from datetime import datetime, timedelta, timezone
            
            # Convert provider to UniPile format (exact provider names from UniPile docs)
            # Supported: LINKEDIN | WHATSAPP | INSTAGRAM | MESSENGER | TELEGRAM | GOOGLE | OUTLOOK | MAIL | TWITTER
            if isinstance(providers, str):
                provider_lower = providers.lower()
                if provider_lower == 'linkedin':
                    provider_list = ['LINKEDIN']
                elif provider_lower in ['gmail', 'google']:
                    provider_list = ['GOOGLE']
                elif provider_lower == 'outlook':
                    provider_list = ['OUTLOOK']
                elif provider_lower in ['email', 'mail']:
                    provider_list = ['MAIL']
                elif provider_lower == 'whatsapp':
                    provider_list = ['WHATSAPP']
                elif provider_lower == 'instagram':
                    provider_list = ['INSTAGRAM']
                elif provider_lower in ['messenger', 'facebook']:
                    provider_list = ['MESSENGER']
                elif provider_lower == 'telegram':
                    provider_list = ['TELEGRAM']
                elif provider_lower == 'twitter':
                    provider_list = ['TWITTER']
                else:
                    # For unknown providers, try uppercase
                    provider_list = [providers.upper()]
            else:
                # Convert list of providers
                provider_list = []
                for p in providers:
                    p_lower = p.lower()
                    if p_lower == 'linkedin':
                        provider_list.append('LINKEDIN')
                    elif p_lower in ['gmail', 'google']:
                        provider_list.append('GOOGLE')
                    elif p_lower == 'outlook':
                        provider_list.append('OUTLOOK')
                    elif p_lower in ['email', 'mail']:
                        provider_list.append('MAIL')
                    elif p_lower == 'whatsapp':
                        provider_list.append('WHATSAPP')
                    elif p_lower == 'instagram':
                        provider_list.append('INSTAGRAM')
                    elif p_lower in ['messenger', 'facebook']:
                        provider_list.append('MESSENGER')
                    elif p_lower == 'telegram':
                        provider_list.append('TELEGRAM')
                    elif p_lower == 'twitter':
                        provider_list.append('TWITTER')
                    else:
                        provider_list.append(p.upper())
            
            # Set expiration to 24 hours from now with proper ISO format
            expires_dt = datetime.now(timezone.utc) + timedelta(days=1)
            expires_on = expires_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            
            # Create the request data
            data = {
                'type': 'reconnect' if account_id else 'create',
                'api_url': self.client.dsn,  # Use the DSN as the API URL
                'expiresOn': expires_on,
                'providers': provider_list
            }
            
            if account_id:
                data['reconnect_account'] = account_id
            
            if name:
                data['name'] = name
            
            if success_redirect_url:
                data['success_redirect_url'] = success_redirect_url
                
            if failure_redirect_url:
                data['failure_redirect_url'] = failure_redirect_url
                
            if notify_url:
                data['notify_url'] = notify_url
                
            response = await self.client._make_request('POST', 'hosted/accounts/link', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to request hosted link for {providers}: {e}")
            raise
    
    async def get_account(self, account_id: str) -> Dict[str, Any]:
        """Get specific account details"""
        try:
            response = await self.client._make_request('GET', f'accounts/{account_id}')
            return response
        except Exception as e:
            logger.error(f"Failed to get account {account_id}: {e}")
            raise
    
    async def connect_linkedin(self, username: str, password: str) -> Dict[str, Any]:
        """Connect LinkedIn account"""
        try:
            data = {
                'provider': 'linkedin',
                'username': username,
                'password': password
            }
            response = await self.client._make_request('POST', 'accounts/connect', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to connect LinkedIn account: {e}")
            raise
    
    async def connect_whatsapp(self) -> Dict[str, Any]:
        """Connect WhatsApp account (returns QR code)"""
        try:
            data = {'provider': 'whatsapp'}
            response = await self.client._make_request('POST', 'accounts/connect', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to connect WhatsApp account: {e}")
            raise
    
    async def connect_gmail(self, email: str, password: str) -> Dict[str, Any]:
        """Connect Gmail account"""
        try:
            data = {
                'provider': 'gmail',
                'email': email,
                'password': password
            }
            response = await self.client._make_request('POST', 'accounts/connect', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to connect Gmail account: {e}")
            raise
    
    async def connect_outlook(self, email: str, password: str) -> Dict[str, Any]:
        """Connect Outlook account"""
        try:
            data = {
                'provider': 'outlook',
                'email': email,
                'password': password
            }
            response = await self.client._make_request('POST', 'accounts/connect', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to connect Outlook account: {e}")
            raise
    
    async def disconnect_account(self, account_id: str) -> Dict[str, Any]:
        """Disconnect account"""
        try:
            response = await self.client._make_request('DELETE', f'accounts/{account_id}')
            return response
        except Exception as e:
            logger.error(f"Failed to disconnect account {account_id}: {e}")
            raise
    
    async def get_account_status(self, account_id: str) -> Dict[str, Any]:
        """Get account connection status"""
        try:
            response = await self.client._make_request('GET', f'accounts/{account_id}/status')
            return response
        except Exception as e:
            logger.error(f"Failed to get account status {account_id}: {e}")
            raise
    
    async def restart_account(self, account_id: str) -> Dict[str, Any]:
        """Restart an account"""
        try:
            response = await self.client._make_request('POST', f'accounts/{account_id}/restart')
            return response
        except Exception as e:
            logger.error(f"Failed to restart account {account_id}: {e}")
            raise
    
    async def resync_account(self, account_id: str) -> Dict[str, Any]:
        """Resynchronize account messaging data"""
        try:
            response = await self.client._make_request('POST', f'accounts/{account_id}/resync')
            return response
        except Exception as e:
            logger.error(f"Failed to resync account {account_id}: {e}")
            raise
    
    async def solve_checkpoint(self, account_id: str, code: str) -> Dict[str, Any]:
        """Solve a code checkpoint"""
        try:
            data = {'code': code}
            response = await self.client._make_request('POST', f'accounts/{account_id}/checkpoint/solve', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to solve checkpoint for account {account_id}: {e}")
            raise
    
    async def resend_checkpoint(self, account_id: str) -> Dict[str, Any]:
        """Resend checkpoint notification"""
        try:
            response = await self.client._make_request('POST', f'accounts/{account_id}/checkpoint/resend')
            return response
        except Exception as e:
            logger.error(f"Failed to resend checkpoint for account {account_id}: {e}")
            raise
    
    async def reconnect_account(self, account_id: str) -> Dict[str, Any]:
        """Reconnect an account"""
        try:
            response = await self.client._make_request('POST', f'accounts/{account_id}/reconnect')
            return response
        except Exception as e:
            logger.error(f"Failed to reconnect account {account_id}: {e}")
            raise


class UnipileMessagingClient:
    """UniPile messaging client"""
    
    def __init__(self, client: UnipileClient):
        self.client = client
    
    async def get_all_chats(
        self, 
        account_id: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get all chats with pagination"""
        try:
            params = {'limit': limit}
            if account_id:
                params['account_id'] = account_id
            if cursor:
                params['cursor'] = cursor
                
            response = await self.client._make_request('GET', 'chats', params=params)
            return response
        except Exception as e:
            logger.error(f"Failed to get chats: {e}")
            raise
    
    async def get_chat(self, chat_id: str) -> Dict[str, Any]:
        """Get specific chat details"""
        try:
            response = await self.client._make_request('GET', f'chats/{chat_id}')
            return response
        except Exception as e:
            logger.error(f"Failed to get chat {chat_id}: {e}")
            raise
    
    async def get_all_messages(
        self, 
        chat_id: Optional[str] = None,
        account_id: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 50,
        since: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all messages with pagination"""
        try:
            params = {'limit': limit}
            if chat_id:
                params['chat_id'] = chat_id
            if account_id:
                params['account_id'] = account_id
            if cursor:
                params['cursor'] = cursor
            if since:
                params['since'] = since
                
            response = await self.client._make_request('GET', 'messages', params=params)
            return response
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            raise
    
    async def send_message(
        self, 
        chat_id: str, 
        text: str,
        attachments: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Send message to existing chat"""
        try:
            data = {
                'chat_id': chat_id,
                'text': text
            }
            if attachments:
                data['attachments'] = attachments
                
            response = await self.client._make_request('POST', 'messages/send', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise
    
    async def start_new_chat(
        self, 
        account_id: str, 
        attendees_ids: List[str], 
        text: str,
        attachments: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Start new chat with message"""
        try:
            data = {
                'account_id': account_id,
                'attendees_ids': attendees_ids,
                'text': text
            }
            if attachments:
                data['attachments'] = attachments
                
            response = await self.client._make_request('POST', 'chats/start', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to start new chat: {e}")
            raise
    
    async def get_all_attendees(
        self, 
        account_id: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get all chat attendees"""
        try:
            params = {'limit': limit}
            if account_id:
                params['account_id'] = account_id
            if cursor:
                params['cursor'] = cursor
                
            response = await self.client._make_request('GET', 'attendees', params=params)
            return response
        except Exception as e:
            logger.error(f"Failed to get attendees: {e}")
            raise


class UnipileUsersClient:
    """UniPile users client"""
    
    def __init__(self, client: UnipileClient):
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


class UnipileWebhookClient:
    """UniPile webhook management client"""
    
    def __init__(self, client: UnipileClient):
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


class UnipileRequestClient:
    """UniPile custom request client for unsupported endpoints"""
    
    def __init__(self, client: UnipileClient):
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
    
    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make custom DELETE request"""
        return await self.client._make_request('DELETE', endpoint)


class UnipileService:
    """
    High-level UniPile service for Django integration
    Uses global configuration and manages user-level connections
    """
    
    def __init__(self):
        self._client = None  # Single global client
    
    def get_client(self) -> UnipileClient:
        """Get or create global UniPile client"""
        if self._client is None:
            # Import the global config directly from settings module
            from oneo_crm.settings import unipile_settings as global_config
            
            if not global_config.is_configured():
                raise UnipileConnectionError("UniPile not configured. Please set UNIPILE_DSN and UNIPILE_API_KEY")
            
            self._client = UnipileClient(global_config.dsn, global_config.api_key)
        
        return self._client
    
    async def connect_user_account(
        self, 
        user_channel_connection,
        provider: str, 
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Connect user account via tenant's UniPile configuration"""
        from django.db import connection
        
        try:
            # Get tenant UniPile config
            tenant = connection.tenant
            if not hasattr(tenant, 'unipile_config') or not tenant.unipile_config.is_configured():
                raise UnipileConnectionError("Tenant UniPile configuration not found or incomplete")
            
            tenant_config = tenant.unipile_config
            client = self.get_client(tenant_config.dsn, tenant_config.get_access_token())
            
            # Connect account based on provider
            if provider == 'linkedin':
                result = await client.account.connect_linkedin(
                    username=credentials.get('username'),
                    password=credentials.get('password')
                )
            elif provider == 'gmail':
                result = await client.account.connect_gmail(
                    email=credentials.get('email'),
                    password=credentials.get('password')
                )
            elif provider == 'outlook':
                result = await client.account.connect_outlook(
                    email=credentials.get('email'),
                    password=credentials.get('password')
                )
            elif provider == 'whatsapp':
                result = await client.account.connect_whatsapp()
            else:
                raise UnipileConnectionError(f"Unsupported provider: {provider}")
            
            # Update user channel connection with UniPile account ID
            if result.get('account_id'):
                user_channel_connection.unipile_account_id = result['account_id']
                user_channel_connection.auth_status = 'connected'
                user_channel_connection.provider_config = result.get('config', {})
                await sync_to_async(user_channel_connection.save)()
            
            return {
                'success': True,
                'account_id': result.get('account_id'),
                'provider': provider,
                'qr_code': result.get('qrCodeString'),  # For WhatsApp
                'config': result.get('config', {})
            }
            
        except Exception as e:
            logger.error(f"Failed to connect {provider} account: {e}")
            
            # Update user channel connection with error status
            user_channel_connection.auth_status = 'error'
            await sync_to_async(user_channel_connection.save)()
            
            return {
                'success': False,
                'error': str(e),
                'provider': provider
            }
    
    async def send_message(
        self,
        user_channel_connection,
        recipient: str,
        content: str,
        message_type: str = 'text',
        attachments: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Send message via user's channel connection"""
        from django.db import connection
        
        try:
            # Get tenant and client
            tenant = connection.tenant
            tenant_config = tenant.unipile_config
            client = self.get_client(tenant_config.dsn, tenant_config.get_access_token())
            
            # Check if user can send messages
            if not user_channel_connection.can_send_messages():
                raise UnipileConnectionError("User channel not ready for sending messages")
            
            # Find existing chat or start new one
            # First, try to find existing chat with recipient
            chats_response = await client.messaging.get_all_chats(
                account_id=user_channel_connection.unipile_account_id
            )
            
            existing_chat_id = None
            for chat in chats_response.get('chats', []):
                # Check if recipient is in chat attendees
                attendees = chat.get('attendees', [])
                for attendee in attendees:
                    if (attendee.get('email') == recipient or 
                        attendee.get('phone') == recipient or
                        attendee.get('username') == recipient):
                        existing_chat_id = chat.get('id')
                        break
                if existing_chat_id:
                    break
            
            # Send message
            if existing_chat_id:
                # Send to existing chat
                result = await client.messaging.send_message(
                    chat_id=existing_chat_id,
                    text=content,
                    attachments=attachments
                )
            else:
                # Start new chat
                result = await client.messaging.start_new_chat(
                    account_id=user_channel_connection.unipile_account_id,
                    attendees_ids=[recipient],  # UniPile will resolve recipient
                    text=content,
                    attachments=attachments
                )
            
            # Record message sent
            user_channel_connection.record_message_sent()
            
            return {
                'success': True,
                'message_id': result.get('message_id'),
                'chat_id': result.get('chat_id'),
                'recipient': recipient,
                'content': content
            }
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return {
                'success': False,
                'error': str(e),
                'recipient': recipient
            }
    
    async def sync_messages(
        self,
        user_channel_connection,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Sync messages from user's channel connection"""
        from django.db import connection
        
        try:
            # Get tenant and client
            tenant = connection.tenant
            tenant_config = tenant.unipile_config
            client = self.get_client(tenant_config.dsn, tenant_config.get_access_token())
            
            # Get messages since last sync
            params = {
                'account_id': user_channel_connection.unipile_account_id,
                'limit': limit
            }
            
            if since:
                params['since'] = since.isoformat()
            
            messages_response = await client.messaging.get_all_messages(**params)
            messages = messages_response.get('messages', [])
            
            # Process messages (this would integrate with existing message processing)
            processed_count = 0
            for message_data in messages:
                # This would call the existing message processing logic
                # For now, just count the messages
                processed_count += 1
            
            # Update sync status
            user_channel_connection.record_sync_success()
            
            return {
                'success': True,
                'processed_count': processed_count,
                'total_messages': len(messages),
                'account_id': user_channel_connection.unipile_account_id
            }
            
        except Exception as e:
            logger.error(f"Failed to sync messages: {e}")
            user_channel_connection.record_sync_failure()
            
            return {
                'success': False,
                'error': str(e),
                'processed_count': 0
            }
    
    async def disconnect_account(self, user_channel_connection) -> Dict[str, Any]:
        """Disconnect user's account"""
        from django.db import connection
        
        try:
            # Get tenant and client
            tenant = connection.tenant
            tenant_config = tenant.unipile_config
            client = self.get_client(tenant_config.dsn, tenant_config.get_access_token())
            
            # Disconnect from UniPile
            if user_channel_connection.unipile_account_id:
                await client.account.disconnect_account(user_channel_connection.unipile_account_id)
            
            # Update local status
            user_channel_connection.auth_status = 'disconnected'
            user_channel_connection.unipile_account_id = None
            await sync_to_async(user_channel_connection.save)()
            
            return {
                'success': True,
                'message': 'Account disconnected successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to disconnect account: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Global service instance
unipile_service = UnipileService()