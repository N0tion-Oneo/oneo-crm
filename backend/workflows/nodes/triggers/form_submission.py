"""
Form submission trigger node processor
"""
import logging
from typing import Dict, Any
from workflows.nodes.base import BaseNodeProcessor

logger = logging.getLogger(__name__)


class TriggerFormSubmittedProcessor(BaseNodeProcessor):
    """
    Processes form submission trigger events
    This node starts a workflow when a form is submitted
    """

    async def process(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process form submission trigger

        The trigger data from the event is passed in context['trigger_data']
        This includes form_data, pipeline_id, stage, etc.
        """
        trigger_data = context.get('trigger_data', {})

        # Extract form submission data
        form_data = trigger_data.get('form_data', {})
        pipeline_id = config.get('pipeline_id') or trigger_data.get('pipeline_id')
        form_mode = config.get('form_mode', 'create')
        stage = trigger_data.get('stage')

        # Add submission metadata
        submission_info = {
            'submitted_at': trigger_data.get('submitted_at'),
            'ip_address': trigger_data.get('ip_address'),
            'user_agent': trigger_data.get('user_agent'),
        }

        logger.info(f"Form submission trigger activated for pipeline {pipeline_id}")

        # Pass the form data forward in the workflow
        return {
            'success': True,
            'form_data': form_data,
            'pipeline_id': pipeline_id,
            'form_mode': form_mode,
            'stage': stage,
            'submission_info': submission_info,
            'trigger_type': 'form_submitted'
        }

    def get_display_name(self) -> str:
        return "Form Submission Trigger"

    def get_description(self) -> str:
        return "Starts workflow when a form is submitted"

    def get_category(self) -> str:
        return "Triggers"

    def get_icon(self) -> str:
        return "📝"