"""
URL configuration for scheduling endpoints
Includes both internal (authenticated) and public endpoints
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    SchedulingProfileViewSet,
    MeetingTypeViewSet,
    SchedulingLinkViewSet,
    ScheduledMeetingViewSet,
    AvailabilityOverrideViewSet,
    FacilitatorBookingViewSet
)
from .public_views import (
    PublicSchedulingLinkView,
    PublicAvailabilityView,
    PublicBookingView,
    PublicMeetingStatusView,
    PublicMeetingCancelView,
    PublicMeetingRescheduleView,
    PublicMeetingTypeView,
    PublicMeetingTypeFormView,
    PublicMeetingTypeAvailabilityView,
    PublicMeetingTypeBookingView
)
from .facilitator_views import (
    FacilitatorInitiateView,
    FacilitatorParticipant1View,
    FacilitatorBookingConfigView,
    FacilitatorBookingAvailabilityView,
    FacilitatorBookingStep1View,
    FacilitatorBookingDetailView,
    FacilitatorBookingStep2View
)

# Internal API router
router = DefaultRouter()
router.register(r'profiles', SchedulingProfileViewSet, basename='scheduling-profile')
router.register(r'meeting-types', MeetingTypeViewSet, basename='meeting-type')
router.register(r'links', SchedulingLinkViewSet, basename='scheduling-link')
router.register(r'meetings', ScheduledMeetingViewSet, basename='scheduled-meeting')
router.register(r'overrides', AvailabilityOverrideViewSet, basename='availability-override')
router.register(r'facilitator-bookings', FacilitatorBookingViewSet, basename='facilitator-booking')

# URL patterns
urlpatterns = [
    # Internal authenticated APIs
    path('', include(router.urls)),
    
    # Public booking APIs with clean URLs (no authentication required)
    path('public/book/<str:username>/<str:slug>/', PublicMeetingTypeView.as_view(), name='public-meeting-type'),
    path('public/book/<str:username>/<str:slug>/form/', PublicMeetingTypeFormView.as_view(), name='public-meeting-type-form'),
    path('public/book/<str:username>/<str:slug>/availability/', PublicMeetingTypeAvailabilityView.as_view(), name='public-meeting-type-availability'),
    path('public/book/<str:username>/<str:slug>/book/', PublicMeetingTypeBookingView.as_view(), name='public-meeting-type-booking'),
    
    # Legacy public booking APIs for SchedulingLink (backward compatibility)
    path('public/links/<str:slug>/', PublicSchedulingLinkView.as_view(), name='public-scheduling-link'),
    path('public/links/<str:slug>/availability/', PublicAvailabilityView.as_view(), name='public-availability'),
    path('public/links/<str:slug>/book/', PublicBookingView.as_view(), name='public-booking'),
    
    # Public meeting management
    path('public/meetings/<uuid:meeting_id>/status/', PublicMeetingStatusView.as_view(), name='public-meeting-status'),
    path('public/meetings/<uuid:meeting_id>/cancel/', PublicMeetingCancelView.as_view(), name='public-meeting-cancel'),
    path('public/meetings/<uuid:meeting_id>/reschedule/', PublicMeetingRescheduleView.as_view(), name='public-meeting-reschedule'),
    
    # Facilitator booking endpoints - NEW flow
    path('facilitator/initiate/', FacilitatorInitiateView.as_view(), name='facilitator-initiate'),  # Dashboard endpoint
    path('public/facilitator/<uuid:token>/participant1/', FacilitatorParticipant1View.as_view(), name='facilitator-p1'),  # P1 config
    path('public/facilitator/<uuid:token>/', FacilitatorBookingDetailView.as_view(), name='facilitator-detail'),  # P2 view (keep existing)
    path('public/facilitator/<uuid:token>/confirm/', FacilitatorBookingStep2View.as_view(), name='facilitator-step2'),  # P2 confirm (keep existing)
    
    # Legacy facilitator endpoints (to be deprecated)
    path('public/facilitator/<str:username>/<str:slug>/config/', FacilitatorBookingConfigView.as_view(), name='facilitator-config'),
    path('public/facilitator/<str:username>/<str:slug>/availability/', FacilitatorBookingAvailabilityView.as_view(), name='facilitator-availability'),
    path('public/facilitator/<str:username>/<str:slug>/step1/', FacilitatorBookingStep1View.as_view(), name='facilitator-step1'),
]