"""
Cursor cache manager for email pagination
Stores cursor positions for efficient pagination
"""
import json
import logging
from typing import Dict, Optional
from django.core.cache import cache

logger = logging.getLogger(__name__)


class CursorCacheManager:
    """Manages cursor positions for email pagination"""
    
    CACHE_TTL = 1800  # 30 minutes
    
    @classmethod
    def get_cache_key(cls, account_id: str, folder: str, page: int) -> str:
        """Generate cache key for cursor at specific page"""
        return f"email_cursor:{account_id}:{folder}:page_{page}"
    
    @classmethod
    def save_cursor(cls, account_id: str, folder: str, page: int, cursor: str) -> None:
        """Save cursor for a specific page"""
        try:
            cache_key = cls.get_cache_key(account_id, folder, page)
            cache.set(cache_key, cursor, cls.CACHE_TTL)
            logger.debug(f"Saved cursor for page {page}: {cursor[:20]}...")
        except Exception as e:
            logger.error(f"Failed to save cursor: {e}")
    
    @classmethod
    def get_cursor(cls, account_id: str, folder: str, page: int) -> Optional[str]:
        """Get cursor for a specific page"""
        try:
            # Page 1 always starts with no cursor
            if page <= 1:
                return None
            
            # Try to get cursor for the previous page
            cache_key = cls.get_cache_key(account_id, folder, page - 1)
            cursor = cache.get(cache_key)
            
            if cursor:
                logger.debug(f"Found cursor for page {page}: {cursor[:20]}...")
            else:
                logger.debug(f"No cursor found for page {page}")
            
            return cursor
        except Exception as e:
            logger.error(f"Failed to get cursor: {e}")
            return None
    
    @classmethod
    def clear_cursors(cls, account_id: str, folder: str) -> None:
        """Clear all cursors for an account/folder combination"""
        try:
            # Clear up to 100 pages worth of cursors
            for page in range(1, 101):
                cache_key = cls.get_cache_key(account_id, folder, page)
                cache.delete(cache_key)
            logger.info(f"Cleared all cursors for {account_id}/{folder}")
        except Exception as e:
            logger.error(f"Failed to clear cursors: {e}")