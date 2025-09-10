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
    AvailabilityOverrideViewSet
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

# Internal API router
router = DefaultRouter()
router.register(r'profiles', SchedulingProfileViewSet, basename='scheduling-profile')
router.register(r'meeting-types', MeetingTypeViewSet, basename='meeting-type')
router.register(r'links', SchedulingLinkViewSet, basename='scheduling-link')
router.register(r'meetings', ScheduledMeetingViewSet, basename='scheduled-meeting')
router.register(r'overrides', AvailabilityOverrideViewSet, basename='availability-override')

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
]