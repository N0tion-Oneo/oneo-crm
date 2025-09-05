from django.apps import AppConfig


class CommunicationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'communications'
    verbose_name = 'Communications & Tracking'
    
    def ready(self):
        """Initialize communication tracking system when Django starts"""
        # Import the new centralized signals package to register all signal handlers
        from . import signals
        
        # Import account sync signals for automatic account data collection
        from .signals import account_sync
        
        # Import field population signals to ensure all fields are properly set
        from .signals import field_population
        
        # Import record communication sync signals for automatic sync on identifier changes
        from .record_communications import signals as record_comm_signals
        
        # Import auto-creation signals for participant to contact conversion
        from .signals import auto_creation
