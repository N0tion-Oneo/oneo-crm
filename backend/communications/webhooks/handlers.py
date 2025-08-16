"""
UniPile webhook event handlers
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from communications.models import UserChannelConnection, Message, Conversation, ChannelType, MessageDirection, MessageStatus
from communications.webhooks.routing import account_router

logger = logging.getLogger(__name__)


class UnipileWebhookHandler:
    """Handles different types of UniPile webhook events"""
    
    def __init__(self):
        self.event_handlers = {
            'message.received': self.handle_message_received,
            'message.sent': self.handle_message_sent,
            'account.connected': self.handle_account_connected,
            'account.disconnected': self.handle_account_disconnected,
            'account.error': self.handle_account_error,
            'account.checkpoint': self.handle_account_checkpoint,
            # Enhanced UniPile account events
            'creation_success': self.handle_account_created,
            'creation_fail': self.handle_account_creation_failed,
            'credentials': self.handle_credentials_required,
            'permissions': self.handle_permissions_error,
            'error': self.handle_account_error,
        }
    
    def process_webhook(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a webhook event
        
        Args:
            event_type: Type of webhook event
            data: Event data from UniPile
            
        Returns:
            Dict[str, Any]: Processing result
        """
        logger.info(f"Processing webhook event: {event_type}")
        
        # Extract account ID from event data
        account_id = self.extract_account_id(data)
        if not account_id:
            logger.error(f"No account ID found in webhook data: {data}")
            return {'success': False, 'error': 'No account ID in webhook data'}
        
        # Get event handler
        handler = self.event_handlers.get(event_type)
        if not handler:
            logger.warning(f"No handler for event type: {event_type}")
            return {'success': False, 'error': f'Unsupported event type: {event_type}'}
        
        # Route to correct tenant and process
        result = account_router.process_with_tenant_context(
            account_id, 
            handler, 
            data
        )
        
        if result is None:
            return {'success': False, 'error': 'Failed to route to tenant'}
        
        return result
    
    def extract_account_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract account ID from webhook data"""
        # Try different possible locations for account ID
        possible_keys = ['account_id', 'accountId', 'account', 'from_account_id']
        
        for key in possible_keys:
            if key in data:
                return str(data[key])
        
        # Check nested structures
        if 'account' in data and isinstance(data['account'], dict):
            return str(data['account'].get('id'))
        
        if 'message' in data and isinstance(data['message'], dict):
            return str(data['message'].get('account_id'))
        
        return None
    
    def handle_message_received(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming message webhook"""
        try:
            # Get user connection (we're already in tenant context)
            connection = account_router.get_user_connection(account_id)
            if not connection:
                logger.error(f"No user connection found for account {account_id}")
                return {'success': False, 'error': 'User connection not found'}
            
            # Extract message data
            message_data = data.get('message', data)
            
            # Create or get conversation
            conversation = self.get_or_create_conversation(
                connection, 
                message_data
            )
            
            # Create message record
            message = self.create_message_record(
                connection,
                conversation,
                message_data,
                MessageDirection.INBOUND
            )
            
            logger.info(f"Created inbound message {message.id} for account {account_id}")
            
            # Auto-create contact if enabled
            if connection.user.tenant_unipile_config.auto_create_contacts:
                self.auto_create_contact(message_data, connection)
            
            return {
                'success': True,
                'message_id': str(message.id),
                'conversation_id': str(conversation.id)
            }
            
        except Exception as e:
            logger.error(f"Error handling message received for account {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_message_sent(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle outbound message confirmation webhook"""
        try:
            # Update message status if we have a record
            message_data = data.get('message', data)
            external_message_id = message_data.get('id')
            
            if external_message_id:
                # Find existing message record
                message = Message.objects.filter(
                    external_message_id=external_message_id
                ).first()
                
                if message:
                    message.status = MessageStatus.SENT
                    message.sent_at = timezone.now()
                    message.save()
                    
                    logger.info(f"Updated message {message.id} status to sent")
                    return {'success': True, 'message_id': str(message.id)}
            
            logger.warning(f"No message record found for external ID {external_message_id}")
            return {'success': True, 'note': 'No local message record to update'}
            
        except Exception as e:
            logger.error(f"Error handling message sent for account {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_account_connected(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle account connection success webhook"""
        try:
            connection = account_router.get_user_connection(account_id)
            if connection:
                connection.auth_status = 'authenticated'
                connection.last_sync_at = timezone.now()
                connection.sync_error_count = 0
                connection.last_error = ''
                connection.save()
                
                logger.info(f"Account {account_id} connected successfully")
                return {'success': True, 'status': 'connected'}
            
            return {'success': False, 'error': 'Connection not found'}
            
        except Exception as e:
            logger.error(f"Error handling account connected for {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_account_disconnected(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle account disconnection webhook"""
        try:
            connection = account_router.get_user_connection(account_id)
            if connection:
                connection.auth_status = 'failed'
                connection.last_error = data.get('reason', 'Account disconnected')
                connection.save()
                
                logger.warning(f"Account {account_id} disconnected: {connection.last_error}")
                return {'success': True, 'status': 'disconnected'}
            
            return {'success': False, 'error': 'Connection not found'}
            
        except Exception as e:
            logger.error(f"Error handling account disconnected for {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_account_error(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle account error webhook"""
        try:
            connection = account_router.get_user_connection(account_id)
            if connection:
                connection.auth_status = 'failed'
                connection.sync_error_count += 1
                connection.last_error = data.get('error', 'Unknown error')
                connection.save()
                
                logger.error(f"Account {account_id} error: {connection.last_error}")
                return {'success': True, 'status': 'error_recorded'}
            
            return {'success': False, 'error': 'Connection not found'}
            
        except Exception as e:
            logger.error(f"Error handling account error for {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_account_checkpoint(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle account checkpoint (2FA) webhook"""
        try:
            connection = account_router.get_user_connection(account_id)
            if connection:
                connection.auth_status = 'pending'
                # Store checkpoint data for frontend to handle
                checkpoint_data = {
                    'type': data.get('checkpoint_type', 'unknown'),
                    'message': data.get('message', 'Checkpoint required'),
                    'timestamp': timezone.now().isoformat()
                }
                connection.connection_config['checkpoint'] = checkpoint_data
                connection.save()
                
                logger.info(f"Account {account_id} requires checkpoint: {checkpoint_data['type']}")
                return {'success': True, 'status': 'checkpoint_required'}
            
            return {'success': False, 'error': 'Connection not found'}
            
        except Exception as e:
            logger.error(f"Error handling account checkpoint for {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_or_create_conversation(self, connection: UserChannelConnection, message_data: Dict[str, Any]) -> Conversation:
        """Get or create conversation for message"""
        # Try to find existing conversation
        external_thread_id = message_data.get('thread_id') or message_data.get('conversation_id')
        
        if external_thread_id:
            conversation = Conversation.objects.filter(
                external_thread_id=external_thread_id
            ).first()
            if conversation:
                return conversation
        
        # Create new conversation
        from communications.models import Channel
        
        # Get or create channel for this connection
        channel, _ = Channel.objects.get_or_create(
            external_account_id=connection.external_account_id,
            channel_type=connection.channel_type,
            defaults={
                'name': f"{connection.channel_type.title()} - {connection.account_name}",
                'auth_status': connection.auth_status,
                'created_by': connection.user
            }
        )
        
        conversation = Conversation.objects.create(
            channel=channel,
            external_thread_id=external_thread_id or f"msg_{message_data.get('id', timezone.now().timestamp())}",
            subject=message_data.get('subject', f"Conversation via {connection.channel_type}"),
            status='active'
        )
        
        return conversation
    
    def create_message_record(self, connection: UserChannelConnection, conversation: Conversation, 
                            message_data: Dict[str, Any], direction: str) -> Message:
        """Create message record from webhook data"""
        
        # Extract sender/recipient info
        sender_email = message_data.get('from', {}).get('email') if isinstance(message_data.get('from'), dict) else message_data.get('from')
        contact_email = sender_email if direction == MessageDirection.INBOUND else message_data.get('to')
        
        message = Message.objects.create(
            channel=conversation.channel,
            conversation=conversation,
            external_message_id=message_data.get('id'),
            direction=direction,
            content=message_data.get('text', message_data.get('content', '')),
            subject=message_data.get('subject', ''),
            contact_email=contact_email or '',
            status=MessageStatus.DELIVERED if direction == MessageDirection.INBOUND else MessageStatus.SENT,
            metadata=message_data,
            sent_at=timezone.now() if direction == MessageDirection.OUTBOUND else None,
            received_at=timezone.now() if direction == MessageDirection.INBOUND else None
        )
        
        return message
    
    def auto_create_contact(self, message_data: Dict[str, Any], connection: UserChannelConnection):
        """Auto-create contact from message if enabled"""
        try:
            from communications.services import communication_service
            
            # Extract contact info
            sender_info = message_data.get('from', {})
            if isinstance(sender_info, str):
                sender_email = sender_info
                sender_name = None
            else:
                sender_email = sender_info.get('email')
                sender_name = sender_info.get('name')
            
            if sender_email:
                # Try to create/resolve contact
                communication_service.resolve_or_create_contact(
                    recipient=sender_email,
                    name=sender_name,
                    additional_data={
                        'source': 'webhook',
                        'channel_type': connection.channel_type
                    }
                )
                
        except Exception as e:
            logger.warning(f"Failed to auto-create contact: {e}")
    
    def handle_account_created(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful account creation webhook from UniPile"""
        try:
            # This is called when a hosted auth account is successfully created
            # The account_id is the new UniPile account ID
            provider = data.get('provider', '').lower()
            
            logger.info(f"Account created successfully: {account_id}, provider: {provider}")
            
            # Try to find pending connections that match this creation
            # Look for recent pending connections for this provider type
            recent_pending = UserChannelConnection.objects.filter(
                channel_type=provider,
                account_status='pending',
                external_account_id__isnull=True,
                created_at__gte=timezone.now() - timezone.timedelta(hours=1)
            ).order_by('-created_at')
            
            if recent_pending.exists():
                connection = recent_pending.first()
                
                # Update the connection with the new account ID
                connection.external_account_id = account_id
                connection.account_status = 'active'
                connection.auth_status = 'authenticated'
                connection.hosted_auth_url = ''
                connection.last_sync_at = timezone.now()
                
                # Store account metadata
                if 'account' in data:
                    connection.connection_config['account_info'] = data['account']
                
                connection.save()
                
                logger.info(f"Linked new account {account_id} to connection {connection.id}")
                
                return {
                    'success': True,
                    'linked_connection': str(connection.id),
                    'account_id': account_id
                }
            else:
                # No pending connection found - this might be a manual creation
                logger.warning(f"No pending connection found for new account {account_id} of type {provider}")
                return {
                    'success': True,
                    'note': 'Account created but no pending connection to link'
                }
            
        except Exception as e:
            logger.error(f"Error handling account creation for {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_account_creation_failed(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed account creation webhook from UniPile"""
        try:
            provider = data.get('provider', '').lower()
            error_message = data.get('error', 'Account creation failed')
            
            logger.warning(f"Account creation failed for provider {provider}: {error_message}")
            
            # Find and update pending connections
            recent_pending = UserChannelConnection.objects.filter(
                channel_type=provider,
                account_status='pending',
                created_at__gte=timezone.now() - timezone.timedelta(hours=1)
            ).order_by('-created_at')
            
            if recent_pending.exists():
                connection = recent_pending.first()
                connection.account_status = 'failed'
                connection.auth_status = 'failed'
                connection.last_error = error_message
                connection.hosted_auth_url = ''
                connection.save()
                
                logger.info(f"Updated connection {connection.id} with creation failure")
                
                return {
                    'success': True,
                    'updated_connection': str(connection.id),
                    'error': error_message
                }
            
            return {'success': True, 'note': 'No pending connection to update'}
            
        except Exception as e:
            logger.error(f"Error handling account creation failure: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_credentials_required(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle credentials required webhook (checkpoint/2FA needed)"""
        try:
            connection = account_router.get_user_connection(account_id)
            if connection:
                connection.account_status = 'checkpoint_required'
                connection.auth_status = 'pending'
                
                # Store checkpoint information
                checkpoint_info = {
                    'type': data.get('checkpoint_type', 'credentials'),
                    'message': data.get('message', 'Credentials verification required'),
                    'timestamp': timezone.now().isoformat(),
                    'data': data
                }
                connection.checkpoint_data = checkpoint_info
                connection.save()
                
                logger.info(f"Account {account_id} requires credentials verification")
                return {'success': True, 'status': 'checkpoint_required'}
            
            return {'success': False, 'error': 'Connection not found'}
            
        except Exception as e:
            logger.error(f"Error handling credentials required for {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_permissions_error(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle permissions error webhook"""
        try:
            connection = account_router.get_user_connection(account_id)
            if connection:
                connection.account_status = 'failed'
                connection.auth_status = 'failed'
                connection.last_error = data.get('error', 'Permissions error - please re-authenticate')
                connection.save()
                
                logger.warning(f"Account {account_id} has permissions error")
                return {'success': True, 'status': 'permissions_error'}
            
            return {'success': False, 'error': 'Connection not found'}
            
        except Exception as e:
            logger.error(f"Error handling permissions error for {account_id}: {e}")
            return {'success': False, 'error': str(e)}


# Global handler instance
webhook_handler = UnipileWebhookHandler()