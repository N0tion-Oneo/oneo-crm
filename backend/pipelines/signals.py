"""
Pipeline-related signal handlers
"""

import logging
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify
from django.db import models
import asyncio

from .models import Record, Pipeline, Field
from core.models import AuditLog

# AI processing now handled by ai/integrations.py
logger = logging.getLogger(__name__)


def _format_field_value_for_display(value, field_type):
    """Format field value for human-readable display in audit logs"""
    if value is None or value == "":
        return "(empty)"
    
    # Handle different field types for better display
    if field_type == 'boolean':
        return "Yes" if value else "No"
    elif field_type == 'date':
        try:
            from datetime import datetime
            if isinstance(value, str):
                # Parse ISO date string
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return dt.strftime('%B %d, %Y')
            elif hasattr(value, 'strftime'):
                return value.strftime('%B %d, %Y')
        except:
            pass
    elif field_type == 'email':
        return str(value)
    elif field_type == 'phone':
        return str(value)
    elif field_type in ['select', 'multiselect']:
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        return str(value)
    elif field_type == 'tags':
        if isinstance(value, list):
            return ", ".join(f"#{tag}" for tag in value)
        return str(value)
    elif field_type == 'number':
        try:
            # Try to format as integer if it's a whole number
            if isinstance(value, (int, float)) and value == int(value):
                return str(int(value))
            elif isinstance(value, (int, float)):
                return f"{value:.2f}".rstrip('0').rstrip('.')
        except:
            pass
    
    # Default: convert to string and truncate if too long
    str_value = str(value)
    if len(str_value) > 50:
        return str_value[:47] + "..."
    return str_value


@receiver(post_save, sender=Record)
def handle_record_save(sender, instance, created, **kwargs):
    """Handle record save events"""
    
    # Create audit log for updates (not creates)
    if not created and hasattr(instance, '_original_data'):
        try:
            original_data = getattr(instance, '_original_data', {})
            current_data = instance.data
            
            changes = {}
            field_changes_summary = []
            
            # Get field definitions for display names and types
            pipeline_fields = {f.slug: f for f in instance.pipeline.fields.all()}
            
            for key, new_value in current_data.items():
                old_value = original_data.get(key)
                if old_value != new_value:
                    # Store raw change data
                    changes[key] = {
                        'old': old_value,
                        'new': new_value
                    }
                    
                    # Create human-readable change description
                    field_def = pipeline_fields.get(key)
                    if field_def:
                        field_name = field_def.display_name or field_def.name
                        
                        # Format values for display
                        old_display = _format_field_value_for_display(old_value, field_def.field_type)
                        new_display = _format_field_value_for_display(new_value, field_def.field_type)
                        
                        if old_value is None or old_value == "":
                            change_summary = f"{field_name}: {new_display} (added)"
                        elif new_value is None or new_value == "":
                            change_summary = f"{field_name}: {old_display} (removed)"
                        else:
                            change_summary = f"{field_name}: {old_display} → {new_display}"
                        
                        field_changes_summary.append(change_summary)
                        
                        # Add field metadata to change data
                        changes[key].update({
                            'field_name': field_name,
                            'field_type': field_def.field_type,
                            'change_summary': change_summary
                        })
            
            # Only create audit log if there are actual changes
            if changes:
                audit_log = AuditLog.objects.create(
                    user=instance.updated_by,
                    action='updated',
                    model_name='Record',
                    object_id=str(instance.id),
                    changes={
                        'record_title': instance.title,
                        'pipeline_name': instance.pipeline.name,
                        'field_changes': changes,
                        'changes_summary': field_changes_summary,
                        'total_changes': len(changes)
                    }
                )
                
                # Broadcast audit log update for real-time Activity tab
                try:
                    from realtime.signals import broadcast_audit_log_update
                    broadcast_audit_log_update(audit_log, instance)
                except Exception as broadcast_error:
                    logger.error(f"Failed to broadcast audit log update: {broadcast_error}")
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
    """Handle field save events - SIMPLIFIED to delegate to FieldOperationManager"""
    
    # Update pipeline field schema cache (only include active fields)
    try:
        instance.pipeline._update_field_schema()
        instance.pipeline.save(update_fields=['field_schema'])
    except Exception as e:
        logger.error(f"Failed to update pipeline schema for field {instance.slug}: {e}")
    
    # Create audit logs for field lifecycle events
    if created:
        logger.info(f"New field created: {instance.slug} in pipeline {instance.pipeline.name}")
        
    elif instance.is_deleted and not getattr(instance, '_was_deleted_before_save', False):
        # Field was just soft deleted
        logger.info(f"Field soft deleted: {instance.slug} in pipeline {instance.pipeline.name}")
        
        # Create audit log for field deletion
        try:
            AuditLog.objects.create(
                user=instance.deleted_by,
                action='field_soft_deleted',
                model_name='Field',
                object_id=str(instance.id),
                changes={
                    'field_slug': instance.slug,
                    'field_name': instance.name,
                    'pipeline': instance.pipeline.name,
                    'deleted_at': instance.deleted_at.isoformat() if instance.deleted_at else None
                }
            )
        except Exception as e:
            logger.error(f"Failed to create audit log for field deletion {instance.slug}: {e}")
    
    elif not instance.is_deleted and getattr(instance, '_was_deleted_before_save', False):
        # Field was just restored
        logger.info(f"Field restored: {instance.slug} in pipeline {instance.pipeline.name}")
        
        # Create audit log for field restoration
        try:
            AuditLog.objects.create(
                user=getattr(instance, 'updated_by', None),
                action='field_restored',
                model_name='Field',
                object_id=str(instance.id),
                changes={
                    'field_slug': instance.slug,
                    'field_name': instance.name,
                    'pipeline': instance.pipeline.name,
                    'restored_at': timezone.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Failed to create audit log for field restoration {instance.slug}: {e}")
    
    # Delegate complex migration logic to FieldOperationManager
    try:
        from .field_operations import get_field_operation_manager
        
        manager = get_field_operation_manager(instance.pipeline)
        manager.handle_field_save_signal(instance, created)
        
    except Exception as e:
        logger.error(f"FieldOperationManager signal handling failed for field {instance.slug}: {e}")
        # Don't raise - we don't want to break field saves if FieldOperationManager fails


@receiver(pre_save, sender=Field)
def capture_field_state_before_save(sender, instance, **kwargs):
    """Capture field state before save for deletion/restoration tracking - SIMPLIFIED"""
    if instance.pk:
        try:
            original = Field.objects.with_deleted().get(pk=instance.pk)
            # Simple state tracking for audit logs
            instance._was_deleted_before_save = original.is_deleted
        except Field.DoesNotExist:
            instance._was_deleted_before_save = False


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
    """Handle status transition triggers for workflows"""
    if not created and hasattr(instance, '_original_status'):
        original_status = getattr(instance, '_original_status')
        current_status = instance.status
        
        if original_status != current_status:
            # Status transition occurred - this could trigger workflows
            logger.info(f"Record {instance.id} moved from status {original_status} to {current_status}")
            
            # Workflow triggers would be handled here
            # This will be implemented when we add workflow integration


@receiver(pre_save, sender=Record)
def capture_stage_before_save(sender, instance, **kwargs):
    """Capture status before save for transition detection"""
    if instance.pk:
        try:
            original = Record.objects.get(pk=instance.pk)
            instance._original_status = original.status
        except Record.DoesNotExist:
            instance._original_status = None
