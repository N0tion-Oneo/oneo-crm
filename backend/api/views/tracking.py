"""
Communication tracking API views - imported from communications.tracking app
"""
from communications.tracking.views import (
    # Core tracking ViewSets
    CommunicationTrackingViewSet,
    DeliveryTrackingViewSet,
    ReadTrackingViewSet,
    ResponseTrackingViewSet,
    CampaignTrackingViewSet,
    PerformanceMetricsViewSet,
    
    # Analytics Views
    PerformanceTrendsView,
    ChannelComparisonView,
    TimingAnalysisView,
    AudienceEngagementView,
    PerformanceReportView,
    
    # Tracking & Webhook Views
    TrackingPixelView,
    DeliveryWebhookView,
    UniPileWebhookView,
    
    # Dashboard Views
    ChannelDashboardView,
    CampaignDashboardView,
    OverviewDashboardView
)

# Re-export for API registration
__all__ = [
    # Core tracking ViewSets
    'CommunicationTrackingViewSet',
    'DeliveryTrackingViewSet',
    'ReadTrackingViewSet',
    'ResponseTrackingViewSet',
    'CampaignTrackingViewSet',
    'PerformanceMetricsViewSet',
    
    # Analytics Views
    'PerformanceTrendsView',
    'ChannelComparisonView',
    'TimingAnalysisView',
    'AudienceEngagementView',
    'PerformanceReportView',
    
    # Tracking & Webhook Views
    'TrackingPixelView',
    'DeliveryWebhookView',
    'UniPileWebhookView',
    
    # Dashboard Views
    'ChannelDashboardView',
    'CampaignDashboardView',
    'OverviewDashboardView'
]