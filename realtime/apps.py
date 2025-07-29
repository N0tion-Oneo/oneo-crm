from django.apps import AppConfig


class RealtimeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'realtime'
    verbose_name = 'Real-time Collaboration'
    
    def ready(self):
        """Initialize real-time features when Django starts"""
        # Import signal handlers
        from . import signals