"""
Generate Form Link Node Processor
Creates form URLs for pipeline data collection
"""
import logging
from typing import Dict, Any
from workflows.nodes.base import BaseNodeProcessor

logger = logging.getLogger(__name__)


class GenerateFormLinkProcessor(BaseNodeProcessor):
    """Processor for generating form links for pipelines"""

    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "pipeline_id": {
                "type": "string",
                "required": True,
                "description": "Pipeline to generate form for",
                "ui_hints": {
                    "widget": "pipeline_select",
                    "placeholder": "Select pipeline"
                }
            },
            "form_mode": {
                "type": "string",
                "default": "public_filtered",
                "description": "Form access mode",
                "ui_hints": {
                    "widget": "select",
                    "options": [
                        {"value": "public_filtered", "label": "Public (Filtered Fields)"},
                        {"value": "internal_full", "label": "Internal (All Fields)"}
                    ]
                }
            },
            "custom_path": {
                "type": "string",
                "description": "Custom URL path (optional)",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "e.g., /apply-now",
                    "advanced": True
                }
            },
            "expiry_hours": {
                "type": "number",
                "description": "Hours until link expires (0 for no expiry)",
                "default": 0,
                "ui_hints": {
                    "widget": "number",
                    "min": 0,
                    "max": 8760,
                    "step": 24,
                    "advanced": True
                }
            },
            "prefill_data": {
                "type": "object",
                "description": "Data to prefill in the form",
                "ui_hints": {
                    "widget": "json",
                    "collapsible": True,
                    "advanced": True
                }
            }
        },
        "required": ["pipeline_id"]
    }

    def __init__(self):
        super().__init__()
        self.node_type = "generate_form_link"

    def process(self, input_data, context=None):
        """Generate a form URL with configuration"""

        pipeline_id = input_data.get('pipeline_id')
        form_mode = input_data.get('form_mode', 'public_filtered')
        custom_path = input_data.get('custom_path')
        expiry_hours = input_data.get('expiry_hours', 0)
        prefill_data = input_data.get('prefill_data', {})

        if not pipeline_id:
            return {
                'success': False,
                'error': 'Pipeline ID is required'
            }

        # Generate form URL based on mode
        if custom_path:
            form_url = custom_path
        elif form_mode == 'internal_full':
            form_url = f"/forms/internal/{pipeline_id}"
        else:
            form_url = f"/forms/{pipeline_id}"

        # Add query parameters if needed
        query_params = []
        if prefill_data:
            # In production, this would encode the prefill data
            query_params.append("prefill=true")
        if expiry_hours > 0:
            query_params.append(f"expires={expiry_hours}")

        if query_params:
            form_url += "?" + "&".join(query_params)

        return {
            'success': True,
            'output': {
                'form_url': form_url,
                'full_url': f"https://domain.com{form_url}",  # Would use actual domain
                'pipeline_id': pipeline_id,
                'form_mode': form_mode,
                'expires_in_hours': expiry_hours,
                'has_prefill': bool(prefill_data)
            }
        }