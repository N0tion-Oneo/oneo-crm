"""
Communications tasks subpackage
"""
# Make this directory a Python package

# Import record communications tasks for Celery autodiscovery
try:
    from communications.record_communications.tasks.sync_tasks import (
        sync_record_communications,
        process_webhook_message_task,
        sync_all_records_for_pipeline,
        cleanup_old_sync_jobs,
        check_stale_profiles
    )
except ImportError:
    # If import fails during early Django initialization, skip it
    pass