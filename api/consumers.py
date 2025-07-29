import json
import logging
from typing import Dict, Any
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from authentication.permissions import AsyncPermissionManager

logger = logging.getLogger(__name__)
User = get_user_model()


class SSEConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that mimics Server-Sent Events (SSE) behavior.
    Handles GraphQL subscriptions and real-time updates.
    """
    
    async def connect(self):
        """Accept WebSocket connection and authenticate user."""
        await self.accept()
        
        # Get user from scope (set by JWT middleware)
        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)  # Unauthorized
            return
        
        self.permission_manager = AsyncPermissionManager(self.user)
        self.subscriptions = {}  # Track active subscriptions
        
        logger.info(f"SSE connection established for user {self.user.id}")
    
    async def disconnect(self, close_code):
        """Clean up subscriptions on disconnect."""
        for subscription_id in self.subscriptions:
            await self.channel_layer.group_discard(
                self.subscriptions[subscription_id]["group"],
                self.channel_name
            )
        
        logger.info(f"SSE connection closed for user {self.user.id}")
    
    async def receive(self, text_data):
        """Handle incoming subscription requests."""
        try:
            data = json.loads(text_data)
            message_type = data.get("type")
            
            if message_type == "subscribe":
                await self.handle_subscription(data)
            elif message_type == "unsubscribe":
                await self.handle_unsubscription(data)
            elif message_type == "ping":
                await self.send_event("pong", {"timestamp": data.get("timestamp")})
            else:
                await self.send_error("Unknown message type")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON")
        except Exception as e:
            logger.error(f"Error handling SSE message: {e}")
            await self.send_error("Internal error")
    
    async def handle_subscription(self, data: Dict[str, Any]):
        """Handle subscription requests for different event types."""
        subscription_type = data.get("subscription")
        subscription_id = data.get("id", f"{subscription_type}_{id(data)}")
        
        if subscription_type == "record_updates":
            await self.subscribe_to_record_updates(subscription_id, data.get("filters", {}))
        elif subscription_type == "pipeline_updates":
            await self.subscribe_to_pipeline_updates(subscription_id, data.get("filters", {}))
        elif subscription_type == "activity_feed":
            await self.subscribe_to_activity_feed(subscription_id, data.get("filters", {}))
        else:
            await self.send_error(f"Unknown subscription type: {subscription_type}")
            return
        
        await self.send_event("subscription_confirmed", {
            "id": subscription_id,
            "type": subscription_type
        })
    
    async def handle_unsubscription(self, data: Dict[str, Any]):
        """Handle unsubscription requests."""
        subscription_id = data.get("id")
        
        if subscription_id in self.subscriptions:
            subscription_info = self.subscriptions[subscription_id]
            await self.channel_layer.group_discard(
                subscription_info["group"],
                self.channel_name
            )
            del self.subscriptions[subscription_id]
            
            await self.send_event("unsubscription_confirmed", {
                "id": subscription_id
            })
        else:
            await self.send_error(f"Subscription not found: {subscription_id}")
    
    async def subscribe_to_record_updates(self, subscription_id: str, filters: Dict[str, Any]):
        """Subscribe to record update events."""
        group_name = "record_updates"
        
        await self.channel_layer.group_add(group_name, self.channel_name)
        
        self.subscriptions[subscription_id] = {
            "group": group_name,
            "type": "record_updates",
            "filters": filters
        }
    
    async def subscribe_to_pipeline_updates(self, subscription_id: str, filters: Dict[str, Any]):
        """Subscribe to pipeline update events."""
        group_name = "pipeline_updates"
        
        await self.channel_layer.group_add(group_name, self.channel_name)
        
        self.subscriptions[subscription_id] = {
            "group": group_name,
            "type": "pipeline_updates",
            "filters": filters
        }
    
    async def subscribe_to_activity_feed(self, subscription_id: str, filters: Dict[str, Any]):
        """Subscribe to activity feed events."""
        group_name = "activity_feed"
        
        await self.channel_layer.group_add(group_name, self.channel_name)
        
        self.subscriptions[subscription_id] = {
            "group": group_name,
            "type": "activity_feed",
            "filters": filters
        }
    
    async def record_update(self, event):
        """Handle record update events from the channel layer."""
        record_data = event["record"]
        
        # Apply filters from active subscriptions
        for subscription_id, subscription_info in self.subscriptions.items():
            if subscription_info["type"] == "record_updates":
                if await self.should_send_event(record_data, subscription_info["filters"]):
                    await self.send_event("record_update", {
                        "subscription_id": subscription_id,
                        "data": record_data
                    })
    
    async def pipeline_update(self, event):
        """Handle pipeline update events from the channel layer."""
        pipeline_data = event["pipeline"]
        
        for subscription_id, subscription_info in self.subscriptions.items():
            if subscription_info["type"] == "pipeline_updates":
                if await self.should_send_event(pipeline_data, subscription_info["filters"]):
                    await self.send_event("pipeline_update", {
                        "subscription_id": subscription_id,
                        "data": pipeline_data
                    })
    
    async def activity_event(self, event):
        """Handle activity feed events from the channel layer."""
        activity_data = event["event"]
        
        # Check permissions for this activity
        if not await self.permission_manager.can_view_activity(activity_data):
            return
        
        for subscription_id, subscription_info in self.subscriptions.items():
            if subscription_info["type"] == "activity_feed":
                if await self.should_send_event(activity_data, subscription_info["filters"]):
                    await self.send_event("activity_event", {
                        "subscription_id": subscription_id,
                        "data": activity_data
                    })
    
    async def should_send_event(self, event_data: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if event matches subscription filters."""
        if not filters:
            return True
        
        # Apply pipeline filter
        if "pipeline_id" in filters:
            if event_data.get("pipeline_id") != filters["pipeline_id"]:
                return False
        
        # Apply record filter
        if "record_id" in filters:
            if event_data.get("id") != filters["record_id"]:
                return False
        
        # Apply event type filter
        if "event_types" in filters:
            if event_data.get("event_type") not in filters["event_types"]:
                return False
        
        return True
    
    async def send_event(self, event_type: str, data: Dict[str, Any]):
        """Send SSE-formatted event to client."""
        sse_data = {
            "type": event_type,
            "data": data,
            "timestamp": data.get("timestamp") or str(int(json.time() * 1000))
        }
        
        await self.send(text_data=json.dumps(sse_data))
    
    async def send_error(self, message: str):
        """Send error event to client."""
        await self.send_event("error", {"message": message})


class GraphQLSubscriptionConsumer(AsyncWebsocketConsumer):
    """
    Specialized consumer for GraphQL subscriptions.
    Implements GraphQL-over-WebSocket protocol.
    """
    
    async def connect(self):
        """Accept connection and wait for connection init."""
        await self.accept(subprotocol="graphql-ws")
        self.user = self.scope.get("user")
        self.subscriptions = {}
    
    async def disconnect(self, close_code):
        """Clean up all active GraphQL subscriptions."""
        for sub_id in list(self.subscriptions.keys()):
            await self.stop_subscription(sub_id)
    
    async def receive(self, text_data):
        """Handle GraphQL subscription protocol messages."""
        try:
            message = json.loads(text_data)
            message_type = message.get("type")
            
            if message_type == "connection_init":
                await self.send(text_data=json.dumps({
                    "type": "connection_ack"
                }))
            elif message_type == "start":
                await self.start_subscription(message)
            elif message_type == "stop":
                await self.stop_subscription(message.get("id"))
            elif message_type == "connection_terminate":
                await self.close()
                
        except Exception as e:
            logger.error(f"GraphQL subscription error: {e}")
            await self.send(text_data=json.dumps({
                "type": "error",
                "payload": {"message": str(e)}
            }))
    
    async def start_subscription(self, message):
        """Start a GraphQL subscription."""
        sub_id = message.get("id")
        payload = message.get("payload", {})
        query = payload.get("query", "")
        variables = payload.get("variables", {})
        
        # Parse and execute GraphQL subscription
        # This would integrate with your GraphQL schema
        # For now, we'll handle it as a simple event subscription
        
        if "recordUpdates" in query:
            await self.subscribe_to_records(sub_id, variables)
        elif "pipelineUpdates" in query:
            await self.subscribe_to_pipelines(sub_id, variables)
        
        self.subscriptions[sub_id] = {
            "query": query,
            "variables": variables
        }
    
    async def stop_subscription(self, sub_id):
        """Stop a GraphQL subscription."""
        if sub_id in self.subscriptions:
            # Clean up subscription resources
            del self.subscriptions[sub_id]
            
            await self.send(text_data=json.dumps({
                "type": "complete",
                "id": sub_id
            }))
    
    async def subscribe_to_records(self, sub_id, variables):
        """Subscribe to record updates for GraphQL."""
        await self.channel_layer.group_add("record_updates", self.channel_name)
    
    async def subscribe_to_pipelines(self, sub_id, variables):
        """Subscribe to pipeline updates for GraphQL."""
        await self.channel_layer.group_add("pipeline_updates", self.channel_name)
    
    async def record_update(self, event):
        """Send record update as GraphQL subscription data."""
        for sub_id, subscription in self.subscriptions.items():
            if "recordUpdates" in subscription["query"]:
                await self.send(text_data=json.dumps({
                    "type": "data",
                    "id": sub_id,
                    "payload": {
                        "data": {
                            "recordUpdates": event["record"]
                        }
                    }
                }))
    
    async def pipeline_update(self, event):
        """Send pipeline update as GraphQL subscription data."""
        for sub_id, subscription in self.subscriptions.items():
            if "pipelineUpdates" in subscription["query"]:
                await self.send(text_data=json.dumps({
                    "type": "data",
                    "id": sub_id,
                    "payload": {
                        "data": {
                            "pipelineUpdates": event["pipeline"]
                        }
                    }
                }))