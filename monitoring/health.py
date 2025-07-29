"""
System health monitoring and checking
Provides comprehensive health checks for all system components
"""
import logging
import time
import psutil
import redis
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from django.db import connection, connections
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import SystemHealthCheck, HealthStatus, SystemAlert, AlertSeverity

User = get_user_model()
logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Data structure for health check results"""
    component_name: str
    component_type: str
    status: str
    message: str
    response_time_ms: Optional[int] = None
    details: Dict[str, Any] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    disk_usage: Optional[float] = None


class SystemHealthChecker:
    """
    Comprehensive system health monitoring
    Checks all critical system components
    """
    
    def __init__(self):
        self.timeout_seconds = 30
        
    def run_all_checks(self) -> List[HealthCheckResult]:
        """Run all health checks and return results"""
        checks = [
            self.check_database,
            self.check_cache,
            self.check_celery_workers,
            self.check_file_storage,
            self.check_system_resources,
            self.check_workflow_engine,
            self.check_communication_system,
            self.check_authentication,
            self.check_external_apis
        ]
        
        results = []
        for check in checks:
            try:
                result = check()
                results.append(result)
                
                # Store result in database
                self._store_health_check(result)
                
                # Check for alerts
                self._check_for_alerts(result)
                
            except Exception as e:
                logger.error(f"Health check failed: {check.__name__}: {e}")
                error_result = HealthCheckResult(
                    component_name=check.__name__.replace('check_', ''),
                    component_type='unknown',
                    status=HealthStatus.CRITICAL,
                    message=f"Health check failed: {str(e)}",
                    details={'error': str(e)}
                )
                results.append(error_result)
                self._store_health_check(error_result)
        
        return results
    
    def check_database(self) -> HealthCheckResult:
        """Check database connectivity and performance"""
        start_time = time.time()
        
        try:
            # Test connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            # Test all database connections
            connection_statuses = {}
            for db_name in connections:
                try:
                    db_conn = connections[db_name]
                    with db_conn.cursor() as cursor:
                        cursor.execute("SELECT version()")
                        version = cursor.fetchone()[0]
                        connection_statuses[db_name] = {
                            'status': 'healthy',
                            'version': version
                        }
                except Exception as e:
                    connection_statuses[db_name] = {
                        'status': 'error',
                        'error': str(e)
                    }
            
            response_time = int((time.time() - start_time) * 1000)
            
            # Check for slow queries or connection issues
            if response_time > 1000:  # Slower than 1 second
                status = HealthStatus.WARNING
                message = f"Database responding slowly ({response_time}ms)"
            elif any(conn['status'] == 'error' for conn in connection_statuses.values()):
                status = HealthStatus.CRITICAL
                message = "One or more database connections failed"
            else:
                status = HealthStatus.HEALTHY
                message = "Database connections healthy"
            
            return HealthCheckResult(
                component_name='database',
                component_type='database',
                status=status,
                message=message,
                response_time_ms=response_time,
                details={
                    'connections': connection_statuses,
                    'active_connections': len(connections)
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                component_name='database',
                component_type='database',
                status=HealthStatus.DOWN,
                message=f"Database connection failed: {str(e)}",
                response_time_ms=int((time.time() - start_time) * 1000),
                details={'error': str(e)}
            )
    
    def check_cache(self) -> HealthCheckResult:
        """Check cache system (Redis) connectivity and performance"""
        start_time = time.time()
        
        try:
            # Test cache operations
            test_key = f"health_check_{int(time.time())}"
            test_value = "health_check_value"
            
            # Set and get test value
            cache.set(test_key, test_value, timeout=60)
            cached_value = cache.get(test_key)
            cache.delete(test_key)
            
            response_time = int((time.time() - start_time) * 1000)
            
            if cached_value != test_value:
                status = HealthStatus.CRITICAL
                message = "Cache read/write operations failed"
                details = {'error': 'Value mismatch in cache operations'}
            elif response_time > 500:  # Slower than 500ms
                status = HealthStatus.WARNING
                message = f"Cache responding slowly ({response_time}ms)"
                details = {'response_time_ms': response_time}
            else:
                status = HealthStatus.HEALTHY
                message = "Cache operations healthy"
                details = {'response_time_ms': response_time}
            
            # Get Redis info if available
            try:
                import redis
                redis_client = redis.Redis.from_url(settings.CACHES['default']['LOCATION'])
                redis_info = redis_client.info()
                details.update({
                    'redis_version': redis_info.get('redis_version'),
                    'used_memory': redis_info.get('used_memory_human'),
                    'connected_clients': redis_info.get('connected_clients'),
                    'uptime_in_seconds': redis_info.get('uptime_in_seconds')
                })
            except Exception:
                pass
            
            return HealthCheckResult(
                component_name='cache',
                component_type='cache',
                status=status,
                message=message,
                response_time_ms=response_time,
                details=details
            )
            
        except Exception as e:
            return HealthCheckResult(
                component_name='cache',
                component_type='cache',
                status=HealthStatus.DOWN,
                message=f"Cache system failed: {str(e)}",
                response_time_ms=int((time.time() - start_time) * 1000),
                details={'error': str(e)}
            )
    
    def check_celery_workers(self) -> HealthCheckResult:
        """Check Celery worker status and queue health"""
        start_time = time.time()
        
        try:
            from celery import current_app
            
            # Get worker stats
            inspect = current_app.control.inspect()
            
            # Check active workers
            stats = inspect.stats()
            active = inspect.active()
            reserved = inspect.reserved()
            
            response_time = int((time.time() - start_time) * 1000)
            
            if not stats:
                status = HealthStatus.CRITICAL
                message = "No Celery workers found"
                details = {'error': 'No active workers'}
            else:
                worker_count = len(stats)
                total_active_tasks = sum(len(tasks) for tasks in (active.values() if active else []))
                total_reserved_tasks = sum(len(tasks) for tasks in (reserved.values() if reserved else []))
                
                if worker_count == 0:
                    status = HealthStatus.CRITICAL
                    message = "No active Celery workers"
                elif total_active_tasks > 100:  # High task load
                    status = HealthStatus.WARNING
                    message = f"High task load: {total_active_tasks} active tasks"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"Celery workers healthy ({worker_count} workers)"
                
                details = {
                    'worker_count': worker_count,
                    'active_tasks': total_active_tasks,
                    'reserved_tasks': total_reserved_tasks,
                    'workers': list(stats.keys()) if stats else []
                }
            
            return HealthCheckResult(
                component_name='celery',
                component_type='celery',
                status=status,
                message=message,
                response_time_ms=response_time,
                details=details
            )
            
        except ImportError:
            return HealthCheckResult(
                component_name='celery',
                component_type='celery',
                status=HealthStatus.WARNING,
                message="Celery not configured",
                response_time_ms=int((time.time() - start_time) * 1000),
                details={'info': 'Celery not available'}
            )
        except Exception as e:
            return HealthCheckResult(
                component_name='celery',
                component_type='celery',
                status=HealthStatus.CRITICAL,
                message=f"Celery check failed: {str(e)}",
                response_time_ms=int((time.time() - start_time) * 1000),
                details={'error': str(e)}
            )
    
    def check_file_storage(self) -> HealthCheckResult:
        """Check file storage system health"""
        start_time = time.time()
        
        try:
            from django.core.files.storage import default_storage
            import tempfile
            import os
            
            # Test file operations
            test_filename = f"health_check_{int(time.time())}.txt"
            test_content = b"Health check test content"
            
            # Write test file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(test_content)
                temp_path = temp_file.name
            
            # Test storage operations
            with open(temp_path, 'rb') as test_file:
                saved_path = default_storage.save(test_filename, test_file)
            
            # Test file exists and read
            if default_storage.exists(saved_path):
                with default_storage.open(saved_path, 'rb') as stored_file:
                    stored_content = stored_file.read()
                
                # Clean up
                default_storage.delete(saved_path)
                os.unlink(temp_path)
                
                response_time = int((time.time() - start_time) * 1000)
                
                if stored_content == test_content:
                    status = HealthStatus.HEALTHY
                    message = "File storage operations healthy"
                else:
                    status = HealthStatus.CRITICAL
                    message = "File storage read/write verification failed"
            else:
                status = HealthStatus.CRITICAL
                message = "File storage save operation failed"
                os.unlink(temp_path)
            
            # Get storage info
            details = {
                'storage_backend': default_storage.__class__.__name__,
                'response_time_ms': response_time
            }
            
            # Check disk space if local storage
            if hasattr(default_storage, 'location'):
                try:
                    disk_usage = psutil.disk_usage(default_storage.location)
                    free_space_gb = disk_usage.free / (1024**3)
                    total_space_gb = disk_usage.total / (1024**3)
                    used_percent = (disk_usage.used / disk_usage.total) * 100
                    
                    details.update({
                        'free_space_gb': round(free_space_gb, 2),
                        'total_space_gb': round(total_space_gb, 2),
                        'used_percent': round(used_percent, 2)
                    })
                    
                    if used_percent > 90:
                        status = HealthStatus.CRITICAL
                        message = f"Disk space critical: {used_percent:.1f}% used"
                    elif used_percent > 80:
                        status = HealthStatus.WARNING
                        message = f"Disk space warning: {used_percent:.1f}% used"
                        
                except Exception:
                    pass
            
            return HealthCheckResult(
                component_name='file_storage',
                component_type='storage',
                status=status,
                message=message,
                response_time_ms=response_time,
                details=details
            )
            
        except Exception as e:
            return HealthCheckResult(
                component_name='file_storage',
                component_type='storage',
                status=HealthStatus.CRITICAL,
                message=f"File storage check failed: {str(e)}",
                response_time_ms=int((time.time() - start_time) * 1000),
                details={'error': str(e)}
            )
    
    def check_system_resources(self) -> HealthCheckResult:
        """Check system resource usage (CPU, memory, disk)"""
        start_time = time.time()
        
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            response_time = int((time.time() - start_time) * 1000)
            
            # Determine status based on resource usage
            if cpu_percent > 90 or memory.percent > 90 or (disk.used / disk.total * 100) > 90:
                status = HealthStatus.CRITICAL
                message = "Critical resource usage detected"
            elif cpu_percent > 80 or memory.percent > 80 or (disk.used / disk.total * 100) > 80:
                status = HealthStatus.WARNING
                message = "High resource usage detected"
            else:
                status = HealthStatus.HEALTHY
                message = "System resources healthy"
            
            details = {
                'cpu_percent': round(cpu_percent, 2),
                'memory_percent': round(memory.percent, 2),
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'disk_percent': round((disk.used / disk.total * 100), 2),
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'disk_total_gb': round(disk.total / (1024**3), 2),
                'load_average': list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
            }
            
            return HealthCheckResult(
                component_name='system_resources',
                component_type='system',
                status=status,
                message=message,
                response_time_ms=response_time,
                details=details,
                cpu_usage=cpu_percent,
                memory_usage=memory.percent,
                disk_usage=(disk.used / disk.total * 100)
            )
            
        except Exception as e:
            return HealthCheckResult(
                component_name='system_resources',
                component_type='system',
                status=HealthStatus.CRITICAL,
                message=f"System resource check failed: {str(e)}",
                response_time_ms=int((time.time() - start_time) * 1000),
                details={'error': str(e)}
            )
    
    def check_workflow_engine(self) -> HealthCheckResult:
        """Check workflow engine health"""
        start_time = time.time()
        
        try:
            from workflows.models import Workflow, WorkflowExecution
            from workflows.triggers.manager import TriggerManager
            
            # Basic workflow system checks
            active_workflows = Workflow.objects.filter(status='active').count()
            recent_executions = WorkflowExecution.objects.filter(
                started_at__gte=timezone.now() - timedelta(hours=1)
            ).count()
            failed_executions = WorkflowExecution.objects.filter(
                status='failed',
                started_at__gte=timezone.now() - timedelta(hours=1)
            ).count()
            
            response_time = int((time.time() - start_time) * 1000)
            
            # Check trigger manager
            trigger_manager_healthy = True
            try:
                # This would check if trigger manager is responsive
                # Placeholder for actual trigger manager health check
                pass
            except Exception:
                trigger_manager_healthy = False
            
            # Determine status
            failure_rate = (failed_executions / recent_executions * 100) if recent_executions > 0 else 0
            
            if not trigger_manager_healthy:
                status = HealthStatus.CRITICAL
                message = "Workflow trigger manager not responding"
            elif failure_rate > 50:
                status = HealthStatus.CRITICAL
                message = f"High workflow failure rate: {failure_rate:.1f}%"
            elif failure_rate > 20:
                status = HealthStatus.WARNING
                message = f"Elevated workflow failure rate: {failure_rate:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = "Workflow engine healthy"
            
            details = {
                'active_workflows': active_workflows,
                'recent_executions': recent_executions,
                'failed_executions': failed_executions,
                'failure_rate_percent': round(failure_rate, 2),
                'trigger_manager_healthy': trigger_manager_healthy
            }
            
            return HealthCheckResult(
                component_name='workflow_engine',
                component_type='workflow_engine',
                status=status,
                message=message,
                response_time_ms=response_time,
                details=details
            )
            
        except Exception as e:
            return HealthCheckResult(
                component_name='workflow_engine',
                component_type='workflow_engine',
                status=HealthStatus.CRITICAL,
                message=f"Workflow engine check failed: {str(e)}",
                response_time_ms=int((time.time() - start_time) * 1000),
                details={'error': str(e)}
            )
    
    def check_communication_system(self) -> HealthCheckResult:
        """Check communication system health"""
        start_time = time.time()
        
        try:
            from communications.models import Channel, Message
            
            # Check communication system
            active_channels = Channel.objects.filter(is_active=True).count()
            recent_messages = Message.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=1)
            ).count()
            failed_messages = Message.objects.filter(
                status='failed',
                created_at__gte=timezone.now() - timedelta(hours=1)
            ).count()
            
            response_time = int((time.time() - start_time) * 1000)
            
            # Determine status
            failure_rate = (failed_messages / recent_messages * 100) if recent_messages > 0 else 0
            
            if active_channels == 0:
                status = HealthStatus.WARNING
                message = "No active communication channels"
            elif failure_rate > 25:
                status = HealthStatus.CRITICAL
                message = f"High message failure rate: {failure_rate:.1f}%"
            elif failure_rate > 10:
                status = HealthStatus.WARNING
                message = f"Elevated message failure rate: {failure_rate:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = "Communication system healthy"
            
            details = {
                'active_channels': active_channels,
                'recent_messages': recent_messages,
                'failed_messages': failed_messages,
                'failure_rate_percent': round(failure_rate, 2)
            }
            
            return HealthCheckResult(
                component_name='communication_system',
                component_type='communication',
                status=status,
                message=message,
                response_time_ms=response_time,
                details=details
            )
            
        except Exception as e:
            return HealthCheckResult(
                component_name='communication_system',
                component_type='communication',
                status=HealthStatus.CRITICAL,
                message=f"Communication system check failed: {str(e)}",
                response_time_ms=int((time.time() - start_time) * 1000),
                details={'error': str(e)}
            )
    
    def check_authentication(self) -> HealthCheckResult:
        """Check authentication system health"""
        start_time = time.time()
        
        try:
            from authentication.models import User
            from django.contrib.sessions.models import Session
            
            # Check authentication system
            total_users = User.objects.count()
            active_sessions = Session.objects.filter(
                expire_date__gte=timezone.now()
            ).count()
            
            response_time = int((time.time() - start_time) * 1000)
            
            # Basic authentication health check
            if total_users == 0:
                status = HealthStatus.WARNING
                message = "No users in system"
            else:
                status = HealthStatus.HEALTHY
                message = "Authentication system healthy"
            
            details = {
                'total_users': total_users,
                'active_sessions': active_sessions,
            }
            
            return HealthCheckResult(
                component_name='authentication',
                component_type='auth',
                status=status,
                message=message,
                response_time_ms=response_time,
                details=details
            )
            
        except Exception as e:
            return HealthCheckResult(
                component_name='authentication',
                component_type='auth',
                status=HealthStatus.CRITICAL,
                message=f"Authentication check failed: {str(e)}",
                response_time_ms=int((time.time() - start_time) * 1000),
                details={'error': str(e)}
            )
    
    def check_external_apis(self) -> HealthCheckResult:
        """Check external API dependencies"""
        start_time = time.time()
        
        try:
            import requests
            
            # List of critical external APIs to check
            apis_to_check = []
            
            # Add OpenAI API if configured
            if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
                apis_to_check.append({
                    'name': 'OpenAI API',
                    'url': 'https://api.openai.com/v1/models',
                    'headers': {'Authorization': f'Bearer {settings.OPENAI_API_KEY}'}
                })
            
            # Add UniPile API if configured
            if hasattr(settings, 'UNIPILE_API_KEY') and settings.UNIPILE_API_KEY:
                apis_to_check.append({
                    'name': 'UniPile API',
                    'url': 'https://api.unipile.com/api/v1/health',
                    'headers': {'Authorization': f'Bearer {settings.UNIPILE_API_KEY}'}
                })
            
            response_time = int((time.time() - start_time) * 1000)
            
            if not apis_to_check:
                return HealthCheckResult(
                    component_name='external_apis',
                    component_type='external_api',
                    status=HealthStatus.HEALTHY,
                    message="No external APIs configured",
                    response_time_ms=response_time,
                    details={'info': 'No external APIs to check'}
                )
            
            # Check each API
            api_results = {}
            overall_status = HealthStatus.HEALTHY
            
            for api in apis_to_check:
                try:
                    api_start = time.time()
                    response = requests.get(
                        api['url'],
                        headers=api.get('headers', {}),
                        timeout=10
                    )
                    api_time = int((time.time() - api_start) * 1000)
                    
                    if response.status_code == 200:
                        api_results[api['name']] = {
                            'status': 'healthy',
                            'response_time_ms': api_time,
                            'status_code': response.status_code
                        }
                    else:
                        api_results[api['name']] = {
                            'status': 'error',
                            'response_time_ms': api_time,
                            'status_code': response.status_code
                        }
                        overall_status = HealthStatus.WARNING
                        
                except requests.RequestException as e:
                    api_results[api['name']] = {
                        'status': 'error',
                        'error': str(e)
                    }
                    overall_status = HealthStatus.CRITICAL
            
            # Determine overall message
            healthy_apis = sum(1 for result in api_results.values() if result.get('status') == 'healthy')
            total_apis = len(api_results)
            
            if healthy_apis == total_apis:
                message = f"All external APIs healthy ({total_apis}/{total_apis})"
            elif healthy_apis > 0:
                message = f"Some external APIs failing ({healthy_apis}/{total_apis} healthy)"
            else:
                message = "All external APIs failing"
                overall_status = HealthStatus.CRITICAL
            
            return HealthCheckResult(
                component_name='external_apis',
                component_type='external_api',
                status=overall_status,
                message=message,
                response_time_ms=response_time,
                details={
                    'apis_checked': total_apis,
                    'apis_healthy': healthy_apis,
                    'results': api_results
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                component_name='external_apis',
                component_type='external_api',
                status=HealthStatus.CRITICAL,
                message=f"External API check failed: {str(e)}",
                response_time_ms=int((time.time() - start_time) * 1000),
                details={'error': str(e)}
            )
    
    def _store_health_check(self, result: HealthCheckResult) -> None:
        """Store health check result in database"""
        try:
            SystemHealthCheck.objects.create(
                component_name=result.component_name,
                component_type=result.component_type,
                status=result.status,
                response_time_ms=result.response_time_ms,
                message=result.message,
                details=result.details or {},
                cpu_usage_percent=result.cpu_usage,
                memory_usage_percent=result.memory_usage,
                disk_usage_percent=result.disk_usage,
                checked_at=timezone.now()
            )
        except Exception as e:
            logger.error(f"Failed to store health check result: {e}")
    
    def _check_for_alerts(self, result: HealthCheckResult) -> None:
        """Check if health check result should trigger alerts"""
        try:
            if result.status in [HealthStatus.CRITICAL, HealthStatus.DOWN]:
                # Check if alert already exists
                existing_alert = SystemAlert.objects.filter(
                    component=result.component_name,
                    alert_type='health_check',
                    is_active=True,
                    resolved=False
                ).first()
                
                if not existing_alert:
                    # Create new alert
                    SystemAlert.objects.create(
                        alert_name=f"{result.component_name} Health Check Failed",
                        alert_type='health_check',
                        severity=AlertSeverity.CRITICAL if result.status == HealthStatus.CRITICAL else AlertSeverity.ERROR,
                        message=result.message,
                        description=f"Health check for {result.component_name} returned {result.status}",
                        component=result.component_name,
                        alert_data={
                            'health_check_result': {
                                'status': result.status,
                                'message': result.message,
                                'response_time_ms': result.response_time_ms,
                                'details': result.details
                            }
                        }
                    )
                    
            elif result.status == HealthStatus.HEALTHY:
                # Resolve any existing alerts for this component
                active_alerts = SystemAlert.objects.filter(
                    component=result.component_name,
                    alert_type='health_check',
                    is_active=True,
                    resolved=False
                )
                
                for alert in active_alerts:
                    alert.resolved = True
                    alert.resolved_at = timezone.now()
                    alert.is_active = False
                    alert.resolution_notes = "Component health check returned to healthy status"
                    alert.save()
                    
        except Exception as e:
            logger.error(f"Failed to process health check alerts: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status summary"""
        try:
            # Get recent health checks (last 5 minutes)
            recent_checks = SystemHealthCheck.objects.filter(
                checked_at__gte=timezone.now() - timedelta(minutes=5)
            ).order_by('component_name', '-checked_at').distinct('component_name')
            
            status_counts = {
                HealthStatus.HEALTHY: 0,
                HealthStatus.WARNING: 0,
                HealthStatus.CRITICAL: 0,
                HealthStatus.DOWN: 0
            }
            
            component_statuses = {}
            
            for check in recent_checks:
                status_counts[check.status] += 1
                component_statuses[check.component_name] = {
                    'status': check.status,
                    'message': check.message,
                    'checked_at': check.checked_at.isoformat(),
                    'response_time_ms': check.response_time_ms
                }
            
            # Determine overall system status
            if status_counts[HealthStatus.DOWN] > 0:
                overall_status = HealthStatus.DOWN
                overall_message = f"{status_counts[HealthStatus.DOWN]} components are down"
            elif status_counts[HealthStatus.CRITICAL] > 0:
                overall_status = HealthStatus.CRITICAL
                overall_message = f"{status_counts[HealthStatus.CRITICAL]} components are critical"
            elif status_counts[HealthStatus.WARNING] > 0:
                overall_status = HealthStatus.WARNING
                overall_message = f"{status_counts[HealthStatus.WARNING]} components have warnings"
            else:
                overall_status = HealthStatus.HEALTHY
                overall_message = "All components are healthy"
            
            return {
                'overall_status': overall_status,
                'overall_message': overall_message,
                'component_count': len(component_statuses),
                'status_counts': status_counts,
                'components': component_statuses,
                'last_updated': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                'overall_status': HealthStatus.CRITICAL,
                'overall_message': f"Failed to get system status: {str(e)}",
                'error': str(e)
            }


# Create global instance
system_health_checker = SystemHealthChecker()