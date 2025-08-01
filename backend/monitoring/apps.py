"""
Monitoring app configuration
"""
from django.apps import AppConfig


class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitoring'
    verbose_name = 'System Monitoring & Reporting'
    
    def ready(self):
        """Initialize monitoring system when Django starts"""
        # Import signal handlers to register them
        from . import signals
        
        # Initialize background monitoring tasks
        try:
            from .tasks import initialize_monitoring
            initialize_monitoring.delay()
        except ImportError:
            # Celery not available
            pass