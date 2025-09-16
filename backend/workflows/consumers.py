"""
WebSocket consumers for real-time workflow updates
"""
import json
import logging
from typing import Dict, Any, Optional
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)
User = get_user_model()


class WorkflowConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for real-time workflow execution updates
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.tenant = None
        self.workflow_groups = set()
        self.execution_groups = set()
    
    async def connect(self):
        """Handle WebSocket connection"""
        try:
            # Get user from scope (requires authentication middleware)
            self.user = self.scope.get('user')
            
            if not self.user or not self.user.is_authenticated:
                logger.warning("Unauthenticated WebSocket connection attempt")
                await self.close(code=4001)
                return
            
            # Get tenant from user or URL
            self.tenant = await self.get_user_tenant()
            if not self.tenant:
                logger.warning(f"No tenant found for user {self.user.email}")
                await self.close(code=4002)
                return
            
            # Accept connection
            await self.accept()
            
            # Join tenant-wide workflow updates group
            tenant_group = f"workflows_{self.tenant.schema_name}"
            await self.channel_layer.group_add(tenant_group, self.channel_name)
            self.workflow_groups.add(tenant_group)
            
            # Send connection confirmation
            await self.send_json({
                'type': 'connection',
                'status': 'connected',
                'tenant': self.tenant.schema_name,
                'user': self.user.email
            })
            
            logger.info(f"WebSocket connected: {self.user.email} on {self.tenant.schema_name}")
            
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            await self.close(code=4000)
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        try:
            # Leave all groups
            for group in self.workflow_groups:
                await self.channel_layer.group_discard(group, self.channel_name)
            
            for group in self.execution_groups:
                await self.channel_layer.group_discard(group, self.channel_name)
            
            logger.info(f"WebSocket disconnected: {self.user.email if self.user else 'unknown'}")
            
        except Exception as e:
            logger.error(f"WebSocket disconnect error: {e}")
    
    async def receive_json(self, content: Dict[str, Any]):
        """Handle incoming WebSocket messages"""
        try:
            message_type = content.get('type')
            
            if message_type == 'subscribe_workflow':
                await self.subscribe_to_workflow(content.get('workflow_id'))
            
            elif message_type == 'subscribe_execution':
                await self.subscribe_to_execution(content.get('execution_id'))
            
            elif message_type == 'unsubscribe_workflow':
                await self.unsubscribe_from_workflow(content.get('workflow_id'))
            
            elif message_type == 'unsubscribe_execution':
                await self.unsubscribe_from_execution(content.get('execution_id'))
            
            elif message_type == 'ping':
                await self.send_json({'type': 'pong'})
            
            else:
                await self.send_json({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                })
        
        except Exception as e:
            logger.error(f"WebSocket receive error: {e}")
            await self.send_json({
                'type': 'error',
                'message': str(e)
            })
    
    async def subscribe_to_workflow(self, workflow_id: str):
        """Subscribe to workflow updates"""
        if not workflow_id:
            return
        
        # Verify user has access to this workflow
        if not await self.user_can_access_workflow(workflow_id):
            await self.send_json({
                'type': 'error',
                'message': 'Access denied to workflow'
            })
            return
        
        # Join workflow-specific group
        group_name = f"workflow_{self.tenant.schema_name}_{workflow_id}"
        await self.channel_layer.group_add(group_name, self.channel_name)
        self.workflow_groups.add(group_name)
        
        await self.send_json({
            'type': 'subscribed',
            'workflow_id': workflow_id
        })
    
    async def subscribe_to_execution(self, execution_id: str):
        """Subscribe to specific execution updates"""
        if not execution_id:
            return
        
        # Verify user has access to this execution
        if not await self.user_can_access_execution(execution_id):
            await self.send_json({
                'type': 'error',
                'message': 'Access denied to execution'
            })
            return
        
        # Join execution-specific group
        group_name = f"execution_{self.tenant.schema_name}_{execution_id}"
        await self.channel_layer.group_add(group_name, self.channel_name)
        self.execution_groups.add(group_name)
        
        await self.send_json({
            'type': 'subscribed',
            'execution_id': execution_id
        })
    
    async def unsubscribe_from_workflow(self, workflow_id: str):
        """Unsubscribe from workflow updates"""
        if not workflow_id:
            return
        
        group_name = f"workflow_{self.tenant.schema_name}_{workflow_id}"
        if group_name in self.workflow_groups:
            await self.channel_layer.group_discard(group_name, self.channel_name)
            self.workflow_groups.remove(group_name)
        
        await self.send_json({
            'type': 'unsubscribed',
            'workflow_id': workflow_id
        })
    
    async def unsubscribe_from_execution(self, execution_id: str):
        """Unsubscribe from execution updates"""
        if not execution_id:
            return
        
        group_name = f"execution_{self.tenant.schema_name}_{execution_id}"
        if group_name in self.execution_groups:
            await self.channel_layer.group_discard(group_name, self.channel_name)
            self.execution_groups.remove(group_name)
        
        await self.send_json({
            'type': 'unsubscribed',
            'execution_id': execution_id
        })
    
    # Channel layer message handlers
    async def workflow_update(self, event: Dict[str, Any]):
        """Handle workflow update messages from channel layer"""
        await self.send_json({
            'type': 'workflow_update',
            'workflow_id': event.get('workflow_id'),
            'data': event.get('data')
        })
    
    async def execution_started(self, event: Dict[str, Any]):
        """Handle execution started messages"""
        await self.send_json({
            'type': 'execution_started',
            'execution_id': event.get('execution_id'),
            'workflow_id': event.get('workflow_id'),
            'started_at': event.get('started_at'),
            'triggered_by': event.get('triggered_by')
        })
    
    async def execution_node_started(self, event: Dict[str, Any]):
        """Handle node execution started messages"""
        await self.send_json({
            'type': 'node_started',
            'execution_id': event.get('execution_id'),
            'node_id': event.get('node_id'),
            'node_type': event.get('node_type'),
            'started_at': event.get('started_at')
        })
    
    async def execution_node_completed(self, event: Dict[str, Any]):
        """Handle node execution completed messages"""
        await self.send_json({
            'type': 'node_completed',
            'execution_id': event.get('execution_id'),
            'node_id': event.get('node_id'),
            'status': event.get('status'),
            'output': event.get('output'),
            'error': event.get('error'),
            'completed_at': event.get('completed_at'),
            'duration_ms': event.get('duration_ms')
        })
    
    async def execution_completed(self, event: Dict[str, Any]):
        """Handle execution completed messages"""
        await self.send_json({
            'type': 'execution_completed',
            'execution_id': event.get('execution_id'),
            'status': event.get('status'),
            'completed_at': event.get('completed_at'),
            'duration_ms': event.get('duration_ms'),
            'error': event.get('error')
        })
    
    async def execution_log(self, event: Dict[str, Any]):
        """Handle execution log messages"""
        await self.send_json({
            'type': 'execution_log',
            'execution_id': event.get('execution_id'),
            'node_id': event.get('node_id'),
            'level': event.get('level'),
            'message': event.get('message'),
            'timestamp': event.get('timestamp')
        })
    
    async def approval_required(self, event: Dict[str, Any]):
        """Handle approval required messages"""
        await self.send_json({
            'type': 'approval_required',
            'execution_id': event.get('execution_id'),
            'approval_id': event.get('approval_id'),
            'node_id': event.get('node_id'),
            'title': event.get('title'),
            'description': event.get('description'),
            'assigned_to': event.get('assigned_to')
        })
    
    # Helper methods
    @database_sync_to_async
    def get_user_tenant(self):
        """Get tenant for the current user"""
        try:
            from tenants.models import Tenant
            
            # Try to get tenant from user's organization
            if hasattr(self.user, 'tenant'):
                return self.user.tenant
            
            # Try to get tenant from domain in scope
            host = self.scope.get('headers', {}).get(b'host', b'').decode('utf-8')
            if host:
                from tenants.models import Domain
                domain = Domain.objects.filter(domain=host).first()
                if domain:
                    return domain.tenant
            
            # Get default/first tenant for user
            return Tenant.objects.filter(
                users__id=self.user.id
            ).first()
            
        except Exception as e:
            logger.error(f"Failed to get user tenant: {e}")
            return None
    
    @database_sync_to_async
    def user_can_access_workflow(self, workflow_id: str) -> bool:
        """Check if user can access a workflow"""
        try:
            with schema_context(self.tenant.schema_name):
                from workflows.models import Workflow
                from authentication.permissions import SyncPermissionManager
                
                # Check if workflow exists
                try:
                    workflow = Workflow.objects.get(id=workflow_id)
                except Workflow.DoesNotExist:
                    return False
                
                # Check permissions
                permission_manager = SyncPermissionManager(self.user)
                return permission_manager.has_permission(
                    'workflows', 'workflow', 'view', workflow_id
                )
        
        except Exception as e:
            logger.error(f"Error checking workflow access: {e}")
            return False
    
    @database_sync_to_async
    def user_can_access_execution(self, execution_id: str) -> bool:
        """Check if user can access an execution"""
        try:
            with schema_context(self.tenant.schema_name):
                from workflows.models import WorkflowExecution
                from authentication.permissions import SyncPermissionManager
                
                # Check if execution exists
                try:
                    execution = WorkflowExecution.objects.get(id=execution_id)
                except WorkflowExecution.DoesNotExist:
                    return False
                
                # Check permissions on the workflow
                permission_manager = SyncPermissionManager(self.user)
                return permission_manager.has_permission(
                    'workflows', 'workflow', 'view', str(execution.workflow_id)
                )
        
        except Exception as e:
            logger.error(f"Error checking execution access: {e}")
            return False


class WorkflowCollaborationConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for collaborative workflow editing
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.tenant = None
        self.workflow_id = None
        self.collaboration_group = None
    
    async def connect(self):
        """Handle WebSocket connection for collaboration"""
        try:
            # Get user and workflow ID from URL
            self.user = self.scope.get('user')
            self.workflow_id = self.scope['url_route']['kwargs'].get('workflow_id')
            
            if not self.user or not self.user.is_authenticated:
                await self.close(code=4001)
                return
            
            # Get tenant
            self.tenant = await self.get_user_tenant()
            if not self.tenant:
                await self.close(code=4002)
                return
            
            # Verify access to workflow
            if not await self.user_can_edit_workflow(self.workflow_id):
                await self.close(code=4003)
                return
            
            # Accept connection
            await self.accept()
            
            # Join collaboration group
            self.collaboration_group = f"collab_{self.tenant.schema_name}_{self.workflow_id}"
            await self.channel_layer.group_add(self.collaboration_group, self.channel_name)
            
            # Notify others of new collaborator
            await self.channel_layer.group_send(
                self.collaboration_group,
                {
                    'type': 'collaborator_joined',
                    'user_id': str(self.user.id),
                    'user_email': self.user.email,
                    'user_name': f"{self.user.first_name} {self.user.last_name}".strip()
                }
            )
            
            logger.info(f"Collaboration session started: {self.user.email} on workflow {self.workflow_id}")
            
        except Exception as e:
            logger.error(f"Collaboration connection error: {e}")
            await self.close(code=4000)
    
    async def disconnect(self, close_code):
        """Handle disconnection from collaboration"""
        try:
            if self.collaboration_group:
                # Notify others of collaborator leaving
                await self.channel_layer.group_send(
                    self.collaboration_group,
                    {
                        'type': 'collaborator_left',
                        'user_id': str(self.user.id) if self.user else None
                    }
                )
                
                # Leave group
                await self.channel_layer.group_discard(
                    self.collaboration_group,
                    self.channel_name
                )
            
        except Exception as e:
            logger.error(f"Collaboration disconnect error: {e}")
    
    async def receive_json(self, content: Dict[str, Any]):
        """Handle incoming collaboration messages"""
        try:
            message_type = content.get('type')
            
            if message_type == 'cursor_position':
                # Broadcast cursor position to other collaborators
                await self.channel_layer.group_send(
                    self.collaboration_group,
                    {
                        'type': 'cursor_update',
                        'user_id': str(self.user.id),
                        'position': content.get('position')
                    }
                )
            
            elif message_type == 'node_selected':
                # Broadcast node selection
                await self.channel_layer.group_send(
                    self.collaboration_group,
                    {
                        'type': 'selection_update',
                        'user_id': str(self.user.id),
                        'node_id': content.get('node_id')
                    }
                )
            
            elif message_type == 'definition_update':
                # Broadcast workflow definition changes
                await self.channel_layer.group_send(
                    self.collaboration_group,
                    {
                        'type': 'definition_changed',
                        'user_id': str(self.user.id),
                        'changes': content.get('changes')
                    }
                )
            
        except Exception as e:
            logger.error(f"Collaboration receive error: {e}")
            await self.send_json({
                'type': 'error',
                'message': str(e)
            })
    
    # Channel layer message handlers
    async def collaborator_joined(self, event: Dict[str, Any]):
        """Handle collaborator joined messages"""
        if event.get('user_id') != str(self.user.id):
            await self.send_json({
                'type': 'collaborator_joined',
                'user_id': event.get('user_id'),
                'user_email': event.get('user_email'),
                'user_name': event.get('user_name')
            })
    
    async def collaborator_left(self, event: Dict[str, Any]):
        """Handle collaborator left messages"""
        if event.get('user_id') != str(self.user.id):
            await self.send_json({
                'type': 'collaborator_left',
                'user_id': event.get('user_id')
            })
    
    async def cursor_update(self, event: Dict[str, Any]):
        """Handle cursor position updates"""
        if event.get('user_id') != str(self.user.id):
            await self.send_json({
                'type': 'cursor_update',
                'user_id': event.get('user_id'),
                'position': event.get('position')
            })
    
    async def selection_update(self, event: Dict[str, Any]):
        """Handle selection updates"""
        if event.get('user_id') != str(self.user.id):
            await self.send_json({
                'type': 'selection_update',
                'user_id': event.get('user_id'),
                'node_id': event.get('node_id')
            })
    
    async def definition_changed(self, event: Dict[str, Any]):
        """Handle definition change updates"""
        if event.get('user_id') != str(self.user.id):
            await self.send_json({
                'type': 'definition_changed',
                'user_id': event.get('user_id'),
                'changes': event.get('changes')
            })
    
    # Helper methods
    @database_sync_to_async
    def get_user_tenant(self):
        """Get tenant for the current user"""
        try:
            from tenants.models import Tenant
            
            # Get tenant from user or domain
            if hasattr(self.user, 'tenant'):
                return self.user.tenant
            
            return Tenant.objects.filter(users__id=self.user.id).first()
            
        except Exception as e:
            logger.error(f"Failed to get user tenant: {e}")
            return None
    
    @database_sync_to_async
    def user_can_edit_workflow(self, workflow_id: str) -> bool:
        """Check if user can edit a workflow"""
        try:
            with schema_context(self.tenant.schema_name):
                from workflows.models import Workflow
                from authentication.permissions import SyncPermissionManager
                
                # Check if workflow exists
                try:
                    workflow = Workflow.objects.get(id=workflow_id)
                except Workflow.DoesNotExist:
                    return False
                
                # Check edit permissions
                permission_manager = SyncPermissionManager(self.user)
                return permission_manager.has_permission(
                    'workflows', 'workflow', 'edit', workflow_id
                )
        
        except Exception as e:
            logger.error(f"Error checking workflow edit access: {e}")
            return False
