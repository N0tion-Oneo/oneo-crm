"""
Django signals for automatic record communication sync
Triggers sync when identifier fields (from duplicate rules) are added or updated
"""
import logging
from typing import Dict, Any, Set, Optional
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.db import transaction

from pipelines.models import Record
from duplicates.models import DuplicateRule
from .models import RecordCommunicationProfile, RecordSyncJob
from .services import RecordIdentifierExtractor

logger = logging.getLogger(__name__)


def get_identifier_fields_from_duplicate_rules(pipeline) -> Dict[str, Any]:
    """
    Extract field information from duplicate rules for a pipeline.
    Returns both the field slugs and their match types.
    """
    identifier_fields = {}  # field_slug -> {match_type, url_rules}
    
    # Get active duplicate rules for this pipeline
    duplicate_rules = DuplicateRule.objects.filter(
        pipeline=pipeline,
        is_active=True
    )
    
    for rule in duplicate_rules:
        logic = rule.logic or {}
        
        # Handle simple 'fields' format
        if 'fields' in logic:
            for field_config in logic['fields']:
                field_slug = field_config.get('field')
                if field_slug:
                    identifier_fields[field_slug] = {
                        'match_type': field_config.get('match_type', 'exact'),
                        'url_extraction_rules': field_config.get('url_extraction_rules')
                    }
        
        # Handle 'conditions' format (OR/AND groups)
        if 'conditions' in logic:
            for condition in logic.get('conditions', []):
                for field_config in condition.get('fields', []):
                    field_slug = field_config.get('field')
                    if field_slug:
                        identifier_fields[field_slug] = {
                            'match_type': field_config.get('match_type', 'exact'),
                            'url_extraction_rules': field_config.get('url_extraction_rules')
                        }
    
    return identifier_fields


def detect_identifier_changes(original_data: Dict[str, Any], 
                             current_data: Dict[str, Any],
                             identifier_fields_info: Dict[str, Any],
                             pipeline) -> Dict[str, Any]:
    """
    Detect changes in identifier fields between original and current data.
    Uses match_type from duplicate rules to determine communication channels.
    
    Returns:
        Dict with 'has_changes' bool, 'changed_fields' list, and 'changed_types' set
    """
    from duplicates.models import URLExtractionRule
    
    changed_fields = []
    changed_types = set()
    
    # Map match_type to communication channel types
    match_type_to_channel = {
        'email_normalized': 'email',
        'phone_normalized': 'phone',
        'url_normalized': None,  # Will be determined by URL extraction rules
    }
    
    # Get URL extraction rules for this pipeline
    url_rules = {}
    if any(info.get('match_type') == 'url_normalized' for info in identifier_fields_info.values()):
        url_extraction_rules = URLExtractionRule.objects.filter(
            pipeline=pipeline,
            is_active=True
        )
        for rule in url_extraction_rules:
            url_rules[rule.id] = rule
    
    def determine_channels_for_field(field_slug, value, field_info):
        """Determine which channels should sync based on field match_type"""
        channels = set()
        match_type = field_info.get('match_type', 'exact')
        
        # Handle different match types
        if match_type == 'email_normalized':
            channels.add('email')
        elif match_type == 'phone_normalized':
            channels.add('phone')
        elif match_type == 'url_normalized':
            # Check URL extraction rules
            url_rule_ids = field_info.get('url_extraction_rules')
            if url_rule_ids:
                for rule_id in url_rule_ids:
                    rule = url_rules.get(rule_id)
                    if rule and rule.template_type:
                        # The template_type tells us the channel (e.g., 'linkedin')
                        channels.add(rule.template_type)
            else:
                # No specific rules, try to detect from URL value
                if value and 'linkedin' in str(value).lower():
                    channels.add('linkedin')
        
        return channels
    
    # Check each identifier field for changes
    for field_slug, field_info in identifier_fields_info.items():
        old_value = original_data.get(field_slug)
        new_value = current_data.get(field_slug)
        
        # Check if field was added (None/empty -> value)
        if (not old_value or old_value == '') and new_value:
            changed_fields.append({
                'field': field_slug,
                'type': 'added',
                'old': old_value,
                'new': new_value
            })
            # Determine channels based on match_type
            channels = determine_channels_for_field(field_slug, new_value, field_info)
            changed_types.update(channels)
                    
        # Check if field was updated (value -> different value)
        elif old_value and new_value and old_value != new_value:
            changed_fields.append({
                'field': field_slug,
                'type': 'updated',
                'old': old_value,
                'new': new_value
            })
            # Determine channels based on match_type
            channels = determine_channels_for_field(field_slug, new_value, field_info)
            changed_types.update(channels)
    
    return {
        'has_changes': len(changed_fields) > 0,
        'changed_fields': changed_fields,
        'changed_types': changed_types  # e.g., {'email', 'phone', 'linkedin'}
    }


@receiver(pre_save, sender=Record)
def capture_record_identifiers_before_save(sender, instance, **kwargs):
    """
    Capture record's identifier field values before save for change detection.
    This works alongside the existing capture_record_state_before_save signal.
    """
    if instance.pk:
        try:
            original = Record.objects.get(pk=instance.pk)
            # Store original data for identifier comparison
            instance._original_identifier_data = original.data.copy()
        except Record.DoesNotExist:
            instance._original_identifier_data = {}
    else:
        instance._original_identifier_data = {}


@receiver(post_save, sender=Record)
def trigger_communication_sync_on_identifier_change(sender, instance, created, **kwargs):
    """
    Trigger communication sync when identifier fields are added or updated.
    This runs after record save and checks for changes in fields used by duplicate rules.
    """
    logger.info(f"📡 COMM SYNC SIGNAL: post_save triggered for record {instance.id}")
    logger.info(f"   🆕 Created: {created}")
    logger.info(f"   📊 Has _original_identifier_data: {hasattr(instance, '_original_identifier_data')}")
    
    # Skip if explicitly disabled
    if hasattr(instance, '_skip_communication_sync') and instance._skip_communication_sync:
        logger.info(f"   ⏸️  Skipping communication sync: _skip_communication_sync is True")
        return
    
    # Get identifier fields from duplicate rules
    identifier_fields_info = get_identifier_fields_from_duplicate_rules(instance.pipeline)
    
    if not identifier_fields_info:
        logger.info(f"   ⏸️  No identifier fields defined in duplicate rules for pipeline {instance.pipeline.name}")
        return
    
    logger.info(f"   🔍 Identifier fields from duplicate rules: {list(identifier_fields_info.keys())}")
    
    # Determine if we should sync
    should_sync = False
    trigger_reason = ""
    changed_fields_info = []
    channels_to_sync = set()
    
    if created:
        # New record - check if it has any identifier fields populated
        has_identifiers = any(
            instance.data.get(field) and instance.data.get(field) != ''
            for field in identifier_fields_info.keys()
        )
        
        if has_identifiers:
            should_sync = True
            trigger_reason = "New record with communication identifiers"
            
            # Use detect_identifier_changes with empty original data for new record
            empty_original = {}
            changes = detect_identifier_changes(empty_original, instance.data, identifier_fields_info, instance.pipeline)
            
            if changes['has_changes']:
                changed_fields_info = changes['changed_fields']
                
                # Map channel types to actual channel names
                for channel_type in changes['changed_types']:
                    if channel_type == 'email':
                        channels_to_sync.update(['gmail', 'email'])
                    elif channel_type == 'phone':
                        channels_to_sync.update(['whatsapp'])
                    elif channel_type:  # LinkedIn or other social media
                        channels_to_sync.add(channel_type)
            
            logger.info(f"   ✅ New record has identifiers: {[f['field'] for f in changed_fields_info]}")
            logger.info(f"   📡 Channels to sync: {channels_to_sync}")
    else:
        # Existing record - check for changes in identifier fields
        original_data = getattr(instance, '_original_identifier_data', {})
        changes = detect_identifier_changes(original_data, instance.data, identifier_fields_info, instance.pipeline)
        
        if changes['has_changes']:
            should_sync = True
            changed_fields_info = changes['changed_fields']
            trigger_reason = f"Identifier fields updated: {', '.join([f['field'] for f in changed_fields_info])}"
            
            # Map channel types to actual channel names
            for channel_type in changes['changed_types']:
                if channel_type == 'email':
                    channels_to_sync.update(['gmail', 'email'])
                elif channel_type == 'phone':
                    channels_to_sync.update(['whatsapp'])
                elif channel_type:  # LinkedIn or other social media
                    channels_to_sync.add(channel_type)
            
            logger.info(f"   ✅ Identifier fields changed: {changed_fields_info}")
            logger.info(f"   📡 Channels to sync: {channels_to_sync}")
    
    if not should_sync:
        logger.info(f"   ⏸️  No identifier field changes detected, skipping sync")
        return
    
    # Check if sync is already in progress
    try:
        profile, profile_created = RecordCommunicationProfile.objects.get_or_create(
            record=instance,
            defaults={
                'pipeline': instance.pipeline,
                'created_by': instance.created_by
            }
        )
        
        if profile.sync_in_progress:
            logger.info(f"   ⚠️  Sync already in progress for record {instance.id}, skipping")
            return
        
        # Check if recently synced (unless it's a new record with identifiers)
        if not created and profile.last_full_sync:
            time_since_sync = timezone.now() - profile.last_full_sync
            # Allow re-sync after 5 minutes for automatic triggers
            if time_since_sync.total_seconds() < 300:  # 5 minutes
                logger.info(f"   ⏰ Record was synced {time_since_sync.total_seconds():.0f}s ago, skipping")
                return
        
        # Extract and update identifiers in profile
        extractor = RecordIdentifierExtractor()
        identifiers = extractor.extract_identifiers_from_record(instance)
        
        profile.communication_identifiers = identifiers
        profile.identifier_fields = list(identifier_fields_info.keys())
        profile.save()
        
        logger.info(f"   📝 Updated profile with identifiers: {identifiers}")
        
    except Exception as e:
        logger.error(f"Failed to check/create communication profile: {str(e)}")
        return
    
    # Queue the sync task
    try:
        from .tasks import sync_record_communications
        
        # Get tenant schema from connection
        from django.db import connection
        tenant_schema = getattr(connection, 'tenant', None)
        tenant_schema_name = tenant_schema.schema_name if tenant_schema else 'public'
        
        logger.info(f"   🚀 Queueing sync task for record {instance.id} in tenant {tenant_schema_name}")
        logger.info(f"   📋 Trigger reason: {trigger_reason}")
        
        # Queue the Celery task with channel filter
        result = sync_record_communications.delay(
            record_id=instance.id,
            tenant_schema=tenant_schema_name,
            triggered_by_id=instance.updated_by.id if instance.updated_by else instance.created_by.id if instance.created_by else None,
            trigger_reason=trigger_reason,
            channels_to_sync=list(channels_to_sync) if channels_to_sync else None
        )
        
        # Create sync job record
        sync_job = RecordSyncJob.objects.create(
            record=instance,
            profile=profile,
            job_type='auto_trigger',
            status='pending',
            triggered_by=instance.updated_by or instance.created_by,
            trigger_reason=trigger_reason,
            celery_task_id=result.id
            # Note: metadata field doesn't exist, consider adding in future migration
        )
        
        logger.info(f"   ✅ Sync job created: {sync_job.id} with Celery task: {result.id}")
        
    except Exception as e:
        logger.error(f"Failed to queue communication sync for record {instance.id}: {str(e)}")
        # Don't raise - we don't want to break record saves if sync fails


@receiver(post_save, sender=RecordCommunicationProfile)
def log_profile_updates(sender, instance, created, **kwargs):
    """Log when communication profiles are created or updated"""
    if created:
        logger.info(f"📱 Communication profile created for record {instance.record_id}")
    else:
        logger.info(f"📱 Communication profile updated for record {instance.record_id}")