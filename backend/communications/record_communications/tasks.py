"""
Celery tasks for record communications - imports for autodiscovery
This file ensures Celery's autodiscover_tasks() finds these tasks
"""

# Import all tasks from sync_tasks to ensure Celery discovers them
from .tasks.sync_tasks import (
    sync_record_communications,
    process_webhook_message_task,
    sync_all_records_for_pipeline,
    cleanup_old_sync_jobs,
    check_stale_profiles
)

__all__ = [
    'sync_record_communications',
    'process_webhook_message_task',
    'sync_all_records_for_pipeline',
    'cleanup_old_sync_jobs',
    'check_stale_profiles',
]