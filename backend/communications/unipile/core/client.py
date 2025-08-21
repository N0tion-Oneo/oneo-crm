"""
Core UniPile Client Implementation
Handles base client functionality, authentication, and request management
"""
import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone

import aiohttp
from django.conf import settings

from .exceptions import (
    UnipileConnectionError,
    UnipileAuthenticationError,
    UnipileRateLimitError
)

logger = logging.getLogger(__name__)


class UnipileClient:
    """
    Core UniPile SDK client
    Handles authentication, request management, and client initialization
    """
    
    def __init__(self, dsn: str, access_token: str):
        """Initialize UniPile client with DSN and access token"""
        self.dsn = dsn.rstrip('/')
        self.access_token = access_token
        self.base_url = f"{self.dsn}/api/v1"
        
        # Initialize sub-clients (lazy loading to avoid circular imports)
        self._account = None
        self._messaging = None
        self._users = None
        self._webhooks = None
        self._request = None
        self._linkedin = None
        self._email = None
        self._calendar = None
    
    @property
    def account(self):
        """Lazy load account client"""
        if self._account is None:
            from ..clients.account import UnipileAccountClient
            self._account = UnipileAccountClient(self)
        return self._account
    
    @property
    def messaging(self):
        """Lazy load messaging client"""
        if self._messaging is None:
            from ..clients.messaging import UnipileMessagingClient
            self._messaging = UnipileMessagingClient(self)
        return self._messaging
    
    @property
    def users(self):
        """Lazy load users client"""
        if self._users is None:
            from ..clients.users import UnipileUsersClient
            self._users = UnipileUsersClient(self)
        return self._users
    
    @property
    def webhooks(self):
        """Lazy load webhooks client"""
        if self._webhooks is None:
            from ..clients.webhooks import UnipileWebhookClient
            self._webhooks = UnipileWebhookClient(self)
        return self._webhooks
    
    @property
    def request(self):
        """Lazy load request client"""
        if self._request is None:
            from ..utils.request import UnipileRequestClient
            self._request = UnipileRequestClient(self)
        return self._request
    
    @property
    def linkedin(self):
        """Lazy load LinkedIn client"""
        if self._linkedin is None:
            from ..clients.linkedin import UnipileLinkedInClient
            self._linkedin = UnipileLinkedInClient(self)
        return self._linkedin
    
    @property
    def email(self):
        """Lazy load email client"""
        if self._email is None:
            from ..clients.email import UnipileEmailClient
            self._email = UnipileEmailClient(self)
        return self._email
    
    @property
    def calendar(self):
        """Lazy load calendar client"""
        if self._calendar is None:
            from ..clients.calendar import UnipileCalendarClient
            self._calendar = UnipileCalendarClient(self)
        return self._calendar
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        files: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to UniPile API"""
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_headers = {
            'X-API-KEY': self.access_token,
            'Accept': 'application/json',
        }
        
        # Handle multipart/form-data for file uploads
        if files:
            # Don't set Content-Type for multipart, let aiohttp handle it
            request_data = aiohttp.FormData()
            
            # Add regular form fields
            if data:
                for key, value in data.items():
                    request_data.add_field(key, str(value))
            
            # Add files
            for field_name, (filename, file_obj, content_type) in files.items():
                request_data.add_field(
                    field_name,
                    file_obj,
                    filename=filename,
                    content_type=content_type
                )
        else:
            # Regular JSON request
            request_headers['Content-Type'] = 'application/json'
            request_data = data
        
        if headers:
            request_headers.update(headers)
        
        try:
            async with aiohttp.ClientSession() as session:
                request_kwargs = {
                    'method': method,
                    'url': url,
                    'params': params,
                    'headers': request_headers,
                    'timeout': aiohttp.ClientTimeout(total=30)
                }
                
                if files:
                    request_kwargs['data'] = request_data
                else:
                    request_kwargs['json'] = request_data
                
                async with session.request(**request_kwargs) as response:
                    
                    # Check content type to determine how to parse response
                    content_type = response.headers.get('content-type', '').lower()
                    
                    if content_type.startswith('image/') or 'binary' in content_type or 'octet-stream' in content_type:
                        # Handle binary data (images, files, etc.)
                        if response.status in [200, 201]:
                            binary_data = await response.read()
                            # Return binary data with metadata
                            return {
                                'binary_data': binary_data,
                                'content_type': content_type,
                                'content_length': len(binary_data)
                            }
                        else:
                            # For binary endpoints, we still need error info, try to read as text
                            try:
                                error_text = await response.text()
                                raise UnipileConnectionError(f"API request failed ({response.status}): {error_text}")
                            except:
                                raise UnipileConnectionError(f"API request failed ({response.status}): Binary endpoint error")
                    else:
                        # Handle JSON data (normal API responses)
                        response_data = await response.json()
                        
                        if response.status in [200, 201]:  # Accept both 200 OK and 201 Created
                            return response_data
                        elif response.status == 401:
                            raise UnipileAuthenticationError(
                                f"Authentication failed: {response_data.get('message', 'Invalid access token')}"
                            )
                        elif response.status == 429:
                            raise UnipileRateLimitError(
                                f"Rate limit exceeded: {response_data.get('message', 'Too many requests')}"
                            )
                        else:
                            raise UnipileConnectionError(
                                f"API request failed ({response.status}): {response_data.get('message', 'Unknown error')}"
                            )
                        
        except aiohttp.ClientError as e:
            raise UnipileConnectionError(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            raise UnipileConnectionError(f"Invalid JSON response: {str(e)}")