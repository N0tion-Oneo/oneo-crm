"""
Unified Validation System
All pipeline validation logic consolidated in this directory
"""

def __getattr__(name):
    """Lazy import to avoid circular import issues"""
    
    # Core validation classes and functions
    if name in ('ValidationResult', 'FieldValidator', 'validate_record_data', 
                '_evaluate_condition', '_evaluate_conditional_rules'):
        from .data_validator import (
            ValidationResult, FieldValidator, validate_record_data,
            _evaluate_condition, _evaluate_conditional_rules
        )
        if name == 'ValidationResult':
            return ValidationResult
        elif name == 'FieldValidator':
            return FieldValidator
        elif name == 'validate_record_data':
            return validate_record_data
        elif name == '_evaluate_condition':
            return _evaluate_condition
        elif name == '_evaluate_conditional_rules':
            return _evaluate_conditional_rules
    
    # Field operations and migration validation
    elif name in ('AdvancedFieldValidator', 'FieldValidationResult'):
        from .field_validator import (
            FieldValidator as AdvancedFieldValidator,
            FieldValidationResult
        )
        if name == 'AdvancedFieldValidator':
            return AdvancedFieldValidator
        elif name == 'FieldValidationResult':
            return FieldValidationResult
    
    # Migration system (lazy loaded to avoid circular imports)
    elif name == 'MigrationValidator':
        from .migration_validator import MigrationValidator
        return MigrationValidator
    elif name in ('DataMigrator', 'MigrationResult'):
        from .data_migrator import DataMigrator, MigrationResult
        if name == 'DataMigrator':
            return DataMigrator
        elif name == 'MigrationResult':
            return MigrationResult
    
    # Record validation system
    elif name in ('RecordValidator', 'RecordValidationResult'):
        from .record_validator import RecordValidator, RecordValidationResult
        if name == 'RecordValidator':
            return RecordValidator
        elif name == 'RecordValidationResult':
            return RecordValidationResult
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    # Core data validation
    'ValidationResult',
    'FieldValidator', 
    'validate_record_data',
    '_evaluate_condition',
    '_evaluate_conditional_rules',
    
    # Advanced field operations
    'AdvancedFieldValidator',
    'FieldValidationResult',
    
    # Record validation system
    'RecordValidator',
    'RecordValidationResult',
    
    # Migration system
    'MigrationValidator',
    'DataMigrator',
    'MigrationResult',
]