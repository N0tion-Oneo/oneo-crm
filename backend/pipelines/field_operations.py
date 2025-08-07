"""
Unified Field Operation Manager
Single entry point for ALL field operations to eliminate fragmented architecture
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import Pipeline, Field, Record
from .field_types import FieldType
from .validation.field_validator import FieldValidator
from .migration.data_migrator import DataMigrator
from .state.field_state_manager import get_field_state_manager
from core.models import AuditLog

logger = logging.getLogger(__name__)
User = get_user_model()


class FieldOperationResult:
    """Standardized result object for all field operations"""
    
    def __init__(self, success: bool, field: Optional[Field] = None, 
                 operation_id: Optional[str] = None, errors: List[str] = None,
                 warnings: List[str] = None, metadata: Dict[str, Any] = None):
        self.success = success
        self.field = field
        self.operation_id = operation_id
        self.errors = errors or []
        self.warnings = warnings or []
        self.metadata = metadata or {}
        self.timestamp = timezone.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for API responses"""
        return {
            'success': self.success,
            'field_id': self.field.id if self.field else None,
            'operation_id': self.operation_id,
            'errors': self.errors,
            'warnings': self.warnings,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


class FieldOperationManager:
    """
    Single entry point for ALL field operations
    
    Replaces fragmented system across signals.py, migrator.py, migration_validator.py
    Provides consistent validation, migration, and error handling for all field operations.
    """
    
    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline
        self._operation_counter = 0
        self.validator = FieldValidator()
        self.migrator = DataMigrator(pipeline)
        self.state_manager = get_field_state_manager()
    
    def _generate_operation_id(self) -> str:
        """Generate unique operation ID for tracking"""
        self._operation_counter += 1
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        return f"field_op_{self.pipeline.id}_{timestamp}_{self._operation_counter}"
    
    def _create_audit_log(self, user: User, action: str, field: Field, 
                          changes: Dict[str, Any], operation_id: str = None):
        """Create comprehensive audit log entry for field operations"""
        try:
            # Build detailed change information
            audit_changes = {
                'operation_id': operation_id,
                'pipeline_id': self.pipeline.id,
                'pipeline_name': self.pipeline.name,
                'field_slug': field.slug,
                'field_name': field.name,
                'field_type': field.field_type,
            }
            
            # Safely serialize changes to avoid JSON serialization errors
            for key, value in changes.items():
                try:
                    if hasattr(value, 'id'):  # Django model objects
                        audit_changes[key] = f"{value.__class__.__name__}(id={value.id})"
                    elif key == 'field_config' and isinstance(value, dict):
                        # Clean field_config by removing non-serializable objects
                        clean_config = {}
                        for config_key, config_value in value.items():
                            if config_key == 'pipeline':
                                clean_config[config_key] = f"Pipeline(id={config_value.id})" if hasattr(config_value, 'id') else str(config_value)
                            elif config_key == 'created_by':
                                clean_config[config_key] = f"User(id={config_value.id})" if hasattr(config_value, 'id') else str(config_value)
                            else:
                                clean_config[config_key] = config_value
                        audit_changes[key] = clean_config
                    else:
                        audit_changes[key] = value
                except (TypeError, AttributeError):
                    audit_changes[key] = str(value)
            
            AuditLog.objects.create(
                user=user,
                action=action,
                model_name='Field',
                object_id=str(field.id),
                changes=audit_changes
            )
            
            logger.info(f"Created audit log: {action} for field {field.slug} by user {user.username if user else 'system'}")
            
        except Exception as e:
            logger.error(f"Failed to create audit log for field {field.slug}: {e}")
    
    # =============================================================================
    # MAIN FIELD OPERATIONS - Single entry points for all field operations
    # =============================================================================
    
    def create_field(self, field_config: Dict[str, Any], user: User) -> FieldOperationResult:
        """
        Create new field with comprehensive validation
        
        Args:
            field_config: Field configuration dictionary
            user: User performing the operation
            
        Returns:
            FieldOperationResult with success status and field instance
        """
        operation_id = self._generate_operation_id()
        logger.info(f"[{operation_id}] Starting field creation: {field_config.get('name')}")
        
        try:
            with transaction.atomic():
                # Step 1: Validate field creation using FieldValidator
                validation_result = self.validator.validate_field_creation(field_config, self.pipeline)
                if not validation_result.valid:
                    return FieldOperationResult(
                        success=False,
                        operation_id=operation_id,
                        errors=validation_result.errors,
                        warnings=validation_result.warnings
                    )
                
                # Step 2: Create field instance
                field = Field.objects.create(
                    pipeline=self.pipeline,
                    name=field_config['name'],
                    display_name=field_config.get('display_name', field_config['name']),
                    field_type=field_config['field_type'],
                    field_config=field_config.get('field_config', {}),
                    storage_constraints=field_config.get('storage_constraints', {}),
                    business_rules=field_config.get('business_rules', {}),
                    form_validation_rules=field_config.get('form_validation_rules', {}),
                    is_ai_field=field_config.get('is_ai_field', False),
                    ai_config=field_config.get('ai_config', {}),
                    created_by=user
                )
                
                # Step 3: Create audit log
                self._create_audit_log(
                    user=user,
                    action='field_created',
                    field=field,
                    operation_id=operation_id,
                    changes={
                        'field_config': field_config,
                        'created_at': field.created_at.isoformat()
                    }
                )
                
                # Step 4: Migrate existing records to include new field
                migration_result = None
                records_migrated = 0
                
                # Check if there are existing records that need the new field added
                existing_records_count = self.pipeline.records.filter(is_deleted=False).count()
                
                if existing_records_count > 0:
                    logger.info(f"[{operation_id}] Migrating {existing_records_count} existing records to include new field: {field.slug}")
                    
                    # Use DataMigrator to add new field to existing records
                    migration_result = self._migrate_new_field_to_existing_records(
                        field, field_config, operation_id
                    )
                    
                    if not migration_result.success:
                        # Rollback field creation if migration failed
                        field.delete()
                        raise Exception(f"Migration failed: {'; '.join(migration_result.errors)}")
                    
                    records_migrated = migration_result.records_migrated
                    logger.info(f"[{operation_id}] Successfully migrated {records_migrated} records")
                else:
                    logger.info(f"[{operation_id}] No existing records to migrate")
                
                # Step 5: Update pipeline schema
                self._update_pipeline_schema()
                
                logger.info(f"[{operation_id}] Field created successfully: {field.name} (slug: {field.slug})")
                
                return FieldOperationResult(
                    success=True,
                    field=field,
                    operation_id=operation_id,
                    warnings=migration_result.warnings if migration_result else [],
                    metadata={
                        'operation_type': 'create',
                        'field_slug': field.slug,
                        'field_type': field.field_type,
                        'existing_records_migrated': records_migrated,
                        'migration_result': migration_result.to_dict() if migration_result else None
                    }
                )
                
        except Exception as e:
            logger.error(f"[{operation_id}] Field creation failed: {str(e)}")
            return FieldOperationResult(
                success=False,
                operation_id=operation_id,
                errors=[f"Field creation failed: {str(e)}"]
            )
    
    def update_field(self, field_id: int, changes: Dict[str, Any], user: User) -> FieldOperationResult:
        """
        Update existing field with automatic migration detection and execution
        
        Args:
            field_id: ID of field to update
            changes: Dictionary of changes to apply
            user: User performing the operation
            
        Returns:
            FieldOperationResult with success status and migration details
        """
        operation_id = self._generate_operation_id()
        logger.info(f"[{operation_id}] Starting field update: field_id={field_id}")
        
        try:
            with transaction.atomic():
                # Step 1: Get and lock field for update
                try:
                    field = Field.objects.select_for_update().get(
                        id=field_id, 
                        pipeline=self.pipeline,
                        is_deleted=False
                    )
                except Field.DoesNotExist:
                    return FieldOperationResult(
                        success=False,
                        operation_id=operation_id,
                        errors=["Field not found or is deleted"]
                    )
                
                # Step 2: Capture original state using FieldStateManager
                if not self.state_manager.capture_field_state(field.id, operation_id):
                    return FieldOperationResult(
                        success=False,
                        operation_id=operation_id,
                        errors=["Failed to capture field state for change tracking"]
                    )
                
                original_state = self.state_manager.get_field_state(field.id, operation_id)
                if not original_state:
                    return FieldOperationResult(
                        success=False,
                        operation_id=operation_id,
                        errors=["Failed to retrieve field state for change tracking"]
                    )
                
                # Step 3: Validate field changes using FieldValidator
                validation_result = self.validator.validate_field_update(field, changes)
                if not validation_result.valid:
                    return FieldOperationResult(
                        success=False,
                        operation_id=operation_id,
                        errors=validation_result.errors,
                        warnings=validation_result.warnings
                    )
                
                # Step 4: Apply changes to field
                self._apply_field_changes(field, changes, user)
                
                # Step 5: Detect if migration is required using FieldStateManager
                change_analysis = self.state_manager.get_field_changes(field.id, field, operation_id)
                
                migration_result = None
                if change_analysis and change_analysis['requires_migration']:
                    logger.info(f"[{operation_id}] Migration required: {change_analysis['migration_types']}")
                    
                    # Execute migration using DataMigrator
                    migration_result = self.migrator.migrate_field_data(
                        field, original_state['original_config'], change_analysis, operation_id
                    )
                    
                    if not migration_result.success:
                        # Rollback field changes if migration failed
                        self._rollback_field_changes(field, original_state['original_config'])
                        raise Exception(f"Migration failed: {'; '.join(migration_result.errors)}")
                
                # Step 6: Create audit log
                self._create_audit_log(
                    user=user,
                    action='field_updated',
                    field=field,
                    operation_id=operation_id,
                    changes={
                        'changes_applied': changes,
                        'original_state': original_state,
                        'migration_required': change_analysis['requires_migration'] if change_analysis else False,
                        'migration_types': change_analysis['migration_types'] if change_analysis else [],
                        'migration_success': migration_result.success if migration_result else None,
                        'updated_at': timezone.now().isoformat()
                    }
                )
                
                # Step 7: Update pipeline schema
                self._update_pipeline_schema()
                
                # Step 8: Clean up operation state
                self.state_manager.cleanup_operation_state(operation_id)
                
                logger.info(f"[{operation_id}] Field update completed successfully")
                
                return FieldOperationResult(
                    success=True,
                    field=field,
                    operation_id=operation_id,
                    warnings=validation_result.warnings + (migration_result.warnings if migration_result else []),
                    metadata={
                        'operation_type': 'update',
                        'changes_applied': list(changes.keys()),
                        'migration_required': change_analysis['requires_migration'] if change_analysis else False,
                        'migration_types': change_analysis['migration_types'] if change_analysis else [],
                        'migration_result': migration_result.to_dict() if migration_result else None
                    }
                )
                
        except Exception as e:
            logger.error(f"[{operation_id}] Field update failed: {str(e)}")
            return FieldOperationResult(
                success=False,
                operation_id=operation_id,
                errors=[f"Field update failed: {str(e)}"]
            )
    
    def delete_field(self, field_id: int, user: User, hard_delete: bool = False) -> FieldOperationResult:
        """
        Delete field with proper cleanup and validation
        
        Args:
            field_id: ID of field to delete
            user: User performing the operation
            hard_delete: Whether to perform hard deletion (default: soft delete)
            
        Returns:
            FieldOperationResult with success status and deletion details
        """
        operation_id = self._generate_operation_id()
        logger.info(f"[{operation_id}] Starting field deletion: field_id={field_id}, hard_delete={hard_delete}")
        
        try:
            with transaction.atomic():
                # Step 1: Get and lock field
                try:
                    if hard_delete:
                        # For hard delete, include soft-deleted fields
                        field = Field.objects.with_deleted().select_for_update().get(
                            id=field_id, pipeline=self.pipeline
                        )
                    else:
                        # For soft delete, only active fields
                        field = Field.objects.select_for_update().get(
                            id=field_id, pipeline=self.pipeline, is_deleted=False
                        )
                except Field.DoesNotExist:
                    return FieldOperationResult(
                        success=False,
                        operation_id=operation_id,
                        errors=["Field not found or already deleted"]
                    )
                
                # Step 2: Validate deletion using FieldValidator
                validation_result = self.validator.validate_field_deletion(field, hard_delete)
                if not validation_result.valid:
                    return FieldOperationResult(
                        success=False,
                        operation_id=operation_id,
                        errors=validation_result.errors,
                        warnings=validation_result.warnings
                    )
                
                # Step 3: Perform deletion
                deletion_metadata = {}
                
                if hard_delete:
                    # Hard deletion - permanent removal
                    field_slug = field.slug
                    field_name = field.name
                    
                    # Queue cleanup of orphaned data
                    deletion_metadata['orphaned_data_cleanup_queued'] = True
                    
                    # Delete the field
                    field.delete()  # This will trigger cleanup signals
                    
                    deletion_metadata['deletion_type'] = 'hard'
                    deletion_metadata['field_slug'] = field_slug
                    deletion_metadata['field_name'] = field_name
                    
                else:
                    # Soft deletion - direct update to avoid circular dependency
                    from django.utils import timezone
                    field.is_deleted = True
                    field.deleted_at = timezone.now()
                    field.deleted_by = user
                    field.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
                    
                    deletion_metadata['deletion_type'] = 'soft'
                    deletion_metadata['hard_delete_scheduled'] = field.scheduled_for_hard_delete
                
                # Step 4: Create audit log
                self._create_audit_log(
                    user=user,
                    action='field_deleted' if not hard_delete else 'field_hard_deleted',
                    field=field if not hard_delete else None,  # Field might be deleted for hard delete
                    operation_id=operation_id,
                    changes={
                        'deletion_type': deletion_metadata['deletion_type'],
                        'hard_delete': hard_delete,
                        'field_slug': field.slug if not hard_delete else deletion_metadata.get('field_slug'),
                        'field_name': field.name if not hard_delete else deletion_metadata.get('field_name'),
                        'deleted_at': timezone.now().isoformat(),
                        **deletion_metadata
                    }
                )
                
                # Step 5: Update pipeline schema
                self._update_pipeline_schema()
                
                logger.info(f"[{operation_id}] Field deletion completed: {deletion_metadata['deletion_type']}")
                
                return FieldOperationResult(
                    success=True,
                    field=field if not hard_delete else None,
                    operation_id=operation_id,
                    warnings=validation_result.warnings,
                    metadata={
                        'operation_type': 'delete',
                        **deletion_metadata
                    }
                )
                
        except Exception as e:
            logger.error(f"[{operation_id}] Field deletion failed: {str(e)}")
            return FieldOperationResult(
                success=False,
                operation_id=operation_id,
                errors=[f"Field deletion failed: {str(e)}"]
            )
    
    def restore_field(self, field_id: int, user: User) -> FieldOperationResult:
        """
        Restore soft-deleted field with validation
        
        Args:
            field_id: ID of field to restore
            user: User performing the operation
            
        Returns:
            FieldOperationResult with success status and restoration details
        """
        operation_id = self._generate_operation_id()
        logger.info(f"[{operation_id}] Starting field restoration: field_id={field_id}")
        
        try:
            with transaction.atomic():
                # Step 1: Get soft-deleted field
                try:
                    field = Field.objects.with_deleted().select_for_update().get(
                        id=field_id, 
                        pipeline=self.pipeline,
                        is_deleted=True
                    )
                except Field.DoesNotExist:
                    return FieldOperationResult(
                        success=False,
                        operation_id=operation_id,
                        errors=["Field not found or not deleted"]
                    )
                
                # Step 2: Validate restoration using FieldValidator
                validation_result = self.validator.validate_field_restoration(field)
                if not validation_result.valid:
                    return FieldOperationResult(
                        success=False,
                        operation_id=operation_id,
                        errors=validation_result.errors,
                        warnings=validation_result.warnings
                    )
                
                # Step 3: Restore field - direct update to avoid circular dependency
                field.is_deleted = False
                field.deleted_at = None 
                field.deleted_by = None
                field.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
                
                # Step 4: Create audit log
                self._create_audit_log(
                    user=user,
                    action='field_restored',
                    field=field,
                    operation_id=operation_id,
                    changes={
                        'field_slug': field.slug,
                        'field_name': field.name,
                        'restored_at': timezone.now().isoformat(),
                        'was_deleted_at': field.deleted_at.isoformat() if field.deleted_at else None
                    }
                )
                
                # Step 5: Update pipeline schema
                self._update_pipeline_schema()
                
                logger.info(f"[{operation_id}] Field restoration completed: {field.name}")
                
                return FieldOperationResult(
                    success=True,
                    field=field,
                    operation_id=operation_id,
                    warnings=validation_result.warnings,
                    metadata={
                        'operation_type': 'restore',
                        'field_slug': field.slug,
                        'restored_at': timezone.now().isoformat()
                    }
                )
                
        except Exception as e:
            logger.error(f"[{operation_id}] Field restoration failed: {str(e)}")
            return FieldOperationResult(
                success=False,
                operation_id=operation_id,
                errors=[f"Field restoration failed: {str(e)}"]
            )
    
    # =============================================================================
    # INTERNAL COORDINATION METHODS - Private methods for operation coordination
    # =============================================================================
    
    def _migrate_new_field_to_existing_records(self, field: Field, field_config: Dict[str, Any], operation_id: str):
        """
        Migrate existing records to include new field with default values
        
        Args:
            field: Newly created field instance
            field_config: Field configuration used for creation
            operation_id: Operation ID for tracking
            
        Returns:
            MigrationResult with migration details
        """
        from .migration.data_migrator import MigrationResult
        import time
        
        start_time = time.time()
        
        try:
            # Get all active records in the pipeline
            records = self.pipeline.records.filter(is_deleted=False)
            total_records = records.count()
            
            if total_records == 0:
                return MigrationResult(
                    success=True,
                    records_processed=0,
                    records_migrated=0,
                    processing_time_seconds=0.0,
                    metadata={'operation_id': operation_id}
                )
            
            # Determine default value for the new field
            default_value = self._get_field_default_value(field, field_config)
            
            logger.info(f"[{operation_id}] Adding field '{field.slug}' with default value '{default_value}' to {total_records} records")
            
            # Migrate records in batches for performance
            batch_size = 100
            migrated_count = 0
            failed_count = 0
            errors = []
            
            for batch_start in range(0, total_records, batch_size):
                batch_records = records[batch_start:batch_start + batch_size]
                
                for record in batch_records:
                    try:
                        # Only add field if it doesn't already exist
                        if field.slug not in (record.data or {}):
                            # Add new field with default value
                            if record.data is None:
                                record.data = {}
                            
                            record.data[field.slug] = default_value
                            record._skip_broadcast = True  # Prevent real-time broadcasts during migration
                            record.save(update_fields=['data'])
                            migrated_count += 1
                        
                    except Exception as record_error:
                        failed_count += 1
                        errors.append(f"Record {record.id}: {str(record_error)}")
                        logger.error(f"[{operation_id}] Failed to migrate record {record.id}: {record_error}")
            
            processing_time = time.time() - start_time
            
            success = failed_count == 0
            
            logger.info(f"[{operation_id}] Field migration completed: {migrated_count} migrated, {failed_count} failed")
            
            return MigrationResult(
                success=success,
                records_processed=total_records,
                records_migrated=migrated_count,
                records_failed=failed_count,
                errors=errors[:10],  # Limit errors to prevent memory issues
                processing_time_seconds=processing_time,
                metadata={
                    'operation_id': operation_id,
                    'field_slug': field.slug,
                    'default_value': default_value,
                    'batch_size': batch_size
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"[{operation_id}] Field migration failed: {str(e)}")
            
            return MigrationResult(
                success=False,
                records_processed=0,
                records_migrated=0,
                errors=[f"Migration failed: {str(e)}"],
                processing_time_seconds=processing_time,
                metadata={'operation_id': operation_id}
            )
    
    def _get_field_default_value(self, field: Field, field_config: Dict[str, Any]):
        """
        Determine appropriate default value for new field based on field type
        
        Args:
            field: Field instance
            field_config: Field configuration
            
        Returns:
            Appropriate default value for the field type
        """
        # Check if explicit default value is provided in field config
        if 'default_value' in field_config:
            return field_config['default_value']
        
        # Check field-specific config for default
        if field.field_config and 'default_value' in field.field_config:
            return field.field_config['default_value']
        
        # Return type-appropriate default values
        field_type = field.field_type
        
        if field_type in ['text', 'textarea', 'rich_text', 'email', 'phone', 'url']:
            return ""
        elif field_type in ['number', 'decimal']:
            return None  # Numeric fields should be null rather than 0
        elif field_type == 'boolean':
            return False
        elif field_type == 'date':
            return None  # Date fields should be null
        elif field_type in ['select']:
            return None  # No default selection
        elif field_type in ['multiselect', 'tags']:
            return []  # Empty array for multi-value fields
        elif field_type == 'file':
            return None  # No default file
        elif field_type == 'ai_generated':
            return None  # AI fields start null until processed
        elif field_type in ['computed', 'formula']:
            return None  # Computed fields calculated separately
        else:
            return None  # Safe default for unknown types
    
    def _apply_field_changes(self, field: Field, changes: Dict[str, Any], user: User):
        """Apply changes to field instance"""
        for key, value in changes.items():
            if hasattr(field, key):
                setattr(field, key, value)
        
        field.updated_by = user
        field.save()
    
    
    def _rollback_field_changes(self, field: Field, original_state: Dict[str, Any]):
        """Rollback field changes if migration fails"""
        for key, value in original_state.items():
            if hasattr(field, key):
                setattr(field, key, value)
        field.save()
    
    def _update_pipeline_schema(self):
        """Update pipeline field schema cache"""
        self.pipeline._update_field_schema()
        self.pipeline.save(update_fields=['field_schema'])
    
    # =============================================================================
    # SIGNAL INTEGRATION - Methods called from simplified signal handlers
    # =============================================================================
    
    def handle_field_save_signal(self, field: Field, created: bool):
        """Handle field save signal - called from simplified signal handlers"""
        if created:
            logger.info(f"New field created via signal: {field.slug}")
            # Additional post-creation logic can go here
        else:
            logger.info(f"Field updated via signal: {field.slug}")
            # Additional post-update logic can go here


# =============================================================================
# FACTORY FUNCTIONS - Convenient access to FieldOperationManager instances
# =============================================================================

def get_field_operation_manager(pipeline: Pipeline) -> FieldOperationManager:
    """Get FieldOperationManager instance for a pipeline"""
    return FieldOperationManager(pipeline)


def get_field_operation_manager_by_field_id(field_id: int) -> FieldOperationManager:
    """Get FieldOperationManager instance by field ID"""
    field = Field.objects.select_related('pipeline').get(id=field_id)
    return FieldOperationManager(field.pipeline)