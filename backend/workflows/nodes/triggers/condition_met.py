"""
Condition met trigger processor
Triggers when complex conditions are satisfied
"""
from typing import Any, Dict
from ..base import BaseNodeProcessor
import logging
import operator

logger = logging.getLogger(__name__)


class TriggerConditionMetProcessor(BaseNodeProcessor):
    """
    Processor for condition-based triggers
    Monitors and triggers when complex conditions are met
    """

    node_type = "trigger_condition_met"

    # Configuration schema for condition met triggers
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "pipeline_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Which pipelines to monitor?",
                "ui_hints": {
                    "widget": "pipeline_multiselect",
                    "placeholder": "Select pipelines to monitor",
                    "help_text": "Leave empty to monitor all pipelines"
                }
            },
            "conditions": {
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
                            "enum": [
                                "equals", "not_equals",
                                "greater_than", "greater_than_or_equal",
                                "less_than", "less_than_or_equal",
                                "contains", "not_contains",
                                "starts_with", "ends_with",
                                "is_empty", "is_not_empty",
                                "changed_to", "changed_from"
                            ],
                            "description": "How to compare"
                        },
                        "value": {
                            "description": "Value to compare"
                        }
                    }
                },
                "description": "What conditions should trigger this workflow?",
                "ui_hints": {
                    "widget": "condition_builder",
                    "help_text": "Define the conditions that will start your workflow"
                }
            },
            "condition_logic": {
                "type": "string",
                "enum": ["AND", "OR", "CUSTOM"],
                "default": "AND",
                "description": "How to combine multiple conditions",
                "ui_hints": {
                    "widget": "select",
                    "show_when": {"condition_expression": ""},
                    "options": [
                        {"value": "AND", "label": "All conditions must be true"},
                        {"value": "OR", "label": "At least one condition must be true"},
                        {"value": "CUSTOM", "label": "Use custom expression"}
                    ]
                }
            },
            "custom_logic_expression": {
                "type": "string",
                "description": "Custom logic expression using condition indexes (e.g., '(1 AND 2) OR 3')",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "(1 AND 2) OR (3 AND 4)",
                    "show_when": {"condition_logic": "CUSTOM"}
                }
            },
            "evaluation_frequency": {
                "type": "string",
                "enum": ["real_time", "hourly", "daily", "on_record_change"],
                "default": "real_time",
                "description": "How often to check conditions",
                "ui_hints": {
                    "widget": "select",
                    "options": [
                        {"value": "real_time", "label": "Real-time (immediate)"},
                        {"value": "on_record_change", "label": "When records change"},
                        {"value": "hourly", "label": "Every hour"},
                        {"value": "daily", "label": "Daily at midnight"}
                    ]
                }
            },
            "check_interval": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1440,
                "description": "Check interval in minutes (for scheduled evaluation)",
                "ui_hints": {
                    "widget": "number",
                    "placeholder": "60 = hourly",
                    "show_when": {"evaluation_frequency": "hourly"}
                }
            },
            "data_source": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["pipeline", "external_api", "database_query"],
                        "default": "pipeline"
                    },
                    "pipeline_id": {"type": "string"},
                    "api_endpoint": {"type": "string"},
                    "query": {"type": "string"}
                },
                "description": "Source of data for condition evaluation",
                "ui_hints": {
                    "widget": "data_source_builder",
                    "section": "advanced"
                }
            },
            "reset_on_trigger": {
                "type": "boolean",
                "default": True,
                "description": "Reset condition state after triggering",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            },
            "persistent_state": {
                "type": "boolean",
                "default": False,
                "description": "Maintain condition state across system restarts",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            },
            "cooldown_minutes": {
                "type": "integer",
                "minimum": 0,
                "maximum": 10080,
                "default": 0,
                "description": "Minimum time between triggers (minutes)",
                "ui_hints": {
                    "widget": "number",
                    "placeholder": "0 = no cooldown",
                    "section": "advanced"
                }
            },
            "max_triggers_per_day": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1000,
                "description": "Maximum triggers per day (prevents spam)",
                "ui_hints": {
                    "widget": "number",
                    "placeholder": "Leave empty for unlimited",
                    "section": "advanced"
                }
            },
            "condition_timeout_seconds": {
                "type": "integer",
                "minimum": 1,
                "maximum": 300,
                "default": 30,
                "description": "Timeout for condition evaluation (seconds)",
                "ui_hints": {
                    "widget": "number",
                    "section": "advanced"
                }
            }
        },
        "oneOf": [
            {"required": ["condition_expression"]},
            {"required": ["conditions"]}
        ]
    }

    def get_required_fields(self) -> list:
        """Required fields for condition triggers"""
        return [
            'conditions',  # List of conditions to evaluate
        ]

    def get_optional_fields(self) -> list:
        """Optional fields"""
        return [
            'condition_operator',  # 'AND' or 'OR' for multiple conditions
            'record_type',        # Type of record to monitor
            'check_interval',     # How often to check (in minutes)
            'max_checks',         # Maximum number of checks before giving up
        ]

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process condition met trigger
        """
        try:
            config = node_config.get('config', {})
            trigger_data = context.get('trigger_data', {})
            record = trigger_data.get('record', {})

            conditions = config.get('conditions', [])
            condition_operator = config.get('condition_operator', 'AND')
            group_operators = config.get('group_operators', {})

            if not conditions:
                raise ValueError("No conditions specified")

            # Use the GroupedConditionEvaluator for consistent evaluation
            from workflows.utils.condition_evaluator import condition_evaluator

            # Evaluate conditions against the record
            all_met, details = condition_evaluator.evaluate(
                conditions=conditions,
                data=record,
                logic_operator=condition_operator,
                group_operators=group_operators
            )

            if not all_met:
                return {
                    'success': False,
                    'trigger_type': 'condition_met',
                    'reason': 'Conditions not met',
                    'evaluation_details': details
                }

            # Build output
            output = {
                'success': True,
                'trigger_type': 'condition_met',
                'evaluation_details': details,
                'record': record,
                'record_id': trigger_data.get('record_id'),
                'record_type': config.get('record_type')
            }

            logger.info(f"Condition trigger activated: conditions met with details {details}")

            # Store in context
            context['condition_trigger'] = output

            return output

        except Exception as e:
            logger.error(f"Condition trigger error: {e}")
            return {
                'success': False,
                'error': str(e),
                'trigger_type': 'condition_met'
            }

    def _evaluate_condition(self, condition: Dict, record: Dict, trigger_data: Dict) -> bool:
        """
        Evaluate a single condition
        """
        try:
            field = condition.get('field')
            op = condition.get('operator')
            expected_value = condition.get('value')

            # Get the actual value from the record
            actual_value = record.get(field)

            # If field not in record, check trigger_data
            if actual_value is None and field in trigger_data:
                actual_value = trigger_data[field]

            # Operator mapping
            operators = {
                'equals': operator.eq,
                'not_equals': operator.ne,
                'greater_than': operator.gt,
                'greater_than_or_equal': operator.ge,
                'less_than': operator.lt,
                'less_than_or_equal': operator.le,
                'contains': lambda a, b: b in str(a) if a is not None else False,
                'not_contains': lambda a, b: b not in str(a) if a is not None else True,
                'is_null': lambda a, b: a is None,
                'is_not_null': lambda a, b: a is not None,
            }

            if op not in operators:
                logger.warning(f"Unknown operator: {op}")
                return False

            # Special handling for null checks
            if op in ['is_null', 'is_not_null']:
                return operators[op](actual_value, None)

            # Convert to appropriate types for comparison
            if isinstance(expected_value, str) and expected_value.isdigit():
                try:
                    expected_value = float(expected_value)
                    if actual_value is not None:
                        actual_value = float(actual_value)
                except:
                    pass

            return operators[op](actual_value, expected_value)

        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False