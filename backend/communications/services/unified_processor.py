"""
Unified Message & Data Processor
Normalizes webhook and API data into consistent format for processing
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union, Tuple
from django.utils import timezone as django_timezone
from asgiref.sync import sync_to_async

from ..models import (
    Channel, Conversation, Message, ChatAttendee,
    ConversationStatus, MessageDirection, MessageStatus, UserChannelConnection
)
from .conversation_naming import conversation_naming_service
from .contact_identification import contact_identification_service
from .direction_detection import direction_detection_service

logger = logging.getLogger(__name__)


class UnifiedMessageProcessor:
    """
    Unified processor for normalizing and processing message data from different sources
    Handles both webhook (real-time) and API sync (historical) data
    """
    
    def __init__(self):
        self.naming_service = conversation_naming_service
        self.contact_service = contact_identification_service
        self.direction_service = direction_detection_service
    
    # =========================================================================
    # DATA NORMALIZATION
    # =========================================================================
    
    def normalize_message_data(self, raw_data: Dict[str, Any], source: str) -> Dict[str, Any]:
        """
        Normalize message data from webhook or API to common format
        
        Args:
            raw_data: Raw message data from webhook or API
            source: 'webhook' or 'api'
            
        Returns:
            Normalized message data with consistent field names
        """
        if source == 'webhook':
            return self._normalize_webhook_message(raw_data)
        elif source == 'api':
            return self._normalize_api_message(raw_data)
        else:
            raise ValueError(f"Unsupported source: {source}")
    
    def _normalize_webhook_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize webhook message data"""
        # Extract sender information
        sender_info = data.get('sender', {})
        if isinstance(sender_info, dict):
            sender_id = sender_info.get('attendee_id') or sender_info.get('attendee_provider_id')
        else:
            sender_id = data.get('from') or data.get('sender_id')
        
        # Extract and transform attachments
        raw_attachments = data.get('attachments', []) or []
        if isinstance(raw_attachments, dict):
            raw_attachments = [raw_attachments]
        
        attachments = []
        for i, raw_att in enumerate(raw_attachments):
            transformed_attachment = {
                'id': raw_att.get('id', f'whatsapp_att_{i}'),
                'type': raw_att.get('content_type', raw_att.get('type', 'application/octet-stream')),
                'filename': raw_att.get('filename', raw_att.get('name', f'attachment_{raw_att.get("id", i)}')),
                'url': raw_att.get('url'),
                'size': raw_att.get('size'),
                'mime_type': raw_att.get('content_type', raw_att.get('type', 'application/octet-stream')),
                'thumbnail_url': raw_att.get('thumbnail_url'),
                'unipile_data': raw_att
            }
            attachments.append(transformed_attachment)
        
        # Handle attachment-only messages
        content = data.get('message', '')
        if not content and attachments:
            content = f'[{len(attachments)} attachment(s)]'
        elif not content:
            content = ''
        
        return {
            'external_message_id': data.get('message_id'),
            'chat_id': data.get('chat_id') or data.get('provider_chat_id'),
            'content': content,
            'subject': '',  # Webhooks don't typically have subjects
            'sender_id': sender_id,
            'timestamp': None,  # Use current time for real-time webhook
            'attachments': attachments,
            'is_sender': None,  # Will be determined by direction service
            'raw_data': data,
            'source': 'webhook'
        }
    
    def _normalize_api_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize API message data"""
        # Extract content with fallback chain
        content = (
            data.get('text') or 
            data.get('body') or 
            data.get('content') or
            ''
        )
        
        # Get subject safely
        subject = data.get('subject', '') or ''
        if subject and len(subject) > 500:
            subject = subject[:500]
        
        # Parse timestamp - UniPile API uses 'timestamp' field
        timestamp = None
        try:
            timestamp_str = data.get('timestamp') or data.get('date')
            if timestamp_str:
                timestamp = self._parse_timestamp(timestamp_str)
        except Exception as e:
            logger.warning(f"Failed to parse timestamp: {e}")
        
        # Transform API attachments to match webhook format
        raw_attachments = data.get('attachments', []) or []
        if isinstance(raw_attachments, dict):
            raw_attachments = [raw_attachments]
        
        attachments = []
        for i, raw_att in enumerate(raw_attachments):
            transformed_attachment = {
                'id': raw_att.get('id', f'api_att_{i}'),
                'type': raw_att.get('type', raw_att.get('content_type', 'application/octet-stream')),
                'filename': raw_att.get('name', raw_att.get('filename', f'attachment_{raw_att.get("id", i)}')),
                'url': raw_att.get('url'),
                'size': raw_att.get('size'),
                'mime_type': raw_att.get('type', raw_att.get('content_type', 'application/octet-stream')),
                'thumbnail_url': raw_att.get('thumbnail_url'),
                'unipile_data': raw_att
            }
            attachments.append(transformed_attachment)
        
        return {
            'external_message_id': data.get('id'),
            'chat_id': None,  # Will be provided by context in API sync
            'content': content,
            'subject': subject,
            'sender_id': data.get('from'),
            'timestamp': timestamp,
            'attachments': attachments,
            'is_sender': data.get('is_sender', False),
            'raw_data': data,
            'source': 'api'
        }
    
    def normalize_attendee_data(self, raw_data: Dict[str, Any], source: str) -> Dict[str, Any]:
        """
        Normalize attendee data from webhook or API to common format
        
        Args:
            raw_data: Raw attendee data
            source: 'webhook' or 'api'
            
        Returns:
            Normalized attendee data
        """
        # Attendee data structure is typically consistent between webhook and API
        # but we normalize field names for consistency
        return {
            'external_attendee_id': raw_data.get('id'),
            'provider_id': raw_data.get('provider_id', ''),
            'name': raw_data.get('name', ''),
            'picture_url': raw_data.get('picture_url', ''),
            'is_self': raw_data.get('is_self', False),
            'metadata': raw_data,
            'source': source
        }
    
    def normalize_conversation_data(self, raw_data: Dict[str, Any], source: str) -> Dict[str, Any]:
        """
        Normalize conversation/chat data from webhook or API to common format
        
        Args:
            raw_data: Raw conversation data
            source: 'webhook' or 'api'
            
        Returns:
            Normalized conversation data
        """
        if source == 'webhook':
            # Webhook creates conversations based on message context
            return {
                'external_thread_id': raw_data.get('chat_id') or raw_data.get('provider_chat_id'),
                'name': None,  # Will be generated by naming service
                'is_group': raw_data.get('is_group', False),
                'metadata': {
                    'webhook_created': True,
                    'created_from_message': True
                },
                'source': 'webhook'
            }
        elif source == 'api':
            # API provides chat data directly
            return {
                'external_thread_id': raw_data.get('id'),
                'name': raw_data.get('name') or raw_data.get('subject'),
                'is_group': raw_data.get('type', 0) == 1 or bool(raw_data.get('is_group')),
                'is_muted': bool(raw_data.get('muted_until')),
                'is_pinned': raw_data.get('is_pinned', False),
                'is_archived': bool(raw_data.get('archived', 0)),
                'unread_count': raw_data.get('unread_count', 0),
                'picture_url': raw_data.get('picture_url'),
                'last_message_date': raw_data.get('timestamp'),
                'metadata': {
                    'api_synced': True,
                    'sync_timestamp': django_timezone.now().isoformat()
                },
                'source': 'api'
            }
        else:
            raise ValueError(f"Unsupported source: {source}")
    
    # =========================================================================
    # UNIFIED PROCESSING METHODS
    # =========================================================================
    
    async def process_message(
        self,
        normalized_data: Dict[str, Any],
        channel: Channel,
        conversation: Conversation,
        connection: Optional[UserChannelConnection] = None
    ) -> Tuple[Message, bool]:
        """
        Create or update a message from normalized data
        
        Args:
            normalized_data: Normalized message data
            channel: Channel for the message
            conversation: Conversation for the message
            connection: User connection (for webhooks)
            
        Returns:
            Tuple of (message, created)
        """
        external_message_id = normalized_data.get('external_message_id')
        if not external_message_id:
            raise ValueError("Message ID is required")
        
        # Check if message already exists
        existing_message = await sync_to_async(Message.objects.filter(
            external_message_id=external_message_id,
            channel=channel
        ).first)()
        
        if existing_message:
            # Update existing message if needed
            if existing_message.status != MessageStatus.DELIVERED:
                existing_message.status = MessageStatus.DELIVERED
                existing_message.received_at = django_timezone.now()
                await sync_to_async(existing_message.save)(update_fields=['status', 'received_at'])
            return existing_message, False
        
        # Determine message direction
        direction = await self._determine_message_direction(normalized_data, connection)
        
        # Get timestamp
        received_at = normalized_data.get('timestamp') or django_timezone.now()
        
        # Extract contact information
        contact_phone = ''
        if connection and normalized_data.get('source') == 'webhook':
            contact_info = self.contact_service.identify_whatsapp_contact(
                connection, normalized_data.get('raw_data', {})
            )
            contact_phone = contact_info.get('contact_phone', '')
        
        # Create new message
        message = await sync_to_async(Message.objects.create)(
            external_message_id=external_message_id,
            channel=channel,
            conversation=conversation,
            content=normalized_data.get('content', ''),
            subject=normalized_data.get('subject', ''),
            direction=direction,
            contact_phone=contact_phone,
            status=MessageStatus.DELIVERED,
            received_at=received_at,
            sync_status='synced',
            metadata={
                'source': normalized_data.get('source'),
                'sender_id': normalized_data.get('sender_id'),
                'attachments': normalized_data.get('attachments', []),
                'attachment_count': len(normalized_data.get('attachments', [])),
                'raw_data': normalized_data.get('raw_data', {}),
                'processed_at': django_timezone.now().isoformat()
            }
        )
        
        logger.info(f"✅ Created message {message.id} from {normalized_data.get('source')} data")
        return message, True
    
    async def process_attendees(
        self,
        normalized_attendees: List[Dict[str, Any]],
        channel: Channel
    ) -> List[ChatAttendee]:
        """
        Create or update attendees from normalized data
        
        Args:
            normalized_attendees: List of normalized attendee data
            channel: Channel for the attendees
            
        Returns:
            List of created/updated ChatAttendee objects
        """
        attendees = []
        
        for attendee_data in normalized_attendees:
            attendee_id = attendee_data.get('external_attendee_id')
            if not attendee_id:
                continue
            
            attendee, created = await sync_to_async(ChatAttendee.objects.get_or_create)(
                external_attendee_id=attendee_id,
                channel=channel,
                defaults={
                    'provider_id': attendee_data.get('provider_id', ''),
                    'name': attendee_data.get('name', ''),
                    'picture_url': attendee_data.get('picture_url', ''),
                    'is_self': attendee_data.get('is_self', False),
                    'metadata': attendee_data.get('metadata', {})
                }
            )
            
            if not created:
                # Update existing attendee if needed
                attendee.name = attendee_data.get('name', attendee.name)
                attendee.picture_url = attendee_data.get('picture_url', attendee.picture_url)
                attendee.metadata = attendee_data.get('metadata', attendee.metadata)
                await sync_to_async(attendee.save)()
            
            attendees.append(attendee)
            
            action = "Created" if created else "Updated"
            logger.debug(f"{action} attendee: {attendee.name} ({attendee_id})")
        
        return attendees
    
    async def process_conversation(
        self,
        normalized_data: Dict[str, Any],
        channel: Channel,
        attendees: Optional[List[ChatAttendee]] = None,
        contact_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[Conversation, bool]:
        """
        Create or update a conversation from normalized data
        
        Args:
            normalized_data: Normalized conversation data
            channel: Channel for the conversation
            attendees: List of attendees for the conversation
            contact_info: Contact information for naming
            
        Returns:
            Tuple of (conversation, created)
        """
        external_thread_id = normalized_data.get('external_thread_id')
        if not external_thread_id:
            raise ValueError("Conversation thread ID is required")
        
        # Check if conversation exists
        existing_conversation = await sync_to_async(Conversation.objects.filter(
            channel=channel,
            external_thread_id=external_thread_id
        ).first)()
        
        if existing_conversation:
            return existing_conversation, False
        
        # Generate conversation name
        conversation_name = self._generate_conversation_name(
            normalized_data, channel, attendees, contact_info
        )
        
        # Create new conversation
        conversation = await sync_to_async(Conversation.objects.create)(
            channel=channel,
            external_thread_id=external_thread_id,
            subject=conversation_name,
            status=ConversationStatus.ARCHIVED if normalized_data.get('is_archived') else ConversationStatus.ACTIVE,
            sync_status='pending',
            metadata=normalized_data.get('metadata', {})
        )
        
        logger.info(f"✅ Created conversation '{conversation_name}' from {normalized_data.get('source')} data")
        return conversation, True
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    async def _determine_message_direction(
        self,
        normalized_data: Dict[str, Any],
        connection: Optional[UserChannelConnection] = None
    ) -> MessageDirection:
        """Determine message direction using available data"""
        source = normalized_data.get('source')
        
        if connection:
            # Always use the sophisticated direction detection service when we have a connection
            raw_data = normalized_data.get('raw_data', {})
            
            # For API sync, try to determine event type from is_sender field
            event_type = None
            if source == 'api':
                is_sender = normalized_data.get('is_sender')
                if is_sender is not None:
                    event_type = 'message_sent' if is_sender else 'message_received'
            elif source == 'webhook':
                # For webhook, we can use the actual event type if available in raw data
                event_type = raw_data.get('event_type', 'message_received')
            
            # Use the comprehensive direction detection service
            direction, detection_metadata = self.direction_service.determine_direction(
                connection=connection,
                message_data=raw_data,
                event_type=event_type
            )
            
            # Log detection details for debugging
            logger.info(f"🔍 Direction Detection: {direction.value}")
            logger.info(f"   Method: {detection_metadata.get('detection_method')}")
            logger.info(f"   Confidence: {detection_metadata.get('confidence')}")
            if detection_metadata.get('account_phone'):
                logger.info(f"   Account Phone: {detection_metadata.get('account_phone')}")
            if detection_metadata.get('sender_info'):
                logger.info(f"   Sender Info: {detection_metadata.get('sender_info')}")
            
            return direction
        else:
            # Fallback when no connection available
            if source == 'api' and 'is_sender' in normalized_data:
                # API provides is_sender field as backup
                return MessageDirection.OUTBOUND if normalized_data.get('is_sender') else MessageDirection.INBOUND
            else:
                # Final fallback: assume inbound for received messages
                logger.warning(f"No connection available for direction detection, assuming INBOUND")
                return MessageDirection.INBOUND
    
    def _generate_conversation_name(
        self,
        normalized_data: Dict[str, Any],
        channel: Channel,
        attendees: Optional[List[ChatAttendee]] = None,
        contact_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate conversation name using naming service"""
        
        # Use provided name if available
        if normalized_data.get('name'):
            return normalized_data['name']
        
        # Prepare contact info for naming service
        naming_contact_info = {}
        if contact_info:
            naming_contact_info = contact_info.copy()
        elif attendees:
            # Find primary attendee (not self)
            primary_attendee = None
            for attendee in attendees:
                if not attendee.is_self:
                    primary_attendee = attendee
                    break
            
            if primary_attendee:
                naming_contact_info = {
                    'name': primary_attendee.name,
                    'phone': primary_attendee.metadata.get('phone', ''),
                    'profile': primary_attendee.metadata
                }
        
        # Generate name using naming service
        return self.naming_service.generate_conversation_name(
            channel_type=channel.channel_type,
            contact_info=naming_contact_info,
            message_content='',  # No message content for conversation naming
            external_thread_id=normalized_data.get('external_thread_id')
        )
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string to datetime object"""
        if not timestamp_str:
            return None
        
        try:
            # Handle various timestamp formats
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str.replace('Z', '+00:00')
            
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
            return None


# Global instance
unified_processor = UnifiedMessageProcessor()