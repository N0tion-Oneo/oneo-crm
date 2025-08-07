"""
Consolidated Field Validation System
Moves all validation logic from scattered locations into single unified class
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from django.db.models import Count

logger = logging.getLogger(__name__)


class FieldValidationResult:
    """Standardized validation result"""
    
    def __init__(self, valid: bool, errors: List[str] = None, warnings: List[str] = None, 
                 metadata: Dict[str, Any] = None):
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'valid': self.valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'metadata': self.metadata
        }


class FieldValidator:
    """
    Consolidated field validation logic from migration_validator.py, migrator.py, and signals.py
    Single source of truth for ALL field validation operations
    """
    
    # =============================================================================
    # MIGRATION SAFETY RULES - Moved from migration_validator.py
    # =============================================================================
    
    # Hard-denied migration patterns - these migrations are impossible or too risky
    DENIED_MIGRATIONS = {
        # System/AI field conversions - cannot be migrated due to complex logic
        ('ai_generated', '*'): {
            'reason': 'AI fields cannot be converted to other types',
            'explanation': 'AI-generated fields contain complex processing logic that cannot be migrated. The AI prompts, model configurations, and generated content would be lost.',
            'alternatives': [
                'Create new field with desired type',
                'Keep AI field and add separate field for additional data',
                'Export AI-generated content before creating new field'
            ]
        },
        ('record_data', '*'): {
            'reason': 'System record data fields cannot be changed',
            'explanation': 'Record data fields are system-managed and tied to core functionality. Changing them would break record management features.',
            'alternatives': [
                'Use computed fields for custom record data views',
                'Create new field that references record metadata'
            ]
        },
        
        # Relationship field conversions - contain references to other records
        ('relation', '*'): {
            'reason': 'Relationship fields cannot be converted to other types',
            'explanation': 'Relations contain references to other records that would be permanently lost. The relationship data structure cannot be converted to simple field types.',
            'alternatives': [
                'Export relation data first as CSV/JSON',
                'Create computed field with formatted relationship info',
                'Keep relation field and add new field for additional data'
            ]
        },
        
        # File field conversions - contain binary data and metadata
        ('file', '*'): {
            'reason': 'File fields cannot be migrated to other types',
            'explanation': 'File attachments, metadata, and access permissions would be permanently lost. File data cannot be converted to text or other simple types.',
            'alternatives': [
                'Export files to external storage before conversion',
                'Keep file field and add computed text field with file names',
                'Create new field that references file metadata'
            ]
        },
        
        # Complex structured field conversions
        ('address', '*'): {
            'reason': 'Address fields contain structured data that cannot be converted',
            'explanation': 'Address components (street, city, state, country, postal code) would be lost or improperly merged into a single text field.',
            'alternatives': [
                'Create computed field with formatted address string',
                'Create separate text field for each address component',
                'Export address data before creating replacement fields'
            ]
        },
        
        ('button', '*'): {
            'reason': 'Button fields contain workflow logic that cannot be migrated',
            'explanation': 'Associated workflows, actions, and trigger logic would be broken. Button functionality cannot be preserved in other field types.',
            'alternatives': [
                'Recreate button functionality in new field type',
                'Document button workflows before removal',
                'Create text field with action descriptions'
            ]
        },
        
        # Reverse conversions to complex types - require specific configuration
        ('*', 'ai_generated'): {
            'reason': 'Cannot convert existing fields to AI-generated fields',
            'explanation': 'AI fields require specific prompt configuration, model selection, and processing logic that cannot be automatically generated from existing data.',
            'alternatives': [
                'Create new AI field that references existing field data',
                'Set up AI field with prompts that use existing field values',
                'Manually configure AI processing for existing data'
            ]
        },
        
        ('*', 'relation'): {
            'reason': 'Cannot convert existing data to relationship references',
            'explanation': 'Relations require valid record IDs from target pipelines. Existing text/number data cannot be automatically matched to relationship targets.',
            'alternatives': [
                'Create new relation field separately',
                'Use lookup functionality to manually match existing data',
                'Export data and create mapping table for relationship setup'
            ]
        },
        
        ('*', 'record_data'): {
            'reason': 'Cannot convert fields to system record data type',
            'explanation': 'Record data fields are system-managed and cannot be created from user data.',
            'alternatives': [
                'Use existing record metadata features',
                'Create computed field that formats record information'
            ]
        },
        
        # Ambiguous/error-prone conversions
        ('date', 'number'): {
            'reason': 'Date to number conversion is ambiguous and error-prone',
            'explanation': 'Unclear whether to convert to timestamp, year, day-of-year, etc. Different interpretations could cause data confusion.',
            'alternatives': [
                'Create computed field with specific date calculation (year, month, etc.)',
                'Create separate number field and manually populate with desired date values'
            ]
        },
        
        ('number', 'date'): {
            'reason': 'Number to date conversion is ambiguous',
            'explanation': 'Numbers could represent timestamps, years, days, etc. Automatic conversion could create incorrect dates.',
            'alternatives': [
                'Create new date field and manually map number values',
                'Use computed field with specific number-to-date logic'
            ]
        }
    }
    
    # Safe migrations - low risk, automatic conversion possible
    SAFE_MIGRATIONS = {
        # Text expansions (no data loss)
        ('text', 'textarea'): {
            'risk': 'low',
            'auto_convert': True,
            'description': 'Text content preserved, expanded to multi-line format'
        },
        ('text', 'tags'): {
            'risk': 'low', 
            'auto_convert': True,
            'description': 'Text split by commas into tag array'
        },
        ('number', 'text'): {
            'risk': 'low',
            'auto_convert': True,
            'description': 'Numbers converted to string representation'
        },
        ('boolean', 'text'): {
            'risk': 'low',
            'auto_convert': True,
            'description': 'Boolean values converted to "true"/"false" text'
        },
        ('select', 'multiselect'): {
            'risk': 'low',
            'auto_convert': True,
            'description': 'Single selection converted to array with one item'
        },
        ('select', 'tags'): {
            'risk': 'low',
            'auto_convert': True,
            'description': 'Selected option converted to single tag'
        },
        
        # Email/URL to text (always safe)
        ('email', 'text'): {
            'risk': 'low',
            'auto_convert': True,
            'description': 'Email addresses preserved as text'
        },
        ('url', 'text'): {
            'risk': 'low',
            'auto_convert': True,
            'description': 'URLs preserved as text'
        },
        ('phone', 'text'): {
            'risk': 'low',
            'auto_convert': True,
            'description': 'Phone numbers preserved as formatted text'
        }
    }
    
    # Risky migrations - potential data loss, require confirmation
    RISKY_MIGRATIONS = {
        # Truncation risks
        ('textarea', 'text'): {
            'risk': 'medium',
            'data_loss': 'truncation',
            'warning': 'Long text content will be truncated to 160 characters. Multi-line formatting will be lost.',
            'requires_preview': True
        },
        
        # Array reduction
        ('multiselect', 'select'): {
            'risk': 'medium',
            'data_loss': 'array_reduction',
            'warning': 'Multiple selections will be reduced to first selected value only. Additional selections will be lost.',
            'requires_preview': True
        },
        ('tags', 'text'): {
            'risk': 'medium',
            'data_loss': 'array_join',
            'warning': 'Multiple tags will be joined into single comma-separated text. Tag structure will be lost.',
            'requires_preview': True
        },
        ('tags', 'select'): {
            'risk': 'medium',
            'data_loss': 'array_reduction',
            'warning': 'Multiple tags will be reduced to first tag only. Additional tags will be lost.',
            'requires_preview': True
        },
        
        # Format validation filtering
        ('text', 'number'): {
            'risk': 'high',
            'data_loss': 'validation_filter',
            'warning': 'Non-numeric text will become null. Only valid numbers will be preserved.',
            'requires_preview': True
        },
        ('text', 'email'): {
            'risk': 'high',
            'data_loss': 'validation_filter',
            'warning': 'Invalid email formats will become null. Only valid email addresses will be preserved.',
            'requires_preview': True
        },
        ('text', 'url'): {
            'risk': 'high',
            'data_loss': 'validation_filter',
            'warning': 'Invalid URL formats will become null. Only valid URLs will be preserved.',
            'requires_preview': True
        },
        ('text', 'phone'): {
            'risk': 'high',
            'data_loss': 'validation_filter',
            'warning': 'Invalid phone number formats will become null. Only valid phone numbers will be preserved.',
            'requires_preview': True
        },
        ('text', 'boolean'): {
            'risk': 'medium',
            'data_loss': 'interpretation',
            'warning': 'Text will be interpreted as true/false. Values like "true", "1", "yes" become true; others become false.',
            'requires_preview': True
        },
        
        # Date conversions
        ('text', 'date'): {
            'risk': 'high',
            'data_loss': 'date_parsing',
            'warning': 'Invalid date formats will become null. Only recognizable date strings will be preserved.',
            'requires_preview': True
        },
        ('date', 'text'): {
            'risk': 'low',
            'data_loss': 'format_change',
            'warning': 'Dates will be converted to ISO string format. Original formatting will be lost.',
            'requires_preview': False
        }
    }
    
    # =============================================================================
    # MAIN VALIDATION METHODS - Unified validation for all field operations
    # =============================================================================
    
    def validate_field_creation(self, field_config: Dict[str, Any], pipeline) -> FieldValidationResult:
        """
        Validate field creation configuration
        
        Args:
            field_config: Field configuration dictionary
            pipeline: Pipeline instance where field will be created
            
        Returns:
            FieldValidationResult with validation outcome
        """
        errors = []
        warnings = []
        metadata = {}
        
        # Basic field validation
        if not field_config.get('name'):
            errors.append("Field name is required")
        
        if not field_config.get('field_type'):
            errors.append("Field type is required")
        
        # Validate field name
        if field_config.get('name'):
            name_validation = self._validate_field_name(field_config['name'], pipeline)
            if not name_validation['valid']:
                errors.extend(name_validation['errors'])
        
        # Validate field type
        if field_config.get('field_type'):
            type_validation = self._validate_field_type(field_config['field_type'])
            if not type_validation['valid']:
                errors.extend(type_validation['errors'])
        
        # Validate field configuration
        if field_config.get('field_config'):
            config_validation = self._validate_field_config(
                field_config['field_type'], 
                field_config['field_config']
            )
            if not config_validation['valid']:
                errors.extend(config_validation['errors'])
            warnings.extend(config_validation['warnings'])
        
        # Validate storage constraints
        if field_config.get('storage_constraints'):
            constraint_validation = self._validate_storage_constraints(field_config['storage_constraints'])
            if not constraint_validation['valid']:
                errors.extend(constraint_validation['errors'])
            warnings.extend(constraint_validation['warnings'])
        
        return FieldValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )
    
    def validate_field_update(self, field, changes: Dict[str, Any]) -> FieldValidationResult:
        """
        Validate field modification changes
        
        Args:
            field: Existing field instance
            changes: Dictionary of proposed changes
            
        Returns:
            FieldValidationResult with validation outcome and migration requirements
        """
        errors = []
        warnings = []
        metadata = {}
        
        # Validate name changes
        if 'name' in changes:
            if not changes['name']:
                errors.append("Field name cannot be empty")
            else:
                name_validation = self._validate_field_name(changes['name'], field.pipeline, exclude_field=field)
                if not name_validation['valid']:
                    errors.extend(name_validation['errors'])
        
        # Validate field type changes
        if 'field_type' in changes:
            current_type = field.field_type
            new_type = changes['field_type']
            
            migration_validation = self.validate_field_change(field, {'field_type': new_type})
            
            if not migration_validation['allowed']:
                if migration_validation['category'] == 'denied':
                    errors.append(f"Migration not allowed: {migration_validation['reason']}")
                    metadata['migration_denied'] = True
                    metadata['alternatives'] = migration_validation.get('alternatives', [])
            else:
                if migration_validation['category'] == 'risky':
                    warnings.append(migration_validation['data_loss_warning'])
                    metadata['migration_risky'] = True
                    metadata['requires_preview'] = migration_validation.get('requires_preview', False)
        
        # Validate constraint changes
        if 'storage_constraints' in changes:
            constraint_validation = self._validate_constraint_changes(
                field.storage_constraints or {}, 
                changes['storage_constraints']
            )
            if not constraint_validation['valid']:
                errors.extend(constraint_validation['errors'])
            warnings.extend(constraint_validation['warnings'])
        
        return FieldValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )
    
    def validate_field_deletion(self, field, hard_delete: bool = False) -> FieldValidationResult:
        """
        Validate field deletion
        
        Args:
            field: Field instance to be deleted
            hard_delete: Whether this is a hard deletion
            
        Returns:
            FieldValidationResult with validation outcome
        """
        errors = []
        warnings = []
        metadata = {}
        
        # Check for field dependencies
        dependencies = self._analyze_field_dependencies(field)
        
        if dependencies['total_dependencies'] > 0:
            if hard_delete:
                errors.append(f"Cannot hard delete field with {dependencies['total_dependencies']} dependencies")
                metadata['dependencies'] = dependencies
            else:
                warnings.append(f"Field has {dependencies['total_dependencies']} dependencies that may be affected")
                metadata['dependencies'] = dependencies
        
        # Check for data impact
        from ..models import Record
        records_with_data = Record.objects.filter(
            pipeline=field.pipeline,
            is_deleted=False,
            data__has_key=field.slug
        ).count()
        
        if records_with_data > 0:
            if hard_delete:
                warnings.append(f"Field has data in {records_with_data} records - data will be permanently lost")
            else:
                warnings.append(f"Field has data in {records_with_data} records - data will be preserved")
            
            metadata['records_with_data'] = records_with_data
        
        return FieldValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )
    
    def validate_field_restoration(self, field) -> FieldValidationResult:
        """
        Validate field restoration
        
        Args:
            field: Soft-deleted field instance to be restored
            
        Returns:
            FieldValidationResult with validation outcome
        """
        errors = []
        warnings = []
        metadata = {}
        
        # Check for name conflicts
        from ..models import Field
        conflicting_field = Field.objects.filter(
            pipeline=field.pipeline, 
            slug=field.slug, 
            is_deleted=False
        ).first()
        
        if conflicting_field:
            errors.append(f"Cannot restore: field with name '{field.name}' already exists")
            metadata['conflicting_field_id'] = conflicting_field.id
        
        # Check field age
        from django.utils import timezone
        from datetime import timedelta
        
        if field.deleted_at:
            days_deleted = (timezone.now() - field.deleted_at).days
            if days_deleted > 30:
                warnings.append(f"Field has been deleted for {days_deleted} days - restoration may affect data integrity")
        
        return FieldValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )
    
    # =============================================================================
    # MIGRATION VALIDATION - Moved from migration_validator.py
    # =============================================================================
    
    def validate_field_change(self, field, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main validation method - determines if a field migration is allowed, risky, or denied
        
        Args:
            field: Current field object
            new_config: Proposed new field configuration
            
        Returns:
            Dict with validation result including allowed status, risk level, warnings, etc.
        """
        current_type = field.field_type
        new_type = new_config.get('field_type', current_type)
        
        logger.info(f"Validating migration: {current_type} → {new_type} for field {field.name}")
        
        # If no type change, check for constraint changes only
        if current_type == new_type:
            return self._validate_constraint_changes_migration(field, new_config)
        
        # Check hard-denied patterns first
        denial = self._check_denial_patterns(current_type, new_type)
        if denial:
            logger.warning(f"Migration denied: {current_type} → {new_type} - {denial['reason']}")
            return {
                'allowed': False,
                'category': 'denied',
                'risk_level': 'high',
                'reason': denial['reason'],
                'explanation': denial['explanation'],
                'alternatives': denial['alternatives'],
                'current_type': current_type,
                'target_type': new_type
            }
        
        # Check safe patterns
        safe_migration = self._check_safe_patterns(current_type, new_type)
        if safe_migration:
            logger.info(f"Safe migration approved: {current_type} → {new_type}")
            return {
                'allowed': True,
                'category': 'safe',
                'risk_level': 'low',
                'auto_convert': safe_migration.get('auto_convert', False),
                'description': safe_migration.get('description'),
                'confirmation_required': False,
                'current_type': current_type,
                'target_type': new_type
            }
        
        # Check risky patterns
        risky_migration = self._check_risky_patterns(current_type, new_type)
        if risky_migration:
            logger.warning(f"Risky migration flagged: {current_type} → {new_type} - {risky_migration['warning']}")
            return {
                'allowed': True,
                'category': 'risky',
                'risk_level': risky_migration['risk'],
                'data_loss_type': risky_migration.get('data_loss'),
                'data_loss_warning': risky_migration['warning'],
                'requires_preview': risky_migration.get('requires_preview', False),
                'confirmation_required': True,
                'current_type': current_type,
                'target_type': new_type
            }
        
        # Unknown migration pattern - deny by default for safety
        logger.error(f"Unknown migration pattern denied: {current_type} → {new_type}")
        return {
            'allowed': False,
            'category': 'denied',
            'risk_level': 'high',
            'reason': 'Unknown or untested field type conversion',
            'explanation': f'Migration from {current_type} to {new_type} has not been tested and could cause data corruption.',
            'alternatives': [
                'Create new field with desired type',
                'Export existing data before making changes',
                'Contact system administrator for custom migration support'
            ],
            'current_type': current_type,
            'target_type': new_type
        }
    
    # =============================================================================
    # PRIVATE VALIDATION HELPER METHODS
    # =============================================================================
    
    def _validate_field_name(self, name: str, pipeline, exclude_field=None) -> Dict[str, Any]:
        """Validate field name for uniqueness and format"""
        errors = []
        
        if not name:
            errors.append("Field name is required")
            return {'valid': False, 'errors': errors}
        
        # Check for duplicate names
        from ..models import Field, field_slugify
        
        proposed_slug = field_slugify(name)
        query = Field.objects.filter(pipeline=pipeline, slug=proposed_slug, is_deleted=False)
        
        if exclude_field:
            query = query.exclude(id=exclude_field.id)
        
        if query.exists():
            errors.append(f"Field with name '{name}' already exists")
        
        return {'valid': len(errors) == 0, 'errors': errors}
    
    def _validate_field_type(self, field_type: str) -> Dict[str, Any]:
        """Validate field type is supported"""
        errors = []
        
        try:
            from ..field_types import FieldType
            FieldType(field_type)
        except ValueError:
            errors.append(f"Invalid field type: {field_type}")
        
        return {'valid': len(errors) == 0, 'errors': errors}
    
    def _validate_field_config(self, field_type: str, field_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate field-specific configuration"""
        errors = []
        warnings = []
        
        # Field-specific validation will be enhanced here
        # For now, basic validation
        
        return {'valid': len(errors) == 0, 'errors': errors, 'warnings': warnings}
    
    def _validate_storage_constraints(self, constraints: Dict[str, Any]) -> Dict[str, Any]:
        """Validate storage constraints"""
        errors = []
        warnings = []
        
        # Validate max_storage_length
        if 'max_storage_length' in constraints:
            max_length = constraints['max_storage_length']
            if max_length is not None and (not isinstance(max_length, int) or max_length < 1):
                errors.append("max_storage_length must be a positive integer or null")
        
        return {'valid': len(errors) == 0, 'errors': errors, 'warnings': warnings}
    
    def _validate_constraint_changes(self, old_constraints: Dict[str, Any], 
                                   new_constraints: Dict[str, Any]) -> Dict[str, Any]:
        """Validate constraint changes for potential data loss"""
        errors = []
        warnings = []
        
        # Check max length reduction
        old_max = old_constraints.get('max_storage_length')
        new_max = new_constraints.get('max_storage_length')
        if old_max and new_max and new_max < old_max:
            warnings.append(f"Maximum length reduced from {old_max} to {new_max} - data truncation risk")
        
        # Check uniqueness enforcement
        old_unique = old_constraints.get('enforce_uniqueness', False)
        new_unique = new_constraints.get('enforce_uniqueness', False)
        if not old_unique and new_unique:
            warnings.append("Uniqueness constraint added - duplicate values will become null")
        
        return {'valid': len(errors) == 0, 'errors': errors, 'warnings': warnings}
    
    def _validate_constraint_changes_migration(self, field, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate constraint changes when field type remains the same"""
        current_constraints = field.storage_constraints or {}
        new_constraints = new_config.get('storage_constraints', {})
        
        # Check for constraint tightening
        constraint_changes = []
        
        # Length constraint changes
        old_max_length = current_constraints.get('max_storage_length')
        new_max_length = new_constraints.get('max_storage_length')
        
        if old_max_length and new_max_length and new_max_length < old_max_length:
            constraint_changes.append({
                'type': 'length_decrease',
                'warning': f'Maximum length reduced from {old_max_length} to {new_max_length}. Longer values will be truncated.',
                'risk': 'medium'
            })
        
        # Uniqueness constraint addition
        old_unique = current_constraints.get('enforce_uniqueness', False)
        new_unique = new_constraints.get('enforce_uniqueness', False)
        
        if not old_unique and new_unique:
            constraint_changes.append({
                'type': 'enforce_uniqueness',
                'warning': 'Uniqueness enforcement added. Duplicate values will become null.',
                'risk': 'high'
            })
        
        # If no risky constraint changes, allow
        if not constraint_changes:
            return {
                'allowed': True,
                'category': 'safe',
                'risk_level': 'low',
                'description': 'Configuration changes only - no data migration required',
                'confirmation_required': False
            }
        
        # Risky constraint changes require confirmation
        highest_risk = max(change['risk'] for change in constraint_changes)
        warnings = [change['warning'] for change in constraint_changes]
        
        return {
            'allowed': True,
            'category': 'risky',
            'risk_level': highest_risk,
            'constraint_changes': constraint_changes,
            'data_loss_warning': '; '.join(warnings),
            'requires_preview': True,
            'confirmation_required': True
        }
    
    def _analyze_field_dependencies(self, field) -> Dict[str, Any]:
        """Analyze field dependencies (moved from migration_validator.py)"""
        dependencies = {
            'field_relationships': [],
            'business_rules': [],
            'ai_dependencies': [],
            'workflow_dependencies': [],
            'validation_dependencies': [],
            'form_dependencies': [],
            'total_dependencies': 0
        }
        
        try:
            # Check field relationships (computed fields, formulas)
            pipeline = field.pipeline
            related_fields = []
            
            for other_field in pipeline.fields.exclude(id=field.id):
                # Check if other fields reference this field
                if self._field_references_field(other_field, field):
                    related_fields.append({
                        'field_name': other_field.name,
                        'field_type': other_field.field_type,
                        'relationship_type': self._get_relationship_type(other_field, field),
                        'impact': 'Will need reconfiguration'
                    })
            
            dependencies['field_relationships'] = related_fields
            
            # Check AI field dependencies
            ai_deps = []
            for other_field in pipeline.fields.filter(is_ai_field=True):
                if other_field.ai_config and self._ai_config_references_field(other_field.ai_config, field):
                    ai_deps.append({
                        'field_name': other_field.name,
                        'dependency_type': 'prompt_reference',
                        'impact': 'AI prompts will need updating'
                    })
            
            dependencies['ai_dependencies'] = ai_deps
            
            # Calculate total
            dependencies['total_dependencies'] = len(related_fields) + len(ai_deps)
            dependencies['has_dependencies'] = dependencies['total_dependencies'] > 0
            dependencies['risk_level'] = 'high' if dependencies['total_dependencies'] > 5 else (
                'medium' if dependencies['total_dependencies'] > 2 else 'low'
            )
            
        except Exception as e:
            logger.error(f"Error analyzing dependencies: {e}")
            dependencies['error'] = f'Error analyzing dependencies: {str(e)}'
        
        return dependencies
    
    def _field_references_field(self, source_field, target_field):
        """Check if source field references target field"""
        # Check computed field formulas, AI prompts, etc.
        if source_field.field_type == 'computed' and source_field.field_config:
            formula = source_field.field_config.get('formula', '')
            return target_field.slug in formula
        elif source_field.is_ai_field and source_field.ai_config:
            prompt = source_field.ai_config.get('prompt', '')
            return target_field.slug in prompt or f"{{{target_field.slug}}}" in prompt
        return False
    
    def _get_relationship_type(self, source_field, target_field):
        """Determine the type of relationship between fields"""
        if source_field.field_type == 'computed':
            return 'formula_dependency'
        elif source_field.is_ai_field:
            return 'ai_prompt_reference'
        else:
            return 'unknown'
    
    def _ai_config_references_field(self, ai_config, field):
        """Check if AI config references a field"""
        if not isinstance(ai_config, dict):
            return False
        prompt = ai_config.get('prompt', '')
        return field.slug in prompt or f"{{{field.slug}}}" in prompt
    
    def _check_denial_patterns(self, current_type: str, new_type: str) -> Optional[Dict[str, Any]]:
        """Check if migration matches any hard-denial patterns"""
        # Direct pattern match
        pattern_key = (current_type, new_type)
        if pattern_key in self.DENIED_MIGRATIONS:
            return self.DENIED_MIGRATIONS[pattern_key]
        
        # Wildcard pattern matches
        current_wildcard = (current_type, '*')
        if current_wildcard in self.DENIED_MIGRATIONS:
            return self.DENIED_MIGRATIONS[current_wildcard]
        
        new_wildcard = ('*', new_type)
        if new_wildcard in self.DENIED_MIGRATIONS:
            return self.DENIED_MIGRATIONS[new_wildcard]
        
        return None
    
    def _check_safe_patterns(self, current_type: str, new_type: str) -> Optional[Dict[str, Any]]:
        """Check if migration matches any safe patterns"""
        pattern_key = (current_type, new_type)
        return self.SAFE_MIGRATIONS.get(pattern_key)
    
    def _check_risky_patterns(self, current_type: str, new_type: str) -> Optional[Dict[str, Any]]:
        """Check if migration matches any risky patterns"""
        pattern_key = (current_type, new_type)
        return self.RISKY_MIGRATIONS.get(pattern_key)
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def get_migration_alternatives(self, current_type: str, target_type: str) -> List[str]:
        """Get suggested alternatives for denied migrations"""
        denial = self._check_denial_patterns(current_type, target_type)
        if denial and 'alternatives' in denial:
            return denial['alternatives']
        
        # Default alternatives
        return [
            f'Create new {target_type} field alongside existing {current_type} field',
            f'Export {current_type} data before making changes',
            'Contact system administrator for custom migration support'
        ]