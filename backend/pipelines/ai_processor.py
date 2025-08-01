"""
AI field processing system with OpenAI integration and tool support
"""
import asyncio
import json
import logging
import hashlib
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from asgiref.sync import sync_to_async

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None

from .field_types import AIGeneratedFieldConfig

logger = logging.getLogger(__name__)


class AIFieldProcessor:
    """Processes AI fields with tool integration and caching"""
    
    def __init__(self, field, record):
        self.field = field
        self.record = record
        
        # Validate AI configuration
        try:
            self.config = AIGeneratedFieldConfig(**field.ai_config)
        except Exception as e:
            logger.error(f"Invalid AI config for field {field.name}: {e}")
            raise ValueError(f"Invalid AI configuration: {e}")
        
        # Get tenant from record's pipeline
        self.tenant = self._get_tenant_from_record()
        
        # Initialize OpenAI client with tenant-specific API key
        self.client = self._initialize_openai_client()
    
    def _get_tenant_from_record(self):
        """Get tenant from the current record's schema context"""
        from django_tenants.utils import get_tenant_model
        from django.db import connection
        
        # Get tenant model
        TenantModel = get_tenant_model()
        
        # Get current schema name from connection
        schema_name = connection.schema_name if hasattr(connection, 'schema_name') else 'public'
        
        try:
            # Find tenant by schema name
            return TenantModel.objects.get(schema_name=schema_name)
        except TenantModel.DoesNotExist:
            logger.error(f"Tenant not found for schema: {schema_name}")
            return None
    
    def _initialize_openai_client(self):
        """Initialize OpenAI client with tenant-specific configuration ONLY"""
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI not available - AI fields will use fallback values")
            return None
        
        if not self.tenant:
            logger.error("No tenant found - AI processing requires tenant context")
            return None
        
        # Check if tenant has AI enabled and configured
        if not self.tenant.can_use_ai_features():
            logger.warning(f"AI features not available for tenant {self.tenant.name} - check configuration and usage limits")
            return None
        
        # Get tenant's OpenAI API key (REQUIRED - no global fallback)
        api_key = self.tenant.get_openai_api_key()
        if not api_key:
            logger.warning(f"No OpenAI API key configured for tenant {self.tenant.name} - configure via tenant AI settings")
            return None
        
        try:
            return AsyncOpenAI(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client for tenant {self.tenant.name}: {e}")
            return None
    
    async def process_field(self) -> Any:
        """Main processing method for AI field"""
        try:
            # Check cache first
            cached_result = await self._get_cached_result()
            if cached_result is not None:
                logger.debug(f"Using cached result for AI field {self.field.name}")
                return cached_result
            
            # Check if OpenAI is available
            if not self.client:
                logger.warning(f"OpenAI not available for field {self.field.name}, using fallback")
                return self.config.fallback_value
            
            # Build context with record data
            context = self._build_context()
            
            # Prepare tools if enabled
            tools = self._prepare_tools() if self.config.enable_tools else None
            
            # Execute AI with tool access
            result = await self._execute_ai_request(context, tools)
            
            # Cache the result
            await self._cache_result(result)
            
            # Log usage for billing/monitoring
            await self._log_usage(result)
            
            return result
            
        except Exception as e:
            logger.error(f"AI field processing failed for {self.field.name}: {e}")
            return self.config.fallback_value
    
    def _build_context(self) -> str:
        """Build AI prompt with record data substitution"""
        context = self.config.ai_prompt
        
        # Get all record data
        record_data = self.record.data.copy()
        
        # Add metadata if enabled
        if self.config.include_metadata:
            record_data.update({
                'id': self.record.id,
                'created_at': self.record.created_at.isoformat() if self.record.created_at else '',
                'updated_at': self.record.updated_at.isoformat() if self.record.updated_at else '',
                'created_by': self.record.created_by.username if self.record.created_by else '',
                'pipeline_name': self.record.pipeline.name
            })
        
        # Remove excluded fields
        for field_name in self.config.excluded_fields:
            record_data.pop(field_name, None)
        
        # Handle special syntax
        if '{*}' in context:
            # Replace {*} with formatted summary of all fields
            all_fields_summary = self._format_all_fields(record_data)
            context = context.replace('{*}', all_fields_summary)
        
        # Replace individual field references {field_name|default}
        field_pattern = r'\\{([^}]+)\\}'
        
        def replace_field(match):
            field_expr = match.group(1)
            if '|' in field_expr:
                field_name, default = field_expr.split('|', 1)
                default = default.strip("'\"")
            else:
                field_name, default = field_expr, ''
            
            value = record_data.get(field_name, default)
            return str(value) if value is not None else default
        
        context = re.sub(field_pattern, replace_field, context)
        
        return context
    
    def _format_all_fields(self, record_data: Dict[str, Any]) -> str:
        """Format all fields for {*} replacement"""
        formatted_lines = []
        for key, value in record_data.items():
            if value is not None and value != '':
                # Handle complex data types
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value, indent=2)
                else:
                    value_str = str(value)
                formatted_lines.append(f"{key}: {value_str}")
        return '\\n'.join(formatted_lines)
    
    def _prepare_tools(self) -> Optional[List[Dict[str, Any]]]:
        """Prepare OpenAI tools based on configuration"""
        if not self.config.enable_tools:
            return None
        
        tools = []
        
        if 'web_search' in self.config.allowed_tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for current information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "num_results": {"type": "integer", "default": 5}
                        },
                        "required": ["query"]
                    }
                }
            })
        
        if 'code_interpreter' in self.config.allowed_tools:
            # Note: Code interpreter is handled differently in the OpenAI API
            # This is a placeholder for the actual implementation
            tools.append({
                "type": "code_interpreter"
            })
        
        if 'dalle' in self.config.allowed_tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": "generate_image",
                    "description": "Generate images using DALL-E",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string", "description": "Image generation prompt"},
                            "size": {"type": "string", "enum": ["1024x1024", "1792x1024", "1024x1792"], "default": "1024x1024"}
                        },
                        "required": ["prompt"]
                    }
                }
            })
        
        return tools if tools else None
    
    async def _execute_ai_request(self, context: str, tools: Optional[List[Dict[str, Any]]]) -> Any:
        """Execute the AI request with tool support"""
        messages = [{"role": "user", "content": context}]
        
        # Check tool budget
        if tools and not await self._check_tool_budget():
            raise Exception("Tool usage budget exceeded")
        
        # Make the API call
        kwargs = {
            "model": self.config.ai_model,
            "messages": messages,
            "temperature": self.config.temperature,
        }
        
        if tools:
            kwargs["tools"] = tools
        
        if self.config.max_tokens:
            kwargs["max_tokens"] = self.config.max_tokens
        
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(**kwargs),
                timeout=self.config.timeout
            )
        except asyncio.TimeoutError:
            raise Exception(f"AI request timed out after {self.config.timeout} seconds")
        
        # Handle tool calls if present
        if response.choices[0].message.tool_calls:
            result = await self._handle_tool_calls(response.choices[0].message, messages)
        else:
            result = response.choices[0].message.content
        
        # Parse output based on type
        return self._parse_output(result)
    
    async def _handle_tool_calls(self, message, messages: List[Dict[str, Any]]) -> str:
        """Handle OpenAI tool calls"""
        # Add assistant message with tool calls
        messages.append({
            "role": "assistant", 
            "content": message.content,
            "tool_calls": [tc.model_dump() for tc in message.tool_calls]
        })
        
        # Execute each tool call
        for tool_call in message.tool_calls:
            tool_result = await self._execute_tool_call(tool_call)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result)
            })
            
            # Update tool usage tracking
            await self._update_tool_usage(tool_call.function.name)
        
        # Get final response from AI
        response = await self.client.chat.completions.create(
            model=self.config.ai_model,
            messages=messages,
            temperature=self.config.temperature
        )
        
        return response.choices[0].message.content
    
    async def _execute_tool_call(self, tool_call) -> Dict[str, Any]:
        """Execute a specific tool call"""
        function_name = tool_call.function.name
        try:
            function_args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            return {"error": "Invalid function arguments"}
        
        if function_name == "web_search":
            return await self._web_search(function_args.get("query", ""), function_args.get("num_results", 5))
        elif function_name == "generate_image":
            return await self._generate_image(function_args.get("prompt", ""), function_args.get("size", "1024x1024"))
        else:
            return {"error": f"Unknown function: {function_name}"}
    
    async def _web_search(self, query: str, num_results: int) -> Dict[str, Any]:
        """Perform web search using configured search API"""
        # This is a mock implementation
        # In production, you would integrate with a search API like Serper, Tavily, etc.
        logger.info(f"Mock web search for: {query}")
        
        return {
            "query": query,
            "results": [
                {
                    "title": f"Mock Result for {query}",
                    "url": "https://example.com",
                    "snippet": f"This is a mock search result for the query: {query}"
                }
            ],
            "num_results": 1
        }
    
    async def _generate_image(self, prompt: str, size: str) -> Dict[str, Any]:
        """Generate image using DALL-E"""
        try:
            response = await self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality="standard",
                n=1
            )
            
            return {
                "url": response.data[0].url,
                "prompt": prompt,
                "size": size,
                "success": True
            }
        except Exception as e:
            logger.error(f"DALL-E image generation failed: {e}")
            return {"error": str(e), "success": False}
    
    def _parse_output(self, result: str) -> Any:
        """Parse AI output based on configured output type"""
        if not result:
            return self.config.fallback_value
        
        try:
            if self.config.output_type == 'json':
                return json.loads(result)
            
            elif self.config.output_type == 'number':
                # Extract number from text
                number_match = re.search(r'-?\\d+(?:\\.\\d+)?', result)
                if number_match:
                    return float(number_match.group())
                else:
                    return self.config.fallback_value
            
            elif self.config.output_type == 'boolean':
                lower_result = result.lower().strip()
                return lower_result in ['true', 'yes', '1', 'correct', 'positive', 'good']
            
            elif self.config.output_type == 'image':
                # For image outputs, expect URL or base64 data
                if result.startswith('http'):
                    return {"url": result}
                else:
                    return {"data": result}
            
            else:  # text or other types
                return result.strip()
                
        except Exception as e:
            logger.warning(f"Failed to parse AI output as {self.config.output_type}: {e}")
            return self.config.fallback_value
    
    async def _check_tool_budget(self) -> bool:
        """Check if tool usage is within budget"""
        if not self.config.tool_budget:
            return True
        
        # Get usage from cache
        cache_key = f"tool_budget:{self.record.id}:{self.field.id}"
        current_usage = await sync_to_async(cache.get)(cache_key, {})
        
        # Check each tool budget
        for tool, limit in self.config.tool_budget.items():
            used = current_usage.get(tool, 0)
            if used >= limit:
                logger.warning(f"Tool budget exceeded for {tool}: {used}/{limit}")
                return False
        
        return True
    
    async def _update_tool_usage(self, tool_name: str):
        """Update tool usage tracking"""
        if not self.config.tool_budget:
            return
        
        cache_key = f"tool_budget:{self.record.id}:{self.field.id}"
        
        # Get current usage
        current_usage = await sync_to_async(cache.get)(cache_key, {})
        
        # Increment usage
        current_usage[tool_name] = current_usage.get(tool_name, 0) + 1
        
        # Cache for 24 hours
        await sync_to_async(cache.set)(cache_key, current_usage, 86400)
    
    async def _get_cached_result(self) -> Optional[Any]:
        """Get cached result if available and not expired"""
        if self.config.cache_duration <= 0:
            return None
        
        cache_key = self._get_cache_key()
        return await sync_to_async(cache.get)(cache_key)
    
    async def _cache_result(self, result: Any) -> None:
        """Cache the AI result"""
        if self.config.cache_duration > 0:
            cache_key = self._get_cache_key()
            await sync_to_async(cache.set)(cache_key, result, self.config.cache_duration)
    
    def _get_cache_key(self) -> str:
        """Generate cache key based on record data and configuration"""
        # Include relevant field values in cache key
        relevant_data = {}
        if self.config.update_triggers:
            for field_name in self.config.update_triggers:
                relevant_data[field_name] = self.record.data.get(field_name)
        else:
            relevant_data = self.record.data
        
        # Create hash of relevant data
        data_hash = hashlib.md5(json.dumps(relevant_data, sort_keys=True).encode()).hexdigest()
        
        return f"ai_field:{self.record.pipeline.id}:{self.field.id}:{data_hash}"
    
    async def _log_usage(self, result: Any) -> None:
        """Log AI usage for monitoring and billing"""
        usage_data = {
            'tenant_id': self.tenant.id if self.tenant else None,
            'tenant_name': self.tenant.name if self.tenant else None,
            'field_id': self.field.id,
            'field_name': self.field.name,
            'record_id': self.record.id,
            'pipeline_id': self.record.pipeline.id,
            'model': self.config.ai_model,
            'tools_used': self.config.allowed_tools if self.config.enable_tools else [],
            'timestamp': timezone.now().isoformat(),
            'result_type': self.config.output_type,
            'success': result != self.config.fallback_value,
            'cache_hit': False  # This would be set appropriately
        }
        
        logger.info(f"AI field usage: {json.dumps(usage_data)}")
        
        # Record usage cost for tenant billing (simplified cost calculation)
        if self.tenant and result != self.config.fallback_value:
            # Estimate cost based on model and tokens (simplified)
            estimated_cost = self._estimate_usage_cost()
            if estimated_cost > 0:
                await sync_to_async(self.tenant.record_ai_usage)(estimated_cost)
    
    def _estimate_usage_cost(self) -> float:
        """Estimate usage cost based on model and approximate token usage"""
        # Simplified cost estimation - in production, use actual token counts from API response
        model = self.config.ai_model
        
        # Approximate pricing (per 1000 tokens) as of 2024
        pricing = {
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
            'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002},
        }
        
        if model not in pricing:
            return 0.01  # Default small cost
        
        # Estimate tokens (very rough approximation)
        estimated_input_tokens = len(self._build_context()) / 4  # ~4 chars per token
        estimated_output_tokens = 100  # Assume 100 tokens output
        
        cost = (
            (estimated_input_tokens / 1000) * pricing[model]['input'] +
            (estimated_output_tokens / 1000) * pricing[model]['output']
        )
        
        # Add tool usage cost if applicable
        if self.config.enable_tools:
            cost += 0.005  # Additional cost for tool usage
        
        return round(cost, 6)


class AIFieldManager:
    """Manager for batch processing AI fields"""
    
    @staticmethod
    async def process_record_ai_fields(record, force_update: bool = False) -> Dict[str, Any]:
        """Process all AI fields for a record"""
        ai_fields = await sync_to_async(list)(record.pipeline.fields.filter(is_ai_field=True))
        results = {}
        
        if not ai_fields:
            return results
        
        # Process fields concurrently
        tasks = []
        for field in ai_fields:
            processor = AIFieldProcessor(field, record)
            tasks.append(processor.process_field())
        
        try:
            # Execute all AI field processing concurrently
            field_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect results
            for field, result in zip(ai_fields, field_results):
                if isinstance(result, Exception):
                    logger.error(f"AI field {field.name} failed: {result}")
                    results[field.slug] = field.ai_config.get('fallback_value')
                else:
                    results[field.slug] = result
                    
        except Exception as e:
            logger.error(f"Batch AI processing failed: {e}")
            # Return fallback values for all fields
            for field in ai_fields:
                results[field.slug] = field.ai_config.get('fallback_value')
        
        return results
    
    @staticmethod
    async def trigger_field_updates(record, changed_fields: List[str]) -> None:
        """Trigger AI field updates based on changed fields"""
        ai_fields = await sync_to_async(list)(record.pipeline.fields.filter(is_ai_field=True))
        
        fields_to_update = []
        for field in ai_fields:
            try:
                config = AIGeneratedFieldConfig(**field.ai_config)
                
                # Check if any trigger fields were changed
                if not config.update_triggers:  # Update on any change
                    fields_to_update.append(field)
                else:
                    for trigger_field in config.update_triggers:
                        if trigger_field in changed_fields:
                            fields_to_update.append(field)
                            break
            except Exception as e:
                logger.error(f"Invalid AI config for field {field.name}: {e}")
                continue
        
        # Update triggered fields
        if fields_to_update:
            update_results = {}
            for field in fields_to_update:
                try:
                    processor = AIFieldProcessor(field, record)
                    result = await processor.process_field()
                    update_results[field.slug] = result
                except Exception as e:
                    logger.error(f"Failed to update AI field {field.name}: {e}")
                    update_results[field.slug] = field.ai_config.get('fallback_value')
            
            # Update record data
            record.data.update(update_results)
            await sync_to_async(record.save)(update_fields=['data'])
            
            logger.info(f"Updated {len(update_results)} AI fields for record {record.id}")


# Convenience function for synchronous usage
def process_ai_fields_sync(record, force_update: bool = False) -> Dict[str, Any]:
    """Synchronous wrapper for AI field processing"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        AIFieldManager.process_record_ai_fields(record, force_update)
    )