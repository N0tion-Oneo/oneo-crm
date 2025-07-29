"""
Field validation system for dynamic pipeline fields
"""
from typing import Any, Dict, List, Union
from datetime import datetime, date, time
import re
import json
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from .field_types import FieldType, FIELD_TYPE_CONFIGS


class ValidationResult:
    """Result of field validation"""
    
    def __init__(self, is_valid: bool = True, cleaned_value: Any = None, errors: List[str] = None):
        self.is_valid = is_valid
        self.cleaned_value = cleaned_value
        self.errors = errors or []
    
    def add_error(self, error: str):
        """Add validation error"""
        self.is_valid = False
        self.errors.append(error)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'is_valid': self.is_valid,
            'cleaned_value': self.cleaned_value,
            'errors': self.errors
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
                if field_type == FieldType.AI_FIELD and ai_config:
                    self.config = self.config_class(**ai_config)
                else:
                    self.config = self.config_class(**field_config)
            except Exception as e:
                raise ValueError(f"Invalid field configuration: {e}")
        else:
            self.config = None
    
    def validate(self, value: Any, is_required: bool = False) -> ValidationResult:
        """Validate field value and return result with any errors"""
        result = ValidationResult(cleaned_value=value)
        
        # Check required
        if is_required and self._is_empty(value):
            result.add_error('This field is required')
            return result
        
        # Skip validation for empty optional fields
        if self._is_empty(value):
            result.cleaned_value = None
            return result
        
        # Type-specific validation
        try:
            if self.field_type == FieldType.TEXT:
                result.cleaned_value = self._validate_text(value)
            elif self.field_type == FieldType.TEXTAREA:
                result.cleaned_value = self._validate_textarea(value)
            elif self.field_type == FieldType.NUMBER:
                result.cleaned_value = self._validate_number(value)
            elif self.field_type == FieldType.DECIMAL:
                result.cleaned_value = self._validate_decimal(value)
            elif self.field_type == FieldType.BOOLEAN:
                result.cleaned_value = self._validate_boolean(value)
            elif self.field_type == FieldType.DATE:
                result.cleaned_value = self._validate_date(value)
            elif self.field_type == FieldType.DATETIME:
                result.cleaned_value = self._validate_datetime(value)
            elif self.field_type == FieldType.TIME:
                result.cleaned_value = self._validate_time(value)
            elif self.field_type == FieldType.EMAIL:
                result.cleaned_value = self._validate_email(value)
            elif self.field_type == FieldType.PHONE:
                result.cleaned_value = self._validate_phone(value)
            elif self.field_type == FieldType.URL:
                result.cleaned_value = self._validate_url(value)
            elif self.field_type == FieldType.COLOR:
                result.cleaned_value = self._validate_color(value)
            elif self.field_type in [FieldType.SELECT, FieldType.MULTISELECT, FieldType.RADIO]:
                result.cleaned_value = self._validate_select(value)
            elif self.field_type == FieldType.CHECKBOX:
                result.cleaned_value = self._validate_checkbox(value)
            elif self.field_type in [FieldType.FILE, FieldType.IMAGE]:
                result.cleaned_value = self._validate_file(value)
            elif self.field_type == FieldType.RELATION:
                result.cleaned_value = self._validate_relation(value)
            elif self.field_type == FieldType.USER:
                result.cleaned_value = self._validate_user(value)
            elif self.field_type == FieldType.AI_FIELD:
                result.cleaned_value = self._validate_ai_field(value)
            else:
                # For computed, formula, or unknown types, accept as-is
                result.cleaned_value = value
                
        except ValueError as e:
            result.add_error(str(e))
        except Exception as e:
            result.add_error(f"Validation error: {e}")
        
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
        """Validate text field"""
        if not isinstance(value, str):
            value = str(value)
        
        value = value.strip()
        
        if self.config:
            if self.config.min_length and len(value) < self.config.min_length:
                raise ValueError(f'Text must be at least {self.config.min_length} characters')
            
            if self.config.max_length and len(value) > self.config.max_length:
                raise ValueError(f'Text must not exceed {self.config.max_length} characters')
            
            if self.config.pattern and not re.match(self.config.pattern, value):
                raise ValueError('Text does not match required pattern')
        
        return value
    
    def _validate_textarea(self, value: Any) -> str:
        """Validate textarea field (same as text but typically allows more length)"""
        return self._validate_text(value)
    
    def _validate_number(self, value: Any) -> float:
        """Validate number field"""
        try:
            if isinstance(value, str):
                value = value.strip()
            num = float(value)
        except (TypeError, ValueError):
            raise ValueError('Value must be a number')
        
        if self.config:
            if self.config.min_value is not None and num < self.config.min_value:
                raise ValueError(f'Number must be at least {self.config.min_value}')
            
            if self.config.max_value is not None and num > self.config.max_value:
                raise ValueError(f'Number must not exceed {self.config.max_value}')
        
        return num
    
    def _validate_decimal(self, value: Any) -> Decimal:
        """Validate decimal field"""
        try:
            if isinstance(value, str):
                value = value.strip()
            decimal_value = Decimal(str(value))
        except (TypeError, ValueError, InvalidOperation):
            raise ValueError('Value must be a valid decimal number')
        
        if self.config:
            if self.config.min_value is not None and decimal_value < Decimal(str(self.config.min_value)):
                raise ValueError(f'Decimal must be at least {self.config.min_value}')
            
            if self.config.max_value is not None and decimal_value > Decimal(str(self.config.max_value)):
                raise ValueError(f'Decimal must not exceed {self.config.max_value}')
            
            # Check decimal places
            if decimal_value.as_tuple().exponent < -self.config.decimal_places:
                raise ValueError(f'Decimal cannot have more than {self.config.decimal_places} decimal places')
        
        return float(decimal_value)
    
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
    
    def _validate_date(self, value: Any) -> date:
        """Validate date field"""
        if isinstance(value, date):
            return value
        
        if isinstance(value, datetime):
            return value.date()
        
        if isinstance(value, str):
            try:
                # Try common date formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                    try:
                        return datetime.strptime(value.strip(), fmt).date()
                    except ValueError:
                        continue
            except Exception:
                pass
        
        raise ValueError('Invalid date format. Use YYYY-MM-DD')
    
    def _validate_datetime(self, value: Any) -> datetime:
        """Validate datetime field"""
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            try:
                # Try ISO format first
                return datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
            except ValueError:
                # Try other common formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%m/%d/%Y %H:%M:%S']:
                    try:
                        return datetime.strptime(value.strip(), fmt)
                    except ValueError:
                        continue
        
        raise ValueError('Invalid datetime format. Use ISO format or YYYY-MM-DD HH:MM:SS')
    
    def _validate_time(self, value: Any) -> time:
        """Validate time field"""
        if isinstance(value, time):
            return value
        
        if isinstance(value, datetime):
            return value.time()
        
        if isinstance(value, str):
            try:
                # Try common time formats
                for fmt in ['%H:%M:%S', '%H:%M', '%I:%M %p']:
                    try:
                        return datetime.strptime(value.strip(), fmt).time()
                    except ValueError:
                        continue
            except Exception:
                pass
        
        raise ValueError('Invalid time format. Use HH:MM:SS or HH:MM')
    
    def _validate_email(self, value: Any) -> str:
        """Validate email field"""
        if not isinstance(value, str):
            raise ValueError('Email must be a string')
        
        email = value.strip().lower()
        
        # Basic email regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValueError('Invalid email format')
        
        return email
    
    def _validate_phone(self, value: Any) -> str:
        """Validate phone field"""
        if not isinstance(value, str):
            value = str(value)
        
        # Remove common phone number characters
        phone = re.sub(r'[^\d+]', '', value.strip())
        
        # Basic phone validation (US format)
        if not re.match(r'^\+?1?[2-9]\d{2}[2-9]\d{2}\d{4}$', phone):
            # Try international format
            if not re.match(r'^\+\d{1,3}\d{4,14}$', phone):
                raise ValueError('Invalid phone number format')
        
        return phone
    
    def _validate_url(self, value: Any) -> str:
        """Validate URL field"""
        if not isinstance(value, str):
            raise ValueError('URL must be a string')
        
        url = value.strip()
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                raise ValueError('Invalid URL format')
        except Exception:
            raise ValueError('Invalid URL format')
        
        return url
    
    def _validate_color(self, value: Any) -> str:
        """Validate color field (hex format)"""
        if not isinstance(value, str):
            raise ValueError('Color must be a string')
        
        color = value.strip()
        
        # Validate hex color format
        if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
            raise ValueError('Color must be in hex format (#RRGGBB)')
        
        return color.upper()
    
    def _validate_select(self, value: Any) -> Union[Any, List[Any]]:
        """Validate select/multiselect/radio field"""
        if not self.config or not self.config.options:
            raise ValueError('No options configured for select field')
        
        valid_values = [opt['value'] for opt in self.config.options]
        
        # Handle multiselect
        if self.config.allow_multiple:
            if not isinstance(value, list):
                # Convert single value to list
                value = [value] if value is not None else []
            
            cleaned_values = []
            for v in value:
                if v in valid_values:
                    cleaned_values.append(v)
                else:
                    if self.config.allow_custom:
                        cleaned_values.append(v)
                    else:
                        raise ValueError(f'Invalid option: {v}')
            
            return cleaned_values
        else:
            # Single select
            if value not in valid_values:
                if self.config.allow_custom:
                    return value
                else:
                    raise ValueError(f'Invalid option: {value}')
            
            return value
    
    def _validate_checkbox(self, value: Any) -> List[Any]:
        """Validate checkbox field (multiple selections)"""
        if not isinstance(value, list):
            value = [value] if value is not None else []
        
        return value
    
    def _validate_file(self, value: Any) -> Dict[str, Any]:
        """Validate file field"""
        if isinstance(value, dict):
            # File info structure
            required_keys = ['filename', 'size']
            if not all(key in value for key in required_keys):
                raise ValueError('File must have filename and size')
            
            if self.config:
                # Check file size
                if value['size'] > self.config.max_size:
                    raise ValueError(f'File size exceeds maximum of {self.config.max_size} bytes')
                
                # Check file type
                if self.config.allowed_types:
                    filename = value['filename']
                    file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
                    if file_ext not in self.config.allowed_types:
                        raise ValueError(f'File type .{file_ext} not allowed. Allowed types: {self.config.allowed_types}')
            
            return value
        
        raise ValueError('File must be a dictionary with filename and size')
    
    def _validate_relation(self, value: Any) -> Union[int, List[int]]:
        """Validate relation field"""
        if self.config and self.config.allow_multiple:
            if not isinstance(value, list):
                value = [value] if value is not None else []
            
            cleaned_values = []
            for v in value:
                try:
                    cleaned_values.append(int(v))
                except (ValueError, TypeError):
                    raise ValueError(f'Relation value must be an integer ID: {v}')
            
            return cleaned_values
        else:
            try:
                return int(value)
            except (ValueError, TypeError):
                raise ValueError('Relation value must be an integer ID')
    
    def _validate_user(self, value: Any) -> int:
        """Validate user field"""
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ValueError('User value must be an integer user ID')
    
    def _validate_ai_field(self, value: Any) -> Any:
        """Validate AI field (flexible validation based on output type)"""
        if not self.config:
            return value
        
        output_type = self.config.output_type
        
        if output_type == 'json':
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    raise ValueError('Invalid JSON format')
            return value
        
        elif output_type == 'number':
            try:
                return float(value)
            except (ValueError, TypeError):
                raise ValueError('AI field output must be a number')
        
        elif output_type == 'boolean':
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower().strip() in ['true', 'yes', '1']
            raise ValueError('AI field output must be a boolean')
        
        else:
            # Text or other types - accept as string
            return str(value) if value is not None else None


def validate_record_data(field_definitions: List[Dict[str, Any]], record_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate complete record data against field definitions
    
    Args:
        field_definitions: List of field definition dictionaries
        record_data: Dictionary of field values to validate
        
    Returns:
        Dictionary with validation results
    """
    errors = {}
    cleaned_data = {}
    
    for field_def in field_definitions:
        field_slug = field_def['slug']
        field_type = FieldType(field_def['field_type'])
        field_config = field_def.get('field_config', {})
        is_required = field_def.get('is_required', False)
        
        # Get field value
        value = record_data.get(field_slug)
        
        # Validate field (pass ai_config for AI fields)
        ai_config = field_def.get('ai_config', {}) if field_type == FieldType.AI_FIELD else None
        validator = FieldValidator(field_type, field_config, ai_config)
        result = validator.validate(value, is_required)
        
        if not result.is_valid:
            errors[field_slug] = result.errors
        else:
            cleaned_data[field_slug] = result.cleaned_value
    
    return {
        'is_valid': len(errors) == 0,
        'errors': errors,
        'cleaned_data': cleaned_data
    }