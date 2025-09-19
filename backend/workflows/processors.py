"""
Node processors for workflow engine
"""
import logging
from workflows.nodes.crm.status_update import FollowUpTaskProcessor

# Import all real trigger processors
from workflows.nodes.triggers.form_submission import TriggerFormSubmittedProcessor
from workflows.nodes.triggers.manual import TriggerManualProcessor
from workflows.nodes.triggers.record_created import TriggerRecordCreatedProcessor
from workflows.nodes.triggers.record_updated import TriggerRecordUpdatedProcessor
from workflows.nodes.triggers.record_deleted import TriggerRecordDeletedProcessor
from workflows.nodes.triggers.schedule import TriggerScheduleProcessor
from workflows.nodes.triggers.webhook import TriggerWebhookProcessor
from workflows.nodes.triggers.email_received import TriggerEmailReceivedProcessor
from workflows.nodes.triggers.message_received import (
    TriggerLinkedInMessageProcessor, TriggerWhatsAppMessageProcessor
)
from workflows.nodes.triggers.date_reached import TriggerDateReachedProcessor
from workflows.nodes.triggers.pipeline_stage import TriggerPipelineStageChangedProcessor
from workflows.nodes.triggers.workflow_completed import TriggerWorkflowCompletedProcessor
from workflows.nodes.triggers.condition_met import TriggerConditionMetProcessor

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


# TriggerFormSubmittedProcessor removed - using the real processor from workflows.nodes.triggers.form_submission


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
    # Triggers - using real processors from nodes/triggers/
    'trigger_form_submitted': TriggerFormSubmittedProcessor,
    'trigger_manual': TriggerManualProcessor,
    'trigger_record_created': TriggerRecordCreatedProcessor,
    'trigger_record_updated': TriggerRecordUpdatedProcessor,
    'trigger_record_deleted': TriggerRecordDeletedProcessor,
    'trigger_scheduled': TriggerScheduleProcessor,
    'trigger_webhook': TriggerWebhookProcessor,
    'trigger_email_received': TriggerEmailReceivedProcessor,
    'trigger_linkedin_message': TriggerLinkedInMessageProcessor,
    'trigger_whatsapp_message': TriggerWhatsAppMessageProcessor,
    'trigger_date_reached': TriggerDateReachedProcessor,
    'trigger_pipeline_stage_changed': TriggerPipelineStageChangedProcessor,
    'trigger_workflow_completed': TriggerWorkflowCompletedProcessor,
    'trigger_condition_met': TriggerConditionMetProcessor,

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

    # CRM nodes
    'CREATE_FOLLOW_UP_TASK': FollowUpTaskProcessor,
}


def get_node_processor(node_type):
    """Get processor instance for a given node type"""
    processor_class = NODE_PROCESSORS.get(node_type)

    if processor_class:
        return processor_class()

    # Try to get from the registry if not in local dict
    try:
        from workflows.core.registry import node_registry
        return node_registry.get_processor(node_type)
    except:
        pass

    # Log warning for unknown node types
    logger.warning(f"No processor found for node type: {node_type}")
    return None


def get_all_node_processors():
    """Get all available node processors including those from registry"""
    all_processors = {}

    # Don't use the old NODE_PROCESSORS - it has outdated naming
    # all_processors.update(NODE_PROCESSORS)

    # Try to get processors from registry
    try:
        from workflows.core.registry import node_registry

        # Add all registered processors
        for node_type in node_registry.get_available_node_types():
            if node_type not in all_processors:
                processor = node_registry.get_processor(node_type)
                all_processors[node_type] = processor.__class__
    except Exception as e:
        logger.debug(f"Could not load processors from registry: {e}")

    # Try to import specific node processors that we know have CONFIG_SCHEMA
    try:
        # Import trigger processors
        from workflows.nodes.triggers.manual import TriggerManualProcessor
        from workflows.nodes.triggers.record_created import TriggerRecordCreatedProcessor
        from workflows.nodes.triggers.record_updated import TriggerRecordUpdatedProcessor
        from workflows.nodes.triggers.record_deleted import TriggerRecordDeletedProcessor
        from workflows.nodes.triggers.form_submission import TriggerFormSubmittedProcessor
        from workflows.nodes.triggers.schedule import TriggerScheduleProcessor
        from workflows.nodes.triggers.webhook import TriggerWebhookProcessor
        from workflows.nodes.triggers.email_received import TriggerEmailReceivedProcessor
        from workflows.nodes.triggers.message_received import (
            TriggerLinkedInMessageProcessor, TriggerWhatsAppMessageProcessor
        )
        from workflows.nodes.triggers.date_reached import TriggerDateReachedProcessor
        from workflows.nodes.triggers.pipeline_stage import TriggerPipelineStageChangedProcessor
        from workflows.nodes.triggers.workflow_completed import TriggerWorkflowCompletedProcessor
        from workflows.nodes.triggers.condition_met import TriggerConditionMetProcessor

        # Import all the processors we've updated
        from workflows.nodes.data.record_ops import (
            RecordCreateProcessor, RecordUpdateProcessor,
            RecordFindProcessor, RecordDeleteProcessor
        )
        from workflows.nodes.ai.prompt import AIPromptProcessor
        from workflows.nodes.ai.analysis import AIAnalysisProcessor
        from workflows.nodes.ai.message_generator import AIMessageGeneratorProcessor
        from workflows.nodes.ai.response_evaluator import AIResponseEvaluatorProcessor
        from workflows.nodes.communication.ai_conversation_loop import AIConversationLoopProcessor
        from workflows.nodes.control.condition import ConditionProcessor
        from workflows.nodes.control.for_each import ForEachProcessor
        from workflows.nodes.control.workflow_loop import WorkflowLoopController
        from workflows.nodes.utility.wait import WaitDelayProcessor
        from workflows.nodes.utility.wait_advanced import (
            WaitForResponseProcessor, WaitForRecordEventProcessor, WaitForConditionProcessor
        )
        from workflows.nodes.utility.conversation_state import ConversationStateProcessor
        from workflows.nodes.communication.email import EmailProcessor
        from workflows.nodes.communication.whatsapp import WhatsAppProcessor
        from workflows.nodes.communication.linkedin import LinkedInProcessor
        from workflows.nodes.communication.sms import SMSProcessor
        from workflows.nodes.communication.sync import MessageSyncProcessor
        from workflows.nodes.communication.logging import CommunicationLoggingProcessor
        from workflows.nodes.communication.analysis import CommunicationAnalysisProcessor, EngagementScoringProcessor
        from workflows.nodes.utility.notification import TaskNotificationProcessor
        from workflows.nodes.crm.contact import ContactResolveProcessor
        from workflows.nodes.crm.status_update import ContactStatusUpdateProcessor, FollowUpTaskProcessor
        from workflows.nodes.external.http import HTTPRequestProcessor
        from workflows.nodes.external.webhook import WebhookOutProcessor
        from workflows.nodes.workflow.sub_workflow import SubWorkflowProcessor
        from workflows.nodes.data.merge import MergeDataProcessor

        # Add all the processors with their CONFIG_SCHEMA (using lowercase keys)
        processor_classes = {
            # Trigger processors
            'trigger_manual': TriggerManualProcessor,
            'trigger_record_created': TriggerRecordCreatedProcessor,
            'trigger_record_updated': TriggerRecordUpdatedProcessor,
            'trigger_record_deleted': TriggerRecordDeletedProcessor,
            'trigger_form_submitted': TriggerFormSubmittedProcessor,
            'trigger_scheduled': TriggerScheduleProcessor,
            'trigger_webhook': TriggerWebhookProcessor,
            'trigger_email_received': TriggerEmailReceivedProcessor,
            'trigger_linkedin_message': TriggerLinkedInMessageProcessor,
            'trigger_whatsapp_message': TriggerWhatsAppMessageProcessor,
            'trigger_date_reached': TriggerDateReachedProcessor,
            'trigger_pipeline_stage_changed': TriggerPipelineStageChangedProcessor,
            'trigger_workflow_completed': TriggerWorkflowCompletedProcessor,
            'trigger_condition_met': TriggerConditionMetProcessor,

            # Data operation processors
            'record_create': RecordCreateProcessor,
            'record_update': RecordUpdateProcessor,
            'record_find': RecordFindProcessor,
            'record_delete': RecordDeleteProcessor,
            'ai_prompt': AIPromptProcessor,
            'ai_analysis': AIAnalysisProcessor,
            'ai_message_generator': AIMessageGeneratorProcessor,
            'ai_response_evaluator': AIResponseEvaluatorProcessor,
            'ai_conversation_loop': AIConversationLoopProcessor,
            'condition': ConditionProcessor,
            'for_each': ForEachProcessor,
            'workflow_loop_controller': WorkflowLoopController,
            'wait_delay': WaitDelayProcessor,
            'wait_for_response': WaitForResponseProcessor,
            'wait_for_record_event': WaitForRecordEventProcessor,
            'wait_for_condition': WaitForConditionProcessor,
            'conversation_state': ConversationStateProcessor,
            'unipile_send_email': EmailProcessor,
            'unipile_send_whatsapp': WhatsAppProcessor,
            'unipile_send_linkedin': LinkedInProcessor,
            'unipile_send_sms': SMSProcessor,
            'unipile_sync_messages': MessageSyncProcessor,
            'log_communication': CommunicationLoggingProcessor,
            'analyze_communication': CommunicationAnalysisProcessor,
            'score_engagement': EngagementScoringProcessor,
            'task_notify': TaskNotificationProcessor,
            'resolve_contact': ContactResolveProcessor,
            'update_contact_status': ContactStatusUpdateProcessor,
            'create_follow_up_task': FollowUpTaskProcessor,
            'http_request': HTTPRequestProcessor,
            'webhook_out': WebhookOutProcessor,
            'sub_workflow': SubWorkflowProcessor,
            'merge_data': MergeDataProcessor,
        }

        all_processors.update(processor_classes)

    except ImportError as e:
        logger.error(f"Could not import all node processors: {e}")
        import traceback
        traceback.print_exc()

    return all_processors