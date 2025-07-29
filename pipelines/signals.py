"""
Django signals for pipeline system
"""
from django.db import models
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from asgiref.sync import sync_to_async
import asyncio
import logging

from .models import Pipeline, Field, Record
from .ai_processor import AIFieldManager

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Record)
def validate_record_data(sender, instance, **kwargs):
    """Validate record data before saving"""
    # This is handled in the model's save method, but we can add additional logic here
    pass


@receiver(post_save, sender=Record)
def handle_record_save(sender, instance, created, **kwargs):
    """Handle record save events"""
    # Update pipeline statistics
    if created:
        Pipeline.objects.filter(id=instance.pipeline_id).update(
            record_count=models.F('record_count') + 1,
            last_record_created=timezone.now()
        )
    
    # Trigger AI field processing for updates (async)
    if not created and hasattr(instance, '_changed_fields'):
        # This would be set by the model when fields change
        changed_fields = getattr(instance, '_changed_fields', [])
        if changed_fields:
            # Schedule AI field updates asynchronously
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    AIFieldManager.trigger_field_updates(instance, changed_fields)
                )
                loop.close()
            except Exception as e:
                logger.error(f"Failed to trigger AI field updates: {e}")


@receiver(post_delete, sender=Record)
def handle_record_delete(sender, instance, **kwargs):
    """Handle record deletion"""
    # Update pipeline statistics
    Pipeline.objects.filter(id=instance.pipeline_id).update(
        record_count=models.F('record_count') - 1
    )


@receiver(post_save, sender=Field)
def handle_field_save(sender, instance, created, **kwargs):
    """Handle field save events"""
    # Update pipeline field schema cache
    instance.pipeline._update_field_schema()
    instance.pipeline.save(update_fields=['field_schema'])
    
    # If it's a new AI field, process existing records
    if created and instance.is_ai_field:
        # Schedule processing of existing records
        try:
            records = instance.pipeline.records.filter(is_deleted=False)[:10]  # Process first 10
            
            for record in records:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    from .ai_processor import AIFieldProcessor
                    processor = AIFieldProcessor(instance, record)
                    result = loop.run_until_complete(processor.process_field())
                    
                    if result is not None:
                        record.data[instance.slug] = result
                        record.save(update_fields=['data'])
                    
                    loop.close()
                    
                except Exception as e:
                    logger.error(f"Failed to process AI field for record {record.id}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to process existing records for new AI field: {e}")


@receiver(post_delete, sender=Field)
def handle_field_delete(sender, instance, **kwargs):
    """Handle field deletion"""
    # Update pipeline field schema cache
    instance.pipeline._update_field_schema()
    instance.pipeline.save(update_fields=['field_schema'])
    
    # Remove field data from all records
    instance.pipeline.records.all().update(
        data=models.F('data') - instance.slug
    )


@receiver(post_save, sender=Pipeline)
def handle_pipeline_save(sender, instance, created, **kwargs):
    """Handle pipeline save events"""
    if created:
        logger.info(f"New pipeline created: {instance.name} by {instance.created_by}")


# Custom signal for AI field processing
from django.dispatch import Signal

ai_field_processed = Signal()

@receiver(ai_field_processed)
def handle_ai_field_processed(sender, field, record, result, **kwargs):
    """Handle AI field processing completion"""
    logger.info(f"AI field {field.name} processed for record {record.id}: {type(result)}")


# Utility functions for async signal handling
def run_async_signal(coro):
    """Run async function in signal context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(coro)
    except Exception as e:
        logger.error(f"Async signal execution failed: {e}")
        return None
    finally:
        try:
            loop.close()
        except:
            pass