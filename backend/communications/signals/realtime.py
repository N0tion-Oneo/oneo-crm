"""
Real-time signal handlers for WebSocket broadcasting and cache management
Handles conversation updates, message broadcasts, and cache invalidation
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='communications.Message')
def update_conversation_stats(sender, instance, created, **kwargs):
    """Update conversation statistics when messages are created"""
    if created and instance.conversation:
        conversation = instance.conversation
        old_timestamp = conversation.last_message_at
        conversation.message_count = conversation.messages.count()
        conversation.last_message_at = instance.created_at
        conversation.save(update_fields=['message_count', 'last_message_at'])
        
        logger.debug(f"🔄 Updated conversation {conversation.id} timestamp: {old_timestamp} → {instance.created_at}")
        logger.debug(f"🔄 Message content: {instance.content[:100] if instance.content else 'No content'}")
        
        # Invalidate cached conversation data to ensure fresh timestamps
        _invalidate_conversation_cache(instance.conversation)


@receiver(post_save, sender='communications.Conversation')
def broadcast_conversation_update(sender, instance, created, **kwargs):
    """Broadcast conversation updates for real-time inbox refresh"""
    # Import here to avoid circular imports
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.debug("No channel layer available for conversation broadcasting")
            return
        
        # Create conversation update event
        event_data = {
            'type': 'conversation_updated' if not created else 'new_conversation',
            'conversation_id': str(instance.id),
            'message_count': instance.message_count,
            'unread_count': instance.unread_count,
            'last_message_at': instance.last_message_at.isoformat() if instance.last_message_at else None,
            'timestamp': instance.updated_at.isoformat() if instance.updated_at else None
        }
        
        # Broadcast to unified inbox subscribers
        async_to_sync(channel_layer.group_send)(
            'unified_inbox_updates',
            {
                'type': 'conversation_update',
                'data': event_data
            }
        )
        
        logger.debug(f"Broadcasted conversation update {instance.id} via WebSocket")
        
    except Exception as e:
        logger.error(f"Error broadcasting conversation update via WebSocket: {e}")


@receiver(post_save, sender='communications.Message')
def broadcast_message_update(sender, instance, created, **kwargs):
    """Broadcast new messages and status updates via WebSocket for real-time updates"""
    # Always broadcast for new messages or any updates (simplify for debugging)
    should_broadcast = True
    
    if created:
        logger.debug(f"🚨 NEW MESSAGE CREATED: Message {instance.id} with status {instance.status}")
    else:
        logger.debug(f"🚨 MESSAGE UPDATED: Message {instance.id} with status {instance.status}")
        if 'status' in (kwargs.get('update_fields') or []):
            logger.debug(f"🚨 STATUS FIELD UPDATED: Message {instance.id}")
        else:
            logger.debug(f"🚨 OTHER FIELDS UPDATED: Message {instance.id}, update_fields: {kwargs.get('update_fields')}")
    
    if should_broadcast:
        logger.debug(f"🚨 SIGNAL TRIGGERED: New message {instance.id} in conversation {instance.conversation.id if instance.conversation else 'None'}")
        logger.debug(f"🚨 Message content: '{instance.content[:50] if instance.content else 'No content'}...'")
        logger.debug(f"🚨 Message direction: {instance.direction}")
        logger.debug(f"🚨 About to broadcast to WebSocket...")
        # Import here to avoid circular imports
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                logger.debug("No channel layer available for WebSocket broadcasting")
                return
            
            # Import serializer here to avoid circular imports
            try:
                from ..serializers import MessageSerializer
                # Serialize the message data for frontend
                serializer = MessageSerializer(instance)
                message_data = serializer.data
                
                # Convert direction to frontend format (serializer returns 'outbound'/'inbound')
                if 'direction' in message_data:
                    message_data['direction'] = 'out' if message_data['direction'] == 'outbound' else 'in'
                
                # Keep status as-is, frontend will handle pending status with spinner
                
            except ImportError:
                # Fallback to basic message data if serializer not available
                # Convert direction from enum to frontend format
                frontend_direction = 'out' if instance.direction == 'outbound' else 'in'
                # Keep status as-is, frontend will handle pending status with spinner
                
                message_data = {
                    'id': str(instance.id),
                    'text': instance.content,  # Frontend expects 'text' not 'content'
                    'content': instance.content,  # Keep both for compatibility
                    'direction': frontend_direction,  # Convert outbound/inbound to out/in
                    'status': instance.status,  # Keep original status, frontend handles pending
                    'date': instance.created_at.isoformat() if instance.created_at else None,
                    'created_at': instance.created_at.isoformat() if instance.created_at else None,
                    'type': 'text',  # Default message type
                    'chat_id': str(instance.conversation.id) if instance.conversation else None,
                    'conversation_id': str(instance.conversation.id) if instance.conversation else None,
                    'attachments': [],  # Empty for now
                    'account_id': instance.conversation.channel.user_connection.unipile_account_id if instance.conversation and instance.conversation.channel.user_connection else None
                }
            
            # Create WebSocket event data
            event_data = {
                'type': 'message_update',
                'message': message_data,
                'conversation_id': str(instance.conversation.id) if instance.conversation else None,
                'timestamp': instance.created_at.isoformat() if instance.created_at else None
            }
            
            # Broadcast to unified inbox subscribers
            async_to_sync(channel_layer.group_send)(
                'unified_inbox_updates',
                {
                    'type': 'message_update',
                    'data': event_data
                }
            )
            
            # Also broadcast to conversation-specific room if available
            if instance.conversation:
                # Use external_thread_id (the frontend uses this ID, not the database UUID)
                channel_name = f'conversation_{instance.conversation.external_thread_id or instance.conversation.id}'
                # Ensure all UUIDs are converted to strings for JSON serialization
                serialized_message_data = {}
                for key, value in message_data.items():
                    if hasattr(value, '__str__') and 'UUID' in str(type(value)):
                        serialized_message_data[key] = str(value)
                    else:
                        serialized_message_data[key] = value
                
                # Send different event types based on whether it's new or an update
                event_type = 'new_message' if created else 'message_update'
                
                websocket_event = {
                    'type': event_type,
                    'message': serialized_message_data,  # UUID-safe message data
                    'conversation_id': str(instance.conversation.external_thread_id or instance.conversation.id),
                    'timestamp': instance.created_at.isoformat() if instance.created_at else None
                }
                
                logger.debug(f"🚨 BROADCASTING {event_type} to channel: {channel_name}")
                logger.debug(f"🚨 Message status: {serialized_message_data.get('status')}")
                logger.debug(f"🚨 WebSocket event: {websocket_event}")
                logger.debug(f"🚨 Conversation details: DB_ID={instance.conversation.id}, EXTERNAL_ID={instance.conversation.external_thread_id}")
                
                try:
                    async_to_sync(channel_layer.group_send)(channel_name, websocket_event)
                    logger.debug(f"🚨 ✅ BROADCAST SUCCESS to {channel_name}")
                except Exception as broadcast_error:
                    logger.error(f"🚨 ❌ BROADCAST FAILED to {channel_name}: {broadcast_error}")
            
            logger.debug(f"🚨 SIGNAL COMPLETE: Finished processing message {instance.id}")
            
        except Exception as e:
            logger.error(f"Error broadcasting message via WebSocket: {e}")


@receiver(post_delete, sender='communications.Message')
def update_conversation_stats_on_delete(sender, instance, **kwargs):
    """Update conversation statistics when messages are deleted"""
    if instance.conversation:
        conversation = instance.conversation
        conversation.message_count = conversation.messages.count()
        last_message = conversation.messages.order_by('-created_at').first()
        conversation.last_message_at = last_message.created_at if last_message else None
        conversation.save(update_fields=['message_count', 'last_message_at'])


@receiver(post_save, sender='communications.Message')
def update_channel_stats(sender, instance, created, **kwargs):
    """Update channel statistics when messages are created"""
    if created:
        channel = instance.channel
        channel.message_count = channel.messages.count()
        channel.last_message_at = instance.created_at
        channel.save(update_fields=['message_count', 'last_message_at'])


def _invalidate_conversation_cache(conversation):
    """
    Invalidate cached conversation data and message caches to ensure fresh data
    """
    try:
        from core.cache import invalidate_tenant_cache
        from django.core.cache import cache
        
        # Clear conversation list cache using the same format as persistence service
        if hasattr(conversation.channel, 'user_connection') and conversation.channel.user_connection:
            connection = conversation.channel.user_connection
            channel_type = connection.channel_type or 'whatsapp'
            account_id = connection.unipile_account_id
            
            # Clear all cached conversation lists for this account (different cursors/limits)
            # Use pattern matching to clear multiple cache keys
            try:
                from core.cache import tenant_cache_key
                import fnmatch
                
                # Get all cache keys and find ones that match our pattern
                cache_pattern = f"conversations:{channel_type}:{account_id}:*"
                
                # For Django cache backends that support key iteration
                if hasattr(cache, '_cache') and hasattr(cache._cache, 'keys'):
                    all_keys = cache._cache.keys()
                    matching_keys = [key for key in all_keys if fnmatch.fnmatch(str(key), f"*{cache_pattern}*")]
                    for key in matching_keys:
                        cache.delete(key)
                        
                # Also try common cache keys for conversations
                for cursor in [None, '', '0', '1']:
                    for limit in [10, 15, 20, 50]:
                        test_key = tenant_cache_key(f"conversations:{channel_type}:{account_id}:{cursor}:{limit}")
                        cache.delete(test_key)
                
                # CRITICAL: Also invalidate message caches for this conversation
                conversation_id = str(conversation.external_thread_id or conversation.id)
                for cursor in [None, '', '0', '1']:
                    for limit in [10, 20, 50, 100]:
                        message_cache_key = tenant_cache_key(f"messages:{conversation_id}:{cursor}:{limit}")
                        cache.delete(message_cache_key)
                        logger.info(f"🗑️ Cleared message cache: {message_cache_key}")
                        
            except Exception as e:
                # Fallback: just clear some common cache patterns
                logger.warning(f"Cache invalidation error, using fallback: {e}")
                
                for cursor in [None, '', '0']:
                    for limit in [15, 20]:
                        try:
                            from core.cache import tenant_cache_key
                            cache_key = tenant_cache_key(f"conversations:{channel_type}:{account_id}:{cursor}:{limit}")
                            cache.delete(cache_key)
                        except:
                            pass
                
                # Also clear message caches in fallback
                try:
                    from core.cache import tenant_cache_key
                    conversation_id = str(conversation.external_thread_id or conversation.id)
                    for cursor in [None, '', '0']:
                        for limit in [20, 50]:
                            message_cache_key = tenant_cache_key(f"messages:{conversation_id}:{cursor}:{limit}")
                            cache.delete(message_cache_key)
                            logger.info(f"🗑️ Fallback cleared message cache: {message_cache_key}")
                except:
                    pass
                            
    except Exception as e:
        logger.warning(f"Failed to invalidate conversation cache: {e}")


# Utility functions for manual broadcasting

def broadcast_custom_event(room_name: str, event_type: str, data: dict):
    """
    Manually broadcast a custom event to a specific room
    
    Args:
        room_name: WebSocket room/group name
        event_type: Type of event to broadcast
        data: Event data to send
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning("No channel layer available for custom event broadcasting")
            return False
        
        async_to_sync(channel_layer.group_send)(
            room_name,
            {
                'type': event_type,
                'data': data
            }
        )
        
        logger.debug(f"Broadcasted custom event {event_type} to room {room_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error broadcasting custom event: {e}")
        return False


def invalidate_conversation_cache_manual(channel_type: str, account_id: str):
    """
    Manually invalidate conversation cache for a specific account
    
    Args:
        channel_type: Type of channel (whatsapp, email, etc.)
        account_id: UniPile account ID
    """
    try:
        from core.cache import tenant_cache_key
        from django.core.cache import cache
        
        # Clear common cache patterns
        for cursor in [None, '', '0', '1']:
            for limit in [10, 15, 20, 50]:
                cache_key = tenant_cache_key(f"conversations:{channel_type}:{account_id}:{cursor}:{limit}")
                cache.delete(cache_key)
        
        logger.info(f"Manually invalidated conversation cache for {channel_type}:{account_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to manually invalidate conversation cache: {e}")
        return False