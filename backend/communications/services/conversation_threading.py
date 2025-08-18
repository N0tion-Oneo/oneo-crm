"""
Cross-channel Conversation Threading Service
Intelligently groups related conversations across different channels for the same Record
"""
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from django.db.models import Q, Count, Max, Min
from django.utils import timezone
from django.db import transaction

from communications.models import (
    Message, Conversation, Channel, UserChannelConnection, ChannelType, MessageDirection
)
from pipelines.models import Record

logger = logging.getLogger(__name__)


class ConversationThreadingService:
    """Service for managing cross-channel conversation threading and grouping"""
    
    def __init__(self):
        self.logger = logger
        
        # Threading strategies for different scenarios
        self.threading_strategies = {
            'same_contact_record': self._thread_by_contact_record,
            'email_references': self._thread_by_email_references,
            'temporal_proximity': self._thread_by_temporal_proximity,
            'subject_similarity': self._thread_by_subject_similarity,
            'content_references': self._thread_by_content_references
        }
    
    def create_unified_conversation_thread(self, record: Record, force_rethread: bool = False) -> Dict[str, Any]:
        """
        Create unified conversation thread for a Record across all channels
        
        Args:
            record: The Record to create unified thread for
            force_rethread: Whether to force re-threading of existing conversations
            
        Returns:
            Dict containing threading results and statistics
        """
        try:
            with transaction.atomic():
                # Get all conversations and messages for this Record
                conversations = self._get_record_conversations(record)
                messages = self._get_record_messages(record)
                
                if not conversations and not messages:
                    return {
                        'success': True,
                        'record_id': record.id,
                        'threads_created': 0,
                        'messages_threaded': 0,
                        'note': 'No conversations or messages found for Record'
                    }
                
                # Analyze threading opportunities
                threading_analysis = self._analyze_threading_opportunities(record, conversations, messages)
                
                # Apply threading strategies
                threading_results = self._apply_threading_strategies(record, threading_analysis, force_rethread)
                
                # Create conversation thread metadata
                thread_metadata = self._create_thread_metadata(record, threading_results)
                
                # Update conversations with threading information
                updated_conversations = self._update_conversation_threading(threading_results)
                
                return {
                    'success': True,
                    'record_id': record.id,
                    'threads_created': len(threading_results.get('thread_groups', [])),
                    'messages_threaded': threading_results.get('total_messages_threaded', 0),
                    'conversations_updated': len(updated_conversations),
                    'threading_strategies_used': threading_results.get('strategies_used', []),
                    'thread_metadata': thread_metadata,
                    'analysis': threading_analysis
                }
                
        except Exception as e:
            self.logger.error(f"Error creating unified conversation thread for record {record.id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'record_id': record.id
            }
    
    def _get_record_conversations(self, record: Record) -> List[Conversation]:
        """Get all conversations associated with a Record"""
        return list(Conversation.objects.filter(
            Q(primary_contact_record=record) |
            Q(messages__contact_record=record)
        ).select_related('channel').distinct())
    
    def _get_record_messages(self, record: Record) -> List[Message]:
        """Get all messages associated with a Record"""
        return list(Message.objects.filter(
            Q(contact_record=record) |
            Q(conversation__primary_contact_record=record)
        ).select_related('channel', 'conversation', 'conversation__channel').order_by('created_at'))
    
    def _analyze_threading_opportunities(self, record: Record, conversations: List[Conversation], 
                                       messages: List[Message]) -> Dict[str, Any]:
        """Analyze potential threading opportunities for a Record"""
        
        analysis = {
            'record_id': record.id,
            'total_conversations': len(conversations),
            'total_messages': len(messages),
            'channels_involved': set(),
            'time_span': None,
            'threading_signals': {},
            'potential_threads': []
        }
        
        # Analyze channels involved
        for conversation in conversations:
            if conversation.channel:
                analysis['channels_involved'].add(conversation.channel.channel_type)
        
        for message in messages:
            channel = message.channel or (message.conversation.channel if message.conversation else None)
            if channel:
                analysis['channels_involved'].add(channel.channel_type)
        
        analysis['channels_involved'] = list(analysis['channels_involved'])
        
        # Analyze time span
        if messages:
            message_times = [msg.created_at for msg in messages if msg.created_at]
            if message_times:
                analysis['time_span'] = {
                    'start': min(message_times),
                    'end': max(message_times),
                    'duration_days': (max(message_times) - min(message_times)).days
                }
        
        # Analyze threading signals
        analysis['threading_signals'] = {
            'email_references': self._analyze_email_references(messages),
            'subject_patterns': self._analyze_subject_patterns(messages),
            'temporal_clusters': self._analyze_temporal_clusters(messages),
            'content_references': self._analyze_content_references(messages),
            'cross_channel_sequences': self._analyze_cross_channel_sequences(messages)
        }
        
        # Identify potential thread groups
        analysis['potential_threads'] = self._identify_potential_threads(record, conversations, messages, analysis)
        
        return analysis
    
    def _analyze_email_references(self, messages: List[Message]) -> Dict[str, Any]:
        """Analyze email reference headers for threading"""
        email_refs = {
            'message_ids': set(),
            'in_reply_to': set(),
            'references': set(),
            'thread_chains': []
        }
        
        for message in messages:
            if not message.metadata:
                continue
                
            # Extract email threading headers
            headers = message.metadata.get('email_headers', {})
            if headers:
                msg_id = headers.get('Message-ID')
                if msg_id:
                    email_refs['message_ids'].add(msg_id)
                
                in_reply_to = headers.get('In-Reply-To')
                if in_reply_to:
                    email_refs['in_reply_to'].add(in_reply_to)
                
                references = headers.get('References')
                if references:
                    # References can contain multiple message IDs
                    ref_list = [ref.strip() for ref in references.split() if ref.strip()]
                    email_refs['references'].update(ref_list)
        
        # Build thread chains from references
        email_refs['thread_chains'] = self._build_email_thread_chains(email_refs)
        
        return {
            'total_message_ids': len(email_refs['message_ids']),
            'reply_references': len(email_refs['in_reply_to']),
            'reference_chains': len(email_refs['references']),
            'identifiable_threads': len(email_refs['thread_chains']),
            'threading_potential': 'high' if email_refs['thread_chains'] else 'low'
        }
    
    def _analyze_subject_patterns(self, messages: List[Message]) -> Dict[str, Any]:
        """Analyze subject line patterns for threading clues"""
        subjects = {}
        reply_patterns = {'re:', 'fwd:', 'fw:', '[', '('}
        
        for message in messages:
            if message.subject:
                # Normalize subject (remove Re:, Fwd:, etc.)
                normalized_subject = self._normalize_subject(message.subject)
                if normalized_subject not in subjects:
                    subjects[normalized_subject] = []
                subjects[normalized_subject].append(message)
        
        # Identify subject-based threads
        subject_threads = {subject: msgs for subject, msgs in subjects.items() if len(msgs) > 1}
        
        return {
            'unique_subjects': len(subjects),
            'potential_subject_threads': len(subject_threads),
            'messages_with_reply_indicators': sum(1 for msg in messages 
                                                if msg.subject and any(pattern in msg.subject.lower() for pattern in reply_patterns)),
            'threading_potential': 'high' if subject_threads else 'medium'
        }
    
    def _analyze_temporal_clusters(self, messages: List[Message]) -> Dict[str, Any]:
        """Analyze temporal clustering of messages across channels"""
        if not messages:
            return {'threading_potential': 'none'}
        
        # Group messages by time windows (e.g., within 1 hour of each other)
        time_window = timedelta(hours=1)
        clusters = []
        
        sorted_messages = sorted(messages, key=lambda m: m.created_at or timezone.now())
        
        current_cluster = [sorted_messages[0]]
        
        for message in sorted_messages[1:]:
            if message.created_at and current_cluster[-1].created_at:
                time_diff = message.created_at - current_cluster[-1].created_at
                if time_diff <= time_window:
                    current_cluster.append(message)
                else:
                    if len(current_cluster) > 1:
                        clusters.append(current_cluster)
                    current_cluster = [message]
        
        if len(current_cluster) > 1:
            clusters.append(current_cluster)
        
        # Analyze cross-channel clusters
        cross_channel_clusters = []
        for cluster in clusters:
            channels = set()
            for msg in cluster:
                channel = msg.channel or (msg.conversation.channel if msg.conversation else None)
                if channel:
                    channels.add(channel.channel_type)
            
            if len(channels) > 1:
                cross_channel_clusters.append({
                    'messages': len(cluster),
                    'channels': list(channels),
                    'time_span': (cluster[-1].created_at - cluster[0].created_at).total_seconds() / 3600
                })
        
        return {
            'total_clusters': len(clusters),
            'cross_channel_clusters': len(cross_channel_clusters),
            'largest_cluster_size': max(len(cluster) for cluster in clusters) if clusters else 0,
            'threading_potential': 'high' if cross_channel_clusters else 'medium' if clusters else 'low',
            'cluster_details': cross_channel_clusters[:5]  # Top 5 for analysis
        }
    
    def _analyze_content_references(self, messages: List[Message]) -> Dict[str, Any]:
        """Analyze content references between messages"""
        content_refs = {
            'quoted_content': 0,
            'forwarded_messages': 0,
            'message_references': 0,
            'conversation_continuity': []
        }
        
        # Look for quoted content, forwarded messages, explicit references
        for message in messages:
            content = message.content.lower() if message.content else ''
            
            # Check for quoted content indicators
            if any(indicator in content for indicator in ['>', '-----original message-----', 'wrote:', 'said:']):
                content_refs['quoted_content'] += 1
            
            # Check for forwarded message indicators
            if any(indicator in content for indicator in ['fwd:', 'forwarded message', 'begin forwarded']):
                content_refs['forwarded_messages'] += 1
            
            # Check for explicit message references
            if any(indicator in content for indicator in ['your message', 'previous email', 'earlier conversation']):
                content_refs['message_references'] += 1
        
        return {
            **content_refs,
            'threading_potential': 'high' if content_refs['quoted_content'] > 0 else 'medium'
        }
    
    def _analyze_cross_channel_sequences(self, messages: List[Message]) -> Dict[str, Any]:
        """Analyze sequences of messages across different channels"""
        sequences = []
        
        # Group messages by day and analyze channel transitions
        daily_groups = {}
        for message in messages:
            if message.created_at:
                day = message.created_at.date()
                if day not in daily_groups:
                    daily_groups[day] = []
                daily_groups[day].append(message)
        
        # Analyze channel switching patterns
        channel_switches = []
        for day, day_messages in daily_groups.items():
            if len(day_messages) > 1:
                sorted_day_messages = sorted(day_messages, key=lambda m: m.created_at)
                prev_channel = None
                
                for message in sorted_day_messages:
                    channel = message.channel or (message.conversation.channel if message.conversation else None)
                    current_channel = channel.channel_type if channel else None
                    
                    if prev_channel and current_channel and prev_channel != current_channel:
                        channel_switches.append({
                            'from_channel': prev_channel,
                            'to_channel': current_channel,
                            'time_gap_minutes': 0  # Could calculate actual gap
                        })
                    
                    prev_channel = current_channel
        
        return {
            'total_channel_switches': len(channel_switches),
            'switch_patterns': channel_switches[:10],  # Top 10 patterns
            'threading_potential': 'high' if len(channel_switches) > 2 else 'low'
        }
    
    def _identify_potential_threads(self, record: Record, conversations: List[Conversation], 
                                  messages: List[Message], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify potential conversation threads based on analysis"""
        potential_threads = []
        
        # Thread 1: Group by temporal proximity and channel switching
        temporal_signals = analysis['threading_signals']['temporal_clusters']
        if temporal_signals['threading_potential'] == 'high':
            for cluster_detail in temporal_signals.get('cluster_details', []):
                potential_threads.append({
                    'type': 'temporal_cross_channel',
                    'confidence': 0.8,
                    'channels': cluster_detail['channels'],
                    'message_count': cluster_detail['messages'],
                    'strategy': 'temporal_proximity'
                })
        
        # Thread 2: Group by email references
        email_signals = analysis['threading_signals']['email_references']
        if email_signals['threading_potential'] == 'high':
            potential_threads.append({
                'type': 'email_thread_chain',
                'confidence': 0.9,
                'thread_count': email_signals['identifiable_threads'],
                'strategy': 'email_references'
            })
        
        # Thread 3: Group by subject similarity
        subject_signals = analysis['threading_signals']['subject_patterns']
        if subject_signals['potential_subject_threads'] > 0:
            potential_threads.append({
                'type': 'subject_based',
                'confidence': 0.7,
                'thread_count': subject_signals['potential_subject_threads'],
                'strategy': 'subject_similarity'
            })
        
        # Thread 4: Content reference based
        content_signals = analysis['threading_signals']['content_references']
        if content_signals['threading_potential'] == 'high':
            potential_threads.append({
                'type': 'content_reference',
                'confidence': 0.8,
                'quoted_messages': content_signals['quoted_content'],
                'strategy': 'content_references'
            })
        
        # Always include the basic Record-based thread
        potential_threads.append({
            'type': 'record_unified',
            'confidence': 1.0,
            'conversation_count': len(conversations),
            'message_count': len(messages),
            'channels': analysis['channels_involved'],
            'strategy': 'same_contact_record'
        })
        
        return potential_threads
    
    def _apply_threading_strategies(self, record: Record, analysis: Dict[str, Any], 
                                  force_rethread: bool) -> Dict[str, Any]:
        """Apply threading strategies based on analysis"""
        results = {
            'thread_groups': [],
            'strategies_used': [],
            'total_messages_threaded': 0,
            'threading_metadata': {}
        }
        
        # Apply strategies in order of confidence
        potential_threads = sorted(analysis['potential_threads'], key=lambda x: x.get('confidence', 0), reverse=True)
        
        for thread in potential_threads:
            strategy_name = thread['strategy']
            if strategy_name in self.threading_strategies:
                strategy_func = self.threading_strategies[strategy_name]
                
                try:
                    strategy_result = strategy_func(record, thread, analysis, force_rethread)
                    if strategy_result['success']:
                        results['thread_groups'].extend(strategy_result.get('thread_groups', []))
                        results['strategies_used'].append(strategy_name)
                        results['total_messages_threaded'] += strategy_result.get('messages_threaded', 0)
                        results['threading_metadata'][strategy_name] = strategy_result.get('metadata', {})
                        
                        self.logger.info(f"Applied threading strategy '{strategy_name}' for record {record.id}")
                    
                except Exception as e:
                    self.logger.warning(f"Error applying threading strategy '{strategy_name}': {e}")
        
        return results
    
    def _thread_by_contact_record(self, record: Record, thread_config: Dict[str, Any], 
                                analysis: Dict[str, Any], force_rethread: bool) -> Dict[str, Any]:
        """Primary threading strategy: group all conversations/messages by Record"""
        try:
            conversations = self._get_record_conversations(record)
            messages = self._get_record_messages(record)
            
            # Create unified thread group
            thread_group = {
                'id': f"record_{record.id}_unified",
                'type': 'record_unified',
                'record_id': record.id,
                'conversation_ids': [str(conv.id) for conv in conversations],
                'message_ids': [str(msg.id) for msg in messages],
                'channels': list(set(analysis['channels_involved'])),
                'created_at': timezone.now(),
                'strategy': 'same_contact_record',
                'metadata': {
                    'record_title': record.title,
                    'pipeline_name': record.pipeline.name,
                    'total_conversations': len(conversations),
                    'total_messages': len(messages),
                    'time_span': analysis.get('time_span')
                }
            }
            
            return {
                'success': True,
                'thread_groups': [thread_group],
                'messages_threaded': len(messages),
                'conversations_threaded': len(conversations),
                'metadata': thread_group['metadata']
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _thread_by_email_references(self, record: Record, thread_config: Dict[str, Any], 
                                  analysis: Dict[str, Any], force_rethread: bool) -> Dict[str, Any]:
        """Thread by email reference headers (Message-ID, In-Reply-To, References)"""
        try:
            messages = self._get_record_messages(record)
            email_messages = [msg for msg in messages if msg.metadata and msg.metadata.get('email_headers')]
            
            if not email_messages:
                return {'success': False, 'error': 'No email messages with headers found'}
            
            # Build email thread chains
            thread_chains = self._build_email_thread_chains_from_messages(email_messages)
            
            thread_groups = []
            for i, chain in enumerate(thread_chains):
                thread_group = {
                    'id': f"record_{record.id}_email_thread_{i}",
                    'type': 'email_thread_chain',
                    'record_id': record.id,
                    'message_ids': [str(msg.id) for msg in chain],
                    'channels': ['email'],
                    'created_at': timezone.now(),
                    'strategy': 'email_references',
                    'metadata': {
                        'chain_length': len(chain),
                        'root_message_id': chain[0].external_message_id if chain else None,
                        'latest_message_date': max(msg.created_at for msg in chain if msg.created_at) if chain else None
                    }
                }
                thread_groups.append(thread_group)
            
            return {
                'success': True,
                'thread_groups': thread_groups,
                'messages_threaded': sum(len(chain) for chain in thread_chains),
                'metadata': {'thread_chains_created': len(thread_chains)}
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _thread_by_temporal_proximity(self, record: Record, thread_config: Dict[str, Any], 
                                    analysis: Dict[str, Any], force_rethread: bool) -> Dict[str, Any]:
        """Thread by temporal proximity across channels"""
        try:
            temporal_analysis = analysis['threading_signals']['temporal_clusters']
            if temporal_analysis['threading_potential'] == 'low':
                return {'success': False, 'error': 'Low temporal threading potential'}
            
            messages = self._get_record_messages(record)
            temporal_groups = self._create_temporal_message_groups(messages)
            
            thread_groups = []
            for i, group in enumerate(temporal_groups):
                if len(group) > 1:  # Only create threads for groups with multiple messages
                    channels = set()
                    for msg in group:
                        channel = msg.channel or (msg.conversation.channel if msg.conversation else None)
                        if channel:
                            channels.add(channel.channel_type)
                    
                    thread_group = {
                        'id': f"record_{record.id}_temporal_{i}",
                        'type': 'temporal_proximity',
                        'record_id': record.id,
                        'message_ids': [str(msg.id) for msg in group],
                        'channels': list(channels),
                        'created_at': timezone.now(),
                        'strategy': 'temporal_proximity',
                        'metadata': {
                            'time_window_start': min(msg.created_at for msg in group if msg.created_at),
                            'time_window_end': max(msg.created_at for msg in group if msg.created_at),
                            'cross_channel': len(channels) > 1
                        }
                    }
                    thread_groups.append(thread_group)
            
            return {
                'success': True,
                'thread_groups': thread_groups,
                'messages_threaded': sum(len(group) for group in temporal_groups if len(group) > 1),
                'metadata': {'temporal_groups_created': len(thread_groups)}
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _thread_by_subject_similarity(self, record: Record, thread_config: Dict[str, Any], 
                                    analysis: Dict[str, Any], force_rethread: bool) -> Dict[str, Any]:
        """Thread by subject line similarity"""
        try:
            messages = self._get_record_messages(record)
            subject_messages = [msg for msg in messages if msg.subject]
            
            if not subject_messages:
                return {'success': False, 'error': 'No messages with subjects found'}
            
            # Group by normalized subject
            subject_groups = {}
            for message in subject_messages:
                normalized_subject = self._normalize_subject(message.subject)
                if normalized_subject not in subject_groups:
                    subject_groups[normalized_subject] = []
                subject_groups[normalized_subject].append(message)
            
            # Create thread groups for subjects with multiple messages
            thread_groups = []
            for subject, group in subject_groups.items():
                if len(group) > 1:
                    channels = set()
                    for msg in group:
                        channel = msg.channel or (msg.conversation.channel if msg.conversation else None)
                        if channel:
                            channels.add(channel.channel_type)
                    
                    thread_group = {
                        'id': f"record_{record.id}_subject_{hash(subject) % 10000}",
                        'type': 'subject_similarity',
                        'record_id': record.id,
                        'message_ids': [str(msg.id) for msg in group],
                        'channels': list(channels),
                        'created_at': timezone.now(),
                        'strategy': 'subject_similarity',
                        'metadata': {
                            'normalized_subject': subject,
                            'message_count': len(group),
                            'cross_channel': len(channels) > 1
                        }
                    }
                    thread_groups.append(thread_group)
            
            return {
                'success': True,
                'thread_groups': thread_groups,
                'messages_threaded': sum(len(group) for group in subject_groups.values() if len(group) > 1),
                'metadata': {'subject_threads_created': len(thread_groups)}
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _thread_by_content_references(self, record: Record, thread_config: Dict[str, Any], 
                                    analysis: Dict[str, Any], force_rethread: bool) -> Dict[str, Any]:
        """Thread by content references and quoted material"""
        try:
            messages = self._get_record_messages(record)
            reference_chains = self._build_content_reference_chains(messages)
            
            thread_groups = []
            for i, chain in enumerate(reference_chains):
                if len(chain) > 1:
                    channels = set()
                    for msg in chain:
                        channel = msg.channel or (msg.conversation.channel if msg.conversation else None)
                        if channel:
                            channels.add(channel.channel_type)
                    
                    thread_group = {
                        'id': f"record_{record.id}_content_ref_{i}",
                        'type': 'content_reference',
                        'record_id': record.id,
                        'message_ids': [str(msg.id) for msg in chain],
                        'channels': list(channels),
                        'created_at': timezone.now(),
                        'strategy': 'content_references',
                        'metadata': {
                            'reference_chain_length': len(chain),
                            'cross_channel': len(channels) > 1
                        }
                    }
                    thread_groups.append(thread_group)
            
            return {
                'success': True,
                'thread_groups': thread_groups,
                'messages_threaded': sum(len(chain) for chain in reference_chains if len(chain) > 1),
                'metadata': {'content_reference_chains': len(thread_groups)}
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # Helper methods
    
    def _normalize_subject(self, subject: str) -> str:
        """Normalize subject line for comparison"""
        if not subject:
            return ''
        
        # Remove common prefixes and normalize
        normalized = subject.lower().strip()
        prefixes = ['re:', 'fwd:', 'fw:', 'fwd', 'fw']
        
        for prefix in prefixes:
            while normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
        
        # Remove bracketed content like [EXTERNAL]
        import re
        normalized = re.sub(r'\[.*?\]', '', normalized).strip()
        normalized = re.sub(r'\(.*?\)', '', normalized).strip()
        
        return normalized
    
    def _build_email_thread_chains(self, email_refs: Dict[str, Set]) -> List[List]:
        """Build email thread chains from reference data"""
        # This is a simplified version - could be enhanced with more sophisticated logic
        chains = []
        
        # For now, just group by shared references
        # In practice, this would parse the reference headers more carefully
        
        return chains
    
    def _build_email_thread_chains_from_messages(self, email_messages: List[Message]) -> List[List[Message]]:
        """Build email thread chains from actual messages"""
        chains = []
        processed_messages = set()
        
        for message in email_messages:
            if message.id in processed_messages:
                continue
                
            chain = [message]
            processed_messages.add(message.id)
            
            # Look for replies to this message
            message_id = message.metadata.get('email_headers', {}).get('Message-ID')
            if message_id:
                for other_message in email_messages:
                    if other_message.id in processed_messages:
                        continue
                    
                    in_reply_to = other_message.metadata.get('email_headers', {}).get('In-Reply-To')
                    if in_reply_to == message_id:
                        chain.append(other_message)
                        processed_messages.add(other_message.id)
            
            if len(chain) > 1:
                chains.append(chain)
        
        return chains
    
    def _create_temporal_message_groups(self, messages: List[Message]) -> List[List[Message]]:
        """Create temporal groups of messages"""
        if not messages:
            return []
        
        time_window = timedelta(hours=2)  # 2-hour window for grouping
        groups = []
        
        sorted_messages = sorted(messages, key=lambda m: m.created_at or timezone.now())
        current_group = [sorted_messages[0]]
        
        for message in sorted_messages[1:]:
            if message.created_at and current_group[-1].created_at:
                time_diff = message.created_at - current_group[-1].created_at
                if time_diff <= time_window:
                    current_group.append(message)
                else:
                    groups.append(current_group)
                    current_group = [message]
            else:
                current_group.append(message)
        
        groups.append(current_group)
        return groups
    
    def _build_content_reference_chains(self, messages: List[Message]) -> List[List[Message]]:
        """Build chains based on content references"""
        chains = []
        processed_messages = set()
        
        for message in messages:
            if message.id in processed_messages or not message.content:
                continue
            
            content = message.content.lower()
            
            # Look for quoted content or references
            if any(indicator in content for indicator in ['>', '-----original message-----', 'wrote:', 'said:']):
                chain = [message]
                processed_messages.add(message.id)
                
                # This is simplified - in practice, would analyze the quoted content
                # to find the original message being referenced
                
                chains.append(chain)
        
        return chains
    
    def _create_thread_metadata(self, record: Record, threading_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata for the threading results"""
        return {
            'record_id': record.id,
            'threading_timestamp': timezone.now().isoformat(),
            'total_thread_groups': len(threading_results.get('thread_groups', [])),
            'strategies_applied': threading_results.get('strategies_used', []),
            'total_messages_in_threads': threading_results.get('total_messages_threaded', 0),
            'threading_summary': {
                strategy: threading_results['threading_metadata'].get(strategy, {})
                for strategy in threading_results.get('strategies_used', [])
            }
        }
    
    def _update_conversation_threading(self, threading_results: Dict[str, Any]) -> List[str]:
        """Update conversations with threading metadata"""
        updated_conversations = []
        
        for thread_group in threading_results.get('thread_groups', []):
            conversation_ids = thread_group.get('conversation_ids', [])
            
            for conv_id in conversation_ids:
                try:
                    conversation = Conversation.objects.get(id=conv_id)
                    
                    if not conversation.metadata:
                        conversation.metadata = {}
                    
                    conversation.metadata['thread_group_id'] = thread_group['id']
                    conversation.metadata['threading_strategy'] = thread_group['strategy']
                    conversation.metadata['thread_type'] = thread_group['type']
                    conversation.metadata['thread_updated_at'] = timezone.now().isoformat()
                    
                    conversation.save(update_fields=['metadata'])
                    updated_conversations.append(conv_id)
                    
                except Conversation.DoesNotExist:
                    self.logger.warning(f"Conversation {conv_id} not found for threading update")
        
        return updated_conversations


# Global service instance
conversation_threading_service = ConversationThreadingService()