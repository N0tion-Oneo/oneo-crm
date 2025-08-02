"""
Simple form validation engine for basic field validation
Focuses on essential validation types without complex business logic
"""

import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError

from ..models import ValidationRule

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check"""
    is_valid: bool
    field_name: str
    error_message: str = ""
    value_checked: Any = None


@dataclass
class FormValidationResult:
    """Complete form validation result"""
    is_valid: bool
    field_results: Dict[str, List[ValidationResult]]
    errors: Dict[str, List[str]]
    total_errors: int


class SimpleValidationEngine:
    """
    Simple form validation engine for basic field validation
    Handles: required, length, value ranges, email, phone, basic regex
    """
    
    # Basic regex patterns for common validation
    BASIC_PATTERNS = {
        'email': {
            'pattern': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'error': 'Please enter a valid email address'
        },
        'phone': {
            'pattern': r'^\+?[\d\s\-\(\)]{10,}$',
            'error': 'Please enter a valid phone number'
        },
        'phone_us': {
            'pattern': r'^\+?1?[-.\s]?(\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}$',
            'error': 'Please enter a valid US phone number'
        },
    }
    
    def validate_form_data(self, form_data: Dict[str, Any], 
                          field_validations: Dict[str, List[ValidationRule]]) -> FormValidationResult:
        """
        Validate form data against validation rules
        
        Args:
            form_data: Dictionary of field names to values
            field_validations: Dictionary mapping field names to their validation rules
            
        Returns:
            FormValidationResult with validation results
        """
        field_results = {}
        errors = {}
        total_errors = 0
        
        for field_name, validation_rules in field_validations.items():
            field_value = form_data.get(field_name)
            field_validation_results = []
            field_errors = []
            
            for rule in validation_rules:
                if not rule.is_active:
                    continue
                    
                result = self._validate_field_value(field_name, field_value, rule)
                field_validation_results.append(result)
                
                if not result.is_valid:
                    field_errors.append(result.error_message)
                    total_errors += 1
            
            field_results[field_name] = field_validation_results
            if field_errors:
                errors[field_name] = field_errors
        
        return FormValidationResult(
            is_valid=total_errors == 0,
            field_results=field_results,
            errors=errors,
            total_errors=total_errors
        )
    
    def _validate_field_value(self, field_name: str, value: Any, rule: ValidationRule) -> ValidationResult:
        """Validate a single field value against a validation rule"""
        try:
            if rule.rule_type == 'required':
                return self._validate_required(field_name, value, rule)
            elif rule.rule_type == 'min_length':
                return self._validate_min_length(field_name, value, rule)
            elif rule.rule_type == 'max_length':
                return self._validate_max_length(field_name, value, rule)
            elif rule.rule_type == 'min_value':
                return self._validate_min_value(field_name, value, rule)
            elif rule.rule_type == 'max_value':
                return self._validate_max_value(field_name, value, rule)
            elif rule.rule_type == 'email':
                return self._validate_email(field_name, value, rule)
            elif rule.rule_type == 'phone':
                return self._validate_phone(field_name, value, rule)
            elif rule.rule_type == 'regex':
                return self._validate_regex(field_name, value, rule)
            else:
                logger.warning(f"Unsupported validation rule type: {rule.rule_type}")
                return ValidationResult(
                    is_valid=True,
                    field_name=field_name,
                    value_checked=value
                )
        except Exception as e:
            logger.error(f"Error validating field {field_name} with rule {rule.rule_type}: {e}")
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                error_message=f"Validation error: {str(e)}",
                value_checked=value
            )
    
    def _validate_required(self, field_name: str, value: Any, rule: ValidationRule) -> ValidationResult:
        """Validate required field"""
        is_valid = value is not None and str(value).strip() != ""
        
        return ValidationResult(
            is_valid=is_valid,
            field_name=field_name,
            error_message=rule.error_message if not is_valid else "",
            value_checked=value
        )
    
    def _validate_min_length(self, field_name: str, value: Any, rule: ValidationRule) -> ValidationResult:
        """Validate minimum length"""
        if value is None:
            return ValidationResult(is_valid=True, field_name=field_name, value_checked=value)
        
        min_length = rule.configuration.get('min_length', 0)
        str_value = str(value)
        is_valid = len(str_value) >= min_length
        
        return ValidationResult(
            is_valid=is_valid,
            field_name=field_name,
            error_message=rule.error_message if not is_valid else "",
            value_checked=value
        )
    
    def _validate_max_length(self, field_name: str, value: Any, rule: ValidationRule) -> ValidationResult:
        """Validate maximum length"""
        if value is None:
            return ValidationResult(is_valid=True, field_name=field_name, value_checked=value)
        
        max_length = rule.configuration.get('max_length', float('inf'))
        str_value = str(value)
        is_valid = len(str_value) <= max_length
        
        return ValidationResult(
            is_valid=is_valid,
            field_name=field_name,
            error_message=rule.error_message if not is_valid else "",
            value_checked=value
        )
    
    def _validate_min_value(self, field_name: str, value: Any, rule: ValidationRule) -> ValidationResult:
        """Validate minimum value for numeric fields"""
        if value is None:
            return ValidationResult(is_valid=True, field_name=field_name, value_checked=value)
        
        try:
            numeric_value = float(value)
            min_value = rule.configuration.get('min_value', float('-inf'))
            is_valid = numeric_value >= min_value
            
            return ValidationResult(
                is_valid=is_valid,
                field_name=field_name,
                error_message=rule.error_message if not is_valid else "",
                value_checked=value
            )
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                error_message="Value must be a number",
                value_checked=value
            )
    
    def _validate_max_value(self, field_name: str, value: Any, rule: ValidationRule) -> ValidationResult:
        """Validate maximum value for numeric fields"""
        if value is None:
            return ValidationResult(is_valid=True, field_name=field_name, value_checked=value)
        
        try:
            numeric_value = float(value)
            max_value = rule.configuration.get('max_value', float('inf'))
            is_valid = numeric_value <= max_value
            
            return ValidationResult(
                is_valid=is_valid,
                field_name=field_name,
                error_message=rule.error_message if not is_valid else "",
                value_checked=value
            )
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                error_message="Value must be a number",
                value_checked=value
            )
    
    def _validate_email(self, field_name: str, value: Any, rule: ValidationRule) -> ValidationResult:
        """Validate email format"""
        if value is None or str(value).strip() == "":
            return ValidationResult(is_valid=True, field_name=field_name, value_checked=value)
        
        try:
            validate_email(str(value))
            is_valid = True
        except DjangoValidationError:
            is_valid = False
        
        return ValidationResult(
            is_valid=is_valid,
            field_name=field_name,
            error_message=rule.error_message if not is_valid else "",
            value_checked=value
        )
    
    def _validate_phone(self, field_name: str, value: Any, rule: ValidationRule) -> ValidationResult:
        """Validate phone number format"""
        if value is None or str(value).strip() == "":
            return ValidationResult(is_valid=True, field_name=field_name, value_checked=value)
        
        str_value = str(value).strip()
        
        # Use custom pattern if provided, otherwise use basic phone pattern
        pattern = rule.configuration.get('pattern')
        if not pattern:
            phone_type = rule.configuration.get('phone_type', 'phone')
            pattern_config = self.BASIC_PATTERNS.get(phone_type, self.BASIC_PATTERNS['phone'])
            pattern = pattern_config['pattern']
        
        is_valid = bool(re.match(pattern, str_value))
        
        return ValidationResult(
            is_valid=is_valid,
            field_name=field_name,
            error_message=rule.error_message if not is_valid else "",
            value_checked=value
        )
    
    def _validate_regex(self, field_name: str, value: Any, rule: ValidationRule) -> ValidationResult:
        """Validate using custom regex pattern"""
        if value is None or str(value).strip() == "":
            return ValidationResult(is_valid=True, field_name=field_name, value_checked=value)
        
        pattern = rule.configuration.get('pattern')
        if not pattern:
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                error_message="No regex pattern configured",
                value_checked=value
            )
        
        try:
            str_value = str(value)
            is_valid = bool(re.match(pattern, str_value))
            
            return ValidationResult(
                is_valid=is_valid,
                field_name=field_name,
                error_message=rule.error_message if not is_valid else "",
                value_checked=value
            )
        except re.error as e:
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                error_message=f"Invalid regex pattern: {str(e)}",
                value_checked=value
            )


def validate_form_simple(form_data: Dict[str, Any], 
                        field_validations: Dict[str, List[ValidationRule]]) -> FormValidationResult:
    """
    Convenience function for simple form validation
    
    Args:
        form_data: Dictionary of field names to values
        field_validations: Dictionary mapping field names to their validation rules
        
    Returns:
        FormValidationResult with validation results
    """
    engine = SimpleValidationEngine()
    return engine.validate_form_data(form_data, field_validations)