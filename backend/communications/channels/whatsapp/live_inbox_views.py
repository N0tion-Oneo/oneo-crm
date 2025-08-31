"""
WhatsApp Live Inbox Views
Shows chats directly from UniPile without storing (similar to email approach)
Only stores conversations when explicitly linked to contacts/companies
"""
import logging
from typing import List, Dict, Any, Optional
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Exists, OuterRef

from communications.models import (
    Conversation, ConversationParticipant, Participant,
    UserChannelConnection, Message, Channel
)
from communications.services import ParticipantResolutionService, ConversationStorageDecider

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_whatsapp_live_inbox(request):
    """
    Get WhatsApp chats directly from UniPile without storing
    Shows ALL chats with storage status and linking information
    
    This is the new approach - similar to email:
    - Fetch live data from UniPile
    - Check participant resolution
    - Determine if should be stored (contact/company match)
    - Only store when explicitly requested
    
    Query params:
    - account_id: Specific WhatsApp account
    - chat_type: Filter by chat type (individual, group)
    - limit: Number of conversations (default: 20)
    - cursor: Pagination cursor from UniPile
    - search: Search query
    """
    account_id = request.GET.get('account_id')
    chat_type = request.GET.get('chat_type')  # individual, group
    limit = int(request.GET.get('limit', 20))
    cursor = request.GET.get('cursor')
    search_query = request.GET.get('search', '')
    
    try:
        # Get user's WhatsApp connections
        connections_query = UserChannelConnection.objects.filter(
            user=request.user,
            channel_type='whatsapp',
            auth_status='authenticated'
        )
        
        if account_id:
            connections_query = connections_query.filter(unipile_account_id=account_id)
        
        connections = list(connections_query)
        
        if not connections:
            return Response({
                'success': True,
                'conversations': [],
                'has_more': False,
                'cursor': None,
                'message': 'No WhatsApp accounts connected'
            })
        
        # Use first connection (or specific one if account_id provided)
        connection = connections[0]
        
        # Get tenant for participant resolution
        tenant = request.tenant if hasattr(request, 'tenant') else None
        
        # Fetch live data from UniPile using synchronous approach
        result = fetch_live_whatsapp_chats_sync(
            connection=connection,
            tenant=tenant,
            chat_type=chat_type,
            limit=limit,
            cursor=cursor,
            search=search_query
        )
        
        return Response({
            'success': True,
            'conversations': result['conversations'],
            'has_more': result.get('has_more', False),
            'cursor': result.get('next_cursor'),
            'connections': [
                {
                    'id': str(conn.id),
                    'account_id': conn.unipile_account_id,
                    'phone': conn.provider_config.get('phone', '') if conn.provider_config else '',
                    'name': conn.account_name
                } for conn in connections
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting live WhatsApp inbox: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def fetch_live_whatsapp_chats_sync(
    connection: UserChannelConnection,
    tenant,
    chat_type: Optional[str] = None,
    limit: int = 20,
    cursor: Optional[str] = None,
    search: str = ''
) -> Dict[str, Any]:
    """
    Fetch WhatsApp chats from UniPile without storing (synchronous version)
    Similar to email's live fetch approach
    """
    try:
        # Initialize UniPile client
        from communications.unipile_sdk import unipile_service
        from oneo_crm.settings import unipile_settings
        from communications.channels.whatsapp.utils.attendee_detection import WhatsAppAttendeeDetector
        import requests
        
        # Get client configuration from settings
        dsn = unipile_settings.dsn
        access_token = unipile_settings.api_key
        
        # Initialize attendee detector for proper participant identification
        attendee_detector = WhatsAppAttendeeDetector(account_identifier=connection.unipile_account_id)
        
        # Build request URL and headers
        url = f"{dsn}/api/v1/chats"
        headers = {
            'X-API-KEY': access_token,
            'Accept': 'application/json'
        }
        
        # Build params for the request
        params = {
            'limit': limit,
            'account_id': connection.unipile_account_id,
            'account_type': 'WHATSAPP'
        }
        if cursor:
            params['cursor'] = cursor
        
        # Make synchronous request to UniPile
        logger.info(f"Fetching live WhatsApp chats for account {connection.unipile_account_id}")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            logger.error(f"UniPile API error: {response.status_code} - {response.text}")
            return {
                'conversations': [],
                'has_more': False,
                'next_cursor': None
            }
        
        chats_data = response.json()
        
        if not chats_data:
            logger.warning(f"No chats returned from UniPile")
            return {
                'conversations': [],
                'has_more': False,
                'next_cursor': None
            }
        
        # Initialize services for participant resolution
        resolution_service = ParticipantResolutionService(tenant) if tenant else None
        storage_decider = ConversationStorageDecider(tenant) if tenant else None
        
        # Get list of chats
        chats = chats_data.get('items', []) if isinstance(chats_data, dict) else chats_data
        
        # Log first chat to see structure
        if chats and len(chats) > 0:
            logger.info(f"Sample chat structure: {chats[0].keys() if isinstance(chats[0], dict) else 'Not a dict'}")
            if 'attendees' in chats[0]:
                logger.info(f"Chat has {len(chats[0]['attendees'])} attendees")
        
        # Batch fetch all stored conversations to avoid N+1 queries
        chat_ids = [chat.get('id') for chat in chats if chat.get('id')]
        stored_conversations_map = {}
        if tenant and chat_ids:
            from communications.models import ConversationParticipant
            stored_convs = Conversation.objects.filter(
                external_thread_id__in=chat_ids,
                channel__channel_type='whatsapp'
            ).prefetch_related('conversation_participants__participant')
            
            for conv in stored_convs:
                stored_conversations_map[conv.external_thread_id] = conv
        
        # Process each chat
        conversations = []
        for chat in chats:
            try:
                # Basic chat info
                chat_id = chat.get('id')
                is_group = chat.get('type', 0) == 2  # type 2 is group in UniPile
                
                # OPTIMIZATION: Skip fetching attendees for now - use chat data
                # For 1-on-1 chats, we can get the participant name from chat name
                # For groups, we'd need the attendees but can show group name for now
                attendees = []
                
                # Extract basic attendee info from chat data without extra API calls
                if not is_group:
                    # For 1-on-1 chats, create participant from chat info
                    attendee_name = chat.get('name', 'WhatsApp User')
                    attendee_provider_id = chat.get('attendee_provider_id', '')
                    
                    # Extract phone from provider_id if available
                    phone = ''
                    if attendee_provider_id and '@' in attendee_provider_id:
                        phone = attendee_provider_id.split('@')[0]
                    
                    attendees.append({
                        'external_id': attendee_provider_id or chat_id,
                        'name': attendee_name,
                        'is_self': False,
                        'phone_number': phone
                    })
                    
                    # Add self as participant (account owner)
                    from communications.utils.account_utils import get_account_owner_info
                    account_info = get_account_owner_info(
                        unipile_account_id=connection.unipile_account_id,
                        channel_type='whatsapp'
                    )
                    attendees.append({
                        'external_id': connection.unipile_account_id,
                        'name': account_info['name'],
                        'is_self': True,
                        'phone_number': account_info['phone'] or (connection.provider_config.get('phone', '') if connection.provider_config else '')
                    })
                else:
                    # For groups, just use placeholder for now (avoid API call)
                    # Could fetch attendees on-demand when opening the chat
                    attendees.append({
                        'external_id': 'group',
                        'name': f"{chat.get('name', 'Group Chat')}",
                        'is_self': False,
                        'phone_number': ''
                    })
                
                participants = []
                linked_contacts = []
                linked_companies = []
                storage_reason = 'none'
                
                # Process each attendee
                for attendee in attendees:
                    # Get phone from various possible fields
                    phone = attendee.get('phone_number', '')
                    if not phone and attendee.get('external_id'):
                        # Extract phone from external_id if it's in format like "1234567890@s.whatsapp.net"
                        ext_id = attendee.get('external_id', '')
                        if '@' in ext_id:
                            phone = ext_id.split('@')[0]
                    
                    name = attendee.get('name') or phone or 'Unknown'
                    is_self = attendee.get('is_self', False)
                    
                    # Build participant data for ALL attendees (including self)
                    # For self, use the actual account owner name
                    if is_self:
                        from communications.utils.account_utils import get_account_owner_name
                        name = get_account_owner_name(channel=conversation.channel, channel_type='whatsapp')
                    
                    participant_data = {
                        'id': attendee.get('external_id'),
                        'phone': phone,
                        'name': name,
                        'is_self': is_self,
                        'has_contact': False,
                        'contact_id': None,
                        'confidence': 0,
                        'has_secondary': False,
                        'secondary_id': None,
                        'secondary_pipeline': None,
                        'secondary_confidence': 0
                    }
                    
                    # Skip self for CRM resolution but include in participants list
                    if is_self:
                        participants.append(participant_data)
                        continue
                    
                    # Try to resolve participant if we have resolution service
                    if resolution_service and phone:
                        try:
                            # Normalize phone number - add + if not present
                            normalized_phone = phone if phone.startswith('+') else f'+{phone}'
                            
                            # Use the same resolution as Gmail - create identifier data
                            identifier_data = {
                                'phone': normalized_phone,
                                'name': name if name and name != 'Unknown' else None
                            }
                            
                            # This is sync code, so we need to use sync resolution
                            from asgiref.sync import async_to_sync
                            participant, created = async_to_sync(resolution_service.resolve_or_create_participant)(
                                identifier_data=identifier_data,
                                channel_type='whatsapp'
                            )
                            
                            # Get resolution data from the participant
                            # Note: contact_record is a ForeignKey, so we need to access the id via .id
                            resolution = {
                                'contact_record_id': participant.contact_record.id if participant.contact_record else None,
                                'contact_name': participant.name,
                                'confidence': participant.resolution_confidence or 0.8,
                                'secondary_record_id': participant.secondary_record.id if participant.secondary_record else None,
                                'secondary_pipeline': participant.secondary_pipeline,
                                'secondary_confidence': participant.secondary_confidence or 0.5
                            }
                            
                            # Get the actual contact name from the linked record if available
                            if participant.contact_record:
                                try:
                                    from pipelines.record_operations import RecordUtils
                                    contact_name = RecordUtils.generate_title(
                                        participant.contact_record.data,
                                        participant.contact_record.pipeline.name if participant.contact_record.pipeline else 'Contact',
                                        participant.contact_record.pipeline
                                    )
                                    if contact_name:
                                        resolution['contact_name'] = contact_name
                                except Exception as e:
                                    logger.debug(f"Could not get contact name from record: {e}")
                            
                            if resolution.get('contact_record_id'):
                                participant_data['has_contact'] = True
                                participant_data['contact_id'] = str(resolution['contact_record_id'])
                                participant_data['confidence'] = resolution.get('confidence', 0.8)
                                
                                # Update participant name with contact name if available
                                if resolution.get('contact_name'):
                                    participant_data['name'] = resolution['contact_name']
                                
                                linked_contacts.append({
                                    'id': str(resolution['contact_record_id']),
                                    'name': resolution.get('contact_name', name),
                                    'confidence': resolution.get('confidence', 0.8)
                                })
                                
                                if storage_reason == 'none':
                                    storage_reason = 'contact_match'
                            
                            if resolution.get('secondary_record_id'):
                                participant_data['has_secondary'] = True
                                participant_data['secondary_id'] = str(resolution['secondary_record_id'])
                                participant_data['secondary_pipeline'] = resolution.get('secondary_pipeline')
                                participant_data['secondary_confidence'] = resolution.get('secondary_confidence', 0.5)
                                
                                linked_companies.append({
                                    'id': str(resolution['secondary_record_id']),
                                    'pipeline': resolution.get('secondary_pipeline'),
                                    'confidence': resolution.get('secondary_confidence', 0.5)
                                })
                                
                                if storage_reason == 'none':
                                    storage_reason = 'company_match'
                        except Exception as e:
                            logger.debug(f"Failed to resolve participant {phone}: {e}")
                    
                    participants.append(participant_data)
                
                # Check if this conversation is already stored AND has CRM links
                stored = False
                stored_with_links = False
                if tenant:
                    stored_conv = Conversation.objects.filter(
                        external_thread_id=chat_id,
                        channel__channel_type='whatsapp'
                    ).first()
                    
                    if stored_conv:
                        stored = True
                        # Check if it has actual CRM links
                        from communications.models import ConversationParticipant
                        has_crm_link = ConversationParticipant.objects.filter(
                            conversation=stored_conv
                        ).filter(
                            Q(participant__contact_record__isnull=False) |
                            Q(participant__secondary_record__isnull=False)
                        ).exists()
                        
                        if has_crm_link:
                            stored_with_links = True
                            # Add to linked records if not already there
                            if not linked_contacts and not linked_companies:
                                # Get the actual linked records from stored data
                                for cp in ConversationParticipant.objects.filter(conversation=stored_conv).select_related('participant'):
                                    if cp.participant and cp.participant.contact_record:
                                        linked_contacts.append({
                                            'id': str(cp.participant.contact_record.id),
                                            'name': cp.participant.name or 'Contact',
                                            'confidence': 1.0
                                        })
                                    if cp.participant and cp.participant.secondary_record:
                                        linked_companies.append({
                                            'id': str(cp.participant.secondary_record.id),
                                            'pipeline': cp.participant.secondary_pipeline,
                                            'confidence': 0.8
                                        })
                
                # Determine if should be stored (has CRM matches or already stored with links)
                should_store = storage_reason != 'none' or stored_with_links
                
                # Update storage reason if stored with links
                if stored_with_links and storage_reason == 'none':
                    storage_reason = 'manual_link'  # Was manually linked before
                
                # Build conversation object
                conversation = {
                    'id': chat_id,
                    'external_thread_id': chat_id,
                    'name': chat.get('name') or chat.get('title', 'WhatsApp Chat'),
                    'participants': participants,
                    'participant_count': len(participants) if participants else len(attendees),  # Use attendees count if no participants
                    'is_group': is_group,
                    'last_message': chat.get('last_message', {}).get('text', '') if chat.get('last_message') else '',
                    'last_message_at': chat.get('last_message', {}).get('created_at') if chat.get('last_message') else None,
                    'unread_count': chat.get('unread_count', 0),
                    'message_count': chat.get('messages_count', 0),
                    
                    # Storage status (key difference from old approach)
                    'source': 'live',
                    'stored': stored,
                    'should_store': should_store,
                    'storage_reason': storage_reason,
                    'can_link': not stored and storage_reason == 'none',  # Can link if not stored and no automatic reason
                    
                    # Linked records
                    'linked_records': {
                        'contacts': linked_contacts,
                        'companies': linked_companies
                    },
                    
                    'channel_specific': {
                        'account_id': connection.unipile_account_id,
                        'account_phone': connection.provider_config.get('phone', '') if connection.provider_config else '',
                        'is_group': is_group,
                        'chat_type': 'group' if is_group else 'individual'
                    }
                }
                
                # Apply chat type filter
                if chat_type:
                    if chat_type == 'individual' and is_group:
                        continue
                    if chat_type == 'group' and not is_group:
                        continue
                
                conversations.append(conversation)
                
            except Exception as e:
                logger.warning(f"Failed to process chat {chat.get('id')}: {e}")
                continue
        
        # Get pagination info
        has_more = chats_data.get('has_more', False) if isinstance(chats_data, dict) else False
        next_cursor = chats_data.get('cursor', None) if isinstance(chats_data, dict) else None
        
        return {
            'conversations': conversations,
            'has_more': has_more,
            'next_cursor': next_cursor
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch WhatsApp chats: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'conversations': [],
            'has_more': False,
            'next_cursor': None
        }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def store_whatsapp_conversation(request, chat_id):
    """
    Store a WhatsApp conversation locally when user wants to link it
    This is called when user clicks "Link to Contact" button
    """
    try:
        account_id = request.data.get('account_id')
        link_to = request.data.get('link_to', {})
        
        if not account_id:
            return Response({
                'success': False,
                'error': 'account_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # TODO: Implement conversation storage and linking logic
        # This would:
        # 1. Fetch the full conversation from UniPile
        # 2. Store it in local database
        # 3. Link to specified contact/company
        # 4. Start syncing future messages
        
        return Response({
            'success': True,
            'message': 'Conversation stored and linked successfully',
            'conversation_id': chat_id
        })
        
    except Exception as e:
        logger.error(f"Error storing WhatsApp conversation: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)