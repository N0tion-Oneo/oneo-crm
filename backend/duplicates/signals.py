"""
Django signals for duplicate detection integration
"""
import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from pipelines.models import Record
from .models import DuplicateRule, DuplicateDetectionResult
from .logic_engine import DuplicateLogicEngine
from .models import DuplicateMatch

logger = logging.getLogger(__name__)


class DuplicateDetectionError(Exception):
    """Custom exception for duplicate detection errors"""
    def __init__(self, message, duplicates=None):
        super().__init__(message)
        self.duplicates = duplicates


@receiver(pre_save, sender=Record)
def check_duplicates_on_record_save(sender, instance, **kwargs):
    """
    Check for duplicates before saving a record.
    This runs on both create and update operations.
    """
    # Skip duplicate checking if explicitly disabled
    if hasattr(instance, '_skip_duplicate_check') and instance._skip_duplicate_check:
        return
    
    # Get the pipeline
    pipeline = instance.pipeline
    
    # Get tenant from request (multi-tenant architecture)
    try:
        from django.db import connection
        # Check if we're in a tenant context
        if not hasattr(connection, 'tenant') or not connection.tenant:
            logger.debug("No tenant context found, skipping duplicate checking")
            return
        
        tenant = connection.tenant
        tenant_schema = connection.tenant.schema_name
        
        # Skip duplicate checking on public schema
        if tenant_schema == 'public':
            return
            
    except Exception as e:
        logger.error(f"Error getting tenant context: {str(e)}")
        return
    
    # Get all active duplicate rules for this pipeline
    rules = DuplicateRule.objects.filter(
        tenant=tenant,
        pipeline=pipeline,
        is_active=True
    ).prefetch_related('test_cases')
    
    if not rules:
        logger.debug(f"No duplicate rules found for pipeline {pipeline.name} in tenant {tenant.name}")
        return
    
    # Initialize the logic engine
    engine = DuplicateLogicEngine(tenant_id=tenant.id)
    
    # Check against existing records (excluding the current record if it's an update)
    existing_records = Record.objects.filter(
        pipeline=pipeline
    )
    
    # Exclude the current record if it's an update (has an ID)
    if instance.id:
        existing_records = existing_records.exclude(id=instance.id)
    
    detected_duplicates = []
    
    # Check each rule
    for rule in rules:
        logger.debug(f"Checking rule: {rule.name}")
        
        # Check against existing records
        for existing_record in existing_records:
            try:
                is_duplicate = engine.evaluate_rule(
                    rule=rule,
                    record1_data=instance.data,
                    record2_data=existing_record.data
                )
                
                if is_duplicate:
                    duplicate_info = {
                        'rule': rule,
                        'existing_record': existing_record,
                        'confidence': 0.95,  # Could be calculated based on rule complexity
                        'matched_fields': engine.get_matched_fields(rule, instance.data, existing_record.data)
                    }
                    detected_duplicates.append(duplicate_info)
                    logger.info(f"Duplicate detected: Record matches existing record {existing_record.id} via rule '{rule.name}'")
                    
                    # Handle based on rule action
                    if rule.action_on_duplicate == 'block':
                        raise DuplicateDetectionError(
                            f"Record creation blocked: Duplicate found matching rule '{rule.name}'",
                            duplicates=detected_duplicates
                        )
                    elif rule.action_on_duplicate == 'merge_prompt':
                        # Store the duplicate for later handling by frontend
                        instance._detected_duplicates = detected_duplicates
                        # Don't block, but flag for frontend handling
                        
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.name}: {str(e)}")
                continue
    
    # Store detected duplicates for post-save processing
    if detected_duplicates:
        instance._detected_duplicates = detected_duplicates


@receiver(post_save, sender=Record)
def handle_duplicates_after_record_save(sender, instance, created, **kwargs):
    """
    Handle duplicate detection results after a record is saved.
    This creates DuplicateMatch entries and DuplicateDetectionResult entries.
    """
    # Skip if no duplicates detected
    if not hasattr(instance, '_detected_duplicates'):
        return
    
    detected_duplicates = instance._detected_duplicates
    
    # Get tenant using the same approach as pre_save signal
    try:
        from django.db import connection
        # Check if we're in a tenant context
        if not hasattr(connection, 'tenant') or not connection.tenant:
            logger.debug("No tenant context found, skipping duplicate match creation")
            return
        
        tenant = connection.tenant
        tenant_schema = connection.tenant.schema_name
        
        # Skip processing on public schema
        if tenant_schema == 'public':
            return
            
    except Exception as e:
        logger.error(f"Error getting tenant context in post_save: {str(e)}")
        return
    
    # Create DuplicateDetectionResult entry
    detection_result = DuplicateDetectionResult.objects.create(
        tenant=tenant,
        pipeline=instance.pipeline,
        record=instance,
        total_duplicates_found=len(detected_duplicates),
        detection_summary={
            'rules_triggered': [dup['rule'].name for dup in detected_duplicates],
            'matched_records': [dup['existing_record'].id for dup in detected_duplicates],
            'detection_timestamp': timezone.now().isoformat()
        },
        requires_review=any(dup['rule'].action_on_duplicate == 'merge_prompt' for dup in detected_duplicates)
    )
    
    # Create DuplicateMatch entries for each detected duplicate
    for duplicate_info in detected_duplicates:
        try:
            # Check if this duplicate match already exists
            existing_match = DuplicateMatch.objects.filter(
                tenant=tenant,
                record1=instance,
                record2=duplicate_info['existing_record'],
                status='pending'
            ).first()
            
            if not existing_match:
                # Create new duplicate match
                duplicate_match = DuplicateMatch.objects.create(
                    tenant=tenant,
                    record1=instance,
                    record2=duplicate_info['existing_record'],
                    confidence_score=duplicate_info['confidence'],
                    matched_fields=duplicate_info['matched_fields'],
                    detection_rule=duplicate_info['rule'].name,
                    match_details={
                        'rule_id': duplicate_info['rule'].id,
                        'rule_name': duplicate_info['rule'].name,
                        'detection_timestamp': timezone.now().isoformat(),
                        'record_operation': 'create' if created else 'update'
                    },
                    status='pending',
                    requires_review=duplicate_info['rule'].action_on_duplicate == 'merge_prompt'
                )
                
                logger.info(f"Created duplicate match: {duplicate_match.id}")
                
                # Update detection result with match IDs
                detection_result.duplicate_match_ids.append(duplicate_match.id)
                detection_result.save(update_fields=['duplicate_match_ids'])
                
        except Exception as e:
            logger.error(f"Error creating duplicate match: {str(e)}")
    
    # Clean up the temporary attribute
    delattr(instance, '_detected_duplicates')
    
    logger.info(f"Duplicate detection completed for record {instance.id}. Found {len(detected_duplicates)} duplicates.")


@receiver(post_save, sender=DuplicateRule)
def invalidate_duplicate_cache_on_rule_change(sender, instance, **kwargs):
    """
    Invalidate any duplicate detection caches when rules are modified.
    """
    # TODO: Implement cache invalidation if we add caching later
    logger.info(f"Duplicate rule {instance.name} was modified. Cache invalidation would occur here.")


def run_bulk_duplicate_detection(pipeline, tenant=None, dry_run=False):
    """
    Utility function to run duplicate detection on all existing records in a pipeline.
    Useful when new rules are added or when doing bulk analysis.
    
    Args:
        pipeline: Pipeline to check
        tenant: Specific tenant (if None, uses pipeline's tenant)
        dry_run: If True, only report duplicates without creating matches
        
    Returns:
        dict: Results summary
    """
    if tenant is None:
        tenant = pipeline.tenant
    
    # Get all active rules for this pipeline
    rules = DuplicateRule.objects.filter(
        tenant=tenant,
        pipeline=pipeline,
        is_active=True
    )
    
    if not rules:
        return {'error': 'No active duplicate rules found for this pipeline'}
    
    # Get all records for this pipeline
    records = Record.objects.filter(
        tenant=tenant,
        pipeline=pipeline,
        is_deleted=False
    ).order_by('created_at')
    
    engine = DuplicateLogicEngine()
    total_comparisons = 0
    total_duplicates_found = 0
    matches_created = 0
    
    results = {
        'pipeline': pipeline.name,
        'tenant': tenant.name,
        'total_records': records.count(),
        'rules_checked': list(rules.values_list('name', flat=True)),
        'duplicates_by_rule': {},
        'dry_run': dry_run
    }
    
    # Compare each record against all subsequent records
    records_list = list(records)
    for i, record1 in enumerate(records_list):
        for record2 in records_list[i+1:]:
            total_comparisons += 1
            
            # Check each rule
            for rule in rules:
                try:
                    is_duplicate = engine.evaluate_rule(
                        rule=rule,
                        record1_data=record1.data,
                        record2_data=record2.data
                    )
                    
                    if is_duplicate:
                        total_duplicates_found += 1
                        
                        # Track by rule
                        if rule.name not in results['duplicates_by_rule']:
                            results['duplicates_by_rule'][rule.name] = []
                        
                        results['duplicates_by_rule'][rule.name].append({
                            'record1_id': record1.id,
                            'record2_id': record2.id,
                            'matched_fields': engine.get_matched_fields(rule, record1.data, record2.data)
                        })
                        
                        # Create duplicate match if not dry run
                        if not dry_run:
                            # Check if match already exists
                            existing_match = DuplicateMatch.objects.filter(
                                tenant=tenant,
                                record1=record1,
                                record2=record2
                            ).first()
                            
                            if not existing_match:
                                DuplicateMatch.objects.create(
                                    tenant=tenant,
                                    record1=record1,
                                    record2=record2,
                                    confidence_score=0.90,  # Bulk detection confidence
                                    matched_fields=engine.get_matched_fields(rule, record1.data, record2.data),
                                    detection_rule=rule.name,
                                    match_details={
                                        'rule_id': rule.id,
                                        'detection_method': 'bulk_analysis',
                                        'detection_timestamp': timezone.now().isoformat()
                                    },
                                    status='pending',
                                    requires_review=True
                                )
                                matches_created += 1
                        
                except Exception as e:
                    logger.error(f"Error in bulk duplicate detection: {str(e)}")
                    continue
    
    results.update({
        'total_comparisons': total_comparisons,
        'total_duplicates_found': total_duplicates_found,
        'matches_created': matches_created
    })
    
    return results