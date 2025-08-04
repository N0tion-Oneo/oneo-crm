"""
Field validation system for dynamic pipeline fields
"""
from typing import Any, Dict, List, Union
from datetime import datetime, date
import re
import json
from urllib.parse import urlparse

from .field_types import FieldType, FIELD_TYPE_CONFIGS


class ValidationResult:
    """Result of field validation"""
    
    def __init__(self, is_valid: bool = True, cleaned_value: Any = None, errors: List[str] = None, source: str = 'backend_validator'):
        self.is_valid = is_valid
        self.cleaned_value = cleaned_value
        self.errors = errors or []
        self.source = source  # Track validation source for debugging
    
    def add_error(self, error: str, source: str = 'backend_validator'):
        """Add validation error with source tracking"""
        self.is_valid = False
        # Prefix error message with source indicator for clear tracking
        formatted_error = f"[{source.upper()}] {error}"
        self.errors.append(formatted_error)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'is_valid': self.is_valid,
            'cleaned_value': self.cleaned_value,
            'errors': self.errors,
            'source': self.source
        }


class FieldValidator:
    """Validates field values based on field type and configuration"""
    
    def __init__(self, field_type: FieldType, field_config: Dict[str, Any], ai_config: Dict[str, Any] = None):
        self.field_type = field_type
        self.field_config = field_config
        self.config_class = FIELD_TYPE_CONFIGS.get(field_type)
        
        if self.config_class:
            try:
                # For AI fields, use ai_config instead of field_config
                if field_type == FieldType.AI_GENERATED and ai_config:
                    self.config = self.config_class(**ai_config)
                else:
                    self.config = self.config_class(**field_config)
            except Exception as e:
                raise ValueError(f"Invalid field configuration: {e}")
        else:
            self.config = None
    
    def validate_storage(self, value: Any, storage_constraints: Dict[str, Any]) -> ValidationResult:
        """Validate value against storage constraints only - never reject for completeness"""
        result = ValidationResult(cleaned_value=value, source='backend_storage_validator')
        
        # Storage validation never requires fields - always allow NULL/empty
        if self._is_empty(value):
            result.cleaned_value = None  # Store as NULL in database
            return result
        
        # Apply storage constraints validation
        max_length = storage_constraints.get('max_storage_length')
        if max_length and isinstance(value, str) and len(value) > max_length:
            result.add_error(f'Value exceeds maximum storage length of {max_length} characters', 'storage_constraint')
            return result
        
        # Type-specific storage validation (basic type checking only)
        try:
            if self.field_type == FieldType.TEXT:
                result.cleaned_value = self._validate_text(value)
            elif self.field_type == FieldType.TEXTAREA:
                result.cleaned_value = self._validate_textarea(value)
            elif self.field_type == FieldType.NUMBER:
                result.cleaned_value = self._validate_number(value)
            elif self.field_type == FieldType.BOOLEAN:
                result.cleaned_value = self._validate_boolean(value)
            elif self.field_type == FieldType.DATE:
                result.cleaned_value = self._validate_date(value)
            elif self.field_type == FieldType.EMAIL:
                result.cleaned_value = self._validate_email(value)
            elif self.field_type == FieldType.PHONE:
                result.cleaned_value = self._validate_phone(value)
            elif self.field_type == FieldType.URL:
                result.cleaned_value = self._validate_url(value)
            elif self.field_type == FieldType.ADDRESS:
                result.cleaned_value = self._validate_address(value)
            elif self.field_type in [FieldType.SELECT, FieldType.MULTISELECT]:
                result.cleaned_value = self._validate_select(value)
            elif self.field_type == FieldType.TAGS:
                result.cleaned_value = self._validate_tags(value)
            elif self.field_type == FieldType.FILE:  # FILE handles all file types including images
                result.cleaned_value = self._validate_file(value)
            elif self.field_type == FieldType.BUTTON:
                result.cleaned_value = self._validate_button(value)
            elif self.field_type == FieldType.RELATION:
                result.cleaned_value = self._validate_relation(value)
            elif self.field_type == FieldType.RECORD_DATA:
                result.cleaned_value = self._validate_record_data(value)
            elif self.field_type == FieldType.AI_GENERATED:
                result.cleaned_value = self._validate_ai_field(value)
            else:
                # For computed, formula, or unknown types, accept as-is
                result.cleaned_value = value
                
        except ValueError as e:
            result.add_error(str(e), f'{self.field_type.value}_field_validator')
        except Exception as e:
            result.add_error(f"Validation error: {e}", f'{self.field_type.value}_field_validator')
        
        return result
    
    def _is_empty(self, value: Any) -> bool:
        """Check if value is considered empty"""
        if value is None:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        if isinstance(value, (list, dict)) and len(value) == 0:
            return True
        return False
    
    def _validate_text(self, value: Any) -> str:
        """Validate text field using TextFieldConfig"""
        if not isinstance(value, str):
            value = str(value)
        
        value = value.strip()
        
        # Use TextFieldConfig
        if self.config:
            # Case sensitivity handling
            if hasattr(self.config, 'case_sensitive') and not self.config.case_sensitive:
                value = value.lower()
            
            # Auto-formatting (placeholder for future implementation)
            if hasattr(self.config, 'auto_format') and self.config.auto_format:
                # Could implement auto-capitalization, etc.
                pass
        
        return value
    
    def _validate_textarea(self, value: Any) -> str:
        """Validate textarea field (same as text but typically allows more length)"""
        return self._validate_text(value)
    
    def _validate_number(self, value: Any) -> Union[float, int, str]:
        """Validate number field using NumberFieldConfig"""
        import re
        from typing import Union
        
        config = self.config
        
        # Handle auto-increment fields (don't validate input)
        if config and hasattr(config, 'format') and config.format == 'auto_increment':
            # Auto-increment values are generated by system, not user input
            # Return the value as-is or generate next value
            return value
        
        # Convert to number
        try:
            if isinstance(value, dict) and 'amount' in value:
                # Handle currency objects from frontend
                if config and hasattr(config, 'format') and config.format == 'currency':
                    # Extract the numeric amount from currency object
                    num = float(value['amount'])
                    # Return the currency object as-is for storage
                    # Validation will continue with the numeric amount
                else:
                    raise ValueError('Currency objects are only supported for currency format fields')
            elif isinstance(value, str):
                # Remove currency symbols and formatting for validation
                clean_value = value.strip()
                if config and hasattr(config, 'format') and config.format == 'currency':
                    # Remove common currency symbols and thousands separators
                    clean_value = re.sub(r'[$€£¥,\s]', '', clean_value)
                elif config and hasattr(config, 'format') and config.format == 'percentage':
                    # Handle percentage input (75% or 0.75)
                    clean_value = clean_value.rstrip('%')
                    
                num = float(clean_value)
            else:
                num = float(value)
        except (TypeError, ValueError):
            raise ValueError('Value must be a number')
        
        # Apply format-specific validation
        if config and hasattr(config, 'format'):
            if config.format == 'percentage':
                # Handle percentage validation based on display format
                if hasattr(config, 'percentage_display') and config.percentage_display == 'whole':
                    # Input as whole number (75 for 75%)
                    if num < 0 or num > 100:
                        raise ValueError('Percentage must be between 0 and 100')
                else:
                    # Input as decimal (0.75 for 75%)
                    if num < 0 or num > 1:
                        raise ValueError('Percentage must be between 0 and 1')
            
            elif config.format == 'currency':
                # Currency cannot be negative (in most cases)
                if num < 0:
                    raise ValueError('Currency amount cannot be negative')
                
                # For currency objects, return the original object (already validated)
                if isinstance(value, dict) and 'amount' in value:
                    return value
            
            elif config.format == 'integer':
                # Ensure it's a whole number
                if num != int(num):
                    raise ValueError('Value must be a whole number')
                return int(num)
        
        # Apply decimal places validation
        if config and hasattr(config, 'decimal_places'):
            decimal_places = config.decimal_places
            if decimal_places == 0:
                return int(num)
            else:
                # Round to specified decimal places
                return round(num, decimal_places)
        
        return num
    
    
    def _validate_boolean(self, value: Any) -> bool:
        """Validate boolean field"""
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            lower_value = value.lower().strip()
            if lower_value in ['true', '1', 'yes', 'on']:
                return True
            elif lower_value in ['false', '0', 'no', 'off']:
                return False
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        raise ValueError('Value must be a boolean')
    
    def _validate_date(self, value: Any) -> str:
        """Validate date field using DateFieldConfig"""
        # Convert to datetime object for validation
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                # Try common date formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                    try:
                        dt = datetime.strptime(value.strip(), fmt)
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError('Invalid date format. Use ISO format (YYYY-MM-DD) or common formats')
        elif isinstance(value, datetime):
            dt = value
        elif isinstance(value, date):
            dt = datetime.combine(value, datetime.min.time())
        else:
            raise ValueError('Value must be a date string or datetime object')
        
        # Use DateFieldConfig
        if self.config:
            # Validate date range
            if hasattr(self.config, 'min_date') and self.config.min_date:
                try:
                    min_dt = datetime.fromisoformat(self.config.min_date)
                    if dt < min_dt:
                        raise ValueError(f'Date must be after {self.config.min_date}')
                except ValueError:
                    pass  # Invalid min_date config, skip validation
            
            if hasattr(self.config, 'max_date') and self.config.max_date:
                try:
                    max_dt = datetime.fromisoformat(self.config.max_date)
                    if dt > max_dt:
                        raise ValueError(f'Date must be before {self.config.max_date}')
                except ValueError:
                    pass  # Invalid max_date config, skip validation
            
            # Handle time inclusion
            if hasattr(self.config, 'include_time') and not self.config.include_time:
                # Date only - strip time component
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        
        return dt.isoformat()
    
    
    
    def _validate_email(self, value: Any) -> str:
        """Validate email field using EmailFieldConfig"""
        if not isinstance(value, str):
            value = str(value)
        
        # Use EmailFieldConfig
        if self.config:
            if hasattr(self.config, 'trim_whitespace') and self.config.trim_whitespace:
                value = value.strip()
            
            if hasattr(self.config, 'auto_lowercase') and self.config.auto_lowercase:
                value = value.lower()
        else:
            # Default behavior
            value = value.strip().lower()
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            raise ValueError('Invalid email format')
        
        return value
    
    def _validate_phone(self, value: Any) -> Union[str, Dict[str, Any]]:
        """Validate phone field using PhoneFieldConfig with country-specific patterns"""
        import re
        from typing import Union, Dict, Any
        
        config = self.config
        
        # Country-specific validation patterns (digits only, no + sign)
        country_patterns = {
            '+1': r'^1\d{10}$',           # US/Canada: 1 followed by 10 digits
            '+44': r'^44\d{10,11}$',      # UK: 44 followed by 10-11 digits  
            '+27': r'^27\d{9}$',          # South Africa: 27 followed by 9 digits
            '+49': r'^49\d{10,12}$',      # Germany: 49 followed by 10-12 digits
            '+33': r'^33\d{9}$',          # France: 33 followed by 9 digits
            '+61': r'^61\d{9}$',          # Australia: 61 followed by 9 digits
            '+39': r'^39\d{9,10}$',       # Italy: 39 followed by 9-10 digits
            '+34': r'^34\d{9}$',          # Spain: 34 followed by 9 digits
            '+31': r'^31\d{9}$',          # Netherlands: 31 followed by 9 digits
            '+91': r'^91\d{10}$',         # India: 91 followed by 10 digits
        }
        
        # Handle phone objects from frontend
        if isinstance(value, dict) and 'country_code' in value and 'number' in value:
            if config and hasattr(config, 'require_country_code') and config.require_country_code:
                country_code = value.get('country_code', '')
                number = value.get('number', '')
                
                if not country_code or not number:
                    raise ValueError('Phone number requires both country code and number')
                
                # Validate country code format
                if not re.match(r'^\+\d{1,4}$', country_code):
                    raise ValueError('Invalid country code format')
                
                # Check allowed countries if configured
                if (hasattr(config, 'allowed_countries') and config.allowed_countries and 
                    not any(country_code == f'+{self._get_country_phone_code(c)}' for c in config.allowed_countries)):
                    raise ValueError(f'Country code {country_code} is not allowed')
                
                # Country-specific validation
                # Build full number: country_code already has +, number is just digits
                full_number = f"{country_code}{number}"
                digits_only = re.sub(r'\D', '', full_number)
                
                # Debug validation
                print(f"🔍 PHONE VALIDATION DEBUG:")
                print(f"  - country_code: {country_code}")  
                print(f"  - number: {number}")
                print(f"  - full_number: {full_number}")
                print(f"  - digits_only: {digits_only}")
                print(f"  - checking pattern for: {country_code}")
                
                if country_code in country_patterns:
                    if not re.match(country_patterns[country_code], digits_only):
                        raise ValueError(f'Invalid phone number format for {country_code}')
                else:
                    # Generic validation for unsupported countries
                    if len(re.sub(r'\D', '', number)) < 7:
                        raise ValueError('Phone number must contain at least 7 digits')
                
                # Custom validation pattern if provided
                if hasattr(config, 'validation_pattern') and config.validation_pattern:
                    if not re.match(config.validation_pattern, full_number):
                        raise ValueError('Phone number does not match required format')
                
                return value
            else:
                raise ValueError('Phone objects are only supported when country code is required')
        
        # Handle string phone numbers
        if not isinstance(value, str):
            value = str(value)
        
        phone = re.sub(r'[^\d+\-\(\)\s]', '', value.strip())
        
        if not phone:
            raise ValueError('Phone number is required')
        
        # String validation with country-specific patterns
        digits_only = re.sub(r'\D', '', phone)
        
        if config and hasattr(config, 'require_country_code') and config.require_country_code:
            if not phone.startswith('+'):
                # Add default country code if configured
                if hasattr(config, 'default_country') and config.default_country:
                    default_code = self._get_country_phone_code(config.default_country)
                    phone = f'+{default_code}{digits_only}'
                else:
                    raise ValueError('Phone number must include country code')
        
        # Apply country-specific validation if phone starts with country code
        for country_code, pattern in country_patterns.items():
            if phone.startswith(country_code):
                full_digits = re.sub(r'\D', '', phone)
                print(f"🔍 STRING PHONE VALIDATION: {phone} -> {full_digits} vs pattern {pattern}")
                if not re.match(pattern, full_digits):
                    raise ValueError(f'Invalid phone number format for {country_code}')
                break
        else:
            # Generic validation
            if len(digits_only) < 7:
                raise ValueError('Phone number must contain at least 7 digits')
        
        return phone
    
    def _get_country_phone_code(self, country_code: str) -> str:
        """Get phone code for country"""
        country_codes = {
            'US': '1', 'CA': '1', 'GB': '44', 'AU': '61', 'DE': '49',
            'FR': '33', 'IT': '39', 'ES': '34', 'NL': '31', 'ZA': '27',
            'NG': '234', 'KE': '254', 'EG': '20', 'MA': '212',
            'IN': '91', 'CN': '86', 'JP': '81', 'KR': '82', 'SG': '65',
            'BR': '55', 'MX': '52', 'AR': '54', 'CL': '56', 'CO': '57'
        }
        return country_codes.get(country_code, '1')
    
    def _validate_url(self, value: Any) -> str:
        """Validate URL field using URLFieldConfig"""
        if not isinstance(value, str):
            value = str(value)
        
        # Use URLFieldConfig
        if self.config:
            if hasattr(self.config, 'trim_whitespace') and self.config.trim_whitespace:
                value = value.strip()
            
            if hasattr(self.config, 'auto_add_protocol') and self.config.auto_add_protocol:
                if value and not value.startswith(('http://', 'https://', 'ftp://')):
                    value = 'http://' + value
        else:
            # Default behavior
            value = value.strip()
            if value and not value.startswith(('http://', 'https://', 'ftp://')):
                value = 'http://' + value
        
        # Basic URL validation
        try:
            parsed = urlparse(value)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError('Invalid URL format')
        except Exception:
            raise ValueError('Invalid URL format')
        
        return value
    
    
    def _validate_select(self, value: Any) -> Any:
        """Validate select field using SelectFieldConfig"""
        config = self.config
        if not config or not hasattr(config, 'options'):
            return value
        
        # Get valid option values
        valid_values = []
        for option in config.options:
            if isinstance(option, dict):
                valid_values.append(option.get('value'))
            else:
                valid_values.append(option)
        
        # Handle single select (FieldType.SELECT)
        if self.field_type == FieldType.SELECT:
            if value not in valid_values:
                # Check if custom values are allowed
                if hasattr(config, 'allow_custom') and config.allow_custom:
                    return value  # Allow custom value
                else:
                    raise ValueError('Invalid selection. Please choose from available options.')
        
        # Handle multiselect (FieldType.MULTISELECT) 
        elif self.field_type == FieldType.MULTISELECT:
            if not isinstance(value, list):
                raise ValueError('Multiple selections must be provided as a list')
            for v in value:
                if v not in valid_values:
                    if not (hasattr(config, 'allow_custom') and config.allow_custom):
                        raise ValueError(f'Invalid selection: {v}. Please choose from available options.')
        
        return value
    
    
    def _validate_file(self, value: Any) -> Dict[str, Any]:
        """Validate file field using FileFieldConfig"""
        if isinstance(value, dict):
            file_info = value
        elif isinstance(value, str):
            # Assume it's a file path or name
            file_info = {'name': value}
        else:
            raise ValueError('File value must be a dictionary with file information')
        
        # Use FileFieldConfig
        if self.config:
            # File type validation
            if hasattr(self.config, 'allowed_types') and self.config.allowed_types:
                file_name = file_info.get('name', file_info.get('filename', ''))
                file_ext = file_name.split('.')[-1].lower() if '.' in file_name else ''
                
                if file_ext not in [ext.lower() for ext in self.config.allowed_types]:
                    raise ValueError(f'File type ".{file_ext}" not allowed. Allowed types: {", ".join(self.config.allowed_types)}')
            
            # File size validation
            if hasattr(self.config, 'max_size') and 'size' in file_info:
                if file_info['size'] > self.config.max_size:
                    max_mb = self.config.max_size / (1024 * 1024)
                    raise ValueError(f'File size exceeds maximum allowed size of {max_mb:.1f}MB')
        
        return file_info
    
    def _validate_relation(self, value: Any) -> Union[int, str]:
        """Validate relation field using RelationFieldConfig"""
        if value is None:
            return None
        
        # Convert to integer ID if it's a string
        try:
            record_id = int(value)
        except (TypeError, ValueError):
            raise ValueError('Relation value must be a record ID (integer)')
        
        # Use RelationFieldConfig for validation
        if self.config and hasattr(self.config, 'target_pipeline_id'):
            # Could validate that the record exists in the target pipeline
            # This would require database access, so might be done at a higher level
            pass
        
        return record_id
    
    
    def _validate_address(self, value: Any) -> Union[str, Dict[str, Any]]:
        """Validate address field using AddressFieldConfig"""
        if isinstance(value, str):
            # Single line address
            return value.strip()
        elif isinstance(value, dict):
            # Structured address
            if self.config and hasattr(self.config, 'components'):
                # Validate required components
                required_components = [k for k, v in self.config.components.items() if v]
                for component in required_components:
                    if component not in value or not value[component]:
                        raise ValueError(f'Address component "{component}" is required')
            return value
        else:
            raise ValueError('Address must be a string or structured object')
    
    def _validate_tags(self, value: Any) -> List[str]:
        """Validate tags field using TagsFieldConfig"""
        if isinstance(value, str):
            # Convert comma-separated string to list
            tags = [tag.strip() for tag in value.split(',') if tag.strip()]
        elif isinstance(value, list):
            tags = [str(tag).strip() for tag in value if str(tag).strip()]
        else:
            raise ValueError('Tags must be a list or comma-separated string')
        
        # Use TagsFieldConfig
        if self.config:
            # Case sensitivity
            if hasattr(self.config, 'case_sensitive') and not self.config.case_sensitive:
                tags = [tag.lower() for tag in tags]
            
            # Max tags validation
            if hasattr(self.config, 'max_tags') and self.config.max_tags:
                if len(tags) > self.config.max_tags:
                    raise ValueError(f'Maximum {self.config.max_tags} tags allowed')
            
            # Custom tags validation
            if hasattr(self.config, 'allow_custom_tags') and not self.config.allow_custom_tags:
                if hasattr(self.config, 'predefined_tags'):
                    predefined = self.config.predefined_tags
                    if not self.config.case_sensitive:
                        predefined = [tag.lower() for tag in predefined]
                    
                    for tag in tags:
                        if tag not in predefined:
                            raise ValueError(f'Tag "{tag}" is not allowed. Use predefined tags only.')
        
        return tags
    
    def _validate_button(self, value: Any) -> Dict[str, Any]:
        """Validate button field using ButtonFieldConfig"""
        # Button fields don't have user input to validate
        # They trigger workflows, so validation is about button configuration
        if self.config:
            if not hasattr(self.config, 'button_text') or not self.config.button_text:
                raise ValueError('Button must have text')
        
        # Return button configuration for rendering
        return {
            'type': 'button',
            'triggered': bool(value),
            'config': self.config.model_dump() if self.config else {}
        }
    
    def _validate_record_data(self, value: Any) -> Any:
        """Validate record data field using RecordDataFieldConfig"""
        # Record data fields are typically system-generated
        # Validation depends on the data type
        if self.config and hasattr(self.config, 'data_type'):
            data_type = self.config.data_type
            
            if data_type == 'timestamp':
                # Validate timestamp format
                if isinstance(value, str):
                    try:
                        datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except ValueError:
                        raise ValueError('Invalid timestamp format')
                elif not isinstance(value, datetime):
                    raise ValueError('Timestamp must be a datetime object or ISO string')
            
            elif data_type == 'user':
                # Validate user ID
                try:
                    int(value)
                except (TypeError, ValueError):
                    raise ValueError('User value must be a user ID (integer)')
            
            elif data_type in ['count', 'duration']:
                # Validate numeric value
                try:
                    float(value)
                except (TypeError, ValueError):
                    raise ValueError(f'{data_type.title()} value must be numeric')
            
            elif data_type == 'status':
                # Status can be any string
                if not isinstance(value, str):
                    value = str(value)
        
        return value
    
    def _validate_ai_field(self, value: Any) -> Any:
        """Validate AI field using AIGeneratedFieldConfig"""
        # AI fields can accept any input for processing
        # Validation is mainly about the AI configuration and output type
        if self.config:
            # Validate output type
            if hasattr(self.config, 'output_type'):
                output_type = self.config.output_type
                
                if output_type == 'number':
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        if hasattr(self.config, 'fallback_value') and self.config.fallback_value is not None:
                            return self.config.fallback_value
                        raise ValueError('AI field output must be numeric')
                
                elif output_type == 'tags':
                    if isinstance(value, str):
                        return [tag.strip() for tag in value.split(',') if tag.strip()]
                    elif isinstance(value, list):
                        return value
                    else:
                        return []
                
                elif output_type == 'url':
                    if value and not isinstance(value, str):
                        value = str(value)
                    # Could apply URL validation here
                    return value
                
                elif output_type == 'json':
                    if isinstance(value, str):
                        try:
                            return json.loads(value)
                        except json.JSONDecodeError:
                            if hasattr(self.config, 'fallback_value') and self.config.fallback_value is not None:
                                return self.config.fallback_value
                            raise ValueError('AI field output must be valid JSON')
                    return value
                
                else:  # 'text' or other
                    return str(value) if value is not None else ''
        
        return value


def validate_record_data(field_definitions: List[Dict[str, Any]], record_data: Dict[str, Any], context: str = 'storage') -> Dict[str, Any]:
    """
    Validate complete record data against field definitions
    
    Args:
        field_definitions: List of field definition dictionaries
        record_data: Dictionary of field values to validate
        context: Validation context ('storage', 'form', 'business_rules')
        
    Returns:
        Dictionary with validation results
    """
    errors = {}
    cleaned_data = {}
    
    # First determine the current stage from the data
    current_stage = None
    stage_field_slug = None
    
    # Find stage field (look for fields that might represent pipeline stages)
    for field_def in field_definitions:
        field_slug = field_def['slug']
        business_rules = field_def.get('business_rules', {})
        stage_requirements = business_rules.get('stage_requirements', {})
        
        # If this field has stage requirements, it might be used to determine current stage
        # Or if it's in the data, use it as potential stage value
        if field_slug in record_data and stage_requirements:
            current_stage = record_data[field_slug]
            stage_field_slug = field_slug
            break
    
    # If no stage field found, check for common stage field names
    if current_stage is None:
        common_stage_fields = ['stage', 'pipeline_stage', 'pipeline_stages', 'status']
        for stage_field in common_stage_fields:
            if stage_field in record_data:
                current_stage = record_data[stage_field]
                stage_field_slug = stage_field
                break
    
    for field_def in field_definitions:
        field_slug = field_def['slug']
        field_type = FieldType(field_def['field_type'])
        field_config = field_def.get('field_config', {})
        storage_constraints = field_def.get('storage_constraints', {})
        business_rules = field_def.get('business_rules', {})
        
        # Get field value
        value = record_data.get(field_slug)
        
        # Create validator
        ai_config = field_def.get('ai_config', {}) if field_type == FieldType.AI_GENERATED else None
        validator = FieldValidator(field_type, field_config, ai_config)
        
        # Validate based on context
        if context == 'storage':
            result = validator.validate_storage(value, storage_constraints)
        else:
            # For now, other contexts use storage validation
            # Form and business validation will be implemented later
            result = validator.validate_storage(value, storage_constraints)
        
        if not result.is_valid:
            errors[field_slug] = result.errors
        else:
            cleaned_data[field_slug] = result.cleaned_value
        
        # Check business rules if we have a current stage
        if current_stage and business_rules:
            stage_requirements = business_rules.get('stage_requirements', {})
            if current_stage in stage_requirements:
                requirements = stage_requirements[current_stage]
                if requirements.get('required') and not value:
                    # Get display name from field config or use slug
                    display_name = field_def.get('display_name') or field_def.get('name') or field_slug
                    if field_slug not in errors:
                        errors[field_slug] = []
                    errors[field_slug].append(f"[BUSINESS_RULES] This field is required.")
    
    return {
        'is_valid': len(errors) == 0,
        'errors': errors,
        'cleaned_data': cleaned_data
    }