import hashlib
import hmac
import time
import logging
from typing import Optional, Dict, Any
from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


class SecurityMiddleware:
    """
    Comprehensive security middleware for API protection.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Security configuration
        self.max_request_size = getattr(settings, 'MAX_REQUEST_SIZE', 10 * 1024 * 1024)  # 10MB
        self.suspicious_patterns = [
            b'<script',
            b'javascript:',
            b'eval(',
            b'document.cookie',
            b'DROP TABLE',
            b'UNION SELECT',
            b'../../../',
        ]
        
        # Rate limiting for suspicious activity
        self.security_cache_timeout = 3600  # 1 hour
        self.max_security_violations = 10   # per hour
    
    def __call__(self, request):
        """Process request through security checks."""
        # Check request size
        if not self._check_request_size(request):
            return self._security_response("Request too large", status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        
        # Check for suspicious patterns
        if not self._check_suspicious_patterns(request):
            self._log_security_violation(request, "Suspicious pattern detected")
            return self._security_response("Malicious content detected", status.HTTP_400_BAD_REQUEST)
        
        # Check rate limits for security violations
        if not self._check_security_rate_limit(request):
            return self._security_response("Too many security violations", status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Add security headers
        response = self.get_response(request)
        return self._add_security_headers(response)
    
    def _check_request_size(self, request: HttpRequest) -> bool:
        """Check if request size is within limits."""
        content_length = request.META.get('CONTENT_LENGTH')
        if content_length and int(content_length) > self.max_request_size:
            return False
        return True
    
    def _check_suspicious_patterns(self, request: HttpRequest) -> bool:
        """Check request for suspicious patterns."""
        # Check URL
        request_path = request.get_full_path().encode('utf-8', errors='ignore')
        for pattern in self.suspicious_patterns:
            if pattern in request_path.lower():
                return False
        
        # Check headers
        for header_name, header_value in request.META.items():
            if isinstance(header_value, str):
                header_bytes = header_value.encode('utf-8', errors='ignore')
                for pattern in self.suspicious_patterns:
                    if pattern in header_bytes.lower():
                        return False
        
        # Check POST data if available
        if hasattr(request, 'body') and request.body:
            try:
                body_lower = request.body.lower()
                for pattern in self.suspicious_patterns:
                    if pattern in body_lower:
                        return False
            except Exception:
                pass  # Skip if body can't be read
        
        return True
    
    def _check_security_rate_limit(self, request: HttpRequest) -> bool:
        """Check rate limit for security violations."""
        client_ip = self._get_client_ip(request)
        cache_key = f'security_violations:{client_ip}'
        
        violations = cache.get(cache_key, 0)
        if violations >= self.max_security_violations:
            return False
        
        return True
    
    def _log_security_violation(self, request: HttpRequest, violation_type: str):
        """Log security violation and increment counter."""
        client_ip = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
        
        logger.warning(
            f"Security violation: {violation_type} from {client_ip} "
            f"(User-Agent: {user_agent}) Path: {request.get_full_path()}"
        )
        
        # Increment violation counter
        cache_key = f'security_violations:{client_ip}'
        violations = cache.get(cache_key, 0) + 1
        cache.set(cache_key, violations, timeout=self.security_cache_timeout)
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address with proxy support."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        
        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            return x_real_ip.strip()
        
        return request.META.get('REMOTE_ADDR', '0.0.0.0')
    
    def _security_response(self, message: str, status_code: int) -> Response:
        """Create security error response."""
        return Response(
            {"error": message, "code": "SECURITY_VIOLATION"},
            status=status_code
        )
    
    def _add_security_headers(self, response: Response) -> Response:
        """Add security headers to response."""
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
        }
        
        for header, value in security_headers.items():
            response[header] = value
        
        return response


class APIKeyAuthenticator:
    """
    API Key authentication with rate limiting and validation.
    """
    
    def __init__(self):
        self.cache_timeout = 300  # 5 minutes
        self.key_prefix = 'apikey_'
    
    def authenticate_api_key(self, request: Request) -> Optional[Dict[str, Any]]:
        """Authenticate request using API key."""
        api_key = self._extract_api_key(request)
        if not api_key:
            return None
        
        # Check cache first
        cache_key = f'{self.key_prefix}{hashlib.sha256(api_key.encode()).hexdigest()}'
        cached_auth = cache.get(cache_key)
        if cached_auth:
            return cached_auth
        
        # Validate API key (implement based on your API key storage)
        auth_data = self._validate_api_key(api_key)
        if auth_data:
            cache.set(cache_key, auth_data, timeout=self.cache_timeout)
        
        return auth_data
    
    def _extract_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from request headers."""
        # Try X-API-Key header
        api_key = request.META.get('HTTP_X_API_KEY')
        if api_key:
            return api_key
        
        # Try Authorization header with Bearer scheme
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        
        return None
    
    def _validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate API key against your storage.
        This is a placeholder - implement based on your API key model.
        """
        # Example implementation:
        # try:
        #     api_key_obj = APIKey.objects.get(key=api_key, is_active=True)
        #     return {
        #         'user_id': api_key_obj.user_id,
        #         'tier': api_key_obj.tier,
        #         'permissions': api_key_obj.permissions,
        #     }
        # except APIKey.DoesNotExist:
        #     return None
        
        return None


class QueryComplexityAnalyzer:
    """
    Analyze GraphQL query complexity to prevent expensive queries.
    """
    
    def __init__(self, max_complexity: int = 100):
        self.max_complexity = max_complexity
        self.field_costs = {
            # Expensive operations
            'records': 2,
            'relationships': 3,
            'search': 5,
            'analytics': 10,
            
            # Medium cost
            'pipelines': 1,
            'users': 1,
            
            # Low cost
            'me': 0.1,
            'pipeline': 0.5,
        }
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze GraphQL query complexity.
        Returns complexity score and whether query should be allowed.
        """
        try:
            # This is a simplified implementation
            # In production, use a proper GraphQL parser
            complexity = self._calculate_complexity(query)
            
            return {
                'complexity': complexity,
                'allowed': complexity <= self.max_complexity,
                'max_complexity': self.max_complexity
            }
        except Exception as e:
            logger.error(f"Query complexity analysis failed: {e}")
            return {
                'complexity': self.max_complexity,  # Assume max on error
                'allowed': False,
                'error': str(e)
            }
    
    def _calculate_complexity(self, query: str) -> float:
        """Calculate query complexity score."""
        complexity = 0
        query_lower = query.lower()
        
        # Count field occurrences and multiply by cost
        for field, cost in self.field_costs.items():
            count = query_lower.count(field)
            complexity += count * cost
        
        # Add complexity for nested queries
        nesting_level = query.count('{')
        complexity += nesting_level * 0.5
        
        # Add complexity for arguments (pagination, filtering)
        arg_patterns = ['limit:', 'offset:', 'where:', 'filter:']
        for pattern in arg_patterns:
            complexity += query_lower.count(pattern) * 0.2
        
        return complexity


class ContentSecurityPolicy:
    """
    Content Security Policy (CSP) header management.
    """
    
    def __init__(self):
        self.default_policy = {
            'default-src': ["'self'"],
            'script-src': ["'self'", "'unsafe-inline'"],
            'style-src': ["'self'", "'unsafe-inline'"],
            'img-src': ["'self'", "data:", "https:"],
            'font-src': ["'self'"],
            'connect-src': ["'self'"],
            'frame-ancestors': ["'none'"],
        }
    
    def get_csp_header(self, policy_overrides: Optional[Dict] = None) -> str:
        """Generate CSP header string."""
        policy = self.default_policy.copy()
        if policy_overrides:
            policy.update(policy_overrides)
        
        csp_parts = []
        for directive, sources in policy.items():
            sources_str = ' '.join(sources)
            csp_parts.append(f"{directive} {sources_str}")
        
        return '; '.join(csp_parts)


class RequestSignatureValidator:
    """
    Validate request signatures for webhook security.
    """
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode('utf-8')
    
    def validate_signature(self, request: Request, signature: str) -> bool:
        """Validate HMAC signature of request body."""
        try:
            # Extract signature from header format like "sha256=..."
            if '=' in signature:
                algorithm, signature_hex = signature.split('=', 1)
            else:
                algorithm, signature_hex = 'sha256', signature
            
            # Calculate expected signature
            if algorithm == 'sha256':
                expected_signature = hmac.new(
                    self.secret_key,
                    request.body,
                    hashlib.sha256
                ).hexdigest()
            else:
                logger.warning(f"Unsupported signature algorithm: {algorithm}")
                return False
            
            # Compare signatures securely
            return hmac.compare_digest(signature_hex, expected_signature)
            
        except Exception as e:
            logger.error(f"Signature validation error: {e}")
            return False
    
    def generate_signature(self, payload: bytes) -> str:
        """Generate HMAC signature for payload."""
        signature = hmac.new(
            self.secret_key,
            payload,
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"


# Utility functions for common security tasks

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks."""
    import os
    import re
    
    # Remove path separators
    filename = os.path.basename(filename)
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename


def validate_json_schema(data: Any, schema: Dict) -> bool:
    """Validate JSON data against schema (placeholder)."""
    # Implement JSON schema validation
    # You might use jsonschema library for this
    return True


def rate_limit_key(request: Request, key_suffix: str = '') -> str:
    """Generate consistent rate limit cache key."""
    user_id = getattr(request.user, 'id', 'anonymous')
    client_ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    return f"rate_limit:{user_id}:{client_ip}:{key_suffix}"