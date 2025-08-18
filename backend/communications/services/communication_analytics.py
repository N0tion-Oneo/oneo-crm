"""
Communication Analytics Service
Provides relationship intelligence and communication analytics
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from django.db.models import Q, Count, Avg, Max, Min, Sum, F, Case, When, Value, DateField
from django.db.models.functions import Coalesce, TruncDate, Cast
from django.utils import timezone as tz
from pipelines.models import Record
from .models import Message, Conversation
import logging

logger = logging.getLogger(__name__)


class CommunicationAnalyticsService:
    """Service for communication analytics and relationship intelligence"""
    
    def __init__(self):
        self.cache_ttl = 300  # 5 minutes

    def get_record_analytics(self, record: Record, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive communication analytics for a record"""
        end_date = tz.now()
        start_date = end_date - timedelta(days=days)
        
        # Get all conversations for this record
        conversations = Conversation.objects.filter(
            Q(primary_record=record) | Q(contact_records=record)
        ).distinct()
        
        # Get all messages in these conversations
        messages = Message.objects.filter(
            conversation__in=conversations,
            created_at__gte=start_date
        ).select_related('conversation')
        
        return {
            'record_id': record.id,
            'record_title': record.data.get('title', f'Record {record.id}'),
            'period_days': days,
            'summary': self._calculate_summary_metrics(messages, record),
            'channel_breakdown': self._calculate_channel_metrics(messages, record),
            'engagement_metrics': self._calculate_engagement_metrics(messages, conversations, record),
            'response_patterns': self._analyze_response_patterns(messages, record),
            'communication_trends': self._analyze_communication_trends(messages, days),
            'relationship_health': self._calculate_relationship_health(messages, conversations, record),
            'recommendations': self._generate_recommendations(messages, conversations, record)
        }

    def _calculate_summary_metrics(self, messages, record: Record) -> Dict[str, Any]:
        """Calculate high-level summary metrics"""
        outbound_messages = messages.filter(direction='outbound')
        inbound_messages = messages.filter(direction='inbound')
        
        total_messages = messages.count()
        outbound_count = outbound_messages.count()
        inbound_count = inbound_messages.count()
        
        return {
            'total_messages': total_messages,
            'outbound_messages': outbound_count,
            'inbound_messages': inbound_count,
            'response_rate': (inbound_count / max(outbound_count, 1)) * 100,
            'initiation_rate': (outbound_count / max(total_messages, 1)) * 100,
            'unique_conversations': messages.values('conversation').distinct().count(),
            'active_channels': messages.values('channel_type').distinct().count(),
            'first_contact': messages.order_by('created_at').first().created_at if messages.exists() else None,
            'last_contact': messages.order_by('-created_at').first().created_at if messages.exists() else None
        }

    def _calculate_channel_metrics(self, messages, record: Record) -> Dict[str, Any]:
        """Calculate metrics broken down by channel"""
        channel_data = {}
        
        for channel_type in messages.values_list('channel_type', flat=True).distinct():
            channel_messages = messages.filter(channel_type=channel_type)
            
            outbound = channel_messages.filter(direction='outbound').count()
            inbound = channel_messages.filter(direction='inbound').count()
            total = channel_messages.count()
            
            # Calculate average response time for this channel
            response_times = []
            outbound_msgs = channel_messages.filter(direction='outbound').order_by('created_at')
            
            for out_msg in outbound_msgs:
                next_inbound = channel_messages.filter(
                    direction='inbound',
                    created_at__gt=out_msg.created_at,
                    conversation=out_msg.conversation
                ).order_by('created_at').first()
                
                if next_inbound:
                    response_time = (next_inbound.created_at - out_msg.created_at).total_seconds() / 3600  # hours
                    response_times.append(response_time)
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else None
            
            channel_data[channel_type] = {
                'total_messages': total,
                'outbound_messages': outbound,
                'inbound_messages': inbound,
                'response_rate': (inbound / max(outbound, 1)) * 100,
                'message_share': (total / max(messages.count(), 1)) * 100,
                'avg_response_time_hours': avg_response_time,
                'last_activity': channel_messages.order_by('-created_at').first().created_at if channel_messages.exists() else None
            }
        
        return channel_data

    def _calculate_engagement_metrics(self, messages, conversations, record: Record) -> Dict[str, Any]:
        """Calculate engagement quality metrics"""
        
        # Message length analysis
        content_lengths = [len(msg.content) for msg in messages if msg.content]
        avg_message_length = sum(content_lengths) / len(content_lengths) if content_lengths else 0
        
        # Conversation depth (messages per conversation)
        conversation_depths = []
        for conv in conversations:
            depth = messages.filter(conversation=conv).count()
            conversation_depths.append(depth)
        
        avg_conversation_depth = sum(conversation_depths) / len(conversation_depths) if conversation_depths else 0
        
        # Subject line analysis (for email channels)
        email_messages = messages.filter(channel_type__in=['gmail', 'outlook', 'mail'])
        messages_with_subjects = email_messages.exclude(Q(subject='') | Q(subject__isnull=True)).count()
        subject_rate = (messages_with_subjects / max(email_messages.count(), 1)) * 100
        
        # Attachment usage
        messages_with_attachments = messages.exclude(attachments__isnull=True).exclude(attachments__exact=[]).count()
        attachment_rate = (messages_with_attachments / max(messages.count(), 1)) * 100
        
        return {
            'avg_message_length': round(avg_message_length, 1),
            'avg_conversation_depth': round(avg_conversation_depth, 1),
            'subject_line_usage_rate': round(subject_rate, 1),
            'attachment_usage_rate': round(attachment_rate, 1),
            'engagement_score': self._calculate_engagement_score(messages, conversations)
        }

    def _analyze_response_patterns(self, messages, record: Record) -> Dict[str, Any]:
        """Analyze response timing and patterns"""
        
        # Group messages by day of week
        weekday_counts = defaultdict(int)
        for msg in messages:
            weekday = msg.created_at.strftime('%A')
            weekday_counts[weekday] += 1
        
        # Group messages by hour of day
        hour_counts = defaultdict(int)
        for msg in messages:
            hour = msg.created_at.hour
            hour_counts[hour] += 1
        
        # Find peak activity times
        peak_weekday = max(weekday_counts.items(), key=lambda x: x[1]) if weekday_counts else ('N/A', 0)
        peak_hour = max(hour_counts.items(), key=lambda x: x[1]) if hour_counts else (0, 0)
        
        # Response time analysis
        response_times = []
        outbound_messages = messages.filter(direction='outbound').order_by('created_at')
        
        for out_msg in outbound_messages:
            next_inbound = messages.filter(
                direction='inbound',
                created_at__gt=out_msg.created_at,
                conversation=out_msg.conversation
            ).order_by('created_at').first()
            
            if next_inbound:
                response_time = (next_inbound.created_at - out_msg.created_at).total_seconds() / 3600  # hours
                response_times.append(response_time)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        median_response_time = sorted(response_times)[len(response_times)//2] if response_times else None
        
        return {
            'weekday_distribution': dict(weekday_counts),
            'hourly_distribution': dict(hour_counts),
            'peak_weekday': peak_weekday[0],
            'peak_hour': peak_hour[0],
            'avg_response_time_hours': round(avg_response_time, 2) if avg_response_time else None,
            'median_response_time_hours': round(median_response_time, 2) if median_response_time else None,
            'response_consistency': self._calculate_response_consistency(response_times)
        }

    def _analyze_communication_trends(self, messages, days: int) -> Dict[str, Any]:
        """Analyze communication trends over time"""
        
        # Group messages by date
        daily_counts = defaultdict(int)
        daily_outbound = defaultdict(int)
        daily_inbound = defaultdict(int)
        
        for msg in messages:
            date_key = msg.created_at.date().isoformat()
            daily_counts[date_key] += 1
            
            if msg.direction == 'outbound':
                daily_outbound[date_key] += 1
            else:
                daily_inbound[date_key] += 1
        
        # Calculate trend direction
        dates = sorted(daily_counts.keys())
        if len(dates) >= 7:
            recent_avg = sum(daily_counts[d] for d in dates[-7:]) / 7
            earlier_avg = sum(daily_counts[d] for d in dates[-14:-7]) / 7 if len(dates) >= 14 else recent_avg
            trend_direction = 'increasing' if recent_avg > earlier_avg else 'decreasing' if recent_avg < earlier_avg else 'stable'
        else:
            trend_direction = 'insufficient_data'
        
        return {
            'daily_message_counts': dict(daily_counts),
            'daily_outbound_counts': dict(daily_outbound),
            'daily_inbound_counts': dict(daily_inbound),
            'trend_direction': trend_direction,
            'peak_activity_date': max(daily_counts.items(), key=lambda x: x[1])[0] if daily_counts else None,
            'total_active_days': len([d for d in daily_counts.values() if d > 0])
        }

    def _calculate_relationship_health(self, messages, conversations, record: Record) -> Dict[str, Any]:
        """Calculate relationship health indicators"""
        
        # Recent activity (last 7 days)
        week_ago = tz.now() - timedelta(days=7)
        recent_messages = messages.filter(created_at__gte=week_ago)
        
        # Communication balance
        total_messages = messages.count()
        outbound_count = messages.filter(direction='outbound').count()
        inbound_count = messages.filter(direction='inbound').count()
        
        balance_score = min(outbound_count, inbound_count) / max(max(outbound_count, inbound_count), 1) * 100
        
        # Response rate
        response_rate = (inbound_count / max(outbound_count, 1)) * 100
        
        # Conversation initiation balance
        initiated_conversations = conversations.filter(
            messages__direction='outbound',
            messages__created_at=F('created_at')
        ).distinct().count()
        
        total_conversations = conversations.count()
        initiation_balance = (initiated_conversations / max(total_conversations, 1)) * 100
        
        # Calculate overall health score
        health_score = (balance_score * 0.3 + min(response_rate, 100) * 0.4 + (100 - abs(50 - initiation_balance)) * 0.3)
        
        return {
            'health_score': round(health_score, 1),
            'communication_balance': round(balance_score, 1),
            'response_rate': round(response_rate, 1),
            'initiation_balance': round(initiation_balance, 1),
            'recent_activity': recent_messages.count(),
            'relationship_age_days': (tz.now() - messages.order_by('created_at').first().created_at).days if messages.exists() else 0,
            'status': self._get_health_status(health_score)
        }

    def _generate_recommendations(self, messages, conversations, record: Record) -> List[Dict[str, Any]]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Analyze recent activity
        week_ago = tz.now() - timedelta(days=7)
        recent_messages = messages.filter(created_at__gte=week_ago)
        
        if recent_messages.count() == 0:
            recommendations.append({
                'type': 'engagement',
                'priority': 'high',
                'title': 'No recent communication',
                'description': 'No messages in the last 7 days. Consider reaching out to maintain the relationship.',
                'action': 'send_followup'
            })
        
        # Check response rate
        outbound_count = messages.filter(direction='outbound').count()
        inbound_count = messages.filter(direction='inbound').count()
        response_rate = (inbound_count / max(outbound_count, 1)) * 100
        
        if response_rate < 30 and outbound_count > 3:
            recommendations.append({
                'type': 'response_rate',
                'priority': 'medium',
                'title': 'Low response rate',
                'description': f'Response rate is {response_rate:.1f}%. Consider changing communication approach or timing.',
                'action': 'adjust_strategy'
            })
        
        # Check channel diversification
        unique_channels = messages.values('channel_type').distinct().count()
        if unique_channels == 1 and messages.count() > 10:
            recommendations.append({
                'type': 'channel_diversity',
                'priority': 'low',
                'title': 'Single channel communication',
                'description': 'Consider using multiple communication channels for better engagement.',
                'action': 'diversify_channels'
            })
        
        # Check for long conversations without progression
        long_conversations = conversations.annotate(
            message_count=Count('messages')
        ).filter(message_count__gt=20)
        
        if long_conversations.exists():
            recommendations.append({
                'type': 'conversation_management',
                'priority': 'medium',
                'title': 'Long conversations detected',
                'description': 'Some conversations are very long. Consider summarizing or moving to a call.',
                'action': 'escalate_communication'
            })
        
        return recommendations

    def _calculate_engagement_score(self, messages, conversations) -> float:
        """Calculate overall engagement score (0-100)"""
        
        if not messages.exists():
            return 0.0
        
        factors = []
        
        # Response rate factor
        outbound = messages.filter(direction='outbound').count()
        inbound = messages.filter(direction='inbound').count()
        response_rate = (inbound / max(outbound, 1)) * 100
        factors.append(min(response_rate, 100) * 0.3)
        
        # Message frequency factor
        days_active = (tz.now() - messages.order_by('created_at').first().created_at).days
        if days_active > 0:
            frequency = messages.count() / days_active
            frequency_score = min(frequency * 20, 100)  # Cap at 100
            factors.append(frequency_score * 0.2)
        
        # Conversation depth factor
        avg_depth = messages.count() / max(conversations.count(), 1)
        depth_score = min(avg_depth * 10, 100)  # Cap at 100
        factors.append(depth_score * 0.2)
        
        # Recent activity factor
        week_ago = tz.now() - timedelta(days=7)
        recent_activity = messages.filter(created_at__gte=week_ago).count()
        activity_score = min(recent_activity * 20, 100)  # Cap at 100
        factors.append(activity_score * 0.3)
        
        return sum(factors)

    def _calculate_response_consistency(self, response_times: List[float]) -> str:
        """Calculate how consistent response times are"""
        if len(response_times) < 3:
            return 'insufficient_data'
        
        avg_time = sum(response_times) / len(response_times)
        variance = sum((t - avg_time) ** 2 for t in response_times) / len(response_times)
        std_dev = variance ** 0.5
        
        # Coefficient of variation
        cv = std_dev / avg_time if avg_time > 0 else 0
        
        if cv < 0.5:
            return 'very_consistent'
        elif cv < 1.0:
            return 'consistent'
        elif cv < 2.0:
            return 'variable'
        else:
            return 'inconsistent'

    def _get_health_status(self, health_score: float) -> str:
        """Get health status based on score"""
        if health_score >= 80:
            return 'excellent'
        elif health_score >= 60:
            return 'good'
        elif health_score >= 40:
            return 'fair'
        elif health_score >= 20:
            return 'poor'
        else:
            return 'critical'

    def get_portfolio_analytics(self, limit: int = 20) -> Dict[str, Any]:
        """Get analytics across all records in the portfolio"""
        
        # Get top records by message volume
        record_stats = []
        
        # Get all records with communication activity
        records_with_activity = Record.objects.filter(
            Q(primary_conversations__isnull=False) |
            Q(message_contact_records__isnull=False)
        ).distinct()[:limit]
        
        for record in records_with_activity:
            conversations = Conversation.objects.filter(
                Q(primary_record=record) | Q(contact_records=record)
            ).distinct()
            
            messages = Message.objects.filter(conversation__in=conversations)
            
            if messages.exists():
                analytics = self.get_record_analytics(record, days=30)
                record_stats.append({
                    'record_id': record.id,
                    'record_title': record.data.get('title', f'Record {record.id}'),
                    'total_messages': analytics['summary']['total_messages'],
                    'health_score': analytics['relationship_health']['health_score'],
                    'response_rate': analytics['summary']['response_rate'],
                    'last_contact': analytics['summary']['last_contact']
                })
        
        # Sort by health score
        record_stats.sort(key=lambda x: x['health_score'], reverse=True)
        
        return {
            'total_active_records': len(record_stats),
            'top_records_by_health': record_stats[:10],
            'records_needing_attention': [r for r in record_stats if r['health_score'] < 50][:5],
            'portfolio_summary': {
                'avg_health_score': sum(r['health_score'] for r in record_stats) / len(record_stats) if record_stats else 0,
                'avg_response_rate': sum(r['response_rate'] for r in record_stats) / len(record_stats) if record_stats else 0,
                'total_messages': sum(r['total_messages'] for r in record_stats)
            }
        }