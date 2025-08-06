"""
API views for field types metadata
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from pipelines.field_types import FieldType, FIELD_TYPE_CONFIGS, get_field_config_class
from pydantic import BaseModel
import json


class FieldTypeViewSet(viewsets.GenericViewSet):
    """
    Read-only viewset for field type metadata
    Provides field type definitions, configuration schemas, and capabilities
    """
    permission_classes = [IsAuthenticated]
    
    def get_field_type_metadata(self, field_type: FieldType) -> dict:
        """Get complete metadata for a field type"""
        config_class = get_field_config_class(field_type)
        
        # Generate JSON schema for the configuration class
        config_schema = {}
        if config_class != BaseModel:
            try:
                config_schema = config_class.schema()
                # Enhance schema with proper enum constraints
                config_schema = self.enhance_schema_with_enums(config_schema, field_type)
            except Exception:
                config_schema = {"type": "object", "properties": {}}
        
        # Determine field capabilities - Updated for Tier 1 (simplified validation)
        is_computed = field_type in [FieldType.RECORD_DATA, FieldType.AI_GENERATED]
        # Tier 1: Reduced validation capabilities - most validation moved to form level (Tier 3)
        supports_validation = field_type in [
            FieldType.EMAIL, FieldType.PHONE, FieldType.URL, FieldType.ADDRESS
        ]
        
        # Category mapping
        category_map = {
            # Basic Input Types
            FieldType.TEXT: 'basic',
            FieldType.TEXTAREA: 'basic', 
            FieldType.NUMBER: 'basic',
            FieldType.BOOLEAN: 'basic',
            FieldType.DATE: 'datetime',
            FieldType.PHONE: 'basic',
            FieldType.EMAIL: 'basic',
            FieldType.ADDRESS: 'basic',
            
            # Selection Types
            FieldType.SELECT: 'selection',
            FieldType.MULTISELECT: 'selection',
            FieldType.TAGS: 'selection',
            
            # Advanced Types
            FieldType.URL: 'advanced',
            FieldType.FILE: 'advanced',
            FieldType.BUTTON: 'advanced',
            FieldType.RELATION: 'advanced',
            
            # System Types
            FieldType.RECORD_DATA: 'system',
            FieldType.AI_GENERATED: 'system',
        }
        
        # Field descriptions - Updated for Tier 1 simplified configurations
        descriptions = {
            FieldType.TEXT: 'Single line text input (160 char limit, no defaults)',
            FieldType.TEXTAREA: 'Multi-line text input (auto-adjusting height)',
            FieldType.NUMBER: 'Numeric input with formatting (integer/decimal/currency/percentage/auto-increment)',
            FieldType.BOOLEAN: 'True/false checkbox',
            FieldType.DATE: 'Date picker with optional time (no default dates)',
            FieldType.PHONE: 'Phone number with country code selection',
            FieldType.EMAIL: 'Email address input (auto-lowercase, trim whitespace)',
            FieldType.ADDRESS: 'Structured address input with geocoding',
            FieldType.SELECT: 'Single choice dropdown selection',
            FieldType.MULTISELECT: 'Multiple choice selection',
            FieldType.TAGS: 'Tag input with autocomplete',
            FieldType.URL: 'URL input with auto-protocol addition',
            FieldType.FILE: 'File upload (includes images)',
            FieldType.BUTTON: 'Action button powered by workflows',
            FieldType.RELATION: 'Reference to another pipeline record (single selection)',
            FieldType.RECORD_DATA: 'Predefined record metadata and analytics',
            FieldType.AI_GENERATED: 'AI-powered field with latest OpenAI models (0-1 temperature)',
        }
        
        # Icon mapping (Lucide React icons)
        icons = {
            FieldType.TEXT: 'Type',
            FieldType.TEXTAREA: 'FileText',
            FieldType.NUMBER: 'Hash',
            FieldType.BOOLEAN: 'CheckSquare',
            FieldType.DATE: 'Calendar',
            FieldType.PHONE: 'Phone',
            FieldType.EMAIL: 'Mail',
            FieldType.ADDRESS: 'MapPin',
            FieldType.SELECT: 'List',
            FieldType.MULTISELECT: 'CheckSquare',
            FieldType.TAGS: 'Tags',
            FieldType.URL: 'Link',
            FieldType.FILE: 'Paperclip',
            FieldType.BUTTON: 'Play',
            FieldType.RELATION: 'Link2',
            FieldType.RECORD_DATA: 'Database',
            FieldType.AI_GENERATED: 'Bot',
        }
        
        return {
            'key': field_type.value,
            'label': field_type.value.replace('_', ' ').title(),
            'description': descriptions.get(field_type, 'Field type'),
            'category': category_map.get(field_type, 'basic'),
            'icon': icons.get(field_type, 'Type'),
            'config_schema': config_schema,
            'supports_validation': supports_validation,
            'is_computed': is_computed,
            'config_class': config_class.__name__ if config_class else 'BaseFieldConfig'
        }
    
    def list(self, request):
        """
        Get all available field types grouped by category
        """
        field_types_by_category = {}
        
        for field_type in FieldType:
            metadata = self.get_field_type_metadata(field_type)
            category = metadata['category']
            
            if category not in field_types_by_category:
                field_types_by_category[category] = []
            
            field_types_by_category[category].append(metadata)
        
        return Response(field_types_by_category)
    
    def retrieve(self, request, pk=None):
        """
        Get detailed information for a specific field type
        """
        try:
            field_type = FieldType(pk)
            metadata = self.get_field_type_metadata(field_type)
            return Response(metadata)
        except ValueError:
            return Response(
                {'error': f'Invalid field type: {pk}'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def config_schema(self, request, pk=None):
        """
        Get the configuration schema for a specific field type
        """
        try:
            field_type = FieldType(pk)
            config_class = get_field_config_class(field_type)
            
            if config_class == BaseModel:
                schema = {"type": "object", "properties": {}}
            else:
                schema = config_class.schema()
                # Enhance schema with proper enum constraints
                schema = self.enhance_schema_with_enums(schema, field_type)
            
            return Response({
                'field_type': field_type.value,
                'config_schema': schema,
                'config_class': config_class.__name__
            })
        except ValueError:
            return Response(
                {'error': f'Invalid field type: {pk}'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """
        Get field type categories with counts
        """
        categories = {}
        
        for field_type in FieldType:
            metadata = self.get_field_type_metadata(field_type)
            category = metadata['category']
            
            if category not in categories:
                categories[category] = {
                    'name': category.title(),
                    'count': 0,
                    'description': self.get_category_description(category)
                }
            
            categories[category]['count'] += 1
        
        return Response(categories)
    
    def get_category_description(self, category: str) -> str:
        """Get description for field type category"""
        descriptions = {
            'basic': 'Fundamental input fields for common data types',
            'selection': 'Fields for choosing from predefined options',
            'datetime': 'Date and time related fields',
            'advanced': 'Specialized fields with advanced functionality',
            'system': 'System-generated fields with computed values'
        }
        return descriptions.get(category, 'Field category')
    
    def enhance_schema_with_enums(self, schema: dict, field_type: FieldType) -> dict:
        """Enhance schema with proper enum constraints for dropdown fields"""
        if not schema.get('properties'):
            return schema
        
        # Define enum values for fields that should be dropdowns
        enum_mappings = {
            # Number field format options
            'format': {
                'enum': ['integer', 'decimal', 'currency', 'percentage', 'auto_increment'],
                'description': 'Number format type'
            },
            # Date field format options
            'date_format': {
                'enum': ['MM/DD/YYYY', 'DD/MM/YYYY', 'YYYY-MM-DD'],
                'description': 'Date format display'
            },
            'time_format': {
                'enum': ['12h', '24h'],
                'description': 'Time format display'
            },
            # Address field format options
            'address_format': {
                'enum': ['single_line', 'multi_line', 'structured'],
                'description': 'Address input format'
            },
            'display_format': {
                'enum': ['full', 'compact', 'custom'],
                'description': 'Address display format'
            },
            # Button field options
            'button_style': {
                'enum': ['primary', 'secondary', 'success', 'warning', 'danger'],
                'description': 'Button visual style'
            },
            'button_size': {
                'enum': ['small', 'medium', 'large'],
                'description': 'Button size'
            },
            # AI field options - models are dynamically configured per tenant
            # 'model' enum removed - should be loaded from tenant AI configuration
            'output_type': {
                'enum': ['text', 'number', 'tags', 'url', 'json'],
                'description': 'Expected output format'
            },
            # Record data field options
            'data_type': {
                'enum': ['timestamp', 'user', 'count', 'duration', 'status'],
                'description': 'Type of record data to display'
            },
            # Currency display options
            'currency_display': {
                'enum': ['symbol', 'code', 'none'],
                'description': 'How to display currency'
            },
            'percentage_display': {
                'enum': ['decimal', 'whole'],
                'description': 'Percentage display format'
            }
        }
        
        # Apply enum constraints to schema properties
        for prop_name, prop_schema in schema['properties'].items():
            if prop_name in enum_mappings:
                enum_config = enum_mappings[prop_name]
                prop_schema['enum'] = enum_config['enum']
                if 'description' not in prop_schema:
                    prop_schema['description'] = enum_config['description']
        
        return schema