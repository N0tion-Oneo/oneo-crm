"""
Field type definitions and configurations for dynamic pipelines
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, validator
from datetime import datetime, date
import re


# Storage Constraints - Database Level Only
class FieldStorageConstraints(BaseModel):
    """Database-level storage constraints - always allows incomplete data"""
    allow_null: bool = True                          # Always True - DB never enforces completeness
    max_storage_length: Optional[int] = None         # Physical VARCHAR limits only
    enforce_uniqueness: bool = False                 # Only for true business uniqueness
    create_index: bool = False                       # Performance optimization
    
    # Type-specific storage constraints
    numeric_precision: Optional[int] = None          # DECIMAL precision for numbers
    numeric_scale: Optional[int] = None              # DECIMAL scale for numbers
    check_constraints: List[str] = []                # Custom DB CHECK constraints
    
    class Config:
        extra = "forbid"


# Business Rules - Pipeline Logic
class FieldBusinessRules(BaseModel):
    """Business logic rules for pipeline stages and workflows"""
    # Stage-based requirements
    stage_requirements: Dict[str, Dict[str, Any]] = {}  # {"qualified": {"required": True}}
    
    # Conditional requirements
    conditional_requirements: List[Dict[str, Any]] = []  # [{"condition_field": "type", "condition_value": "enterprise", "requires_field": "company"}]
    
    # Transition rules
    transition_rules: Dict[str, List[str]] = {}         # {"lead_to_qualified": ["phone", "email"]}
    
    # Validation settings
    block_transitions: bool = True                       # Block stage changes if requirements not met
    show_warnings: bool = True                          # Show warnings for missing data
    warning_message: Optional[str] = None               # Custom warning message
    
    class Config:
        extra = "forbid"


class FieldType(str, Enum):
    """Enumeration of available field types - Refined Architecture (16 core types)"""
    
    # Basic Input Types (8)
    TEXT = "text"                    # Single line text input
    TEXTAREA = "textarea"            # Multi-line text input
    NUMBER = "number"                # All numeric types (integer/decimal/currency/percentage/auto-increment)
    BOOLEAN = "boolean"              # True/false checkbox
    DATE = "date"                    # Date picker with optional time
    PHONE = "phone"                  # Phone number with country code
    EMAIL = "email"                  # Email address input
    ADDRESS = "address"              # Structured address input
    
    # Selection Types (3)
    SELECT = "select"                # Single choice dropdown
    MULTISELECT = "multiselect"      # Multiple choice selection
    TAGS = "tags"                    # Tag input with autocomplete
    
    # Advanced Types (4)
    URL = "url"                      # URL input with validation
    FILE = "file"                    # File upload (includes images)
    BUTTON = "button"                # Action button powered by workflows
    RELATION = "relation"            # Reference to another pipeline record
    
    # System Types (2)
    RECORD_DATA = "record_data"      # Predefined record metadata
    AI_GENERATED = "ai_generated"    # AI-powered field with latest OpenAI models


class BaseFieldConfig(BaseModel):
    """Base configuration for all field types - Tier 1 only (no defaults, no placeholders)"""
    help_text: Optional[str] = None
    
    class Config:
        extra = "forbid"  # Don't allow extra fields


class TextFieldConfig(BaseFieldConfig):
    """Configuration for single-line text fields - Tier 1 (no length limits, hard cap at 160 chars)"""
    # No min/max length validation per requirements - hard cap at 160 characters handled at storage level
    case_sensitive: bool = True
    auto_format: bool = False  # Auto-formatting rules


class TextareaFieldConfig(BaseFieldConfig):
    """Configuration for multi-line text fields - Tier 1 (auto-adjusting height, no length limits)"""
    # No rows/resize options per requirements - should adjust based on content
    # No min/max length validation per requirements
    enable_rich_text: bool = False  # Rich text editor toggle


class EmailFieldConfig(BaseFieldConfig):
    """Configuration for email fields - Tier 1 (no domain suggestions)"""
    # Storage constraints moved to FieldStorageConstraints
    # Form validation will be handled by form builder
    # Only keep display and behavior configurations here
    
    # Display options
    auto_lowercase: bool = True          # Automatically convert to lowercase
    trim_whitespace: bool = True         # Remove leading/trailing spaces
    
    # Domain suggestions removed per requirements


class URLFieldConfig(BaseFieldConfig):
    """Configuration for URL fields - storage and display focused"""
    # Storage constraints moved to FieldStorageConstraints
    # Protocol validation will be form-level
    
    # Display behavior
    open_in_new_tab: bool = True         # Display behavior
    show_favicon: bool = False           # Display URL favicon
    preview_on_hover: bool = False       # Show URL preview on hover
    
    # Auto-formatting
    auto_add_protocol: bool = True       # Add http:// if missing
    trim_whitespace: bool = True         # Remove leading/trailing spaces


class NumberFieldConfig(BaseFieldConfig):
    """Configuration for consolidated number fields - display and behavior focused"""
    format: str = 'integer'  # 'integer', 'decimal', 'currency', 'percentage', 'auto_increment'
    
    # Auto-increment settings
    auto_increment_prefix: Optional[str] = None    # "INV-", "CUST-", etc.
    auto_increment_padding: Optional[int] = None   # Zero-pad to X digits
    auto_increment_start: Optional[int] = 1        # Starting number
    
    # Currency settings (dynamic from global options, not hardcoded)
    currency_code: Optional[str] = None           # Selected from global currency list
    currency_display: str = 'symbol'             # 'symbol', 'code', 'none'
    
    # Percentage settings
    percentage_decimal_places: Optional[int] = 2
    percentage_display: str = 'decimal'          # 'decimal' (0.75) or 'whole' (75%)
    
    # Display formatting (not validation)
    decimal_places: int = 2
    thousands_separator: bool = True
    
    @validator('format')
    def validate_format(cls, v):
        valid_formats = ['integer', 'decimal', 'currency', 'percentage', 'auto_increment']
        if v not in valid_formats:
            raise ValueError(f'Format must be one of: {valid_formats}')
        return v
    
    @validator('decimal_places', 'percentage_decimal_places')
    def validate_decimal_places(cls, v):
        if v is not None and (v < 0 or v > 10):
            raise ValueError('Decimal places must be between 0 and 10')
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
    """Configuration for relation fields - Tier 1 (single selection only)"""
    target_pipeline_id: int
    display_field: str = 'title'
    # allow_multiple removed per requirements - single selection only 
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


class DateFieldConfig(BaseFieldConfig):
    """Configuration for consolidated date fields"""
    include_time: bool = False            # false = date only, true = datetime
    default_time: Optional[str] = None    # Default time when date selected (e.g., "09:00")
    date_format: str = 'MM/DD/YYYY'       # 'MM/DD/YYYY', 'DD/MM/YYYY', 'YYYY-MM-DD'
    time_format: str = '12h'              # '12h' or '24h'
    min_date: Optional[str] = None        # Minimum selectable date
    max_date: Optional[str] = None        # Maximum selectable date
    # default_value removed per requirements - no defaults
    
    @validator('date_format')
    def validate_date_format(cls, v):
        valid_formats = ['MM/DD/YYYY', 'DD/MM/YYYY', 'YYYY-MM-DD']
        if v not in valid_formats:
            raise ValueError(f'Date format must be one of: {valid_formats}')
        return v
    
    @validator('time_format')
    def validate_time_format(cls, v):
        valid_formats = ['12h', '24h']
        if v not in valid_formats:
            raise ValueError(f'Time format must be one of: {valid_formats}')
        return v


class PhoneFieldConfig(BaseFieldConfig):
    """Configuration for phone fields with dynamic country support and formatting"""
    default_country: Optional[str] = None    # Selected from global country list (e.g., 'US', 'ZA', 'GB')
    allowed_countries: List[str] = []        # Restrict to specific countries (dynamic)
    format_display: bool = True              # Auto-format display with country-specific patterns
    require_country_code: bool = True        # Show country selector vs simple input
    
    # Country-specific formatting options
    auto_format_input: bool = True           # Format phone number as user types
    validation_pattern: Optional[str] = None # Custom regex pattern for validation
    
    # Display preferences
    display_format: str = 'international'    # 'international', 'national', 'compact'
    show_country_flag: bool = False          # Show country flag in display (future feature)
    
    @validator('display_format')
    def validate_display_format(cls, v):
        valid_formats = ['international', 'national', 'compact']
        if v not in valid_formats:
            raise ValueError(f'Display format must be one of: {valid_formats}')
        return v


class AddressFieldConfig(BaseFieldConfig):
    """Configuration for structured address fields"""
    address_format: str = 'structured'       # 'single_line', 'multi_line', 'structured'
    
    # Structured format components
    components: Dict[str, bool] = {
        'street_address': True,
        'apartment_suite': True,
        'city': True,
        'state_province': True,
        'postal_code': True,
        'country': True
    }
    
    # Geocoding and validation
    enable_geocoding: bool = False           # Auto-complete and validation
    default_country: Optional[str] = None    # Selected from global country list
    require_validation: bool = False         # Must be valid address
    
    # Display options
    display_format: str = 'full'             # 'full', 'compact', 'custom'
    
    @validator('address_format')
    def validate_address_format(cls, v):
        valid_formats = ['single_line', 'multi_line', 'structured']
        if v not in valid_formats:
            raise ValueError(f'Address format must be one of: {valid_formats}')
        return v
    
    @validator('display_format')
    def validate_display_format(cls, v):
        valid_formats = ['full', 'compact', 'custom']
        if v not in valid_formats:
            raise ValueError(f'Display format must be one of: {valid_formats}')
        return v


class ButtonFieldConfig(BaseFieldConfig):
    """Configuration for workflow-powered button fields"""
    button_text: str                         # "Send Email", "Mark Complete", etc.
    button_style: str = 'primary'            # 'primary', 'secondary', 'success', 'warning', 'danger'
    button_size: str = 'medium'              # 'small', 'medium', 'large'
    
    # Workflow Integration
    workflow_id: Optional[str] = None        # Connected workflow to trigger
    workflow_params: Dict[str, Any] = {}     # Parameters to pass to workflow
    
    # Behavior
    require_confirmation: bool = False       # Show "Are you sure?" dialog
    confirmation_message: Optional[str] = None
    disable_after_click: bool = False        # Prevent multiple clicks
    
    # Permissions
    visible_to_roles: List[str] = []         # Which user roles can see button
    clickable_by_roles: List[str] = []       # Which user roles can click
    
    @validator('button_style')
    def validate_button_style(cls, v):
        valid_styles = ['primary', 'secondary', 'success', 'warning', 'danger']
        if v not in valid_styles:
            raise ValueError(f'Button style must be one of: {valid_styles}')
        return v
    
    @validator('button_size')
    def validate_button_size(cls, v):
        valid_sizes = ['small', 'medium', 'large']
        if v not in valid_sizes:
            raise ValueError(f'Button size must be one of: {valid_sizes}')
        return v


class RecordDataFieldConfig(BaseFieldConfig):
    """Configuration for predefined record metadata fields"""
    data_type: str                           # 'timestamp', 'user', 'count', 'duration', 'status'
    
    # Timestamp fields
    timestamp_type: Optional[str] = None     # 'created_at', 'updated_at', 'last_engaged_at', etc.
    
    # User fields  
    user_type: Optional[str] = None          # 'created_by', 'updated_by', 'first_contacted_by', etc.
    
    # Count fields
    count_type: Optional[str] = None         # 'total_communications', 'days_in_pipeline', etc.
    
    # Duration fields
    duration_type: Optional[str] = None      # 'time_to_response', 'stage_duration', etc.
    
    # Status fields
    status_type: Optional[str] = None        # 'engagement_status', 'response_status', etc.
    
    # Display formatting
    format: str = 'relative'                 # 'relative' ("2 days ago") vs 'absolute' ("Jan 15, 2024")
    include_time: bool = False               # For timestamp fields
    
    @validator('data_type')
    def validate_data_type(cls, v):
        valid_types = ['timestamp', 'user', 'count', 'duration', 'status']
        if v not in valid_types:
            raise ValueError(f'Data type must be one of: {valid_types}')
        return v


class AIGeneratedFieldConfig(BaseFieldConfig):
    """Configuration for AI-powered fields with latest OpenAI models and tools"""
    # Core AI Settings - Latest Models (2025)
    model: str = 'gpt-4.1-mini'              # Cost-effective default
    prompt: str                              # The prompt template
    temperature: float = 0.3                 # AI creativity level
    
    # OpenAI Tools Integration
    enable_tools: bool = False               # Safety: tools disabled by default
    allowed_tools: List[str] = []            # 'web_search', 'code_interpreter', 'file_reader', 'dalle', 'image_generation'
    
    # Context & Triggers
    trigger_fields: List[str] = []           # Which fields trigger regeneration
    include_all_fields: bool = True          # AI can access all record data
    excluded_fields: List[str] = []          # Fields to hide from AI
    
    # Output Configuration
    output_type: str = 'text'                # 'text', 'number', 'tags', 'url', 'json'
    is_editable: bool = True                 # Users can edit AI output after generation
    auto_regenerate: bool = True             # Auto-update when triggers change
    cache_duration: int = 3600               # Cache AI responses (seconds)
    
    # Advanced Settings
    max_tokens: Optional[int] = None
    timeout: int = 120                       # Max execution time
    fallback_value: Any = None               # Value if AI fails
    
    @validator('prompt')
    def validate_prompt(cls, v):
        if not v or not v.strip():
            raise ValueError('AI prompt cannot be empty')
        return v
    
    @validator('model')
    def validate_model(cls, v):
        # Model validation is now handled at tenant level via AI configuration
        # This allows tenant admins to configure which models are available
        if not v or not isinstance(v, str) or len(v.strip()) == 0:
            raise ValueError('AI model must be a non-empty string')
        return v
    
    @validator('allowed_tools')
    def validate_allowed_tools(cls, v):
        valid_tools = ['web_search', 'code_interpreter', 'file_reader', 'dalle', 'image_generation']
        for tool in v:
            if tool not in valid_tools:
                raise ValueError(f'Invalid tool: {tool}. Valid tools: {valid_tools}')
        return v
    
    @validator('output_type')
    def validate_output_type(cls, v):
        valid_types = ['text', 'number', 'tags', 'url', 'json']
        if v not in valid_types:
            raise ValueError(f'Output type must be one of: {valid_types}')
        return v
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Temperature must be between 0 and 1')
        return v


class TagsFieldConfig(BaseFieldConfig):
    """Configuration for tags fields"""
    predefined_tags: List[str] = []
    allow_custom_tags: bool = True
    max_tags: Optional[int] = None
    case_sensitive: bool = False
    
    @validator('predefined_tags')
    def validate_predefined_tags(cls, v):
        if v:
            # Check for duplicates
            tags_lower = [tag.lower() for tag in v]
            if len(tags_lower) != len(set(tags_lower)):
                raise ValueError('Predefined tags must be unique (case-insensitive)')
            
            # Check for empty tags
            if any(not tag.strip() for tag in v):
                raise ValueError('Predefined tags cannot be empty')
        return v
    
    @validator('max_tags')
    def validate_max_tags(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Max tags must be positive')
        return v


# Field type registry - maps field types to their configuration classes
FIELD_TYPE_CONFIGS = {
    # Basic Input Types (8) - Now with proper field-specific configurations
    FieldType.TEXT: TextFieldConfig,            # Clean single-line text
    FieldType.TEXTAREA: TextareaFieldConfig,    # Multi-line with rows, resize options
    FieldType.NUMBER: NumberFieldConfig,        # Consolidated numeric handling
    FieldType.BOOLEAN: BaseFieldConfig,
    FieldType.DATE: DateFieldConfig,            # Consolidated date/datetime
    FieldType.PHONE: PhoneFieldConfig,          # Enhanced with country codes
    FieldType.EMAIL: EmailFieldConfig,          # Proper email validation and domain options
    FieldType.ADDRESS: AddressFieldConfig,      # Structured address field
    
    # Selection Types (3)
    FieldType.SELECT: SelectFieldConfig,
    FieldType.MULTISELECT: SelectFieldConfig,
    FieldType.TAGS: TagsFieldConfig,
    
    # Advanced Types (4)
    FieldType.URL: URLFieldConfig,              # Proper URL validation and protocol options
    FieldType.FILE: FileFieldConfig,            # Includes images
    FieldType.BUTTON: ButtonFieldConfig,        # New workflow-powered buttons
    FieldType.RELATION: RelationFieldConfig,    # Reference to another pipeline
    
    # System Types (2)
    FieldType.RECORD_DATA: RecordDataFieldConfig,    # New predefined metadata
    FieldType.AI_GENERATED: AIGeneratedFieldConfig,  # Enhanced AI with latest models
}


def get_field_config_class(field_type: FieldType) -> BaseFieldConfig:
    """Get the configuration class for a field type"""
    return FIELD_TYPE_CONFIGS.get(field_type, BaseFieldConfig)


def validate_field_config(field_type: FieldType, config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate field configuration against field type"""
    # For AI fields, field_config can be empty since config is in ai_config
    if field_type == FieldType.AI_GENERATED and not config:
        return {}
    
    config_class = get_field_config_class(field_type)
    try:
        validated_config = config_class(**config)
        return validated_config.dict()
    except Exception as e:
        raise ValueError(f"Invalid configuration for field type {field_type}: {e}")