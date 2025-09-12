"""
URLs for custom calendar events
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomCalendarEventViewSet

router = DefaultRouter()
router.register(r'events', CustomCalendarEventViewSet, basename='calendar-events')

urlpatterns = [
    path('', include(router.urls)),
]