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
        """Get Celery overview for current tenant only"""
        try:
            # Get current tenant schema
            current_schema = connection.schema_name
            
            if current_schema == 'public':
                return Response({
                    'error': 'Celery management not available for public schema'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get tenant-specific queue names - now with all queue types
            from celery_workers.worker_manager import TenantWorkerManager
            
            # Get all queue types from worker definitions
            all_queues = []
            for worker_type_config in TenantWorkerManager.WORKER_TYPES.values():
                all_queues.extend(worker_type_config['queues'])
            
            # Remove duplicates and create tenant-specific queue names
            unique_queues = list(set(all_queues))
            tenant_queues = [f"{current_schema}_{qt}" for qt in unique_queues]
            
            # Get queue information for tenant queues only
            queues = {}
            total_tasks = 0
            
            for queue in tenant_queues:
                queue_length = self.redis_client.llen(queue)
                # Show friendly name without tenant prefix
                queue_display = queue.replace(f"{current_schema}_", "")
                queues[queue_display] = queue_length
                total_tasks += queue_length
            
            # Get tenant-specific worker information
            from celery_workers import worker_manager
            
            # Get worker information using Celery inspect
            inspect = current_app.control.inspect()
            active_tasks = inspect.active() or {}
            stats = inspect.stats() or {}
            
            # Find all workers for this tenant (6 specialized workers)
            tenant_workers = []
            total_active = 0
            
            for worker_name, worker_stats in stats.items():
                # Check if this is one of the tenant's workers
                if current_schema in worker_name:
                    active_count = len(active_tasks.get(worker_name, []))
                    total_active += active_count
                    
                    # Extract worker type from name (e.g., "oneotalent_sync@hostname" -> "sync")
                    worker_type = 'unknown'
                    for wt in TenantWorkerManager.WORKER_TYPES.keys():
                        if f"{current_schema}_{wt}" in worker_name:
                            worker_type = wt
                            break
                    
                    # Get worker config for this type
                    worker_config = TenantWorkerManager.WORKER_TYPES.get(worker_type, {})
                    
                    tenant_workers.append({
                        'name': f"{current_schema}_{worker_type}",
                        'type': worker_type,
                        'description': worker_config.get('description', 'Worker'),
                        'hostname': worker_name,
                        'status': 'online',
                        'active_tasks': active_count,
                        'processed': worker_stats.get('total', {}).get('tasks.completed', 0),
                        'failed': worker_stats.get('total', {}).get('tasks.failed', 0),
                        'pool': worker_stats.get('pool', {}).get('implementation', 'N/A'),
                        'concurrency': worker_config.get('concurrency', 1),
                        'uptime': self._format_uptime(worker_stats.get('clock', 0)),
                        'queues': worker_config.get('queues', [])
                    })
            
            # If no workers found, check if they're starting
            if not tenant_workers:
                # Get status for all worker types
                for worker_type in TenantWorkerManager.WORKER_TYPES.keys():
                    worker_key = f"{current_schema}_{worker_type}"
                    worker_status = worker_manager.get_worker_status(worker_key)
                    if worker_status.get('running'):
                        worker_config = TenantWorkerManager.WORKER_TYPES[worker_type]
                        tenant_workers.append({
                            'name': worker_key,
                            'type': worker_type,
                            'description': worker_config.get('description', 'Worker'),
                            'hostname': f"{worker_key}@localhost",
                            'status': 'starting',
                            'active_tasks': 0,
                            'processed': 0,
                            'failed': 0,
                            'pool': 'prefork',
                            'concurrency': worker_config.get('concurrency', 1),
                            'uptime': 'N/A',
                            'pid': worker_status.get('pid'),
                            'queues': worker_config.get('queues', [])
                        })
            
            workers = tenant_workers
            
            # Get recent task execution stats for current tenant only
            # RecordSyncJob is a tenant-specific model
            recent_jobs = RecordSyncJob.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=24)
            )
            
            return Response({
                'status': 'healthy' if workers else 'no_worker',
                'timestamp': timezone.now().isoformat(),
                'current_tenant': current_schema,
                'summary': {
                    'workers_online': len(workers),
                    'expected_workers': len(TenantWorkerManager.WORKER_TYPES),
                    'total_queued': total_tasks,
                    'total_active': total_active,
                    'tasks_24h': recent_jobs.count(),
                    'failed_24h': recent_jobs.filter(status='failed').count()
                },
                'queues': queues,  # Tenant-specific queues only
                'workers': workers,  # All tenant-specific workers
                'worker_types': TenantWorkerManager.WORKER_TYPES,  # Worker type definitions
                'note': f'Showing {len(workers)} specialized workers for tenant {current_schema}'
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
    
    @action(detail=False, methods=['get'])
    def task_history(self, request):
        """Get task execution history from Redis and database"""
        try:
            limit = int(request.query_params.get('limit', 50))
            status_filter = request.query_params.get('status', None)
            
            # Get current tenant schema
            current_schema = connection.schema_name
            
            # Get recent sync jobs from database (tenant-specific)
            from communications.record_communications.models import RecordSyncJob
            
            jobs_query = RecordSyncJob.objects.select_related(
                'record', 'record__pipeline', 'triggered_by'
            ).all()
            if status_filter:
                jobs_query = jobs_query.filter(status=status_filter)
            
            recent_jobs = jobs_query.order_by('-created_at')[:limit]
            
            history = []
            for job in recent_jobs:
                # Get record display name
                record_name = 'Unknown Record'
                record_pipeline = 'Unknown Pipeline'
                if job.record:
                    record_data = job.record.data or {}
                    # Try common name fields
                    record_name = (
                        record_data.get('name') or 
                        record_data.get('full_name') or 
                        record_data.get('first_name', '') + ' ' + record_data.get('last_name', '') or
                        record_data.get('company_name') or
                        record_data.get('title') or
                        f'Record #{job.record.id}'
                    ).strip()
                    if job.record.pipeline:
                        record_pipeline = job.record.pipeline.name
                
                history.append({
                    'id': str(job.id),
                    'task_name': 'sync_record_communications',
                    'status': job.status,
                    'record_id': job.record_id,
                    'record_name': record_name,
                    'pipeline_name': record_pipeline,
                    'job_type': job.job_type,
                    'trigger_reason': job.trigger_reason or 'Manual sync',
                    'triggered_by': job.triggered_by.email if job.triggered_by else 'System',
                    'created_at': job.created_at.isoformat(),
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                    'duration_ms': (job.completed_at - job.started_at).total_seconds() * 1000 if job.completed_at and job.started_at else None,
                    'error_message': job.error_message,
                    'error_details': job.error_details,
                    # Progress tracking
                    'progress_percentage': job.progress_percentage,
                    'current_step': job.current_step,
                    'accounts_synced': job.accounts_synced,
                    'total_accounts_to_sync': job.total_accounts_to_sync,
                    # Results
                    'messages_found': job.messages_found,
                    'conversations_found': job.conversations_found,
                    'new_links_created': job.new_links_created,
                    # Celery task info
                    'celery_task_id': job.celery_task_id
                })
            
            # Get task result keys from Redis (last N results)
            result_keys = self.redis_client.keys('celery-task-meta-*')[-limit:]
            
            for key in result_keys:
                try:
                    result_data = self.redis_client.get(key)
                    if result_data:
                        task_result = json.loads(result_data)
                        task_id = key.replace('celery-task-meta-', '')
                        
                        history.append({
                            'id': task_id,
                            'task_name': task_result.get('task', 'unknown'),
                            'status': task_result.get('status', 'unknown'),
                            'result': str(task_result.get('result', ''))[:200],  # Truncate result
                            'traceback': task_result.get('traceback'),
                            'date_done': task_result.get('date_done'),
                            'children': task_result.get('children', [])
                        })
                except Exception as e:
                    logger.warning(f"Error parsing task result {key}: {e}")
                    continue
            
            # Sort by date
            history.sort(key=lambda x: x.get('created_at') or x.get('date_done', ''), reverse=True)
            
            return Response({
                'count': len(history),
                'tasks': history[:limit],
                'tenant': current_schema
            })
            
        except Exception as e:
            logger.error(f"Error getting task history: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def redis_stats(self, request):
        """Get Redis statistics and queue metrics"""
        try:
            # Get Redis info
            info = self.redis_client.info()
            
            # Get memory stats
            memory_info = self.redis_client.info('memory')
            
            # Get all queue keys for current tenant
            current_schema = connection.schema_name
            tenant_queues = self.redis_client.keys(f'{current_schema}_*')
            
            queue_stats = {}
            total_messages = 0
            
            for queue_key in tenant_queues:
                queue_type = self.redis_client.type(queue_key)
                if queue_type == 'list':
                    queue_length = self.redis_client.llen(queue_key)
                    queue_stats[queue_key] = {
                        'type': 'queue',
                        'length': queue_length
                    }
                    total_messages += queue_length
                elif queue_type == 'zset':
                    # Scheduled tasks
                    scheduled_count = self.redis_client.zcard(queue_key)
                    queue_stats[queue_key] = {
                        'type': 'scheduled',
                        'count': scheduled_count
                    }
            
            # Get Celery-specific keys
            celery_keys = self.redis_client.keys('celery*')
            celery_stats = {
                'task_results': len([k for k in celery_keys if k.startswith('celery-task-meta-')]),
                'unacked': len([k for k in celery_keys if 'unacked' in k]),
            }
            
            return Response({
                'redis': {
                    'version': info.get('redis_version'),
                    'uptime_days': info.get('uptime_in_days'),
                    'connected_clients': info.get('connected_clients'),
                    'used_memory_human': memory_info.get('used_memory_human'),
                    'used_memory_peak_human': memory_info.get('used_memory_peak_human'),
                    'total_commands_processed': info.get('total_commands_processed'),
                },
                'queues': queue_stats,
                'celery': celery_stats,
                'tenant': current_schema,
                'total_messages': total_messages
            })
            
        except Exception as e:
            logger.error(f"Error getting Redis stats: {e}")
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