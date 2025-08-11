# AI Processing System

Advanced AI integration for Oneo CRM with OpenAI API support, context-aware field processing, and enterprise-grade job management.

## Overview

The AI system provides sophisticated artificial intelligence capabilities for pipeline fields, including:

- **Context-aware AI fields** with full record access
- **Template expansion** with `{*}` placeholder support
- **Multi-tenant isolation** with per-tenant API keys
- **Async processing** via Celery with retry logic
- **Cost tracking** and usage analytics
- **Tool integration** (web search, code interpreter, DALL-E)
- **Security controls** with field exclusion and budget limits

## Architecture

### Core Components

```
ai/
├── models.py           # AIJob, AIUsageAnalytics models
├── processors.py       # AIFieldProcessor with OpenAI integration
├── integrations.py     # AI integration manager and triggers
├── tasks.py           # Celery async processing tasks
├── config.py          # AI configuration management
└── views/             # REST API endpoints
    ├── jobs.py        # AI job management
    └── analytics.py   # Usage analytics
```

### Data Flow

1. **Field Creation** → AI field configured in pipeline
2. **Record Update** → Triggers AI processing via signals
3. **Job Creation** → AIJob created with context and config
4. **Async Processing** → Celery task processes with OpenAI
5. **Result Storage** → AI output saved back to record field

## Models

### AIJob

Tracks all AI processing jobs with full lifecycle management.

```python
class AIJob(models.Model):
    # Job identification
    job_type = models.CharField(max_length=50)  # field_generation, classification, etc.
    pipeline = models.ForeignKey('pipelines.Pipeline')
    record_id = models.BigIntegerField()
    field_name = models.CharField(max_length=255)
    
    # AI configuration
    ai_provider = models.CharField(max_length=50, default='openai')
    model_name = models.CharField(max_length=100)
    prompt_template = models.TextField()
    ai_config = models.JSONField(default=dict)
    input_data = models.JSONField(default=dict)
    
    # Processing results
    status = models.CharField(max_length=20)  # pending, processing, completed, failed
    output_data = models.JSONField(default=dict)
    tokens_used = models.IntegerField(default=0)
    cost_cents = models.IntegerField(default=0)
    processing_time_ms = models.IntegerField(default=0)
    
    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
```

**Status Flow:**
- `pending` → Job created, waiting for processing
- `processing` → Currently being processed by Celery worker
- `completed` → Successfully processed with results
- `failed` → Processing failed (may be retryable)
- `cancelled` → Manually cancelled

### AIUsageAnalytics

Tracks AI usage for billing and analytics.

```python
class AIUsageAnalytics(models.Model):
    user = models.ForeignKey('authentication.User')
    ai_provider = models.CharField(max_length=50)
    model_name = models.CharField(max_length=100)
    operation_type = models.CharField(max_length=50)
    tokens_used = models.IntegerField()
    cost_cents = models.IntegerField()
    response_time_ms = models.IntegerField()
    pipeline = models.ForeignKey('pipelines.Pipeline', null=True)
    record_id = models.BigIntegerField(null=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
```

## AI Field Processing

### Field Configuration

AI fields in pipelines support comprehensive configuration:

```python
ai_config = {
    # Core AI settings
    "model": "gpt-4o-mini",           # OpenAI model
    "temperature": 0.3,               # Creativity level (0-1)
    "max_tokens": 1000,               # Response length limit
    "prompt": "Analyze this record: {*}",  # Template with placeholders
    
    # Tool integration
    "enable_tools": True,
    "allowed_tools": ["web_search", "code_interpreter"],
    
    # Trigger configuration
    "auto_regenerate": True,          # Auto-trigger on changes
    "trigger_fields": ["name", "company"],  # Specific trigger fields
    
    # Security and performance
    "excluded_fields": ["ssn", "password"],  # Exclude sensitive fields
    "cache_duration": 3600,           # Cache TTL in seconds
    "budget_limit_cents": 1000,       # Per-field budget limit
    
    # Output configuration
    "output_type": "text",            # text, json, structured
    "system_message": "You are a helpful assistant"
}
```

### Template System

AI prompts support powerful template expansion:

#### Placeholder Types

- `{field_name}` → Replace with specific field value
- `{*}` → Replace with all non-excluded field data
- `{record_id}` → Record identifier
- `{pipeline_name}` → Pipeline name
- `{tenant_name}` → Tenant name
- `{current_user}` → User who triggered processing

#### Example Templates

```python
# Basic field reference
"Summarize the customer: {name} from {company}"

# Full record analysis
"Analyze this record: {*}"

# Conditional logic
"Based on the status '{status}', recommend next steps for {name}"

# Multi-field context
"Create email for {name} at {email} regarding {subject}: {*}"
```

#### Template Expansion Process

1. **Field Exclusion** → Remove sensitive fields per `excluded_fields`
2. **Value Formatting** → Format complex objects (currency, arrays, etc.)
3. **Placeholder Replacement** → Replace `{*}` with formatted field data
4. **Context Building** → Add metadata (record_id, user, etc.)
5. **Final Processing** → Send to OpenAI with full context

## Processors

### AIFieldProcessor

Core AI processing engine with OpenAI integration.

```python
processor = AIFieldProcessor(tenant, user)
result = processor.process_field_sync(record, field_config, context_data)
```

**Key Features:**
- **Context Building** → Full record context with excluded field filtering
- **Template Preprocessing** → `{*}` expansion with security controls
- **Tool Integration** → Web search, code interpreter, DALL-E, file search
- **Caching Strategy** → Redis-based result caching with TTL
- **Cost Calculation** → Token-based cost tracking by model
- **Error Handling** → Fallback responses and retry logic

### Tool Integration

Supported OpenAI tools:

```python
tools_config = [
    {"type": "web_search_preview"},           # Real-time web search
    {"type": "code_interpreter"},             # Python code execution
    {"type": "image_generation"},             # DALL-E image creation
    {"type": "file_search"}                   # Document analysis
]
```

## Integration Layer

### AIIntegrationManager

Unified manager for AI processing across pipelines and workflows.

```python
from ai.integrations import AIIntegrationManager

ai_manager = AIIntegrationManager(tenant, user)

# Process field AI
result = await ai_manager.process_field_ai(
    field_config=field_config,
    record_data=record.data,
    field_name="ai_summary",
    record_id=record.id,
    pipeline_id=pipeline.id
)

# Process workflow AI
result = await ai_manager.process_workflow_ai(
    workflow_context=context,
    ai_node_config=node_config,
    execution_id="exec_123"
)
```

### Automatic Triggering

AI fields are automatically triggered when records change:

```python
# In pipelines/signals.py or record save operation
from ai.integrations import trigger_field_ai_processing

# Triggered on record save with changed fields
result = trigger_field_ai_processing(
    record=record,
    changed_fields=["name", "company", "status"],
    user=current_user
)

# Returns job information
{
    "triggered_jobs": [
        {
            "field": "ai_summary",
            "job_id": "123",
            "status": "queued_on_commit",
            "celery_task_id": "task_456"
        }
    ],
    "record_id": 789,
    "processing_mode": "async"
}
```

**Trigger Logic:**
1. **Change Detection** → Identify which fields changed
2. **AI Field Discovery** → Find AI fields in pipeline
3. **Trigger Evaluation** → Check if field should be triggered
4. **Job Creation** → Create AIJob with context and config
5. **Async Queuing** → Queue Celery task after transaction commits

## Celery Tasks

### process_ai_job

Main async processing task with multi-tenant isolation.

```python
@shared_task(bind=True, name='ai.tasks.process_ai_job', max_retries=3)
def process_ai_job(self, job_id: int, tenant_schema: str):
    """Process AI job asynchronously with proper tenant isolation"""
```

**Processing Flow:**
1. **Tenant Context** → Set schema context for multi-tenancy
2. **Job Validation** → Verify job exists and is processable
3. **Record Loading** → Get record for context building
4. **Config Preparation** → Prepare field config for processor
5. **AI Processing** → Call OpenAI with full context
6. **Result Storage** → Save results to job and record field
7. **Error Handling** → Retry logic with exponential backoff

**Error Handling:**
- **Retry Logic** → Exponential backoff with max 3 retries
- **Status Tracking** → Update job status throughout process
- **Result Storage** → Save both success and error results
- **Recursive Prevention** → Skip AI processing during result saves

## API Endpoints

### Job Management

```bash
# List AI jobs
GET /api/v1/ai-jobs/

# Get specific job
GET /api/v1/ai-jobs/{id}/

# Retry failed job
POST /api/v1/ai-jobs/{id}/retry/

# Cancel pending job
POST /api/v1/ai-jobs/{id}/cancel/

# Worker health check
GET /api/v1/ai-jobs/worker_health/

# Bulk operations
POST /api/v1/ai-jobs/bulk_retry/
POST /api/v1/ai-jobs/queue_pending/

# System diagnostics
GET /api/v1/ai-jobs/diagnostics/
```

### Usage Analytics

```bash
# Usage statistics
GET /api/v1/ai-analytics/usage/

# Cost breakdown
GET /api/v1/ai-analytics/costs/

# Performance metrics
GET /api/v1/ai-analytics/performance/
```

## Configuration

### Tenant-Specific API Keys

Each tenant can have their own OpenAI API key:

```python
# In tenant model or settings
tenant.ai_config = {
    "openai_api_key": "sk-tenant-specific-key",
    "default_model": "gpt-4o-mini",
    "budget_limit_cents": 10000,  # Monthly budget
    "enable_tools": True
}
```

### System Configuration

```python
# settings.py
AI_CONFIG = {
    'OPENAI_API_KEY': env('OPENAI_API_KEY'),  # Global fallback
    'DEFAULT_MODEL': 'gpt-4o-mini',
    'DEFAULT_TEMPERATURE': 0.3,
    'DEFAULT_MAX_TOKENS': 1000,
    'CACHE_TTL': 3600,
    'MAX_RETRIES': 3,
    'RETRY_DELAY': 60,
    'BUDGET_LIMIT_CENTS': 1000,
}

# Celery configuration for AI tasks
CELERY_TASK_ROUTES = {
    'ai.tasks.process_ai_job': {'queue': 'ai_processing'},
    'ai.tasks.cleanup_old_jobs': {'queue': 'maintenance'},
    'ai.tasks.retry_failed_jobs': {'queue': 'ai_processing'},
}
```

## Security

### Field Exclusion

Prevent sensitive data from being sent to AI:

```python
ai_config = {
    "excluded_fields": [
        "ssn", "social_security_number",
        "password", "token", "api_key",
        "credit_card", "bank_account",
        "private_notes", "confidential"
    ]
}
```

**Exclusion Process:**
1. **Context Building** → Skip excluded fields in context
2. **Template Expansion** → Exclude from `{*}` expansion  
3. **Logging** → Log excluded field count for audit
4. **Validation** → Ensure no sensitive data in prompts

### Budget Controls

Control AI spending per field and tenant:

```python
# Field-level budget
field.ai_config = {
    "budget_limit_cents": 500  # $5 limit per field
}

# Tenant-level budget
tenant.ai_config = {
    "monthly_budget_cents": 10000  # $100 monthly limit
}
```

### Access Control

AI operations respect user permissions:

```python
# Permission checks in API views
class AIJobPermission(BasePermission):
    def has_permission(self, request, view):
        if view.action in ['list', 'retrieve']:
            return permission_manager.has_permission('action', 'ai_features', 'read')
        elif view.action in ['retry', 'cancel']:
            return permission_manager.has_permission('action', 'ai_features', 'create')
```

## Performance

### Caching Strategy

Multi-layer caching for optimal performance:

```python
# Result caching
cache_key = f"ai_field_process:{tenant.id}:{content_hash}"
cache.set(cache_key, result, ttl=3600)

# Context caching
context_key = f"ai_context:{record.id}:{version}"
cache.set(context_key, context, ttl=1800)
```

### Database Optimization

Optimized queries and indexing:

```sql
-- AIJob indexes
CREATE INDEX idx_aijob_status ON ai_aijob(status);
CREATE INDEX idx_aijob_pipeline_record ON ai_aijob(pipeline_id, record_id);
CREATE INDEX idx_aijob_created_at ON ai_aijob(created_at);

-- Usage analytics indexes  
CREATE INDEX idx_usage_date_tenant ON ai_usageanalytics(date, tenant_id);
CREATE INDEX idx_usage_user_date ON ai_usageanalytics(user_id, date);
```

### Monitoring

Comprehensive monitoring and alerting:

```python
# Performance metrics
- Average processing time by model
- Token usage trends
- Cost per operation
- Error rates and retry patterns

# Health checks
- Celery worker status
- OpenAI API connectivity
- Queue depth monitoring  
- Budget utilization tracking
```

## Troubleshooting

### Common Issues

**Jobs Stuck in Pending**
- Check Celery worker status: `celery -A oneo_crm status`
- Verify Redis connectivity: `redis-cli ping`
- Review transaction commit timing

**High Costs**
- Check model usage (GPT-4 vs GPT-4o-mini)
- Review prompt lengths and token usage
- Implement stricter budget limits

**Processing Errors**
- Verify OpenAI API key validity
- Check excluded fields configuration
- Review prompt template syntax

**Context Issues**
- Verify field exclusion settings
- Check record data structure
- Review template placeholder usage

### Debugging Tools

**Management Commands**
```bash
# Check AI job status
python manage.py shell -c "from ai.models import AIJob; print(AIJob.objects.values('status').annotate(count=models.Count('id')))"

# Retry failed jobs
python manage.py shell -c "from ai.tasks import retry_failed_jobs; retry_failed_jobs.delay('tenant_schema')"

# Clean up old jobs
python manage.py shell -c "from ai.tasks import cleanup_old_jobs; cleanup_old_jobs.delay(30)"
```

**API Diagnostics**
```bash
# Worker health
curl -H "Authorization: Bearer $TOKEN" http://tenant.localhost:8000/api/v1/ai-jobs/worker_health/

# System diagnostics
curl -H "Authorization: Bearer $TOKEN" http://tenant.localhost:8000/api/v1/ai-jobs/diagnostics/
```

## Usage Examples

### Basic AI Field

```python
# Pipeline field configuration
field = {
    "name": "AI Summary",
    "slug": "ai_summary", 
    "field_type": "ai_generated",
    "ai_config": {
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "prompt": "Create a brief summary of this customer: {*}",
        "auto_regenerate": True,
        "cache_duration": 3600
    }
}
```

### Advanced AI Field with Tools

```python
field = {
    "name": "Market Research",
    "slug": "market_research",
    "field_type": "ai_generated", 
    "ai_config": {
        "model": "gpt-4o",
        "temperature": 0.5,
        "max_tokens": 2000,
        "prompt": "Research the company {company} in {industry} sector. Find recent news, financial data, and market position: {*}",
        "enable_tools": True,
        "allowed_tools": ["web_search"],
        "trigger_fields": ["company", "industry"],
        "excluded_fields": ["internal_notes", "confidential_data"],
        "budget_limit_cents": 200,
        "cache_duration": 7200
    }
}
```

### Workflow AI Node

```python
ai_node_config = {
    "node_id": "classify_lead",
    "job_type": "classification", 
    "model": "gpt-4o-mini",
    "prompt": "Classify this lead as Hot, Warm, or Cold based on: {workflow_data}",
    "output_type": "json",
    "temperature": 0.1
}

result = await ai_manager.process_workflow_ai(
    workflow_context={"lead_score": 85, "engagement": "high"},
    ai_node_config=ai_node_config,
    execution_id="workflow_123"
)
```

## Best Practices

### Prompt Design

1. **Be Specific** → Clear, detailed instructions
2. **Use Context** → Leverage `{*}` for full record context
3. **Set Boundaries** → Define expected output format
4. **Handle Edge Cases** → Account for missing data

```python
# Good prompt
"Based on the customer data: {*}, generate a personalized email subject line that addresses their specific industry ({industry}) and company size ({employee_count}). Keep it under 60 characters and professional tone."

# Avoid vague prompts
"Write something about this customer: {*}"
```

### Performance Optimization

1. **Choose Right Model** → GPT-4o-mini for simple tasks, GPT-4o for complex
2. **Cache Results** → Set appropriate cache duration
3. **Exclude Unnecessary Fields** → Reduce token usage
4. **Batch Processing** → Group related operations

### Security Guidelines

1. **Field Exclusion** → Always exclude sensitive data
2. **Budget Limits** → Set reasonable spending limits
3. **Access Control** → Restrict AI features by user type
4. **Audit Logging** → Monitor AI usage patterns

### Error Handling

1. **Fallback Values** → Provide meaningful defaults
2. **Retry Logic** → Handle temporary failures gracefully  
3. **User Feedback** → Show processing status to users
4. **Monitor Failures** → Alert on high error rates

## Migration Guide

### From Legacy AI System

If migrating from an older AI implementation:

1. **Update Field Configs** → Migrate to new ai_config format
2. **Update Triggers** → Use new trigger_field_ai_processing
3. **Update Processors** → Replace with AIFieldProcessor
4. **Update Tasks** → Use new Celery task structure

### Database Migration

```python
# Migration to add AI job tracking
class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY idx_aijob_status_created ON ai_aijob(status, created_at);",
            reverse_sql="DROP INDEX idx_aijob_status_created;"
        )
    ]
```

## Contributing

When contributing to the AI system:

1. **Follow Patterns** → Use established processors and managers
2. **Test Thoroughly** → Include unit and integration tests
3. **Document Changes** → Update this README for new features
4. **Security Review** → Ensure no sensitive data exposure
5. **Performance Testing** → Validate under load

---

For questions or issues, see the main project documentation or contact the development team.