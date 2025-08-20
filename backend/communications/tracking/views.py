"""
API views for communication tracking system
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from api.permissions import CommunicationTrackingPermission
from rest_framework.pagination import PageNumberPagination

from ..models import Channel, Message
from .models import (
    CommunicationTracking, DeliveryTracking, ReadTracking,
    ResponseTracking, CampaignTracking, PerformanceMetrics
)
from .serializers import (
    CommunicationTrackingSerializer, DeliveryTrackingSerializer, 
    ReadTrackingSerializer, ResponseTrackingSerializer,
    CampaignTrackingSerializer, PerformanceMetricsSerializer
)
from .manager import communication_tracker
from .analytics import communication_analyzer
from communications.signals.tracking import handle_unipile_delivery_webhook, handle_tracking_pixel_request

logger = logging.getLogger(__name__)


class StandardPagination(PageNumberPagination):
    """Standard pagination for tracking APIs"""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


# === API VIEWSETS ===

class CommunicationTrackingViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for communication tracking events"""
    
    queryset = CommunicationTracking.objects.all().select_related(
        'message', 'channel', 'conversation'
    ).order_by('-event_timestamp')
    serializer_class = CommunicationTrackingSerializer
    permission_classes = [CommunicationTrackingPermission]
    pagination_class = StandardPagination
    
    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = super().get_queryset()
        
        # Filter by channel
        channel_id = self.request.query_params.get('channel')
        if channel_id:
            queryset = queryset.filter(channel_id=channel_id)
        
        # Filter by tracking type
        tracking_type = self.request.query_params.get('type')
        if tracking_type:
            queryset = queryset.filter(tracking_type=tracking_type)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
                queryset = queryset.filter(event_timestamp__gte=start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                queryset = queryset.filter(event_timestamp__lte=end_dt)
            except ValueError:
                pass
        
        return queryset


class DeliveryTrackingViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for delivery tracking"""
    
    queryset = DeliveryTracking.objects.all().select_related(
        'message', 'channel'
    ).order_by('-created_at')
    serializer_class = DeliveryTrackingSerializer
    permission_classes = [CommunicationTrackingPermission]
    pagination_class = StandardPagination
    
    def get_queryset(self):
        """Filter delivery tracking queryset"""
        queryset = super().get_queryset()
        
        # Filter by delivery status
        status_filter = self.request.query_params.get('status')
        if status_filter == 'delivered':
            queryset = queryset.filter(delivered_at__isnull=False)
        elif status_filter == 'failed':
            queryset = queryset.filter(failed_at__isnull=False)
        elif status_filter == 'pending':
            queryset = queryset.filter(delivered_at__isnull=True, failed_at__isnull=True)
        
        # Filter by channel
        channel_id = self.request.query_params.get('channel')
        if channel_id:
            queryset = queryset.filter(channel_id=channel_id)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get delivery tracking summary"""
        queryset = self.get_queryset()
        
        summary = {
            'total_messages': queryset.count(),
            'delivered': queryset.filter(delivered_at__isnull=False).count(),
            'failed': queryset.filter(failed_at__isnull=False).count(),
            'pending': queryset.filter(delivered_at__isnull=True, failed_at__isnull=True).count(),
            'avg_delivery_time_ms': queryset.filter(
                total_delivery_time_ms__isnull=False
            ).aggregate(
                avg_time=models.Avg('total_delivery_time_ms')
            )['avg_time']
        }
        
        return Response(summary)


class ReadTrackingViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for read tracking"""
    
    queryset = ReadTracking.objects.all().select_related(
        'message', 'channel'
    ).order_by('-first_read_at')
    serializer_class = ReadTrackingSerializer
    permission_classes = [CommunicationTrackingPermission]
    pagination_class = StandardPagination
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get read tracking summary"""
        queryset = self.get_queryset()
        
        summary = {
            'total_messages': queryset.count(),
            'read_messages': queryset.filter(first_read_at__isnull=False).count(),
            'avg_time_to_read_minutes': queryset.filter(
                time_to_first_read_minutes__isnull=False
            ).aggregate(
                avg_time=models.Avg('time_to_first_read_minutes')
            )['avg_time'],
            'avg_read_count': queryset.aggregate(
                avg_count=models.Avg('read_count')
            )['avg_count']
        }
        
        # Calculate read rate
        if summary['total_messages'] > 0:
            summary['read_rate'] = (summary['read_messages'] / summary['total_messages']) * 100
        else:
            summary['read_rate'] = 0
        
        return Response(summary)


class ResponseTrackingViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for response tracking"""
    
    queryset = ResponseTracking.objects.all().select_related(
        'original_message', 'response_message', 'conversation'
    ).order_by('-response_received_at')
    serializer_class = ResponseTrackingSerializer
    permission_classes = [CommunicationTrackingPermission]
    pagination_class = StandardPagination
    
    @action(detail=False, methods=['get'])
    def sentiment_analysis(self, request):
        """Get sentiment analysis summary"""
        queryset = self.get_queryset()
        
        sentiment_counts = queryset.values('response_sentiment').annotate(
            count=models.Count('id')
        ).order_by('response_sentiment')
        
        total_responses = queryset.count()
        
        analysis = {
            'total_responses': total_responses,
            'sentiment_breakdown': {}
        }
        
        for sentiment_data in sentiment_counts:
            sentiment = sentiment_data['response_sentiment']
            count = sentiment_data['count']
            percentage = (count / total_responses * 100) if total_responses > 0 else 0
            
            analysis['sentiment_breakdown'][sentiment] = {
                'count': count,
                'percentage': round(percentage, 2)
            }
        
        return Response(analysis)


class CampaignTrackingViewSet(viewsets.ModelViewSet):
    """ViewSet for campaign tracking"""
    
    queryset = CampaignTracking.objects.all().prefetch_related('channels').order_by('-created_at')
    serializer_class = CampaignTrackingSerializer
    permission_classes = [CommunicationTrackingPermission]
    pagination_class = StandardPagination
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a campaign"""
        campaign = self.get_object()
        
        try:
            communication_tracker.start_campaign(campaign)
            return Response({'status': 'Campaign started successfully'})
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        """Get campaign performance metrics"""
        campaign = self.get_object()
        
        try:
            performance = communication_tracker.get_campaign_performance(campaign)
            return Response(performance)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PerformanceMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for performance metrics"""
    
    queryset = PerformanceMetrics.objects.all().select_related(
        'channel', 'campaign'
    ).order_by('-date', '-hour')
    serializer_class = PerformanceMetricsSerializer
    permission_classes = [CommunicationTrackingPermission]
    pagination_class = StandardPagination
    
    def get_queryset(self):
        """Filter metrics queryset"""
        queryset = super().get_queryset()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__gte=start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__lte=end_dt)
            except ValueError:
                pass
        
        # Filter by channel
        channel_id = self.request.query_params.get('channel')
        if channel_id:
            queryset = queryset.filter(channel_id=channel_id)
        
        # Filter by campaign
        campaign_id = self.request.query_params.get('campaign')
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)
        
        # Filter by granularity (daily vs hourly)
        granularity = self.request.query_params.get('granularity', 'daily')
        if granularity == 'daily':
            queryset = queryset.filter(hour__isnull=True)
        elif granularity == 'hourly':
            queryset = queryset.filter(hour__isnull=False)
        
        return queryset


# === ANALYTICS VIEWS ===

class PerformanceTrendsView(APIView):
    """API view for performance trend analysis"""
    
    permission_classes = [CommunicationTrackingPermission]
    
    def get(self, request):
        """Get performance trends analysis"""
        channel_id = request.query_params.get('channel')
        days = int(request.query_params.get('days', 30))
        
        channel = None
        if channel_id:
            try:
                channel = Channel.objects.get(id=channel_id)
            except Channel.DoesNotExist:
                return Response(
                    {'error': 'Channel not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        try:
            trends = communication_analyzer.analyze_performance_trends(
                channel=channel,
                days=days
            )
            return Response(trends)
        except Exception as e:
            logger.error(f"Failed to analyze performance trends: {e}")
            return Response(
                {'error': 'Failed to analyze trends'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChannelComparisonView(APIView):
    """API view for channel performance comparison"""
    
    permission_classes = [CommunicationTrackingPermission]
    
    def get(self, request):
        """Get channel performance comparison"""
        days = int(request.query_params.get('days', 30))
        
        try:
            comparison = communication_analyzer.generate_channel_comparison(days=days)
            return Response({
                'comparison': [
                    {
                        'channel_name': c.channel_name,
                        'channel_type': c.channel_type,
                        'delivery_rate': c.delivery_rate,
                        'open_rate': c.open_rate,
                        'response_rate': c.response_rate,
                        'engagement_score': c.engagement_score,
                        'total_messages': c.total_messages,
                        'ranking': c.ranking
                    } for c in comparison
                ]
            })
        except Exception as e:
            logger.error(f"Failed to generate channel comparison: {e}")
            return Response(
                {'error': 'Failed to generate comparison'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TimingAnalysisView(APIView):
    """API view for message timing analysis"""
    
    permission_classes = [CommunicationTrackingPermission]
    
    def get(self, request):
        """Get message timing analysis"""
        channel_id = request.query_params.get('channel')
        days = int(request.query_params.get('days', 30))
        
        channel = None
        if channel_id:
            try:
                channel = Channel.objects.get(id=channel_id)
            except Channel.DoesNotExist:
                return Response(
                    {'error': 'Channel not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        try:
            analysis = communication_analyzer.analyze_message_timing(
                channel=channel,
                days=days
            )
            return Response(analysis)
        except Exception as e:
            logger.error(f"Failed to analyze message timing: {e}")
            return Response(
                {'error': 'Failed to analyze timing'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AudienceEngagementView(APIView):
    """API view for audience engagement analysis"""
    
    permission_classes = [CommunicationTrackingPermission]
    
    def get(self, request):
        """Get audience engagement analysis"""
        channel_id = request.query_params.get('channel')
        days = int(request.query_params.get('days', 30))
        
        channel = None
        if channel_id:
            try:
                channel = Channel.objects.get(id=channel_id)
            except Channel.DoesNotExist:
                return Response(
                    {'error': 'Channel not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        try:
            analysis = communication_analyzer.analyze_audience_engagement(
                channel=channel,
                days=days
            )
            return Response(analysis)
        except Exception as e:
            logger.error(f"Failed to analyze audience engagement: {e}")
            return Response(
                {'error': 'Failed to analyze engagement'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PerformanceReportView(APIView):
    """API view for comprehensive performance reports"""
    
    permission_classes = [CommunicationTrackingPermission]
    
    def get(self, request):
        """Generate performance report"""
        channel_id = request.query_params.get('channel')
        campaign_id = request.query_params.get('campaign')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        channel = None
        campaign = None
        
        if channel_id:
            try:
                channel = Channel.objects.get(id=channel_id)
            except Channel.DoesNotExist:
                return Response(
                    {'error': 'Channel not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        if campaign_id:
            try:
                campaign = CampaignTracking.objects.get(id=campaign_id)
            except CampaignTracking.DoesNotExist:
                return Response(
                    {'error': 'Campaign not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Parse dates
        start_date_obj = None
        end_date_obj = None
        
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid start_date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid end_date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            report = communication_analyzer.generate_performance_report(
                channel=channel,
                campaign=campaign,
                start_date=start_date_obj,
                end_date=end_date_obj
            )
            return Response(report)
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return Response(
                {'error': 'Failed to generate report'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# === TRACKING VIEWS ===

class TrackingPixelView(APIView):
    """View for handling tracking pixel requests"""
    
    def get(self, request, message_id):
        """Handle tracking pixel request"""
        try:
            # Extract request data
            request_data = {
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'ip_address': self._get_client_ip(request),
                'referer': request.META.get('HTTP_REFERER', ''),
                'screen_resolution': request.query_params.get('res'),
                'browser': request.query_params.get('browser'),
                'os': request.query_params.get('os')
            }
            
            # Process tracking pixel
            handle_tracking_pixel_request(str(message_id), request_data)
            
            # Return 1x1 transparent pixel
            pixel_data = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x04\x01\x00\x3b'
            
            response = HttpResponse(pixel_data, content_type='image/gif')
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to handle tracking pixel for {message_id}: {e}")
            # Still return pixel to avoid broken images
            pixel_data = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x04\x01\x00\x3b'
            return HttpResponse(pixel_data, content_type='image/gif')
    
    def _get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@method_decorator(csrf_exempt, name='dispatch')
class DeliveryWebhookView(APIView):
    """View for handling delivery webhooks"""
    
    def post(self, request):
        """Handle delivery webhook"""
        try:
            data = request.data
            message_id = data.get('message_id')
            event_data = data.get('event_data', {})
            
            if not message_id:
                return JsonResponse(
                    {'error': 'message_id is required'},
                    status=400
                )
            
            # Process webhook
            handle_unipile_delivery_webhook(message_id, event_data)
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            logger.error(f"Failed to handle delivery webhook: {e}")
            return JsonResponse(
                {'error': 'Failed to process webhook'},
                status=500
            )


@method_decorator(csrf_exempt, name='dispatch')
class UniPileWebhookView(APIView):
    """View for handling UniPile webhooks"""
    
    def post(self, request):
        """Handle UniPile webhook events"""
        try:
            data = request.data
            events = data.get('events', [])
            
            if not events:
                return JsonResponse(
                    {'error': 'No events provided'},
                    status=400
                )
            
            # Process events asynchronously
            from .tasks import process_webhook_events
            process_webhook_events.delay(events)
            
            return JsonResponse({
                'status': 'success',
                'events_queued': len(events)
            })
            
        except Exception as e:
            logger.error(f"Failed to handle UniPile webhook: {e}")
            return JsonResponse(
                {'error': 'Failed to process webhook'},
                status=500
            )


# === DASHBOARD VIEWS ===

class ChannelDashboardView(APIView):
    """Dashboard view for channel performance"""
    
    permission_classes = [CommunicationTrackingPermission]
    
    def get(self, request, channel_id):
        """Get channel dashboard data"""
        try:
            channel = Channel.objects.get(id=channel_id)
        except Channel.DoesNotExist:
            return Response(
                {'error': 'Channel not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        days = int(request.query_params.get('days', 30))
        
        try:
            # Get channel performance
            performance = communication_tracker.get_channel_performance(channel, days)
            
            # Get recent trends
            trends = communication_analyzer.analyze_performance_trends(channel, days)
            
            # Get timing analysis
            timing = communication_analyzer.analyze_message_timing(channel, days)
            
            dashboard = {
                'channel': {
                    'id': str(channel.id),
                    'name': channel.name,
                    'type': channel.channel_type,
                    'is_active': channel.is_active
                },
                'performance': performance,
                'trends': trends,
                'timing_analysis': timing,
                'period_days': days
            }
            
            return Response(dashboard)
            
        except Exception as e:
            logger.error(f"Failed to generate channel dashboard: {e}")
            return Response(
                {'error': 'Failed to load dashboard'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CampaignDashboardView(APIView):
    """Dashboard view for campaign performance"""
    
    permission_classes = [CommunicationTrackingPermission]
    
    def get(self, request, campaign_id):
        """Get campaign dashboard data"""
        try:
            campaign = CampaignTracking.objects.get(id=campaign_id)
        except CampaignTracking.DoesNotExist:
            return Response(
                {'error': 'Campaign not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # Get campaign performance
            performance = communication_tracker.get_campaign_performance(campaign)
            
            # Get performance report
            report = communication_analyzer.generate_performance_report(campaign=campaign)
            
            dashboard = {
                'campaign': {
                    'id': str(campaign.id),
                    'name': campaign.name,
                    'type': campaign.campaign_type,
                    'status': campaign.status,
                    'start_date': campaign.actual_start.isoformat() if campaign.actual_start else None,
                    'end_date': campaign.actual_end.isoformat() if campaign.actual_end else None
                },
                'performance': performance,
                'report': report
            }
            
            return Response(dashboard)
            
        except Exception as e:
            logger.error(f"Failed to generate campaign dashboard: {e}")
            return Response(
                {'error': 'Failed to load dashboard'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OverviewDashboardView(APIView):
    """Overview dashboard for all communication performance"""
    
    permission_classes = [CommunicationTrackingPermission]
    
    def get(self, request):
        """Get overview dashboard data"""
        days = int(request.query_params.get('days', 30))
        
        try:
            # Get channel comparison
            channel_comparison = communication_analyzer.generate_channel_comparison(days)
            
            # Get overall performance trends
            trends = communication_analyzer.analyze_performance_trends(days=days)
            
            # Get recent metrics summary
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            recent_metrics = PerformanceMetrics.objects.filter(
                date__range=[start_date, end_date],
                hour__isnull=True,
                channel__isnull=True
            ).aggregate(
                total_sent=models.Sum('messages_sent'),
                total_delivered=models.Sum('messages_delivered'),
                total_read=models.Sum('messages_read'),
                total_responses=models.Sum('responses_received'),
                avg_delivery_rate=models.Avg('delivery_rate'),
                avg_open_rate=models.Avg('open_rate'),
                avg_response_rate=models.Avg('response_rate')
            )
            
            dashboard = {
                'period_days': days,
                'summary': {
                    'total_messages_sent': recent_metrics['total_sent'] or 0,
                    'total_messages_delivered': recent_metrics['total_delivered'] or 0,
                    'total_messages_read': recent_metrics['total_read'] or 0,
                    'total_responses': recent_metrics['total_responses'] or 0,
                    'overall_delivery_rate': float(recent_metrics['avg_delivery_rate'] or 0),
                    'overall_open_rate': float(recent_metrics['avg_open_rate'] or 0),
                    'overall_response_rate': float(recent_metrics['avg_response_rate'] or 0)
                },
                'channel_comparison': [
                    {
                        'channel_name': c.channel_name,
                        'channel_type': c.channel_type,
                        'delivery_rate': c.delivery_rate,
                        'open_rate': c.open_rate,
                        'response_rate': c.response_rate,
                        'engagement_score': c.engagement_score,
                        'total_messages': c.total_messages,
                        'ranking': c.ranking
                    } for c in channel_comparison
                ],
                'trends': trends
            }
            
            return Response(dashboard)
            
        except Exception as e:
            logger.error(f"Failed to generate overview dashboard: {e}")
            return Response(
                {'error': 'Failed to load dashboard'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )