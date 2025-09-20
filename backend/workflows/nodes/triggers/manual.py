"""
Manual trigger processor for workflows
Allows workflows to be triggered manually by users
"""
from typing import Any, Dict
from ..base import AsyncNodeProcessor
import logging

logger = logging.getLogger(__name__)


class TriggerManualProcessor(AsyncNodeProcessor):
    """
    Processor for manual workflow triggers
    Used when a user manually initiates a workflow
    """

    node_type = "trigger_manual"

    # Configuration schema for manual triggers
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "require_confirmation": {
                "type": "boolean",
                "default": False,
                "description": "Require user confirmation before executing",
                "ui_hints": {
                    "widget": "checkbox"
                }
            },
            "confirmation_message": {
                "type": "string",
                "description": "Message to show when confirmation is required",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 3,
                    "placeholder": "Are you sure you want to execute this workflow?",
                    "show_when": {"require_confirmation": True}
                }
            },
            "button_text": {
                "type": "string",
                "default": "Execute Workflow",
                "description": "Text for the trigger button",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "Execute Workflow"
                }
            },
            "allowed_user_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "User types allowed to trigger this workflow",
                "ui_hints": {
                    "widget": "user_type_multiselect",
                    "placeholder": "Select user types (leave empty for all)"
                }
            },
            "metadata_fields": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"},
                        "label": {"type": "string"},
                        "type": {"type": "string", "enum": ["text", "number", "select", "textarea"]},
                        "required": {"type": "boolean", "default": False}
                    }
                },
                "description": "Additional fields to collect when triggering",
                "ui_hints": {
                    "widget": "field_builder",
                    "section": "advanced"
                }
            }
        }
    }

    def get_required_fields(self) -> list:
        """No required fields for manual triggers"""
        return []

    def get_optional_fields(self) -> list:
        """Optional fields for manual triggers"""
        return [
            'user_input',  # Optional user input data
            'reason',      # Reason for manual trigger
            'metadata',    # Additional metadata
        ]

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process manual trigger
        """
        try:
            # Extract trigger data from context
            trigger_data = context.get('trigger_data', {})
            triggered_by = context.get('triggered_by')

            # Build output
            output = {
                'success': True,
                'trigger_type': 'manual',
                'triggered_by': str(triggered_by.id) if triggered_by else None,
                'triggered_by_email': triggered_by.email if triggered_by else None,
                'user_input': trigger_data.get('user_input', {}),
                'reason': trigger_data.get('reason', 'Manual trigger'),
                'metadata': trigger_data.get('metadata', {}),
                'trigger_time': context.get('trigger_time'),
            }

            logger.info(f"Manual trigger activated by {triggered_by.email if triggered_by else 'unknown'}")

            # Store in context for downstream nodes
            context['manual_trigger'] = output

            return output

        except Exception as e:
            logger.error(f"Manual trigger error: {e}")
            return {
                'success': False,
                'error': str(e),
                'trigger_type': 'manual'
            }