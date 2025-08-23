"""
WhatsApp Views with Local-First Architecture
Consolidated implementation using the new persistence layer
Combines all WhatsApp functionality with webhook-first sync strategy
"""
import logging
from django.http import JsonResponse, HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from asgiref.sync import async_to_sync
from django.utils import timezone as django_timezone

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_whatsapp_chats_local_first(request):
    """Get WhatsApp chats with local-first architecture"""
    account_id = request.GET.get('account_id')
    limit = int(request.GET.get('limit', 15))  # Default to 15 chats
    cursor = request.GET.get('cursor')
    force_sync = request.GET.get('force_sync', 'false').lower() == 'true'
    
    if not account_id:
        return Response({
            'success': False,
            'error': 'account_id parameter is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Import persistence services
        from ..services.persistence import message_sync_service
        
        # Use local-first approach for intelligent caching and sync with tenant context preservation
        from django.db import connection as db_connection
        from django_tenants.utils import schema_context
        current_schema = db_connection.schema_name
        
        async def get_conversations_with_tenant_context():
            with schema_context(current_schema):
                return await message_sync_service.get_conversations_local_first(
                    channel_type='whatsapp',
                    user_id=str(request.user.id),
                    account_id=account_id,
                    limit=limit,
                    cursor=cursor,
                    force_sync=force_sync
                )
        
        result = async_to_sync(get_conversations_with_tenant_context)()
        
        # Extract conversations from the result
        conversations = result.get('conversations', [])
        
        logger.info(f"✅ Retrieved {len(conversations)} WhatsApp conversations (force_sync: {force_sync})")
        
        return Response({
            'success': True,
            'chats': conversations,
            # Move pagination info to root level to match frontend expectations
            'has_more': result.get('has_more', False),
            'cursor': result.get('cursor'),
            'pagination': {
                'limit': limit,
                'cursor': cursor,
                'next_cursor': result.get('cursor'),
                'has_more': result.get('has_more', False),
                'total_fetched': len(conversations)
            },
            'cache_info': {
                'from_cache': not force_sync,
                'sync_triggered': force_sync,
                'source': 'local_first_persistence'
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get WhatsApp chats: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_messages_local_first(request, chat_id):
    """Get messages for a WhatsApp chat with local-first architecture"""
    limit = int(request.GET.get('limit', 50))
    cursor = request.GET.get('cursor')
    force_sync = True  # Always get fresh data for real-time messaging
    
    try:
        # Import persistence services
        from ..services.persistence import message_sync_service
        
        # Use local-first approach for messages with tenant context preservation
        from django.db import connection as db_connection
        from django_tenants.utils import schema_context
        current_schema = db_connection.schema_name
        
        async def get_messages_with_tenant_context():
            with schema_context(current_schema):
                return await message_sync_service.get_messages_local_first(
                    conversation_id=chat_id,
                    channel_type='whatsapp',
                    limit=limit,
                    cursor=cursor,
                    force_sync=force_sync
                )
        
        result = async_to_sync(get_messages_with_tenant_context)()
        
        # Extract messages from the result
        messages = result.get('messages', [])
        
        logger.info(f"✅ Retrieved {len(messages)} messages for chat {chat_id} (force_sync: {force_sync})")
        
        return Response({
            'success': True,
            'messages': messages,
            # Move pagination info to root level to match frontend expectations
            'has_more': result.get('has_more', False),
            'cursor': result.get('cursor'),
            'pagination': {
                'limit': limit,
                'cursor': cursor,
                'next_cursor': result.get('cursor'),
                'has_more': result.get('has_more', False),
                'total_fetched': len(messages)
            },
            'cache_info': {
                'from_cache': not force_sync,
                'sync_triggered': force_sync,
                'source': 'local_first_persistence'
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get messages for chat {chat_id}: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message_local_first(request, chat_id):
    """Send a WhatsApp message with optimistic updates and chat-centric approach"""
    try:
        # Import models first to avoid circular imports
        from communications.models import Channel, Conversation, Message, MessageDirection, MessageStatus, UserChannelConnection, ChatAttendee
        from communications.unipile_sdk import unipile_service
        from communications.services.conversation_naming import conversation_naming_service
        
        # Get message text (support both 'text' and 'message' field names for frontend compatibility)
        message_text = request.data.get('text') or request.data.get('message', '')
        if not message_text.strip():
            return Response({
                'success': False,
                'error': 'Message text is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        message_text = message_text.strip()
        logger.info(f"📤 Sending WhatsApp message to chat {chat_id}: '{message_text[:50]}...'")
        
        # Find the conversation by external_thread_id (chat_id from frontend)
        conversation = Conversation.objects.filter(external_thread_id=chat_id).first()
        
        if not conversation:
            # If conversation doesn't exist, try to create it using chat-centric approach
            logger.info(f"📤 Conversation not found for chat {chat_id}, attempting to create with attendee lookup")
            
            # Get user's WhatsApp connections to find the right account
            user_connections = UserChannelConnection.objects.filter(
                user=request.user,
                channel_type='whatsapp',
                is_active=True
            )
            
            if not user_connections.exists():
                return Response({
                    'success': False,
                    'error': 'No active WhatsApp account found'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Use the first active connection
            user_connection = user_connections.first()
            
            # Get or create channel
            channel, _ = Channel.objects.get_or_create(
                unipile_account_id=user_connection.unipile_account_id,
                channel_type='whatsapp',
                defaults={
                    'name': f"WhatsApp Account {user_connection.account_name or user_connection.unipile_account_id}",
                    'auth_status': 'authenticated',
                    'is_active': True,
                    'created_by': request.user
                }
            )
            
            # Try to get attendees for proper conversation naming
            try:
                client = unipile_service.get_client()
                chat_attendees_data = async_to_sync(client.request.get)(f'chats/{chat_id}/attendees')
                
                attendees_list = chat_attendees_data.get('items', []) if isinstance(chat_attendees_data, dict) else []
                
                # Store attendees in database
                chat_attendees = []
                for attendee_data in attendees_list:
                    attendee_id = attendee_data.get('id')
                    if attendee_id:
                        chat_attendee, created = ChatAttendee.objects.get_or_create(
                            external_attendee_id=attendee_id,
                            channel=channel,
                            defaults={
                                'provider_id': attendee_data.get('provider_id', ''),
                                'name': attendee_data.get('name', ''),
                                'picture_url': attendee_data.get('picture_url', ''),
                                'is_self': attendee_data.get('is_self', False),
                                'metadata': attendee_data
                            }
                        )
                        chat_attendees.append(chat_attendee)
                        
                        if created:
                            logger.info(f"✅ Created ChatAttendee {attendee_id} for outbound message chat {chat_id}")
                
                # Generate conversation name using naming service
                contact_info = {}
                first_attendee = next((a for a in attendees_list if not a.get('is_self')), None)
                if first_attendee:
                    contact_info = {
                        'name': first_attendee.get('name', ''),
                        'phone': first_attendee.get('phone', ''),
                        'profile': first_attendee
                    }
                
                conversation_name = conversation_naming_service.generate_conversation_name(
                    channel_type='whatsapp',
                    contact_info=contact_info,
                    message_content=message_text,
                    external_thread_id=chat_id
                )
                
            except Exception as attendee_error:
                logger.warning(f"Failed to fetch attendees for outbound message chat {chat_id}: {attendee_error}")
                conversation_name = f"WhatsApp Chat {chat_id[:8]}"
            
            # Create conversation with only the fields that exist in the model
            conversation = Conversation.objects.create(
                channel=channel,
                external_thread_id=chat_id,
                subject=conversation_name,  # Using subject field instead of name
                status='active',  # Using the actual field from ConversationStatus choices
                sync_status='pending',
                metadata={
                    'conversation_name': conversation_name,
                    'conversation_type': 'whatsapp',
                    'created_by_user': str(request.user.id),
                    'chat_id': chat_id
                }
            )
            logger.info(f"✅ Created conversation '{conversation_name}' for outbound message to chat {chat_id}")
        
        # Step 1: Create local message immediately (optimistic update)
        logger.info(f"🚨 ABOUT TO CREATE MESSAGE IN DATABASE - This should trigger signal")
        local_message = Message.objects.create(
            channel=conversation.channel,
            conversation=conversation,
            content=message_text,
            direction=MessageDirection.OUTBOUND,
            status=MessageStatus.PENDING,  # Initially pending
            is_local_only=True,  # Mark as local-only until sent
            sync_status='pending',
            metadata={
                'chat_id': chat_id,
                'is_optimistic': True,
                'send_attempt': 1,
                'sent_by_user': str(request.user.id)  # Store user info in metadata
            }
        )
        logger.info(f"🚨 MESSAGE CREATED IN DATABASE: {local_message.id} - Signal should have fired")
        
        logger.info(f"✅ Created local message {local_message.id} for chat {chat_id}")
        
        # Step 2: Send to UniPile API
        
        send_success = False
        external_message_id = None
        
        try:
            client = unipile_service.get_client()
            sent_message = async_to_sync(client.messaging.send_message)(
                chat_id=chat_id,
                text=message_text
            )
            
            if sent_message and sent_message.get('success', True):  # Some APIs return success flag
                # Update local message with sent status
                logger.info(f"🔄 UniPile API succeeded, updating message {local_message.id} status: PENDING → SENT")
                external_message_id = sent_message.get('id') or sent_message.get('message_id')
                local_message.status = MessageStatus.SENT
                local_message.sent_at = django_timezone.now()
                local_message.external_message_id = external_message_id
                local_message.is_local_only = False  # No longer local-only
                local_message.sync_status = 'synced'
                local_message.last_synced_at = django_timezone.now()
                local_message.metadata.update({
                    'is_optimistic': False,
                    'unipile_response': sent_message
                })
                local_message.save(update_fields=['status', 'sent_at', 'external_message_id', 'is_local_only', 'sync_status', 'last_synced_at', 'metadata'])
                
                send_success = True
                logger.info(f"✅ Message sent successfully to chat {chat_id}, external_id: {external_message_id}")
            else:
                raise Exception(f"UniPile API returned unsuccessful response: {sent_message}")
            
        except Exception as send_error:
            # Mark local message as failed
            local_message.status = MessageStatus.FAILED
            local_message.sync_status = 'failed'
            local_message.metadata.update({
                'is_optimistic': False,
                'send_error': str(send_error),
                'failed_at': django_timezone.now().isoformat()
            })
            local_message.save(update_fields=['status', 'sync_status', 'metadata'])
            
            logger.error(f"❌ Failed to send message to UniPile: {send_error}")
        
        # Prepare response data compatible with frontend expectations
        message_response = {
            'id': str(local_message.id),
            'text': local_message.content,
            'date': local_message.created_at.isoformat(),
            'status': local_message.status,
            'external_message_id': external_message_id,
            'conversation_id': str(conversation.id),
            'direction': 'out'
        }
        
        # Send real-time update via WebSocket
        try:
            from channels.layers import get_channel_layer
            
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"conversation_{conversation.id}",
                    {
                        'type': 'new_message',
                        'message': {
                            'id': str(local_message.id),
                            'content': local_message.content,
                            'direction': 'outbound',
                            'status': local_message.status,
                            'created_at': local_message.created_at.isoformat(),
                            'conversation_id': str(conversation.id)
                        }
                    }
                )
                logger.info(f"📡 Sent real-time update for outbound message {local_message.id}")
        except Exception as ws_error:
            logger.warning(f"Failed to send real-time update: {ws_error}")
        
        # Get conversation name from subject or metadata
        conversation_name = conversation.subject or conversation.metadata.get('conversation_name', f'Chat {chat_id[:8]}')
        
        if send_success:
            return Response({
                'success': True,
                'message': message_response,
                'conversation_id': str(conversation.id),
                'conversation_name': conversation_name
            })
        else:
            return Response({
                'success': False,
                'message': message_response,  # Still return message data for frontend to show failed state
                'error': 'Failed to send message via UniPile API, but message saved locally',
                'conversation_id': str(conversation.id),
                'conversation_name': conversation_name
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"❌ Failed to send message: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# CONSOLIDATED WHATSAPP FUNCTIONS FROM LEGACY whatsapp_views.py
# These functions maintain existing API contracts while using webhook-first architecture
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_whatsapp_accounts(request):
    """Get all WhatsApp account connections for the current user"""
    try:
        from ..models import UserChannelConnection
        from ..unipile_sdk import unipile_service
        
        logger.info(f"WhatsApp accounts requested by user: {request.user}")
        
        # Get WhatsApp connections for the current user
        whatsapp_connections = UserChannelConnection.objects.filter(
            user=request.user,
            channel_type='whatsapp',
            is_active=True
        ).select_related('user')
        
        accounts = []
        
        for connection in whatsapp_connections:
            # Start with basic connection data
            account_data = {
                'id': connection.unipile_account_id,
                'connection_id': str(connection.id),
                'phone': '',
                'identifier': connection.unipile_account_id or '',
                'status': connection.account_status,
                'auth_status': connection.auth_status,
                'is_business': False,
                'name': connection.account_name or 'WhatsApp Account',
                'picture_url': None,
                'created_at': connection.created_at.isoformat(),
                'updated_at': connection.updated_at.isoformat(),
                'last_sync_at': connection.last_sync_at.isoformat() if connection.last_sync_at else None
            }
            
            # Get real account status from UniPile API (webhook-first: only for active status)
            try:
                if connection.unipile_account_id and connection.account_status == 'active':
                    client = unipile_service.get_client()
                    account_info = async_to_sync(client.account.get_account)(connection.unipile_account_id)
                    
                    # Update with real UniPile data
                    account_data.update({
                        'phone': account_info.get('phone', account_data['phone']),
                        'is_business': account_info.get('is_business_account', False),
                        'status': 'active' if account_info.get('status') == 'authenticated' else 'error',
                        'name': account_info.get('name', account_data['name']),
                        'picture_url': account_info.get('profile_picture_url')
                    })
                    
            except Exception as api_error:
                logger.warning(f"Failed to get UniPile account info for {connection.id}: {api_error}")
                # Continue with basic connection data if UniPile API fails
            
            accounts.append(account_data)
        
        return Response({
            'success': True,
            'accounts': accounts,
            'total': len(accounts)
        })
        
    except Exception as e:
        logger.error(f"Failed to get WhatsApp accounts: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_chat(request, chat_id):
    """Update chat properties (mark as read, mute, archive, etc.) with webhook-first approach"""
    try:
        from ..unipile_sdk import unipile_service
        
        data = request.data
        logger.info(f"🔄 Chat update requested for {chat_id} with data: {data}")
        
        # Handle mark as read specifically (most common action)
        if 'unread_count' in data and data['unread_count'] == 0:
            account_id = data.get('account_id')
            if not account_id:
                return Response({
                    'success': False,
                    'error': 'account_id is required for marking chat as read'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Use the centralized mark_chat_as_read method
            result = async_to_sync(unipile_service.mark_chat_as_read)(
                account_id=account_id,
                chat_id=chat_id
            )
            
            if result.get('success'):
                logger.info(f"✅ UniPile API successfully marked chat {chat_id} as read")
                
                # Update local database to persist read status (webhook-first: immediate local update)
                try:
                    from ..models import Conversation, Message, MessageStatus, MessageDirection
                    
                    conversation = Conversation.objects.filter(external_thread_id=chat_id).first()
                    if conversation:
                        # Mark all inbound messages in this conversation as read
                        updated_count = Message.objects.filter(
                            conversation=conversation,
                            direction=MessageDirection.INBOUND,
                            status__in=[MessageStatus.SENT, MessageStatus.DELIVERED]
                        ).update(status=MessageStatus.READ)
                        
                        logger.info(f"✅ Marked {updated_count} local messages as read for chat {chat_id}")
                        
                except Exception as db_error:
                    logger.error(f"❌ Failed to update local database: {db_error}")
                
                return Response({
                    'success': True,
                    'message': 'Chat marked as read successfully',
                    'chat': {
                        'id': chat_id,
                        'unread_count': 0,
                        'updated': True
                    }
                })
            else:
                error_message = result.get('error', 'Unknown error')
                logger.error(f"❌ UniPile API failed to mark chat {chat_id} as read: {error_message}")
                
                return Response({
                    'success': False,
                    'error': f'Failed to mark chat as read: {error_message}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # For other actions, use generic approach
        client = unipile_service.get_client()
        response = async_to_sync(client.request.patch)(f'chats/{chat_id}', data=data)
        
        return Response({
            'success': True,
            'chat': response
        })
        
    except Exception as e:
        logger.error(f"Failed to update chat {chat_id}: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_mark_read_formats(request, chat_id):
    """Test different mark-as-read API formats to find what works with UniPile"""
    try:
        from ..unipile_sdk import unipile_service
        
        logger.info(f"🧪 Testing mark-as-read formats for chat {chat_id}")
        
        result = async_to_sync(unipile_service.test_mark_read_formats)(chat_id)
        
        return Response({
            'success': result.get('success', False),
            'chat_id': chat_id,
            'test_results': result.get('test_results', []),
            'working_formats': result.get('working_formats', []),
            'summary': {
                'total_tested': len(result.get('test_results', [])),
                'successful': len(result.get('working_formats', [])),
                'failed': len(result.get('test_results', [])) - len(result.get('working_formats', []))
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to test mark-read formats for chat {chat_id}: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_whatsapp_attendees(request):
    """Get WhatsApp chat attendees for a specific account"""
    account_id = request.GET.get('account_id')
    limit = int(request.GET.get('limit', 100))
    cursor = request.GET.get('cursor')
    
    if not account_id:
        return Response({
            'success': False,
            'error': 'account_id parameter is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from ..unipile_sdk import unipile_service, UnipileConnectionError
        from ..utils.phone_extractor import extract_whatsapp_contact_name
        
        client = unipile_service.get_client()
        
        # Get attendees from Unipile API
        attendees_data = async_to_sync(client.messaging.get_all_attendees)(
            account_id=account_id,
            limit=limit,
            cursor=cursor
        )
        
        attendees = attendees_data.get('items', [])
        transformed_attendees = []
        
        for attendee_data in attendees:
            # Extract contact name using phone extractor
            contact_name = extract_whatsapp_contact_name(attendee_data)
            
            transformed_attendee = {
                'id': attendee_data.get('id'),
                'name': contact_name or attendee_data.get('name'),
                'phone': attendee_data.get('phone'),
                'picture_url': attendee_data.get('picture_url'),
                'provider_id': attendee_data.get('provider_id'),
                'is_business_account': attendee_data.get('is_business_account', False),
                'status': attendee_data.get('status'),
                'last_seen': attendee_data.get('last_seen'),
                'account_id': account_id
            }
            
            transformed_attendees.append(transformed_attendee)
        
        return Response({
            'success': True,
            'attendees': transformed_attendees,
            'total': len(transformed_attendees),
            'cursor': attendees_data.get('cursor'),
            'has_more': attendees_data.get('has_more', False)
        })
        
    except Exception as e:
        logger.error(f"Failed to get WhatsApp attendees: {e}")
        
        # For 404 errors, account might not have attendees yet
        if "404" in str(e) or "Cannot GET" in str(e):
            return Response({
                'success': True,
                'attendees': [],
                'total': 0,
                'cursor': None,
                'has_more': False,
                'warning': f'Account {account_id} has no accessible attendees'
            })
        else:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_whatsapp_data(request):
    """Manual comprehensive synchronization trigger - fetches all attendees, chats, and messages"""
    try:
        from ..models import UserChannelConnection, Channel
        from ..services.comprehensive_sync import comprehensive_sync_service
        
        # Get all WhatsApp connections for the current user
        whatsapp_connections = UserChannelConnection.objects.filter(
            user=request.user,
            channel_type='whatsapp',
            is_active=True,
            unipile_account_id__isnull=False
        )
        
        if not whatsapp_connections.exists():
            return Response({
                'success': False,
                'error': 'No active WhatsApp connections found',
                'sync_type': 'comprehensive_sync'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        sync_results = []
        
        for connection in whatsapp_connections:
            try:
                # Get or create channel for this connection
                channel, created = Channel.objects.get_or_create(
                    unipile_account_id=connection.unipile_account_id,
                    channel_type='whatsapp',
                    defaults={
                        'name': f"WhatsApp Account {connection.account_name}",
                        'auth_status': 'authenticated',
                        'is_active': True,
                        'created_by': request.user
                    }
                )
                
                # Run comprehensive sync to get all attendees, chats, and messages
                logger.info(f"🔄 Starting comprehensive sync for WhatsApp account {connection.unipile_account_id}")
                
                # Preserve tenant context for async operation
                from django.db import connection as db_connection
                from django_tenants.utils import schema_context
                current_schema = db_connection.schema_name
                
                async def sync_with_tenant_context():
                    with schema_context(current_schema):
                        return await comprehensive_sync_service.sync_account_comprehensive(
                            channel=channel,
                            days_back=30,  # Sync 30 days of history
                            max_messages_per_chat=100,  # Limit messages per chat for reasonable sync time
                            connection=connection  # Add connection for direction detection
                        )
                
                stats = async_to_sync(sync_with_tenant_context)()
                
                # Update connection sync status
                connection.last_sync_at = django_timezone.now()
                connection.sync_error_count = 0
                connection.last_error = ''
                connection.save(update_fields=['last_sync_at', 'sync_error_count', 'last_error'])
                
                sync_results.append({
                    'account_id': connection.unipile_account_id,
                    'connection_id': str(connection.id),
                    'success': True,
                    'attendees_synced': stats.get('attendees_synced', 0),
                    'conversations_synced': stats.get('chats_synced', 0),
                    'conversations_created': stats.get('conversations_created', 0),
                    'conversations_updated': stats.get('conversations_updated', 0),
                    'messages_synced': stats.get('messages_synced', 0),
                    'errors': stats.get('errors', [])
                })
                
                logger.info(f"✅ Comprehensive sync completed for {connection.unipile_account_id}: {stats}")
                
            except Exception as sync_error:
                logger.error(f"❌ Failed to sync account {connection.unipile_account_id}: {sync_error}")
                
                connection.sync_error_count += 1
                connection.last_error = str(sync_error)
                connection.save(update_fields=['sync_error_count', 'last_error'])
                
                sync_results.append({
                    'account_id': connection.unipile_account_id,
                    'connection_id': str(connection.id),
                    'success': False,
                    'error': str(sync_error),
                    'attendees_synced': 0,
                    'conversations_synced': 0,
                    'messages_synced': 0
                })
        
        successful_syncs = sum(1 for result in sync_results if result['success'])
        total_attendees = sum(result.get('attendees_synced', 0) for result in sync_results)
        total_conversations = sum(result.get('conversations_synced', 0) for result in sync_results)
        total_messages = sum(result.get('messages_synced', 0) for result in sync_results)
        
        return Response({
            'success': True,
            'message': f'Comprehensive sync completed for {successful_syncs}/{len(sync_results)} accounts',
            'sync_results': sync_results,
            'summary': {
                'total_accounts': len(sync_results),
                'successful_syncs': successful_syncs,
                'total_attendees_synced': total_attendees,
                'total_conversations_synced': total_conversations,
                'total_messages_synced': total_messages
            },
            'sync_type': 'comprehensive_sync_with_attendees'
        })
        
    except Exception as e:
        logger.error(f"Failed to sync WhatsApp data: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_attendee_picture(request, attendee_id):
    """Get profile picture for a WhatsApp attendee"""
    try:
        from ..unipile_sdk import unipile_service
        
        if not attendee_id or attendee_id.strip() == '' or attendee_id in ['undefined', 'null', 'None']:
            return Response({
                'success': True,
                'picture_url': None,
                'picture_data': None,
                'message': 'Invalid attendee ID'
            })
        
        logger.info(f"🖼️ Fetching profile picture for attendee_id: {attendee_id}")
        
        client = unipile_service.get_client()
        picture_response = async_to_sync(client.request.get)(f'chat_attendees/{attendee_id}/picture')
        
        # Handle binary image data response
        if picture_response.get('binary_data'):
            import base64
            binary_data = picture_response['binary_data']
            base64_data = base64.b64encode(binary_data).decode('utf-8')
            
            return Response({
                'success': True,
                'picture_url': None,
                'picture_data': base64_data,
                'content_type': picture_response.get('content_type', 'image/jpeg')
            })
        
        # Handle URL-based response
        elif picture_response.get('url'):
            return Response({
                'success': True,
                'picture_url': picture_response.get('url'),
                'picture_data': None
            })
        
        # No picture data available
        else:
            return Response({
                'success': True,
                'picture_url': None,
                'picture_data': None,
                'message': 'Profile picture not available'
            })
        
    except Exception as e:
        # Check if it's a 404 error (profile not available)
        if "404" in str(e) or "Cannot GET" in str(e) or "Unknown error" in str(e):
            return Response({
                'success': True,
                'picture_url': None,
                'picture_data': None,
                'message': 'Profile picture not available'
            })
        else:
            logger.error(f"Failed to get attendee picture for {attendee_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_message_attachment(request, message_id, attachment_id):
    """Get attachment from a WhatsApp message"""
    try:
        from ..unipile_sdk import unipile_service
        
        client = unipile_service.get_client()
        
        # Get attachment via Unipile API
        attachment_response = async_to_sync(client.request.get)(f'messages/{message_id}/attachments/{attachment_id}')
        
        # Check if we got binary data or just metadata
        if attachment_response.get('data'):
            import base64
            
            attachment_data = attachment_response.get('data')
            content_type = attachment_response.get('content_type', 'application/octet-stream')
            filename = attachment_response.get('filename', f'attachment_{attachment_id}')
            
            # Decode base64 data if needed
            if isinstance(attachment_data, str):
                try:
                    binary_data = base64.b64decode(attachment_data)
                except:
                    binary_data = attachment_data.encode() if isinstance(attachment_data, str) else attachment_data
            else:
                binary_data = attachment_data
            
            # Return file as download
            response = HttpResponse(binary_data, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(binary_data)
            return response
            
        elif attachment_response.get('url'):
            # Fetch the file from the URL
            import requests
            attachment_url = attachment_response.get('url')
            
            file_response = requests.get(attachment_url)
            file_response.raise_for_status()
            
            content_type = file_response.headers.get('content-type', 'application/octet-stream')
            filename = attachment_response.get('filename', f'attachment_{attachment_id}')
            
            # Return file as download
            response = HttpResponse(file_response.content, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(file_response.content)
            return response
        else:
            return Response({
                'success': False,
                'error': 'Attachment data not available'
            }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Failed to get message attachment: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_chat_history(request, chat_id):
    """Synchronize full message history for a specific WhatsApp chat - webhook-first minimizes need"""
    try:
        from ..services.persistence import message_sync_service
        
        # Get sync parameters
        full_sync = request.data.get('full_sync', False)
        since = request.data.get('since')
        
        # In webhook-first architecture, use persistence layer for intelligent sync
        result = async_to_sync(message_sync_service.get_messages_local_first)(
            conversation_id=chat_id,
            channel_type='whatsapp',
            limit=1000,  # Large limit for full sync
            force_sync=True  # Force sync from API to fill gaps
        )
        
        return Response({
            'success': True,
            'chat_id': chat_id,
            'messages_synced': len(result.get('messages', [])),
            'full_sync': full_sync,
            'message': f'Chat history sync completed for chat {chat_id}',
            'sync_type': 'webhook_first_gap_fill'
        })
        
    except Exception as e:
        logger.error(f"Failed to sync chat history for chat {chat_id}: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_sync_status(request, chat_id):
    """Get synchronization status for a specific WhatsApp chat"""
    try:
        from ..models import Conversation, Message
        
        # In webhook-first architecture, get sync status from local database
        conversation = Conversation.objects.filter(external_thread_id=chat_id).first()
        
        if not conversation:
            return Response({
                'success': True,
                'chat_id': chat_id,
                'status': 'not_found',
                'message': 'Chat not found in local database'
            })
        
        # Get local message count and sync status
        total_messages = conversation.messages.count()
        synced_messages = conversation.messages.exclude(sync_status='pending').count()
        pending_messages = conversation.messages.filter(sync_status='pending').count()
        
        return Response({
            'success': True,
            'chat_id': chat_id,
            'status': 'synced' if pending_messages == 0 else 'partial',
            'total_messages': total_messages,
            'synced_messages': synced_messages,
            'pending_messages': pending_messages,
            'last_updated': conversation.updated_at.isoformat(),
            'sync_type': 'webhook_first_local_tracking'
        })
        
    except Exception as e:
        logger.error(f"Failed to get chat sync status for chat {chat_id}: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)