"""
Field type definitions and configurations for dynamic pipelines
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, validator
from datetime import datetime, date
import re


class FieldType(str, Enum):
    """Enumeration of available field types"""
    # Basic types
    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    
    # Date/Time types
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"
    
    # Selection types
    SELECT = "select"
    MULTISELECT = "multiselect"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    
    # Advanced types
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    COLOR = "color"
    FILE = "file"
    IMAGE = "image"
    
    # Relationship types
    RELATION = "relation"
    USER = "user"
    
    # AI types
    AI_FIELD = "ai_field"
    
    # System types
    COMPUTED = "computed"
    FORMULA = "formula"


class BaseFieldConfig(BaseModel):
    """Base configuration for all field types"""
    default_value: Any = None
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    
    class Config:
        extra = "forbid"  # Don't allow extra fields


class TextFieldConfig(BaseFieldConfig):
    """Configuration for text fields"""
    min_length: Optional[int] = None
    max_length: Optional[int] = 500
    pattern: Optional[str] = None
    multiline: bool = False
    
    @validator('pattern')
    def validate_pattern(cls, v):
        if v:
            try:
                re.compile(v)
            except re.error:
                raise ValueError('Invalid regex pattern')
        return v
    
    @validator('min_length', 'max_length')
    def validate_length(cls, v):
        if v is not None and v < 0:
            raise ValueError('Length must be non-negative')
        return v


class NumberFieldConfig(BaseFieldConfig):
    """Configuration for number fields"""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    
    @validator('step')
    def validate_step(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Step must be positive')
        return v


class DecimalFieldConfig(BaseFieldConfig):
    """Configuration for decimal fields"""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    decimal_places: int = 2
    max_digits: int = 10
    
    @validator('decimal_places', 'max_digits')
    def validate_digits(cls, v):
        if v < 0:
            raise ValueError('Digits must be non-negative')
        return v


class SelectFieldConfig(BaseFieldConfig):
    """Configuration for select fields"""
    options: List[Dict[str, Any]] = []
    allow_multiple: bool = False
    allow_custom: bool = False
    
    @validator('options')
    def validate_options(cls, v):
        if not v:
            raise ValueError('Select field must have at least one option')
        for option in v:
            if not isinstance(option, dict):
                raise ValueError('Each option must be a dictionary')
            if 'value' not in option or 'label' not in option:
                raise ValueError('Each option must have value and label')
        return v


class RelationFieldConfig(BaseFieldConfig):
    """Configuration for relation fields"""
    target_pipeline_id: int
    display_field: str = 'title'
    allow_multiple: bool = False
    reverse_field_name: Optional[str] = None
    
    @validator('target_pipeline_id')
    def validate_target_pipeline_id(cls, v):
        if v <= 0:
            raise ValueError('Target pipeline ID must be positive')
        return v


class FileFieldConfig(BaseFieldConfig):
    """Configuration for file fields"""
    allowed_types: List[str] = []
    max_size: int = 10485760  # 10MB default
    upload_path: str = 'uploads/'
    
    @validator('max_size')
    def validate_max_size(cls, v):
        if v <= 0:
            raise ValueError('Max size must be positive')
        return v


class AIFieldConfig(BaseFieldConfig):
    """Configuration for AI fields with tool integration"""
    # Core AI configuration
    ai_prompt: str  # The actual prompt template with field substitutions {field_name}
    ai_model: str = 'gpt-4'
    
    # Tool capabilities
    enable_tools: bool = False  # Safety: tools disabled by default
    allowed_tools: List[str] = []  # Specific tools: ['web_search', 'code_interpreter', 'dalle']
    tool_budget: Optional[Dict[str, int]] = None  # Usage limits per tool
    
    # Context configuration
    include_all_fields: bool = True  # AI can access all record data via {field_name}
    excluded_fields: List[str] = []  # Fields to hide from AI (e.g., sensitive data)
    include_metadata: bool = True    # Include created_at, updated_at, etc.
    include_record_id: bool = True   # Include record ID and pipeline info
    include_external_context: bool = False  # Allow web search for additional context
    
    # Field-specific triggers (optional optimization)
    update_triggers: List[str] = []  # If empty, updates on ANY field change
    
    # Output configuration
    output_type: str = 'text'  # 'text', 'number', 'json', 'boolean', 'image', 'file'
    output_format: Optional[str] = None  # Additional formatting instructions
    
    # Behavior settings
    auto_update: bool = True
    cache_duration: int = 3600  # Cache AI responses and tool results (seconds)
    temperature: float = 0.3  # AI creativity level
    max_tokens: Optional[int] = None
    timeout: int = 120  # Max execution time for tool-enabled fields
    
    # Advanced features
    multi_step_reasoning: bool = False  # Allow AI to use tools in sequence
    save_tool_outputs: bool = False     # Store intermediate tool results for debugging
    
    # Security and validation
    fallback_value: Any = None  # Value if AI fails
    validation_rules: Dict[str, Any] = {}  # Validate AI output
    require_approval: bool = False  # Manual approval for sensitive operations
    
    @validator('ai_prompt')
    def validate_ai_prompt(cls, v):
        if not v or not v.strip():
            raise ValueError('AI prompt cannot be empty')
        return v
    
    @validator('ai_model')
    def validate_ai_model(cls, v):
        allowed_models = ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo']
        if v not in allowed_models:
            raise ValueError(f'AI model must be one of: {allowed_models}')
        return v
    
    @validator('allowed_tools')
    def validate_allowed_tools(cls, v):
        valid_tools = ['web_search', 'code_interpreter', 'dalle']
        for tool in v:
            if tool not in valid_tools:
                raise ValueError(f'Invalid tool: {tool}. Valid tools: {valid_tools}')
        return v
    
    @validator('output_type')
    def validate_output_type(cls, v):
        valid_types = ['text', 'number', 'json', 'boolean', 'image', 'file']
        if v not in valid_types:
            raise ValueError(f'Output type must be one of: {valid_types}')
        return v
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if not 0 <= v <= 2:
            raise ValueError('Temperature must be between 0 and 2')
        return v
    
    @validator('timeout')
    def validate_timeout(cls, v):
        if v <= 0 or v > 600:  # Max 10 minutes
            raise ValueError('Timeout must be between 1 and 600 seconds')
        return v


# Field type registry - maps field types to their configuration classes
FIELD_TYPE_CONFIGS = {
    FieldType.TEXT: TextFieldConfig,
    FieldType.TEXTAREA: TextFieldConfig,
    FieldType.NUMBER: NumberFieldConfig,
    FieldType.DECIMAL: DecimalFieldConfig,
    FieldType.BOOLEAN: BaseFieldConfig,
    FieldType.DATE: BaseFieldConfig,
    FieldType.DATETIME: BaseFieldConfig,
    FieldType.TIME: BaseFieldConfig,
    FieldType.SELECT: SelectFieldConfig,
    FieldType.MULTISELECT: SelectFieldConfig,
    FieldType.RADIO: SelectFieldConfig,
    FieldType.CHECKBOX: BaseFieldConfig,
    FieldType.EMAIL: TextFieldConfig,
    FieldType.PHONE: TextFieldConfig,
    FieldType.URL: TextFieldConfig,
    FieldType.COLOR: BaseFieldConfig,
    FieldType.FILE: FileFieldConfig,
    FieldType.IMAGE: FileFieldConfig,
    FieldType.RELATION: RelationFieldConfig,
    FieldType.USER: BaseFieldConfig,
    FieldType.AI_FIELD: AIFieldConfig,
    FieldType.COMPUTED: BaseFieldConfig,
    FieldType.FORMULA: TextFieldConfig,
}


def get_field_config_class(field_type: FieldType) -> BaseFieldConfig:
    """Get the configuration class for a field type"""
    return FIELD_TYPE_CONFIGS.get(field_type, BaseFieldConfig)


def validate_field_config(field_type: FieldType, config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate field configuration against field type"""
    # For AI fields, field_config can be empty since config is in ai_config
    if field_type == FieldType.AI_FIELD and not config:
        return {}
    
    config_class = get_field_config_class(field_type)
    try:
        validated_config = config_class(**config)
        return validated_config.dict()
    except Exception as e:
        raise ValueError(f"Invalid configuration for field type {field_type}: {e}")