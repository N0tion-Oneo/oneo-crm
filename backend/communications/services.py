"""
Communication services for Phase 8 - Django integration layer
Bridges Django models with UniPile SDK functionality
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.utils import timezone
from asgiref.sync import sync_to_async

from .models import (
    UserChannelConnection, Conversation, Message, 
    ChannelType, AuthStatus, MessageDirection, MessageStatus
)
from .unipile_sdk import unipile_service, UnipileConnectionError

logger = logging.getLogger(__name__)
User = get_user_model()


class CommunicationService:
    """
    High-level communication service that integrates Django models
    with UniPile SDK functionality
    """
    
    def __init__(self):
        self.unipile = unipile_service
    
    async def connect_user_channel(
        self,
        user: User,
        channel_type: str,
        account_identifier: str,
        credentials: Dict[str, Any],
        channel_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Connect a new user channel via UniPile"""
        
        try:
            # Create or get user channel connection
            user_channel, created = await sync_to_async(
                UserChannelConnection.objects.get_or_create
            )(
                user=user,
                channel_type=channel_type,
                account_identifier=account_identifier,
                defaults={
                    'name': channel_name or f"{channel_type.title()} Account",
                    'auth_status': AuthStatus.DISCONNECTED
                }
            )
            
            # Map channel type to provider
            provider_mapping = {
                ChannelType.EMAIL: 'gmail' if 'gmail' in account_identifier else 'outlook',
                ChannelType.LINKEDIN: 'linkedin',
                ChannelType.WHATSAPP: 'whatsapp',
                ChannelType.SMS: 'sms'
            }
            
            provider = provider_mapping.get(channel_type, channel_type)
            
            # Connect via UniPile SDK
            result = await self.unipile.connect_user_account(
                user_channel_connection=user_channel,
                provider=provider,
                credentials=credentials
            )
            
            if result['success']:
                return {
                    'success': True,
                    'channel_id': str(user_channel.id),
                    'account_id': result.get('account_id'),
                    'provider': provider,
                    'qr_code': result.get('qr_code'),  # For WhatsApp
                    'created': created
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error'),
                    'channel_id': str(user_channel.id) if user_channel else None
                }
                
        except Exception as e:
            logger.error(f"Failed to connect user channel: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def send_message(
        self,
        user: User,
        channel_type: str,
        recipient: str,
        content: str,
        subject: Optional[str] = None,
        conversation_id: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Send message via user's channel"""
        
        try:
            # Get user's default channel for this type
            user_channel = await sync_to_async(
                UserChannelConnection.objects.filter(
                    user=user,
                    channel_type=channel_type,
                    is_active=True,
                    auth_status=AuthStatus.CONNECTED
                ).first
            )()
            
            if not user_channel:
                return {
                    'success': False,
                    'error': f'No connected {channel_type} channel found for user'
                }
            
            # Format content for email
            message_content = content
            if channel_type == ChannelType.EMAIL and subject:
                message_content = f"Subject: {subject}\n\n{content}"
            
            # Send via UniPile SDK
            result = await self.unipile.send_message(
                user_channel_connection=user_channel,
                recipient=recipient,
                content=message_content,
                message_type=channel_type,
                attachments=attachments
            )
            
            if result['success']:
                # Get or create conversation
                conversation = await self._get_or_create_conversation(
                    user_channel=user_channel,
                    recipient=recipient,
                    subject=subject,
                    conversation_id=conversation_id
                )
                
                # Create message record
                message = await self._create_message_record(
                    conversation=conversation,
                    content=content,
                    direction=MessageDirection.OUTBOUND,
                    external_id=result.get('message_id'),
                    recipient_info={'identifier': recipient},
                    status=MessageStatus.SENT,
                    created_by=user,
                    attachments=attachments or []
                )
                
                return {
                    'success': True,
                    'message_id': str(message.id),
                    'external_message_id': result.get('message_id'),
                    'conversation_id': str(conversation.id),
                    'recipient': recipient,
                    'channel': user_channel.name
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error')
                }
                
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def sync_user_messages(
        self,
        user: User,
        channel_types: Optional[List[str]] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Sync messages for user's channels"""
        
        try:
            # Get user's active channels
            query = UserChannelConnection.objects.filter(
                user=user,
                is_active=True,
                auth_status=AuthStatus.CONNECTED
            )
            
            if channel_types:
                query = query.filter(channel_type__in=channel_types)
            
            channels = await sync_to_async(list)(query)
            
            total_synced = 0
            channel_results = []
            
            for channel in channels:
                try:
                    result = await self.unipile.sync_messages(
                        user_channel_connection=channel,
                        since=since or channel.last_sync_at,
                        limit=100
                    )
                    
                    if result['success']:
                        total_synced += result.get('processed_count', 0)
                        
                        # Process messages would go here
                        # This would integrate with existing message processing logic
                    
                    channel_results.append({
                        'channel_id': str(channel.id),
                        'channel_type': channel.channel_type,
                        'channel_name': channel.name,
                        'success': result['success'],
                        'messages_synced': result.get('processed_count', 0),
                        'error': result.get('error')
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to sync channel {channel.id}: {e}")
                    channel_results.append({
                        'channel_id': str(channel.id),
                        'channel_type': channel.channel_type,
                        'channel_name': channel.name,
                        'success': False,
                        'messages_synced': 0,
                        'error': str(e)
                    })
            
            return {
                'success': True,
                'total_messages_synced': total_synced,
                'channels_processed': len(channels),
                'channel_results': channel_results
            }
            
        except Exception as e:
            logger.error(f"Failed to sync user messages: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_messages_synced': 0
            }
    
    async def disconnect_user_channel(
        self,
        user: User,
        channel_id: str
    ) -> Dict[str, Any]:
        """Disconnect user's channel"""
        
        try:
            user_channel = await sync_to_async(
                UserChannelConnection.objects.filter(
                    id=channel_id,
                    user=user
                ).first
            )()
            
            if not user_channel:
                return {
                    'success': False,
                    'error': 'Channel not found or not owned by user'
                }
            
            # Disconnect via UniPile SDK
            result = await self.unipile.disconnect_account(user_channel)
            
            return {
                'success': True,
                'channel_id': channel_id,
                'message': 'Channel disconnected successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to disconnect channel: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_user_channels(
        self,
        user: User,
        channel_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user's channel connections"""
        
        try:
            query = UserChannelConnection.objects.filter(user=user)
            
            if channel_type:
                query = query.filter(channel_type=channel_type)
            
            channels = await sync_to_async(list)(
                query.order_by('-created_at')
            )
            
            return [
                {
                    'id': str(channel.id),
                    'name': channel.name,
                    'channel_type': channel.channel_type,
                    'account_identifier': channel.account_identifier,
                    'auth_status': channel.auth_status,
                    'is_active': channel.is_active,
                    'is_default': channel.is_default,
                    'last_sync_at': channel.last_sync_at.isoformat() if channel.last_sync_at else None,
                    'messages_sent_today': channel.messages_sent_today,
                    'rate_limit_per_hour': channel.rate_limit_per_hour,
                    'created_at': channel.created_at.isoformat(),
                    'can_send_messages': channel.can_send_messages()
                }
                for channel in channels
            ]
            
        except Exception as e:
            logger.error(f"Failed to get user channels: {e}")
            return []
    
    async def _get_or_create_conversation(
        self,
        user_channel: UserChannelConnection,
        recipient: str,
        subject: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> Conversation:
        """Get or create conversation for message"""
        
        if conversation_id:
            # Try to find existing conversation by ID
            conversation = await sync_to_async(
                Conversation.objects.filter(id=conversation_id).first
            )()
            if conversation:
                return conversation
        
        # Try to find existing conversation with recipient
        conversation = await sync_to_async(
            Conversation.objects.filter(
                user_channel=user_channel,
                participants__contains=[{'identifier': recipient}]
            ).first
        )()
        
        if conversation:
            return conversation
        
        # Create new conversation
        conversation = await sync_to_async(Conversation.objects.create)(
            user_channel=user_channel,
            participants=[{'identifier': recipient}],
            subject=subject or f"Conversation with {recipient}",
            status='active'
        )
        
        # Try to link to existing contact record
        await self._link_conversation_to_contact(conversation, recipient)
        
        return conversation
    
    async def _create_message_record(
        self,
        conversation: Conversation,
        content: str,
        direction: str,
        external_id: Optional[str] = None,
        recipient_info: Optional[Dict] = None,
        sender_info: Optional[Dict] = None,
        status: str = MessageStatus.PENDING,
        created_by: Optional[User] = None,
        attachments: Optional[List] = None
    ) -> Message:
        """Create message record"""
        
        message = await sync_to_async(Message.objects.create)(
            conversation=conversation,
            external_message_id=external_id,
            content=content,
            direction=direction,
            recipient_info=recipient_info or {},
            sender_email=sender_info.get('email') if sender_info else None,
            sender_name=sender_info.get('name') if sender_info else None,
            status=status,
            attachments=attachments or [],
            created_by=created_by,
            sent_at=timezone.now() if direction == MessageDirection.OUTBOUND else None
        )
        
        # Update conversation
        conversation.last_message_at = message.created_at
        conversation.message_count += 1
        
        if direction == MessageDirection.INBOUND:
            conversation.last_inbound_at = message.created_at
        else:
            conversation.last_outbound_at = message.created_at
        
        await sync_to_async(conversation.save)()
        
        return message
    
    async def _link_conversation_to_contact(
        self,
        conversation: Conversation,
        recipient: str
    ):
        """Link conversation to existing contact record using contact resolver"""
        
        try:
            from .contact_resolver import contact_resolver
            
            # Use contact resolver for comprehensive contact resolution
            result = await contact_resolver.resolve_contact_from_conversation(
                conversation=conversation,
                force_update=False
            )
            
            if result['success']:
                logger.info(f"Linked conversation {conversation.id} to contact {result['contact_id']}")
                if result.get('created'):
                    logger.info(f"Auto-created new contact: {result['contact_id']}")
            else:
                logger.warning(f"Failed to resolve contact for conversation {conversation.id}: {result['error']}")
                
        except Exception as e:
            logger.warning(f"Failed to link conversation to contact: {e}")
    
    async def resolve_or_create_contact(
        self,
        recipient: str,
        name: Optional[str] = None,
        pipeline_id: Optional[str] = None,
        additional_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Resolve existing contact or create new one"""
        
        try:
            from pipelines.models import Pipeline, Record
            from django.db import connection
            
            # Get default contact pipeline from tenant config if not provided
            if not pipeline_id:
                tenant = connection.tenant
                if (hasattr(tenant, 'unipile_config') and 
                    tenant.unipile_config.default_contact_pipeline):
                    pipeline_id = str(tenant.unipile_config.default_contact_pipeline.id)
                else:
                    return {
                        'success': False,
                        'error': 'No contact pipeline specified and no default configured'
                    }
            
            pipeline = await sync_to_async(Pipeline.objects.get)(id=pipeline_id)
            
            # Search for existing contact
            search_filters = {}
            if '@' in recipient:
                search_filters['data__email__icontains'] = recipient
            elif recipient.replace('+', '').replace('-', '').replace(' ', '').isdigit():
                search_filters['data__phone__icontains'] = recipient
            
            existing_contact = None
            if search_filters:
                existing_contact = await sync_to_async(
                    Record.objects.filter(
                        pipeline=pipeline,
                        **search_filters,
                        is_deleted=False
                    ).first
                )()
            
            if existing_contact:
                return {
                    'success': True,
                    'contact_id': str(existing_contact.id),
                    'created': False,
                    'contact_data': existing_contact.data
                }
            
            # Create new contact
            contact_data = additional_data or {}
            
            if '@' in recipient:
                contact_data['email'] = recipient
            elif recipient.replace('+', '').replace('-', '').replace(' ', '').isdigit():
                contact_data['phone'] = recipient
            
            if name:
                contact_data['name'] = name
            
            # Set default status from tenant config
            tenant = connection.tenant
            if (hasattr(tenant, 'unipile_config') and 
                tenant.unipile_config.default_contact_status):
                contact_data['status'] = tenant.unipile_config.default_contact_status
            
            new_contact = await sync_to_async(Record.objects.create)(
                pipeline=pipeline,
                data=contact_data
            )
            
            return {
                'success': True,
                'contact_id': str(new_contact.id),
                'created': True,
                'contact_data': new_contact.data
            }
            
        except Exception as e:
            logger.error(f"Failed to resolve/create contact: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Global service instance
communication_service = CommunicationService()