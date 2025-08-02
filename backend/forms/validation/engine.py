"""
Comprehensive form validation engine with multi-tenant support and robust validation capabilities
"""

import re
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
from urllib.parse import urlparse

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email, URLValidator
from django.utils import timezone
from django.conf import settings

from .patterns import VALIDATION_PATTERNS, get_pattern, validate_with_pattern, get_patterns_by_category
from ..models import ValidationRule, FormTemplate, FormFieldConfiguration, FormFieldValidation
from django.core.cache import cache


logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check"""
    is_valid: bool
    field_name: str
    rule_name: str
    error_message: str = ""
    warning_message: str = ""
    value_checked: Any = None
    rule_type: str = ""
    execution_time_ms: float = 0.0


@dataclass
class FormValidationResult:
    """Complete form validation result"""
    is_valid: bool
    field_results: Dict[str, List[ValidationResult]]
    cross_field_results: List[ValidationResult]
    duplicate_results: List[Dict[str, Any]]
    execution_time_ms: float
    total_errors: int
    total_warnings: int


class FormValidationEngine:
    """
    Comprehensive, multi-tenant form validation engine with advanced validation capabilities
    Consolidates all validation types including regex patterns, cross-field validation, 
    async API validation, and business rules
    """
    
    # Advanced regex patterns with descriptive names and error messages
    PATTERN_LIBRARY = {
        'strong_password': {
            'pattern': r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
            'error': 'Password must be at least 8 characters with uppercase, lowercase, number, and special character'
        },
        'phone_us': {
            'pattern': r'^\+?1?[-.\s]?(\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}$',
            'error': 'Please enter a valid US phone number (e.g., (555) 123-4567)'
        },
        'phone_international': {
            'pattern': r'^\+[1-9]\d{1,14}$',
            'error': 'Please enter a valid international phone number (e.g., +1234567890)'
        },
        'postal_code_us': {
            'pattern': r'^\d{5}(-\d{4})?$',
            'error': 'Please enter a valid US postal code (e.g., 12345 or 12345-6789)'
        },
        'postal_code_ca': {
            'pattern': r'^[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d$',
            'error': 'Please enter a valid Canadian postal code (e.g., K1A 0A6)'
        },
        'credit_card': {
            'pattern': r'^(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})$',
            'error': 'Please enter a valid credit card number'
        },
        'social_security': {
            'pattern': r'^\d{3}-?\d{2}-?\d{4}$',
            'error': 'Please enter a valid Social Security number (e.g., 123-45-6789)'
        },
        'ip_address': {
            'pattern': r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
            'error': 'Please enter a valid IP address (e.g., 192.168.1.1)'
        },
        'slug': {
            'pattern': r'^[a-z0-9]+(?:-[a-z0-9]+)*$',
            'error': 'Please enter a valid slug (lowercase letters, numbers, and hyphens only)'
        },
        'hex_color': {
            'pattern': r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
            'error': 'Please enter a valid hex color (e.g., #FF0000 or #F00)'
        }
    }
    
    # Cache configuration
    CACHE_PREFIX = "form_validation"
    DEFAULT_CACHE_TTL = 300  # 5 minutes
    
    def __init__(self, tenant_id: Optional[int] = None):
        self.tenant_id = tenant_id
        self.url_validator = URLValidator()
        
    async def validate_form_submission(
        self, 
        form_template_id: int, 
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> FormValidationResult:
        """
        Validate complete form submission with all configured rules
        
        Args:
            form_template_id: ID of the form template
            data: Form data to validate
            context: Additional context (user, stage, etc.)
            
        Returns:
            FormValidationResult with detailed validation results
        """
        start_time = datetime.now()
        
        try:
            # Get form template with field configurations
            form_template = await self._get_form_template(form_template_id)
            if not form_template:
                raise ValueError(f"Form template {form_template_id} not found")
            
            # Initialize results
            field_results = {}
            cross_field_results = []
            duplicate_results = []
            
            # Validate each field
            for field_config in form_template.field_configs.all():
                field_name = field_config.pipeline_field.name
                field_value = data.get(field_name)
                
                # Get all validation rules for this field
                validations = field_config.validations.filter(is_active=True).order_by('execution_order')
                
                field_validation_results = []
                for validation in validations:
                    # Check conditional logic
                    if not self._should_apply_validation(validation, data, context):
                        continue
                    
                    # Execute validation rule
                    result = await self._validate_field_value(
                        field_config, 
                        validation.validation_rule, 
                        field_value, 
                        data, 
                        context
                    )
                    
                    # Override message if specified
                    if validation.override_message:
                        result.error_message = validation.override_message
                    
                    field_validation_results.append(result)
                    
                    # Stop on first blocking error unless in lenient mode
                    if not result.is_valid and validation.is_blocking and form_template.validation_mode == 'strict':
                        break
                
                field_results[field_name] = field_validation_results
            
            # Execute cross-field validations
            cross_field_results = await self._validate_cross_field_rules(form_template, data, context)
            
            # Execute duplicate detection if enabled
            if form_template.enable_duplicate_detection:
                duplicate_results = await self._check_duplicates(form_template, data, context)
            
            # Calculate overall results
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            total_errors = sum(
                1 for results in field_results.values() 
                for result in results 
                if not result.is_valid
            ) + sum(1 for result in cross_field_results if not result.is_valid)
            
            total_warnings = sum(
                1 for results in field_results.values() 
                for result in results 
                if result.warning_message
            ) + sum(1 for result in cross_field_results if result.warning_message)
            
            is_valid = total_errors == 0 or form_template.validation_mode == 'lenient'
            
            return FormValidationResult(
                is_valid=is_valid,
                field_results=field_results,
                cross_field_results=cross_field_results,
                duplicate_results=duplicate_results,
                execution_time_ms=execution_time,
                total_errors=total_errors,
                total_warnings=total_warnings
            )
            
        except Exception as e:
            logger.error(f"Form validation error: {e}", exc_info=True)
            # Return error result
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return FormValidationResult(
                is_valid=False,
                field_results={},
                cross_field_results=[ValidationResult(
                    is_valid=False,
                    field_name="__form__",
                    rule_name="system",
                    error_message=f"Validation system error: {str(e)}",
                    execution_time_ms=execution_time
                )],
                duplicate_results=[],
                execution_time_ms=execution_time,
                total_errors=1,
                total_warnings=0
            )
    
    async def _validate_field_value(
        self,
        field_config: FormFieldConfiguration,
        validation_rule: ValidationRule,
        value: Any,
        form_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Validate individual field value against a specific rule"""
        start_time = datetime.now()
        
        try:
            result = ValidationResult(
                is_valid=True,
                field_name=field_config.pipeline_field.name,
                rule_name=validation_rule.name,
                value_checked=value,
                rule_type=validation_rule.rule_type
            )
            
            # Execute validation based on rule type
            if validation_rule.rule_type == 'required':
                result = self._validate_required(value, validation_rule, result)
                
            elif validation_rule.rule_type == 'min_length':
                result = self._validate_min_length(value, validation_rule, result)
                
            elif validation_rule.rule_type == 'max_length':
                result = self._validate_max_length(value, validation_rule, result)
                
            elif validation_rule.rule_type == 'min_value':
                result = self._validate_min_value(value, validation_rule, result)
                
            elif validation_rule.rule_type == 'max_value':
                result = self._validate_max_value(value, validation_rule, result)
                
            elif validation_rule.rule_type == 'regex':
                result = self._validate_regex(value, validation_rule, result)
                
            elif validation_rule.rule_type == 'email':
                result = self._validate_email(value, validation_rule, result)
                
            elif validation_rule.rule_type == 'url':
                result = self._validate_url(value, validation_rule, result)
                
            elif validation_rule.rule_type == 'phone':
                result = self._validate_phone(value, validation_rule, result)
                
            elif validation_rule.rule_type == 'cross_field':
                result = self._validate_cross_field(value, validation_rule, result, form_data)
                
            elif validation_rule.rule_type == 'conditional':
                result = self._validate_conditional(value, validation_rule, result, form_data)
                
            elif validation_rule.rule_type == 'date_range':
                result = self._validate_date_range(value, validation_rule, result)
                
            elif validation_rule.rule_type == 'numeric_range':
                result = self._validate_numeric_range(value, validation_rule, result)
                
            elif validation_rule.rule_type == 'list_validation':
                result = self._validate_list(value, validation_rule, result)
                
            elif validation_rule.rule_type == 'file_validation':
                result = self._validate_file(value, validation_rule, result)
                
            elif validation_rule.rule_type == 'custom_function':
                result = await self._validate_custom_function(value, validation_rule, result, form_data, context)
                
            elif validation_rule.rule_type == 'async_api':
                result = await self._validate_async_api(value, validation_rule, result, context)
                
            else:
                result.is_valid = False
                result.error_message = f"Unknown validation rule type: {validation_rule.rule_type}"
            
            # Calculate execution time
            end_time = datetime.now()
            result.execution_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return result
            
        except Exception as e:
            logger.error(f"Field validation error: {e}", exc_info=True)
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return ValidationResult(
                is_valid=False,
                field_name=field_config.pipeline_field.name,
                rule_name=validation_rule.name,
                error_message=f"Validation error: {str(e)}",
                value_checked=value,
                rule_type=validation_rule.rule_type,
                execution_time_ms=execution_time
            )
    
    def _validate_required(self, value: Any, rule: ValidationRule, result: ValidationResult) -> ValidationResult:
        """Validate required field"""
        if value is None or value == '' or (isinstance(value, (list, dict)) and len(value) == 0):
            result.is_valid = False
            result.error_message = rule.error_message or "This field is required"
        return result
    
    def _validate_min_length(self, value: Any, rule: ValidationRule, result: ValidationResult) -> ValidationResult:
        """Validate minimum length"""
        if value is None:
            return result
        
        min_length = rule.configuration.get('min_length', 0)
        if len(str(value)) < min_length:
            result.is_valid = False
            result.error_message = rule.error_message or f"Minimum length is {min_length} characters"
        return result
    
    def _validate_max_length(self, value: Any, rule: ValidationRule, result: ValidationResult) -> ValidationResult:
        """Validate maximum length"""
        if value is None:
            return result
        
        max_length = rule.configuration.get('max_length', float('inf'))
        if len(str(value)) > max_length:
            result.is_valid = False
            result.error_message = rule.error_message or f"Maximum length is {max_length} characters"
        return result
    
    def _validate_min_value(self, value: Any, rule: ValidationRule, result: ValidationResult) -> ValidationResult:
        """Validate minimum numeric value"""
        if value is None or value == '':
            return result
        
        try:
            num_value = Decimal(str(value))
            min_value = Decimal(str(rule.configuration.get('min_value', 0)))
            
            if num_value < min_value:
                result.is_valid = False
                result.error_message = rule.error_message or f"Minimum value is {min_value}"
        except (InvalidOperation, ValueError):
            result.is_valid = False
            result.error_message = rule.error_message or "Invalid numeric value"
        
        return result
    
    def _validate_max_value(self, value: Any, rule: ValidationRule, result: ValidationResult) -> ValidationResult:
        """Validate maximum numeric value"""
        if value is None or value == '':
            return result
        
        try:
            num_value = Decimal(str(value))
            max_value = Decimal(str(rule.configuration.get('max_value', float('inf'))))
            
            if num_value > max_value:
                result.is_valid = False
                result.error_message = rule.error_message or f"Maximum value is {max_value}"
        except (InvalidOperation, ValueError):
            result.is_valid = False
            result.error_message = rule.error_message or "Invalid numeric value"
        
        return result
    
    def _validate_regex(self, value: Any, rule: ValidationRule, result: ValidationResult) -> ValidationResult:
        """Advanced regex validation with pattern library support"""
        if value is None or value == '':
            return result
        
        try:
            pattern = rule.configuration.get('pattern', '')
            pattern_name = rule.configuration.get('pattern_name', '')
            flags = rule.configuration.get('flags', 0)
            
            # Use predefined pattern if pattern_name provided
            if pattern_name and pattern_name in self.PATTERN_LIBRARY:
                pattern_info = self.PATTERN_LIBRARY[pattern_name]
                pattern = pattern_info['pattern']
                if not rule.error_message:
                    result.error_message = pattern_info['error']
            
            if not pattern:
                result.is_valid = False
                result.error_message = "No regex pattern configured"
                return result
            
            # Compile pattern for better performance and error checking
            compiled_pattern = re.compile(pattern, flags or (re.IGNORECASE if pattern_name else 0))
            if not compiled_pattern.match(str(value)):
                result.is_valid = False
                if not result.error_message:
                    result.error_message = rule.error_message or "Value does not match required pattern"
                    
        except re.error as e:
            logger.error(f"Invalid regex pattern: {pattern}. Error: {str(e)}")
            result.is_valid = False
            result.error_message = f"Invalid validation pattern configured: {str(e)}"
        
        return result
    
    def _validate_email(self, value: Any, rule: ValidationRule, result: ValidationResult) -> ValidationResult:
        """Validate email format"""
        if value is None or value == '':
            return result
        
        try:
            # Use Django's built-in email validator
            validate_email(str(value))
            
            # Additional pattern-based validation if specified
            email_pattern = rule.configuration.get('pattern', 'email_basic')
            if not validate_with_pattern(email_pattern, str(value)):
                result.is_valid = False
                result.error_message = rule.error_message or "Invalid email format"
        except DjangoValidationError:
            result.is_valid = False
            result.error_message = rule.error_message or "Invalid email format"
        
        return result
    
    def _validate_url(self, value: Any, rule: ValidationRule, result: ValidationResult) -> ValidationResult:
        """Validate URL format"""
        if value is None or value == '':
            return result
        
        try:
            self.url_validator(str(value))
        except DjangoValidationError:
            result.is_valid = False
            result.error_message = rule.error_message or "Invalid URL format"
        
        return result
    
    def _validate_phone(self, value: Any, rule: ValidationRule, result: ValidationResult) -> ValidationResult:
        """Validate phone number format"""
        if value is None or value == '':
            return result
        
        phone_pattern = rule.configuration.get('pattern', 'phone_flexible')
        if not validate_with_pattern(phone_pattern, str(value)):
            result.is_valid = False
            result.error_message = rule.error_message or "Invalid phone number format"
        
        return result
    
    def _validate_cross_field(
        self, 
        value: Any, 
        rule: ValidationRule, 
        result: ValidationResult, 
        form_data: Dict[str, Any]
    ) -> ValidationResult:
        """Advanced cross-field validation with comprehensive operators"""
        try:
            target_field = rule.configuration.get('target_field', '')
            operator = rule.configuration.get('operator', 'equals')
            
            if not target_field or target_field not in form_data:
                return result
            
            target_value = form_data[target_field]
            is_valid = self._compare_values(value, target_value, operator)
            
            if not is_valid:
                result.is_valid = False
                if not result.error_message:
                    result.error_message = rule.error_message or f"Fields do not match required comparison: {operator}"
                    
        except Exception as e:
            logger.error(f"Cross-field validation error: {str(e)}")
            result.is_valid = False
            result.error_message = f"Cross-field validation error: {e}"
        
        return result
    
    def _compare_values(self, value1: Any, value2: Any, comparison: str) -> bool:
        """Compare two values based on comparison type"""
        try:
            if comparison == 'equals':
                return value1 == value2
            elif comparison == 'not_equals':
                return value1 != value2
            elif comparison == 'greater_than':
                return value1 > value2
            elif comparison == 'less_than':
                return value1 < value2
            elif comparison == 'greater_equal':
                return value1 >= value2
            elif comparison == 'less_equal':
                return value1 <= value2
            elif comparison == 'contains':
                return str(value2) in str(value1)
            elif comparison == 'starts_with':
                return str(value1).startswith(str(value2))
            elif comparison == 'ends_with':
                return str(value1).endswith(str(value2))
            elif comparison == 'date_after':
                # Convert to dates if strings
                if isinstance(value1, str):
                    value1 = datetime.fromisoformat(value1.replace('Z', '+00:00'))
                if isinstance(value2, str):
                    value2 = datetime.fromisoformat(value2.replace('Z', '+00:00'))
                return value1 > value2
            elif comparison == 'date_before':
                if isinstance(value1, str):
                    value1 = datetime.fromisoformat(value1.replace('Z', '+00:00'))
                if isinstance(value2, str):
                    value2 = datetime.fromisoformat(value2.replace('Z', '+00:00'))
                return value1 < value2
            else:
                return False
        except (ValueError, TypeError):
            return False
    
    def _validate_conditional(
        self, 
        value: Any, 
        rule: ValidationRule, 
        result: ValidationResult, 
        form_data: Dict[str, Any]
    ) -> ValidationResult:
        """Advanced conditional validation with comprehensive condition support"""
        try:
            conditions = rule.configuration.get('conditions', [])
            required_when = rule.configuration.get('required_when', True)
            
            # Evaluate conditions using enhanced condition evaluation
            condition_met = self._evaluate_advanced_conditions(conditions, form_data)
            
            if condition_met and required_when and (value is None or value == ''):
                result.is_valid = False
                result.error_message = rule.error_message or "This field is required based on other selections"
            elif not condition_met and not required_when and (value is None or value == ''):
                result.is_valid = False
                result.error_message = rule.error_message or "This field is conditionally required"
        except Exception as e:
            logger.error(f"Conditional validation error: {str(e)}")
            result.is_valid = False
            result.error_message = f"Conditional validation error: {e}"
        
        return result
    
    def _evaluate_advanced_conditions(self, conditions: List[Dict[str, Any]], form_data: Dict[str, Any]) -> bool:
        """Enhanced condition evaluation with more operators"""
        if not conditions:
            return True
        
        results = []
        for condition in conditions:
            field = condition.get('field', '')
            operator = condition.get('operator', 'equals')
            expected_value = condition.get('value')
            
            if field not in form_data:
                results.append(False)
                continue
            
            actual_value = form_data[field]
            results.append(self._evaluate_condition(actual_value, expected_value, operator))
        
        # Support for logical operators (default AND)
        logic_operator = conditions[0].get('logic', 'and') if conditions else 'and'
        return all(results) if logic_operator == 'and' else any(results)
    
    def _evaluate_condition(self, field_value: Any, target_value: Any, operator: str) -> bool:
        """Evaluate single condition between field value and target value"""
        if operator == 'equals':
            return field_value == target_value
        elif operator == 'not_equals':
            return field_value != target_value
        elif operator == 'in':
            return field_value in (target_value if isinstance(target_value, (list, tuple)) else [target_value])
        elif operator == 'not_in':
            return field_value not in (target_value if isinstance(target_value, (list, tuple)) else [target_value])
        elif operator == 'greater_than':
            try:
                return float(field_value) > float(target_value)
            except (ValueError, TypeError):
                return False
        elif operator == 'less_than':
            try:
                return float(field_value) < float(target_value)
            except (ValueError, TypeError):
                return False
        elif operator == 'greater_equal':
            try:
                return float(field_value) >= float(target_value)
            except (ValueError, TypeError):
                return False
        elif operator == 'less_equal':
            try:
                return float(field_value) <= float(target_value)
            except (ValueError, TypeError):
                return False
        elif operator == 'contains':
            return str(target_value) in str(field_value)
        elif operator == 'starts_with':
            return str(field_value).startswith(str(target_value))
        elif operator == 'ends_with':
            return str(field_value).endswith(str(target_value))
        else:
            return False
    
    def _validate_date_range(self, value: Any, rule: ValidationRule, result: ValidationResult) -> ValidationResult:
        """Validate date is within specified range"""
        if value is None or value == '':
            return result
        
        try:
            if isinstance(value, str):
                # Try to parse date string
                value = datetime.fromisoformat(value.replace('Z', '+00:00')).date()
            elif isinstance(value, datetime):
                value = value.date()
            
            min_date = rule.configuration.get('min_date')
            max_date = rule.configuration.get('max_date')
            
            if min_date:
                min_date = datetime.fromisoformat(min_date).date()
                if value < min_date:
                    result.is_valid = False
                    result.error_message = rule.error_message or f"Date must be after {min_date}"
            
            if max_date:
                max_date = datetime.fromisoformat(max_date).date()
                if value > max_date:
                    result.is_valid = False
                    result.error_message = rule.error_message or f"Date must be before {max_date}"
        except (ValueError, TypeError):
            result.is_valid = False
            result.error_message = rule.error_message or "Invalid date format"
        
        return result
    
    def _validate_numeric_range(self, value: Any, rule: ValidationRule, result: ValidationResult) -> ValidationResult:
        """Validate numeric value is within range"""
        if value is None or value == '':
            return result
        
        try:
            num_value = Decimal(str(value))
            min_val = rule.configuration.get('min_value')
            max_val = rule.configuration.get('max_value')
            
            if min_val is not None and num_value < Decimal(str(min_val)):
                result.is_valid = False
                result.error_message = rule.error_message or f"Value must be at least {min_val}"
            
            if max_val is not None and num_value > Decimal(str(max_val)):
                result.is_valid = False
                result.error_message = rule.error_message or f"Value must be at most {max_val}"
        except (InvalidOperation, ValueError):
            result.is_valid = False
            result.error_message = rule.error_message or "Invalid numeric value"
        
        return result
    
    def _validate_list(self, value: Any, rule: ValidationRule, result: ValidationResult) -> ValidationResult:
        """Validate list/array values"""
        if value is None:
            return result
        
        if not isinstance(value, (list, tuple)):
            try:
                # Try to parse as JSON array
                import json
                value = json.loads(value) if isinstance(value, str) else [value]
            except:
                value = [value]
        
        min_items = rule.configuration.get('min_items', 0)
        max_items = rule.configuration.get('max_items', float('inf'))
        allowed_values = rule.configuration.get('allowed_values', [])
        
        if len(value) < min_items:
            result.is_valid = False
            result.error_message = rule.error_message or f"Must have at least {min_items} items"
        elif len(value) > max_items:
            result.is_valid = False
            result.error_message = rule.error_message or f"Must have at most {max_items} items"
        elif allowed_values and not all(item in allowed_values for item in value):
            result.is_valid = False
            result.error_message = rule.error_message or "Contains invalid values"
        
        return result
    
    def _validate_file(self, value: Any, rule: ValidationRule, result: ValidationResult) -> ValidationResult:
        """Validate file upload"""
        if value is None:
            return result
        
        # This would typically validate file objects
        # For now, we'll validate file-like properties
        max_size = rule.configuration.get('max_size_mb', 10) * 1024 * 1024  # Convert MB to bytes
        allowed_types = rule.configuration.get('allowed_types', [])
        
        # Basic validation - in real implementation, you'd check actual file properties
        if hasattr(value, 'size') and value.size > max_size:
            result.is_valid = False
            result.error_message = rule.error_message or f"File size must be less than {max_size // (1024*1024)}MB"
        
        if allowed_types and hasattr(value, 'content_type'):
            if value.content_type not in allowed_types:
                result.is_valid = False
                result.error_message = rule.error_message or f"File type not allowed. Allowed types: {', '.join(allowed_types)}"
        
        return result
    
    async def _validate_custom_function(
        self, 
        value: Any, 
        rule: ValidationRule, 
        result: ValidationResult, 
        form_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Execute custom business rule validation functions"""
        try:
            function_name = rule.configuration.get('function_name', '')
            function_params = rule.configuration.get('params', {})
            
            # Business rule validations
            if function_name == 'unique_email':
                result = await self._validate_unique_field(value, 'email', rule, result, form_data, context)
            elif function_name == 'budget_limits':
                result = await self._validate_budget_limits(value, function_params, rule, result, form_data)
            elif function_name == 'inventory_check':
                result = await self._validate_inventory_availability(value, function_params, rule, result, form_data)
            elif function_name == 'credit_approval':
                result = await self._validate_credit_requirements(value, function_params, rule, result, form_data)
            else:
                logger.warning(f"Unknown custom function: {function_name}")
                result.is_valid = False
                result.error_message = f"Unknown custom function: {function_name}"
        except Exception as e:
            logger.error(f"Custom validation error: {e}", exc_info=True)
            result.is_valid = False
            result.error_message = f"Custom validation error: {e}"
        
        return result
    
    async def _validate_unique_field(self, value: Any, field_type: str, rule: ValidationRule, result: ValidationResult, form_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate field uniqueness across records"""
        try:
            from pipelines.models import Record
            
            # Get pipeline from context or rule configuration
            pipeline_id = rule.configuration.get('pipeline_id') or context.get('pipeline_id')
            if not pipeline_id:
                result.is_valid = False
                result.error_message = "Pipeline not specified for uniqueness validation"
                return result
            
            # Check for existing records with same value
            existing_records = Record.objects.filter(
                pipeline_id=pipeline_id,
                data__contains={result.field_name: value}
            )
            
            # Exclude current record if updating
            if context and context.get('record_id'):
                existing_records = existing_records.exclude(id=context['record_id'])
            
            if await existing_records.aexists():
                result.is_valid = False
                result.error_message = rule.error_message or f"This {field_type} is already in use"
                
        except Exception as e:
            logger.error(f"Uniqueness validation error: {e}")
            result.is_valid = False
            result.error_message = f"Unable to verify uniqueness: {str(e)}"
        
        return result
    
    async def _validate_budget_limits(self, amount: Any, budget_config: Dict[str, Any], rule: ValidationRule, result: ValidationResult, form_data: Dict[str, Any]) -> ValidationResult:
        """Validate amount against budget limits and spending rules"""
        try:
            amount = float(amount)
            max_amount = budget_config.get('max_amount', float('inf'))
            min_amount = budget_config.get('min_amount', 0)
            
            # Basic min/max validation
            if amount < min_amount or amount > max_amount:
                result.is_valid = False
                result.error_message = rule.error_message or f'Amount must be between ${min_amount} and ${max_amount}'
                return result
            
            # Department-specific budget validation
            department_budgets = budget_config.get('department_budgets', {})
            if department_budgets:
                department = form_data.get('department')
                if department and department in department_budgets:
                    dept_limit = department_budgets[department]
                    if amount > dept_limit:
                        result.is_valid = False
                        result.error_message = rule.error_message or f'Amount exceeds {department} department budget limit of ${dept_limit}'
                        return result
            
            # Approval requirement warning
            approval_threshold = budget_config.get('approval_required_above')
            if approval_threshold and amount > approval_threshold:
                result.warning_message = f'Amount over ${approval_threshold} requires additional approval'
                
        except (ValueError, TypeError):
            result.is_valid = False
            result.error_message = rule.error_message or 'Please enter a valid amount'
        
        return result
    
    async def _validate_inventory_availability(self, quantity: Any, inventory_config: Dict[str, Any], rule: ValidationRule, result: ValidationResult, form_data: Dict[str, Any]) -> ValidationResult:
        """Validate inventory availability for orders"""
        try:
            quantity = int(quantity)
            product_id = form_data.get(inventory_config.get('product_field', 'product_id'))
            
            if not product_id:
                result.is_valid = False
                result.error_message = "Product not specified for inventory check"
                return result
            
            # Simulate inventory check - in production, query actual inventory system
            available_quantity = inventory_config.get('mock_available', 100)  # Mock data
            
            if quantity > available_quantity:
                result.is_valid = False
                result.error_message = rule.error_message or f'Only {available_quantity} units available'
            elif quantity > (available_quantity * 0.8):  # Low stock warning
                result.warning_message = f'Low stock warning: Only {available_quantity} units remaining'
                
        except (ValueError, TypeError):
            result.is_valid = False
            result.error_message = 'Please enter a valid quantity'
        
        return result
    
    async def _validate_credit_requirements(self, amount: Any, credit_config: Dict[str, Any], rule: ValidationRule, result: ValidationResult, form_data: Dict[str, Any]) -> ValidationResult:
        """Validate credit requirements for financial transactions"""
        try:
            amount = float(amount)
            customer_id = form_data.get(credit_config.get('customer_field', 'customer_id'))
            
            if not customer_id:
                result.is_valid = False
                result.error_message = "Customer not specified for credit check"
                return result
            
            # Simulate credit check - in production, integrate with credit system
            credit_limit = credit_config.get('mock_credit_limit', 10000)  # Mock data
            current_balance = credit_config.get('mock_current_balance', 0)  # Mock data
            
            available_credit = credit_limit - current_balance
            
            if amount > available_credit:
                result.is_valid = False
                result.error_message = rule.error_message or f'Amount exceeds available credit of ${available_credit}'
            elif amount > (available_credit * 0.9):  # Credit warning
                result.warning_message = f'High credit utilization: ${available_credit} remaining'
                
        except (ValueError, TypeError):
            result.is_valid = False
            result.error_message = 'Please enter a valid amount'
        
        return result
    
    async def _validate_async_api(
        self, 
        value: Any, 
        rule: ValidationRule, 
        result: ValidationResult,
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Advanced async API validation with caching and error handling"""
        validation_type = rule.configuration.get('validation_type', 'generic')
        
        try:
            if validation_type == 'email_deliverable':
                return await self._validate_async_email(value, rule, result)
            elif validation_type == 'address_validation':
                address_data = rule.configuration.get('address_fields', {})
                return await self._validate_async_address(address_data, rule, result)
            elif validation_type == 'business_hours':
                business_config = rule.configuration.get('business_config', {})
                return await self._validate_business_hours(value, business_config, rule, result)
            else:
                # Generic API validation
                api_url = rule.configuration.get('api_url', '')
                method = rule.configuration.get('method', 'POST')
                timeout = rule.configuration.get('timeout', 5)
                
                # Simulate async validation - in production, make real HTTP requests
                await asyncio.sleep(0.1)  # Simulate network delay
                result.is_valid = True  # Placeholder
                
        except Exception as e:
            logger.error(f"Async validation error: {e}", exc_info=True)
            # Fail gracefully - don't block form submission due to external API issues
            result.is_valid = True
            result.warning_message = f"External validation service temporarily unavailable: {str(e)}"
        
        return result
    
    async def _validate_async_email(self, email: str, rule: ValidationRule, result: ValidationResult) -> ValidationResult:
        """Validate email deliverability with caching"""
        cache_key = f"{self.CACHE_PREFIX}:email:{email}"
        
        # Check cache first
        cached_result = cache.get(cache_key)
        if cached_result:
            result.is_valid = cached_result['is_valid']
            result.error_message = cached_result.get('error_message', '')
            result.warning_message = cached_result.get('warning_message', '')
            return result
        
        try:
            # Basic email format validation first
            from django.core.validators import validate_email
            validate_email(email)
            
            # Simulate external API call - replace with actual service integration
            domain = email.split('@')[1].lower()
            disposable_domains = ['10minutemail.com', 'guerrillamail.com', 'tempmail.org']
            
            is_valid = domain not in disposable_domains
            error_message = rule.error_message or "Disposable email addresses are not allowed" if not is_valid else ""
            
            # Cache the result
            cache_data = {
                'is_valid': is_valid,
                'error_message': error_message
            }
            cache.set(cache_key, cache_data, self.DEFAULT_CACHE_TTL)
            
            result.is_valid = is_valid
            result.error_message = error_message
            
        except Exception as e:
            result.is_valid = True  # Fail gracefully
            result.warning_message = 'Email validation service temporarily unavailable'
        
        return result
    
    async def _validate_async_address(self, address_data: Dict[str, str], rule: ValidationRule, result: ValidationResult) -> ValidationResult:
        """Validate address using external geocoding/address validation API"""
        try:
            # Basic validation - ensure required fields
            required_fields = ['street', 'city', 'state', 'zip']
            missing_fields = [field for field in required_fields if not address_data.get(field)]
            
            if missing_fields:
                result.is_valid = False
                result.error_message = rule.error_message or f'Missing required address fields: {", ".join(missing_fields)}'
                return result
            
            # Simulate external API validation - replace with actual service
            zip_code = address_data.get('zip', '')
            is_valid = bool(re.match(r'^\d{5}(-\d{4})?$', zip_code))
            
            result.is_valid = is_valid
            if not is_valid:
                result.error_message = rule.error_message or 'Invalid ZIP code format'
                
        except Exception as e:
            result.is_valid = True  # Fail gracefully
            result.warning_message = 'Address validation service temporarily unavailable'
        
        return result
    
    async def _validate_business_hours(self, datetime_value: str, business_config: Dict[str, Any], rule: ValidationRule, result: ValidationResult) -> ValidationResult:
        """Validate that a datetime falls within business hours"""
        try:
            # Parse the datetime
            if isinstance(datetime_value, str):
                dt = datetime.fromisoformat(datetime_value.replace('Z', '+00:00'))
            else:
                dt = datetime_value
            
            # Check if it's a business day
            business_days = business_config.get('business_days', [1, 2, 3, 4, 5])
            if dt.weekday() + 1 not in business_days:  # weekday() returns 0-6, we want 1-7
                result.is_valid = False
                result.error_message = rule.error_message or business_config.get('error_message', 'Must be scheduled on a business day')
                return result
            
            # Check if it's within business hours
            start_hour, start_min = map(int, business_config.get('start_time', '09:00').split(':'))
            end_hour, end_min = map(int, business_config.get('end_time', '17:00').split(':'))
            
            appointment_time = dt.time()
            start_time_obj = datetime.min.time().replace(hour=start_hour, minute=start_min)
            end_time_obj = datetime.min.time().replace(hour=end_hour, minute=end_min)
            
            is_valid = start_time_obj <= appointment_time <= end_time_obj
            
            result.is_valid = is_valid
            if not is_valid:
                result.error_message = rule.error_message or business_config.get('error_message', 'Must be scheduled during business hours')
                
        except Exception as e:
            logger.error(f"Business hours validation error: {str(e)}")
            result.is_valid = False
            result.error_message = f'Business hours validation error: {str(e)}'
        
        return result
    
    def _should_apply_validation(
        self, 
        validation: FormFieldValidation, 
        data: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if validation should be applied based on conditional logic"""
        if not validation.conditional_logic:
            return True
        
        return self._evaluate_conditions(validation.conditional_logic.get('conditions', []), data)
    
    def _evaluate_conditions(self, conditions: List[Dict[str, Any]], data: Dict[str, Any]) -> bool:
        """Evaluate conditional logic conditions"""
        if not conditions:
            return True
        
        results = []
        for condition in conditions:
            field = condition.get('field', '')
            operator = condition.get('operator', 'equals')
            expected_value = condition.get('value')
            
            if field not in data:
                results.append(False)
                continue
            
            actual_value = data[field]
            
            if operator == 'equals':
                results.append(actual_value == expected_value)
            elif operator == 'not_equals':
                results.append(actual_value != expected_value)
            elif operator == 'contains':
                results.append(expected_value in str(actual_value))
            elif operator == 'greater_than':
                try:
                    results.append(float(actual_value) > float(expected_value))
                except (ValueError, TypeError):
                    results.append(False)
            elif operator == 'less_than':
                try:
                    results.append(float(actual_value) < float(expected_value))
                except (ValueError, TypeError):
                    results.append(False)
            else:
                results.append(False)
        
        # For now, we'll use AND logic - all conditions must be true
        return all(results)
    
    async def _validate_cross_field_rules(
        self,
        form_template: FormTemplate,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[ValidationResult]:
        """Execute cross-field validation rules"""
        # Placeholder for cross-field validations
        return []
    
    async def _check_duplicates(
        self,
        form_template: FormTemplate,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Check for duplicate records"""
        # This would integrate with the duplicate detection engine
        # For now, return empty list
        return []
    
    async def _get_form_template(self, form_template_id: int) -> Optional[FormTemplate]:
        """Get form template with field configurations"""
        try:
            from ..models import FormTemplate
            # Use select_related and prefetch_related for efficient querying
            return await FormTemplate.objects.select_related('pipeline').prefetch_related(
                'field_configs__pipeline_field',
                'field_configs__validations__validation_rule'
            ).aget(id=form_template_id, tenant_id=self.tenant_id)
        except FormTemplate.DoesNotExist:
            return None
    
    # Performance Optimization Methods
    
    async def batch_validate_fields(self, validation_requests: List[Dict[str, Any]]) -> List[ValidationResult]:
        """Batch validate multiple fields for performance optimization"""
        results = []
        
        # Group validations by type for batch processing
        grouped_validations = {}
        for i, request in enumerate(validation_requests):
            rule_type = request.get('rule_type', 'unknown')
            if rule_type not in grouped_validations:
                grouped_validations[rule_type] = []
            grouped_validations[rule_type].append((i, request))
        
        # Process each group
        for rule_type, type_requests in grouped_validations.items():
            if rule_type == 'regex':
                type_results = await self._batch_regex_validation([req[1] for req in type_requests])
            elif rule_type == 'email':
                type_results = await self._batch_email_validation([req[1] for req in type_requests])
            else:
                # Fall back to individual validation
                type_results = [await self._single_validation(req[1]) for req in type_requests]
            
            # Map results back to original order
            for (original_index, _), result in zip(type_requests, type_results):
                results.append((original_index, result))
        
        # Sort by original order and return just the results
        results.sort(key=lambda x: x[0])
        return [result for _, result in results]
    
    async def _batch_regex_validation(self, requests: List[Dict[str, Any]]) -> List[ValidationResult]:
        """Batch process regex validations with compiled pattern reuse"""
        results = []
        
        # Compile patterns once for reuse
        compiled_patterns = {}
        
        for request in requests:
            pattern = request.get('pattern', '')
            if pattern not in compiled_patterns:
                try:
                    compiled_patterns[pattern] = re.compile(pattern)
                except re.error:
                    compiled_patterns[pattern] = None
            
            compiled_pattern = compiled_patterns[pattern]
            if compiled_pattern is None:
                results.append(ValidationResult(
                    is_valid=False,
                    field_name=request.get('field_name', ''),
                    rule_name='regex_error',
                    error_message='Invalid regex pattern',
                    rule_type='regex',
                    execution_time_ms=0
                ))
            else:
                value = str(request.get('value', ''))
                is_valid = bool(compiled_pattern.match(value))
                results.append(ValidationResult(
                    is_valid=is_valid,
                    field_name=request.get('field_name', ''),
                    rule_name='regex_batch',
                    error_message=request.get('error_message', '') if not is_valid else '',
                    rule_type='regex',
                    execution_time_ms=0.1,  # Approximate batch time
                    value_checked=value
                ))
        
        return results
    
    async def _batch_email_validation(self, requests: List[Dict[str, Any]]) -> List[ValidationResult]:
        """Batch process email validations"""
        results = []
        
        for request in requests:
            email = request.get('value', '')
            try:
                from django.core.validators import validate_email
                validate_email(email)
                results.append(ValidationResult(
                    is_valid=True,
                    field_name=request.get('field_name', ''),
                    rule_name='email_batch',
                    rule_type='email',
                    execution_time_ms=0.1,
                    value_checked=email
                ))
            except Exception:
                results.append(ValidationResult(
                    is_valid=False,
                    field_name=request.get('field_name', ''),
                    rule_name='email_batch',
                    error_message='Please enter a valid email address',
                    rule_type='email',
                    execution_time_ms=0.1,
                    value_checked=email
                ))
        
        return results
    
    async def _single_validation(self, request: Dict[str, Any]) -> ValidationResult:
        """Fallback for single validation"""
        return ValidationResult(
            is_valid=True,
            field_name=request.get('field_name', ''),
            rule_name='single_fallback',
            rule_type=request.get('rule_type', 'unknown'),
            execution_time_ms=1.0,
            value_checked=request.get('value')
        )
    
    def cache_validation_result(self, cache_key: str, result: ValidationResult, ttl: int = None):
        """Cache validation result for performance"""
        if ttl is None:
            ttl = self.DEFAULT_CACHE_TTL
        
        cache_data = {
            'is_valid': result.is_valid,
            'field_name': result.field_name,
            'rule_name': result.rule_name,
            'error_message': result.error_message,
            'warning_message': result.warning_message,
            'rule_type': result.rule_type,
        }
        
        cache.set(f"{self.CACHE_PREFIX}:{cache_key}", cache_data, ttl)
    
    def get_cached_validation(self, cache_key: str) -> Optional[ValidationResult]:
        """Retrieve cached validation result"""
        cached_data = cache.get(f"{self.CACHE_PREFIX}:{cache_key}")
        if cached_data:
            return ValidationResult(**cached_data)
        return None
    
    @classmethod
    def get_pattern_suggestions(cls, category: str = None) -> Dict[str, Any]:
        """Get pattern suggestions for regex validation from comprehensive patterns"""
        from .patterns import get_patterns_by_category, VALIDATION_PATTERNS
        
        if category:
            # Return patterns for specific category
            categories = get_patterns_by_category()
            if category in categories:
                pattern_list = []
                for pattern_name in categories[category]:
                    if pattern_name in VALIDATION_PATTERNS:
                        pattern_obj = VALIDATION_PATTERNS[pattern_name]
                        pattern_list.append({
                            'name': pattern_name,
                            'pattern': pattern_obj.pattern,
                            'error': pattern_obj.description,
                            'examples_valid': pattern_obj.examples_valid,
                            'examples_invalid': pattern_obj.examples_invalid
                        })
                return {category: pattern_list}
            return {}
        
        # Return all patterns organized by category
        result = {}
        categories = get_patterns_by_category()
        
        for category_name, pattern_names in categories.items():
            pattern_list = []
            for pattern_name in pattern_names:
                if pattern_name in VALIDATION_PATTERNS:
                    pattern_obj = VALIDATION_PATTERNS[pattern_name]
                    pattern_list.append({
                        'name': pattern_name,
                        'pattern': pattern_obj.pattern, 
                        'error': pattern_obj.description,
                        'examples_valid': pattern_obj.examples_valid,
                        'examples_invalid': pattern_obj.examples_invalid
                    })
            if pattern_list:  # Only add categories that have patterns
                result[category_name] = pattern_list
        
        return result