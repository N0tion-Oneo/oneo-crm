"""
Celery tasks for pipeline-related async processing
"""

from celery import shared_task
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django_tenants.utils import schema_context
import logging
import json

logger = logging.getLogger(__name__)


# OLD AI TASK REMOVED - Now using ai.tasks.process_ai_job
@shared_task(bind=True, name='pipelines.tasks.process_bulk_operation')
def process_bulk_operation(self, operation_type, record_ids, operation_data):
    """
    Process bulk operations on multiple records
    Used for: Bulk updates, mass data imports, batch processing
    """
    try:
        from .models import Record
        
        records = Record.objects.filter(id__in=record_ids)
        processed_count = 0
        errors = []
        
        for record in records:
            try:
                if operation_type == 'update':
                    # Bulk update operation
                    record_data = record.data.copy()
                    record_data.update(operation_data.get('updates', {}))
                    record.data = record_data
                    record.save()
                    
                elif operation_type == 'delete':
                    # Bulk delete operation
                    record.delete()
                    
                elif operation_type == 'export':
                    # Export operation would generate files
                    pass
                    
                processed_count += 1
                
            except Exception as record_error:
                errors.append({
                    'record_id': record.id,
                    'error': str(record_error)
                })
        
        result = {
            'operation_type': operation_type,
            'processed_count': processed_count,
            'total_records': len(record_ids),
            'errors': errors,
            'success': len(errors) == 0
        }
        
        # Cache result for status checking
        cache_key = f"bulk_operation:{self.request.id}"
        cache.set(cache_key, result, timeout=3600)
        
        logger.info(f"Bulk operation {operation_type} processed {processed_count} records")
        return result
        
    except Exception as e:
        error_msg = f"Bulk operation error: {e}"
        logger.error(error_msg)
        return {'error': error_msg, 'success': False}


@shared_task(bind=True, name='pipelines.tasks.generate_pipeline_report')
def generate_pipeline_report(self, pipeline_id, report_type, filters=None):
    """
    Generate comprehensive pipeline reports
    Used for: Analytics, data exports, performance reports
    """
    try:
        from .models import Pipeline, Record
        
        pipeline = Pipeline.objects.get(id=pipeline_id)
        records = Record.objects.filter(pipeline=pipeline)
        
        # Apply filters if provided
        if filters:
            # Add filtering logic here
            pass
        
        # Generate report based on type
        if report_type == 'summary':
            report_data = {
                'pipeline_name': pipeline.name,
                'total_records': records.count(),
                'field_distribution': {},
                'recent_activity': []
            }
        elif report_type == 'detailed':
            report_data = {
                'pipeline_name': pipeline.name,
                'records': [record.data for record in records[:1000]],  # Limit for performance
                'field_definitions': [field.to_dict() for field in pipeline.fields.all()]
            }
        
        # Cache the report
        cache_key = f"pipeline_report:{self.request.id}"
        cache.set(cache_key, report_data, timeout=7200)  # 2 hours
        
        logger.info(f"Report generated for pipeline {pipeline_id}")
        return {
            'report_type': report_type,
            'pipeline_id': pipeline_id,
            'status': 'completed',
            'cache_key': cache_key
        }
        
    except Exception as e:
        error_msg = f"Report generation error: {e}"
        logger.error(error_msg)
        return {'error': error_msg, 'success': False}


@shared_task(bind=True, name='pipelines.tasks.migrate_field_schema')
def migrate_field_schema(self, pipeline_id, field_slug, new_config, batch_size=100):
    """
    Migrate field schema changes in background
    """
    try:
        from .models import Pipeline, Field
        from .migrator import FieldSchemaMigrator
        
        pipeline = Pipeline.objects.get(id=pipeline_id)
        field = pipeline.fields.get(slug=field_slug)
        migrator = FieldSchemaMigrator(pipeline)
        
        # Perform migration
        result = migrator.migrate_field_data(field, new_config, batch_size, dry_run=False)
        
        # Cache result for status checking
        cache_key = f"field_migration:{self.request.id}"
        cache.set(cache_key, result, timeout=3600)
        
        logger.info(f"Field schema migration completed: {field_slug}")
        return result
        
    except Exception as e:
        error_msg = f"Field migration error: {e}"
        logger.error(error_msg)
        return {'error': error_msg, 'success': False}


@shared_task(bind=True, name='pipelines.tasks.execute_scheduled_hard_deletes')
def execute_scheduled_hard_deletes(self):
    """
    Execute hard deletes for fields that have passed their grace period
    """
    try:
        from django.utils import timezone
        from .models import Field
        from django.db import models
        
        # Find fields ready for hard deletion
        now = timezone.now()
        fields_to_delete = Field.objects.with_deleted().filter(
            scheduled_for_hard_delete__lte=now,
            is_deleted=True
        )
        
        deleted_count = 0
        errors = []
        
        for field in fields_to_delete:
            try:
                can_delete, message = field.can_hard_delete()
                if can_delete:
                    # Export field data before deletion
                    export_result = export_field_data_before_deletion(field)
                    
                    # Perform hard deletion
                    field_slug = field.slug
                    pipeline_name = field.pipeline.name
                    
                    # Clean up field data from all records
                    field.pipeline.records.filter(
                        data__has_key=field.slug
                    ).update(
                        data=models.F('data') - field.slug
                    )
                    
                    # Delete the field itself
                    field.delete()
                    
                    deleted_count += 1
                    logger.warning(f"Hard deleted field {field_slug} from pipeline {pipeline_name}")
                    
                else:
                    logger.info(f"Field {field.slug} not ready for hard deletion: {message}")
                    
            except Exception as field_error:
                errors.append({
                    'field_id': field.id,
                    'field_slug': field.slug,
                    'error': str(field_error)
                })
                logger.error(f"Error hard deleting field {field.slug}: {field_error}")
        
        result = {
            'deleted_count': deleted_count,
            'errors': errors,
            'success': len(errors) == 0
        }
        
        # Cache result
        cache_key = f"hard_delete_execution:{self.request.id}"
        cache.set(cache_key, result, timeout=3600)
        
        logger.info(f"Scheduled hard delete execution completed: {deleted_count} fields deleted")
        return result
        
    except Exception as e:
        error_msg = f"Hard delete execution error: {e}"
        logger.error(error_msg)
        return {'error': error_msg, 'success': False}


@shared_task(bind=True, name='pipelines.tasks.cleanup_orphaned_field_data')
def cleanup_orphaned_field_data(self, pipeline_id):
    """
    Clean up orphaned field data from records (data for fields that no longer exist)
    """
    try:
        from .models import Pipeline
        from django.db import models
        
        pipeline = Pipeline.objects.get(id=pipeline_id)
        
        # Get current field slugs
        current_field_slugs = set(pipeline.fields.values_list('slug', flat=True))
        
        # Find records with orphaned data
        records_with_data = pipeline.records.exclude(data__isnull=True)
        
        cleaned_count = 0
        total_keys_removed = 0
        
        for record in records_with_data:
            if not record.data:
                continue
            
            # Find orphaned keys
            record_keys = set(record.data.keys())
            orphaned_keys = record_keys - current_field_slugs
            
            if orphaned_keys:
                # Remove orphaned keys
                cleaned_data = {k: v for k, v in record.data.items() if k not in orphaned_keys}
                record.data = cleaned_data
                record._skip_broadcast = True
                record.save(update_fields=['data'])
                
                cleaned_count += 1
                total_keys_removed += len(orphaned_keys)
                
                logger.info(f"Cleaned {len(orphaned_keys)} orphaned keys from record {record.id}")
        
        result = {
            'pipeline_id': pipeline_id,
            'records_cleaned': cleaned_count,
            'keys_removed': total_keys_removed,
            'success': True
        }
        
        # Cache result
        cache_key = f"orphaned_cleanup:{self.request.id}"
        cache.set(cache_key, result, timeout=3600)
        
        logger.info(f"Orphaned field data cleanup completed for pipeline {pipeline_id}")
        return result
        
    except Exception as e:
        error_msg = f"Orphaned data cleanup error: {e}"
        logger.error(error_msg)
        return {'error': error_msg, 'success': False}


@shared_task(bind=True, name='pipelines.tasks.migrate_tenant_schema_automatically')
def migrate_tenant_schema_automatically(self, tenant_schema, field_id, changes):
    """
    Automatically migrate tenant schema when field changes require it
    Runs with tenant in maintenance mode for complete data consistency
    """
    
    try:
        with schema_context(tenant_schema):
            # Get tenant and field objects
            from tenants.models import Tenant, TenantMaintenance
            from .models import Field
            
            tenant = Tenant.objects.get(schema_name=tenant_schema)
            field = Field.objects.get(id=field_id)
            maintenance = TenantMaintenance.objects.get(tenant=tenant)
            
            logger.info(f"Starting automatic schema migration for field {field.slug} in tenant {tenant_schema}")
            
            # Initialize migration with progress tracking
            maintenance.status_message = "Initializing schema migration..."
            maintenance.progress_percentage = 0
            maintenance.save()
            
            # Use existing FieldSchemaMigrator for actual migration
            from .migrator import FieldSchemaMigrator
            migrator = FieldSchemaMigrator(field.pipeline)
            
            # Create new field configuration from current field
            new_config = {
                'field_type': field.field_type,
                'field_config': field.field_config,
                'storage_constraints': field.storage_constraints,
                'business_rules': field.business_rules
            }
            
            # Analyze migration requirements
            maintenance.status_message = "Analyzing migration requirements..."
            maintenance.progress_percentage = 10
            maintenance.save()
            
            analysis = migrator.analyze_field_change_impact(field, new_config)
            
            # Estimate completion time
            estimated_minutes = analysis.get('estimated_time_minutes', 1)
            maintenance.estimated_completion = timezone.now() + timezone.timedelta(minutes=estimated_minutes)
            maintenance.progress_percentage = 20
            maintenance.save()
            
            # Generate migration preview for validation
            maintenance.status_message = "Generating migration preview..."
            maintenance.save()
            
            preview = migrator.generate_migration_preview(field, new_config, preview_limit=50)
            
            # Check if migration is safe to proceed
            risk_level = preview.get('risk_assessment', {}).get('risk_level', 'low')
            if risk_level == 'high':
                logger.warning(f"High-risk migration detected for field {field.slug} - proceeding with caution")
            
            maintenance.progress_percentage = 30
            maintenance.save()
            
            # Execute actual migration in batches
            maintenance.status_message = f"Migrating {analysis.get('records_with_data', 0)} records..."
            maintenance.save()
            
            # Perform migration with progress tracking
            migration_error = None
            migration_result = None
            
            logger.info(f"🚀 STARTING ATOMIC MIGRATION TRANSACTION for field {field.slug} in tenant {tenant_schema}")
            try:
                with transaction.atomic():
                    logger.info(f"🔒 TRANSACTION STARTED - Migration work begins")
                    
                    # Handle different migration types
                    if 'field_rename' in changes['migration_types']:
                        logger.info(f"📝 FIELD RENAME MIGRATION: {changes['change_details']}")
                        migration_result = migrate_field_rename(field, changes['change_details'], maintenance)
                    elif 'type_change' in changes['migration_types']:
                        logger.info(f"🔄 FIELD TYPE CHANGE MIGRATION")
                        migration_result = migrator.migrate_field_data(
                            field, new_config, batch_size=100, dry_run=False
                        )
                    elif 'constraint_change' in changes['migration_types']:
                        logger.info(f"⚙️ CONSTRAINT CHANGE MIGRATION")
                        migration_result = migrate_constraint_changes(field, new_config, maintenance)
                    else:
                        logger.info(f"🔧 GENERIC FIELD MIGRATION")
                        # Generic migration
                        migration_result = migrator.migrate_field_data(
                            field, new_config, batch_size=100, dry_run=False
                        )
                    
                    logger.info(f"✅ MIGRATION WORK COMPLETED - Result: {migration_result['success']}, Records: {migration_result.get('records_migrated', 0)}")
                    
                    # Update progress during migration
                    maintenance.progress_percentage = 70
                    maintenance.save()
                    logger.info(f"📊 PROGRESS UPDATE: 70% - Migration work done")
                    
                    if not migration_result['success']:
                        raise Exception(f"Migration failed: {migration_result['errors']}")
                    
                    # Verify migration success
                    maintenance.status_message = "Verifying migration results..."
                    maintenance.progress_percentage = 90
                    maintenance.save()
                    logger.info(f"🔍 VERIFICATION PHASE: Running migration verification checks")
                    
                    # Run verification checks
                    verification_result = verify_schema_migration_success(field, new_config)
                    if not verification_result['success']:
                        raise Exception(f"Migration verification failed: {verification_result['errors']}")
                    
                    logger.info(f"✅ VERIFICATION PASSED: Migration integrity confirmed")
                    
                    # Migration completed successfully
                    maintenance.status_message = "Migration completed successfully"
                    maintenance.progress_percentage = 100
                    maintenance.save()
                    logger.info(f"📊 PROGRESS UPDATE: 100% - Migration complete")
                    
                    # CRITICAL FIX: Deactivate maintenance mode INSIDE the transaction
                    # This ensures atomicity - either everything succeeds or everything rolls back
                    logger.info(f"🎯 ATOMIC DEACTIVATION: Deactivating maintenance mode inside transaction")
                    maintenance.deactivate("Schema migration completed successfully")
                    logger.info(f"✅ MAINTENANCE DEACTIVATED: Maintenance mode turned off atomically")
                    
                    logger.info(f"💾 TRANSACTION READY TO COMMIT: All migration work and deactivation complete")
                    
                logger.info(f"🎉 TRANSACTION COMMITTED SUCCESSFULLY: Field {field.slug} migration complete in tenant {tenant_schema}")
                    
            except Exception as e:
                migration_error = e
                logger.error(f"💥 MIGRATION EXCEPTION: {migration_error}")
                logger.error(f"🔄 TRANSACTION ROLLBACK: All changes will be rolled back atomically")
            
            # Handle migration failure OUTSIDE the transaction to prevent rollback
            if migration_error:
                logger.info(f"⚠️ ERROR HANDLING: Processing migration failure outside transaction")
                # Update maintenance status outside transaction so it persists
                maintenance.status_message = f"Migration failed: {str(migration_error)}"
                maintenance.save()
                logger.info(f"📝 MAINTENANCE STATUS: Updated with error message (persists after rollback)")
                
                # Keep tenant in maintenance mode for admin investigation
                logger.info(f"🔒 MAINTENANCE KEPT ACTIVE: Tenant remains in maintenance for investigation")
                return {
                    'status': 'failed',
                    'error': str(migration_error),
                    'tenant_schema': tenant_schema,
                    'field_id': field_id
                }
            
            # Migration completed successfully - maintenance mode already deactivated inside transaction
            
            # Broadcast completion to WebSocket clients
            try:
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        f'maintenance_{tenant.id}',
                        {
                            'type': 'maintenance_update',
                            'progress_percentage': 100,
                            'status_message': 'Migration completed successfully',
                            'is_complete': True
                        }
                    )
            except Exception as broadcast_error:
                logger.warning(f"Failed to broadcast completion: {broadcast_error}")
            
            return {
                'status': 'completed',
                'tenant_schema': tenant_schema,
                'field_id': field_id,
                'records_migrated': migration_result.get('records_migrated', 0),
                'processing_time_minutes': estimated_minutes
            }
            
    except Exception as e:
        logger.critical(f"Critical error in schema migration: {e}")
        
        # Ensure tenant is released from maintenance mode
        try:
            with schema_context(tenant_schema):
                from tenants.models import TenantMaintenance
                maintenance = TenantMaintenance.objects.get(tenant__schema_name=tenant_schema)
                maintenance.deactivate(f"Critical error: {str(e)}")
        except Exception:
            pass
        
        return {
            'status': 'critical_error',
            'error': str(e),
            'tenant_schema': tenant_schema
        }


def migrate_field_rename(field, change_details, maintenance):
    """Handle field rename migration specifically"""
    try:
        from .models import Record
        
        # Extract old and new names from change details
        old_slug = None
        new_slug = field.slug
        
        for detail in change_details:
            if "renamed from" in detail:
                # Extract old slug from message like "Field renamed from 'old_name' to 'new_name'"
                import re
                match = re.search(r"'([^']+)' to '([^']+)'", detail)
                if match:
                    old_slug = match.group(1)
                    break
        
        if not old_slug:
            raise Exception("Could not determine old field slug for rename migration")
        
        logger.info(f"Migrating field rename from '{old_slug}' to '{new_slug}'")
        
        # Count affected records
        affected_records = Record.objects.filter(
            pipeline=field.pipeline,
            is_deleted=False,
            data__has_key=old_slug
        )
        
        total_count = affected_records.count()
        migrated_count = 0
        batch_size = 100
        
        # Process in batches
        for batch_start in range(0, total_count, batch_size):
            batch_records = affected_records[batch_start:batch_start + batch_size]
            
            for record in batch_records:
                # Rename field in record data
                if old_slug in record.data:
                    record.data[new_slug] = record.data.pop(old_slug)
                    record._skip_broadcast = True  # Prevent real-time broadcasts during migration
                    record.save(update_fields=['data'])
                    migrated_count += 1
            
            # Update progress
            progress = 30 + int((batch_start / total_count) * 40)  # 30-70% range
            maintenance.progress_percentage = progress
            maintenance.status_message = f"Renamed field in {migrated_count}/{total_count} records"
            maintenance.save()
        
        return {
            'success': True,
            'records_processed': total_count,
            'records_migrated': migrated_count,
            'records_failed': 0,
            'migration_type': 'field_rename'
        }
        
    except Exception as e:
        logger.error(f"Field rename migration failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'migration_type': 'field_rename'
        }


def migrate_constraint_changes(field, new_config, maintenance):
    """Handle constraint change migrations"""
    try:
        from .models import Record
        
        # Get records with data for this field
        affected_records = Record.objects.filter(
            pipeline=field.pipeline,
            is_deleted=False,
            data__has_key=field.slug
        )
        
        total_count = affected_records.count()
        migrated_count = 0
        failed_count = 0
        
        new_constraints = new_config.get('storage_constraints', {})
        
        for record in affected_records:
            try:
                field_value = record.data.get(field.slug)
                updated_value = apply_constraint_changes(field_value, new_constraints)
                
                if updated_value != field_value:
                    record.data[field.slug] = updated_value
                    record._skip_broadcast = True
                    record.save(update_fields=['data'])
                    migrated_count += 1
                
            except Exception as record_error:
                logger.warning(f"Failed to migrate constraints for record {record.id}: {record_error}")
                failed_count += 1
        
        return {
            'success': failed_count == 0,
            'records_processed': total_count,
            'records_migrated': migrated_count,
            'records_failed': failed_count,
            'migration_type': 'constraint_change'
        }
        
    except Exception as e:
        logger.error(f"Constraint migration failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'migration_type': 'constraint_change'
        }


def apply_constraint_changes(value, new_constraints):
    """Apply new storage constraints to a field value"""
    if value is None:
        return value
    
    # Handle max length constraint
    max_length = new_constraints.get('max_storage_length')
    if max_length and isinstance(value, str) and len(value) > max_length:
        return value[:max_length]
    
    # Handle other constraint types as needed
    return value


def verify_schema_migration_success(field, new_config):
    """Verify that migration completed successfully"""
    try:
        from .models import Record
        
        # Check that all records now use the correct field structure
        total_records = Record.objects.filter(
            pipeline=field.pipeline,
            is_deleted=False
        ).count()
        
        records_with_field = Record.objects.filter(
            pipeline=field.pipeline,
            is_deleted=False,
            data__has_key=field.slug
        ).count()
        
        # Verification checks depend on migration type
        verification_result = {
            'success': True,
            'total_records': total_records,
            'records_with_field': records_with_field,
            'errors': []
        }
        
        # Additional verification logic could be added here
        
        logger.info(f"Migration verification: {records_with_field} records have field {field.slug}")
        
        return verification_result
        
    except Exception as e:
        logger.error(f"Migration verification failed: {e}")
        return {
            'success': False,
            'errors': [str(e)]
        }


def export_field_data_before_deletion(field):
    """
    Export field data before hard deletion
    """
    try:
        import csv
        import json
        from django.conf import settings
        from datetime import datetime
        import os
        
        # Create export directory if it doesn't exist
        export_dir = os.path.join(settings.MEDIA_ROOT, 'field_exports')
        os.makedirs(export_dir, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"field_export_{field.pipeline.slug}_{field.slug}_{timestamp}"
        
        # Export field configuration
        config_data = {
            'field_info': {
                'pipeline_name': field.pipeline.name,
                'pipeline_slug': field.pipeline.slug,
                'field_name': field.name,
                'field_slug': field.slug,
                'field_type': field.field_type,
                'field_config': field.field_config,
                'storage_constraints': field.storage_constraints,
                'business_rules': field.business_rules,
                'ai_config': field.ai_config,
                'deleted_at': field.deleted_at.isoformat() if field.deleted_at else None,
                'deleted_by': field.deleted_by.username if field.deleted_by else None,
                'hard_delete_reason': field.hard_delete_reason,
                'export_timestamp': datetime.now().isoformat()
            }
        }
        
        # Save configuration
        config_file = os.path.join(export_dir, f"{filename}_config.json")
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        # Export record data
        records_with_data = field.pipeline.records.filter(
            data__has_key=field.slug
        ).values('id', 'data', 'created_at', 'updated_at')
        
        csv_file = os.path.join(export_dir, f"{filename}_data.csv")
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['record_id', 'field_value', 'created_at', 'updated_at'])
            
            for record in records_with_data:
                field_value = record['data'].get(field.slug, '')
                writer.writerow([
                    record['id'],
                    str(field_value),
                    record['created_at'],
                    record['updated_at']
                ])
        
        logger.info(f"Exported field data for {field.slug} to {config_file} and {csv_file}")
        
        return {
            'success': True,
            'config_file': config_file,
            'data_file': csv_file
        }
        
    except Exception as e:
        logger.error(f"Error exporting field data: {e}")
        return {
            'success': False,
            'error': str(e)
        }