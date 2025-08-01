"""
AI integration utilities for workflows
Extends the existing AI processor to work with workflow nodes
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from django.contrib.auth import get_user_model
from pipelines.ai_processor import AIFieldProcessor
from tenants.models import Tenant

User = get_user_model()
logger = logging.getLogger(__name__)


class WorkflowAIProcessor:
    """Extended AI processor for workflow nodes"""
    
    def __init__(self):
        pass
    
    async def process_ai_request(
        self,
        prompt: str,
        ai_config: Dict[str, Any],
        tenant: Tenant,
        user: User,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process AI request for workflow nodes
        Integrates with existing Phase 3 AI infrastructure
        """
        
        if not tenant.can_use_ai_features():
            raise ValueError("AI features not available for this tenant")
        
        # Create a mock field and record for the existing AI processor
        mock_field = type('MockField', (), {
            'name': 'workflow_ai_node',
            'ai_config': {
                'ai_prompt': prompt,
                'ai_model': ai_config.get('model', 'gpt-4'),
                'temperature': ai_config.get('temperature', 0.7),
                'max_tokens': ai_config.get('max_tokens', 1000),
                'enable_tools': ai_config.get('enable_tools', False),
                'allowed_tools': ai_config.get('allowed_tools', []),
                'timeout': ai_config.get('timeout', 120),
                'include_all_fields': False,  # Workflow context is different
                'auto_update': False,
                'cache_duration': ai_config.get('cache_duration', 3600)
            }
        })()
        
        # Create mock record with workflow context
        mock_record = type('MockRecord', (), {
            'id': 'workflow_context',
            'data': context or {},
            'pipeline': type('MockPipeline', (), {
                'tenant_id': tenant.id if hasattr(tenant, 'id') else None
            })()
        })()
        
        try:
            # Use existing AI field processor
            processor = AIFieldProcessor(mock_field, mock_record)
            
            # Process the AI request
            result = await processor.process_field_async()
            
            # Track AI usage for the tenant
            if 'tokens_used' in result and 'cost_cents' in result:
                tenant.record_ai_usage(result['cost_cents'] / 100.0)  # Convert cents to dollars
            
            return {
                'content': result.get('content', ''),
                'tokens_used': result.get('tokens_used', 0),
                'model': result.get('model', ai_config.get('model', 'gpt-4')),
                'processing_time_ms': result.get('processing_time_ms', 0),
                'cost_cents': result.get('cost_cents', 0),
                'tool_outputs': result.get('tool_outputs', []) if ai_config.get('enable_tools') else []
            }
            
        except Exception as e:
            logger.error(f"Workflow AI processing failed: {e}")
            
            # Return error response
            return {
                'content': f"AI processing failed: {str(e)}",
                'tokens_used': 0,
                'model': ai_config.get('model', 'gpt-4'),
                'processing_time_ms': 0,
                'cost_cents': 0,
                'error': True,
                'error_message': str(e)
            }
    
    async def process_ai_field_async(
        self,
        record_data: Dict[str, Any],
        field_config: Dict[str, Any],
        tenant: Tenant,
        user: User
    ) -> Dict[str, Any]:
        """
        Simplified AI field processing for workflow compatibility
        """
        prompt = field_config.get('ai_prompt', '')
        
        # Format prompt with record data
        try:
            formatted_prompt = prompt.format(**record_data)
        except KeyError as e:
            logger.warning(f"Prompt formatting failed, missing key: {e}")
            formatted_prompt = prompt
        
        return await self.process_ai_request(
            prompt=formatted_prompt,
            ai_config=field_config,
            tenant=tenant,
            user=user,
            context=record_data
        )
    
    def get_available_ai_models(self, tenant: Tenant) -> List[str]:
        """Get available AI models for the tenant"""
        if not tenant.can_use_ai_features():
            return []
        
        # Get model preferences from tenant AI config
        preferences = tenant.get_ai_model_preferences()
        
        # Return available models based on tenant configuration
        available_models = [
            'gpt-4',
            'gpt-4-turbo',
            'gpt-3.5-turbo'
        ]
        
        # Filter based on tenant preferences or permissions
        return available_models
    
    def estimate_ai_cost(
        self,
        prompt: str,
        model: str = 'gpt-4',
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Estimate AI processing cost
        """
        # Rough token estimation (more accurate would use tiktoken)
        estimated_input_tokens = len(prompt.split()) * 1.3  # Rough estimation
        estimated_output_tokens = max_tokens
        
        # Cost per token (approximate, should be updated with current pricing)
        costs = {
            'gpt-4': {'input': 0.03 / 1000, 'output': 0.06 / 1000},
            'gpt-4-turbo': {'input': 0.01 / 1000, 'output': 0.03 / 1000},
            'gpt-3.5-turbo': {'input': 0.001 / 1000, 'output': 0.002 / 1000}
        }
        
        model_costs = costs.get(model, costs['gpt-4'])  # Default to GPT-4
        
        estimated_cost = (
            estimated_input_tokens * model_costs['input'] +
            estimated_output_tokens * model_costs['output']
        )
        
        return {
            'estimated_input_tokens': int(estimated_input_tokens),
            'estimated_output_tokens': estimated_output_tokens,
            'estimated_total_tokens': int(estimated_input_tokens + estimated_output_tokens),
            'estimated_cost_usd': round(estimated_cost, 4),
            'estimated_cost_cents': int(estimated_cost * 100),
            'model': model
        }


# Global instance for workflow AI processing
workflow_ai_processor = WorkflowAIProcessor()