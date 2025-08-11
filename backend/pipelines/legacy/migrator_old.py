"""
🔴 DEPRECATED - DO NOT USE 🔴
Field Schema Migration Engine
Handles migration of existing record data when field schemas change

MOVED TO: pipelines/validation/data_migrator.py

This file is kept for reference only. All new imports should use:
from pipelines.validation import DataMigrator, MigrationResult

Date moved: 2025-01-10
Reason: Validation system reorganization for better architecture
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from .models import Pipeline, Field, Record
from .field_types import FieldType
from .validation import FieldValidator, validate_record_data

logger = logging.getLogger(__name__)


class FieldSchemaMigrator:
    """Handles migration of existing record data when field schemas change"""
    
    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline
        self.migration_log = []
    
    def analyze_field_change_impact(self, field: Field, new_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze the impact of changing a field configuration"""
        analysis = {
            'field_slug': field.slug,
            'field_name': field.name,
            'total_records': 0,
            'records_with_data': 0,
            'affected_records': 0,
            'migration_required': False,
            'breaking_changes': [],
            'warnings': [],
            'estimated_time_minutes': 0,
            'dependent_fields': []
        }
        
        # Count total records
        total_records = self.pipeline.records.filter(is_deleted=False).count()
        analysis['total_records'] = total_records
        
        # Count records with data for this field
        records_with_data = self.pipeline.records.filter(
            data__has_key=field.slug,
            is_deleted=False
        ).exclude(data__isnull=True).count()
        analysis['records_with_data'] = records_with_data
        
        # If no config change provided, return basic analysis
        if not new_config:
            analysis['affected_records'] = records_with_data
            return analysis
        
        # Analyze configuration changes
        old_config = {
            'field_type': field.field_type,
            'field_config': field.field_config,
            'storage_constraints': field.storage_constraints,
            'business_rules': field.business_rules
        }
        
        changes = self._detect_config_changes(old_config, new_config)
        analysis.update(changes)
        
        # Check dependent fields
        dependent_fields = self._find_dependent_fields(field.slug)
        analysis['dependent_fields'] = dependent_fields
        
        # Estimate migration time
        if analysis['migration_required']:
            # Base time: 1 second per 1000 records
            base_time = max(1, records_with_data / 1000)
            # Add complexity factor for breaking changes
            complexity_factor = 1 + len(analysis['breaking_changes']) * 0.5
            analysis['estimated_time_minutes'] = round(base_time * complexity_factor, 1)
        
        return analysis
    
    def generate_migration_preview(self, field: Field, new_config: Dict[str, Any], 
                                 preview_limit: int = 10) -> Dict[str, Any]:
        """Generate detailed migration preview with sample transformations"""
        
        preview_result = {
            'field_info': {
                'name': field.name,
                'current_type': field.field_type,
                'target_type': new_config.get('field_type', field.field_type),
                'current_config': field.field_config,
                'target_config': new_config.get('field_config', {})
            },
            'sample_transformations': [],
            'transformation_summary': {},
            'compatibility_analysis': {},
            'risk_assessment': {}
        }
        
        try:
            from .models import Record
            
            # Get sample records with data for this field
            sample_records = Record.objects.filter(
                pipeline=self.pipeline,
                is_deleted=False,
                data__has_key=field.slug
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
                current_value = record.data.get(field.slug)
                
                try:
                    # Simulate the transformation
                    transformed_value = self._simulate_field_transformation(
                        current_value, field, new_config
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
            preview_result['transformation_summary'] = {
                'total_samples': len(sample_records),
                'successful_transformations': successful_transformations,
                'failed_transformations': failed_transformations,
                'success_rate': (successful_transformations / len(sample_records)) * 100,
                'data_types_encountered': list(value_types_seen)
            }
            
            # Compatibility analysis
            preview_result['compatibility_analysis'] = self._analyze_field_compatibility(
                field, new_config, preview_result['sample_transformations']
            )
            
            # Risk assessment based on preview results
            preview_result['risk_assessment'] = self._assess_migration_risk(
                preview_result['transformation_summary'],
                preview_result['compatibility_analysis']
            )
            
        except Exception as e:
            preview_result['error'] = f'Preview generation failed: {str(e)}'
        
        return preview_result
    
    def migrate_field_data(self, field: Field, new_config: Dict[str, Any], 
                          batch_size: int = 100, dry_run: bool = False) -> Dict[str, Any]:
        """Migrate existing record data to match new field configuration"""
        
        migration_result = {
            'success': False,
            'records_processed': 0,
            'records_migrated': 0,
            'records_failed': 0,
            'errors': [],
            'warnings': [],
            'dry_run': dry_run
        }
        
        try:
            with transaction.atomic():
                # Get records that have data for this field
                records_to_migrate = self.pipeline.records.filter(
                    data__has_key=field.slug,
                    is_deleted=False
                )
                
                total_records = records_to_migrate.count()
                logger.info(f"Starting field migration for {field.slug}: {total_records} records to process")
                
                # Process records in batches
                processed = 0
                migrated = 0
                failed = 0
                
                for batch_start in range(0, total_records, batch_size):
                    batch_end = min(batch_start + batch_size, total_records)
                    batch_records = records_to_migrate[batch_start:batch_end]
                    
                    for record in batch_records:
                        processed += 1
                        
                        try:
                            old_value = record.data.get(field.slug)
                            if old_value is None:
                                continue
                            
                            # Migrate the field value
                            migration_success, new_value, warnings = self._migrate_field_value(
                                field, old_value, new_config
                            )
                            
                            if migration_success:
                                if not dry_run:
                                    # Update the record with new value
                                    record.data[field.slug] = new_value
                                    record._skip_broadcast = True  # Prevent real-time broadcasts during migration
                                    record.save(update_fields=['data', 'updated_at'])
                                
                                migrated += 1
                                if warnings:
                                    migration_result['warnings'].extend(warnings)
                            else:
                                failed += 1
                                error_msg = f"Record {record.id}: Failed to migrate value {old_value}"
                                migration_result['errors'].append(error_msg)
                                logger.warning(error_msg)
                        
                        except Exception as e:
                            failed += 1
                            error_msg = f"Record {record.id}: Exception during migration: {str(e)}"
                            migration_result['errors'].append(error_msg)
                            logger.error(error_msg)
                    
                    # Log progress
                    if processed % 1000 == 0:
                        logger.info(f"Migration progress: {processed}/{total_records} records processed")
                
                migration_result.update({
                    'success': failed == 0,
                    'records_processed': processed,
                    'records_migrated': migrated,
                    'records_failed': failed
                })
                
                if dry_run:
                    logger.info(f"DRY RUN complete for {field.slug}: {migrated} would be migrated, {failed} would fail")
                else:
                    logger.info(f"Migration complete for {field.slug}: {migrated} migrated, {failed} failed")
                
                # If this is a dry run or there were failures, don't commit
                if dry_run or failed > 0:
                    if dry_run:
                        transaction.set_rollback(True)
                    elif failed > 0:
                        migration_result['success'] = False
                        logger.error(f"Migration failed with {failed} errors - rolling back")
                        transaction.set_rollback(True)
                
        except Exception as e:
            migration_result['success'] = False
            migration_result['errors'].append(f"Migration transaction failed: {str(e)}")
            logger.error(f"Field migration failed for {field.slug}: {str(e)}")
        
        return migration_result
    
    def migrate_pipeline_schema_changes(self, changes: List[Dict[str, Any]], 
                                       batch_size: int = 100) -> Dict[str, Any]:
        """Migrate multiple field changes in a coordinated manner"""
        
        overall_result = {
            'success': False,
            'field_migrations': [],
            'total_records_affected': 0,
            'total_time_minutes': 0,
            'errors': [],
            'warnings': []
        }
        
        start_time = timezone.now()
        
        try:
            with transaction.atomic():
                for change in changes:
                    field_slug = change.get('field_slug')
                    new_config = change.get('new_config')
                    
                    try:
                        field = self.pipeline.fields.get(slug=field_slug)
                        
                        # Perform field migration
                        migration_result = self.migrate_field_data(
                            field, new_config, batch_size, dry_run=False
                        )
                        
                        migration_result['field_slug'] = field_slug
                        overall_result['field_migrations'].append(migration_result)
                        overall_result['total_records_affected'] += migration_result['records_processed']
                        
                        if not migration_result['success']:
                            overall_result['errors'].extend(migration_result['errors'])
                        
                        overall_result['warnings'].extend(migration_result['warnings'])
                        
                    except Field.DoesNotExist:
                        error_msg = f"Field {field_slug} not found"
                        overall_result['errors'].append(error_msg)
                        logger.error(error_msg)
                
                # Calculate total time
                end_time = timezone.now()
                total_time = (end_time - start_time).total_seconds() / 60
                overall_result['total_time_minutes'] = round(total_time, 2)
                
                # Check overall success
                overall_result['success'] = len(overall_result['errors']) == 0
                
                if not overall_result['success']:
                    logger.error("Pipeline schema migration failed - rolling back all changes")
                    transaction.set_rollback(True)
                else:
                    logger.info(f"Pipeline schema migration completed successfully in {total_time:.2f} minutes")
        
        except Exception as e:
            overall_result['success'] = False
            overall_result['errors'].append(f"Pipeline migration failed: {str(e)}")
            logger.error(f"Pipeline schema migration failed: {str(e)}")
        
        return overall_result
    
    def _detect_config_changes(self, old_config: Dict[str, Any], 
                             new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Detect what changes are being made to field configuration"""
        changes = {
            'migration_required': False,
            'breaking_changes': [],
            'warnings': [],
            'affected_records': 0
        }
        
        old_type = old_config.get('field_type')
        new_type = new_config.get('field_type')
        
        # Check for field type changes
        if old_type != new_type:
            changes['migration_required'] = True
            if self._is_breaking_type_change(old_type, new_type):
                changes['breaking_changes'].append(f"Field type change from {old_type} to {new_type}")
            else:
                changes['warnings'].append(f"Field type change from {old_type} to {new_type}")
        
        # Check for constraint changes
        old_constraints = old_config.get('storage_constraints', {})
        new_constraints = new_config.get('storage_constraints', {})
        
        # Check for validation becoming stricter
        if self._constraints_became_stricter(old_constraints, new_constraints):
            changes['migration_required'] = True
            changes['breaking_changes'].append("Storage constraints became stricter")
        
        # Check for field config changes
        old_field_config = old_config.get('field_config', {})
        new_field_config = new_config.get('field_config', {})
        
        if old_field_config != new_field_config:
            changes['warnings'].append("Field configuration changed")
        
        return changes
    
    def _migrate_field_value(self, field: Field, old_value: Any, 
                           new_config: Dict[str, Any]) -> Tuple[bool, Any, List[str]]:
        """Migrate a single field value to new configuration"""
        warnings = []
        
        try:
            new_field_type = FieldType(new_config.get('field_type', field.field_type))
            new_field_config = new_config.get('field_config', field.field_config)
            new_storage_constraints = new_config.get('storage_constraints', field.storage_constraints)
            
            # Create validator for new configuration
            validator = FieldValidator(new_field_type, new_field_config)
            
            # Try to convert the value
            converted_value = self._convert_value_to_new_type(
                old_value, field.field_type, new_field_type.value
            )
            
            # Validate the converted value
            validation_result = validator.validate_storage(converted_value, new_storage_constraints)
            
            if validation_result.is_valid:
                return True, validation_result.cleaned_value, warnings
            else:
                # Try fallback conversions
                fallback_value = self._try_fallback_conversion(old_value, new_field_type)
                if fallback_value is not None:
                    fallback_result = validator.validate_storage(fallback_value, new_storage_constraints)
                    if fallback_result.is_valid:
                        warnings.append(f"Used fallback conversion for value: {old_value} -> {fallback_value}")
                        return True, fallback_result.cleaned_value, warnings
                
                return False, None, [f"Validation failed: {validation_result.errors}"]
        
        except Exception as e:
            return False, None, [f"Migration error: {str(e)}"]
    
    def _convert_value_to_new_type(self, value: Any, old_type: str, new_type: str) -> Any:
        """Convert value from old field type to new field type"""
        
        # Same type, no conversion needed
        if old_type == new_type:
            return value
        
        # String conversions
        if new_type == FieldType.TEXT or new_type == FieldType.TEXTAREA:
            return str(value) if value is not None else ""
        
        # Number conversions
        if new_type == FieldType.NUMBER:
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
                    pass
            return None
        
        # Boolean conversions
        if new_type == FieldType.BOOLEAN:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ['true', '1', 'yes', 'on']
            if isinstance(value, (int, float)):
                return bool(value)
            return False
        
        # Email conversions
        if new_type == FieldType.EMAIL:
            if isinstance(value, str) and '@' in value:
                return value.lower().strip()
            return None
        
        # URL conversions  
        if new_type == FieldType.URL:
            if isinstance(value, str) and ('http' in value or 'www.' in value):
                return value.strip()
            return None
        
        # Default: try to preserve value as-is
        return value
    
    def _try_fallback_conversion(self, value: Any, new_type: FieldType) -> Any:
        """Try fallback conversions when primary conversion fails"""
        
        if new_type == FieldType.TEXT:
            # Everything can become text
            return str(value) if value is not None else ""
        
        if new_type == FieldType.TAGS:
            # Convert various formats to tag list
            if isinstance(value, str):
                return [tag.strip() for tag in value.split(',') if tag.strip()]
            if isinstance(value, list):
                return [str(item) for item in value]
            return [str(value)] if value else []
        
        return None
    
    def _is_breaking_type_change(self, old_type: str, new_type: str) -> bool:
        """Check if type change is potentially breaking"""
        breaking_changes = [
            (FieldType.TEXT, FieldType.NUMBER),
            (FieldType.TEXT, FieldType.EMAIL),
            (FieldType.TEXT, FieldType.URL),
            (FieldType.NUMBER, FieldType.EMAIL),
            (FieldType.BOOLEAN, FieldType.NUMBER),
        ]
        
        return (old_type, new_type) in breaking_changes
    
    def _constraints_became_stricter(self, old_constraints: Dict, new_constraints: Dict) -> bool:
        """Check if storage constraints became stricter"""
        
        # Check max length reduction
        old_max = old_constraints.get('max_storage_length')
        new_max = new_constraints.get('max_storage_length')
        if old_max and new_max and new_max < old_max:
            return True
        
        # Check uniqueness enforcement
        if not old_constraints.get('enforce_uniqueness') and new_constraints.get('enforce_uniqueness'):
            return True
        
        return False
    
    def _find_dependent_fields(self, field_slug: str) -> List[Dict[str, Any]]:
        """Find fields that depend on the given field"""
        dependent_fields = []
        
        # Check business rules dependencies
        fields_with_dependencies = self.pipeline.fields.filter(
            business_rules__conditional_requirements__condition_field=field_slug
        )
        
        for field in fields_with_dependencies:
            dependent_fields.append({
                'field_slug': field.slug,
                'field_name': field.name,
                'dependency_type': 'business_rules'
            })
        
        # Check AI field dependencies
        ai_fields = self.pipeline.fields.filter(
            is_ai_field=True,
            ai_config__trigger_fields__contains=[field_slug]
        )
        
        for field in ai_fields:
            dependent_fields.append({
                'field_slug': field.slug,
                'field_name': field.name,
                'dependency_type': 'ai_trigger'
            })
        
        return dependent_fields
    
    def _simulate_field_transformation(self, value: Any, field: Field, new_config: Dict[str, Any]) -> Any:
        """Simulate transformation of a field value"""
        current_type = field.field_type
        target_type = new_config.get('field_type', current_type)
        
        # If no type change, return the original value
        if current_type == target_type:
            return value
        
        # Use the existing conversion logic
        return self._convert_value_to_new_type(value, current_type, target_type)
    
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
    
    def _analyze_field_compatibility(self, field: Field, new_config: Dict[str, Any], 
                                   transformations: List[Dict]) -> Dict[str, Any]:
        """Analyze compatibility between current and target field configurations"""
        
        current_type = field.field_type
        target_type = new_config.get('field_type', current_type)
        
        # Count transformation outcomes
        preserved_count = sum(1 for t in transformations if t.get('data_preserved') == 'preserved')
        partial_count = sum(1 for t in transformations if t.get('data_preserved') == 'partial_preservation')
        changed_count = sum(1 for t in transformations if t.get('data_preserved') == 'data_changed')
        failed_count = sum(1 for t in transformations if not t.get('success'))
        
        total_count = len(transformations)
        
        compatibility_score = 0
        if total_count > 0:
            compatibility_score = (preserved_count + (partial_count * 0.5)) / total_count * 100
        
        return {
            'compatibility_score': round(compatibility_score, 1),
            'data_preservation': {
                'fully_preserved': preserved_count,
                'partially_preserved': partial_count,
                'data_changed': changed_count,
                'transformation_failed': failed_count
            },
            'assessment': self._get_compatibility_assessment(compatibility_score),
            'recommendations': self._get_compatibility_recommendations(
                current_type, target_type, compatibility_score, failed_count
            )
        }
    
    def _assess_migration_risk(self, transformation_summary: Dict, compatibility_analysis: Dict) -> Dict[str, Any]:
        """Assess overall migration risk based on preview results"""
        
        success_rate = transformation_summary.get('success_rate', 0)
        compatibility_score = compatibility_analysis.get('compatibility_score', 0)
        
        # Calculate risk level
        if success_rate >= 95 and compatibility_score >= 90:
            risk_level = 'low'
            risk_message = 'Migration appears safe with minimal data loss risk'
        elif success_rate >= 80 and compatibility_score >= 70:
            risk_level = 'medium'
            risk_message = 'Migration has moderate risk - review sample transformations'
        else:
            risk_level = 'high'
            risk_message = 'Migration has high risk of data loss or transformation failures'
        
        return {
            'risk_level': risk_level,
            'risk_message': risk_message,
            'success_rate': success_rate,
            'compatibility_score': compatibility_score,
            'recommendations': self._get_risk_recommendations(risk_level, transformation_summary)
        }
    
    def _get_compatibility_assessment(self, score: float) -> str:
        """Get textual assessment of compatibility score"""
        if score >= 90:
            return 'Excellent compatibility - minimal data changes expected'
        elif score >= 70:
            return 'Good compatibility - some data transformation expected'
        elif score >= 50:
            return 'Moderate compatibility - significant data changes expected'
        else:
            return 'Poor compatibility - major data transformation required'
    
    def _get_compatibility_recommendations(self, current_type: str, target_type: str, 
                                         score: float, failed_count: int) -> List[str]:
        """Generate recommendations based on compatibility analysis"""
        recommendations = []
        
        if score < 70:
            recommendations.append('Consider creating a backup of the current field before migration')
            recommendations.append('Review all sample transformations carefully')
        
        if failed_count > 0:
            recommendations.append('Some transformations failed - investigate data quality issues')
            recommendations.append('Consider cleaning data before migration')
        
        if current_type in ['select', 'multiselect'] and target_type in ['text', 'textarea']:
            recommendations.append('Option values will be converted to text - verify formatting')
        
        if current_type in ['number', 'decimal'] and target_type in ['text', 'textarea']:
            recommendations.append('Number formatting may change - review numeric precision')
        
        return recommendations
    
    def _get_risk_recommendations(self, risk_level: str, transformation_summary: Dict) -> List[str]:
        """Generate risk-specific recommendations"""
        recommendations = []
        
        if risk_level == 'high':
            recommendations.extend([
                'Strongly recommend performing a dry run first',
                'Create a full backup before proceeding',
                'Consider migrating data manually in smaller batches',
                'Review and fix data quality issues before migration'
            ])
        elif risk_level == 'medium':
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
        
        return recommendations