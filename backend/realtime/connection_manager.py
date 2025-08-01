"""
Real-time connection manager for WebSocket connections and user presence
"""
import json
import asyncio
from typing import Dict, Set, Optional, Any
from channels.layers import get_channel_layer
from django.core.cache import cache
from django.contrib.auth import get_user_model
import logging
import time

User = get_user_model()
logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections and user presence"""
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.presence_ttl = 300  # 5 minutes
    
    async def connect_user(self, user_id: int, channel_name: str, connection_info: Dict[str, Any]):
        """Register user connection"""
        connection_key = f"conn:{user_id}:{channel_name}"
        
        # Store connection info
        self.connections[connection_key] = {
            'user_id': user_id,
            'channel_name': channel_name,
            'connected_at': connection_info.get('connected_at'),
            'user_agent': connection_info.get('user_agent'),
            'ip_address': connection_info.get('ip_address'),
            'subscriptions': set(),
            'active_documents': set(),
            'cursor_position': None,
        }
        
        # Update presence in Redis
        await self._update_user_presence(user_id, 'online', {
            'channel_name': channel_name,
            'last_seen': connection_info.get('connected_at'),
            'active_documents': [],
        })
        
        # Broadcast presence change
        await self._broadcast_presence_change(user_id, 'online')
        
        logger.info(f"User {user_id} connected via {channel_name}")
    
    async def disconnect_user(self, user_id: int, channel_name: str):
        """Handle user disconnection"""
        connection_key = f"conn:{user_id}:{channel_name}"
        
        if connection_key in self.connections:
            connection = self.connections[connection_key]
            
            # Clean up subscriptions
            for subscription in connection['subscriptions']:
                await self._unsubscribe(channel_name, subscription)
            
            # Clean up document presence
            for doc_id in connection['active_documents']:
                await self._remove_document_presence(user_id, doc_id)
            
            # Remove connection
            del self.connections[connection_key]
        
        # Check if user has other active connections
        user_connections = [
            conn for conn in self.connections.values() 
            if conn['user_id'] == user_id
        ]
        
        if not user_connections:
            # User is fully offline
            await self._update_user_presence(user_id, 'offline')
            await self._broadcast_presence_change(user_id, 'offline')
        
        logger.info(f"User {user_id} disconnected from {channel_name}")
    
    async def subscribe_to_channel(self, user_id: int, channel_name: str, subscription: str):
        """Subscribe connection to a specific channel"""
        connection_key = f"conn:{user_id}:{channel_name}"
        
        if connection_key in self.connections:
            self.connections[connection_key]['subscriptions'].add(subscription)
            
            # Add to channel group
            await self.channel_layer.group_add(subscription, channel_name)
            
            logger.debug(f"User {user_id} subscribed to {subscription}")
    
    async def update_document_presence(self, user_id: int, channel_name: str, document_id: str, cursor_info: Dict[str, Any]):
        """Update user's document presence and cursor position"""
        connection_key = f"conn:{user_id}:{channel_name}"
        
        if connection_key in self.connections:
            connection = self.connections[connection_key]
            connection['active_documents'].add(document_id)
            connection['cursor_position'] = cursor_info
            
            # Update document presence in Redis
            presence_key = f"doc_presence:{document_id}"
            user_presence = {
                'user_id': user_id,
                'cursor_position': cursor_info,
                'last_active': cursor_info.get('timestamp', time.time()),
                'channel_name': channel_name,
            }
            
            # Store with TTL
            cache.set(f"{presence_key}:{user_id}", user_presence, self.presence_ttl)
            
            # Broadcast cursor update to other document users
            await self._broadcast_cursor_update(document_id, user_id, cursor_info)
    
    async def get_document_presence(self, document_id: str) -> Dict[str, Any]:
        """Get all users currently active in a document"""
        presence_data = {}
        
        # Use cache pattern matching (simplified for this implementation)
        # In production, this would use Redis SCAN for better performance
        pattern_prefix = f"doc_presence:{document_id}:"
        
        # Get all keys from cache that match the pattern
        try:
            from django.core.cache.backends.redis import RedisCache
            if isinstance(cache, RedisCache):
                # Redis-specific implementation
                redis_client = cache._cache.get_client()
                keys = redis_client.keys(f"{pattern_prefix}*")
                
                for key in keys:
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    user_id = key_str.split(':')[-1]
                    user_presence = cache.get(key_str)
                    if user_presence:
                        presence_data[user_id] = user_presence
            else:
                # Fallback for non-Redis cache backends
                # This is less efficient but works with any cache backend
                for i in range(1, 1000):  # Reasonable upper limit
                    key = f"{pattern_prefix}{i}"
                    user_presence = cache.get(key)
                    if user_presence:
                        presence_data[str(i)] = user_presence
        except Exception as e:
            logger.warning(f"Error getting document presence: {e}")
        
        return presence_data
    
    async def broadcast_to_document(self, document_id: str, message: Dict[str, Any], exclude_user: Optional[int] = None):
        """Broadcast message to all users in a document"""
        group_name = f"document:{document_id}"
        
        # Add exclusion info to message
        if exclude_user:
            message['exclude_user'] = exclude_user
        
        await self.channel_layer.group_send(group_name, {
            'type': 'document_message',
            'message': message
        })
    
    async def get_user_connections(self, user_id: int) -> list:
        """Get all active connections for a user"""
        return [
            conn for conn in self.connections.values()
            if conn['user_id'] == user_id
        ]
    
    async def get_online_users(self) -> list:
        """Get list of currently online users"""
        online_users = set()
        for connection in self.connections.values():
            online_users.add(connection['user_id'])
        return list(online_users)
    
    async def _update_user_presence(self, user_id: int, status: str, details: Optional[Dict[str, Any]] = None):
        """Update user presence in Redis"""
        presence_key = f"user_presence:{user_id}"
        presence_data = {
            'status': status,
            'last_updated': time.time(),
            'details': details or {}
        }
        
        cache.set(presence_key, presence_data, self.presence_ttl)
    
    async def _broadcast_presence_change(self, user_id: int, status: str):
        """Broadcast presence change to interested parties"""
        await self.channel_layer.group_send("user_presence", {
            'type': 'presence_change',
            'user_id': user_id,
            'status': status
        })
    
    async def _broadcast_cursor_update(self, document_id: str, user_id: int, cursor_info: Dict[str, Any]):
        """Broadcast cursor position update"""
        await self.channel_layer.group_send(f"document:{document_id}", {
            'type': 'cursor_update',
            'user_id': user_id,
            'cursor_info': cursor_info
        })
    
    async def _remove_document_presence(self, user_id: int, document_id: str):
        """Remove user from document presence"""
        presence_key = f"doc_presence:{document_id}:{user_id}"
        cache.delete(presence_key)
        
        # Broadcast user left document
        await self.channel_layer.group_send(f"document:{document_id}", {
            'type': 'user_left_document',
            'user_id': user_id
        })
    
    async def _unsubscribe(self, channel_name: str, subscription: str):
        """Unsubscribe from a channel"""
        if self.channel_layer:
            await self.channel_layer.group_discard(subscription, channel_name)

# Global connection manager instance
connection_manager = ConnectionManager()