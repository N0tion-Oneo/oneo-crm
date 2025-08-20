"""
Smart gap detection service for webhook-first architecture
Only syncs when actual gaps are detected, not on schedule
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q, Max, Min, Count
from django.core.cache import cache
from asgiref.sync import async_to_sync

from communications.models import (
    UserChannelConnection, Message, Conversation, 
    MessageDirection, MessageStatus
)

logger = logging.getLogger(__name__)


class SmartGapDetector:
    """
    Intelligent gap detection system for webhook-first architecture
    
    Detects actual data gaps rather than running on schedule:
    1. Sequence number gaps in message streams
    2. Time-based gaps (missing messages in expected timeframes)
    3. Status inconsistencies (messages stuck in pending states)
    4. Account health indicators (webhook failures, API errors)
    """
    
    def __init__(self):
        self.cache_timeout = 300  # 5 minutes
        self.gap_threshold_minutes = 30  # Consider gaps > 30 minutes
        self.max_gap_age_hours = 24  # Don't sync gaps older than 24 hours
    
    async def detect_conversation_gaps(self, 
                                     connection_id: str, 
                                     trigger_reason: str = "health_check") -> Dict[str, Any]:
        """
        Detect conversation-level gaps for a specific connection
        
        Args:
            connection_id: UserChannelConnection ID
            trigger_reason: Why gap detection was triggered
            
        Returns:
            Gap detection results with recommendations
        """
        try:
            # Get connection
            connection = await UserChannelConnection.objects.aget(id=connection_id)
            
            logger.info(f"🔍 Detecting conversation gaps for {connection.channel_type} "
                       f"account {connection.unipile_account_id} (reason: {trigger_reason})")
            
            # Check if we recently checked for gaps
            cache_key = f"gap_check:{connection_id}:conversations"
            if cache.get(cache_key) and trigger_reason == "routine":
                logger.debug(f"Skipping gap detection - recently checked for {connection_id}")
                return {'gaps_detected': False, 'reason': 'recently_checked'}
            
            # Detect different types of gaps
            sequence_gaps = await self._detect_sequence_gaps(connection)
            time_gaps = await self._detect_time_gaps(connection)
            status_gaps = await self._detect_status_inconsistencies(connection)
            health_issues = await self._detect_account_health_issues(connection)
            
            # Combine all gap types
            all_gaps = {
                'sequence_gaps': sequence_gaps,
                'time_gaps': time_gaps,
                'status_gaps': status_gaps,
                'health_issues': health_issues
            }
            
            # Determine if sync is needed
            gaps_detected = any([
                sequence_gaps['gaps_found'],
                time_gaps['gaps_found'],
                status_gaps['gaps_found'],
                health_issues['issues_found']
            ])
            
            result = {
                'connection_id': connection_id,
                'account_id': connection.unipile_account_id,
                'channel_type': connection.channel_type,
                'gaps_detected': gaps_detected,
                'trigger_reason': trigger_reason,
                'gap_analysis': all_gaps,
                'sync_recommended': gaps_detected,
                'checked_at': timezone.now().isoformat()
            }
            
            if gaps_detected:
                logger.warning(f"🚨 Gaps detected for {connection.channel_type} account "
                             f"{connection.unipile_account_id}: {self._summarize_gaps(all_gaps)}")
            else:
                logger.info(f"✅ No gaps detected for {connection.channel_type} account "
                           f"{connection.unipile_account_id}")
            
            # Cache result to avoid repeated checks
            cache.set(cache_key, result, timeout=self.cache_timeout)
            
            return result
            
        except Exception as e:
            logger.error(f"Gap detection failed for connection {connection_id}: {e}")
            return {
                'connection_id': connection_id,
                'gaps_detected': False,
                'error': str(e),
                'trigger_reason': trigger_reason
            }
    
    async def detect_message_gaps(self, 
                                conversation_id: str,
                                trigger_reason: str = "health_check") -> Dict[str, Any]:
        """
        Detect message-level gaps within a specific conversation
        
        Args:
            conversation_id: Conversation ID to check
            trigger_reason: Why gap detection was triggered
            
        Returns:
            Message gap detection results
        """
        try:
            # Get conversation
            conversation = await Conversation.objects.select_related('channel').aget(id=conversation_id)
            
            logger.info(f"🔍 Detecting message gaps for conversation {conversation_id} "
                       f"(reason: {trigger_reason})")
            
            # Check cache
            cache_key = f"gap_check:{conversation_id}:messages"
            if cache.get(cache_key) and trigger_reason == "routine":
                return {'gaps_detected': False, 'reason': 'recently_checked'}
            
            # Get message sequence for analysis
            messages = await self._get_conversation_message_sequence(conversation)
            
            if not messages:
                return {
                    'conversation_id': conversation_id,
                    'gaps_detected': False,
                    'reason': 'no_messages'
                }
            
            # Analyze message sequence for gaps
            sequence_analysis = await self._analyze_message_sequence(messages)
            timestamp_analysis = await self._analyze_message_timestamps(messages)
            status_analysis = await self._analyze_message_statuses(messages)
            
            gaps_detected = any([
                sequence_analysis['gaps_found'],
                timestamp_analysis['gaps_found'],
                status_analysis['issues_found']
            ])
            
            result = {
                'conversation_id': conversation_id,
                'channel_type': conversation.channel.channel_type,
                'gaps_detected': gaps_detected,
                'trigger_reason': trigger_reason,
                'message_analysis': {
                    'sequence': sequence_analysis,
                    'timestamps': timestamp_analysis,
                    'statuses': status_analysis
                },
                'total_messages': len(messages),
                'sync_recommended': gaps_detected,
                'checked_at': timezone.now().isoformat()
            }
            
            if gaps_detected:
                logger.warning(f"🚨 Message gaps detected in conversation {conversation_id}")
            else:
                logger.info(f"✅ No message gaps in conversation {conversation_id}")
            
            # Cache result
            cache.set(cache_key, result, timeout=self.cache_timeout)
            
            return result
            
        except Exception as e:
            logger.error(f"Message gap detection failed for conversation {conversation_id}: {e}")
            return {
                'conversation_id': conversation_id,
                'gaps_detected': False,
                'error': str(e),
                'trigger_reason': trigger_reason
            }
    
    async def get_sync_recommendations(self, 
                                     connection_id: str) -> Dict[str, Any]:
        """
        Get intelligent sync recommendations based on gap analysis
        
        Args:
            connection_id: UserChannelConnection ID
            
        Returns:
            Sync recommendations with priority and scope
        """
        try:
            # Run comprehensive gap detection
            gap_results = await self.detect_conversation_gaps(connection_id, "recommendation_request")
            
            if not gap_results.get('gaps_detected'):
                return {
                    'sync_needed': False,
                    'recommendation': 'no_sync_needed',
                    'reason': 'no_gaps_detected'
                }
            
            # Analyze gap severity and create recommendations
            recommendations = await self._create_sync_recommendations(gap_results)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get sync recommendations for {connection_id}: {e}")
            return {
                'sync_needed': False,
                'error': str(e),
                'recommendation': 'error_occurred'
            }
    
    async def _detect_sequence_gaps(self, connection: UserChannelConnection) -> Dict[str, Any]:
        """Detect gaps in message sequence numbers or IDs"""
        try:
            # Get recent conversations for this connection
            conversations = await self._get_recent_conversations(connection)
            
            sequence_gaps = []
            
            for conversation in conversations:
                # Check for sequence gaps in external message IDs
                messages = await self._get_conversation_message_sequence(conversation)
                
                if len(messages) < 2:
                    continue
                
                # Look for numeric sequence patterns
                numeric_ids = []
                for msg in messages:
                    try:
                        if msg.external_message_id and msg.external_message_id.isdigit():
                            numeric_ids.append((int(msg.external_message_id), msg))
                    except (ValueError, AttributeError):
                        continue
                
                if len(numeric_ids) > 2:
                    numeric_ids.sort(key=lambda x: x[0])
                    
                    # Check for missing sequence numbers
                    for i in range(len(numeric_ids) - 1):
                        current_id = numeric_ids[i][0]
                        next_id = numeric_ids[i + 1][0]
                        
                        if next_id - current_id > 1:
                            gap_size = next_id - current_id - 1
                            sequence_gaps.append({
                                'conversation_id': str(conversation.id),
                                'gap_start': current_id,
                                'gap_end': next_id,
                                'gap_size': gap_size,
                                'gap_type': 'sequence_number'
                            })
            
            return {
                'gaps_found': len(sequence_gaps) > 0,
                'gap_count': len(sequence_gaps),
                'gaps': sequence_gaps
            }
            
        except Exception as e:
            logger.error(f"Sequence gap detection failed: {e}")
            return {'gaps_found': False, 'error': str(e)}
    
    async def _detect_time_gaps(self, connection: UserChannelConnection) -> Dict[str, Any]:
        """Detect unusual time gaps in message flow"""
        try:
            # Get message activity patterns
            time_gaps = []
            
            # Check for conversations with suspicious time gaps
            conversations = await self._get_recent_conversations(connection)
            
            for conversation in conversations:
                messages = await self._get_conversation_message_sequence(conversation)
                
                if len(messages) < 2:
                    continue
                
                # Sort by timestamp
                messages.sort(key=lambda x: x.created_at)
                
                # Look for unusual gaps between messages
                for i in range(len(messages) - 1):
                    current_msg = messages[i]
                    next_msg = messages[i + 1]
                    
                    time_diff = next_msg.created_at - current_msg.created_at
                    
                    # Flag gaps longer than threshold
                    if time_diff > timedelta(minutes=self.gap_threshold_minutes):
                        # Don't flag old gaps
                        if current_msg.created_at > timezone.now() - timedelta(hours=self.max_gap_age_hours):
                            time_gaps.append({
                                'conversation_id': str(conversation.id),
                                'gap_start': current_msg.created_at.isoformat(),
                                'gap_end': next_msg.created_at.isoformat(),
                                'gap_duration_minutes': int(time_diff.total_seconds() / 60),
                                'gap_type': 'time_gap'
                            })
            
            return {
                'gaps_found': len(time_gaps) > 0,
                'gap_count': len(time_gaps),
                'gaps': time_gaps
            }
            
        except Exception as e:
            logger.error(f"Time gap detection failed: {e}")
            return {'gaps_found': False, 'error': str(e)}
    
    async def _detect_status_inconsistencies(self, connection: UserChannelConnection) -> Dict[str, Any]:
        """Detect messages stuck in inconsistent states"""
        try:
            status_issues = []
            
            # Find messages stuck in pending states for too long
            stuck_threshold = timezone.now() - timedelta(hours=1)
            
            stuck_messages = Message.objects.filter(
                channel__unipile_account_id=connection.unipile_account_id,
                sync_status='pending',
                created_at__lt=stuck_threshold
            )
            
            async for message in stuck_messages:
                status_issues.append({
                    'message_id': str(message.id),
                    'external_id': message.external_message_id,
                    'conversation_id': str(message.conversation.id),
                    'issue_type': 'stuck_pending',
                    'stuck_duration_hours': int((timezone.now() - message.created_at).total_seconds() / 3600)
                })
            
            # Find outbound messages that never got status updates
            old_outbound = Message.objects.filter(
                channel__unipile_account_id=connection.unipile_account_id,
                direction=MessageDirection.OUTBOUND,
                status=MessageStatus.SENT,
                created_at__lt=timezone.now() - timedelta(hours=2)
            )
            
            async for message in old_outbound:
                # These should have been updated to delivered/read by now
                status_issues.append({
                    'message_id': str(message.id),
                    'external_id': message.external_message_id,
                    'conversation_id': str(message.conversation.id),
                    'issue_type': 'missing_status_update',
                    'age_hours': int((timezone.now() - message.created_at).total_seconds() / 3600)
                })
            
            return {
                'gaps_found': len(status_issues) > 0,
                'issue_count': len(status_issues),
                'issues': status_issues
            }
            
        except Exception as e:
            logger.error(f"Status inconsistency detection failed: {e}")
            return {'gaps_found': False, 'error': str(e)}
    
    async def _detect_account_health_issues(self, connection: UserChannelConnection) -> Dict[str, Any]:
        """Detect account-level health issues that might indicate gaps"""
        try:
            health_issues = []
            
            # Check connection error rates
            if connection.sync_error_count > 5:
                health_issues.append({
                    'issue_type': 'high_error_rate',
                    'error_count': connection.sync_error_count,
                    'last_error': connection.last_error
                })
            
            # Check last successful sync time
            if connection.last_sync_at:
                time_since_sync = timezone.now() - connection.last_sync_at
                if time_since_sync > timedelta(hours=6):
                    health_issues.append({
                        'issue_type': 'stale_sync',
                        'hours_since_sync': int(time_since_sync.total_seconds() / 3600),
                        'last_sync_at': connection.last_sync_at.isoformat()
                    })
            
            # Check account status
            if connection.account_status != 'active':
                health_issues.append({
                    'issue_type': 'inactive_account',
                    'account_status': connection.account_status,
                    'auth_status': connection.auth_status
                })
            
            return {
                'issues_found': len(health_issues) > 0,
                'issue_count': len(health_issues),
                'issues': health_issues
            }
            
        except Exception as e:
            logger.error(f"Account health detection failed: {e}")
            return {'issues_found': False, 'error': str(e)}
    
    async def _get_recent_conversations(self, connection: UserChannelConnection) -> List:
        """Get recent conversations for gap analysis"""
        recent_cutoff = timezone.now() - timedelta(hours=24)
        
        conversations = []
        async for conversation in Conversation.objects.filter(
            channel__unipile_account_id=connection.unipile_account_id,
            updated_at__gte=recent_cutoff
        ).order_by('-updated_at')[:20]:
            conversations.append(conversation)
        
        return conversations
    
    async def _get_conversation_message_sequence(self, conversation) -> List:
        """Get message sequence for a conversation"""
        messages = []
        async for message in Message.objects.filter(
            conversation=conversation
        ).order_by('created_at'):
            messages.append(message)
        
        return messages
    
    async def _analyze_message_sequence(self, messages: List) -> Dict[str, Any]:
        """Analyze message sequence for gaps"""
        try:
            if len(messages) < 2:
                return {'gaps_found': False, 'reason': 'insufficient_messages'}
            
            # Simple sequence analysis
            gaps = []
            
            # Check for duplicate external IDs
            external_ids = [msg.external_message_id for msg in messages if msg.external_message_id]
            duplicates = len(external_ids) - len(set(external_ids))
            
            if duplicates > 0:
                gaps.append({
                    'type': 'duplicate_external_ids',
                    'count': duplicates
                })
            
            return {
                'gaps_found': len(gaps) > 0,
                'gap_count': len(gaps),
                'gaps': gaps
            }
            
        except Exception as e:
            return {'gaps_found': False, 'error': str(e)}
    
    async def _analyze_message_timestamps(self, messages: List) -> Dict[str, Any]:
        """Analyze message timestamps for inconsistencies"""
        try:
            if len(messages) < 2:
                return {'gaps_found': False, 'reason': 'insufficient_messages'}
            
            gaps = []
            
            # Sort by timestamp
            sorted_messages = sorted(messages, key=lambda x: x.created_at)
            
            # Check for messages in the future (clock skew issues)
            future_messages = [msg for msg in messages if msg.created_at > timezone.now()]
            if future_messages:
                gaps.append({
                    'type': 'future_timestamps',
                    'count': len(future_messages)
                })
            
            return {
                'gaps_found': len(gaps) > 0,
                'gap_count': len(gaps),
                'gaps': gaps
            }
            
        except Exception as e:
            return {'gaps_found': False, 'error': str(e)}
    
    async def _analyze_message_statuses(self, messages: List) -> Dict[str, Any]:
        """Analyze message status consistency"""
        try:
            issues = []
            
            # Check for status inconsistencies
            pending_count = len([msg for msg in messages if msg.sync_status == 'pending'])
            failed_count = len([msg for msg in messages if msg.sync_status == 'failed'])
            
            if pending_count > 0:
                issues.append({
                    'type': 'pending_messages',
                    'count': pending_count
                })
            
            if failed_count > 0:
                issues.append({
                    'type': 'failed_messages',
                    'count': failed_count
                })
            
            return {
                'issues_found': len(issues) > 0,
                'issue_count': len(issues),
                'issues': issues
            }
            
        except Exception as e:
            return {'issues_found': False, 'error': str(e)}
    
    async def _create_sync_recommendations(self, gap_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create intelligent sync recommendations based on gap analysis"""
        try:
            recommendations = {
                'sync_needed': True,
                'priority': 'low',
                'scope': 'incremental',
                'recommendations': []
            }
            
            gap_analysis = gap_results.get('gap_analysis', {})
            
            # Determine priority based on gap types
            high_priority_indicators = [
                gap_analysis.get('status_gaps', {}).get('gaps_found', False),
                gap_analysis.get('health_issues', {}).get('issues_found', False)
            ]
            
            if any(high_priority_indicators):
                recommendations['priority'] = 'high'
                recommendations['scope'] = 'full'
            elif gap_analysis.get('sequence_gaps', {}).get('gaps_found', False):
                recommendations['priority'] = 'medium'
                recommendations['scope'] = 'targeted'
            
            # Add specific recommendations
            if gap_analysis.get('sequence_gaps', {}).get('gaps_found'):
                recommendations['recommendations'].append({
                    'action': 'sync_missing_messages',
                    'reason': 'sequence_gaps_detected',
                    'gap_count': gap_analysis['sequence_gaps']['gap_count']
                })
            
            if gap_analysis.get('time_gaps', {}).get('gaps_found'):
                recommendations['recommendations'].append({
                    'action': 'sync_time_range',
                    'reason': 'time_gaps_detected',
                    'gap_count': gap_analysis['time_gaps']['gap_count']
                })
            
            if gap_analysis.get('status_gaps', {}).get('gaps_found'):
                recommendations['recommendations'].append({
                    'action': 'retry_failed_messages',
                    'reason': 'status_inconsistencies',
                    'issue_count': gap_analysis['status_gaps']['issue_count']
                })
            
            if gap_analysis.get('health_issues', {}).get('issues_found'):
                recommendations['recommendations'].append({
                    'action': 'account_health_sync',
                    'reason': 'account_health_issues',
                    'issue_count': gap_analysis['health_issues']['issue_count']
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to create sync recommendations: {e}")
            return {
                'sync_needed': False,
                'error': str(e),
                'recommendation': 'error_occurred'
            }
    
    def _summarize_gaps(self, gap_analysis: Dict[str, Any]) -> str:
        """Create human-readable gap summary"""
        summary_parts = []
        
        if gap_analysis.get('sequence_gaps', {}).get('gaps_found'):
            count = gap_analysis['sequence_gaps']['gap_count']
            summary_parts.append(f"{count} sequence gaps")
        
        if gap_analysis.get('time_gaps', {}).get('gaps_found'):
            count = gap_analysis['time_gaps']['gap_count']
            summary_parts.append(f"{count} time gaps")
        
        if gap_analysis.get('status_gaps', {}).get('gaps_found'):
            count = gap_analysis['status_gaps']['issue_count']
            summary_parts.append(f"{count} status issues")
        
        if gap_analysis.get('health_issues', {}).get('issues_found'):
            count = gap_analysis['health_issues']['issue_count']
            summary_parts.append(f"{count} health issues")
        
        return ", ".join(summary_parts) if summary_parts else "minor issues"


# Global instance
gap_detector = SmartGapDetector()