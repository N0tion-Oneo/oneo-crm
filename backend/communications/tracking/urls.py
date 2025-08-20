"""
URL patterns for communication tracking system
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# Create router for API endpoints
router = DefaultRouter()
router.register(r'tracking', views.CommunicationTrackingViewSet)
router.register(r'delivery', views.DeliveryTrackingViewSet)
router.register(r'reads', views.ReadTrackingViewSet)
router.register(r'responses', views.ResponseTrackingViewSet)
router.register(r'campaigns', views.CampaignTrackingViewSet)
router.register(r'metrics', views.PerformanceMetricsViewSet)

app_name = 'communication_tracking'

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Analytics endpoints
    path('api/analytics/trends/', views.PerformanceTrendsView.as_view(), name='performance-trends'),
    path('api/analytics/channel-comparison/', views.ChannelComparisonView.as_view(), name='channel-comparison'),
    path('api/analytics/timing-analysis/', views.TimingAnalysisView.as_view(), name='timing-analysis'),
    path('api/analytics/audience-engagement/', views.AudienceEngagementView.as_view(), name='audience-engagement'),
    path('api/analytics/performance-report/', views.PerformanceReportView.as_view(), name='performance-report'),
    
    # Real-time tracking endpoints
    path('pixel/<uuid:message_id>/', views.TrackingPixelView.as_view(), name='tracking-pixel'),
    path('webhook/delivery/', views.DeliveryWebhookView.as_view(), name='delivery-webhook'),
    # Note: UniPile webhook consolidated into main /webhooks/unipile/ endpoint with tracking handler
    
    # Dashboard endpoints
    path('dashboard/channel/<uuid:channel_id>/', views.ChannelDashboardView.as_view(), name='channel-dashboard'),
    path('dashboard/campaign/<uuid:campaign_id>/', views.CampaignDashboardView.as_view(), name='campaign-dashboard'),
    path('dashboard/overview/', views.OverviewDashboardView.as_view(), name='overview-dashboard'),
]