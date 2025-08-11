"""
Comprehensive migration validation system with hard-denial rules
Validates field migration feasibility before execution to prevent data disasters
Moved from pipelines/migration_validator.py for better organization
"""
from typing import Dict, Any, List, Tuple, Optional, TYPE_CHECKING
import logging
from ..field_types import FieldType

# Use TYPE_CHECKING to avoid circular import at runtime
if TYPE_CHECKING:
    from ..models import Field

logger = logging.getLogger(__name__)


class MigrationValidator:
    """Comprehensive migration validation with hard-denial rules"""
    
    # Hard-denied migration patterns - these migrations are technically impossible or too risky
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
    
    def validate_field_change(self, field: Field, new_config: Dict[str, Any]) -> Dict[str, Any]:
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
        
        logger.info(f"MIGRATION: Validating {current_type} → {new_type} for field '{field.name}'")
        
        # If no type change, check for constraint changes only
        if current_type == new_type:
            return self._validate_constraint_changes(field, new_config)
        
        # Check hard-denied patterns first
        denial = self._check_denial_patterns(current_type, new_type)
        if denial:
            logger.error(f"MIGRATION: FAILED - {current_type} → {new_type} blocked: {denial['reason']}")
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
            logger.info(f"MIGRATION: PASSED - {current_type} → {new_type} approved (safe)")
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
            logger.warning(f"MIGRATION: WARNING - {current_type} → {new_type} allowed but risky: {risky_migration['warning']}")
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
        logger.error(f"MIGRATION: FAILED - {current_type} → {new_type} denied (unknown pattern)")
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
    
    def _validate_constraint_changes(self, field: Field, new_config: Dict[str, Any]) -> Dict[str, Any]:
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
    
    def analyze_field_dependencies(self, field: Field) -> Dict[str, Any]:
        """
        Analyze what would break if this field is deleted or changed
        
        Returns:
            Dict with dependency analysis including impact assessment
        """
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
            logger.error(f"MIGRATION: Dependency analysis failed - {e}")
            dependencies['error'] = f'Error analyzing dependencies: {str(e)}'
        
        return dependencies
    
    def _field_references_field(self, source_field: Field, target_field: Field) -> bool:
        """Check if source field references target field"""
        # Check computed field formulas, AI prompts, etc.
        if source_field.field_type == 'computed' and source_field.field_config:
            formula = source_field.field_config.get('formula', '')
            return target_field.slug in formula
        elif source_field.is_ai_field and source_field.ai_config:
            prompt = source_field.ai_config.get('prompt', '')
            return target_field.slug in prompt or f"{{{target_field.slug}}}" in prompt
        return False
    
    def _get_relationship_type(self, source_field: Field, target_field: Field) -> str:
        """Determine the type of relationship between fields"""
        if source_field.field_type == 'computed':
            return 'formula_dependency'
        elif source_field.is_ai_field:
            return 'ai_prompt_reference'
        else:
            return 'unknown'
    
    def _ai_config_references_field(self, ai_config: dict, field: Field) -> bool:
        """Check if AI config references a field"""
        if not isinstance(ai_config, dict):
            return False
        prompt = ai_config.get('prompt', '')
        return field.slug in prompt or f"{{{field.slug}}}" in prompt
    
    def get_migration_preview(self, field: Field, new_type: str, sample_size: int = 10) -> Dict[str, Any]:
        """
        Generate preview of what migration would look like
        
        Args:
            field: Field to migrate
            new_type: Target field type
            sample_size: Number of sample records to preview
            
        Returns:
            Dict with preview data showing before/after values
        """
        from ..models import Record
        
        try:
            # Get sample records with data for this field
            records = Record.objects.filter(
                pipeline=field.pipeline,
                is_deleted=False,
                data__has_key=field.slug
            ).exclude(
                data__isnull=True
            )[:sample_size]
            
            preview_data = []
            for record in records:
                current_value = record.data.get(field.slug)
                
                # Simulate migration
                try:
                    migrated_value = self._simulate_migration(current_value, field.field_type, new_type)
                    migration_status = 'success'
                    migration_notes = None
                except Exception as e:
                    migrated_value = None
                    migration_status = 'error'
                    migration_notes = str(e)
                
                preview_data.append({
                    'record_id': record.id,
                    'record_title': record.title or f"Record {record.id}",
                    'current_value': current_value,
                    'migrated_value': migrated_value,
                    'migration_status': migration_status,
                    'migration_notes': migration_notes
                })
            
            # Generate summary statistics
            total_records = Record.objects.filter(
                pipeline=field.pipeline,
                is_deleted=False,
                data__has_key=field.slug
            ).count()
            
            successful_migrations = len([p for p in preview_data if p['migration_status'] == 'success'])
            failed_migrations = len([p for p in preview_data if p['migration_status'] == 'error'])
            
            return {
                'preview_data': preview_data,
                'summary': {
                    'total_records_with_data': total_records,
                    'sample_size': len(preview_data),
                    'estimated_successful': int((successful_migrations / max(len(preview_data), 1)) * total_records),
                    'estimated_failed': int((failed_migrations / max(len(preview_data), 1)) * total_records),
                    'success_rate': f"{(successful_migrations / max(len(preview_data), 1)) * 100:.1f}%"
                }
            }
            
        except Exception as e:
            logger.error(f"MIGRATION: Preview generation failed - {e}")
            return {
                'error': f'Could not generate preview: {str(e)}',
                'preview_data': [],
                'summary': {}
            }
    
    def _simulate_migration(self, value: Any, current_type: str, new_type: str) -> Any:
        """Simulate what happens to a value during migration"""
        if value is None:
            return None
        
        # Use the migration patterns to determine conversion logic
        if current_type == 'text' and new_type == 'number':
            return float(value)
        elif current_type == 'text' and new_type == 'email':
            if '@' not in str(value):
                raise ValueError('Not a valid email format')
            return str(value).lower().strip()
        elif current_type == 'textarea' and new_type == 'text':
            # Truncate to 160 characters for text fields
            return str(value)[:160]
        elif current_type == 'multiselect' and new_type == 'select':
            # Take first value only
            if isinstance(value, list) and value:
                return value[0]
            return value
        elif current_type == 'tags' and new_type == 'text':
            # Join tags with commas
            if isinstance(value, list):
                return ', '.join(value)
            return str(value)
        else:
            # Default: convert to string representation
            return str(value)
    
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