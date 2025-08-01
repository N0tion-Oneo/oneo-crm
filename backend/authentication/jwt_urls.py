"""
Clean JWT Authentication URLs
Simple, straightforward routing for JWT auth
"""

from django.urls import path
from . import jwt_views

app_name = 'jwt_auth'

urlpatterns = [
    # JWT Authentication endpoints
    path('login/', jwt_views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', jwt_views.CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', jwt_views.logout_view, name='logout'),
    
    # User info endpoints
    path('me/', jwt_views.current_user_view, name='current_user'),
    
    # Health check
    path('health/', jwt_views.health_check_view, name='health_check'),
]