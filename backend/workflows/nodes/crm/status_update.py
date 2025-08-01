"""
Contact Status Update Node Processor - Update contact status and properties
"""
import logging
from typing import Dict, Any, Optional, List
from django.utils import timezone
from asgiref.sync import sync_to_async
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class ContactStatusUpdateProcessor(AsyncNodeProcessor):
    """Process contact status update nodes"""
    
    def __init__(self):
        super().__init__()
        self.node_type = "UPDATE_CONTACT_STATUS"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process contact status update node"""
        
        node_data = node_config.get('data', {})
        
        # Extract configuration
        contact_id_path = node_data.get('contact_id_path', '')
        contact_id = self._get_nested_value(context, contact_id_path) if contact_id_path else None
        new_status = self._format_template(node_data.get('new_status', ''), context)
        status_reason = self._format_template(node_data.get('status_reason', ''), context)
        additional_updates = node_data.get('additional_updates', {})
        create_status_history = node_data.get('create_status_history', True)
        
        # Get execution context
        execution = context.get('execution')
        
        # Validate required fields
        if not contact_id:
            raise ValueError("Contact status update requires contact_id")
        
        if not new_status:
            raise ValueError("Contact status update requires new_status")
        
        try:
            # Get contact record
            from pipelines.models import Record
            contact = await sync_to_async(Record.objects.get)(id=contact_id, is_deleted=False)
            
            # Get previous status for history
            previous_status = contact.data.get('status', 'unknown')
            
            # Prepare update data
            update_data = {
                'status': new_status,
                'status_updated_at': timezone.now().isoformat()
            }
            
            if status_reason:
                update_data['status_reason'] = status_reason
            
            # Add workflow metadata
            if execution:
                update_data['status_updated_by_workflow'] = str(execution.workflow.id)
                update_data['status_updated_by_execution'] = str(execution.id)
                if execution.triggered_by:
                    update_data['status_updated_by_user'] = execution.triggered_by.email
            
            # Process additional updates
            for field_key, field_value in additional_updates.items():
                formatted_value = self._format_template(str(field_value), context)
                update_data[field_key] = formatted_value
            
            # Create status history if requested
            if create_status_history:
                await self._create_status_history_entry(
                    contact, previous_status, new_status, status_reason, execution
                )
            
            # Update contact
            contact.data.update(update_data)
            contact.updated_by = execution.triggered_by if execution else None
            await sync_to_async(contact.save)()
            
            # Log status change
            logger.info(
                f"Contact status updated - ID: {contact_id}, "
                f"Status: {previous_status} → {new_status}, "
                f"Reason: {status_reason or 'N/A'}"
            )
            
            # Trigger status change events
            await self._trigger_status_change_events(
                contact, previous_status, new_status, status_reason, execution
            )
            
            return {
                'success': True,
                'contact_id': contact_id,
                'previous_status': previous_status,
                'new_status': new_status,
                'status_reason': status_reason,
                'additional_updates': list(additional_updates.keys()),
                'status_history_created': create_status_history,
                'updated_at': update_data['status_updated_at']
            }
            
        except Exception as e:
            logger.error(f"Contact status update failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'contact_id': contact_id,
                'attempted_status': new_status
            }
    
    async def _create_status_history_entry(
        self,
        contact,
        previous_status: str,
        new_status: str, 
        status_reason: Optional[str],
        execution
    ):
        """Create status history entry"""
        
        try:
            # Get or create status history
            status_history = contact.data.get('status_history', [])
            
            # Create new history entry
            history_entry = {
                'previous_status': previous_status,
                'new_status': new_status,
                'status_reason': status_reason,
                'changed_at': timezone.now().isoformat(),
                'changed_by_workflow': str(execution.workflow.id) if execution else None,
                'changed_by_execution': str(execution.id) if execution else None,
                'changed_by_user': execution.triggered_by.email if execution and execution.triggered_by else None
            }
            
            # Add to history (keep last 50 entries)
            status_history.append(history_entry)
            if len(status_history) > 50:
                status_history = status_history[-50:]
            
            # Update contact data
            contact.data['status_history'] = status_history
            
            logger.info(f"Status history entry created for contact {contact.id}")
            
        except Exception as e:
            logger.warning(f"Failed to create status history entry: {e}")
    
    async def _trigger_status_change_events(
        self,
        contact,
        previous_status: str,
        new_status: str,
        status_reason: Optional[str],
        execution
    ):
        """Trigger events for status changes"""
        
        try:
            # This would integrate with event system
            # For now, just structured logging
            
            logger.info(
                "Contact Status Changed",
                extra={
                    'event_type': 'contact_status_changed',
                    'contact_id': str(contact.id),
                    'previous_status': previous_status,
                    'new_status': new_status,
                    'status_reason': status_reason,
                    'workflow_id': str(execution.workflow.id) if execution else None,
                    'execution_id': str(execution.id) if execution else None,
                    'pipeline_id': str(contact.pipeline.id)
                }
            )
            
            # TODO: Send to event bus for:
            # - Real-time notifications
            # - Webhook triggers
            # - Analytics updates
            # - Other workflow triggers
            
        except Exception as e:
            logger.warning(f"Failed to trigger status change events: {e}")
    
    def _format_template(self, template: str, context: Dict[str, Any]) -> str:
        """Format template string with context variables"""
        if not template:
            return ''
        
        try:
            return template.format(**context)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return template
        except Exception as e:
            logger.error(f"Template formatting error: {e}")
            return template
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate contact status update node inputs"""
        node_data = node_config.get('data', {})
        
        # Check required fields
        if not node_data.get('contact_id_path'):
            return False
        
        if not node_data.get('new_status'):
            return False
        
        # Validate additional updates
        additional_updates = node_data.get('additional_updates', {})
        if not isinstance(additional_updates, dict):
            return False
        
        # Validate boolean flags
        create_status_history = node_data.get('create_status_history', True)
        if not isinstance(create_status_history, bool):
            return False
        
        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for contact status update node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        node_data = node_config.get('data', {})
        
        # Resolve contact ID for checkpoint
        contact_id_path = node_data.get('contact_id_path', '')
        resolved_contact_id = self._get_nested_value(context, contact_id_path) if contact_id_path else None
        
        checkpoint.update({
            'status_update_config': {
                'contact_id_path': contact_id_path,
                'resolved_contact_id': resolved_contact_id,
                'new_status': self._format_template(node_data.get('new_status', ''), context),
                'status_reason': self._format_template(node_data.get('status_reason', ''), context),
                'additional_updates_count': len(node_data.get('additional_updates', {})),
                'create_status_history': node_data.get('create_status_history', True)
            }
        })
        
        return checkpoint


class FollowUpTaskProcessor(AsyncNodeProcessor):
    """Process follow-up task creation nodes"""
    
    def __init__(self):
        super().__init__()
        self.node_type = "CREATE_FOLLOW_UP_TASK"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process follow-up task creation node"""
        
        node_data = node_config.get('data', {})
        
        # Extract configuration with context formatting
        task_title = self._format_template(node_data.get('task_title', ''), context)
        task_description = self._format_template(node_data.get('task_description', ''), context)
        due_date = self._format_template(node_data.get('due_date', ''), context)
        assigned_to_id = node_data.get('assigned_to_id')
        priority = node_data.get('priority', 'normal')  # low, normal, high, urgent
        task_type = node_data.get('task_type', 'follow_up')  # follow_up, call, email, meeting, etc.
        
        # Related entities
        contact_id_path = node_data.get('contact_id_path', '')
        contact_id = self._get_nested_value(context, contact_id_path) if contact_id_path else None
        
        # Get execution context
        execution = context.get('execution')
        
        # Validate required fields
        if not task_title:
            raise ValueError("Follow-up task requires task_title")
        
        try:
            # Create task record
            task_data = await self._create_task_record(
                title=task_title,
                description=task_description,
                due_date=due_date,
                assigned_to_id=assigned_to_id,
                priority=priority,
                task_type=task_type,
                contact_id=contact_id,
                execution=execution,
                context=context
            )
            
            # Send task notification
            if assigned_to_id:
                await self._send_task_assignment_notification(task_data, assigned_to_id)
            
            # Update contact with task reference if applicable
            if contact_id:
                await self._link_task_to_contact(contact_id, task_data['id'])
            
            return {
                'success': True,
                'task_id': task_data['id'],
                'title': task_title,
                'description': task_description,
                'due_date': due_date,
                'assigned_to_id': assigned_to_id,
                'priority': priority,
                'task_type': task_type,
                'contact_id': contact_id,
                'created_at': task_data['created_at']
            }
            
        except Exception as e:
            logger.error(f"Follow-up task creation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'task_title': task_title,
                'assigned_to_id': assigned_to_id
            }
    
    async def _create_task_record(
        self,
        title: str,
        description: str,
        due_date: str,
        assigned_to_id: Optional[str],
        priority: str,
        task_type: str,
        contact_id: Optional[str],
        execution,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create task record"""
        
        try:
            import uuid
            
            # Parse due date if provided
            parsed_due_date = None
            if due_date:
                try:
                    from datetime import datetime
                    if 'T' in due_date:
                        parsed_due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    else:
                        parsed_due_date = datetime.strptime(due_date, '%Y-%m-%d')
                except ValueError:
                    logger.warning(f"Invalid due date format: {due_date}")
            
            # Create task data
            task_data = {
                'id': str(uuid.uuid4()),
                'title': title,
                'description': description,
                'due_date': parsed_due_date.isoformat() if parsed_due_date else None,
                'assigned_to_id': assigned_to_id,
                'priority': priority,
                'task_type': task_type,
                'status': 'pending',
                'contact_id': contact_id,
                'created_via_workflow': True,
                'created_at': timezone.now().isoformat(),
                'workflow_id': str(execution.workflow.id) if execution else None,
                'execution_id': str(execution.id) if execution else None,
                'created_by': execution.triggered_by.id if execution and execution.triggered_by else None
            }
            
            # TODO: Store in task management system/table
            # This would typically create a Task record
            
            logger.info(
                f"Follow-up task created - ID: {task_data['id']}, "
                f"Title: {title}, Assigned to: {assigned_to_id or 'Unassigned'}"
            )
            
            return task_data
            
        except Exception as e:
            logger.error(f"Failed to create task record: {e}")
            raise
    
    async def _send_task_assignment_notification(self, task_data: Dict[str, Any], assigned_to_id: str):
        """Send notification about task assignment"""
        
        try:
            # This would integrate with notification system
            logger.info(
                f"Task assignment notification sent - Task: {task_data['id']}, "
                f"Assigned to: {assigned_to_id}"
            )
            
            # TODO: Use notification processor to send notification
            
        except Exception as e:
            logger.warning(f"Failed to send task assignment notification: {e}")
    
    async def _link_task_to_contact(self, contact_id: str, task_id: str):
        """Link task to contact record"""
        
        try:
            from pipelines.models import Record
            
            # Get contact and add task reference
            contact = await sync_to_async(Record.objects.get)(id=contact_id, is_deleted=False)
            
            # Add task to contact's task list
            contact_tasks = contact.data.get('tasks', [])
            contact_tasks.append({
                'task_id': task_id,
                'created_at': timezone.now().isoformat(),
                'task_type': 'follow_up'
            })
            
            # Keep only last 20 tasks
            if len(contact_tasks) > 20:
                contact_tasks = contact_tasks[-20:]
            
            contact.data['tasks'] = contact_tasks
            await sync_to_async(contact.save)()
            
            logger.info(f"Task {task_id} linked to contact {contact_id}")
            
        except Exception as e:
            logger.warning(f"Failed to link task to contact: {e}")
    
    def _format_template(self, template: str, context: Dict[str, Any]) -> str:
        """Format template string with context variables"""
        if not template:
            return ''
        
        try:
            return template.format(**context)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return template
        except Exception as e:
            logger.error(f"Template formatting error: {e}")
            return template
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate follow-up task node inputs"""
        node_data = node_config.get('data', {})
        
        # Check required fields
        if not node_data.get('task_title'):
            return False
        
        # Validate priority
        priority = node_data.get('priority', 'normal')
        valid_priorities = ['low', 'normal', 'high', 'urgent']
        if priority not in valid_priorities:
            return False
        
        # Validate task type
        task_type = node_data.get('task_type', 'follow_up')
        valid_task_types = ['follow_up', 'call', 'email', 'meeting', 'demo', 'proposal', 'contract', 'other']
        if task_type not in valid_task_types:
            return False
        
        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for follow-up task node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        node_data = node_config.get('data', {})
        
        # Resolve contact ID for checkpoint
        contact_id_path = node_data.get('contact_id_path', '')
        resolved_contact_id = self._get_nested_value(context, contact_id_path) if contact_id_path else None
        
        checkpoint.update({
            'task_config': {
                'task_title': self._format_template(node_data.get('task_title', ''), context),
                'task_description': self._format_template(node_data.get('task_description', ''), context),
                'due_date': self._format_template(node_data.get('due_date', ''), context),
                'assigned_to_id': node_data.get('assigned_to_id'),
                'priority': node_data.get('priority', 'normal'),
                'task_type': node_data.get('task_type', 'follow_up'),
                'contact_id_path': contact_id_path,
                'resolved_contact_id': resolved_contact_id
            }
        })
        
        return checkpoint