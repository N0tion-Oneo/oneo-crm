from django.apps import AppConfig


class AIConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai'
    verbose_name = 'AI Integration & Intelligent Workflows'

    def ready(self):
        # Import signal handlers when app is ready
        import ai.signals