"""
Celery tasks for real-time communication and WebSocket broadcasting
"""

from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
import logging
import json

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


@shared_task(bind=True, name='realtime.tasks.broadcast_update')
def broadcast_update(self, group_name, event_type, data):
    """
    Broadcast real-time updates to WebSocket groups
    Used for: Live updates, collaborative editing, notifications
    """
    try:
        message = {
            'type': 'broadcast_message',
            'event_type': event_type,
            'data': data,
            'timestamp': json.dumps({
                'timestamp': str(timezone.now())
            }, default=str)
        }
        
        # Send to WebSocket group
        async_to_sync(channel_layer.group_send)(group_name, message)
        
        logger.info(f"Broadcast sent to group {group_name}: {event_type}")
        return {
            'group_name': group_name,
            'event_type': event_type,
            'status': 'sent'
        }
        
    except Exception as e:
        error_msg = f"Broadcast error: {e}"
        logger.error(error_msg)
        return {'error': error_msg}


@shared_task(bind=True, name='realtime.tasks.send_user_notification')
def send_user_notification(self, user_id, notification_type, message, data=None):
    """
    Send notifications to specific users via WebSocket
    Used for: Personal notifications, alerts, status updates
    """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.get(id=user_id)
        user_group = f"user_{user_id}"
        
        notification_data = {
            'type': 'user_notification',
            'notification_type': notification_type,
            'message': message,
            'data': data or {},
            'user_id': user_id,
            'timestamp': str(timezone.now())
        }
        
        # Send to user's personal WebSocket group
        async_to_sync(channel_layer.group_send)(
            user_group, 
            {
                'type': 'send_notification',
                'notification': notification_data
            }
        )
        
        logger.info(f"Notification sent to user {user_id}: {notification_type}")
        return {
            'user_id': user_id,
            'notification_type': notification_type,
            'status': 'sent'
        }
        
    except Exception as e:
        error_msg = f"User notification error: {e}"
        logger.error(error_msg)
        return {'error': error_msg}


@shared_task(bind=True, name='realtime.tasks.process_collaborative_edit')
def process_collaborative_edit(self, document_id, user_id, operation, data):
    """
    Process collaborative editing operations
    Used for: Real-time document editing, operational transforms
    """
    try:
        from .operational_transform import OperationalTransform
        
        # Process the operation
        ot = OperationalTransform()
        result = ot.apply_operation(
            document_id=document_id,
            user_id=user_id,
            operation=operation,
            data=data
        )
        
        if result['success']:
            # Broadcast the operation to other users
            document_group = f"document_{document_id}"
            
            broadcast_data = {
                'type': 'collaborative_edit',
                'document_id': document_id,
                'user_id': user_id,
                'operation': operation,
                'data': result['transformed_data'],
                'version': result['version']
            }
            
            async_to_sync(channel_layer.group_send)(
                document_group,
                {
                    'type': 'broadcast_edit',
                    'edit_data': broadcast_data
                }
            )
        
        logger.info(f"Collaborative edit processed for document {document_id}")
        return result
        
    except Exception as e:
        error_msg = f"Collaborative edit error: {e}"
        logger.error(error_msg)
        return {'error': error_msg, 'success': False}


@shared_task(bind=True, name='realtime.tasks.stream_ai_response')
def stream_ai_response(self, session_id, prompt, context_data=None):
    """
    Stream AI responses in real-time chunks
    Used for: Streaming AI responses, real-time AI chat
    """
    try:
        import time
        
        # Simulate streaming AI response
        response_chunks = [
            "Processing your request...",
            "Analyzing data...", 
            "Generating response...",
            f"Here's the response to: {prompt}",
            "Response complete."
        ]
        
        stream_group = f"ai_stream_{session_id}"
        
        for i, chunk in enumerate(response_chunks):
            # Send each chunk with a delay to simulate streaming
            chunk_data = {
                'type': 'ai_stream_chunk',
                'session_id': session_id,
                'chunk': chunk,
                'chunk_index': i,
                'is_final': i == len(response_chunks) - 1
            }
            
            async_to_sync(channel_layer.group_send)(
                stream_group,
                {
                    'type': 'stream_chunk',
                    'chunk_data': chunk_data
                }
            )
            
            time.sleep(1)  # Simulate processing delay
        
        logger.info(f"AI response streamed for session {session_id}")
        return {
            'session_id': session_id,
            'chunks_sent': len(response_chunks),
            'status': 'completed'
        }
        
    except Exception as e:
        error_msg = f"AI streaming error: {e}"
        logger.error(error_msg)
        return {'error': error_msg}