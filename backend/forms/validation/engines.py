"""
Sophisticated validation engines for enterprise-grade form validation
"""
import re
import asyncio
import requests
from typing import Dict, Any, List, Optional, Union
from django.core.cache import cache
from django.core.validators import validate_email, URLValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)


class ValidationResult:
    """Standardized validation result"""
    def __init__(self, is_valid: bool, field_name: str, rule_name: str, 
                 error_message: str = "", warning_message: str = "", 
                 value_checked: Any = None, rule_type: str = "", 
                 execution_time_ms: float = 0):
        self.is_valid = is_valid
        self.field_name = field_name
        self.rule_name = rule_name
        self.error_message = error_message
        self.warning_message = warning_message
        self.value_checked = value_checked
        self.rule_type = rule_type
        self.execution_time_ms = execution_time_ms


class AdvancedRegexValidator:
    """Advanced regex validation with custom error messages and pattern libraries"""
    
    # Common regex patterns with descriptive names and error messages
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
    
    @classmethod
    def validate(cls, value: str, pattern: str, error_message: str = None, 
                pattern_name: str = None) -> ValidationResult:
        """
        Validate value against regex pattern with custom error messaging
        """
        start_time = timezone.now()
        
        # Use predefined pattern if pattern_name provided
        if pattern_name and pattern_name in cls.PATTERN_LIBRARY:
            pattern_info = cls.PATTERN_LIBRARY[pattern_name]
            pattern = pattern_info['pattern']
            if not error_message:
                error_message = pattern_info['error']
        
        try:
            if not isinstance(value, str):
                value = str(value) if value is not None else ""
            
            # Compile pattern for better performance and error checking
            compiled_pattern = re.compile(pattern, re.IGNORECASE if pattern_name else 0)
            is_valid = bool(compiled_pattern.match(value))
            
            execution_time = (timezone.now() - start_time).total_seconds() * 1000
            
            return ValidationResult(
                is_valid=is_valid,
                field_name="",  # Will be set by caller
                rule_name=f"regex_{pattern_name or 'custom'}",
                error_message=error_message or "Value does not match required pattern" if not is_valid else "",
                rule_type="regex",
                execution_time_ms=execution_time,
                value_checked=value
            )
            
        except re.error as e:
            logger.error(f"Invalid regex pattern: {pattern}. Error: {str(e)}")
            execution_time = (timezone.now() - start_time).total_seconds() * 1000
            
            return ValidationResult(
                is_valid=False,
                field_name="",
                rule_name="regex_error",
                error_message=f"Invalid validation pattern configured: {str(e)}",
                rule_type="regex",
                execution_time_ms=execution_time,
                value_checked=value
            )


class CrossFieldValidator:
    """Cross-field validation with conditional logic and field dependencies"""
    
    @classmethod
    def validate_conditional(cls, form_data: Dict[str, Any], field_name: str, 
                           condition_config: Dict[str, Any]) -> ValidationResult:
        """
        Validate field based on conditions from other fields
        
        condition_config example:
        {
            "if_field": "user_type",
            "if_value": "premium", 
            "then_required": True,
            "else_required": False,
            "if_operator": "equals",  # equals, not_equals, in, not_in, greater_than, etc
            "error_message": "This field is required for premium users"
        }
        """
        start_time = timezone.now()
        
        try:
            if_field = condition_config.get('if_field')
            if_value = condition_config.get('if_value')
            if_operator = condition_config.get('if_operator', 'equals')
            then_required = condition_config.get('then_required', False)
            else_required = condition_config.get('else_required', False)
            error_message = condition_config.get('error_message', 'Field validation failed')
            
            # Get the condition field value
            condition_field_value = form_data.get(if_field)
            current_field_value = form_data.get(field_name)
            
            # Evaluate condition
            condition_met = cls._evaluate_condition(condition_field_value, if_value, if_operator)
            
            # Determine if field is required based on condition
            is_required = then_required if condition_met else else_required
            
            # Check if field meets requirement
            is_valid = True
            final_error = ""
            
            if is_required and (current_field_value is None or str(current_field_value).strip() == ""):
                is_valid = False
                final_error = error_message
            
            execution_time = (timezone.now() - start_time).total_seconds() * 1000
            
            return ValidationResult(
                is_valid=is_valid,
                field_name=field_name,
                rule_name="conditional_validation",
                error_message=final_error,
                rule_type="conditional",
                execution_time_ms=execution_time,
                value_checked=current_field_value
            )
            
        except Exception as e:
            logger.error(f"Cross-field validation error: {str(e)}")
            execution_time = (timezone.now() - start_time).total_seconds() * 1000
            
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                rule_name="conditional_error",
                error_message=f"Validation configuration error: {str(e)}",
                rule_type="conditional",
                execution_time_ms=execution_time,
                value_checked=form_data.get(field_name)
            )
    
    @classmethod
    def validate_field_comparison(cls, form_data: Dict[str, Any], field1: str, 
                                field2: str, comparison: str, error_message: str = None) -> ValidationResult:
        """
        Compare two fields (e.g., password confirmation, date ranges)
        
        comparison options: 'equals', 'not_equals', 'greater_than', 'less_than', 
                           'greater_equal', 'less_equal', 'date_after', 'date_before'
        """
        start_time = timezone.now()
        
        try:
            value1 = form_data.get(field1)
            value2 = form_data.get(field2)
            
            is_valid = cls._compare_values(value1, value2, comparison)
            
            if not error_message:
                error_message = f"Fields {field1} and {field2} do not match required comparison: {comparison}"
            
            execution_time = (timezone.now() - start_time).total_seconds() * 1000
            
            return ValidationResult(
                is_valid=is_valid,
                field_name=f"{field1}_vs_{field2}",
                rule_name="field_comparison",
                error_message=error_message if not is_valid else "",
                rule_type="cross_field",
                execution_time_ms=execution_time,
                value_checked={"field1": value1, "field2": value2}
            )
            
        except Exception as e:
            logger.error(f"Field comparison validation error: {str(e)}")
            execution_time = (timezone.now() - start_time).total_seconds() * 1000
            
            return ValidationResult(
                is_valid=False,
                field_name=f"{field1}_vs_{field2}",
                rule_name="comparison_error",
                error_message=f"Field comparison error: {str(e)}",
                rule_type="cross_field",
                execution_time_ms=execution_time,
                value_checked={"field1": value1, "field2": value2}
            )
    
    @staticmethod
    def _evaluate_condition(field_value: Any, target_value: Any, operator: str) -> bool:
        """Evaluate condition between field value and target value"""
        if operator == 'equals':
            return field_value == target_value
        elif operator == 'not_equals':
            return field_value != target_value
        elif operator == 'in':
            return field_value in (target_value if isinstance(target_value, (list, tuple)) else [target_value])
        elif operator == 'not_in':
            return field_value not in (target_value if isinstance(target_value, (list, tuple)) else [target_value])
        elif operator == 'greater_than':
            return field_value > target_value
        elif operator == 'less_than':
            return field_value < target_value
        elif operator == 'greater_equal':
            return field_value >= target_value
        elif operator == 'less_equal':
            return field_value <= target_value
        elif operator == 'contains':
            return str(target_value) in str(field_value)
        elif operator == 'starts_with':
            return str(field_value).startswith(str(target_value))
        elif operator == 'ends_with':
            return str(field_value).endswith(str(target_value))
        else:
            return False
    
    @staticmethod
    def _compare_values(value1: Any, value2: Any, comparison: str) -> bool:
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


class AsyncAPIValidator:
    """Async API validation for external service validation"""
    
    # Cache validation results to avoid repeated API calls
    CACHE_PREFIX = "async_validation"
    DEFAULT_CACHE_TTL = 300  # 5 minutes
    
    @classmethod
    def validate_email_deliverable(cls, email: str, timeout: int = 5) -> ValidationResult:
        """
        Validate email deliverability using external API
        (This is a placeholder - in production you'd use services like ZeroBounce, Hunter.io, etc.)
        """
        start_time = timezone.now()
        cache_key = f"{cls.CACHE_PREFIX}:email:{email}"
        
        # Check cache first
        cached_result = cache.get(cache_key)
        if cached_result:
            cached_result['execution_time_ms'] = (timezone.now() - start_time).total_seconds() * 1000
            cached_result['value_checked'] = email
            return ValidationResult(**cached_result)
        
        try:
            # Basic email format validation first
            validate_email(email)
            
            # Simulate external API call (replace with actual service)
            # In production, integrate with services like:
            # - ZeroBounce: https://www.zerobounce.net/
            # - Hunter.io: https://hunter.io/
            # - Abstract API: https://www.abstractapi.com/
            
            # For demo purposes, simulate based on domain
            domain = email.split('@')[1].lower()
            disposable_domains = ['10minutemail.com', 'guerrillamail.com', 'tempmail.org']
            
            is_valid = domain not in disposable_domains
            error_message = "Disposable email addresses are not allowed" if not is_valid else ""
            
            # Cache the result
            result_data = {
                'is_valid': is_valid,
                'field_name': '',
                'rule_name': 'email_deliverable',
                'error_message': error_message,
                'rule_type': 'async_api',
            }
            cache.set(cache_key, result_data, cls.DEFAULT_CACHE_TTL)
            
            execution_time = (timezone.now() - start_time).total_seconds() * 1000
            
            return ValidationResult(
                **result_data,
                execution_time_ms=execution_time,
                value_checked=email
            )
            
        except ValidationError:
            execution_time = (timezone.now() - start_time).total_seconds() * 1000
            return ValidationResult(
                is_valid=False,
                field_name='',
                rule_name='email_format',
                error_message='Please enter a valid email address',
                rule_type='async_api',
                execution_time_ms=execution_time,
                value_checked=email
            )
        except Exception as e:
            logger.error(f"Email validation API error: {str(e)}")
            execution_time = (timezone.now() - start_time).total_seconds() * 1000
            
            # Fail gracefully - don't block form submission due to external API issues
            return ValidationResult(
                is_valid=True,  # Allow submission if external validation fails
                field_name='',
                rule_name='email_api_error',
                warning_message='Email validation service temporarily unavailable',
                rule_type='async_api',
                execution_time_ms=execution_time,
                value_checked=email
            )
    
    @classmethod
    def validate_address(cls, address_data: Dict[str, str], timeout: int = 10) -> ValidationResult:
        """
        Validate address using external geocoding/address validation API
        """
        start_time = timezone.now()
        
        # Create cache key from address components
        address_string = f"{address_data.get('street', '')} {address_data.get('city', '')} {address_data.get('state', '')} {address_data.get('zip', '')}"
        cache_key = f"{cls.CACHE_PREFIX}:address:{hash(address_string)}"
        
        # Check cache first
        cached_result = cache.get(cache_key)
        if cached_result:
            cached_result['execution_time_ms'] = (timezone.now() - start_time).total_seconds() * 1000
            cached_result['value_checked'] = address_data
            return ValidationResult(**cached_result)
        
        try:
            # Basic validation - ensure required fields
            required_fields = ['street', 'city', 'state', 'zip']
            missing_fields = [field for field in required_fields if not address_data.get(field)]
            
            if missing_fields:
                execution_time = (timezone.now() - start_time).total_seconds() * 1000
                return ValidationResult(
                    is_valid=False,
                    field_name='address',
                    rule_name='address_incomplete',
                    error_message=f'Missing required address fields: {", ".join(missing_fields)}',
                    rule_type='async_api',
                    execution_time_ms=execution_time,
                    value_checked=address_data
                )
            
            # Simulate external API validation
            # In production, integrate with services like:
            # - Google Maps Geocoding API
            # - USPS Address Validation
            # - SmartyStreets
            
            # For demo, basic validation
            zip_code = address_data.get('zip', '')
            is_valid = bool(re.match(r'^\d{5}(-\d{4})?$', zip_code))
            error_message = 'Invalid ZIP code format' if not is_valid else ''
            
            # Cache the result
            result_data = {
                'is_valid': is_valid,
                'field_name': 'address',
                'rule_name': 'address_validation',
                'error_message': error_message,
                'rule_type': 'async_api',
            }
            cache.set(cache_key, result_data, cls.DEFAULT_CACHE_TTL)
            
            execution_time = (timezone.now() - start_time).total_seconds() * 1000
            
            return ValidationResult(
                **result_data,
                execution_time_ms=execution_time,
                value_checked=address_data
            )
            
        except Exception as e:
            logger.error(f"Address validation API error: {str(e)}")
            execution_time = (timezone.now() - start_time).total_seconds() * 1000
            
            return ValidationResult(
                is_valid=True,  # Fail gracefully
                field_name='address',
                rule_name='address_api_error',
                warning_message='Address validation service temporarily unavailable',
                rule_type='async_api',
                execution_time_ms=execution_time,
                value_checked=address_data
            )


class BusinessRuleValidator:
    """Custom business logic validation engines"""
    
    @classmethod
    def validate_business_hours(cls, datetime_value: str, business_config: Dict[str, Any]) -> ValidationResult:
        """
        Validate that a datetime falls within business hours
        
        business_config example:
        {
            "business_days": [1, 2, 3, 4, 5],  # Monday=1, Sunday=7
            "start_time": "09:00",
            "end_time": "17:00",
            "timezone": "America/New_York",
            "error_message": "Appointments must be scheduled during business hours"
        }
        """
        start_time = timezone.now()
        
        try:
            # Parse the datetime
            if isinstance(datetime_value, str):
                dt = datetime.fromisoformat(datetime_value.replace('Z', '+00:00'))
            else:
                dt = datetime_value
            
            # Check if it's a business day
            business_days = business_config.get('business_days', [1, 2, 3, 4, 5])
            if dt.weekday() + 1 not in business_days:  # weekday() returns 0-6, we want 1-7
                execution_time = (timezone.now() - start_time).total_seconds() * 1000
                return ValidationResult(
                    is_valid=False,
                    field_name='',
                    rule_name='business_hours',
                    error_message=business_config.get('error_message', 'Must be scheduled on a business day'),
                    rule_type='business_rule',
                    execution_time_ms=execution_time,
                    value_checked=datetime_value
                )
            
            # Check if it's within business hours
            start_hour, start_min = map(int, business_config.get('start_time', '09:00').split(':'))
            end_hour, end_min = map(int, business_config.get('end_time', '17:00').split(':'))
            
            appointment_time = dt.time()
            start_time_obj = datetime.min.time().replace(hour=start_hour, minute=start_min)
            end_time_obj = datetime.min.time().replace(hour=end_hour, minute=end_min)
            
            is_valid = start_time_obj <= appointment_time <= end_time_obj
            
            execution_time = (timezone.now() - start_time).total_seconds() * 1000
            
            return ValidationResult(
                is_valid=is_valid,
                field_name='',
                rule_name='business_hours',
                error_message=business_config.get('error_message', 'Must be scheduled during business hours') if not is_valid else '',
                rule_type='business_rule',
                execution_time_ms=execution_time,
                value_checked=datetime_value
            )
            
        except Exception as e:
            logger.error(f"Business hours validation error: {str(e)}")
            execution_time = (timezone.now() - start_time).total_seconds() * 1000
            
            return ValidationResult(
                is_valid=False,
                field_name='',
                rule_name='business_hours_error',
                error_message=f'Business hours validation error: {str(e)}',
                rule_type='business_rule',
                execution_time_ms=execution_time,
                value_checked=datetime_value
            )
    
    @classmethod
    def validate_budget_limits(cls, amount: float, budget_config: Dict[str, Any], 
                             form_data: Dict[str, Any] = None) -> ValidationResult:
        """
        Validate amount against budget limits and spending rules
        
        budget_config example:
        {
            "max_amount": 10000,
            "min_amount": 100,
            "department_budgets": {
                "marketing": 5000,
                "operations": 8000
            },
            "approval_required_above": 2500,
            "error_message": "Amount exceeds budget limits"
        }
        """
        start_time = timezone.now()
        
        try:
            amount = float(amount)
            max_amount = budget_config.get('max_amount', float('inf'))
            min_amount = budget_config.get('min_amount', 0)
            
            # Basic min/max validation
            if amount < min_amount or amount > max_amount:
                execution_time = (timezone.now() - start_time).total_seconds() * 1000
                return ValidationResult(
                    is_valid=False,
                    field_name='',
                    rule_name='budget_limits',
                    error_message=budget_config.get('error_message', f'Amount must be between ${min_amount} and ${max_amount}'),
                    rule_type='business_rule',
                    execution_time_ms=execution_time,
                    value_checked=amount
                )
            
            # Department-specific budget validation
            department_budgets = budget_config.get('department_budgets', {})
            if form_data and department_budgets:
                department = form_data.get('department')
                if department and department in department_budgets:
                    dept_limit = department_budgets[department]
                    if amount > dept_limit:
                        execution_time = (timezone.now() - start_time).total_seconds() * 1000
                        return ValidationResult(
                            is_valid=False,
                            field_name='',
                            rule_name='department_budget',
                            error_message=f'Amount exceeds {department} department budget limit of ${dept_limit}',
                            rule_type='business_rule',
                            execution_time_ms=execution_time,
                            value_checked=amount
                        )
            
            # Approval requirement warning
            approval_threshold = budget_config.get('approval_required_above')
            warning_message = ""
            if approval_threshold and amount > approval_threshold:
                warning_message = f'Amount over ${approval_threshold} requires additional approval'
            
            execution_time = (timezone.now() - start_time).total_seconds() * 1000
            
            return ValidationResult(
                is_valid=True,
                field_name='',
                rule_name='budget_validation',
                warning_message=warning_message,
                rule_type='business_rule',
                execution_time_ms=execution_time,
                value_checked=amount
            )
            
        except (ValueError, TypeError) as e:
            execution_time = (timezone.now() - start_time).total_seconds() * 1000
            return ValidationResult(
                is_valid=False,
                field_name='',
                rule_name='budget_format_error',
                error_message='Please enter a valid amount',
                rule_type='business_rule',
                execution_time_ms=execution_time,
                value_checked=amount
            )


class ValidationPerformanceOptimizer:
    """Performance optimization for validation with caching and batch processing"""
    
    BATCH_CACHE_PREFIX = "validation_batch"
    PERFORMANCE_CACHE_TTL = 3600  # 1 hour
    
    @classmethod
    def batch_validate(cls, validation_requests: List[Dict[str, Any]]) -> List[ValidationResult]:
        """
        Batch validate multiple fields for performance optimization
        """
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
                type_results = cls._batch_regex_validation([req[1] for req in type_requests])
            elif rule_type == 'email':
                type_results = cls._batch_email_validation([req[1] for req in type_requests])
            else:
                # Fall back to individual validation
                type_results = [cls._single_validation(req[1]) for req in type_requests]
            
            # Map results back to original order
            for (original_index, _), result in zip(type_requests, type_results):
                results.append((original_index, result))
        
        # Sort by original order and return just the results
        results.sort(key=lambda x: x[0])
        return [result for _, result in results]
    
    @classmethod
    def _batch_regex_validation(cls, requests: List[Dict[str, Any]]) -> List[ValidationResult]:
        """Batch process regex validations"""
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
    
    @classmethod
    def _batch_email_validation(cls, requests: List[Dict[str, Any]]) -> List[ValidationResult]:
        """Batch process email validations"""
        results = []
        
        for request in requests:
            email = request.get('value', '')
            try:
                validate_email(email)
                results.append(ValidationResult(
                    is_valid=True,
                    field_name=request.get('field_name', ''),
                    rule_name='email_batch',
                    rule_type='email',
                    execution_time_ms=0.1,
                    value_checked=email
                ))
            except ValidationError:
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
    
    @classmethod
    def _single_validation(cls, request: Dict[str, Any]) -> ValidationResult:
        """Fallback for single validation"""
        return ValidationResult(
            is_valid=True,
            field_name=request.get('field_name', ''),
            rule_name='single_fallback',
            rule_type=request.get('rule_type', 'unknown'),
            execution_time_ms=1.0,
            value_checked=request.get('value')
        )
    
    @classmethod
    def cache_validation_result(cls, cache_key: str, result: ValidationResult, ttl: int = None):
        """Cache validation result for performance"""
        if ttl is None:
            ttl = cls.PERFORMANCE_CACHE_TTL
        
        cache_data = {
            'is_valid': result.is_valid,
            'field_name': result.field_name,
            'rule_name': result.rule_name,
            'error_message': result.error_message,
            'warning_message': result.warning_message,
            'rule_type': result.rule_type,
        }
        
        cache.set(f"{cls.BATCH_CACHE_PREFIX}:{cache_key}", cache_data, ttl)
    
    @classmethod
    def get_cached_validation(cls, cache_key: str) -> Optional[ValidationResult]:
        """Retrieve cached validation result"""
        cached_data = cache.get(f"{cls.BATCH_CACHE_PREFIX}:{cache_key}")
        if cached_data:
            return ValidationResult(**cached_data)
        return None