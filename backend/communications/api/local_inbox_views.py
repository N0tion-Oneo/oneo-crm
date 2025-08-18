"""
Local Database Inbox Views - shows synced messages from local database
This is the correct approach for showing messages that have been synced from UniPile
"""
import logging
from django.db.models import Q, Count, Max, Prefetch
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import (
    UserChannelConnection, Channel, Conversation, Message, 
    MessageDirection, MessageStatus
)

logger = logging.getLogger(__name__)


def _get_contact_name(contact_record):
    """
    Extract contact name from various possible fields in the contact record data.
    Tries multiple field names commonly used for contact names.
    """
    if not contact_record or not contact_record.data:
        return 'Unknown'
    
    data = contact_record.data
    
    # Try different possible name fields in order of preference
    name_fields = [
        'name',           # Standard name field
        'company_name',   # Company name for business contacts
        'full_name',      # Full name field
        'contact_name',   # Contact name field
        'first_name',     # Combine first and last names
        'title',          # Use record title as fallback
    ]
    
    # First, try to get a complete name from single fields
    for field in name_fields:
        if field in data and data[field]:
            return str(data[field]).strip()
    
    # Try to combine first and last name if they exist
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    if first_name and last_name:
        return f"{first_name} {last_name}"
    elif first_name:
        return first_name
    elif last_name:
        return last_name
    
    # Try using the record title as a fallback
    if hasattr(contact_record, 'title') and contact_record.title:
        return contact_record.title
    
    # Final fallback
    return 'Unknown'


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_local_unified_inbox(request):
    """
    Get unified inbox from locally synced messages
    This shows messages that have been synced from UniPile to local database
    """
    try:
        # Get query parameters
        search = request.GET.get('search', '')
        message_type = request.GET.get('type', 'all')  # linkedin, gmail, etc.
        status_filter = request.GET.get('status', 'all')  # unread, all
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        
        # Get user's connected accounts
        user_connections = UserChannelConnection.objects.filter(
            user=request.user,
            is_active=True,
            account_status='active'
        ).select_related('user')
        
        if not user_connections.exists():
            return Response({
                'conversations': [],
                'total_count': 0,
                'user_connections': [],
                'sync_info': {
                    'message': 'No active connections found. Connect accounts to see messages.',
                    'has_connections': False
                }
            })
        
        # Get channels for these connections
        unipile_account_ids = [conn.unipile_account_id for conn in user_connections if conn.unipile_account_id]
        
        if not unipile_account_ids:
            return Response({
                'conversations': [],
                'total_count': 0,
                'user_connections': [
                    {
                        'id': str(conn.id),
                        'account_name': conn.account_name,
                        'channel_type': conn.channel_type,
                        'account_status': conn.account_status,
                        'last_sync_at': conn.last_sync_at.isoformat() if conn.last_sync_at else None,
                        'needs_sync': not conn.last_sync_at
                    } for conn in user_connections
                ],
                'sync_info': {
                    'message': 'Connections found but no UniPile account IDs. Try reconnecting accounts.',
                    'has_connections': True,
                    'needs_sync': True
                }
            })
        
        # Get channels that correspond to user connections
        channels = Channel.objects.filter(
            unipile_account_id__in=unipile_account_ids
        )
        
        if not channels.exists():
            return Response({
                'conversations': [],
                'total_count': 0,
                'user_connections': [
                    {
                        'id': str(conn.id),
                        'account_name': conn.account_name,
                        'channel_type': conn.channel_type,
                        'account_status': conn.account_status,
                        'last_sync_at': conn.last_sync_at.isoformat() if conn.last_sync_at else None,
                        'needs_sync': True
                    } for conn in user_connections
                ],
                'sync_info': {
                    'message': 'No synced channels found. Trigger a message sync to see conversations.',
                    'has_connections': True,
                    'needs_sync': True
                }
            })
        
        # Build query for conversations
        conversations_query = Conversation.objects.filter(
            channel__in=channels
        ).select_related('channel', 'primary_contact_record').prefetch_related(
            Prefetch(
                'messages',
                queryset=Message.objects.order_by('-created_at')[:1],
                to_attr='latest_messages'
            )
        )
        
        # Apply filters
        if message_type != 'all':
            conversations_query = conversations_query.filter(channel__channel_type=message_type)
        
        if search:
            conversations_query = conversations_query.filter(
                Q(subject__icontains=search) |
                Q(messages__content__icontains=search) |
                Q(primary_contact_record__data__name__icontains=search)
            ).distinct()
        
        # Get conversations with latest message info
        conversations = conversations_query.annotate(
            latest_message_time=Max('messages__created_at'),
            total_messages=Count('messages'),
            unread_messages=Count('messages', filter=Q(
                messages__direction=MessageDirection.INBOUND,
                messages__status__in=[MessageStatus.DELIVERED, MessageStatus.SENT]
            ) & ~Q(messages__status=MessageStatus.READ))
        ).order_by('-latest_message_time')[offset:offset + limit]
        
        # Format conversations for response
        conversation_list = []
        for conv in conversations:
            # Get the latest message
            latest_message = None
            if conv.latest_messages:
                latest_msg = conv.latest_messages[0]
                
                # Extract sender name from various sources (prioritize real contact names)
                sender_name = 'Unknown'
                
                # First priority: Enhanced contact name from metadata (real WhatsApp names)
                if latest_msg.metadata and latest_msg.metadata.get('contact_name'):
                    sender_name = latest_msg.metadata['contact_name']
                # Second priority: Contact record
                elif latest_msg.contact_record:
                    sender_name = latest_msg.contact_record.data.get('name', 'Unknown')
                # Third priority: Extract from email
                elif latest_msg.contact_email:
                    if '@' in latest_msg.contact_email:
                        sender_name = latest_msg.contact_email.split('@')[0].replace('.', ' ').title()
                    else:
                        sender_name = latest_msg.contact_email
                
                latest_message = {
                    'id': str(latest_msg.id),
                    'type': conv.channel.channel_type,  # Frontend expects this
                    'subject': latest_msg.subject or '',
                    'content': latest_msg.content[:200] + '...' if len(latest_msg.content) > 200 else latest_msg.content,
                    'timestamp': latest_msg.created_at.isoformat(),
                    'is_read': latest_msg.status in ['read', 'delivered'],
                    'is_starred': False,  # Default for now
                    'sender': {
                        'name': sender_name,
                        'email': latest_msg.contact_email or '',
                        'platform_id': latest_msg.contact_email or ''
                    },
                    'recipient': {
                        'name': 'You',  # Default recipient name
                        'email': ''  # We don't have recipient email stored
                    },
                    # Keep original fields for backward compatibility
                    'direction': latest_msg.direction,
                    'status': latest_msg.status,
                    'created_at': latest_msg.created_at.isoformat(),
                    'contact_email': latest_msg.contact_email,
                    'sender_name': sender_name
                }
            
            # Get channel connection info
            connection_info = None
            for conn in user_connections:
                if conn.unipile_account_id == conv.channel.unipile_account_id:
                    connection_info = {
                        'id': str(conn.id),
                        'account_name': conn.account_name,
                        'channel_type': conn.channel_type,
                        'last_sync_at': conn.last_sync_at.isoformat() if conn.last_sync_at else None
                    }
                    break
            
            # Prepare participants array for frontend compatibility
            participants = []
            
            # Try to get participant info from multiple sources (prioritize real contact names)
            participant_name = 'Unknown Contact'
            participant_email = ''
            
            # First priority: Enhanced contact name from latest message metadata
            if latest_message and latest_message.get('sender_name') and latest_message['sender_name'] not in ['Unknown', '']:
                participant_name = latest_message['sender_name']
                participant_email = latest_message.get('contact_email', '')
            # Second priority: Contact record
            elif conv.primary_contact_record:
                participant_name = conv.primary_contact_record.data.get('name', 'Unknown')
                participant_email = conv.primary_contact_record.data.get('email', '')
            # Third priority: Extract from email
            elif latest_message:
                participant_email = latest_message.get('contact_email', '')
                participant_name = participant_email.split('@')[0] if '@' in participant_email else 'Unknown'
            
            # If still no name, try to extract from email or use fallback
            if participant_name in ['Unknown', 'Unknown Contact', ''] and participant_email:
                if '@' in participant_email:
                    participant_name = participant_email.split('@')[0].replace('.', ' ').title()
                else:
                    participant_name = participant_email
            
            participants.append({
                'name': participant_name,
                'email': participant_email,
                'platform': conv.channel.channel_type
            })

            conversation_data = {
                'id': f"{conv.channel.channel_type}_{conv.external_thread_id}",  # Format for send message API compatibility
                'database_id': str(conv.id),  # Keep original UUID for reference
                'external_thread_id': conv.external_thread_id,
                'subject': conv.subject or 'No Subject',
                'type': conv.channel.channel_type,  # Frontend expects this field
                'participants': participants,  # Frontend expects this field
                'channel': {
                    'id': str(conv.channel.id),
                    'name': conv.channel.name,
                    'type': conv.channel.channel_type,
                    'unipile_account_id': conv.channel.unipile_account_id
                },
                'connection': connection_info,
                'primary_contact': {
                    'id': str(conv.primary_contact_record.id),
                    'name': _get_contact_name(conv.primary_contact_record),
                    'email': conv.primary_contact_record.data.get('email', conv.primary_contact_record.data.get('contact_email', '')),
                    'pipeline_name': conv.primary_contact_record.pipeline.name if conv.primary_contact_record.pipeline else 'Unknown Pipeline'
                } if conv.primary_contact_record else None,
                'last_message': latest_message,
                'message_count': conv.total_messages,
                'unread_count': conv.unread_messages,
                'status': conv.status,
                'priority': conv.priority,
                'created_at': conv.created_at.isoformat(),
                'updated_at': conv.updated_at.isoformat(),
                'last_message_at': conv.last_message_at.isoformat() if conv.last_message_at else None
            }
            
            # Apply status filter
            if status_filter == 'unread' and conversation_data['unread_count'] == 0:
                continue
            
            conversation_list.append(conversation_data)
        
        # Get total count for pagination
        total_conversations = conversations_query.count()
        
        # Get connection info for frontend
        connection_info = []
        for conn in user_connections:
            connection_info.append({
                'id': str(conn.id),
                'account_name': conn.account_name,
                'channel_type': conn.channel_type,
                'account_status': conn.account_status,
                'last_sync_at': conn.last_sync_at.isoformat() if conn.last_sync_at else None,
                'sync_error_count': conn.sync_error_count,
                'can_send_messages': conn.can_send_messages(),
                'needs_sync': not conn.last_sync_at or conn.sync_error_count > 0
            })
        
        return Response({
            'conversations': conversation_list,
            'total_count': total_conversations,
            'limit': limit,
            'offset': offset,
            'has_more': (offset + limit) < total_conversations,
            'user_connections': connection_info,
            'channels_count': channels.count(),
            'sync_info': {
                'message': f'Showing {len(conversation_list)} conversations from {channels.count()} synced channels',
                'has_connections': True,
                'needs_sync': any(not conn.last_sync_at for conn in user_connections)
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get_local_unified_inbox: {e}")
        return Response(
            {'error': 'Failed to load inbox', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_local_conversation_messages(request, conversation_id):
    """
    Get messages for a conversation from local database
    """
    try:
        # Get the conversation - handle both UUID and channel_type_external_id formats
        conversation = None
        
        # Check if it's the new format (contains underscore) first
        if '_' in conversation_id:
            try:
                channel_type, external_thread_id = conversation_id.split('_', 1)
                conversation = Conversation.objects.select_related(
                    'channel', 'primary_contact_record'
                ).get(
                    external_thread_id=external_thread_id,
                    channel__channel_type=channel_type
                )
            except Conversation.DoesNotExist:
                pass
        
        # If not found and no underscore, try UUID format (database_id)
        if not conversation:
            try:
                conversation = Conversation.objects.select_related(
                    'channel', 'primary_contact_record'
                ).get(id=conversation_id)
            except (Conversation.DoesNotExist, ValueError):
                pass
        
        if not conversation:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify user has access to this conversation's channel
        user_connection = UserChannelConnection.objects.filter(
            user=request.user,
            unipile_account_id=conversation.channel.unipile_account_id,
            is_active=True
        ).first()
        
        if not user_connection:
            return Response(
                {'error': 'Access denied to this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get messages with pagination
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        
        messages = Message.objects.filter(
            conversation=conversation
        ).select_related('contact_record').order_by('-created_at')[offset:offset + limit]
        
        # Format messages
        message_list = []
        for msg in messages:
            # Extract sender name from various sources (prioritize real contact names)
            sender_name = 'Unknown'
            sender_email = msg.contact_email or ''
            
            # First priority: Enhanced contact name from metadata (real WhatsApp names)
            if msg.metadata and msg.metadata.get('contact_name'):
                sender_name = msg.metadata['contact_name']
            # Second priority: Contact record
            elif msg.contact_record:
                sender_name = msg.contact_record.data.get('name', 'Unknown')
                sender_email = msg.contact_record.data.get('email', sender_email)
            # Third priority: Extract from email
            elif msg.contact_email:
                if '@' in msg.contact_email:
                    sender_name = msg.contact_email.split('@')[0].replace('.', ' ').title()
                else:
                    sender_name = msg.contact_email
            
            message_data = {
                'id': str(msg.id),
                'type': conversation.channel.channel_type,  # Frontend expects this
                'subject': msg.subject or '',
                'content': msg.content,
                'timestamp': msg.created_at.isoformat(),
                'is_read': msg.status in ['read', 'delivered'],
                'is_starred': False,  # Default for now
                'sender': {
                    'name': sender_name,
                    'email': sender_email,
                    'platform_id': sender_email
                },
                'recipient': {
                    'name': 'You',  # Default recipient name
                    'email': ''  # We don't have recipient email stored
                },
                'attachments': msg.metadata.get('attachments', []) if msg.metadata else [],
                # Keep original fields for backward compatibility
                'external_message_id': msg.external_message_id,
                'direction': msg.direction,
                'status': msg.status,
                'contact_email': msg.contact_email,
                'contact_record': {
                    'id': str(msg.contact_record.id),
                    'name': msg.contact_record.data.get('name', 'Unknown'),
                    'email': msg.contact_record.data.get('email', ''),
                } if msg.contact_record else None,
                'sent_at': msg.sent_at.isoformat() if msg.sent_at else None,
                'received_at': msg.received_at.isoformat() if msg.received_at else None,
                'created_at': msg.created_at.isoformat(),
                'metadata': msg.metadata
            }
            message_list.append(message_data)
        
        # Get total message count
        total_messages = Message.objects.filter(conversation=conversation).count()
        
        return Response({
            'conversation': {
                'id': f"{conversation.channel.channel_type}_{conversation.external_thread_id}",  # Consistent format
                'database_id': str(conversation.id),  # Keep original UUID for reference
                'subject': conversation.subject,
                'external_thread_id': conversation.external_thread_id,
                'status': conversation.status,
                'priority': conversation.priority,
                'channel': {
                    'id': str(conversation.channel.id),
                    'name': conversation.channel.name,
                    'type': conversation.channel.channel_type
                },
                'primary_contact': {
                    'id': str(conversation.primary_contact_record.id),
                    'name': conversation.primary_contact_record.data.get('name', 'Unknown'),
                    'email': conversation.primary_contact_record.data.get('email', ''),
                } if conversation.primary_contact_record else None,
            },
            'messages': message_list,
            'total_count': total_messages,
            'limit': limit,
            'offset': offset,
            'has_more': (offset + limit) < total_messages,
            'connection': {
                'id': str(user_connection.id),
                'account_name': user_connection.account_name,
                'channel_type': user_connection.channel_type,
                'last_sync_at': user_connection.last_sync_at.isoformat() if user_connection.last_sync_at else None
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get_local_conversation_messages: {e}")
        return Response(
            {'error': 'Failed to load conversation messages', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_inbox_stats(request):
    """
    Get inbox statistics for the user
    """
    try:
        # Get user's connections
        user_connections = UserChannelConnection.objects.filter(
            user=request.user,
            is_active=True
        )
        
        if not user_connections.exists():
            return Response({
                'total_conversations': 0,
                'unread_messages': 0,
                'total_messages': 0,
                'channels_count': 0,
                'connections_count': 0,
                'sync_status': {
                    'never_synced': 0,
                    'recently_synced': 0,
                    'sync_errors': 0
                }
            })
        
        # Get channels for these connections
        unipile_account_ids = [conn.unipile_account_id for conn in user_connections if conn.unipile_account_id]
        channels = Channel.objects.filter(unipile_account_id__in=unipile_account_ids)
        
        # Count conversations and messages
        conversations = Conversation.objects.filter(channel__in=channels)
        messages = Message.objects.filter(channel__in=channels)
        
        # Calculate sync status
        never_synced = user_connections.filter(last_sync_at__isnull=True).count()
        recently_synced = user_connections.filter(
            last_sync_at__gte=timezone.now() - timezone.timedelta(hours=1)
        ).count()
        sync_errors = user_connections.filter(sync_error_count__gt=0).count()
        
        return Response({
            'total_conversations': conversations.count(),
            'unread_messages': messages.filter(
                direction=MessageDirection.INBOUND,
                status__in=[MessageStatus.SENT, MessageStatus.DELIVERED]
            ).count(),
            'total_messages': messages.count(),
            'channels_count': channels.count(),
            'connections_count': user_connections.count(),
            'sync_status': {
                'never_synced': never_synced,
                'recently_synced': recently_synced,
                'sync_errors': sync_errors
            },
            'last_sync_times': [
                {
                    'connection_id': str(conn.id),
                    'account_name': conn.account_name,
                    'last_sync_at': conn.last_sync_at.isoformat() if conn.last_sync_at else None,
                    'sync_error_count': conn.sync_error_count
                } for conn in user_connections
            ]
        })
        
    except Exception as e:
        logger.error(f"Error in get_inbox_stats: {e}")
        return Response(
            {'error': 'Failed to load inbox stats', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )