"""
Tenant-aware Celery task routing
Routes tasks to tenant-specific queues
"""
import logging
from typing import Dict, Any, Optional
from django.db import connection

logger = logging.getLogger(__name__)


class TenantTaskRouter:
    """
    Routes Celery tasks to tenant-specific queues
    Ensures tenant isolation at the queue level
    """
    
    # Map task types to queue categories
    TASK_QUEUE_MAPPING = {
        # Sync tasks - MUST come before general communications pattern
        'sync_record_communications': 'sync',
        'sync_all_records': 'sync',
        'process_webhook_message': 'sync',
        'check_stale_profiles': 'sync',
        'cleanup_old_sync_jobs': 'sync',
        
        # Communication tasks (sending messages, not syncing)
        'communications.': 'communications',
        'send_email': 'communications',
        'send_message': 'communications',
        
        # Workflow tasks
        'workflows.': 'workflows',
        'execute_workflow': 'workflows',
        
        # AI tasks
        'ai.': 'ai_processing',
        'process_ai_': 'ai_processing',
        
        # Analytics tasks
        'analytics.': 'analytics',
        'generate_report': 'analytics',
        'calculate_metrics': 'analytics',
        
        # Maintenance tasks
        'cleanup_': 'maintenance',
        'verify_': 'maintenance',
        'update_statistics': 'maintenance',
    }
    
    @classmethod
    def get_queue_type(cls, task_name: str) -> str:
        """
        Determine queue type based on task name
        """
        # Check for exact matches or prefixes
        for pattern, queue_type in cls.TASK_QUEUE_MAPPING.items():
            if pattern in task_name:
                return queue_type
        
        # Default queue type
        return 'general'
    
    @classmethod
    def route_task(cls, name: str, args: tuple, kwargs: dict, options: dict, 
                   task=None, **kw) -> Dict[str, Any]:
        """
        Celery router function - determines which queue a task goes to
        
        Returns routing configuration for the task
        """
        try:
            # Try to get tenant schema from various sources
            tenant_schema = cls._extract_tenant_schema(name, args, kwargs, options)
            
            if not tenant_schema or tenant_schema == 'public':
                # No tenant context, use default routing
                logger.debug(f"No tenant context for task {name}, using default routing")
                return {}
            
            # Determine queue type
            queue_type = cls.get_queue_type(name)
            
            # Build tenant-specific queue name
            queue_name = f"{tenant_schema}_{queue_type}"
            
            logger.debug(f"Routing task {name} to queue {queue_name}")
            
            return {
                'queue': queue_name,
                'routing_key': queue_name,
                'exchange': queue_name,  # Use queue name as exchange name
                'exchange_type': 'direct',
            }
            
        except Exception as e:
            logger.error(f"Error routing task {name}: {e}")
            return {}
    
    @classmethod
    def _extract_tenant_schema(cls, task_name: str, args: tuple, 
                               kwargs: dict, options: dict) -> Optional[str]:
        """
        Extract tenant schema from task arguments
        """
        # 1. Check kwargs for explicit tenant_schema
        if 'tenant_schema' in kwargs:
            return kwargs['tenant_schema']
        
        # 2. Check if tenant_schema is in args (common pattern)
        if args and len(args) > 1:
            # Many tasks have (record_id, tenant_schema) as args
            for arg in args:
                if isinstance(arg, str) and not arg.isdigit():
                    # Could be a schema name
                    if '_' not in arg or arg in ['demo', 'test', 'oneotalent']:
                        return arg
        
        # 3. Check options (for scheduled tasks)
        if 'tenant_schema' in options:
            return options['tenant_schema']
        
        # 4. Try to get from database connection (if in request context)
        try:
            current_schema = connection.schema_name
            if current_schema and current_schema != 'public':
                return current_schema
        except:
            pass
        
        return None


def tenant_task(tenant_schema: str = None, queue_type: str = None):
    """
    Decorator to mark a task as tenant-specific
    Ensures the task is routed to the correct tenant queue
    
    Usage:
        @tenant_task(queue_type='sync')
        @shared_task
        def my_task(record_id, tenant_schema):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Ensure tenant_schema is passed
            if not tenant_schema and 'tenant_schema' not in kwargs:
                raise ValueError(f"Task {func.__name__} requires tenant_schema")
            
            # Add routing metadata
            if hasattr(func, 'apply_async'):
                original_apply_async = func.apply_async
                
                def apply_async_with_routing(*args, **kwargs):
                    # Add tenant routing
                    schema = tenant_schema or kwargs.get('kwargs', {}).get('tenant_schema')
                    if schema:
                        queue = f"{schema}_{queue_type or 'general'}"
                        kwargs['queue'] = queue
                    
                    return original_apply_async(*args, **kwargs)
                
                func.apply_async = apply_async_with_routing
            
            return func(*args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator