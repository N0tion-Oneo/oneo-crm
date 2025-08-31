"""
API ViewSet for Record Attendee Mappings
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import RecordAttendeeMapping
from .serializers import RecordAttendeeMappingSerializer


class RecordAttendeeMappingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing discovered attendee mappings for records.
    These mappings are created during the sync process to track
    which communication attendees are associated with which records.
    """
    
    queryset = RecordAttendeeMapping.objects.all()
    serializer_class = RecordAttendeeMappingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter by record_id if provided"""
        qs = super().get_queryset()
        
        # Filter by record if specified
        if record_id := self.request.query_params.get('record_id'):
            qs = qs.filter(record_id=record_id)
        
        # Filter by channel type if specified
        if channel_type := self.request.query_params.get('channel_type'):
            qs = qs.filter(channel_type=channel_type)
        
        # Order by most recently discovered
        return qs.order_by('-discovered_at')
    
    @extend_schema(
        summary="Get attendee mappings for a specific record",
        parameters=[
            OpenApiParameter(name='record_id', type=int, required=False),
            OpenApiParameter(name='channel_type', type=str, required=False)
        ]
    )
    def list(self, request, *args, **kwargs):
        """List all attendee mappings, optionally filtered by record or channel"""
        return super().list(request, *args, **kwargs)