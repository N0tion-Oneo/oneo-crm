"""
Record updated trigger node processor
"""
import logging
from typing import Dict, Any
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class TriggerRecordUpdatedProcessor(AsyncNodeProcessor):
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
            "track_stage_changes": {
                "type": "boolean",
                "default": False,
                "description": "",
                "ui_hints": {
                    "widget": "stage_tracking_toggle"
                }
            },
            "from_stages": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Only trigger when moving FROM these stages",
                "ui_hints": {
                    "widget": "stage_options_multiselect",
                    "stage_field_key": "watch_fields",
                    "placeholder": "Any stage",
                    "help_text": "Leave empty to trigger from any stage",
                    "show_when": {"track_stage_changes": True}
                }
            },
            "to_stages": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Only trigger when moving TO these stages",
                "ui_hints": {
                    "widget": "stage_options_multiselect",
                    "stage_field_key": "watch_fields",
                    "placeholder": "Any stage",
                    "help_text": "Leave empty to trigger to any stage",
                    "show_when": {"track_stage_changes": True}
                }
            },
            "stage_direction": {
                "type": "string",
                "enum": ["forward", "backward", "any"],
                "default": "any",
                "description": "Direction of stage movement",
                "ui_hints": {
                    "widget": "select",
                    "show_when": {"track_stage_changes": True},
                    "options": [
                        {"value": "forward", "label": "Forward only (progress)"},
                        {"value": "backward", "label": "Backward only (regression)"},
                        {"value": "any", "label": "Any direction"}
                    ]
                }
            },
            "track_stage_duration": {
                "type": "boolean",
                "default": False,
                "description": "Track time spent in previous stage",
                "ui_hints": {
                    "widget": "checkbox",
                    "show_when": {"track_stage_changes": True},
                    "section": "advanced"
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
                "description": "",
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

        # Stage tracking configuration
        track_stage_changes = config.get('track_stage_changes', False)
        # When stage tracking is enabled, the stage field is the watched field
        stage_field = watch_fields[0] if track_stage_changes and len(watch_fields) == 1 else None
        from_stages = config.get('from_stages', [])
        to_stages = config.get('to_stages', [])
        stage_direction = config.get('stage_direction', 'any')
        track_stage_duration = config.get('track_stage_duration', False)

        # Extract record data
        record = trigger_data.get('record', {})
        previous_record = trigger_data.get('previous_record', {})
        pipeline_id = trigger_data.get('pipeline_id')
        updated_by = trigger_data.get('updated_by')
        changed_fields = trigger_data.get('changed_fields', [])

        logger.info(f"Record updated trigger activated for pipeline {pipeline_id}, fields changed: {changed_fields}")

        # Handle stage change tracking if enabled
        stage_transition = None
        if track_stage_changes and stage_field:
            # Use the stage field (which is watch_fields[0] when stage tracking is enabled)
            field_to_check = stage_field

            if field_to_check and field_to_check in changed_fields:
                old_value = previous_record.get(field_to_check)
                new_value = record.get(field_to_check)

                # Check from_stages filter
                if from_stages and old_value not in from_stages:
                    logger.info(f"Stage change from '{old_value}' not in allowed from_stages: {from_stages}")
                    return {
                        'success': False,
                        'skip': True,
                        'reason': 'Stage transition from stage not allowed',
                        'stage_transition': {
                            'from': old_value,
                            'to': new_value,
                            'allowed_from': from_stages
                        }
                    }

                # Check to_stages filter
                if to_stages and new_value not in to_stages:
                    logger.info(f"Stage change to '{new_value}' not in allowed to_stages: {to_stages}")
                    return {
                        'success': False,
                        'skip': True,
                        'reason': 'Stage transition to stage not allowed',
                        'stage_transition': {
                            'from': old_value,
                            'to': new_value,
                            'allowed_to': to_stages
                        }
                    }

                # Check stage direction if specified
                if stage_direction != 'any':
                    # This would require knowing the stage order - simplified check for now
                    # In a real implementation, you'd need to know the stage sequence
                    stage_transition = {
                        'field': field_to_check,
                        'from': old_value,
                        'to': new_value,
                        'direction': 'unknown'  # Would need stage order to determine
                    }

                    if track_stage_duration and 'updated_at' in trigger_data:
                        # Calculate duration in previous stage if timestamps are available
                        stage_transition['duration_hours'] = None  # Would need to calculate

                # Store stage transition info
                stage_transition = {
                    'field': field_to_check,
                    'from': old_value,
                    'to': new_value,
                    'timestamp': trigger_data.get('updated_at')
                }

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

        # Pass record data forward with identifiable data
        record_id = trigger_data.get('record_id')
        result = {
            'success': True,
            'entity_type': 'record',
            'entity_id': record_id,  # Primary identifier
            'record_id': record_id,  # Explicit record ID for easy access
            'pipeline_id': pipeline_id,
            'record': record,  # Current record data
            'previous_record': previous_record,  # Previous state
            'updated_by': updated_by,
            'updated_at': trigger_data.get('updated_at'),
            'changed_fields': changed_fields,
            'trigger_type': 'record_updated',
            'related_ids': {
                'record_id': record_id,
                'pipeline_id': pipeline_id,
                'user_id': updated_by
            }
        }

        # Add stage transition info if tracking
        if stage_transition:
            result['stage_transition'] = stage_transition
            result['is_stage_change'] = True

        return result

    def get_display_name(self) -> str:
        return "Record Updated Trigger"

    def get_description(self) -> str:
        return "Starts workflow when a record is updated"

    def get_category(self) -> str:
        return "Triggers"

    def get_icon(self) -> str:
        return "✏️"