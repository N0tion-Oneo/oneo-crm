"""
API views for workflow management
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from api.permissions import WorkflowPermission, WorkflowExecutionPermission, WorkflowApprovalPermission
from api.permissions.base import TenantMemberPermission
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
import json
import logging
import traceback

from .models import (
    Workflow, WorkflowExecution, WorkflowExecutionLog,
    WorkflowApproval, WorkflowSchedule
)
from .serializers import (
    WorkflowSerializer, WorkflowExecutionSerializer,
    WorkflowExecutionLogSerializer, WorkflowApprovalSerializer,
    WorkflowScheduleSerializer
)
from .engine import workflow_engine
from .tasks import execute_workflow_async, validate_workflow_definition
from .trigger_registry import trigger_registry

User = get_user_model()
logger = logging.getLogger(__name__)


class WorkflowViewSet(viewsets.ModelViewSet):
    """ViewSet for workflow management"""
    
    serializer_class = WorkflowSerializer
    permission_classes = [WorkflowPermission]
    
    def get_queryset(self):
        """Filter workflows by user access"""
        user = self.request.user
        return Workflow.objects.filter(
            Q(created_by=user) | 
            Q(visibility='public') | 
            Q(allowed_users=user)
        ).distinct()
    
    def perform_create(self, serializer):
        """Set workflow creator and register triggers"""
        # Get tenant from connection
        from django.db import connection
        from tenants.models import Tenant

        if hasattr(connection, 'tenant'):
            tenant = connection.tenant
        else:
            # Fallback to first tenant for development
            tenant = Tenant.objects.exclude(schema_name='public').first()

        # Create workflow
        workflow = serializer.save(
            created_by=self.request.user,
            tenant=tenant
        )

        # Register workflow with trigger registry for node-based triggers
        try:
            trigger_registry.register_workflow(workflow)
            logger.info(f"Registered workflow {workflow.name} with trigger registry")
        except Exception as e:
            logger.error(f"Failed to register workflow triggers: {e}")

    def perform_update(self, serializer):
        """Update workflow and re-register triggers"""
        workflow = serializer.save()

        # Re-register workflow with trigger registry for node-based triggers
        try:
            trigger_registry.register_workflow(workflow)
            logger.info(f"Re-registered workflow {workflow.name} with trigger registry")
        except Exception as e:
            logger.error(f"Failed to re-register workflow triggers: {e}")

    @action(detail=True, methods=['post'])
    def trigger(self, request, pk=None):
        """Manually trigger a workflow"""
        workflow = self.get_object()
        manual_data = request.data.get('data', {})
        
        try:
            import asyncio
            
            async def trigger_async():
                return await workflow_engine.execute_workflow(
                    workflow=workflow,
                    trigger_data={'manual': True, **manual_data},
                    triggered_by=request.user,
                    tenant=workflow.tenant
                )

            execution = asyncio.run(trigger_async())

            return Response({
                'success': True,
                'execution_id': str(execution.id),
                'workflow_id': str(workflow.id),
                'message': f'Workflow {workflow.name} triggered successfully'
            })
            
        except Exception as e:
            logger.error(f"Manual trigger failed: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """Get workflow executions"""
        workflow = self.get_object()
        executions = WorkflowExecution.objects.filter(workflow=workflow).order_by('-started_at')
        
        page = self.paginate_queryset(executions)
        if page is not None:
            serializer = WorkflowExecutionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = WorkflowExecutionSerializer(executions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a workflow"""
        workflow = self.get_object()

        # Get tenant
        from django.db import connection
        from tenants.models import Tenant

        if hasattr(connection, 'tenant'):
            tenant = connection.tenant
        else:
            tenant = Tenant.objects.exclude(schema_name='public').first()

        # Create duplicate
        duplicate = Workflow.objects.create(
            tenant=tenant,
            name=f"{workflow.name} (Copy)",
            description=workflow.description,
            created_by=request.user,
            trigger_type=workflow.trigger_type,
            trigger_config=workflow.trigger_config,
            workflow_definition=workflow.workflow_definition,
            max_executions_per_hour=workflow.max_executions_per_hour,
            timeout_minutes=workflow.timeout_minutes,
            retry_count=workflow.retry_count,
            status='draft'  # Always create duplicates as draft
        )

        # Duplicate triggers
        for trigger in workflow.triggers.all():
            WorkflowTrigger.objects.create(
                tenant=tenant,
                workflow=duplicate,
                trigger_type=trigger.trigger_type,
                name=f"{trigger.name} (Copy)",
                description=trigger.description,
                trigger_config=trigger.trigger_config,
                conditions=trigger.conditions,
                is_active=False  # Start as inactive
            )

        serializer = self.get_serializer(duplicate)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a workflow"""
        workflow = self.get_object()
        workflow.status = 'active'
        workflow.save()
        
        return Response({
            'success': True,
            'message': f'Workflow {workflow.name} activated'
        })
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a workflow"""
        workflow = self.get_object()
        workflow.status = 'paused'
        workflow.save()
        
        return Response({
            'success': True,
            'message': f'Workflow {workflow.name} deactivated'
        })
    
    @action(detail=False, methods=['get'])
    def templates(self, request):
        """Get workflow templates"""
        templates = [
            {
                'id': 'ai_content_processor',
                'name': 'AI Content Processor',
                'description': 'Process incoming content with AI analysis',
                'category': 'ai',
                'nodes': [
                    {
                        'id': 'trigger',
                        'type': 'trigger',
                        'position': {'x': 100, 'y': 100},
                        'data': {'name': 'Record Created'}
                    },
                    {
                        'id': 'ai_analysis',
                        'type': 'ai_analysis',
                        'position': {'x': 300, 'y': 100},
                        'data': {
                            'name': 'AI Content Analysis',
                            'analysis_type': 'sentiment',
                            'data_source': 'record_data.content'
                        }
                    },
                    {
                        'id': 'update_record',
                        'type': 'record_update',
                        'position': {'x': 500, 'y': 100},
                        'data': {
                            'name': 'Update Record',
                            'record_id_source': 'record_id',
                            'update_data': {
                                'ai_sentiment': '{node_ai_analysis}'
                            }
                        }
                    }
                ],
                'edges': [
                    {'id': 'e1', 'source': 'trigger', 'target': 'ai_analysis'},
                    {'id': 'e2', 'source': 'ai_analysis', 'target': 'update_record'}
                ]
            },
            {
                'id': 'approval_workflow',
                'name': 'Approval Workflow',
                'description': 'Workflow requiring human approval',
                'category': 'approval',
                'nodes': [
                    {
                        'id': 'trigger',
                        'type': 'trigger',
                        'position': {'x': 100, 'y': 100},
                        'data': {'name': 'High Value Record'}
                    },
                    {
                        'id': 'condition',
                        'type': 'condition',
                        'position': {'x': 300, 'y': 100},
                        'data': {
                            'name': 'Check Value',
                            'conditions': [{
                                'left': {'context_path': 'record_data.value'},
                                'operator': '>',
                                'right': 10000,
                                'output': 'requires_approval'
                            }],
                            'default_output': 'auto_approve'
                        }
                    },
                    {
                        'id': 'approval',
                        'type': 'approval',
                        'position': {'x': 500, 'y': 50},
                        'data': {
                            'name': 'Manager Approval',
                            'title': 'High Value Record Approval',
                            'description': 'Please review this high-value record',
                            'assigned_to_id': 1
                        }
                    },
                    {
                        'id': 'auto_process',
                        'type': 'record_update',
                        'position': {'x': 500, 'y': 150},
                        'data': {
                            'name': 'Auto Process',
                            'record_id_source': 'record_id',
                            'update_data': {'status': 'approved'}
                        }
                    }
                ],
                'edges': [
                    {'id': 'e1', 'source': 'trigger', 'target': 'condition'},
                    {'id': 'e2', 'source': 'condition', 'target': 'approval', 'label': 'requires_approval'},
                    {'id': 'e3', 'source': 'condition', 'target': 'auto_process', 'label': 'auto_approve'}
                ]
            }
        ]
        
        return Response(templates)
    
    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """Validate a workflow definition"""
        workflow = self.get_object()
        
        try:
            from django.db import connection
            current_schema = connection.schema_name
            
            # Run validation using Celery task
            result = validate_workflow_definition.delay(
                workflow_id=str(workflow.id),
                tenant_schema=current_schema
            )
            
            # Get result synchronously for immediate feedback
            validation_result = result.get(timeout=10)
            
            return Response({
                'success': True,
                'validation': validation_result,
                'workflow_id': str(workflow.id)
            })
            
        except Exception as e:
            logger.error(f"Workflow validation failed: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='test-records', permission_classes=[TenantMemberPermission])
    def get_test_records(self, request):
        """Get recent records for testing workflow nodes"""
        # For 'new' workflows, we still want to allow fetching test records
        # based on the pipeline_id, even though the workflow doesn't exist yet

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
            from django_tenants.utils import get_tenant_model

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

    def get_record_display_name(self, record):
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

    @action(detail=False, methods=['get'], url_path='test-data', permission_classes=[TenantMemberPermission])
    def get_test_data(self, request):
        """Get recent test data based on trigger type - uses real data from system"""
        from django_tenants.utils import get_tenant
        current_tenant = get_tenant(request)
        logger.info(f"get_test_data called in tenant: {current_tenant.schema_name if current_tenant else 'No tenant'}")

        node_type = request.query_params.get('node_type', '').lower()
        pipeline_id = request.query_params.get('pipeline_id')

        # Also check for node_config to extract pipeline_id from there
        node_config_str = request.query_params.get('node_config')
        node_config = None
        if node_config_str:
            try:
                import json
                node_config = json.loads(node_config_str)
                # Always check node_config for pipeline_id, even if one was provided
                # This ensures we use the pipeline from the form config when available
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

        logger.info(f"get_test_data called with node_type={node_type}, pipeline_id={pipeline_id}, has_config={bool(node_config)}")

        # Helper function for getting record display name
        def get_record_display_name(record):
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

        try:
            # Determine what type of data to fetch based on trigger type
            if 'email' in node_type:
                # Fetch recent email messages
                from communications.models import Message, Channel

                messages = Message.objects.filter(
                    channel__channel_type__in=['email', 'gmail', 'outlook'],
                    direction='inbound'
                ).select_related('channel', 'conversation').order_by('-created_at')[:10]

                formatted_data = []
                for msg in messages:
                    formatted_data.append({
                        'id': str(msg.id),
                        'type': 'email',
                        'title': msg.subject or f"Email from {msg.contact_email or 'Unknown'}",
                        'created_at': msg.created_at.isoformat(),
                        'preview': {
                            'from': msg.contact_email,
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

            elif 'linkedin' in node_type or 'whatsapp' in node_type:
                # Fetch recent messages from specific channel
                from communications.models import Message, Channel

                channel_type = 'linkedin' if 'linkedin' in node_type else 'whatsapp'
                messages = Message.objects.filter(
                    channel__channel_type=channel_type,
                    direction='inbound'
                ).select_related('channel', 'conversation').order_by('-created_at')[:10]

                formatted_data = []
                for msg in messages:
                    formatted_data.append({
                        'id': str(msg.id),
                        'type': channel_type,
                        'title': f"{channel_type.title()} from {msg.contact_phone or msg.contact_email or 'Unknown'}",
                        'created_at': msg.created_at.isoformat(),
                        'preview': {
                            'from': msg.contact_phone or msg.contact_email,
                            'content': msg.content[:200] if msg.content else '',
                            'channel': msg.channel.name if msg.channel else None
                        }
                    })

                return Response({
                    'data': formatted_data,
                    'data_type': channel_type,
                    'total': len(formatted_data)
                })

            elif 'form' in node_type:
                # Get FormSubmission data for form triggers
                if not pipeline_id:
                    return Response({
                        'data': [],
                        'data_type': 'form_submission',
                        'message': 'Pipeline ID required for form triggers'
                    })

                from pipelines.models import FormSubmission, Record

                # Debug: Check which tenant we're in
                from django_tenants.utils import get_tenant
                current_tenant = get_tenant(request)
                logger.info(f"Querying FormSubmissions in tenant: {current_tenant.schema_name if current_tenant else 'No tenant'}")

                # Get recent form submissions
                initial_count = FormSubmission.objects.filter(
                    record__pipeline_id=pipeline_id
                ).count()

                form_submissions_qs = FormSubmission.objects.filter(
                    record__pipeline_id=pipeline_id
                )

                # Log initial state
                logger.info(f"Starting with {initial_count} form submissions for pipeline {pipeline_id} in tenant {current_tenant.schema_name if current_tenant else 'unknown'}")

                # Filter by form_mode and stage if provided in config
                if node_config:
                    form_mode = node_config.get('mode') or node_config.get('form_mode')
                    stage = node_config.get('stage') or node_config.get('form_stage')

                    logger.info(f"Filtering form submissions - mode: {form_mode}, stage: {stage}, full config: {node_config}")

                    if form_mode:
                        form_submissions_qs = form_submissions_qs.filter(form_mode=form_mode)
                        logger.info(f"Filtered by form_mode={form_mode}, count: {form_submissions_qs.count()}")

                    # If stage is specified, filter by form_config containing the stage
                    # Note: form_config is a JSONField, so we need to use the correct lookup
                    if stage:
                        # First try to filter by form_config JSON field
                        try:
                            form_submissions_qs = form_submissions_qs.filter(
                                form_config__stage=stage
                            )
                            logger.info(f"Filtered by form_config__stage={stage}, count: {form_submissions_qs.count()}")
                        except Exception as e:
                            logger.warning(f"Could not filter by form_config__stage: {e}")
                            # Fallback: check if any submissions match manually (for debugging)
                            matching = []
                            for fs in form_submissions_qs[:10]:
                                if fs.form_config.get('stage') == stage:
                                    matching.append(fs.id)
                            logger.info(f"Manual check found {len(matching)} matching submissions with stage={stage}")

                form_submissions = form_submissions_qs.select_related(
                    'record', 'record__pipeline', 'submitted_by'
                ).order_by('-created_at')[:10]

                formatted_data = []
                for submission in form_submissions:
                    # Use submission metadata for preview
                    preview_data = submission.submitted_data or {}
                    title = (
                        f"{submission.form_name} - {submission.created_at.strftime('%Y-%m-%d %H:%M')}" if submission.form_name
                        else f"Form Submission - {submission.created_at.strftime('%Y-%m-%d %H:%M')}"
                    )

                    # Extract stage from form_config if present
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
                            'fields': list(preview_data.keys())[:5]  # Show first 5 field names
                        },
                        'record_id': str(submission.record.id)
                    })

                # Initialize message variable
                message = None

                # If no form submissions exist yet, provide helpful message
                if not formatted_data:
                    # Check if there are ANY form submissions for this pipeline
                    total_submissions = FormSubmission.objects.filter(
                        record__pipeline_id=pipeline_id
                    ).count()

                    # Check if filters were applied
                    form_mode = node_config.get('mode') or node_config.get('form_mode') if node_config else None
                    stage = node_config.get('stage') or node_config.get('form_stage') if node_config else None

                    if total_submissions > 0 and (form_mode or stage):
                        # There are submissions, but none match the filters
                        message = f"No form submissions found matching filters (mode: {form_mode}, stage: {stage}). "
                        message += f"Pipeline has {total_submissions} total submissions."
                        logger.info(message)
                    else:
                        message = "No form submissions found. Submit a form first to test this trigger."

                    # Still try to fall back to records for convenience
                    records = Record.objects.filter(
                        pipeline_id=pipeline_id,
                        is_deleted=False
                    ).order_by('-created_at')[:5]

                    for record in records:
                        data = record.data or {}
                        formatted_data.append({
                            'id': str(record.id),
                            'type': 'record_as_form',  # Special type to indicate this is a record being used as form data
                            'title': f"Record (as form data) - {record.created_at.strftime('%Y-%m-%d %H:%M')}",
                            'created_at': record.created_at.isoformat(),
                            'preview': {
                                'form_name': f"{record.pipeline.name} Form",
                                'form_id': f"pipeline_{pipeline_id}_default",
                                'fields': list(data.keys())[:5]
                            }
                        })

                    # Change data_type to indicate these are records being used as form test data
                    return Response({
                        'data': formatted_data,
                        'data_type': 'record_as_form' if formatted_data and formatted_data[0]['type'] == 'record_as_form' else 'form_submission',
                        'total': len(formatted_data)
                    })

                response_data = {
                    'data': formatted_data,
                    'data_type': 'form_submission',
                    'total': len(formatted_data)
                }

                # Add message if defined
                if message:
                    response_data['message'] = message

                return Response(response_data)

            elif 'record' in node_type:
                # Use existing record fetching logic for record triggers
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
                    data = record.data or {}
                    title = (
                        data.get('name') or
                        f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or
                        data.get('email') or
                        f"Record {str(record.id)[:8]}"
                    )

                    formatted_data.append({
                        'id': str(record.id),
                        'type': 'record',
                        'title': title,
                        'created_at': record.created_at.isoformat(),
                        'preview': {
                            k: v for k, v in data.items()
                            if k in ['name', 'first_name', 'last_name', 'email', 'company']
                        }
                    })

                return Response({
                    'data': formatted_data,
                    'data_type': 'record',
                    'total': len(formatted_data)
                })

            elif 'scheduled' in node_type:
                # Fetch scheduled workflow executions
                from .models import WorkflowSchedule

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

            elif 'date_reached' in node_type:
                # Fetch records with date fields
                if not pipeline_id:
                    return Response({
                        'data': [],
                        'data_type': 'date_trigger',
                        'message': 'Please select a pipeline to see records with date fields'
                    })

                from pipelines.models import Record

                # Get records that have fields containing 'date' in their data
                records = []
                all_records = Record.objects.filter(
                    pipeline_id=pipeline_id,
                    is_deleted=False
                ).order_by('-updated_at')[:50]  # Check up to 50 records

                for record in all_records:
                    if record.data:
                        # Check if any field contains date-like values
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
                                'title': f"Record with date fields: {get_record_display_name(record)}",
                                'created_at': record.created_at.isoformat(),
                                'preview': {
                                    'record_name': get_record_display_name(record),
                                    'date_fields': date_fields
                                }
                            })

                return Response({
                    'data': records,
                    'data_type': 'date_trigger',
                    'total': len(records),
                    'message': 'Records with date fields found' if records else 'No records with date fields found in this pipeline'
                })

            elif 'pipeline_stage' in node_type:
                # Fetch records with stage information
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
                            'title': f"{get_record_display_name(record)} - Stage: {record.data.get('stage', 'Unknown')}",
                            'created_at': record.created_at.isoformat(),
                            'preview': {
                                'current_stage': record.data.get('stage'),
                                'record_name': get_record_display_name(record),
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

            elif 'workflow_completed' in node_type:
                # Fetch completed workflow executions
                from .models import WorkflowExecution

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

            elif 'condition_met' in node_type:
                # Return records that can be tested against conditions
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
                        'title': f"Test conditions with: {get_record_display_name(record)}",
                        'created_at': record.created_at.isoformat(),
                        'preview': {
                            'record_name': get_record_display_name(record),
                            'sample_fields': dict(list(record.data.items())[:5]) if record.data else {}
                        }
                    })

                return Response({
                    'data': formatted_data,
                    'data_type': 'condition_test',
                    'total': len(formatted_data),
                    'message': 'Select a record to test condition evaluation' if formatted_data else 'No records found in this pipeline'
                })

            elif 'webhook' in node_type:
                # For webhooks, we can't fetch historical data but provide guidance
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

            elif 'manual' in node_type:
                # Manual triggers don't need test data
                return Response({
                    'data': [],
                    'data_type': 'manual',
                    'message': 'Manual triggers are activated by users. No test data needed.'
                })

            else:
                # For any other trigger types
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

    @action(detail=False, methods=['post'], url_path='test-node-standalone', permission_classes=[TenantMemberPermission])
    def test_node_standalone(self, request):
        """Test a node without requiring a workflow - for test page"""
        import time
        import asyncio
        from asgiref.sync import async_to_sync
        from django.utils import timezone

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
            context = {
                'workflow_id': 'test_workflow',
                'execution_id': 'test_execution',
                'tenant_id': request.user.tenant_id if hasattr(request.user, 'tenant_id') else None,
                'user_id': request.user.id,
                'trigger_time': timezone.now().isoformat()
            }

            # For trigger nodes, add real trigger_data
            if node_type.startswith('trigger_'):
                trigger_data = {}

                if node_type == 'trigger_form_submitted':
                    # Use config values for form configuration
                    trigger_data['pipeline_id'] = node_config.get('pipeline_id')
                    trigger_data['form_mode'] = node_config.get('mode', 'internal_full')
                    trigger_data['stage'] = node_config.get('stage')
                    trigger_data['submitted_at'] = timezone.now().isoformat()

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

                elif node_type in ['trigger_record_created', 'trigger_record_updated', 'trigger_record_deleted']:
                    # For record triggers, use test record if available
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
                                # For updates, simulate previous record data
                                trigger_data['previous_record'] = record.data or {}
                                trigger_data['changed_fields'] = list(record.data.keys()) if record.data else []
                                trigger_data['updated_by'] = str(request.user.id)
                            elif node_type == 'trigger_record_created':
                                trigger_data['created_by'] = str(request.user.id)
                            elif node_type == 'trigger_record_deleted':
                                trigger_data['deleted_by'] = str(request.user.id)
                                trigger_data['deleted_at'] = timezone.now().isoformat()
                        except Record.DoesNotExist:
                            # No record found, provide empty trigger data
                            pipeline_id = node_config.get('pipeline_id') or node_config.get('pipeline_ids', [None])[0] if node_config.get('pipeline_ids') else None

                            trigger_data = {
                                'record': {},
                                'pipeline_id': pipeline_id,
                                'updated_at': timezone.now().isoformat()
                            }

                            if node_type == 'trigger_record_updated':
                                trigger_data['previous_record'] = {}
                                trigger_data['changed_fields'] = []
                                trigger_data['updated_by'] = str(request.user.id) if request.user.is_authenticated else None
                    else:
                        # No test record provided - provide complete structure for proper testing
                        pipeline_id = node_config.get('pipeline_id') or node_config.get('pipeline_ids', [None])[0] if node_config.get('pipeline_ids') else None

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

                elif node_type == 'trigger_email_received':
                    # For email triggers, check if we have test email data
                    if test_data_id and test_data_type == 'email':
                        from communications.models import Message
                        try:
                            message = Message.objects.get(id=test_data_id)
                            trigger_data = {
                                'from': message.contact_email,
                                'to': message.channel.email_address if hasattr(message.channel, 'email_address') else 'team@company.com',
                                'subject': message.subject or '',
                                'body': message.content or '',
                                'message_id': str(message.id),
                                'received_at': message.created_at.isoformat()
                            }
                        except:
                            trigger_data = {
                                'from': 'test@example.com',
                                'to': 'team@company.com',
                                'subject': 'Test Email',
                                'body': 'Test email body'
                            }
                    else:
                        trigger_data = {
                            'from': 'test@example.com',
                            'to': 'team@company.com',
                            'subject': 'Test Email',
                            'body': 'Test email body'
                        }

                # Add default trigger_data for other trigger types
                elif not trigger_data:
                    trigger_data = {
                        'triggered_at': timezone.now().isoformat(),
                        'trigger_type': node_type
                    }

                context['trigger_data'] = trigger_data

            # For action nodes with test record
            elif test_record_id:
                from pipelines.models import Record
                try:
                    record = Record.objects.get(id=test_record_id, is_deleted=False)
                    context['record'] = {
                        'id': str(record.id),
                        'pipeline_id': str(record.pipeline_id),
                        'data': record.data or {},
                        'created_at': record.created_at.isoformat(),
                        'updated_at': record.updated_at.isoformat()
                    }
                except Record.DoesNotExist:
                    pass

            # Execute the processor
            start_time = time.time()

            if asyncio.iscoroutinefunction(processor.process):
                result = async_to_sync(processor.process)(node_config, context)
            else:
                result = processor.process(node_config, context)

            execution_time = (time.time() - start_time) * 1000

            # Return response with full result data
            # The result from the processor should contain all the output fields
            # The processor returns the complete output, so we pass it directly
            response_data = {
                'status': 'success',
                'execution_time': execution_time,
            }

            # If the processor returned a dict result, spread it into the response
            if isinstance(result, dict):
                # Preserve the processor's output structure
                response_data['output'] = result
            else:
                # For non-dict results, wrap in output
                response_data['output'] = {'result': result}

            return Response(response_data)

        except Exception as e:
            logger.error(f"Node test failed: {e}", exc_info=True)
            return Response({
                'status': 'error',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='test-node')
    def test_node(self, request, pk=None):
        """Test a single workflow node"""
        workflow = self.get_object()

        # Get node configuration from request
        node_id = request.data.get('node_id')
        node_type = request.data.get('node_type')
        node_config = request.data.get('node_config', {})
        test_context = request.data.get('test_context', {})
        test_record_id = request.data.get('test_record_id')  # New parameter for selecting specific record

        logger.info(f"test_node called with node_id={node_id}, test_record_id={test_record_id}")
        logger.info(f"Full request data: {request.data}")

        if not node_id or not node_type:
            return Response({
                'success': False,
                'error': 'node_id and node_type are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Import the node processor based on node type
            from workflows.processors import get_node_processor
            import time

            logger.info(f"test_node called with node_type={node_type}, test_record_id={test_record_id}")

            # For trigger nodes, we'll return configuration validation or real data
            if 'trigger' in node_type.lower():
                # If a test record is selected, use its actual data
                if test_record_id:
                    from pipelines.models import Record

                    try:
                        record = Record.objects.get(id=test_record_id, is_deleted=False)
                        logger.info(f"Found record {record.id} with data: {record.data}")

                        # Format the record data based on the trigger type
                        if node_type.lower() == 'trigger_form_submitted' or node_type == 'TRIGGER_FORM_SUBMITTED':
                            # Extract form data from the record
                            form_data = record.data or {}
                            logger.info(f"Extracted form_data: {form_data}")

                            # Build the output that matches what a real form submission would provide
                            # Start with all the actual field data from the record
                            output_data = {}

                            # Add all fields from the record data directly to output
                            for field_name, field_value in form_data.items():
                                output_data[field_name] = field_value
                                logger.info(f"Adding field {field_name} = {field_value} to output")

                            # Add the full form data as nested object
                            output_data['form_data'] = form_data

                            # Add metadata fields
                            output_data.update({
                                'submission_id': f'sub_{record.id}',
                                'submitted_at': record.created_at.isoformat(),
                                'pipeline_id': str(record.pipeline_id),
                                'record_id': str(record.id),

                                # User info (simulated for testing)
                                'user_info': {
                                    'ip_address': '192.168.1.100',
                                    'user_agent': 'Mozilla/5.0 (Testing)',
                                    'referrer': 'https://example.com/contact'
                                },
                                'ip_address': '192.168.1.100',
                                'referrer_url': 'https://example.com/contact'
                            })

                            return Response({
                                'status': 'success',
                                'message': f'Using actual record data from "{record.get_title() if hasattr(record, "get_title") else record.id}"',
                                'output': {
                                    'data': output_data,
                                    'metadata': {
                                        'executionTime': '0ms',
                                        'node_id': node_id,
                                        'timestamp': timezone.now().isoformat(),
                                        'source': 'actual_record',
                                        'record_id': str(record.id)
                                    }
                                }
                            })

                        elif node_type in ['trigger_record_created', 'trigger_record_updated', 'TRIGGER_RECORD_CREATED', 'TRIGGER_RECORD_UPDATED']:
                            # For record triggers, return the actual record data
                            # Include all record fields at the top level for easy template variable access
                            output_data = {}

                            # Add all fields from the record data directly to output
                            if record.data:
                                for field_name, field_value in record.data.items():
                                    output_data[field_name] = field_value

                            # Add record metadata
                            output_data.update({
                                'record_id': str(record.id),
                                'pipeline_id': str(record.pipeline_id),
                                'created_at': record.created_at.isoformat(),
                                'updated_at': record.updated_at.isoformat(),
                                'record': {
                                    'id': str(record.id),
                                    'pipeline_id': str(record.pipeline_id),
                                    'data': record.data,
                                    'created_at': record.created_at.isoformat(),
                                    'updated_at': record.updated_at.isoformat()
                                },
                                'trigger_type': node_type
                            })

                            return Response({
                                'status': 'success',
                                'message': f'Using actual record data',
                                'output': {
                                    'data': output_data,
                                    'metadata': {
                                        'executionTime': '0ms',
                                        'node_id': node_id,
                                        'timestamp': timezone.now().isoformat(),
                                        'source': 'actual_record'
                                    }
                                }
                            })

                    except Record.DoesNotExist:
                        return Response({
                            'status': 'error',
                            'message': 'Selected record not found',
                            'output': {
                                'data': {'error': 'Record not found'},
                                'metadata': {
                                    'executionTime': '0ms',
                                    'node_id': node_id,
                                    'timestamp': timezone.now().isoformat()
                                }
                            }
                        })

                # Otherwise, return validation info and sample data
                validation_errors = []

                # Initialize form_url outside the if block
                form_url = None

                if node_type == 'trigger_form_submitted':
                    if not test_context.get('pipeline_id'):
                        validation_errors.append('Pipeline ID is required')
                    if not test_context.get('form_mode'):
                        validation_errors.append('Form mode is required')

                    # Generate the form URL based on configuration
                    if test_context.get('pipeline_id'):
                        pipeline_id = test_context['pipeline_id']
                        form_mode = test_context.get('form_mode', 'public_filtered')

                        if form_mode == 'internal_full':
                            form_url = f"/forms/internal/{pipeline_id}"
                        elif form_mode == 'public_filtered':
                            form_url = f"/forms/{pipeline_id}"
                        elif form_mode == 'stage_internal' and test_context.get('stage'):
                            form_url = f"/forms/internal/{pipeline_id}?stage={test_context['stage']}"
                        elif form_mode == 'stage_public' and test_context.get('stage'):
                            form_url = f"/forms/{pipeline_id}/stage/{test_context['stage']}"
                        else:
                            form_url = f"/forms/{pipeline_id}"

                if validation_errors:
                    return Response({
                        'status': 'error',
                        'message': 'Trigger configuration has errors',
                        'output': {
                            'data': {
                                'validation_errors': validation_errors,
                                'config': node_config,
                                'test_context': test_context
                            },
                            'metadata': {
                                'executionTime': '0ms',
                                'node_id': node_id,
                                'timestamp': timezone.now().isoformat()
                            }
                        }
                    })

                # Generate sample data for triggers without a selected record
                sample_data = {
                    'trigger_type': node_type,
                    'config': node_config,
                    'test_context': test_context,
                    'form_url': form_url,
                    'validation': 'All required fields are configured'
                }

                # Add sample form data for form submission trigger
                if node_type == 'trigger_form_submitted':
                    sample_data.update({
                        'first_name': 'John',
                        'last_name': 'Doe',
                        'email': 'john.doe@example.com',
                        'phone': '+1 (555) 123-4567',
                        'company': 'Acme Corporation',
                        'title': 'Product Manager',
                        'message': 'I am interested in learning more about your product.',
                        'form_data': {
                            'first_name': 'John',
                            'last_name': 'Doe',
                            'email': 'john.doe@example.com',
                            'phone': '+1 (555) 123-4567',
                            'company': 'Acme Corporation',
                            'title': 'Product Manager',
                            'message': 'I am interested in learning more about your product.'
                        },
                        'submission_id': 'sub_sample_123',
                        'submitted_at': timezone.now().isoformat(),
                        'pipeline_id': test_context.get('pipeline_id', ''),
                        'record_id': 'rec_sample_456',
                        'ip_address': '192.168.1.100',
                        'referrer_url': 'https://example.com/contact'
                    })

                return Response({
                    'status': 'success',
                    'message': f'Trigger node "{node_type}" test with sample data',
                    'output': {
                        'data': sample_data,
                        'metadata': {
                            'executionTime': '0ms',
                            'node_id': node_id,
                            'timestamp': timezone.now().isoformat(),
                            'source': 'sample_data'
                        }
                    }
                })

            # Get the appropriate processor for this node type
            processor = get_node_processor(node_type)

            if not processor:
                return Response({
                    'success': False,
                    'error': f'No processor found for node type: {node_type}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # If a record is selected for testing non-trigger nodes, add its data to context
            if test_record_id and 'trigger' not in node_type.lower():
                from pipelines.models import Record
                try:
                    record = Record.objects.get(id=test_record_id, is_deleted=False)
                    # Add record data to the test context
                    if 'record' not in test_context:
                        test_context['record'] = {}
                    test_context['record']['id'] = str(record.id)
                    test_context['record'].update(record.data or {})
                    logger.info(f"Added record {record.id} data to test context for non-trigger node")
                except Record.DoesNotExist:
                    logger.warning(f"Record {test_record_id} not found, continuing without record data")

            # Test the node with sample data
            start_time = time.time()

            try:
                # Execute the processor with test data
                import asyncio
                from asgiref.sync import async_to_sync

                # Check if the processor has an async process method
                if asyncio.iscoroutinefunction(processor.process):
                    # Handle async processor
                    result = async_to_sync(processor.process)(node_config, test_context)
                else:
                    # Handle sync processor
                    result = processor.process(node_config, test_context)

                execution_time = (time.time() - start_time) * 1000

                return Response({
                    'status': 'success',
                    'message': f'Node tested successfully',
                    'output': {
                        'data': result.get('output', result) if isinstance(result, dict) else {'result': result},
                        'metadata': {
                            'executionTime': f'{execution_time:.2f}ms',
                            'node_id': node_id,
                            'processor': processor.__class__.__name__,
                            'timestamp': timezone.now().isoformat()
                        }
                    }
                })

            except Exception as proc_error:
                execution_time = (time.time() - start_time) * 1000
                return Response({
                    'status': 'error',
                    'message': f'Node execution failed',
                    'output': {
                        'data': {
                            'error': str(proc_error),
                            'node_type': node_type,
                            'config': node_config
                        },
                        'metadata': {
                            'executionTime': f'{execution_time:.2f}ms',
                            'node_id': node_id,
                            'processor': processor.__class__.__name__ if processor else None,
                            'timestamp': timezone.now().isoformat()
                        }
                    }
                })

        except Exception as e:
            logger.error(f"Node test failed: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def triggers(self, request, pk=None):
        """Get workflow trigger nodes from the workflow definition"""
        workflow = self.get_object()

        # Extract trigger nodes from workflow definition
        trigger_nodes = []
        if workflow.workflow_definition:
            nodes = workflow.workflow_definition.get('nodes', [])
            for node in nodes:
                if 'trigger' in node.get('type', '').lower():
                    trigger_nodes.append({
                        'id': node.get('id'),
                        'type': node.get('type'),
                        'label': node.get('data', {}).get('label', 'Trigger'),
                        'config': node.get('data', {}).get('config', {}),
                        'position': node.get('position'),
                        'is_active': workflow.status == 'active'
                    })

        return Response(trigger_nodes)

#     @action(detail=True, methods=['post'])
#     def create_trigger(self, request, pk=None):
#         """Create a new trigger for the workflow"""
#         workflow = self.get_object()
# 
#         # Get tenant
#         from django.db import connection
#         from tenants.models import Tenant
# 
#         if hasattr(connection, 'tenant'):
#             schema_name = connection.schema_name
#             if schema_name and schema_name != 'public':
#                 tenant = Tenant.objects.filter(schema_name=schema_name).first()
#             else:
#                 tenant = Tenant.objects.exclude(schema_name='public').first()
#         else:
#             tenant = Tenant.objects.exclude(schema_name='public').first()
# 
#         trigger = WorkflowTrigger.objects.create(
#             tenant=tenant,
#             workflow=workflow,
#             name=request.data.get('name', f'{workflow.name} Trigger'),
#             description=request.data.get('description', ''),
#             trigger_type=request.data.get('trigger_type', 'manual'),
#             trigger_config=request.data.get('trigger_config', {}),
#             conditions=request.data.get('conditions', []),
#             is_active=request.data.get('is_active', True)
#         )
# 
#         return Response({
#             'id': str(trigger.id),
#             'name': trigger.name,
#             'trigger_type': trigger.trigger_type,
#             'is_active': trigger.is_active
#         }, status=status.HTTP_201_CREATED)
# 
#     @action(detail=True, methods=['patch'], url_path='triggers/(?P<trigger_id>[^/.]+)')
#     def update_trigger(self, request, pk=None, trigger_id=None):
#         """Update a trigger"""
#         workflow = self.get_object()
# 
#         try:
#             trigger = WorkflowTrigger.objects.get(id=trigger_id, workflow=workflow)
# 
#             # Update fields
#             if 'name' in request.data:
#                 trigger.name = request.data['name']
#             if 'description' in request.data:
#                 trigger.description = request.data['description']
#             if 'trigger_type' in request.data:
#                 trigger.trigger_type = request.data['trigger_type']
#             if 'trigger_config' in request.data:
#                 trigger.trigger_config = request.data['trigger_config']
#             if 'conditions' in request.data:
#                 trigger.conditions = request.data['conditions']
#             if 'is_active' in request.data:
#                 trigger.is_active = request.data['is_active']
# 
#             trigger.save()
# 
#             return Response({
#                 'id': str(trigger.id),
#                 'name': trigger.name,
#                 'trigger_type': trigger.trigger_type,
#                 'is_active': trigger.is_active
#             })
#         except WorkflowTrigger.DoesNotExist:
#             return Response({'error': 'Trigger not found'}, status=status.HTTP_404_NOT_FOUND)
# 
#     @action(detail=True, methods=['delete'], url_path='triggers/(?P<trigger_id>[^/.]+)')
#     def delete_trigger(self, request, pk=None, trigger_id=None):
#         """Delete a trigger"""
#         workflow = self.get_object()
# 
#         try:
#             trigger = WorkflowTrigger.objects.get(id=trigger_id, workflow=workflow)
#             trigger.delete()
#             return Response(status=status.HTTP_204_NO_CONTENT)
#         except WorkflowTrigger.DoesNotExist:
#             return Response({'error': 'Trigger not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def node_schemas(self, request):
        """Get configuration schemas for all node types"""
        from workflows.processors import get_all_node_processors

        schemas = {}
        processors = get_all_node_processors()

        for node_type, processor_class in processors.items():
            try:
                # Instantiate processor to get its schema
                processor = processor_class()
                schema_info = {
                    'node_type': node_type,
                    'display_name': getattr(processor, 'display_name', node_type.replace('_', ' ').title()),
                    'description': processor.__class__.__doc__.strip() if processor.__class__.__doc__ else '',
                    'supports_replay': getattr(processor, 'supports_replay', False),
                    'supports_checkpoints': getattr(processor, 'supports_checkpoints', False)
                }

                # Get CONFIG_SCHEMA if it exists
                if hasattr(processor, 'CONFIG_SCHEMA'):
                    schema_info['config_schema'] = processor.CONFIG_SCHEMA
                elif hasattr(processor, 'get_config_schema'):
                    schema_info['config_schema'] = processor.get_config_schema()
                else:
                    schema_info['config_schema'] = None

                schemas[node_type] = schema_info

            except Exception as e:
                logger.warning(f"Failed to get schema for {node_type}: {e}")
                schemas[node_type] = {
                    'node_type': node_type,
                    'error': str(e),
                    'config_schema': None
                }

        return Response(schemas)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get workflow statistics"""
        user = self.request.user
        workflows = self.get_queryset()
        
        # Calculate statistics
        total_workflows = workflows.count()
        active_workflows = workflows.filter(status='active').count()
        draft_workflows = workflows.filter(status='draft').count()
        
        # Get recent executions
        recent_executions = WorkflowExecution.objects.filter(
            workflow__in=workflows
        ).order_by('-started_at')[:10]
        
        # Calculate success rate
        total_executions = recent_executions.count()
        successful_executions = recent_executions.filter(status='success').count()
        success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0
        
        return Response({
            'total_workflows': total_workflows,
            'active_workflows': active_workflows,
            'draft_workflows': draft_workflows,
            'recent_executions': total_executions,
            'success_rate': round(success_rate, 1),
            'recent_execution_details': WorkflowExecutionSerializer(recent_executions, many=True).data
        })

    def _generate_test_form_url(self, pipeline_id: str, form_mode: str, stage: str = None) -> str:
        """Generate the form URL based on mode and stage for test outputs"""
        if form_mode == 'internal_full':
            return f'/forms/internal/{pipeline_id}'
        elif form_mode == 'public_filtered':
            return f'/forms/{pipeline_id}'
        elif form_mode == 'stage_internal' and stage:
            return f'/forms/internal/{pipeline_id}?stage={stage}'
        elif form_mode == 'stage_public' and stage:
            return f'/forms/{pipeline_id}/stage/{stage}'
        return '/forms'


class WorkflowExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for workflow execution management"""
    
    serializer_class = WorkflowExecutionSerializer
    permission_classes = [WorkflowExecutionPermission]
    
    def get_queryset(self):
        """Filter executions by user access"""
        user = self.request.user
        return WorkflowExecution.objects.filter(
            Q(workflow__created_by=user) |
            Q(workflow__is_public=True) |
            Q(workflow__allowed_users=user) |
            Q(triggered_by=user)
        ).distinct().order_by('-started_at')
    
    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """Get execution logs"""
        execution = self.get_object()
        logs = WorkflowExecutionLog.objects.filter(execution=execution).order_by('started_at')
        
        serializer = WorkflowExecutionLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed execution"""
        execution = self.get_object()
        
        if execution.status != 'failed':
            return Response({
                'success': False,
                'error': 'Only failed executions can be retried'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Retry execution using Celery
            from django.db import connection
            current_schema = connection.schema_name
            
            result = execute_workflow_async.delay(
                tenant_schema=current_schema,
                workflow_id=str(execution.workflow.id),
                trigger_data=execution.trigger_data,
                triggered_by_id=request.user.id
            )
            
            return Response({
                'success': True,
                'task_id': result.id,
                'workflow_id': str(execution.workflow.id),
                'message': 'Execution retried successfully'
            })
            
        except Exception as e:
            logger.error(f"Execution retry failed: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a running execution"""
        execution = self.get_object()
        
        if execution.status not in ['running', 'paused']:
            return Response({
                'success': False,
                'error': 'Only running or paused executions can be cancelled'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        execution.status = 'cancelled'
        execution.completed_at = timezone.now()
        execution.error_message = f'Cancelled by {request.user.email}'
        execution.save()
        
        return Response({
            'success': True,
            'message': 'Execution cancelled successfully'
        })


class WorkflowApprovalViewSet(viewsets.ModelViewSet):
    """ViewSet for workflow approval management"""
    
    serializer_class = WorkflowApprovalSerializer
    permission_classes = [WorkflowApprovalPermission]
    
    def get_queryset(self):
        """Filter approvals by user"""
        user = self.request.user
        return WorkflowApproval.objects.filter(
            Q(assigned_to=user) | Q(requested_by=user)
        ).order_by('-requested_at')
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending approvals for current user"""
        approvals = self.get_queryset().filter(
            assigned_to=request.user,
            approved__isnull=True
        )
        
        serializer = self.get_serializer(approvals, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a workflow request"""
        approval = self.get_object()
        
        if approval.assigned_to != request.user:
            return Response({
                'success': False,
                'error': 'Only assigned user can approve this request'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if approval.approved is not None:
            return Response({
                'success': False,
                'error': 'This request has already been processed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        approval.approved = True
        approval.approved_at = timezone.now()
        approval.approved_by = request.user
        approval.approval_notes = request.data.get('notes', '')
        approval.save()
        
        # Resume workflow execution
        execution = approval.execution
        if execution.status == 'paused':
            execution.status = 'running'
            execution.save()
            
            # TODO: Resume execution from approval node
        
        return Response({
            'success': True,
            'message': 'Request approved successfully'
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a workflow request"""
        approval = self.get_object()
        
        if approval.assigned_to != request.user:
            return Response({
                'success': False,
                'error': 'Only assigned user can reject this request'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if approval.approved is not None:
            return Response({
                'success': False,
                'error': 'This request has already been processed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        approval.approved = False
        approval.approved_at = timezone.now()
        approval.approved_by = request.user
        approval.approval_notes = request.data.get('notes', '')
        approval.save()
        
        # Mark execution as failed
        execution = approval.execution
        execution.status = 'failed'
        execution.error_message = f'Rejected by {request.user.email}: {approval.approval_notes}'
        execution.completed_at = timezone.now()
        execution.save()
        
        return Response({
            'success': True,
            'message': 'Request rejected successfully'
        })


class WorkflowScheduleViewSet(viewsets.ModelViewSet):
    """ViewSet for workflow schedule management"""
    
    serializer_class = WorkflowScheduleSerializer
    permission_classes = [WorkflowPermission]
    
    def get_queryset(self):
        """Filter schedules by user access"""
        user = self.request.user
        return WorkflowSchedule.objects.filter(
            Q(workflow__created_by=user) |
            Q(workflow__is_public=True) |
            Q(workflow__allowed_users=user)
        ).distinct().order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause a schedule"""
        schedule = self.get_object()
        schedule.is_active = False
        schedule.save()
        
        return Response({
            'success': True,
            'message': f'Schedule {schedule.name} paused'
        })
    
    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume a schedule"""
        schedule = self.get_object()
        schedule.is_active = True
        
        # Recalculate next execution using croniter
        from croniter import croniter
        from django.utils import timezone
        from datetime import datetime
        import pytz
        
        tz = pytz.timezone(schedule.timezone) if schedule.timezone else timezone.get_current_timezone()
        now = timezone.now().astimezone(tz)
        cron = croniter(schedule.cron_expression, now)
        schedule.next_execution = cron.get_next(datetime)
        schedule.save()
        
        return Response({
            'success': True,
            'message': f'Schedule {schedule.name} resumed'
        })
    
    @action(detail=True, methods=['post'])
    def trigger_now(self, request, pk=None):
        """Trigger scheduled workflow immediately"""
        schedule = self.get_object()
        
        try:
            # Execute the workflow directly using the workflow engine
            from .tasks import execute_workflow_async
            execute_workflow_async.delay(
                str(schedule.workflow.id),
                trigger_data={'scheduled': True, 'schedule_id': str(schedule.id)},
                triggered_by_user_id=str(request.user.id)
            )
            
            return Response({
                'success': True,
                'message': f'Schedule {schedule.name} triggered successfully'
            })
            
        except Exception as e:
            logger.error(f"Schedule trigger failed: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@require_http_methods(["POST", "GET", "PUT"])
def webhook_endpoint(request, workflow_id):
    """
    Enhanced webhook endpoint for triggering workflows

    Supports:
    - Secret token validation for security
    - Multiple HTTP methods (GET, POST, PUT)
    - JSON payload parsing
    - Automatic workflow triggering via workflow engine
    """
    import hashlib
    import hmac
    from django.contrib.auth import get_user_model
    from asgiref.sync import async_to_sync

    User = get_user_model()

    try:
        # Get the workflow
        workflow = Workflow.objects.get(id=workflow_id)

        # Find webhook trigger configuration
        webhook_trigger = None
        if hasattr(workflow, 'triggers') and workflow.triggers:
            for trigger in workflow.triggers:
                if trigger.get('type') == 'webhook':
                    webhook_trigger = trigger
                    break

        if not webhook_trigger:
            logger.warning(f"Workflow {workflow_id} doesn't have webhook trigger configured")
            return JsonResponse({
                "error": "Webhook trigger not configured for this workflow"
            }, status=404)

        # Validate secret token if configured
        if webhook_trigger.get('config', {}).get('secret'):
            expected_secret = webhook_trigger['config']['secret']

            # Check for secret in headers
            provided_secret = request.headers.get('X-Webhook-Secret', '')

            # Also check for signature-based validation (GitHub/Stripe style)
            signature = request.headers.get('X-Webhook-Signature', '')
            if signature and request.body:
                expected_signature = hmac.new(
                    expected_secret.encode(),
                    request.body,
                    hashlib.sha256
                ).hexdigest()

                if not hmac.compare_digest(signature, expected_signature):
                    logger.warning(f"Invalid webhook signature for workflow {workflow_id}")
                    return JsonResponse({
                        "error": "Invalid webhook signature"
                    }, status=401)
            elif provided_secret != expected_secret:
                logger.warning(f"Invalid webhook secret for workflow {workflow_id}")
                return JsonResponse({
                    "error": "Invalid webhook secret"
                }, status=401)

        # Check if method matches configuration
        configured_method = webhook_trigger.get('config', {}).get('method', 'POST')
        if request.method != configured_method:
            return JsonResponse({
                "error": f"Method {request.method} not allowed. Expected {configured_method}"
            }, status=405)

        # Parse webhook payload
        webhook_data = {
            "webhook_headers": dict(request.headers),
            "webhook_method": request.method,
            "webhook_path": request.path,
            "webhook_query_params": dict(request.GET),
        }

        # Add body data
        if request.method in ['POST', 'PUT']:
            try:
                if request.content_type == 'application/json':
                    webhook_data["webhook_body"] = json.loads(request.body)
                else:
                    webhook_data["webhook_body"] = dict(request.POST)
            except:
                webhook_data["webhook_body"] = {}

        # Get system user for webhook triggers
        system_user = User.objects.filter(email='system@oneo.com').first()
        if not system_user:
            # Create system user if it doesn't exist
            system_user = User.objects.create(
                email='system@oneo.com',
                username='system',
                first_name='System',
                last_name='User',
                is_active=True
            )

        # Trigger the workflow using workflow engine
        try:
            from workflows.engine import workflow_engine

            execution = async_to_sync(workflow_engine.execute_workflow)(
                workflow=workflow,
                trigger_data=webhook_data,
                triggered_by=system_user,
                tenant=workflow.tenant
            )

            logger.info(f"Workflow {workflow_id} triggered via webhook, execution ID: {execution.id}")

            return JsonResponse({
                "success": True,
                "message": "Workflow triggered successfully",
                "execution_id": str(execution.id),
                "workflow_id": str(workflow.id),
                "workflow_name": workflow.name
            }, status=200)

        except Exception as e:
            logger.error(f"Failed to trigger workflow {workflow_id} via webhook: {str(e)}")
            return JsonResponse({
                "error": "Failed to trigger workflow",
                "details": str(e)
            }, status=500)

    except Workflow.DoesNotExist:
        logger.warning(f"Webhook received for non-existent workflow {workflow_id}")
        return JsonResponse({
            "error": "Workflow not found"
        }, status=404)
    except Exception as e:
        logger.error(f"Webhook endpoint error: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e) if request.user.is_authenticated else 'An error occurred'
        }, status=500)


@csrf_exempt  
@require_http_methods(["GET"])
def workflow_status(request, execution_id):
    """Get workflow execution status"""
    try:
        execution = WorkflowExecution.objects.get(id=execution_id)
        
        # Check user permissions
        user = request.user
        if not (execution.workflow.created_by == user or 
                execution.workflow.is_public or
                execution.workflow.allowed_users.filter(id=user.id).exists() or
                execution.triggered_by == user):
            return JsonResponse({
                'error': 'Permission denied'
            }, status=403)
        
        # Get execution logs
        logs = WorkflowExecutionLog.objects.filter(execution=execution).order_by('started_at')
        
        return JsonResponse({
            'execution_id': str(execution.id),
            'workflow_name': execution.workflow.name,
            'status': execution.status,
            'started_at': execution.started_at.isoformat(),
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
            'duration_seconds': execution.duration_seconds,
            'logs': [
                {
                    'node_id': log.node_id,
                    'node_name': log.node_name,
                    'node_type': log.node_type,
                    'status': log.status,
                    'started_at': log.started_at.isoformat(),
                    'completed_at': log.completed_at.isoformat() if log.completed_at else None,
                    'duration_ms': log.duration_ms,
                    'error_details': log.error_details
                } for log in logs
            ]
        })
        
    except WorkflowExecution.DoesNotExist:
        return JsonResponse({
            'error': 'Execution not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Status endpoint error: {e}")
        return JsonResponse({
            'error': str(e)
        }, status=500)