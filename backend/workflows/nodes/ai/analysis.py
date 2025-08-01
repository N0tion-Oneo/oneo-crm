"""
AI Analysis Node Processor - Structured data analysis with AI
"""
import logging
from typing import Dict, Any
from workflows.nodes.ai.prompt import AIPromptProcessor

logger = logging.getLogger(__name__)


class AIAnalysisProcessor(AIPromptProcessor):
    """Process AI analysis nodes with structured prompts for different analysis types"""
    
    def __init__(self):
        super().__init__()
        self.node_type = "AI_ANALYSIS"
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process AI analysis node"""
        
        node_data = node_config.get('data', {})
        analysis_type = node_data.get('analysis_type', 'general')
        data_source = node_data.get('data_source', '')
        
        # Get data to analyze
        data_to_analyze = self._get_nested_value(context, data_source)
        
        if not data_to_analyze:
            raise ValueError(f"No data found at source path: {data_source}")
        
        # Generate analysis prompt based on type
        prompt = self._generate_analysis_prompt(analysis_type, data_to_analyze, node_data)
        
        # Create a modified node config with the generated prompt
        analysis_config = {
            **node_config,
            'data': {
                **node_data,
                'prompt': prompt
            }
        }
        
        # Use parent AI prompt processing
        result = await super().process(analysis_config, context)
        
        # Post-process result based on analysis type
        return self._post_process_analysis_result(analysis_type, result, node_data)
    
    def _generate_analysis_prompt(self, analysis_type: str, data: Any, node_data: Dict[str, Any]) -> str:
        """Generate structured prompt based on analysis type"""
        
        if analysis_type == 'sentiment':
            return f"""
Analyze the sentiment of this text and return only one word: 'positive', 'negative', or 'neutral'.

Text to analyze:
{data}

Sentiment:"""
        
        elif analysis_type == 'summary':
            max_length = node_data.get('max_summary_length', 100)
            return f"""
Provide a concise summary of the following content in no more than {max_length} words:

Content:
{data}

Summary:"""
        
        elif analysis_type == 'classification':
            categories = node_data.get('categories', [])
            if not categories:
                raise ValueError("Categories required for classification analysis")
            
            return f"""
Classify this content into exactly one of these categories: {', '.join(categories)}

Content:
{data}

Return only the category name that best fits:"""
        
        elif analysis_type == 'extraction':
            fields_to_extract = node_data.get('fields_to_extract', [])
            if not fields_to_extract:
                raise ValueError("fields_to_extract required for extraction analysis")
            
            return f"""
Extract the following information from this content: {', '.join(fields_to_extract)}

Content:
{data}

Return as JSON format with the requested fields:"""
        
        elif analysis_type == 'lead_qualification':
            criteria = node_data.get('criteria', {})
            return f"""
Analyze this lead data for qualification based on these criteria:

Criteria: {criteria}

Lead Data:
{data}

Provide analysis in JSON format:
{{
  "qualification_score": [0-100],
  "qualified": [true/false],
  "strengths": ["strength1", "strength2"],
  "concerns": ["concern1", "concern2"],
  "recommendation": "next step recommendation"
}}"""
        
        elif analysis_type == 'channel_optimization':
            return f"""
Analyze this contact data to recommend the best communication channels:

Contact Data:
{data}

Based on the available contact information, rank the communication channels by effectiveness:
1. Email - available: {bool(self._extract_field(data, 'email'))}
2. LinkedIn - available: {bool(self._extract_field(data, 'linkedin_url'))}
3. Phone/SMS - available: {bool(self._extract_field(data, 'phone'))}
4. WhatsApp - available: {bool(self._extract_field(data, 'whatsapp'))}

Return JSON format:
{{
  "recommended_channels": ["channel1", "channel2"],
  "reasoning": "explanation of recommendation",
  "fallback_channels": ["fallback1", "fallback2"]
}}"""
        
        elif analysis_type == 'contact_profiling':
            return f"""
Analyze this contact information and infer missing professional details:

Contact Data:
{data}

Based on available information, infer and provide:

Return JSON format:
{{
  "inferred_title": "likely job title",
  "inferred_seniority": "junior/mid/senior/executive",
  "inferred_department": "likely department",
  "inferred_company_size": "startup/small/medium/large/enterprise",
  "inferred_industry": "likely industry",
  "confidence_score": [0-100],
  "reasoning": "explanation of inferences"
}}"""
        
        else:
            # General analysis
            instructions = node_data.get('analysis_instructions', 'Analyze this data and provide insights')
            return f"""
{instructions}

Data to analyze:
{data}

Analysis:"""
    
    def _post_process_analysis_result(self, analysis_type: str, result: Dict[str, Any], node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process analysis results based on type"""
        
        output = result.get('output', '')
        
        if analysis_type in ['classification', 'extraction', 'lead_qualification', 'channel_optimization', 'contact_profiling']:
            # Try to parse JSON output
            try:
                import json
                parsed_output = json.loads(output)
                result['structured_output'] = parsed_output
                result['output'] = parsed_output
            except json.JSONDecodeError:
                # If JSON parsing fails, keep original output
                logger.warning(f"Failed to parse JSON output for {analysis_type}: {output}")
        
        elif analysis_type == 'sentiment':
            # Normalize sentiment output
            sentiment = output.strip().lower()
            if sentiment not in ['positive', 'negative', 'neutral']:
                # Try to extract sentiment from longer response
                if 'positive' in sentiment:
                    sentiment = 'positive'
                elif 'negative' in sentiment:
                    sentiment = 'negative'
                else:
                    sentiment = 'neutral'
            
            result['sentiment'] = sentiment
            result['output'] = sentiment
        
        # Add analysis metadata
        result['analysis_type'] = analysis_type
        result['analysis_timestamp'] = context.get('execution_timestamp', '')
        
        return result
    
    def _extract_field(self, data: Any, field_name: str) -> Any:
        """Extract field from data structure"""
        if isinstance(data, dict):
            return data.get(field_name)
        elif hasattr(data, field_name):
            return getattr(data, field_name)
        return None
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate AI analysis node inputs"""
        # First run parent validation
        if not await super().validate_inputs(node_config, context):
            return False
        
        node_data = node_config.get('data', {})
        analysis_type = node_data.get('analysis_type', 'general')
        
        # Validate type-specific requirements
        if analysis_type == 'classification':
            categories = node_data.get('categories', [])
            if not categories or not isinstance(categories, list):
                return False
        
        elif analysis_type == 'extraction':
            fields_to_extract = node_data.get('fields_to_extract', [])
            if not fields_to_extract or not isinstance(fields_to_extract, list):
                return False
        
        # Check data source is provided
        data_source = node_data.get('data_source', '')
        if not data_source:
            return False
        
        return True