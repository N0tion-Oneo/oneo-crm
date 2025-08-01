"""
Custom pagination classes for the API
"""
from rest_framework.pagination import PageNumberPagination, CursorPagination as DRFCursorPagination
from rest_framework.response import Response
from collections import OrderedDict
import base64
import json


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination with detailed metadata"""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000
    
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('pages', self.page.paginator.num_pages),
            ('page_size', self.get_page_size(self.request)),
            ('current_page', self.page.number),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))


class CursorPagination(DRFCursorPagination):
    """Cursor-based pagination for real-time data"""
    page_size = 50
    page_size_query_param = 'page_size'
    cursor_query_param = 'cursor'
    ordering = '-created_at'
    
    def paginate_queryset(self, queryset, request, view=None):
        cursor = request.GET.get(self.cursor_query_param)
        if cursor:
            # Decode cursor and filter queryset
            try:
                cursor_data = json.loads(base64.b64decode(cursor).decode())
                if 'created_at' in cursor_data:
                    queryset = queryset.filter(created_at__lt=cursor_data['created_at'])
            except:
                pass  # Invalid cursor, ignore
        
        return super().paginate_queryset(queryset, request, view)


class OptimizedPagination(PageNumberPagination):
    """Optimized pagination for large datasets"""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 500
    
    def get_paginated_response(self, data):
        # Simplified response for performance
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })