"""
Unified Inbox API Views for comprehensive communication management
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from django.db.models import Q, Count, Max, Case, When, IntegerField
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from asgiref.sync import sync_to_async, async_to_sync

from communications.models import UserChannelConnection
from communications.unipile_sdk import unipile_service
from authentication.permissions import SyncPermissionManager

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unified_inbox(request):
    """Get unified inbox with conversations from all connected channels"""
    try:
        # Get query parameters
        search = request.GET.get('search', '')
        message_type = request.GET.get('type', 'all')
        status_filter = request.GET.get('status', 'all')
        account_filter = request.GET.get('account', 'all')
        limit = int(request.GET.get('limit', 50))
        cursor = request.GET.get('cursor')
        
        # Get user's connected accounts
        user_connections = list(
            UserChannelConnection.objects.filter(
                user=request.user,
                auth_status='authenticated',
                account_status='active'
            ).select_related('user')
        )
        
        if not user_connections:
            return Response({
                'conversations': [],
                'total_count': 0,
                'has_more': False,
                'next_cursor': None
            })
        
        # Build conversations from all channels
        all_conversations = []
        
        for connection in user_connections:
            try:
                # Skip if account filter is specified and doesn't match
                if account_filter != 'all' and connection.id != account_filter:
                    continue
                
                # Skip if type filter doesn't match
                if message_type != 'all' and connection.channel_type != message_type:
                    continue
                
                # Get conversations from stored data with provider logic (Approach 2)
                channel_conversations = get_channel_conversations_from_stored_data(
                    connection, search, status_filter, limit
                )
                
                # Add channel info to each conversation
                for conv in channel_conversations:
                    conv['channel_connection_id'] = connection.id
                    conv['channel_type'] = connection.channel_type
                    conv['account_name'] = connection.account_name
                
                all_conversations.extend(channel_conversations)
                
            except Exception as e:
                logger.error(f"Error fetching conversations from {connection.channel_type} account {connection.id}: {e}")
                continue
        
        # Sort conversations by last message timestamp
        all_conversations.sort(
            key=lambda x: x.get('updated_at', ''), 
            reverse=True
        )
        
        # Apply pagination
        start_idx = 0
        if cursor:
            try:
                start_idx = int(cursor)
            except (ValueError, TypeError):
                start_idx = 0
        
        end_idx = start_idx + limit
        paginated_conversations = all_conversations[start_idx:end_idx]
        
        # Determine if there are more results
        has_more = end_idx < len(all_conversations)
        next_cursor = str(end_idx) if has_more else None
        
        return Response({
            'conversations': paginated_conversations,
            'total_count': len(all_conversations),
            'has_more': has_more,
            'next_cursor': next_cursor
        })
        
    except Exception as e:
        logger.error(f"Error in get_unified_inbox: {e}")
        return Response(
            {'error': 'Failed to load inbox'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def get_channel_conversations_from_stored_data(
    connection: UserChannelConnection, 
    search: str, 
    status_filter: str, 
    limit: int
) -> List[Dict[str, Any]]:
    """Get conversations from stored messages using provider logic (Approach 2)"""
    try:
        from django.db.models import Max, Count, Q
        from communications.models import Conversation, Message
        from communications.utils.phone_extractor import get_display_name_or_phone
        
        # Get conversations for this connection's channel that have messages
        conversations_qs = Conversation.objects.filter(
            channel__unipile_account_id=connection.unipile_account_id,
            channel__channel_type=connection.channel_type,
            messages__isnull=False  # Only conversations with messages
        ).annotate(
            latest_message_at=Max('messages__created_at'),
            calculated_unread_count=Count('messages', filter=Q(messages__status='delivered', messages__direction='inbound'))
        ).distinct().order_by('-latest_message_at')
        
        conversations = []
        
        for conversation in conversations_qs[:limit * 2]:  # Get extra for filtering
            # Get the latest message for preview
            latest_message = conversation.messages.order_by('-created_at').first()
            if not latest_message:
                continue
            
            # Extract contact info using NEW group chat-aware provider logic
            contact_name = None
            contact_phone = None
            contact_provider_id = None
            
            # Method 1: Use stored contact data from message metadata
            if latest_message.metadata and latest_message.metadata.get('contact_name'):
                stored_name = latest_message.metadata['contact_name']
                # Validate it's not a phone/ID
                if not ('@s.whatsapp.net' in stored_name or stored_name.isdigit() or len(stored_name) > 20):
                    contact_name = stored_name
            
            # Method 2: Extract using NEW group chat-aware provider logic
            if not contact_name and latest_message.metadata and latest_message.metadata.get('raw_webhook_data'):
                raw_data = latest_message.metadata['raw_webhook_data']
                
                # Use our updated provider logic functions
                from communications.utils.phone_extractor import (
                    extract_whatsapp_contact_name,
                    extract_whatsapp_phone_from_webhook
                )
                
                # Extract contact name (handles both 1-on-1 and group chats)
                extracted_name = extract_whatsapp_contact_name(raw_data)
                if extracted_name:
                    contact_name = extracted_name
                
                # Extract contact phone (empty for group chats, phone for 1-on-1)
                extracted_phone = extract_whatsapp_phone_from_webhook(raw_data)
                if extracted_phone:
                    contact_phone = extracted_phone
                    contact_provider_id = contact_phone.replace('+', '') + '@s.whatsapp.net'
                elif raw_data.get('is_group'):
                    # For group chats, use group ID as provider_id
                    contact_provider_id = raw_data.get('provider_chat_id', '')
            
            # Method 3: Use contact_phone field from message
            if not contact_phone and latest_message.contact_phone:
                contact_phone = latest_message.contact_phone
                if not contact_provider_id:
                    contact_provider_id = contact_phone.replace('+', '') + '@s.whatsapp.net' if connection.channel_type == 'whatsapp' else contact_phone
            
            # Method 4: Format phone as fallback name for 1-on-1 chats only
            if not contact_name and contact_phone:
                contact_name = get_display_name_or_phone('', contact_phone)
            
            # Method 5: Skip conversations without any contact information
            if not contact_name:
                # Skip conversations that we can't identify
                # This filters out legacy conversations with missing data
                continue
            
            # Apply search filter
            if search and search.lower() not in (
                (contact_name or '').lower() + 
                (latest_message.content or '').lower() +
                (contact_phone or '').lower()
            ):
                continue
            
            # Create conversation object with provider logic
            conversation_data = {
                'id': f"{connection.channel_type}_{conversation.id}",
                'external_id': conversation.external_thread_id,
                'type': connection.channel_type,
                'participants': [
                    {
                        'name': contact_name or 'Unknown Contact',
                        'email': latest_message.contact_email if latest_message.contact_email else None,
                        'avatar': None,  # Could extract from raw_webhook_data if needed
                        'platform': connection.channel_type,
                        'platform_id': contact_provider_id,
                        'provider_id': contact_provider_id
                    }
                ] if contact_name or contact_phone else [],
                'last_message': {
                    'id': str(latest_message.id),
                    'type': connection.channel_type,
                    'content': latest_message.content or '',
                    'sender': {
                        'name': contact_name if latest_message.direction == 'inbound' else 'You',
                        'platform_id': contact_provider_id if latest_message.direction == 'inbound' else connection.unipile_account_id
                    },
                    'timestamp': latest_message.created_at.isoformat() if latest_message.created_at else None,
                    'is_read': latest_message.status in ['read', 'delivered'],
                    'attachments': []  # Could extract from raw_webhook_data if needed
                },
                'unread_count': conversation.calculated_unread_count,
                'message_count': conversation.message_count,
                'created_at': conversation.created_at.isoformat() if conversation.created_at else None,
                'updated_at': conversation.last_message_at.isoformat() if conversation.last_message_at else None
            }
            
            # Apply status filter
            if status_filter == 'unread' and conversation.calculated_unread_count == 0:
                continue
            elif status_filter == 'starred':
                # TODO: Implement starred conversations in stored data
                continue
            
            conversations.append(conversation_data)
            
            if len(conversations) >= limit:
                break
        
        return conversations
        
    except Exception as e:
        logger.error(f"Error getting stored conversations for {connection.channel_type}: {e}")
        # Fallback to live API if stored data fails
        return get_channel_conversations_live_api(connection, search, status_filter, limit)


def get_channel_conversations_live_api(
    connection: UserChannelConnection, 
    search: str, 
    status_filter: str, 
    limit: int
) -> List[Dict[str, Any]]:
    """Get conversations from live UniPile API (fallback method)"""
    try:
        client = unipile_service.get_client()
        
        if connection.channel_type in ['linkedin', 'whatsapp', 'instagram', 'messenger', 'telegram']:
            # Get chats for messaging platforms
            chats_response = async_to_sync(client.messaging.get_all_chats)(
                account_id=connection.unipile_account_id,
                limit=limit
            )
            
            conversations = []
            for chat in chats_response.get('chats', []):
                # Get latest message for each chat
                messages_response = async_to_sync(client.messaging.get_all_messages)(
                    chat_id=chat.get('id'),
                    limit=1
                )
                
                messages = messages_response.get('messages', [])
                if not messages:
                    continue
                
                last_message = messages[0]
                
                # Apply search filter
                if search and search.lower() not in (
                    last_message.get('text', '').lower() + 
                    ' '.join([att.get('name', '') for att in chat.get('attendees', [])])
                ):
                    continue
                
                # Create conversation object using provider logic
                # For WhatsApp, the provider_chat_id represents the contact we're speaking to
                provider_chat_id = chat.get('provider_chat_id') or chat.get('id')
                
                # Find the contact (provider) from attendees
                contact_participant = None
                for att in chat.get('attendees', []):
                    att_provider_id = att.get('attendee_provider_id') or att.get('id')
                    # For WhatsApp, match the provider_chat_id (contact we're speaking to)
                    if connection.channel_type == 'whatsapp':
                        if att_provider_id == provider_chat_id:
                            contact_participant = att
                            break
                    else:
                        # For other platforms, exclude business account
                        if att.get('id') != connection.unipile_account_id:
                            contact_participant = att
                            break
                
                # Create participants array with the contact
                participants = []
                if contact_participant:
                    # Use provider logic for name extraction
                    contact_name = contact_participant.get('attendee_name') or contact_participant.get('display_name') or contact_participant.get('username')
                    contact_provider_id = contact_participant.get('attendee_provider_id') or contact_participant.get('id')
                    
                    # Don't use phone numbers or JIDs as names
                    if contact_name and ('@s.whatsapp.net' in contact_name or contact_name.isdigit()):
                        contact_name = None
                    
                    # Fallback to formatted phone for WhatsApp
                    if not contact_name and connection.channel_type == 'whatsapp' and contact_provider_id:
                        if '@s.whatsapp.net' in contact_provider_id:
                            phone = contact_provider_id.replace('@s.whatsapp.net', '')
                            # Format phone with country code
                            clean_phone = ''.join(c for c in phone if c.isdigit())
                            if len(clean_phone) >= 7:
                                from communications.utils.phone_extractor import get_display_name_or_phone
                                contact_name = get_display_name_or_phone('', f"+{clean_phone}")
                    
                    participants.append({
                        'name': contact_name or 'Unknown Contact',
                        'email': contact_participant.get('email'),
                        'avatar': contact_participant.get('profile_picture_url'),
                        'platform': connection.channel_type,
                        'platform_id': contact_participant.get('id'),
                        'provider_id': contact_provider_id
                    })
                
                conversation = {
                    'id': f"{connection.channel_type}_{chat.get('id')}",
                    'external_id': chat.get('id'),
                    'type': connection.channel_type,
                    'participants': participants,
                    'last_message': {
                        'id': last_message.get('id'),
                        'type': connection.channel_type,
                        'content': last_message.get('text', ''),
                        'sender': {
                            'name': last_message.get('sender', {}).get('display_name', 'Unknown'),
                            'platform_id': last_message.get('sender', {}).get('id')
                        },
                        'timestamp': last_message.get('timestamp'),
                        'is_read': last_message.get('is_read', False),
                        'attachments': last_message.get('attachments', [])
                    },
                    'unread_count': chat.get('unread_messages_count', 0),
                    'created_at': chat.get('created_at'),
                    'updated_at': last_message.get('timestamp')
                }
                
                # Apply status filter
                if status_filter == 'unread' and conversation['unread_count'] == 0:
                    continue
                elif status_filter == 'starred':
                    # TODO: Implement starred conversations
                    continue
                
                conversations.append(conversation)
            
            return conversations
            
        elif connection.channel_type in ['gmail', 'outlook', 'mail']:
            # Get emails for email platforms
            emails_response = async_to_sync(client.email.get_emails)(
                account_id=connection.unipile_account_id,
                folder='INBOX',
                limit=limit
            )
            
            conversations = []
            emails_by_thread = {}
            
            # Group emails by conversation thread
            for email in emails_response.get('emails', []):
                thread_id = email.get('thread_id', email.get('id'))
                
                if thread_id not in emails_by_thread:
                    emails_by_thread[thread_id] = []
                
                emails_by_thread[thread_id].append(email)
            
            # Create conversation objects
            for thread_id, thread_emails in emails_by_thread.items():
                # Sort emails by timestamp to get the latest
                thread_emails.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                latest_email = thread_emails[0]
                
                # Apply search filter
                if search and search.lower() not in (
                    latest_email.get('subject', '').lower() + 
                    latest_email.get('body', '').lower() +
                    latest_email.get('sender', {}).get('name', '').lower()
                ):
                    continue
                
                # Count unread emails in thread
                unread_count = sum(1 for email in thread_emails if not email.get('is_read', False))
                
                conversation = {
                    'id': f"{connection.channel_type}_{thread_id}",
                    'external_id': thread_id,
                    'type': connection.channel_type,
                    'participants': [
                        {
                            'name': latest_email.get('sender', {}).get('name', 'Unknown'),
                            'email': latest_email.get('sender', {}).get('email'),
                            'platform': connection.channel_type
                        }
                    ],
                    'last_message': {
                        'id': latest_email.get('id'),
                        'type': connection.channel_type,
                        'subject': latest_email.get('subject'),
                        'content': latest_email.get('body', ''),
                        'sender': {
                            'name': latest_email.get('sender', {}).get('name', 'Unknown'),
                            'email': latest_email.get('sender', {}).get('email')
                        },
                        'timestamp': latest_email.get('timestamp'),
                        'is_read': latest_email.get('is_read', False),
                        'attachments': latest_email.get('attachments', [])
                    },
                    'unread_count': unread_count,
                    'message_count': len(thread_emails),
                    'created_at': min(email.get('timestamp', '') for email in thread_emails),
                    'updated_at': latest_email.get('timestamp')
                }
                
                # Apply status filter
                if status_filter == 'unread' and conversation['unread_count'] == 0:
                    continue
                elif status_filter == 'starred':
                    # Check if any email in thread is starred
                    if not any(email.get('is_starred', False) for email in thread_emails):
                        continue
                
                conversations.append(conversation)
            
            return conversations
        
        else:
            logger.warning(f"Unsupported channel type for inbox: {connection.channel_type}")
            return []
            
    except Exception as e:
        logger.error(f"Error getting conversations for {connection.channel_type}: {e}")
        return []


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversation_messages(request, conversation_id):
    """Get messages for a specific conversation from database records"""
    try:
        # Import models here to avoid circular imports
        from communications.models import Message, Conversation
        
        # Try to find conversation by UUID first
        import uuid
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        
        conversation = None
        
        if re.match(uuid_pattern, conversation_id, re.IGNORECASE):
            # UUID format - look up conversation directly
            try:
                conversation = Conversation.objects.select_related('channel').get(id=conversation_id)
            except Conversation.DoesNotExist:
                return Response(
                    {'error': 'Conversation not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Legacy format: channel_type_external_id
            if '_' not in conversation_id:
                return Response(
                    {'error': 'Invalid conversation ID format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            channel_type, external_id = conversation_id.split('_', 1)
            
            # Find the user's connection for this channel
            try:
                connection = UserChannelConnection.objects.get(
                    user=request.user,
                    channel_type=channel_type,
                    auth_status='authenticated',
                    account_status='active'
                )
            except UserChannelConnection.DoesNotExist:
                return Response(
                    {'error': 'Channel connection not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Find conversation by external thread ID
            try:
                conversation = Conversation.objects.select_related('channel').get(
                    external_thread_id=external_id,
                    channel__unipile_account_id=connection.unipile_account_id
                )
            except Conversation.DoesNotExist:
                return Response(
                    {'error': 'Conversation not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Get messages from database
        db_messages = Message.objects.filter(
            conversation=conversation
        ).order_by('created_at')
        
        messages = []
        
        # Convert database messages to API format
        for msg in db_messages:
            # Determine message type based on channel
            msg_type = 'email' if conversation.channel.channel_type in ['gmail', 'outlook', 'mail'] else conversation.channel.channel_type
            
            # Extract sender information
            sender_name = 'Unknown'
            sender_email = None
            
            if msg.metadata and isinstance(msg.metadata, dict):
                sender_info = msg.metadata.get('sender_info', {})
                sender_name = sender_info.get('name', 'Unknown')
                sender_email = sender_info.get('email')
            
            message_data = {
                'id': str(msg.id),
                'type': msg_type,
                'subject': getattr(msg, 'subject', ''),
                'content': msg.content,
                'direction': msg.direction.value if hasattr(msg.direction, 'value') else str(msg.direction),
                'sender': {
                    'name': sender_name,
                    'email': sender_email
                },
                'timestamp': msg.created_at.isoformat(),
                'is_read': msg.status.value == 'READ' if hasattr(msg.status, 'value') else str(msg.status) == 'READ',
                'attachments': [],  # TODO: Extract from metadata if needed
                'conversation_id': str(conversation.id),
                'account_id': conversation.channel.unipile_account_id,
                'external_id': msg.external_message_id or str(msg.id),
                'metadata': msg.metadata  # Include full metadata for frontend processing
            }
            
            messages.append(message_data)
        
        # Sort messages by timestamp  
        messages.sort(key=lambda x: x.get('timestamp', ''))
        
        return Response({
            'messages': messages,
            'conversation_id': str(conversation.id),
            'total_count': len(messages)
        })
        
    except Exception as e:
        logger.error(f"Error getting conversation messages: {e}")
        return Response(
            {'error': 'Failed to load messages'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_conversation_as_read(request, conversation_id):
    """Mark a conversation as read"""
    try:
        # Handle both conversation ID formats:
        # 1. New format: database UUID (e.g., "12345678-1234-1234-1234-123456789abc")
        # 2. Legacy format: channel_type_external_id (e.g., "whatsapp_chat123", "whatsapp_msg_1755375390.209687")
        
        # First, try to detect if it's a UUID format
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        
        # Import Conversation model for both format types
        from communications.models import Conversation
        
        if re.match(uuid_pattern, conversation_id, re.IGNORECASE):
            # New format: database UUID - look up conversation directly
            try:
                conversation = Conversation.objects.select_related('channel').get(id=conversation_id)
                # Derive channel_type and external_id from the conversation
                channel_type = conversation.channel.channel_type
                external_id = conversation.external_thread_id
            except (Conversation.DoesNotExist, ValueError):
                return Response(
                    {'error': 'Conversation not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Legacy format: channel_type_external_id (split by first underscore)
            if '_' in conversation_id:
                channel_type, external_id = conversation_id.split('_', 1)
                conversation = None
            else:
                return Response(
                    {'error': 'Invalid conversation ID format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Find the user's connection
        try:
            connection = UserChannelConnection.objects.get(
                user=request.user,
                channel_type=channel_type,
                auth_status='authenticated',
                account_status='active'
            )
        except UserChannelConnection.DoesNotExist:
            return Response(
                {'error': 'Channel connection not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        client = unipile_service.get_client()
        
        if channel_type in ['gmail', 'outlook', 'mail']:
            # Get all emails in thread and mark as read
            emails_response = async_to_sync(client.email.get_emails)(
                account_id=connection.unipile_account_id,
                limit=100
            )
            
            email_ids = []
            for email in emails_response.get('emails', []):
                if (email.get('thread_id') == external_id or email.get('id') == external_id) and not email.get('is_read', False):
                    email_ids.append(email.get('id'))
            
            if email_ids:
                async_to_sync(client.email.mark_as_read)(
                    account_id=connection.unipile_account_id,
                    email_ids=email_ids
                )
        
        elif channel_type == 'whatsapp':
            # For WhatsApp, mark messages as read in our local database
            try:
                from communications.models import Message, MessageStatus, MessageDirection
                
                # If we don't already have the conversation from UUID lookup, find it by external_id
                if conversation is None:
                    conversation = Conversation.objects.filter(
                        external_thread_id=external_id,
                        channel__unipile_account_id=connection.unipile_account_id
                    ).first()
                
                if conversation:
                    # Mark all delivered inbound messages in this conversation as read
                    updated_count = Message.objects.filter(
                        conversation=conversation,
                        direction=MessageDirection.INBOUND,
                        status=MessageStatus.DELIVERED
                    ).update(status=MessageStatus.READ)
                    
                    logger.info(f"Marked {updated_count} WhatsApp messages as read in conversation {conversation.id}")
                else:
                    logger.warning(f"WhatsApp conversation not found for external_id: {external_id}")
                    
            except Exception as e:
                logger.error(f"Error marking WhatsApp conversation as read: {e}")
        
        # Note: For other messaging platforms, read status is typically handled automatically
        # when messages are retrieved, but we could implement explicit read marking here
        
        return Response({'success': True})
        
    except Exception as e:
        logger.error(f"Error marking conversation as read: {e}")
        return Response(
            {'error': 'Failed to mark conversation as read'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request):
    """Send a message in a conversation"""
    try:
        data = request.data
        conversation_id = data.get('conversation_id')
        content = data.get('content')
        message_type = data.get('type')
        attachments = data.get('attachments', [])
        
        # Debug logging
        logger.info(f"Send message request data: {data}")
        logger.info(f"conversation_id: {conversation_id}, content: {content and content[:50]}, type: {message_type}")
        
        if not all([content, message_type]):
            return Response(
                {'error': 'Missing required fields: content and type are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse conversation ID or use message type for new messages
        if conversation_id and '_' in conversation_id:
            # Existing conversation
            channel_type, external_id = conversation_id.split('_', 1)
        elif not conversation_id and message_type:
            # New message - use message type as channel type
            channel_type = message_type
            external_id = None
        else:
            return Response(
                {'error': 'Invalid conversation ID format or message type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find the user's connection
        try:
            connection = UserChannelConnection.objects.get(
                user=request.user,
                channel_type=channel_type,
                auth_status='authenticated',
                account_status='active'
            )
        except UserChannelConnection.DoesNotExist:
            return Response(
                {'error': 'Channel connection not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        client = unipile_service.get_client()
        
        if channel_type in ['linkedin', 'whatsapp', 'instagram', 'messenger', 'telegram']:
            # Send chat message
            result = async_to_sync(client.messaging.send_message)(
                chat_id=external_id,
                text=content,
                attachments=attachments
            )
            
            # Create local database record for sent message
            try:
                from communications.models import Channel, Conversation, Message, MessageDirection, MessageStatus
                
                # Get or create channel
                channel, created = Channel.objects.get_or_create(
                    unipile_account_id=connection.unipile_account_id,
                    defaults={
                        'name': f"{connection.account_name} ({channel_type})",
                        'channel_type': channel_type,
                        'is_active': True
                    }
                )
                
                # Get or create conversation
                conversation, created = Conversation.objects.get_or_create(
                    channel=channel,
                    external_thread_id=external_id,
                    defaults={
                        'subject': 'WhatsApp Conversation',
                        'status': 'active',
                        'priority': 'normal'
                    }
                )
                
                # Create message record with provider logic for recipient
                # For WhatsApp, extract recipient info using provider logic
                contact_phone = ''
                contact_name = ''
                
                if channel_type == 'whatsapp' and external_id:
                    # external_id should be the WhatsApp chat ID (recipient's phone number)
                    if '@s.whatsapp.net' in external_id:
                        # Extract phone number and format with country code
                        phone_number = external_id.replace('@s.whatsapp.net', '')
                        clean_phone = ''.join(c for c in phone_number if c.isdigit())
                        if len(clean_phone) >= 7:
                            contact_phone = f"+{clean_phone}"
                    elif external_id.isdigit():
                        # Direct phone number
                        contact_phone = f"+{external_id}"
                    
                    # Try to get contact name from existing messages in this conversation
                    if conversation:
                        existing_message = conversation.messages.filter(
                            direction=MessageDirection.INBOUND
                        ).order_by('-created_at').first()
                        
                        if existing_message and existing_message.metadata:
                            contact_name = existing_message.metadata.get('contact_name', '')
                    
                    # Fallback to formatted phone if no name found
                    if not contact_name and contact_phone:
                        from communications.utils.phone_extractor import get_display_name_or_phone
                        contact_name = get_display_name_or_phone('', contact_phone)
                
                message = Message.objects.create(
                    conversation=conversation,
                    channel=channel,
                    external_message_id=result.get('message_id'),
                    direction=MessageDirection.OUTBOUND,
                    status=MessageStatus.SENT,
                    content=content,
                    contact_phone=contact_phone,  # Use contact_phone with country code
                    contact_email='',  # Empty for WhatsApp
                    sent_at=timezone.now(),
                    metadata={
                        'contact_name': contact_name,
                        'processing_version': '2.0_simplified',
                        'sent_via_api': True,
                        'attachments': attachments,
                        'raw_api_response': result,  # Store the raw UniPile API response
                        'api_request_data': {
                            'chat_id': external_id,
                            'text': content,
                            'attachments': attachments,
                            'account_id': connection.unipile_account_id
                        }
                    }
                )
                
                logger.info(f"Created local message record {message.id} for sent message")
                
            except Exception as e:
                logger.error(f"Failed to create local message record: {e}")
                # Don't fail the send operation, just log the error
        
        elif channel_type in ['gmail', 'outlook', 'mail', 'email']:
            # Send email (reply or new)
            subject = data.get('subject', 'New Message' if not external_id else 'Re: Conversation')
            to_emails = data.get('to', [])
            cc_emails = data.get('cc', [])
            bcc_emails = data.get('bcc', [])
            recipient = data.get('recipient', '')
            
            # If no to_emails but recipient is provided, use recipient
            if not to_emails and recipient:
                to_emails = [recipient] if isinstance(recipient, str) else recipient
            
            # If no recipients provided and we have a conversation, try to extract from conversation context
            if not to_emails and external_id:
                # For email conversations, external_id is typically the thread_id
                # We need to look up the original conversation to get participants
                try:
                    from communications.models import Conversation, Message
                    conversation = Conversation.objects.filter(
                        external_thread_id=external_id,
                        channel__unipile_account_id=connection.unipile_account_id
                    ).first()
                    
                    if conversation:
                        # Get the most recent inbound message to determine reply recipient
                        latest_message = Message.objects.filter(
                            conversation=conversation,
                            direction='inbound'
                        ).order_by('-received_at').first()
                        
                        if latest_message and latest_message.contact_email:
                            to_emails = [latest_message.contact_email]
                
                except Exception as e:
                    logger.warning(f"Could not determine email recipients: {e}")
            
            # Validate that we have recipients
            if not to_emails:
                return Response(
                    {'error': 'Email recipients must be specified. Provide either "to" array or "recipient" field.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f"Sending email to: {to_emails}, subject: {subject}, external_id: {external_id}")
            
            # Send email via UniPile SDK
            result = async_to_sync(client.email.send_email)(
                account_id=connection.unipile_account_id,
                to=to_emails,
                subject=subject,
                body=content,
                cc=cc_emails if cc_emails else None,
                bcc=bcc_emails if bcc_emails else None,
                attachments=attachments if attachments else None,
                is_html=True
            )
            
            # Create local database record for sent email
            try:
                from communications.models import Channel, Conversation, Message, MessageDirection, MessageStatus
                
                # Get or create channel
                channel, created = Channel.objects.get_or_create(
                    unipile_account_id=connection.unipile_account_id,
                    defaults={
                        'name': f"{connection.account_name} ({channel_type})",
                        'channel_type': channel_type,
                        'is_active': True
                    }
                )
                
                # Get or create conversation
                thread_id = external_id or result.get('thread_id', '') or f"email_{timezone.now().timestamp()}"
                conversation, created = Conversation.objects.get_or_create(
                    channel=channel,
                    external_thread_id=thread_id,
                    defaults={
                        'subject': subject,
                        'status': 'active',
                        'priority': 'normal'
                    }
                )
                
                # Create message record
                message = Message.objects.create(
                    conversation=conversation,
                    channel=channel,
                    external_message_id=result.get('email_id'),
                    direction=MessageDirection.OUTBOUND,
                    status=MessageStatus.SENT,
                    content=content,
                    contact_email=', '.join(to_emails),  # Store primary recipients
                    sent_at=timezone.now(),
                    metadata={
                        'subject': subject,
                        'to': to_emails,
                        'cc': cc_emails,
                        'bcc': bcc_emails,
                        'attachments': attachments
                    }
                )
                
                logger.info(f"Created local email message record {message.id}")
                
            except Exception as e:
                logger.error(f"Failed to create local email message record: {e}")
                # Don't fail the send operation, just log the error
        
        else:
            return Response(
                {'error': f'Unsupported message type: {channel_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            'success': True,
            'message_id': result.get('message_id'),
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return Response(
            {'error': 'Failed to send message'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )