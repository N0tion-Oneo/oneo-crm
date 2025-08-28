"""
Email-specific inbox views
Shows ALL emails from UniPile API with storage status and linking information
"""
import logging
from typing import List, Dict, Any, Optional
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from asgiref.sync import async_to_sync, sync_to_async
from django.db.models import Q, Prefetch, Exists, OuterRef

from communications.models import (
    Conversation, ConversationParticipant, Participant,
    UserChannelConnection, Message, Channel
)
from communications.services import ParticipantResolutionService, ConversationStorageDecider
from communications.channels.email.service import EmailService
from communications.unipile.clients.email import UnipileEmailClient

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_email_inbox(request):
    """
    Get email inbox showing ALL emails from UniPile with storage status
    
    Query params:
    - account_id: Specific email account (optional, defaults to all)
    - folder: Email folder (INBOX, SENT, etc.) - default INBOX
    - limit: Number of conversations to return (default: 50)
    - offset: Pagination offset (default: 0)
    - search: Search query for filtering
    """
    account_id = request.GET.get('account_id')
    folder = request.GET.get('folder', 'INBOX')
    limit = int(request.GET.get('limit', 50))
    offset = int(request.GET.get('offset', 0))
    search_query = request.GET.get('search', '')
    
    try:
        # Log the request for debugging
        logger.info(f"Email inbox request - User: {request.user.email}, Account: {account_id}, Folder: {folder}")
        
        # Get user's email connections
        connections_query = UserChannelConnection.objects.filter(
            user=request.user,
            channel_type__in=['gmail', 'outlook', 'mail'],
            auth_status='authenticated'  # Changed from 'connected' to match actual status
        )
        
        if account_id:
            connections_query = connections_query.filter(unipile_account_id=account_id)
        
        connections = list(connections_query)
        
        logger.info(f"Found {len(connections)} email connections for user {request.user.email}")
        
        if not connections:
            # Return mock data for testing when no accounts are connected
            mock_conversations = [
                {
                    'id': 'mock-thread-1',
                    'external_thread_id': 'mock-thread-1',
                    'subject': 'Welcome to Oneo CRM!',
                    'participants': [
                        {
                            'id': 'p1',
                            'email': 'support@oneo.com',
                            'name': 'Oneo Support',
                            'has_contact': False,
                            'confidence': 0
                        }
                    ],
                    'stored': False,
                    'should_store': False,
                    'storage_reason': 'none',
                    'can_link': True,
                    'message_count': 1,
                    'unread_count': 1,
                    'last_message_at': '2024-01-15T10:00:00Z',
                    'channel_specific': {
                        'folder': 'INBOX',
                        'has_attachments': False
                    }
                },
                {
                    'id': 'mock-thread-2',
                    'external_thread_id': 'mock-thread-2',
                    'subject': 'Meeting Tomorrow',
                    'participants': [
                        {
                            'id': 'p2',
                            'email': 'john@example.com',
                            'name': 'John Doe',
                            'has_contact': True,
                            'contact_id': 'contact-123',
                            'confidence': 0.9
                        }
                    ],
                    'stored': True,
                    'should_store': True,
                    'storage_reason': 'contact_match',
                    'linked_records': {
                        'contacts': [{'id': 'contact-123', 'name': 'John Doe', 'confidence': 0.9}],
                        'companies': []
                    },
                    'can_link': False,
                    'message_count': 3,
                    'unread_count': 0,
                    'last_message_at': '2024-01-14T15:30:00Z',
                    'channel_specific': {
                        'folder': 'INBOX',
                        'has_attachments': True
                    }
                }
            ]
            
            return Response({
                'success': True,
                'conversations': mock_conversations,
                'total': 2,
                'has_more': False,
                'connections': [],
                'message': 'Using mock data - no email accounts connected'
            })
        
        # Get tenant for participant resolution
        tenant = request.tenant if hasattr(request, 'tenant') else None
        
        # Fetch emails from UniPile for each connection
        all_conversations = []
        
        # We'll fetch one extra to detect if there are more pages
        fetch_limit = limit + 1
        
        logger.info(f"📧 Email inbox request: offset={offset}, limit={limit}, folder={folder}, search={search_query}")
        
        for connection in connections:
            inbox_data = async_to_sync(fetch_email_inbox)(
                connection=connection,
                tenant=tenant,
                folder=folder,
                limit=fetch_limit,
                offset=offset,
                search=search_query
            )
            logger.info(f"📧 Fetched {len(inbox_data)} conversations from connection {connection.account_name}")
            all_conversations.extend(inbox_data)
        
        # Sort by date (most recent first)
        all_conversations.sort(key=lambda x: x.get('last_message_at', ''), reverse=True)
        
        # Check if we got more than requested
        has_more = len(all_conversations) > limit
        
        # Only return the requested amount
        conversations_to_return = all_conversations[:limit]
        
        # Estimate total - if we have more, estimate based on typical inbox size
        # Most users have between 100-500 emails in their inbox
        if has_more:
            # Conservative estimate: current position + at least 100 more
            total_estimate = max(offset + len(conversations_to_return) + 100, 200)
        else:
            # Exact count when we're on the last page
            total_estimate = offset + len(conversations_to_return)
        
        logger.info(f"📧 Email inbox response: returning {len(conversations_to_return)} conversations, total={total_estimate}, has_more={has_more}, offset={offset}")
        
        return Response({
            'success': True,
            'conversations': conversations_to_return,
            'total': total_estimate,
            'has_more': has_more,
            'connections': [
                {
                    'id': str(conn.id),
                    'account_id': conn.unipile_account_id,
                    'email': conn.account_name,  # Using account_name as it's what we have
                    'provider': conn.channel_type
                } for conn in connections
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting email inbox: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def fetch_email_inbox(
    connection: UserChannelConnection,
    tenant,
    folder: str = 'INBOX',
    limit: int = 50,
    offset: int = 0,
    search: str = ''
) -> List[Dict[str, Any]]:
    """
    Fetch email inbox from UniPile and enhance with storage status
    """
    try:
        logger.info(f"Fetching emails for account {connection.unipile_account_id} ({connection.account_name})")
        
        # Initialize services
        from communications.unipile_sdk import unipile_service
        client = unipile_service.get_client()
        email_client = UnipileEmailClient(client)
        resolution_service = ParticipantResolutionService(tenant)
        storage_decider = ConversationStorageDecider(tenant)
        
        # Fetch emails from UniPile
        try:
            # For better performance, just fetch what we need
            # UniPile typically returns threads, not individual messages
            result = await email_client.get_emails(
                account_id=connection.unipile_account_id,
                folder=folder,
                limit=limit + offset,  # Fetch enough to cover the offset
                cursor=None
            )
            logger.info(f"UniPile API called with limit={limit + offset} (offset={offset}, requested_limit={limit})")
            logger.info(f"UniPile response type: {type(result)}, keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
        except Exception as api_error:
            logger.error(f"Error calling UniPile API: {api_error}")
            return []
        
        if not result:
            logger.warning(f"Empty result from UniPile for account {connection.unipile_account_id}")
            return []
        
        conversations = []
        # The UnipileEmailClient returns the raw UniPile response
        # Check for both 'items' and 'emails' keys as UniPile might use either
        messages = result.get('items', result.get('emails', [])) if isinstance(result, dict) else []
        
        logger.info(f"Found {len(messages)} messages from UniPile (before offset slicing)")
        
        # Group messages by thread
        thread_groups = {}
        for message in messages:
            thread_id = message.get('thread_id') or message.get('id')
            if thread_id not in thread_groups:
                thread_groups[thread_id] = []
            thread_groups[thread_id].append(message)
        
        # Process each thread
        for thread_id, thread_messages in thread_groups.items():
            # Sort messages by date
            thread_messages.sort(key=lambda x: x.get('date', ''), reverse=True)
            latest_message = thread_messages[0]
            
            # Extract conversation data for participant resolution
            conversation_data = {
                'from_attendee': latest_message.get('from_attendee') or latest_message.get('from'),
                'to_attendees': latest_message.get('to_attendees', []) or latest_message.get('to', []),
                'cc_attendees': latest_message.get('cc_attendees', []) or latest_message.get('cc', []),
            }
            
            
            # Resolve participants and check storage decision
            should_store, participants = await storage_decider.should_store_conversation(
                conversation_data,
                'email'
            )
            
            # Check if conversation is already stored
            from django_tenants.utils import schema_context
            
            def check_stored():
                with schema_context(tenant.schema_name if tenant else 'public'):
                    return Conversation.objects.filter(
                        external_thread_id=thread_id,
                        channel__unipile_account_id=connection.unipile_account_id
                    ).exists()
            
            stored = await sync_to_async(check_stored)()
            
            # Build participant list with link status
            participants_data = []
            linked_contacts = []
            linked_companies = []
            storage_reason = 'none'
            
            # Need to access foreign keys in sync context
            def get_participant_data():
                with schema_context(tenant.schema_name if tenant else 'public'):
                    data = []
                    for participant in participants:
                        # Access foreign keys safely in sync context
                        has_contact = bool(participant.contact_record_id)
                        has_secondary = bool(participant.secondary_record_id)
                        
                        participant_info = {
                            'id': str(participant.id),
                            'email': participant.email,
                            'name': participant.name or participant.email,
                            'has_contact': has_contact,
                            'contact_id': str(participant.contact_record_id) if participant.contact_record_id else None,
                            'confidence': participant.resolution_confidence,
                            'has_secondary': has_secondary,
                            'secondary_id': str(participant.secondary_record_id) if participant.secondary_record_id else None,
                            'secondary_pipeline': participant.secondary_pipeline,
                            'secondary_confidence': participant.secondary_confidence
                        }
                        
                        # Add pipeline and record details if we have a contact
                        if has_contact and participant.contact_record_id:
                            try:
                                from pipelines.models import Record
                                record = Record.objects.select_related('pipeline').get(id=participant.contact_record_id)
                                participant_info['contact_pipeline'] = record.pipeline.name if record.pipeline else None
                                participant_info['contact_pipeline_id'] = str(record.pipeline.id) if record.pipeline else None
                                # Dynamically generate title using current pipeline template (like the API does)
                                from pipelines.record_operations import RecordUtils
                                record_title = RecordUtils.generate_title(
                                    record.data,
                                    record.pipeline.name,
                                    record.pipeline
                                ) or record.data.get('name') or record.data.get('email', participant.email)
                                participant_info['contact_record_name'] = record_title
                                participant_info['contact_record_title'] = record_title
                            except Exception as e:
                                logger.debug(f"Could not fetch record details: {e}")
                        
                        # Add secondary record details if we have a company
                        if has_secondary and participant.secondary_record_id:
                            try:
                                from pipelines.models import Record
                                from pipelines.record_operations import RecordUtils
                                company = Record.objects.select_related('pipeline').get(id=participant.secondary_record_id)
                                # Dynamically generate title using current pipeline template (like the API does)
                                company_title = RecordUtils.generate_title(
                                    company.data,
                                    company.pipeline.name,
                                    company.pipeline
                                ) or company.data.get('company_name') or company.data.get('name') or 'Unknown Company'
                                participant_info['secondary_record_name'] = company_title
                                participant_info['secondary_record_title'] = company_title
                            except Exception as e:
                                logger.debug(f"Could not fetch company details: {e}")
                        
                        data.append(participant_info)
                    return data
            
            participants_data = await sync_to_async(get_participant_data)()
            
            # Build linked records from participant data
            for p_data in participants_data:
                if p_data['has_contact']:
                    linked_contacts.append({
                        'id': p_data['contact_id'],
                        'name': p_data.get('contact_record_title', p_data.get('contact_record_name', p_data['name'])),
                        'title': p_data.get('contact_record_title', p_data.get('contact_record_name', p_data['name'])),
                        'confidence': p_data['confidence']
                    })
                    if storage_reason == 'none':
                        storage_reason = 'contact_match'
                
                if p_data['has_secondary']:
                    linked_companies.append({
                        'id': p_data['secondary_id'],
                        'name': p_data.get('secondary_record_title', p_data.get('secondary_record_name', 'Unknown Company')),
                        'title': p_data.get('secondary_record_title', p_data.get('secondary_record_name', 'Unknown Company')),
                        'pipeline': p_data['secondary_pipeline'],
                        'confidence': p_data['secondary_confidence']
                    })
                    if storage_reason == 'none':
                        storage_reason = 'company_match'
            
            # Check if manually linked (would be stored but no automatic match)
            if stored and storage_reason == 'none':
                storage_reason = 'manual_link'
            
            # Build conversation object
            conversation = {
                'id': thread_id,
                'external_thread_id': thread_id,
                'subject': latest_message.get('subject', '(no subject)'),
                'participants': participants_data,
                'stored': stored,
                'should_store': should_store,
                'storage_reason': storage_reason,
                'linked_records': {
                    'contacts': linked_contacts,
                    'companies': linked_companies
                },
                'can_link': not stored and not should_store,  # Can link if not stored and no matches
                'message_count': len(thread_messages),
                'unread_count': sum(1 for m in thread_messages if not m.get('is_read', False)),
                'last_message_at': latest_message.get('date'),
                'created_at': thread_messages[-1].get('date') if thread_messages else None,
                'channel_specific': {
                    'folder': folder,
                    'labels': latest_message.get('labels', []),
                    'has_attachments': any(m.get('attachments', []) for m in thread_messages),
                    'account_email': connection.account_name,
                    'account_id': connection.unipile_account_id
                }
            }
            
            # Apply search filter if provided
            if search:
                search_lower = search.lower()
                # Check subject
                if search_lower in conversation['subject'].lower():
                    conversations.append(conversation)
                    continue
                # Check participant emails/names
                for p in participants_data:
                    if search_lower in p['email'].lower() or search_lower in p['name'].lower():
                        conversations.append(conversation)
                        break
            else:
                conversations.append(conversation)
        
        # Apply offset slicing after all conversations are processed
        logger.info(f"Total conversations before offset slicing: {len(conversations)}")
        if offset > 0:
            # Skip the first 'offset' conversations
            conversations = conversations[offset:]
            logger.info(f"Applied offset={offset}, remaining conversations: {len(conversations)}")
        
        # Limit to requested amount
        conversations = conversations[:limit]
        logger.info(f"Final conversations count after limit={limit}: {len(conversations)}")
        
        return conversations
        
    except Exception as e:
        logger.error(f"Error fetching email inbox for {connection.account_name}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def link_email_conversation(request, thread_id: str):
    """
    Manually link an email conversation to a CRM record
    
    POST /api/v1/communications/email/conversations/{thread_id}/link/
    {
        "link_to": {
            "record_type": "contact|company",
            "record_id": "uuid"
        },
        "participant_email": "email@example.com"  // Which participant to link
    }
    """
    try:
        link_data = request.data.get('link_to', {})
        record_type = link_data.get('record_type')
        record_id = link_data.get('record_id')
        participant_email = request.data.get('participant_email')
        
        if not all([record_type, record_id, participant_email]):
            return Response({
                'success': False,
                'error': 'Missing required fields'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create participant
        tenant = request.tenant if hasattr(request, 'tenant') else None
        resolution_service = ParticipantResolutionService(tenant)
        
        # Create manual link
        result = async_to_sync(create_manual_link)(
            thread_id=thread_id,
            participant_email=participant_email,
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
        logger.error(f"Error linking email conversation {thread_id}: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def create_manual_link(
    thread_id: str,
    participant_email: str,
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
            {'email': participant_email},
            'email'
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
                
                # TODO: Trigger storage of conversation history for this thread
                # This would fetch the full conversation from UniPile and store it
                
                return True
        
        success = await sync_to_async(link_participant)()
        
        if success:
            return {
                'success': True,
                'message': f'Successfully linked {participant_email} to {record_type}',
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