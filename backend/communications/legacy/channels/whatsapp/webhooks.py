"""
WhatsApp Webhook Handler
Processes real-time webhook events from UniPile
"""
import logging
from typing import Dict, Any, Optional
from ..base import BaseWebhookHandler
from .service import WhatsAppService

logger = logging.getLogger(__name__)


class WhatsAppWebhookHandler(BaseWebhookHandler):
    """WhatsApp webhook handler for real-time updates"""
    
    def __init__(self):
        """Initialize WhatsApp webhook handler"""
        super().__init__('whatsapp')
        self.service = WhatsAppService()
    
    def get_supported_events(self) -> list[str]:
        """Get list of supported WhatsApp webhook events"""
        return [
            # Message events
            'message.received',
            'message_received',  # Alternative format
            'message.sent',
            'message_sent',
            'message.delivered',
            'message_delivered',
            'message.read',
            'message_read',
            'message.deleted',
            
            # Chat events
            'chat.created',
            'chat.updated',
            'chat.archived',
            'chat.unarchived',
            
            # Attendee events
            'attendee.added',
            'attendee.removed',
            'attendee.updated',
            
            # Account events
            'account.connected',
            'account.disconnected',
            'account.error',
            'account.updated',
            
            # Status events
            'status.typing',
            'status.online',
            'status.offline'
        ]
    
    def extract_account_id(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Extract UniPile account ID from webhook data
        
        WhatsApp webhooks may have account ID in various locations
        """
        # Try direct account_id field
        if 'account_id' in data:
            return str(data['account_id'])
        
        # Try accountId (camelCase)
        if 'accountId' in data:
            return str(data['accountId'])
        
        # Try account object
        if 'account' in data:
            if isinstance(data['account'], dict):
                return str(data['account'].get('id'))
            else:
                return str(data['account'])
        
        # Try from_account_id (for some message events)
        if 'from_account_id' in data:
            return str(data['from_account_id'])
        
        # Try message object
        if 'message' in data and isinstance(data['message'], dict):
            return (
                data['message'].get('account_id') or
                data['message'].get('accountId') or
                data['message'].get('from_account_id')
            )
        
        # Try chat object
        if 'chat' in data and isinstance(data['chat'], dict):
            return data['chat'].get('account_id')
        
        logger.warning(f"Could not extract account_id from WhatsApp webhook: {data.keys()}")
        return None
    
    def handle_message_received(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming WhatsApp message
        Real-time processing for immediate updates
        """
        try:
            # Use async_to_sync to call the async service method
            from asgiref.sync import async_to_sync
            result = async_to_sync(self.service.process_webhook)(
                event_type='message.received',
                data=data,
                account_id=account_id
            )
            
            logger.info(f"✅ Processed incoming WhatsApp message for account {account_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to handle WhatsApp message received: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_message_sent(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle outbound message confirmation"""
        try:
            from asgiref.sync import async_to_sync
            result = async_to_sync(self.service.process_webhook)(
                event_type='message.sent',
                data=data,
                account_id=account_id
            )
            
            logger.info(f"✅ Processed outbound WhatsApp message for account {account_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to handle WhatsApp message sent: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_message_delivered(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message delivery status update"""
        try:
            from asgiref.sync import async_to_sync
            result = async_to_sync(self.service.process_webhook)(
                event_type='message.delivered',
                data=data,
                account_id=account_id
            )
            
            logger.debug(f"Updated WhatsApp message delivery status")
            return result
            
        except Exception as e:
            logger.error(f"Failed to handle WhatsApp message delivered: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_message_read(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message read receipt"""
        try:
            from asgiref.sync import async_to_sync
            result = async_to_sync(self.service.process_webhook)(
                event_type='message.read',
                data=data,
                account_id=account_id
            )
            
            logger.debug(f"Updated WhatsApp message read status")
            return result
            
        except Exception as e:
            logger.error(f"Failed to handle WhatsApp message read: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_message_deleted(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message deletion"""
        try:
            from communications.models import Message, Channel
            
            message_id = data.get('message_id') or data.get('id')
            if not message_id:
                return {'success': False, 'error': 'No message_id in deletion webhook'}
            
            # Mark message as deleted
            channel = Channel.objects.filter(
                unipile_account_id=account_id,
                channel_type='whatsapp'
            ).first()
            
            if channel:
                message = Message.objects.filter(
                    external_message_id=message_id,
                    channel=channel
                ).first()
                
                if message:
                    message.is_deleted = True
                    message.content = "[Message deleted]"
                    message.save()
                    logger.info(f"Marked WhatsApp message {message_id} as deleted")
                    return {'success': True, 'deleted': True}
            
            return {'success': False, 'error': 'Message not found'}
            
        except Exception as e:
            logger.error(f"Failed to handle WhatsApp message deletion: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_chat_created(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle new chat creation"""
        try:
            from asgiref.sync import async_to_sync
            from communications.models import Channel
            
            # Get channel
            channel = Channel.objects.filter(
                unipile_account_id=account_id,
                channel_type='whatsapp'
            ).first()
            
            if not channel:
                logger.warning(f"No channel found for WhatsApp account {account_id}")
                return {'success': False, 'error': 'Channel not found'}
            
            # Store the new conversation
            chat_data = data.get('chat', data)
            result = async_to_sync(self.service._store_conversation)(channel, chat_data)
            
            logger.info(f"✅ Created new WhatsApp chat from webhook")
            return {'success': True, 'chat_created': True}
            
        except Exception as e:
            logger.error(f"Failed to handle WhatsApp chat creation: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_chat_updated(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat updates (name change, settings, etc.)"""
        try:
            from communications.models import Channel, Conversation
            
            chat_id = data.get('chat_id') or data.get('chat', {}).get('id')
            if not chat_id:
                return {'success': False, 'error': 'No chat_id in update webhook'}
            
            # Get channel and conversation
            channel = Channel.objects.filter(
                unipile_account_id=account_id,
                channel_type='whatsapp'
            ).first()
            
            if channel:
                conversation = Conversation.objects.filter(
                    channel=channel,
                    external_thread_id=chat_id
                ).first()
                
                if conversation:
                    # Update conversation metadata
                    updates = data.get('updates', {})
                    if 'name' in updates:
                        conversation.subject = updates['name']
                    if 'archived' in updates:
                        conversation.is_archived = updates['archived']
                    
                    conversation.save()
                    logger.info(f"Updated WhatsApp chat {chat_id}")
                    return {'success': True, 'updated': True}
            
            return {'success': False, 'error': 'Conversation not found'}
            
        except Exception as e:
            logger.error(f"Failed to handle WhatsApp chat update: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_attendee_added(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle attendee added to chat"""
        try:
            from asgiref.sync import async_to_sync
            result = async_to_sync(self.service.process_webhook)(
                event_type='attendee.added',
                data=data,
                account_id=account_id
            )
            
            logger.info(f"✅ Added attendee to WhatsApp chat")
            return result
            
        except Exception as e:
            logger.error(f"Failed to handle attendee addition: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_attendee_removed(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle attendee removed from chat"""
        try:
            from asgiref.sync import async_to_sync
            result = async_to_sync(self.service.process_webhook)(
                event_type='attendee.removed',
                data=data,
                account_id=account_id
            )
            
            logger.info(f"✅ Removed attendee from WhatsApp chat")
            return result
            
        except Exception as e:
            logger.error(f"Failed to handle attendee removal: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_account_connected(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle WhatsApp account connection"""
        try:
            from communications.models import UserChannelConnection
            
            # Update connection status
            connection = UserChannelConnection.objects.filter(
                unipile_account_id=account_id,
                channel_type='whatsapp'
            ).first()
            
            if connection:
                connection.account_status = 'active'
                connection.last_sync_at = timezone.now()
                connection.save()
                logger.info(f"✅ WhatsApp account {account_id} connected")
                return {'success': True, 'connected': True}
            
            return {'success': False, 'error': 'Connection not found'}
            
        except Exception as e:
            logger.error(f"Failed to handle account connection: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_account_disconnected(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle WhatsApp account disconnection"""
        try:
            from communications.models import UserChannelConnection
            
            # Update connection status
            connection = UserChannelConnection.objects.filter(
                unipile_account_id=account_id,
                channel_type='whatsapp'
            ).first()
            
            if connection:
                connection.account_status = 'disconnected'
                connection.last_error = data.get('reason', 'Account disconnected')
                connection.save()
                logger.warning(f"⚠️ WhatsApp account {account_id} disconnected")
                return {'success': True, 'disconnected': True}
            
            return {'success': False, 'error': 'Connection not found'}
            
        except Exception as e:
            logger.error(f"Failed to handle account disconnection: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_account_error(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle WhatsApp account error"""
        try:
            from communications.models import UserChannelConnection
            
            # Update connection with error
            connection = UserChannelConnection.objects.filter(
                unipile_account_id=account_id,
                channel_type='whatsapp'
            ).first()
            
            if connection:
                connection.account_status = 'error'
                connection.last_error = data.get('error', 'Unknown error')
                connection.sync_error_count += 1
                connection.save()
                logger.error(f"❌ WhatsApp account {account_id} error: {connection.last_error}")
                return {'success': True, 'error_logged': True}
            
            return {'success': False, 'error': 'Connection not found'}
            
        except Exception as e:
            logger.error(f"Failed to handle account error: {e}")
            return {'success': False, 'error': str(e)}