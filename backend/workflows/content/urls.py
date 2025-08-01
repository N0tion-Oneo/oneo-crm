"""
URL patterns for Content Management System
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ContentLibraryViewSet, ContentAssetViewSet, ContentTagViewSet,
    ContentUsageViewSet, ContentApprovalViewSet
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'libraries', ContentLibraryViewSet)
router.register(r'assets', ContentAssetViewSet)
router.register(r'tags', ContentTagViewSet)
router.register(r'usage', ContentUsageViewSet)
router.register(r'approvals', ContentApprovalViewSet)

urlpatterns = [
    # API endpoints
    path('', include(router.urls)),
]