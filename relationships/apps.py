from django.apps import AppConfig


class RelationshipsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'relationships'
    verbose_name = 'Relationships'

    def ready(self):
        """Initialize relationship system when app is ready"""
        try:
            from . import signals  # Import signals when app is ready
        except ImportError:
            pass
