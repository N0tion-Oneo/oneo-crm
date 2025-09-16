"""
WebSocket broadcasting for workflow execution updates
"""
import json
import logging
from typing import Dict, Any, Optional
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone

logger = logging.getLogger(__name__)


class WorkflowExecutionBroadcaster:
    """
    Handles broadcasting workflow execution events to WebSocket connections
    """
    
    def __init__(self, channel_layer=None):
        self.channel_layer = channel_layer or get_channel_layer()
    
    async def broadcast_execution_started(self, execution):
        """
        Broadcast that a workflow execution has started
        """
        try:
            tenant_schema = execution.tenant.schema_name
            
            # Send to workflow-specific group
            await self.channel_layer.group_send(
                f"workflow_{tenant_schema}_{execution.workflow_id}",
                {
                    'type': 'execution_started',
                    'execution_id': str(execution.id),
                    'workflow_id': str(execution.workflow_id),
                    'started_at': execution.started_at.isoformat(),
                    'triggered_by': execution.triggered_by.email if execution.triggered_by else None
                }
            )
            
            # Send to execution-specific group
            await self.channel_layer.group_send(
                f"execution_{tenant_schema}_{execution.id}",
                {
                    'type': 'execution_started',
                    'execution_id': str(execution.id),
                    'workflow_id': str(execution.workflow_id),
                    'started_at': execution.started_at.isoformat(),
                    'triggered_by': execution.triggered_by.email if execution.triggered_by else None
                }
            )
            
            logger.debug(f"Broadcasted execution started: {execution.id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast execution started: {e}")
    
    async def broadcast_node_started(self, execution, node_id: str, node_type: str):
        """
        Broadcast that a node has started executing
        """
        try:
            tenant_schema = execution.tenant.schema_name
            
            message = {
                'type': 'execution_node_started',
                'execution_id': str(execution.id),
                'node_id': node_id,
                'node_type': node_type,
                'started_at': timezone.now().isoformat()
            }
            
            # Send to execution group
            await self.channel_layer.group_send(
                f"execution_{tenant_schema}_{execution.id}",
                message
            )
            
            logger.debug(f"Broadcasted node started: {node_id} in execution {execution.id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast node started: {e}")
    
    async def broadcast_node_completed(
        self, 
        execution, 
        node_id: str, 
        status: str, 
        output: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        duration_ms: Optional[int] = None
    ):
        """
        Broadcast that a node has completed executing
        """
        try:
            tenant_schema = execution.tenant.schema_name
            
            message = {
                'type': 'execution_node_completed',
                'execution_id': str(execution.id),
                'node_id': node_id,
                'status': status,
                'output': output,
                'error': error,
                'completed_at': timezone.now().isoformat(),
                'duration_ms': duration_ms
            }
            
            # Send to execution group
            await self.channel_layer.group_send(
                f"execution_{tenant_schema}_{execution.id}",
                message
            )
            
            logger.debug(f"Broadcasted node completed: {node_id} in execution {execution.id} with status {status}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast node completed: {e}")
    
    async def broadcast_execution_completed(self, execution):
        """
        Broadcast that a workflow execution has completed
        """
        try:
            tenant_schema = execution.tenant.schema_name
            duration_ms = None
            
            if execution.completed_at and execution.started_at:
                duration_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000)
            
            message = {
                'type': 'execution_completed',
                'execution_id': str(execution.id),
                'status': execution.status,
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                'duration_ms': duration_ms,
                'error': execution.error_message
            }
            
            # Send to workflow group
            await self.channel_layer.group_send(
                f"workflow_{tenant_schema}_{execution.workflow_id}",
                message
            )
            
            # Send to execution group
            await self.channel_layer.group_send(
                f"execution_{tenant_schema}_{execution.id}",
                message
            )
            
            logger.debug(f"Broadcasted execution completed: {execution.id} with status {execution.status}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast execution completed: {e}")
    
    async def broadcast_execution_log(
        self,
        execution,
        node_id: Optional[str],
        level: str,
        message: str
    ):
        """
        Broadcast a log message from workflow execution
        """
        try:
            tenant_schema = execution.tenant.schema_name
            
            log_message = {
                'type': 'execution_log',
                'execution_id': str(execution.id),
                'node_id': node_id,
                'level': level,
                'message': message,
                'timestamp': timezone.now().isoformat()
            }
            
            # Send to execution group
            await self.channel_layer.group_send(
                f"execution_{tenant_schema}_{execution.id}",
                log_message
            )
            
            logger.debug(f"Broadcasted log: {level} - {message[:50]}...")
            
        except Exception as e:
            logger.error(f"Failed to broadcast log: {e}")
    
    async def broadcast_approval_required(
        self,
        execution,
        approval_id: str,
        node_id: str,
        title: str,
        description: str,
        assigned_to_email: str
    ):
        """
        Broadcast that an approval is required
        """
        try:
            tenant_schema = execution.tenant.schema_name
            
            message = {
                'type': 'approval_required',
                'execution_id': str(execution.id),
                'approval_id': approval_id,
                'node_id': node_id,
                'title': title,
                'description': description,
                'assigned_to': assigned_to_email
            }
            
            # Send to workflow group
            await self.channel_layer.group_send(
                f"workflow_{tenant_schema}_{execution.workflow_id}",
                message
            )
            
            # Send to execution group
            await self.channel_layer.group_send(
                f"execution_{tenant_schema}_{execution.id}",
                message
            )
            
            # Send to tenant-wide group for notifications
            await self.channel_layer.group_send(
                f"workflows_{tenant_schema}",
                message
            )
            
            logger.info(f"Broadcasted approval required: {approval_id} for execution {execution.id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast approval required: {e}")
    
    async def broadcast_workflow_update(self, workflow):
        """
        Broadcast that a workflow has been updated
        """
        try:
            tenant_schema = workflow.tenant.schema_name
            
            message = {
                'type': 'workflow_update',
                'workflow_id': str(workflow.id),
                'data': {
                    'name': workflow.name,
                    'status': workflow.status,
                    'updated_at': workflow.updated_at.isoformat()
                }
            }
            
            # Send to workflow group
            await self.channel_layer.group_send(
                f"workflow_{tenant_schema}_{workflow.id}",
                message
            )
            
            logger.debug(f"Broadcasted workflow update: {workflow.id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast workflow update: {e}")


class SyncWorkflowBroadcaster:
    """
    Synchronous wrapper for WorkflowExecutionBroadcaster
    Use this when calling from synchronous code
    """
    
    def __init__(self, channel_layer=None):
        self.async_broadcaster = WorkflowExecutionBroadcaster(channel_layer)
    
    def broadcast_execution_started(self, execution):
        async_to_sync(self.async_broadcaster.broadcast_execution_started)(execution)
    
    def broadcast_node_started(self, execution, node_id: str, node_type: str):
        async_to_sync(self.async_broadcaster.broadcast_node_started)(
            execution, node_id, node_type
        )
    
    def broadcast_node_completed(
        self,
        execution,
        node_id: str,
        status: str,
        output: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        duration_ms: Optional[int] = None
    ):
        async_to_sync(self.async_broadcaster.broadcast_node_completed)(
            execution, node_id, status, output, error, duration_ms
        )
    
    def broadcast_execution_completed(self, execution):
        async_to_sync(self.async_broadcaster.broadcast_execution_completed)(execution)
    
    def broadcast_execution_log(
        self,
        execution,
        node_id: Optional[str],
        level: str,
        message: str
    ):
        async_to_sync(self.async_broadcaster.broadcast_execution_log)(
            execution, node_id, level, message
        )
    
    def broadcast_approval_required(
        self,
        execution,
        approval_id: str,
        node_id: str,
        title: str,
        description: str,
        assigned_to_email: str
    ):
        async_to_sync(self.async_broadcaster.broadcast_approval_required)(
            execution, approval_id, node_id, title, description, assigned_to_email
        )
    
    def broadcast_workflow_update(self, workflow):
        async_to_sync(self.async_broadcaster.broadcast_workflow_update)(workflow)
