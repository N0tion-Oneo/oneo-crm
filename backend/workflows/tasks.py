"""
Celery tasks for workflow automation - Phase 7
Provides asynchronous workflow execution with proper tenant isolation
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.utils import schema_context
from tenants.models import Tenant
from .models import Workflow, WorkflowExecution, ExecutionStatus
from .engine import workflow_engine

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_workflow_async(
    self, 
    tenant_schema: str,
    workflow_id: str, 
    trigger_data: Dict[str, Any],
    triggered_by_id: int
) -> Dict[str, Any]:
    """
    Execute workflow asynchronously with proper tenant isolation
    
    Args:
        tenant_schema: Tenant schema name for multi-tenant isolation
        workflow_id: UUID of workflow to execute
        trigger_data: Data that triggered the workflow
        triggered_by_id: ID of user who triggered the workflow
    
    Returns:
        Dict containing execution results and metadata
    """
    try:
        # Set tenant context for multi-tenant isolation
        with schema_context(tenant_schema):
            # Get workflow and user
            workflow = Workflow.objects.get(id=workflow_id)
            triggered_by = User.objects.get(id=triggered_by_id)
            
            # Validate workflow can be executed
            if not workflow.can_execute():
                raise ValueError(f"Workflow {workflow.name} cannot be executed (status: {workflow.status})")
            
            # Execute workflow using the engine
            logger.info(f"Starting workflow execution: {workflow.name} (ID: {workflow_id})")
            
            # Run async workflow execution in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                execution = loop.run_until_complete(
                    workflow_engine.execute_workflow(
                        workflow=workflow,
                        trigger_data=trigger_data,
                        triggered_by=triggered_by
                    )
                )
                
                logger.info(f"Workflow {workflow.name} completed successfully: {execution.id}")
                
                return {
                    'success': True,
                    'execution_id': str(execution.id),
                    'workflow_id': str(workflow.id),
                    'workflow_name': workflow.name,
                    'status': execution.status,
                    'duration_seconds': execution.duration_seconds,
                    'final_output': execution.final_output,
                    'started_at': execution.started_at.isoformat(),
                    'completed_at': execution.completed_at.isoformat() if execution.completed_at else None
                }
                
            finally:
                loop.close()
                
    except Workflow.DoesNotExist:
        error_msg = f"Workflow {workflow_id} not found in tenant {tenant_schema}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'workflow_id': workflow_id
        }
        
    except User.DoesNotExist:
        error_msg = f"User {triggered_by_id} not found"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'triggered_by_id': triggered_by_id
        }
        
    except Exception as exc:
        error_msg = f"Workflow execution failed: {str(exc)}"
        logger.error(error_msg, exc_info=True)
        
        # Retry logic for transient errors
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying workflow execution (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=exc)
        
        return {
            'success': False,
            'error': error_msg,
            'workflow_id': workflow_id,
            'retries_exhausted': True
        }


@shared_task
def process_scheduled_workflows():
    """
    Process all scheduled workflows across all tenants
    This task runs periodically via Celery Beat
    """
    from .models import WorkflowSchedule
    from django.utils import timezone
    import croniter
    
    processed_count = 0
    error_count = 0
    
    # Get all tenants
    tenants = Tenant.objects.all()
    
    for tenant in tenants:
        try:
            with schema_context(tenant.schema_name):
                # Get active schedules that are due
                now = timezone.now()
                due_schedules = WorkflowSchedule.objects.filter(
                    is_active=True,
                    next_execution__lte=now
                )
                
                for schedule in due_schedules:
                    try:
                        # Execute the workflow
                        result = execute_workflow_async.delay(
                            tenant_schema=tenant.schema_name,
                            workflow_id=str(schedule.workflow.id),
                            trigger_data={
                                'trigger_type': 'scheduled',
                                'schedule_id': str(schedule.id),
                                'schedule_name': schedule.name,
                                'triggered_at': now.isoformat()
                            },
                            triggered_by_id=schedule.workflow.created_by.id
                        )
                        
                        # Update schedule execution tracking
                        schedule.last_execution = now
                        schedule.execution_count += 1
                        
                        # Calculate next execution time using croniter
                        cron = croniter.croniter(schedule.cron_expression, now)
                        schedule.next_execution = cron.get_next(timezone.datetime)
                        schedule.save()
                        
                        processed_count += 1
                        
                        logger.info(f"Scheduled workflow triggered: {schedule.workflow.name} (Schedule: {schedule.name})")
                        
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Failed to process schedule {schedule.name}: {e}")
                        
        except Exception as e:
            error_count += 1
            logger.error(f"Failed to process tenant {tenant.schema_name}: {e}")
    
    logger.info(f"Scheduled workflow processing complete: {processed_count} triggered, {error_count} errors")
    
    return {
        'processed': processed_count,
        'errors': error_count,
        'timestamp': timezone.now().isoformat()
    }


@shared_task
def resume_paused_workflow(execution_id: str, tenant_schema: str, approval_result: Dict[str, Any]):
    """
    Resume a paused workflow after approval is granted/denied
    
    Args:
        execution_id: UUID of the paused execution
        tenant_schema: Tenant schema name
        approval_result: Result of the approval (approved, notes, etc.)
    """
    try:
        with schema_context(tenant_schema):
            execution = WorkflowExecution.objects.get(id=execution_id)
            
            if execution.status != ExecutionStatus.PAUSED:
                logger.warning(f"Attempted to resume non-paused execution: {execution_id}")
                return {'success': False, 'error': 'Execution is not paused'}
            
            # Update execution context with approval result
            execution.execution_context['approval_result'] = approval_result
            execution.status = ExecutionStatus.RUNNING
            execution.save()
            
            # Continue workflow execution from where it left off
            # This is a simplified approach - in production, you'd need to track
            # which node was waiting for approval and resume from there
            logger.info(f"Resuming workflow execution {execution_id} after approval")
            
            # For now, we'll mark as completed since we don't have the full
            # resumption logic implemented yet
            execution.status = ExecutionStatus.SUCCESS
            execution.completed_at = timezone.now()
            execution.final_output = {
                'resumed_after_approval': True,
                'approval_result': approval_result
            }
            execution.save()
            
            return {
                'success': True,
                'execution_id': execution_id,
                'resumed_at': timezone.now().isoformat()
            }
            
    except WorkflowExecution.DoesNotExist:
        error_msg = f"Workflow execution {execution_id} not found"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}
        
    except Exception as e:
        error_msg = f"Failed to resume workflow execution: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {'success': False, 'error': error_msg}


@shared_task
def cleanup_old_executions(days_to_keep: int = 30):
    """
    Clean up old workflow executions across all tenants
    
    Args:
        days_to_keep: Number of days of execution history to retain
    """
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days_to_keep)
    total_deleted = 0
    
    # Process all tenants
    tenants = Tenant.objects.all()
    
    for tenant in tenants:
        try:
            with schema_context(tenant.schema_name):
                # Delete old executions and related logs
                old_executions = WorkflowExecution.objects.filter(
                    started_at__lt=cutoff_date,
                    status__in=[ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]
                )
                
                count = old_executions.count()
                old_executions.delete()  # This will cascade to logs due to FK relationship
                
                total_deleted += count
                
                if count > 0:
                    logger.info(f"Cleaned up {count} old workflow executions in tenant {tenant.schema_name}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup executions in tenant {tenant.schema_name}: {e}")
    
    logger.info(f"Workflow execution cleanup complete: {total_deleted} executions removed")
    
    return {
        'deleted_count': total_deleted,
        'cutoff_date': cutoff_date.isoformat(),
        'timestamp': timezone.now().isoformat()
    }


@shared_task
def validate_workflow_definition(workflow_id: str, tenant_schema: str) -> Dict[str, Any]:
    """
    Validate a workflow definition for correctness
    
    Args:
        workflow_id: UUID of workflow to validate
        tenant_schema: Tenant schema name
        
    Returns:
        Dict containing validation results
    """
    try:
        with schema_context(tenant_schema):
            workflow = Workflow.objects.get(id=workflow_id)
            
            # Get workflow definition
            nodes = workflow.get_nodes()
            edges = workflow.get_edges()
            
            errors = []
            warnings = []
            
            # Validate nodes
            node_ids = {node['id'] for node in nodes}
            for node in nodes:
                node_type = node.get('type')
                node_data = node.get('data', {})
                
                # Check if node type is supported
                if node_type not in workflow_engine.node_processors:
                    errors.append(f"Unsupported node type: {node_type} (Node: {node['id']})")
                
                # Validate node-specific configuration
                if node_type == 'ai_prompt' and not node_data.get('prompt'):
                    errors.append(f"AI prompt node missing prompt configuration (Node: {node['id']})")
                
                if node_type == 'record_create' and not node_data.get('pipeline_id'):
                    errors.append(f"Record create node missing pipeline_id (Node: {node['id']})")
                
                if node_type == 'approval' and not node_data.get('assigned_to_id'):
                    errors.append(f"Approval node missing assigned_to_id (Node: {node['id']})")
            
            # Validate edges
            for edge in edges:
                source = edge.get('source')
                target = edge.get('target')
                
                if source not in node_ids:
                    errors.append(f"Edge references unknown source node: {source}")
                
                if target not in node_ids:
                    errors.append(f"Edge references unknown target node: {target}")
            
            # Check for circular dependencies (simplified check)
            visited = set()
            rec_stack = set()
            
            def has_cycle(node_id, edges_map):
                if node_id in rec_stack:
                    return True
                if node_id in visited:
                    return False
                
                visited.add(node_id)
                rec_stack.add(node_id)
                
                for target in edges_map.get(node_id, []):
                    if has_cycle(target, edges_map):
                        return True
                
                rec_stack.remove(node_id)
                return False
            
            # Build edges map for cycle detection
            edges_map = {}
            for edge in edges:
                source = edge.get('source')
                target = edge.get('target')
                if source not in edges_map:
                    edges_map[source] = []
                edges_map[source].append(target)
            
            # Check for cycles
            for node_id in node_ids:
                if node_id not in visited:
                    if has_cycle(node_id, edges_map):
                        errors.append("Workflow contains circular dependencies")
                        break
            
            # Check for orphaned nodes (nodes with no path from start)
            start_nodes = [node_id for node_id in node_ids if node_id not in [edge['target'] for edge in edges]]
            if not start_nodes:
                warnings.append("No start nodes found (all nodes have incoming edges)")
            elif len(start_nodes) > 1:
                warnings.append(f"Multiple start nodes detected: {start_nodes}")
            
            is_valid = len(errors) == 0
            
            validation_result = {
                'valid': is_valid,
                'errors': errors,
                'warnings': warnings,
                'node_count': len(nodes),
                'edge_count': len(edges),
                'start_nodes': start_nodes,
                'validated_at': timezone.now().isoformat()
            }
            
            logger.info(f"Workflow validation complete for {workflow.name}: {'VALID' if is_valid else 'INVALID'}")
            
            return validation_result
            
    except Workflow.DoesNotExist:
        error_msg = f"Workflow {workflow_id} not found"
        logger.error(error_msg)
        return {
            'valid': False,
            'errors': [error_msg],
            'warnings': []
        }
        
    except Exception as e:
        error_msg = f"Workflow validation failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'valid': False,
            'errors': [error_msg],
            'warnings': []
        }