"""
Signal handlers for workflow triggers
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from pipelines.models import Record
from workflows.views.trigger_events import RecordEventTriggerView
import asyncio

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Record)
def trigger_record_event_workflows(sender, instance, created, **kwargs):
    """
    Trigger workflows when a record is created or updated
    """
    event_type = 'created' if created else 'updated'

    try:
        # Prepare record data with Record object for FieldPathResolver
        record_data = {
            'id': str(instance.id),
            'pipeline_id': str(instance.pipeline_id),
            'data': instance.data,
            'record_object': instance,  # Pass actual Record instance for relation traversal
            'created_at': instance.created_at.isoformat() if instance.created_at else None,
            'updated_at': instance.updated_at.isoformat() if instance.updated_at else None,
        }

        # Create a trigger view instance to handle the event
        trigger_view = RecordEventTriggerView()

        # Run the async trigger in a sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(
                trigger_view.trigger_record_event(event_type, record_data)
            )
        finally:
            loop.close()

        logger.info(f"Triggered {event_type} workflows for record {instance.id}")

    except Exception as e:
        logger.error(f"Failed to trigger record {event_type} workflows: {e}")


@receiver(post_delete, sender=Record)
def trigger_record_deleted_workflows(sender, instance, **kwargs):
    """
    Trigger workflows when a record is deleted
    """
    try:
        # Prepare record data (limited since record is being deleted)
        record_data = {
            'id': str(instance.id),
            'pipeline_id': str(instance.pipeline_id),
            'data': instance.data,
            'record_object': instance,  # Pass actual Record instance for relation traversal
        }

        # Create a trigger view instance to handle the event
        trigger_view = RecordEventTriggerView()

        # Run the async trigger in a sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(
                trigger_view.trigger_record_event('deleted', record_data)
            )
        finally:
            loop.close()

        logger.info(f"Triggered deleted workflows for record {instance.id}")

    except Exception as e:
        logger.error(f"Failed to trigger record deleted workflows: {e}")