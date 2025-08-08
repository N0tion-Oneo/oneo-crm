"""
AI Processing Engine for Oneo CRM
Implements sophisticated AI field processing with tenant isolation and tool integration
"""
import time
import json
import hashlib
import logging
from typing import Dict, Any, Optional, List
from django.core.cache import cache
from django.utils import timezone
from django.db import models
from ai.models import AIJob, AIUsageAnalytics
from ai.config import ai_config

logger = logging.getLogger(__name__)


class BudgetExceededException(Exception):
    """Raised when AI processing budget is exceeded"""
    pass


class UsageLimitExceededException(Exception):
    """Raised when tenant usage limit is exceeded"""
    pass


class AIFieldProcessor:
    """
    Context-aware AI field processor with tool integration
    Implements the sophisticated processing described in frontend plan lines 849-879
    """
    
    def __init__(self, tenant, user):
        self.tenant = tenant
        self.user = user
        
        # Get tenant-specific API key (no global fallback)
        self.api_key = self._get_tenant_api_key()
        if not self.api_key:
            raise ValueError(f"No OpenAI API key configured for tenant {tenant.name}")
        
        logger.info(f"AI processor initialized for tenant {tenant.name}")
    
    def _get_tenant_api_key(self):
        """Get tenant-specific OpenAI API key"""
        if hasattr(self.tenant, 'get_ai_config'):
            ai_config = self.tenant.get_ai_config()
            return ai_config.get('openai_api_key')
        return None
    
    async def process_field(self, record, field_config, context_data=None):
        """Process AI field with context building and tool integration"""
        
        # Build dynamic context with {field_name} syntax
        context = self._build_context(record, field_config, context_data)
        
        # Preprocess template to handle {*} expansion with excluded fields respect
        template = field_config.get('prompt_template', '')
        processed_template = self._preprocess_template(template, record, field_config)
        
        # Update field config with processed template
        processed_field_config = field_config.copy()
        processed_field_config['prompt_template'] = processed_template
        
        # Check cache first
        cache_key = self._generate_cache_key(processed_field_config, context)
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            logger.info(f"Cache hit for field processing: {cache_key}")
            return cached_result
        
        # Check budget before processing
        await self._check_budget(processed_field_config)
        
        # Process with appropriate AI tools
        start_time = time.time()
        result = await self._process_with_tools(processed_field_config, context)
        processing_time = (time.time() - start_time) * 1000  # ms
        
        # Cache result with TTL
        cache_ttl = processed_field_config.get('cache_ttl', 3600)
        await self._cache_result(cache_key, result, cache_ttl)
        
        # Track usage for billing
        await self._track_usage(result, processing_time, processed_field_config)
        
        logger.info(f"AI field processed successfully in {processing_time:.2f}ms")
        return result
    
    def _build_context(self, record, field_config, context_data):
        """Build context with {field_name} expansion, respecting excluded fields"""
        context = context_data or {}
        
        # Get excluded fields from configuration
        excluded_fields = field_config.get('excluded_fields', [])
        
        # Add record field data to context, excluding sensitive fields
        for field_name, field_value in record.data.items():
            if field_name not in excluded_fields:
                context[field_name] = field_value
            else:
                logger.debug(f"Excluding field '{field_name}' from AI context")
        
        # Add metadata
        context.update({
            'record_id': record.id,
            'pipeline_name': record.pipeline.name,
            'tenant_name': self.tenant.name,
            'current_user': self.user.get_full_name() or self.user.email
        })
        
        excluded_count = len(excluded_fields)
        included_count = len([k for k in record.data.keys() if k not in excluded_fields])
        logger.info(f"Built context with {included_count} fields, excluded {excluded_count} sensitive fields for record {record.id}")
        
        return context
    
    def _preprocess_template(self, template, record, field_config):
        """Preprocess template to handle {*} expansion with excluded fields filtering"""
        if '{*}' not in template:
            return template
        
        # Get excluded fields from configuration
        excluded_fields = field_config.get('excluded_fields', [])
        
        # Build a formatted representation of all non-excluded record fields
        field_lines = []
        for field_name, field_value in record.data.items():
            # Skip excluded fields
            if field_name in excluded_fields:
                logger.debug(f"Excluding field '{field_name}' from {{*}} expansion")
                continue
                
            if field_value is not None and field_value != '':
                # Convert complex objects to readable string representation
                if isinstance(field_value, dict):
                    # Format dictionary nicely
                    if 'amount' in field_value and 'currency' in field_value:
                        # Special formatting for currency objects
                        field_value = f"{field_value.get('amount', 0)} {field_value.get('currency', 'USD')}"
                    else:
                        # General dictionary formatting
                        field_value = ', '.join(f"{k}: {v}" for k, v in field_value.items())
                elif isinstance(field_value, list):
                    field_value = ', '.join(str(item) for item in field_value)
                else:
                    # Escape any problematic characters for template formatting
                    field_value = str(field_value).replace('{', '{{').replace('}', '}}')
                
                field_lines.append(f"{field_name}: {field_value}")
        
        # Replace {*} with the formatted field data
        all_fields_text = '\n'.join(field_lines) if field_lines else 'No data available'
        
        # Escape any remaining braces in the final text to avoid format conflicts
        all_fields_text = all_fields_text.replace('{', '{{').replace('}', '}}')
        processed_template = template.replace('{*}', all_fields_text)
        
        excluded_count = len(excluded_fields)
        included_count = len(field_lines)
        logger.info(f"Preprocessed template: replaced {{*}} with {included_count} fields, excluded {excluded_count} fields")
        return processed_template
    
    def _process_with_openai(self, field_config, context):
        """Unified OpenAI processing (works in both sync and async contexts)"""
        tools = field_config.get('tools', [])
        model = field_config.get('model', 'gpt-4o-mini')
        temperature = field_config.get('temperature', 0.7)
        max_tokens = field_config.get('max_tokens', 2000)
        
        # Prepare input text and system instructions
        system_message = field_config.get('system_message')
        input_text = field_config['prompt_template'].format(**context)
        
        # Tool configuration - only if tools are enabled
        tools_config = []
        enable_tools = field_config.get('enable_tools', False)
        
        if enable_tools and 'web_search' in tools:
            # Web search (working correctly)
            tools_config.append({"type": "web_search_preview"})
        
        if enable_tools and 'code_interpreter' in tools:
            # Code interpreter for data analysis and Python execution
            tools_config.append({
                "type": "code_interpreter",
                "container": {"type": "auto"}
            })
        
        if enable_tools and 'dall_e' in tools:
            # DALL-E for image generation
            tools_config.append({"type": "image_generation"})
        
        if enable_tools and 'file_search' in tools:
            # File search for document analysis (requires vector store IDs)
            tools_config.append({
                "type": "file_search",
                "vector_store_ids": []  # Empty array for now - would need actual vector store IDs
            })
        
        # Make actual OpenAI API call
        try:
            import openai
            
            # Create client with API key
            client = openai.OpenAI(
                api_key=self.api_key,
                timeout=30.0
            )
            
            # Prepare API call parameters for new responses API
            api_params = {
                "model": model,
                "input": input_text
            }
            
            # Add system instructions if specified
            if system_message:
                api_params["instructions"] = system_message
            
            # Add tools if specified
            if tools_config:
                api_params["tools"] = tools_config
                logger.info(f"🔧 Sending tools to OpenAI: {tools_config}")
            else:
                logger.info(f"🔧 No tools configured")
                
            logger.info(f"🚀 API params: {api_params}")
            
            # Make the API call using new responses.create method
            response = client.responses.create(**api_params)
            
            # Extract result from new API format
            # The response.output_text contains the complete formatted response including tool results
            content = response.output_text if hasattr(response, 'output_text') else ""
            
            # For debugging: log tool usage details
            if hasattr(response, 'output') and response.output:
                tool_calls = [
                    output.type for output in response.output 
                    if hasattr(output, 'type') and 'call' in output.type
                ]
                if tool_calls:
                    logger.info(f"🛠️ Tool calls executed: {tool_calls}")
                    
                # Count actual code executions
                code_calls = [
                    output for output in response.output 
                    if hasattr(output, 'type') and output.type == 'code_interpreter_call'
                ]
                if code_calls:
                    logger.info(f"🐍 Code interpreter executed {len(code_calls)} code block(s)")
            
            # Handle usage data with fallback for new API
            total_tokens = 0
            prompt_tokens = 0
            completion_tokens = 0
            
            try:
                usage = getattr(response, 'usage', None)
                if usage:
                    if hasattr(usage, 'total_tokens'):
                        total_tokens = usage.total_tokens or 0
                        prompt_tokens = getattr(usage, 'prompt_tokens', 0) or 0
                        completion_tokens = getattr(usage, 'completion_tokens', 0) or 0
                    elif isinstance(usage, dict):
                        total_tokens = usage.get('total_tokens', 0)
                        prompt_tokens = usage.get('prompt_tokens', 0)
                        completion_tokens = usage.get('completion_tokens', 0)
                else:
                    # Fallback calculation for new API
                    prompt_tokens = len(input_text) // 4
                    completion_tokens = len(content) // 4
                    total_tokens = prompt_tokens + completion_tokens
            except Exception as usage_error:
                logger.warning(f"Usage parsing failed: {usage_error}, using fallback calculation")
                prompt_tokens = len(input_text) // 4
                completion_tokens = len(content) // 4
                total_tokens = prompt_tokens + completion_tokens
            
            # Create usage object for cost calculation
            usage_obj = type('Usage', (), {
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': total_tokens
            })()
            
            result = {
                'content': content,
                'tool_calls': len(tools_config),
                'usage': {
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': total_tokens,
                },
                'model': model,
                'temperature': temperature,
                'cost_cents': self._calculate_cost(usage_obj, model)
            }
            
            logger.info(f"OpenAI API call successful - Content: {len(content)} chars, Tokens: {total_tokens}, Cost: {result['cost_cents']} cents")
            return result
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            # Fallback to simulated response if API fails
            result = {
                'content': f"AI processing unavailable (using {model}): {str(e)[:100]}",
                'tool_calls': len(tools_config),
                'usage': {
                    'prompt_tokens': len(input_text) // 4 if 'input_text' in locals() else 100,
                    'completion_tokens': 100,
                    'total_tokens': (len(input_text) // 4 if 'input_text' in locals() else 100) + 100
                },
                'model': model,
                'temperature': temperature,
                'cost_cents': 5,
                'error': str(e)
            }
            return result
    
    # Async wrapper for the unified method
    async def _process_with_tools(self, field_config, context):
        """Async wrapper for unified OpenAI processing"""
        return self._process_with_openai(field_config, context)
    
    def _calculate_cost(self, usage, model):
        """Calculate cost in cents based on token usage and model"""
        # OpenAI pricing (approximate, as of 2025)
        model_costs = {
            'gpt-4.1-mini': {'input': 0.15, 'output': 0.6},  # per 1M tokens
            'gpt-4.1': {'input': 30, 'output': 60},
            'gpt-4o': {'input': 5, 'output': 15},
            'gpt-4o-mini': {'input': 0.15, 'output': 0.6},
            'gpt-3.5-turbo': {'input': 0.5, 'output': 1.5},
            'o3': {'input': 60, 'output': 120},
            'o3-mini': {'input': 3, 'output': 12}
        }
        
        costs = model_costs.get(model, {'input': 1, 'output': 2})  # Default costs
        
        # Calculate cost in dollars per million tokens
        input_cost = (usage.prompt_tokens / 1_000_000) * costs['input']
        output_cost = (usage.completion_tokens / 1_000_000) * costs['output']
        total_cost_dollars = input_cost + output_cost
        
        # Convert to cents
        return int(total_cost_dollars * 100)
    
    async def _check_budget(self, field_config):
        """Check budget constraints before processing"""
        budget_limit = field_config.get('budget_limit_cents', 1000)
        current_usage = await self._get_current_usage()
        
        if current_usage >= budget_limit:
            raise BudgetExceededException(f"AI budget limit exceeded: {current_usage} >= {budget_limit}")
    
    async def _get_current_usage(self):
        """Get current usage for the tenant"""
        from django.db.models import Sum
        from datetime import datetime, timedelta
        
        # Get usage for current month
        start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        usage = AIUsageAnalytics.objects.filter(
            created_at__gte=start_of_month
        ).aggregate(
            total_cost=Sum('cost_cents')
        )
        
        return usage['total_cost'] or 0
    
    def _generate_cache_key(self, field_config, context):
        """Generate cache key for AI processing"""
        # Create hash of config and context for caching
        cache_data = {
            'prompt_template': field_config.get('prompt_template'),
            'model': field_config.get('model'),
            'temperature': field_config.get('temperature'),
            'context': context
        }
        
        hash_string = hashlib.md5(json.dumps(cache_data, sort_keys=True).encode()).hexdigest()
        return f"ai_field_process:{self.tenant.id}:{hash_string}"
    
    async def _get_cached_result(self, cache_key):
        """Get cached result if available"""
        return cache.get(cache_key)
    
    async def _cache_result(self, cache_key, result, ttl):
        """Cache processing result"""
        cache.set(cache_key, result, ttl)
    
    async def _track_usage(self, result, processing_time, field_config):
        """Track usage for billing and analytics"""
        usage = result.get('usage', {})
        tokens_used = usage.get('total_tokens', 0)
        
        # Calculate cost (rough estimate - $0.01 per 1000 tokens)
        cost_cents = int((tokens_used / 1000) * 1)  # 1 cent per 1000 tokens
        
        # Create usage analytics record
        AIUsageAnalytics.objects.create(
            user=self.user,
            ai_provider=field_config.get('provider', 'openai'),
            model_name=field_config.get('model', 'gpt-4o-mini'),
            operation_type='field_generation',
            tokens_used=tokens_used,
            cost_cents=cost_cents,
            response_time_ms=int(processing_time),
            created_at=timezone.now(),
            date=timezone.now().date()
        )
        
        logger.info(f"Usage tracked: {tokens_used} tokens, ${cost_cents/100:.2f}")
    
    def process_field_sync(self, record, field_config, context_data=None):
        """Synchronous version of process_field for Celery tasks"""
        
        # Build dynamic context with {field_name} syntax
        context = self._build_context(record, field_config, context_data)
        
        # Preprocess template to handle {*} expansion with excluded fields respect
        template = field_config.get('prompt_template', '')
        processed_template = self._preprocess_template(template, record, field_config)
        
        # Update field config with processed template
        processed_field_config = field_config.copy()
        processed_field_config['prompt_template'] = processed_template
        
        # Skip cache for now in sync version to avoid async issues
        logger.info(f"Processing field synchronously: {processed_template[:50]}...")
        
        # Process with OpenAI API (sync version)
        result = self._process_with_openai_sync(processed_field_config, context)
        
        return result
    
    def _process_with_openai_sync(self, field_config, context):
        """Synchronous wrapper for unified OpenAI processing"""
        return self._process_with_openai(field_config, context)


class AIJobManager:
    """
    Comprehensive AI job management for all 6 job types
    Implements job processing with cost tracking, retry logic, and performance monitoring
    """
    
    JOB_PROCESSORS = {
        'field_generation': 'ai.processors.FieldGenerationProcessor',
        'summarization': 'ai.processors.SummarizationProcessor',
        'classification': 'ai.processors.ClassificationProcessor', 
        'sentiment_analysis': 'ai.processors.SentimentAnalysisProcessor',
        'embedding_generation': 'ai.processors.EmbeddingProcessor',
        'semantic_search': 'ai.processors.SemanticSearchProcessor'
    }
    
    def __init__(self, tenant):
        self.tenant = tenant
    
    async def create_job(self, job_type, config, user, **kwargs):
        """Create and queue AI job with full tracking"""
        
        # Validate job type
        if job_type not in self.JOB_PROCESSORS:
            raise ValueError(f"Unknown job type: {job_type}")
        
        # Check tenant AI limits
        await self._check_tenant_limits()
        
        # Create job record
        job = AIJob.objects.create(
            job_type=job_type,
            ai_provider=config.get('provider', 'openai'),
            model_name=config.get('model', 'gpt-4.1-mini'),
            prompt_template=config.get('prompt_template', ''),
            ai_config=config,
            input_data=config.get('input_data', {}),
            created_by=user,
            status='pending',
            **kwargs
        )
        
        # Queue for processing (would integrate with Celery in production)
        logger.info(f"Created AI job {job.id} of type {job_type}")
        
        return job
    
    async def process_job(self, job):
        """Process AI job with retry logic and cost tracking"""
        
        try:
            job.status = 'processing'
            job.save()
            
            # Get processor class (would dynamically import in production)
            processor = self._get_processor(job.job_type)
            
            # Track start time
            start_time = time.time()
            
            # Process job based on type
            result = await self._process_by_type(job, processor)
            
            # Calculate metrics
            processing_time = (time.time() - start_time) * 1000  # ms
            tokens_used = result.get('usage', {}).get('total_tokens', 0)
            cost_cents = self._calculate_cost(tokens_used, job.model_name)
            
            # Update job
            job.output_data = result
            job.tokens_used = tokens_used
            job.cost_cents = cost_cents
            job.processing_time_ms = int(processing_time)
            job.status = 'completed'
            job.completed_at = timezone.now()
            job.save()
            
            # Update tenant usage
            await self._update_tenant_usage(cost_cents)
            
            # Create analytics record
            await self._create_analytics_record(job)
            
            logger.info(f"Job {job.id} completed successfully in {processing_time:.2f}ms")
            
        except Exception as e:
            # Handle failure with retry logic
            await self._handle_job_failure(job, str(e))
    
    async def _check_tenant_limits(self):
        """Check tenant usage limits"""
        if hasattr(self.tenant, 'ai_usage_limit'):
            usage_limit = self.tenant.ai_usage_limit or 10000  # cents
            current_usage = self.tenant.ai_current_usage or 0
            
            if current_usage >= usage_limit:
                raise UsageLimitExceededException("Tenant AI usage limit exceeded")
    
    def _get_processor(self, job_type):
        """Get processor for job type (simplified)"""
        # In production, would dynamically import processor classes
        return f"MockProcessor_{job_type}"
    
    async def _process_by_type(self, job, processor):
        """Process job based on type"""
        # Simplified processing - would implement actual AI calls
        return {
            'content': f"Processed {job.job_type} job",
            'usage': {
                'prompt_tokens': 50,
                'completion_tokens': 100,
                'total_tokens': 150
            },
            'model': job.model_name,
            'job_id': job.id
        }
    
    def _calculate_cost(self, tokens_used, model_name):
        """Calculate cost based on tokens and model"""
        # Simplified cost calculation
        cost_per_1k_tokens = 1  # 1 cent per 1000 tokens
        return int((tokens_used / 1000) * cost_per_1k_tokens)
    
    async def _update_tenant_usage(self, cost_cents):
        """Update tenant usage tracking"""
        if hasattr(self.tenant, 'ai_current_usage'):
            self.tenant.ai_current_usage = (self.tenant.ai_current_usage or 0) + cost_cents
            self.tenant.save(update_fields=['ai_current_usage'])
    
    async def _create_analytics_record(self, job):
        """Create analytics record for job"""
        AIUsageAnalytics.objects.create(
            user=job.created_by,
            ai_provider=job.ai_provider,
            model_name=job.model_name,
            operation_type=job.job_type,
            tokens_used=job.tokens_used,
            cost_cents=job.cost_cents,
            response_time_ms=job.processing_time_ms,
            pipeline=job.pipeline,
            record_id=job.record_id,
            created_at=job.completed_at,
            date=job.completed_at.date()
        )
    
    async def _handle_job_failure(self, job, error_message):
        """Handle job failure with retry logic"""
        job.error_message = error_message
        job.status = 'failed'
        
        if job.can_retry():
            job.retry_count += 1
            job.status = 'pending'  # Will be retried
            logger.warning(f"Job {job.id} failed, retrying (attempt {job.retry_count})")
        else:
            logger.error(f"Job {job.id} failed permanently: {error_message}")
        
        job.save()