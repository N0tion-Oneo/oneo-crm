"""
API views for workflow management
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from api.permissions import WorkflowPermission, WorkflowExecutionPermission, WorkflowApprovalPermission
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
import json
import logging

from .models import (
    Workflow, WorkflowExecution, WorkflowExecutionLog,
    WorkflowApproval, WorkflowSchedule, WorkflowTrigger
)
from .serializers import (
    WorkflowSerializer, WorkflowExecutionSerializer,
    WorkflowExecutionLogSerializer, WorkflowApprovalSerializer,
    WorkflowScheduleSerializer
)
from .engine import workflow_engine
from .triggers.manager import TriggerManager
from .tasks import execute_workflow_async, validate_workflow_definition

User = get_user_model()
logger = logging.getLogger(__name__)

# Initialize trigger manager
trigger_manager = TriggerManager()


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
        """Set workflow creator and create default trigger"""
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

        # Create default trigger if not exists
        if not WorkflowTrigger.objects.filter(workflow=workflow).exists():
            trigger_type = self.request.data.get('trigger_type', 'manual')
            trigger_config = self.request.data.get('trigger_config', {})

            WorkflowTrigger.objects.create(
                tenant=tenant,
                workflow=workflow,
                trigger_type=trigger_type,
                name=f"{workflow.name} - Primary Trigger",
                description=f"Auto-generated trigger for {workflow.name}",
                trigger_config=trigger_config,
                is_active=True
            )
    
    @action(detail=True, methods=['post'])
    def trigger(self, request, pk=None):
        """Manually trigger a workflow"""
        workflow = self.get_object()
        manual_data = request.data.get('data', {})
        
        try:
            import asyncio
            
            async def trigger_async():
                return await trigger_manager.trigger_manual(
                    workflow_id=str(workflow.id),
                    user_id=str(request.user.id),
                    data=manual_data
                )
            
            result = asyncio.run(trigger_async())
            
            return Response({
                'success': True,
                'task_id': result.get('task_id'),
                'workflow_id': result.get('workflow_id'),
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
    
    @action(detail=True, methods=['post'], url_path='test-node')
    def test_node(self, request, pk=None):
        """Test a single workflow node"""
        workflow = self.get_object()

        # Get node configuration from request
        node_id = request.data.get('node_id')
        node_type = request.data.get('node_type')
        node_config = request.data.get('node_config', {})
        test_context = request.data.get('test_context', {})

        if not node_id or not node_type:
            return Response({
                'success': False,
                'error': 'node_id and node_type are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Import the node processor based on node type
            from workflows.processors import get_node_processor
            import time

            # For trigger nodes, we'll return configuration validation
            if 'trigger' in node_type.lower():
                # Validate trigger configuration
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

                return Response({
                    'status': 'success',
                    'message': f'Trigger node "{node_type}" configured successfully',
                    'output': {
                        'data': {
                            'trigger_type': node_type,
                            'config': node_config,
                            'test_context': test_context,
                            'form_url': form_url,
                            'validation': 'All required fields are configured'
                        },
                        'metadata': {
                            'executionTime': '0ms',
                            'node_id': node_id,
                            'timestamp': timezone.now().isoformat()
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

            # Test the node with sample data
            start_time = time.time()

            try:
                # Execute the processor with test data
                result = processor.process(node_config, test_context)
                execution_time = (time.time() - start_time) * 1000

                return Response({
                    'status': 'success',
                    'message': f'Node tested successfully',
                    'output': {
                        'data': result.get('output', {}),
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
        """Get workflow triggers"""
        workflow = self.get_object()
        triggers = WorkflowTrigger.objects.filter(workflow=workflow)

        # Serialize manually for now
        trigger_data = []
        for trigger in triggers:
            trigger_data.append({
                'id': str(trigger.id),
                'name': trigger.name,
                'description': trigger.description,
                'trigger_type': trigger.trigger_type,
                'is_active': trigger.is_active,
                'trigger_config': trigger.trigger_config,
                'conditions': trigger.conditions,
                'execution_count': trigger.execution_count,
                'last_triggered_at': trigger.last_triggered_at.isoformat() if trigger.last_triggered_at else None,
                'created_at': trigger.created_at.isoformat()
            })

        return Response(trigger_data)

    @action(detail=True, methods=['post'])
    def create_trigger(self, request, pk=None):
        """Create a new trigger for the workflow"""
        workflow = self.get_object()

        # Get tenant
        from django.db import connection
        from tenants.models import Tenant

        if hasattr(connection, 'tenant'):
            schema_name = connection.schema_name
            if schema_name and schema_name != 'public':
                tenant = Tenant.objects.filter(schema_name=schema_name).first()
            else:
                tenant = Tenant.objects.exclude(schema_name='public').first()
        else:
            tenant = Tenant.objects.exclude(schema_name='public').first()

        trigger = WorkflowTrigger.objects.create(
            tenant=tenant,
            workflow=workflow,
            name=request.data.get('name', f'{workflow.name} Trigger'),
            description=request.data.get('description', ''),
            trigger_type=request.data.get('trigger_type', 'manual'),
            trigger_config=request.data.get('trigger_config', {}),
            conditions=request.data.get('conditions', []),
            is_active=request.data.get('is_active', True)
        )

        return Response({
            'id': str(trigger.id),
            'name': trigger.name,
            'trigger_type': trigger.trigger_type,
            'is_active': trigger.is_active
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path='triggers/(?P<trigger_id>[^/.]+)')
    def update_trigger(self, request, pk=None, trigger_id=None):
        """Update a trigger"""
        workflow = self.get_object()

        try:
            trigger = WorkflowTrigger.objects.get(id=trigger_id, workflow=workflow)

            # Update fields
            if 'name' in request.data:
                trigger.name = request.data['name']
            if 'description' in request.data:
                trigger.description = request.data['description']
            if 'trigger_type' in request.data:
                trigger.trigger_type = request.data['trigger_type']
            if 'trigger_config' in request.data:
                trigger.trigger_config = request.data['trigger_config']
            if 'conditions' in request.data:
                trigger.conditions = request.data['conditions']
            if 'is_active' in request.data:
                trigger.is_active = request.data['is_active']

            trigger.save()

            return Response({
                'id': str(trigger.id),
                'name': trigger.name,
                'trigger_type': trigger.trigger_type,
                'is_active': trigger.is_active
            })
        except WorkflowTrigger.DoesNotExist:
            return Response({'error': 'Trigger not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['delete'], url_path='triggers/(?P<trigger_id>[^/.]+)')
    def delete_trigger(self, request, pk=None, trigger_id=None):
        """Delete a trigger"""
        workflow = self.get_object()

        try:
            trigger = WorkflowTrigger.objects.get(id=trigger_id, workflow=workflow)
            trigger.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except WorkflowTrigger.DoesNotExist:
            return Response({'error': 'Trigger not found'}, status=status.HTTP_404_NOT_FOUND)

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