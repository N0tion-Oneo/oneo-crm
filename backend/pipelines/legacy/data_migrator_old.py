"""
🔴 DEPRECATED - DO NOT USE 🔴
Unified Data Migration Engine
Consolidates data transformation logic from migrator.py into single system
Handles all field change types: renames, type changes, constraint updates

MOVED TO: pipelines/validation/data_migrator.py

This file is kept for reference only. All new imports should use:
from pipelines.validation import DataMigrator, MigrationResult

Date moved: 2025-01-10
Reason: Validation system reorganization for better architecture
"""
import logging
from typing import Dict, Any, List, Optional, Tuple, Callable
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


class MigrationResult:
    """Standardized migration result object"""
    
    def __init__(self, success: bool, records_processed: int = 0, records_migrated: int = 0,
                 records_failed: int = 0, errors: List[str] = None, warnings: List[str] = None,
                 processing_time_seconds: float = 0.0, metadata: Dict[str, Any] = None):
        self.success = success
        self.records_processed = records_processed
        self.records_migrated = records_migrated
        self.records_failed = records_failed
        self.errors = errors or []
        self.warnings = warnings or []
        self.processing_time_seconds = processing_time_seconds
        self.metadata = metadata or {}
        self.timestamp = timezone.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for API responses"""
        return {
            'success': self.success,
            'records_processed': self.records_processed,
            'records_migrated': self.records_migrated,
            'records_failed': self.records_failed,
            'errors': self.errors,
            'warnings': self.warnings,
            'processing_time_seconds': self.processing_time_seconds,
            'processing_time_minutes': round(self.processing_time_seconds / 60, 2),
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


class DataMigrator:
    """
    Unified data migration engine for all field changes
    
    Replaces FieldSchemaMigrator from migrator.py with cleaner architecture
    Handles field renames, type changes, constraint updates with single system
    """
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.progress_callbacks = []
    
    def add_progress_callback(self, callback: Callable[[int, int, str], None]):
        """Add callback for migration progress updates"""
        self.progress_callbacks.append(callback)
    
    def _notify_progress(self, processed: int, total: int, message: str):
        """Notify all progress callbacks"""
        for callback in self.progress_callbacks:
            try:
                callback(processed, total, message)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
    
    # =============================================================================
    # MAIN MIGRATION METHODS - Single entry points for all migration types
    # =============================================================================
    
    def migrate_field_data(self, field, original_state: Dict[str, Any], 
                          change_analysis: Dict[str, Any], operation_id: str,
                          batch_size: int = 100, dry_run: bool = False) -> MigrationResult:
        """
        Unified migration method for all field change types
        
        Args:
            field: Field instance after changes applied
            original_state: Field state before changes  
            change_analysis: Analysis of what changed and migration requirements
            operation_id: Unique operation identifier for logging
            batch_size: Number of records to process per batch
            dry_run: If True, don't actually modify records
            
        Returns:
            MigrationResult with detailed outcome
        """
        start_time = timezone.now()
        logger.info(f"[{operation_id}] Starting data migration: {change_analysis['migration_types']}")
        
        try:
            with transaction.atomic():
                # Step 1: Analyze migration requirements
                migration_plan = self._create_migration_plan(field, original_state, change_analysis)
                
                if not migration_plan['records_to_migrate']:
                    logger.info(f"[{operation_id}] No records to migrate")
                    return MigrationResult(
                        success=True,
                        metadata={'migration_plan': migration_plan, 'reason': 'no_records_to_migrate'}
                    )
                
                # Step 2: Execute migration based on change types
                migration_result = None
                
                for migration_type in change_analysis['migration_types']:
                    if migration_type == 'field_rename':
                        migration_result = self._migrate_field_rename(
                            field, original_state, migration_plan, operation_id, batch_size, dry_run
                        )
                    elif migration_type == 'type_change':
                        migration_result = self._migrate_field_type_change(
                            field, original_state, migration_plan, operation_id, batch_size, dry_run
                        )
                    elif migration_type == 'constraint_change':
                        migration_result = self._migrate_constraint_changes(
                            field, original_state, migration_plan, operation_id, batch_size, dry_run
                        )
                    elif migration_type == 'config_change':
                        migration_result = self._migrate_config_changes(
                            field, original_state, migration_plan, operation_id, batch_size, dry_run
                        )
                    
                    if migration_result and not migration_result.success:
                        # Stop on first failure
                        break
                
                # Step 3: Calculate processing time and finalize result
                end_time = timezone.now()
                processing_time = (end_time - start_time).total_seconds()
                
                if migration_result:
                    migration_result.processing_time_seconds = processing_time
                    migration_result.metadata.update({
                        'migration_plan': migration_plan,
                        'change_analysis': change_analysis,
                        'operation_id': operation_id,
                        'dry_run': dry_run
                    })
                    
                    logger.info(f"[{operation_id}] Migration completed: success={migration_result.success}, "
                              f"processed={migration_result.records_processed}, time={processing_time:.2f}s")
                    
                    return migration_result
                else:
                    logger.warning(f"[{operation_id}] No migration handler for types: {change_analysis['migration_types']}")
                    return MigrationResult(
                        success=False,
                        errors=[f"No migration handler for types: {change_analysis['migration_types']}"],
                        processing_time_seconds=processing_time
                    )
                
                # If dry run, rollback transaction
                if dry_run:
                    transaction.set_rollback(True)
                
        except Exception as e:
            end_time = timezone.now()
            processing_time = (end_time - start_time).total_seconds()
            logger.error(f"[{operation_id}] Migration failed: {str(e)}")
            return MigrationResult(
                success=False,
                errors=[f"Migration failed: {str(e)}"],
                processing_time_seconds=processing_time
            )
    
    def generate_migration_preview(self, field, original_state: Dict[str, Any],
                                  change_analysis: Dict[str, Any], preview_limit: int = 10) -> Dict[str, Any]:
        """
        Generate detailed migration preview with sample transformations
        
        Args:
            field: Field instance after changes applied
            original_state: Field state before changes
            change_analysis: Analysis of what changed
            preview_limit: Number of sample records to show
            
        Returns:
            Dict with preview details and transformation samples
        """
        preview_result = {
            'field_info': {
                'name': field.name,
                'current_type': field.field_type,
                'original_type': original_state.get('field_type', field.field_type),
                'current_slug': field.slug,
                'original_slug': original_state.get('slug', field.slug)
            },
            'sample_transformations': [],
            'transformation_summary': {},
            'compatibility_analysis': {},
            'risk_assessment': {}
        }
        
        try:
            from ..models import Record
            
            # Determine which field slug to search for in existing data
            search_slug = original_state.get('slug', field.slug)
            
            # Get sample records with data for this field
            sample_records = Record.objects.filter(
                pipeline=self.pipeline,
                is_deleted=False,
                data__has_key=search_slug
            ).exclude(
                data__isnull=True
            ).order_by('-updated_at')[:preview_limit]
            
            if not sample_records.exists():
                preview_result['message'] = 'No sample data available for preview'
                return preview_result
            
            # Analyze each sample record
            successful_transformations = 0
            failed_transformations = 0
            value_types_seen = set()
            
            for record in sample_records:
                current_value = record.data.get(search_slug)
                
                try:
                    # Simulate the transformation based on migration types
                    transformed_value = self._simulate_field_transformation(
                        current_value, original_state, field, change_analysis
                    )
                    
                    transformation = {
                        'record_id': record.id,
                        'record_title': record.title or f"Record {record.id}",
                        'current_value': current_value,
                        'current_type': type(current_value).__name__,
                        'transformed_value': transformed_value,
                        'transformed_type': type(transformed_value).__name__,
                        'success': True,
                        'data_preserved': self._assess_data_preservation(current_value, transformed_value),
                        'warnings': []
                    }
                    
                    successful_transformations += 1
                    
                except Exception as e:
                    transformation = {
                        'record_id': record.id,
                        'record_title': record.title or f"Record {record.id}",
                        'current_value': current_value,
                        'current_type': type(current_value).__name__,
                        'transformed_value': None,
                        'transformed_type': 'None',
                        'success': False,
                        'error': str(e),
                        'warnings': ['Transformation failed']
                    }
                    
                    failed_transformations += 1
                
                preview_result['sample_transformations'].append(transformation)
                value_types_seen.add(type(current_value).__name__)
            
            # Generate transformation summary
            total_samples = len(sample_records)
            preview_result['transformation_summary'] = {
                'total_samples': total_samples,
                'successful_transformations': successful_transformations,
                'failed_transformations': failed_transformations,
                'success_rate': (successful_transformations / total_samples) * 100 if total_samples > 0 else 0,
                'data_types_encountered': list(value_types_seen)
            }
            
            # Compatibility analysis
            preview_result['compatibility_analysis'] = self._analyze_field_compatibility(
                original_state, field, preview_result['sample_transformations']
            )
            
            # Risk assessment
            preview_result['risk_assessment'] = self._assess_migration_risk(
                preview_result['transformation_summary'],
                preview_result['compatibility_analysis'],
                change_analysis
            )
            
        except Exception as e:
            preview_result['error'] = f'Preview generation failed: {str(e)}'
            logger.error(f"Migration preview failed: {str(e)}")
        
        return preview_result
    
    # =============================================================================
    # SPECIFIC MIGRATION HANDLERS - Handlers for different change types
    # =============================================================================
    
    def _migrate_field_rename(self, field, original_state: Dict[str, Any], 
                             migration_plan: Dict[str, Any], operation_id: str,
                             batch_size: int, dry_run: bool) -> MigrationResult:
        """Handle field rename migration - move data from old slug to new slug"""
        logger.info(f"[{operation_id}] Executing field rename migration: {original_state['slug']} → {field.slug}")
        
        from ..models import Record
        
        records_to_migrate = migration_plan['records_to_migrate']
        total_records = len(records_to_migrate)
        processed = 0
        migrated = 0
        failed = 0
        errors = []
        warnings = []
        
        old_slug = original_state['slug']
        new_slug = field.slug
        
        try:
            # Process records in batches
            for batch_start in range(0, total_records, batch_size):
                batch_end = min(batch_start + batch_size, total_records)
                batch_record_ids = records_to_migrate[batch_start:batch_end]
                
                batch_records = Record.objects.filter(id__in=batch_record_ids)
                
                for record in batch_records:
                    processed += 1
                    
                    try:
                        # Move data from old slug to new slug
                        if old_slug in record.data and new_slug not in record.data:
                            if not dry_run:
                                record.data[new_slug] = record.data.pop(old_slug)
                                record._skip_broadcast = True  # Prevent real-time broadcasts during migration
                                record.save(update_fields=['data', 'updated_at'])
                            
                            migrated += 1
                        
                        # Notify progress
                        self._notify_progress(processed, total_records, f"Renaming field data: {processed}/{total_records}")
                        
                    except Exception as e:
                        failed += 1
                        error_msg = f"Record {record.id}: Failed to rename field: {str(e)}"
                        errors.append(error_msg)
                        logger.warning(error_msg)
                
                # Log batch progress
                if processed % 1000 == 0 or batch_end >= total_records:
                    logger.info(f"[{operation_id}] Rename progress: {processed}/{total_records} records processed")
            
            return MigrationResult(
                success=failed == 0,
                records_processed=processed,
                records_migrated=migrated,
                records_failed=failed,
                errors=errors,
                warnings=warnings,
                metadata={
                    'migration_type': 'field_rename',
                    'old_slug': old_slug,
                    'new_slug': new_slug
                }
            )
            
        except Exception as e:
            return MigrationResult(
                success=False,
                records_processed=processed,
                records_migrated=migrated,
                records_failed=failed + 1,
                errors=errors + [f"Rename migration failed: {str(e)}"]
            )
    
    def _migrate_field_type_change(self, field, original_state: Dict[str, Any],
                                  migration_plan: Dict[str, Any], operation_id: str,
                                  batch_size: int, dry_run: bool) -> MigrationResult:
        """Handle field type change migration - transform data to new type"""
        logger.info(f"[{operation_id}] Executing type change migration: {original_state['field_type']} → {field.field_type}")
        
        from ..models import Record
        
        records_to_migrate = migration_plan['records_to_migrate']
        total_records = len(records_to_migrate)
        processed = 0
        migrated = 0
        failed = 0
        errors = []
        warnings = []
        
        old_type = original_state['field_type']
        new_type = field.field_type
        field_slug = field.slug
        
        try:
            # Process records in batches
            for batch_start in range(0, total_records, batch_size):
                batch_end = min(batch_start + batch_size, total_records)
                batch_record_ids = records_to_migrate[batch_start:batch_end]
                
                batch_records = Record.objects.filter(id__in=batch_record_ids)
                
                for record in batch_records:
                    processed += 1
                    
                    try:
                        old_value = record.data.get(field_slug)
                        if old_value is None:
                            continue
                        
                        # Transform the value to new type
                        transformed_value = self._convert_value_to_new_type(old_value, old_type, new_type)
                        
                        if transformed_value is not None:
                            if not dry_run:
                                record.data[field_slug] = transformed_value
                                record._skip_broadcast = True
                                record.save(update_fields=['data', 'updated_at'])
                            
                            migrated += 1
                        else:
                            warnings.append(f"Record {record.id}: Could not convert value {old_value}")
                        
                        # Notify progress
                        self._notify_progress(processed, total_records, f"Converting field data: {processed}/{total_records}")
                        
                    except Exception as e:
                        failed += 1
                        error_msg = f"Record {record.id}: Failed to convert value: {str(e)}"
                        errors.append(error_msg)
                        logger.warning(error_msg)
                
                # Log batch progress
                if processed % 1000 == 0 or batch_end >= total_records:
                    logger.info(f"[{operation_id}] Type change progress: {processed}/{total_records} records processed")
            
            return MigrationResult(
                success=failed == 0,
                records_processed=processed,
                records_migrated=migrated,
                records_failed=failed,
                errors=errors,
                warnings=warnings,
                metadata={
                    'migration_type': 'type_change',
                    'old_type': old_type,
                    'new_type': new_type
                }
            )
            
        except Exception as e:
            return MigrationResult(
                success=False,
                records_processed=processed,
                records_migrated=migrated,
                records_failed=failed + 1,
                errors=errors + [f"Type change migration failed: {str(e)}"]
            )
    
    def _migrate_constraint_changes(self, field, original_state: Dict[str, Any],
                                   migration_plan: Dict[str, Any], operation_id: str,
                                   batch_size: int, dry_run: bool) -> MigrationResult:
        """Handle storage constraint changes - validate and clean data"""
        logger.info(f"[{operation_id}] Executing constraint change migration")
        
        # For now, return success - constraint validation will be added later
        return MigrationResult(
            success=True,
            records_processed=0,
            records_migrated=0,
            records_failed=0,
            metadata={
                'migration_type': 'constraint_change',
                'note': 'Constraint validation to be implemented'
            }
        )
    
    def _migrate_config_changes(self, field, original_state: Dict[str, Any],
                               migration_plan: Dict[str, Any], operation_id: str,
                               batch_size: int, dry_run: bool) -> MigrationResult:
        """Handle field configuration changes"""
        logger.info(f"[{operation_id}] Executing config change migration")
        
        # For now, return success - config-specific migrations will be added later
        return MigrationResult(
            success=True,
            records_processed=0,
            records_migrated=0,
            records_failed=0,
            metadata={
                'migration_type': 'config_change',
                'note': 'Config-specific migrations to be implemented'
            }
        )
    
    # =============================================================================
    # MIGRATION PLANNING AND ANALYSIS
    # =============================================================================
    
    def _create_migration_plan(self, field, original_state: Dict[str, Any], 
                              change_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create migration execution plan"""
        from ..models import Record
        
        # Determine which field slug to search for in existing data
        search_slug = original_state.get('slug', field.slug)
        
        # Get records that need migration
        records_to_migrate = list(
            Record.objects.filter(
                pipeline=self.pipeline,
                is_deleted=False,
                data__has_key=search_slug
            ).values_list('id', flat=True)
        )
        
        plan = {
            'records_to_migrate': records_to_migrate,
            'total_records': len(records_to_migrate),
            'search_slug': search_slug,
            'target_slug': field.slug,
            'migration_types': change_analysis['migration_types'],
            'risk_level': change_analysis['risk_level'],
            'estimated_time_minutes': max(1, len(records_to_migrate) / 1000)  # Rough estimate
        }
        
        return plan
    
    def _simulate_field_transformation(self, value: Any, original_state: Dict[str, Any],
                                      field, change_analysis: Dict[str, Any]) -> Any:
        """Simulate how a value would be transformed"""
        if value is None:
            return None
        
        # Handle different migration types
        if 'field_rename' in change_analysis['migration_types']:
            # Rename doesn't change the value, just the key
            return value
        
        if 'type_change' in change_analysis['migration_types']:
            old_type = original_state['field_type']
            new_type = field.field_type
            return self._convert_value_to_new_type(value, old_type, new_type)
        
        # Default: return unchanged
        return value
    
    def _convert_value_to_new_type(self, value: Any, old_type: str, new_type: str) -> Any:
        """Convert value from old field type to new field type"""
        if value is None:
            return None
        
        # Same type, no conversion needed
        if old_type == new_type:
            return value
        
        try:
            # String conversions
            if new_type in ['text', 'textarea']:
                return str(value) if value is not None else ""
            
            # Number conversions
            elif new_type == 'number':
                if isinstance(value, (int, float)):
                    return value
                if isinstance(value, str) and value.strip():
                    try:
                        # Try integer first, then float
                        if '.' not in value:
                            return int(value)
                        else:
                            return float(value)
                    except ValueError:
                        return None
                return None
            
            # Boolean conversions
            elif new_type == 'boolean':
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ['true', '1', 'yes', 'on']
                if isinstance(value, (int, float)):
                    return bool(value)
                return False
            
            # Email conversions
            elif new_type == 'email':
                if isinstance(value, str) and '@' in value:
                    return value.lower().strip()
                return None
            
            # URL conversions  
            elif new_type == 'url':
                if isinstance(value, str) and ('http' in value or 'www.' in value):
                    return value.strip()
                return None
            
            # Tags conversions
            elif new_type == 'tags':
                if isinstance(value, str):
                    return [tag.strip() for tag in value.split(',') if tag.strip()]
                if isinstance(value, list):
                    return [str(item) for item in value]
                return [str(value)] if value else []
            
            # Default: try to preserve value as-is
            return value
            
        except Exception as e:
            logger.warning(f"Value conversion failed: {old_type} → {new_type}, value: {value}, error: {e}")
            return None
    
    def _assess_data_preservation(self, original_value: Any, transformed_value: Any) -> str:
        """Assess how well data is preserved in the transformation"""
        if original_value is None and transformed_value is None:
            return 'preserved'
        
        if original_value is None or transformed_value is None:
            return 'partial_loss'
        
        # Compare string representations for rough equivalence
        original_str = str(original_value).strip().lower()
        transformed_str = str(transformed_value).strip().lower()
        
        if original_str == transformed_str:
            return 'preserved'
        elif original_str in transformed_str or transformed_str in original_str:
            return 'partial_preservation'
        else:
            return 'data_changed'
    
    def _analyze_field_compatibility(self, original_state: Dict[str, Any], field,
                                   transformations: List[Dict]) -> Dict[str, Any]:
        """Analyze compatibility between current and target field configurations"""
        if not transformations:
            return {'compatibility_score': 100, 'assessment': 'No data to analyze'}
        
        # Count transformation outcomes
        preserved_count = sum(1 for t in transformations if t.get('data_preserved') == 'preserved')
        partial_count = sum(1 for t in transformations if t.get('data_preserved') == 'partial_preservation')
        changed_count = sum(1 for t in transformations if t.get('data_preserved') == 'data_changed')
        failed_count = sum(1 for t in transformations if not t.get('success'))
        
        total_count = len(transformations)
        
        compatibility_score = 0
        if total_count > 0:
            compatibility_score = (preserved_count + (partial_count * 0.5)) / total_count * 100
        
        # Generate assessment
        if compatibility_score >= 90:
            assessment = 'Excellent compatibility - minimal data changes expected'
        elif compatibility_score >= 70:
            assessment = 'Good compatibility - some data transformation expected'
        elif compatibility_score >= 50:
            assessment = 'Moderate compatibility - significant data changes expected'
        else:
            assessment = 'Poor compatibility - major data transformation required'
        
        return {
            'compatibility_score': round(compatibility_score, 1),
            'data_preservation': {
                'fully_preserved': preserved_count,
                'partially_preserved': partial_count,
                'data_changed': changed_count,
                'transformation_failed': failed_count
            },
            'assessment': assessment
        }
    
    def _assess_migration_risk(self, transformation_summary: Dict, compatibility_analysis: Dict,
                              change_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall migration risk based on analysis results"""
        success_rate = transformation_summary.get('success_rate', 0)
        compatibility_score = compatibility_analysis.get('compatibility_score', 0)
        risk_level = change_analysis.get('risk_level', 'low')
        
        # Calculate overall risk level
        if success_rate >= 95 and compatibility_score >= 90 and risk_level == 'low':
            final_risk = 'low'
            risk_message = 'Migration appears safe with minimal data loss risk'
        elif success_rate >= 80 and compatibility_score >= 70 and risk_level in ['low', 'medium']:
            final_risk = 'medium'
            risk_message = 'Migration has moderate risk - review sample transformations'
        else:
            final_risk = 'high'
            risk_message = 'Migration has high risk of data loss or transformation failures'
        
        # Generate recommendations
        recommendations = []
        
        if final_risk == 'high':
            recommendations.extend([
                'Strongly recommend performing a dry run first',
                'Create a full backup before proceeding',
                'Consider migrating data manually in smaller batches'
            ])
        elif final_risk == 'medium':
            recommendations.extend([
                'Perform a dry run to verify transformations',
                'Create a backup of affected records',
                'Monitor the migration process closely'
            ])
        else:
            recommendations.extend([
                'Migration appears safe to proceed',
                'Consider running during low-usage hours'
            ])
        
        failed_rate = transformation_summary.get('failed_transformations', 0)
        if failed_rate > 0:
            recommendations.append(f'{failed_rate} transformations failed - investigate before proceeding')
        
        return {
            'risk_level': final_risk,
            'risk_message': risk_message,
            'success_rate': success_rate,
            'compatibility_score': compatibility_score,
            'recommendations': recommendations
        }