"""
Message synchronization service for UniPile integration
Handles fetching and syncing messages from connected UniPile accounts
"""
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from asgiref.sync import sync_to_async, async_to_sync

from django.db import transaction
from django.utils import timezone as django_timezone
from django.contrib.auth import get_user_model

from .models import (
    UserChannelConnection, Channel, Conversation, Message, 
    MessageDirection, MessageStatus, ConversationStatus
)
from .unipile_sdk import unipile_service, UnipileConnectionError, UnipileAuthenticationError
from pipelines.models import Pipeline, Record

User = get_user_model()
logger = logging.getLogger(__name__)


class MessageSyncService:
    """
    Service for synchronizing messages between UniPile and local database
    Handles both initial sync and real-time updates
    """
    
    def __init__(self):
        self.unipile_service = unipile_service
    
    async def sync_account_messages(
        self,
        user_channel_connection: UserChannelConnection,
        initial_sync: bool = False,
        days_back: int = 30,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Sync messages for a specific user channel connection
        
        Args:
            user_channel_connection: The connection to sync
            initial_sync: Whether this is initial setup sync
            days_back: How many days to sync back (for initial sync)
            limit: Max messages per request
        """
        try:
            # Validate connection is ready
            if not user_channel_connection.can_send_messages():
                return {
                    'success': False,
                    'error': 'Account not ready for message sync',
                    'account_id': user_channel_connection.unipile_account_id
                }
            
            # Calculate sync start time
            if initial_sync:
                since = django_timezone.now() - timedelta(days=days_back)
            else:
                since = user_channel_connection.last_sync_at or django_timezone.now() - timedelta(hours=1)
            
            # Get UniPile client
            client = self.unipile_service.get_client()
            
            # Fetch chats/conversations first
            chats_result = await self._sync_conversations(
                client, user_channel_connection, since, limit
            )
            
            # Fetch messages
            messages_result = await self._sync_messages(
                client, user_channel_connection, since, limit
            )
            
            # Update sync timestamp
            await sync_to_async(user_channel_connection.record_sync_success)()
            
            return {
                'success': True,
                'account_id': user_channel_connection.unipile_account_id,
                'conversations_synced': chats_result['count'],
                'messages_synced': messages_result['count'],
                'sync_time': django_timezone.now().isoformat(),
                'initial_sync': initial_sync
            }
            
        except Exception as e:
            logger.error(f"Failed to sync messages for account {user_channel_connection.unipile_account_id}: {e}")
            await sync_to_async(user_channel_connection.record_sync_failure)(str(e))
            
            return {
                'success': False,
                'error': str(e),
                'account_id': user_channel_connection.unipile_account_id,
                'conversations_synced': 0,
                'messages_synced': 0
            }
    
    async def _sync_conversations(
        self,
        client,
        user_channel_connection: UserChannelConnection,
        since: datetime,
        limit: int
    ) -> Dict[str, Any]:
        """Sync conversations/chats from UniPile"""
        
        try:
            # Get chats from UniPile
            chats_response = await client.messaging.get_all_chats(
                account_id=user_channel_connection.unipile_account_id,
                limit=limit
            )
            
            chats = chats_response.get('chats', [])
            if isinstance(chats_response, list):
                chats = chats_response
            
            # Get or create channel for this connection
            channel = await self._get_or_create_channel(user_channel_connection)
            
            synced_count = 0
            
            for chat_data in chats:
                try:
                    # Create or update conversation
                    conversation = await self._create_or_update_conversation(
                        channel, chat_data, user_channel_connection
                    )
                    
                    if conversation:
                        synced_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to sync conversation {chat_data.get('id')}: {e}")
                    continue
            
            return {'success': True, 'count': synced_count}
            
        except Exception as e:
            logger.error(f"Failed to sync conversations: {e}")
            return {'success': False, 'count': 0, 'error': str(e)}
    
    async def _sync_messages(
        self,
        client,
        user_channel_connection: UserChannelConnection,
        since: datetime,
        limit: int
    ) -> Dict[str, Any]:
        """Sync messages from UniPile"""
        
        try:
            # Get messages from UniPile
            messages_response = await client.messaging.get_all_messages(
                account_id=user_channel_connection.unipile_account_id,
                since=since.isoformat(),
                limit=limit
            )
            
            messages = messages_response.get('messages', [])
            if isinstance(messages_response, list):
                messages = messages_response
            
            # Get channel for this connection
            channel = await self._get_or_create_channel(user_channel_connection)
            
            synced_count = 0
            
            for message_data in messages:
                try:
                    # Create or update message
                    message = await self._create_or_update_message(
                        channel, message_data, user_channel_connection
                    )
                    
                    if message:
                        synced_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to sync message {message_data.get('id')}: {e}")
                    continue
            
            return {'success': True, 'count': synced_count}
            
        except Exception as e:
            logger.error(f"Failed to sync messages: {e}")
            return {'success': False, 'count': 0, 'error': str(e)}
    
    @sync_to_async
    def _get_or_create_channel(self, user_channel_connection: UserChannelConnection) -> Channel:
        """Get or create channel for user connection"""
        
        # Use get_or_create to handle race conditions
        channel, created = Channel.objects.get_or_create(
            unipile_account_id=user_channel_connection.unipile_account_id,
            defaults={
                'name': f"{user_channel_connection.account_name} ({user_channel_connection.get_channel_type_display()})",
                'description': f"Channel for {user_channel_connection.user.username}'s {user_channel_connection.get_channel_type_display()} account",
                'channel_type': user_channel_connection.channel_type,
                'auth_status': user_channel_connection.auth_status,
                'created_by': user_channel_connection.user,
                'connection_config': {
                    'user_channel_connection_id': str(user_channel_connection.id),
                    'account_name': user_channel_connection.account_name,
                    'provider': user_channel_connection.channel_type
                }
            }
        )
        
        # Update channel status if needed
        if not created and channel.auth_status != user_channel_connection.auth_status:
            channel.auth_status = user_channel_connection.auth_status
            channel.save(update_fields=['auth_status'])
        
        return channel
    
    @sync_to_async
    def _create_or_update_conversation(
        self,
        channel: Channel,
        chat_data: Dict[str, Any],
        user_channel_connection: UserChannelConnection
    ) -> Optional[Conversation]:
        """Create or update conversation from UniPile chat data"""
        
        try:
            external_thread_id = chat_data.get('id') or chat_data.get('chat_id')
            
            if not external_thread_id:
                logger.warning("Chat data missing ID, skipping")
                return None
            
            # Extract conversation details
            subject = chat_data.get('subject') or chat_data.get('name') or ''
            
            # Try to identify primary contact
            primary_contact_record = None
            attendees = chat_data.get('attendees', [])
            
            # Look for contact records based on chat attendees
            if attendees:
                # Try to match attendees to existing contact records
                primary_contact_record = self._find_contact_from_attendees(attendees)
            
            # Create or update conversation
            conversation, created = Conversation.objects.get_or_create(
                channel=channel,
                external_thread_id=external_thread_id,
                defaults={
                    'subject': subject[:500],  # Truncate to field length
                    'primary_contact_record': primary_contact_record,
                    'status': ConversationStatus.ACTIVE,
                    'metadata': {
                        'unipile_data': chat_data,
                        'attendees': attendees,
                        'sync_source': 'unipile_sync',
                        'user_channel_connection_id': str(user_channel_connection.id)
                    }
                }
            )
            
            # Update metadata if not created
            if not created:
                conversation.metadata.update({
                    'unipile_data': chat_data,
                    'attendees': attendees,
                    'last_sync': django_timezone.now().isoformat()
                })
                conversation.save(update_fields=['metadata'])
            
            return conversation
            
        except Exception as e:
            logger.error(f"Failed to create/update conversation: {e}")
            return None
    
    @sync_to_async
    def _find_contact_from_attendees(self, attendees: List[Dict]) -> Optional['Record']:
        """Find existing contact record from chat attendees"""
        try:
            # Get tenant's contact pipeline
            from .models import TenantUniPileConfig
            config = TenantUniPileConfig.get_or_create_for_tenant()
            
            if not config.default_contact_pipeline:
                return None
            
            # Try to match attendees by email or phone
            for attendee in attendees:
                email = attendee.get('email')
                phone = attendee.get('phone')
                username = attendee.get('username')
                
                if email:
                    # Look for contact with matching email
                    contacts = Record.objects.filter(
                        pipeline=config.default_contact_pipeline,
                        data__email=email
                    ).first()
                    if contacts:
                        return contacts
                
                if phone:
                    # Look for contact with matching phone
                    contacts = Record.objects.filter(
                        pipeline=config.default_contact_pipeline,
                        data__phone=phone
                    ).first()
                    if contacts:
                        return contacts
                
                if username:
                    # Look for contact with matching username/handle
                    contacts = Record.objects.filter(
                        pipeline=config.default_contact_pipeline,
                        data__username=username
                    ).first()
                    if contacts:
                        return contacts
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find contact from attendees: {e}")
            return None
    
    @sync_to_async
    def _create_or_update_message(
        self,
        channel: Channel,
        message_data: Dict[str, Any],
        user_channel_connection: UserChannelConnection
    ) -> Optional[Message]:
        """Create or update message from UniPile message data"""
        
        try:
            external_message_id = message_data.get('id') or message_data.get('message_id')
            
            if not external_message_id:
                logger.warning("Message data missing ID, skipping")
                return None
            
            # Check if message already exists
            existing_message = Message.objects.filter(
                external_message_id=external_message_id,
                channel=channel
            ).first()
            
            if existing_message:
                # Merge webhook data with existing API-sent message data
                # Preserve API-sent metadata while adding webhook data
                current_metadata = existing_message.metadata or {}
                
                # Check if this is an API-sent message
                is_api_sent = current_metadata.get('sent_via_api', False)
                
                if is_api_sent:
                    # Preserve API metadata and merge webhook data
                    merged_metadata = current_metadata.copy()
                    merged_metadata.update({
                        'raw_webhook_data': message_data,
                        'webhook_processed_at': django_timezone.now().isoformat(),
                        'last_sync': django_timezone.now().isoformat(),
                        # Add extracted contact info from webhook if not present
                        'extracted_phone': self._extract_phone_from_webhook(message_data),
                    })
                    
                    # Update contact info if webhook has better data
                    webhook_contact_name = self._extract_contact_name_from_webhook(message_data, user_channel_connection)
                    if webhook_contact_name and not merged_metadata.get('contact_name'):
                        merged_metadata['contact_name'] = webhook_contact_name
                    
                    existing_message.metadata = merged_metadata
                    
                    # Update status and timestamps from webhook (webhook wins for delivery status)
                    webhook_status = self._extract_status_from_webhook(message_data)
                    if webhook_status:
                        existing_message.status = webhook_status
                    
                    # Update contact_phone field if webhook has better data
                    webhook_phone = self._extract_phone_from_webhook(message_data)
                    if webhook_phone and not existing_message.contact_phone:
                        existing_message.contact_phone = webhook_phone
                    
                    existing_message.save(update_fields=['metadata', 'status', 'contact_phone'])
                    
                    logger.info(f"Merged webhook data with API-sent message {existing_message.id}")
                    return existing_message
                
                else:
                    # Regular webhook-only message update
                    raw_content = message_data.get('text') or message_data.get('content') or ''
                    attachments = message_data.get('attachments', [])
                    
                    # Handle attachment-only messages in updates too
                    if not existing_message.content and not raw_content and attachments:
                        existing_message.content = f'[{len(attachments)} attachment(s)]'
                        update_fields = ['metadata', 'content']
                    else:
                        update_fields = ['metadata']
                    
                    existing_message.metadata.update({
                        'unipile_data': message_data,
                        'last_sync': django_timezone.now().isoformat(),
                        'attachments': attachments,
                        'attachment_count': len(attachments) if attachments else 0
                    })
                    existing_message.save(update_fields=update_fields)
                    return existing_message
            
            # Extract message details
            raw_content = message_data.get('text') or message_data.get('content') or ''
            raw_attachments = message_data.get('attachments', [])
            
            # Transform UniPile attachment format to our standard format
            attachments = []
            for i, raw_att in enumerate(raw_attachments):
                logger.info(f"🔍 Processing webhook attachment {i}: {raw_att}")
                
                # Transform UniPile attachment fields to our standard format
                transformed_attachment = {
                    'id': raw_att.get('id', f'webhook_att_{i}'),
                    'type': raw_att.get('content_type', raw_att.get('type', 'application/octet-stream')),
                    'filename': raw_att.get('filename', raw_att.get('name', f'attachment_{raw_att.get("id", i)}')),
                    'url': raw_att.get('url'),  # UniPile provides download URL
                    'size': raw_att.get('size'),
                    'mime_type': raw_att.get('content_type', raw_att.get('type', 'application/octet-stream')),
                    'thumbnail_url': raw_att.get('thumbnail_url'),
                    # Keep original UniPile data for reference
                    'unipile_data': raw_att
                }
                attachments.append(transformed_attachment)
                logger.info(f"✅ Transformed attachment: {transformed_attachment}")
            
            # Handle attachment-only messages (ensure content is never empty string for database)
            if not raw_content and attachments:
                content = f'[{len(attachments)} attachment(s)]'
            else:
                content = raw_content or ''
            
            # Determine direction
            author = message_data.get('author', {})
            is_from_account = author.get('account_id') == user_channel_connection.unipile_account_id
            direction = MessageDirection.OUTBOUND if is_from_account else MessageDirection.INBOUND
            
            # Find conversation
            conversation = None
            chat_id = message_data.get('chat_id')
            if chat_id:
                conversation = Conversation.objects.filter(
                    channel=channel,
                    external_thread_id=chat_id
                ).first()
            
            # Extract contact information
            contact_email = ''
            contact_record = None
            
            if direction == MessageDirection.INBOUND:
                contact_email = author.get('email', '')
                # Try to find or create contact
                contact_record = self._find_or_create_contact_from_author(author)
            
            # Determine message status
            status = MessageStatus.SENT
            if message_data.get('delivered'):
                status = MessageStatus.DELIVERED
            if message_data.get('read'):
                status = MessageStatus.READ
            
            # Parse timestamps
            sent_at = None
            received_at = None
            
            timestamp_str = message_data.get('timestamp') or message_data.get('created_at')
            if timestamp_str:
                try:
                    # Parse ISO timestamp
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    if direction == MessageDirection.OUTBOUND:
                        sent_at = timestamp
                    else:
                        received_at = timestamp
                except ValueError:
                    pass
            
            # Create message
            message = Message.objects.create(
                external_message_id=external_message_id,
                channel=channel,
                conversation=conversation,
                contact_record=contact_record,
                direction=direction,
                content=content[:10000],  # Truncate to reasonable length
                contact_email=contact_email,
                status=status,
                sent_at=sent_at,
                received_at=received_at,
                metadata={
                    'unipile_data': message_data,
                    'sync_source': 'unipile_sync',
                    'user_channel_connection_id': str(user_channel_connection.id),
                    'author': author,
                    'attachments': attachments,
                    'attachment_count': len(attachments) if attachments else 0
                }
            )
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to create/update message: {e}")
            return None
    
    @sync_to_async
    def _find_or_create_contact_from_author(self, author: Dict[str, Any]) -> Optional['Record']:
        """Find or create contact record from message author"""
        try:
            from .models import TenantUniPileConfig
            config = TenantUniPileConfig.get_or_create_for_tenant()
            
            if not config.auto_create_contacts or not config.default_contact_pipeline:
                return None
            
            email = author.get('email')
            phone = author.get('phone')
            username = author.get('username')
            name = author.get('name') or author.get('display_name')
            
            # Try to find existing contact
            existing_contact = None
            
            if email:
                existing_contact = Record.objects.filter(
                    pipeline=config.default_contact_pipeline,
                    data__email=email
                ).first()
            
            if not existing_contact and phone:
                existing_contact = Record.objects.filter(
                    pipeline=config.default_contact_pipeline,
                    data__phone=phone
                ).first()
            
            if existing_contact:
                return existing_contact
            
            # Create new contact if auto-create is enabled
            contact_data = {
                'status': config.default_contact_status
            }
            
            if name:
                contact_data['name'] = name
            if email:
                contact_data['email'] = email
            if phone:
                contact_data['phone'] = phone
            if username:
                contact_data['username'] = username
            
            # Add UniPile-specific data
            contact_data['unipile_author_data'] = author
            contact_data['source'] = 'unipile_sync'
            
            new_contact = Record.objects.create(
                pipeline=config.default_contact_pipeline,
                data=contact_data
            )
            
            return new_contact
            
        except Exception as e:
            logger.error(f"Failed to find/create contact from author: {e}")
            return None
    
    async def sync_all_active_connections(
        self,
        initial_sync: bool = False,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Sync messages for all active user channel connections"""
        
        # Get all active connections that are ready for sync
        active_connections = await sync_to_async(list)(
            UserChannelConnection.objects.filter(
                is_active=True,
                account_status='active',
                unipile_account_id__isnull=False
            ).select_related('user')
        )
        
        total_connections = len(active_connections)
        successful_syncs = 0
        failed_syncs = 0
        results = []
        
        for connection in active_connections:
            try:
                result = await self.sync_account_messages(
                    connection,
                    initial_sync=initial_sync,
                    days_back=days_back
                )
                
                if result['success']:
                    successful_syncs += 1
                else:
                    failed_syncs += 1
                
                results.append({
                    'connection_id': str(connection.id),
                    'account_name': connection.account_name,
                    'channel_type': connection.channel_type,
                    'result': result
                })
                
            except Exception as e:
                logger.error(f"Failed to sync connection {connection.id}: {e}")
                failed_syncs += 1
                results.append({
                    'connection_id': str(connection.id),
                    'account_name': connection.account_name,
                    'channel_type': connection.channel_type,
                    'result': {'success': False, 'error': str(e)}
                })
        
        return {
            'success': True,
            'total_connections': total_connections,
            'successful_syncs': successful_syncs,
            'failed_syncs': failed_syncs,
            'sync_time': django_timezone.now().isoformat(),
            'results': results
        }
    
    def sync_account_messages_sync(self, connection_id: str, **kwargs) -> Dict[str, Any]:
        """Synchronous wrapper for sync_account_messages"""
        try:
            connection = UserChannelConnection.objects.get(id=connection_id)
            return async_to_sync(self.sync_account_messages)(connection, **kwargs)
        except UserChannelConnection.DoesNotExist:
            return {
                'success': False,
                'error': f'Connection {connection_id} not found'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_phone_from_webhook(self, message_data: Dict[str, Any]) -> Optional[str]:
        """Extract phone number from webhook data using provider logic"""
        try:
            provider_chat_id = message_data.get('provider_chat_id', '')
            if '@s.whatsapp.net' in provider_chat_id:
                phone_number = provider_chat_id.replace('@s.whatsapp.net', '')
                clean_phone = ''.join(c for c in phone_number if c.isdigit())
                if len(clean_phone) >= 7:
                    return f"+{clean_phone}"
            return None
        except Exception as e:
            logger.error(f"Error extracting phone from webhook: {e}")
            return None
    
    def _extract_contact_name_from_webhook(self, message_data: Dict[str, Any], connection: UserChannelConnection) -> Optional[str]:
        """Extract contact name from webhook data using provider logic"""
        try:
            provider_chat_id = message_data.get('provider_chat_id')
            if not provider_chat_id:
                return None
            
            # Find attendee matching provider_chat_id (the contact we're speaking to)
            attendees = message_data.get('attendees', [])
            for attendee in attendees:
                if attendee.get('attendee_provider_id') == provider_chat_id:
                    attendee_name = attendee.get('attendee_name', '')
                    # Validate it's not a phone/ID
                    if attendee_name and not ('@s.whatsapp.net' in attendee_name or attendee_name.isdigit()):
                        return attendee_name
            
            # Also check sender if it matches provider_chat_id (inbound case)
            sender = message_data.get('sender', {})
            if sender.get('attendee_provider_id') == provider_chat_id:
                sender_name = sender.get('attendee_name', '')
                if sender_name and not ('@s.whatsapp.net' in sender_name or sender_name.isdigit()):
                    return sender_name
            
            return None
        except Exception as e:
            logger.error(f"Error extracting contact name from webhook: {e}")
            return None
    
    def _extract_status_from_webhook(self, message_data: Dict[str, Any]) -> Optional[str]:
        """Extract message status from webhook data"""
        try:
            # Check webhook event type or status indicators
            event = message_data.get('event', '')
            
            if event == 'message_delivered' or message_data.get('delivered'):
                return MessageStatus.DELIVERED
            elif event == 'message_read' or message_data.get('read'):
                return MessageStatus.READ
            elif event == 'message_sent':
                return MessageStatus.SENT
            
            # Default to sent for outbound messages
            return MessageStatus.SENT
        except Exception as e:
            logger.error(f"Error extracting status from webhook: {e}")
            return None


# Global service instance
message_sync_service = MessageSyncService()