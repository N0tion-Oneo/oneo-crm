"""
Strawberry GraphQL URL configuration
"""
from django.urls import path
from strawberry.django.views import AsyncGraphQLView
from .strawberry_schema import schema

urlpatterns = [
    path('', AsyncGraphQLView.as_view(schema=schema)),
]