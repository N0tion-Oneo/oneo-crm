"""
AI Analysis Node Processor - Analyze text content with AI
"""
import logging
from typing import Dict, Any
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class AIAnalysisProcessor(AsyncNodeProcessor):
    """Process AI analysis and classification nodes"""

    def __init__(self):
        super().__init__()
        self.node_type = "AI_ANALYSIS"
        self.supports_replay = True
        self.supports_checkpoints = True

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process AI analysis node"""

        node_data = node_config.get('data', {})
        analysis_type = node_data.get('analysis_type', 'general')
        data_source = node_data.get('data_source', '')

        # Get data to analyze from context
        data_to_analyze = self._get_nested_value(context, data_source) if data_source else node_data.get('content', '')

        if not data_to_analyze:
            return {
                'success': False,
                'error': 'No data provided for analysis'
            }

        # Build analysis prompt based on type
        if analysis_type == 'sentiment':
            prompt = f"Analyze the sentiment of this text and return 'positive', 'negative', or 'neutral': {data_to_analyze}"
        elif analysis_type == 'summary':
            max_length = node_data.get('max_summary_length', 100)
            prompt = f"Provide a concise summary in {max_length} words or less: {data_to_analyze}"
        elif analysis_type == 'classification':
            categories = node_data.get('categories', [])
            if not categories:
                return {
                    'success': False,
                    'error': 'Classification requires categories'
                }
            categories_str = ", ".join(categories)
            prompt = f"Classify this content into one of these categories [{categories_str}]: {data_to_analyze}"
        elif analysis_type == 'extraction':
            extract_fields = node_data.get('extract_fields', [])
            fields_str = ", ".join(extract_fields)
            prompt = f"Extract the following information [{fields_str}] from this text: {data_to_analyze}"
        elif analysis_type == 'question':
            question = node_data.get('question', '')
            prompt = f"Answer this question based on the text: {question}\n\nText: {data_to_analyze}"
        else:
            # General analysis
            analysis_prompt = node_data.get('analysis_prompt', 'Analyze this data')
            prompt = f"{analysis_prompt}: {data_to_analyze}"

        try:
            # Use AI service for analysis
            from workflows.ai_integration import workflow_ai_processor
            from django_tenants.utils import schema_context

            tenant_schema = context.get('tenant_schema')

            # Get tenant
            from tenants.models import Tenant
            tenant = await self._get_tenant(tenant_schema)

            if not tenant or not tenant.can_use_ai_features():
                return {
                    'success': False,
                    'error': 'AI features not available for this tenant'
                }

            # Process with AI
            with schema_context(tenant_schema):
                result = await workflow_ai_processor.process_ai_field_async(
                    record_data={'analysis_input': data_to_analyze},
                    field_config={
                        'ai_prompt': prompt,
                        'ai_model': node_data.get('ai_model', 'gpt-4'),
                        'temperature': node_data.get('temperature', 0.3),  # Lower for analysis
                        'max_tokens': node_data.get('max_tokens', 500),
                    },
                    tenant=tenant,
                    user=None  # TODO: Get user from context
                )

            analysis_result = result.get('content', '')

            # Parse result based on analysis type
            if analysis_type == 'sentiment':
                # Ensure we return a valid sentiment
                sentiment = analysis_result.lower().strip()
                if sentiment not in ['positive', 'negative', 'neutral']:
                    sentiment = 'neutral'
                return {
                    'success': True,
                    'output': sentiment,
                    'sentiment': sentiment,
                    'raw_analysis': analysis_result
                }
            elif analysis_type == 'classification':
                # Extract the category from response
                category = analysis_result.strip()
                # Try to match with provided categories
                for cat in categories:
                    if cat.lower() in category.lower():
                        category = cat
                        break
                return {
                    'success': True,
                    'output': category,
                    'category': category,
                    'confidence': result.get('confidence', 1.0)
                }
            elif analysis_type == 'extraction':
                return {
                    'success': True,
                    'output': analysis_result,
                    'extracted_data': self._parse_extraction(analysis_result, extract_fields)
                }
            else:
                # General analysis result
                return {
                    'success': True,
                    'output': analysis_result,
                    'analysis_type': analysis_type,
                    'tokens_used': result.get('tokens_used', 0)
                }

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _parse_extraction(self, text: str, fields: list) -> Dict[str, Any]:
        """Parse extracted fields from AI response"""
        extracted = {}
        for field in fields:
            # Simple parsing - look for field: value pattern
            import re
            pattern = rf"{field}[:\s]+([^,\n]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted[field] = match.group(1).strip()
            else:
                extracted[field] = None
        return extracted

    async def _get_tenant(self, schema_name: str):
        """Get tenant by schema name"""
        from tenants.models import Tenant
        from asgiref.sync import sync_to_async

        try:
            return await sync_to_async(Tenant.objects.get)(schema_name=schema_name)
        except Tenant.DoesNotExist:
            return None

    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate analysis node inputs"""
        node_data = node_config.get('data', {})
        analysis_type = node_data.get('analysis_type', 'general')

        # Check for data source or content
        data_source = node_data.get('data_source', '')
        content = node_data.get('content', '')

        if not data_source and not content:
            return False

        # Validate type-specific requirements
        if analysis_type == 'classification':
            categories = node_data.get('categories', [])
            if not categories:
                return False
        elif analysis_type == 'extraction':
            extract_fields = node_data.get('extract_fields', [])
            if not extract_fields:
                return False
        elif analysis_type == 'question':
            question = node_data.get('question', '')
            if not question:
                return False

        return True