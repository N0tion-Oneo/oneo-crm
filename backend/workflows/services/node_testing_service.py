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
                    node_type, node_config, test_data_id, test_data_type, request
                )
                context['trigger_data'] = trigger_data

            # For action nodes, try to get a test record from configured pipeline
            else:
                test_record = NodeTestingService._get_test_record_from_config(node_config, test_data_id, test_data_type)
                if test_record:
                    context['record'] = test_record

            # Wrap node_config in the structure expected by execute()
            # The execute method expects {'data': {'config': {...}}}
            wrapped_node_config = {
                'id': None,  # No ID in test mode
                'type': node_type,
                'data': {
                    'config': node_config  # This is the actual configuration
                }
            }

            # Execute the processor using async_to_sync to avoid fork() issues on macOS
            from asgiref.sync import async_to_sync
            import time

            start_time = time.time()

            try:
                # Use execute() method if available (AsyncNodeProcessor), otherwise use process()
                if hasattr(processor, 'execute'):
                    result = async_to_sync(processor.execute)(wrapped_node_config, context)
                else:
                    result = async_to_sync(processor.process)(wrapped_node_config, context)

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

            except asyncio.TimeoutError:
                logger.error("Node test execution timed out")
                return Response({
                    'status': 'error',
                    'error': 'Test execution timed out',
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
    def _build_trigger_data(node_type, node_config, test_data_id, test_data_type, request):
        """Build trigger data based on node type"""
        trigger_data = {}

        if node_type == 'trigger_form_submitted':
            trigger_data = NodeTestingService._build_form_trigger_data(
                node_config, test_data_id, test_data_type
            )

        elif node_type in ['trigger_record_created', 'trigger_record_updated', 'trigger_record_deleted']:
            trigger_data = NodeTestingService._build_record_trigger_data(
                node_type, node_config, test_data_id, test_data_type, request
            )

        elif node_type == 'trigger_email_received':
            trigger_data = NodeTestingService._build_email_trigger_data(node_config, test_data_id, test_data_type)

        elif node_type in ['trigger_linkedin_message', 'trigger_whatsapp_message']:
            trigger_data = NodeTestingService._build_message_trigger_data(
                node_type, node_config, test_data_id, test_data_type
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
    def _build_form_trigger_data(node_config, test_data_id, test_data_type):
        """Build form submission trigger data"""
        pipeline_id = node_config.get('pipeline_id')
        trigger_data = {
            'pipeline_id': pipeline_id,
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
        elif pipeline_id:
            # Try to get a record from the configured pipeline
            from pipelines.models import Record
            try:
                record = Record.objects.filter(pipeline_id=pipeline_id, is_deleted=False).first()
                if record:
                    trigger_data['form_data'] = record.data or {}
                else:
                    trigger_data['form_data'] = {}
            except:
                trigger_data['form_data'] = {}
        else:
            trigger_data['form_data'] = {}

        return trigger_data

    @staticmethod
    def _build_record_trigger_data(node_type, node_config, test_data_id, test_data_type, request):
        """Build record trigger data"""
        # Get pipeline from config - could be pipeline_id or pipeline_ids
        pipeline_id = node_config.get('pipeline_id')
        if not pipeline_id:
            pipeline_ids = node_config.get('pipeline_ids', [])
            pipeline_id = pipeline_ids[0] if pipeline_ids else None

        # Try to get a specific record or any record from the configured pipeline
        record = None
        from pipelines.models import Record

        if test_data_id and test_data_type == 'record':
            try:
                record = Record.objects.get(id=test_data_id, is_deleted=False)
                # Validate record is from configured pipeline if pipeline is specified
                if pipeline_id and str(record.pipeline_id) != str(pipeline_id):
                    record = None  # Record doesn't match configured pipeline
            except Record.DoesNotExist:
                pass

        # If no record yet and we have a pipeline, get any record from it
        if not record and pipeline_id:
            try:
                record = Record.objects.filter(pipeline_id=pipeline_id, is_deleted=False).first()
            except Exception as e:
                logger.error(f"Failed to get record test data: {e}", exc_info=True)
                return {
                    'success': False,
                    'message': f'Error retrieving record data: {str(e)}',
                    'trigger_type': node_type
                }

        if record:
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
    def _build_email_trigger_data(node_config, test_data_id, test_data_type):
        """Build email trigger data"""
        # Get monitor_users from config to filter messages
        monitor_users = node_config.get('monitor_users', [])

        # If no users are configured, don't return any data
        if not monitor_users:
            return {
                'success': False,
                'message': 'No users configured to monitor for emails',
                'trigger_type': 'email_received'
            }

        if test_data_id and test_data_type == 'email':
            from communications.models import Message, UserChannelConnection
            from django.contrib.auth import get_user_model

            User = get_user_model()

            try:
                message = Message.objects.get(id=test_data_id)

                # Check if "all users" is selected or find the message owner
                if monitor_users == 'all' or monitor_users == ['all']:
                    user_match = True
                    # Find who owns this channel via UserChannelConnection
                    user_connection = UserChannelConnection.objects.filter(
                        unipile_account_id=message.channel.unipile_account_id
                    ).first()
                    message_user_id = str(user_connection.user_id) if user_connection else None
                else:
                    # Convert monitor_users to integers for comparison
                    monitor_user_ids = []
                    for monitor_user in monitor_users:
                        if isinstance(monitor_user, dict):
                            user_id = monitor_user.get('user_id')
                            if user_id:
                                monitor_user_ids.append(int(user_id))
                        else:
                            monitor_user_ids.append(int(monitor_user))

                    # Find who owns this channel via UserChannelConnection
                    user_connection = UserChannelConnection.objects.filter(
                        unipile_account_id=message.channel.unipile_account_id,
                        user_id__in=monitor_user_ids
                    ).first()

                    user_match = user_connection is not None
                    message_user_id = str(user_connection.user_id) if user_connection else None

                # Only return the message if it belongs to a monitored user
                if user_match:
                    # Extract proper from field based on direction and metadata
                    from_email = ''
                    from_name = ''
                    if message.direction == 'inbound':
                        # For inbound messages, sender is the contact
                        from_email = message.contact_email or ''

                        # Get sender name from participant
                        if message.sender_participant:
                            from_name = message.sender_participant.name or ''
                    elif message.metadata:
                        # For outbound messages, check metadata for sender info
                        from_field = message.metadata.get('from', {})
                        if isinstance(from_field, dict):
                            from_email = from_field.get('email', '')
                            from_name = from_field.get('name', '')
                        # Fallback to sender_info in metadata
                        if not from_email:
                            sender_info = message.metadata.get('sender_info', {})
                            from_email = sender_info.get('email', '')
                            from_name = sender_info.get('name', '')

                    # If still no from email and we have sender_participant
                    if not from_email and hasattr(message, 'sender_participant') and message.sender_participant:
                        from_email = message.sender_participant.email or ''

                    # Extract proper to field from metadata
                    to_emails = []
                    if message.metadata:
                        to_field = message.metadata.get('to', [])
                        if isinstance(to_field, list):
                            to_emails = [r.get('email', '') for r in to_field if isinstance(r, dict) and r.get('email')]

                    # Format to field
                    to_email = ', '.join(to_emails) if to_emails else ''

                    # Fallback: for inbound messages, use the channel/account owner
                    if not to_email:
                        if message.direction == 'outbound':
                            # For outbound, contact_email might be the recipient
                            to_email = message.contact_email or message.channel.name or 'team@company.com'
                        else:
                            # For inbound, use the channel name
                            to_email = message.channel.name or 'team@company.com'

                    # Extract attachments from metadata
                    attachments = []
                    if message.metadata:
                        attachments = message.metadata.get('attachments', [])

                    # Get connected record if sender participant has one
                    record_data = None
                    if message.sender_participant and message.sender_participant.contact_record_id:
                        from pipelines.models import Record
                        try:
                            record = Record.objects.get(id=message.sender_participant.contact_record_id)
                            record_data = {
                                'id': str(record.id),
                                'pipeline_id': str(record.pipeline_id),
                                'data': record.data,
                                'status': record.status,
                                'title': record.title
                            }
                        except Record.DoesNotExist:
                            pass

                    trigger_data = {
                        'from': from_email,
                        'from_name': from_name,
                        'to': to_email,
                        'subject': message.subject or '',
                        'body': message.content or '',
                        'message_id': str(message.id),
                        'received_at': message.created_at.isoformat(),
                        'user_id': message_user_id,
                        'account_id': message.channel.unipile_account_id,
                        'account_name': message.channel.name,
                        'attachments': attachments
                    }

                    # Include record data if available
                    if record_data:
                        trigger_data['record'] = record_data

                    return trigger_data
            except Exception as e:
                logger.error(f"Failed to get email test data: {e}", exc_info=True)
                return {
                    'success': False,
                    'message': f'Error retrieving email data: {str(e)}',
                    'trigger_type': 'email_received'
                }

        # If no specific test data or monitor_users configured, try to get messages for configured users
        if monitor_users and not test_data_id:
            from communications.models import Message, Channel, UserChannelConnection
            from django.contrib.auth import get_user_model

            User = get_user_model()

            try:
                # Check if "all users" is selected
                if monitor_users == 'all' or monitor_users == ['all']:
                    # Get all user IDs
                    user_ids = list(User.objects.values_list('id', flat=True))
                else:
                    # Get messages for the monitored users
                    # monitor_users can be user IDs or objects with user_id and account_id
                    user_ids = []
                    for monitor_user in monitor_users:
                        if isinstance(monitor_user, dict):
                            user_id = monitor_user.get('user_id')
                            if user_id:
                                user_ids.append(int(user_id))
                        else:
                            user_ids.append(int(monitor_user))

                # Get unipile account IDs for these users
                connections = UserChannelConnection.objects.filter(
                    user_id__in=user_ids,
                    channel_type__in=['email', 'gmail', 'outlook']
                )
                unipile_ids = list(connections.values_list('unipile_account_id', flat=True))

                # Find channels for these unipile accounts
                channels = Channel.objects.filter(
                    unipile_account_id__in=unipile_ids
                )

                if channels.exists():
                    # Get messages from any of these channels
                    message = Message.objects.filter(
                        channel__in=channels,
                        direction='inbound'
                    ).order_by('-created_at').first()

                    if message:
                        # Get the user who owns this channel via UserChannelConnection
                        user_connection = connections.filter(unipile_account_id=message.channel.unipile_account_id).first()
                        user_id = str(user_connection.user_id) if user_connection else None

                        # Get participant name
                        from_name = ''
                        if message.sender_participant:
                            from_name = message.sender_participant.name or ''

                        return {
                            'from': message.contact_email or message.sender_email or '',
                            'from_name': from_name,
                            'to': message.recipient_email or message.channel.name or 'team@company.com',
                            'subject': message.subject or '',
                            'body': message.content or '',
                            'message_id': str(message.id),
                            'received_at': message.created_at.isoformat(),
                            'user_id': user_id,
                            'account_id': message.channel.unipile_account_id,
                            'account_name': message.channel.name,
                            'attachments': []
                        }
            except Exception as e:
                logger.error(f"Failed to get email test data: {e}", exc_info=True)
                return {
                    'success': False,
                    'message': f'Error retrieving email data: {str(e)}',
                    'trigger_type': 'email_received'
                }

        # No test data available - return empty trigger data
        return {
            'success': False,
            'message': 'No email messages found for the configured users',
            'trigger_type': 'email_received'
        }

    @staticmethod
    def _build_message_trigger_data(node_type, node_config, test_data_id, test_data_type):
        """Build LinkedIn/WhatsApp message trigger data"""
        channel_type = 'linkedin' if 'linkedin' in node_type else 'whatsapp'
        monitor_users = node_config.get('monitor_users', [])

        # If no users are configured, don't return any data
        if not monitor_users:
            return {
                'success': False,
                'message': f'No users configured to monitor for {channel_type} messages',
                'trigger_type': f'{channel_type}_message',
                'channel': channel_type
            }

        if test_data_id and test_data_type == channel_type:
            from communications.models import Message, UserChannelConnection
            from django.contrib.auth import get_user_model

            User = get_user_model()

            try:
                message = Message.objects.get(id=test_data_id)
                logger.info(f"Found message {test_data_id} for channel {channel_type}")

                # Check if "all users" is selected or find the message owner (same as email)
                if monitor_users == 'all' or monitor_users == ['all']:
                    user_match = True
                    # Find who owns this channel via UserChannelConnection
                    user_connection = UserChannelConnection.objects.filter(
                        unipile_account_id=message.channel.unipile_account_id
                    ).first()
                    message_user_id = str(user_connection.user_id) if user_connection else None
                else:
                    # Convert monitor_users to integers for comparison (same as email)
                    monitor_user_ids = []
                    for monitor_user in monitor_users:
                        if isinstance(monitor_user, dict):
                            user_id = monitor_user.get('user_id')
                            if user_id:
                                monitor_user_ids.append(int(user_id))
                        else:
                            monitor_user_ids.append(int(monitor_user))

                    # Find who owns this channel via UserChannelConnection
                    user_connection = UserChannelConnection.objects.filter(
                        unipile_account_id=message.channel.unipile_account_id,
                        user_id__in=monitor_user_ids
                    ).first()

                    user_match = user_connection is not None
                    message_user_id = str(user_connection.user_id) if user_connection else None

                # Only return the message if it belongs to a monitored user
                if user_match:
                    logger.info(f"User match found, returning message data")

                    # Get participant information and connected record if available
                    participant_name = ''
                    record_data = None

                    if message.sender_participant:
                        participant_name = message.sender_participant.name or ''

                        # Get connected record if participant has one
                        if message.sender_participant.contact_record_id:
                            from pipelines.models import Record
                            try:
                                record = Record.objects.get(id=message.sender_participant.contact_record_id)
                                record_data = {
                                    'id': str(record.id),
                                    'pipeline_id': str(record.pipeline_id),
                                    'data': record.data,
                                    'status': record.status,
                                    'title': record.title
                                }
                            except Record.DoesNotExist:
                                pass

                    trigger_data = {
                        'from': message.contact_phone or message.contact_email or '',
                        'from_name': participant_name,
                        'message': message.content or '',
                        'message_id': str(message.id),
                        'received_at': message.created_at.isoformat(),
                        'channel': channel_type,
                        'user_id': message_user_id,
                        'account_id': message.channel.unipile_account_id,
                        'account_name': message.channel.name
                    }

                    # Include record data if available
                    if record_data:
                        trigger_data['record'] = record_data

                    return trigger_data
                else:
                    logger.warning(f"No user match found for message {test_data_id}. Monitor users: {monitor_user_ids}")
            except Exception as e:
                logger.error(f"Failed to get {channel_type} test data: {e}", exc_info=True)
                return {
                    'success': False,
                    'message': f'Error retrieving email data: {str(e)}',
                    'trigger_type': 'email_received'
                }

        # If no specific test data or monitor_users configured, try to get messages for configured users
        if monitor_users and not test_data_id:
            from communications.models import Message, Channel, UserChannelConnection
            from django.contrib.auth import get_user_model

            User = get_user_model()

            try:
                # Check if "all users" is selected
                if monitor_users == 'all' or monitor_users == ['all']:
                    # Get all user IDs
                    user_ids = list(User.objects.values_list('id', flat=True))
                else:
                    # Get messages for the monitored users
                    user_ids = []
                    for monitor_user in monitor_users:
                        if isinstance(monitor_user, dict):
                            user_id = monitor_user.get('user_id')
                            if user_id:
                                user_ids.append(int(user_id))
                        else:
                            user_ids.append(int(monitor_user))

                # Get unipile account IDs for these users
                connections = UserChannelConnection.objects.filter(
                    user_id__in=user_ids,
                    channel_type=channel_type
                )
                unipile_ids = list(connections.values_list('unipile_account_id', flat=True))

                # Find channels for these unipile accounts
                channels = Channel.objects.filter(
                    unipile_account_id__in=unipile_ids
                )

                if channels.exists():
                    # Get messages from any of these channels
                    message = Message.objects.filter(
                        channel__in=channels,
                        direction='inbound'
                    ).order_by('-created_at').first()

                    if message:
                        # Get the user who owns this channel via UserChannelConnection
                        user_connection = connections.filter(unipile_account_id=message.channel.unipile_account_id).first()
                        user_id = str(user_connection.user_id) if user_connection else None

                        # Get participant name
                        from_name = ''
                        if message.sender_participant:
                            from_name = message.sender_participant.name or ''

                        return {
                            'from': message.contact_phone or message.contact_email or '',
                            'from_name': from_name,
                            'message': message.content or '',
                            'message_id': str(message.id),
                            'received_at': message.created_at.isoformat(),
                            'channel': channel_type,
                            'user_id': user_id,
                            'account_id': message.channel.unipile_account_id,
                            'account_name': message.channel.name
                        }
            except Exception as e:
                logger.error(f"Failed to get message test data: {e}", exc_info=True)
                return {
                    'success': False,
                    'message': f'Error retrieving message data: {str(e)}',
                    'trigger_type': channel_type
                }

        # No test data available - return empty trigger data
        return {
            'success': False,
            'message': f'No {channel_type} messages found for the configured users',
            'trigger_type': f'{channel_type}_message',
            'channel': channel_type
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
            except Exception as e:
                logger.error(f"Failed to get schedule test data: {e}", exc_info=True)
                return {
                    'success': False,
                    'message': f'Error retrieving schedule data: {str(e)}',
                    'trigger_type': 'scheduled'
                }

        # No test data available
        return {
            'success': False,
            'message': 'No workflow schedules found',
            'trigger_type': 'scheduled'
        }

    @staticmethod
    def _build_webhook_trigger_data(node_config):
        """Build webhook trigger data"""
        # Webhook triggers need actual webhook data - can't be simulated
        return {
            'success': False,
            'message': 'Webhook triggers require actual webhook data. Configure and send a webhook to test.',
            'trigger_type': 'webhook',
            'webhook_url': node_config.get('webhook_url', ''),
            'method': node_config.get('method', 'POST')
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
            except Exception as e:
                logger.error(f"Failed to get stage change test data: {e}", exc_info=True)
                return {
                    'success': False,
                    'message': f'Error retrieving stage change data: {str(e)}',
                    'trigger_type': 'pipeline_stage_changed'
                }

        # No test data available
        pipeline_id = node_config.get('pipeline_id')
        if pipeline_id:
            # Try to find a record with stage data
            from pipelines.models import Record
            try:
                record = Record.objects.filter(
                    pipeline_id=pipeline_id,
                    is_deleted=False
                ).exclude(data__stage__isnull=True).first()

                if record and record.data.get('stage'):
                    return {
                        'record_id': str(record.id),
                        'pipeline_id': str(record.pipeline_id),
                        'previous_stage': record.data.get('stage'),  # Would be same in test
                        'new_stage': record.data.get('stage'),
                        'changed_at': timezone.now().isoformat(),
                        'message': 'Using existing record stage for test'
                    }
            except Exception as e:
                logger.error(f"Failed to get stage change test data: {e}", exc_info=True)
                return {
                    'success': False,
                    'message': f'Error retrieving stage change data: {str(e)}',
                    'trigger_type': 'pipeline_stage_changed'
                }

        return {
            'success': False,
            'message': 'No records with stage data found in the configured pipeline',
            'trigger_type': 'pipeline_stage_changed',
            'pipeline_id': pipeline_id
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
            except Exception as e:
                logger.error(f"Failed to get workflow execution test data: {e}", exc_info=True)
                return {
                    'success': False,
                    'message': f'Error retrieving workflow execution data: {str(e)}',
                    'trigger_type': 'workflow_completed'
                }

        # No test data available
        return {
            'success': False,
            'message': 'No workflow executions found',
            'trigger_type': 'workflow_completed'
        }

    @staticmethod
    def _get_test_record_from_config(node_config, test_data_id, test_data_type):
        """Get test record from node configuration or test data"""
        # Extract pipeline from config - could be pipeline_id, pipeline_ids, or target_pipeline_id
        pipeline_id = node_config.get('pipeline_id') or node_config.get('target_pipeline_id')
        if not pipeline_id:
            pipeline_ids = node_config.get('pipeline_ids', [])
            pipeline_id = pipeline_ids[0] if pipeline_ids else None

        from pipelines.models import Record

        # First try to use specific test data if provided and it matches the pipeline
        if test_data_id and test_data_type == 'record':
            try:
                record = Record.objects.get(id=test_data_id, is_deleted=False)
                # If pipeline is configured, validate the record matches
                if not pipeline_id or str(record.pipeline_id) == str(pipeline_id):
                    return {
                        'id': str(record.id),
                        'pipeline_id': str(record.pipeline_id),
                        'data': record.data or {},
                        'created_at': record.created_at.isoformat(),
                        'updated_at': record.updated_at.isoformat()
                    }
            except Record.DoesNotExist:
                pass

        # If no specific record or it doesn't match, get any record from configured pipeline
        if pipeline_id:
            try:
                record = Record.objects.filter(pipeline_id=pipeline_id, is_deleted=False).first()
                if record:
                    return {
                        'id': str(record.id),
                        'pipeline_id': str(record.pipeline_id),
                        'data': record.data or {},
                        'created_at': record.created_at.isoformat(),
                        'updated_at': record.updated_at.isoformat()
                    }
            except Exception as e:
                logger.error(f"Failed to get test record: {e}", exc_info=True)
                return None

        return None

