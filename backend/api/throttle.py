from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta
import hashlib


class BurstRateThrottle(UserRateThrottle):
    """
    High-frequency rate limiting for burst requests.
    Allows 60 requests per minute per user.
    """
    scope = 'burst'
    rate = '60/min'


class SustainedRateThrottle(UserRateThrottle):
    """
    Sustained rate limiting for long-term usage.
    Allows 1000 requests per hour per user.
    """
    scope = 'sustained'
    rate = '1000/hour'


class GraphQLRateThrottle(UserRateThrottle):
    """
    Specialized rate limiting for GraphQL endpoints.
    Considers query complexity in addition to request count.
    """
    scope = 'graphql'
    rate = '100/min'
    
    def get_cache_key(self, request, view):
        """Include user and query hash in cache key."""
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        
        # Add query hash for GraphQL-specific throttling
        query = request.data.get('query', '') if hasattr(request, 'data') else ''
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        
        return f'{self.scope}:{ident}:{query_hash}'
    
    def allow_request(self, request, view):
        """
        Override to consider query complexity.
        Simple queries get normal rate limits, complex queries get reduced limits.
        """
        # Get query complexity from request (set by GraphQL complexity analyzer)
        complexity = getattr(request, 'query_complexity', 1)
        
        # Adjust rate based on complexity
        if complexity > 50:
            # Complex queries get 1/3 the rate limit
            original_rate = self.rate
            self.rate = f'{int(self.rate.split("/")[0]) // 3}/{self.rate.split("/")[1]}'
            result = super().allow_request(request, view)
            self.rate = original_rate  # Restore original rate
            return result
        elif complexity > 20:
            # Medium complexity queries get 2/3 the rate limit
            original_rate = self.rate
            self.rate = f'{int(self.rate.split("/")[0]) * 2 // 3}/{self.rate.split("/")[1]}'
            result = super().allow_request(request, view)
            self.rate = original_rate
            return result
        
        return super().allow_request(request, view)


class WebSocketRateThrottle:
    """
    Rate limiting for WebSocket connections.
    Tracks connection attempts and message rates.
    """
    
    def __init__(self):
        self.connection_rate = 10  # connections per minute
        self.message_rate = 60     # messages per minute
        self.cache_timeout = 3600  # 1 hour
    
    def allow_connection(self, user_id, client_ip):
        """Check if user can establish a new WebSocket connection."""
        cache_key = f'ws_conn:{user_id}:{client_ip}'
        
        current_time = timezone.now()
        connections = cache.get(cache_key, [])
        
        # Remove old connections (outside the time window)
        minute_ago = current_time - timedelta(minutes=1)
        connections = [conn_time for conn_time in connections if conn_time > minute_ago]
        
        # Check if under limit
        if len(connections) >= self.connection_rate:
            return False
        
        # Add current connection
        connections.append(current_time)
        cache.set(cache_key, connections, timeout=self.cache_timeout)
        
        return True
    
    def allow_message(self, user_id, client_ip):
        """Check if user can send a WebSocket message."""
        cache_key = f'ws_msg:{user_id}:{client_ip}'
        
        current_time = timezone.now()
        messages = cache.get(cache_key, [])
        
        # Remove old messages
        minute_ago = current_time - timedelta(minutes=1)
        messages = [msg_time for msg_time in messages if msg_time > minute_ago]
        
        # Check if under limit
        if len(messages) >= self.message_rate:
            return False
        
        # Add current message
        messages.append(current_time)
        cache.set(cache_key, messages, timeout=self.cache_timeout)
        
        return True


class APIKeyRateThrottle(AnonRateThrottle):
    """
    Rate limiting based on API key.
    Higher limits for authenticated API keys.
    """
    scope = 'apikey'
    rate = '10000/hour'  # Default for API key users
    
    def get_cache_key(self, request, view):
        """Use API key as identifier instead of IP."""
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return None  # No API key, fall back to other throttles
        
        # Hash the API key for cache key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        return f'{self.scope}:{key_hash}'
    
    def get_rate(self):
        """Get rate limit based on API key tier."""
        # This could be enhanced to check API key tier from database
        return self.rate


class DynamicRateThrottle(UserRateThrottle):
    """
    Dynamic rate limiting that adjusts based on user tier and endpoint sensitivity.
    """
    
    def __init__(self):
        super().__init__()
        self.tier_rates = {
            'free': '100/hour',
            'basic': '1000/hour', 
            'premium': '10000/hour',
            'enterprise': '100000/hour'
        }
        self.endpoint_multipliers = {
            'high_sensitivity': 0.1,     # Reduce rate by 90%
            'medium_sensitivity': 0.5,   # Reduce rate by 50%
            'low_sensitivity': 1.0,      # Normal rate
            'public': 2.0                # Double rate for public endpoints
        }
    
    def get_rate(self):
        """Get dynamic rate based on user tier and endpoint sensitivity."""
        # Get user tier (you'd implement this based on your user model)
        user_tier = getattr(self.request.user, 'subscription_tier', 'free')
        base_rate = self.tier_rates.get(user_tier, self.tier_rates['free'])
        
        # Get endpoint sensitivity from view
        sensitivity = getattr(self.view, 'sensitivity_level', 'low_sensitivity')
        multiplier = self.endpoint_multipliers.get(sensitivity, 1.0)
        
        # Calculate adjusted rate
        rate_num, rate_period = base_rate.split('/')
        adjusted_rate_num = int(int(rate_num) * multiplier)
        
        return f'{adjusted_rate_num}/{rate_period}'


# Throttle class registry for easy configuration
THROTTLE_CLASSES = {
    'burst': BurstRateThrottle,
    'sustained': SustainedRateThrottle,
    'graphql': GraphQLRateThrottle,
    'apikey': APIKeyRateThrottle,
    'dynamic': DynamicRateThrottle,
}


def get_throttle_classes_for_view(view_name, user_type='authenticated'):
    """
    Get appropriate throttle classes for a given view and user type.
    """
    if view_name == 'graphql':
        return [GraphQLRateThrottle, SustainedRateThrottle]
    elif view_name in ['login', 'register', 'password_reset']:
        return [BurstRateThrottle]  # Stricter for auth endpoints
    elif user_type == 'api_key':
        return [APIKeyRateThrottle]
    elif user_type == 'anonymous':
        return [AnonRateThrottle]
    else:
        return [BurstRateThrottle, SustainedRateThrottle]