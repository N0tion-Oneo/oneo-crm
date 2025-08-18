from django.apps import AppConfig


class CommunicationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'communications'
    verbose_name = 'Communications & Tracking'
    
    def ready(self):
        """Initialize communication tracking system when Django starts"""
        # Import signal handlers to register them
        from .tracking import signals
        from . import signals as communications_signals
