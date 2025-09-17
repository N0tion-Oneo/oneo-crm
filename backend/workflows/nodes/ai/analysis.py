"""
AI Analysis Node Processor - Analyze text content with AI
"""
import logging
from typing import Dict, Any
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class AIAnalysisProcessor(AsyncNodeProcessor):
    """Process AI analysis and classification nodes"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["analysis_type"],
        "properties": {
            "analysis_type": {
                "type": "string",
                "enum": ["sentiment", "summary", "classification", "extraction", "question", "general"],
                "default": "general",
                "description": "Type of analysis to perform",
                "ui_hints": {
                    "widget": "select"
                }
            },
            "data_source": {
                "type": "string",
                "description": "Path to data in context (e.g., 'node_123.output')",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "{{previous_node.output}} or trigger.data.content"
                }
            },
            "content": {
                "type": "string",
                "description": "Direct content to analyze (if not using data_source)",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 6,
                    "placeholder": "Enter or paste content to analyze",
                    "show_when": {"data_source": ""}
                }
            },
            "categories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Categories for classification analysis",
                "ui_hints": {
                    "widget": "tag_input",
                    "placeholder": "Add categories (e.g., Support, Sales, Bug)",
                    "show_when": {"analysis_type": "classification"}
                }
            },
            "extract_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Fields to extract from content",
                "ui_hints": {
                    "widget": "tag_input",
                    "placeholder": "Add fields to extract (e.g., name, email, date)",
                    "show_when": {"analysis_type": "extraction"}
                }
            },
            "question": {
                "type": "string",
                "description": "Question to answer about the content",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "What is the main topic discussed?",
                    "show_when": {"analysis_type": "question"}
                }
            },
            "analysis_prompt": {
                "type": "string",
                "description": "Custom analysis prompt for general analysis",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 4,
                    "placeholder": "Analyze the key themes and provide insights",
                    "show_when": {"analysis_type": "general"}
                }
            },
            "max_summary_length": {
                "type": "integer",
                "minimum": 10,
                "maximum": 500,
                "default": 100,
                "description": "Maximum words for summary",
                "ui_hints": {
                    "show_when": {"analysis_type": "summary"}
                }
            },
            "ai_model": {
                "type": "string",
                "enum": ["gpt-4", "gpt-3.5-turbo", "claude-3", "claude-3-haiku"],
                "default": "gpt-4",
                "description": "AI model to use for analysis",
                "ui_hints": {
                    "widget": "select"
                }
            },
            "temperature": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "default": 0.3,
                "description": "AI creativity level (lower for factual analysis)",
                "ui_hints": {
                    "widget": "slider",
                    "step": 0.1
                }
            },
            "max_tokens": {
                "type": "integer",
                "minimum": 50,
                "maximum": 2000,
                "default": 500,
                "description": "Maximum response length"
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "ai_analysis"
        self.supports_replay = True
        self.supports_checkpoints = True

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process AI analysis node"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Get configuration values
        analysis_type = config.get('analysis_type', 'general')
        data_source = config.get('data_source', '')

        # Get data to analyze from context
        data_to_analyze = self._get_nested_value(context, data_source) if data_source else config.get('content', '')

        if not data_to_analyze:
            return {
                'success': False,
                'error': 'No data provided for analysis'
            }

        # Build analysis prompt based on type
        if analysis_type == 'sentiment':
            prompt = f"Analyze the sentiment of this text and return 'positive', 'negative', or 'neutral': {data_to_analyze}"
        elif analysis_type == 'summary':
            max_length = config.get('max_summary_length', 100)
            prompt = f"Provide a concise summary in {max_length} words or less: {data_to_analyze}"
        elif analysis_type == 'classification':
            categories = config.get('categories', [])
            if not categories:
                return {
                    'success': False,
                    'error': 'Classification requires categories'
                }
            categories_str = ", ".join(categories)
            prompt = f"Classify this content into one of these categories [{categories_str}]: {data_to_analyze}"
        elif analysis_type == 'extraction':
            extract_fields = config.get('extract_fields', [])
            fields_str = ", ".join(extract_fields)
            prompt = f"Extract the following information [{fields_str}] from this text: {data_to_analyze}"
        elif analysis_type == 'question':
            question = config.get('question', '')
            prompt = f"Answer this question based on the text: {question}\n\nText: {data_to_analyze}"
        else:
            # General analysis
            analysis_prompt = config.get('analysis_prompt', 'Analyze this data')
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
                        'ai_model': config.get('ai_model', 'gpt-4'),
                        'temperature': config.get('temperature', 0.3),  # Lower for analysis
                        'max_tokens': config.get('max_tokens', 500),
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

