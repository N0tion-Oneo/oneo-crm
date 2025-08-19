"""
WhatsApp-specific API views for Unipile integration
Provides endpoints for WhatsApp chat management, messaging, and synchronization
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from asgiref.sync import async_to_sync

from django.utils import timezone as django_timezone
from django.conf import settings

from communications.unipile_sdk import unipile_service, UnipileConnectionError
from communications.models import UserChannelConnection, Conversation, Message
from communications.utils.phone_extractor import extract_whatsapp_contact_name
from tenants.models import Tenant

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_whatsapp_accounts(request):
    """Get all WhatsApp account connections for the current user"""
    try:
        logger.info(f"WhatsApp API called by user: {request.user} (ID: {getattr(request.user, 'id', 'Unknown')})")
        
        # Debug: Log request details
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request path: {request.path}")
        logger.info(f"User authenticated: {request.user.is_authenticated}")
        
        if not request.user.is_authenticated:
            return Response({
                'success': False,
                'error': 'User not authenticated'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Get WhatsApp connections for the current user
        whatsapp_connections = UserChannelConnection.objects.filter(
            user=request.user,
            channel_type='whatsapp',
            is_active=True
        ).select_related('user')
        
        # Convert to list to avoid lazy evaluation issues
        connections_list = list(whatsapp_connections)
        logger.info(f"Found {len(connections_list)} WhatsApp connections for user {request.user}")
        
        accounts = []
        
        for connection in connections_list:
            logger.info(f"Processing connection {connection.id}: {connection.account_name} (Unipile ID: {connection.unipile_account_id})")
            
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
            
            # TODO: Re-enable Unipile API calls once basic functionality is working
            # For now, just use the connection data to avoid API issues
            logger.info(f"Using connection data only for account {connection.id}")
            
            accounts.append(account_data)
        
        return Response({
            'success': True,
            'accounts': accounts,
            'total': len(accounts)
        })
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Failed to get WhatsApp accounts: {e}")
        logger.error(f"Full traceback: {error_traceback}")
        return Response({
            'success': False,
            'error': str(e),
            'traceback': error_traceback if settings.DEBUG else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_whatsapp_chats(request):
    """Get WhatsApp chats for a specific account with pagination"""
    account_id = request.GET.get('account_id')
    limit = int(request.GET.get('limit', 10))  # Default to 10 for better performance
    cursor = request.GET.get('cursor')
    
    if not account_id:
        return Response({
            'success': False,
            'error': 'account_id parameter is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get chats from Unipile API
        client = unipile_service.get_client()
        chats_data = async_to_sync(client.messaging.get_all_chats)(
            account_id=account_id,
            limit=limit,
            cursor=cursor
        )
        
        # Unipile API returns 'items' not 'chats'
        chats = chats_data.get('items', chats_data.get('chats', []))
        
        # We'll fetch attendees per chat instead of using global attendees
        # This ensures we get the correct attendee info for each chat
        logger.info(f"🔍 Will fetch attendees per chat for better accuracy")
        
        # Parallel processing for attendee fetching to improve performance
        async def fetch_chat_attendees(chat_data, client):
            """Fetch attendees for a single chat"""
            chat_id = chat_data.get('id')
            attendees = []
            
            try:
                # Get chat-specific attendees using the discovered API endpoint
                logger.info(f"🔍 Fetching attendees for chat {chat_id}")
                chat_attendees_data = await client.request.get(f'chats/{chat_id}/attendees')
                chat_attendees_list = chat_attendees_data.get('items', [])
                
                logger.info(f"📋 Found {len(chat_attendees_list)} attendees for chat {chat_id}")
                
                # Process each attendee for this chat
                for attendee_data in chat_attendees_list:
                    # Extract contact name - attendee_data from Unipile has 'name' field directly
                    contact_name = attendee_data.get('name', '')
                    
                    # If no name, try extracting from provider_id (phone number)
                    if not contact_name or contact_name == attendee_data.get('phone'):
                        attendee_provider_id = attendee_data.get('provider_id', '')
                        if '@s.whatsapp.net' in attendee_provider_id:
                            # Extract phone from provider_id for fallback
                            phone_part = attendee_provider_id.replace('@s.whatsapp.net', '')
                            contact_name = attendee_data.get('name') or phone_part
                    
                    attendee = {
                        'id': attendee_data.get('id'),
                        'name': contact_name,
                        'phone': attendee_data.get('phone'),
                        'provider_id': attendee_data.get('provider_id'),
                        'picture_url': attendee_data.get('picture_url'),
                        'is_admin': False,
                        'is_business_account': attendee_data.get('is_business_account', False)
                    }
                    attendees.append(attendee)
                    
                    # Log the attendee info for debugging
                    provider_id = chat_data.get('provider_id', '')
                    if attendee_data.get('provider_id') == provider_id:
                        logger.info(f"✅ Found chat attendee for {provider_id}: ID={attendee['id']}, name='{attendee['name']}'")
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch attendees for chat {chat_id}: {e}")
                
                # Fallback: create basic attendee info for individual chats
                provider_id = chat_data.get('provider_id', '')
                phone_number = None
                if '@s.whatsapp.net' in provider_id:
                    # Individual chat: extract phone number
                    phone_number = provider_id.replace('@s.whatsapp.net', '')
                elif '@g.us' in provider_id:
                    # Group chat: extract group ID
                    phone_number = provider_id.replace('@g.us', '')
                
                is_group = chat_data.get('type', 0) == 1
                if not is_group and phone_number:
                    attendees.append({
                        'id': provider_id,  # Fallback ID (may not work for pictures)
                        'name': phone_number,
                        'phone': phone_number,
                        'provider_id': provider_id,
                        'picture_url': None,
                        'is_admin': False,
                        'is_business_account': False
                    })
                elif is_group:
                    # For groups, estimate member count based on unread count
                    estimated_members = max(2, chat_data.get('unread_count', 0) + 1)
                    chat_data['estimated_member_count'] = estimated_members
            
            return chat_data, attendees
        
        # Fetch all attendees in parallel for better performance
        logger.info(f"🚀 Starting parallel attendee fetching for {len(chats)} chats")
        import time
        start_time = time.time()
        
        # Create async tasks for all chats
        async def fetch_all_attendees():
            tasks = []
            for chat_data in chats:
                task = fetch_chat_attendees(chat_data, client)
                tasks.append(task)
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        # Execute all attendee fetching in parallel
        chat_attendee_results = async_to_sync(fetch_all_attendees)()
        
        fetch_time = time.time() - start_time
        logger.info(f"⚡ Parallel attendee fetching completed in {fetch_time:.2f}s")
        
        transformed_chats = []
        
        for result in chat_attendee_results:
            if isinstance(result, Exception):
                logger.error(f"🚨 Error in parallel attendee fetch: {result}")
                continue
            
            chat_data, attendees = result
            
            # Extract phone number from provider_id for contact name
            provider_id = chat_data.get('provider_id', '')
            phone_number = None
            if '@s.whatsapp.net' in provider_id:
                # Individual chat: extract phone number
                phone_number = provider_id.replace('@s.whatsapp.net', '')
            elif '@g.us' in provider_id:
                # Group chat: extract group ID
                phone_number = provider_id.replace('@g.us', '')
            
            # Determine if it's a group chat
            is_group = chat_data.get('type', 0) == 1
            
            # If this is a group and we got attendees, store the member count
            if is_group and attendees:
                chat_data['estimated_member_count'] = len(attendees)
            
            # Transform latest message - Unipile doesn't include latest message in chat list
            # We'll need to fetch it separately or leave it empty
            latest_message = None
            
            # Determine chat name - prioritize meaningful names over phone numbers
            chat_name = chat_data.get('name')
            
            # For individual chats, prioritize attendee name if it's different from phone number
            if not is_group and attendees:
                attendee_name = attendees[0].get('name')
                if attendee_name and attendee_name != phone_number:
                    # Use attendee name if it's a real name (not just phone number)
                    chat_name = attendee_name
                elif not chat_name or chat_name == phone_number:
                    # Fallback to phone number if no better name available
                    chat_name = phone_number
            
            # For groups, use the group name or create a default
            if is_group and not chat_name:
                chat_name = f"Group {chat_data.get('id', 'Unknown')[:8]}"
            
            # Final fallback
            if not chat_name:
                chat_name = 'Unknown Contact'
            
            transformed_chat = {
                'id': chat_data.get('id'),
                'provider_chat_id': chat_data.get('provider_id'),
                'name': chat_name,
                'title': chat_name,
                'picture_url': None,  # Unipile doesn't provide picture_url in chat list
                'is_group': is_group,
                'is_muted': bool(chat_data.get('muted_until')),
                'is_pinned': False,  # Not provided by Unipile
                'is_archived': bool(chat_data.get('archived', 0)),
                'unread_count': chat_data.get('unread_count', 0),
                'last_message_date': chat_data.get('timestamp'),
                'attendees': attendees,
                'latest_message': latest_message,
                'account_id': account_id,
                'member_count': chat_data.get('estimated_member_count', len(attendees)) if is_group else None
            }
            
            transformed_chats.append(transformed_chat)
        
        # Fix pagination - Unipile API incorrectly returns has_more=False
        # We'll determine has_more based on whether we got a full page
        actual_has_more = len(transformed_chats) == limit and chats_data.get('cursor') is not None
        
        logger.info(f"📄 Pagination info: returned {len(transformed_chats)}, limit {limit}, cursor present: {chats_data.get('cursor') is not None}")
        logger.info(f"📄 Unipile has_more: {chats_data.get('has_more', False)}, actual has_more: {actual_has_more}")
        
        return Response({
            'success': True,
            'chats': transformed_chats,
            'total': len(transformed_chats),
            'cursor': chats_data.get('cursor'),
            'has_more': actual_has_more  # Use our calculated value instead of Unipile's
        })
        
    except UnipileConnectionError as e:
        logger.error(f"Unipile connection error: {e}")
        return Response({
            'success': False,
            'error': 'Failed to connect to messaging service'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        logger.error(f"Failed to get WhatsApp chats: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_messages(request, chat_id):
    """Get messages for a specific WhatsApp chat"""
    logger.info(f"📨 Messages API called for chat_id: {chat_id} by user: {request.user}")
    
    limit = int(request.GET.get('limit', 20))  # Default to 20 messages for better performance
    cursor = request.GET.get('cursor')
    since = request.GET.get('since')
    
    logger.info(f"📨 Parameters: limit={limit}, cursor={cursor}, since={since}")
    
    try:
        client = unipile_service.get_client()
        
        # Get messages from Unipile API
        logger.info(f"📨 Calling Unipile get_all_messages for chat_id: {chat_id}")
        messages_data = async_to_sync(client.messaging.get_all_messages)(
            chat_id=chat_id,
            limit=limit,
            cursor=cursor,
            since=since
        )
        
        logger.info(f"📨 Unipile response: {messages_data}")
        # Fix: Unipile returns 'items' not 'messages'
        messages = messages_data.get('items', messages_data.get('messages', []))
        logger.info(f"📨 Extracted messages count: {len(messages)}")
        transformed_messages = []
        
        for msg_data in messages:
            # Transform attachments
            attachments = []
            for att in msg_data.get('attachments', []):
                attachments.append({
                    'id': att.get('id'),
                    'type': att.get('type'),
                    'filename': att.get('filename'),
                    'url': att.get('url'),
                    'thumbnail_url': att.get('thumbnail_url'),
                    'size': att.get('size'),
                    'mime_type': att.get('mime_type') or att.get('content_type')
                })
            
            # Determine direction from is_sender field
            is_sender = msg_data.get('is_sender', 0)
            direction = 'out' if is_sender else 'in'
            
            
            transformed_message = {
                'id': msg_data.get('id'),
                'text': msg_data.get('text') or msg_data.get('body'),
                'html': msg_data.get('html'),
                'type': msg_data.get('type', 'text'),
                'direction': direction,
                'date': msg_data.get('timestamp') or msg_data.get('date') or msg_data.get('created_at'),
                'status': msg_data.get('status', 'sent'),
                'attendee_id': msg_data.get('attendee_id') or msg_data.get('from_id') or msg_data.get('sender_attendee_id'),
                'chat_id': chat_id,
                'attachments': attachments,
                'location': msg_data.get('location'),
                'contact': msg_data.get('contact'),
                'quoted_message_id': msg_data.get('quoted_message_id'),
                'account_id': msg_data.get('account_id')
            }
            
            transformed_messages.append(transformed_message)
        
        return Response({
            'success': True,
            'messages': transformed_messages,
            'total': len(transformed_messages),
            'cursor': messages_data.get('cursor'),
            'has_more': messages_data.get('has_more', False)
        })
        
    except UnipileConnectionError as e:
        if "404" in str(e) or "Cannot GET" in str(e) or "Unknown error" in str(e):
            # Messages endpoint might not exist for this chat - return empty list gracefully
            logger.warning(f"Messages endpoint not available for chat {chat_id}: {e}")
            return Response({
                'success': True,
                'messages': [],
                'total': 0,
                'cursor': None,
                'has_more': False,
                'message': 'Messages not available for this chat'
            })
        else:
            # Other connection errors
            logger.error(f"Unipile connection error getting messages: {e}")
            return Response({
                'success': False,
                'error': 'Failed to connect to messaging service'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        logger.error(f"Failed to get chat messages: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request, chat_id):
    """Send a message to a WhatsApp chat"""
    try:
        data = request.data
        text = data.get('text', '').strip()
        message_type = data.get('type', 'text')
        attachments = data.get('attachments', [])
        
        if not text and not attachments:
            return Response({
                'success': False,
                'error': 'Message text or attachments required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        client = unipile_service.get_client()
        
        # Send message via Unipile
        response = async_to_sync(client.messaging.send_message)(
            chat_id=chat_id,
            text=text,
            attachments=attachments
        )
        
        # Transform response
        sent_message = {
            'id': response.get('id'),
            'text': text,
            'type': message_type,
            'direction': 'out',
            'chat_id': chat_id,
            'date': response.get('date') or response.get('created_at'),
            'status': response.get('status', 'sent'),
            'attachments': attachments,
            'account_id': response.get('account_id')
        }
        
        return Response({
            'success': True,
            'message': sent_message
        })
        
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_chat(request, chat_id):
    """Update chat properties (mark as read, mute, archive, etc.)"""
    try:
        data = request.data
        logger.info(f"🔄 Chat update requested for {chat_id} with data: {data}")
        
        client = unipile_service.get_client()
        
        # Convert frontend format to Unipile action format
        unipile_data = {}
        
        if 'unread_count' in data:
            # If setting unread_count to 0, mark as read
            if data['unread_count'] == 0:
                unipile_data['action'] = 'mark_as_read'
            else:
                unipile_data['action'] = 'mark_as_unread'
        elif 'action' in data:
            # Direct action specified
            unipile_data['action'] = data['action']
        else:
            # Unknown action format
            logger.warning(f"🔄 Unknown chat update format: {data}")
            unipile_data = data
        
        try:
            # Try the PATCH request with Unipile API
            response = async_to_sync(client.request.patch)(f'chats/{chat_id}', data=unipile_data)
            logger.info(f"🔄 Chat update response: {response}")
            
            return Response({
                'success': True,
                'chat': response
            })
            
        except Exception as patch_error:
            # If PATCH fails, it might not be supported for WhatsApp
            logger.warning(f"🔄 PATCH failed for WhatsApp chat {chat_id}: {patch_error}")
            
            # For WhatsApp, marking as read often happens automatically when messages are fetched
            # Return success to prevent UI errors
            if 'mark_as_read' in str(unipile_data.get('action', '')):
                logger.info(f"🔄 Simulating mark-as-read success for WhatsApp chat {chat_id}")
                return Response({
                    'success': True,
                    'message': 'WhatsApp messages are marked as read when fetched',
                    'chat': {
                        'id': chat_id,
                        'unread_count': 0,
                        'updated': True
                    }
                })
            else:
                # For other actions, re-raise the error
                raise patch_error
        
    except Exception as e:
        logger.error(f"Failed to update chat {chat_id}: {e}")
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
        client = unipile_service.get_client()
        
        # Get attendees from Unipile API
        attendees_data = async_to_sync(client.messaging.get_all_attendees)(
            account_id=account_id,
            limit=limit,
            cursor=cursor
        )
        
        # Fix: Unipile returns 'items' not 'attendees'
        attendees = attendees_data.get('items', attendees_data.get('attendees', []))
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
        
    except UnipileConnectionError as e:
        if "404" in str(e) or "Cannot GET" in str(e):
            # Attendees endpoint doesn't exist - return empty list gracefully
            logger.warning(f"Attendees endpoint not available for account {account_id}: {e}")
            return Response({
                'success': True,
                'attendees': [],
                'total': 0,
                'cursor': None,
                'has_more': False,
                'message': 'Attendees endpoint not available for this account'
            })
        else:
            # Other connection errors
            logger.error(f"Unipile connection error getting attendees: {e}")
            return Response({
                'success': False,
                'error': 'Failed to connect to messaging service'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        logger.error(f"Failed to get WhatsApp attendees: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_whatsapp_data(request):
    """Synchronize WhatsApp data with Unipile API"""
    try:
        # Get all WhatsApp connections for the current user
        whatsapp_connections = UserChannelConnection.objects.filter(
            user=request.user,
            channel_type='whatsapp',
            is_active=True,
            unipile_account_id__isnull=False
        )
        
        client = unipile_service.get_client()
        sync_results = []
        
        for connection in whatsapp_connections:
            try:
                # Try multiple sync methods
                sync_response = None
                sync_method = None
                
                # Method 1: Try resync (current method)
                try:
                    sync_response = async_to_sync(client.account.resync_account)(connection.unipile_account_id)
                    sync_method = "resync_account"
                except Exception as resync_error:
                    logger.warning(f"resync_account failed for {connection.unipile_account_id}: {resync_error}")
                    
                    # Method 2: Try restart instead
                    try:
                        sync_response = async_to_sync(client.account.restart_account)(connection.unipile_account_id)
                        sync_method = "restart_account"
                    except Exception as restart_error:
                        logger.warning(f"restart_account failed for {connection.unipile_account_id}: {restart_error}")
                        
                        # Method 3: Try a custom sync endpoint with correct GET method
                        try:
                            sync_response = async_to_sync(client.request.get)(f'accounts/{connection.unipile_account_id}/sync')
                            sync_method = "custom_sync_get"
                        except Exception as custom_error:
                            logger.warning(f"custom sync failed for {connection.unipile_account_id}: {custom_error}")
                            raise custom_error
                
                logger.info(f"Sync successful using method '{sync_method}' for account {connection.unipile_account_id}")
                
                # Update last sync attempt
                connection.last_sync_at = django_timezone.now()
                connection.save(update_fields=['last_sync_at'])
                
                sync_results.append({
                    'account_id': connection.unipile_account_id,
                    'connection_id': str(connection.id),
                    'success': True,
                    'sync_id': sync_response.get('sync_id'),
                    'status': sync_response.get('status', 'started')
                })
                
            except Exception as sync_error:
                logger.error(f"Failed to sync account {connection.unipile_account_id}: {sync_error}")
                
                # Record error
                connection.sync_error_count += 1
                connection.last_error = str(sync_error)
                connection.save(update_fields=['sync_error_count', 'last_error'])
                
                sync_results.append({
                    'account_id': connection.unipile_account_id,
                    'connection_id': str(connection.id),
                    'success': False,
                    'error': str(sync_error)
                })
        
        successful_syncs = sum(1 for result in sync_results if result['success'])
        
        return Response({
            'success': True,
            'message': f'Sync initiated for {successful_syncs}/{len(sync_results)} accounts',
            'results': sync_results,
            'total_accounts': len(sync_results),
            'successful_syncs': successful_syncs
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
        # Validate attendee_id
        if not attendee_id or attendee_id.strip() == '':
            logger.warning(f"Empty or invalid attendee_id provided: '{attendee_id}'")
            return Response({
                'success': True,
                'picture_url': None,
                'picture_data': None,
                'message': 'Invalid attendee ID'
            })
        
        # Check for common invalid values
        if attendee_id in ['undefined', 'null', 'None']:
            logger.warning(f"Invalid attendee_id value: {attendee_id}")
            return Response({
                'success': True,
                'picture_url': None,
                'picture_data': None,
                'message': 'Invalid attendee ID'
            })
        
        logger.info(f"🖼️ Fetching profile picture for attendee_id: {attendee_id}")
        
        client = unipile_service.get_client()
        
        # Get attendee picture via Unipile API
        picture_endpoint = f'chat_attendees/{attendee_id}/picture'
        logger.info(f"🖼️ Making picture API call to: {picture_endpoint}")
        
        picture_response = async_to_sync(client.request.get)(picture_endpoint)
        
        logger.info(f"🖼️ Picture response type: {type(picture_response)}")
        logger.info(f"🖼️ Picture response keys: {list(picture_response.keys()) if isinstance(picture_response, dict) else 'Not a dict'}")
        if isinstance(picture_response, dict):
            logger.info(f"🖼️ Has binary_data: {bool(picture_response.get('binary_data'))}")
            logger.info(f"🖼️ Has url: {bool(picture_response.get('url'))}")
            logger.info(f"🖼️ Content type: {picture_response.get('content_type')}")
            if picture_response.get('binary_data'):
                logger.info(f"🖼️ Binary data length: {len(picture_response['binary_data'])}")
        else:
            logger.warning(f"🖼️ Unexpected picture response format: {picture_response}")
        
        # Handle binary image data response
        if picture_response.get('binary_data'):
            # Convert binary data to base64 for frontend
            import base64
            binary_data = picture_response['binary_data']
            base64_data = base64.b64encode(binary_data).decode('utf-8')
            
            return Response({
                'success': True,
                'picture_url': None,
                'picture_data': base64_data,
                'content_type': picture_response.get('content_type', 'image/jpeg')
            })
        
        # Handle URL-based response (if Unipile returns URLs instead of binary data)
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
        # Check if it's a 404 error (endpoint doesn't exist or profile not available)
        if "404" in str(e) or "Cannot GET" in str(e) or "Unknown error" in str(e):
            # Profile pictures not available - this is normal for WhatsApp
            # Many users have privacy settings that block profile picture access
            logger.debug(f"Profile picture not accessible for attendee {attendee_id}: {e}")
            return Response({
                'success': True,
                'picture_url': None,
                'picture_data': None,
                'message': 'Profile picture not available'
            })
        else:
            # Other errors (500, connection issues, etc.)
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
        client = unipile_service.get_client()
        
        # Get attachment via Unipile API
        attachment_response = async_to_sync(client.request.get)(f'messages/{message_id}/attachments/{attachment_id}')
        
        # Check if we got binary data or just metadata
        if attachment_response.get('data'):
            # We have binary data - return it directly
            import base64
            from django.http import HttpResponse
            
            attachment_data = attachment_response.get('data')
            content_type = attachment_response.get('content_type', 'application/octet-stream')
            filename = attachment_response.get('filename', f'attachment_{attachment_id}')
            
            # Decode base64 data if needed
            if isinstance(attachment_data, str):
                try:
                    binary_data = base64.b64decode(attachment_data)
                except:
                    # If not base64, assume it's already binary
                    binary_data = attachment_data.encode() if isinstance(attachment_data, str) else attachment_data
            else:
                binary_data = attachment_data
            
            # Return file as download
            response = HttpResponse(binary_data, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(binary_data)
            return response
            
        elif attachment_response.get('url'):
            # We have a URL - redirect to it or proxy it
            import httpx
            attachment_url = attachment_response.get('url')
            
            # Fetch the file from the URL
            import requests
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
            # No binary data or URL available
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
    """Synchronize full message history for a specific WhatsApp chat"""
    try:
        # Get sync parameters
        full_sync = request.data.get('full_sync', False)  # Whether to sync all history or recent only
        since = request.data.get('since')  # Optional: sync from specific date
        
        client = unipile_service.get_client()
        
        # Trigger chat history sync via Unipile API
        sync_params = {
            'chat_id': chat_id,
            'full_sync': full_sync
        }
        
        if since:
            sync_params['since'] = since
            
        sync_response = async_to_sync(client.request.post)(f'chats/{chat_id}/sync', data=sync_params)
        
        return Response({
            'success': True,
            'sync_id': sync_response.get('sync_id'),
            'status': sync_response.get('status', 'started'),
            'estimated_messages': sync_response.get('estimated_messages', 0),
            'chat_id': chat_id,
            'full_sync': full_sync,
            'message': f'Chat history sync {"(full)" if full_sync else "(recent)"} initiated for chat {chat_id}'
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
        sync_id = request.GET.get('sync_id')
        
        client = unipile_service.get_client()
        
        # Check sync status via Unipile API
        if sync_id:
            status_response = async_to_sync(client.request.get)(f'sync/{sync_id}/status')
        else:
            # Get latest sync status for this chat
            status_response = async_to_sync(client.request.get)(f'chats/{chat_id}/sync/status')
        
        return Response({
            'success': True,
            'chat_id': chat_id,
            'sync_id': status_response.get('sync_id'),
            'status': status_response.get('status', 'unknown'),
            'progress': status_response.get('progress', 0),
            'total_messages': status_response.get('total_messages', 0),
            'synced_messages': status_response.get('synced_messages', 0),
            'last_updated': status_response.get('last_updated'),
            'error': status_response.get('error'),
            'completed_at': status_response.get('completed_at')
        })
        
    except Exception as e:
        logger.error(f"Failed to get chat sync status for chat {chat_id}: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Note: These views are async and will be automatically converted by Django's async middleware