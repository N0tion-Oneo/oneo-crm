"""
API views for message synchronization with UniPile
Handles both manual sync requests and webhook processing
"""
import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from asgiref.sync import async_to_sync

from ..message_sync import message_sync_service
from ..models import UserChannelConnection

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_account_messages(request, connection_id=None):
    """
    Manually trigger message sync for a specific account or all accounts
    """
    try:
        if connection_id:
            # Sync specific connection
            try:
                connection = UserChannelConnection.objects.get(
                    id=connection_id,
                    user=request.user
                )
            except UserChannelConnection.DoesNotExist:
                return Response(
                    {'error': 'Connection not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get sync parameters
            initial_sync = request.data.get('initial_sync', False)
            days_back = request.data.get('days_back', 30)
            
            # Trigger sync
            result = async_to_sync(message_sync_service.sync_account_messages)(
                connection,
                initial_sync=initial_sync,
                days_back=days_back
            )
            
            return Response(result)
        
        else:
            # Sync all user's connections
            user_connections = UserChannelConnection.objects.filter(
                user=request.user,
                is_active=True,
                account_status='active'
            )
            
            if not user_connections.exists():
                return Response({
                    'success': True,
                    'message': 'No active connections to sync',
                    'total_connections': 0,
                    'successful_syncs': 0,
                    'failed_syncs': 0
                })
            
            # Get sync parameters
            initial_sync = request.data.get('initial_sync', False)
            days_back = request.data.get('days_back', 30)
            
            results = []
            successful_syncs = 0
            failed_syncs = 0
            
            for connection in user_connections:
                result = async_to_sync(message_sync_service.sync_account_messages)(
                    connection,
                    initial_sync=initial_sync,
                    days_back=days_back
                )
                
                if result['success']:
                    successful_syncs += 1
                else:
                    failed_syncs += 1
                
                results.append({
                    'connection_id': str(connection.id),
                    'account_name': connection.account_name,
                    'channel_type': connection.channel_type,
                    'result': result
                })
            
            return Response({
                'success': True,
                'total_connections': len(user_connections),
                'successful_syncs': successful_syncs,
                'failed_syncs': failed_syncs,
                'results': results
            })
        
    except Exception as e:
        logger.error(f"Failed to sync messages: {e}")
        return Response(
            {'error': 'Failed to sync messages', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_sync_status(request, connection_id=None):
    """
    Get sync status for user's connections
    """
    try:
        if connection_id:
            # Get specific connection status
            try:
                connection = UserChannelConnection.objects.get(
                    id=connection_id,
                    user=request.user
                )
            except UserChannelConnection.DoesNotExist:
                return Response(
                    {'error': 'Connection not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response({
                'connection_id': str(connection.id),
                'account_name': connection.account_name,
                'channel_type': connection.channel_type,
                'unipile_account_id': connection.unipile_account_id,
                'account_status': connection.account_status,
                'last_sync_at': connection.last_sync_at.isoformat() if connection.last_sync_at else None,
                'sync_error_count': connection.sync_error_count,
                'last_error': connection.last_error,
                'can_send_messages': connection.can_send_messages(),
                'needs_reconnection': connection.needs_reconnection()
            })
        
        else:
            # Get all user's connections status
            connections = UserChannelConnection.objects.filter(
                user=request.user
            ).order_by('-created_at')
            
            connection_statuses = []
            for connection in connections:
                connection_statuses.append({
                    'connection_id': str(connection.id),
                    'account_name': connection.account_name,
                    'channel_type': connection.channel_type,
                    'unipile_account_id': connection.unipile_account_id,
                    'account_status': connection.account_status,
                    'last_sync_at': connection.last_sync_at.isoformat() if connection.last_sync_at else None,
                    'sync_error_count': connection.sync_error_count,
                    'last_error': connection.last_error,
                    'can_send_messages': connection.can_send_messages(),
                    'needs_reconnection': connection.needs_reconnection()
                })
            
            return Response({
                'total_connections': len(connection_statuses),
                'connections': connection_statuses
            })
        
    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        return Response(
            {'error': 'Failed to get sync status', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_all_messages(request):
    """
    Sync messages for all active connections (admin/manager only)
    """
    try:
        # Check if user has permission to sync all messages
        if not request.user.user_type or request.user.user_type.name not in ['Admin', 'Manager']:
            return Response(
                {'error': 'Insufficient permissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get sync parameters
        initial_sync = request.data.get('initial_sync', False)
        days_back = request.data.get('days_back', 30)
        
        # Trigger sync for all active connections
        result = async_to_sync(message_sync_service.sync_all_active_connections)(
            initial_sync=initial_sync,
            days_back=days_back
        )
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"Failed to sync all messages: {e}")
        return Response(
            {'error': 'Failed to sync all messages', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([])  # No authentication required for webhooks
def webhook_message_received(request):
    """
    Handle incoming UniPile webhook for new messages
    This endpoint receives webhooks routed from the global side to tenant side
    
    NOTE: This endpoint is DEPRECATED in favor of the main webhook handler
    It's kept for backwards compatibility but should not be used.
    """
    
    # DEPRECATED: This endpoint is redundant with the main webhook handler
    # Return early to prevent duplicate processing
    logger.warning("webhook_message_received endpoint is deprecated, use main webhook handler instead")
    return Response({
        'status': 'deprecated',
        'message': 'This endpoint is deprecated. Use the main webhook handler instead.'
    })


async def _process_webhook_message(
    connection: UserChannelConnection,
    event_type: str,
    message_data: dict
) -> dict:
    """
    Process a single message from webhook data
    """
    try:
        from ..message_sync import message_sync_service
        
        # Get or create channel
        channel = await message_sync_service._get_or_create_channel(connection)
        
        if event_type == 'message_received':
            # New inbound message
            message = await message_sync_service._create_or_update_message(
                channel, message_data, connection
            )
            
            if message:
                return {
                    'success': True,
                    'message_id': str(message.id),
                    'action': 'created'
                }
        
        elif event_type in ['message_delivered', 'message_read']:
            # Update existing message status
            external_message_id = message_data.get('id') or message_data.get('message_id')
            
            if external_message_id:
                from ..models import Message, MessageStatus
                
                try:
                    message = await sync_to_async(Message.objects.get)(
                        external_message_id=external_message_id,
                        channel=channel
                    )
                    
                    # Update status
                    if event_type == 'message_delivered':
                        message.status = MessageStatus.DELIVERED
                    elif event_type == 'message_read':
                        message.status = MessageStatus.READ
                    
                    await sync_to_async(message.save)(update_fields=['status'])
                    
                    return {
                        'success': True,
                        'message_id': str(message.id),
                        'action': 'updated_status'
                    }
                    
                except Message.DoesNotExist:
                    # Message not found locally, try to sync it
                    message = await message_sync_service._create_or_update_message(
                        channel, message_data, connection
                    )
                    
                    if message:
                        return {
                            'success': True,
                            'message_id': str(message.id),
                            'action': 'synced_and_updated'
                        }
        
        elif event_type == 'message_sent':
            # Outbound message confirmation
            message = await message_sync_service._create_or_update_message(
                channel, message_data, connection
            )
            
            if message:
                return {
                    'success': True,
                    'message_id': str(message.id),
                    'action': 'confirmed_sent'
                }
        
        return {'success': False, 'error': f'Unhandled event type: {event_type}'}
        
    except Exception as e:
        logger.error(f"Failed to process webhook message: {e}")
        return {'success': False, 'error': str(e)}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_message_history(request, connection_id):
    """
    Get message history for a specific connection
    """
    try:
        # Verify user owns the connection
        try:
            connection = UserChannelConnection.objects.get(
                id=connection_id,
                user=request.user
            )
        except UserChannelConnection.DoesNotExist:
            return Response(
                {'error': 'Connection not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get channel for this connection
        from ..models import Channel, Message
        
        try:
            channel = Channel.objects.get(unipile_account_id=connection.unipile_account_id)
        except Channel.DoesNotExist:
            return Response({
                'connection_id': str(connection.id),
                'account_name': connection.account_name,
                'messages': [],
                'total_count': 0
            })
        
        # Get messages with pagination
        limit = min(int(request.query_params.get('limit', 50)), 100)
        offset = int(request.query_params.get('offset', 0))
        
        messages = Message.objects.filter(
            channel=channel
        ).select_related('conversation', 'contact_record').order_by('-created_at')[offset:offset+limit]
        
        total_count = Message.objects.filter(channel=channel).count()
        
        # Serialize messages
        message_list = []
        for message in messages:
            message_list.append({
                'id': str(message.id),
                'external_message_id': message.external_message_id,
                'direction': message.direction,
                'content': message.content,
                'subject': message.subject,
                'contact_email': message.contact_email,
                'status': message.status,
                'sent_at': message.sent_at.isoformat() if message.sent_at else None,
                'received_at': message.received_at.isoformat() if message.received_at else None,
                'created_at': message.created_at.isoformat(),
                'conversation': {
                    'id': str(message.conversation.id),
                    'subject': message.conversation.subject
                } if message.conversation else None,
                'contact_record': {
                    'id': str(message.contact_record.id),
                    'name': message.contact_record.data.get('name', 'Unknown')
                } if message.contact_record else None,
                'metadata': message.metadata
            })
        
        return Response({
            'connection_id': str(connection.id),
            'account_name': connection.account_name,
            'channel_id': str(channel.id),
            'messages': message_list,
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"Failed to get message history: {e}")
        return Response(
            {'error': 'Failed to get message history', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )