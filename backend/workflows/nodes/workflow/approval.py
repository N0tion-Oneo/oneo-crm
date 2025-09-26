"""
Approval Node Processor - Handle human approval workflows
"""
import logging
from typing import Dict, Any
from django.contrib.auth import get_user_model
from django.utils import timezone
from asgiref.sync import sync_to_async
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)
User = get_user_model()


class ApprovalProcessor(AsyncNodeProcessor):
    """Process human approval nodes that pause workflow execution"""

    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "default": "Approval Required",
                "description": "Title of the approval request",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "Enter approval title"
                }
            },
            "description": {
                "type": "string",
                "description": "Detailed description of what needs approval",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 4,
                    "placeholder": "Describe what needs to be approved"
                }
            },
            "assigned_to_id": {
                "type": "string",
                "required": True,
                "description": "User who should approve this request",
                "ui_hints": {
                    "widget": "user_select",
                    "placeholder": "Select approver"
                }
            },
            "timeout_hours": {
                "type": "number",
                "default": 24,
                "description": "Hours before the approval times out",
                "ui_hints": {
                    "widget": "number",
                    "min": 1,
                    "max": 168,
                    "step": 1
                }
            },
            "escalation_rules": {
                "type": "array",
                "description": "Rules for escalating unactioned approvals",
                "items": {
                    "type": "object",
                    "properties": {
                        "after_hours": {
                            "type": "number",
                            "description": "Hours after which to escalate"
                        },
                        "escalate_to_id": {
                            "type": "string",
                            "description": "User to escalate to"
                        }
                    }
                },
                "ui_hints": {
                    "widget": "array",
                    "collapsible": True
                }
            }
        },
        "required": ["assigned_to_id"]
    }

    def __init__(self):
        super().__init__()
        self.node_type = "approval"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process human approval node"""
        
        node_data = node_config.get('data', {})
        
        # Extract configuration with context formatting
        title = self.format_template(node_data.get('title', 'Approval Required'), context)
        description = self.format_template(node_data.get('description', ''), context)
        assigned_to_id = node_data.get('assigned_to_id')
        timeout_hours = node_data.get('timeout_hours', 24)
        escalation_rules = node_data.get('escalation_rules', [])
        
        # Get execution context
        execution = context.get('execution')
        if not execution:
            raise ValueError("Execution context required for approval node")
        
        # Validate assigned user
        if not assigned_to_id:
            raise ValueError("Approval node requires assigned_to_id")
        
        try:
            assigned_to = await sync_to_async(User.objects.get)(id=assigned_to_id)
        except User.DoesNotExist:
            raise ValueError(f"User {assigned_to_id} not found")
        
        # Create approval request
        approval = await self._create_approval_request(
            execution=execution,
            assigned_to=assigned_to,
            title=title,
            description=description,
            context=context,
            timeout_hours=timeout_hours,
            escalation_rules=escalation_rules
        )
        
        # Pause execution until approval
        from workflows.models import ExecutionStatus
        execution.status = ExecutionStatus.PAUSED
        await sync_to_async(execution.save)()
        
        # Send notification to assigned user
        await self._send_approval_notification(approval, assigned_to, context)
        
        # Schedule escalation if configured
        if escalation_rules:
            await self._schedule_escalation(approval, escalation_rules)
        
        return {
            'success': True,
            'approval_id': str(approval.id),
            'status': 'pending_approval',
            'assigned_to': assigned_to.email,
            'assigned_to_name': f"{assigned_to.first_name} {assigned_to.last_name}".strip(),
            'title': title,
            'description': description,
            'timeout_hours': timeout_hours,
            'requires_approval': True,
            'created_at': approval.created_at.isoformat()
        }
    
    async def _create_approval_request(
        self,
        execution,
        assigned_to: User,
        title: str,
        description: str,
        context: Dict[str, Any],
        timeout_hours: int,
        escalation_rules: list
    ):
        """Create workflow approval request"""
        
        try:
            from workflows.models import WorkflowApproval
            from django.utils import timezone
            import datetime
            
            # Calculate timeout
            timeout_at = None
            if timeout_hours > 0:
                timeout_at = timezone.now() + datetime.timedelta(hours=timeout_hours)
            
            # Create approval request
            approval = await sync_to_async(WorkflowApproval.objects.create)(
                execution=execution,
                requested_by=execution.triggered_by,
                assigned_to=assigned_to,
                title=title,
                description=description,
                approval_data=self._sanitize_context_for_storage(context),
                timeout_at=timeout_at,
                escalation_rules=escalation_rules
            )
            
            return approval
            
        except Exception as e:
            logger.error(f"Failed to create approval request: {e}")
            raise
    
    def _sanitize_context_for_storage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize context data for database storage"""
        
        sanitized = {}
        
        for key, value in context.items():
            # Skip internal keys and non-serializable objects
            if key.startswith('_') or key in ['execution']:
                continue
            
            try:
                # Test if value is JSON serializable
                import json
                json.dumps(value)
                sanitized[key] = value
            except (TypeError, ValueError):
                # Convert non-serializable values to string
                sanitized[key] = str(value)
        
        return sanitized
    
    async def _send_approval_notification(self, approval, assigned_to: User, context: Dict[str, Any]):
        """Send notification to assigned user about pending approval"""
        
        try:
            # This would integrate with the notification system
            # For now, just log the notification
            logger.info(
                f"Approval notification sent - ID: {approval.id}, "
                f"Assigned to: {assigned_to.email}, Title: {approval.title}"
            )
            
            # TODO: Integrate with email/notification system
            # - Send email notification
            # - Create in-app notification
            # - Send webhook to external systems if configured
            
        except Exception as e:
            logger.warning(f"Failed to send approval notification: {e}")
    
    async def _schedule_escalation(self, approval, escalation_rules: list):
        """Schedule escalation for approval request"""
        
        try:
            # This would integrate with a task scheduler (Celery, etc.)
            # For now, just log the escalation scheduling
            logger.info(
                f"Escalation scheduled for approval {approval.id} with {len(escalation_rules)} rules"
            )
            
            # TODO: Implement escalation scheduling
            # - Schedule periodic checks for approval timeout
            # - Escalate to manager/other users based on rules
            # - Send reminder notifications
            
        except Exception as e:
            logger.warning(f"Failed to schedule escalation: {e}")
    
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
        """Validate approval node inputs"""
        node_data = node_config.get('data', {})
        
        # Check required fields
        if not node_data.get('assigned_to_id'):
            return False
        
        # Validate timeout hours
        timeout_hours = node_data.get('timeout_hours', 24)
        if not isinstance(timeout_hours, (int, float)) or timeout_hours < 0:
            return False
        
        # Validate escalation rules structure
        escalation_rules = node_data.get('escalation_rules', [])
        if not isinstance(escalation_rules, list):
            return False
        
        for rule in escalation_rules:
            if not isinstance(rule, dict):
                return False
            # Basic rule validation
            required_rule_fields = ['trigger_after_hours', 'action_type']
            if not all(field in rule for field in required_rule_fields):
                return False
        
        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for approval node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        node_data = node_config.get('data', {})
        
        # Get assigned user info safely
        assigned_to_id = node_data.get('assigned_to_id')
        assigned_to_email = 'unknown'
        try:
            if assigned_to_id:
                assigned_to = await sync_to_async(User.objects.get)(id=assigned_to_id)
                assigned_to_email = assigned_to.email
        except:
            pass
        
        checkpoint.update({
            'approval_config': {
                'title': self.format_template(node_data.get('title', 'Approval Required'), context),
                'assigned_to_id': assigned_to_id,
                'assigned_to_email': assigned_to_email,
                'timeout_hours': node_data.get('timeout_hours', 24),
                'escalation_rules_count': len(node_data.get('escalation_rules', []))
            }
        })
        
        return checkpoint


class ApprovalResponseProcessor(AsyncNodeProcessor):
    """Process approval responses and resume workflow execution"""
    
    def __init__(self):
        super().__init__()
        self.node_type = "approval_response"
        self.supports_replay = False  # Approval responses are one-time events
        self.supports_checkpoints = True
    
    async def process_approval_response(
        self, 
        approval_id: str, 
        response: str, 
        responder: User, 
        comments: str = ''
    ) -> Dict[str, Any]:
        """Process approval response and resume workflow"""
        
        try:
            from workflows.models import WorkflowApproval, ExecutionStatus
            
            # Get approval request
            approval = await sync_to_async(WorkflowApproval.objects.get)(id=approval_id)
            
            if approval.status != 'pending':
                raise ValueError(f"Approval {approval_id} is not pending")
            
            # Validate response
            if response not in ['approved', 'rejected']:
                raise ValueError("Response must be 'approved' or 'rejected'")
            
            # Update approval
            approval.status = response
            approval.responded_by = responder
            approval.response_comments = comments
            approval.responded_at = timezone.now()
            await sync_to_async(approval.save)()
            
            # Resume workflow execution
            execution = approval.execution
            
            if response == 'approved':
                execution.status = ExecutionStatus.RUNNING
                # Add approval result to context
                execution.execution_context['approval_result'] = {
                    'approved': True,
                    'approved_by': responder.email,
                    'comments': comments,
                    'approved_at': approval.responded_at.isoformat()
                }
            else:
                execution.status = ExecutionStatus.FAILED
                execution.error_message = f"Workflow rejected by {responder.email}: {comments}"
                execution.execution_context['approval_result'] = {
                    'approved': False,
                    'rejected_by': responder.email,
                    'comments': comments,
                    'rejected_at': approval.responded_at.isoformat()
                }
            
            await sync_to_async(execution.save)()
            
            # TODO: Resume workflow execution from the approval node
            # This would require integration with the workflow engine
            
            return {
                'success': True,
                'approval_id': approval_id,
                'response': response,
                'responder': responder.email,
                'execution_id': str(execution.id),
                'workflow_status': execution.status
            }
            
        except Exception as e:
            logger.error(f"Failed to process approval response: {e}")
            return {
                'success': False,
                'error': str(e),
                'approval_id': approval_id
            }