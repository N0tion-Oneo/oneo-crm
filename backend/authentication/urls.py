"""
URL patterns for authentication API endpoints
Defines routes for async session-based authentication
"""

from django.urls import path, include
from . import views

app_name = 'authentication'

# Main authentication endpoints
auth_patterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('me/', views.CurrentUserView.as_view(), name='current_user'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('permissions/', views.user_permissions_view, name='user_permissions'),
    path('health/', views.health_check_view, name='health_check'),
]

# Session management endpoints
session_patterns = [
    path('sessions/', views.user_sessions_view, name='user_sessions'),
    path('sessions/extend/', views.extend_session_view, name='extend_session'),
    path('sessions/<int:session_id>/destroy/', views.destroy_session_view, name='destroy_session'),
    path('sessions/destroy-all/', views.destroy_all_sessions_view, name='destroy_all_sessions'),
]

# User type endpoints removed - now handled by UserTypeViewSet in urls_drf.py

# Combine all patterns - remove 'auth/' prefix since it's already in tenant URLs
urlpatterns = [
    path('', include(auth_patterns)),
    path('', include(session_patterns)),
]