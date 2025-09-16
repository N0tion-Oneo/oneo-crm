"""
Webhook trigger node processor
"""
import logging
from typing import Dict, Any
from workflows.nodes.base import BaseNodeProcessor

logger = logging.getLogger(__name__)


class TriggerWebhookProcessor(BaseNodeProcessor):
    """
    Processes webhook trigger events
    This node starts a workflow when a webhook is received
    """

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