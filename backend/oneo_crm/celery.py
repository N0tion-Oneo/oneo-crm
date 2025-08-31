"""
Celery configuration for Oneo CRM
Includes workflow automation task scheduling and multi-tenant support
"""
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')

app = Celery('oneo_crm')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps
app.autodiscover_tasks()

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    # Process scheduled workflows every minute
    'process-scheduled-workflows': {
        'task': 'workflows.tasks.process_scheduled_workflows',
        'schedule': 60.0,  # Run every 60 seconds
    },
    
    # Clean up old workflow executions daily at 2 AM
    'cleanup-old-executions': {
        'task': 'workflows.tasks.cleanup_old_executions',
        'schedule': 60 * 60 * 24,  # Daily
        'kwargs': {'days_to_keep': 30}
    },
    
    # Optional: Regular health check for workflow system
    'workflow-system-health-check': {
        'task': 'workflows.tasks.validate_workflow_definition',
        'schedule': 60 * 60 * 6,  # Every 6 hours
        'enabled': False  # Disabled by default
    },
    
    # Communication system periodic sync (backup to webhooks)
    # DISABLED: These tasks are placeholders and cause unnecessary load
    # 'communications-periodic-sync': {
    #     'task': 'communications.tasks.periodic_message_sync_task',
    #     'schedule': 300.0,  # Every 5 minutes
    # },
    
    # Generate daily communication analytics
    'communications-daily-analytics': {
        'task': 'communications.tasks.field_maintenance.generate_daily_analytics',
        'schedule': 60 * 60 * 24,  # Daily at midnight
    },
    
    # Update participant statistics
    'update-participant-statistics': {
        'task': 'communications.tasks.field_maintenance.update_participant_statistics',
        'schedule': 60 * 60 * 6,  # Every 6 hours
    },
    
    # Update channel statistics
    'update-channel-statistics': {
        'task': 'communications.tasks.field_maintenance.update_channel_statistics',
        'schedule': 60 * 60 * 4,  # Every 4 hours
    },
    
    # Detect hot conversations
    'detect-hot-conversations': {
        'task': 'communications.tasks.field_maintenance.detect_hot_conversations',
        'schedule': 60 * 60,  # Every hour
    },
    
    # Cleanup expired tokens
    'cleanup-expired-tokens': {
        'task': 'communications.tasks.field_maintenance.cleanup_expired_tokens',
        'schedule': 60 * 60 * 12,  # Every 12 hours
    },
    
    # Process scheduled record syncs
    'process-scheduled-syncs': {
        'task': 'communications.tasks.field_maintenance.process_scheduled_syncs',
        'schedule': 60 * 60,  # Every hour
    },
    
    # Verify communication links
    'verify-communication-links': {
        'task': 'communications.tasks.field_maintenance.verify_communication_links',
        'schedule': 60 * 60 * 24,  # Daily
    },
    
    # Update conversation types
    'update-conversation-types': {
        'task': 'communications.tasks.field_maintenance.update_conversation_types',
        'schedule': 60 * 60 * 12,  # Every 12 hours
    },
    
    # Automatic contact resolution for unconnected conversations
    # DISABLED: Not implemented yet, causes unnecessary processing
    # 'automatic-contact-resolution': {
    #     'task': 'communications.tasks.periodic_contact_resolution_task',
    #     'schedule': 1800.0,  # Every 30 minutes
    # }
    
    # Auto-store email conversations that match CRM contacts
    'auto-store-pending-emails': {
        'task': 'communications.channels.email.tasks.auto_store_pending_emails',
        'schedule': 300.0,  # Every 5 minutes
        'kwargs': {'tenant_schema_name': None}  # Process all tenants
    },
}

# Celery configuration
app.conf.update(
    # Task result backend (Redis)
    result_backend='redis://localhost:6379/1',
    
    # Message broker (Redis)
    broker_url='redis://localhost:6379/0',
    broker_connection_retry_on_startup=True,
    
    # Task serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Timezone settings
    timezone='UTC',
    enable_utc=True,
    
    # Django-tenants compatibility settings
    worker_hijack_root_logger=False,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,  # Reject unacked tasks if worker crashes
    worker_max_tasks_per_child=50,
    
    # Task routing and limits
    task_routes={
        # Workflow tasks
        'workflows.tasks.execute_workflow_async': {'queue': 'workflows'},
        'workflows.tasks.process_scheduled_workflows': {'queue': 'schedules'},
        'workflows.tasks.resume_paused_workflow': {'queue': 'workflows'},
        'workflows.tasks.cleanup_old_executions': {'queue': 'maintenance'},
        'workflows.tasks.validate_workflow_definition': {'queue': 'validation'},
        
        # AI processing tasks
        'authentication.tasks.process_ai_response': {'queue': 'ai_processing'},
        # OLD: 'pipelines.tasks.process_ai_field' - replaced by ai.tasks.process_ai_job
        'ai.tasks.process_ai_job': {'queue': 'ai_processing'},
        'ai.tasks.cleanup_old_jobs': {'queue': 'maintenance'},
        'ai.tasks.retry_failed_jobs': {'queue': 'ai_processing'},
        
        # Real-time communication tasks
        'communications.tasks.send_realtime_message': {'queue': 'realtime'},
        'realtime.tasks.broadcast_update': {'queue': 'realtime'},
        
        # Long-running trigger tasks
        'workflows.tasks.process_long_running_trigger': {'queue': 'triggers'},
        'pipelines.tasks.process_bulk_operation': {'queue': 'bulk_operations'},
        
        # Communication sync tasks
        'communications.tasks.periodic_message_sync_task': {'queue': 'communications'},
        'communications.tasks.sync_account_messages_task': {'queue': 'communications'},
        'communications.tasks.sync_channel_messages': {'queue': 'communications'},
        'communications.tasks.generate_daily_analytics': {'queue': 'analytics'},
        'communications.tasks.initial_sync_new_connection_task': {'queue': 'communications'},
        
        # Background sync tasks - Updated to match refactored structure
        'communications.channels.whatsapp.sync.tasks.sync_account_comprehensive_background': {'queue': 'background_sync'},
        'communications.channels.whatsapp.sync.tasks.sync_chat_specific_background': {'queue': 'background_sync'},
        'communications.channels.whatsapp.sync.tasks.cleanup_old_sync_jobs': {'queue': 'maintenance'},
        # Legacy routing for backwards compatibility
        'communications.tasks_background_sync.sync_account_comprehensive_background': {'queue': 'background_sync'},
        'communications.tasks_background_sync.sync_chat_specific_background': {'queue': 'background_sync'},
        
        # Email sync tasks
        'communications.channels.email.sync.run_comprehensive': {'queue': 'background_sync'},
        'communications.channels.email.sync.run_incremental': {'queue': 'background_sync'},
        'communications.channels.email.sync.sync_single_thread': {'queue': 'background_sync'},
        'communications.channels.email.sync.sync_folders': {'queue': 'background_sync'},
        'communications.channels.email.sync.cleanup_old_emails': {'queue': 'maintenance'},
        
        # Contact resolution tasks
        'communications.tasks.resolve_unconnected_conversations_task': {'queue': 'contact_resolution'},
        'communications.tasks.resolve_conversation_contact_task': {'queue': 'contact_resolution'},
        'communications.tasks.periodic_contact_resolution_task': {'queue': 'maintenance'},
        
        # Record-level communication sync tasks
        'communications.record_communications.tasks.sync_tasks.sync_record_communications': {'queue': 'background_sync'},
        'communications.record_communications.tasks.sync_tasks.process_webhook_message_task': {'queue': 'background_sync'},
        'communications.record_communications.tasks.sync_tasks.sync_all_records_for_pipeline': {'queue': 'background_sync'},
        'communications.record_communications.tasks.sync_tasks.cleanup_old_sync_jobs': {'queue': 'maintenance'},
        'communications.record_communications.tasks.sync_tasks.check_stale_profiles': {'queue': 'maintenance'},
    },
    
    # Worker configuration
    
    # Task execution limits
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,       # 10 minutes hard limit
    
    # Result expiration
    result_expires=3600,  # 1 hour
    
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Multi-tenant task routing
@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery functionality"""
    print(f'Request: {self.request!r}')
    return 'Celery is working!'


if __name__ == '__main__':
    app.start()