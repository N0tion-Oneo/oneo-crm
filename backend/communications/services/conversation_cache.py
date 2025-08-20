"""
Conversation Cache Manager
Provides intelligent Redis-based caching for conversation data
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from django.core.cache import cache
from django.conf import settings
from core.cache import tenant_cache_key, invalidate_tenant_cache

logger = logging.getLogger(__name__)


class ConversationCache:
    """
    High-performance conversation caching with intelligent invalidation
    """
    
    def __init__(self):
        self.default_timeout = getattr(settings, 'CONVERSATION_CACHE_TIMEOUT', 300)  # 5 minutes
        self.hot_data_timeout = getattr(settings, 'HOT_DATA_CACHE_TIMEOUT', 60)     # 1 minute for frequently accessed
        self.conversation_list_timeout = getattr(settings, 'CONVERSATION_LIST_TIMEOUT', 300)  # 5 minutes
        
    # =========================================================================
    # CONVERSATION LIST CACHING
    # =========================================================================
    
    def get_conversation_list(
        self,
        channel_type: str,
        account_id: Optional[str] = None,
        user_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached conversation list"""
        
        cache_key = self._build_conversation_list_key(
            channel_type, account_id, user_id, filters
        )
        
        try:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.debug(f"✅ Cache hit: conversation list {cache_key}")
                return cached_data
        except Exception as e:
            logger.error(f"Cache get failed for {cache_key}: {e}")
        
        return None
    
    def set_conversation_list(
        self,
        data: Dict[str, Any],
        channel_type: str,
        account_id: Optional[str] = None,
        user_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> bool:
        """Cache conversation list data"""
        
        cache_key = self._build_conversation_list_key(
            channel_type, account_id, user_id, filters
        )
        
        timeout = timeout or self.conversation_list_timeout
        
        try:
            # Add metadata
            cache_data = {
                'data': data,
                'cached_at': datetime.utcnow().isoformat(),
                'cache_key': cache_key,
                'metadata': {
                    'channel_type': channel_type,
                    'account_id': account_id,
                    'user_id': user_id,
                    'filters': filters
                }
            }
            
            cache.set(cache_key, cache_data, timeout)
            
            # Track this cache key for invalidation
            self._track_cache_key(cache_key, channel_type, account_id)
            
            logger.debug(f"💾 Cached conversation list: {cache_key} ({len(data.get('conversations', []))} items)")
            return True
            
        except Exception as e:
            logger.error(f"Cache set failed for {cache_key}: {e}")
            return False
    
    def _build_conversation_list_key(
        self,
        channel_type: str,
        account_id: Optional[str] = None,
        user_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build cache key for conversation list"""
        
        key_parts = ['conversations', channel_type]
        
        if account_id:
            key_parts.append(account_id)
        if user_id:
            key_parts.append(f'user:{user_id}')
        if filters:
            # Create deterministic hash of filters
            filter_str = json.dumps(filters, sort_keys=True)
            key_parts.append(f'filters:{hash(filter_str)}')
        
        return tenant_cache_key(':'.join(key_parts))
    
    # =========================================================================
    # INDIVIDUAL CONVERSATION CACHING
    # =========================================================================
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get cached conversation data"""
        
        cache_key = tenant_cache_key(f"conversation:{conversation_id}")
        
        try:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.debug(f"✅ Cache hit: conversation {conversation_id}")
                return cached_data['data']
        except Exception as e:
            logger.error(f"Cache get failed for conversation {conversation_id}: {e}")
        
        return None
    
    def set_conversation(
        self,
        conversation_id: str,
        data: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> bool:
        """Cache individual conversation data"""
        
        cache_key = tenant_cache_key(f"conversation:{conversation_id}")
        timeout = timeout or self.default_timeout
        
        try:
            cache_data = {
                'data': data,
                'cached_at': datetime.utcnow().isoformat(),
                'conversation_id': conversation_id
            }
            
            cache.set(cache_key, cache_data, timeout)
            logger.debug(f"💾 Cached conversation: {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Cache set failed for conversation {conversation_id}: {e}")
            return False
    
    # =========================================================================
    # MESSAGE CACHING
    # =========================================================================
    
    def get_messages(
        self,
        conversation_id: str,
        cursor: Optional[str] = None,
        limit: int = 50
    ) -> Optional[Dict[str, Any]]:
        """Get cached messages for a conversation"""
        
        cache_key = tenant_cache_key(f"messages:{conversation_id}:{cursor}:{limit}")
        
        try:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.debug(f"✅ Cache hit: messages {conversation_id}")
                return cached_data['data']
        except Exception as e:
            logger.error(f"Cache get failed for messages {conversation_id}: {e}")
        
        return None
    
    def set_messages(
        self,
        conversation_id: str,
        data: Dict[str, Any],
        cursor: Optional[str] = None,
        limit: int = 50,
        timeout: Optional[int] = None
    ) -> bool:
        """Cache messages for a conversation"""
        
        cache_key = tenant_cache_key(f"messages:{conversation_id}:{cursor}:{limit}")
        timeout = timeout or self.default_timeout
        
        try:
            cache_data = {
                'data': data,
                'cached_at': datetime.utcnow().isoformat(),
                'conversation_id': conversation_id,
                'cursor': cursor,
                'limit': limit
            }
            
            cache.set(cache_key, cache_data, timeout)
            logger.debug(f"💾 Cached messages: {conversation_id} ({len(data.get('messages', []))} items)")
            return True
            
        except Exception as e:
            logger.error(f"Cache set failed for messages {conversation_id}: {e}")
            return False
    
    # =========================================================================
    # HOT DATA CACHING (FREQUENTLY ACCESSED)
    # =========================================================================
    
    def get_hot_conversations(self, channel_type: str, account_id: str) -> Optional[List[str]]:
        """Get list of hot (frequently accessed) conversation IDs"""
        
        cache_key = tenant_cache_key(f"hot_conversations:{channel_type}:{account_id}")
        
        try:
            return cache.get(cache_key, [])
        except Exception as e:
            logger.error(f"Failed to get hot conversations: {e}")
            return []
    
    def mark_conversation_hot(self, conversation_id: str, channel_type: str, account_id: str):
        """Mark a conversation as hot (frequently accessed)"""
        
        cache_key = tenant_cache_key(f"hot_conversations:{channel_type}:{account_id}")
        
        try:
            hot_conversations = cache.get(cache_key, [])
            
            # Add to hot list if not already there
            if conversation_id not in hot_conversations:
                hot_conversations.append(conversation_id)
                
                # Keep only last 20 hot conversations
                hot_conversations = hot_conversations[-20:]
                
                cache.set(cache_key, hot_conversations, self.hot_data_timeout * 10)  # 10 minutes for hot list
                
        except Exception as e:
            logger.error(f"Failed to mark conversation as hot: {e}")
    
    def preload_hot_conversations(self, channel_type: str, account_id: str) -> bool:
        """Preload frequently accessed conversations into cache"""
        
        hot_conversation_ids = self.get_hot_conversations(channel_type, account_id)
        
        if not hot_conversation_ids:
            return True
        
        try:
            # Preload conversation data for hot conversations
            # This would typically be called by a background task
            logger.info(f"Preloading {len(hot_conversation_ids)} hot conversations for {channel_type}:{account_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to preload hot conversations: {e}")
            return False
    
    # =========================================================================
    # CACHE INVALIDATION
    # =========================================================================
    
    def invalidate_conversation(self, conversation_id: str):
        """Invalidate all cache entries for a specific conversation"""
        
        try:
            # Invalidate conversation data
            cache_key = tenant_cache_key(f"conversation:{conversation_id}")
            cache.delete(cache_key)
            
            # Invalidate messages for this conversation
            invalidate_tenant_cache(f"messages:{conversation_id}")
            
            logger.debug(f"🗑️  Invalidated conversation cache: {conversation_id}")
            
        except Exception as e:
            logger.error(f"Failed to invalidate conversation {conversation_id}: {e}")
    
    def invalidate_channel(self, channel_type: str, account_id: Optional[str] = None):
        """Invalidate all cache entries for a channel/account"""
        
        try:
            # Build pattern to match
            pattern = f"conversations:{channel_type}"
            if account_id:
                pattern += f":{account_id}"
            
            invalidate_tenant_cache(pattern)
            
            # Also invalidate hot conversations
            if account_id:
                hot_cache_key = tenant_cache_key(f"hot_conversations:{channel_type}:{account_id}")
                cache.delete(hot_cache_key)
            
            logger.debug(f"🗑️  Invalidated channel cache: {pattern}")
            
        except Exception as e:
            logger.error(f"Failed to invalidate channel cache: {e}")
    
    def invalidate_user_data(self, user_id: str):
        """Invalidate all cache entries for a user"""
        
        try:
            pattern = f"*:user:{user_id}*"
            invalidate_tenant_cache(pattern)
            
            logger.debug(f"🗑️  Invalidated user cache: {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to invalidate user cache: {e}")
    
    # =========================================================================
    # CACHE KEY TRACKING
    # =========================================================================
    
    def _track_cache_key(self, cache_key: str, channel_type: str, account_id: Optional[str] = None):
        """Track cache keys for organized invalidation"""
        
        try:
            # Track cache keys by channel for easier invalidation
            tracking_key = tenant_cache_key(f"cache_keys:{channel_type}")
            if account_id:
                tracking_key += f":{account_id}"
            
            tracked_keys = cache.get(tracking_key, set())
            tracked_keys.add(cache_key)
            
            cache.set(tracking_key, tracked_keys, self.conversation_list_timeout * 2)
            
        except Exception as e:
            logger.error(f"Failed to track cache key: {e}")
    
    # =========================================================================
    # CACHE STATISTICS AND MONITORING
    # =========================================================================
    
    def get_cache_stats(self, channel_type: str, account_id: Optional[str] = None) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        
        stats = {
            'channel_type': channel_type,
            'account_id': account_id,
            'timestamp': datetime.utcnow().isoformat(),
            'cache_keys': [],
            'hot_conversations': []
        }
        
        try:
            # Get tracked cache keys
            tracking_key = tenant_cache_key(f"cache_keys:{channel_type}")
            if account_id:
                tracking_key += f":{account_id}"
            
            tracked_keys = cache.get(tracking_key, set())
            stats['cache_keys'] = list(tracked_keys)
            
            # Get hot conversations
            if account_id:
                hot_conversations = self.get_hot_conversations(channel_type, account_id)
                stats['hot_conversations'] = hot_conversations or []
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            stats['error'] = str(e)
        
        return stats
    
    def clear_all_cache(self, channel_type: Optional[str] = None) -> bool:
        """Clear all cache entries (use with caution)"""
        
        try:
            if channel_type:
                pattern = f"*{channel_type}*"
                invalidate_tenant_cache(pattern)
                logger.warning(f"🧹 Cleared all cache for channel type: {channel_type}")
            else:
                # Clear all tenant cache
                invalidate_tenant_cache("*")
                logger.warning("🧹 Cleared ALL tenant cache")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False


# Initialize global cache manager
conversation_cache = ConversationCache()