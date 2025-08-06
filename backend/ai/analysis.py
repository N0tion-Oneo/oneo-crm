"""
AI Analysis Processor with 7 analysis types
Implements structured JSON outputs for sentiment, summary, classification, extraction, 
lead_qualification, contact_profiling, channel_optimization
"""
import json
import logging
from typing import Dict, Any, List
from django.utils import timezone

logger = logging.getLogger(__name__)


class AIAnalysisProcessor:
    """
    7 analysis types: sentiment, summary, classification, extraction, 
    lead_qualification, contact_profiling, channel_optimization
    Implements structured JSON outputs as described in frontend plan lines 464-465
    """
    
    ANALYSIS_TYPES = {
        'sentiment': {
            'prompt_template': '''
            Analyze the sentiment of the following content and provide a structured response:
            
            Content: {content}
            
            Respond with a JSON object containing:
            - sentiment: one of "positive", "negative", "neutral"
            - confidence: a number between 0 and 1
            - reasoning: brief explanation of the sentiment analysis
            ''',
            'output_schema': {
                'sentiment': 'string',  # positive, negative, neutral
                'confidence': 'number',  # 0-1
                'reasoning': 'string'
            }
        },
        'summary': {
            'prompt_template': '''
            Summarize the following content in {max_words} words or less:
            
            Content: {content}
            
            Respond with a JSON object containing:
            - summary: the main summary text
            - key_points: array of the most important points
            - word_count: actual number of words in the summary
            ''',
            'output_schema': {
                'summary': 'string',
                'key_points': 'array',
                'word_count': 'number'
            }
        },
        'classification': {
            'prompt_template': '''
            Classify the following content into one of these categories: {categories}
            
            Content: {content}
            
            Respond with a JSON object containing:
            - primary_category: the most likely category
            - confidence: confidence score for the primary category (0-1)
            - all_categories: array of all categories with confidence scores
            ''',
            'output_schema': {
                'primary_category': 'string',
                'confidence': 'number',
                'all_categories': 'array'
            }
        },
        'extraction': {
            'prompt_template': '''
            Extract the following entity types from the content: {entity_types}
            
            Content: {content}
            
            Respond with a JSON object containing:
            - entities: array of extracted entities with their types and values
            - confidence_scores: object with confidence scores for each entity type
            ''',
            'output_schema': {
                'entities': 'array',
                'confidence_scores': 'object'
            }
        },
        'lead_qualification': {
            'prompt_template': '''
            Qualify this lead based on the following criteria: {criteria}
            
            Lead Data: {lead_data}
            
            Respond with a JSON object containing:
            - qualification_score: score from 0-100
            - qualification_level: one of "hot", "warm", "cold"
            - missing_information: array of missing data points that would improve qualification
            - next_actions: array of recommended next steps
            ''',
            'output_schema': {
                'qualification_score': 'number',  # 0-100
                'qualification_level': 'string',  # hot, warm, cold
                'missing_information': 'array',
                'next_actions': 'array'
            }
        },
        'contact_profiling': {
            'prompt_template': '''
            Create a comprehensive profile for this contact based on available data:
            
            Contact Data: {contact_data}
            
            Respond with a JSON object containing:
            - persona: brief description of the contact's professional persona
            - interests: array of identified interests and topics
            - communication_preference: preferred communication style
            - engagement_likelihood: probability of engagement (0-1)
            ''',
            'output_schema': {
                'persona': 'string',
                'interests': 'array', 
                'communication_preference': 'string',
                'engagement_likelihood': 'number'
            }
        },
        'channel_optimization': {
            'prompt_template': '''
            Optimize communication channel strategy for the following goal: {goal}
            
            Channel Data: {channel_data}
            Historical Performance: {performance_data}
            
            Respond with a JSON object containing:
            - recommended_channels: array of channels ranked by effectiveness
            - timing_recommendations: object with optimal timing for each channel
            - content_suggestions: array of content recommendations per channel
            - expected_performance: object with predicted metrics for each channel
            ''',
            'output_schema': {
                'recommended_channels': 'array',
                'timing_recommendations': 'object',
                'content_suggestions': 'array',
                'expected_performance': 'object'
            }
        }
    }
    
    def __init__(self, tenant, user):
        self.tenant = tenant
        self.user = user
    
    async def analyze(self, analysis_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform AI analysis of the specified type
        
        Args:
            analysis_type: One of the supported analysis types
            data: Input data for analysis
            
        Returns:
            Structured analysis results matching the output schema
        """
        
        if analysis_type not in self.ANALYSIS_TYPES:
            raise ValueError(f"Unsupported analysis type: {analysis_type}")
        
        config = self.ANALYSIS_TYPES[analysis_type]
        
        # Build context from input data
        context = self._build_analysis_context(analysis_type, data)
        
        # Format prompt with context
        prompt = config['prompt_template'].format(**context)
        
        # Process with AI (simplified - would use actual OpenAI API)
        result = await self._process_analysis(analysis_type, prompt, config)
        
        # Validate output against schema
        validated_result = self._validate_output(result, config['output_schema'])
        
        logger.info(f"Completed {analysis_type} analysis for tenant {self.tenant.name}")
        
        return validated_result
    
    def _build_analysis_context(self, analysis_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Build context for analysis based on type and input data"""
        
        context = data.copy()
        
        # Add common context
        context.update({
            'analysis_type': analysis_type,
            'tenant_name': self.tenant.name,
            'timestamp': timezone.now().isoformat()
        })
        
        # Type-specific context building
        if analysis_type == 'summary':
            context.setdefault('max_words', 100)
        
        elif analysis_type == 'classification':
            if 'categories' not in context:
                context['categories'] = ['general', 'important', 'urgent', 'follow-up']
        
        elif analysis_type == 'extraction':
            if 'entity_types' not in context:
                context['entity_types'] = ['person', 'company', 'email', 'phone', 'date', 'amount']
        
        elif analysis_type == 'lead_qualification':
            if 'criteria' not in context:
                context['criteria'] = [
                    'Budget authority',
                    'Identified need',
                    'Timeline for decision',
                    'Company size',
                    'Industry relevance'
                ]
        
        elif analysis_type == 'channel_optimization':
            if 'goal' not in context:
                context['goal'] = 'maximize engagement'
            if 'performance_data' not in context:
                context['performance_data'] = {}
        
        return context
    
    async def _process_analysis(self, analysis_type: str, prompt: str, config: Dict) -> Dict[str, Any]:
        """Process analysis with AI model (simplified implementation)"""
        
        # Simulate AI processing based on analysis type
        if analysis_type == 'sentiment':
            return {
                'sentiment': 'positive',
                'confidence': 0.85,
                'reasoning': 'The content contains positive language and optimistic tone'
            }
        
        elif analysis_type == 'summary':
            return {
                'summary': 'Key points summarized from the provided content.',
                'key_points': ['Point 1', 'Point 2', 'Point 3'],
                'word_count': 8
            }
        
        elif analysis_type == 'classification':
            return {
                'primary_category': 'important',
                'confidence': 0.78,
                'all_categories': [
                    {'category': 'important', 'confidence': 0.78},
                    {'category': 'urgent', 'confidence': 0.65},
                    {'category': 'follow-up', 'confidence': 0.45}
                ]
            }
        
        elif analysis_type == 'extraction':
            return {
                'entities': [
                    {'type': 'person', 'value': 'John Smith', 'confidence': 0.95},
                    {'type': 'company', 'value': 'Acme Corp', 'confidence': 0.88},
                    {'type': 'email', 'value': 'john@acme.com', 'confidence': 0.99}
                ],
                'confidence_scores': {
                    'person': 0.95,
                    'company': 0.88,
                    'email': 0.99
                }
            }
        
        elif analysis_type == 'lead_qualification':
            return {
                'qualification_score': 75,
                'qualification_level': 'warm',
                'missing_information': ['budget range', 'decision timeline'],
                'next_actions': [
                    'Schedule discovery call',
                    'Send pricing information',
                    'Connect with decision maker'
                ]
            }
        
        elif analysis_type == 'contact_profiling':
            return {
                'persona': 'Technology-focused business leader interested in efficiency solutions',
                'interests': ['automation', 'productivity', 'team collaboration'],
                'communication_preference': 'direct and data-driven',
                'engagement_likelihood': 0.72
            }
        
        elif analysis_type == 'channel_optimization':
            return {
                'recommended_channels': [
                    {'channel': 'email', 'score': 0.85},
                    {'channel': 'linkedin', 'score': 0.78},
                    {'channel': 'phone', 'score': 0.65}
                ],
                'timing_recommendations': {
                    'email': 'Tuesday-Thursday 10am-2pm',
                    'linkedin': 'Monday-Wednesday 8am-10am',
                    'phone': 'Tuesday-Thursday 2pm-4pm'
                },
                'content_suggestions': [
                    'Case studies and ROI data for email',
                    'Thought leadership content for LinkedIn',
                    'Demo invitations for phone calls'
                ],
                'expected_performance': {
                    'email': {'open_rate': 0.25, 'response_rate': 0.08},
                    'linkedin': {'view_rate': 0.45, 'response_rate': 0.12},
                    'phone': {'connect_rate': 0.35, 'conversion_rate': 0.18}
                }
            }
        
        # Default fallback
        return {'error': f'Analysis type {analysis_type} not implemented'}
    
    def _validate_output(self, result: Dict[str, Any], schema: Dict[str, str]) -> Dict[str, Any]:
        """Validate analysis output against expected schema"""
        
        validated = {}
        
        for field, expected_type in schema.items():
            if field in result:
                value = result[field]
                
                # Basic type validation
                if expected_type == 'string' and isinstance(value, str):
                    validated[field] = value
                elif expected_type == 'number' and isinstance(value, (int, float)):
                    validated[field] = value
                elif expected_type == 'array' and isinstance(value, list):
                    validated[field] = value
                elif expected_type == 'object' and isinstance(value, dict):
                    validated[field] = value
                else:
                    logger.warning(f"Type mismatch for field {field}: expected {expected_type}, got {type(value)}")
                    validated[field] = value  # Include anyway with warning
            else:
                logger.warning(f"Missing expected field in analysis output: {field}")
        
        # Include any additional fields from result
        for field, value in result.items():
            if field not in validated:
                validated[field] = value
        
        return validated
    
    def get_available_analysis_types(self) -> List[Dict[str, Any]]:
        """Get list of available analysis types with descriptions"""
        
        return [
            {
                'type': analysis_type,
                'description': self._get_analysis_description(analysis_type),
                'output_schema': config['output_schema']
            }
            for analysis_type, config in self.ANALYSIS_TYPES.items()
        ]
    
    def _get_analysis_description(self, analysis_type: str) -> str:
        """Get human-readable description for analysis type"""
        
        descriptions = {
            'sentiment': 'Analyze the emotional tone and sentiment of text content',
            'summary': 'Generate concise summaries with key points extraction',
            'classification': 'Categorize content into predefined categories',
            'extraction': 'Extract specific entities and data points from text',
            'lead_qualification': 'Score and qualify leads based on business criteria',
            'contact_profiling': 'Create detailed profiles of contacts and prospects',
            'channel_optimization': 'Optimize communication channels and timing for maximum engagement'
        }
        
        return descriptions.get(analysis_type, f'AI analysis of type: {analysis_type}')