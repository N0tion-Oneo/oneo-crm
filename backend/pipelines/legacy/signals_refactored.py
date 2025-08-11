"""
🔴 DEPRECATED - DO NOT USE 🔴
Simplified Pipeline Signal Handlers
All complex business logic moved to FieldOperationManager
Signals now serve as simple triggers that delegate to unified system

REPLACED BY: pipelines/signals.py

This file was an alternative implementation that is not currently active.
The system uses pipelines/signals.py (imported in apps.py).

Date deprecated: 2025-08-10
"""

import logging
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db import models

from .models import Record, Pipeline, Field
from core.models import AuditLog

logger = logging.getLogger(__name__)


# =============================================================================
# RECORD SIGNALS - Handle record lifecycle events
# =============================================================================

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


@receiver(pre_save, sender=Record)
def capture_stage_before_save(sender, instance, **kwargs):
    """Capture stage before save for transition detection"""
    if instance.pk:
        try:
            original = Record.objects.get(pk=instance.pk)
            instance._original_stage_id = original.stage_id
        except Record.DoesNotExist:
            instance._original_stage_id = None


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


# =============================================================================
# FIELD SIGNALS - Simplified to delegate to FieldOperationManager
# =============================================================================

@receiver(post_save, sender=Field)
def handle_field_save(sender, instance, created, **kwargs):
    """
    Handle field save events - SIMPLIFIED
    All complex business logic moved to FieldOperationManager
    """
    # Update pipeline field schema cache (only include active fields)
    try:
        instance.pipeline._update_field_schema()
        instance.pipeline.save(update_fields=['field_schema'])
    except Exception as e:
        logger.error(f"Failed to update pipeline schema for field {instance.slug}: {e}")
    
    # Delegate to FieldOperationManager for complex operations
    try:
        from .field_operations import get_field_operation_manager
        
        manager = get_field_operation_manager(instance.pipeline)
        manager.handle_field_save_signal(instance, created)
        
    except Exception as e:
        logger.error(f"FieldOperationManager signal handling failed for field {instance.slug}: {e}")


@receiver(post_delete, sender=Field)
def handle_field_hard_delete(sender, instance, **kwargs):
    """Handle hard deletion of fields"""
    logger.warning(f"Field hard deleted: {instance.slug} from pipeline {instance.pipeline.name}")
    
    # Create audit log for hard deletion
    try:
        AuditLog.objects.create(
            user=None,  # Hard deletion is usually automated
            action='field_hard_deleted',
            model_name='Field',
            object_id=str(instance.id),
            changes={
                'field_slug': instance.slug,
                'field_name': instance.name,
                'pipeline': instance.pipeline.name,
                'field_config': instance.field_config,
                'hard_deleted_at': timezone.now().isoformat(),
                'reason': instance.hard_delete_reason
            }
        )
    except Exception as e:
        logger.error(f"Failed to create audit log for field hard deletion {instance.slug}: {e}")
    
    # Update pipeline field schema cache
    try:
        instance.pipeline._update_field_schema()
        instance.pipeline.save(update_fields=['field_schema'])
    except Exception as e:
        logger.error(f"Failed to update pipeline schema after field hard deletion: {e}")
    
    # Trigger cleanup of orphaned field data
    try:
        from .tasks import cleanup_orphaned_field_data
        cleanup_orphaned_field_data.delay(instance.pipeline.id)
    except Exception as e:
        logger.error(f"Failed to trigger orphaned data cleanup: {e}")


# =============================================================================
# SIGNAL HELPERS - Clean utility functions
# =============================================================================

def cleanup_old_field_states():
    """Clean up old field states to prevent memory leaks"""
    try:
        from .state.field_state_manager import get_field_state_manager
        state_manager = get_field_state_manager()
        state_manager.cleanup_old_states()
    except Exception as e:
        logger.error(f"Failed to cleanup old field states: {e}")


# =============================================================================
# MIGRATION INTEGRATION - Simple hooks for field changes
# =============================================================================

def trigger_field_migration_if_needed(field_id: int, operation_id: str):
    """
    Simple helper to trigger field migration through FieldOperationManager
    Called by external systems when field changes are detected
    """
    try:
        from .models import Field
        from .field_operations import get_field_operation_manager
        
        field = Field.objects.get(id=field_id)
        manager = get_field_operation_manager(field.pipeline)
        
        # The FieldOperationManager handles all migration logic internally
        logger.info(f"Field migration triggered for field {field.slug} via operation {operation_id}")
        
    except Exception as e:
        logger.error(f"Failed to trigger field migration: {e}")