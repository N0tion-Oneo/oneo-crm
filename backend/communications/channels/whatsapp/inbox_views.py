"""
WhatsApp-specific inbox views
Shows ALL chats from UniPile API with storage status and linking information
"""
import logging
from typing import List, Dict, Any, Optional
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from asgiref.sync import async_to_sync, sync_to_async
from django.db.models import Q, Prefetch

from communications.models import (
    Conversation, ConversationParticipant, Participant,
    UserChannelConnection, Message, Channel
)
from communications.services import ParticipantResolutionService, ConversationStorageDecider
from communications.channels.whatsapp.service import WhatsAppService
from communications.unipile.clients.messaging import UnipileMessagingClient

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_whatsapp_inbox(request):
    """
    Get WhatsApp inbox showing ALL chats from UniPile with storage status
    
    Query params:
    - account_id: Specific WhatsApp account (optional, defaults to all)
    - chat_type: Filter by chat type (individual, group) - optional
    - limit: Number of conversations to return (default: 50)
    - offset: Pagination offset (default: 0)
    - search: Search query for filtering
    """
    account_id = request.GET.get('account_id')
    chat_type = request.GET.get('chat_type')  # individual, group
    limit = int(request.GET.get('limit', 50))
    offset = int(request.GET.get('offset', 0))
    search_query = request.GET.get('search', '')
    
    try:
        # Get user's WhatsApp connections
        connections_query = UserChannelConnection.objects.filter(
            user=request.user,
            channel_type='whatsapp',
            auth_status='authenticated'  # Changed from 'connected' to match actual status
        )
        
        if account_id:
            connections_query = connections_query.filter(unipile_account_id=account_id)
        
        connections = list(connections_query)
        
        if not connections:
            return Response({
                'success': True,
                'conversations': [],
                'total': 0,
                'has_more': False,
                'message': 'No WhatsApp accounts connected'
            })
        
        # Get tenant for participant resolution
        tenant = request.tenant if hasattr(request, 'tenant') else None
        
        # Fetch chats from UniPile for each connection
        all_conversations = []
        
        for connection in connections:
            inbox_data = async_to_sync(fetch_whatsapp_inbox)(
                connection=connection,
                tenant=tenant,
                chat_type=chat_type,
                limit=limit,
                offset=offset,
                search=search_query
            )
            all_conversations.extend(inbox_data)
        
        # Sort by date (most recent first)
        all_conversations.sort(key=lambda x: x.get('last_message_at', ''), reverse=True)
        
        # Apply pagination
        paginated_conversations = all_conversations[offset:offset + limit]
        
        return Response({
            'success': True,
            'conversations': paginated_conversations,
            'total': len(all_conversations),
            'has_more': len(all_conversations) > (offset + limit),
            'connections': [
                {
                    'id': str(conn.id),
                    'account_id': conn.unipile_account_id,
                    'phone': conn.account_phone,
                    'name': conn.account_name
                } for conn in connections
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting WhatsApp inbox: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def fetch_whatsapp_inbox(
    connection: UserChannelConnection,
    tenant,
    chat_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    search: str = ''
) -> List[Dict[str, Any]]:
    """
    Fetch WhatsApp inbox from UniPile and enhance with storage status
    """
    try:
        # Initialize services
        from communications.unipile_sdk import unipile_service
        client = unipile_service.get_client()
        whatsapp_client = UnipileMessagingClient(client)
        resolution_service = ParticipantResolutionService(tenant)
        storage_decider = ConversationStorageDecider(tenant)
        
        # Fetch chats from UniPile
        chats_data = await whatsapp_client.get_all_chats(
            account_id=connection.unipile_account_id,
            account_type='WHATSAPP',
            limit=limit,
            cursor=None  # Use cursor for pagination if needed
        )
        
        if not chats_data:
            logger.error(f"Failed to fetch WhatsApp chats")
            return []
        
        conversations = []
        chats = chats_data if isinstance(chats_data, list) else []
        
        # Process each chat
        for chat in chats:
            chat_id = chat.get('id')
            is_group = chat.get('is_group', False)
            
            # Filter by chat type if specified
            if chat_type:
                if chat_type == 'individual' and is_group:
                    continue
                elif chat_type == 'group' and not is_group:
                    continue
            
            # Extract conversation data for participant resolution
            attendees = chat.get('attendees', [])
            conversation_data = {
                'attendees': attendees
            }
            
            # Resolve participants and check storage decision
            should_store, participants = await storage_decider.should_store_conversation(
                conversation_data,
                'whatsapp'
            )
            
            # Check if conversation is already stored
            stored = await sync_to_async(
                Conversation.objects.filter(
                    external_thread_id=chat_id,
                    channel__unipile_account_id=connection.unipile_account_id
                ).exists
            )()
            
            # Build participant list with link status
            participants_data = []
            linked_contacts = []
            storage_reason = 'none'
            
            for participant in participants:
                participant_info = {
                    'id': str(participant.id),
                    'phone': participant.phone,
                    'name': participant.name or participant.phone,
                    'has_contact': bool(participant.contact_record),
                    'contact_id': str(participant.contact_record.id) if participant.contact_record else None,
                    'confidence': participant.resolution_confidence,
                    'has_secondary': bool(participant.secondary_record),
                    'secondary_id': str(participant.secondary_record.id) if participant.secondary_record else None,
                    'secondary_pipeline': participant.secondary_pipeline,
                    'secondary_confidence': participant.secondary_confidence
                }
                participants_data.append(participant_info)
                
                # Track linked records
                if participant.contact_record:
                    linked_contacts.append({
                        'id': str(participant.contact_record.id),
                        'name': participant.name,
                        'confidence': participant.resolution_confidence
                    })
                    storage_reason = 'contact_match'
            
            # Check if manually linked (would be stored but no automatic match)
            if stored and storage_reason == 'none':
                storage_reason = 'manual_link'
            
            # Get chat name/title
            chat_name = chat.get('name', '')
            if not chat_name and not is_group and attendees:
                # For individual chats, use the other person's name
                for attendee in attendees:
                    if attendee.get('phone_number') != connection.account_phone:
                        chat_name = attendee.get('name', attendee.get('phone_number', 'Unknown'))
                        break
            elif not chat_name and is_group:
                chat_name = f"Group ({len(attendees)} members)"
            
            # Build conversation object
            conversation = {
                'id': chat_id,
                'external_thread_id': chat_id,
                'subject': chat_name,
                'participants': participants_data,
                'stored': stored,
                'should_store': should_store,
                'storage_reason': storage_reason,
                'linked_records': {
                    'contacts': linked_contacts,
                    'companies': []  # WhatsApp typically doesn't have company links
                },
                'can_link': not stored and not should_store,  # Can link if not stored and no matches
                'message_count': chat.get('message_count', 0),
                'unread_count': chat.get('unread_count', 0),
                'last_message_at': chat.get('last_message_date'),
                'created_at': chat.get('created_at'),
                'channel_specific': {
                    'chat_type': 'group' if is_group else 'individual',
                    'is_group': is_group,
                    'member_count': len(attendees) if is_group else None,
                    'account_phone': connection.account_phone,
                    'account_id': connection.unipile_account_id,
                    'chat_status': chat.get('status', 'active')
                }
            }
            
            # Apply search filter if provided
            if search:
                search_lower = search.lower()
                # Check chat name
                if search_lower in chat_name.lower():
                    conversations.append(conversation)
                    continue
                # Check participant names/phones
                for p in participants_data:
                    if search_lower in p.get('name', '').lower() or search_lower in p.get('phone', '').lower():
                        conversations.append(conversation)
                        break
            else:
                conversations.append(conversation)
        
        return conversations
        
    except Exception as e:
        logger.error(f"Error fetching WhatsApp inbox for {connection.account_phone}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def link_whatsapp_conversation(request, chat_id: str):
    """
    Manually link a WhatsApp conversation to a CRM record
    
    POST /api/v1/communications/whatsapp/conversations/{chat_id}/link/
    {
        "link_to": {
            "record_type": "contact",
            "record_id": "uuid"
        },
        "participant_phone": "+1234567890"  // Which participant to link
    }
    """
    try:
        link_data = request.data.get('link_to', {})
        record_type = link_data.get('record_type')
        record_id = link_data.get('record_id')
        participant_phone = request.data.get('participant_phone')
        
        if not all([record_type, record_id, participant_phone]):
            return Response({
                'success': False,
                'error': 'Missing required fields'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create participant
        tenant = request.tenant if hasattr(request, 'tenant') else None
        resolution_service = ParticipantResolutionService(tenant)
        
        # Create manual link
        result = async_to_sync(create_manual_link)(
            chat_id=chat_id,
            participant_phone=participant_phone,
            record_type=record_type,
            record_id=record_id,
            user=request.user,
            tenant=tenant
        )
        
        if result['success']:
            return Response(result)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error linking WhatsApp conversation {chat_id}: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def create_manual_link(
    chat_id: str,
    participant_phone: str,
    record_type: str,
    record_id: str,
    user,
    tenant
):
    """
    Create a manual link between a participant and a CRM record
    This will trigger storage of the conversation
    """
    try:
        from pipelines.models import Record
        from django_tenants.utils import schema_context
        
        # Get or create participant
        resolution_service = ParticipantResolutionService(tenant)
        participant, _ = await resolution_service.resolve_or_create_participant(
            {'phone': participant_phone},
            'whatsapp'
        )
        
        # Link to the specified record
        def link_participant():
            with schema_context(tenant.schema_name if tenant else 'public'):
                record = Record.objects.get(id=record_id)
                
                if record_type == 'contact':
                    participant.contact_record = record
                    participant.resolution_confidence = 1.0  # Manual link = 100% confidence
                    participant.resolution_method = 'manual'
                elif record_type == 'company':
                    participant.secondary_record = record
                    participant.secondary_confidence = 1.0
                    participant.secondary_resolution_method = 'manual'
                    participant.secondary_pipeline = record.pipeline.name
                
                participant.save()
                
                # TODO: Trigger storage of conversation history for this chat
                # This would fetch the full conversation from UniPile and store it
                
                return True
        
        success = await sync_to_async(link_participant)()
        
        if success:
            return {
                'success': True,
                'message': f'Successfully linked {participant_phone} to {record_type}',
                'participant_id': str(participant.id),
                'record_id': record_id
            }
        else:
            return {
                'success': False,
                'error': 'Failed to create link'
            }
            
    except Record.DoesNotExist:
        return {
            'success': False,
            'error': f'Record {record_id} not found'
        }
    except Exception as e:
        logger.error(f"Error creating manual link: {e}")
        return {
            'success': False,
            'error': str(e)
        }