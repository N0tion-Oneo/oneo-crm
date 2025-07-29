"""
System metrics collection and analysis
Provides comprehensive metrics gathering across all system components
"""
import logging
import time
import psutil
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass

from django.db import models, connection
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model

from .models import SystemMetrics, PerformanceMetrics, MetricType

User = get_user_model()
logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Data structure for individual metric points"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, Any] = None
    metadata: Dict[str, Any] = None


class SystemMetricsCollector:
    """
    Comprehensive system metrics collection
    Gathers performance, usage, and business metrics
    """
    
    def __init__(self):
        self.collection_interval = 60  # seconds
        self.metric_buffer = defaultdict(deque)
        self.buffer_size = 1000
        
    def collect_all_metrics(self) -> List[MetricPoint]:
        """Collect all system metrics"""
        metrics = []
        timestamp = timezone.now()
        
        try:
            # System performance metrics
            metrics.extend(self._collect_system_performance(timestamp))
            
            # Database metrics
            metrics.extend(self._collect_database_metrics(timestamp))
            
            # Cache metrics
            metrics.extend(self._collect_cache_metrics(timestamp))
            
            # Application metrics
            metrics.extend(self._collect_application_metrics(timestamp))
            
            # Business metrics
            metrics.extend(self._collect_business_metrics(timestamp))
            
            # Error metrics
            metrics.extend(self._collect_error_metrics(timestamp))
            
            # Store metrics in database
            self._store_metrics(metrics)
            
            # Update performance aggregates
            self._update_performance_aggregates(timestamp)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return []
    
    def _collect_system_performance(self, timestamp: datetime) -> List[MetricPoint]:
        """Collect system performance metrics"""
        metrics = []
        
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
            
            metrics.extend([
                MetricPoint('cpu.usage_percent', cpu_percent, '%', timestamp),
                MetricPoint('cpu.count', cpu_count, 'cores', timestamp),
                MetricPoint('cpu.load_avg_1min', load_avg[0], 'load', timestamp),
                MetricPoint('cpu.load_avg_5min', load_avg[1], 'load', timestamp),
                MetricPoint('cpu.load_avg_15min', load_avg[2], 'load', timestamp),
            ])
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            metrics.extend([
                MetricPoint('memory.usage_percent', memory.percent, '%', timestamp),
                MetricPoint('memory.available_bytes', memory.available, 'bytes', timestamp),
                MetricPoint('memory.used_bytes', memory.used, 'bytes', timestamp),
                MetricPoint('memory.total_bytes', memory.total, 'bytes', timestamp),
                MetricPoint('swap.usage_percent', swap.percent, '%', timestamp),
                MetricPoint('swap.used_bytes', swap.used, 'bytes', timestamp),
            ])
            
            # Disk metrics
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            metrics.extend([
                MetricPoint('disk.usage_percent', (disk_usage.used / disk_usage.total) * 100, '%', timestamp),
                MetricPoint('disk.free_bytes', disk_usage.free, 'bytes', timestamp),
                MetricPoint('disk.used_bytes', disk_usage.used, 'bytes', timestamp),
                MetricPoint('disk.total_bytes', disk_usage.total, 'bytes', timestamp),
            ])
            
            if disk_io:
                metrics.extend([
                    MetricPoint('disk.read_bytes', disk_io.read_bytes, 'bytes', timestamp),
                    MetricPoint('disk.write_bytes', disk_io.write_bytes, 'bytes', timestamp),
                    MetricPoint('disk.read_count', disk_io.read_count, 'operations', timestamp),
                    MetricPoint('disk.write_count', disk_io.write_count, 'operations', timestamp),
                ])
            
            # Network metrics
            net_io = psutil.net_io_counters()
            if net_io:
                metrics.extend([
                    MetricPoint('network.bytes_sent', net_io.bytes_sent, 'bytes', timestamp),
                    MetricPoint('network.bytes_recv', net_io.bytes_recv, 'bytes', timestamp),
                    MetricPoint('network.packets_sent', net_io.packets_sent, 'packets', timestamp),
                    MetricPoint('network.packets_recv', net_io.packets_recv, 'packets', timestamp),
                ])
            
            # Process metrics
            process = psutil.Process()
            metrics.extend([
                MetricPoint('process.memory_percent', process.memory_percent(), '%', timestamp),
                MetricPoint('process.cpu_percent', process.cpu_percent(), '%', timestamp),
                MetricPoint('process.num_threads', process.num_threads(), 'threads', timestamp),
                MetricPoint('process.num_fds', process.num_fds() if hasattr(process, 'num_fds') else 0, 'descriptors', timestamp),
            ])
            
        except Exception as e:
            logger.error(f"Failed to collect system performance metrics: {e}")
        
        return metrics
    
    def _collect_database_metrics(self, timestamp: datetime) -> List[MetricPoint]:
        """Collect database performance metrics"""
        metrics = []
        
        try:
            # Query performance
            with connection.cursor() as cursor:
                # PostgreSQL specific metrics
                if 'postgresql' in settings.DATABASES['default']['ENGINE']:
                    # Database size
                    cursor.execute("""
                        SELECT pg_database_size(current_database())
                    """)
                    db_size = cursor.fetchone()[0]
                    metrics.append(MetricPoint('database.size_bytes', db_size, 'bytes', timestamp))
                    
                    # Active connections
                    cursor.execute("""
                        SELECT count(*) FROM pg_stat_activity 
                        WHERE state = 'active'
                    """)
                    active_connections = cursor.fetchone()[0]
                    metrics.append(MetricPoint('database.active_connections', active_connections, 'connections', timestamp))
                    
                    # Total connections
                    cursor.execute("""
                        SELECT count(*) FROM pg_stat_activity
                    """)
                    total_connections = cursor.fetchone()[0]
                    metrics.append(MetricPoint('database.total_connections', total_connections, 'connections', timestamp))
                    
                    # Lock statistics
                    cursor.execute("""
                        SELECT count(*) FROM pg_locks
                    """)
                    locks_count = cursor.fetchone()[0]
                    metrics.append(MetricPoint('database.locks_count', locks_count, 'locks', timestamp))
                    
                    # Cache hit ratio
                    cursor.execute("""
                        SELECT 
                            sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) * 100 as cache_hit_ratio
                        FROM pg_statio_user_tables
                        WHERE heap_blks_hit + heap_blks_read > 0
                    """)
                    result = cursor.fetchone()
                    if result and result[0]:
                        cache_hit_ratio = float(result[0])
                        metrics.append(MetricPoint('database.cache_hit_ratio', cache_hit_ratio, '%', timestamp))
            
            # Django model counts (business data)
            try:
                from django.apps import apps
                
                # Count records in key models
                model_counts = {}
                
                # User model
                User = apps.get_model('authentication', 'User')
                model_counts['users'] = User.objects.count()
                
                # Workflow models
                try:
                    Workflow = apps.get_model('workflows', 'Workflow')
                    WorkflowExecution = apps.get_model('workflows', 'WorkflowExecution')
                    model_counts['workflows'] = Workflow.objects.count()
                    model_counts['workflow_executions'] = WorkflowExecution.objects.count()
                except:
                    pass
                
                # Communication models
                try:
                    Message = apps.get_model('communications', 'Message')
                    Channel = apps.get_model('communications', 'Channel')
                    model_counts['messages'] = Message.objects.count()
                    model_counts['channels'] = Channel.objects.count()
                except:
                    pass
                
                # Pipeline models
                try:
                    Pipeline = apps.get_model('pipelines', 'Pipeline')
                    Record = apps.get_model('pipelines', 'Record')
                    model_counts['pipelines'] = Pipeline.objects.count()
                    model_counts['records'] = Record.objects.count()
                except:
                    pass
                
                for model_name, count in model_counts.items():
                    metrics.append(MetricPoint(f'database.{model_name}_count', count, 'records', timestamp))
                    
            except Exception as e:
                logger.error(f"Failed to collect model counts: {e}")
            
        except Exception as e:
            logger.error(f"Failed to collect database metrics: {e}")
        
        return metrics
    
    def _collect_cache_metrics(self, timestamp: datetime) -> List[MetricPoint]:
        """Collect cache performance metrics"""
        metrics = []
        
        try:
            # Redis-specific metrics
            if hasattr(cache, '_cache') and hasattr(cache._cache, '_client'):
                try:
                    import redis
                    redis_client = cache._cache._client.get_client()
                    info = redis_client.info()
                    
                    metrics.extend([
                        MetricPoint('cache.used_memory', info.get('used_memory', 0), 'bytes', timestamp),
                        MetricPoint('cache.used_memory_peak', info.get('used_memory_peak', 0), 'bytes', timestamp),
                        MetricPoint('cache.connected_clients', info.get('connected_clients', 0), 'clients', timestamp),
                        MetricPoint('cache.total_commands_processed', info.get('total_commands_processed', 0), 'commands', timestamp),
                        MetricPoint('cache.keyspace_hits', info.get('keyspace_hits', 0), 'hits', timestamp),
                        MetricPoint('cache.keyspace_misses', info.get('keyspace_misses', 0), 'misses', timestamp),
                        MetricPoint('cache.expired_keys', info.get('expired_keys', 0), 'keys', timestamp),
                        MetricPoint('cache.evicted_keys', info.get('evicted_keys', 0), 'keys', timestamp),
                    ])
                    
                    # Calculate hit ratio
                    hits = info.get('keyspace_hits', 0)
                    misses = info.get('keyspace_misses', 0)
                    if hits + misses > 0:
                        hit_ratio = (hits / (hits + misses)) * 100
                        metrics.append(MetricPoint('cache.hit_ratio', hit_ratio, '%', timestamp))
                    
                except Exception as e:
                    logger.error(f"Failed to collect Redis metrics: {e}")
            
            # Generic cache performance test
            test_key = f"metrics_test_{int(time.time())}"
            test_value = "test_value"
            
            # Measure cache set/get performance
            start_time = time.time()
            cache.set(test_key, test_value, timeout=60)
            set_time = (time.time() - start_time) * 1000  # milliseconds
            
            start_time = time.time()
            cached_value = cache.get(test_key)
            get_time = (time.time() - start_time) * 1000  # milliseconds
            
            cache.delete(test_key)
            
            metrics.extend([
                MetricPoint('cache.set_time_ms', set_time, 'ms', timestamp),
                MetricPoint('cache.get_time_ms', get_time, 'ms', timestamp),
                MetricPoint('cache.operation_success', 1 if cached_value == test_value else 0, 'boolean', timestamp),
            ])
            
        except Exception as e:
            logger.error(f"Failed to collect cache metrics: {e}")
        
        return metrics
    
    def _collect_application_metrics(self, timestamp: datetime) -> List[MetricPoint]:
        """Collect Django application metrics"""
        metrics = []
        
        try:
            from django.core.cache import cache
            from django.db import connections
            
            # Request metrics (if available from middleware)
            request_metrics = cache.get('request_metrics', {})
            for metric_name, value in request_metrics.items():
                metrics.append(MetricPoint(f'requests.{metric_name}', value, 'count', timestamp))
            
            # Session metrics
            try:
                from django.contrib.sessions.models import Session
                active_sessions = Session.objects.filter(expire_date__gte=timezone.now()).count()
                total_sessions = Session.objects.count()
                
                metrics.extend([
                    MetricPoint('sessions.active_count', active_sessions, 'sessions', timestamp),
                    MetricPoint('sessions.total_count', total_sessions, 'sessions', timestamp),
                ])
            except Exception:
                pass
            
            # Celery metrics (if available)
            try:
                from celery import current_app
                inspect = current_app.control.inspect()
                
                stats = inspect.stats()
                active = inspect.active()
                reserved = inspect.reserved()
                
                if stats:
                    worker_count = len(stats)
                    total_active_tasks = sum(len(tasks) for tasks in (active.values() if active else []))
                    total_reserved_tasks = sum(len(tasks) for tasks in (reserved.values() if reserved else []))
                    
                    metrics.extend([
                        MetricPoint('celery.worker_count', worker_count, 'workers', timestamp),
                        MetricPoint('celery.active_tasks', total_active_tasks, 'tasks', timestamp),
                        MetricPoint('celery.reserved_tasks', total_reserved_tasks, 'tasks', timestamp),
                    ])
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"Failed to collect application metrics: {e}")
        
        return metrics
    
    def _collect_business_metrics(self, timestamp: datetime) -> List[MetricPoint]:
        """Collect business and usage metrics"""
        metrics = []
        
        try:
            # Time ranges for different metrics
            last_hour = timestamp - timedelta(hours=1)
            last_day = timestamp - timedelta(days=1)
            last_week = timestamp - timedelta(weeks=1)
            
            # User activity metrics
            try:
                active_users_hour = User.objects.filter(last_login__gte=last_hour).count()
                active_users_day = User.objects.filter(last_login__gte=last_day).count()
                total_users = User.objects.count()
                
                metrics.extend([
                    MetricPoint('users.active_last_hour', active_users_hour, 'users', timestamp),
                    MetricPoint('users.active_last_day', active_users_day, 'users', timestamp),
                    MetricPoint('users.total', total_users, 'users', timestamp),
                ])
            except Exception:
                pass
            
            # Workflow metrics
            try:
                from workflows.models import Workflow, WorkflowExecution
                
                executions_hour = WorkflowExecution.objects.filter(started_at__gte=last_hour).count()
                executions_day = WorkflowExecution.objects.filter(started_at__gte=last_day).count()
                successful_executions_day = WorkflowExecution.objects.filter(
                    started_at__gte=last_day,
                    status='completed'
                ).count()
                failed_executions_day = WorkflowExecution.objects.filter(
                    started_at__gte=last_day,
                    status='failed'
                ).count()
                
                metrics.extend([
                    MetricPoint('workflows.executions_last_hour', executions_hour, 'executions', timestamp),
                    MetricPoint('workflows.executions_last_day', executions_day, 'executions', timestamp),
                    MetricPoint('workflows.successful_last_day', successful_executions_day, 'executions', timestamp),
                    MetricPoint('workflows.failed_last_day', failed_executions_day, 'executions', timestamp),
                ])
                
                if executions_day > 0:
                    success_rate = (successful_executions_day / executions_day) * 100
                    metrics.append(MetricPoint('workflows.success_rate_day', success_rate, '%', timestamp))
                    
            except Exception:
                pass
            
            # Communication metrics
            try:
                from communications.models import Message, Channel
                
                messages_hour = Message.objects.filter(created_at__gte=last_hour).count()
                messages_day = Message.objects.filter(created_at__gte=last_day).count()
                delivered_messages_day = Message.objects.filter(
                    created_at__gte=last_day,
                    status='delivered'
                ).count()
                failed_messages_day = Message.objects.filter(
                    created_at__gte=last_day,
                    status='failed'
                ).count()
                
                metrics.extend([
                    MetricPoint('communications.messages_last_hour', messages_hour, 'messages', timestamp),
                    MetricPoint('communications.messages_last_day', messages_day, 'messages', timestamp),
                    MetricPoint('communications.delivered_last_day', delivered_messages_day, 'messages', timestamp),
                    MetricPoint('communications.failed_last_day', failed_messages_day, 'messages', timestamp),
                ])
                
                if messages_day > 0:
                    delivery_rate = (delivered_messages_day / messages_day) * 100
                    metrics.append(MetricPoint('communications.delivery_rate_day', delivery_rate, '%', timestamp))
                    
            except Exception:
                pass
            
            # Pipeline metrics
            try:
                from pipelines.models import Pipeline, Record
                
                records_created_day = Record.objects.filter(created_at__gte=last_day).count()
                records_updated_day = Record.objects.filter(updated_at__gte=last_day).count()
                active_pipelines = Pipeline.objects.filter(is_active=True).count()
                
                metrics.extend([
                    MetricPoint('pipelines.records_created_day', records_created_day, 'records', timestamp),
                    MetricPoint('pipelines.records_updated_day', records_updated_day, 'records', timestamp),
                    MetricPoint('pipelines.active_count', active_pipelines, 'pipelines', timestamp),
                ])
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"Failed to collect business metrics: {e}")
        
        return metrics
    
    def _collect_error_metrics(self, timestamp: datetime) -> List[MetricPoint]:
        """Collect error and exception metrics"""
        metrics = []
        
        try:
            # Django error logging metrics (if available)
            error_counts = cache.get('error_metrics', {})
            for error_type, count in error_counts.items():
                metrics.append(MetricPoint(f'errors.{error_type}', count, 'errors', timestamp))
            
            # System alert metrics
            try:
                from .models import SystemAlert
                
                active_alerts = SystemAlert.objects.filter(is_active=True).count()
                critical_alerts = SystemAlert.objects.filter(
                    is_active=True,
                    severity='critical'
                ).count()
                unacknowledged_alerts = SystemAlert.objects.filter(
                    is_active=True,
                    acknowledged=False
                ).count()
                
                metrics.extend([
                    MetricPoint('alerts.active_count', active_alerts, 'alerts', timestamp),
                    MetricPoint('alerts.critical_count', critical_alerts, 'alerts', timestamp),
                    MetricPoint('alerts.unacknowledged_count', unacknowledged_alerts, 'alerts', timestamp),
                ])
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"Failed to collect error metrics: {e}")
        
        return metrics
    
    def _store_metrics(self, metrics: List[MetricPoint]) -> None:
        """Store metrics in database"""
        try:
            metric_objects = []
            for metric in metrics:
                metric_objects.append(SystemMetrics(
                    metric_name=metric.name,
                    metric_type=self._determine_metric_type(metric.name),
                    value=Decimal(str(metric.value)),
                    unit=metric.unit,
                    tags=metric.tags or {},
                    metadata=metric.metadata or {},
                    timestamp=metric.timestamp
                ))
            
            # Bulk create for performance
            SystemMetrics.objects.bulk_create(metric_objects, batch_size=100)
            
        except Exception as e:
            logger.error(f"Failed to store metrics: {e}")
    
    def _determine_metric_type(self, metric_name: str) -> str:
        """Determine metric type based on metric name"""
        if metric_name.startswith(('cpu.', 'memory.', 'disk.', 'network.', 'process.')):
            return MetricType.PERFORMANCE
        elif metric_name.startswith(('database.', 'cache.', 'requests.', 'sessions.')):
            return MetricType.PERFORMANCE
        elif metric_name.startswith(('users.', 'workflows.', 'communications.', 'pipelines.')):
            return MetricType.BUSINESS
        elif metric_name.startswith(('errors.', 'alerts.')):
            return MetricType.ERROR
        else:
            return MetricType.USAGE
    
    def _update_performance_aggregates(self, timestamp: datetime) -> None:
        """Update performance metrics aggregates"""
        try:
            # Get current hour and day
            current_hour = timestamp.replace(minute=0, second=0, microsecond=0)
            current_day = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Update hourly aggregates
            self._update_hourly_aggregates(current_hour)
            
            # Update daily aggregates
            self._update_daily_aggregates(current_day)
            
        except Exception as e:
            logger.error(f"Failed to update performance aggregates: {e}")
    
    def _update_hourly_aggregates(self, hour_start: datetime) -> None:
        """Update hourly performance aggregates"""
        try:
            hour_end = hour_start + timedelta(hours=1)
            
            # Get or create hourly performance record
            performance, created = PerformanceMetrics.objects.get_or_create(
                period_start=hour_start,
                granularity='hour',
                defaults={
                    'period_end': hour_end,
                }
            )
            
            # Update with latest metrics
            metrics_in_hour = SystemMetrics.objects.filter(
                timestamp__gte=hour_start,
                timestamp__lt=hour_end
            )
            
            # Calculate aggregates
            cpu_metrics = metrics_in_hour.filter(metric_name='cpu.usage_percent')
            if cpu_metrics.exists():
                performance.avg_cpu_usage = cpu_metrics.aggregate(
                    avg=models.Avg('value')
                )['avg']
            
            memory_metrics = metrics_in_hour.filter(metric_name='memory.usage_percent')
            if memory_metrics.exists():
                performance.avg_memory_usage = memory_metrics.aggregate(
                    avg=models.Avg('value')
                )['avg']
            
            # Business metrics
            workflow_executions = metrics_in_hour.filter(metric_name='workflows.executions_last_hour')
            if workflow_executions.exists():
                performance.workflow_executions = int(workflow_executions.last().value)
            
            messages_processed = metrics_in_hour.filter(metric_name='communications.messages_last_hour')
            if messages_processed.exists():
                performance.messages_processed = int(messages_processed.last().value)
            
            active_users = metrics_in_hour.filter(metric_name='users.active_last_hour')
            if active_users.exists():
                performance.active_users = int(active_users.last().value)
            
            performance.save()
            
        except Exception as e:
            logger.error(f"Failed to update hourly aggregates: {e}")
    
    def _update_daily_aggregates(self, day_start: datetime) -> None:
        """Update daily performance aggregates"""
        try:
            day_end = day_start + timedelta(days=1)
            
            # Get or create daily performance record
            performance, created = PerformanceMetrics.objects.get_or_create(
                period_start=day_start,
                granularity='day',
                defaults={
                    'period_end': day_end,
                }
            )
            
            # Update with latest metrics
            metrics_in_day = SystemMetrics.objects.filter(
                timestamp__gte=day_start,
                timestamp__lt=day_end
            )
            
            # Calculate daily aggregates from hourly data
            hourly_metrics = PerformanceMetrics.objects.filter(
                period_start__gte=day_start,
                period_start__lt=day_end,
                granularity='hour'
            )
            
            if hourly_metrics.exists():
                aggregates = hourly_metrics.aggregate(
                    avg_cpu=models.Avg('avg_cpu_usage'),
                    avg_memory=models.Avg('avg_memory_usage'),
                    total_workflows=models.Sum('workflow_executions'),
                    total_messages=models.Sum('messages_processed'),
                    max_active_users=models.Max('active_users')
                )
                
                performance.avg_cpu_usage = aggregates['avg_cpu']
                performance.avg_memory_usage = aggregates['avg_memory']
                performance.workflow_executions = aggregates['total_workflows'] or 0
                performance.messages_processed = aggregates['total_messages'] or 0
                performance.active_users = aggregates['max_active_users'] or 0
            
            performance.save()
            
        except Exception as e:
            logger.error(f"Failed to update daily aggregates: {e}")
    
    def get_metric_history(
        self, 
        metric_name: str, 
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get historical data for a specific metric"""
        try:
            start_time = timezone.now() - timedelta(hours=hours)
            
            metrics = SystemMetrics.objects.filter(
                metric_name=metric_name,
                timestamp__gte=start_time
            ).order_by('timestamp')
            
            return [
                {
                    'timestamp': metric.timestamp.isoformat(),
                    'value': float(metric.value),
                    'unit': metric.unit,
                    'tags': metric.tags,
                    'metadata': metric.metadata
                }
                for metric in metrics
            ]
            
        except Exception as e:
            logger.error(f"Failed to get metric history: {e}")
            return []
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the specified time period"""
        try:
            start_time = timezone.now() - timedelta(hours=hours)
            
            # Get recent metrics
            recent_metrics = SystemMetrics.objects.filter(
                timestamp__gte=start_time
            )
            
            summary = {
                'period_hours': hours,
                'total_metrics_collected': recent_metrics.count(),
                'system_performance': {},
                'business_metrics': {},
                'alerts': {}
            }
            
            # System performance summary
            cpu_metrics = recent_metrics.filter(metric_name='cpu.usage_percent')
            if cpu_metrics.exists():
                cpu_stats = cpu_metrics.aggregate(
                    avg=models.Avg('value'),
                    min=models.Min('value'),
                    max=models.Max('value')
                )
                summary['system_performance']['cpu'] = {
                    'average': float(cpu_stats['avg'] or 0),
                    'minimum': float(cpu_stats['min'] or 0),
                    'maximum': float(cpu_stats['max'] or 0),
                    'unit': '%'
                }
            
            memory_metrics = recent_metrics.filter(metric_name='memory.usage_percent')
            if memory_metrics.exists():
                memory_stats = memory_metrics.aggregate(
                    avg=models.Avg('value'),
                    min=models.Min('value'),
                    max=models.Max('value')
                )
                summary['system_performance']['memory'] = {
                    'average': float(memory_stats['avg'] or 0),
                    'minimum': float(memory_stats['min'] or 0),
                    'maximum': float(memory_stats['max'] or 0),
                    'unit': '%'
                }
            
            # Business metrics summary
            workflow_metrics = recent_metrics.filter(metric_name='workflows.executions_last_day')
            if workflow_metrics.exists():
                latest_workflow = workflow_metrics.last()
                summary['business_metrics']['daily_workflow_executions'] = int(latest_workflow.value)
            
            message_metrics = recent_metrics.filter(metric_name='communications.messages_last_day')
            if message_metrics.exists():
                latest_messages = message_metrics.last()
                summary['business_metrics']['daily_messages'] = int(latest_messages.value)
            
            # Alert summary
            try:
                from .models import SystemAlert
                active_alerts = SystemAlert.objects.filter(is_active=True).count()
                critical_alerts = SystemAlert.objects.filter(
                    is_active=True, 
                    severity='critical'
                ).count()
                
                summary['alerts'] = {
                    'active_count': active_alerts,
                    'critical_count': critical_alerts
                }
            except Exception:
                pass
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {'error': str(e)}


# Create global instance
system_metrics_collector = SystemMetricsCollector()