"""
Communication Logging Node Processor - Log communication activities and interactions
"""
import logging
from typing import Dict, Any, Optional
from django.utils import timezone
from asgiref.sync import sync_to_async
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class CommunicationLoggingProcessor(AsyncNodeProcessor):
    """Process communication logging nodes for activity tracking"""
    
    def __init__(self):
        super().__init__()
        self.node_type = "LOG_COMMUNICATION"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process communication logging node"""
        
        node_data = node_config.get('data', {})
        
        # Extract configuration with context formatting
        activity_type = node_data.get('activity_type', 'communication')
        description = self._format_template(node_data.get('description', ''), context)
        contact_id_path = node_data.get('contact_id_path', '')
        contact_id = self._get_nested_value(context, contact_id_path) if contact_id_path else None
        
        # Additional logging fields
        communication_channel = node_data.get('communication_channel', '')
        communication_direction = node_data.get('communication_direction', 'outbound')  # inbound, outbound
        subject = self._format_template(node_data.get('subject', ''), context)
        metadata = node_data.get('metadata', {})
        tags = node_data.get('tags', [])
        
        # Get execution context
        execution = context.get('execution')
        
        try:
            # Create activity log entry
            activity_log = await self._create_activity_log(
                activity_type=activity_type,
                description=description,
                contact_id=contact_id,
                communication_channel=communication_channel,
                communication_direction=communication_direction,
                subject=subject,
                metadata=metadata,
                tags=tags,
                execution=execution,
                context=context
            )
            
            # Log to monitoring system
            await self._log_to_monitoring_system(activity_log, execution)
            
            # Update contact communication history if contact specified
            if contact_id:
                await self._update_contact_communication_history(contact_id, activity_log)
            
            return {
                'success': True,
                'activity_id': activity_log['id'],
                'activity_type': activity_type,
                'description': description,
                'contact_id': contact_id,
                'communication_channel': communication_channel,
                'communication_direction': communication_direction,
                'subject': subject,
                'tags': tags,
                'logged_at': activity_log['logged_at']
            }
            
        except Exception as e:
            logger.error(f"Communication logging failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'activity_type': activity_type,
                'description': description,
                'contact_id': contact_id
            }
    
    async def _create_activity_log(
        self,
        activity_type: str,
        description: str,
        contact_id: Optional[str],
        communication_channel: str,
        communication_direction: str,
        subject: str,
        metadata: Dict[str, Any],
        tags: list,
        execution,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create activity log entry"""
        
        try:
            # Generate unique activity ID
            import uuid
            activity_id = str(uuid.uuid4())
            
            # Prepare activity log data
            activity_log = {
                'id': activity_id,
                'activity_type': activity_type,
                'description': description,
                'contact_id': contact_id,
                'communication_channel': communication_channel,
                'communication_direction': communication_direction,
                'subject': subject,
                'metadata': {
                    **metadata,
                    'workflow_id': str(execution.workflow.id) if execution else None,
                    'execution_id': str(execution.id) if execution else None,
                    'triggered_by': execution.triggered_by.email if execution and execution.triggered_by else None
                },
                'tags': tags,
                'logged_at': timezone.now().isoformat(),
                'created_by': execution.triggered_by.id if execution and execution.triggered_by else None
            }
            
            # TODO: Store in activity log table
            # This would typically create a CommunicationActivity record
            
            logger.info(
                f"Communication activity logged - ID: {activity_id}, "
                f"Type: {activity_type}, Contact: {contact_id or 'N/A'}, "
                f"Channel: {communication_channel or 'N/A'}"
            )
            
            return activity_log
            
        except Exception as e:
            logger.error(f"Failed to create activity log: {e}")
            raise
    
    async def _log_to_monitoring_system(self, activity_log: Dict[str, Any], execution):
        """Log activity to monitoring/analytics system"""
        
        try:
            # This would integrate with monitoring/analytics system
            # For now, just structured logging
            
            logger.info(
                "Communication Activity",
                extra={
                    'activity_id': activity_log['id'],
                    'activity_type': activity_log['activity_type'],
                    'contact_id': activity_log['contact_id'],
                    'communication_channel': activity_log['communication_channel'],
                    'communication_direction': activity_log['communication_direction'],
                    'workflow_id': activity_log['metadata'].get('workflow_id'),
                    'execution_id': activity_log['metadata'].get('execution_id'),
                    'tags': activity_log['tags']
                }
            )
            
            # TODO: Send to analytics/monitoring service
            # - Time series data for communication volume
            # - Activity trends and patterns
            # - Contact engagement metrics
            
        except Exception as e:
            logger.warning(f"Failed to log to monitoring system: {e}")
    
    async def _update_contact_communication_history(self, contact_id: str, activity_log: Dict[str, Any]):
        """Update contact's communication history"""
        
        try:
            # This would update contact records with communication history
            # For now, just log the update
            
            logger.info(
                f"Contact communication history updated - Contact: {contact_id}, "
                f"Activity: {activity_log['id']}, Type: {activity_log['activity_type']}"
            )
            
            # TODO: Update contact record
            # - Last communication date
            # - Communication frequency
            # - Preferred communication channel
            # - Response patterns
            
        except Exception as e:
            logger.warning(f"Failed to update contact communication history: {e}")
    
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
        """Validate communication logging node inputs"""
        node_data = node_config.get('data', {})
        
        # Validate activity type
        activity_type = node_data.get('activity_type', 'communication')
        valid_activity_types = [
            'communication', 'email', 'phone_call', 'meeting', 'linkedin_message',
            'whatsapp_message', 'sms', 'chat', 'video_call', 'note', 'task',
            'follow_up', 'proposal', 'contract', 'demo', 'presentation'
        ]
        if activity_type not in valid_activity_types:
            return False
        
        # Validate communication direction
        communication_direction = node_data.get('communication_direction', 'outbound')
        valid_directions = ['inbound', 'outbound', 'internal']
        if communication_direction not in valid_directions:
            return False
        
        # Validate metadata
        metadata = node_data.get('metadata', {})
        if not isinstance(metadata, dict):
            return False
        
        # Validate tags
        tags = node_data.get('tags', [])
        if not isinstance(tags, list):
            return False
        
        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for communication logging node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        node_data = node_config.get('data', {})
        
        # Resolve contact ID for checkpoint
        contact_id_path = node_data.get('contact_id_path', '')
        resolved_contact_id = self._get_nested_value(context, contact_id_path) if contact_id_path else None
        
        checkpoint.update({
            'logging_config': {
                'activity_type': node_data.get('activity_type', 'communication'),
                'description': self._format_template(node_data.get('description', ''), context),
                'contact_id_path': contact_id_path,
                'resolved_contact_id': resolved_contact_id,
                'communication_channel': node_data.get('communication_channel', ''),
                'communication_direction': node_data.get('communication_direction', 'outbound'),
                'subject': self._format_template(node_data.get('subject', ''), context),
                'tags_count': len(node_data.get('tags', [])),
                'metadata_keys': list(node_data.get('metadata', {}).keys())
            }
        })
        
        return checkpoint