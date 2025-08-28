"""
Fast email inbox views with caching for pagination
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
from .cache_manager import EmailCacheManager

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_email_inbox_fast(request):
    """
    Get email inbox with fast caching for pagination
    """
    try:
        # Get query params
        account_id = request.GET.get('account_id')
        folder = request.GET.get('folder', 'INBOX')
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        search_query = request.GET.get('search', '')
        force_refresh = request.GET.get('refresh', 'false').lower() == 'true'
        
        logger.info(f"📧 Fast email inbox request: offset={offset}, limit={limit}, folder={folder}")
        
        # Get user's email connections
        if account_id:
            connections = UserChannelConnection.objects.filter(
                user=request.user,
                channel_type='email',
                unipile_account_id=account_id,
                is_active=True
            ).select_related('user')
        else:
            connections = UserChannelConnection.objects.filter(
                user=request.user,
                channel_type='email',
                is_active=True
            ).select_related('user')
        
        if not connections:
            return Response({
                'success': True,
                'conversations': [],
                'total': 0,
                'has_more': False,
                'connections': [],
                'cached': False
            })
        
        # For simplicity, use first connection if no specific account
        connection = connections[0]
        
        # Check cache first (unless refresh requested)
        if not force_refresh:
            cached_threads = EmailCacheManager.get_cached_threads(
                connection.unipile_account_id,
                folder,
                offset,
                limit
            )
            
            if cached_threads is not None:
                total = EmailCacheManager.get_cached_total(connection.unipile_account_id, folder) or len(cached_threads)
                logger.info(f"📧 Returning {len(cached_threads)} cached threads")
                
                return Response({
                    'success': True,
                    'conversations': cached_threads,
                    'total': total,
                    'has_more': (offset + limit) < total,
                    'connections': [{
                        'id': str(conn.id),
                        'account_id': conn.unipile_account_id,
                        'email': conn.account_name,
                        'provider': conn.channel_type
                    } for conn in connections],
                    'cached': True
                })
        
        # If not cached or refresh requested, fetch all threads and cache them
        tenant = request.tenant if hasattr(request, 'tenant') else None
        all_threads = async_to_sync(fetch_and_cache_all_threads)(
            connection=connection,
            tenant=tenant,
            folder=folder
        )
        
        # Apply search filter if provided
        if search_query:
            search_lower = search_query.lower()
            filtered_threads = []
            for thread in all_threads:
                # Check subject
                if search_lower in thread.get('subject', '').lower():
                    filtered_threads.append(thread)
                    continue
                # Check participants
                for p in thread.get('participants', []):
                    if search_lower in p.get('email', '').lower() or search_lower in p.get('name', '').lower():
                        filtered_threads.append(thread)
                        break
            all_threads = filtered_threads
        
        # Apply pagination
        total = len(all_threads)
        paginated_threads = all_threads[offset:offset + limit]
        
        logger.info(f"📧 Returning {len(paginated_threads)} threads from {total} total")
        
        return Response({
            'success': True,
            'conversations': paginated_threads,
            'total': total,
            'has_more': (offset + limit) < total,
            'connections': [{
                'id': str(conn.id),
                'account_id': conn.unipile_account_id,
                'email': conn.account_name,
                'provider': conn.channel_type
            } for conn in connections],
            'cached': False
        })
        
    except Exception as e:
        logger.error(f"Error getting fast email inbox: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def fetch_and_cache_all_threads(
    connection: UserChannelConnection,
    tenant,
    folder: str = 'INBOX',
    max_threads: int = 200
) -> List[Dict[str, Any]]:
    """
    Fetch all email threads (up to max_threads) and cache them
    """
    try:
        from communications.unipile_sdk import unipile_service
        client = unipile_service.get_client()
        from communications.unipile.clients.email import UnipileEmailClient
        email_client = UnipileEmailClient(client)
        
        resolution_service = ParticipantResolutionService(tenant)
        storage_decider = ConversationStorageDecider(tenant)
        
        all_threads = []
        cursor = None
        total_fetched = 0
        
        # Fetch in batches until we have enough
        while total_fetched < max_threads:
            batch_size = min(50, max_threads - total_fetched)
            
            logger.info(f"Fetching batch of {batch_size} emails, cursor={cursor}")
            
            result = await email_client.get_emails(
                account_id=connection.unipile_account_id,
                folder=folder,
                limit=batch_size,
                cursor=cursor
            )
            
            if not result:
                break
            
            messages = result.get('items', result.get('emails', []))
            if not messages:
                break
            
            # Group messages by thread
            thread_groups = {}
            for message in messages:
                thread_id = message.get('thread_id') or message.get('id')
                if thread_id not in thread_groups:
                    thread_groups[thread_id] = []
                thread_groups[thread_id].append(message)
            
            # Process threads
            for thread_id, thread_messages in thread_groups.items():
                # Sort messages by date
                thread_messages.sort(key=lambda m: m.get('date', ''), reverse=True)
                latest_message = thread_messages[0]
                
                # Resolve participants
                participants = []
                all_emails = set()
                
                # Collect all email addresses
                for msg in thread_messages:
                    if msg.get('from'):
                        all_emails.add(msg['from'].get('address', ''))
                    for recipient in msg.get('to', []):
                        all_emails.add(recipient.get('address', ''))
                
                # Resolve each participant
                for email in all_emails:
                    if email and email != connection.account_name:
                        participant_info = await resolution_service.resolve_participant(email)
                        participants.append(participant_info)
                
                # Determine storage status
                should_store, storage_reason = await storage_decider.should_store_conversation(
                    participants=participants,
                    channel_type='email'
                )
                
                # Build thread object
                thread = {
                    'id': thread_id,
                    'external_thread_id': thread_id,
                    'subject': latest_message.get('subject', '(no subject)'),
                    'participants': participants,
                    'stored': False,  # Will be updated based on actual storage
                    'should_store': should_store,
                    'storage_reason': storage_reason,
                    'can_link': not should_store,
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
                
                all_threads.append(thread)
            
            # Update cursor for next batch
            cursor = result.get('cursor')
            total_fetched += len(thread_groups)
            
            # If no cursor, we've reached the end
            if not cursor:
                break
        
        # Sort all threads by date
        all_threads.sort(key=lambda x: x.get('last_message_at', ''), reverse=True)
        
        # Cache the threads
        EmailCacheManager.cache_threads(
            connection.unipile_account_id,
            all_threads,
            folder
        )
        
        logger.info(f"Fetched and cached {len(all_threads)} total threads")
        
        return all_threads
        
    except Exception as e:
        logger.error(f"Error fetching threads: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []