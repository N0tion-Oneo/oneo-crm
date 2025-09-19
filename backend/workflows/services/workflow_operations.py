"""
Service for workflow operations (trigger, duplicate, activate, etc.)
"""
import logging
import asyncio
from django.db import connection
from rest_framework.response import Response
from rest_framework import status
from workflows.models import Workflow, WorkflowExecution
from workflows.engine import workflow_engine
from workflows.tasks import validate_workflow_definition
from workflows.serializers import WorkflowSerializer, WorkflowExecutionSerializer
from tenants.models import Tenant

logger = logging.getLogger(__name__)


class WorkflowOperationsService:
    """Service for workflow operations"""

    @staticmethod
    def trigger_workflow(workflow, user, data=None):
        """Manually trigger a workflow"""
        manual_data = data or {}

        try:
            async def trigger_async():
                return await workflow_engine.execute_workflow(
                    workflow=workflow,
                    trigger_data={'manual': True, **manual_data},
                    triggered_by=user,
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

    @staticmethod
    def get_executions(workflow, paginator=None):
        """Get workflow executions"""
        executions = WorkflowExecution.objects.filter(workflow=workflow).order_by('-started_at')

        if paginator:
            page = paginator.paginate_queryset(executions)
            if page is not None:
                serializer = WorkflowExecutionSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)

        serializer = WorkflowExecutionSerializer(executions, many=True)
        return Response(serializer.data)

    @staticmethod
    def duplicate_workflow(workflow, user):
        """Duplicate a workflow"""
        # Get tenant
        if hasattr(connection, 'tenant'):
            tenant = connection.tenant
        else:
            tenant = Tenant.objects.exclude(schema_name='public').first()

        # Create duplicate
        duplicate = Workflow.objects.create(
            tenant=tenant,
            name=f"{workflow.name} (Copy)",
            description=workflow.description,
            created_by=user,
            trigger_type=workflow.trigger_type,
            trigger_config=workflow.trigger_config,
            workflow_definition=workflow.workflow_definition,
            max_executions_per_hour=workflow.max_executions_per_hour,
            timeout_minutes=workflow.timeout_minutes,
            retry_count=workflow.retry_count,
            status='draft'  # Always create duplicates as draft
        )

        # Note: If workflow has triggers, they would be duplicated here
        # Currently the Workflow model doesn't have a triggers relationship

        serializer = WorkflowSerializer(duplicate)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def activate_workflow(workflow):
        """Activate a workflow"""
        workflow.status = 'active'
        workflow.save()

        return Response({
            'success': True,
            'message': f'Workflow {workflow.name} activated'
        })

    @staticmethod
    def deactivate_workflow(workflow):
        """Deactivate a workflow"""
        workflow.status = 'paused'
        workflow.save()

        return Response({
            'success': True,
            'message': f'Workflow {workflow.name} deactivated'
        })

    @staticmethod
    def get_templates():
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
            },
            {
                'id': 'communication_followup',
                'name': 'Communication Follow-up',
                'description': 'Automated follow-up for unresponsive contacts',
                'category': 'communication',
                'nodes': [
                    {
                        'id': 'trigger',
                        'type': 'trigger',
                        'position': {'x': 100, 'y': 100},
                        'data': {'name': 'Email Sent'}
                    },
                    {
                        'id': 'wait',
                        'type': 'wait',
                        'position': {'x': 300, 'y': 100},
                        'data': {
                            'name': 'Wait for Response',
                            'duration': 72,
                            'unit': 'hours'
                        }
                    },
                    {
                        'id': 'check_response',
                        'type': 'condition',
                        'position': {'x': 500, 'y': 100},
                        'data': {
                            'name': 'Check for Response',
                            'conditions': [{
                                'left': {'context_path': 'has_response'},
                                'operator': '==',
                                'right': True,
                                'output': 'responded'
                            }],
                            'default_output': 'no_response'
                        }
                    },
                    {
                        'id': 'followup_email',
                        'type': 'send_email',
                        'position': {'x': 700, 'y': 150},
                        'data': {
                            'name': 'Send Follow-up',
                            'subject': 'Following up on our previous email',
                            'template': 'followup_template'
                        }
                    }
                ],
                'edges': [
                    {'id': 'e1', 'source': 'trigger', 'target': 'wait'},
                    {'id': 'e2', 'source': 'wait', 'target': 'check_response'},
                    {'id': 'e3', 'source': 'check_response', 'target': 'followup_email', 'label': 'no_response'}
                ]
            },
            {
                'id': 'data_enrichment',
                'name': 'Data Enrichment Pipeline',
                'description': 'Enrich record data from external sources',
                'category': 'data',
                'nodes': [
                    {
                        'id': 'trigger',
                        'type': 'trigger',
                        'position': {'x': 100, 'y': 100},
                        'data': {'name': 'New Contact Created'}
                    },
                    {
                        'id': 'http_enrichment',
                        'type': 'http_request',
                        'position': {'x': 300, 'y': 100},
                        'data': {
                            'name': 'Fetch Company Data',
                            'method': 'GET',
                            'url': 'https://api.example.com/company/{record.email_domain}'
                        }
                    },
                    {
                        'id': 'ai_analysis',
                        'type': 'ai_analysis',
                        'position': {'x': 500, 'y': 100},
                        'data': {
                            'name': 'Analyze Company',
                            'analysis_type': 'company_classification'
                        }
                    },
                    {
                        'id': 'update_contact',
                        'type': 'record_update',
                        'position': {'x': 700, 'y': 100},
                        'data': {
                            'name': 'Update Contact',
                            'update_data': {
                                'company_size': '{node_http_enrichment.size}',
                                'industry': '{node_ai_analysis.industry}',
                                'score': '{node_ai_analysis.score}'
                            }
                        }
                    }
                ],
                'edges': [
                    {'id': 'e1', 'source': 'trigger', 'target': 'http_enrichment'},
                    {'id': 'e2', 'source': 'http_enrichment', 'target': 'ai_analysis'},
                    {'id': 'e3', 'source': 'ai_analysis', 'target': 'update_contact'}
                ]
            }
        ]

        return Response(templates)

    @staticmethod
    def validate_workflow(workflow):
        """Validate a workflow definition"""
        try:
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