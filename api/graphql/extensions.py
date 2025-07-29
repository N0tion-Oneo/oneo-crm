"""
GraphQL extensions for query complexity analysis and security
"""
import time
from typing import Any, Dict, List, Optional
from strawberry.extensions import Extension
from strawberry.types import ExecutionResult, ExecutionContext
from django.core.cache import cache
from django.http import HttpRequest


class QueryComplexityExtension(Extension):
    """
    Extension to analyze and limit query complexity
    Prevents complex queries that could cause performance issues
    """
    
    def __init__(self, max_complexity: int = 100):
        self.max_complexity = max_complexity
    
    def on_request_start(self) -> None:
        self.start_time = time.time()
    
    def on_request_end(self) -> None:
        execution_time = time.time() - self.start_time
        if execution_time > 5.0:  # Log slow queries
            print(f"Slow GraphQL query detected: {execution_time:.2f}s")
    
    def on_validate(self, validation_result: List[Any]) -> None:
        # Basic complexity analysis
        # In a production system, you would implement proper query complexity analysis
        if validation_result:
            print("GraphQL validation errors:", validation_result)


class RateLimitExtension(Extension):
    """
    Extension to implement rate limiting for GraphQL requests
    """
    
    def __init__(self, max_requests_per_minute: int = 60):
        self.max_requests_per_minute = max_requests_per_minute
    
    def on_request_start(self) -> None:
        request: HttpRequest = self.execution_context.context.request
        user_id = request.user.id if request.user.is_authenticated else request.META.get('REMOTE_ADDR')
        
        if user_id:
            cache_key = f"graphql_rate_limit:{user_id}"
            current_requests = cache.get(cache_key, 0)
            
            if current_requests >= self.max_requests_per_minute:
                raise Exception("Rate limit exceeded. Please try again later.")
            
            cache.set(cache_key, current_requests + 1, timeout=60)


class AuthenticationExtension(Extension):
    """
    Extension to handle authentication and user context
    """
    
    def on_request_start(self) -> None:
        request: HttpRequest = self.execution_context.context.request
        
        # Add user context to execution
        if hasattr(request, 'user') and request.user.is_authenticated:
            # User is authenticated, proceed normally
            pass
        else:
            # For certain queries, authentication might be required
            # This is handled in individual resolvers for flexibility
            pass


class DepthLimitExtension(Extension):
    """
    Extension to limit query depth to prevent deeply nested queries
    """
    
    def __init__(self, max_depth: int = 10):
        self.max_depth = max_depth
    
    def on_validate(self, validation_result: List[Any]) -> None:
        # Basic depth checking would be implemented here
        # For production, use a proper GraphQL depth analysis library
        pass


class DataLoaderExtension(Extension):
    """
    Extension to manage DataLoader instances for efficient data fetching
    """
    
    def on_request_start(self) -> None:
        # Initialize DataLoaders for this request
        # This would be expanded with actual DataLoader implementations
        self.execution_context.context.dataloaders = {}
    
    def on_request_end(self) -> None:
        # Clean up DataLoaders
        if hasattr(self.execution_context.context, 'dataloaders'):
            # Clear any cached data
            pass


class ErrorFormattingExtension(Extension):
    """
    Extension to format GraphQL errors consistently
    """
    
    def on_request_end(self) -> None:
        # Format errors for consistent API responses
        pass
    
    def format_error(self, error: Exception) -> Dict[str, Any]:
        """Format GraphQL errors for client consumption"""
        formatted_error = {
            "message": str(error),
            "type": error.__class__.__name__,
        }
        
        # Add additional error context in development
        if hasattr(self.execution_context.context, 'request'):
            request = self.execution_context.context.request
            if hasattr(request, 'user') and request.user.is_authenticated:
                formatted_error["user_id"] = request.user.id
        
        return formatted_error


# Default extensions for the schema
DEFAULT_EXTENSIONS = [
    QueryComplexityExtension(max_complexity=100),
    RateLimitExtension(max_requests_per_minute=100),
    AuthenticationExtension(),
    DepthLimitExtension(max_depth=8),
    DataLoaderExtension(),
    ErrorFormattingExtension(),
]