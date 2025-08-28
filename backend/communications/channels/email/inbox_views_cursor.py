"""
Email inbox views with cursor-based pagination
Fast and efficient pagination using UniPile's cursor system
"""
import logging
from typing import List, Dict, Any
from asgiref.sync import async_to_sync
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from communications.models import UserChannelConnection
from communications.services import ParticipantResolutionService, ConversationStorageDecider
from .cursor_cache import CursorCacheManager

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_email_inbox_cursor(request):
    """
    Get email inbox with cursor-based pagination for fast page navigation
    """
    try:
        # Get query params
        account_id = request.GET.get('account_id')
        folder = request.GET.get('folder', 'INBOX')
        limit = int(request.GET.get('limit', 20))
        page = int(request.GET.get('page', 1))  # Page number instead of offset
        search_query = request.GET.get('search', '')
        refresh = request.GET.get('refresh', 'false').lower() == 'true'
        
        print(f"📧 CURSOR INBOX CALLED: page={page}, limit={limit}, folder={folder}, account_id={account_id}")
        logger.info(f"📧 Cursor inbox request: page={page}, limit={limit}, folder={folder}, account_id={account_id}")
        
        # Get user's email connections (matching the working offset-based implementation)
        # Need tenant context for UserChannelConnection model
        tenant = getattr(request, 'tenant', None)
        
        if tenant:
            from django_tenants.utils import schema_context
            with schema_context(tenant.schema_name):
                connections_query = UserChannelConnection.objects.filter(
                    user=request.user,
                    channel_type__in=['gmail', 'outlook', 'mail', 'email'],  # Support all email types
                    auth_status='authenticated'  # Use auth_status instead of is_active
                )
                
                if account_id:
                    connections_query = connections_query.filter(unipile_account_id=account_id)
                    
                connections = list(connections_query)
        else:
            # Fallback to public schema
            connections_query = UserChannelConnection.objects.filter(
                user=request.user,
                channel_type__in=['gmail', 'outlook', 'mail', 'email'],  # Support all email types
                auth_status='authenticated'  # Use auth_status instead of is_active
            )
            
            if account_id:
                connections_query = connections_query.filter(unipile_account_id=account_id)
                
            connections = list(connections_query)
        logger.info(f"Found {len(connections)} email connections for user {request.user.email} (account_id={account_id})")
        
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
                'page': page,
                'total_pages': 1,
                'has_more': False,
                'connections': [],
                'message': 'Using mock data - no email accounts connected'
            })
        
        # Use first connection
        connection = connections[0]
        
        # Clear cursors if refresh requested
        if refresh:
            CursorCacheManager.clear_cursors(connection.unipile_account_id, folder)
        
        # Get cursor for this page
        cursor = CursorCacheManager.get_cursor(connection.unipile_account_id, folder, page)
        
        # Fetch emails for this page
        logger.info(f"Calling fetch_page_with_cursor with cursor={cursor[:20] if cursor else 'None'}, account={connection.unipile_account_id}")
        result = async_to_sync(fetch_page_with_cursor)(
            connection=connection,
            tenant=tenant,
            folder=folder,
            limit=limit,
            cursor=cursor,
            search=search_query
        )
        logger.info(f"fetch_page_with_cursor returned {len(result.get('conversations', []))} conversations")
        
        # Save cursor for next page if available
        if result.get('next_cursor'):
            CursorCacheManager.save_cursor(
                connection.unipile_account_id, 
                folder, 
                page,  # Save cursor AT this page position (to be used for getting next page)
                result['next_cursor']
            )
            logger.info(f"💾 Saved cursor for page {page} to fetch page {page + 1}")
        
        # Calculate total pages (estimate)
        total_pages = page + (1 if result.get('has_more') else 0)
        
        logger.info(f"📧 Returning {len(result['conversations'])} threads for page {page}")
        
        return Response({
            'success': True,
            'conversations': result['conversations'],
            'page': page,
            'total_pages': total_pages,
            'has_more': result.get('has_more', False),
            'connections': [{
                'id': str(conn.id),
                'account_id': conn.unipile_account_id,
                'email': conn.account_name,
                'provider': conn.channel_type
            } for conn in connections]
        })
        
    except Exception as e:
        logger.error(f"Error getting cursor-based email inbox: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def fetch_page_with_cursor(
    connection: UserChannelConnection,
    tenant,
    folder: str = 'INBOX',
    limit: int = 20,
    cursor: str = None,
    search: str = ''
) -> Dict[str, Any]:
    """
    Fetch a single page of emails using cursor
    """
    try:
        from communications.unipile_sdk import unipile_service
        client = unipile_service.get_client()
        from communications.unipile.clients.email import UnipileEmailClient
        email_client = UnipileEmailClient(client)
        
        resolution_service = ParticipantResolutionService(tenant)
        storage_decider = ConversationStorageDecider(tenant)
        
        logger.info(f"Fetching page with cursor: {cursor[:20] if cursor else 'None'}...")
        logger.info(f"UniPile request params: account_id={connection.unipile_account_id}, folder={folder}, limit={limit + 1}")
        
        # Fetch exactly what we need - one page
        try:
            logger.info(f"📧 Calling email_client.get_emails with params:")
            logger.info(f"  account_id={connection.unipile_account_id}")
            logger.info(f"  folder={folder}")
            logger.info(f"  limit={limit + 1}")
            logger.info(f"  cursor={cursor[:20] if cursor else None}")
            
            result = await email_client.get_emails(
                account_id=connection.unipile_account_id,
                folder=folder,
                limit=limit + 1,  # Fetch one extra to detect if there are more
                cursor=cursor
            )
            
            logger.info(f"✅ API call succeeded, got result type: {type(result)}")
            
        except Exception as api_error:
            logger.error(f"❌ Error calling UniPile API: {api_error}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'conversations': [],
                'has_more': False,
                'next_cursor': None
            }
        
        logger.info(f"UniPile raw response type: {type(result)}, keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
        
        if not result:
            logger.warning("UniPile returned empty result")
            return {
                'conversations': [],
                'has_more': False,
                'next_cursor': None
            }
        
        # UniPile returns emails in 'items' field according to documentation
        messages = result.get('items', [])
        next_cursor = result.get('cursor')
        
        logger.info(f"📧 Raw result has {len(result.get('items', []))} items")
        logger.info(f"📧 Messages extracted: {len(messages)} messages")
        logger.info(f"📧 Next cursor: {next_cursor[:20] if next_cursor else 'None'}...")
        
        # Log first message if available
        if messages:
            logger.info(f"📧 First message subject: {messages[0].get('subject')}")
            logger.info(f"📧 First message thread_id: {messages[0].get('thread_id')}")
        
        # If no messages, check if there's an error
        if not messages:
            logger.warning(f"No messages returned from UniPile. Full response: {result}")
            return {
                'conversations': [],
                'has_more': False,
                'next_cursor': None
            }
        
        # Check if we have more pages
        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]  # Trim to requested limit
        
        # Group messages by thread
        thread_groups = {}
        for message in messages:
            thread_id = message.get('thread_id') or message.get('id')
            if thread_id not in thread_groups:
                thread_groups[thread_id] = []
            thread_groups[thread_id].append(message)
        
        logger.info(f"📧 Grouped into {len(thread_groups)} threads")
        
        conversations = []
        
        # Process each thread
        for thread_id, thread_messages in thread_groups.items():
            logger.info(f"📧 Processing thread {thread_id[:20]}... with {len(thread_messages)} messages")
            # Sort messages by date
            thread_messages.sort(key=lambda m: m.get('date', ''), reverse=True)
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
            from asgiref.sync import sync_to_async
            from communications.models import Conversation
            
            def check_stored():
                with schema_context(tenant.schema_name if tenant else 'public'):
                    return Conversation.objects.filter(
                        external_thread_id=thread_id,
                        channel__unipile_account_id=connection.unipile_account_id
                    ).exists()
            
            stored = await sync_to_async(check_stored)()
            
            # Build participant list with link status
            participants_data = []
            
            # Need to access foreign keys in sync context
            def get_participant_data():
                with schema_context(tenant.schema_name if tenant else 'public'):
                    data = []
                    storage_reason = 'none'  # Initialize inside the function
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
                        
                        # Track storage reason
                        if has_contact:
                            storage_reason = 'contact_match'
                        elif has_secondary and storage_reason == 'none':
                            storage_reason = 'company_match'
                        
                        data.append(participant_info)
                    return data, storage_reason
            
            participants_data, storage_reason = await sync_to_async(get_participant_data)()
            
            # Build conversation object
            conversation = {
                'id': thread_id,
                'external_thread_id': thread_id,
                'subject': latest_message.get('subject', '(no subject)'),
                'participants': participants_data,
                'stored': stored,
                'should_store': should_store,
                'storage_reason': storage_reason,
                'can_link': not should_store and not stored,
                'message_count': len(thread_messages),
                'unread_count': sum(1 for m in thread_messages if not m.get('is_read', False)),
                'last_message_at': latest_message.get('date'),
                'created_at': thread_messages[-1].get('date') if thread_messages else None,
                'channel_specific': {
                    'folder': folder,
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
                # Check participants
                for p in participants:
                    if search_lower in p.get('email', '').lower() or search_lower in p.get('name', '').lower():
                        conversations.append(conversation)
                        break
            else:
                conversations.append(conversation)
        
        logger.info(f"📧 Returning {len(conversations)} conversations")
        logger.info(f"📧 has_more={has_more}, next_cursor={next_cursor[:20] if next_cursor else 'None'}...")
        
        return {
            'conversations': conversations,
            'has_more': has_more,
            'next_cursor': next_cursor
        }
        
    except Exception as e:
        logger.error(f"Error fetching page: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'conversations': [],
            'has_more': False,
            'next_cursor': None
        }