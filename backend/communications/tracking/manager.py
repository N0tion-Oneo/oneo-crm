"""
Communication Tracking Manager
Centralized manager for tracking communication events and performance
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, List, Tuple
from collections import defaultdict

from django.db import transaction, models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Avg, Sum, F
from django.core.cache import cache

from ..models import Channel, Message, Conversation, MessageDirection, MessageStatus
from .models import (
    CommunicationTracking, DeliveryTracking, ReadTracking, 
    ResponseTracking, CampaignTracking, PerformanceMetrics,
    TrackingType, TrackingStatus
)

User = get_user_model()
logger = logging.getLogger(__name__)


class CommunicationTracker:
    """
    Central manager for communication tracking and analytics
    Handles event tracking, performance monitoring, and reporting
    """
    
    def __init__(self):
        self.cache_timeout = 300  # 5 minutes
        
    # === DELIVERY TRACKING ===
    
    def track_delivery_attempt(
        self, 
        message: Message, 
        attempt_number: int = 1,
        external_tracking_id: str = None,
        provider_response: Dict[str, Any] = None
    ) -> DeliveryTracking:
        """Track a delivery attempt for a message"""
        try:
            delivery_tracking, created = DeliveryTracking.objects.get_or_create(
                message=message,
                defaults={
                    'channel': message.channel,
                    'attempt_count': 0,
                    'first_attempt_at': timezone.now(),
                }
            )
            
            # Update attempt information
            delivery_tracking.attempt_count = attempt_number
            if external_tracking_id:
                delivery_tracking.external_tracking_id = external_tracking_id
            if provider_response:
                delivery_tracking.provider_response = provider_response
                
            delivery_tracking.save()
            
            # Create tracking event
            self._create_tracking_event(
                message=message,
                tracking_type=TrackingType.DELIVERY,
                status=TrackingStatus.PENDING,
                tracking_data={
                    'attempt_number': attempt_number,
                    'external_tracking_id': external_tracking_id,
                    'provider_response': provider_response or {}
                }
            )
            
            # logger.info(f"Tracked delivery attempt {attempt_number} for message {message.id}")
            return delivery_tracking
            
        except Exception as e:
            logger.error(f"Failed to track delivery attempt: {e}")
            raise
    
    def mark_delivery_success(
        self, 
        message: Message, 
        delivered_at: datetime = None,
        delivery_time_ms: int = None
    ) -> DeliveryTracking:
        """Mark a message as successfully delivered"""
        try:
            delivery_tracking = DeliveryTracking.objects.get(message=message)
            delivery_tracking.delivered_at = delivered_at or timezone.now()
            
            if delivery_time_ms:
                delivery_tracking.total_delivery_time_ms = delivery_time_ms
            elif delivery_tracking.first_attempt_at:
                time_diff = delivery_tracking.delivered_at - delivery_tracking.first_attempt_at
                delivery_tracking.total_delivery_time_ms = int(time_diff.total_seconds() * 1000)
            
            delivery_tracking.save()
            
            # Update message status
            message.status = MessageStatus.DELIVERED
            message.save(update_fields=['status'])
            
            # Create tracking event
            self._create_tracking_event(
                message=message,
                tracking_type=TrackingType.DELIVERY,
                status=TrackingStatus.TRACKED,
                tracking_data={
                    'delivered_at': delivery_tracking.delivered_at.isoformat(),
                    'delivery_time_ms': delivery_tracking.total_delivery_time_ms,
                }
            )
            
            logger.info(f"Marked message {message.id} as delivered")
            return delivery_tracking
            
        except DeliveryTracking.DoesNotExist:
            logger.error(f"No delivery tracking found for message {message.id}")
            raise
        except Exception as e:
            logger.error(f"Failed to mark delivery success: {e}")
            raise
    
    def mark_delivery_failure(
        self, 
        message: Message, 
        error_code: str = None,
        error_message: str = None,
        is_permanent: bool = False
    ) -> DeliveryTracking:
        """Mark a message delivery as failed"""
        try:
            delivery_tracking = DeliveryTracking.objects.get(message=message)
            
            # Add error to history
            error_entry = {
                'timestamp': timezone.now().isoformat(),
                'error_code': error_code,
                'error_message': error_message,
                'attempt': delivery_tracking.attempt_count
            }
            delivery_tracking.error_history.append(error_entry)
            
            # Update error fields
            delivery_tracking.last_error_code = error_code or ''
            delivery_tracking.last_error_message = error_message or ''
            
            # Mark as permanently failed if specified or max attempts reached
            if is_permanent or delivery_tracking.attempt_count >= delivery_tracking.max_attempts:
                delivery_tracking.failed_at = timezone.now()
                message.status = MessageStatus.FAILED
                message.save(update_fields=['status'])
            
            delivery_tracking.save()
            
            # Create tracking event
            self._create_tracking_event(
                message=message,
                tracking_type=TrackingType.BOUNCE,
                status=TrackingStatus.TRACKED,
                tracking_data={
                    'error_code': error_code,
                    'error_message': error_message,
                    'is_permanent': is_permanent,
                    'attempt_count': delivery_tracking.attempt_count
                }
            )
            
            logger.warning(f"Marked message {message.id} delivery as failed: {error_message}")
            return delivery_tracking
            
        except DeliveryTracking.DoesNotExist:
            logger.error(f"No delivery tracking found for message {message.id}")
            raise
        except Exception as e:
            logger.error(f"Failed to mark delivery failure: {e}")
            raise
    
    # === READ TRACKING ===
    
    def track_message_read(
        self, 
        message: Message, 
        read_at: datetime = None,
        user_agent: str = None,
        ip_address: str = None,
        device_info: Dict[str, Any] = None,
        location_info: Dict[str, Any] = None
    ) -> ReadTracking:
        """Track when a message is read"""
        try:
            read_tracking, created = ReadTracking.objects.get_or_create(
                message=message,
                defaults={
                    'channel': message.channel,
                    'first_read_at': read_at or timezone.now(),
                    'read_count': 0,
                }
            )
            
            read_time = read_at or timezone.now()
            
            # Update read tracking
            if created:
                read_tracking.first_read_at = read_time
                # Calculate time to first read
                if message.sent_at:
                    time_diff = read_time - message.sent_at
                    read_tracking.time_to_first_read_minutes = int(time_diff.total_seconds() / 60)
            
            read_tracking.last_read_at = read_time
            read_tracking.read_count += 1
            read_tracking.tracking_pixel_loaded = True
            
            # Add device info
            if device_info:
                read_tracking.read_devices.append({
                    'timestamp': read_time.isoformat(),
                    'user_agent': user_agent,
                    **device_info
                })
            
            # Add location info
            if location_info:
                read_tracking.read_locations.append({
                    'timestamp': read_time.isoformat(),
                    'ip_address': ip_address,
                    **location_info
                })
            
            read_tracking.save()
            
            # Update message status
            if message.status == MessageStatus.DELIVERED:
                message.status = MessageStatus.READ
                message.save(update_fields=['status'])
            
            # Create tracking event
            self._create_tracking_event(
                message=message,
                tracking_type=TrackingType.READ,
                status=TrackingStatus.TRACKED,
                user_agent=user_agent or '',
                ip_address=ip_address,
                tracking_data={
                    'read_count': read_tracking.read_count,
                    'time_to_read_minutes': read_tracking.time_to_first_read_minutes,
                    'device_info': device_info or {},
                    'location_info': location_info or {}
                }
            )
            
            # logger.info(f"Tracked read for message {message.id} (read #{read_tracking.read_count})")
            return read_tracking
            
        except Exception as e:
            logger.error(f"Failed to track message read: {e}")
            raise
    
    # === RESPONSE TRACKING ===
    
    def track_response(
        self, 
        original_message: Message, 
        response_message: Message,
        response_analysis: Dict[str, Any] = None
    ) -> ResponseTracking:
        """Track a response to an outbound message"""
        try:
            # Calculate response time
            if original_message.sent_at and response_message.received_at:
                time_diff = response_message.received_at - original_message.sent_at
                response_time_minutes = int(time_diff.total_seconds() / 60)
            else:
                response_time_minutes = 0
            
            # Create response tracking
            response_tracking = ResponseTracking.objects.create(
                original_message=original_message,
                response_message=response_message,
                conversation=response_message.conversation or original_message.conversation,
                response_time_minutes=response_time_minutes,
                response_received_at=response_message.received_at or response_message.created_at,
                response_length=len(response_message.content),
                contains_question='?' in response_message.content,
                response_analysis=response_analysis or {}
            )
            
            # Basic sentiment analysis (simple keyword-based)
            response_tracking.response_sentiment = self._analyze_sentiment(response_message.content)
            response_tracking.save()
            
            # Create tracking event
            self._create_tracking_event(
                message=response_message,
                tracking_type=TrackingType.RESPONSE,
                status=TrackingStatus.TRACKED,
                tracking_data={
                    'original_message_id': str(original_message.id),
                    'response_time_minutes': response_time_minutes,
                    'response_length': response_tracking.response_length,
                    'sentiment': response_tracking.response_sentiment,
                }
            )
            
            # logger.info(f"Tracked response to message {original_message.id} in {response_time_minutes}min")
            return response_tracking
            
        except Exception as e:
            logger.error(f"Failed to track response: {e}")
            raise
    
    # === CAMPAIGN TRACKING ===
    
    def create_campaign(
        self, 
        name: str, 
        campaign_type: str,
        channels: List[Channel],
        created_by: User,
        description: str = '',
        target_audience: Dict[str, Any] = None,
        **kwargs
    ) -> CampaignTracking:
        """Create a new communication campaign"""
        try:
            campaign = CampaignTracking.objects.create(
                name=name,
                description=description,
                campaign_type=campaign_type,
                target_audience=target_audience or {},
                created_by=created_by,
                **kwargs
            )
            
            # Add channels
            campaign.channels.set(channels)
            
            logger.info(f"Created campaign: {name}")
            return campaign
            
        except Exception as e:
            logger.error(f"Failed to create campaign: {e}")
            raise
    
    def start_campaign(self, campaign: CampaignTracking) -> None:
        """Start a campaign"""
        try:
            campaign.status = 'active'
            campaign.actual_start = timezone.now()
            campaign.save()
            
            logger.info(f"Started campaign: {campaign.name}")
            
        except Exception as e:
            logger.error(f"Failed to start campaign: {e}")
            raise
    
    # === ANALYTICS AND REPORTING ===
    
    @transaction.atomic
    def update_performance_metrics(
        self, 
        date: datetime.date = None, 
        hour: int = None,
        channel: Channel = None,
        campaign: CampaignTracking = None
    ) -> PerformanceMetrics:
        """Update aggregated performance metrics"""
        try:
            target_date = date or timezone.now().date()
            
            # Build base query filters
            message_filters = Q(created_at__date=target_date)
            if hour is not None:
                message_filters &= Q(created_at__hour=hour)
            if channel:
                message_filters &= Q(channel=channel)
            
            # Get or create metrics record
            metrics, created = PerformanceMetrics.objects.get_or_create(
                date=target_date,
                hour=hour,
                channel=channel,
                campaign=campaign,
                defaults={
                    'messages_sent': 0,
                    'messages_delivered': 0,
                    'messages_failed': 0,
                    'messages_read': 0,
                    'responses_received': 0,
                }
            )
            
            # Calculate volume metrics
            messages = Message.objects.filter(message_filters)
            metrics.messages_sent = messages.filter(direction=MessageDirection.OUTBOUND).count()
            
            # Delivery metrics
            delivered_messages = messages.filter(status=MessageStatus.DELIVERED)
            metrics.messages_delivered = delivered_messages.count()
            metrics.messages_failed = messages.filter(status=MessageStatus.FAILED).count()
            
            # Read metrics
            read_messages = messages.filter(status=MessageStatus.READ)
            metrics.messages_read = read_messages.count()
            
            # Response metrics
            response_filters = Q(response_received_at__date=target_date)
            if hour is not None:
                response_filters &= Q(response_received_at__hour=hour)
            metrics.responses_received = ResponseTracking.objects.filter(response_filters).count()
            
            # Calculate rates
            if metrics.messages_sent > 0:
                metrics.delivery_rate = Decimal(metrics.messages_delivered) / Decimal(metrics.messages_sent) * 100
                metrics.open_rate = Decimal(metrics.messages_read) / Decimal(metrics.messages_sent) * 100
                metrics.response_rate = Decimal(metrics.responses_received) / Decimal(metrics.messages_sent) * 100
                metrics.bounce_rate = Decimal(metrics.messages_failed) / Decimal(metrics.messages_sent) * 100
            
            # Calculate average response time
            response_times = ResponseTracking.objects.filter(response_filters).aggregate(
                avg_response_time=Avg('response_time_minutes')
            )
            if response_times['avg_response_time']:
                metrics.avg_response_time_minutes = Decimal(str(response_times['avg_response_time']))
            
            # Sentiment analysis
            sentiment_counts = ResponseTracking.objects.filter(response_filters).values(
                'response_sentiment'
            ).annotate(count=Count('id'))
            
            for sentiment_data in sentiment_counts:
                sentiment = sentiment_data['response_sentiment']
                count = sentiment_data['count']
                
                if sentiment == 'positive':
                    metrics.sentiment_positive_count = count
                elif sentiment == 'neutral':
                    metrics.sentiment_neutral_count = count
                elif sentiment == 'negative':
                    metrics.sentiment_negative_count = count
            
            metrics.save()
            
            # Clear related cache
            self._clear_metrics_cache(channel, campaign, target_date)
            
            logger.info(f"Updated performance metrics for {target_date} - {channel or 'all channels'}")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to update performance metrics: {e}")
            raise
    
    def get_channel_performance(
        self, 
        channel: Channel, 
        days: int = 30
    ) -> Dict[str, Any]:
        """Get performance summary for a channel"""
        cache_key = f"channel_performance_{channel.id}_{days}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Get aggregated metrics
            metrics = PerformanceMetrics.objects.filter(
                channel=channel,
                date__range=[start_date, end_date],
                hour__isnull=True  # Daily metrics only
            ).aggregate(
                total_sent=Sum('messages_sent'),
                total_delivered=Sum('messages_delivered'),
                total_read=Sum('messages_read'),
                total_responses=Sum('responses_received'),
                avg_delivery_rate=Avg('delivery_rate'),
                avg_open_rate=Avg('open_rate'),
                avg_response_rate=Avg('response_rate'),
                avg_response_time=Avg('avg_response_time_minutes')
            )
            
            # Calculate performance summary
            performance = {
                'channel_id': str(channel.id),
                'channel_name': channel.name,
                'channel_type': channel.channel_type,
                'period_days': days,
                'total_messages_sent': metrics['total_sent'] or 0,
                'total_messages_delivered': metrics['total_delivered'] or 0,
                'total_messages_read': metrics['total_read'] or 0,
                'total_responses_received': metrics['total_responses'] or 0,
                'delivery_rate': float(metrics['avg_delivery_rate'] or 0),
                'open_rate': float(metrics['avg_open_rate'] or 0),
                'response_rate': float(metrics['avg_response_rate'] or 0),
                'avg_response_time_minutes': float(metrics['avg_response_time'] or 0),
                'engagement_score': 0.0,
            }
            
            # Calculate engagement score
            if performance['total_messages_sent'] > 0:
                performance['engagement_score'] = (
                    (performance['delivery_rate'] * 0.3) +
                    (performance['open_rate'] * 0.4) +
                    (performance['response_rate'] * 0.3)
                )
            
            cache.set(cache_key, performance, self.cache_timeout)
            return performance
            
        except Exception as e:
            logger.error(f"Failed to get channel performance: {e}")
            return {}
    
    def get_campaign_performance(self, campaign: CampaignTracking) -> Dict[str, Any]:
        """Get performance summary for a campaign"""
        cache_key = f"campaign_performance_{campaign.id}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Get campaign date range
            if not campaign.actual_start:
                return {'error': 'Campaign has not started yet'}
            
            start_date = campaign.actual_start.date()
            end_date = campaign.actual_end.date() if campaign.actual_end else timezone.now().date()
            
            # Get aggregated metrics
            metrics = PerformanceMetrics.objects.filter(
                campaign=campaign,
                date__range=[start_date, end_date]
            ).aggregate(
                total_sent=Sum('messages_sent'),
                total_delivered=Sum('messages_delivered'),
                total_read=Sum('messages_read'),
                total_responses=Sum('responses_received'),
                avg_delivery_rate=Avg('delivery_rate'),
                avg_open_rate=Avg('open_rate'),
                avg_response_rate=Avg('response_rate')
            )
            
            performance = {
                'campaign_id': str(campaign.id),
                'campaign_name': campaign.name,
                'campaign_type': campaign.campaign_type,
                'status': campaign.status,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat() if campaign.actual_end else None,
                'duration_days': campaign.duration_days,
                'total_messages_sent': metrics['total_sent'] or 0,
                'total_messages_delivered': metrics['total_delivered'] or 0,
                'total_messages_read': metrics['total_read'] or 0,
                'total_responses_received': metrics['total_responses'] or 0,
                'delivery_rate': float(metrics['avg_delivery_rate'] or 0),
                'open_rate': float(metrics['avg_open_rate'] or 0),
                'response_rate': float(metrics['avg_response_rate'] or 0),
                'target_delivery_rate': float(campaign.target_delivery_rate),
                'target_open_rate': float(campaign.target_open_rate),
                'target_response_rate': float(campaign.target_response_rate),
            }
            
            # Performance vs targets
            performance['delivery_vs_target'] = performance['delivery_rate'] - performance['target_delivery_rate']
            performance['open_vs_target'] = performance['open_rate'] - performance['target_open_rate']
            performance['response_vs_target'] = performance['response_rate'] - performance['target_response_rate']
            
            cache.set(cache_key, performance, self.cache_timeout)
            return performance
            
        except Exception as e:
            logger.error(f"Failed to get campaign performance: {e}")
            return {}
    
    # === HELPER METHODS ===
    
    def _create_tracking_event(
        self, 
        message: Message, 
        tracking_type: str,
        status: str = TrackingStatus.TRACKED,
        user_agent: str = '',
        ip_address: str = None,
        tracking_data: Dict[str, Any] = None,
        response_time_ms: int = None
    ) -> CommunicationTracking:
        """Create a tracking event record"""
        return CommunicationTracking.objects.create(
            message=message,
            channel=message.channel,
            conversation=message.conversation,
            tracking_type=tracking_type,
            status=status,
            user_agent=user_agent,
            ip_address=ip_address,
            tracking_data=tracking_data or {},
            response_time_ms=response_time_ms
        )
    
    def _analyze_sentiment(self, content: str) -> str:
        """Basic sentiment analysis using keyword matching"""
        content_lower = content.lower()
        
        positive_keywords = ['thank', 'great', 'excellent', 'good', 'amazing', 'love', 'perfect']
        negative_keywords = ['bad', 'terrible', 'awful', 'hate', 'problem', 'issue', 'wrong']
        
        positive_count = sum(1 for word in positive_keywords if word in content_lower)
        negative_count = sum(1 for word in negative_keywords if word in content_lower)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _clear_metrics_cache(
        self, 
        channel: Channel = None, 
        campaign: CampaignTracking = None,
        date: datetime.date = None
    ) -> None:
        """Clear related performance metrics cache"""
        if channel:
            # Clear channel performance cache for different day ranges
            for days in [7, 30, 90]:
                cache.delete(f"channel_performance_{channel.id}_{days}")
        
        if campaign:
            cache.delete(f"campaign_performance_{campaign.id}")


# Create global instance
communication_tracker = CommunicationTracker()