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
    """Process AI prompt nodes using existing AIFieldProcessor"""
    
    def __init__(self):
        super().__init__()
        self.node_type = "AI_PROMPT"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process AI prompt node"""
        
        # Get configuration
        node_data = node_config.get('data', {})
        prompt_template = node_data.get('prompt', '')
        ai_config = node_data.get('ai_config', {})
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
                    'ai_model': ai_config.get('model', 'gpt-4'),
                    'temperature': ai_config.get('temperature', 0.7),
                    'max_tokens': ai_config.get('max_tokens', 1000),
                    'enable_tools': ai_config.get('enable_tools', False),
                    'allowed_tools': ai_config.get('allowed_tools', [])
                },
                tenant=tenant,
                user=execution.triggered_by if execution else None
            )
            
            return {
                'output': result.get('content', ''),
                'success': True,
                'ai_metadata': {
                    'tokens_used': result.get('tokens_used', 0),
                    'model': result.get('model', ''),
                    'processing_time_ms': result.get('processing_time_ms', 0),
                    'cost_cents': result.get('cost_cents', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"AI prompt processing failed: {e}")
            raise ValueError(f"AI processing failed: {str(e)}")
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate AI prompt node inputs"""
        node_data = node_config.get('data', {})
        
        # Check required fields
        if not node_data.get('prompt'):
            return False
        
        # Validate AI config
        ai_config = node_data.get('ai_config', {})
        model = ai_config.get('model', 'gpt-4')
        
        # Check if model is supported
        supported_models = ['gpt-4', 'gpt-3.5-turbo', 'claude-3', 'claude-3-haiku']
        if model not in supported_models:
            return False
        
        # Check temperature range
        temperature = ai_config.get('temperature', 0.7)
        if not (0.0 <= temperature <= 2.0):
            return False
        
        # Check max_tokens
        max_tokens = ai_config.get('max_tokens', 1000)
        if not isinstance(max_tokens, int) or max_tokens <= 0:
            return False
        
        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for AI prompt node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        # Add AI-specific checkpoint data
        node_data = node_config.get('data', {})
        checkpoint.update({
            'prompt_template': node_data.get('prompt', ''),
            'ai_config': node_data.get('ai_config', {}),
            'input_context': await self.prepare_inputs(node_config, context)
        })
        
        return checkpoint