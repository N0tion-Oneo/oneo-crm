"""
Comprehensive migration validation system with hard-denial rules
Validates field migration feasibility before execution to prevent data disasters
"""
from typing import Dict, Any, List, Tuple, Optional
import logging
from .field_types import FieldType
from .models import Field

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
    
    @classmethod
    def validate_field_change(cls, field: Field, new_config: Dict[str, Any]) -> Dict[str, Any]:
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
            return cls._validate_constraint_changes(field, new_config)
        
        # Check hard-denied patterns first
        denial = cls._check_denial_patterns(current_type, new_type)
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
        safe_migration = cls._check_safe_patterns(current_type, new_type)
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
        risky_migration = cls._check_risky_patterns(current_type, new_type)
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
    
    @classmethod
    def _check_denial_patterns(cls, current_type: str, new_type: str) -> Optional[Dict[str, Any]]:
        """Check if migration matches any hard-denial patterns"""
        
        # Direct pattern match
        pattern_key = (current_type, new_type)
        if pattern_key in cls.DENIED_MIGRATIONS:
            return cls.DENIED_MIGRATIONS[pattern_key]
        
        # Wildcard pattern matches
        current_wildcard = (current_type, '*')
        if current_wildcard in cls.DENIED_MIGRATIONS:
            return cls.DENIED_MIGRATIONS[current_wildcard]
        
        new_wildcard = ('*', new_type)
        if new_wildcard in cls.DENIED_MIGRATIONS:
            return cls.DENIED_MIGRATIONS[new_wildcard]
        
        return None
    
    @classmethod
    def _check_safe_patterns(cls, current_type: str, new_type: str) -> Optional[Dict[str, Any]]:
        """Check if migration matches any safe patterns"""
        pattern_key = (current_type, new_type)
        return cls.SAFE_MIGRATIONS.get(pattern_key)
    
    @classmethod
    def _check_risky_patterns(cls, current_type: str, new_type: str) -> Optional[Dict[str, Any]]:
        """Check if migration matches any risky patterns"""
        pattern_key = (current_type, new_type)
        return cls.RISKY_MIGRATIONS.get(pattern_key)
    
    @classmethod
    def _validate_constraint_changes(cls, field: Field, new_config: Dict[str, Any]) -> Dict[str, Any]:
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
    
    @classmethod
    def get_migration_alternatives(cls, current_type: str, target_type: str) -> List[str]:
        """Get suggested alternatives for denied migrations"""
        
        denial = cls._check_denial_patterns(current_type, target_type)
        if denial and 'alternatives' in denial:
            return denial['alternatives']
        
        # Default alternatives
        return [
            f'Create new {target_type} field alongside existing {current_type} field',
            f'Export {current_type} data before making changes',
            'Contact system administrator for custom migration support'
        ]
    
    @classmethod
    def estimate_data_loss(cls, field: Field, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate potential data loss from migration"""
        
        # This would analyze actual field data to estimate impact
        # For now, return basic structure - can be enhanced later
        
        return {
            'total_records': 0,  # Would count records with this field
            'records_at_risk': 0,  # Records that might lose data
            'estimated_loss_percentage': 0.0,
            'loss_types': []  # Types of data loss expected
        }
    
    @classmethod
    def generate_data_preview(cls, field, new_config, sample_limit=5):
        """
        Generate sample data transformation preview
        
        Args:
            field: Field instance to be changed
            new_config: Dictionary with new field configuration
            sample_limit: Number of sample records to show
            
        Returns:
            dict: Sample data transformations showing before/after
        """
        try:
            # Get sample records that have data for this field
            from .models import Record
            
            sample_records = Record.objects.filter(
                pipeline=field.pipeline,
                is_deleted=False,
                data__has_key=field.slug
            ).exclude(
                data__isnull=True
            ).order_by('-updated_at')[:sample_limit]
            
            if not sample_records.exists():
                return {
                    'has_samples': False,
                    'message': 'No sample data available for this field',
                    'samples': []
                }
            
            samples = []
            current_type = field.field_type
            target_type = new_config.get('field_type', current_type)
            
            for record in sample_records:
                current_value = record.data.get(field.slug)
                transformed_value = cls._simulate_value_transformation(
                    current_value, current_type, target_type, new_config
                )
                
                samples.append({
                    'record_id': record.id,
                    'record_title': record.title,
                    'current_value': current_value,
                    'transformed_value': transformed_value,
                    'data_type_change': f"{type(current_value).__name__} → {type(transformed_value).__name__}",
                    'success': transformed_value is not None
                })
            
            return {
                'has_samples': True,
                'sample_count': len(samples),
                'total_records': Record.objects.filter(
                    pipeline=field.pipeline,
                    is_deleted=False,
                    data__has_key=field.slug
                ).count(),
                'samples': samples
            }
            
        except Exception as e:
            logger.error(f"Error generating data preview: {e}")
            return {
                'has_samples': False,
                'error': f'Error generating preview: {str(e)}',
                'samples': []
            }
    
    @classmethod
    def estimate_performance(cls, field, new_config):
        """
        Estimate migration performance and resource requirements
        
        Args:
            field: Field instance to be changed
            new_config: Dictionary with new field configuration
            
        Returns:
            dict: Performance estimates and requirements
        """
        try:
            from .models import Record
            from django.db.models import Count
            
            # Count records that will be affected
            total_records = Record.objects.filter(
                pipeline=field.pipeline,
                is_deleted=False
            ).count()
            
            records_with_data = Record.objects.filter(
                pipeline=field.pipeline,
                is_deleted=False,
                data__has_key=field.slug
            ).count()
            
            # Base processing time estimates (records per second)
            current_type = field.field_type
            target_type = new_config.get('field_type', current_type)
            
            # Processing rates based on complexity (records/second)
            processing_rates = {
                'simple': 1000,  # text->text, number->number
                'moderate': 500,  # text->number, number->text
                'complex': 100,   # AI fields, complex validations
                'very_complex': 50  # AI->other, complex transformations
            }
            
            # Determine complexity
            complexity = cls._determine_migration_complexity(current_type, target_type)
            processing_rate = processing_rates.get(complexity, 100)
            
            # Calculate estimates
            processing_time_seconds = max(1, records_with_data / processing_rate)
            
            # Batch calculations
            default_batch_size = 100
            optimal_batch_size = min(max(10, records_with_data // 20), 500)
            total_batches = max(1, (records_with_data + optimal_batch_size - 1) // optimal_batch_size)
            
            return {
                'total_records': total_records,
                'records_with_data': records_with_data,
                'records_without_data': total_records - records_with_data,
                'processing_rate': f"{processing_rate} records/second",
                'estimated_time_seconds': processing_time_seconds,
                'estimated_time_formatted': cls._format_duration(processing_time_seconds),
                'complexity': complexity,
                'optimal_batch_size': optimal_batch_size,
                'total_batches': total_batches,
                'memory_estimate': cls._estimate_memory_usage(records_with_data),
                'requires_backup': records_with_data > 0,
                'recommended_maintenance_window': processing_time_seconds > 300  # > 5 minutes
            }
            
        except Exception as e:
            logger.error(f"Error estimating performance: {e}")
            return {
                'error': f'Error estimating performance: {str(e)}',
                'total_records': 0,
                'records_with_data': 0
            }
    
    @classmethod
    def analyze_dependencies(cls, field):
        """
        Comprehensive analysis of field dependencies
        
        Args:
            field: Field instance to analyze
            
        Returns:
            dict: Complete dependency analysis
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
                if cls._field_references_field(other_field, field):
                    related_fields.append({
                        'field_name': other_field.name,
                        'field_type': other_field.field_type,
                        'relationship_type': cls._get_relationship_type(other_field, field),
                        'impact': 'Will need reconfiguration'
                    })
            
            dependencies['field_relationships'] = related_fields
            
            # Check business rules that reference this field
            business_rules = []
            for other_field in pipeline.fields.all():
                if other_field.business_rules:
                    rules = other_field.business_rules
                    if cls._business_rules_reference_field(rules, field):
                        business_rules.append({
                            'field_name': other_field.name,
                            'rule_type': 'stage_requirements',
                            'impact': 'May require rule updates'
                        })
            
            dependencies['business_rules'] = business_rules
            
            # Check AI field dependencies
            ai_deps = []
            for other_field in pipeline.fields.filter(is_ai_field=True):
                if other_field.ai_config and cls._ai_config_references_field(other_field.ai_config, field):
                    ai_deps.append({
                        'field_name': other_field.name,
                        'dependency_type': 'prompt_reference',
                        'impact': 'AI prompts will need updating'
                    })
            
            dependencies['ai_dependencies'] = ai_deps
            
            # Calculate total
            dependencies['total_dependencies'] = (
                len(related_fields) + len(business_rules) + len(ai_deps)
            )
            
            dependencies['has_dependencies'] = dependencies['total_dependencies'] > 0
            dependencies['risk_level'] = 'high' if dependencies['total_dependencies'] > 5 else (
                'medium' if dependencies['total_dependencies'] > 2 else 'low'
            )
            
        except Exception as e:
            logger.error(f"Error analyzing dependencies: {e}")
            dependencies['error'] = f'Error analyzing dependencies: {str(e)}'
        
        return dependencies
    
    @classmethod
    def _simulate_value_transformation(cls, value, current_type, target_type, new_config):
        """Simulate how a value would be transformed"""
        if value is None:
            return None
            
        try:
            # Simple transformations for preview
            if current_type == target_type:
                return value
            elif target_type == 'text':
                return str(value)
            elif target_type == 'boolean':
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ['true', '1', 'yes', 'on']
            elif target_type in ['email', 'phone', 'url', 'select', 'multiselect', 'number'] and current_type in ['text', 'textarea']:
                # Use actual field validators with proper configurations
                from .validators import FieldValidator
                from .field_types import FieldType, FIELD_TYPE_CONFIGS
                
                try:
                    # Get the target field type enum
                    target_field_type = getattr(FieldType, target_type.upper())
                    
                    # Create default configuration for the target field type
                    config_class = FIELD_TYPE_CONFIGS.get(target_field_type)
                    default_config = config_class() if config_class else {}
                    
                    # For migration preview, use the configuration from new_config if provided
                    field_config = new_config.get('field_config', {})
                    
                    # Merge with default config
                    if config_class and field_config:
                        try:
                            # Create config with provided options
                            merged_config = config_class(**field_config)
                        except:
                            # If config creation fails, use default
                            merged_config = default_config
                    else:
                        merged_config = default_config
                    
                    # Create validator with proper configuration
                    validator = FieldValidator(target_field_type, merged_config)
                    
                    # Use the validator's validate method for complete validation
                    validation_result = validator.validate(value)
                    
                    if validation_result.is_valid:
                        return validation_result.cleaned_value
                    else:
                        # Validation failed - return None (will become null)
                        return None
                        
                except Exception as e:
                    # If validation fails, return None (will become null)
                    return None
            elif target_type in ['text', 'textarea'] and current_type in ['email', 'url', 'phone']:
                # Converting from structured fields to text
                return str(value)
            elif target_type in ['date', 'boolean', 'address', 'tags'] and current_type in ['text', 'textarea']:
                # Use actual validators with proper configurations
                from .validators import FieldValidator
                from .field_types import FieldType, FIELD_TYPE_CONFIGS
                
                try:
                    # Get the target field type enum
                    target_field_type = getattr(FieldType, target_type.upper())
                    
                    # Create default configuration for the target field type
                    config_class = FIELD_TYPE_CONFIGS.get(target_field_type)
                    default_config = config_class() if config_class else {}
                    
                    # For migration preview, use the configuration from new_config if provided
                    field_config = new_config.get('field_config', {})
                    
                    # Merge with default config
                    if config_class and field_config:
                        try:
                            merged_config = config_class(**field_config)
                        except:
                            merged_config = default_config
                    else:
                        merged_config = default_config
                    
                    # Create validator with proper configuration
                    validator = FieldValidator(target_field_type, merged_config)
                    
                    # Use the validator's validate method for complete validation
                    validation_result = validator.validate(value)
                    
                    if validation_result.is_valid:
                        return validation_result.cleaned_value
                    else:
                        # Validation failed - return None (will become null)
                        return None
                        
                except Exception as e:
                    # If validation fails, return None (will become null)
                    return None
            elif target_type in ['file', 'relation', 'ai_generated'] and current_type in ['text', 'textarea']:
                # For complex field types, show descriptive transformation
                if target_type == 'file':
                    return f"file_from_text_{hash(str(value)) % 1000}.txt"
                elif target_type == 'ai_generated':
                    return f"AI will process: {value}"
                elif target_type == 'relation':
                    return f"Match for: {value}"
            elif current_type in ['select', 'multiselect', 'tags'] and target_type in ['text', 'textarea']:
                # Converting from structured to text
                if isinstance(value, list):
                    return ", ".join(str(v) for v in value)
                return str(value)
            elif current_type == 'address' and target_type in ['text', 'textarea']:
                # Converting address to text
                if isinstance(value, dict):
                    return f"{value.get('address', '')}, {value.get('city', '')}, {value.get('state', '')} {value.get('zip', '')}".strip(', ')
                return str(value)
            elif current_type in ['date', 'datetime'] and target_type in ['text', 'textarea']:
                # Converting date to text
                return str(value)
            elif current_type == 'file' and target_type in ['text', 'textarea']:
                # Converting file to text
                return f"File: {value}" if value else "No file"
            elif current_type == 'boolean' and target_type in ['text', 'textarea']:
                # Converting boolean to text
                return "Yes" if value else "No"
            elif current_type in ['text', 'textarea'] and target_type == 'boolean':
                # Already handled above, but adding for completeness
                return str(value).lower() in ['true', '1', 'yes', 'on', 'y']
            else:
                # For any remaining conversions, show actual value with note
                return f"{value} (converted to {target_type})"
        except:
            return None
    
    @classmethod
    def _determine_migration_complexity(cls, current_type, target_type):
        """Determine migration complexity level"""
        if current_type == target_type:
            return 'simple'
        elif current_type in ['text', 'textarea'] and target_type in ['text', 'textarea']:
            return 'simple'
        elif current_type in ['number', 'decimal'] and target_type in ['number', 'decimal']:
            return 'simple'
        elif 'ai_generated' in [current_type, target_type]:
            return 'very_complex'
        elif current_type in ['text', 'textarea'] and target_type in ['number', 'decimal']:
            return 'complex'
        else:
            return 'moderate'
    
    @classmethod
    def _format_duration(cls, seconds):
        """Format duration in human readable format"""
        if seconds < 60:
            return f"{int(seconds)} seconds"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''}"
    
    @classmethod
    def _estimate_memory_usage(cls, record_count):
        """Estimate memory usage for migration"""
        # Rough estimate: ~1KB per record for processing
        memory_kb = record_count * 1
        if memory_kb < 1024:
            return f"{memory_kb} KB"
        elif memory_kb < 1024 * 1024:
            return f"{int(memory_kb / 1024)} MB"
        else:
            return f"{int(memory_kb / (1024 * 1024))} GB"
    
    @classmethod
    def _field_references_field(cls, source_field, target_field):
        """Check if source field references target field"""
        # Check computed field formulas, AI prompts, etc.
        if source_field.field_type == 'computed' and source_field.field_config:
            formula = source_field.field_config.get('formula', '')
            return target_field.slug in formula
        elif source_field.is_ai_field and source_field.ai_config:
            prompt = source_field.ai_config.get('prompt', '')
            return target_field.slug in prompt or f"{{{target_field.slug}}}" in prompt
        return False
    
    @classmethod
    def _get_relationship_type(cls, source_field, target_field):
        """Determine the type of relationship between fields"""
        if source_field.field_type == 'computed':
            return 'formula_dependency'
        elif source_field.is_ai_field:
            return 'ai_prompt_reference'
        else:
            return 'unknown'
    
    @classmethod
    def _business_rules_reference_field(cls, rules, field):
        """Check if business rules reference a field"""
        if not isinstance(rules, dict):
            return False
        # Check stage requirements, conditional rules, etc.
        stage_reqs = rules.get('stage_requirements', {})
        return any(field.slug in str(req) for req in stage_reqs.values())
    
    @classmethod
    def _ai_config_references_field(cls, ai_config, field):
        """Check if AI config references a field"""
        if not isinstance(ai_config, dict):
            return False
        prompt = ai_config.get('prompt', '')
        return field.slug in prompt or f"{{{field.slug}}}" in prompt