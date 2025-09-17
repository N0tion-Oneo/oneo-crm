"""
Form submission trigger node processor
"""
import logging
from typing import Dict, Any, Optional
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class TriggerFormSubmittedProcessor(AsyncNodeProcessor):
    """
    Processes form submission trigger events
    This node starts a workflow when a form is submitted
    """

    node_type = "trigger_form_submitted"

    # Configuration schema for form submission triggers
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "pipeline_id": {
                "type": "string",
                "description": "Pipeline",
                "required": True,
                "ui_hints": {
                    "widget": "pipeline_select",
                    "placeholder": "Select pipeline",
                    "help_text": "Select the pipeline for the form",
                    "on_change_update": ["form_selection"]  # Clear form selection when pipeline changes
                }
            },
            "form_selection": {
                "type": "string",
                "description": "Form Selection",
                "required": True,
                "ui_hints": {
                    "widget": "dynamic_select",
                    "placeholder": "Select a form",
                    "help_text": "Select a specific form for this pipeline",
                    "fetch_endpoint": "/api/v1/pipelines/{pipeline_id}/forms/available-forms/",
                    "depends_on": "pipeline_id",
                    "value_field": "id",
                    "label_field": "label",
                    "show_field_count": True,
                    "group_by": "type"  # Groups forms by general vs stage-specific
                }
            },
            "form_url_preview": {
                "type": "string",
                "description": "Form URL Preview",
                "ui_hints": {
                    "widget": "readonly_text",
                    "help_text": "This is the URL that will be generated for your form",
                    "computed_from": "form_metadata.url",
                    "show_when": {"form_selection": {"$exists": True}}
                }
            },
            "required_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Fields that must be present in submission",
                "ui_hints": {
                    "widget": "field_multiselect",
                    "placeholder": "Select required fields"
                }
            },
            "field_conditions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {
                            "type": "string",
                            "description": "Field to check"
                        },
                        "operator": {
                            "type": "string",
                            "description": "Comparison operator"
                        },
                        "value": {
                            "description": "Value to compare against"
                        }
                    }
                },
                "description": "Field value conditions that must be met",
                "ui_hints": {
                    "widget": "condition_builder",
                    "help_text": "Define conditions that form submissions must meet to trigger the workflow"
                }
            },
            "spam_detection": {
                "type": "boolean",
                "default": True,
                "description": "Enable spam detection and filtering",
                "ui_hints": {
                    "widget": "checkbox"
                }
            },
            "duplicate_prevention": {
                "type": "boolean",
                "default": True,
                "description": "Prevent duplicate form submissions",
                "ui_hints": {
                    "widget": "checkbox"
                }
            },
            "auto_create_record": {
                "type": "boolean",
                "default": True,
                "description": "Automatically create record from form data",
                "ui_hints": {
                    "widget": "checkbox"
                }
            },
            "notification_email": {
                "type": "string",
                "format": "email",
                "description": "Email address for submission notifications",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "notify@example.com"
                }
            },
            "submission_limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1000,
                "description": "Maximum submissions per time period",
                "ui_hints": {
                    "widget": "number",
                    "section": "advanced"
                }
            },
            "limit_time_window": {
                "type": "integer",
                "minimum": 60,
                "maximum": 86400,
                "default": 3600,
                "description": "Time window for submission limits (seconds)",
                "ui_hints": {
                    "widget": "number",
                    "section": "advanced",
                    "show_when": {"submission_limit": {"$exists": True}}
                }
            },
            "skip_validation": {
                "type": "boolean",
                "default": False,
                "description": "Skip form validation checks",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            }
        }
    }

    async def process(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process form submission trigger

        The trigger_data is nested in the context from the trigger_registry
        """
        # Get the nested trigger_data from context
        trigger_data = context.get('trigger_data', {})

        # Extract form data from trigger_data
        form_data = trigger_data.get('form_data', {})
        pipeline_id = config.get('pipeline_id') or trigger_data.get('pipeline_id')

        # Parse form_selection to extract mode and stage if needed
        form_selection = config.get('form_selection', '')
        form_mode = 'public_filtered'  # default
        stage = None

        if form_selection:
            # Form selection format: {pipeline_id}_{mode} or {pipeline_id}_{mode}_{stage}
            parts = form_selection.split('_')
            if len(parts) >= 2:
                form_mode = '_'.join(parts[1:3]) if parts[1] == 'stage' else parts[1] + '_' + parts[2] if len(parts) > 2 and parts[2] in ['full', 'filtered', 'internal', 'public'] else parts[1]
                if 'stage' in form_mode and len(parts) > 3:
                    stage = '_'.join(parts[3:])

        # Extract condition configuration
        field_conditions = config.get('field_conditions', [])
        logic_operator = config.get('logic_operator', 'AND')
        group_operators = config.get('group_operators', {})

        logger.info(f"Form submission trigger activated for pipeline {pipeline_id}, form_mode={form_mode}")

        # Check if we have conditions to evaluate against form data
        if field_conditions:
            from workflows.utils.condition_evaluator import condition_evaluator

            # Evaluate conditions against the form data
            matches, details = condition_evaluator.evaluate(
                conditions=field_conditions,
                data=form_data,
                logic_operator=logic_operator,
                group_operators=group_operators
            )

            if not matches:
                logger.info(f"Form submission trigger conditions not met: {details}")
                return {
                    'success': False,
                    'skip': True,
                    'reason': 'Form submission conditions not met',
                    'evaluation_details': details
                }

        # Add submission metadata
        submission_info = {
            'submitted_at': trigger_data.get('submitted_at'),
            'ip_address': trigger_data.get('ip_address'),
            'user_agent': trigger_data.get('user_agent'),
        }

        # Generate form metadata
        form_id = f"{pipeline_id}_{form_mode}"
        if stage:
            form_id += f"_{stage}"

        form_url = self._generate_form_url(pipeline_id, form_mode, stage)

        # Get required and visible fields for this form
        try:
            from pipelines.models import Pipeline
            from pipelines.form_generation import DynamicFormGenerator

            pipeline = Pipeline.objects.get(id=pipeline_id)
            generator = DynamicFormGenerator(pipeline)
            form_schema = generator.generate_form(mode=form_mode, stage=stage)

            required_fields = [f.field_slug for f in form_schema.fields if f.is_required]
            visible_fields = [f.field_slug for f in form_schema.fields if f.is_visible]
        except Exception as e:
            logger.warning(f"Could not fetch form metadata: {e}")
            required_fields = []
            visible_fields = []

        # Pass the form data forward in the workflow
        return {
            'success': True,
            'form_data': form_data,
            'pipeline_id': pipeline_id,
            'form_mode': form_mode,
            'stage': stage,
            'form_selection': form_selection,
            'form_metadata': {
                'id': form_id,
                'url': form_url,
                'mode': form_mode,
                'stage': stage,
                'required_fields': required_fields,
                'visible_fields': visible_fields
            },
            'submission_info': submission_info,
            'trigger_type': 'form_submitted'
        }

    def _generate_form_url(self, pipeline_id: str, form_mode: str, stage: Optional[str] = None) -> str:
        """Generate the form URL based on mode and stage"""
        if form_mode == 'internal_full':
            return f'/forms/internal/{pipeline_id}'
        elif form_mode == 'public_filtered':
            # Would need pipeline slug here, using ID as fallback
            return f'/forms/{pipeline_id}'
        elif form_mode == 'stage_internal' and stage:
            return f'/forms/internal/{pipeline_id}?stage={stage}'
        elif form_mode == 'stage_public' and stage:
            return f'/forms/{pipeline_id}/stage/{stage}'
        return '/forms'

    def get_display_name(self) -> str:
        return "Form Submission Trigger"

    def get_description(self) -> str:
        return "Starts workflow when a form is submitted"

    def get_category(self) -> str:
        return "Triggers"

    def get_icon(self) -> str:
        return "📝"