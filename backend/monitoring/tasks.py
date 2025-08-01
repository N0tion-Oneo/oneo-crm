"""
Celery tasks for monitoring and reporting system
Background tasks for health checks, metrics collection, and report generation
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from django.contrib.auth import get_user_model

from .models import Report, SystemAlert, SystemMetrics, PerformanceMetrics, MonitoringConfiguration
from .health import system_health_checker
from .metrics import system_metrics_collector
from .reports import report_generator

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def run_system_health_checks(self):
    """Run comprehensive system health checks"""
    try:
        logger.info("Starting system health checks")
        
        # Run all health checks
        health_results = system_health_checker.run_all_checks()
        
        # Update system status cache
        system_status = system_health_checker.get_system_status()
        cache.set('system_status', system_status, timeout=300)  # Cache for 5 minutes
        
        logger.info(f"Completed {len(health_results)} health checks")
        return {
            'status': 'success',
            'checks_completed': len(health_results),
            'overall_status': system_status.get('overall_status', 'unknown'),
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to run system health checks: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def collect_system_metrics(self):
    """Collect comprehensive system metrics"""
    try:
        logger.info("Starting system metrics collection")
        
        # Collect all metrics
        metrics = system_metrics_collector.collect_all_metrics()
        
        # Update metrics cache
        performance_summary = system_metrics_collector.get_performance_summary(hours=1)
        cache.set('performance_summary', performance_summary, timeout=300)
        
        logger.info(f"Collected {len(metrics)} system metrics")
        return {
            'status': 'success',
            'metrics_collected': len(metrics),
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to collect system metrics: {e}")
        raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=2)
def generate_scheduled_reports(self):
    """Generate scheduled reports based on configuration"""
    try:
        logger.info("Starting scheduled report generation")
        
        # Get report configurations
        report_configs = MonitoringConfiguration.objects.filter(
            config_type='report_schedule',
            is_enabled=True
        )
        
        reports_generated = 0
        
        for config in report_configs:
            try:
                config_data = config.config_data
                report_type = config_data.get('report_type')
                schedule = config_data.get('schedule', 'daily')
                
                # Check if report should be generated based on schedule
                if not _should_generate_report(config, schedule):
                    continue
                
                # Generate report based on type
                if report_type == 'system_health':
                    report = report_generator.generate_system_health_report(
                        date_range_days=config_data.get('date_range_days', 7)
                    )
                elif report_type == 'performance':
                    report = report_generator.generate_performance_report(
                        date_range_days=config_data.get('date_range_days', 7),
                        granularity=config_data.get('granularity', 'hour')
                    )
                elif report_type == 'business':
                    report = report_generator.generate_business_report(
                        date_range_days=config_data.get('date_range_days', 30)
                    )
                elif report_type == 'security':
                    report = report_generator.generate_security_report(
                        date_range_days=config_data.get('date_range_days', 7)
                    )
                else:
                    logger.warning(f"Unknown report type: {report_type}")
                    continue
                
                # Update last generation time
                config.config_data['last_generated'] = timezone.now().isoformat()
                config.save()
                
                reports_generated += 1
                logger.info(f"Generated {report_type} report: {report.id}")
                
            except Exception as e:
                logger.error(f"Failed to generate report for config {config.id}: {e}")
        
        return {
            'status': 'success',
            'reports_generated': reports_generated,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to generate scheduled reports: {e}")
        raise self.retry(exc=e, countdown=300)  # Retry after 5 minutes


@shared_task
def cleanup_old_monitoring_data(days_to_keep: int = 90):
    """Clean up old monitoring data to manage database size"""
    try:
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        # Count records before cleanup
        old_metrics = SystemMetrics.objects.filter(timestamp__lt=cutoff_date)
        old_health_checks = SystemHealthCheck.objects.filter(checked_at__lt=cutoff_date)
        old_performance = PerformanceMetrics.objects.filter(period_start__lt=cutoff_date)
        old_reports = Report.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['completed', 'failed']
        )
        
        metrics_count = old_metrics.count()
        health_count = old_health_checks.count()
        performance_count = old_performance.count()
        reports_count = old_reports.count()
        
        # Delete old records
        with transaction.atomic():
            old_metrics.delete()
            old_health_checks.delete()
            old_performance.delete()
            old_reports.delete()
        
        # Clean up resolved alerts older than 30 days
        old_alerts = SystemAlert.objects.filter(
            resolved=True,
            resolved_at__lt=timezone.now() - timedelta(days=30)
        )
        alerts_count = old_alerts.count()
        old_alerts.delete()
        
        logger.info(f"Cleaned up old monitoring data: {metrics_count + health_count + performance_count + reports_count + alerts_count} records")
        
        return {
            'status': 'success',
            'cutoff_date': cutoff_date.isoformat(),
            'deleted_records': {
                'system_metrics': metrics_count,
                'health_checks': health_count,
                'performance_metrics': performance_count,
                'reports': reports_count,
                'alerts': alerts_count
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup old monitoring data: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def process_alert_notifications():
    """Process and send alert notifications"""
    try:
        # Get unacknowledged critical and error alerts
        critical_alerts = SystemAlert.objects.filter(
            is_active=True,
            acknowledged=False,
            severity__in=['critical', 'error']
        ).order_by('triggered_at')
        
        notifications_sent = 0
        
        for alert in critical_alerts:
            try:
                # Check if notification was already sent recently
                last_notification = alert.alert_data.get('last_notification_sent')
                if last_notification:
                    last_sent = datetime.fromisoformat(last_notification)
                    if timezone.now() - last_sent < timedelta(minutes=30):
                        continue  # Don't spam notifications
                
                # Send notification (implement based on your notification system)
                notification_sent = _send_alert_notification(alert)
                
                if notification_sent:
                    # Update alert with notification info
                    alert.alert_data['last_notification_sent'] = timezone.now().isoformat()
                    alert.alert_data['notification_count'] = alert.alert_data.get('notification_count', 0) + 1
                    alert.save()
                    
                    notifications_sent += 1
                    
            except Exception as e:
                logger.error(f"Failed to process notification for alert {alert.id}: {e}")
        
        return {
            'status': 'success',
            'notifications_sent': notifications_sent,
            'total_alerts_checked': critical_alerts.count()
        }
        
    except Exception as e:
        logger.error(f"Failed to process alert notifications: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def auto_resolve_stale_alerts():
    """Automatically resolve alerts that are no longer relevant"""
    try:
        # Get alerts that haven't been updated in 24 hours
        stale_threshold = timezone.now() - timedelta(hours=24)
        stale_alerts = SystemAlert.objects.filter(
            is_active=True,
            resolved=False,
            updated_at__lt=stale_threshold
        )
        
        resolved_count = 0
        
        for alert in stale_alerts:
            try:
                # Check if the condition that triggered the alert still exists
                if _is_alert_condition_resolved(alert):
                    alert.resolved = True
                    alert.resolved_at = timezone.now()
                    alert.is_active = False
                    alert.resolution_notes = "Auto-resolved: condition no longer detected"
                    alert.save()
                    
                    resolved_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to check alert condition for {alert.id}: {e}")
        
        return {
            'status': 'success',
            'alerts_resolved': resolved_count,
            'alerts_checked': stale_alerts.count()
        }
        
    except Exception as e:
        logger.error(f"Failed to auto-resolve stale alerts: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def generate_daily_health_report():
    """Generate daily system health report"""
    try:
        report = report_generator.generate_system_health_report(
            date_range_days=1
        )
        
        return {
            'status': 'success',
            'report_id': str(report.id),
            'report_status': report.status
        }
        
    except Exception as e:
        logger.error(f"Failed to generate daily health report: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def generate_weekly_performance_report():
    """Generate weekly performance report"""
    try:
        report = report_generator.generate_performance_report(
            date_range_days=7,
            granularity='day'
        )
        
        return {
            'status': 'success',
            'report_id': str(report.id),
            'report_status': report.status
        }
        
    except Exception as e:
        logger.error(f"Failed to generate weekly performance report: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def initialize_monitoring():
    """Initialize monitoring system on startup"""
    try:
        logger.info("Initializing monitoring system")
        
        # Create default monitoring configurations if they don't exist
        _create_default_monitoring_configs()
        
        # Run initial health checks
        run_system_health_checks.delay()
        
        # Collect initial metrics
        collect_system_metrics.delay()
        
        return {'status': 'success', 'message': 'Monitoring system initialized'}
        
    except Exception as e:
        logger.error(f"Failed to initialize monitoring system: {e}")
        return {'status': 'error', 'error': str(e)}


# === HELPER FUNCTIONS ===

def _should_generate_report(config: MonitoringConfiguration, schedule: str) -> bool:
    """Check if a report should be generated based on schedule"""
    try:
        last_generated = config.config_data.get('last_generated')
        if not last_generated:
            return True  # Never generated before
        
        last_generated_dt = datetime.fromisoformat(last_generated)
        now = timezone.now()
        
        if schedule == 'hourly':
            return now - last_generated_dt >= timedelta(hours=1)
        elif schedule == 'daily':
            return now - last_generated_dt >= timedelta(days=1)
        elif schedule == 'weekly':
            return now - last_generated_dt >= timedelta(weeks=1)
        elif schedule == 'monthly':
            return now - last_generated_dt >= timedelta(days=30)
        else:
            return False
            
    except Exception as e:
        logger.error(f"Failed to check report schedule: {e}")
        return False


def _send_alert_notification(alert: SystemAlert) -> bool:
    """Send alert notification (implement based on your notification system)"""
    try:
        # This is a placeholder - implement based on your notification preferences
        # Could send email, Slack message, webhook, etc.
        
        notification_data = {
            'alert_id': str(alert.id),
            'alert_name': alert.alert_name,
            'severity': alert.severity,
            'message': alert.message,
            'component': alert.component,
            'triggered_at': alert.triggered_at.isoformat()
        }
        
        # Example: Log the notification (replace with actual notification logic)
        logger.warning(f"ALERT NOTIFICATION: {alert.alert_name} - {alert.message}")
        
        return True  # Return True if notification was sent successfully
        
    except Exception as e:
        logger.error(f"Failed to send alert notification: {e}")
        return False


def _is_alert_condition_resolved(alert: SystemAlert) -> bool:
    """Check if the condition that triggered an alert is resolved"""
    try:
        if alert.alert_type == 'health_check':
            # Check if component is now healthy
            from .models import SystemHealthCheck
            recent_check = SystemHealthCheck.objects.filter(
                component_name=alert.component,
                checked_at__gte=timezone.now() - timedelta(minutes=10)
            ).order_by('-checked_at').first()
            
            return recent_check and recent_check.status == 'healthy'
        
        elif alert.alert_type == 'metric_threshold':
            # Check if metric is now within normal range
            recent_metric = SystemMetrics.objects.filter(
                metric_name=alert.metric_name,
                timestamp__gte=timezone.now() - timedelta(minutes=10)
            ).order_by('-timestamp').first()
            
            if recent_metric and alert.threshold_value:
                return float(recent_metric.value) < float(alert.threshold_value)
        
        return False  # Conservative approach - don't auto-resolve if unsure
        
    except Exception as e:
        logger.error(f"Failed to check alert condition: {e}")
        return False


def _create_default_monitoring_configs():
    """Create default monitoring configurations"""
    try:
        # Default health check configuration
        health_config, created = MonitoringConfiguration.objects.get_or_create(
            config_name='default_health_checks',
            config_type='health_check',
            defaults={
                'config_data': {
                    'enabled_checks': [
                        'database', 'cache', 'celery', 'file_storage',
                        'system_resources', 'workflow_engine', 'communication_system',
                        'authentication', 'external_apis'
                    ],
                    'check_interval_minutes': 5,
                    'timeout_seconds': 30
                },
                'is_enabled': True
            }
        )
        
        # Default metric collection configuration
        metrics_config, created = MonitoringConfiguration.objects.get_or_create(
            config_name='default_metrics_collection',
            config_type='metric_collection',
            defaults={
                'config_data': {
                    'collection_interval_seconds': 60,
                    'enabled_metrics': [
                        'system_performance', 'database_metrics', 'cache_metrics',
                        'application_metrics', 'business_metrics', 'error_metrics'
                    ],
                    'retention_days': 90
                },
                'is_enabled': True
            }
        )
        
        # Default daily health report
        daily_report_config, created = MonitoringConfiguration.objects.get_or_create(
            config_name='daily_health_report',
            config_type='report_schedule',
            defaults={
                'config_data': {
                    'report_type': 'system_health',
                    'schedule': 'daily',
                    'date_range_days': 1,
                    'recipients': []  # Add email recipients as needed
                },
                'is_enabled': True
            }
        )
        
        # Default weekly performance report
        weekly_report_config, created = MonitoringConfiguration.objects.get_or_create(
            config_name='weekly_performance_report',
            config_type='report_schedule',
            defaults={
                'config_data': {
                    'report_type': 'performance',
                    'schedule': 'weekly',
                    'date_range_days': 7,
                    'granularity': 'day',
                    'recipients': []
                },
                'is_enabled': True
            }
        )
        
        logger.info("Created default monitoring configurations")
        
    except Exception as e:
        logger.error(f"Failed to create default monitoring configs: {e}")


# Periodic task schedules (to be configured in Celery beat)
"""
CELERY_BEAT_SCHEDULE = {
    'run-health-checks': {
        'task': 'monitoring.tasks.run_system_health_checks',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'collect-system-metrics': {
        'task': 'monitoring.tasks.collect_system_metrics',
        'schedule': crontab(minute='*/1'),  # Every minute
    },
    'generate-scheduled-reports': {
        'task': 'monitoring.tasks.generate_scheduled_reports',
        'schedule': crontab(hour=6, minute=0),  # Daily at 6 AM
    },
    'process-alert-notifications': {
        'task': 'monitoring.tasks.process_alert_notifications',
        'schedule': crontab(minute='*/10'),  # Every 10 minutes
    },
    'auto-resolve-stale-alerts': {
        'task': 'monitoring.tasks.auto_resolve_stale_alerts',
        'schedule': crontab(hour='*/6', minute=0),  # Every 6 hours
    },
    'cleanup-old-monitoring-data': {
        'task': 'monitoring.tasks.cleanup_old_monitoring_data',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),  # Weekly on Sunday at 2 AM
        'kwargs': {'days_to_keep': 90}
    },
    'generate-daily-health-report': {
        'task': 'monitoring.tasks.generate_daily_health_report',
        'schedule': crontab(hour=7, minute=0),  # Daily at 7 AM
    },
    'generate-weekly-performance-report': {
        'task': 'monitoring.tasks.generate_weekly_performance_report',
        'schedule': crontab(hour=8, minute=0, day_of_week=1),  # Weekly on Monday at 8 AM
    },
}
"""