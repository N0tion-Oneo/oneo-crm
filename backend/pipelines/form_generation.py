"""
Dynamic form generation system for pipelines
Generates forms based on pipeline fields with different modes
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from .models import Pipeline, Field


@dataclass
class DynamicFieldConfig:
    """Configuration for a dynamically generated form field"""
    field_id: int
    field_slug: str
    field_name: str
    field_type: str
    display_name: str
    help_text: str
    is_required: bool
    is_visible: bool
    is_readonly: bool
    display_order: int
    field_config: Dict[str, Any]
    storage_constraints: Dict[str, Any]
    form_validation_rules: Dict[str, Any] = None
    default_value: Any = None
    placeholder: str = ""
    current_value: Any = None  # For shared record forms


@dataclass
class DynamicFormSchema:
    """Schema for a dynamically generated form"""
    pipeline_id: int
    pipeline_name: str
    form_mode: str
    target_stage: Optional[str]
    fields: List[DynamicFieldConfig]
    total_fields: int
    required_fields: int
    visible_fields: int


class DynamicFormGenerator:
    """Generates forms dynamically from pipeline definitions"""
    
    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline
    
    def generate_form(self, mode: str = 'internal_full', stage: Optional[str] = None, 
                     record_data: Optional[Dict[str, Any]] = None) -> DynamicFormSchema:
        """
        Generate a dynamic form based on the specified mode
        
        Args:
            mode: Form generation mode:
                - 'internal_full': All fields (Type 1)
                - 'public_filtered': Only public-visible fields (Type 2)
                - 'stage_internal': Stage-required fields, all visibility (Type 3)
                - 'stage_public': Stage-required AND public-visible fields (Type 4)
                - 'shared_record': Public-visible fields with record data (Type 5)
            stage: Target stage for stage-specific forms
            record_data: Existing record data for shared forms
        
        Returns:
            DynamicFormSchema with field configurations
        """
        # Get base fields from pipeline
        base_fields = self.pipeline.fields.all().order_by('display_order', 'name')
        
        # Apply filtering based on mode
        if mode == 'internal_full':
            # Type 1: All fields (permission-based filtering applied at API level)
            filtered_fields = base_fields.filter(is_visible_in_detail=True)
        elif mode == 'public_filtered':
            # Type 2: Only public-visible fields
            filtered_fields = base_fields.filter(
                is_visible_in_public_forms=True,
                is_visible_in_detail=True
            )
        elif mode == 'stage_internal' and stage:
            # Type 3: Stage-required fields (all visibility)
            filtered_fields = self._filter_fields_by_stage(base_fields, stage)
        elif mode == 'stage_public' and stage:
            # Type 4: Stage-required AND public-visible (double filter)
            stage_fields = self._filter_fields_by_stage(base_fields, stage)
            filtered_fields = [f for f in stage_fields if f.is_visible_in_public_forms]
        elif mode == 'shared_record':
            # Type 5: Public-visible fields with record data
            filtered_fields = base_fields.filter(
                is_visible_in_public_forms=True,
                is_visible_in_detail=True
            )
        else:
            # Default fallback
            filtered_fields = base_fields.filter(is_visible_in_detail=True)
        
        # Convert to dynamic field configurations
        dynamic_fields = []
        required_count = 0
        visible_count = 0
        
        for field in filtered_fields:
            # Determine if field is required based on stage and business rules
            is_required = self._is_field_required(field, stage)
            is_visible = field.is_visible_in_detail
            
            if is_required:
                required_count += 1
            if is_visible:
                visible_count += 1
            
            # Get current value for shared record forms
            current_value = None
            if mode == 'shared_record' and record_data:
                current_value = record_data.get(field.slug)
            
            dynamic_field = DynamicFieldConfig(
                field_id=field.id,
                field_slug=field.slug,
                field_name=field.name,
                field_type=field.field_type,
                display_name=field.display_name or field.name,
                help_text=field.help_text,
                is_required=is_required,
                is_visible=is_visible,
                is_readonly=False,  # Forms are for input, not display
                display_order=field.display_order,
                field_config=field.field_config,
                storage_constraints=field.storage_constraints,
                form_validation_rules=field.form_validation_rules,
                placeholder=self._generate_placeholder(field),
                current_value=current_value
            )
            
            dynamic_fields.append(dynamic_field)
        
        return DynamicFormSchema(
            pipeline_id=self.pipeline.id,
            pipeline_name=self.pipeline.name,
            form_mode=mode,
            target_stage=stage,
            fields=dynamic_fields,
            total_fields=len(dynamic_fields),
            required_fields=required_count,
            visible_fields=visible_count
        )
    
    def _filter_fields_by_stage(self, fields, stage: str) -> List[Field]:
        """Filter fields based on stage-specific business rules"""
        filtered_fields = []
        
        for field in fields:
            # Check if field has stage-specific requirements
            business_rules = field.business_rules or {}
            stage_requirements = business_rules.get('stage_requirements', {})
            
            # Include field if:
            # 1. It has requirements for this stage
            # 2. It has no stage requirements (always visible)
            # 3. It's marked as visible
            if (stage in stage_requirements or 
                not stage_requirements or 
                field.is_visible_in_detail):
                filtered_fields.append(field)
        
        return filtered_fields
    
    def _is_field_required(self, field: Field, stage: Optional[str] = None) -> bool:
        """Determine if a field is required based on business rules and stage"""
        business_rules = field.business_rules or {}
        
        # Check stage-specific requirements
        if stage:
            stage_requirements = business_rules.get('stage_requirements', {})
            if stage in stage_requirements:
                return stage_requirements[stage].get('required', False)
        
        # Check general business rules for required fields
        # For now, we don't have a general 'required' flag in pipeline fields
        # This would be handled by form-level validation rules instead
        return False
    
    def _generate_placeholder(self, field: Field) -> str:
        """Generate appropriate placeholder text for a field"""
        field_type = field.field_type.lower()
        field_name = field.display_name or field.name
        
        placeholder_map = {
            'text': f'Enter {field_name.lower()}',
            'textarea': f'Enter {field_name.lower()}',
            'email': 'Enter email address',
            'phone': 'Enter phone number',
            'url': 'Enter URL',
            'number': f'Enter {field_name.lower()}',
            'decimal': f'Enter {field_name.lower()}',
            'date': 'Select date',
            'datetime': 'Select date and time',
            'time': 'Select time',
            'select': f'Choose {field_name.lower()}',
            'multiselect': f'Choose {field_name.lower()}',
            'boolean': f'Check if {field_name.lower()}',
            'currency': 'Enter amount',
            'percentage': 'Enter percentage',
        }
        
        return placeholder_map.get(field_type, f'Enter {field_name.lower()}')
    
    def get_available_stages(self) -> List[str]:
        """Get all stages that have business rules defined in pipeline fields"""
        stages = set()
        
        for field in self.pipeline.fields.all():
            business_rules = field.business_rules or {}
            stage_requirements = business_rules.get('stage_requirements', {})
            stages.update(stage_requirements.keys())
        
        return sorted(list(stages))
    
    def to_json_schema(self, form_schema: DynamicFormSchema) -> Dict[str, Any]:
        """Convert dynamic form schema to JSON schema format for frontend"""
        json_schema = {
            'pipeline_id': form_schema.pipeline_id,
            'pipeline_name': form_schema.pipeline_name,
            'form_mode': form_schema.form_mode,
            'target_stage': form_schema.target_stage,
            'metadata': {
                'total_fields': form_schema.total_fields,
                'required_fields': form_schema.required_fields,
                'visible_fields': form_schema.visible_fields,
            },
            'fields': []
        }
        
        for field in form_schema.fields:
            field_json = {
                'id': field.field_id,
                'slug': field.field_slug,
                'name': field.field_name,
                'type': field.field_type,
                'display_name': field.display_name,
                'help_text': field.help_text,
                'placeholder': field.placeholder,
                'is_required': field.is_required,
                'is_visible': field.is_visible,
                'is_readonly': field.is_readonly,
                'display_order': field.display_order,
                'field_config': field.field_config,
                'storage_constraints': field.storage_constraints,
                'form_validation_rules': field.form_validation_rules,
                'default_value': field.default_value,
                'current_value': field.current_value,
            }
            json_schema['fields'].append(field_json)
        
        return json_schema


def generate_pipeline_form(pipeline_id: int, mode: str = 'internal_full', 
                          stage: Optional[str] = None, 
                          record_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Convenience function to generate a dynamic form for a pipeline
    
    Args:
        pipeline_id: ID of the pipeline to generate form for
        mode: Form generation mode:
            - 'internal_full': All fields (Type 1)
            - 'public_filtered': Only public-visible fields (Type 2)
            - 'stage_internal': Stage-required fields, all visibility (Type 3)
            - 'stage_public': Stage-required AND public-visible fields (Type 4)
            - 'shared_record': Public-visible fields with record data (Type 5)
        stage: Target stage for stage-specific forms
        record_data: Existing record data for shared forms
    
    Returns:
        JSON schema for the dynamic form
    """
    try:
        pipeline = Pipeline.objects.get(id=pipeline_id)
        generator = DynamicFormGenerator(pipeline)
        form_schema = generator.generate_form(mode=mode, stage=stage, record_data=record_data)
        return generator.to_json_schema(form_schema)
    except Pipeline.DoesNotExist:
        raise ValueError(f"Pipeline with ID {pipeline_id} does not exist")


def get_pipeline_stages(pipeline_id: int) -> List[str]:
    """
    Get available stages for a pipeline based on field business rules
    
    Args:
        pipeline_id: ID of the pipeline
    
    Returns:
        List of stage names that have business rules defined
    """
    try:
        pipeline = Pipeline.objects.get(id=pipeline_id)
        generator = DynamicFormGenerator(pipeline)
        return generator.get_available_stages()
    except Pipeline.DoesNotExist:
        return []