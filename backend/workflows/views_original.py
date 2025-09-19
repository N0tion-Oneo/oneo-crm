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

# Import services
from .services import TestDataService, NodeTestingService, WorkflowOperationsService

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
        data = request.data.get('data')
        return WorkflowOperationsService.trigger_workflow(workflow, request.user, data)
    
    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """Get workflow executions"""
        workflow = self.get_object()
        return WorkflowOperationsService.get_executions(workflow, self)
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a workflow"""
        workflow = self.get_object()
        return WorkflowOperationsService.duplicate_workflow(workflow, request.user)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a workflow"""
        workflow = self.get_object()
        return WorkflowOperationsService.activate_workflow(workflow)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a workflow"""
        workflow = self.get_object()
        return WorkflowOperationsService.deactivate_workflow(workflow)
    
    @action(detail=False, methods=['get'])
    def templates(self, request):
        """Get workflow templates"""
        return WorkflowOperationsService.get_templates()
    
    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """Validate a workflow definition"""
        workflow = self.get_object()
        return WorkflowOperationsService.validate_workflow(workflow)
    
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
        return TestDataService.get_record_display_name(record)

    @action(detail=False, methods=['get'], url_path='test-data', permission_classes=[TenantMemberPermission])
    def get_test_data(self, request):
        """Get recent test data based on trigger type - uses real data from system"""
        return TestDataService.get_test_data(request)

    @action(detail=False, methods=['post'], url_path='test-node-standalone', permission_classes=[TenantMemberPermission])
    def test_node_standalone(self, request):
        """Test a node without requiring a workflow - for test page"""
        return NodeTestingService.test_node_standalone(request)

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