"""
Node processors for workflow engine
"""
import logging

logger = logging.getLogger(__name__)


class BaseNodeProcessor:
    """Base class for all node processors"""

    def __init__(self):
        self.name = self.__class__.__name__

    def process(self, input_data, context=None):
        """Process the node with given input"""
        raise NotImplementedError("Subclasses must implement process method")

    def validate(self, config):
        """Validate node configuration"""
        return True


class TriggerFormSubmittedProcessor(BaseNodeProcessor):
    """Processor for form submission trigger"""

    def process(self, input_data, context=None):
        """Process form submission trigger"""
        return {
            'success': True,
            'output': {
                'form_data': input_data,
                'pipeline_id': context.get('pipeline_id'),
                'form_mode': context.get('form_mode')
            }
        }


class GenerateFormProcessor(BaseNodeProcessor):
    """Processor for form generation node"""

    def process(self, input_data, context=None):
        """Generate a form URL"""
        pipeline_id = input_data.get('pipeline_id')
        form_mode = input_data.get('form_mode', 'public_filtered')

        # Generate form URL based on mode
        if form_mode == 'internal_full':
            form_url = f"/forms/internal/{pipeline_id}"
        elif form_mode == 'public_filtered':
            form_url = f"/forms/{pipeline_id}"
        else:
            form_url = f"/forms/{pipeline_id}"

        return {
            'success': True,
            'output': {
                'form_url': form_url,
                'pipeline_id': pipeline_id,
                'form_mode': form_mode
            }
        }


class SendEmailProcessor(BaseNodeProcessor):
    """Processor for send email node"""

    def process(self, input_data, context=None):
        """Send email"""
        return {
            'success': True,
            'output': {
                'status': 'Email would be sent',
                'to': input_data.get('to', 'recipient@example.com'),
                'subject': input_data.get('subject', 'Test Email'),
                'body': input_data.get('body', 'This is a test email from workflow')
            }
        }


class UpdateRecordProcessor(BaseNodeProcessor):
    """Processor for update record node"""

    def process(self, input_data, context=None):
        """Update record"""
        return {
            'success': True,
            'output': {
                'status': 'Record would be updated',
                'pipeline_id': input_data.get('pipeline_id'),
                'record_id': input_data.get('record_id', 'test-record-123'),
                'fields_updated': input_data.get('fields', {})
            }
        }


class CreateRecordProcessor(BaseNodeProcessor):
    """Processor for create record node"""

    def process(self, input_data, context=None):
        """Create record"""
        return {
            'success': True,
            'output': {
                'status': 'Record would be created',
                'pipeline_id': input_data.get('pipeline_id'),
                'new_record_id': 'new-record-456',
                'fields': input_data.get('fields', {})
            }
        }


class ConditionalProcessor(BaseNodeProcessor):
    """Processor for conditional logic node"""

    def process(self, input_data, context=None):
        """Process conditional logic"""
        condition = input_data.get('condition', {})
        return {
            'success': True,
            'output': {
                'status': 'Condition evaluated',
                'condition': condition,
                'result': 'Would evaluate to true/false based on runtime data',
                'next_path': 'true_branch' if condition else 'false_branch'
            }
        }


class AIAnalysisProcessor(BaseNodeProcessor):
    """Processor for AI analysis node"""

    def process(self, input_data, context=None):
        """AI analysis"""
        return {
            'success': True,
            'output': {
                'status': 'AI analysis would be performed',
                'prompt': input_data.get('prompt', 'Analyze this data'),
                'model': input_data.get('model', 'gpt-4'),
                'sample_result': 'This is a sample AI analysis result. In production, this would call OpenAI API.'
            }
        }


class DelayProcessor(BaseNodeProcessor):
    """Processor for delay node"""

    def process(self, input_data, context=None):
        """Process delay"""
        delay_seconds = input_data.get('delay_seconds', 60)
        return {
            'success': True,
            'output': {
                'status': f'Would wait for {delay_seconds} seconds',
                'delay_seconds': delay_seconds
            }
        }


class WebhookProcessor(BaseNodeProcessor):
    """Processor for webhook node"""

    def process(self, input_data, context=None):
        """Process webhook"""
        return {
            'success': True,
            'output': {
                'status': 'Webhook would be called',
                'url': input_data.get('url', 'https://api.example.com/webhook'),
                'method': input_data.get('method', 'POST'),
                'headers': input_data.get('headers', {}),
                'sample_response': {'status': 200, 'body': {'success': True}}
            }
        }


# Registry of node processors
NODE_PROCESSORS = {
    # Triggers
    'trigger_form_submitted': TriggerFormSubmittedProcessor,

    # Form operations
    'generate_form': GenerateFormProcessor,

    # Communication
    'send_email': SendEmailProcessor,
    'send_sms': SendEmailProcessor,  # Reuse for now
    'send_whatsapp': SendEmailProcessor,  # Reuse for now

    # Record operations
    'update_record': UpdateRecordProcessor,
    'create_record': CreateRecordProcessor,
    'delete_record': UpdateRecordProcessor,  # Reuse for now
    'find_records': CreateRecordProcessor,  # Reuse for now

    # Logic nodes
    'conditional': ConditionalProcessor,
    'delay': DelayProcessor,

    # AI nodes
    'ai_analysis': AIAnalysisProcessor,
    'ai_prompt': AIAnalysisProcessor,  # Reuse for now

    # External integrations
    'webhook': WebhookProcessor,
    'http_request': WebhookProcessor,  # Reuse for now
}


def get_node_processor(node_type):
    """Get processor instance for a given node type"""
    processor_class = NODE_PROCESSORS.get(node_type)

    if processor_class:
        return processor_class()

    # Log warning for unknown node types
    logger.warning(f"No processor found for node type: {node_type}")
    return None