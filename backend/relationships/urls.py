"""
URL configuration for relationships API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RelationshipTypeViewSet,
    RelationshipViewSet,
    RelationshipPathViewSet,
    PermissionTraversalViewSet,
    AssignmentViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'types', RelationshipTypeViewSet, basename='relationshiptype')
router.register(r'relationships', RelationshipViewSet, basename='relationship')
router.register(r'paths', RelationshipPathViewSet, basename='relationshippath')
router.register(r'permissions', PermissionTraversalViewSet, basename='permissiontraversal')
router.register(r'assignments', AssignmentViewSet, basename='assignment')

app_name = 'relationships'

# Additional assignment endpoints for Option A frontend
assignment_patterns = [
    path('assignments/record-assignments/', AssignmentViewSet.as_view({'get': 'record_assignments'}), name='record-assignments'),
    path('assignments/change-role/', AssignmentViewSet.as_view({'post': 'change_role'}), name='change-role'),
    path('assignments/add-user/', AssignmentViewSet.as_view({'post': 'add_user'}), name='add-user'),
    path('assignments/available-users/', AssignmentViewSet.as_view({'get': 'available_users'}), name='available-users'),
    path('assignments/reassign/', AssignmentViewSet.as_view({'post': 'reassign'}), name='reassign'),
]

urlpatterns = [
    path('', include(router.urls)),
] + assignment_patterns