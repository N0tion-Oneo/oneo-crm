"""
URL patterns for Phase 8 Communication System with Tracking
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'channels', views.ChannelViewSet)
router.register(r'conversations', views.ConversationViewSet)
router.register(r'messages', views.MessageViewSet)
# Sequence management has been moved to the workflows app
# router.register(r'sequences', views.SequenceViewSet) - REMOVED
# router.register(r'enrollments', views.SequenceEnrollmentViewSet) - REMOVED
router.register(r'analytics', views.CommunicationAnalyticsViewSet)

app_name = 'communications'

urlpatterns = [
    # Core API endpoints
    path('api/', include(router.urls)),
    
    # Communication tracking system
    path('tracking/', include('communications.tracking.urls')),
]