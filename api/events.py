import json
import logging
from typing import Dict, Any, Optional, List
from django.utils import timezone
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from pipelines.models import Pipeline, Record
from relationships.models import Relationship

logger = logging.getLogger(__name__)
User = get_user_model()


class EventBroadcaster:
    """
    Central event broadcasting system for real-time updates.
    Handles both SSE and WebSocket event distribution.
    """
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    async def broadcast_record_update(
        self, 
        record: Record, 
        event_type: str = "updated",
        user_id: Optional[int] = None,
        changes: Optional[Dict[str, Any]] = None
    ):
        """
        Broadcast record update events to all subscribers.
        """
        try:
            event_data = {
                "type": "record.update",
                "record": {
                    "id": str(record.id),
                    "pipeline_id": str(record.pipeline.id),
                    "data": record.data,
                    "updated_at": record.updated_at.isoformat(),
                    "event_type": event_type,
                    "changes": changes or {},
                    "user_id": user_id
                },
                "timestamp": timezone.now().isoformat()
            }
            
            # Broadcast to record update subscribers
            await self.channel_layer.group_send(
                "record_updates",
                event_data
            )
            
            # Also broadcast to activity feed
            await self.broadcast_activity_event({
                "type": "record_update",
                "record_id": str(record.id),
                "pipeline_id": str(record.pipeline.id),
                "event_type": event_type,
                "user_id": user_id,
                "timestamp": timezone.now().isoformat(),
                "changes": changes
            })
            
            logger.info(f"Broadcasted record {event_type} event for record {record.id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast record update: {e}")
    
    async def broadcast_pipeline_update(
        self, 
        pipeline: Pipeline, 
        event_type: str = "updated",
        user_id: Optional[int] = None,
        changes: Optional[Dict[str, Any]] = None
    ):
        """
        Broadcast pipeline update events to all subscribers.
        """
        try:
            event_data = {
                "type": "pipeline.update",
                "pipeline": {
                    "id": str(pipeline.id),
                    "name": pipeline.name,
                    "updated_at": pipeline.updated_at.isoformat(),
                    "event_type": event_type,
                    "changes": changes or {},
                    "user_id": user_id
                },
                "timestamp": timezone.now().isoformat()
            }
            
            await self.channel_layer.group_send(
                "pipeline_updates",
                event_data
            )
            
            # Also broadcast to activity feed
            await self.broadcast_activity_event({
                "type": "pipeline_update",
                "pipeline_id": str(pipeline.id),
                "event_type": event_type,
                "user_id": user_id,
                "timestamp": timezone.now().isoformat(),
                "changes": changes
            })
            
            logger.info(f"Broadcasted pipeline {event_type} event for pipeline {pipeline.id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast pipeline update: {e}")
    
    async def broadcast_relationship_update(
        self,
        relationship: Relationship,
        event_type: str = "updated",
        user_id: Optional[int] = None
    ):
        """
        Broadcast relationship update events.
        """
        try:
            event_data = {
                "type": "relationship.update",
                "relationship": {
                    "id": str(relationship.id),
                    "from_record_id": str(relationship.from_record.id),
                    "to_record_id": str(relationship.to_record.id),
                    "relationship_type": relationship.relationship_type,
                    "event_type": event_type,
                    "user_id": user_id
                },
                "timestamp": timezone.now().isoformat()
            }
            
            # Broadcast to both related records' pipeline subscribers
            await self.channel_layer.group_send(
                "record_updates",
                event_data
            )
            
            await self.broadcast_activity_event({
                "type": "relationship_update",
                "relationship_id": str(relationship.id),
                "from_record_id": str(relationship.from_record.id),
                "to_record_id": str(relationship.to_record.id),
                "event_type": event_type,
                "user_id": user_id,
                "timestamp": timezone.now().isoformat()
            })
            
            logger.info(f"Broadcasted relationship {event_type} event for relationship {relationship.id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast relationship update: {e}")
    
    async def broadcast_activity_event(self, event_data: Dict[str, Any]):
        """
        Broadcast activity event to activity feed subscribers.
        """
        try:
            activity_event = {
                "type": "activity.event",
                "event": event_data
            }
            
            await self.channel_layer.group_send(
                "activity_feed",
                activity_event
            )
            
            # Store recent activity in cache for new subscribers
            cache_key = "recent_activity"
            recent_activities = cache.get(cache_key, [])
            recent_activities.append(event_data)
            
            # Keep only last 100 activities
            if len(recent_activities) > 100:
                recent_activities = recent_activities[-100:]
            
            cache.set(cache_key, recent_activities, timeout=3600)  # 1 hour
            
        except Exception as e:
            logger.error(f"Failed to broadcast activity event: {e}")
    
    def sync_broadcast_record_update(self, *args, **kwargs):
        """Synchronous wrapper for record update broadcasting."""
        return async_to_sync(self.broadcast_record_update)(*args, **kwargs)
    
    def sync_broadcast_pipeline_update(self, *args, **kwargs):
        """Synchronous wrapper for pipeline update broadcasting."""
        return async_to_sync(self.broadcast_pipeline_update)(*args, **kwargs)
    
    def sync_broadcast_relationship_update(self, *args, **kwargs):
        """Synchronous wrapper for relationship update broadcasting."""
        return async_to_sync(self.broadcast_relationship_update)(*args, **kwargs)


# Global broadcaster instance
broadcaster = EventBroadcaster()


class RealtimeEventMixin:
    """
    Mixin for Django models to automatically broadcast updates.
    """
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_data = None
        
        # Capture changes for existing objects
        if not is_new and hasattr(self, '_get_field_changes'):
            old_data = self._get_field_changes()
        
        super().save(*args, **kwargs)
        
        # Broadcast the update
        self._broadcast_update(
            event_type="created" if is_new else "updated",
            changes=old_data,
            user_id=getattr(self, '_current_user_id', None)
        )
    
    def delete(self, *args, **kwargs):
        self._broadcast_update(
            event_type="deleted",
            user_id=getattr(self, '_current_user_id', None)
        )
        super().delete(*args, **kwargs)
    
    def _broadcast_update(self, event_type: str, changes: Optional[Dict] = None, user_id: Optional[int] = None):
        """Override in subclasses to define specific broadcasting logic."""
        pass
    
    def set_current_user(self, user):
        """Set the current user for tracking who made changes."""
        self._current_user_id = user.id if user else None