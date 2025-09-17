"""
Record created trigger node processor
"""
import logging
from typing import Dict, Any
from workflows.nodes.base import BaseNodeProcessor

logger = logging.getLogger(__name__)


class TriggerRecordCreatedProcessor(BaseNodeProcessor):
    """
    Processes record created trigger events
    This node starts a workflow when a record is created
    """

    node_type = "trigger_record_created"

    # Configuration schema for record created triggers
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
                "description": "When should this trigger activate?",
                "ui_hints": {
                    "widget": "condition_builder",
                    "help_text": "Set conditions that new records must meet to trigger this workflow"
                }
            },
            "created_by_filter": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Only trigger for records created by",
                "ui_hints": {
                    "widget": "user_multiselect",
                    "placeholder": "Select users",
                    "help_text": "Leave empty for all users",
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
            },
            "batch_processing": {
                "type": "boolean",
                "default": False,
                "description": "Process multiple records as batch",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            },
            "batch_size": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "default": 10,
                "description": "Maximum records per batch",
                "ui_hints": {
                    "widget": "number",
                    "show_when": {"batch_processing": True},
                    "section": "advanced"
                }
            },
            "batch_timeout": {
                "type": "integer",
                "minimum": 1,
                "maximum": 60,
                "default": 5,
                "description": "Wait time before processing batch (seconds)",
                "ui_hints": {
                    "widget": "number",
                    "show_when": {"batch_processing": True},
                    "section": "advanced"
                }
            }
        }
    }

    async def process(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process record created trigger

        The record data from the event is passed in context['trigger_data']
        """
        trigger_data = context.get('trigger_data', {})

        # Extract configuration
        pipeline_ids = config.get('pipeline_ids', [])
        field_conditions = config.get('field_conditions', [])
        logic_operator = config.get('logic_operator', 'AND')
        group_operators = config.get('group_operators', {})

        # Extract record data
        record = trigger_data.get('record', {})
        pipeline_id = trigger_data.get('pipeline_id')
        created_by = trigger_data.get('created_by')

        logger.info(f"Record created trigger activated for pipeline {pipeline_id}")

        # Check if we have conditions to evaluate
        if field_conditions:
            from workflows.utils.condition_evaluator import condition_evaluator

            # Evaluate conditions against the record
            matches, details = condition_evaluator.evaluate(
                conditions=field_conditions,
                data=record,
                logic_operator=logic_operator,
                group_operators=group_operators
            )

            if not matches:
                logger.info(f"Record created trigger conditions not met: {details}")
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
            'pipeline_id': pipeline_id,
            'created_by': created_by,
            'created_at': trigger_data.get('created_at'),
            'trigger_type': 'record_created'
        }

    def get_display_name(self) -> str:
        return "Record Created Trigger"

    def get_description(self) -> str:
        return "Starts workflow when a new record is created"

    def get_category(self) -> str:
        return "Triggers"

    def get_icon(self) -> str:
        return "➕"