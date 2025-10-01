"""
Service for fetching test data for workflow nodes
"""
import logging
import json
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status
from django_tenants.utils import get_tenant

logger = logging.getLogger(__name__)


class TestDataService:
    """Service for managing test data retrieval for workflow nodes"""

    @staticmethod
    def get_record_display_name(record):
        """Helper to get a display name for a record"""
        if not record.data:
            return f"Record {str(record.id)[:8]}"

        # Try common field names
        for field in ['name', 'title', 'label', 'subject', 'email', 'company']:
            if field in record.data and record.data[field]:
                return str(record.data[field])

        # Try combining first and last name
        if 'first_name' in record.data and 'last_name' in record.data:
            return f"{record.data.get('first_name', '')} {record.data.get('last_name', '')}".strip()

        # Fallback to ID
        return f"Record {str(record.id)[:8]}"

    @staticmethod
    def expand_relation_fields(record, depth=2, _visited=None):
        """
        Recursively expand relation fields to support multi-hop traversal
        Example: company.jobs[0].interviews[0].candidates

        Args:
            record: Record instance to expand
            depth: Maximum depth for relation expansion (default 2 for performance)
            _visited: Set of visited record IDs to prevent circular references

        Returns:
            dict: Record data with expanded relation fields
        """
        from pipelines.models import Record
        from pipelines.relation_field_handler import RelationFieldHandler

        if _visited is None:
            _visited = set()

        # Prevent infinite loops
        if record.id in _visited or depth <= 0:
            return record.data or {}

        _visited.add(record.id)

        # Start with the record's data
        expanded_data = dict(record.data or {})

        # Get all relation fields for this pipeline
        relation_fields = record.pipeline.fields.filter(
            field_type='relation',
            is_deleted=False
        )

        for field in relation_fields:
            handler = RelationFieldHandler(field)
            relationships = handler.get_bidirectional_relationships(record, include_deleted=False)

            if not relationships:
                # Keep original value or set empty structure
                if field.slug not in expanded_data:
                    expanded_data[field.slug] = [] if handler.allow_multiple else None
                continue

            expanded_relations = []

            for rel in relationships:
                # Determine target record
                if rel.source_record_id == record.id:
                    target_record_id = rel.target_record_id
                    target_pipeline_id = rel.target_pipeline_id
                else:
                    target_record_id = rel.source_record_id
                    target_pipeline_id = rel.source_pipeline_id

                try:
                    # Get target record
                    target_record = Record.objects.select_related('pipeline').get(
                        id=target_record_id,
                        pipeline_id=target_pipeline_id,
                        is_deleted=False
                    )

                    # Get display value
                    display_value = target_record.data.get(handler.display_field) if target_record.data else None
                    if not display_value:
                        alt_field = handler.display_field.lower().replace(' ', '_')
                        display_value = target_record.data.get(alt_field) if target_record.data else None
                    if not display_value:
                        display_value = target_record.title or f"Record #{target_record_id}"

                    # Recursively expand nested relations
                    nested_data = TestDataService.expand_relation_fields(
                        target_record,
                        depth=depth - 1,
                        _visited=_visited.copy()
                    )

                    # Build expanded relation object
                    expanded_relation = {
                        'id': target_record_id,
                        'display_value': display_value,
                        'data': nested_data,  # Nested data for multi-hop traversal
                        'pipeline_id': str(target_pipeline_id),
                        'title': target_record.title
                    }

                    expanded_relations.append(expanded_relation)

                except Record.DoesNotExist:
                    # Skip missing records
                    continue

            # Store based on cardinality
            if handler.allow_multiple:
                expanded_data[field.slug] = expanded_relations
            else:
                expanded_data[field.slug] = expanded_relations[0] if expanded_relations else None

        return expanded_data

    @staticmethod
    def parse_node_config(request):
        """Parse node config from request parameters"""
        pipeline_id = request.query_params.get('pipeline_id')
        node_config_str = request.query_params.get('node_config')
        node_config = None

        if node_config_str:
            try:
                node_config = json.loads(node_config_str)
                # Check both pipeline_id and pipeline_ids (some triggers use plural)
                config_pipeline_id = node_config.get('pipeline_id')
                if not config_pipeline_id:
                    # Try pipeline_ids array (used by record triggers)
                    pipeline_ids = node_config.get('pipeline_ids', [])
                    if pipeline_ids and len(pipeline_ids) > 0:
                        config_pipeline_id = pipeline_ids[0]
                        logger.info(f"Using first pipeline_id from pipeline_ids array: {config_pipeline_id}")

                if config_pipeline_id:
                    pipeline_id = config_pipeline_id
                    logger.info(f"Using pipeline_id from node_config: {pipeline_id}")
                logger.info(f"Parsed node_config: {node_config}")
            except (json.JSONDecodeError, AttributeError) as e:
                logger.error(f"Failed to parse node_config: {e}, raw: {node_config_str[:200]}")

        return pipeline_id, node_config

    @classmethod
    def get_test_records(cls, request):
        """Get recent records for testing workflow nodes"""
        pipeline_id = request.query_params.get('pipeline_id')
        node_type = request.query_params.get('node_type')

        logger.info(f"get_test_records called with pipeline_id={pipeline_id}, node_type={node_type}")

        if not pipeline_id:
            return Response({
                'records': [],
                'message': 'No pipeline selected'
            })

        try:
            from pipelines.models import Record
            from django.db import connection

            # Get current tenant schema
            schema_name = connection.schema_name
            logger.info(f"Fetching test records for pipeline {pipeline_id} in schema {schema_name}")

            # Fetch recent records from the pipeline
            records = Record.objects.filter(
                pipeline_id=pipeline_id,
                is_deleted=False
            ).order_by('-created_at')[:10]

            logger.info(f"Found {records.count()} records for pipeline {pipeline_id}")

            # Format records for the dropdown
            formatted_records = []
            for record in records:
                # Get a title for the record
                title = record.get_title() if hasattr(record, 'get_title') else None
                if not title:
                    # Try to construct a title from common fields
                    data = record.data or {}
                    if data.get('first_name') and data.get('last_name'):
                        title = f"{data['first_name']} {data['last_name']}"
                    elif data.get('name'):
                        title = data['name']
                    elif data.get('email'):
                        title = data['email']
                    else:
                        title = f"Record {str(record.id)[:8]}"

                formatted_records.append({
                    'id': str(record.id),
                    'title': title,
                    'created_at': record.created_at.isoformat(),
                    'updated_at': record.updated_at.isoformat(),
                    'preview': {
                        k: v for k, v in (record.data or {}).items()
                        if k in ['first_name', 'last_name', 'email', 'company', 'phone']
                    }
                })

            return Response({
                'records': formatted_records,
                'total': len(formatted_records)
            })

        except Exception as e:
            import traceback
            logger.error(f"Failed to fetch test records: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response({
                'records': [],
                'total': 0,
                'error': f'Unable to fetch records from pipeline: {str(e)}'
            })

    @classmethod
    def get_test_data(cls, request):
        """Get recent test data based on trigger type - uses real data from system"""
        current_tenant = get_tenant(request)
        logger.info(f"get_test_data called in tenant: {current_tenant.schema_name if current_tenant else 'No tenant'}")

        node_type = request.query_params.get('node_type', '').lower()
        pipeline_id, node_config = cls.parse_node_config(request)

        logger.info(f"get_test_data called with node_type={node_type}, pipeline_id={pipeline_id}, has_config={bool(node_config)}")

        try:
            # Email triggers
            if 'email' in node_type:
                return cls._get_email_test_data(node_config)

            # LinkedIn/WhatsApp triggers
            elif 'linkedin' in node_type or 'whatsapp' in node_type:
                return cls._get_messaging_test_data(node_type, node_config)

            # Form triggers
            elif 'form' in node_type:
                return cls._get_form_test_data(pipeline_id, node_config, request)

            # Record triggers
            elif 'record' in node_type:
                return cls._get_record_test_data(pipeline_id)

            # Scheduled triggers
            elif 'scheduled' in node_type:
                return cls._get_schedule_test_data()

            # Date reached triggers
            elif 'date_reached' in node_type:
                return cls._get_date_trigger_test_data(pipeline_id)

            # Pipeline stage triggers
            elif 'pipeline_stage' in node_type:
                return cls._get_stage_change_test_data(pipeline_id)

            # Workflow completed triggers
            elif 'workflow_completed' in node_type:
                return cls._get_workflow_execution_test_data()

            # Condition met triggers
            elif 'condition_met' in node_type:
                return cls._get_condition_test_data(pipeline_id)

            # Webhook triggers
            elif 'webhook' in node_type:
                return cls._get_webhook_test_data()

            # Manual triggers
            elif 'manual' in node_type:
                return Response({
                    'data': [],
                    'data_type': 'manual',
                    'message': 'Manual triggers are activated by users. No test data needed.'
                })

            else:
                return Response({
                    'data': [],
                    'data_type': 'unknown',
                    'message': f'No test data available for trigger type: {node_type}'
                })

        except Exception as e:
            logger.error(f"Failed to fetch test data: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response({
                'data': [],
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @staticmethod
    def _get_email_test_data(node_config):
        """Get email test data"""
        from communications.models import Message, Channel, UserChannelConnection
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Check monitor_users configuration
        monitor_users = node_config.get('monitor_users', []) if node_config else []

        # If no users are configured, return empty
        if not monitor_users:
            return Response({
                'data': [],
                'data_type': 'email',
                'message': 'No users configured to monitor for emails'
            })

        # Check if "all users" is selected
        if monitor_users == 'all' or monitor_users == ['all']:
            # Get all user IDs
            user_ids = list(User.objects.values_list('id', flat=True))
        else:
            # Extract user IDs from monitor_users configuration
            # Convert to integers to match database and frontend
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

        # Get channels for these unipile accounts
        channels = Channel.objects.filter(
            unipile_account_id__in=unipile_ids
        ).values_list('id', flat=True)

        # Filter messages by the channels of monitored users
        messages = Message.objects.filter(
            channel_id__in=channels,
            direction='inbound'
        ).select_related('channel', 'conversation', 'sender_participant').order_by('-created_at')[:10]

        formatted_data = []
        for msg in messages:
            # Get sender name from participant if available
            sender_name = ''
            if msg.sender_participant:
                sender_name = msg.sender_participant.name or ''

            # Build display title including name if available
            if sender_name and msg.contact_email:
                title = f"{sender_name} ({msg.contact_email})"
            elif sender_name:
                title = sender_name
            elif msg.contact_email:
                title = msg.contact_email
            else:
                title = "Unknown sender"

            # Add subject if available
            if msg.subject:
                title = f"{title} - {msg.subject}"

            formatted_data.append({
                'id': str(msg.id),
                'type': 'email',
                'title': title,
                'created_at': msg.created_at.isoformat(),
                'preview': {
                    'from': msg.contact_email,
                    'from_name': sender_name,
                    'subject': msg.subject,
                    'body': msg.content[:200] if msg.content else '',
                    'channel': msg.channel.name if msg.channel else None
                }
            })

        return Response({
            'data': formatted_data,
            'data_type': 'email',
            'total': len(formatted_data)
        })

    @staticmethod
    def _get_messaging_test_data(node_type, node_config):
        """Get LinkedIn/WhatsApp test data"""
        from communications.models import Message, Channel, UserChannelConnection
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Check monitor_users configuration
        monitor_users = node_config.get('monitor_users', []) if node_config else []

        # If no users are configured, return empty
        if not monitor_users:
            channel_type = 'linkedin' if 'linkedin' in node_type else 'whatsapp'
            return Response({
                'data': [],
                'data_type': channel_type,
                'message': f'No users configured to monitor for {channel_type} messages'
            })

        # Check if "all users" is selected
        if monitor_users == 'all' or monitor_users == ['all']:
            # Get all user IDs
            user_ids = list(User.objects.values_list('id', flat=True))
        else:
            # Extract user IDs from monitor_users configuration
            # Convert to integers to match database and frontend
            user_ids = []
            for monitor_user in monitor_users:
                if isinstance(monitor_user, dict):
                    user_id = monitor_user.get('user_id')
                    if user_id:
                        user_ids.append(int(user_id))
                else:
                    user_ids.append(int(monitor_user))

        channel_type = 'linkedin' if 'linkedin' in node_type else 'whatsapp'

        # Get unipile account IDs for these users
        connections = UserChannelConnection.objects.filter(
            user_id__in=user_ids,
            channel_type=channel_type
        )
        unipile_ids = list(connections.values_list('unipile_account_id', flat=True))

        # Get channels for these unipile accounts
        channels = Channel.objects.filter(
            unipile_account_id__in=unipile_ids
        ).values_list('id', flat=True)

        # Filter messages by the channels of monitored users
        messages = Message.objects.filter(
            channel_id__in=channels,
            direction='inbound'
        ).select_related('channel', 'conversation', 'sender_participant').order_by('-created_at')[:10]

        formatted_data = []
        for msg in messages:
            # Get sender name from participant if available
            sender_name = ''
            if msg.sender_participant:
                sender_name = msg.sender_participant.name or ''

            # Build display title including name if available
            contact = msg.contact_phone or msg.contact_email
            if sender_name and contact:
                title = f"{sender_name} ({contact})"
            elif sender_name:
                title = sender_name
            elif contact:
                title = contact
            else:
                title = "Unknown sender"

            formatted_data.append({
                'id': str(msg.id),
                'type': channel_type,
                'title': title,
                'created_at': msg.created_at.isoformat(),
                'preview': {
                    'from': msg.contact_phone or msg.contact_email,
                    'from_name': sender_name,
                    'content': msg.content[:200] if msg.content else '',
                    'channel': msg.channel.name if msg.channel else None
                }
            })

        return Response({
            'data': formatted_data,
            'data_type': channel_type,
            'total': len(formatted_data)
        })

    @classmethod
    def _get_form_test_data(cls, pipeline_id, node_config, request):
        """Get form submission test data"""
        if not pipeline_id:
            return Response({
                'data': [],
                'data_type': 'form_submission',
                'message': 'Pipeline ID required for form triggers'
            })

        from pipelines.models import FormSubmission, Record

        current_tenant = get_tenant(request)
        logger.info(f"Querying FormSubmissions in tenant: {current_tenant.schema_name if current_tenant else 'No tenant'}")

        # Get recent form submissions
        form_submissions_qs = FormSubmission.objects.filter(
            record__pipeline_id=pipeline_id
        )

        # Filter by form_mode and stage if provided
        if node_config:
            form_mode = node_config.get('mode') or node_config.get('form_mode')
            stage = node_config.get('stage') or node_config.get('form_stage')

            if form_mode:
                form_submissions_qs = form_submissions_qs.filter(form_mode=form_mode)

            if stage:
                try:
                    form_submissions_qs = form_submissions_qs.filter(
                        form_config__stage=stage
                    )
                except Exception as e:
                    logger.warning(f"Could not filter by form_config__stage: {e}")

        form_submissions = form_submissions_qs.select_related(
            'record', 'record__pipeline', 'submitted_by'
        ).order_by('-created_at')[:10]

        formatted_data = []
        for submission in form_submissions:
            preview_data = submission.submitted_data or {}
            title = (
                f"{submission.form_name} - {submission.created_at.strftime('%Y-%m-%d %H:%M')}" if submission.form_name
                else f"Form Submission - {submission.created_at.strftime('%Y-%m-%d %H:%M')}"
            )

            form_stage = submission.form_config.get('stage') if submission.form_config else None

            formatted_data.append({
                'id': str(submission.id),
                'type': 'form_submission',
                'title': title,
                'created_at': submission.created_at.isoformat(),
                'preview': {
                    'form_name': submission.form_name,
                    'form_id': submission.form_id,
                    'form_mode': submission.form_mode,
                    'form_stage': form_stage,
                    'submission_source': submission.submission_source,
                    'is_anonymous': submission.is_anonymous,
                    'submitted_by': submission.submitted_by.email if submission.submitted_by else 'Anonymous',
                    'fields': list(preview_data.keys())[:5],
                    'submitted_data': preview_data  # Include full data for frontend preview
                },
                'record_id': str(submission.record.id)
            })

        # If no form submissions, fallback to records
        if not formatted_data:
            records = Record.objects.filter(
                pipeline_id=pipeline_id,
                is_deleted=False
            ).order_by('-created_at')[:5]

            for record in records:
                data = record.data or {}
                formatted_data.append({
                    'id': str(record.id),
                    'type': 'record_as_form',
                    'title': f"Record (as form data) - {record.created_at.strftime('%Y-%m-%d %H:%M')}",
                    'created_at': record.created_at.isoformat(),
                    'preview': {
                        'form_name': f"{record.pipeline.name} Form",
                        'form_id': f"pipeline_{pipeline_id}_default",
                        'fields': list(data.keys())[:5]
                    }
                })

        return Response({
            'data': formatted_data,
            'data_type': 'record_as_form' if formatted_data and formatted_data[0]['type'] == 'record_as_form' else 'form_submission',
            'total': len(formatted_data)
        })

    @classmethod
    def _get_record_test_data(cls, pipeline_id):
        """Get record test data"""
        if not pipeline_id:
            return Response({
                'data': [],
                'data_type': 'record',
                'message': 'Pipeline ID required for record-based triggers'
            })

        from pipelines.models import Record

        records = Record.objects.filter(
            pipeline_id=pipeline_id,
            is_deleted=False
        ).order_by('-created_at')[:10]

        formatted_data = []
        for record in records:
            # Expand relation fields recursively for multi-hop traversal support
            expanded_data = cls.expand_relation_fields(record, depth=2)

            title = (
                expanded_data.get('name') or
                f"{expanded_data.get('first_name', '')} {expanded_data.get('last_name', '')}".strip() or
                expanded_data.get('email') or
                f"Record {str(record.id)[:8]}"
            )

            formatted_data.append({
                'id': str(record.id),
                'type': 'record',
                'title': title,
                'pipeline_id': str(record.pipeline_id),
                'created_at': record.created_at.isoformat(),
                'updated_at': record.updated_at.isoformat() if record.updated_at else None,
                'created_by': str(record.created_by_id) if hasattr(record, 'created_by_id') and record.created_by_id else None,
                'updated_by': str(record.updated_by_id) if hasattr(record, 'updated_by_id') and record.updated_by_id else None,
                'data': expanded_data,  # Expanded data with nested relations for multi-hop traversal
                'preview': {
                    k: v for k, v in expanded_data.items()
                    if k in ['name', 'first_name', 'last_name', 'email', 'company']
                }
            })

        return Response({
            'data': formatted_data,
            'data_type': 'record',
            'total': len(formatted_data)
        })

    @staticmethod
    def _get_schedule_test_data():
        """Get schedule test data"""
        from workflows.models import WorkflowSchedule

        schedules = WorkflowSchedule.objects.filter(
            is_active=True
        ).select_related('workflow').order_by('-next_run')[:10]

        formatted_data = []
        for schedule in schedules:
            formatted_data.append({
                'id': str(schedule.id),
                'type': 'schedule',
                'title': f"{schedule.workflow.name} - {schedule.cron_expression}",
                'created_at': schedule.created_at.isoformat() if hasattr(schedule, 'created_at') else None,
                'preview': {
                    'workflow_name': schedule.workflow.name,
                    'next_run': schedule.next_run.isoformat() if schedule.next_run else None,
                    'cron_expression': schedule.cron_expression,
                    'timezone': str(schedule.timezone) if hasattr(schedule, 'timezone') else 'UTC'
                }
            })

        return Response({
            'data': formatted_data,
            'data_type': 'schedule',
            'total': len(formatted_data)
        })

    @classmethod
    def _get_date_trigger_test_data(cls, pipeline_id):
        """Get date trigger test data"""
        from datetime import datetime, timedelta
        from django.utils import timezone

        # If no pipeline, provide static date options
        if not pipeline_id:
            now = timezone.now()
            today_noon = now.replace(hour=12, minute=0, second=0, microsecond=0)
            tomorrow = now + timedelta(days=1)
            tomorrow_9am = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            next_monday = now + timedelta(days=(7 - now.weekday()))
            next_monday_10am = next_monday.replace(hour=10, minute=0, second=0, microsecond=0)

            # Calculate end of month
            if now.month == 12:
                end_of_month = now.replace(year=now.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_of_month = now.replace(month=now.month + 1, day=1) - timedelta(days=1)
            end_of_month = end_of_month.replace(hour=23, minute=59, second=59)

            static_dates = [
                {
                    'id': 'static_today_noon',
                    'type': 'date_trigger_static',
                    'title': 'Today at noon',
                    'created_at': now.isoformat(),
                    'preview': {
                        'target_date': today_noon.isoformat(),
                        'description': f'{today_noon.strftime("%B %d, %Y at %I:%M %p")}',
                        'mode': 'static'
                    }
                },
                {
                    'id': 'static_tomorrow_9am',
                    'type': 'date_trigger_static',
                    'title': 'Tomorrow at 9 AM',
                    'created_at': now.isoformat(),
                    'preview': {
                        'target_date': tomorrow_9am.isoformat(),
                        'description': f'{tomorrow_9am.strftime("%B %d, %Y at %I:%M %p")}',
                        'mode': 'static'
                    }
                },
                {
                    'id': 'static_next_monday',
                    'type': 'date_trigger_static',
                    'title': 'Next Monday at 10 AM',
                    'created_at': now.isoformat(),
                    'preview': {
                        'target_date': next_monday_10am.isoformat(),
                        'description': f'{next_monday_10am.strftime("%B %d, %Y at %I:%M %p")}',
                        'mode': 'static'
                    }
                },
                {
                    'id': 'static_end_of_month',
                    'type': 'date_trigger_static',
                    'title': 'End of this month',
                    'created_at': now.isoformat(),
                    'preview': {
                        'target_date': end_of_month.isoformat(),
                        'description': f'{end_of_month.strftime("%B %d, %Y at %I:%M %p")}',
                        'mode': 'static'
                    }
                },
                {
                    'id': 'static_custom',
                    'type': 'date_trigger_static',
                    'title': 'Custom date/time',
                    'created_at': now.isoformat(),
                    'preview': {
                        'target_date': now.isoformat(),
                        'description': 'Enter your own date and time',
                        'mode': 'static',
                        'custom': True
                    }
                }
            ]

            return Response({
                'data': static_dates,
                'data_type': 'date_trigger',
                'total': len(static_dates),
                'message': 'Static date options for testing. Select a pipeline to see records with date fields.'
            })

        # With pipeline, show records with date fields (existing behavior)
        from pipelines.models import Record

        records = []
        all_records = Record.objects.filter(
            pipeline_id=pipeline_id,
            is_deleted=False
        ).order_by('-updated_at')[:50]

        for record in all_records:
            if record.data:
                date_fields = {}
                for key, value in record.data.items():
                    if 'date' in key.lower() or isinstance(value, str) and any(
                        pattern in value for pattern in ['2024', '2025', '2023', '-', '/']
                    ):
                        date_fields[key] = value

                if date_fields and len(records) < 10:
                    records.append({
                        'id': str(record.id),
                        'type': 'date_trigger',
                        'title': f"Record with date fields: {cls.get_record_display_name(record)}",
                        'created_at': record.created_at.isoformat(),
                        'preview': {
                            'record_name': cls.get_record_display_name(record),
                            'date_fields': date_fields,
                            'mode': 'dynamic'
                        }
                    })

        return Response({
            'data': records,
            'data_type': 'date_trigger',
            'total': len(records),
            'message': 'Records with date fields found' if records else 'No records with date fields found in this pipeline'
        })

    @classmethod
    def _get_stage_change_test_data(cls, pipeline_id):
        """Get stage change test data"""
        if not pipeline_id:
            return Response({
                'data': [],
                'data_type': 'stage_change',
                'message': 'Please select a pipeline to see records with stage information'
            })

        from pipelines.models import Record

        records = Record.objects.filter(
            pipeline_id=pipeline_id,
            is_deleted=False
        ).order_by('-updated_at')[:20]

        formatted_data = []
        for record in records:
            if record.data and 'stage' in record.data:
                formatted_data.append({
                    'id': str(record.id),
                    'type': 'stage_change',
                    'title': f"{cls.get_record_display_name(record)} - Stage: {record.data.get('stage', 'Unknown')}",
                    'created_at': record.created_at.isoformat(),
                    'preview': {
                        'current_stage': record.data.get('stage'),
                        'record_name': cls.get_record_display_name(record),
                        'pipeline': record.pipeline.name if hasattr(record, 'pipeline') else None
                    }
                })
                if len(formatted_data) >= 10:
                    break

        return Response({
            'data': formatted_data,
            'data_type': 'stage_change',
            'total': len(formatted_data),
            'message': 'Records with stage information found' if formatted_data else 'No records with stage field found in this pipeline'
        })

    @staticmethod
    def _get_workflow_execution_test_data():
        """Get workflow execution test data"""
        from workflows.models import WorkflowExecution

        executions = WorkflowExecution.objects.filter(
            status='success'
        ).select_related('workflow').order_by('-completed_at')[:10]

        formatted_data = []
        for execution in executions:
            formatted_data.append({
                'id': str(execution.id),
                'type': 'workflow_execution',
                'title': f"{execution.workflow.name} - Completed {execution.completed_at.strftime('%Y-%m-%d %H:%M') if execution.completed_at else 'Unknown'}",
                'created_at': execution.started_at.isoformat() if execution.started_at else None,
                'preview': {
                    'workflow_name': execution.workflow.name,
                    'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                    'status': execution.status,
                    'execution_time': str(execution.completed_at - execution.started_at) if execution.completed_at and execution.started_at else None
                }
            })

        return Response({
            'data': formatted_data,
            'data_type': 'workflow_execution',
            'total': len(formatted_data)
        })

    @classmethod
    def _get_condition_test_data(cls, pipeline_id):
        """Get condition test data"""
        if not pipeline_id:
            return Response({
                'data': [],
                'data_type': 'condition_test',
                'message': 'Please select a pipeline to see records for condition testing'
            })

        from pipelines.models import Record

        records = Record.objects.filter(
            pipeline_id=pipeline_id,
            is_deleted=False
        ).order_by('-updated_at')[:10]

        formatted_data = []
        for record in records:
            formatted_data.append({
                'id': str(record.id),
                'type': 'condition_test',
                'title': f"Test conditions with: {cls.get_record_display_name(record)}",
                'created_at': record.created_at.isoformat(),
                'preview': {
                    'record_name': cls.get_record_display_name(record),
                    'sample_fields': dict(list(record.data.items())[:5]) if record.data else {}
                }
            })

        return Response({
            'data': formatted_data,
            'data_type': 'condition_test',
            'total': len(formatted_data),
            'message': 'Select a record to test condition evaluation' if formatted_data else 'No records found in this pipeline'
        })

    @staticmethod
    def _get_webhook_test_data():
        """Get webhook test data"""
        return Response({
            'data': [],
            'data_type': 'webhook',
            'message': 'Webhook triggers use live data. Configure the webhook URL and send a test request.',
            'supports_manual_input': True,
            'sample_payload': {
                'event': 'test_webhook',
                'data': {
                    'id': '123',
                    'action': 'created',
                    'resource': 'contact'
                },
                'timestamp': timezone.now().isoformat()
            }
        })