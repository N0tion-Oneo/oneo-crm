"""
Signal handlers for real-time feature integration
"""
import json
import time
import asyncio
from threading import Thread
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)


def safe_group_send_sync(channel_layer, group_name, message):
    """
    Safely send message to channel group from sync context.
    Handles event loop issues properly.
    """
    try:
        # Simple approach: use async_to_sync directly with the coroutine
        async_to_sync(channel_layer.group_send)(group_name, message)
        logger.debug(f"Sent message to group {group_name}: {message.get('type', 'unknown')}")
    except Exception as e:
        logger.error(f"Failed to send message to group {group_name}: {e}")
        # Try alternative approach if the first fails
        try:
            import asyncio
            asyncio.run(channel_layer.group_send(group_name, message))
            logger.debug(f"Sent message to group {group_name} (fallback): {message.get('type', 'unknown')}")
        except Exception as e2:
            logger.error(f"Fallback also failed for group {group_name}: {e2}")


async def safe_group_send(channel_layer, group_name, message):
    """Safely send message to channel group"""
    try:
        await channel_layer.group_send(group_name, message)
        logger.debug(f"Sent message to group {group_name}: {message.get('type', 'unknown')}")
    except Exception as e:
        logger.error(f"Failed to send message to group {group_name}: {e}")


# Import models when they're available
try:
    from pipelines.models import Pipeline, Record, Field
    from relationships.models import Relationship
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    logger.warning("Pipeline/Relationship models not available for real-time signals")

if MODELS_AVAILABLE:
    
    @receiver(post_save, sender=Record)
    def handle_record_saved(sender, instance, created, **kwargs):
        """Handle record creation/update/soft deletion for real-time broadcasting"""
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                return
            
            # Get updated record count for the pipeline (exclude soft deleted)
            new_record_count = Record.objects.filter(pipeline_id=instance.pipeline_id, is_deleted=False).count()
            
            # Check if this is a soft deletion
            if not created and instance.is_deleted:
                # This is a soft deletion - broadcast as record_deleted
                event_data = {
                    'type': 'record_deleted',
                    'record_id': str(instance.id),
                    'pipeline_id': str(instance.pipeline_id),
                    'title': getattr(instance, 'title', f'Record {instance.id}'),
                    'new_count': new_record_count,  # Updated count after deletion
                    'timestamp': time.time()
                }
                
                # Broadcast to pipeline subscribers
                pipeline_group = f"pipeline_records_{instance.pipeline_id}"
                safe_group_send_sync(channel_layer, pipeline_group, {
                    'type': 'record_deleted',
                    'data': event_data
                })
                
                # Broadcast to document subscribers
                document_group = f"document_{instance.id}"
                safe_group_send_sync(channel_layer, document_group, {
                    'type': 'document_deleted',
                    'data': event_data
                })
                
                # Store for SSE subscribers
                store_sse_message(
                    f"pipeline_records_{instance.pipeline_id}",
                    event_data
                )
                
                logger.debug(f"Broadcasted record soft deleted: {instance.id}")
                return
            
            # Handle normal creation/update (not soft deletion)
            if not instance.is_deleted:  # Only broadcast if record is not deleted
                print(f"🟢 DATABASE STEP 4: WebSocket Broadcasting")
                print(f"   📡 Broadcasting record {instance.id} update")
                print(f"   📦 Data being broadcast: {instance.data}")
                if instance.data:
                    print(f"   🔑 Broadcast contains {len(instance.data)} field(s): [{', '.join(instance.data.keys())}]")
                    null_fields = [k for k, v in instance.data.items() if v is None]
                    if null_fields:
                        print(f"   ⚠️  Broadcast contains {len(null_fields)} NULL fields: [{', '.join(null_fields)}]")
                
                # Create event data
                event_data = {
                    'type': 'record_created' if created else 'record_updated',
                    'record_id': str(instance.id),
                    'pipeline_id': str(instance.pipeline_id),
                    'title': getattr(instance, 'title', f'Record {instance.id}'),
                    'data': instance.data,  # Use the actual saved data, not cleaned data
                    'updated_at': instance.updated_at.isoformat() if instance.updated_at else None,
                    'updated_by': {
                        'id': instance.updated_by.id if instance.updated_by else None,
                        'username': instance.updated_by.username if instance.updated_by else None,
                    },
                    'new_count': new_record_count,  # Add the updated count
                    'timestamp': time.time()
                }
                
                print(f"   🔍 SIGNAL DEBUG: Broadcasting data vs saved data")
                print(f"   📡 Broadcasting: {instance.data}")
                print(f"   🎯 Should contain all saved fields including new ones")
                
                # Broadcast to pipeline subscribers
                pipeline_group = f"pipeline_records_{instance.pipeline_id}"
                safe_group_send_sync(channel_layer, pipeline_group, {
                    'type': 'record_update',
                    'data': event_data
                })
                
                # Broadcast to document subscribers (for collaborative editing)
                document_group = f"document_{instance.id}"
                safe_group_send_sync(channel_layer, document_group, {
                    'type': 'document_updated',
                    'data': event_data
                })
                
                # Store for SSE subscribers
                store_sse_message(
                    f"pipeline_records_{instance.pipeline_id}",
                    event_data
                )
                
                # Store activity
                store_activity_event({
                    'type': 'record_activity',
                    'action': 'created' if created else 'updated',
                    'record_id': str(instance.id),
                    'pipeline_id': str(instance.pipeline_id),
                    'user_id': instance.updated_by.id if instance.updated_by else None,
                    'timestamp': time.time()
                })
                
                logger.debug(f"Broadcasted record {'created' if created else 'updated'}: {instance.id}")
            
        except Exception as e:
            logger.error(f"Error handling record save signal: {e}")
    
    
    @receiver(post_delete, sender=Record)
    def handle_record_deleted(sender, instance, **kwargs):
        """Handle record deletion for real-time broadcasting"""
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                return
            
            # Get updated record count for the pipeline (after deletion)
            new_record_count = Record.objects.filter(pipeline_id=instance.pipeline_id).count()
            
            # Create event data
            event_data = {
                'type': 'record_deleted',
                'record_id': str(instance.id),
                'pipeline_id': str(instance.pipeline_id),
                'title': getattr(instance, 'title', f'Record {instance.id}'),
                'new_count': new_record_count,  # Add the updated count
                'timestamp': time.time()
            }
            
            # Broadcast to pipeline subscribers
            pipeline_group = f"pipeline_records_{instance.pipeline_id}"
            safe_group_send_sync(channel_layer, pipeline_group, {
                'type': 'record_deleted',
                'data': event_data
            })
            
            # Broadcast to document subscribers
            document_group = f"document_{instance.id}"
            safe_group_send_sync(channel_layer, document_group, {
                'type': 'document_deleted',
                'data': event_data
            })
            
            # Store for SSE subscribers
            store_sse_message(
                f"pipeline_records_{instance.pipeline_id}",
                event_data
            )
            
            logger.debug(f"Broadcasted record deleted: {instance.id}")
            
        except Exception as e:
            logger.error(f"Error handling record delete signal: {e}")
    
    
    @receiver(post_save, sender=Pipeline)
    def handle_pipeline_saved(sender, instance, created, **kwargs):
        """Handle pipeline creation/update for real-time broadcasting"""
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                return
            
            # Create event data
            event_data = {
                'type': 'pipeline_created' if created else 'pipeline_updated',
                'pipeline_id': str(instance.id),
                'name': instance.name,
                'description': instance.description,
                'pipeline_type': getattr(instance, 'pipeline_type', 'custom'),
                'is_active': getattr(instance, 'is_active', True),
                'timestamp': time.time()
            }
            
            # Broadcast to general pipeline subscribers
            safe_group_send_sync(channel_layer, "pipeline_updates", {
                'type': 'pipeline_update',
                'data': event_data
            })
            
            # Broadcast to specific pipeline subscribers
            pipeline_group = f"pipeline_updates_{instance.id}"
            safe_group_send_sync(channel_layer, pipeline_group, {
                'type': 'pipeline_update',
                'data': event_data
            })
            
            # Store for SSE subscribers
            store_sse_message("global_activity", event_data)
            
            logger.debug(f"Broadcasted pipeline {'created' if created else 'updated'}: {instance.id}")
            
        except Exception as e:
            logger.error(f"Error handling pipeline save signal: {e}")
    
    
    @receiver(post_save, sender=Relationship)
    def handle_relationship_saved(sender, instance, created, **kwargs):
        """Handle relationship creation for real-time broadcasting"""
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                return
            
            # Create event data
            event_data = {
                'type': 'relationship_created' if created else 'relationship_updated',
                'relationship_id': str(instance.id),
                'source_record_id': str(instance.source_record_id),
                'target_record_id': str(instance.target_record_id),
                'relationship_type': str(instance.relationship_type_id),
                'strength': float(instance.strength) if hasattr(instance, 'strength') else 1.0,
                'timestamp': time.time()
            }
            
            # Broadcast to relationship subscribers
            safe_group_send_sync(channel_layer, "relationship_updates", {
                'type': 'relationship_update',
                'data': event_data
            })
            
            # Broadcast to both record documents
            for record_id in [instance.source_record_id, instance.target_record_id]:
                document_group = f"document_{record_id}"
                safe_group_send_sync(channel_layer, document_group, {
                    'type': 'relationship_update',
                    'data': event_data
                })
            
            logger.debug(f"Broadcasted relationship {'created' if created else 'updated'}: {instance.id}")
            
        except Exception as e:
            logger.error(f"Error handling relationship save signal: {e}")


def store_sse_message(channel: str, event_data: dict):
    """Store message for SSE subscribers"""
    try:
        # This is a simplified approach - in production, you'd want to 
        # maintain subscriber lists and send to specific users
        message_key = f"sse_channel_messages:{channel}"
        messages = cache.get(message_key, [])
        
        messages.append({
            'type': event_data.get('type', 'update'),
            'data': event_data,
            'timestamp': time.time()
        })
        
        # Keep only recent messages
        if len(messages) > 100:
            messages = messages[-100:]
        
        cache.set(message_key, messages, 600)  # 10 minute TTL
        
    except Exception as e:
        logger.error(f"Error storing SSE message: {e}")


def store_activity_event(activity_data: dict):
    """Store activity event for activity feeds"""
    try:
        # Store global activity
        global_activity_key = "recent_activity:global"
        activities = cache.get(global_activity_key, [])
        
        activities.append(activity_data)
        
        # Keep only recent activities
        if len(activities) > 50:
            activities = activities[-50:]
        
        cache.set(global_activity_key, activities, 1800)  # 30 minute TTL
        
        # Store user-specific activity if user is specified
        if activity_data.get('user_id'):
            user_activity_key = f"recent_activity:{activity_data['user_id']}"
            user_activities = cache.get(user_activity_key, [])
            user_activities.append(activity_data)
            
            if len(user_activities) > 20:
                user_activities = user_activities[-20:]
            
            cache.set(user_activity_key, user_activities, 1800)
        
    except Exception as e:
        logger.error(f"Error storing activity event: {e}")


# Additional utility functions for real-time features
def broadcast_user_notification(user_id: int, notification_data: dict):
    """Broadcast notification to specific user"""
    try:
        # Store for SSE
        message_key = f"sse_messages:{user_id}:user_notifications:{user_id}"
        messages = cache.get(message_key, [])
        
        messages.append({
            'type': 'notification',
            'data': notification_data,
            'timestamp': time.time()
        })
        
        if len(messages) > 20:
            messages = messages[-20:]
        
        cache.set(message_key, messages, 600)
        
        # Update unread count
        unread_key = f"unread_notifications:{user_id}"
        current_count = cache.get(unread_key, 0)
        cache.set(unread_key, current_count + 1, 3600)
        
        logger.debug(f"Broadcasted notification to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting user notification: {e}")


def broadcast_system_announcement(announcement_data: dict):
    """Broadcast system-wide announcement"""
    try:
        # Store for all SSE subscribers
        message_key = "sse_channel_messages:system_notifications"
        messages = cache.get(message_key, [])
        
        messages.append({
            'type': 'system_announcement',
            'data': announcement_data,
            'timestamp': time.time()
        })
        
        if len(messages) > 10:
            messages = messages[-10:]
        
        cache.set(message_key, messages, 1800)
        
        logger.info("Broadcasted system announcement")
        
    except Exception as e:
        logger.error(f"Error broadcasting system announcement: {e}")