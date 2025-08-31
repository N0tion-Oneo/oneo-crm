"""
WhatsApp Service with persistence and sync capabilities
Handles historical syncing via API and real-time updates via webhooks
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from asgiref.sync import sync_to_async

from ..base import BaseChannelService
from .client import WhatsAppClient
from .utils import WhatsAppAttendeeDetector, WhatsAppMessageFormatter, WhatsAppMediaHandler
from communications.utils.message_direction import determine_message_direction

logger = logging.getLogger(__name__)


class WhatsAppService(BaseChannelService):
    """WhatsApp service implementation with persistence"""
    
    def __init__(self, channel: Optional[Any] = None, account_identifier: Optional[str] = None):
        """
        Initialize WhatsApp service
        
        Args:
            channel: Channel instance to extract account identifier from
            account_identifier: Business WhatsApp phone number for owner detection (overrides channel)
        """
        # Don't call super().__init__() to avoid circular reference
        self.channel_type = 'whatsapp'
        self.client = WhatsAppClient()
        self.channel = channel
        
        # Initialize attendee detector (it will handle getting account_identifier)
        self.attendee_detector = WhatsAppAttendeeDetector(channel=channel, account_identifier=account_identifier)
        # Get the account_identifier from the detector
        self.account_identifier = self.attendee_detector.account_identifier
        
        self.message_formatter = WhatsAppMessageFormatter()
        self.media_handler = WhatsAppMediaHandler()
        
        # Cache settings
        self.conversation_cache_timeout = 60  # 1 minute for conversation list
        self.message_cache_timeout = 300  # 5 minutes for messages
    
    def get_channel_type(self) -> str:
        """Return the channel type"""
        return 'whatsapp'
    
    def get_client(self):
        """Return the WhatsApp client"""
        return self.client
    
    async def sync_conversations(
        self,
        user,
        account_id: str,
        force_sync: bool = False
    ) -> Dict[str, Any]:
        """
        Sync WhatsApp conversations using local-first architecture
        
        Strategy:
        1. Check cache if not forcing sync
        2. Query local database
        3. Trigger background API sync if needed
        4. Return local data immediately
        """
        from communications.models import Channel, Conversation, UserChannelConnection
        
        cache_key = f"whatsapp:conversations:{account_id}:{user.id}"
        
        # Step 1: Check cache
        if not force_sync:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.debug(f"✅ WhatsApp conversations cache hit for {account_id}")
                return cached_data
        
        # Step 2: Get local conversations
        try:
            # Get channel
            channel = await sync_to_async(Channel.objects.filter(
                unipile_account_id=account_id,
                channel_type='whatsapp'
            ).first)()
            
            if not channel:
                # Create channel if it doesn't exist
                channel = await self.get_or_create_channel(account_id, user)
            
            # Get conversations from database (no is_active field)
            conversations = await sync_to_async(list)(
                Conversation.objects.filter(
                    channel=channel
                ).select_related('channel').prefetch_related('messages').order_by('-last_message_at')[:50]
            )
            
            # Format conversations for response
            formatted_conversations = []
            for conv in conversations:
                # Get attendees for this conversation
                attendees = await sync_to_async(list)(
                    conv.attendees.filter(is_active=True)
                )
                
                # Get last message
                last_message = await sync_to_async(
                    conv.messages.order_by('-created_at').first
                )()
                
                formatted_conversations.append({
                    'id': conv.external_thread_id,
                    'subject': conv.subject,
                    'last_message': {
                        'content': last_message.content if last_message else None,
                        'timestamp': last_message.created_at.isoformat() if last_message else None
                    },
                    'attendees': [
                        {
                            'id': att.external_attendee_id,
                            'name': att.name,
                            'phone': att.phone_number,
                            'is_self': att.is_self
                        }
                        for att in attendees
                    ],
                    'unread_count': conv.unread_count,
                    'last_activity': conv.last_message_at.isoformat() if conv.last_message_at else None
                })
            
            result = {
                'conversations': formatted_conversations,
                'from_cache': False,
                'from_local': True,
                'sync_triggered': force_sync
            }
            
            # Step 3: Trigger background sync if forcing or data is stale
            if force_sync or await self._should_sync_conversations(channel):
                # Run API sync in background
                await self._sync_conversations_from_api(channel, account_id)
            
            # Cache the result
            cache.set(cache_key, result, self.conversation_cache_timeout)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to sync WhatsApp conversations: {e}")
            return {'conversations': [], 'error': str(e)}
    
    async def sync_messages(
        self,
        user,
        account_id: str,
        conversation_id: str,
        force_sync: bool = False
    ) -> Dict[str, Any]:
        """
        Sync WhatsApp messages for a conversation
        
        Strategy:
        1. Always sync from API for real-time messaging
        2. Store in database
        3. Return combined results
        """
        from communications.models import Channel, Conversation, Message
        
        try:
            # Get channel and conversation
            channel = await sync_to_async(Channel.objects.filter(
                unipile_account_id=account_id,
                channel_type='whatsapp'
            ).first)()
            
            if not channel:
                channel = await self.get_or_create_channel(account_id, user)
            
            conversation = await sync_to_async(Conversation.objects.filter(
                channel=channel,
                external_thread_id=conversation_id
            ).first)()
            
            # Always sync messages from API for real-time experience
            # Note: Don't pass account_id when using conversation_id endpoint
            api_messages = await self.client.get_messages(
                account_id=account_id,  # This is still needed for the client method signature
                conversation_id=conversation_id,
                limit=50
            )
            
            if api_messages.get('success') and api_messages.get('messages'):
                # Process and store messages
                await self._store_messages(
                    channel,
                    conversation,
                    api_messages['messages'],
                    conversation_id
                )
            
            # Get messages from database (now includes fresh API data)
            if conversation:
                db_messages = await sync_to_async(list)(
                    Message.objects.filter(
                        conversation=conversation
                    ).order_by('-created_at')[:100]
                )
                
                formatted_messages = []
                for msg in db_messages:
                    formatted_messages.append({
                        'id': msg.external_message_id,
                        'content': msg.content,
                        'direction': msg.direction,
                        'status': msg.status,
                        'created_at': msg.created_at.isoformat(),
                        'sender': msg.metadata.get('attendee_name') if msg.metadata else None
                    })
                
                return {
                    'messages': formatted_messages,
                    'conversation_id': conversation_id,
                    'synced': True
                }
            else:
                # No local conversation yet, return API messages
                return {
                    'messages': api_messages.get('messages', []),
                    'conversation_id': conversation_id,
                    'synced': True
                }
            
        except Exception as e:
            logger.error(f"Failed to sync WhatsApp messages: {e}")
            return {'messages': [], 'error': str(e)}
    
    async def process_webhook(
        self,
        event_type: str,
        data: Dict[str, Any],
        account_id: str
    ) -> Dict[str, Any]:
        """
        Process WhatsApp webhook events for real-time updates
        
        This handles:
        - New messages
        - Message status updates
        - Attendee changes
        - Chat updates
        """
        from communications.models import Channel, Conversation, Message, MessageDirection, MessageStatus
        
        try:
            # Get channel
            channel = await sync_to_async(Channel.objects.filter(
                unipile_account_id=account_id,
                channel_type='whatsapp'
            ).first)()
            
            if not channel:
                logger.warning(f"No WhatsApp channel found for account {account_id}")
                return {'success': False, 'error': 'Channel not found'}
            
            # Route to appropriate handler
            if event_type in ['message.received', 'message_received']:
                return await self._handle_message_received(channel, data)
            elif event_type in ['message.sent', 'message_sent']:
                return await self._handle_message_sent(channel, data)
            elif event_type in ['message.delivered', 'message_delivered']:
                return await self._handle_message_delivered(channel, data)
            elif event_type in ['message.read', 'message_read']:
                return await self._handle_message_read(channel, data)
            elif event_type == 'attendee.added':
                return await self._handle_attendee_added(channel, data)
            elif event_type == 'attendee.removed':
                return await self._handle_attendee_removed(channel, data)
            else:
                logger.info(f"Unhandled WhatsApp webhook event: {event_type}")
                return {'success': True, 'message': f'Event {event_type} received'}
            
        except Exception as e:
            logger.error(f"Failed to process WhatsApp webhook: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_message_received(self, channel, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming WhatsApp message webhook"""
        from communications.models import Conversation, Message, MessageDirection, MessageStatus
        
        # Extract message details
        message_data = data.get('message', data)
        chat_id = message_data.get('chat_id') or message_data.get('conversation_id')
        message_id = message_data.get('id') or message_data.get('message_id')
        
        if not chat_id:
            return {'success': False, 'error': 'No chat_id in webhook'}
        
        # Extract and process attendee information
        attendee_info = self.attendee_detector.extract_attendee_from_webhook(data)
        
        # Get or create conversation
        conversation = await sync_to_async(Conversation.objects.filter(
            channel=channel,
            external_thread_id=chat_id
        ).first)()
        
        if not conversation:
            # Create new conversation
            attendees = self.attendee_detector.extract_chat_attendees(data)
            conversation_name = self.message_formatter.format_conversation_name(
                {'id': chat_id}, 
                attendees
            )
            
            conversation = await sync_to_async(Conversation.objects.create)(
                channel=channel,
                external_thread_id=chat_id,
                subject=conversation_name,
                status='active',
                last_message_at=timezone.now()
            )
            
            # Process attendees with correct parameters
            for att_info in attendees:
                await sync_to_async(self.attendee_detector.create_or_update_attendee)(
                    att_info, conversation=conversation, channel=channel
                )
        
        # Check if message already exists
        existing = await sync_to_async(Message.objects.filter(
            external_message_id=message_id,
            channel=channel
        ).exists)()
        
        if existing:
            logger.debug(f"Message {message_id} already exists")
            return {'success': True, 'message': 'Already processed'}
        
        # Format and create message
        formatted = self.message_formatter.format_incoming_message(message_data)
        
        # Determine direction using unified utility
        direction_str = determine_message_direction(data, 'whatsapp', self.account_identifier)
        direction = MessageDirection.OUTBOUND if direction_str == 'out' else MessageDirection.INBOUND
        
        # Create message
        message = await sync_to_async(Message.objects.create)(
            channel=channel,
            conversation=conversation,
            external_message_id=message_id,
            content=formatted['content'],
            direction=direction,
            status=MessageStatus.DELIVERED,
            created_at=formatted.get('timestamp') or timezone.now(),
            metadata={
                'attendee_info': attendee_info,
                'media': {
                    'type': formatted.get('media_type'),
                    'url': formatted.get('media_url'),
                    'caption': formatted.get('media_caption')
                } if formatted.get('media_type') else None
            }
        )
        
        # Update conversation last message time
        conversation.last_message_at = message.created_at
        await sync_to_async(conversation.save)()
        
        # Link message to attendee with correct parameters
        if attendee_info.get('external_id'):
            attendee = await sync_to_async(self.attendee_detector.create_or_update_attendee)(
                attendee_info, conversation=conversation, channel=channel
            )
            if attendee:
                message.metadata['attendee_id'] = str(attendee.id)
                message.metadata['attendee_name'] = attendee.name
                await sync_to_async(message.save)()
        
        logger.info(f"✅ Processed WhatsApp message {message_id} in conversation {chat_id}")
        
        return {
            'success': True,
            'message_id': str(message.id),
            'conversation_id': str(conversation.id)
        }
    
    async def _handle_message_sent(self, channel, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle outbound message confirmation"""
        # Similar to received but with OUTBOUND direction
        return await self._handle_message_received(channel, data)
    
    async def _handle_message_delivered(self, channel, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update message delivery status"""
        from communications.models import Message, MessageStatus
        
        message_id = data.get('message_id') or data.get('id')
        if not message_id:
            return {'success': False, 'error': 'No message_id'}
        
        message = await sync_to_async(Message.objects.filter(
            external_message_id=message_id,
            channel=channel
        ).first)()
        
        if message:
            message.status = MessageStatus.DELIVERED
            await sync_to_async(message.save)()
            return {'success': True, 'updated': True}
        
        return {'success': False, 'error': 'Message not found'}
    
    async def _handle_message_read(self, channel, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update message read status"""
        from communications.models import Message, MessageStatus
        
        message_id = data.get('message_id') or data.get('id')
        if not message_id:
            return {'success': False, 'error': 'No message_id'}
        
        message = await sync_to_async(Message.objects.filter(
            external_message_id=message_id,
            channel=channel
        ).first)()
        
        if message:
            message.status = MessageStatus.READ
            await sync_to_async(message.save)()
            return {'success': True, 'updated': True}
        
        return {'success': False, 'error': 'Message not found'}
    
    async def _handle_attendee_added(self, channel, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle new attendee added to chat"""
        chat_id = data.get('chat_id')
        attendee_data = data.get('attendee', {})
        
        if not chat_id:
            return {'success': False, 'error': 'No chat_id'}
        
        attendee_info = self.attendee_detector.extract_attendee_from_webhook({'sender': attendee_data})
        
        if attendee_info.get('external_id'):
            attendee = await sync_to_async(self.attendee_detector.create_or_update_attendee)(
                attendee_info, conversation=None, channel=channel
            )
            if attendee:
                return {'success': True, 'attendee_id': str(attendee.id)}
        
        return {'success': False, 'error': 'Could not process attendee'}
    
    async def _handle_attendee_removed(self, channel, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle attendee removed from chat"""
        from communications.models import Conversation, ConversationParticipant, Participant
        
        chat_id = data.get('chat_id')
        attendee_id = data.get('attendee_id')
        
        if not chat_id or not attendee_id:
            return {'success': False, 'error': 'Missing chat_id or attendee_id'}
        
        # Find conversation by external_thread_id
        conversation = await sync_to_async(Conversation.objects.filter(
            external_thread_id=chat_id,
            channel=channel
        ).first)()
        
        if not conversation:
            return {'success': False, 'error': f'Conversation not found for chat {chat_id}'}
        
        # Find the conversation participant to mark as inactive
        # Note: This would need proper implementation to map attendee_id to participant
        # For now, return success as this is a deprecated endpoint
        logger.warning(f"Attendee removal webhook for deprecated model - chat_id: {chat_id}, attendee_id: {attendee_id}")
        return {'success': True, 'note': 'Deprecated endpoint - no action taken'}
    
    async def _sync_conversations_from_api(self, channel, account_id: str):
        """Background sync conversations from API"""
        try:
            # Get conversations from API
            api_result = await self.client.get_conversations(account_id)
            
            if not api_result.get('success'):
                logger.warning(f"Failed to sync conversations from API: {api_result.get('error')}")
                return
            
            conversations = api_result.get('conversations', [])
            
            # Store each conversation
            for conv_data in conversations:
                await self._store_conversation(channel, conv_data)
            
            logger.info(f"✅ Synced {len(conversations)} WhatsApp conversations from API")
            
        except Exception as e:
            logger.error(f"Failed to sync conversations from API: {e}")
    
    async def _store_conversation(self, channel, conv_data: Dict[str, Any]):
        """Store a conversation from API data"""
        from communications.models import Conversation
        
        chat_id = conv_data.get('id') or conv_data.get('chat_id')
        if not chat_id:
            return
        
        # Extract attendees
        attendees = self.attendee_detector.extract_chat_attendees(conv_data)
        
        # Generate conversation name
        conversation_name = self.message_formatter.format_conversation_name(conv_data, attendees)
        
        # Get or create conversation
        conversation, created = await sync_to_async(Conversation.objects.update_or_create)(
            channel=channel,
            external_thread_id=chat_id,
            defaults={
                'subject': conversation_name,
                'status': 'active',
                'last_message_at': conv_data.get('last_activity') or timezone.now(),
                'unread_count': conv_data.get('unread_count', 0),
                'metadata': {
                    'is_group': conv_data.get('is_group', False),
                    'participant_count': len(attendees)
                }
            }
        )
        
        # Process attendees with correct parameters
        for att_info in attendees:
            await sync_to_async(self.attendee_detector.create_or_update_attendee)(
                att_info, conversation=conversation, channel=channel
            )
        
        if created:
            logger.debug(f"Created conversation: {conversation_name}")
        else:
            logger.debug(f"Updated conversation: {conversation_name}")
    
    async def _store_messages(self, channel, conversation, messages: List[Dict], conversation_id: str):
        """Store messages from API data"""
        from communications.models import Message, MessageDirection, MessageStatus
        
        if not conversation:
            # Create conversation if it doesn't exist
            conversation = await sync_to_async(Conversation.objects.create)(
                channel=channel,
                external_thread_id=conversation_id,
                subject=f"WhatsApp Chat {conversation_id[:8]}",
                status='active',
                last_message_at=timezone.now()
            )
        
        for msg_data in messages:
            message_id = msg_data.get('id') or msg_data.get('message_id')
            if not message_id:
                continue
            
            # Check if message exists
            exists = await sync_to_async(Message.objects.filter(
                external_message_id=message_id,
                channel=channel
            ).exists)()
            
            if exists:
                continue
            
            # Format message
            formatted = self.message_formatter.format_incoming_message(msg_data)
            
            # Extract attendee info - pass message data directly for API messages
            attendee_info = self.attendee_detector.extract_attendee_from_message(msg_data)
            
            # Determine direction using unified utility
            direction_str = determine_message_direction(msg_data, 'whatsapp', self.account_identifier)
            # Convert 'in'/'out' to model's expected values 'inbound'/'outbound'
            direction = 'inbound' if direction_str == 'in' else 'outbound'
            
            # Create message
            await sync_to_async(Message.objects.create)(
                channel=channel,
                conversation=conversation,
                external_message_id=message_id,
                content=formatted['content'],
                direction=direction,
                status=MessageStatus.DELIVERED,
                created_at=formatted.get('timestamp') or timezone.now(),
                metadata={
                    'attendee_info': attendee_info,
                    'api_synced': True
                }
            )
    
    async def _should_sync_conversations(self, channel) -> bool:
        """Determine if conversations should be synced"""
        from communications.models import Conversation
        
        # Check when we last synced
        latest_conversation = await sync_to_async(
            Conversation.objects.filter(channel=channel).order_by('-updated_at').first
        )()
        
        if not latest_conversation:
            return True  # No conversations, should sync
        
        # Sync if last update was more than 5 minutes ago
        time_since_update = timezone.now() - latest_conversation.updated_at
        return time_since_update.total_seconds() > 300