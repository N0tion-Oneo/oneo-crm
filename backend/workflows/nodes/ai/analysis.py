"""
AI Analysis Node for Workflow Integration
"""
import logging
from typing import Dict, Any, List
from workflows.nodes.base import BaseNode
from ai.analysis import AIAnalysisProcessor

logger = logging.getLogger(__name__)


class AIAnalysisNode(BaseNode):
    """AI Analysis workflow node supporting 7 analysis types"""
    
    node_type = 'ai_analysis'
    display_name = 'AI Analysis'
    description = 'Perform AI analysis with structured outputs'
    
    config_schema = {
        'analysis_type': {
            'type': 'select',
            'label': 'Analysis Type',
            'options': [
                {'value': 'sentiment', 'label': 'Sentiment Analysis'},
                {'value': 'summary', 'label': 'Content Summary'},
                {'value': 'classification', 'label': 'Content Classification'},
                {'value': 'extraction', 'label': 'Entity Extraction'},
                {'value': 'lead_qualification', 'label': 'Lead Qualification'},
                {'value': 'contact_profiling', 'label': 'Contact Profiling'},
                {'value': 'channel_optimization', 'label': 'Channel Optimization'}
            ],
            'required': True
        },
        'input_field': {
            'type': 'field_reference',
            'label': 'Input Field',
            'required': True
        },
        'output_field': {
            'type': 'field_reference',
            'label': 'Output Field',
            'required': True
        }
    }
    
    input_ports = ['trigger']
    output_ports = ['success', 'error']
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute AI analysis"""
        try:
            analysis_type = self.config.get('analysis_type')
            input_field = self.config.get('input_field')
            output_field = self.config.get('output_field')
            
            # Get input content
            content = context.get('record', {}).get('data', {}).get(input_field)
            if not content:
                raise ValueError(f"No content found in field: {input_field}")
            
            # Initialize processor
            from django.connection import connection
            tenant = connection.tenant
            user = context.get('user')
            
            processor = AIAnalysisProcessor(tenant, user)
            
            # Perform analysis
            result = await processor.analyze(analysis_type, {'content': content})
            
            # Store result
            if 'record' not in context:
                context['record'] = {'data': {}}
            if 'data' not in context['record']:
                context['record']['data'] = {}
            
            context['record']['data'][output_field] = result
            
            return {
                'status': 'success',
                'output_port': 'success',
                'context': context,
                'analysis_result': result
            }
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {
                'status': 'error',
                'output_port': 'error',
                'context': context,
                'error': str(e)
            }


class AIPromptNode(BaseNode):
    """AI Prompt workflow node for custom prompts"""
    
    node_type = 'ai_prompt'
    display_name = 'AI Prompt'
    description = 'Execute custom AI prompts'
    
    config_schema = {
        'prompt_template': {
            'type': 'textarea',
            'label': 'Prompt Template',
            'required': True
        },
        'output_field': {
            'type': 'field_reference',
            'label': 'Output Field',
            'required': True
        },
        'model': {
            'type': 'select',
            'label': 'AI Model',
            'options': [
                {'value': 'gpt-4o-mini', 'label': 'GPT-4o Mini'},
                {'value': 'gpt-4o', 'label': 'GPT-4o'},
            ],
            'default': 'gpt-4o-mini'
        }
    }
    
    input_ports = ['trigger']
    output_ports = ['success', 'error']
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute custom AI prompt"""
        try:
            prompt_template = self.config.get('prompt_template')
            output_field = self.config.get('output_field')
            
            # Build context and format prompt
            record_data = context.get('record', {}).get('data', {})
            formatted_prompt = prompt_template.format(**record_data)
            
            # Process with AI (simplified)
            result = f"AI processed: {formatted_prompt[:100]}..."
            
            # Store result
            if 'record' not in context:
                context['record'] = {'data': {}}
            if 'data' not in context['record']:
                context['record']['data'] = {}
            
            context['record']['data'][output_field] = result
            
            return {
                'status': 'success',
                'output_port': 'success',
                'context': context
            }
            
        except Exception as e:
            logger.error(f"AI prompt failed: {e}")
            return {
                'status': 'error',
                'output_port': 'error',
                'context': context,
                'error': str(e)
            }