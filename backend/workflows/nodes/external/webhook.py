"""
Webhook Node Processor - Send outgoing webhooks with payload data
"""
import logging
from typing import Dict, Any
from django.utils import timezone
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class WebhookOutProcessor(AsyncNodeProcessor):
    """Process outgoing webhook nodes"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["webhook_url"],
        "properties": {
            "webhook_url": {
                "type": "string",
                "format": "uri",
                "description": "Webhook endpoint URL",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "https://api.example.com/webhook"
                }
            },
            "payload": {
                "type": "object",
                "description": "Custom payload data",
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 8,
                    "placeholder": '{\n  "event": "workflow_completed",\n  "data": {\n    "contact_id": "{{contact.id}}",\n    "status": "{{status}}"\n  }\n}'
                }
            },
            "headers": {
                "type": "object",
                "description": "Additional HTTP headers",
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 3,
                    "placeholder": '{\n  "X-Webhook-Secret": "your-secret"\n}',
                    "section": "advanced"
                }
            },
            "include_context": {
                "type": "boolean",
                "default": True,
                "description": "Include workflow context in payload"
            },
            "include_execution_metadata": {
                "type": "boolean",
                "default": True,
                "description": "Include execution metadata"
            },
            "timeout": {
                "type": "integer",
                "minimum": 1,
                "maximum": 60,
                "default": 30,
                "description": "Request timeout in seconds",
                "ui_hints": {
                    "section": "advanced"
                }
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "webhook_out"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process outgoing webhook node"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})
        webhook_url = config.get('webhook_url', '')
        headers = config.get('headers', {})
        payload = config.get('payload', {})
        timeout = config.get('timeout', 30)
        include_context = config.get('include_context', True)
        include_execution_metadata = config.get('include_execution_metadata', True)
        
        if not webhook_url:
            raise ValueError("Webhook node requires webhook_url")
        
        # Build webhook payload
        webhook_payload = {}
        
        # Add execution metadata if requested
        if include_execution_metadata:
            execution = context.get('execution')
            if execution:
                webhook_payload.update({
                    'workflow_id': str(execution.workflow.id),
                    'workflow_name': execution.workflow.name,
                    'execution_id': str(execution.id),
                    'triggered_by': execution.triggered_by.email if execution.triggered_by else None,
                    'timestamp': timezone.now().isoformat()
                })
        
        # Add context data if requested
        if include_context:
            # Filter out internal context keys
            filtered_context = {
                k: v for k, v in context.items() 
                if not k.startswith('_') and k not in ['execution']
            }
            webhook_payload['context'] = filtered_context
        
        # Add custom payload data
        if payload:
            # Format payload with context variables
            formatted_payload = self._format_payload_with_context(payload, context)
            webhook_payload.update(formatted_payload)
        
        # Prepare HTTP request configuration
        http_config = {
            'type': 'HTTP_REQUEST',
            'data': {
                'method': 'POST',
                'url': webhook_url,
                'headers': {
                    'Content-Type': 'application/json',
                    'User-Agent': 'Oneo-CRM-Workflow/1.0',
                    **headers
                },
                'body': webhook_payload,
                'timeout': timeout,
                'retry': {
                    'max_retries': 3,
                    'delay': 1.0,
                    'exponential_backoff': True,
                    'retry_on_status': [500, 502, 503, 504]
                }
            }
        }
        
        # Use HTTP processor to send webhook
        from workflows.nodes.external.http import HTTPRequestProcessor
        http_processor = HTTPRequestProcessor()
        
        try:
            result = await http_processor.process(http_config, context)
            
            # Log webhook delivery
            await self._log_webhook_delivery(webhook_url, webhook_payload, result, context)
            
            return {
                'success': result.get('success', False),
                'webhook_url': webhook_url,
                'status_code': result.get('status_code', 0),
                'response_data': result.get('data'),
                'payload_size': len(str(webhook_payload)),
                'delivery_timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Webhook delivery failed: {e}")
            
            # Log failed delivery
            await self._log_webhook_delivery(webhook_url, webhook_payload, {'success': False, 'error': str(e)}, context)
            
            return {
                'success': False,
                'webhook_url': webhook_url,
                'error': str(e),
                'payload_size': len(str(webhook_payload)),
                'delivery_timestamp': timezone.now().isoformat()
            }
    
    def _format_payload_with_context(self, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload values with context variables"""
        
        formatted_payload = {}
        
        for key, value in payload.items():
            try:
                if isinstance(value, str):
                    formatted_payload[key] = value.format(**context)
                elif isinstance(value, dict):
                    formatted_payload[key] = self._format_payload_with_context(value, context)
                elif isinstance(value, list):
                    formatted_payload[key] = [
                        item.format(**context) if isinstance(item, str) else item
                        for item in value
                    ]
                else:
                    formatted_payload[key] = value
                    
            except KeyError as e:
                logger.warning(f"Context variable not found for payload key '{key}': {e}")
                formatted_payload[key] = value
            except Exception as e:
                logger.error(f"Error formatting payload key '{key}': {e}")
                formatted_payload[key] = value
        
        return formatted_payload
    
    async def _log_webhook_delivery(
        self, 
        webhook_url: str, 
        payload: Dict[str, Any], 
        result: Dict[str, Any], 
        context: Dict[str, Any]
    ):
        """Log webhook delivery for monitoring and debugging"""
        
        try:
            execution = context.get('execution')
            
            # Create webhook delivery log entry
            log_entry = {
                'webhook_url': webhook_url,
                'success': result.get('success', False),
                'status_code': result.get('status_code', 0),
                'payload_size': len(str(payload)),
                'response_size': len(str(result.get('data', ''))),
                'timestamp': timezone.now().isoformat(),
                'execution_id': str(execution.id) if execution else None,
                'error': result.get('error')
            }
            
            # Log at appropriate level
            if result.get('success'):
                logger.info(f"Webhook delivered successfully: {webhook_url} (status: {result.get('status_code')})")
            else:
                logger.warning(f"Webhook delivery failed: {webhook_url} - {result.get('error', 'Unknown error')}")
            
            # TODO: Store in webhook delivery log table for monitoring dashboard
            
        except Exception as e:
            logger.error(f"Failed to log webhook delivery: {e}")
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate webhook node inputs"""
        node_data = node_config.get('data', {})
        
        # Check required fields
        if not node_data.get('webhook_url'):
            return False
        
        # Validate URL format (basic check)
        webhook_url = node_data.get('webhook_url', '')
        if not webhook_url.startswith(('http://', 'https://')):
            return False
        
        # Validate timeout
        timeout = node_data.get('timeout', 30)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            return False
        
        # Validate payload structure
        payload = node_data.get('payload', {})
        if not isinstance(payload, dict):
            return False
        
        # Validate headers
        headers = node_data.get('headers', {})
        if not isinstance(headers, dict):
            return False
        
        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for webhook node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        node_data = node_config.get('data', {})
        
        # Calculate payload size for checkpoint
        payload = node_data.get('payload', {})
        payload_size = len(str(payload))
        
        checkpoint.update({
            'webhook_url': node_data.get('webhook_url', ''),
            'timeout': node_data.get('timeout', 30),
            'include_context': node_data.get('include_context', True),
            'include_execution_metadata': node_data.get('include_execution_metadata', True),
            'payload_size': payload_size,
            'custom_headers_count': len(node_data.get('headers', {}))
        })
        
        return checkpoint