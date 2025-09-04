"""
Media file serving for multi-tenant architecture
"""
from django.http import HttpResponse, Http404
from django.conf import settings
from django.views.static import serve
from django.views.decorators.cache import cache_control
import os


@cache_control(max_age=86400)  # Cache for 1 day
def serve_media(request, path):
    """
    Serve media files in development for multi-tenant setup
    This handles both public and tenant-specific media files
    """
    # Construct the full file path
    media_root = settings.MEDIA_ROOT
    file_path = os.path.join(media_root, path)
    
    # Security check - ensure the path doesn't escape media root
    if not os.path.abspath(file_path).startswith(os.path.abspath(media_root)):
        raise Http404("Invalid file path")
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise Http404("File not found")
    
    # Serve the file
    return serve(request, path, document_root=media_root)