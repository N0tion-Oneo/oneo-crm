"""
Conversation Messages API - Chronological threading with provider logic
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from communications.models import Conversation, Message, UserChannelConnection
from communications.utils.phone_extractor import get_display_name_or_phone

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversation_messages(request, conversation_id):
    """
    Get chronologically threaded messages for a conversation using provider logic
    
    Query Parameters:
    - limit: Number of messages to return (default: 50)
    - offset: Offset for pagination (default: 0)
    - before: Get messages before this timestamp (ISO format)
    - after: Get messages after this timestamp (ISO format)
    """
    try:
        # Get query parameters
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        before = request.GET.get('before')
        after = request.GET.get('after')
        
        # Get the conversation
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Build query for messages
        messages_qs = conversation.messages.all()
        
        # Apply timestamp filters
        if before:
            try:
                before_dt = datetime.fromisoformat(before.replace('Z', '+00:00'))
                messages_qs = messages_qs.filter(created_at__lt=before_dt)
            except ValueError:
                return Response(
                    {'error': 'Invalid before timestamp format'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if after:
            try:
                after_dt = datetime.fromisoformat(after.replace('Z', '+00:00'))
                messages_qs = messages_qs.filter(created_at__gt=after_dt)
            except ValueError:
                return Response(
                    {'error': 'Invalid after timestamp format'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Order chronologically (oldest first for conversation view)
        messages_qs = messages_qs.order_by('created_at', 'id')
        
        # Apply pagination
        total_count = messages_qs.count()
        messages = messages_qs[offset:offset + limit]
        
        # Process messages with provider logic
        processed_messages = []
        for message in messages:
            message_data = process_message_with_provider_logic(message, conversation)
            processed_messages.append(message_data)
        
        # Get conversation metadata
        conversation_metadata = get_conversation_metadata_with_provider_logic(conversation)
        
        return Response({
            'conversation': conversation_metadata,
            'messages': processed_messages,
            'pagination': {
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + len(messages) < total_count
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting conversation messages: {e}")
        return Response(
            {'error': 'Failed to load conversation messages'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def process_message_with_provider_logic(message: Message, conversation: Conversation) -> Dict[str, Any]:
    """Process a message using provider logic for consistent display (with group chat support)"""
    
    # Extract contact and sender info using NEW group chat-aware provider logic
    contact_name = None
    contact_phone = None
    contact_provider_id = None
    sender_name = 'Unknown Sender'
    is_from_user = False
    is_group_message = False
    
    # Check if we have raw webhook data to work with
    if message.metadata and message.metadata.get('raw_webhook_data'):
        raw_data = message.metadata['raw_webhook_data']
        
        # Use our updated provider logic functions
        from communications.utils.phone_extractor import (
            extract_whatsapp_contact_name,
            extract_whatsapp_phone_from_webhook,
            extract_whatsapp_message_sender
        )
        
        # Extract contact info (group name for groups, contact name for 1-on-1)
        contact_name = extract_whatsapp_contact_name(raw_data)
        contact_phone = extract_whatsapp_phone_from_webhook(raw_data)
        
        # Extract sender info for group messages
        sender_info = extract_whatsapp_message_sender(raw_data)
        is_group_message = sender_info['is_group_message']
        
        if is_group_message:
            # GROUP CHAT: Show individual sender name
            if message.direction == 'inbound':
                sender_name = sender_info['name'] or 'Unknown Member'
                is_from_user = False
            else:
                sender_name = 'You'
                is_from_user = True
            
            # For groups, use group ID as provider_id
            contact_provider_id = raw_data.get('provider_chat_id', '')
        else:
            # 1-ON-1 CHAT: Use contact as sender for inbound, 'You' for outbound
            if message.direction == 'inbound':
                sender_name = contact_name or 'Unknown Contact'
                is_from_user = False
            else:
                sender_name = 'You'
                is_from_user = True
            
            # For 1-on-1, use phone-based provider_id
            if contact_phone:
                contact_provider_id = contact_phone.replace('+', '') + '@s.whatsapp.net'
    
    else:
        # Fallback: Use stored metadata or message fields
        if message.metadata and message.metadata.get('contact_name'):
            stored_name = message.metadata['contact_name']
            if not ('@s.whatsapp.net' in stored_name or stored_name.isdigit() or len(stored_name) > 20):
                contact_name = stored_name
        
        if message.contact_phone:
            contact_phone = message.contact_phone
            contact_provider_id = contact_phone.replace('+', '') + '@s.whatsapp.net' if conversation.channel.channel_type == 'whatsapp' else contact_phone
        
        # Format phone as fallback name
        if not contact_name and contact_phone:
            contact_name = get_display_name_or_phone('', contact_phone)
        
        # Standard direction logic for non-webhook messages
        if message.direction == 'inbound':
            sender_name = contact_name or 'Unknown Contact'
            is_from_user = False
        else:
            sender_name = 'You'
            is_from_user = True
    
    # Extract attachments from raw webhook data if available
    attachments = []
    if message.metadata and message.metadata.get('raw_webhook_data'):
        raw_data = message.metadata['raw_webhook_data']
        webhook_attachments = raw_data.get('attachments', [])
        for attachment in webhook_attachments:
            if isinstance(attachment, dict):
                attachments.append({
                    'id': attachment.get('id'),
                    'type': attachment.get('type'),
                    'name': attachment.get('name'),
                    'url': attachment.get('url'),
                    'size': attachment.get('size')
                })
    
    return {
        'id': str(message.id),
        'content': message.content or '',
        'direction': message.direction,
        'status': message.status,
        'sender': {
            'name': sender_name,
            'is_user': is_from_user,
            'contact_name': contact_name,
            'contact_phone': contact_phone,
            'provider_id': contact_provider_id,
            'is_group_message': is_group_message
        },
        'timestamp': message.created_at.isoformat() if message.created_at else None,
        'sent_at': message.sent_at.isoformat() if message.sent_at else None,
        'received_at': message.received_at.isoformat() if message.received_at else None,
        'attachments': attachments,
        'metadata': {
            'processing_version': message.metadata.get('processing_version', 'unknown') if message.metadata else 'no_metadata',
            'external_message_id': message.external_message_id
        }
    }


def get_conversation_metadata_with_provider_logic(conversation: Conversation) -> Dict[str, Any]:
    """Get conversation metadata using provider logic for contact info"""
    
    # Get the latest message to extract contact info
    latest_message = conversation.messages.order_by('-created_at').first()
    
    contact_name = 'Unknown Contact'
    contact_phone = None
    contact_provider_id = None
    
    if latest_message:
        # Use the same provider logic as message processing
        message_data = process_message_with_provider_logic(latest_message, conversation)
        sender_info = message_data.get('sender', {})
        contact_name = sender_info.get('contact_name') or sender_info.get('name', 'Unknown Contact')
        contact_phone = sender_info.get('contact_phone')
        contact_provider_id = sender_info.get('provider_id')
        
        # If sender is "You", get the contact from the other direction
        if contact_name == 'You' and latest_message.direction == 'outbound':
            # Look for an inbound message to get the contact name
            inbound_message = conversation.messages.filter(direction='inbound').order_by('-created_at').first()
            if inbound_message:
                inbound_data = process_message_with_provider_logic(inbound_message, conversation)
                inbound_sender = inbound_data.get('sender', {})
                contact_name = inbound_sender.get('contact_name') or inbound_sender.get('name', 'Unknown Contact')
                contact_phone = inbound_sender.get('contact_phone')
                contact_provider_id = inbound_sender.get('provider_id')
    
    return {
        'id': str(conversation.id),
        'subject': conversation.subject,
        'external_thread_id': conversation.external_thread_id,
        'status': conversation.status,
        'channel': {
            'id': str(conversation.channel.id),
            'name': conversation.channel.name,
            'type': conversation.channel.channel_type
        },
        'contact': {
            'name': contact_name,
            'phone': contact_phone,
            'provider_id': contact_provider_id
        },
        'created_at': conversation.created_at.isoformat() if conversation.created_at else None,
        'updated_at': conversation.updated_at.isoformat() if conversation.updated_at else None
    }