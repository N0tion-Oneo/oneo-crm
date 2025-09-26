"""
Message Sync Node Processor - Sync messages from communication channels
"""
import logging
from typing import Dict, Any, List
from django.utils import timezone
from asgiref.sync import sync_to_async
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class MessageSyncProcessor(AsyncNodeProcessor):
    """Process UniPile message synchronization nodes"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["user_id"],
        "properties": {
            "user_id": {
                "type": "string",
                "description": "User ID to sync messages for",
                "ui_hints": {
                    "widget": "user_select",
                    "placeholder": "{{user.id}}"
                }
            },
            "channel_types": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["email", "whatsapp", "linkedin", "sms"]
                },
                "description": "Channel types to sync (empty for all)",
                "ui_hints": {
                    "widget": "multiselect",
                    "placeholder": "Select channels to sync"
                }
            },
            "sync_limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1000,
                "default": 100,
                "description": "Maximum messages to sync per channel"
            },
            "sync_since": {
                "type": "string",
                "format": "date-time",
                "description": "Sync messages since this datetime",
                "ui_hints": {
                    "widget": "datetime",
                    "placeholder": "{{last_sync_time}} or 2024-01-01T00:00:00Z"
                }
            },
            "include_deleted": {
                "type": "boolean",
                "default": False,
                "description": "Include deleted messages in sync"
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "unipile_sync_messages"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process UniPile message sync node"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Extract configuration with context formatting
        user_id = self.format_template(config.get('user_id', ''), context)
        channel_types = config.get('channel_types', [])
        sync_limit = config.get('sync_limit', 100)
        sync_since = config.get('sync_since', '')  # Optional datetime filter
        include_deleted = config.get('include_deleted', False)
        
        # Validate required fields
        if not user_id:
            raise ValueError("Sync messages node requires user_id")
        
        try:
            # Get user's active channels
            channels = await self._get_user_channels(user_id, channel_types)
            
            if not channels:
                return {
                    'success': True,
                    'channels_synced': 0,
                    'message': 'No active channels found for user',
                    'user_id': user_id,
                    'requested_channel_types': channel_types
                }
            
            # Sync messages from each channel
            synced_channels = []
            total_messages_synced = 0
            
            for channel in channels:
                sync_result = await self._sync_channel_messages(
                    channel, sync_limit, sync_since, include_deleted
                )
                
                synced_channels.append(sync_result)
                if sync_result.get('success'):
                    total_messages_synced += sync_result.get('messages_synced', 0)
            
            # Update sync statistics
            successful_channels = sum(1 for result in synced_channels if result.get('success'))
            
            return {
                'success': True,
                'user_id': user_id,
                'channels_found': len(channels),
                'channels_synced': successful_channels,
                'total_messages_synced': total_messages_synced,
                'sync_details': synced_channels,
                'synced_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Message sync failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id,
                'requested_channel_types': channel_types
            }
    
    async def _get_user_channels(self, user_id: str, channel_types: List[str]) -> List:
        """Get user's active communication channels"""
        
        try:
            from communications.models import UserChannelConnection
            
            # Build query for active channels
            query_filter = {
                'user_id': user_id,
                'is_active': True,
                'auth_status': 'connected'
            }
            
            # Filter by channel types if specified
            if channel_types:
                query_filter['channel_type__in'] = channel_types
            
            # Execute query
            channels = await sync_to_async(list)(
                UserChannelConnection.objects.filter(**query_filter)
            )
            
            return channels
            
        except Exception as e:
            logger.error(f"Failed to get user channels: {e}")
            return []
    
    async def _sync_channel_messages(
        self,
        channel,
        sync_limit: int,
        sync_since: str,
        include_deleted: bool
    ) -> Dict[str, Any]:
        """Sync messages for a single channel"""
        
        try:
            # Determine sync start time
            since_datetime = None
            if sync_since:
                try:
                    formatted_since = self.format_template(sync_since, {'channel': channel})
                    since_datetime = timezone.datetime.fromisoformat(formatted_since.replace('Z', '+00:00'))
                except:
                    # Fall back to channel's last sync time
                    since_datetime = channel.last_sync_at
            else:
                since_datetime = channel.last_sync_at
            
            # Sync messages via UniPile SDK
            sync_result = await self._sync_via_unipile(
                channel, since_datetime, sync_limit, include_deleted
            )
            
            if sync_result.get('success'):
                # Update channel sync timestamp
                await self._update_channel_sync_time(channel)
            
            return {
                'channel_id': str(channel.id),
                'channel_name': channel.name,
                'channel_type': channel.channel_type,
                'success': sync_result.get('success', False),
                'messages_synced': sync_result.get('processed_count', 0),
                'messages_new': sync_result.get('new_messages', 0),
                'messages_updated': sync_result.get('updated_messages', 0),
                'sync_duration_ms': sync_result.get('sync_duration_ms', 0),
                'last_sync': timezone.now().isoformat(),
                'error': sync_result.get('error')
            }
            
        except Exception as e:
            logger.error(f"Channel sync failed for {channel.name}: {e}")
            return {
                'channel_id': str(channel.id),
                'channel_name': channel.name,
                'channel_type': channel.channel_type,
                'success': False,
                'messages_synced': 0,
                'error': str(e)
            }
    
    async def _sync_via_unipile(
        self,
        channel,
        since_datetime,
        sync_limit: int,
        include_deleted: bool
    ) -> Dict[str, Any]:
        """Sync messages via UniPile SDK"""
        
        try:
            from communications.unipile_sdk import unipile_service
            
            sync_result = await unipile_service.sync_messages(
                user_channel_connection=channel,
                since=since_datetime,
                limit=sync_limit,
                include_deleted=include_deleted
            )
            
            return sync_result
            
        except ImportError:
            # Fallback for development/testing
            logger.warning("UniPile SDK not available, simulating message sync")
            return {
                'success': True,
                'processed_count': 0,
                'new_messages': 0,
                'updated_messages': 0,
                'sync_duration_ms': 0
            }
        except Exception as e:
            logger.error(f"UniPile sync failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'processed_count': 0
            }
    
    async def _update_channel_sync_time(self, channel):
        """Update channel's last sync timestamp"""
        
        try:
            channel.last_sync_at = timezone.now()
            await sync_to_async(channel.save)(update_fields=['last_sync_at'])
            
        except Exception as e:
            logger.warning(f"Failed to update channel sync time: {e}")
    
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
        """Validate message sync node inputs"""
        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Check required fields
        if not config.get('user_id'):
            return False

        # Validate sync limit
        sync_limit = config.get('sync_limit', 100)
        if not isinstance(sync_limit, int) or sync_limit <= 0 or sync_limit > 1000:
            return False

        # Validate channel types if specified
        channel_types = config.get('channel_types', [])
        if not isinstance(channel_types, list):
            return False

        # Validate boolean flags
        include_deleted = config.get('include_deleted', False)
        if not isinstance(include_deleted, bool):
            return False

        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for message sync node"""
        checkpoint = await super().create_checkpoint(node_config, context)

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        checkpoint.update({
            'sync_config': {
                'user_id': self.format_template(config.get('user_id', ''), context),
                'channel_types': config.get('channel_types', []),
                'sync_limit': config.get('sync_limit', 100),
                'sync_since': config.get('sync_since', ''),
                'include_deleted': config.get('include_deleted', False)
            }
        })

        return checkpoint