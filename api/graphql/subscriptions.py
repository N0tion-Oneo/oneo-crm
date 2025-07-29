import strawberry
import asyncio
from typing import AsyncGenerator, Optional
from django.core.cache import cache
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async
from pipelines.models import Pipeline, Record
from authentication.permissions import AsyncPermissionManager
from .strawberry_schema import PipelineType, RecordType


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def record_updates(
        self, 
        info,
        pipeline_id: Optional[str] = None,
        record_id: Optional[str] = None
    ) -> AsyncGenerator[RecordType, None]:
        """
        Subscribe to real-time record updates using SSE-compatible streaming.
        Filters by pipeline_id and/or record_id if provided.
        """
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        # Create unique subscription channel for this user session
        channel_layer = get_channel_layer()
        subscription_id = f"record_updates_{user.id}_{id(info.context)}"
        
        try:
            # Join subscription group
            await channel_layer.group_add("record_updates", subscription_id)
            
            # Send initial state if specific record requested
            if record_id:
                try:
                    record = await sync_to_async(Record.objects.get)(
                        id=record_id, is_deleted=False
                    )
                    # Check permissions
                    perm_manager = AsyncPermissionManager(user)
                    if await perm_manager.can_view_record(record):
                        yield RecordType.from_model(record)
                except Record.DoesNotExist:
                    pass
            
            # Listen for updates
            while True:
                try:
                    # Check for messages in Redis channel
                    message = await channel_layer.receive(subscription_id)
                    
                    if message["type"] == "record.update":
                        record_data = message["record"]
                        
                        # Apply filters
                        if pipeline_id and record_data["pipeline_id"] != pipeline_id:
                            continue
                        if record_id and record_data["id"] != record_id:
                            continue
                        
                        # Check permissions
                        perm_manager = AsyncPermissionManager(user)
                        record = await sync_to_async(Record.objects.get)(
                            id=record_data["id"]
                        )
                        if await perm_manager.can_view_record(record):
                            yield RecordType.from_model(record)
                            
                except asyncio.TimeoutError:
                    # Send keepalive every 30 seconds
                    await asyncio.sleep(30)
                    continue
                except Exception as e:
                    break
                    
        finally:
            # Clean up subscription
            await channel_layer.group_discard("record_updates", subscription_id)

    @strawberry.subscription
    async def pipeline_updates(
        self, 
        info,
        pipeline_id: Optional[str] = None
    ) -> AsyncGenerator[PipelineType, None]:
        """
        Subscribe to real-time pipeline structure and analytics updates.
        """
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        channel_layer = get_channel_layer()
        subscription_id = f"pipeline_updates_{user.id}_{id(info.context)}"
        
        try:
            await channel_layer.group_add("pipeline_updates", subscription_id)
            
            # Send initial state if specific pipeline requested
            if pipeline_id:
                try:
                    pipeline = await sync_to_async(Pipeline.objects.get)(
                        id=pipeline_id, is_deleted=False
                    )
                    perm_manager = AsyncPermissionManager(user)
                    if await perm_manager.can_view_pipeline(pipeline):
                        yield PipelineType.from_model(pipeline)
                except Pipeline.DoesNotExist:
                    pass
            
            while True:
                try:
                    message = await channel_layer.receive(subscription_id)
                    
                    if message["type"] == "pipeline.update":
                        pipeline_data = message["pipeline"]
                        
                        if pipeline_id and pipeline_data["id"] != pipeline_id:
                            continue
                        
                        perm_manager = AsyncPermissionManager(user)
                        pipeline = await sync_to_async(Pipeline.objects.get)(
                            id=pipeline_data["id"]
                        )
                        if await perm_manager.can_view_pipeline(pipeline):
                            yield PipelineType.from_model(pipeline)
                            
                except asyncio.TimeoutError:
                    await asyncio.sleep(30)
                    continue
                except Exception:
                    break
                    
        finally:
            await channel_layer.group_discard("pipeline_updates", subscription_id)

    @strawberry.subscription
    async def activity_feed(
        self, 
        info,
        pipeline_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Subscribe to real-time activity feed updates.
        Returns JSON-formatted activity events.
        """
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        channel_layer = get_channel_layer()
        subscription_id = f"activity_feed_{user.id}_{id(info.context)}"
        
        try:
            await channel_layer.group_add("activity_feed", subscription_id)
            
            while True:
                try:
                    message = await channel_layer.receive(subscription_id)
                    
                    if message["type"] == "activity.event":
                        event_data = message["event"]
                        
                        if pipeline_id and event_data.get("pipeline_id") != pipeline_id:
                            continue
                        
                        # Check if user has permission to see this activity
                        perm_manager = AsyncPermissionManager(user)
                        if await perm_manager.can_view_activity(event_data):
                            import json
                            yield json.dumps(event_data)
                            
                except asyncio.TimeoutError:
                    await asyncio.sleep(30)
                    continue
                except Exception:
                    break
                    
        finally:
            await channel_layer.group_discard("activity_feed", subscription_id)