"""
Cache utilities for multi-tenant Oneo CRM system.
Provides tenant-isolated caching functionality.
"""

from django.core.cache import cache
from django.conf import settings
from functools import wraps


def tenant_cache_key(key, tenant_schema=None):
    """Generate tenant-specific cache key"""
    from django_tenants.utils import get_tenant_model, connection
    
    if not tenant_schema:
        # Try to get current tenant schema from connection
        if hasattr(connection, 'tenant') and connection.tenant:
            tenant_schema = connection.tenant.schema_name
        else:
            tenant_schema = 'public'
    
    return f"{tenant_schema}:{key}"


def cache_tenant_data(timeout=settings.CACHE_TTL):
    """Decorator for caching tenant-specific data"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key based on function and tenant
            cache_key = tenant_cache_key(f"{func.__name__}:{hash(str(args) + str(kwargs))}")
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is None:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


def invalidate_tenant_cache(pattern):
    """Invalidate tenant-specific cache entries matching pattern"""
    from django_tenants.utils import connection
    
    if hasattr(connection, 'tenant') and connection.tenant:
        tenant_schema = connection.tenant.schema_name
        cache_pattern = f"{tenant_schema}:{pattern}"
        
        # Note: Redis-specific cache clearing
        # In production, consider using cache versioning instead
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            keys = redis_conn.keys(f"{cache_pattern}*")
            if keys:
                redis_conn.delete(*keys)
        except ImportError:
            # Fallback for non-Redis cache backends
            pass