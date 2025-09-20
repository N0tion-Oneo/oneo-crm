"""
Pipeline stage changed trigger processor for workflows
Triggers when records move between pipeline stages
"""
from typing import Any, Dict
from ..base import AsyncNodeProcessor
import logging

logger = logging.getLogger(__name__)


class TriggerPipelineStageChangedProcessor(AsyncNodeProcessor):
    """
    Processor for pipeline stage change triggers
    Essential for CRM and sales automation

    DEPRECATED: Use trigger_record_updated with track_stage_changes option instead.
    This trigger will be removed in a future version.
    """

    node_type = "trigger_pipeline_stage_changed"
    is_deprecated = True  # Mark as deprecated

    # Configuration schema for pipeline stage triggers
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "pipeline_ids": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "description": "Pipelines to monitor for stage changes",
                "ui_hints": {
                    "widget": "pipeline_multiselect",
                    "placeholder": "Select pipelines to monitor"
                }
            },
            "from_stages": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Only trigger when moving FROM these stages (leave empty for any)",
                "ui_hints": {
                    "widget": "stage_multiselect",
                    "placeholder": "Select 'from' stages (optional)",
                    "depends_on": "pipeline_ids"
                }
            },
            "to_stages": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Only trigger when moving TO these stages (leave empty for any)",
                "ui_hints": {
                    "widget": "stage_multiselect",
                    "placeholder": "Select 'to' stages (optional)",
                    "depends_on": "pipeline_ids"
                }
            },
            "stage_direction": {
                "type": "string",
                "enum": ["forward", "backward", "any"],
                "default": "any",
                "description": "Direction of stage movement",
                "ui_hints": {
                    "widget": "select",
                    "options": [
                        {"value": "forward", "label": "Forward (progress)"},
                        {"value": "backward", "label": "Backward (regression)"},
                        {"value": "any", "label": "Any direction"}
                    ]
                }
            },
            "stage_patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Stage name patterns to match (regex supported)",
                "ui_hints": {
                    "widget": "text_list",
                    "placeholder": "e.g., 'qualified_*', 'closed_*'",
                    "section": "advanced"
                }
            },
            "track_stage_duration": {
                "type": "boolean",
                "default": True,
                "description": "Track how long records stayed in previous stage",
                "ui_hints": {
                    "widget": "checkbox"
                }
            },
            "minimum_stage_time_hours": {
                "type": "integer",
                "minimum": 0,
                "maximum": 8760,
                "default": 0,
                "description": "Minimum time in previous stage before triggering (hours)",
                "ui_hints": {
                    "widget": "number",
                    "placeholder": "0 = no minimum",
                    "show_when": {"track_stage_duration": True}
                }
            },
            "record_filters": {
                "type": "object",
                "description": "Additional filters for records",
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 4,
                    "placeholder": '{\n  "owner": "john@company.com",\n  "value": {"$gte": 1000}\n}',
                    "section": "advanced"
                }
            },
            "stage_field": {
                "type": "string",
                "default": "stage",
                "description": "Field name that contains the stage value",
                "ui_hints": {
                    "widget": "field_select",
                    "placeholder": "stage",
                    "section": "advanced"
                }
            },
            "include_stage_metadata": {
                "type": "boolean",
                "default": True,
                "description": "Include stage transition metadata in output",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            },
            "notify_on_regression": {
                "type": "boolean",
                "default": False,
                "description": "Send special notification for backward moves",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            }
        },
        "required": ["pipeline_ids"]
    }

    def get_required_fields(self) -> list:
        """Required fields for pipeline triggers"""
        return [
            'pipeline_id',  # The pipeline to monitor
        ]

    def get_optional_fields(self) -> list:
        """Optional fields for pipeline triggers"""
        return [
            'from_stage',      # Trigger only when moving from this stage
            'to_stage',        # Trigger only when moving to this stage
            'stage_field',     # Field name that contains the stage (default: 'stage')
            'record_type',     # Type of record to monitor
            'conditions',      # Additional conditions for triggering
        ]

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process pipeline stage change trigger
        """
        try:
            config = node_config.get('config', {})
            trigger_data = context.get('trigger_data', {})

            # Get pipeline and stage information
            pipeline_id = config.get('pipeline_id')
            from_stage = config.get('from_stage')
            to_stage = config.get('to_stage')
            stage_field = config.get('stage_field', 'stage')

            # Get the actual stage change from trigger data
            old_stage = trigger_data.get('old_values', {}).get(stage_field)
            new_stage = trigger_data.get('new_values', {}).get(stage_field)

            # Check if this is the stage transition we're looking for
            should_trigger = True
            if from_stage and old_stage != from_stage:
                should_trigger = False
            if to_stage and new_stage != to_stage:
                should_trigger = False

            if not should_trigger:
                return {
                    'success': False,
                    'trigger_type': 'pipeline_stage_changed',
                    'reason': 'Stage transition does not match criteria',
                    'expected': {'from': from_stage, 'to': to_stage},
                    'actual': {'from': old_stage, 'to': new_stage}
                }

            # Build output
            output = {
                'success': True,
                'trigger_type': 'pipeline_stage_changed',
                'pipeline_id': pipeline_id,
                'stage_transition': {
                    'from': old_stage,
                    'to': new_stage,
                    'field': stage_field
                },
                'record': trigger_data.get('record', {}),
                'record_id': trigger_data.get('record_id'),
                'record_type': config.get('record_type'),
                'timestamp': trigger_data.get('timestamp'),
            }

            logger.info(f"Pipeline stage trigger: {old_stage} -> {new_stage} for record {trigger_data.get('record_id')}")

            # Store in context for downstream nodes
            context['pipeline_trigger'] = output
            context['stage_from'] = old_stage
            context['stage_to'] = new_stage

            return output

        except Exception as e:
            logger.error(f"Pipeline stage trigger error: {e}")
            return {
                'success': False,
                'error': str(e),
                'trigger_type': 'pipeline_stage_changed'
            }