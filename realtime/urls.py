"""
URL routing for real-time features
"""
from django.urls import path, include
from . import sse_views

app_name = 'realtime'

urlpatterns = [
    # Server-Sent Events endpoints
    path('sse/notifications/', sse_views.notifications_stream, name='notifications_stream'),
    path('sse/activity/', sse_views.activity_stream, name='activity_stream'),
    path('sse/dashboard/<str:dashboard_id>/', sse_views.dashboard_stream, name='dashboard_stream'),
    path('sse/pipeline/<str:pipeline_id>/', sse_views.pipeline_stream, name='pipeline_stream'),
]