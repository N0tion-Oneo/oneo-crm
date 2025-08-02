from django.apps import AppConfig


class DuplicatesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'duplicates'
    verbose_name = 'Duplicate Detection'
    
    def ready(self):
        """Import signals when app is ready"""
        try:
            import duplicates.signals
        except ImportError:
            pass