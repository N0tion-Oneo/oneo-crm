"""
Communication Analytics and Reporting System
Provides advanced analytics, insights, and reporting capabilities
"""
import logging
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass

from django.db import models
from django.db.models import Q, Count, Avg, Sum, F, Case, When, Value
from django.utils import timezone
from django.core.cache import cache

from ..models import Channel, Message, Conversation, MessageDirection, MessageStatus
from .models import (
    CommunicationTracking, DeliveryTracking, ReadTracking, 
    ResponseTracking, CampaignTracking, PerformanceMetrics,
    TrackingType
)

logger = logging.getLogger(__name__)


@dataclass
class PerformanceInsight:
    """Data structure for performance insights"""
    metric: str
    current_value: float
    previous_value: float
    change_percentage: float
    trend: str  # 'up', 'down', 'stable'
    recommendation: str


@dataclass
class ChannelComparison:
    """Data structure for channel performance comparison"""
    channel_name: str
    channel_type: str
    delivery_rate: float
    open_rate: float
    response_rate: float
    engagement_score: float
    total_messages: int
    ranking: int


class CommunicationAnalyzer:
    """
    Advanced analytics engine for communication performance
    Provides insights, trends, and recommendations
    """
    
    def __init__(self):
        self.cache_timeout = 600  # 10 minutes
        
    # === TREND ANALYSIS ===
    
    def analyze_performance_trends(
        self, 
        channel: Channel = None,
        days: int = 30
    ) -> Dict[str, List[PerformanceInsight]]:
        """Analyze performance trends over time"""
        cache_key = f"performance_trends_{channel.id if channel else 'all'}_{days}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            mid_date = start_date + timedelta(days=days//2)
            
            # Get metrics for two periods
            period1_metrics = self._get_period_metrics(start_date, mid_date, channel)
            period2_metrics = self._get_period_metrics(mid_date, end_date, channel)
            
            insights = {
                'delivery_performance': [],
                'engagement_metrics': [],
                'response_analytics': [],
                'quality_indicators': []
            }
            
            # Delivery performance insights
            insights['delivery_performance'].extend([
                self._create_insight(
                    'Delivery Rate',
                    period2_metrics.get('delivery_rate', 0),
                    period1_metrics.get('delivery_rate', 0),
                    'Higher delivery rates indicate better sender reputation and list quality.'
                ),
                self._create_insight(
                    'Bounce Rate',
                    period2_metrics.get('bounce_rate', 0),
                    period1_metrics.get('bounce_rate', 0),
                    'Lower bounce rates suggest cleaner contact lists and better targeting.',
                    reverse_trend=True
                )
            ])
            
            # Engagement metrics insights
            insights['engagement_metrics'].extend([
                self._create_insight(
                    'Open Rate',
                    period2_metrics.get('open_rate', 0),
                    period1_metrics.get('open_rate', 0),
                    'Higher open rates indicate compelling subject lines and sender trust.'
                ),
                self._create_insight(
                    'Response Rate',
                    period2_metrics.get('response_rate', 0),
                    period1_metrics.get('response_rate', 0),
                    'Higher response rates show engaging content and clear calls-to-action.'
                )
            ])
            
            # Response analytics insights
            insights['response_analytics'].extend([
                self._create_insight(
                    'Average Response Time',
                    period2_metrics.get('avg_response_time', 0),
                    period1_metrics.get('avg_response_time', 0),
                    'Faster response times indicate higher engagement and urgency.',
                    reverse_trend=True,
                    unit='minutes'
                )
            ])
            
            cache.set(cache_key, insights, self.cache_timeout)
            return insights
            
        except Exception as e:
            logger.error(f"Failed to analyze performance trends: {e}")
            return {}
    
    def generate_channel_comparison(
        self, 
        days: int = 30
    ) -> List[ChannelComparison]:
        """Generate performance comparison across all channels"""
        cache_key = f"channel_comparison_{days}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            channels = Channel.objects.filter(is_active=True)
            comparisons = []
            
            for channel in channels:
                metrics = self._get_period_metrics(start_date, end_date, channel)
                
                comparison = ChannelComparison(
                    channel_name=channel.name,
                    channel_type=channel.channel_type,
                    delivery_rate=metrics.get('delivery_rate', 0),
                    open_rate=metrics.get('open_rate', 0),
                    response_rate=metrics.get('response_rate', 0),
                    engagement_score=metrics.get('engagement_score', 0),
                    total_messages=metrics.get('total_messages', 0),
                    ranking=0  # Will be set after sorting
                )
                comparisons.append(comparison)
            
            # Sort by engagement score and assign rankings
            comparisons.sort(key=lambda x: x.engagement_score, reverse=True)
            for i, comparison in enumerate(comparisons, 1):
                comparison.ranking = i
            
            cache.set(cache_key, comparisons, self.cache_timeout)
            return comparisons
            
        except Exception as e:
            logger.error(f"Failed to generate channel comparison: {e}")
            return []
    
    # === ADVANCED ANALYTICS ===
    
    def analyze_message_timing(
        self, 
        channel: Channel = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Analyze optimal message timing patterns"""
        cache_key = f"message_timing_{channel.id if channel else 'all'}_{days}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Build base query
            query = Q(created_at__date__range=[start_date, end_date])
            if channel:
                query &= Q(channel=channel)
                
            messages = Message.objects.filter(query)
            
            # Analyze by hour of day
            hourly_performance = messages.values(
                hour=models.functions.Extract('created_at', 'hour')
            ).annotate(
                total_messages=Count('id'),
                delivered_messages=Count(Case(
                    When(status=MessageStatus.DELIVERED, then=1),
                    output_field=models.IntegerField()
                )),
                read_messages=Count(Case(
                    When(status=MessageStatus.READ, then=1),
                    output_field=models.IntegerField()
                ))
            ).order_by('hour')
            
            # Analyze by day of week
            daily_performance = messages.annotate(
                weekday=models.functions.Extract('created_at', 'week_day')
            ).values('weekday').annotate(
                total_messages=Count('id'),
                delivered_messages=Count(Case(
                    When(status=MessageStatus.DELIVERED, then=1),
                    output_field=models.IntegerField()
                )),
                read_messages=Count(Case(
                    When(status=MessageStatus.READ, then=1),
                    output_field=models.IntegerField()
                ))
            ).order_by('weekday')
            
            # Calculate performance metrics
            timing_analysis = {
                'hourly_patterns': [],
                'daily_patterns': [],
                'recommendations': []
            }
            
            # Process hourly data
            best_hour = None
            best_hour_score = 0
            
            for hour_data in hourly_performance:
                if hour_data['total_messages'] > 0:
                    delivery_rate = (hour_data['delivered_messages'] / hour_data['total_messages']) * 100
                    read_rate = (hour_data['read_messages'] / hour_data['total_messages']) * 100
                    performance_score = (delivery_rate * 0.4) + (read_rate * 0.6)
                    
                    if performance_score > best_hour_score:
                        best_hour = hour_data['hour']
                        best_hour_score = performance_score
                    
                    timing_analysis['hourly_patterns'].append({
                        'hour': hour_data['hour'],
                        'total_messages': hour_data['total_messages'],
                        'delivery_rate': delivery_rate,
                        'read_rate': read_rate,
                        'performance_score': performance_score
                    })
            
            # Process daily data
            weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            best_day = None
            best_day_score = 0
            
            for day_data in daily_performance:
                if day_data['total_messages'] > 0:
                    delivery_rate = (day_data['delivered_messages'] / day_data['total_messages']) * 100
                    read_rate = (day_data['read_messages'] / day_data['total_messages']) * 100
                    performance_score = (delivery_rate * 0.4) + (read_rate * 0.6)
                    
                    if performance_score > best_day_score:
                        best_day = weekday_names[day_data['weekday'] - 2]  # Adjust for Sunday=1 vs Monday=0
                        best_day_score = performance_score
                    
                    timing_analysis['daily_patterns'].append({
                        'weekday': weekday_names[day_data['weekday'] - 2],
                        'total_messages': day_data['total_messages'],
                        'delivery_rate': delivery_rate,
                        'read_rate': read_rate,
                        'performance_score': performance_score
                    })
            
            # Generate recommendations
            if best_hour is not None:
                timing_analysis['recommendations'].append(
                    f"Optimal sending time: {best_hour}:00 with {best_hour_score:.1f}% performance score"
                )
            
            if best_day is not None:
                timing_analysis['recommendations'].append(
                    f"Best performing day: {best_day} with {best_day_score:.1f}% performance score"
                )
            
            cache.set(cache_key, timing_analysis, self.cache_timeout)
            return timing_analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze message timing: {e}")
            return {}
    
    def analyze_audience_engagement(
        self, 
        channel: Channel = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Analyze audience engagement patterns and segments"""
        cache_key = f"audience_engagement_{channel.id if channel else 'all'}_{days}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Build base query
            query = Q(response_received_at__date__range=[start_date, end_date])
            if channel:
                query &= Q(original_message__channel=channel)
            
            responses = ResponseTracking.objects.filter(query)
            
            engagement_analysis = {
                'response_patterns': {},
                'engagement_segments': [],
                'sentiment_analysis': {},
                'recommendations': []
            }
            
            # Analyze response time patterns
            response_time_ranges = [
                (0, 60, 'Immediate (0-1 hour)'),
                (61, 360, 'Quick (1-6 hours)'),
                (361, 1440, 'Same Day (6-24 hours)'),
                (1441, 4320, 'Within 3 Days'),
                (4321, float('inf'), 'Late (3+ days)')
            ]
            
            for min_time, max_time, label in response_time_ranges:
                if max_time == float('inf'):
                    count = responses.filter(response_time_minutes__gte=min_time).count()
                else:
                    count = responses.filter(
                        response_time_minutes__gte=min_time,
                        response_time_minutes__lt=max_time
                    ).count()
                
                engagement_analysis['response_patterns'][label] = count
            
            # Sentiment analysis
            sentiment_counts = responses.values('response_sentiment').annotate(
                count=Count('id')
            ).order_by('response_sentiment')
            
            total_responses = responses.count()
            for sentiment_data in sentiment_counts:
                sentiment = sentiment_data['response_sentiment']
                count = sentiment_data['count']
                percentage = (count / total_responses * 100) if total_responses > 0 else 0
                
                engagement_analysis['sentiment_analysis'][sentiment] = {
                    'count': count,
                    'percentage': percentage
                }
            
            # Generate recommendations
            if total_responses > 0:
                # Find most common response time range
                most_active_range = max(
                    engagement_analysis['response_patterns'].items(),
                    key=lambda x: x[1]
                )
                
                engagement_analysis['recommendations'].append(
                    f"Most active response period: {most_active_range[0]} "
                    f"({most_active_range[1]} responses)"
                )
                
                # Sentiment recommendations
                positive_pct = engagement_analysis['sentiment_analysis'].get('positive', {}).get('percentage', 0)
                negative_pct = engagement_analysis['sentiment_analysis'].get('negative', {}).get('percentage', 0)
                
                if negative_pct > 20:
                    engagement_analysis['recommendations'].append(
                        f"High negative sentiment ({negative_pct:.1f}%) - review message tone and content"
                    )
                elif positive_pct > 60:
                    engagement_analysis['recommendations'].append(
                        f"Excellent positive sentiment ({positive_pct:.1f}%) - current approach is working well"
                    )
            
            cache.set(cache_key, engagement_analysis, self.cache_timeout)
            return engagement_analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze audience engagement: {e}")
            return {}
    
    # === REPORTING ===
    
    def generate_performance_report(
        self, 
        channel: Channel = None,
        campaign: CampaignTracking = None,
        start_date: date = None,
        end_date: date = None
    ) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        try:
            # Set default date range
            if not end_date:
                end_date = timezone.now().date()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            report = {
                'report_metadata': {
                    'generated_at': timezone.now().isoformat(),
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'channel': channel.name if channel else 'All Channels',
                    'campaign': campaign.name if campaign else 'All Campaigns'
                },
                'executive_summary': {},
                'detailed_metrics': {},
                'performance_trends': {},
                'recommendations': []
            }
            
            # Get period metrics
            metrics = self._get_period_metrics(start_date, end_date, channel, campaign)
            
            # Executive summary
            report['executive_summary'] = {
                'total_messages_sent': metrics.get('total_messages', 0),
                'delivery_rate': metrics.get('delivery_rate', 0),
                'open_rate': metrics.get('open_rate', 0),
                'response_rate': metrics.get('response_rate', 0),
                'engagement_score': metrics.get('engagement_score', 0),
                'total_responses': metrics.get('total_responses', 0),
                'avg_response_time_hours': metrics.get('avg_response_time', 0) / 60 if metrics.get('avg_response_time') else 0
            }
            
            # Detailed metrics
            report['detailed_metrics'] = {
                'volume_metrics': {
                    'messages_sent': metrics.get('total_messages', 0),
                    'messages_delivered': metrics.get('messages_delivered', 0),
                    'messages_read': metrics.get('messages_read', 0),
                    'messages_failed': metrics.get('messages_failed', 0),
                    'responses_received': metrics.get('total_responses', 0)
                },
                'performance_rates': {
                    'delivery_rate': metrics.get('delivery_rate', 0),
                    'open_rate': metrics.get('open_rate', 0),
                    'response_rate': metrics.get('response_rate', 0),
                    'bounce_rate': metrics.get('bounce_rate', 0)
                },
                'engagement_metrics': {
                    'avg_response_time_minutes': metrics.get('avg_response_time', 0),
                    'engagement_score': metrics.get('engagement_score', 0)
                }
            }
            
            # Performance trends (compare with previous period)
            prev_start = start_date - (end_date - start_date)
            prev_end = start_date
            prev_metrics = self._get_period_metrics(prev_start, prev_end, channel, campaign)
            
            report['performance_trends'] = {
                'delivery_rate_change': metrics.get('delivery_rate', 0) - prev_metrics.get('delivery_rate', 0),
                'open_rate_change': metrics.get('open_rate', 0) - prev_metrics.get('open_rate', 0),
                'response_rate_change': metrics.get('response_rate', 0) - prev_metrics.get('response_rate', 0),
                'engagement_score_change': metrics.get('engagement_score', 0) - prev_metrics.get('engagement_score', 0)
            }
            
            # Generate recommendations
            report['recommendations'] = self._generate_recommendations(metrics, report['performance_trends'])
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return {}
    
    # === HELPER METHODS ===
    
    def _get_period_metrics(
        self, 
        start_date: date, 
        end_date: date,
        channel: Channel = None,
        campaign: CampaignTracking = None
    ) -> Dict[str, float]:
        """Get aggregated metrics for a specific period"""
        try:
            # Get performance metrics
            metrics_query = PerformanceMetrics.objects.filter(
                date__range=[start_date, end_date],
                hour__isnull=True  # Daily metrics only
            )
            
            if channel:
                metrics_query = metrics_query.filter(channel=channel)
            if campaign:
                metrics_query = metrics_query.filter(campaign=campaign)
            
            aggregated = metrics_query.aggregate(
                total_messages=Sum('messages_sent'),
                messages_delivered=Sum('messages_delivered'),
                messages_failed=Sum('messages_failed'),
                messages_read=Sum('messages_read'),
                total_responses=Sum('responses_received'),
                avg_delivery_rate=Avg('delivery_rate'),
                avg_open_rate=Avg('open_rate'),
                avg_response_rate=Avg('response_rate'),
                avg_bounce_rate=Avg('bounce_rate'),
                avg_response_time=Avg('avg_response_time_minutes')
            )
            
            # Calculate metrics with defaults
            total_messages = aggregated['total_messages'] or 0
            
            metrics = {
                'total_messages': total_messages,
                'messages_delivered': aggregated['messages_delivered'] or 0,
                'messages_failed': aggregated['messages_failed'] or 0,
                'messages_read': aggregated['messages_read'] or 0,
                'total_responses': aggregated['total_responses'] or 0,
                'delivery_rate': float(aggregated['avg_delivery_rate'] or 0),
                'open_rate': float(aggregated['avg_open_rate'] or 0),
                'response_rate': float(aggregated['avg_response_rate'] or 0),
                'bounce_rate': float(aggregated['avg_bounce_rate'] or 0),
                'avg_response_time': float(aggregated['avg_response_time'] or 0)
            }
            
            # Calculate engagement score
            if total_messages > 0:
                metrics['engagement_score'] = (
                    (metrics['delivery_rate'] * 0.3) +
                    (metrics['open_rate'] * 0.4) +
                    (metrics['response_rate'] * 0.3)
                )
            else:
                metrics['engagement_score'] = 0.0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get period metrics: {e}")
            return {}
    
    def _create_insight(
        self, 
        metric: str, 
        current: float, 
        previous: float,
        recommendation: str,
        reverse_trend: bool = False,
        unit: str = '%'
    ) -> PerformanceInsight:
        """Create a performance insight object"""
        if previous == 0:
            change_percentage = 100.0 if current > 0 else 0.0
        else:
            change_percentage = ((current - previous) / previous) * 100
        
        # Determine trend
        if abs(change_percentage) < 1:  # Less than 1% change
            trend = 'stable'
        elif change_percentage > 0:
            trend = 'down' if reverse_trend else 'up'
        else:
            trend = 'up' if reverse_trend else 'down'
        
        return PerformanceInsight(
            metric=metric,
            current_value=current,
            previous_value=previous,
            change_percentage=change_percentage,
            trend=trend,
            recommendation=recommendation
        )
    
    def _generate_recommendations(
        self, 
        current_metrics: Dict[str, float],
        trends: Dict[str, float]
    ) -> List[str]:
        """Generate actionable recommendations based on metrics"""
        recommendations = []
        
        # Delivery rate recommendations
        delivery_rate = current_metrics.get('delivery_rate', 0)
        if delivery_rate < 95:
            recommendations.append(
                "Delivery rate is below 95%. Consider cleaning your contact list and "
                "reviewing sender authentication settings."
            )
        
        # Open rate recommendations
        open_rate = current_metrics.get('open_rate', 0)
        if open_rate < 20:
            recommendations.append(
                "Open rate is below 20%. Test different subject lines and send times "
                "to improve engagement."
            )
        elif open_rate > 40:
            recommendations.append(
                "Excellent open rate! Consider scaling successful campaigns and "
                "analyzing top-performing content."
            )
        
        # Response rate recommendations
        response_rate = current_metrics.get('response_rate', 0)
        if response_rate < 3:
            recommendations.append(
                "Low response rate. Include clear calls-to-action and make content "
                "more engaging and personalized."
            )
        
        # Trend-based recommendations
        if trends.get('delivery_rate_change', 0) < -5:
            recommendations.append(
                "Delivery rate is declining. Check sender reputation and list quality."
            )
        
        if trends.get('engagement_score_change', 0) > 10:
            recommendations.append(
                "Engagement is improving significantly. Document successful strategies "
                "for future campaigns."
            )
        
        return recommendations


# Create global instance
communication_analyzer = CommunicationAnalyzer()