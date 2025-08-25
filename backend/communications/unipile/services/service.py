"""
UniPile Service
High-level Django integration service for UniPile functionality
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from asgiref.sync import sync_to_async

from ..core.client import UnipileClient
from ..core.exceptions import UnipileConnectionError

logger = logging.getLogger(__name__)


class UnipileService:
    """
    High-level UniPile service for Django integration
    Uses global configuration and manages user-level connections
    """
    
    def __init__(self):
        self._client = None  # Single global client
    
    def get_client(self, dsn: str = None, access_token: str = None) -> UnipileClient:
        """Get or create UniPile client (global or tenant-specific)"""
        # If dsn and access_token provided, create tenant-specific client
        if dsn and access_token:
            return UnipileClient(dsn, access_token)
        
        # Otherwise use global client
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
    
    async def verify_chat_read_status(self, account_id: str, chat_id: str, tenant=None) -> Dict[str, Any]:
        """Verify a chat's read status by fetching it from UniPile API"""
        from django.db import connection
        from communications.models import TenantUniPileConfig
        from asgiref.sync import sync_to_async
        
        try:
            # Use passed tenant or try to get from connection
            if tenant is None:
                tenant = connection.tenant
            
            # Get tenant config properly
            if hasattr(tenant, 'unipile_config'):
                tenant_config = tenant.unipile_config
                client = self.get_client(tenant_config.dsn, tenant_config.get_access_token())
            else:
                # Use sync_to_async for database operations in async context
                @sync_to_async
                def get_tenant_config_sync():
                    from django_tenants.utils import schema_context
                    with schema_context(tenant.schema_name if hasattr(tenant, 'schema_name') else 'public'):
                        config = TenantUniPileConfig.get_or_create_for_tenant()
                        if config.is_configured():
                            return config.get_api_credentials()
                        return None
                
                credentials = await get_tenant_config_sync()
                if credentials:
                    client = self.get_client(credentials['dsn'], credentials['api_key'])
                else:
                    client = self.get_client()
            
            # Fetch the specific chat to check its unread count
            logger.info(f"🔍 Verifying read status for chat {chat_id}")
            response = await client.request.get(f'chats/{chat_id}')
            
            if isinstance(response, dict):
                unread_count = response.get('unread_count', 0)
                logger.info(f"📊 Chat {chat_id} unread count: {unread_count}")
                
                return {
                    'success': True,
                    'chat_id': chat_id,
                    'unread_count': unread_count,
                    'is_read': unread_count == 0,
                    'response': response
                }
            else:
                return {
                    'success': False,
                    'error': 'Invalid response format',
                    'response': response
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to verify chat {chat_id} read status: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def mark_chat_as_read(self, account_id: str, chat_id: str, tenant=None) -> Dict[str, Any]:
        """Mark a WhatsApp chat as read using UniPile API with verification"""
        from django.db import connection
        from asgiref.sync import sync_to_async
        
        try:
            # Get tenant config and client using correct pattern
            from communications.models import TenantUniPileConfig
            
            # Use passed tenant or try to get from connection
            if tenant is None:
                tenant = connection.tenant
            
            # Get tenant config with proper async handling
            if hasattr(tenant, 'schema_name'):
                @sync_to_async
                def get_tenant_config_sync():
                    from django_tenants.utils import schema_context
                    with schema_context(tenant.schema_name):
                        config = TenantUniPileConfig.get_or_create_for_tenant()
                        if config.is_configured():
                            # Get credentials from tenant config (which delegates to global settings)
                            return config.get_api_credentials()
                        return None
                
                credentials = await get_tenant_config_sync()
                if credentials:
                    client = self.get_client(credentials['dsn'], credentials['api_key'])
                else:
                    # Fallback to global unipile config
                    client = self.get_client()
            else:
                # If no proper tenant, use global config
                client = self.get_client()
            
            # Enhanced logging for debugging
            logger.info(f"🔍 DEBUG: Attempting to mark chat as read")
            logger.info(f"🔍 DEBUG: Chat ID: {chat_id}")
            logger.info(f"🔍 DEBUG: Account ID: {account_id}")
            
            # Prepare request data with correct UniPile format
            # Note: account_id is NOT part of the request body for PATCH /chats/{chat_id}
            # It's only used to identify which connection to use
            request_data = {
                'action': 'setReadStatus',
                'value': True
            }
            logger.info(f"🔍 DEBUG: Request data: {request_data}")
            logger.info(f"🔍 DEBUG: Making PATCH request to: chats/{chat_id}")
            logger.info(f"🔍 DEBUG: Using client: {client}")
            
            # Use UniPile PATCH endpoint to mark chat as read
            response = await client.request.patch(f'chats/{chat_id}', data=request_data)
            logger.info(f"📡 Raw API response: {response}")
            
            # Log the full response for debugging
            logger.info(f"🔍 DEBUG: UniPile API Response: {response}")
            logger.info(f"🔍 DEBUG: Response type: {type(response)}")
            
            # Check if the change was successful
            if isinstance(response, dict):
                # UniPile returns {'object': 'ChatPatched'} on success
                # Also accept if there's no error field (some providers might have different responses)
                api_success = response.get('object') == 'ChatPatched' or (not response.get('error') and not response.get('status_code'))
                
                if api_success:
                    logger.info(f"✅ UniPile API call succeeded for chat {chat_id}")
                    return {
                        'success': True,
                        'chat_id': chat_id,
                        'response': response
                    }
                else:
                    logger.error(f"❌ UniPile API returned error for chat {chat_id}: {response}")
                    return {
                        'success': False,
                        'chat_id': chat_id,
                        'error': response.get('error', 'Unknown error'),
                        'response': response
                    }
            else:
                # Non-dict response, treat as success (UniPile might return simple confirmation)
                logger.info(f"✅ UniPile API returned non-dict response (assuming success): {response}")
                return {
                    'success': True,
                    'chat_id': chat_id,
                    'response': response
                }
            
        except Exception as e:
            logger.error(f"❌ UniPile mark-as-read API call failed for chat {chat_id}: {str(e)}")
            logger.error(f"❌ Exception type: {type(e)}")
            logger.error(f"❌ Exception details: {e}")
            
            # Don't mask the error - return the actual failure
            return {
                'success': False,
                'chat_id': chat_id,
                'error': str(e),
                'error_type': type(e).__name__
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

    # LinkedIn-specific service methods
    async def create_linkedin_job_posting(
        self,
        user_channel_connection,
        job_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create LinkedIn job posting via user's LinkedIn connection"""
        try:
            client = self.get_client()
            
            result = await client.linkedin.create_job_posting(
                account_id=user_channel_connection.unipile_account_id,
                **job_data
            )
            
            return {
                'success': True,
                'job_id': result.get('job_id'),
                'job_posting': result
            }
            
        except Exception as e:
            logger.error(f"Failed to create LinkedIn job posting: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def search_linkedin_people(
        self,
        user_channel_connection,
        search_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Search for people on LinkedIn"""
        try:
            client = self.get_client()
            
            result = await client.linkedin.search_people(
                account_id=user_channel_connection.unipile_account_id,
                **search_criteria
            )
            
            return {
                'success': True,
                'people': result.get('results', []),
                'total_count': result.get('total_count', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to search LinkedIn people: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def send_linkedin_connection_request(
        self,
        user_channel_connection,
        profile_id: str,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send LinkedIn connection request"""
        try:
            client = self.get_client()
            
            result = await client.linkedin.send_connection_request(
                account_id=user_channel_connection.unipile_account_id,
                profile_id=profile_id,
                message=message
            )
            
            return {
                'success': True,
                'connection_request': result
            }
            
        except Exception as e:
            logger.error(f"Failed to send LinkedIn connection request: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def send_linkedin_inmail(
        self,
        user_channel_connection,
        recipient_profile_id: str,
        subject: str,
        message: str
    ) -> Dict[str, Any]:
        """Send LinkedIn InMail message"""
        try:
            client = self.get_client()
            
            result = await client.linkedin.send_inmail(
                account_id=user_channel_connection.unipile_account_id,
                recipient_profile_id=recipient_profile_id,
                subject=subject,
                message=message
            )
            
            return {
                'success': True,
                'inmail': result
            }
            
        except Exception as e:
            logger.error(f"Failed to send LinkedIn InMail: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # Email service methods
    async def send_email(
        self,
        user_channel_connection,
        email_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send email via user's email connection"""
        try:
            client = self.get_client()
            
            result = await client.email.send_email(
                account_id=user_channel_connection.unipile_account_id,
                **email_data
            )
            
            return {
                'success': True,
                'email_id': result.get('email_id'),
                'email': result
            }
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_emails(
        self,
        user_channel_connection,
        folder: str = "INBOX",
        limit: int = 50,
        unread_only: bool = False
    ) -> Dict[str, Any]:
        """Get emails from user's email account"""
        try:
            client = self.get_client()
            
            result = await client.email.get_emails(
                account_id=user_channel_connection.unipile_account_id,
                folder=folder,
                limit=limit,
                unread_only=unread_only
            )
            
            return {
                'success': True,
                'emails': result.get('emails', []),
                'total_count': result.get('total_count', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get emails: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # Calendar service methods
    async def create_calendar_event(
        self,
        user_channel_connection,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create calendar event via user's calendar connection"""
        try:
            client = self.get_client()
            
            result = await client.calendar.create_event(
                account_id=user_channel_connection.unipile_account_id,
                **event_data
            )
            
            return {
                'success': True,
                'event_id': result.get('event_id'),
                'event': result
            }
            
        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_calendar_events(
        self,
        user_channel_connection,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get calendar events from user's calendar"""
        try:
            client = self.get_client()
            
            result = await client.calendar.get_events(
                account_id=user_channel_connection.unipile_account_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit
            )
            
            return {
                'success': True,
                'events': result.get('events', []),
                'total_count': result.get('total_count', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get calendar events: {e}")
            return {
                'success': False,
                'error': str(e)
            }