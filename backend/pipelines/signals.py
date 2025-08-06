"""
Pipeline-related signal handlers
"""

import logging
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db import models
import asyncio

from .models import Record, Pipeline, Field, AuditLog

# AI processing now handled by ai/integrations.py
logger = logging.getLogger(__name__)


@receiver(post_save, sender=Record)
def handle_record_save(sender, instance, created, **kwargs):
    """Handle record save events"""
    
    # Create audit log for updates (not creates)
    if not created and hasattr(instance, '_original_data'):
        try:
            original_data = getattr(instance, '_original_data', {})
            current_data = instance.data
            
            changes = {}
            for key, new_value in current_data.items():
                old_value = original_data.get(key)
                if old_value != new_value:
                    changes[key] = {
                        'old': old_value,
                        'new': new_value
                    }
            
            # Only create audit log if there are actual changes
            if changes:
                AuditLog.objects.create(
                    user=instance.updated_by,
                    action='updated',
                    model_name='Record',
                    object_id=str(instance.id),
                    changes=changes
                )
        except Exception as e:
            logger.error(f"Failed to create audit log for record {instance.id}: {e}")
    
    # Update pipeline statistics
    if created:
        Pipeline.objects.filter(id=instance.pipeline_id).update(
            record_count=models.F('record_count') + 1,
            last_record_created=timezone.now()
        )
    
    # AI field updates now handled by Record._trigger_ai_updates()
    # This is called automatically in the Record.save() method


@receiver(post_delete, sender=Record)
def handle_record_delete(sender, instance, **kwargs):
    """Handle record deletion"""
    # Create audit log
    try:
        AuditLog.objects.create(
            user=getattr(instance, 'deleted_by', None),
            action='deleted',
            model_name='Record',
            object_id=str(instance.id),
            changes={
                'deleted_data': instance.data,
                'stage': instance.stage.name if instance.stage else None
            }
        )
    except Exception as e:
        logger.error(f"Failed to create audit log for record deletion {instance.id}: {e}")
    
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
    
    # AI field processing now handled by unified AI system in ai/integrations.py


@receiver(pre_save, sender=Record)
def capture_record_state_before_save(sender, instance, **kwargs):
    """Capture the record state before save for change tracking"""
    if instance.pk:
        try:
            original = Record.objects.get(pk=instance.pk)
            instance._original_data = original.data
        except Record.DoesNotExist:
            instance._original_data = {}
    else:
        instance._original_data = {}


@receiver(post_save, sender=Record)
def handle_stage_transition_trigger(sender, instance, created, **kwargs):
    """Handle stage transition triggers for workflows"""
    if not created and hasattr(instance, '_original_stage_id'):
        original_stage_id = getattr(instance, '_original_stage_id')
        current_stage_id = instance.stage_id
        
        if original_stage_id != current_stage_id:
            # Stage transition occurred - this could trigger workflows
            logger.info(f"Record {instance.id} moved from stage {original_stage_id} to {current_stage_id}")
            
            # Workflow triggers would be handled here
            # This will be implemented when we add workflow integration


@receiver(pre_save, sender=Record)
def capture_stage_before_save(sender, instance, **kwargs):
    """Capture stage before save for transition detection"""
    if instance.pk:
        try:
            original = Record.objects.get(pk=instance.pk)
            instance._original_stage_id = original.stage_id
        except Record.DoesNotExist:
            instance._original_stage_id = None
