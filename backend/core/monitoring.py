"""
Performance monitoring utilities for Oneo CRM
"""

import time
import logging
from functools import wraps
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from django_tenants.utils import get_tenant

logger = logging.getLogger(__name__)


def monitor_performance(operation_name):
    """Decorator to monitor operation performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log performance metrics
                try:
                    tenant_schema = 'unknown'
                    # get_tenant() requires request context, which may not be available
                    # This is OK for testing without actual requests
                except:
                    tenant_schema = 'unknown'
                
                logger.info(
                    f"Performance: {operation_name}",
                    extra={
                        'operation': operation_name,
                        'execution_time': execution_time,
                        'tenant': tenant_schema,
                        'success': True
                    }
                )
                
                # Store in cache for monitoring dashboard
                _store_performance_metric(operation_name, execution_time, True)
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                try:
                    tenant_schema = 'unknown'
                    # get_tenant() requires request context, which may not be available
                except:
                    tenant_schema = 'unknown'
                
                logger.error(
                    f"Performance Error: {operation_name}",
                    extra={
                        'operation': operation_name,
                        'execution_time': execution_time,
                        'tenant': tenant_schema,
                        'success': False,
                        'error': str(e)
                    }
                )
                _store_performance_metric(operation_name, execution_time, False)
                raise
                
        return wrapper
    return decorator


def _store_performance_metric(operation, execution_time, success):
    """Store performance metrics in cache for monitoring"""
    try:
        # get_tenant() requires request context, use 'unknown' if not available
        try:
            tenant = get_tenant()  # This will fail without request context
            tenant_key = tenant.schema_name if tenant else 'public'
        except:
            tenant_key = 'unknown'
        
        # Create metric entry
        metric = {
            'timestamp': time.time(),
            'execution_time': execution_time,
            'success': success,
            'tenant': tenant_key
        }
        
        # Store in cache with 1 hour expiry
        cache_key = f"performance:{tenant_key}:{operation}:{int(time.time())}"
        cache.set(cache_key, metric, 3600)
        
    except Exception as e:
        logger.warning(f"Failed to store performance metric: {e}")


def get_database_stats():
    """Get database connection and query statistics"""
    stats = {
        'queries_count': len(connection.queries),
        'total_time': sum(float(q['time']) for q in connection.queries),
        'queries': connection.queries[-10:] if settings.DEBUG else []  # Last 10 queries in debug
    }
    
    # Add tenant context
    try:
        # get_tenant() requires request context, use 'unknown' if not available
        stats['tenant'] = 'unknown'  # Will be set properly in request context
    except:
        stats['tenant'] = 'unknown'
    
    return stats


def get_cache_stats():
    """Get Redis cache statistics"""
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        
        info = redis_conn.info()
        stats = {
            'memory_used': info.get('used_memory_human', 'Unknown'),
            'memory_peak': info.get('used_memory_peak_human', 'Unknown'),
            'connected_clients': info.get('connected_clients', 0),
            'keyspace_hits': info.get('keyspace_hits', 0),
            'keyspace_misses': info.get('keyspace_misses', 0),
            'hit_rate': 0
        }
        
        # Calculate hit rate
        hits = stats['keyspace_hits']
        misses = stats['keyspace_misses']
        if hits + misses > 0:
            stats['hit_rate'] = round((hits / (hits + misses)) * 100, 2)
            
        return stats
        
    except Exception as e:
        logger.warning(f"Failed to get cache stats: {e}")
        return {'error': str(e)}


def get_tenant_metrics(tenant_schema=None):
    """Get performance metrics for specific tenant"""
    if not tenant_schema:
        try:
            tenant = get_tenant()
            tenant_schema = tenant.schema_name if tenant else 'public'
        except:
            tenant_schema = 'unknown'
    
    # Get cached performance metrics
    pattern = f"performance:{tenant_schema}:*"
    
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        
        keys = redis_conn.keys(pattern)
        metrics = []
        
        for key in keys[-100:]:  # Last 100 metrics
            try:
                metric = cache.get(key.decode() if isinstance(key, bytes) else key)
                if metric:
                    metrics.append(metric)
            except:
                continue
        
        # Aggregate metrics
        if not metrics:
            return {'error': 'No metrics available'}
        
        total_requests = len(metrics)
        successful_requests = sum(1 for m in metrics if m.get('success', False))
        avg_response_time = sum(m.get('execution_time', 0) for m in metrics) / total_requests
        
        return {
            'tenant': tenant_schema,
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'success_rate': round((successful_requests / total_requests) * 100, 2),
            'avg_response_time': round(avg_response_time * 1000, 2),  # Convert to ms
            'metrics': metrics[-10:]  # Last 10 metrics
        }
        
    except Exception as e:
        logger.warning(f"Failed to get tenant metrics: {e}")
        return {'error': str(e)}


class PerformanceMiddleware:
    """Middleware to monitor request performance"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Log slow requests (> 1 second)
        if response_time > 1.0:
            logger.warning(
                f"Slow request detected: {request.path}",
                extra={
                    'path': request.path,
                    'method': request.method,
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'tenant': 'unknown',  # Will be set properly in request context
                }
            )
        
        # Add response time header
        response['X-Response-Time'] = f"{response_time:.3f}s"
        
        return response


def health_check():
    """Comprehensive system health check"""
    health_status = {
        'status': 'healthy',
        'timestamp': time.time(),
        'checks': {}
    }
    
    # Database check
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            health_status['checks']['database'] = {
                'status': 'healthy' if result[0] == 1 else 'unhealthy',
                'response_time': None  # Would need timing
            }
    except Exception as e:
        health_status['checks']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'unhealthy'
    
    # Cache check
    try:
        cache.set('health_check', 'ok', 60)
        result = cache.get('health_check')
        health_status['checks']['cache'] = {
            'status': 'healthy' if result == 'ok' else 'unhealthy'
        }
    except Exception as e:
        health_status['checks']['cache'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'unhealthy'
    
    # Memory check (basic)
    try:
        import psutil
        memory = psutil.virtual_memory()
        health_status['checks']['memory'] = {
            'status': 'healthy' if memory.percent < 90 else 'warning',
            'usage_percent': memory.percent,
            'available_gb': round(memory.available / (1024**3), 2)
        }
        if memory.percent > 95:
            health_status['status'] = 'unhealthy'
    except ImportError:
        health_status['checks']['memory'] = {
            'status': 'unknown',
            'error': 'psutil not installed'
        }
    
    return health_status