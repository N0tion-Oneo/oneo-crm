"""
Realtime API views - imported from realtime app
"""
from realtime.sse_views import (
    notifications_stream,
    activity_stream,
    dashboard_stream,
    pipeline_stream
)

# Re-export for API registration
__all__ = [
    'notifications_stream',
    'activity_stream',
    'dashboard_stream',
    'pipeline_stream'
]