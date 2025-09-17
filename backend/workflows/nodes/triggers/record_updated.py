"""
Record updated trigger node processor
"""
import logging
from typing import Dict, Any
from workflows.nodes.base import BaseNodeProcessor

logger = logging.getLogger(__name__)


class TriggerRecordUpdatedProcessor(BaseNodeProcessor):
    """
    Processes record updated trigger events
    This node starts a workflow when a record is updated
    """

    node_type = "trigger_record_updated"

    # Configuration schema for record updated triggers
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "pipeline_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Which pipelines to monitor?",
                "ui_hints": {
                    "widget": "pipeline_multiselect",
                    "placeholder": "Select pipelines (empty = all pipelines)",
                    "help_text": "Leave empty to monitor all pipelines"
                }
            },
            "watch_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Only trigger if these fields change",
                "ui_hints": {
                    "widget": "field_multiselect",
                    "placeholder": "Select fields to watch",
                    "help_text": "Leave empty to trigger on any field change"
                }
            },
            "ignore_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ignore changes to these fields",
                "ui_hints": {
                    "widget": "field_multiselect",
                    "placeholder": "Select fields to ignore",
                    "help_text": "Changes to these fields won't trigger the workflow"
                }
            },
            "field_conditions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string"},
                        "operator": {"type": "string"},
                        "value": {}
                    }
                },
                "description": "When should updates trigger this workflow?",
                "ui_hints": {
                    "widget": "condition_builder",
                    "help_text": "Set conditions that updated records must meet to trigger",
                    "supports_change_operators": True
                }
            },
            "require_actual_changes": {
                "type": "boolean",
                "default": True,
                "description": "Only trigger if values actually changed",
                "ui_hints": {
                    "widget": "checkbox",
                    "help_text": "Skip if the update didn't change any values"
                }
            },
            "updated_by_filter": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Only trigger for updates by these users",
                "ui_hints": {
                    "widget": "user_multiselect",
                    "placeholder": "Select users",
                    "section": "advanced"
                }
            },
            "minimum_time_since_creation": {
                "type": "integer",
                "minimum": 0,
                "maximum": 86400,
                "description": "Minimum seconds after creation before triggering",
                "ui_hints": {
                    "widget": "number",
                    "placeholder": "60",
                    "help_text": "Avoid triggering immediately after record creation",
                    "section": "advanced"
                }
            },
            "maximum_updates_per_day": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "description": "Max triggers per record per day",
                "ui_hints": {
                    "widget": "number",
                    "placeholder": "10",
                    "help_text": "Prevent workflow loops from excessive updates",
                    "section": "advanced"
                }
            },
            "delay_seconds": {
                "type": "integer",
                "minimum": 0,
                "maximum": 3600,
                "default": 0,
                "description": "Delay before triggering (seconds)",
                "ui_hints": {
                    "widget": "number",
                    "section": "advanced"
                }
            }
        }
    }

    async def process(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process record updated trigger

        The record data from the event is passed in context['trigger_data']
        """
        trigger_data = context.get('trigger_data', {})

        # Extract configuration
        pipeline_ids = config.get('pipeline_ids', [])
        watch_fields = config.get('watch_fields', [])
        ignore_fields = config.get('ignore_fields', [])
        field_conditions = config.get('field_conditions', [])
        logic_operator = config.get('logic_operator', 'AND')
        group_operators = config.get('group_operators', {})

        # Extract record data
        record = trigger_data.get('record', {})
        previous_record = trigger_data.get('previous_record', {})
        pipeline_id = trigger_data.get('pipeline_id')
        updated_by = trigger_data.get('updated_by')
        changed_fields = trigger_data.get('changed_fields', [])

        logger.info(f"Record updated trigger activated for pipeline {pipeline_id}, fields changed: {changed_fields}")

        # Check if we have conditions to evaluate
        if field_conditions:
            from workflows.utils.condition_evaluator import condition_evaluator

            # Create context with both current and previous record for change operators
            eval_context = {
                **record,
                '_previous': previous_record,
                '_changed_fields': changed_fields
            }

            # Evaluate conditions against the record
            matches, details = condition_evaluator.evaluate(
                conditions=field_conditions,
                data=eval_context,
                logic_operator=logic_operator,
                group_operators=group_operators
            )

            if not matches:
                logger.info(f"Record updated trigger conditions not met: {details}")
                return {
                    'success': False,
                    'skip': True,
                    'reason': 'Conditions not met',
                    'evaluation_details': details
                }

        # Pass record data forward
        return {
            'success': True,
            'record': record,
            'previous_record': previous_record,
            'pipeline_id': pipeline_id,
            'updated_by': updated_by,
            'updated_at': trigger_data.get('updated_at'),
            'changed_fields': changed_fields,
            'trigger_type': 'record_updated'
        }

    def get_display_name(self) -> str:
        return "Record Updated Trigger"

    def get_description(self) -> str:
        return "Starts workflow when a record is updated"

    def get_category(self) -> str:
        return "Triggers"

    def get_icon(self) -> str:
        return "✏️"