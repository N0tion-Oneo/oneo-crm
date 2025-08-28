"""
Participant-based Inbox Views
Shows both stored conversations and live data from UniPile
with participant resolution and contact matching
"""
import logging
from typing import List, Dict, Any
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from asgiref.sync import async_to_sync, sync_to_async
from django.db.models import Q, Prefetch

from communications.models import (
    Conversation, ConversationParticipant, Participant,
    UserChannelConnection, Message
)
from communications.services import ParticipantResolutionService, ConversationStorageDecider
from communications.channels.email.service import EmailService
from communications.channels.whatsapp.service import WhatsAppService

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_participant_inbox(request):
    """
    Get participant-based inbox showing both stored and live conversations
    
    Priority:
    1. Stored conversations (with linked contacts)
    2. Live conversations (without linked contacts but visible)
    
    Query params:
    - channel_type: Filter by channel type (email, whatsapp, etc.)
    - has_contact: Filter to only show conversations with contacts (true/false)
    - limit: Number of conversations to return (default: 50)
    - offset: Pagination offset (default: 0)
    """
    channel_type = request.GET.get('channel_type')
    has_contact_filter = request.GET.get('has_contact')
    limit = int(request.GET.get('limit', 50))
    offset = int(request.GET.get('offset', 0))
    
    try:
        # Get user's channel connections
        connections_query = UserChannelConnection.objects.filter(
            user=request.user,
            auth_status='connected'
        )
        
        if channel_type:
            connections_query = connections_query.filter(channel_type=channel_type)
        
        connections = list(connections_query)
        
        if not connections:
            return Response({
                'success': True,
                'conversations': [],
                'total': 0,
                'has_more': False
            })
        
        # 1. Get stored conversations with participant information
        from asgiref.sync import async_to_sync
        stored_conversations = async_to_sync(get_stored_conversations_with_participants)(
            request.user,
            channel_type,
            has_contact_filter,
            limit,
            offset
        )
        
        # 2. Get live conversations from UniPile (if we haven't hit the limit)
        remaining_limit = limit - len(stored_conversations)
        live_conversations = []
        
        if remaining_limit > 0:
            # Get live data from each connection
            for connection in connections:
                if connection.channel_type in ['gmail', 'outlook', 'mail']:
                    live_emails = async_to_sync(get_live_email_conversations)(
                        connection,
                        request.tenant if hasattr(request, 'tenant') else None,
                        remaining_limit
                    )
                    live_conversations.extend(live_emails)
                elif connection.channel_type == 'whatsapp':
                    live_chats = async_to_sync(get_live_whatsapp_conversations)(
                        connection,
                        request.tenant if hasattr(request, 'tenant') else None,
                        remaining_limit
                    )
                    live_conversations.extend(live_chats)
                # Add other channel types as needed
        
        # 3. Merge conversations, removing duplicates (prefer stored over live)
        merged_conversations = merge_conversations(stored_conversations, live_conversations)
        
        # 4. Apply has_contact filter if specified
        if has_contact_filter == 'true':
            merged_conversations = [c for c in merged_conversations if c.get('has_contact_match')]
        elif has_contact_filter == 'false':
            merged_conversations = [c for c in merged_conversations if not c.get('has_contact_match')]
        
        # 5. Sort by last activity
        merged_conversations.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        
        return Response({
            'success': True,
            'conversations': merged_conversations[:limit],
            'total': len(merged_conversations),
            'has_more': len(merged_conversations) > limit,
            'stored_count': len(stored_conversations),
            'live_count': len(live_conversations)
        })
        
    except Exception as e:
        logger.error(f"Error getting participant inbox: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def get_stored_conversations_with_participants(
    user,
    channel_type=None,
    has_contact_filter=None,
    limit=50,
    offset=0
) -> List[Dict[str, Any]]:
    """
    Get stored conversations with full participant information
    """
    # Build query
    conversations_query = Conversation.objects.filter(
        channel__created_by=user,
        status='active'
    )
    
    if channel_type:
        conversations_query = conversations_query.filter(channel__channel_type=channel_type)
    
    # Prefetch participants with contact and secondary record information
    conversations_query = conversations_query.prefetch_related(
        Prefetch(
            'conversation_participants',
            queryset=ConversationParticipant.objects.select_related(
                'participant__contact_record',
                'participant__secondary_record'
            ).filter(is_active=True)
        ),
        'messages',
        'channel'
    )
    
    # Order by last activity
    conversations_query = conversations_query.order_by('-last_message_at')
    
    # Apply pagination
    conversations = await sync_to_async(list)(
        conversations_query[offset:offset + limit]
    )
    
    # Transform to response format
    result = []
    for conversation in conversations:
        # Get participants
        participants_data = []
        has_contact = False
        
        conv_participants = await sync_to_async(list)(
            conversation.conversation_participants.all()
        )
        
        for cp in conv_participants:
            participant = cp.participant
            participant_data = {
                'id': str(participant.id),
                'email': participant.email,
                'phone': participant.phone,
                'name': participant.name or participant.get_display_name(),
                'role': cp.role,
                'has_contact': bool(participant.contact_record),
                'contact_id': str(participant.contact_record.id) if participant.contact_record else None,
                'confidence': participant.resolution_confidence,
                # Secondary record (e.g., company via domain)
                'has_secondary': bool(participant.secondary_record),
                'secondary_id': str(participant.secondary_record.id) if participant.secondary_record else None,
                'secondary_pipeline': participant.secondary_pipeline,
                'secondary_confidence': participant.secondary_confidence,
                'secondary_method': participant.secondary_resolution_method
            }
            participants_data.append(participant_data)
            
            if participant.contact_record or participant.secondary_record:
                has_contact = True
        
        # Get message count
        message_count = await sync_to_async(conversation.messages.count)()
        
        # Build conversation object
        conv_data = {
            'id': str(conversation.id),
            'external_thread_id': conversation.external_thread_id,
            'subject': conversation.subject,
            'channel_type': conversation.channel.channel_type,
            'channel_name': conversation.channel.name,
            'participants': participants_data,
            'participant_count': len(participants_data),
            'has_contact_match': has_contact,
            'message_count': message_count,
            'unread_count': conversation.unread_count,
            'last_message_at': conversation.last_message_at.isoformat() if conversation.last_message_at else None,
            'created_at': conversation.created_at.isoformat(),
            'updated_at': conversation.updated_at.isoformat(),
            'source': 'stored',
            'stored': True
        }
        
        # Apply has_contact filter if specified
        if has_contact_filter == 'true' and not has_contact:
            continue
        elif has_contact_filter == 'false' and has_contact:
            continue
        
        result.append(conv_data)
    
    return result


async def get_live_email_conversations(connection, tenant, limit) -> List[Dict[str, Any]]:
    """
    Get live email conversations from UniPile
    """
    try:
        service = EmailService()
        storage_decider = ConversationStorageDecider(tenant)
        
        # Fetch emails from UniPile
        result = await service.get_emails(
            account_id=connection.unipile_account_id,
            limit=limit,
            meta_only=False
        )
        
        if not result.get('success'):
            return []
        
        conversations = []
        
        # Group emails by thread
        email_groups = {}
        for email in result.get('emails', []):
            thread_id = email.get('thread_id') or email.get('id')
            if thread_id not in email_groups:
                email_groups[thread_id] = []
            email_groups[thread_id].append(email)
        
        # Process each thread
        for thread_id, thread_emails in email_groups.items():
            thread_emails.sort(key=lambda x: x.get('date', ''), reverse=True)
            latest_email = thread_emails[0]
            
            # Check if already stored
            existing = await sync_to_async(
                Conversation.objects.filter(
                    external_thread_id=thread_id,
                    channel__unipile_account_id=connection.unipile_account_id
                ).exists
            )()
            
            if existing:
                continue  # Skip if already stored
            
            # Build conversation data for participant resolution
            conversation_data = {
                'from_attendee': latest_email.get('from_attendee') or latest_email.get('from'),
                'to_attendees': latest_email.get('to_attendees', []) or latest_email.get('to', []),
                'cc_attendees': latest_email.get('cc_attendees', []) or latest_email.get('cc', []),
            }
            
            # Resolve participants
            should_store, participants = await storage_decider.should_store_conversation(
                conversation_data,
                'email'
            )
            
            # Build participant display
            participants_data = []
            has_contact = False
            
            for participant in participants:
                participant_data = {
                    'id': str(participant.id),
                    'email': participant.email,
                    'name': participant.name or participant.email,
                    'has_contact': bool(participant.contact_record),
                    'contact_id': str(participant.contact_record.id) if participant.contact_record else None,
                    'confidence': participant.resolution_confidence
                }
                participants_data.append(participant_data)
                
                if participant.contact_record:
                    has_contact = True
            
            conversations.append({
                'external_thread_id': thread_id,
                'subject': latest_email.get('subject', '(no subject)'),
                'channel_type': 'email',
                'channel_name': connection.account_name,
                'participants': participants_data,
                'participant_count': len(participants_data),
                'has_contact_match': has_contact,
                'should_store': should_store,
                'message_count': len(thread_emails),
                'unread_count': sum(1 for e in thread_emails if not e.get('is_read', False)),
                'last_message_at': latest_email.get('date'),
                'created_at': thread_emails[-1].get('date') if thread_emails else None,
                'updated_at': latest_email.get('date'),
                'source': 'live',
                'stored': False
            })
        
        return conversations
        
    except Exception as e:
        logger.error(f"Error getting live email conversations: {e}")
        return []


async def get_live_whatsapp_conversations(connection, tenant, limit) -> List[Dict[str, Any]]:
    """
    Get live WhatsApp conversations from UniPile
    """
    try:
        service = WhatsAppService()
        storage_decider = ConversationStorageDecider(tenant)
        
        # Fetch chats from UniPile
        result = await service.get_chats(
            account_id=connection.unipile_account_id,
            limit=limit
        )
        
        if not result.get('success'):
            return []
        
        conversations = []
        
        for chat in result.get('chats', []):
            chat_id = chat.get('id')
            
            # Check if already stored
            existing = await sync_to_async(
                Conversation.objects.filter(
                    external_thread_id=chat_id,
                    channel__unipile_account_id=connection.unipile_account_id
                ).exists
            )()
            
            if existing:
                continue
            
            # Resolve participants
            should_store, participants = await storage_decider.should_store_conversation(
                chat,
                'whatsapp'
            )
            
            # Build participant display
            participants_data = []
            has_contact = False
            
            for participant in participants:
                participant_data = {
                    'id': str(participant.id),
                    'phone': participant.phone,
                    'name': participant.name or participant.phone,
                    'has_contact': bool(participant.contact_record),
                    'contact_id': str(participant.contact_record.id) if participant.contact_record else None,
                    'confidence': participant.resolution_confidence
                }
                participants_data.append(participant_data)
                
                if participant.contact_record:
                    has_contact = True
            
            conversations.append({
                'external_thread_id': chat_id,
                'subject': chat.get('name', 'WhatsApp Chat'),
                'channel_type': 'whatsapp',
                'channel_name': connection.account_name,
                'participants': participants_data,
                'participant_count': len(participants_data),
                'has_contact_match': has_contact,
                'should_store': should_store,
                'message_count': chat.get('message_count', 0),
                'unread_count': chat.get('unread_count', 0),
                'last_message_at': chat.get('last_message_date'),
                'created_at': chat.get('created_at'),
                'updated_at': chat.get('last_message_date'),
                'source': 'live',
                'stored': False
            })
        
        return conversations
        
    except Exception as e:
        logger.error(f"Error getting live WhatsApp conversations: {e}")
        return []


def merge_conversations(stored: List[Dict], live: List[Dict]) -> List[Dict]:
    """
    Merge stored and live conversations, removing duplicates
    Prefer stored over live when duplicate found
    """
    # Track external IDs of stored conversations
    stored_ids = {conv['external_thread_id'] for conv in stored}
    
    # Add live conversations that aren't already stored
    merged = list(stored)
    for live_conv in live:
        if live_conv['external_thread_id'] not in stored_ids:
            merged.append(live_conv)
    
    return merged


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def link_conversation_to_contact(request):
    """
    Manually link a conversation to a contact
    This will trigger historical sync for the contact
    """
    conversation_id = request.data.get('conversation_id')
    external_thread_id = request.data.get('external_thread_id')
    contact_id = request.data.get('contact_id')
    channel_type = request.data.get('channel_type')
    account_id = request.data.get('account_id')
    
    if not contact_id:
        return Response({
            'success': False,
            'error': 'contact_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from pipelines.models import Record
        from communications.sync import ContactHistorySyncOrchestrator
        
        # Get the contact record
        contact = Record.objects.get(id=contact_id)
        
        # If conversation exists, link it
        if conversation_id:
            conversation = Conversation.objects.get(id=conversation_id)
            # Link via participants (implementation needed)
            # ...
        
        # If external thread, fetch and store it
        elif external_thread_id and channel_type and account_id:
            # Fetch the thread from UniPile and store it
            # ...
            pass
        
        # Trigger historical sync for the contact
        orchestrator = ContactHistorySyncOrchestrator()
        sync_result = async_to_sync(orchestrator.sync_contact_communications)(
            contact,
            trigger_source='manual_link'
        )
        
        return Response({
            'success': True,
            'sync_result': sync_result
        })
        
    except Exception as e:
        logger.error(f"Error linking conversation to contact: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)