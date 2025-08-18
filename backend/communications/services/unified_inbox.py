"""
Unified Inbox Service - Record-centric message aggregation
Groups all communication channels by the Record (contact) they're connected to
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from django.db.models import Q, Count, Max, Subquery, OuterRef, Prefetch
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model

from communications.models import (
    Message, Conversation, UserChannelConnection, ChannelType, MessageDirection
)
from pipelines.models import Record, Pipeline
from communications.unipile_sdk import unipile_service

logger = logging.getLogger(__name__)
User = get_user_model()


class RecordChannelStatus:
    """Represents channel availability and status for a specific Record"""
    
    def __init__(self, record: Record):
        self.record = record
        self.channels = {}
        self.total_unread = 0
        self.last_activity = None
        self.preferred_channel = None
    
    def add_channel(self, channel_type: str, status: Dict[str, Any]):
        """Add channel status information"""
        self.channels[channel_type] = status
        self.total_unread += status.get('unread_count', 0)
        
        # Update last activity if this channel is more recent
        channel_last_activity = status.get('last_activity')
        if channel_last_activity and (not self.last_activity or channel_last_activity > self.last_activity):
            self.last_activity = channel_last_activity
            self.preferred_channel = channel_type
    
    def get_channel_summary(self) -> Dict[str, Any]:
        """Get summary of all channels for this Record"""
        return {
            'record_id': self.record.id,
            'record_title': self.record.title,
            'pipeline_name': self.record.pipeline.name,
            'total_unread': self.total_unread,
            'last_activity': self.last_activity,
            'preferred_channel': self.preferred_channel,
            'channels': self.channels,
            'available_channels': list(self.channels.keys())
        }


class UnifiedInboxService:
    """Service for managing Record-centric unified inbox functionality"""
    
    def __init__(self, user: User):
        self.user = user
        self.logger = logger
    
    def get_record_conversations(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        Get all Records with communication activity, grouped by Record
        
        Returns:
            Dict containing Records with their communication summaries
        """
        try:
            # Get all Records that have associated conversations
            records_with_activity = Record.objects.filter(
                Q(primary_conversations__isnull=False) |  # Records linked as primary contact
                Q(message_contact_records__isnull=False)  # Records linked to individual messages
            ).select_related('pipeline').distinct()
            
            # Apply pagination
            paginator = Paginator(records_with_activity, limit)
            page_number = (offset // limit) + 1
            page = paginator.get_page(page_number)
            
            # Build Record channel status for each Record
            record_summaries = []
            for record in page.object_list:
                record_status = self._build_record_channel_status(record)
                if record_status.total_unread > 0 or record_status.last_activity:
                    record_summaries.append(record_status.get_channel_summary())
            
            # Sort by last activity and unread count
            record_summaries.sort(
                key=lambda x: (x['total_unread'] > 0, x['last_activity'] or datetime.min.replace(tzinfo=timezone.utc)),
                reverse=True
            )
            
            return {
                'records': record_summaries,
                'total_count': paginator.count,
                'has_next': page.has_next(),
                'has_previous': page.has_previous(),
                'current_page': page.number,
                'total_pages': paginator.num_pages
            }
            
        except Exception as e:
            self.logger.error(f"Error getting record conversations: {e}")
            return {
                'records': [],
                'total_count': 0,
                'has_next': False,
                'has_previous': False,
                'current_page': 1,
                'total_pages': 0,
                'error': str(e)
            }
    
    def _build_record_channel_status(self, record: Record) -> RecordChannelStatus:
        """Build channel status summary for a specific Record with threading awareness"""
        record_status = RecordChannelStatus(record)
        
        # Get all conversations where this Record is the primary contact
        primary_conversations = Conversation.objects.filter(
            primary_contact_record=record
        ).select_related('channel')
        
        # Get all messages where this Record is linked as contact
        direct_messages = Message.objects.filter(
            contact_record=record
        ).select_related('conversation__channel', 'channel')
        
        # Aggregate by channel type
        channel_activity = {}
        
        # Process primary conversations
        for conversation in primary_conversations:
            if conversation.channel:
                channel_type = conversation.channel.channel_type
                if channel_type not in channel_activity:
                    channel_activity[channel_type] = {
                        'conversations': [],
                        'messages': [],
                        'unread_count': 0,
                        'last_activity': None
                    }
                
                channel_activity[channel_type]['conversations'].append(conversation)
                
                # Count unread messages in this conversation
                unread_count = Message.objects.filter(
                    conversation=conversation,
                    direction=MessageDirection.INBOUND,
                    status__in=['delivered', 'read']  # Adjust based on your read tracking
                ).count()
                
                channel_activity[channel_type]['unread_count'] += unread_count
                
                # Update last activity
                if conversation.updated_at:
                    if not channel_activity[channel_type]['last_activity'] or conversation.updated_at > channel_activity[channel_type]['last_activity']:
                        channel_activity[channel_type]['last_activity'] = conversation.updated_at
        
        # Process direct messages (for channels without conversations)
        for message in direct_messages:
            channel = message.channel or (message.conversation.channel if message.conversation else None)
            if channel:
                channel_type = channel.channel_type
                if channel_type not in channel_activity:
                    channel_activity[channel_type] = {
                        'conversations': [],
                        'messages': [],
                        'unread_count': 0,
                        'last_activity': None
                    }
                
                channel_activity[channel_type]['messages'].append(message)
                
                # Count as unread if it's inbound and not read
                if message.direction == MessageDirection.INBOUND and message.status != 'read':
                    channel_activity[channel_type]['unread_count'] += 1
                
                # Update last activity
                if message.created_at:
                    if not channel_activity[channel_type]['last_activity'] or message.created_at > channel_activity[channel_type]['last_activity']:
                        channel_activity[channel_type]['last_activity'] = message.created_at
        
        # Add channel summaries to record status
        for channel_type, activity in channel_activity.items():
            channel_summary = {
                'channel_type': channel_type,
                'conversation_count': len(activity['conversations']),
                'message_count': len(activity['messages']),
                'unread_count': activity['unread_count'],
                'last_activity': activity['last_activity'],
                'last_message_preview': self._get_last_message_preview(activity),
                'threading_info': self._get_threading_info(activity)
            }
            record_status.add_channel(channel_type, channel_summary)
        
        return record_status
    
    def _get_threading_info(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Get threading information for channel activity"""
        threading_info = {
            'has_threads': False,
            'thread_groups': [],
            'total_threaded_messages': 0
        }
        
        # Check conversations for threading metadata
        thread_groups = {}
        for conversation in activity['conversations']:
            if conversation.metadata and 'thread_group_id' in conversation.metadata:
                thread_id = conversation.metadata['thread_group_id']
                if thread_id not in thread_groups:
                    thread_groups[thread_id] = {
                        'id': thread_id,
                        'type': conversation.metadata.get('thread_type', 'unknown'),
                        'strategy': conversation.metadata.get('threading_strategy', 'unknown'),
                        'conversations': 0,
                        'last_updated': conversation.metadata.get('thread_updated_at')
                    }
                thread_groups[thread_id]['conversations'] += 1
        
        if thread_groups:
            threading_info['has_threads'] = True
            threading_info['thread_groups'] = list(thread_groups.values())
            threading_info['total_thread_groups'] = len(thread_groups)
        
        return threading_info
    
    def _get_last_message_preview(self, activity: Dict[str, Any]) -> Optional[str]:
        """Get preview of the last message for a channel"""
        last_message = None
        last_timestamp = None
        
        # Check conversations for last message
        for conversation in activity['conversations']:
            conversation_last_message = Message.objects.filter(
                conversation=conversation
            ).order_by('-created_at').first()
            
            if conversation_last_message and (not last_timestamp or conversation_last_message.created_at > last_timestamp):
                last_message = conversation_last_message
                last_timestamp = conversation_last_message.created_at
        
        # Check direct messages
        for message in activity['messages']:
            if not last_timestamp or message.created_at > last_timestamp:
                last_message = message
                last_timestamp = message.created_at
        
        if last_message:
            preview = last_message.subject or last_message.content or ''
            return preview[:100] + '...' if len(preview) > 100 else preview
        
        return None
    
    def get_record_conversation_timeline(self, record_id: int, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        Get unified conversation timeline for a specific Record across all channels
        
        Args:
            record_id: ID of the Record to get timeline for
            limit: Number of messages to return
            offset: Pagination offset
            
        Returns:
            Dict containing unified message timeline
        """
        try:
            record = Record.objects.get(id=record_id, is_deleted=False)
            
            # Get all messages associated with this Record
            messages = Message.objects.filter(
                Q(contact_record=record) |
                Q(conversation__primary_contact_record=record)
            ).select_related(
                'channel', 'conversation', 'conversation__channel', 'contact_record'
            ).order_by('-created_at')
            
            # Apply pagination
            paginator = Paginator(messages, limit)
            page_number = (offset // limit) + 1
            page = paginator.get_page(page_number)
            
            # Normalize messages for unified display
            timeline_messages = []
            for message in page.object_list:
                normalized_message = self._normalize_message_for_timeline(message)
                timeline_messages.append(normalized_message)
            
            # Get channel availability for this Record
            available_channels = self._get_record_channel_availability(record)
            
            return {
                'record': {
                    'id': record.id,
                    'title': record.title,
                    'pipeline_name': record.pipeline.name,
                    'data': record.data
                },
                'messages': timeline_messages,
                'available_channels': available_channels,
                'pagination': {
                    'total_count': paginator.count,
                    'has_next': page.has_next(),
                    'has_previous': page.has_previous(),
                    'current_page': page.number,
                    'total_pages': paginator.num_pages
                }
            }
            
        except Record.DoesNotExist:
            return {'error': 'Record not found'}
        except Exception as e:
            self.logger.error(f"Error getting conversation timeline for record {record_id}: {e}")
            return {'error': str(e)}
    
    def _normalize_message_for_timeline(self, message: Message) -> Dict[str, Any]:
        """Normalize a message for unified timeline display"""
        channel = message.channel or (message.conversation.channel if message.conversation else None)
        
        return {
            'id': str(message.id),
            'content': message.content,
            'subject': message.subject,
            'direction': message.direction,
            'status': message.status,
            'created_at': message.created_at,
            'sent_at': message.sent_at,
            'channel': {
                'type': channel.channel_type if channel else 'unknown',
                'name': channel.name if channel else 'Unknown Channel',
                'icon': self._get_channel_icon(channel.channel_type if channel else 'unknown')
            },
            'conversation_id': str(message.conversation.id) if message.conversation else None,
            'metadata': message.metadata or {},
            'contact_email': message.contact_email,
            'contact_phone': message.contact_phone,
            'attachments': message.metadata.get('attachments', []) if message.metadata else []
        }
    
    def _get_channel_icon(self, channel_type: str) -> str:
        """Get emoji icon for channel type"""
        icons = {
            'email': '📧',
            'gmail': '📧',
            'outlook': '📧',
            'linkedin': '💼',
            'whatsapp': '📱',
            'instagram': '📸',
            'messenger': '💬',
            'telegram': '✈️',
            'twitter': '🐦',
            'unknown': '💬'
        }
        return icons.get(channel_type, '💬')
    
    def _get_record_channel_availability(self, record: Record) -> List[Dict[str, Any]]:
        """Get available communication channels for a Record"""
        # This would integrate with user's connected accounts
        # For now, return channels that have been used for communication with this Record
        
        used_channels = Message.objects.filter(
            Q(contact_record=record) |
            Q(conversation__primary_contact_record=record)
        ).values_list('channel__channel_type', flat=True).distinct()
        
        # Also check conversation channels
        conversation_channels = Conversation.objects.filter(
            primary_contact_record=record
        ).values_list('channel__channel_type', flat=True).distinct()
        
        all_channels = set(list(used_channels) + list(conversation_channels))
        all_channels.discard(None)  # Remove None values
        
        available_channels = []
        for channel_type in all_channels:
            # Check if user has connected account for this channel type
            user_connection = UserChannelConnection.objects.filter(
                user=self.user,
                channel_type=channel_type,
                is_active=True,
                account_status='active'
            ).first()
            
            available_channels.append({
                'type': channel_type,
                'icon': self._get_channel_icon(channel_type),
                'name': channel_type.title(),
                'connected': bool(user_connection),
                'can_send': user_connection.can_send_messages() if user_connection else False,
                'connection_id': str(user_connection.id) if user_connection else None
            })
        
        return available_channels
    
    def get_record_communication_stats(self, record_id: int, days: int = 30) -> Dict[str, Any]:
        """Get communication statistics for a Record over specified time period"""
        try:
            record = Record.objects.get(id=record_id, is_deleted=False)
            cutoff_date = timezone.now() - timedelta(days=days)
            
            # Get message statistics
            messages = Message.objects.filter(
                Q(contact_record=record) |
                Q(conversation__primary_contact_record=record),
                created_at__gte=cutoff_date
            )
            
            total_messages = messages.count()
            sent_messages = messages.filter(direction=MessageDirection.OUTBOUND).count()
            received_messages = messages.filter(direction=MessageDirection.INBOUND).count()
            
            # Calculate response rate (simplified)
            response_rate = (sent_messages / received_messages * 100) if received_messages > 0 else 0
            
            # Channel breakdown
            channel_breakdown = {}
            for channel_choice in ChannelType.choices:
                channel_type = channel_choice[0]  # Get the value from (value, label) tuple
                channel_messages = messages.filter(
                    Q(channel__channel_type=channel_type) |
                    Q(conversation__channel__channel_type=channel_type)
                ).count()
                if channel_messages > 0:
                    channel_breakdown[channel_type] = channel_messages
            
            # Calculate average response time (simplified)
            avg_response_time = self._calculate_average_response_time(record, cutoff_date)
            
            return {
                'record_id': record_id,
                'period_days': days,
                'total_messages': total_messages,
                'sent_messages': sent_messages,
                'received_messages': received_messages,
                'response_rate': round(response_rate, 1),
                'avg_response_time_hours': avg_response_time,
                'channel_breakdown': channel_breakdown,
                'first_contact_date': messages.order_by('created_at').first().created_at if messages.exists() else None,
                'last_activity': messages.order_by('-created_at').first().created_at if messages.exists() else None
            }
            
        except Record.DoesNotExist:
            return {'error': 'Record not found'}
        except Exception as e:
            self.logger.error(f"Error getting communication stats for record {record_id}: {e}")
            return {'error': str(e)}
    
    def _calculate_average_response_time(self, record: Record, since_date: datetime) -> Optional[float]:
        """Calculate average response time for a Record (simplified implementation)"""
        # This is a simplified calculation - could be enhanced with more sophisticated logic
        messages = Message.objects.filter(
            Q(contact_record=record) |
            Q(conversation__primary_contact_record=record),
            created_at__gte=since_date
        ).order_by('created_at')
        
        response_times = []
        last_inbound_time = None
        
        for message in messages:
            if message.direction == MessageDirection.INBOUND:
                last_inbound_time = message.created_at
            elif message.direction == MessageDirection.OUTBOUND and last_inbound_time:
                # Calculate response time
                response_time = (message.created_at - last_inbound_time).total_seconds() / 3600  # Convert to hours
                response_times.append(response_time)
                last_inbound_time = None  # Reset for next inbound message
        
        return sum(response_times) / len(response_times) if response_times else None
    
    def mark_conversation_as_read(self, record_id: int, channel_type: str) -> Dict[str, Any]:
        """Mark all messages in a Record's conversation for a specific channel as read"""
        try:
            record = Record.objects.get(id=record_id, is_deleted=False)
            
            # Find messages for this Record and channel
            messages_to_update = Message.objects.filter(
                Q(contact_record=record) |
                Q(conversation__primary_contact_record=record),
                Q(channel__channel_type=channel_type) |
                Q(conversation__channel__channel_type=channel_type),
                direction=MessageDirection.INBOUND,
                status__in=['delivered', 'sent']  # Not already read
            )
            
            updated_count = messages_to_update.update(status='read')
            
            return {
                'success': True,
                'updated_count': updated_count,
                'record_id': record_id,
                'channel_type': channel_type
            }
            
        except Record.DoesNotExist:
            return {'error': 'Record not found'}
        except Exception as e:
            self.logger.error(f"Error marking conversation as read: {e}")
            return {'error': str(e)}