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
    WorkflowApproval, WorkflowSchedule
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
        """Set workflow creator"""
        serializer.save(created_by=self.request.user)
    
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
        
        # Create duplicate
        duplicate = Workflow.objects.create(
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
@require_http_methods(["POST"])
def webhook_endpoint(request, workflow_id):
    """Webhook endpoint for triggering workflows"""
    try:
        # Parse request data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = dict(request.POST)
        
        # Get request headers
        headers = {
            key: value for key, value in request.META.items()
            if key.startswith('HTTP_')
        }
        
        # Handle webhook asynchronously
        import asyncio
        
        async def handle_webhook_async():
            return await trigger_manager.process_webhook(
                workflow_id=workflow_id,
                payload=data,
                headers=headers
            )
        
        # Run webhook handler
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new event loop for this webhook
                import threading
                import concurrent.futures
                
                def run_webhook():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(handle_webhook_async())
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_webhook)
                    result = future.result(timeout=30)
            else:
                result = asyncio.run(handle_webhook_async())
        except Exception as webhook_error:
            logger.error(f"Webhook processing error: {webhook_error}")
            result = {
                'status': 'error',
                'message': str(webhook_error),
                'workflow_id': workflow_id
            }
        
        if result['status'] == 'success':
            return JsonResponse(result, status=200)
        else:
            return JsonResponse(result, status=400)
            
    except Exception as e:
        logger.error(f"Webhook endpoint error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
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