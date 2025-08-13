from django.apps import AppConfig


class SharingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sharing'
    verbose_name = 'Record Sharing'
    
    def ready(self):
        """Import signals when the app is ready"""
        import sharing.signals