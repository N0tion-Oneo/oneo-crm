"""
HTTP Request Node Processor - Make HTTP requests to external APIs
"""
import logging
import json
from typing import Dict, Any, Optional
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class HTTPRequestProcessor(AsyncNodeProcessor):
    """Process HTTP request nodes for external API calls"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["url", "method"],
        "properties": {
            "url": {
                "type": "string",
                "format": "uri",
                "description": "URL to send request to",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "https://api.example.com/endpoint/{record.id}"
                }
            },
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                "default": "GET",
                "description": "HTTP method",
                "ui_hints": {
                    "widget": "select"
                }
            },
            "headers": {
                "type": "object",
                "description": "Request headers",
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 4,
                    "placeholder": '{\n  "Content-Type": "application/json",\n  "Authorization": "Bearer {{api_key}}"\n}'
                }
            },
            "body": {
                "type": "object",
                "description": "Request body (for POST/PUT/PATCH)",
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 6,
                    "placeholder": '{\n  "name": "{{contact.name}}",\n  "email": "{{contact.email}}"\n}',
                    "show_when": {"method": ["POST", "PUT", "PATCH"]}
                }
            },
            "timeout": {
                "type": "integer",
                "minimum": 1,
                "maximum": 300,
                "default": 30,
                "description": "Request timeout in seconds"
            },
            "auth": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["none", "basic", "bearer", "api_key"],
                        "default": "none"
                    },
                    "username": {"type": "string"},
                    "password": {"type": "string"},
                    "token": {"type": "string"},
                    "api_key": {"type": "string"},
                    "api_key_header": {"type": "string", "default": "X-API-Key"}
                },
                "description": "Authentication configuration",
                "ui_hints": {
                    "section": "authentication"
                }
            },
            "retry": {
                "type": "object",
                "properties": {
                    "max_retries": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 10,
                        "default": 3
                    },
                    "delay": {
                        "type": "number",
                        "minimum": 0.1,
                        "maximum": 60,
                        "default": 1.0
                    },
                    "exponential_backoff": {
                        "type": "boolean",
                        "default": True
                    },
                    "retry_on_status": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "default": [500, 502, 503, 504]
                    }
                },
                "description": "Retry configuration",
                "ui_hints": {
                    "section": "advanced"
                }
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "http_request"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process HTTP request node"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Extract configuration
        method = config.get('method', 'GET').upper()
        url_template = config.get('url', '')
        headers = config.get('headers', {})
        body = config.get('body', {})
        timeout = config.get('timeout', 30)
        auth_config = config.get('auth', {})
        retry_config = config.get('retry', {})
        
        # Validate required fields
        if not url_template:
            raise ValueError("HTTP request node requires URL")
        
        # Format URL with context
        try:
            url = url_template.format(**context)
        except KeyError as e:
            raise ValueError(f"Missing context variable for URL formatting: {e}")
        
        # Format headers and body with context
        formatted_headers = self._format_dict_with_context(headers, context)
        formatted_body = self._format_body_with_context(body, context)
        
        # Add authentication if configured
        if auth_config:
            formatted_headers = await self._apply_authentication(formatted_headers, auth_config, context)
        
        # Make the HTTP request with retry logic
        try:
            response_data = await self._make_request_with_retry(
                method, url, formatted_headers, formatted_body, timeout, retry_config
            )
            
            return {
                'success': True,
                'status_code': response_data['status_code'],
                'headers': response_data['headers'],
                'data': response_data['data'],
                'url': url,
                'method': method
            }
            
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'url': url,
                'method': method
            }
    
    async def _make_request_with_retry(
        self, 
        method: str, 
        url: str, 
        headers: Dict[str, str], 
        body: Any, 
        timeout: int,
        retry_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        
        import aiohttp
        
        max_retries = retry_config.get('max_retries', 3)
        retry_delay = retry_config.get('delay', 1.0)
        retry_exponential = retry_config.get('exponential_backoff', True)
        retry_on_status = retry_config.get('retry_on_status', [500, 502, 503, 504])
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as session:
                    
                    # Make the request based on method
                    if method == 'GET':
                        async with session.get(url, headers=headers) as response:
                            return await self._parse_response(response)
                    elif method == 'POST':
                        async with session.post(url, headers=headers, json=body) as response:
                            return await self._parse_response(response)
                    elif method == 'PUT':
                        async with session.put(url, headers=headers, json=body) as response:
                            return await self._parse_response(response)
                    elif method == 'PATCH':
                        async with session.patch(url, headers=headers, json=body) as response:
                            return await self._parse_response(response)
                    elif method == 'DELETE':
                        async with session.delete(url, headers=headers) as response:
                            return await self._parse_response(response)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")
            
            except aiohttp.ClientError as e:
                last_exception = e
                
                # Check if we should retry
                if attempt < max_retries:
                    if hasattr(e, 'status') and e.status not in retry_on_status:
                        # Don't retry for certain status codes
                        break
                    
                    # Calculate delay for next attempt
                    delay = retry_delay
                    if retry_exponential:
                        delay *= (2 ** attempt)
                    
                    logger.warning(f"HTTP request attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    
                    import asyncio
                    await asyncio.sleep(delay)
                    continue
                else:
                    break
            
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    delay = retry_delay
                    if retry_exponential:
                        delay *= (2 ** attempt)
                    
                    logger.warning(f"HTTP request attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    
                    import asyncio
                    await asyncio.sleep(delay)
                    continue
                else:
                    break
        
        # If we get here, all retries failed
        raise last_exception or Exception("HTTP request failed after all retries")
    
    async def _parse_response(self, response) -> Dict[str, Any]:
        """Parse HTTP response"""
        
        try:
            content_type = response.headers.get('content-type', '').lower()
            
            if 'application/json' in content_type:
                data = await response.json()
            elif 'text/' in content_type or 'application/xml' in content_type:
                data = await response.text()
            else:
                # For binary content, read as bytes and encode as base64
                raw_data = await response.read()
                import base64
                data = base64.b64encode(raw_data).decode('utf-8')
                
        except Exception as e:
            logger.warning(f"Failed to parse response content: {e}")
            try:
                data = await response.text()
            except:
                data = None
        
        return {
            'status_code': response.status,
            'headers': dict(response.headers),
            'data': data,
            'success': response.status < 400
        }
    
    def _format_dict_with_context(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, str]:
        """Format dictionary values with context variables"""
        
        formatted = {}
        for key, value in data.items():
            try:
                if isinstance(value, str):
                    formatted[key] = value.format(**context)
                else:
                    formatted[key] = str(value)
            except KeyError as e:
                logger.warning(f"Context variable not found for key '{key}': {e}")
                formatted[key] = str(value)
            except Exception as e:
                logger.error(f"Error formatting key '{key}': {e}")
                formatted[key] = str(value)
        
        return formatted
    
    def _format_body_with_context(self, body: Any, context: Dict[str, Any]) -> Any:
        """Format request body with context variables"""
        
        if isinstance(body, dict):
            formatted_body = {}
            for key, value in body.items():
                try:
                    if isinstance(value, str):
                        formatted_body[key] = value.format(**context)
                    else:
                        formatted_body[key] = value
                except KeyError as e:
                    logger.warning(f"Context variable not found for body key '{key}': {e}")
                    formatted_body[key] = value
                except Exception as e:
                    logger.error(f"Error formatting body key '{key}': {e}")
                    formatted_body[key] = value
            return formatted_body
        
        elif isinstance(body, str):
            try:
                return body.format(**context)
            except KeyError as e:
                logger.warning(f"Context variable not found for body formatting: {e}")
                return body
            except Exception as e:
                logger.error(f"Error formatting body: {e}")
                return body
        
        else:
            return body
    
    async def _apply_authentication(
        self, 
        headers: Dict[str, str], 
        auth_config: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Apply authentication to request headers"""
        
        auth_type = auth_config.get('type', '').lower()
        
        if auth_type == 'bearer':
            token = auth_config.get('token', '').format(**context)
            headers['Authorization'] = f'Bearer {token}'
        
        elif auth_type == 'basic':
            username = auth_config.get('username', '').format(**context)
            password = auth_config.get('password', '').format(**context)
            
            import base64
            credentials = base64.b64encode(f'{username}:{password}'.encode()).decode()
            headers['Authorization'] = f'Basic {credentials}'
        
        elif auth_type == 'api_key':
            api_key = auth_config.get('api_key', '').format(**context)
            header_name = auth_config.get('header_name', 'X-API-Key')
            headers[header_name] = api_key
        
        elif auth_type == 'custom':
            # Custom headers for authentication
            custom_headers = auth_config.get('headers', {})
            for key, value in custom_headers.items():
                headers[key] = str(value).format(**context)
        
        return headers
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate HTTP request node inputs"""
        node_data = node_config.get('data', {})
        
        # Check required fields
        if not node_data.get('url'):
            return False
        
        # Validate method
        method = node_data.get('method', 'GET').upper()
        valid_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
        if method not in valid_methods:
            return False
        
        # Validate timeout
        timeout = node_data.get('timeout', 30)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            return False
        
        # Validate retry configuration
        retry_config = node_data.get('retry', {})
        if retry_config:
            max_retries = retry_config.get('max_retries', 3)
            if not isinstance(max_retries, int) or max_retries < 0:
                return False
            
            delay = retry_config.get('delay', 1.0)
            if not isinstance(delay, (int, float)) or delay < 0:
                return False
        
        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for HTTP request node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        node_data = node_config.get('data', {})
        
        # Format URL for checkpoint (safely)
        url_template = node_data.get('url', '')
        try:
            formatted_url = url_template.format(**context)
        except:
            formatted_url = url_template
        
        checkpoint.update({
            'method': node_data.get('method', 'GET'),
            'url_template': url_template,
            'formatted_url': formatted_url,
            'timeout': node_data.get('timeout', 30),
            'has_auth': bool(node_data.get('auth')),
            'has_retry': bool(node_data.get('retry'))
        })
        
        return checkpoint