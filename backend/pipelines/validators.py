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
                    print(f"🔧 FIELD CONFIG: Loaded AI config for {field_type}: {ai_config}")
                else:
                    self.config = self.config_class(**field_config)
                    print(f"🔧 FIELD CONFIG: Loaded config for {field_type}: {field_config}")
            except Exception as e:
                print(f"❌ FIELD CONFIG: Failed to load config for {field_type}: {e}")
                print(f"   📦 field_config: {field_config}")
                print(f"   📦 ai_config: {ai_config}")
                raise ValueError(f"Invalid field configuration: {e}")
        else:
            self.config = None
            print(f"⚠️  FIELD CONFIG: No config class found for {field_type}")
    
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
    
    def validate_field_config(self, value: Any) -> ValidationResult:
        """Validate value against field configuration constraints"""
        result = ValidationResult(cleaned_value=value, source='backend_field_config_validator')
        
        # Skip validation for empty values
        if self._is_empty(value):
            return result
        
        # Field-specific configuration validation
        try:
            if self.field_type == FieldType.SELECT and self.config:
                # Validate against allowed options
                options = getattr(self.config, 'options', [])
                if options:
                    valid_values = [opt.get('value') for opt in options if opt.get('value') is not None]
                    if value not in valid_values:
                        result.add_error(f"Value '{value}' is not in allowed options: {valid_values}", 'field_config')
            
            elif self.field_type == FieldType.NUMBER and self.config:
                # Comprehensive number field configuration validation
                number_format = getattr(self.config, 'format', 'integer')
                print(f"🔢 NUMBER FIELD CONFIG: Validating {number_format} format")
                
                # Format-specific validation
                if number_format == 'currency':
                    if isinstance(value, dict):
                        # Currency object validation
                        currency_code = value.get('currency')
                        config_currency = getattr(self.config, 'currency_code', None)
                        amount = value.get('amount')
                        
                        if config_currency and currency_code != config_currency:
                            result.add_error(f"Currency '{currency_code}' does not match configured currency '{config_currency}'", 'field_config')
                        
                        if amount is not None:
                            try:
                                amount_val = float(amount)
                                if amount_val < 0:
                                    result.add_error("Currency amount cannot be negative", 'field_config')
                            except (ValueError, TypeError):
                                result.add_error("Currency amount must be a valid number", 'field_config')
                    elif isinstance(value, (int, float)):
                        # Simple number for currency
                        if value < 0:
                            result.add_error("Currency amount cannot be negative", 'field_config')
                
                elif number_format == 'percentage':
                    try:
                        float_val = float(value)
                        percentage_display = getattr(self.config, 'percentage_display', 'decimal')
                        
                        if percentage_display == 'whole':
                            # Expecting whole numbers (0-100)
                            if float_val < 0 or float_val > 100:
                                result.add_error("Percentage must be between 0 and 100", 'field_config')
                        else:
                            # Expecting decimal (0-1)
                            if float_val < 0 or float_val > 1:
                                result.add_error("Percentage must be between 0 and 1", 'field_config')
                    except (ValueError, TypeError):
                        result.add_error("Percentage must be a valid number", 'field_config')
                
                elif number_format == 'integer':
                    try:
                        num_val = float(value)
                        if num_val != int(num_val):
                            result.add_error("Value must be a whole number (integer format)", 'field_config')
                    except (ValueError, TypeError):
                        result.add_error("Integer must be a valid whole number", 'field_config')
                
                elif number_format == 'decimal':
                    try:
                        float(value)  # Just ensure it's a valid number
                        decimal_places = getattr(self.config, 'decimal_places', 2)
                        
                        # Check decimal places if specified
                        if decimal_places is not None:
                            str_val = str(value)
                            if '.' in str_val:
                                actual_decimals = len(str_val.split('.')[1])
                                if actual_decimals > decimal_places:
                                    result.add_error(f"Number has too many decimal places. Maximum allowed: {decimal_places}", 'field_config')
                    except (ValueError, TypeError):
                        result.add_error("Decimal must be a valid number", 'field_config')
                
                elif number_format == 'auto_increment':
                    # Auto-increment fields should be system-generated, not user input
                    if value is not None:
                        auto_prefix = getattr(self.config, 'auto_increment_prefix', '')
                        if auto_prefix and not str(value).startswith(auto_prefix):
                            result.add_error(f"Auto-increment value must start with '{auto_prefix}'", 'field_config')
                
                else:
                    result.add_error(f"Invalid number format '{number_format}'. Must be one of: integer, decimal, currency, percentage, auto_increment", 'field_config')
            
            elif self.field_type == FieldType.PHONE and self.config:
                # Validate against allowed countries (handle both calling codes and ISO codes)
                allowed_countries = getattr(self.config, 'allowed_countries', [])
                if allowed_countries and isinstance(value, dict):
                    country_code = value.get('country_code')
                    if country_code:
                        # Create mapping between calling codes and ISO codes
                        calling_code_to_iso = {
                            '+1': 'US', '+44': 'GB', '+27': 'ZA', '+33': 'FR', '+49': 'DE',
                            '+39': 'IT', '+34': 'ES', '+31': 'NL', '+32': 'BE', '+41': 'CH',
                            '+43': 'AT', '+45': 'DK', '+46': 'SE', '+47': 'NO', '+358': 'FI',
                            '+353': 'IE', '+351': 'PT', '+30': 'GR', '+48': 'PL', '+420': 'CZ',
                            '+36': 'HU', '+40': 'RO', '+359': 'BG', '+385': 'HR', '+386': 'SI',
                            '+421': 'SK', '+370': 'LT', '+371': 'LV', '+372': 'EE', '+376': 'AD',
                            '+377': 'MC', '+378': 'SM', '+380': 'UA', '+381': 'RS', '+382': 'ME',
                            '+383': 'XK', '+385': 'HR', '+386': 'SI', '+387': 'BA', '+389': 'MK',
                            '+91': 'IN', '+86': 'CN', '+81': 'JP', '+82': 'KR', '+65': 'SG',
                            '+60': 'MY', '+66': 'TH', '+84': 'VN', '+63': 'PH', '+62': 'ID',
                            '+852': 'HK', '+853': 'MO', '+886': 'TW', '+7': 'RU', '+994': 'AZ',
                            '+374': 'AM', '+995': 'GE', '+996': 'KG', '+998': 'UZ', '+992': 'TJ',
                            '+993': 'TM', '+61': 'AU', '+64': 'NZ', '+679': 'FJ', '+685': 'WS'
                        }
                        
                        # Check if country_code is allowed (support both formats)
                        is_allowed = (
                            country_code in allowed_countries or  # Direct ISO match (ZA, US, etc.)
                            calling_code_to_iso.get(country_code) in allowed_countries  # Calling code to ISO ('+27' -> 'ZA')
                        )
                        
                        if not is_allowed:
                            # Show both formats in error for clarity
                            iso_code = calling_code_to_iso.get(country_code, 'Unknown')
                            result.add_error(
                                f"Country '{country_code}' (ISO: {iso_code}) is not in allowed countries: {allowed_countries}. "
                                f"Allowed calling codes: {[code for code, iso in calling_code_to_iso.items() if iso in allowed_countries]}", 
                                'field_config'
                            )
            
            elif self.field_type == FieldType.FILE and self.config:
                # Validate file type and size
                allowed_types = getattr(self.config, 'allowed_types', [])
                max_size = getattr(self.config, 'max_size', None)
                
                if isinstance(value, dict):
                    file_type = value.get('type', '')
                    file_size = value.get('size', 0)
                    
                    if allowed_types and not any(file_type.startswith(allowed_type) for allowed_type in allowed_types):
                        result.add_error(f"File type '{file_type}' is not allowed. Allowed types: {allowed_types}", 'field_config')
                    
                    if max_size and file_size > max_size:
                        result.add_error(f"File size {file_size} bytes exceeds maximum {max_size} bytes", 'field_config')
            
            elif self.field_type == FieldType.TAGS and self.config:
                # Validate against max tags limit
                max_tags = getattr(self.config, 'max_tags', None)
                if max_tags and isinstance(value, list) and len(value) > max_tags:
                    result.add_error(f"Number of tags ({len(value)}) exceeds maximum ({max_tags})", 'field_config')
                
                # Validate against predefined tags if allow_custom_tags is False
                predefined_tags = getattr(self.config, 'predefined_tags', [])
                allow_custom = getattr(self.config, 'allow_custom_tags', True)
                if not allow_custom and predefined_tags and isinstance(value, list):
                    invalid_tags = [tag for tag in value if tag not in predefined_tags]
                    if invalid_tags:
                        result.add_error(f"Custom tags not allowed. Invalid tags: {invalid_tags}", 'field_config')
                        
        except Exception as e:
            result.add_error(f"Field configuration validation error: {e}", 'field_config')
        
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
        
        # Apply format-specific validation and respect field configuration
        if config and hasattr(config, 'format'):
            print(f"🔢 NUMBER STORAGE: Validating {config.format} format, value={value}")
            
            if config.format == 'percentage':
                # Handle percentage validation based on display format
                percentage_display = getattr(config, 'percentage_display', 'decimal')
                percentage_decimal_places = getattr(config, 'percentage_decimal_places', 2)
                
                if percentage_display == 'whole':
                    # Input as whole number (75 for 75%)
                    if num < 0 or num > 100:
                        raise ValueError('Percentage must be between 0 and 100')
                    # Store as decimal (0.75) regardless of input format
                    num = num / 100
                else:
                    # Input as decimal (0.75 for 75%)
                    if num < 0 or num > 1:
                        raise ValueError('Percentage must be between 0 and 1')
                
                # Apply decimal places for percentage
                return round(num, percentage_decimal_places)
            
            elif config.format == 'currency':
                # Currency cannot be negative (in most cases)
                if isinstance(value, dict) and 'amount' in value:
                    # Validate currency object
                    amount = float(value['amount'])
                    if amount < 0:
                        raise ValueError('Currency amount cannot be negative')
                    
                    # Validate currency code if configured
                    if hasattr(config, 'currency_code') and config.currency_code:
                        currency_code = value.get('currency')
                        if currency_code and currency_code != config.currency_code:
                            raise ValueError(f"Currency '{currency_code}' does not match configured currency '{config.currency_code}'")
                    
                    return value  # Return the currency object as-is
                else:
                    # Simple number for currency
                    if num < 0:
                        raise ValueError('Currency amount cannot be negative')
                    return num
            
            elif config.format == 'integer':
                # Ensure it's a whole number
                if num != int(num):
                    raise ValueError('Value must be a whole number (integer format)')
                return int(num)
            
            elif config.format == 'decimal':
                # Apply decimal places constraint
                decimal_places = getattr(config, 'decimal_places', 2)
                return round(num, decimal_places)
            
            elif config.format == 'auto_increment':
                # Auto-increment values should be strings with prefix
                auto_prefix = getattr(config, 'auto_increment_prefix', '')
                auto_padding = getattr(config, 'auto_increment_padding', None)
                
                if auto_prefix or auto_padding:
                    # Convert to proper auto-increment format
                    if auto_padding:
                        num_str = str(int(num)).zfill(auto_padding)
                    else:
                        num_str = str(int(num))
                    
                    return f"{auto_prefix}{num_str}" if auto_prefix else num_str
                else:
                    return int(num)  # Simple integer for auto-increment
        
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


def _evaluate_condition(field_value: Any, operator: str, expected_value: Any) -> bool:
    """
    Evaluate a conditional rule based on operator
    
    Supports operators from conditional-rules-builder.tsx:
    equals, not_equals, contains, not_contains, greater_than, less_than,
    is_empty, is_not_empty, starts_with, ends_with
    """
    # Handle empty/null values
    is_empty = field_value is None or field_value == '' or field_value == []
    
    if operator == 'is_empty':
        return is_empty
    elif operator == 'is_not_empty':
        return not is_empty
    
    # For other operators, return False if field is empty
    if is_empty:
        return False
    
    # Convert to string for string operations
    field_str = str(field_value)
    expected_str = str(expected_value)
    
    if operator == 'equals':
        return field_value == expected_value
    elif operator == 'not_equals':
        return field_value != expected_value
    elif operator == 'contains':
        return expected_str.lower() in field_str.lower()
    elif operator == 'not_contains':
        return expected_str.lower() not in field_str.lower()
    elif operator == 'starts_with':
        return field_str.lower().startswith(expected_str.lower())
    elif operator == 'ends_with':
        return field_str.lower().endswith(expected_str.lower())
    elif operator == 'greater_than':
        try:
            return float(field_value) > float(expected_value)
        except (ValueError, TypeError):
            return False
    elif operator == 'less_than':
        try:
            return float(field_value) < float(expected_value)
        except (ValueError, TypeError):
            return False
    
    # Default to equals if operator not recognized
    return field_value == expected_value


def _evaluate_conditional_rules(rules_config: Any, record_data: dict) -> bool:
    """
    Unified conditional rule evaluation with AND/OR logic support
    
    Format:
    {
        "logic": "OR",
        "rules": [
            {
                "logic": "AND", 
                "rules": [
                    {"field": "sales_stage", "condition": "equals", "value": "proposal"},
                    {"field": "deal_size", "condition": "greater_than", "value": 10000}
                ]
            },
            {"field": "legal_stage", "condition": "equals", "value": "contract_review"}
        ]
    }
    """
    # Handle empty or invalid input
    if not rules_config:
        return False
    
    # Unified conditional rule format - object with logic and rules
    if not isinstance(rules_config, dict) or 'logic' not in rules_config:
        return False
        
    logic = rules_config.get('logic', 'AND').upper()
    rules = rules_config.get('rules', [])
    
    if not rules:
        return False
    
    results = []
    for rule in rules:
        if isinstance(rule, dict) and 'logic' in rule:
            # Nested group - recursive evaluation
            result = _evaluate_conditional_rules(rule, record_data)
        elif isinstance(rule, dict) and 'field' in rule:
            # Simple rule - evaluate using existing function
            field_name = rule.get('field')
            field_value = record_data.get(field_name)
            condition = rule.get('condition', 'equals')
            expected_value = rule.get('value')
            
            result = _evaluate_condition(field_value, condition, expected_value)
        else:
            # Invalid rule format
            result = False
            
        results.append(result)
    
    # Apply logic operator
    if logic == 'OR':
        return any(results)
    else:  # Default to AND
        return all(results)


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
    
    # Find stage field (look for select fields that might represent pipeline stages)
    # With the new conditional system, any select field can be a stage funnel
    for field_def in field_definitions:
        field_slug = field_def['slug']
        field_type = field_def.get('field_type', '')
        
        # If this is a select field in the data, it could be a stage field
        if field_slug in record_data and field_type == 'select':
            # We'll use the first select field we find as potential stage context
            # The conditional system will handle multiple stage funnels properly
            if current_stage is None:
                current_stage = record_data[field_slug]
                stage_field_slug = field_slug
    
    # If no select field found, check for common stage field names
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
            # Storage context: ONLY validate storage constraints (for partial updates)
            result = validator.validate_storage(value, storage_constraints)
            print(f"🔓 STORAGE VALIDATION: {field_slug} - no field config validation")
        elif context == 'business_rules':
            # Business rules context: Full validation (storage + field config + business rules)
            result = validator.validate_storage(value, storage_constraints)
            
            # Additional field configuration validation for business rules context
            if result.is_valid:
                config_result = validator.validate_field_config(value)
                if not config_result.is_valid:
                    result = config_result
                    print(f"🔒 FIELD CONFIG: {field_slug} validation failed")
                else:
                    print(f"🔒 FIELD CONFIG: {field_slug} validation passed")
        else:
            # Form context: Storage validation only (field config should be handled on frontend)
            result = validator.validate_storage(value, storage_constraints)
            print(f"🔓 FORM VALIDATION: {field_slug} - no field config validation (frontend handles this)")
        
        if not result.is_valid:
            errors[field_slug] = result.errors
        else:
            cleaned_data[field_slug] = result.cleaned_value
        
        # Check business rules ONLY if context allows it
        if context == 'business_rules' and business_rules:
            print(f"🔒 BUSINESS RULES: Checking {field_slug} with enhanced conditional system")
            
            # Use enhanced conditional system for all requirements
            conditional_rules = business_rules.get('conditional_rules', {})
            require_when_config = conditional_rules.get('require_when')
            
            if require_when_config:
                try:
                    condition_met = _evaluate_conditional_rules(require_when_config, record_data)
                    
                    if condition_met and not value:
                        display_name = field_def.get('display_name') or field_def.get('name') or field_slug
                        if field_slug not in errors:
                            errors[field_slug] = []
                        errors[field_slug].append(f"[BUSINESS_RULES] This field is required by conditional rules.")
                        print(f"   ❌ {field_slug} required due to conditional rules")
                except Exception as e:
                    print(f"   ⚠️ Error evaluating conditional rules for {field_slug}: {e}")
            
            # Note: stage_requirements are now maintained for UI compatibility only
            # All validation is handled through the unified conditional_rules system above
        elif context != 'business_rules' and business_rules:
            print(f"🔓 BUSINESS RULES: Skipping {field_slug} validation (context: {context})")
    
    return {
        'is_valid': len(errors) == 0,
        'errors': errors,
        'cleaned_data': cleaned_data
    }