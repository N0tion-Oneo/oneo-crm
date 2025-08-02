from django.apps import AppConfig


class PipelinesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pipelines'
    verbose_name = 'Pipeline System'
    
    def ready(self):
        """Import signal handlers when app is ready"""
        try:
            import pipelines.signals  # noqa F401
            import pipelines.triggers  # noqa F401
        except ImportError:
            pass