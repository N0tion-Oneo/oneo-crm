"""
Signal handlers for monitoring system
Automatic monitoring and alerting based on system events
"""
import logging
from typing import Dict, Any

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed

from .models import SystemAlert, SystemMetrics, AlertSeverity, MetricType
from .health import system_health_checker

logger = logging.getLogger(__name__)


# === SYSTEM MONITORING SIGNALS ===

@receiver(post_save, sender=SystemMetrics)
def check_metric_thresholds(sender, instance: SystemMetrics, created: bool, **kwargs):
    """Check if metrics exceed defined thresholds and create alerts"""
    if not created:
        return
    
    try:
        # Define threshold rules
        threshold_rules = {
            'cpu.usage_percent': {'critical': 90, 'warning': 80},
            'memory.usage_percent': {'critical': 90, 'warning': 80},
            'disk.usage_percent': {'critical': 95, 'warning': 85},
            'database.active_connections': {'critical': 100, 'warning': 80},
            'cache.used_memory': {'critical': 1073741824, 'warning': 805306368},  # 1GB, 768MB
            'errors.total_count': {'critical': 100, 'warning': 50},
        }
        
        rule = threshold_rules.get(instance.metric_name)
        if not rule:
            return
        
        current_value = float(instance.value)
        
        # Check critical threshold
        if current_value >= rule['critical']:
            _create_threshold_alert(
                instance, 
                'critical', 
                rule['critical'], 
                current_value,
                AlertSeverity.CRITICAL
            )
        # Check warning threshold
        elif current_value >= rule['warning']:
            _create_threshold_alert(
                instance, 
                'warning', 
                rule['warning'], 
                current_value,
                AlertSeverity.WARNING
            )
        else:
            # Value is within normal range, resolve any existing threshold alerts
            _resolve_threshold_alerts(instance.metric_name)
            
    except Exception as e:
        logger.error(f"Failed to check metric thresholds: {e}")


def _create_threshold_alert(
    metric: SystemMetrics, 
    threshold_type: str, 
    threshold_value: float, 
    actual_value: float,
    severity: str
) -> None:
    """Create a threshold alert if one doesn't already exist"""
    try:
        alert_name = f"{metric.metric_name} {threshold_type} threshold exceeded"
        
        # Check if alert already exists
        existing_alert = SystemAlert.objects.filter(
            alert_name=alert_name,
            metric_name=metric.metric_name,
            is_active=True,
            resolved=False
        ).first()
        
        if existing_alert:
            # Update existing alert with new values
            existing_alert.actual_value = actual_value
            existing_alert.alert_data.update({
                'last_updated': timezone.now().isoformat(),
                'consecutive_violations': existing_alert.alert_data.get('consecutive_violations', 0) + 1
            })
            existing_alert.save()
        else:
            # Create new alert
            SystemAlert.objects.create(
                alert_name=alert_name,
                alert_type='metric_threshold',
                severity=severity,
                message=f"{metric.metric_name} has exceeded {threshold_type} threshold",
                description=f"Metric {metric.metric_name} value {actual_value} {metric.unit} exceeds {threshold_type} threshold of {threshold_value} {metric.unit}",
                component='system_metrics',
                metric_name=metric.metric_name,
                threshold_value=threshold_value,
                actual_value=actual_value,
                alert_data={
                    'metric_type': metric.metric_type,
                    'metric_unit': metric.unit,
                    'threshold_type': threshold_type,
                    'metric_timestamp': metric.timestamp.isoformat(),
                    'consecutive_violations': 1
                }
            )
            
        logger.warning(f"Threshold alert created: {alert_name}")
        
    except Exception as e:
        logger.error(f"Failed to create threshold alert: {e}")


def _resolve_threshold_alerts(metric_name: str) -> None:
    """Resolve threshold alerts for a metric when it returns to normal"""
    try:
        active_alerts = SystemAlert.objects.filter(
            metric_name=metric_name,
            alert_type='metric_threshold',
            is_active=True,
            resolved=False
        )
        
        for alert in active_alerts:
            alert.resolved = True
            alert.resolved_at = timezone.now()
            alert.is_active = False
            alert.resolution_notes = "Metric returned to normal threshold range"
            alert.save()
            
        if active_alerts.exists():
            logger.info(f"Resolved {active_alerts.count()} threshold alerts for {metric_name}")
            
    except Exception as e:
        logger.error(f"Failed to resolve threshold alerts: {e}")


# === AUTHENTICATION MONITORING SIGNALS ===

@receiver(user_login_failed)
def monitor_failed_logins(sender, credentials, request, **kwargs):
    """Monitor failed login attempts for security alerts"""
    try:
        # Get client IP
        ip_address = _get_client_ip(request) if request else 'unknown'
        username = credentials.get('username', 'unknown')
        
        # Create metric for failed login
        SystemMetrics.objects.create(
            metric_name='auth.login_failed',
            metric_type=MetricType.SECURITY,
            value=1,
            unit='attempt',
            tags={
                'username': username,
                'ip_address': ip_address,
                'user_agent': request.META.get('HTTP_USER_AGENT', '') if request else ''
            },
            metadata={
                'event_type': 'login_failed',
                'timestamp': timezone.now().isoformat()
            }
        )
        
        # Check for brute force attempts
        _check_brute_force_attempts(username, ip_address)
        
    except Exception as e:
        logger.error(f"Failed to monitor failed login: {e}")


@receiver(user_logged_in)
def monitor_successful_logins(sender, user, request, **kwargs):
    """Monitor successful logins for analytics"""
    try:
        # Get client IP
        ip_address = _get_client_ip(request) if request else 'unknown'
        
        # Create metric for successful login
        SystemMetrics.objects.create(
            metric_name='auth.login_success',
            metric_type=MetricType.USAGE,
            value=1,
            unit='login',
            tags={
                'username': user.username,
                'user_id': str(user.id),
                'ip_address': ip_address
            },
            metadata={
                'event_type': 'login_success',
                'timestamp': timezone.now().isoformat()
            }
        )
        
        # Update user activity metrics
        SystemMetrics.objects.create(
            metric_name='users.active_sessions',
            metric_type=MetricType.USAGE,
            value=1,
            unit='session',
            tags={'user_id': str(user.id)},
            metadata={'session_started': timezone.now().isoformat()}
        )
        
    except Exception as e:
        logger.error(f"Failed to monitor successful login: {e}")


@receiver(user_logged_out)
def monitor_logouts(sender, user, request, **kwargs):
    """Monitor user logouts"""
    try:
        if user:
            # Create metric for logout
            SystemMetrics.objects.create(
                metric_name='auth.logout',
                metric_type=MetricType.USAGE,
                value=1,
                unit='logout',
                tags={
                    'username': user.username,
                    'user_id': str(user.id)
                },
                metadata={
                    'event_type': 'logout',
                    'timestamp': timezone.now().isoformat()
                }
            )
            
    except Exception as e:
        logger.error(f"Failed to monitor logout: {e}")


def _check_brute_force_attempts(username: str, ip_address: str) -> None:
    """Check for brute force login attempts"""
    try:
        # Check failed attempts in last 15 minutes
        recent_failures = SystemMetrics.objects.filter(
            metric_name='auth.login_failed',
            timestamp__gte=timezone.now() - timezone.timedelta(minutes=15),
            tags__username=username
        ).count()
        
        # Check IP-based failures
        ip_failures = SystemMetrics.objects.filter(
            metric_name='auth.login_failed',
            timestamp__gte=timezone.now() - timezone.timedelta(minutes=30),
            tags__ip_address=ip_address
        ).count()
        
        # Create alerts for suspicious activity
        if recent_failures >= 5:
            _create_security_alert(
                'Brute Force Attack Detected',
                f"User {username} has {recent_failures} failed login attempts in 15 minutes",
                AlertSeverity.CRITICAL,
                {
                    'username': username,
                    'ip_address': ip_address,
                    'failed_attempts': recent_failures,
                    'time_window': '15 minutes'
                }
            )
        elif ip_failures >= 10:
            _create_security_alert(
                'Suspicious IP Activity',
                f"IP {ip_address} has {ip_failures} failed login attempts in 30 minutes",
                AlertSeverity.WARNING,
                {
                    'ip_address': ip_address,
                    'failed_attempts': ip_failures,
                    'time_window': '30 minutes'
                }
            )
            
    except Exception as e:
        logger.error(f"Failed to check brute force attempts: {e}")


# === APPLICATION MONITORING SIGNALS ===

def monitor_workflow_execution(workflow_execution):
    """Monitor workflow execution events"""
    try:
        # Create metrics based on workflow execution
        if workflow_execution.status == 'completed':
            SystemMetrics.objects.create(
                metric_name='workflows.execution_success',
                metric_type=MetricType.BUSINESS,
                value=1,
                unit='execution',
                tags={
                    'workflow_id': str(workflow_execution.workflow.id),
                    'workflow_name': workflow_execution.workflow.name
                },
                metadata={
                    'execution_time_seconds': workflow_execution.duration_seconds,
                    'node_count': workflow_execution.logs.count()
                }
            )
        elif workflow_execution.status == 'failed':
            SystemMetrics.objects.create(
                metric_name='workflows.execution_failure',
                metric_type=MetricType.ERROR,
                value=1,
                unit='execution',
                tags={
                    'workflow_id': str(workflow_execution.workflow.id),
                    'workflow_name': workflow_execution.workflow.name
                },
                metadata={
                    'error_message': workflow_execution.error_message or 'Unknown error',
                    'execution_time_seconds': workflow_execution.duration_seconds
                }
            )
            
            # Create alert for workflow failures
            _create_workflow_failure_alert(workflow_execution)
            
    except Exception as e:
        logger.error(f"Failed to monitor workflow execution: {e}")


def monitor_communication_activity(message):
    """Monitor communication system activity"""
    try:
        # Create metrics for message activity
        if message.direction == 'outbound':
            if message.status == 'delivered':
                SystemMetrics.objects.create(
                    metric_name='communications.message_delivered',
                    metric_type=MetricType.BUSINESS,
                    value=1,
                    unit='message',
                    tags={
                        'channel_id': str(message.channel.id),
                        'channel_type': message.channel.channel_type
                    }
                )
            elif message.status == 'failed':
                SystemMetrics.objects.create(
                    metric_name='communications.message_failed',
                    metric_type=MetricType.ERROR,
                    value=1,
                    unit='message',
                    tags={
                        'channel_id': str(message.channel.id),
                        'channel_type': message.channel.channel_type
                    }
                )
        
    except Exception as e:
        logger.error(f"Failed to monitor communication activity: {e}")


# === HELPER FUNCTIONS ===

def _get_client_ip(request) -> str:
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def _create_security_alert(
    alert_name: str, 
    message: str, 
    severity: str, 
    alert_data: Dict[str, Any]
) -> None:
    """Create a security alert"""
    try:
        # Check if similar alert already exists
        existing_alert = SystemAlert.objects.filter(
            alert_name=alert_name,
            alert_type='security',
            is_active=True,
            resolved=False
        ).first()
        
        if not existing_alert:
            SystemAlert.objects.create(
                alert_name=alert_name,
                alert_type='security',
                severity=severity,
                message=message,
                description=f"Security event detected: {message}",
                component='security',
                alert_data=alert_data
            )
            
            logger.warning(f"Security alert created: {alert_name}")
            
    except Exception as e:
        logger.error(f"Failed to create security alert: {e}")


def _create_workflow_failure_alert(workflow_execution) -> None:
    """Create alert for workflow failure"""
    try:
        # Check for recent failures in the same workflow
        recent_failures = SystemMetrics.objects.filter(
            metric_name='workflows.execution_failure',
            timestamp__gte=timezone.now() - timezone.timedelta(hours=1),
            tags__workflow_id=str(workflow_execution.workflow.id)
        ).count()
        
        if recent_failures >= 3:  # 3 failures in 1 hour
            SystemAlert.objects.create(
                alert_name=f"Workflow {workflow_execution.workflow.name} Repeated Failures",
                alert_type='workflow_failure',
                severity=AlertSeverity.ERROR,
                message=f"Workflow has failed {recent_failures} times in the last hour",
                description=f"Workflow {workflow_execution.workflow.name} has experienced repeated failures",
                component='workflow_engine',
                alert_data={
                    'workflow_id': str(workflow_execution.workflow.id),
                    'workflow_name': workflow_execution.workflow.name,
                    'failure_count': recent_failures,
                    'last_error': workflow_execution.error_message or 'Unknown error'
                }
            )
            
    except Exception as e:
        logger.error(f"Failed to create workflow failure alert: {e}")


# === CUSTOM SIGNAL HANDLERS FOR MONITORING ===

class MonitoringSignalHandler:
    """Custom signal handler for monitoring events"""
    
    @staticmethod
    def handle_database_error(error_details: Dict[str, Any]) -> None:
        """Handle database error events"""
        try:
            SystemMetrics.objects.create(
                metric_name='database.error',
                metric_type=MetricType.ERROR,
                value=1,
                unit='error',
                tags={
                    'error_type': error_details.get('error_type', 'unknown'),
                    'database': error_details.get('database', 'default')
                },
                metadata=error_details
            )
            
            # Create alert for database errors
            if error_details.get('severity') == 'critical':
                _create_security_alert(
                    'Database Critical Error',
                    f"Critical database error: {error_details.get('message', 'Unknown error')}",
                    AlertSeverity.CRITICAL,
                    error_details
                )
                
        except Exception as e:
            logger.error(f"Failed to handle database error signal: {e}")
    
    @staticmethod
    def handle_performance_degradation(performance_data: Dict[str, Any]) -> None:
        """Handle performance degradation events"""
        try:
            SystemMetrics.objects.create(
                metric_name='performance.degradation',
                metric_type=MetricType.PERFORMANCE,
                value=performance_data.get('severity_score', 1),
                unit='score',
                tags={
                    'component': performance_data.get('component', 'unknown'),
                    'metric_type': performance_data.get('metric_type', 'unknown')
                },
                metadata=performance_data
            )
            
        except Exception as e:
            logger.error(f"Failed to handle performance degradation signal: {e}")


# Create global signal handler instance
monitoring_signal_handler = MonitoringSignalHandler()