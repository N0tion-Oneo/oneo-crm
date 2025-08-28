"""
Email cache manager for fast pagination
Caches email threads in Redis for quick access
"""
import json
import logging
from typing import Dict, List, Any, Optional
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class EmailCacheManager:
    """Manages caching of email threads for fast pagination"""
    
    CACHE_TTL = 300  # 5 minutes
    
    @classmethod
    def get_cache_key(cls, account_id: str, folder: str = "INBOX") -> str:
        """Generate cache key for email threads"""
        return f"email_threads:{account_id}:{folder}"
    
    @classmethod
    def get_cursor_key(cls, account_id: str, folder: str = "INBOX") -> str:
        """Generate cache key for pagination cursor"""
        return f"email_cursor:{account_id}:{folder}"
    
    @classmethod
    def cache_threads(cls, account_id: str, threads: List[Dict], folder: str = "INBOX") -> None:
        """Cache email threads"""
        try:
            cache_key = cls.get_cache_key(account_id, folder)
            # Store as JSON string to ensure serialization
            cache.set(cache_key, json.dumps(threads), cls.CACHE_TTL)
            logger.info(f"Cached {len(threads)} threads for account {account_id}")
        except Exception as e:
            logger.error(f"Failed to cache threads: {e}")
    
    @classmethod
    def get_cached_threads(cls, account_id: str, folder: str = "INBOX", 
                          offset: int = 0, limit: int = 20) -> Optional[List[Dict]]:
        """Get cached threads with pagination"""
        try:
            cache_key = cls.get_cache_key(account_id, folder)
            cached_data = cache.get(cache_key)
            
            if cached_data:
                threads = json.loads(cached_data) if isinstance(cached_data, str) else cached_data
                # Apply pagination
                paginated = threads[offset:offset + limit]
                logger.info(f"Retrieved {len(paginated)} cached threads (offset={offset}, limit={limit})")
                return paginated
            
            return None
        except Exception as e:
            logger.error(f"Failed to get cached threads: {e}")
            return None
    
    @classmethod
    def get_cached_total(cls, account_id: str, folder: str = "INBOX") -> Optional[int]:
        """Get total count of cached threads"""
        try:
            cache_key = cls.get_cache_key(account_id, folder)
            cached_data = cache.get(cache_key)
            
            if cached_data:
                threads = json.loads(cached_data) if isinstance(cached_data, str) else cached_data
                return len(threads)
            
            return None
        except Exception as e:
            logger.error(f"Failed to get cached total: {e}")
            return None
    
    @classmethod
    def invalidate_cache(cls, account_id: str, folder: str = "INBOX") -> None:
        """Invalidate cache for specific account/folder"""
        try:
            cache_key = cls.get_cache_key(account_id, folder)
            cursor_key = cls.get_cursor_key(account_id, folder)
            cache.delete(cache_key)
            cache.delete(cursor_key)
            logger.info(f"Invalidated cache for account {account_id}, folder {folder}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
    
    @classmethod
    def save_cursor(cls, account_id: str, cursor: str, folder: str = "INBOX") -> None:
        """Save pagination cursor for next fetch"""
        try:
            cursor_key = cls.get_cursor_key(account_id, folder)
            cache.set(cursor_key, cursor, cls.CACHE_TTL)
        except Exception as e:
            logger.error(f"Failed to save cursor: {e}")
    
    @classmethod
    def get_cursor(cls, account_id: str, folder: str = "INBOX") -> Optional[str]:
        """Get saved pagination cursor"""
        try:
            cursor_key = cls.get_cursor_key(account_id, folder)
            return cache.get(cursor_key)
        except Exception as e:
            logger.error(f"Failed to get cursor: {e}")
            return None