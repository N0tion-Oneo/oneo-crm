"""
AI Prompt Node Processor - Execute AI prompts with context
"""
import logging
from typing import Dict, Any
from django.db import connection
from workflows.nodes.base import AsyncNodeProcessor
from workflows.ai_integration import workflow_ai_processor

logger = logging.getLogger(__name__)


class AIPromptProcessor(AsyncNodeProcessor):
    """Process AI prompt nodes using ai.integrations.AIIntegrationManager"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {
                "type": "string",
                "minLength": 1,
                "description": "AI prompt template with context variables",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 8,
                    "placeholder": "Generate a summary for {{record.name}}:\n\nDetails: {{record.description}}\n\nFocus on key insights."
                }
            },
            "model": {
                "type": "string",
                "enum": ["gpt-4", "gpt-3.5-turbo", "claude-3", "claude-3-haiku"],
                "default": "gpt-4",
                "description": "AI model to use for processing",
                "ui_hints": {
                    "widget": "select"
                }
            },
            "temperature": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 2.0,
                "default": 0.7,
                "description": "Creativity level (0=deterministic, 2=very creative)",
                "ui_hints": {
                    "widget": "slider",
                    "step": 0.1
                }
            },
            "max_tokens": {
                "type": "integer",
                "minimum": 1,
                "maximum": 4000,
                "default": 1000,
                "description": "Maximum response length in tokens"
            },
            "system_prompt": {
                "type": "string",
                "description": "Optional system prompt to set AI behavior",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 4,
                    "placeholder": "You are a helpful assistant that provides concise and accurate information."
                }
            },
            "enable_tools": {
                "type": "boolean",
                "default": False,
                "description": "Enable AI tools (web search, code interpreter, etc.)"
            },
            "allowed_tools": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["web_search", "code_interpreter", "dalle", "retrieval"]
                },
                "description": "Which AI tools to allow when enable_tools is true",
                "ui_hints": {
                    "widget": "multiselect",
                    "show_when": {"enable_tools": True}
                }
            },
            "response_format": {
                "type": "string",
                "enum": ["text", "json", "markdown"],
                "default": "text",
                "description": "Expected response format",
                "ui_hints": {
                    "widget": "radio"
                }
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "ai_prompt"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process AI prompt node"""

        # Get configuration
        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Extract configuration values
        prompt_template = config.get('prompt', '')
        model = config.get('model', 'gpt-4')
        temperature = config.get('temperature', 0.7)
        max_tokens = config.get('max_tokens', 1000)
        system_prompt = config.get('system_prompt', '')
        enable_tools = config.get('enable_tools', False)
        allowed_tools = config.get('allowed_tools', [])
        response_format = config.get('response_format', 'text')
        input_mapping = node_data.get('input_mapping', {})
        
        # Prepare inputs if mapping specified
        prepared_inputs = await self.prepare_inputs(node_config, context)
        
        # Merge prepared inputs with context for prompt formatting
        format_context = {**context, **prepared_inputs}
        
        # Format prompt with context data
        try:
            formatted_prompt = prompt_template.format(**format_context)
        except KeyError as e:
            raise ValueError(f"Missing template variable in prompt: {e}")
        
        # Get tenant from execution context
        execution = context.get('execution')
        tenant = connection.tenant
        
        if not tenant.can_use_ai_features():
            raise ValueError("AI features not available for this tenant")
        
        # Create record data for AI processing
        temp_record_data = {
            'workflow_context': context,
            'prompt_input': formatted_prompt,
            **prepared_inputs
        }
        
        # Process with AI
        try:
            result = await workflow_ai_processor.process_ai_field_async(
                record_data=temp_record_data,
                field_config={
                    'ai_prompt': formatted_prompt,
                    'ai_model': model,
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                    'enable_tools': enable_tools,
                    'allowed_tools': allowed_tools,
                    'system_prompt': system_prompt,
                    'response_format': response_format
                },
                tenant=tenant,
                user=execution.triggered_by if execution else None
            )
            
            # Get source record ID if processing record data
            source_record_id = None
            if 'record' in context or 'record_id' in context:
                source_record_id = context.get('record_id') or (context.get('record', {}).get('id'))
            elif 'trigger_data' in context:
                source_record_id = context.get('trigger_data', {}).get('record_id')

            prompt_id = f"prompt_{context.get('execution_id', 'test')}_{context.get('node_id', 'unknown')}"

            return {
                'success': True,
                'entity_type': 'ai_response',
                'entity_id': prompt_id,  # Primary identifier
                'output': result.get('content', ''),
                'prompt_id': prompt_id,  # For tracking
                'source_record_id': source_record_id,  # Reference to source data
                'ai_metadata': {
                    'tokens_used': result.get('tokens_used', 0),
                    'model': result.get('model', ''),
                    'processing_time_ms': result.get('processing_time_ms', 0),
                    'cost_cents': result.get('cost_cents', 0)
                },
                'related_ids': {
                    'prompt_id': prompt_id,
                    'source_record_id': source_record_id,
                    'execution_id': context.get('execution_id')
                }
            }
            
        except Exception as e:
            logger.error(f"AI prompt processing failed: {e}")
            raise ValueError(f"AI processing failed: {str(e)}")
    
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for AI prompt node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        # Add AI-specific checkpoint data
        node_data = node_config.get('data', {})
        config = node_data.get('config', {})
        checkpoint.update({
            'prompt_template': config.get('prompt', ''),
            'ai_config': {
                'model': config.get('model', 'gpt-4'),
                'temperature': config.get('temperature', 0.7),
                'max_tokens': config.get('max_tokens', 1000)
            },
            'input_context': await self.prepare_inputs(node_config, context)
        })
        
        return checkpoint