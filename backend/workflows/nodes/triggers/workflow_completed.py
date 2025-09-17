"""
Workflow completed trigger processor
Triggers when another workflow completes (for workflow chaining)
"""
from typing import Any, Dict
from ..base import BaseNodeProcessor
import logging

logger = logging.getLogger(__name__)


class TriggerWorkflowCompletedProcessor(BaseNodeProcessor):
    """
    Processor for workflow completion triggers
    Enables workflow chaining and complex multi-stage processes
    """

    node_type = "trigger_workflow_completed"

    # Configuration schema for workflow completion triggers
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "source_workflow_ids": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "description": "Workflows to monitor for completion",
                "ui_hints": {
                    "widget": "workflow_multiselect",
                    "placeholder": "Select workflows to monitor"
                }
            },
            "completion_statuses": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["success", "failed", "cancelled", "timeout"]
                },
                "default": ["success"],
                "description": "Trigger on these completion statuses",
                "ui_hints": {
                    "widget": "multiselect",
                    "options": [
                        {"value": "success", "label": "Successfully completed"},
                        {"value": "failed", "label": "Failed with error"},
                        {"value": "cancelled", "label": "Cancelled by user"},
                        {"value": "timeout", "label": "Timed out"}
                    ]
                }
            },
            "success_only": {
                "type": "boolean",
                "default": False,
                "description": "Only trigger on successful completion (legacy option)",
                "ui_hints": {
                    "widget": "checkbox",
                    "deprecated": True
                }
            },
            "pass_execution_data": {
                "type": "boolean",
                "default": True,
                "description": "Include output data from source workflow",
                "ui_hints": {
                    "widget": "checkbox"
                }
            },
            "output_conditions": {
                "type": "object",
                "description": "Only trigger if output meets these conditions",
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 4,
                    "placeholder": '{\n  "result.success": True,\n  "result.count": {"$gte": 1}\n}',
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
                    "placeholder": "0 = immediate"
                }
            },
            "same_trigger_context": {
                "type": "boolean",
                "default": True,
                "description": "Inherit trigger context from source workflow",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            },
            "cascade_failures": {
                "type": "boolean",
                "default": False,
                "description": "If this workflow fails, mark source workflow as failed too",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            },
            "max_chain_depth": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "default": 3,
                "description": "Maximum workflow chain depth to prevent loops",
                "ui_hints": {
                    "widget": "number",
                    "section": "advanced"
                }
            },
            "filter_by_trigger": {
                "type": "object",
                "description": "Only trigger if source workflow was triggered by specific conditions",
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 3,
                    "placeholder": '{\n  "trigger_type": "manual",\n  "user_id": "specific_user"\n}',
                    "section": "advanced"
                }
            },
            "parallel_execution": {
                "type": "boolean",
                "default": False,
                "description": "Allow multiple instances to run simultaneously",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            },
            "execution_timeout_minutes": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1440,
                "default": 60,
                "description": "Timeout for this workflow execution (minutes)",
                "ui_hints": {
                    "widget": "number",
                    "section": "advanced",
                    "placeholder": "60 = 1 hour"
                }
            }
        },
        "required": ["source_workflow_ids"]
    }

    def get_required_fields(self) -> list:
        """Required fields for workflow completion triggers"""
        return [
            'source_workflow_id',  # The workflow to monitor for completion
        ]

    def get_optional_fields(self) -> list:
        """Optional fields"""
        return [
            'success_only',        # Only trigger on successful completion
            'failure_only',        # Only trigger on failed completion
            'pass_output',         # Pass the output from the source workflow
            'pass_context',        # Pass the context from the source workflow
        ]

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process workflow completion trigger
        """
        try:
            config = node_config.get('config', {})
            trigger_data = context.get('trigger_data', {})

            # Get source workflow information
            source_workflow_id = config.get('source_workflow_id')
            source_execution = trigger_data.get('source_execution', {})

            # Check completion status
            completion_status = source_execution.get('status', 'unknown')
            success_only = config.get('success_only', False)
            failure_only = config.get('failure_only', False)

            # Check if we should trigger based on status
            if success_only and completion_status != 'success':
                return {
                    'success': False,
                    'trigger_type': 'workflow_completed',
                    'reason': f'Source workflow did not complete successfully: {completion_status}'
                }

            if failure_only and completion_status != 'failed':
                return {
                    'success': False,
                    'trigger_type': 'workflow_completed',
                    'reason': f'Source workflow did not fail: {completion_status}'
                }

            # Build output
            output = {
                'success': True,
                'trigger_type': 'workflow_completed',
                'source_workflow_id': source_workflow_id,
                'source_execution_id': source_execution.get('id'),
                'source_status': completion_status,
                'source_duration': source_execution.get('duration_ms'),
                'source_completed_at': source_execution.get('completed_at'),
            }

            # Optionally pass output and context
            if config.get('pass_output'):
                output['source_output'] = source_execution.get('output', {})

            if config.get('pass_context'):
                output['source_context'] = source_execution.get('context', {})
                # Merge source context into current context
                context.update(source_execution.get('context', {}))

            logger.info(f"Workflow completion trigger: source workflow {source_workflow_id} completed with status {completion_status}")

            # Store in context
            context['workflow_chain'] = {
                'source_workflow_id': source_workflow_id,
                'source_execution_id': source_execution.get('id'),
                'source_status': completion_status
            }

            return output

        except Exception as e:
            logger.error(f"Workflow completion trigger error: {e}")
            return {
                'success': False,
                'error': str(e),
                'trigger_type': 'workflow_completed'
            }