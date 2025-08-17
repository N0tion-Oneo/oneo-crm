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
                
                # Get conversations from this channel
                channel_conversations = get_channel_conversations(
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


def get_channel_conversations(
    connection: UserChannelConnection, 
    search: str, 
    status_filter: str, 
    limit: int
) -> List[Dict[str, Any]]:
    """Get conversations from a specific channel connection"""
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
                
                # Create conversation object
                conversation = {
                    'id': f"{connection.channel_type}_{chat.get('id')}",
                    'external_id': chat.get('id'),
                    'type': connection.channel_type,
                    'participants': [
                        {
                            'name': att.get('display_name', att.get('username', 'Unknown')),
                            'email': att.get('email'),
                            'avatar': att.get('profile_picture_url'),
                            'platform': connection.channel_type,
                            'platform_id': att.get('id')
                        }
                        for att in chat.get('attendees', [])
                        if att.get('id') != connection.unipile_account_id  # Exclude self
                    ],
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
    """Get messages for a specific conversation"""
    try:
        # Parse conversation ID to get channel type and external ID
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
        
        client = unipile_service.get_client()
        messages = []
        
        if channel_type in ['linkedin', 'whatsapp', 'instagram', 'messenger', 'telegram']:
            # Get chat messages
            messages_response = async_to_sync(client.messaging.get_all_messages)(
                chat_id=external_id,
                limit=100
            )
            
            for msg in messages_response.get('messages', []):
                messages.append({
                    'id': msg.get('id'),
                    'type': channel_type,
                    'content': msg.get('text', ''),
                    'sender': {
                        'name': msg.get('sender', {}).get('display_name', 'Unknown'),
                        'email': msg.get('sender', {}).get('email'),
                        'platform_id': msg.get('sender', {}).get('id')
                    },
                    'timestamp': msg.get('timestamp'),
                    'is_read': msg.get('is_read', False),
                    'attachments': msg.get('attachments', []),
                    'conversation_id': conversation_id,
                    'account_id': connection.unipile_account_id,
                    'external_id': msg.get('id')
                })
        
        elif channel_type in ['gmail', 'outlook', 'mail']:
            # Get email thread messages
            emails_response = async_to_sync(client.email.get_emails)(
                account_id=connection.unipile_account_id,
                limit=100
            )
            
            # Filter emails by thread ID
            for email in emails_response.get('emails', []):
                if email.get('thread_id') == external_id or email.get('id') == external_id:
                    messages.append({
                        'id': email.get('id'),
                        'type': channel_type,
                        'subject': email.get('subject'),
                        'content': email.get('body', ''),
                        'sender': {
                            'name': email.get('sender', {}).get('name', 'Unknown'),
                            'email': email.get('sender', {}).get('email')
                        },
                        'recipient': {
                            'name': email.get('recipient', {}).get('name', 'Unknown'),
                            'email': email.get('recipient', {}).get('email')
                        },
                        'timestamp': email.get('timestamp'),
                        'is_read': email.get('is_read', False),
                        'attachments': email.get('attachments', []),
                        'conversation_id': conversation_id,
                        'account_id': connection.unipile_account_id,
                        'external_id': email.get('id')
                    })
        
        # Sort messages by timestamp
        messages.sort(key=lambda x: x.get('timestamp', ''))
        
        return Response({
            'messages': messages,
            'conversation_id': conversation_id,
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
        
        if not all([conversation_id, content, message_type]):
            return Response(
                {'error': 'Missing required fields'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse conversation ID
        if '_' not in conversation_id:
            return Response(
                {'error': 'Invalid conversation ID format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        channel_type, external_id = conversation_id.split('_', 1)
        
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
                
                # Create message record with proper contact_email for recipient
                # For WhatsApp, extract recipient from external_id
                recipient_email = ''
                if channel_type == 'whatsapp' and external_id:
                    # external_id should be the WhatsApp chat ID (recipient's phone number)
                    if '@s.whatsapp.net' in external_id:
                        recipient_email = external_id
                    else:
                        # Convert phone number to WhatsApp format if needed
                        recipient_email = f"{external_id}@s.whatsapp.net" if external_id.isdigit() else external_id
                
                message = Message.objects.create(
                    conversation=conversation,
                    channel=channel,
                    external_message_id=result.get('message_id'),
                    direction=MessageDirection.OUTBOUND,
                    status=MessageStatus.SENT,
                    content=content,
                    contact_email=recipient_email,  # Set the recipient's contact email
                    sent_at=timezone.now(),
                    metadata={'attachments': attachments} if attachments else {}
                )
                
                logger.info(f"Created local message record {message.id} for sent message")
                
            except Exception as e:
                logger.error(f"Failed to create local message record: {e}")
                # Don't fail the send operation, just log the error
        
        elif channel_type in ['gmail', 'outlook', 'mail']:
            # For email, we need recipient information
            # This is a simplified implementation - in practice, you'd extract
            # recipients from the original conversation
            return Response(
                {'error': 'Email replies not yet implemented in unified inbox'},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        
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