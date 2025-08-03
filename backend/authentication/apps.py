from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authentication'
    
    def ready(self):
        """Import signals when the app is ready"""
        try:
            from . import signals  # Import signals to register them
        except ImportError:
            pass
