"""
Core middleware for the Oneo CRM system
Includes maintenance mode, tenant context, and security middleware
"""
import logging
from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.models import AnonymousUser
from django.urls import resolve
from django_tenants.middleware import TenantMainMiddleware

logger = logging.getLogger(__name__)


class MaintenanceModeMiddleware:
    """
    Middleware to handle tenant maintenance mode
    Blocks all access to tenants that are in maintenance mode except for superusers
    """
    
    # URLs that should be accessible even during maintenance
    ALLOWED_MAINTENANCE_URLS = [
        'admin:',  # Allow admin access
        'maintenance_status',  # Allow maintenance status checks
        'health_check',  # Allow health checks
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if current tenant is in maintenance mode
        if self._should_block_request(request):
            return self._render_maintenance_page(request)
        
        # Process request normally
        response = self.get_response(request)
        return response
    
    def _should_block_request(self, request):
        """Determine if request should be blocked due to maintenance mode"""
        
        # Skip blocking for static files and media
        if self._is_static_request(request):
            return False
        
        # Skip blocking for allowed URLs
        if self._is_allowed_url(request):
            return False
        
        # Check if tenant exists and has maintenance mode
        if not hasattr(request, 'tenant'):
            return False
        
        # Check if tenant has maintenance record
        if not hasattr(request.tenant, 'maintenance'):
            return False
        
        maintenance = request.tenant.maintenance
        
        # If maintenance mode is not active, allow access
        if not maintenance.is_active:
            return False
        
        # Allow superusers through (check if user exists first)
        if hasattr(request, 'user') and request.user.is_authenticated and request.user.is_superuser:
            logger.info(f"Superuser {request.user.username} accessing tenant {request.tenant.name} during maintenance")
            return False
        
        # Block all other requests
        logger.info(f"Blocking request to {request.path} - tenant {request.tenant.name} in maintenance mode")
        return True
    
    def _is_static_request(self, request):
        """Check if request is for static files or media"""
        path = request.path.lower()
        return (
            path.startswith('/static/') or 
            path.startswith('/media/') or
            path.startswith('/favicon.ico') or
            path.endswith('.css') or
            path.endswith('.js') or
            path.endswith('.png') or
            path.endswith('.jpg') or
            path.endswith('.svg')
        )
    
    def _is_allowed_url(self, request):
        """Check if URL should be allowed during maintenance"""
        try:
            resolved = resolve(request.path)
            url_name = resolved.url_name
            namespace = resolved.namespace
            
            # Check for allowed URL patterns
            for allowed_pattern in self.ALLOWED_MAINTENANCE_URLS:
                if allowed_pattern.endswith(':'):
                    # Namespace check
                    if namespace and namespace.startswith(allowed_pattern[:-1]):
                        return True
                else:
                    # Direct URL name check
                    if url_name == allowed_pattern:
                        return True
            
            return False
            
        except Exception:
            # If URL resolution fails, don't block (safer default)
            return False
    
    def _render_maintenance_page(self, request):
        """Render maintenance mode page"""
        try:
            maintenance = request.tenant.maintenance
            
            context = {
                'tenant_name': request.tenant.name,
                'maintenance': maintenance,
                'progress_percentage': maintenance.progress_percentage,
                'status_message': maintenance.status_message or 'System maintenance in progress...',
                'estimated_completion': maintenance.estimated_completion,
                'started_at': maintenance.started_at,
                'reason': maintenance.reason,
                'is_overdue': maintenance.is_overdue,
            }
            
            # Try to render maintenance template
            try:
                return render(request, 'maintenance/maintenance.html', context, status=503)
            except Exception as template_error:
                logger.error(f"Failed to render maintenance template: {template_error}")
                # Fallback to simple HTML response
                return self._render_simple_maintenance_page(context)
                
        except Exception as e:
            logger.error(f"Error rendering maintenance page: {e}")
            # Fallback to basic maintenance message
            return HttpResponse(
                f"<h1>System Maintenance</h1><p>The system is currently undergoing maintenance. Please try again later.</p>",
                status=503,
                content_type='text/html'
            )
    
    def _render_simple_maintenance_page(self, context):
        """Render a simple maintenance page as fallback"""
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>System Maintenance - {context.get('tenant_name', 'Oneo CRM')}</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    margin: 0;
                    padding: 0;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                .container {{ 
                    text-align: center;
                    padding: 2rem;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                    backdrop-filter: blur(10px);
                    max-width: 500px;
                    margin: 1rem;
                }}
                h1 {{ margin-bottom: 1rem; font-size: 2rem; }}
                .progress-bar {{
                    width: 100%;
                    height: 8px;
                    background: rgba(255, 255, 255, 0.3);
                    border-radius: 4px;
                    overflow: hidden;
                    margin: 1rem 0;
                }}
                .progress-fill {{
                    height: 100%;
                    background: white;
                    width: {context.get('progress_percentage', 0)}%;
                    transition: width 0.3s ease;
                }}
                .status {{ margin: 1rem 0; font-size: 1.1rem; }}
                .details {{ opacity: 0.8; font-size: 0.9rem; margin-top: 1.5rem; }}
            </style>
            <script>
                // Auto-refresh every 30 seconds
                setTimeout(() => window.location.reload(), 30000);
            </script>
        </head>
        <body>
            <div class="container">
                <h1>🔧 System Maintenance</h1>
                <p class="status">{context.get('status_message', 'System maintenance in progress...')}</p>
                
                <div class="progress-bar">
                    <div class="progress-fill"></div>
                </div>
                <p>{context.get('progress_percentage', 0)}% Complete</p>
                
                <div class="details">
                    <p><strong>Reason:</strong> {context.get('reason', 'System Update')}</p>
                    {f"<p><strong>Estimated Completion:</strong> {context['estimated_completion'].strftime('%I:%M %p')}</p>" if context.get('estimated_completion') else ''}
                    <p><small>This page will refresh automatically every 30 seconds.</small></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return HttpResponse(html, status=503, content_type='text/html')


class TenantSecurityMiddleware:
    """
    Additional security middleware for tenant-specific security measures
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Add tenant-specific security headers
        response = self.get_response(request)
        
        if hasattr(request, 'tenant'):
            # Add tenant identifier to headers (for debugging - remove in production)
            if hasattr(response, '__setitem__'):
                response['X-Tenant-Schema'] = request.tenant.schema_name
        
        return response