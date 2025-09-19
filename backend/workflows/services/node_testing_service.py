"""
Service for testing workflow nodes
"""
import logging
import time
import asyncio
from asgiref.sync import async_to_sync
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


class NodeTestingService:
    """Service for testing workflow nodes"""

    @staticmethod
    def test_node_standalone(request):
        """Test a node without requiring a workflow - for test page"""
        # Get node configuration from request
        node_type = request.data.get('node_type')
        node_config = request.data.get('node_config', {})
        test_record_id = request.data.get('test_record_id')
        test_data_id = request.data.get('test_data_id')
        test_data_type = request.data.get('test_data_type')

        logger.info(f"test_node_standalone called with node_type={node_type}, test_data_id={test_data_id}, test_data_type={test_data_type}")

        if not node_type:
            return Response({
                'success': False,
                'error': 'node_type is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get the actual processor directly
            from workflows.processors import get_node_processor
            processor = get_node_processor(node_type)

            if not processor:
                return Response({
                    'status': 'error',
                    'error': f'No processor found for node type: {node_type}'
                }, status=status.HTTP_404_NOT_FOUND)

            # Build base context
            context = NodeTestingService._build_base_context(request)

            # Build trigger data for trigger nodes
            if node_type.startswith('trigger_'):
                trigger_data = NodeTestingService._build_trigger_data(
                    node_type, node_config, test_record_id, test_data_id, test_data_type, request
                )
                context['trigger_data'] = trigger_data

            # For action nodes with test record
            elif test_record_id:
                record_context = NodeTestingService._build_record_context(test_record_id)
                if record_context:
                    context['record'] = record_context

            # Execute the processor in a thread pool to avoid event loop issues
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(NodeTestingService._execute_processor_thread, processor, node_config, context)
                try:
                    result = future.result(timeout=25)
                    return result
                except concurrent.futures.TimeoutError:
                    logger.error("Node test execution timed out")
                    return Response({
                        'status': 'error',
                        'error': 'Test execution timed out after 25 seconds',
                        'timeout': True
                    }, status=status.HTTP_408_REQUEST_TIMEOUT)

        except Exception as e:
            logger.error(f"Node test failed: {e}", exc_info=True)
            return Response({
                'status': 'error',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @staticmethod
    def _build_base_context(request):
        """Build base execution context"""
        return {
            'workflow_id': 'test_workflow',
            'execution_id': 'test_execution',
            'tenant_id': request.user.tenant_id if hasattr(request.user, 'tenant_id') else None,
            'user_id': request.user.id,
            'trigger_time': timezone.now().isoformat()
        }

    @staticmethod
    def _build_trigger_data(node_type, node_config, test_record_id, test_data_id, test_data_type, request):
        """Build trigger data based on node type"""
        trigger_data = {}

        if node_type == 'trigger_form_submitted':
            trigger_data = NodeTestingService._build_form_trigger_data(
                node_config, test_record_id, test_data_id, test_data_type
            )

        elif node_type in ['trigger_record_created', 'trigger_record_updated', 'trigger_record_deleted']:
            trigger_data = NodeTestingService._build_record_trigger_data(
                node_type, node_config, test_record_id, test_data_id, test_data_type, request
            )

        elif node_type == 'trigger_email_received':
            trigger_data = NodeTestingService._build_email_trigger_data(test_data_id, test_data_type)

        elif node_type in ['trigger_linkedin_message', 'trigger_whatsapp_message']:
            trigger_data = NodeTestingService._build_message_trigger_data(
                node_type, test_data_id, test_data_type
            )

        elif node_type == 'trigger_scheduled':
            trigger_data = NodeTestingService._build_schedule_trigger_data(test_data_id, test_data_type)

        elif node_type == 'trigger_webhook':
            trigger_data = NodeTestingService._build_webhook_trigger_data(node_config)

        elif node_type == 'trigger_pipeline_stage_changed':
            trigger_data = NodeTestingService._build_stage_change_trigger_data(
                test_data_id, test_data_type, node_config
            )

        elif node_type == 'trigger_workflow_completed':
            trigger_data = NodeTestingService._build_workflow_completed_trigger_data(
                test_data_id, test_data_type
            )

        else:
            # Default trigger data for unhandled trigger types
            trigger_data = {
                'triggered_at': timezone.now().isoformat(),
                'trigger_type': node_type
            }

        return trigger_data

    @staticmethod
    def _build_form_trigger_data(node_config, test_record_id, test_data_id, test_data_type):
        """Build form submission trigger data"""
        trigger_data = {
            'pipeline_id': node_config.get('pipeline_id'),
            'form_mode': node_config.get('mode', 'internal_full'),
            'stage': node_config.get('stage'),
            'submitted_at': timezone.now().isoformat()
        }

        # Get real form data
        if test_data_id and test_data_type == 'form_submission':
            from pipelines.models import FormSubmission
            try:
                submission = FormSubmission.objects.get(id=test_data_id)
                trigger_data['form_data'] = submission.submitted_data or {}
            except FormSubmission.DoesNotExist:
                trigger_data['form_data'] = {}
        elif test_record_id:
            from pipelines.models import Record
            try:
                record = Record.objects.get(id=test_record_id, is_deleted=False)
                trigger_data['form_data'] = record.data or {}
            except Record.DoesNotExist:
                trigger_data['form_data'] = {}
        else:
            trigger_data['form_data'] = {}

        return trigger_data

    @staticmethod
    def _build_record_trigger_data(node_type, node_config, test_record_id, test_data_id, test_data_type, request):
        """Build record trigger data"""
        # Check both test_record_id and test_data_id (when test_data_type is 'record')
        record_id_to_use = test_record_id or (test_data_id if test_data_type == 'record' else None)

        if record_id_to_use:
            from pipelines.models import Record
            try:
                record = Record.objects.get(id=record_id_to_use, is_deleted=False)
                trigger_data = {
                    'record': record.data or {},
                    'record_id': str(record.id),
                    'pipeline_id': str(record.pipeline_id),
                    'updated_at': record.updated_at.isoformat(),
                    'created_at': record.created_at.isoformat(),
                }

                if node_type == 'trigger_record_updated':
                    trigger_data['previous_record'] = record.data or {}
                    trigger_data['changed_fields'] = list(record.data.keys()) if record.data else []
                    trigger_data['updated_by'] = str(request.user.id)
                elif node_type == 'trigger_record_created':
                    trigger_data['created_by'] = str(request.user.id)
                elif node_type == 'trigger_record_deleted':
                    trigger_data['deleted_by'] = str(request.user.id)
                    trigger_data['deleted_at'] = timezone.now().isoformat()

                return trigger_data
            except Record.DoesNotExist:
                pass

        # No record found or provided - provide empty trigger data
        pipeline_id = node_config.get('pipeline_id') or \
                     (node_config.get('pipeline_ids', [None])[0] if node_config.get('pipeline_ids') else None)

        trigger_data = {
            'record': {},
            'pipeline_id': pipeline_id,
            'updated_at': timezone.now().isoformat(),
            'created_at': timezone.now().isoformat()
        }

        if node_type == 'trigger_record_updated':
            trigger_data['previous_record'] = {}
            trigger_data['changed_fields'] = []
            trigger_data['updated_by'] = str(request.user.id) if request.user.is_authenticated else None
        elif node_type == 'trigger_record_created':
            trigger_data['created_by'] = str(request.user.id) if request.user.is_authenticated else None
        elif node_type == 'trigger_record_deleted':
            trigger_data['deleted_by'] = str(request.user.id) if request.user.is_authenticated else None
            trigger_data['deleted_at'] = timezone.now().isoformat()

        return trigger_data

    @staticmethod
    def _build_email_trigger_data(test_data_id, test_data_type):
        """Build email trigger data"""
        if test_data_id and test_data_type == 'email':
            from communications.models import Message
            try:
                message = Message.objects.get(id=test_data_id)
                return {
                    'from': message.contact_email,
                    'to': message.channel.email_address if hasattr(message.channel, 'email_address') else 'team@company.com',
                    'subject': message.subject or '',
                    'body': message.content or '',
                    'message_id': str(message.id),
                    'received_at': message.created_at.isoformat()
                }
            except:
                pass

        return {
            'from': 'test@example.com',
            'to': 'team@company.com',
            'subject': 'Test Email',
            'body': 'Test email body'
        }

    @staticmethod
    def _build_message_trigger_data(node_type, test_data_id, test_data_type):
        """Build LinkedIn/WhatsApp message trigger data"""
        channel_type = 'linkedin' if 'linkedin' in node_type else 'whatsapp'

        if test_data_id and test_data_type == channel_type:
            from communications.models import Message
            try:
                message = Message.objects.get(id=test_data_id)
                return {
                    'from': message.contact_phone or message.contact_email,
                    'message': message.content or '',
                    'message_id': str(message.id),
                    'received_at': message.created_at.isoformat(),
                    'channel': channel_type
                }
            except:
                pass

        return {
            'from': 'test_user',
            'message': f'Test {channel_type} message',
            'channel': channel_type,
            'received_at': timezone.now().isoformat()
        }

    @staticmethod
    def _build_schedule_trigger_data(test_data_id, test_data_type):
        """Build schedule trigger data"""
        if test_data_id and test_data_type == 'schedule':
            from workflows.models import WorkflowSchedule
            try:
                schedule = WorkflowSchedule.objects.get(id=test_data_id)
                return {
                    'schedule_id': str(schedule.id),
                    'workflow_id': str(schedule.workflow.id),
                    'scheduled_time': schedule.next_run.isoformat() if schedule.next_run else timezone.now().isoformat(),
                    'cron_expression': schedule.cron_expression
                }
            except:
                pass

        return {
            'scheduled_time': timezone.now().isoformat(),
            'trigger_type': 'scheduled'
        }

    @staticmethod
    def _build_webhook_trigger_data(node_config):
        """Build webhook trigger data"""
        return {
            'webhook_url': node_config.get('webhook_url', '/webhook/test'),
            'method': node_config.get('method', 'POST'),
            'headers': node_config.get('headers', {}),
            'body': node_config.get('test_payload', {
                'event': 'test_webhook',
                'data': {'test': True},
                'timestamp': timezone.now().isoformat()
            }),
            'received_at': timezone.now().isoformat()
        }

    @staticmethod
    def _build_stage_change_trigger_data(test_data_id, test_data_type, node_config):
        """Build pipeline stage change trigger data"""
        if test_data_id and test_data_type == 'stage_change':
            from pipelines.models import Record
            try:
                record = Record.objects.get(id=test_data_id)
                return {
                    'record_id': str(record.id),
                    'pipeline_id': str(record.pipeline_id),
                    'previous_stage': 'previous_stage',  # Simulated
                    'new_stage': record.data.get('stage', 'unknown'),
                    'changed_at': timezone.now().isoformat()
                }
            except:
                pass

        return {
            'pipeline_id': node_config.get('pipeline_id'),
            'previous_stage': 'stage_1',
            'new_stage': 'stage_2',
            'changed_at': timezone.now().isoformat()
        }

    @staticmethod
    def _build_workflow_completed_trigger_data(test_data_id, test_data_type):
        """Build workflow completed trigger data"""
        if test_data_id and test_data_type == 'workflow_execution':
            from workflows.models import WorkflowExecution
            try:
                execution = WorkflowExecution.objects.get(id=test_data_id)
                return {
                    'execution_id': str(execution.id),
                    'workflow_id': str(execution.workflow.id),
                    'workflow_name': execution.workflow.name,
                    'status': execution.status,
                    'completed_at': execution.completed_at.isoformat() if execution.completed_at else timezone.now().isoformat()
                }
            except:
                pass

        return {
            'workflow_name': 'Test Workflow',
            'status': 'success',
            'completed_at': timezone.now().isoformat()
        }

    @staticmethod
    def _build_record_context(test_record_id):
        """Build record context for action nodes"""
        from pipelines.models import Record
        try:
            record = Record.objects.get(id=test_record_id, is_deleted=False)
            return {
                'id': str(record.id),
                'pipeline_id': str(record.pipeline_id),
                'data': record.data or {},
                'created_at': record.created_at.isoformat(),
                'updated_at': record.updated_at.isoformat()
            }
        except Record.DoesNotExist:
            return None

    @staticmethod
    def _execute_processor_thread(processor, node_config, context):
        """Execute processor in isolated thread with its own event loop"""
        import asyncio
        import time
        from rest_framework.response import Response

        start_time = time.time()

        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            logger.info(f"Executing processor in thread: {processor.__class__.__name__}")

            # Run the async processor in the new loop
            result = loop.run_until_complete(processor.process(node_config, context))

            logger.info(f"Processor executed successfully: {processor.__class__.__name__}")

        except Exception as e:
            logger.error(f"Processor execution failed: {e}", exc_info=True)
            result = {
                'success': False,
                'error': str(e),
                'traceback': str(e.__class__.__name__)
            }
        finally:
            # Clean up the loop
            try:
                loop.close()
            except:
                pass

        execution_time = (time.time() - start_time) * 1000

        # Return response with full result data
        response_data = {
            'status': 'success',
            'execution_time': execution_time,
        }

        # If the processor returned a dict result, spread it into the response
        if isinstance(result, dict):
            response_data['output'] = result
        else:
            response_data['output'] = {'result': result}

        return Response(response_data)