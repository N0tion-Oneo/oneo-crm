"""
Webhook signature validation for UniPile webhooks
"""
import hashlib
import hmac
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WebhookValidator:
    """Validates UniPile webhook signatures"""
    
    def __init__(self, secret: Optional[str] = None):
        self.secret = secret
    
    def validate_signature(self, payload: bytes, signature: str) -> bool:
        """
        Validate webhook signature
        
        Args:
            payload: Raw request body bytes
            signature: Signature from webhook headers
            
        Returns:
            bool: True if signature is valid
        """
        if not self.secret:
            logger.warning("No webhook secret configured, skipping signature validation")
            return True
        
        try:
            # Create expected signature
            expected_signature = hmac.new(
                self.secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures (constant time comparison)
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Webhook signature validation failed: {e}")
            return False
    
    def extract_signature(self, request) -> Optional[str]:
        """
        Extract signature from request headers
        
        Args:
            request: Django request object
            
        Returns:
            Optional[str]: Extracted signature or None
        """
        # Common webhook signature header patterns
        signature_headers = [
            'HTTP_X_UNIPILE_SIGNATURE',
            'HTTP_X_SIGNATURE', 
            'HTTP_SIGNATURE',
            'HTTP_X_HUB_SIGNATURE',
            'HTTP_X_HUB_SIGNATURE_256'
        ]
        
        for header in signature_headers:
            signature = request.META.get(header)
            if signature:
                # Remove signature algorithm prefix if present (e.g., "sha256=")
                if '=' in signature:
                    signature = signature.split('=', 1)[1]
                return signature
        
        return None


# Global validator instance (will be configured per tenant if needed)
webhook_validator = WebhookValidator()