"""
Email API Views with Local-First Architecture
REST API endpoints for email operations
"""
import logging
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from authentication.jwt_authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework import status
from asgiref.sync import async_to_sync
from django.utils import timezone
from datetime import timedelta

from communications.models import (
    UserChannelConnection, Conversation, Message, Channel, SyncJob, SyncJobStatus, SyncJobType,
    Participant, ConversationParticipant
)
from communications.services import ParticipantResolutionService, ConversationStorageDecider
from .service import EmailService
from .sync.comprehensive import EmailComprehensiveSyncService

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_email_live_threads(request):
    """
    Get email threads directly from UniPile without storing (live data)
    Shows ALL emails regardless of contact association
    """
    account_id = request.GET.get('account_id')
    folder = request.GET.get('folder', 'INBOX')
    limit = int(request.GET.get('limit', 20))
    cursor = request.GET.get('cursor')
    
    if not account_id:
        return Response({
            'success': False,
            'error': 'account_id parameter is required',
            'threads': []
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get connection to verify user has access
        connection = UserChannelConnection.objects.filter(
            user=request.user,
            unipile_account_id=account_id
        ).first()
        
        if not connection:
            return Response({
                'success': False,
                'error': 'Email connection not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Initialize email service
        service = EmailService(account_identifier=connection.account_name)
        
        # Fetch emails directly from UniPile (pass-through)
        logger.info(f"Fetching live email threads from UniPile for account {account_id}, folder: {folder}")
        
        result = async_to_sync(service.get_emails)(
            account_id=account_id,
            folder=folder,
            limit=limit,
            cursor=cursor,
            meta_only=False  # Get full content for display
        )
        
        if isinstance(result, dict) and result.get('success'):
            # Transform UniPile emails to thread format for frontend
            threads = []
            email_groups = {}  # Group by thread_id
            
            for email in result.get('emails', []):
                thread_id = email.get('thread_id') or email.get('id')
                
                if thread_id not in email_groups:
                    email_groups[thread_id] = []
                email_groups[thread_id].append(email)
            
            # Create thread objects from grouped emails
            for thread_id, thread_emails in email_groups.items():
                # Sort emails by date (newest first)
                thread_emails.sort(key=lambda x: x.get('date', ''), reverse=True)
                latest_email = thread_emails[0]
                
                # Check participants for contact matches
                tenant = request.tenant if hasattr(request, 'tenant') else None
                resolution_service = ParticipantResolutionService(tenant)
                storage_decider = ConversationStorageDecider(tenant)
                
                # Build conversation data for participant extraction
                conversation_data = {
                    'from_attendee': latest_email.get('from_attendee') or latest_email.get('from'),
                    'to_attendees': latest_email.get('to_attendees', []) or latest_email.get('to', []),
                    'cc_attendees': latest_email.get('cc_attendees', []) or latest_email.get('cc', []),
                    'bcc_attendees': latest_email.get('bcc_attendees', []) or latest_email.get('bcc', [])
                }
                
                # Resolve participants
                should_store, participants = async_to_sync(storage_decider.should_store_conversation)(
                    conversation_data,
                    'email'
                )
                
                # Build participant display info from resolved participants
                participant_display = []
                matched_contacts = []
                
                for participant in participants:
                    participant_display.append({
                        'id': str(participant.id),
                        'email': participant.email,
                        'name': participant.name or participant.email,
                        'has_contact': bool(participant.contact_record),
                        'contact_id': str(participant.contact_record.id) if participant.contact_record else None,
                        'confidence': participant.resolution_confidence
                    })
                    
                    if participant.contact_record:
                        matched_contacts.append({
                            'participant_id': str(participant.id),
                            'contact_id': str(participant.contact_record.id),
                            'confidence': participant.resolution_confidence,
                            'email': participant.email
                        })
                
                thread = {
                    'thread_id': thread_id,
                    'external_thread_id': thread_id,
                    'subject': latest_email.get('subject', '(no subject)'),
                    'preview': latest_email.get('body_plain', '') or str(latest_email.get('body', ''))[:100],
                    'participants': participant_display,
                    'message_count': len(thread_emails),
                    'unread_count': sum(1 for e in thread_emails if not e.get('is_read', False)),
                    'latest_message': latest_email.get('date'),
                    'created_at': thread_emails[-1].get('date'),  # Oldest email
                    'updated_at': latest_email.get('date'),
                    'has_attachments': any(e.get('attachments') for e in thread_emails),
                    'is_starred': any(e.get('is_important') for e in thread_emails),
                    'folder': folder,
                    'source': 'live',  # Mark as live data
                    'stored': False,   # Not stored locally
                    'should_store': should_store,  # Whether this would be stored if processed
                    'has_contact_match': len(matched_contacts) > 0,
                    'matched_contacts': matched_contacts
                }
                threads.append(thread)
            
            return Response({
                'success': True,
                'threads': threads,
                'cursor': result.get('cursor'),
                'has_more': bool(result.get('cursor')),
                'total': len(threads),
                'source': 'unipile_live',
                'cached': False
            })
        else:
            error_msg = result.get('error', 'Failed to fetch emails') if isinstance(result, dict) else 'Invalid response'
            return Response({
                'success': False,
                'error': error_msg,
                'threads': []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"Failed to get live email threads: {e}")
        return Response({
            'success': False,
            'error': str(e),
            'threads': []
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_merged_email_threads(request):
    """
    Get merged email threads - combines stored (contact-linked) and live (unlinked) data
    Provides a unified view of all communications
    """
    account_id = request.GET.get('account_id')
    folder = request.GET.get('folder', 'INBOX')
    limit = int(request.GET.get('limit', 20))
    offset = int(request.GET.get('offset', 0))
    
    if not account_id:
        return Response({
            'success': False,
            'error': 'account_id parameter is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get connection
        connection = UserChannelConnection.objects.filter(
            user=request.user,
            unipile_account_id=account_id
        ).first()
        
        if not connection:
            return Response({
                'success': False,
                'error': 'Email connection not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        merged_threads = []
        seen_thread_ids = set()
        
        # 1. Get stored threads (contact-linked)
        stored_conversations = Conversation.objects.filter(
            channel__unipile_account_id=account_id,
            primary_contact_record__isnull=False  # Only conversations with linked contacts
        ).select_related('channel', 'primary_contact_record').prefetch_related(
            'messages', 'conversation_attendees__attendee'
        ).order_by('-updated_at')[offset:offset+limit]
        
        for conv in stored_conversations:
            seen_thread_ids.add(conv.external_thread_id)
            
            latest_message = conv.messages.order_by('-created_at').first()
            
            # Build participants list from attendees
            participants = []
            for ca in conv.conversation_attendees.all():
                participants.append({
                    'email': ca.attendee.email or '',
                    'name': ca.attendee.name or ''
                })
            
            # If no attendees, try to extract from metadata or messages
            if not participants and conv.metadata and 'participants' in conv.metadata:
                participants = conv.metadata['participants']
            elif not participants and latest_message:
                # Try to build from message metadata
                if latest_message.metadata:
                    sender = latest_message.metadata.get('from_email', '')
                    if sender:
                        participants.append({'email': sender, 'name': latest_message.metadata.get('sender_name', '')})
                    for to_email in latest_message.metadata.get('to_attendees', []):
                        participants.append({'email': to_email, 'name': ''})
            
            thread = {
                'id': str(conv.id),
                'thread_id': conv.external_thread_id or str(conv.id),
                'conversation_id': str(conv.id),
                'subject': conv.subject or '(no subject)',
                'preview': latest_message.content[:100] if latest_message else '',
                'participants': participants,
                'message_count': conv.messages.count(),
                'unread_count': conv.unread_count,
                'last_message_at': latest_message.created_at.isoformat() if latest_message else None,
                'created_at': conv.created_at.isoformat(),
                'updated_at': conv.updated_at.isoformat(),
                'has_attachments': any(m.metadata.get('has_attachments') for m in conv.messages.all() if m.metadata),
                'folder': folder,
                'source': 'stored',
                'stored': True,
                'contact_linked': True,
                'contact_confidence': 1.0,
                'contact_id': str(conv.primary_contact_record.id) if conv.primary_contact_record else None,
                'contact_name': conv.primary_contact_record.data.get('name', '') if conv.primary_contact_record else None
            }
            merged_threads.append(thread)
        
        # 2. Get live threads to fill remaining slots
        remaining_limit = limit - len(merged_threads)
        
        if remaining_limit > 0:
            # Fetch live threads from UniPile
            service = EmailService(account_identifier=connection.account_name)
            
            live_result = async_to_sync(service.get_emails)(
                account_id=account_id,
                folder=folder,
                limit=remaining_limit * 2,  # Fetch extra to account for duplicates
                meta_only=True  # Faster for listing
            )
            
            if live_result.get('success'):
                # Process live emails, skip if already in stored
                for email in live_result.get('emails', []):
                    thread_id = email.get('thread_id') or email.get('id')
                    
                    if thread_id in seen_thread_ids:
                        continue  # Skip duplicates
                    
                    # Check contact resolution for UI indication - check ALL participants
                    from communications.resolution_gateway_v3 import get_resolution_gateway
                    
                    # Get tenant from request
                    tenant = request.tenant if hasattr(request, 'tenant') else None
                    gateway = get_resolution_gateway(tenant)
                    
                    # Collect all participants to check for matches
                    all_matches = []
                    participants_to_check = []
                    
                    # Add FROM participant
                    from_data = email.get('from_attendee') or email.get('from', {})
                    if from_data and from_data.get('identifier'):
                        participants_to_check.append({
                            'email': from_data.get('identifier'),
                            'name': from_data.get('display_name', ''),
                            'role': 'from'
                        })
                    
                    # Add TO participants
                    for to in (email.get('to_attendees', []) or email.get('to', [])):
                        if to.get('identifier'):
                            participants_to_check.append({
                                'email': to.get('identifier'),
                                'name': to.get('display_name', ''),
                                'role': 'to'
                            })
                    
                    # Add CC participants
                    for cc in (email.get('cc_attendees', []) or email.get('cc', [])):
                        if cc.get('identifier'):
                            participants_to_check.append({
                                'email': cc.get('identifier'),
                                'name': cc.get('display_name', ''),
                                'role': 'cc'
                            })
                    
                    # Check each participant for matches
                    for participant in participants_to_check:
                        identifiers = {
                            'email': participant['email'],
                            'name': participant['name']
                        }
                        
                        resolution = async_to_sync(gateway.resolve_contacts)(identifiers, min_confidence=0.7)
                        
                        # Add all matches from this participant
                        for match in resolution.get('matches', []):
                            # Add participant info to match
                            match['participant_email'] = participant['email']
                            match['participant_role'] = participant['role']
                            all_matches.append(match)
                    
                    # Deduplicate matches by pipeline + record_id
                    seen_records = set()
                    unique_matches = []
                    highest_confidence = 0
                    
                    for match in all_matches:
                        record_key = (match['pipeline'].id, match['record'].id)
                        if record_key not in seen_records:
                            seen_records.add(record_key)
                            unique_matches.append(match)
                            highest_confidence = max(highest_confidence, match['confidence'])
                    
                    # Build participants list properly
                    participants = []
                    from_data = email.get('from_attendee') or email.get('from', {})
                    if from_data:
                        participants.append({
                            'email': from_data.get('identifier', ''),
                            'name': from_data.get('display_name', '') or (from_data.get('identifier', '').split('@')[0] if from_data.get('identifier') else '')
                        })
                    
                    # Add recipients
                    for to in (email.get('to_attendees', []) or email.get('to', [])):
                        email_addr = to.get('identifier', '')
                        if email_addr:
                            participants.append({
                                'email': email_addr,
                                'name': to.get('display_name', '') or email_addr.split('@')[0]
                            })
                    
                    thread = {
                        'id': thread_id,  # Use thread_id as the ID for live threads
                        'thread_id': thread_id,
                        'subject': email.get('subject', '(no subject)'),
                        'preview': email.get('body_plain', '') or str(email.get('body', ''))[:100],
                        'participants': participants,
                        'message_count': 1,  # Individual email
                        'unread_count': 0 if email.get('is_read') else 1,
                        'last_message_at': email.get('date'),  # Frontend expects this field
                        'created_at': email.get('date'),
                        'updated_at': email.get('date'),
                        'has_attachments': bool(email.get('attachments')),
                        'folder': folder,
                        'source': 'live',
                        'stored': False,
                        'contact_linked': len(unique_matches) > 0,
                        'contact_confidence': highest_confidence,
                        'matched_records': [
                            {
                                'pipeline': match['pipeline'].name,
                                'pipeline_id': match['pipeline'].id,
                                'record_id': match['record'].id,
                                'confidence': match['confidence'],
                                'match_type': match['match_details'].get('match_type', 'unknown'),
                                'participant_email': match.get('participant_email'),
                                'participant_role': match.get('participant_role')
                            }
                            for match in unique_matches
                        ],
                        # Keep these for backward compatibility
                        'contact_id': str(unique_matches[0]['record'].id) if unique_matches else None,
                        'contact_name': unique_matches[0]['record'].data.get('name', '') if unique_matches else None
                    }
                    
                    merged_threads.append(thread)
                    seen_thread_ids.add(thread_id)
                    
                    if len(merged_threads) >= limit:
                        break
        
        # Sort merged threads by latest message
        merged_threads.sort(key=lambda x: x.get('latest_message', ''), reverse=True)
        
        return Response({
            'success': True,
            'threads': merged_threads[:limit],
            'total': len(merged_threads),
            'has_more': len(merged_threads) >= limit,
            'source': 'merged',
            'stored_count': len([t for t in merged_threads if t['stored']]),
            'live_count': len([t for t in merged_threads if not t['stored']])
        })
        
    except Exception as e:
        logger.error(f"Failed to get merged email threads: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_email_folders_OLD_REMOVE(request):
    """Get folders for email account - OLD VERSION TO BE REMOVED"""
    try:
        account_id = request.GET.get('account_id')
        if not account_id:
            return Response({
                'success': False,
                'error': 'account_id is required',
                'folders': []
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Debug: Log where we are
        logger.info(f"Getting folders for account_id: {account_id}")
        
        # Skip connection verification for now to avoid model issues
        # In production, you'd want to verify the user has access to this account
        
        # For now, skip UniPile integration since it's returning 404
        # The UniPile API endpoint may not be available or the account may not be properly connected
        folders = []
        
        # Check if we should try UniPile (disabled for now due to 404 errors)
        use_unipile = False  # Disabled until UniPile endpoint is confirmed working
        
        if use_unipile:
            try:
                logger.info(f"Attempting to fetch folders for account_id: {account_id}")
                
                # Create EmailService instance
                service = EmailService()
                
                # Try to get folders from UniPile via the service
                result = async_to_sync(service.get_folders)(account_id)
                
                if result and not result.get('error'):
                    # Parse UniPile response
                    if 'folders' in result:
                        for folder in result.get('folders', []):
                            folder_data = {
                                'id': folder.get('provider_id', folder.get('name', '').lower()),
                                'name': folder.get('name', ''),
                                'type': _get_folder_type(folder.get('name', '')),
                                'unread_count': folder.get('unread_count', 0),
                                'total_count': folder.get('messages_count', 0)
                            }
                            folders.append(folder_data)
                        logger.info(f"Successfully fetched {len(folders)} folders from UniPile")
                else:
                    logger.warning(f"EmailService returned error: {result.get('error') if result else 'No result'}")
                    
            except Exception as e:
                logger.warning(f"Could not fetch folders via EmailService: {e}")
                import traceback
                logger.warning(f"Traceback: {traceback.format_exc()}")
        else:
            logger.info("UniPile integration disabled, using default folders")
        
        # If no folders fetched, use defaults
        if not folders:
            logger.info("Using default folders")
            folders = [
                {'id': 'inbox', 'name': 'Inbox', 'type': 'inbox', 'unread_count': 0, 'total_count': 0},
                {'id': 'sent', 'name': 'Sent', 'type': 'sent', 'unread_count': 0, 'total_count': 0},
                {'id': 'drafts', 'name': 'Drafts', 'type': 'drafts', 'unread_count': 0, 'total_count': 0},
                {'id': 'trash', 'name': 'Trash', 'type': 'trash', 'unread_count': 0, 'total_count': 0},
                {'id': 'spam', 'name': 'Spam', 'type': 'spam', 'unread_count': 0, 'total_count': 0}
            ]
        
        logger.info(f"Returning {len(folders)} folders")
        return Response({
            'success': True,
            'folders': folders
        })
    except Exception as e:
        logger.error(f"Error getting email folders: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        # Always return folders array even on error
        return Response({
            'success': False,
            'error': str(e),
            'folders': []
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _get_folder_type(folder_name: str) -> str:
    """Helper to determine folder type from name"""
    name_lower = folder_name.lower()
    if 'inbox' in name_lower:
        return 'inbox'
    elif 'sent' in name_lower:
        return 'sent'
    elif 'draft' in name_lower:
        return 'drafts'
    elif 'trash' in name_lower or 'deleted' in name_lower:
        return 'trash'
    elif 'spam' in name_lower or 'junk' in name_lower:
        return 'spam'
    else:
        return 'custom'


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_email_accounts(request):
    """Get connected email accounts for the current user"""
    try:
        connections = UserChannelConnection.objects.filter(
            user=request.user,
            channel_type__in=['gmail', 'outlook', 'email', 'mail'],
            is_active=True
        )
        
        accounts = []
        for conn in connections:
            # Get associated channel with the most conversations
            from django.db.models import Count
            channel = Channel.objects.filter(
                channel_type=conn.channel_type,
                unipile_account_id=conn.unipile_account_id
            ).annotate(conv_count=Count('conversations')).order_by('-conv_count').first()
            
            account_data = {
                'id': str(conn.id),
                'account_id': conn.unipile_account_id,
                'provider': conn.channel_type,
                'email': conn.account_name,
                'status': 'active' if conn.is_active else 'inactive',
                'last_sync': conn.last_sync_at.isoformat() if conn.last_sync_at else None,
                'channel_id': str(channel.id) if channel else None,
                'folders': channel.sync_settings.get('folders', []) if channel and channel.sync_settings else []
            }
            accounts.append(account_data)
        
        return Response({
            'success': True,
            'accounts': accounts,
            'count': len(accounts)
        })
        
    except Exception as e:
        logger.error(f"Failed to get email accounts: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_email_threads(request):
    """Get email threads (conversations) with local-first architecture"""
    account_id = request.GET.get('account_id')
    folder = request.GET.get('folder', 'inbox')
    limit = int(request.GET.get('limit', 20))
    cursor = request.GET.get('cursor')
    force_sync = request.GET.get('force_sync', 'false').lower() == 'true'
    
    if not account_id:
        return Response({
            'success': False,
            'error': 'account_id parameter is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get user's connection
        connection = UserChannelConnection.objects.filter(
            user=request.user,
            unipile_account_id=account_id,
            channel_type__in=['gmail', 'outlook', 'email', 'mail']
        ).first()
        
        if not connection:
            return Response({
                'success': False,
                'error': 'Email connection not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get channel
        # Get channel with conversations, preferring one with the most conversations
        from django.db.models import Count
        channel = Channel.objects.filter(
            unipile_account_id=account_id,
            channel_type__in=['gmail', 'outlook', 'email', 'mail']
        ).annotate(conv_count=Count('conversations')).order_by('-conv_count').first()
        
        if not channel:
            # Create channel if it doesn't exist
            channel = Channel.objects.create(
                unipile_account_id=account_id,
                channel_type=connection.channel_type,
                name=connection.account_name or 'Email',
                auth_status='authenticated',
                is_active=True,
                created_by=request.user
            )
        
        # Get conversations from database (local-first)
        conversations_qs = Conversation.objects.filter(
            channel=channel
        )
        
        # Filter by folder if specified (skip if folder metadata not present)
        if folder and folder != 'all' and folder != 'inbox':
            # Only filter by folder if it's not inbox (default should show all)
            conversations_qs = conversations_qs.filter(
                metadata__folder=folder
            )
        
        # Order by most recent
        conversations_qs = conversations_qs.order_by('-last_message_at')
        
        # Parse cursor for pagination
        offset = 0
        if cursor:
            try:
                offset = int(cursor)
            except (ValueError, TypeError):
                offset = 0
        
        # Get paginated conversations
        conversations = list(conversations_qs[offset:offset + limit])
        
        # Format threads for response
        threads = []
        for conv in conversations:
            # Get message count and unread count
            messages_qs = Message.objects.filter(conversation=conv)
            total_messages = messages_qs.count()
            unread_messages = messages_qs.filter(
                direction='inbound',
                status__in=['sent', 'delivered']
            ).count()
            
            # Get participants from metadata
            participants = conv.metadata.get('participants', []) if conv.metadata else []
            
            thread_data = {
                'id': str(conv.id),
                'thread_id': conv.external_thread_id,
                'subject': conv.subject,
                'participants': participants,
                'message_count': total_messages,
                'unread_count': unread_messages,
                'last_message_at': conv.last_message_at.isoformat() if conv.last_message_at else None,
                'created_at': conv.created_at.isoformat() if conv.created_at else None,
                'folder': conv.metadata.get('folder', 'inbox') if conv.metadata else 'inbox',
                'has_attachments': conv.metadata.get('has_attachments', False) if conv.metadata else False
            }
            threads.append(thread_data)
        
        # Calculate next cursor
        next_cursor = None
        if len(conversations) == limit:
            next_cursor = str(offset + limit)
        
        # Trigger background sync if requested
        if force_sync:
            _trigger_background_sync(connection, channel)
        
        return Response({
            'success': True,
            'threads': threads,
            'cursor': next_cursor,
            'has_more': next_cursor is not None,
            'total': conversations_qs.count()
        })
        
    except Exception as e:
        logger.error(f"Failed to get email threads: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_thread_messages(request, thread_id):
    """Get messages in an email thread - tries stored first, then live from UniPile"""
    try:
        # First try to get stored conversation
        conversation = Conversation.objects.filter(
            external_thread_id=thread_id
        ).first()
        
        # If no stored conversation, try fetching from UniPile
        if not conversation:
            # Get account from query param
            account_id = request.GET.get('account_id')
            if not account_id:
                return Response({
                    'success': False,
                    'error': 'Account ID required for live thread'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get connection
            connection = UserChannelConnection.objects.filter(
                user=request.user,
                unipile_account_id=account_id
            ).first()
            
            if not connection:
                return Response({
                    'success': False,
                    'error': 'Email connection not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Fetch thread messages from UniPile
            service = EmailService(account_identifier=connection.account_name)
            
            # Get emails for this thread from UniPile
            # Note: UniPile API expects thread_id parameter to filter emails by thread
            result = async_to_sync(service.get_emails)(
                account_id=account_id,
                thread_id=thread_id,  # This will filter emails by thread
                limit=50  # Get up to 50 messages in the thread
            )
            
            if result.get('success'):
                messages = []
                for msg in result.get('emails', []):
                    message_data = {
                        'id': msg.get('id'),
                        'external_id': msg.get('id'),
                        'subject': msg.get('subject', ''),
                        'content': msg.get('body', '') or msg.get('body_plain', ''),  # UniPile uses 'body' for HTML and 'body_plain' for text
                        'from': msg.get('from_attendee', {}).get('identifier', ''),
                        'sender': {
                            'email': msg.get('from_attendee', {}).get('identifier', ''),
                            'name': msg.get('from_attendee', {}).get('display_name', '')
                        },
                        'recipients': {
                            'to': [r.get('identifier', '') for r in msg.get('to_attendees', [])],
                            'cc': [r.get('identifier', '') for r in msg.get('cc_attendees', [])],
                            'bcc': [r.get('identifier', '') for r in msg.get('bcc_attendees', [])]
                        },
                        'sent_at': msg.get('date'),
                        'direction': 'inbound' if msg.get('from_attendee', {}).get('identifier') != connection.account_name else 'outbound',
                        'status': 'delivered',
                        'has_attachments': bool(msg.get('attachments')),
                        'attachments': msg.get('attachments', [])
                    }
                    messages.append(message_data)
                
                return Response({
                    'success': True,
                    'messages': messages,
                    'thread': None,
                    'source': 'live'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to fetch thread from UniPile'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Check user has access to this conversation
        # For stored conversations, check if user has ANY connection to this channel type
        # This allows users to see auto-stored emails from their connected accounts
        connection = UserChannelConnection.objects.filter(
            user=request.user,
            unipile_account_id=conversation.channel.unipile_account_id
        ).exists()
        
        if not connection:
            # Also check if user has access through channel_type (for backwards compatibility)
            connection = UserChannelConnection.objects.filter(
                user=request.user,
                channel_type=conversation.channel.channel_type
            ).exists()
        
        if not connection:
            return Response({
                'success': False,
                'error': 'Access denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get messages
        messages_qs = Message.objects.filter(
            conversation=conversation
        ).order_by('sent_at', 'created_at')
        
        # Format messages
        messages = []
        for msg in messages_qs:
            message_data = {
                'id': str(msg.id),
                'external_id': msg.external_message_id,
                'subject': msg.subject or msg.metadata.get('subject', '') if msg.metadata else '',
                'content': msg.content,
                'from': msg.contact_email or msg.metadata.get('from_email', '') if msg.metadata else '',
                'sender': {
                    'email': msg.contact_email or '',
                    'name': msg.metadata.get('sender_name', '') if msg.metadata else ''
                },
                'recipients': {
                    'to': [
                        attendee.get('identifier', '') if isinstance(attendee, dict) else str(attendee)
                        for attendee in (msg.metadata.get('to_attendees', []) if msg.metadata else [])
                    ],
                    'cc': [
                        attendee.get('identifier', '') if isinstance(attendee, dict) else str(attendee)
                        for attendee in (msg.metadata.get('cc_attendees', []) if msg.metadata else [])
                    ],
                    'bcc': [
                        attendee.get('identifier', '') if isinstance(attendee, dict) else str(attendee)
                        for attendee in (msg.metadata.get('bcc_attendees', []) if msg.metadata else [])
                    ]
                },
                'sent_at': msg.sent_at.isoformat() if msg.sent_at else None,
                'direction': msg.direction,
                'status': msg.status,
                'has_attachments': bool(msg.metadata.get('attachments')) if msg.metadata else False,
                'attachments': msg.metadata.get('attachments', []) if msg.metadata else []
            }
            messages.append(message_data)
        
        return Response({
            'success': True,
            'messages': messages,
            'count': len(messages),
            'thread': {
                'id': str(conversation.id),
                'thread_id': conversation.external_thread_id,
                'subject': conversation.subject
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get thread messages: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_email(request):
    """Send a new email"""
    account_id = request.data.get('account_id')
    to = request.data.get('to', [])
    subject = request.data.get('subject', '')
    body = request.data.get('body', '')
    cc = request.data.get('cc', [])
    bcc = request.data.get('bcc', [])
    reply_to = request.data.get('reply_to_message_id') or request.data.get('reply_to')  # Support both field names
    
    if not account_id or not to or not body:
        return Response({
            'success': False,
            'error': 'account_id, to, and body are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get connection
        connection = UserChannelConnection.objects.filter(
            user=request.user,
            unipile_account_id=account_id
        ).first()
        
        if not connection:
            return Response({
                'success': False,
                'error': 'Email connection not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Initialize email service
        # Note: UserChannelConnection doesn't have a direct channel relationship
        # We'll initialize the service without a channel for now
        service = EmailService(account_identifier=connection.account_name)
        
        # Format recipients as UniPile expects (list of dicts with identifier)
        def format_recipients(emails):
            if not emails:
                return None
            if isinstance(emails, str):
                emails = [emails]
            return [{'identifier': email.strip()} for email in emails if email.strip()]
        
        to_formatted = format_recipients(to)
        cc_formatted = format_recipients(cc)
        bcc_formatted = format_recipients(bcc)
        
        # Send email
        result = async_to_sync(service.send_email)(
            account_id=account_id,
            to=to_formatted,
            subject=subject,
            body=body,
            cc=cc_formatted,
            bcc=bcc_formatted,
            reply_to=reply_to
        )
        
        if result.get('success'):
            logger.info(f"Email sent successfully with tracking_id: {result.get('tracking_id')}")
            
            # Create local message record
            # TODO: Create conversation and message records
            
            return Response({
                'success': True,
                'tracking_id': result.get('tracking_id'),
                'message': 'Email sent successfully'
            })
        else:
            return Response({
                'success': False,
                'error': result.get('error', 'Failed to send email')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_email(request, email_id):
    """Update an email (mark read/unread, move to folder)"""
    unread = request.data.get('unread')
    folders = request.data.get('folders')
    
    try:
        # Get message
        message = Message.objects.filter(
            external_message_id=email_id
        ).first()
        
        if not message:
            return Response({
                'success': False,
                'error': 'Email not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check user has access
        connection = UserChannelConnection.objects.filter(
            user=request.user,
            channel=message.conversation.channel
        ).first()
        
        if not connection:
            return Response({
                'success': False,
                'error': 'Access denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Initialize service
        service = EmailService(channel=message.conversation.channel)
        
        # Update via API
        result = async_to_sync(service.update_email)(
            email_id=email_id,
            account_id=connection.unipile_account_id,
            unread=unread,
            folders=folders
        )
        
        if result.get('success'):
            # Update local record
            if unread is not None:
                message.status = MessageStatus.DELIVERED if unread else MessageStatus.READ
            if folders:
                if not message.metadata:
                    message.metadata = {}
                message.metadata['folders'] = folders
            message.save()
            
            return Response({
                'success': True,
                'message': 'Email updated successfully'
            })
        else:
            return Response({
                'success': False,
                'error': result.get('error', 'Failed to update email')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"Failed to update email: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_email_folders(request):
    """Get email folders for an account"""
    account_id = request.GET.get('account_id')
    
    if not account_id:
        return Response({
            'success': False,
            'error': 'account_id parameter is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get connection
        connection = UserChannelConnection.objects.filter(
            user=request.user,
            unipile_account_id=account_id
        ).first()
        
        if not connection:
            return Response({
                'success': False,
                'error': 'Email connection not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Initialize service without channel since connection doesn't have that relationship
        service = EmailService(account_identifier=connection.account_name)
        
        # Fetch folders from UniPile API (now with corrected endpoint)
        logger.info(f"Fetching folders from UniPile for account {account_id}")
        result = async_to_sync(service.get_folders)(account_id)
        
        if isinstance(result, dict):
            if result.get('error'):
                logger.error(f"UniPile API error: {result.get('error')}")
                return Response({
                    'success': False,
                    'error': f"Failed to fetch folders: {result.get('error')}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Parse UniPile response - check for both 'items' and 'folders' keys
            folder_items = result.get('items', result.get('folders', []))
            
            # Transform folders to our expected format
            folders = []
            for folder in folder_items:
                folder_data = {
                    'id': folder.get('id', folder.get('provider_id', '')),
                    'name': folder.get('name', ''),
                    'role': folder.get('role', 'unknown'),  # UniPile provides role field
                    'provider_id': folder.get('provider_id', ''),
                    'nb_mails': folder.get('nb_mails', 0),
                    'account_id': folder.get('account_id', account_id)
                }
                folders.append(folder_data)
            
            logger.info(f"Successfully fetched {len(folders)} folders from UniPile")
            
            return Response({
                'success': True,
                'folders': folders,
                'cached': False
            })
        else:
            logger.error(f"Unexpected response type from UniPile: {type(result)}")
            return Response({
                'success': False,
                'error': 'Invalid response from email service'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"Failed to get email folders: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_email_data(request):
    """Trigger manual email sync"""
    account_id = request.data.get('account_id')
    sync_options = request.data.get('options', {})
    
    if not account_id:
        return Response({
            'success': False,
            'error': 'account_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get connection and channel
        connection = UserChannelConnection.objects.filter(
            user=request.user,
            unipile_account_id=account_id
        ).first()
        
        if not connection:
            return Response({
                'success': False,
                'error': 'Email connection not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get associated channel
        channel = Channel.objects.filter(
            channel_type=connection.channel_type,
            unipile_account_id=connection.unipile_account_id
        ).first()
        
        if not channel:
            return Response({
                'success': False,
                'error': 'Channel not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Create sync job
        sync_job = SyncJob.objects.create(
            user=request.user,
            channel=channel,
            job_type=SyncJobType.COMPREHENSIVE,
            status=SyncJobStatus.PENDING,
            sync_options=sync_options
        )
        
        # Trigger sync task
        from .sync.tasks import run_email_comprehensive_sync
        task = run_email_comprehensive_sync.delay(
            str(channel.id),
            str(connection.id),
            sync_options
        )
        
        # Update sync job with task ID
        sync_job.celery_task_id = task.id
        sync_job.status = SyncJobStatus.RUNNING
        sync_job.save()
        
        return Response({
            'success': True,
            'sync_job_id': str(sync_job.id),
            'task_id': task.id,
            'message': 'Email sync started'
        })
        
    except Exception as e:
        logger.error(f"Failed to start email sync: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_active_email_sync_jobs(request):
    """Get active sync jobs for email accounts"""
    try:
        # Get user's email channels
        user_channels = Channel.objects.filter(
            userchannelconnection__user=request.user,
            channel_type__in=['gmail', 'outlook', 'email', 'mail']
        ).distinct()
        
        # Get active sync jobs
        active_jobs = SyncJob.objects.filter(
            channel__in=user_channels,
            status__in=[SyncJobStatus.PENDING, SyncJobStatus.RUNNING]
        ).order_by('-created_at')
        
        jobs_data = []
        for job in active_jobs:
            job_data = {
                'id': str(job.id),
                'channel_id': str(job.channel.id),
                'channel_name': job.channel.name,
                'status': job.status,
                'job_type': job.job_type,
                'created_at': job.created_at.isoformat(),
                'celery_task_id': job.celery_task_id,
                'progress': job.progress or {}
            }
            jobs_data.append(job_data)
        
        return Response({
            'success': True,
            'jobs': jobs_data,
            'count': len(jobs_data)
        })
        
    except Exception as e:
        logger.error(f"Failed to get active sync jobs: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def link_thread_to_contact(request, thread_id):
    """Link an email thread to an existing contact"""
    try:
        contact_id = request.data.get('contact_id')
        if not contact_id:
            return Response({
                'success': False,
                'error': 'Contact ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the conversation
        conversation = Conversation.objects.filter(
            external_id=thread_id
        ).first()
        
        if not conversation:
            # Thread not stored yet, trigger sync after linking
            return Response({
                'success': False,
                'error': 'Thread not found in local storage',
                'needs_sync': True
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update the conversation with contact link
        conversation.contact_id = contact_id
        conversation.contact_linked = True
        conversation.contact_confidence = 1.0  # Manual link is 100% confidence
        conversation.save()
        
        # Update all messages in the conversation
        Message.objects.filter(conversation=conversation).update(
            contact_id=contact_id
        )
        
        return Response({
            'success': True,
            'message': 'Thread linked to contact successfully'
        })
        
    except Exception as e:
        logger.error(f"Error linking thread to contact: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def create_contact_from_thread(request, thread_id):
    """Create a new contact from email thread participants"""
    try:
        email = request.data.get('email')
        name = request.data.get('name', '')
        pipeline_id = request.data.get('pipeline_id')
        
        if not email:
            return Response({
                'success': False,
                'error': 'Email is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not pipeline_id:
            return Response({
                'success': False,
                'error': 'Pipeline ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Import here to avoid circular imports
        from pipelines.models import Pipeline, Record
        
        # Get the pipeline
        pipeline = Pipeline.objects.filter(id=pipeline_id).first()
        if not pipeline:
            return Response({
                'success': False,
                'error': 'Pipeline not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Create the record data
        record_data = {
            'email': email
        }
        
        # Add name if provided
        if name:
            # Try to find name field
            name_fields = ['name', 'full_name', 'contact_name', 'first_name']
            for field_name in name_fields:
                if pipeline.fields.filter(name=field_name).exists():
                    record_data[field_name] = name
                    break
        
        # Create the contact record
        contact = Record.objects.create(
            pipeline=pipeline,
            data=record_data,
            created_by=request.user
        )
        
        # Now link the thread to this contact
        conversation = Conversation.objects.filter(
            external_id=thread_id
        ).first()
        
        if conversation:
            conversation.contact_id = str(contact.id)
            conversation.contact_linked = True
            conversation.contact_confidence = 1.0
            conversation.save()
            
            # Update messages
            Message.objects.filter(conversation=conversation).update(
                contact_id=str(contact.id)
            )
        
        return Response({
            'success': True,
            'contact_id': str(contact.id),
            'message': 'Contact created and linked successfully'
        })
        
    except Exception as e:
        logger.error(f"Error creating contact from thread: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def sync_thread_history(request, thread_id):
    """Sync historical messages for a newly linked thread"""
    try:
        from communications.channels.email.background_sync_views import start_thread_sync
        
        # Delegate to existing thread sync functionality
        return start_thread_sync(request, thread_id)
        
    except Exception as e:
        logger.error(f"Error syncing thread history: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _trigger_background_sync(connection, channel):
    """Helper to trigger background sync"""
    try:
        from .sync.tasks import run_email_incremental_sync
        
        # Check if a sync is already running
        existing_job = SyncJob.objects.filter(
            channel=channel,
            status__in=[SyncJobStatus.PENDING, SyncJobStatus.RUNNING]
        ).exists()
        
        if not existing_job:
            # Create incremental sync job
            sync_job = SyncJob.objects.create(
                user=connection.user,
                channel=channel,
                job_type=SyncJobType.INCREMENTAL,
                status=SyncJobStatus.PENDING,
                parameters={'background': True}
            )
            
            # Trigger async task
            task = run_email_incremental_sync.delay(
                str(channel.id),
                str(connection.id),
                str(sync_job.id)
            )
            
            sync_job.celery_task_id = task.id
            sync_job.status = SyncJobStatus.RUNNING
            sync_job.save()
            
            logger.info(f"Triggered background email sync for channel {channel.id}")
            
    except Exception as e:
        logger.error(f"Failed to trigger background sync: {e}")


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_email(request, email_id):
    """
    Delete an email (move to trash in UniPile)
    
    Args:
        email_id: The email or thread ID to delete
        
    Query params:
        account_id: The UniPile account ID (required)
    """
    try:
        account_id = request.GET.get('account_id')
        
        if not account_id:
            return Response({
                'success': False,
                'error': 'account_id parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify user has access to this account
        tenant = getattr(request, 'tenant', None)
        if tenant:
            from django_tenants.utils import schema_context
            with schema_context(tenant.schema_name):
                connection = UserChannelConnection.objects.filter(
                    user=request.user,
                    unipile_account_id=account_id,
                    auth_status='authenticated'
                ).first()
        else:
            connection = UserChannelConnection.objects.filter(
                user=request.user,
                unipile_account_id=account_id,
                auth_status='authenticated'
            ).first()
        
        if not connection:
            return Response({
                'success': False,
                'error': 'You do not have access to this email account'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Delete the email using UniPile API
        from communications.unipile_sdk import unipile_service
        client = unipile_service.get_client()
        
        try:
            # Use DELETE method to move to trash
            # Pass account_id as query parameter
            params = {'account_id': account_id}
            response = async_to_sync(client._make_request)(
                'DELETE', 
                f'emails/{email_id}',
                params=params
            )
            
            logger.info(f"Successfully deleted email {email_id} for account {account_id}")
            
            return Response({
                'success': True,
                'message': 'Email moved to trash',
                'email_id': email_id
            })
            
        except Exception as api_error:
            logger.error(f"Failed to delete email {email_id}: {api_error}")
            return Response({
                'success': False,
                'error': f'Failed to delete email: {str(api_error)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Error in delete_email endpoint: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)