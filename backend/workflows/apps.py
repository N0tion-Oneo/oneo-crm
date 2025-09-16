"""
Workflows app configuration
"""
from django.apps import AppConfig


class WorkflowsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workflows'
    verbose_name = 'Workflow Automation'
    
    def ready(self):
        """Initialize workflow system when Django starts"""
        # Legacy trigger system removed - using node-based triggers now
        # from .triggers.manager import TriggerManager

        # Import workflow signal handlers for record events
        from . import signals as workflow_signals

        # Import content management signal handlers
        from .content import signals

        # Import recovery system signal handlers
        from .recovery import signals as recovery_signals

        # Import models to ensure they're loaded
        from . import models