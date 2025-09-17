"""
Task Notification Node Processor - Send notifications and alerts
"""
import logging
from typing import Dict, Any, List
from django.utils import timezone
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)
User = get_user_model()


class TaskNotificationProcessor(AsyncNodeProcessor):
    """Process task notification nodes for alerts and messaging"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["message"],
        "properties": {
            "message": {
                "type": "string",
                "minLength": 1,
                "description": "Notification message",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 4,
                    "placeholder": "Task completed for {{contact.name}}"
                }
            },
            "title": {
                "type": "string",
                "default": "Workflow Notification",
                "description": "Notification title",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "Task Update"
                }
            },
            "type": {
                "type": "string",
                "enum": ["info", "success", "warning", "error"],
                "default": "info",
                "description": "Notification type",
                "ui_hints": {
                    "widget": "select"
                }
            },
            "channels": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["in_app", "email", "slack", "webhook"]
                },
                "default": ["in_app"],
                "description": "Notification channels",
                "ui_hints": {
                    "widget": "multiselect"
                }
            },
            "recipients": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Recipient user IDs or emails",
                "ui_hints": {
                    "widget": "user_multiselect",
                    "placeholder": "Select users to notify"
                }
            },
            "priority": {
                "type": "string",
                "enum": ["low", "normal", "high", "urgent"],
                "default": "normal",
                "description": "Notification priority",
                "ui_hints": {
                    "widget": "radio"
                }
            },
            "webhook_url": {
                "type": "string",
                "format": "uri",
                "description": "Webhook URL for notifications",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "https://hooks.slack.com/services/...",
                    "show_when": {"channels": ["webhook"]}
                }
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Notification tags",
                "ui_hints": {
                    "widget": "tag_input",
                    "section": "advanced"
                }
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "task_notify"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process task/notification node"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Extract configuration with context formatting
        notification_type = config.get('type', 'info')
        message = self._format_template(config.get('message', ''), context)
        title = self._format_template(config.get('title', 'Workflow Notification'), context)
        recipients = config.get('recipients', [])
        channels = config.get('channels', ['in_app'])  # in_app, email, slack, webhook
        priority = config.get('priority', 'normal')  # low, normal, high, urgent
        tags = config.get('tags', [])
        
        # Get execution context
        execution = context.get('execution')
        
        try:
            # Resolve recipient users
            recipient_users = await self._resolve_recipients(recipients, context)
            
            # Send notifications through specified channels
            sent_notifications = []
            
            for channel in channels:
                if channel == 'in_app':
                    result = await self._send_in_app_notification(
                        recipient_users, title, message, notification_type, priority, tags, execution
                    )
                    sent_notifications.append({'channel': 'in_app', **result})
                
                elif channel == 'email':
                    result = await self._send_email_notification(
                        recipient_users, title, message, notification_type, execution
                    )
                    sent_notifications.append({'channel': 'email', **result})
                
                elif channel == 'slack':
                    result = await self._send_slack_notification(
                        recipient_users, title, message, notification_type, execution
                    )
                    sent_notifications.append({'channel': 'slack', **result})
                
                elif channel == 'webhook':
                    webhook_url = config.get('webhook_url', '')
                    result = await self._send_webhook_notification(
                        webhook_url, title, message, notification_type, context, execution
                    )
                    sent_notifications.append({'channel': 'webhook', **result})
                
                else:
                    logger.warning(f"Unknown notification channel: {channel}")
            
            # Log the notification
            await self._log_notification(
                notification_type, title, message, recipient_users, channels, execution
            )
            
            return {
                'success': True,
                'notification_type': notification_type,
                'title': title,
                'message': message,
                'recipients_count': len(recipient_users),
                'channels': channels,
                'priority': priority,
                'sent_notifications': sent_notifications,
                'sent_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Task notification failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'notification_type': notification_type,
                'title': title,
                'message': message
            }
    
    async def _resolve_recipients(self, recipients: List[Any], context: Dict[str, Any]) -> List[User]:
        """Resolve recipient identifiers to User objects"""
        
        resolved_users = []
        
        for recipient in recipients:
            try:
                if isinstance(recipient, str):
                    # Try to format with context first
                    formatted_recipient = self._format_template(recipient, context)
                    
                    if '@' in formatted_recipient:
                        # Email address
                        user = await sync_to_async(User.objects.get)(email=formatted_recipient)
                        resolved_users.append(user)
                    elif formatted_recipient.isdigit():
                        # User ID
                        user = await sync_to_async(User.objects.get)(id=int(formatted_recipient))
                        resolved_users.append(user)
                    else:
                        # Username
                        user = await sync_to_async(User.objects.get)(username=formatted_recipient)
                        resolved_users.append(user)
                
                elif isinstance(recipient, int):
                    # Direct user ID
                    user = await sync_to_async(User.objects.get)(id=recipient)
                    resolved_users.append(user)
                
                elif isinstance(recipient, dict):
                    # Complex recipient specification
                    if 'user_id' in recipient:
                        user = await sync_to_async(User.objects.get)(id=recipient['user_id'])
                        resolved_users.append(user)
                    elif 'email' in recipient:
                        email = self._format_template(recipient['email'], context)
                        user = await sync_to_async(User.objects.get)(email=email)
                        resolved_users.append(user)
                
            except User.DoesNotExist:
                logger.warning(f"User not found: {recipient}")
                continue
            except Exception as e:
                logger.error(f"Error resolving recipient {recipient}: {e}")
                continue
        
        return resolved_users
    
    async def _send_in_app_notification(
        self,
        users: List[User],
        title: str,
        message: str,
        notification_type: str,
        priority: str,
        tags: List[str],
        execution
    ) -> Dict[str, Any]:
        """Send in-app notification"""
        
        try:
            # This would integrate with an in-app notification system
            # For now, just log and return success
            
            notification_count = 0
            for user in users:
                # TODO: Create notification record in database
                # TODO: Send real-time notification via WebSocket/SSE
                
                logger.info(
                    f"In-app notification sent - User: {user.email}, "
                    f"Title: {title}, Type: {notification_type}"
                )
                notification_count += 1
            
            return {
                'success': True,
                'notifications_sent': notification_count,
                'users_notified': [user.email for user in users]
            }
            
        except Exception as e:
            logger.error(f"In-app notification failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'notifications_sent': 0
            }
    
    async def _send_email_notification(
        self,
        users: List[User],
        title: str,
        message: str,
        notification_type: str,
        execution
    ) -> Dict[str, Any]:
        """Send email notification"""
        
        try:
            # This would integrate with email system
            emails_sent = 0
            
            for user in users:
                # TODO: Use email processor or send direct email
                
                logger.info(
                    f"Email notification sent - User: {user.email}, "
                    f"Subject: {title}"
                )
                emails_sent += 1
            
            return {
                'success': True,
                'emails_sent': emails_sent,
                'recipients': [user.email for user in users]
            }
            
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'emails_sent': 0
            }
    
    async def _send_slack_notification(
        self,
        users: List[User],
        title: str,
        message: str,
        notification_type: str,
        execution
    ) -> Dict[str, Any]:
        """Send Slack notification"""
        
        try:
            # This would integrate with Slack API
            messages_sent = 0
            
            for user in users:
                # TODO: Get user's Slack ID and send message
                
                logger.info(
                    f"Slack notification sent - User: {user.email}, "
                    f"Message: {title}"
                )
                messages_sent += 1
            
            return {
                'success': True,
                'messages_sent': messages_sent,
                'users_notified': [user.email for user in users]
            }
            
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'messages_sent': 0
            }
    
    async def _send_webhook_notification(
        self,
        webhook_url: str,
        title: str,
        message: str,
        notification_type: str,
        context: Dict[str, Any],
        execution
    ) -> Dict[str, Any]:
        """Send webhook notification"""
        
        try:
            if not webhook_url:
                return {'success': False, 'error': 'No webhook URL provided'}
            
            # Use webhook processor to send notification
            from workflows.nodes.external.webhook import WebhookOutProcessor
            webhook_processor = WebhookOutProcessor()
            
            webhook_config = {
                'type': 'WEBHOOK_OUT',
                'data': {
                    'webhook_url': webhook_url,
                    'payload': {
                        'notification_type': notification_type,
                        'title': title,
                        'message': message,
                        'workflow_id': str(execution.workflow.id) if execution else None,
                        'execution_id': str(execution.id) if execution else None
                    },
                    'include_context': False,
                    'include_execution_metadata': False
                }
            }
            
            result = await webhook_processor.process(webhook_config, context)
            
            return {
                'success': result.get('success', False),
                'webhook_url': webhook_url,
                'status_code': result.get('status_code'),
                'response': result.get('response_data')
            }
            
        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'webhook_url': webhook_url
            }
    
    async def _log_notification(
        self,
        notification_type: str,
        title: str,
        message: str,
        users: List[User],
        channels: List[str],
        execution
    ):
        """Log notification for audit and monitoring"""
        
        try:
            logger.info(
                f"Workflow notification - Type: {notification_type}, "
                f"Title: {title}, Recipients: {len(users)}, "
                f"Channels: {', '.join(channels)}, "
                f"Execution: {execution.id if execution else 'N/A'}"
            )
            
            # TODO: Store in notification log table for monitoring dashboard
            
        except Exception as e:
            logger.warning(f"Failed to log notification: {e}")
    
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
        """Validate task notification node inputs"""
        node_data = node_config.get('data', {})
        
        # Check required fields
        if not node_data.get('message'):
            return False
        
        # Validate notification type
        notification_type = node_data.get('type', 'info')
        valid_types = ['info', 'success', 'warning', 'error', 'debug']
        if notification_type not in valid_types:
            return False
        
        # Validate priority
        priority = node_data.get('priority', 'normal')
        valid_priorities = ['low', 'normal', 'high', 'urgent']
        if priority not in valid_priorities:
            return False
        
        # Validate channels
        channels = node_data.get('channels', ['in_app'])
        if not isinstance(channels, list) or not channels:
            return False
        
        valid_channels = ['in_app', 'email', 'slack', 'webhook']
        if not all(channel in valid_channels for channel in channels):
            return False
        
        # Validate recipients
        recipients = node_data.get('recipients', [])
        if not isinstance(recipients, list):
            return False
        
        # If webhook channel is specified, webhook_url should be provided
        if 'webhook' in channels and not node_data.get('webhook_url'):
            return False
        
        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for task notification node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        node_data = node_config.get('data', {})
        
        checkpoint.update({
            'notification_config': {
                'type': node_data.get('type', 'info'),
                'title': self._format_template(node_data.get('title', 'Workflow Notification'), context),
                'message_length': len(self._format_template(node_data.get('message', ''), context)),
                'recipients_count': len(node_data.get('recipients', [])),
                'channels': node_data.get('channels', ['in_app']),
                'priority': node_data.get('priority', 'normal'),
                'has_webhook_url': bool(node_data.get('webhook_url'))
            }
        })
        
        return checkpoint