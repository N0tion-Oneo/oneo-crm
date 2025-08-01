"""
Simple test view to debug JWT authentication
"""
from django.http import JsonResponse
from django.views import View
from rest_framework_simplejwt.authentication import JWTAuthentication
from .jwt_authentication import TenantAwareJWTAuthentication
import logging

logger = logging.getLogger(__name__)


class SimpleJWTTestView(View):
    """Simple view to test JWT authentication directly"""
    
    def get(self, request):
        logger.info("SimpleJWTTestView called")
        
        # Test our JWT authentication directly
        jwt_auth = TenantAwareJWTAuthentication()
        auth_result = jwt_auth.authenticate(request)
        
        if auth_result:
            user, token = auth_result
            return JsonResponse({
                'authenticated': True,
                'user_email': user.email,
                'user_id': user.id,
                'token_valid': True,
                'tenant': getattr(request, 'tenant', {}).schema_name if hasattr(getattr(request, 'tenant', None), 'schema_name') else 'No tenant'
            })
        else:
            return JsonResponse({
                'authenticated': False,
                'auth_header': request.META.get('HTTP_AUTHORIZATION', 'No auth header'),
                'tenant': getattr(request, 'tenant', {}).schema_name if hasattr(getattr(request, 'tenant', None), 'schema_name') else 'No tenant'
            })