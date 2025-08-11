"""
Smart stage trigger system for dynamic forms
Automatically detects stage transitions and triggers form completion prompts
"""
import logging
from typing import Dict, List, Optional, Tuple
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.urls import reverse
from django.conf import settings

from .models import Record, Pipeline, Field
# get_current_stage function was not found - removing unused import

logger = logging.getLogger(__name__)


class StageTransitionDetector:
    """Detects stage transitions and analyzes required field completion"""
    
    @staticmethod
    def detect_stage_change(old_data: Dict, new_data: Dict, pipeline: Pipeline) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect if a stage transition occurred
        Returns: (old_stage, new_stage) or (None, None) if no transition
        """
        old_stage = StageTransitionDetector._get_stage_from_data(old_data, pipeline)
        new_stage = StageTransitionDetector._get_stage_from_data(new_data, pipeline)
        
        if old_stage != new_stage and new_stage is not None:
            return old_stage, new_stage
        
        return None, None
    
    @staticmethod
    def _get_stage_from_data(data: Dict, pipeline: Pipeline) -> Optional[str]:
        """Extract stage value from record data"""
        if not data:
            return None
            
        # First check for stage field in business rules
        for field in pipeline.fields.all():
            business_rules = field.business_rules or {}
            stage_requirements = business_rules.get('stage_requirements', {})
            if stage_requirements and field.slug in data:
                return data[field.slug]
        
        # Check common stage field names
        common_stage_fields = ['stage', 'pipeline_stage', 'pipeline_stages', 'status']
        for stage_field in common_stage_fields:
            if stage_field in data:
                return data[stage_field]
        
        return None
    
    @staticmethod
    def get_missing_stage_fields(record_data: Dict, stage: str, pipeline: Pipeline) -> List[Dict]:
        """
        Get fields that are required for a stage but missing/empty
        Returns list of field info dicts for missing fields
        """
        missing_fields = []
        
        for field in pipeline.fields.all():
            business_rules = field.business_rules or {}
            stage_requirements = business_rules.get('stage_requirements', {})
            
            if stage in stage_requirements:
                requirements = stage_requirements[stage]
                if requirements.get('required', False):
                    field_value = record_data.get(field.slug)
                    
                    # Check if field is empty/missing
                    if not field_value or (isinstance(field_value, str) and field_value.strip() == ''):
                        missing_fields.append({
                            'slug': field.slug,
                            'name': field.name,
                            'display_name': field.display_name or field.name,
                            'field_type': field.field_type,
                            'is_visible_in_public_forms': field.is_visible_in_public_forms,
                            'requirements': requirements
                        })
        
        return missing_fields
    
    @staticmethod
    def generate_form_urls(pipeline: Pipeline, stage: str, record_id: str) -> Dict[str, str]:
        """Generate form URLs for stage completion"""
        base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        
        return {
            'internal_form': f"{base_url}/forms/internal/{pipeline.id}?stage={stage}&recordId={record_id}",
            'public_form': f"{base_url}/forms/{pipeline.slug}/stage/{stage}",
            'modal_form': f"/forms/internal/{pipeline.id}?stage={stage}&recordId={record_id}&embed=true"
        }


class FormTriggerNotifier:
    """Handles notifications for form completion triggers"""
    
    @staticmethod
    def should_trigger_form(missing_fields: List[Dict], trigger_config: Dict = None) -> bool:
        """
        Determine if form should be triggered based on missing fields and config
        """
        if not missing_fields:
            return False
        
        # Default trigger logic: trigger if any required fields are missing
        if not trigger_config:
            return True
        
        # Custom trigger logic based on configuration
        min_missing = trigger_config.get('min_missing_fields', 1)
        trigger_types = trigger_config.get('trigger_field_types', [])
        
        if len(missing_fields) < min_missing:
            return False
        
        if trigger_types:
            # Only trigger if missing fields include specified types
            missing_types = [field['field_type'] for field in missing_fields]
            return any(field_type in missing_types for field_type in trigger_types)
        
        return True
    
    @staticmethod
    def create_trigger_notification(record: Record, stage: str, missing_fields: List[Dict], form_urls: Dict[str, str]):
        """Create trigger action for form completion (simple logging/notification)"""
        field_names = [field['display_name'] for field in missing_fields]
        message = f"Record '{record.title}' moved to {stage} stage. Missing required fields: {', '.join(field_names)}"
        
        logger.info(f"STAGE TRIGGER: {message}")
        logger.info(f"Form URLs available: {form_urls}")
        
        # Here you could integrate with:
        # - Email notifications
        # - WebSocket real-time notifications  
        # - Task queue for async processing
        # - External webhook calls
        # - Dashboard notification system
        
        # For now, just return the trigger data for potential frontend use
        return {
            'triggered': True,
            'record_id': record.id,
            'stage': stage,
            'message': message,
            'missing_fields': missing_fields,
            'form_urls': form_urls,
            'timestamp': record.updated_at.isoformat()
        }


# Global storage for tracking record states before save
_record_old_data = {}


@receiver(pre_save, sender=Record)
def capture_record_state_before_save(sender, instance, **kwargs):
    """Capture record data before save to detect stage transitions"""
    if instance.pk:
        try:
            old_record = Record.objects.get(pk=instance.pk)
            _record_old_data[instance.pk] = old_record.data.copy()
        except Record.DoesNotExist:
            _record_old_data[instance.pk] = {}
    else:
        _record_old_data[instance.pk] = {}


@receiver(post_save, sender=Record)
def handle_stage_transition_trigger(sender, instance, created, **kwargs):
    """Handle stage transition detection and form triggering"""
    if created:
        # For new records, check if they're missing required fields for initial stage
        current_stage = StageTransitionDetector._get_stage_from_data(instance.data, instance.pipeline)
        if current_stage:
            missing_fields = StageTransitionDetector.get_missing_stage_fields(
                instance.data, current_stage, instance.pipeline
            )
            
            if missing_fields:
                trigger_config = instance.pipeline.settings.get('stage_triggers', {})
                if FormTriggerNotifier.should_trigger_form(missing_fields, trigger_config):
                    form_urls = StageTransitionDetector.generate_form_urls(
                        instance.pipeline, current_stage, str(instance.id)
                    )
                    FormTriggerNotifier.create_trigger_notification(
                        instance, current_stage, missing_fields, form_urls
                    )
        
        # Clean up temporary data
        if instance.pk in _record_old_data:
            del _record_old_data[instance.pk]
        return
    
    # For existing records, detect stage transitions
    old_data = _record_old_data.get(instance.pk, {})
    new_data = instance.data
    
    try:
        old_stage, new_stage = StageTransitionDetector.detect_stage_change(
            old_data, new_data, instance.pipeline
        )
        
        if old_stage and new_stage and old_stage != new_stage:
            logger.info(f"Stage transition detected for record {instance.id}: {old_stage} -> {new_stage}")
            
            # Check for missing required fields in the new stage
            missing_fields = StageTransitionDetector.get_missing_stage_fields(
                new_data, new_stage, instance.pipeline
            )
            
            if missing_fields:
                logger.info(f"Found {len(missing_fields)} missing required fields for stage {new_stage}")
                
                # Check if we should trigger a form based on pipeline configuration
                trigger_config = instance.pipeline.settings.get('stage_triggers', {})
                
                if FormTriggerNotifier.should_trigger_form(missing_fields, trigger_config):
                    form_urls = StageTransitionDetector.generate_form_urls(
                        instance.pipeline, new_stage, str(instance.id)
                    )
                    
                    FormTriggerNotifier.create_trigger_notification(
                        instance, new_stage, missing_fields, form_urls
                    )
                    
                    logger.info(f"Triggered stage completion form for record {instance.id} in stage {new_stage}")
                else:
                    logger.info(f"Stage trigger conditions not met for record {instance.id}")
            else:
                logger.info(f"No missing required fields for stage {new_stage}")
        
    except Exception as e:
        logger.error(f"Error handling stage transition for record {instance.id}: {e}")
    finally:
        # Clean up temporary data
        if instance.pk in _record_old_data:
            del _record_old_data[instance.pk]


def get_stage_trigger_status(record: Record) -> Dict:
    """Get current stage trigger status for a record"""
    current_stage = StageTransitionDetector._get_stage_from_data(record.data, record.pipeline)
    
    if not current_stage:
        return {
            'has_stage': False,
            'current_stage': None,
            'missing_fields': [],
            'form_urls': {},
            'should_trigger': False
        }
    
    missing_fields = StageTransitionDetector.get_missing_stage_fields(
        record.data, current_stage, record.pipeline
    )
    
    trigger_config = record.pipeline.settings.get('stage_triggers', {})
    should_trigger = FormTriggerNotifier.should_trigger_form(missing_fields, trigger_config)
    
    form_urls = {}
    if should_trigger:
        form_urls = StageTransitionDetector.generate_form_urls(
            record.pipeline, current_stage, str(record.id)
        )
    
    return {
        'has_stage': True,
        'current_stage': current_stage,
        'missing_fields': missing_fields,
        'form_urls': form_urls,
        'should_trigger': should_trigger,
        'trigger_config': trigger_config
    }