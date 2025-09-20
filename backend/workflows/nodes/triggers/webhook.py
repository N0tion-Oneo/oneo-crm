"""
Webhook trigger node processor
"""
import logging
from typing import Dict, Any
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class TriggerWebhookProcessor(AsyncNodeProcessor):
    """
    Processes webhook trigger events
    This node starts a workflow when a webhook is received
    """

    node_type = "trigger_webhook"

    # Configuration schema for webhook triggers
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "webhook_path": {
                "type": "string",
                "description": "Webhook URL path",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "customer-signup",
                    "help_text": "Choose a unique name for your webhook URL (e.g., 'order-updates')"
                }
            },
            "http_methods": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"]
                },
                "default": ["POST"],
                "description": "Accepted HTTP methods",
                "ui_hints": {
                    "widget": "multiselect"
                }
            },
            "webhook_secret": {
                "type": "string",
                "description": "Security key (optional)",
                "ui_hints": {
                    "widget": "password",
                    "placeholder": "Enter secret key",
                    "help_text": "A secret key to verify that webhooks are coming from the expected source"
                }
            },
            "require_authentication": {
                "type": "boolean",
                "default": True,
                "description": "Require authentication for webhook",
                "ui_hints": {
                    "widget": "checkbox"
                }
            },
            "signature_header": {
                "type": "string",
                "default": "X-Webhook-Signature",
                "description": "Header containing webhook signature",
                "ui_hints": {
                    "widget": "text",
                    "section": "advanced",
                    "show_when": {"webhook_secret": {"$exists": True}}
                }
            },
            "allowed_ips": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Whitelist of allowed IP addresses",
                "ui_hints": {
                    "widget": "tag_input",
                    "placeholder": "Enter IP addresses",
                    "section": "security"
                }
            },
            "headers_to_capture": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific headers to capture from request",
                "ui_hints": {
                    "widget": "tag_input",
                    "placeholder": "X-Custom-Header",
                    "section": "advanced"
                }
            },
            "payload_validation": {
                "type": "object",
                "description": "Expected data format",
                "ui_hints": {
                    "widget": "json_builder",
                    "rows": 8,
                    "section": "advanced",
                    "help_text": "Define what data structure you expect to receive"
                }
            },
            "response_template": {
                "type": "object",
                "description": "Response to send back",
                "ui_hints": {
                    "widget": "json_builder",
                    "rows": 4,
                    "section": "advanced",
                    "help_text": "What should we send back to confirm receipt?"
                }
            },
            "response_status_code": {
                "type": "integer",
                "minimum": 100,
                "maximum": 599,
                "default": 200,
                "description": "HTTP status code to return",
                "ui_hints": {
                    "widget": "number",
                    "section": "advanced"
                }
            },
            "rate_limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1000,
                "description": "Max requests per minute",
                "ui_hints": {
                    "widget": "number",
                    "section": "security",
                    "help_text": "Prevent webhook flooding"
                }
            },
            "timeout_seconds": {
                "type": "integer",
                "minimum": 1,
                "maximum": 300,
                "default": 30,
                "description": "Processing timeout in seconds",
                "ui_hints": {
                    "widget": "number",
                    "section": "advanced"
                }
            },
            "retry_on_failure": {
                "type": "boolean",
                "default": False,
                "description": "Request retry if workflow fails",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            },
            "log_payloads": {
                "type": "boolean",
                "default": True,
                "description": "Log webhook payloads for debugging",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            }
        },
        "required": ["webhook_path"]
    }

    async def process(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook trigger

        The webhook data from the request is passed in context['trigger_data']
        """
        trigger_data = context.get('trigger_data', {})

        # Extract webhook data
        webhook_path = config.get('path') or trigger_data.get('path')
        headers = trigger_data.get('headers', {})
        body = trigger_data.get('body', {})
        query_params = trigger_data.get('query_params', {})
        method = trigger_data.get('method', 'POST')

        logger.info(f"Webhook trigger activated for path: {webhook_path}")

        # Pass webhook data forward
        return {
            'success': True,
            'webhook_path': webhook_path,
            'method': method,
            'headers': headers,
            'body': body,
            'query_params': query_params,
            'received_at': trigger_data.get('received_at'),
            'trigger_type': 'webhook'
        }

    def get_display_name(self) -> str:
        return "Webhook Trigger"

    def get_description(self) -> str:
        return "Starts workflow when a webhook is received"

    def get_category(self) -> str:
        return "Triggers"

    def get_icon(self) -> str:
        return "🔗"