"""
WhatsApp API Views
Provides REST API endpoints for WhatsApp functionality
"""
import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import JsonResponse, HttpResponse
from asgiref.sync import async_to_sync

from ..base import BaseChannelViews
from .service import WhatsAppService

logger = logging.getLogger(__name__)


class WhatsAppViews(BaseChannelViews):
    """WhatsApp-specific API views"""
    
    def __init__(self):
        """Initialize WhatsApp views"""
        self.service = WhatsAppService()
    
    def get_channel_type(self) -> str:
        """Return the channel type"""
        return 'whatsapp'
    
    def get_service(self):
        """Return the WhatsApp service"""
        return self.service


# Initialize views instance
whatsapp_views = WhatsAppViews()


# View functions for URL patterns
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_whatsapp_chats(request):
    """
    Get WhatsApp chats with local-first architecture
    
    Query params:
    - account_id: UniPile account ID (required)
    - limit: Number of chats to return (default: 15)
    - cursor: Pagination cursor
    - force_sync: Force API sync (default: false)
    """
    account_id = request.GET.get('account_id')
    limit = int(request.GET.get('limit', 15))
    cursor = request.GET.get('cursor')
    force_sync = request.GET.get('force_sync', 'false').lower() == 'true'
    
    if not account_id:
        return Response({
            'success': False,
            'error': 'account_id parameter is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Use the service to get conversations
        result = async_to_sync(whatsapp_views.service.sync_conversations)(
            user=request.user,
            account_id=account_id,
            force_sync=force_sync
        )
        
        # Format response for frontend compatibility
        conversations = result.get('conversations', [])
        
        logger.info(f"✅ Retrieved {len(conversations)} WhatsApp chats for user {request.user.id}")
        
        return Response({
            'success': True,
            'chats': conversations,  # Frontend expects 'chats' not 'conversations'
            'has_more': len(conversations) >= limit,
            'cursor': cursor,
            'pagination': {
                'limit': limit,
                'cursor': cursor,
                'has_more': len(conversations) >= limit,
                'total_fetched': len(conversations)
            },
            'cache_info': {
                'from_cache': result.get('from_cache', False),
                'from_local': result.get('from_local', True),
                'sync_triggered': force_sync
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
def get_chat_messages(request, chat_id):
    """
    Get messages for a WhatsApp chat
    
    Query params:
    - account_id: UniPile account ID (required)
    - limit: Number of messages to return (default: 50)
    - cursor: Pagination cursor
    - force_sync: Force API sync (default: true for real-time)
    """
    account_id = request.GET.get('account_id')
    limit = int(request.GET.get('limit', 50))
    cursor = request.GET.get('cursor')
    force_sync = request.GET.get('force_sync', 'true').lower() == 'true'  # Default to true for messages
    
    if not account_id:
        return Response({
            'success': False,
            'error': 'account_id parameter is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Use the service to get messages
        result = async_to_sync(whatsapp_views.service.sync_messages)(
            user=request.user,
            account_id=account_id,
            conversation_id=chat_id,
            force_sync=force_sync
        )
        
        messages = result.get('messages', [])
        
        logger.info(f"✅ Retrieved {len(messages)} messages for WhatsApp chat {chat_id}")
        
        return Response({
            'success': True,
            'messages': messages,
            'chat_id': chat_id,
            'pagination': {
                'limit': limit,
                'cursor': cursor,
                'has_more': len(messages) >= limit
            },
            'synced': result.get('synced', True)
        })
        
    except Exception as e:
        logger.error(f"Failed to get WhatsApp messages: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_whatsapp_message(request, chat_id):
    """
    Send a WhatsApp message
    
    Body params:
    - account_id: UniPile account ID (required)
    - text: Message text content
    - attachments: List of attachment objects
    """
    account_id = request.data.get('account_id')
    text = request.data.get('text') or request.data.get('content')
    attachments = request.data.get('attachments', [])
    
    if not account_id:
        return Response({
            'success': False,
            'error': 'account_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not text and not attachments:
        return Response({
            'success': False,
            'error': 'Either text or attachments are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Use the service to send message
        result = async_to_sync(whatsapp_views.service.send_message)(
            user=request.user,
            account_id=account_id,
            conversation_id=chat_id,
            content=text,
            attachments=attachments
        )
        
        if result.get('success'):
            logger.info(f"✅ Sent WhatsApp message to chat {chat_id}")
            return Response({
                'success': True,
                'message': result.get('message'),
                'message_id': result.get('message', {}).get('id')
            })
        else:
            return Response({
                'success': False,
                'error': result.get('error', 'Failed to send message')
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_whatsapp_accounts(request):
    """
    Get user's WhatsApp accounts
    """
    try:
        from communications.models import UserChannelConnection
        
        # Get user's WhatsApp connections
        connections = UserChannelConnection.objects.filter(
            user=request.user,
            channel_type='whatsapp',
            is_active=True
        ).order_by('-created_at')
        
        accounts = []
        for conn in connections:
            # Extract phone from provider_config or connection_config
            phone = None
            if conn.provider_config:
                phone = conn.provider_config.get('phone')
            if not phone and conn.connection_config:
                phone = conn.connection_config.get('phone')
            
            accounts.append({
                'id': conn.unipile_account_id,
                'name': conn.account_name,
                'phone': phone,
                'status': conn.account_status,
                'connected_at': conn.created_at.isoformat(),
                'last_sync': conn.last_sync_at.isoformat() if conn.last_sync_at else None
            })
        
        return Response({
            'success': True,
            'accounts': accounts,
            'count': len(accounts)
        })
        
    except Exception as e:
        logger.error(f"Failed to get WhatsApp accounts: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_whatsapp_data(request):
    """
    Trigger manual sync of WhatsApp data
    
    Body params:
    - account_id: UniPile account ID (required)
    - sync_type: 'conversations' or 'all' (default: 'conversations')
    - days_back: Number of days to sync (default: 30)
    """
    account_id = request.data.get('account_id')
    sync_type = request.data.get('sync_type', 'conversations')
    days_back = int(request.data.get('days_back', 30))
    
    if not account_id:
        return Response({
            'success': False,
            'error': 'account_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Trigger sync
        if sync_type == 'all':
            # Comprehensive sync
            from communications.services.comprehensive_sync import comprehensive_sync_service
            from communications.models import Channel
            
            channel = Channel.objects.filter(
                unipile_account_id=account_id,
                channel_type='whatsapp'
            ).first()
            
            if not channel:
                return Response({
                    'success': False,
                    'error': 'Channel not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            stats = async_to_sync(comprehensive_sync_service.sync_account_comprehensive)(
                channel=channel,
                days_back=days_back,
                max_messages_per_chat=100
            )
            
            return Response({
                'success': True,
                'sync_type': 'comprehensive',
                'stats': stats
            })
        else:
            # Just sync conversations
            result = async_to_sync(whatsapp_views.service.sync_conversations)(
                user=request.user,
                account_id=account_id,
                force_sync=True
            )
            
            return Response({
                'success': True,
                'sync_type': 'conversations',
                'conversations_synced': len(result.get('conversations', []))
            })
            
    except Exception as e:
        logger.error(f"Failed to sync WhatsApp data: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_whatsapp_attendees(request):
    """
    Get attendees for a WhatsApp chat
    
    Query params:
    - account_id: UniPile account ID (required)
    - chat_id: Chat ID (required)
    """
    account_id = request.GET.get('account_id')
    chat_id = request.GET.get('chat_id')
    
    if not account_id or not chat_id:
        return Response({
            'success': False,
            'error': 'account_id and chat_id are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from communications.models import ChatAttendee, Channel
        
        # Get channel
        channel = Channel.objects.filter(
            unipile_account_id=account_id,
            channel_type='whatsapp'
        ).first()
        
        if not channel:
            return Response({
                'success': False,
                'error': 'Channel not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get attendees
        attendees = ChatAttendee.objects.filter(
            channel=channel,
            chat_id=chat_id,
            is_active=True
        )
        
        attendee_list = []
        for att in attendees:
            attendee_list.append({
                'id': att.external_attendee_id,
                'name': att.name,
                'phone': att.phone_number,
                'is_self': att.is_self,
                'profile_picture': att.metadata.get('profile_picture') if att.metadata else None,
                'role': att.metadata.get('role', 'member') if att.metadata else 'member'
            })
        
        return Response({
            'success': True,
            'attendees': attendee_list,
            'count': len(attendee_list)
        })
        
    except Exception as e:
        logger.error(f"Failed to get WhatsApp attendees: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_chat(request, chat_id):
    """
    Update WhatsApp chat metadata
    
    Body params:
    - account_id: UniPile account ID (required)
    - archived: Set archived status
    - muted: Set muted status
    - pinned: Set pinned status
    """
    account_id = request.data.get('account_id')
    
    if not account_id:
        return Response({
            'success': False,
            'error': 'account_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from communications.models import Channel, Conversation
        
        # Get channel and conversation
        channel = Channel.objects.filter(
            unipile_account_id=account_id,
            channel_type='whatsapp'
        ).first()
        
        if not channel:
            return Response({
                'success': False,
                'error': 'Channel not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        conversation = Conversation.objects.filter(
            channel=channel,
            external_thread_id=chat_id
        ).first()
        
        if not conversation:
            return Response({
                'success': False,
                'error': 'Conversation not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update metadata
        if 'archived' in request.data:
            conversation.is_archived = request.data['archived']
        
        if not conversation.metadata:
            conversation.metadata = {}
        
        if 'muted' in request.data:
            conversation.metadata['muted'] = request.data['muted']
        
        if 'pinned' in request.data:
            conversation.metadata['pinned'] = request.data['pinned']
        
        conversation.save()
        
        return Response({
            'success': True,
            'updated': True,
            'chat_id': chat_id
        })
        
    except Exception as e:
        logger.error(f"Failed to update WhatsApp chat: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)