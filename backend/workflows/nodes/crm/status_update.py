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

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["contact_id_path", "new_status"],
        "properties": {
            "contact_id_path": {
                "type": "string",
                "description": "Path to contact ID in context",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "contact.id or resolved_contact_id"
                }
            },
            "new_status": {
                "type": "string",
                "description": "New status for the contact",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "{{status}} or qualified"
                }
            },
            "status_reason": {
                "type": "string",
                "description": "Reason for status change",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 2,
                    "placeholder": "Qualified based on meeting outcome"
                }
            },
            "create_status_history": {
                "type": "boolean",
                "default": True,
                "description": "Create status history entry"
            },
            "additional_updates": {
                "type": "object",
                "description": "Additional fields to update",
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 4,
                    "section": "advanced",
                    "placeholder": '{"stage": "opportunity", "score": 85}'
                }
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "update_contact_status"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process contact status update node"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Extract configuration
        contact_id_path = config.get('contact_id_path', '')
        contact_id = self._get_nested_value(context, contact_id_path) if contact_id_path else None
        new_status = self._format_template(config.get('new_status', ''), context)
        status_reason = self._format_template(config.get('status_reason', ''), context)
        additional_updates = config.get('additional_updates', {})
        create_status_history = config.get('create_status_history', True)
        
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

        import re

        # Handle {{variable}} syntax by replacing with actual values from context
        def replace_variable(match):
            var_path = match.group(1).strip()

            # Try to get the value from context
            parts = var_path.split('.')

            # Special handling for node references
            if parts[0].startswith('node-'):
                # First part is a node reference - context stores as node_{id}
                node_key = f"node_{parts[0]}"

                # Try the node_ prefix format first (how engine stores it)
                if node_key in context:
                    value = context[node_key]
                    # Now traverse the rest of the path
                    for part in parts[1:]:
                        # Check in form_data first for form submission nodes
                        if isinstance(value, dict):
                            if 'form_data' in value and part in value['form_data']:
                                value = value['form_data'][part]
                            elif part in value:
                                value = value[part]
                            else:
                                logger.warning(f"Field {part} not found in node {parts[0]} outputs")
                                return match.group(0)  # Return original if not found
                        else:
                            logger.warning(f"Cannot traverse {part} in non-dict value")
                            return match.group(0)
                    return str(value) if value is not None else ''
                else:
                    logger.warning(f"Node {parts[0]} (as {node_key}) not found in context")
                    return match.group(0)  # Return original if not found
            else:
                # Regular context traversal
                value = context
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        logger.warning(f"Variable {var_path} not found in context")
                        return match.group(0)  # Return original if not found
                return str(value) if value is not None else ''

        # Replace {{variable}} patterns
        result = re.sub(r'\{\{([^}]+)\}\}', replace_variable, template)

        # If no replacements were made and the template looks like it needs values, return empty
        if result == template and '{{' in template:
            logger.warning(f"No template variables were replaced in: {template}")
            # For required fields, return empty string to trigger validation
            return ''

        return result
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate contact status update node inputs"""
        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Check required fields
        if not config.get('contact_id_path'):
            return False

        if not config.get('new_status'):
            return False

        # Validate additional updates
        additional_updates = config.get('additional_updates', {})
        if not isinstance(additional_updates, dict):
            return False

        # Validate boolean flags
        create_status_history = config.get('create_status_history', True)
        if not isinstance(create_status_history, bool):
            return False

        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for contact status update node"""
        checkpoint = await super().create_checkpoint(node_config, context)

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Resolve contact ID for checkpoint
        contact_id_path = config.get('contact_id_path', '')
        resolved_contact_id = self._get_nested_value(context, contact_id_path) if contact_id_path else None

        checkpoint.update({
            'status_update_config': {
                'contact_id_path': contact_id_path,
                'resolved_contact_id': resolved_contact_id,
                'new_status': self._format_template(config.get('new_status', ''), context),
                'status_reason': self._format_template(config.get('status_reason', ''), context),
                'additional_updates_count': len(config.get('additional_updates', {})),
                'create_status_history': config.get('create_status_history', True)
            }
        })

        return checkpoint


class FollowUpTaskProcessor(AsyncNodeProcessor):
    """Process follow-up task creation nodes"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["task_title"],
        "properties": {
            "task_title": {
                "type": "string",
                "minLength": 1,
                "description": "Title of the follow-up task",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "Follow up with {{contact.name}}"
                }
            },
            "task_description": {
                "type": "string",
                "description": "Task description",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 4,
                    "placeholder": "Review meeting notes and send proposal to {{contact.email}}"
                }
            },
            "due_date_type": {
                "type": "string",
                "enum": ["days_from_now", "specific_date", "business_days"],
                "default": "days_from_now",
                "description": "How to calculate due date",
                "ui_hints": {
                    "widget": "radio"
                }
            },
            "due_date_value": {
                "type": "integer",
                "minimum": 0,
                "maximum": 365,
                "default": 1,
                "description": "Number of days from now",
                "ui_hints": {
                    "show_when": {"due_date_type": ["days_from_now", "business_days"]}
                }
            },
            "due_date": {
                "type": "string",
                "format": "date-time",
                "description": "Specific due date",
                "ui_hints": {
                    "widget": "datetime",
                    "show_when": {"due_date_type": "specific_date"}
                }
            },
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high", "urgent"],
                "default": "medium",
                "description": "Task priority",
                "ui_hints": {
                    "widget": "select"
                }
            },
            "assign_to": {
                "type": "string",
                "description": "User to assign the task to",
                "ui_hints": {
                    "widget": "user_select",
                    "placeholder": "{{assigned_user.id}}"
                }
            },
            "related_contact_id_path": {
                "type": "string",
                "description": "Path to related contact ID",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "contact.id",
                    "section": "advanced"
                }
            },
            "task_type": {
                "type": "string",
                "enum": ["call", "email", "meeting", "review", "proposal", "other"],
                "default": "other",
                "description": "Type of follow-up task",
                "ui_hints": {
                    "widget": "select"
                }
            },
            "auto_complete_when_done": {
                "type": "boolean",
                "default": False,
                "description": "Auto-complete task when workflow completes",
                "ui_hints": {
                    "section": "advanced"
                }
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "create_follow_up_task"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process follow-up task creation node"""
        import re

        node_data = node_config.get('data', {})

        # Handle both direct config and nested config.config structure
        if 'config' in node_data and isinstance(node_data['config'], dict):
            # Frontend sends config nested under data.config
            config = node_data['config']
        else:
            # Direct configuration
            config = node_data

        # Log the context to debug template variable resolution
        logger.info(f"FollowUpTaskProcessor context keys: {context.keys()}")

        # Check what node outputs we have
        for key in context.keys():
            if key.startswith('node_'):
                logger.info(f"  {key}: {context[key].keys() if isinstance(context[key], dict) else type(context[key])}")
                if isinstance(context[key], dict) and 'form_data' in context[key]:
                    logger.info(f"    form_data: {context[key]['form_data']}")

        logger.info(f"FollowUpTaskProcessor task_title template: {config.get('task_title', '')}")

        # Extract configuration with context formatting
        task_title = self._format_template(config.get('task_title', ''), context)
        task_description = self._format_template(config.get('task_description', ''), context)

        logger.info(f"FollowUpTaskProcessor task_title after formatting: {task_title}")

        # Check if variables were properly resolved
        if '{{' in task_title:
            missing_vars = re.findall(r'\{\{([^}]+)\}\}', task_title)
            raise ValueError(f"Task title contains unresolved variables: {missing_vars}. Please ensure previous nodes provide: {', '.join(missing_vars)}")

        # Handle due date calculation based on type
        due_date = await self._calculate_due_date(config, context)

        # Handle assignment
        assigned_to_id = await self._resolve_assignment(config, context)

        # Map priority to Task model values
        priority_map = {
            'low': 'low',
            'medium': 'medium',
            'high': 'high',
            'urgent': 'urgent',
            'normal': 'medium'  # Map 'normal' to 'medium' for compatibility
        }
        priority = priority_map.get(config.get('priority', 'medium'), 'medium')

        # Status (always starts as pending for new tasks)
        status = config.get('status', 'pending')

        # Related record
        related_record_id = self._format_template(str(config.get('related_record_id', '')), context)
        if not related_record_id:
            # Try to get record from context or trigger_data
            if context.get('record'):
                related_record_id = str(context['record'].get('id', ''))
            elif context.get('trigger_data', {}).get('record_id'):
                related_record_id = str(context['trigger_data']['record_id'])
            elif context.get('trigger_data', {}).get('record_data', {}).get('id'):
                related_record_id = str(context['trigger_data']['record_data']['id'])

        # Check if record ID contains unresolved variables
        if '{{' in str(related_record_id):
            missing_vars = re.findall(r'\{\{([^}]+)\}\}', str(related_record_id))
            raise ValueError(f"Related record ID contains unresolved variables: {missing_vars}. Please ensure previous nodes provide: {', '.join(missing_vars)}")

        # Reminder settings
        reminder_at = await self._calculate_reminder(config, due_date)

        # Checklist items
        initial_checklist = config.get('initial_checklist', [])
        
        # Get execution context
        execution = context.get('execution')

        # Validate required fields
        if not task_title:
            raise ValueError("Follow-up task requires task_title")

        if not related_record_id:
            raise ValueError("Follow-up task requires a related record")
        
        try:
            # Create actual Task model instance
            task = await self._create_task_record(
                title=task_title,
                description=task_description,
                due_date=due_date,
                reminder_at=reminder_at,
                assigned_to_id=assigned_to_id,
                priority=priority,
                status=status,
                related_record_id=related_record_id,
                initial_checklist=initial_checklist,
                metadata=config.get('additional_context', {}),
                execution=execution
            )

            # Send task notification if configured
            notification_settings = config.get('notification_settings', {})
            if notification_settings.get('notify_assignee', True) and assigned_to_id:
                await self._send_task_assignment_notification(task, assigned_to_id)
            
            return {
                'success': True,
                'task_id': str(task.id),
                'title': task.title,
                'description': task.description,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'assigned_to_id': str(task.assigned_to_id) if task.assigned_to_id else None,
                'priority': task.priority,
                'status': task.status,
                'record_id': str(task.record_id) if task.record_id else None,
                'checklist_items_count': await sync_to_async(task.checklist_items.count)(),
                'created_at': task.created_at.isoformat()
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
        due_date: Optional[timezone.datetime],
        reminder_at: Optional[timezone.datetime],
        assigned_to_id: Optional[str],
        priority: str,
        status: str,
        related_record_id: str,
        initial_checklist: List[str],
        metadata: Dict[str, Any],
        execution
    ) -> Any:
        """Create actual Task model record"""

        try:
            from tasks.models import Task, TaskChecklistItem
            from pipelines.models import Record
            from django.contrib.auth import get_user_model

            User = get_user_model()

            # Get the related record
            try:
                record = await sync_to_async(Record.objects.get)(
                    id=related_record_id,
                    is_deleted=False
                )
            except Record.DoesNotExist:
                raise ValueError(f"Record {related_record_id} not found")

            # Get the assigned user if specified
            assigned_to = None
            if assigned_to_id:
                try:
                    assigned_to = await sync_to_async(User.objects.get)(id=assigned_to_id)
                except User.DoesNotExist:
                    logger.warning(f"Assigned user {assigned_to_id} not found, task will be unassigned")

            # Add workflow metadata
            task_metadata = metadata or {}
            task_metadata.update({
                'created_via_workflow': True,
                'workflow_id': str(execution.workflow.id) if execution else None,
                'execution_id': str(execution.id) if execution else None,
                'workflow_node': self.node_type
            })

            # Create the task
            task = await sync_to_async(Task.objects.create)(
                title=title,
                description=description or '',
                priority=priority,
                status=status,
                due_date=due_date,
                reminder_at=reminder_at,
                record=record,
                assigned_to=assigned_to,
                created_by=execution.triggered_by if execution and execution.triggered_by else None,
                metadata=task_metadata
            )

            # Create checklist items if provided
            if initial_checklist:
                for index, item_text in enumerate(initial_checklist):
                    if item_text.strip():
                        await sync_to_async(TaskChecklistItem.objects.create)(
                            task=task,
                            text=item_text.strip(),
                            order=index
                        )

            logger.info(
                f"Task created - ID: {task.id}, "
                f"Title: {title}, "
                f"Record: {record.id}, "
                f"Assigned to: {assigned_to.email if assigned_to else 'Unassigned'}"
            )

            return task

        except Exception as e:
            logger.error(f"Failed to create task record: {e}")
            raise
    
    async def _calculate_due_date(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[timezone.datetime]:
        """Calculate due date based on configuration"""
        from datetime import datetime, timedelta

        due_date_type = node_data.get('due_date_type', 'relative')

        if due_date_type == 'relative':
            days = int(node_data.get('relative_days', 1))
            due_date = timezone.now() + timedelta(days=days)
        elif due_date_type == 'business_days':
            # Simple business days calculation (skip weekends)
            business_days = int(node_data.get('business_days', 1))
            due_date = timezone.now()
            days_added = 0
            while days_added < business_days:
                due_date += timedelta(days=1)
                if due_date.weekday() < 5:  # Monday = 0, Friday = 4
                    days_added += 1
        elif due_date_type == 'specific':
            specific_date = node_data.get('specific_date')
            if specific_date:
                try:
                    due_date = datetime.fromisoformat(specific_date.replace('Z', '+00:00'))
                    due_date = timezone.make_aware(due_date) if timezone.is_naive(due_date) else due_date
                except ValueError:
                    logger.warning(f"Invalid specific date: {specific_date}")
                    due_date = None
            else:
                due_date = None
        elif due_date_type == 'field':
            date_field = self._format_template(node_data.get('date_field', ''), context)
            if date_field:
                try:
                    due_date = datetime.fromisoformat(date_field.replace('Z', '+00:00'))
                    due_date = timezone.make_aware(due_date) if timezone.is_naive(due_date) else due_date
                except (ValueError, AttributeError):
                    logger.warning(f"Invalid date from field: {date_field}")
                    due_date = None
            else:
                due_date = None
        else:
            due_date = None

        # Add time if specified
        if due_date and node_data.get('due_time'):
            try:
                time_parts = node_data['due_time'].split(':')
                due_date = due_date.replace(
                    hour=int(time_parts[0]),
                    minute=int(time_parts[1]) if len(time_parts) > 1 else 0
                )
            except (ValueError, IndexError):
                logger.warning(f"Invalid time format: {node_data.get('due_time')}")

        return due_date

    async def _calculate_reminder(self, node_data: Dict[str, Any], due_date: Optional[timezone.datetime]) -> Optional[timezone.datetime]:
        """Calculate reminder time based on configuration"""
        if not due_date or not node_data.get('reminder', True):
            return None

        reminder_minutes = int(node_data.get('reminder_minutes', '60'))
        from datetime import timedelta
        reminder_at = due_date - timedelta(minutes=reminder_minutes)

        return reminder_at

    async def _resolve_assignment(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[str]:
        """Resolve task assignment based on configuration"""
        assignment_type = node_data.get('assignment_type', 'specific_user')

        if assignment_type == 'specific_user':
            return node_data.get('assigned_to')
        elif assignment_type == 'current_user':
            execution = context.get('execution')
            if execution and execution.triggered_by:
                return str(execution.triggered_by.id)
        elif assignment_type == 'record_owner':
            record = context.get('record')
            if record and record.get('assigned_to_id'):
                return str(record['assigned_to_id'])
        elif assignment_type == 'field':
            field_value = self._format_template(node_data.get('assignment_field', ''), context)
            return field_value if field_value else None
        elif assignment_type == 'round_robin':
            # TODO: Implement round robin logic
            pool = node_data.get('round_robin_pool', [])
            if pool:
                # Simple rotation for now
                import hashlib
                execution = context.get('execution')
                if execution:
                    hash_val = int(hashlib.md5(str(execution.id).encode()).hexdigest(), 16)
                    return pool[hash_val % len(pool)]

        return None

    async def _send_task_assignment_notification(self, task: Any, assigned_to_id: str):
        """Send notification about task assignment"""

        try:
            # This would integrate with notification system
            logger.info(
                f"Task assignment notification sent - Task: {task.id}, "
                f"Title: {task.title}, "
                f"Assigned to: {assigned_to_id}"
            )

            # TODO: Integrate with notification processor to send actual notification
            # For now, the task creation itself will trigger any configured notifications

        except Exception as e:
            logger.warning(f"Failed to send task assignment notification: {e}")
    
    def _format_template(self, template: str, context: Dict[str, Any]) -> str:
        """Format template string with context variables"""
        if not template:
            return ''

        import re

        # Handle {{variable}} syntax by replacing with actual values from context
        def replace_variable(match):
            var_path = match.group(1).strip()

            # Try to get the value from context
            parts = var_path.split('.')

            # Special handling for node references
            if parts[0].startswith('node-'):
                # First part is a node reference - context stores as node_{id}
                node_key = f"node_{parts[0]}"

                # Try the node_ prefix format first (how engine stores it)
                if node_key in context:
                    value = context[node_key]
                    # Now traverse the rest of the path
                    for part in parts[1:]:
                        # Check in form_data first for form submission nodes
                        if isinstance(value, dict):
                            if 'form_data' in value and part in value['form_data']:
                                value = value['form_data'][part]
                            elif part in value:
                                value = value[part]
                            else:
                                logger.warning(f"Field {part} not found in node {parts[0]} outputs")
                                return match.group(0)  # Return original if not found
                        else:
                            logger.warning(f"Cannot traverse {part} in non-dict value")
                            return match.group(0)
                    return str(value) if value is not None else ''
                else:
                    logger.warning(f"Node {parts[0]} (as {node_key}) not found in context")
                    return match.group(0)  # Return original if not found
            else:
                # Regular context traversal
                value = context
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        logger.warning(f"Variable {var_path} not found in context")
                        return match.group(0)  # Return original if not found
                return str(value) if value is not None else ''

        # Replace {{variable}} patterns
        result = re.sub(r'\{\{([^}]+)\}\}', replace_variable, template)

        # If no replacements were made and the template looks like it needs values, return empty
        if result == template and '{{' in template:
            logger.warning(f"No template variables were replaced in: {template}")
            # For required fields, return empty string to trigger validation
            return ''

        return result
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate follow-up task node inputs"""
        # Debug with prints to ensure we see them
        print(f"DEBUG: FollowUpTask validate_inputs - node_config keys: {node_config.keys()}")

        node_data = node_config.get('data', {})
        print(f"DEBUG: node_data keys: {node_data.keys()}")

        # Handle both direct config and nested config.config structure
        if 'config' in node_data and isinstance(node_data['config'], dict):
            config = node_data['config']
            print(f"DEBUG: Using nested config - keys: {config.keys()}")
        else:
            config = node_data
            print(f"DEBUG: Using direct node_data as config")

        # Check required fields
        task_title = config.get('task_title')
        print(f"DEBUG: task_title = '{task_title}'")

        if not task_title:
            print("DEBUG: Validation FAILED - no task_title")
            logger.warning("Validation failed: No task_title found")
            return False

        # Validate priority (allow defaults)
        priority = config.get('priority', 'medium')
        valid_priorities = ['low', 'medium', 'high', 'urgent', 'normal']
        if priority and priority not in valid_priorities:
            logger.warning(f"Validation failed: Invalid priority '{priority}'")
            return False

        # Validate status (allow defaults)
        status = config.get('status', 'pending')
        valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
        if status and status not in valid_statuses:
            logger.warning(f"Validation failed: Invalid status '{status}'")
            return False

        print("DEBUG: FollowUpTask validation PASSED!")
        logger.info("FollowUpTask validation PASSED")
        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for follow-up task node"""
        checkpoint = await super().create_checkpoint(node_config, context)

        node_data = node_config.get('data', {})

        # Resolve record ID for checkpoint
        related_record_id = self._format_template(str(node_data.get('related_record_id', '')), context)
        if not related_record_id:
            # Try to get record from context or trigger_data
            if context.get('record'):
                related_record_id = str(context['record'].get('id', ''))
            elif context.get('trigger_data', {}).get('record_id'):
                related_record_id = str(context['trigger_data']['record_id'])
            elif context.get('trigger_data', {}).get('record_data', {}).get('id'):
                related_record_id = str(context['trigger_data']['record_data']['id'])

        checkpoint.update({
            'task_config': {
                'task_title': self._format_template(node_data.get('task_title', ''), context),
                'task_description': self._format_template(node_data.get('task_description', ''), context),
                'due_date_type': node_data.get('due_date_type', 'relative'),
                'priority': node_data.get('priority', 'medium'),
                'status': node_data.get('status', 'pending'),
                'related_record_id': related_record_id,
                'assignment_type': node_data.get('assignment_type', 'specific_user')
            }
        })

        return checkpoint