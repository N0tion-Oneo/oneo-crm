"""
Celery Management API Views - Comprehensive task and worker monitoring
"""
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import connection
from django_tenants.utils import schema_context
from celery import current_app
from celery.result import AsyncResult
import redis
import json

from api.permissions.settings import CeleryPermission
from communications.record_communications.models import (
    RecordCommunicationProfile, RecordSyncJob
)

logger = logging.getLogger(__name__)


class CeleryManagementViewSet(viewsets.ViewSet):
    """
    ViewSet for comprehensive Celery task and worker management
    """
    permission_classes = [IsAuthenticated, CeleryPermission]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get comprehensive Celery system overview - filtered by current tenant"""
        try:
            # Get current tenant schema
            current_schema = connection.schema_name
            
            # Get all queue information
            queue_names = [
                'background_sync', 'communications_maintenance', 'analytics',
                'workflows', 'ai_processing', 'communications', 'realtime',
                'triggers', 'bulk_operations', 'contact_resolution', 'celery'
            ]
            
            # Count tasks that belong to current tenant
            queues = {}
            total_tasks = 0
            tenant_tasks = 0
            
            for queue in queue_names:
                queue_length = self.redis_client.llen(queue)
                queues[queue] = queue_length
                total_tasks += queue_length
                
                # Count tenant-specific tasks in this queue
                if queue_length > 0:
                    tenant_count = self._count_tenant_tasks_in_queue(queue, current_schema)
                    tenant_tasks += tenant_count
            
            # Get worker information using Celery inspect
            inspect = current_app.control.inspect()
            active_tasks = inspect.active() or {}
            stats = inspect.stats() or {}
            registered = inspect.registered() or {}
            
            # Process worker information
            workers = []
            total_active = 0
            for worker_name, worker_stats in stats.items():
                active_count = len(active_tasks.get(worker_name, []))
                total_active += active_count
                
                workers.append({
                    'name': worker_name.split('@')[0],  # Extract worker type
                    'hostname': worker_name,
                    'status': 'online',
                    'active_tasks': active_count,
                    'processed': worker_stats.get('total', {}).get('tasks.completed', 0),
                    'failed': worker_stats.get('total', {}).get('tasks.failed', 0),
                    'pool': worker_stats.get('pool', {}).get('implementation', 'N/A'),
                    'concurrency': worker_stats.get('pool', {}).get('max-concurrency', 1),
                    'uptime': self._format_uptime(worker_stats.get('clock', 0))
                })
            
            # Get recent task execution stats for current tenant only
            # RecordSyncJob is a tenant-specific model
            recent_jobs = RecordSyncJob.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=24)
            )
            
            return Response({
                'status': 'healthy' if workers else 'degraded',
                'timestamp': timezone.now().isoformat(),
                'current_tenant': current_schema,
                'summary': {
                    'workers_online': len(workers),
                    'total_queued': total_tasks,
                    'tenant_queued': tenant_tasks,  # Tasks for current tenant
                    'total_active': total_active,
                    'tasks_24h': recent_jobs.count(),  # Already filtered by tenant
                    'failed_24h': recent_jobs.filter(status='failed').count()
                },
                'queues': queues,  # Shows all queues but we could filter
                'workers': workers,  # Workers are global, not tenant-specific
                'note': 'Queue counts show all tasks. RecordSyncJob stats are tenant-specific.'
            })
            
        except Exception as e:
            logger.error(f"Error getting Celery overview: {e}")
            return Response(
                {'error': str(e), 'status': 'error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def queue_details(self, request):
        """Get detailed information about a specific queue"""
        try:
            queue_name = request.query_params.get('queue', 'celery')
            limit = int(request.query_params.get('limit', 10))
            
            # Get queue length
            queue_length = self.redis_client.llen(queue_name)
            
            # Get sample of tasks from queue
            tasks = []
            if queue_length > 0:
                # Get first N tasks without removing them
                raw_tasks = self.redis_client.lrange(queue_name, 0, limit - 1)
                
                for raw_task in raw_tasks:
                    try:
                        task_data = json.loads(raw_task)
                        headers = task_data.get('headers', {})
                        
                        # Decode task arguments if needed
                        task_args = None
                        if 'body' in task_data:
                            import base64
                            try:
                                body = base64.b64decode(task_data['body'])
                                task_args = json.loads(body)
                            except:
                                task_args = 'Unable to decode'
                        
                        tasks.append({
                            'id': headers.get('id', 'unknown'),
                            'task': headers.get('task', 'unknown'),
                            'eta': headers.get('eta'),
                            'retries': headers.get('retries', 0),
                            'args': headers.get('argsrepr', str(task_args)),
                            'kwargs': headers.get('kwargsrepr', '{}'),
                            'origin': headers.get('origin', 'unknown')
                        })
                    except Exception as e:
                        logger.warning(f"Error parsing task: {e}")
                        continue
            
            return Response({
                'queue_name': queue_name,
                'length': queue_length,
                'tasks': tasks,
                'showing': len(tasks),
                'has_more': queue_length > limit
            })
            
        except Exception as e:
            logger.error(f"Error getting queue details: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def active_tasks(self, request):
        """Get all currently executing tasks"""
        try:
            inspect = current_app.control.inspect()
            active = inspect.active() or {}
            
            all_tasks = []
            for worker_name, tasks in active.items():
                for task in tasks:
                    all_tasks.append({
                        'worker': worker_name.split('@')[0],
                        'id': task.get('id'),
                        'name': task.get('name'),
                        'args': task.get('args', []),
                        'kwargs': task.get('kwargs', {}),
                        'time_start': task.get('time_start'),
                        'runtime': self._calculate_runtime(task.get('time_start'))
                    })
            
            return Response({
                'count': len(all_tasks),
                'tasks': all_tasks
            })
            
        except Exception as e:
            logger.error(f"Error getting active tasks: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def scheduled_tasks(self, request):
        """Get scheduled tasks (ETA/countdown)"""
        try:
            inspect = current_app.control.inspect()
            scheduled = inspect.scheduled() or {}
            reserved = inspect.reserved() or {}
            
            all_scheduled = []
            
            # Process scheduled tasks
            for worker_name, tasks in scheduled.items():
                for task in tasks:
                    all_scheduled.append({
                        'worker': worker_name.split('@')[0],
                        'id': task.get('id'),
                        'name': task.get('name'),
                        'eta': task.get('eta'),
                        'type': 'scheduled'
                    })
            
            # Process reserved tasks
            for worker_name, tasks in reserved.items():
                for task in tasks:
                    all_scheduled.append({
                        'worker': worker_name.split('@')[0],
                        'id': task.get('id'),
                        'name': task.get('name'),
                        'type': 'reserved'
                    })
            
            return Response({
                'count': len(all_scheduled),
                'tasks': all_scheduled
            })
            
        except Exception as e:
            logger.error(f"Error getting scheduled tasks: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def worker_details(self, request):
        """Get detailed information about workers"""
        try:
            inspect = current_app.control.inspect()
            stats = inspect.stats() or {}
            active = inspect.active() or {}
            registered = inspect.registered() or {}
            
            workers = []
            for worker_name, worker_stats in stats.items():
                worker_info = {
                    'name': worker_name,
                    'type': worker_name.split('@')[0],
                    'stats': {
                        'total_processed': worker_stats.get('total', {}),
                        'pool': worker_stats.get('pool', {}),
                        'prefetch_count': worker_stats.get('prefetch_count', 0),
                        'clock': worker_stats.get('clock', 0),
                        'pid': worker_stats.get('pid'),
                        'rusage': worker_stats.get('rusage', {})
                    },
                    'active_tasks': active.get(worker_name, []),
                    'registered_tasks': registered.get(worker_name, [])[:10]  # Limit for display
                }
                workers.append(worker_info)
            
            return Response({
                'count': len(workers),
                'workers': workers
            })
            
        except Exception as e:
            logger.error(f"Error getting worker details: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def purge_queue(self, request):
        """Purge all tasks from a specific queue"""
        try:
            queue_name = request.data.get('queue_name')
            
            # Validate queue name
            allowed_queues = ['background_sync', 'communications_maintenance', 'analytics']
            if queue_name not in allowed_queues:
                return Response(
                    {'error': f'Queue {queue_name} cannot be purged. Allowed: {allowed_queues}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get count before purging
            count = self.redis_client.llen(queue_name)
            
            # Delete the queue
            self.redis_client.delete(queue_name)
            
            logger.info(f"Purged {count} tasks from queue {queue_name} by user {request.user.email}")
            
            return Response({
                'success': True,
                'queue_name': queue_name,
                'tasks_purged': count,
                'message': f'Successfully purged {count} tasks from {queue_name}'
            })
            
        except Exception as e:
            logger.error(f"Error purging queue: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def revoke_task(self, request):
        """Revoke a specific task"""
        try:
            task_id = request.data.get('task_id')
            terminate = request.data.get('terminate', False)
            
            if not task_id:
                return Response(
                    {'error': 'task_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Revoke the task
            current_app.control.revoke(task_id, terminate=terminate)
            
            logger.info(f"Revoked task {task_id} (terminate={terminate}) by user {request.user.email}")
            
            return Response({
                'success': True,
                'task_id': task_id,
                'terminated': terminate,
                'message': f'Task {task_id} has been {"terminated" if terminate else "revoked"}'
            })
            
        except Exception as e:
            logger.error(f"Error revoking task: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def ping_workers(self, request):
        """Ping all workers to check connectivity"""
        try:
            # Ping workers with timeout
            inspect = current_app.control.inspect(timeout=2.0)
            ping_results = inspect.ping() or {}
            
            results = []
            for worker_name, response in ping_results.items():
                results.append({
                    'worker': worker_name,
                    'status': 'online' if response.get('ok') == 'pong' else 'offline',
                    'response': response
                })
            
            return Response({
                'timestamp': timezone.now().isoformat(),
                'workers_online': len([r for r in results if r['status'] == 'online']),
                'workers_offline': len([r for r in results if r['status'] == 'offline']),
                'results': results
            })
            
        except Exception as e:
            logger.error(f"Error pinging workers: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def beat_schedule(self, request):
        """Get Celery Beat schedule information"""
        try:
            from oneo_crm.celery import app
            
            schedule = []
            for task_name, task_config in app.conf.beat_schedule.items():
                # Skip disabled tasks
                if task_config.get('enabled', True) is False:
                    continue
                    
                schedule.append({
                    'name': task_name,
                    'task': task_config.get('task'),
                    'schedule': str(task_config.get('schedule')),
                    'args': task_config.get('args', []),
                    'kwargs': task_config.get('kwargs', {}),
                    'enabled': task_config.get('enabled', True)
                })
            
            return Response({
                'beat_running': False,  # You can check if beat is running via process check
                'schedule_count': len(schedule),
                'schedule': schedule
            })
            
        except Exception as e:
            logger.error(f"Error getting beat schedule: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _format_uptime(self, clock_value):
        """Format clock value to human-readable uptime"""
        try:
            seconds = int(clock_value)
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        except:
            return "N/A"
    
    def _calculate_runtime(self, time_start):
        """Calculate runtime from start time"""
        try:
            if not time_start:
                return "N/A"
            start = datetime.fromtimestamp(float(time_start))
            runtime = datetime.now() - start
            return str(runtime).split('.')[0]  # Remove microseconds
        except:
            return "N/A"
    
    def _count_tenant_tasks_in_queue(self, queue_name, tenant_schema):
        """Count tasks in a queue that belong to a specific tenant"""
        try:
            # Get all tasks from the queue (without removing them)
            tasks = self.redis_client.lrange(queue_name, 0, -1)
            tenant_count = 0
            
            for task_json in tasks:
                try:
                    task = json.loads(task_json)
                    # Check if task body contains the tenant schema
                    # Most tenant-aware tasks include schema_name in their args
                    if 'body' in task:
                        import base64
                        body = base64.b64decode(task['body'])
                        body_data = json.loads(body)
                        
                        # Check if tenant_schema is in the arguments
                        if isinstance(body_data, list) and len(body_data) > 0:
                            args = body_data[0] if isinstance(body_data[0], list) else []
                            kwargs = body_data[1] if len(body_data) > 1 and isinstance(body_data[1], dict) else {}
                            
                            # Check for tenant_schema in args or kwargs
                            if tenant_schema in str(args) or kwargs.get('tenant_schema') == tenant_schema:
                                tenant_count += 1
                except:
                    continue
                    
            return tenant_count
        except Exception as e:
            logger.warning(f"Error counting tenant tasks in {queue_name}: {e}")
            return 0