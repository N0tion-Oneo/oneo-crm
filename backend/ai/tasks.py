"""
Celery tasks for AI processing - Async job execution
Handles all AI job types with proper tenant isolation and error handling
"""

import logging
import asyncio
from typing import Dict, Any
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.utils import schema_context
from django.db import transaction

from .models import AIJob, AIUsageAnalytics
from .processors import AIFieldProcessor

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, name='ai.tasks.process_ai_job', max_retries=3, default_retry_delay=60)
def process_ai_job(self, job_id: int, tenant_schema: str) -> Dict[str, Any]:
    """
    Process AI job asynchronously with proper tenant isolation
    
    Args:
        job_id: ID of the AI job to process
        tenant_schema: Tenant schema name for multi-tenant isolation
    
    Returns:
        Dict containing processing results
    """
    
    try:
        # Set tenant context for multi-tenant isolation
        with schema_context(tenant_schema):
            # Get the job
            try:
                job = AIJob.objects.get(id=job_id)
            except AIJob.DoesNotExist:
                logger.error(f"AI Job {job_id} not found in tenant {tenant_schema}")
                return {'error': 'Job not found', 'job_id': job_id}
            
            # Check if job is already processed
            if job.status in ['completed', 'failed', 'cancelled']:
                logger.warning(f"Job {job_id} already in final state: {job.status}")
                return {'status': job.status, 'job_id': job_id}
            
            # Update job status to processing
            job.status = 'processing'
            job.save(update_fields=['status', 'updated_at'])
            
            # Get actual tenant object (not FakeTenant from connection)
            from tenants.models import Tenant
            try:
                tenant = Tenant.objects.get(schema_name=tenant_schema)
            except Tenant.DoesNotExist:
                logger.error(f"Tenant with schema {tenant_schema} not found")
                job.status = 'failed'
                job.error_message = f"Tenant {tenant_schema} not found"
                job.save(update_fields=['status', 'error_message', 'updated_at'])
                return {'error': 'Tenant not found', 'job_id': job_id}
            
            # Initialize AI processor
            processor = AIFieldProcessor(tenant, job.created_by)
            
            # Get the actual record object for context building
            from pipelines.models import Record
            try:
                record = Record.objects.get(id=job.record_id, pipeline=job.pipeline)
            except Record.DoesNotExist:
                logger.error(f"Record {job.record_id} not found for AI job {job_id}")
                job.status = 'failed'
                job.error_message = f"Record {job.record_id} not found"
                job.save(update_fields=['status', 'error_message', 'updated_at'])
                return {'error': 'Record not found', 'job_id': job_id}
            
            # Prepare field configuration from job data
            field_config = {
                'prompt_template': job.prompt_template,
                'model': job.model_name,
                'temperature': job.ai_config.get('temperature', 0.3),
                'max_tokens': job.ai_config.get('max_tokens', 1000),
                'tools': job.ai_config.get('allowed_tools', []),  # Map allowed_tools to tools
                'enable_tools': job.ai_config.get('enable_tools', False),
                'system_message': job.ai_config.get('system_message'),
                'output_type': job.ai_config.get('output_type', 'text'),
                'cache_ttl': job.ai_config.get('cache_duration', 3600)  # Map cache_duration to cache_ttl
            }
            
            # Debug: log the tools configuration
            logger.info(f"🔧 Job {job_id} tools mapping:")
            logger.info(f"  - ai_config.allowed_tools: {job.ai_config.get('allowed_tools', [])}")
            logger.info(f"  - ai_config.tools: {job.ai_config.get('tools', [])}")
            logger.info(f"  - enable_tools: {job.ai_config.get('enable_tools', False)}")
            logger.info(f"  - field_config.tools: {field_config.get('tools', [])}")
            logger.info(f"  - field_config.enable_tools: {field_config.get('enable_tools', False)}")
            
            # Prepare context from input data (optional additional context)
            context_data = job.input_data.get('additional_context', {})
            
            logger.info(f"Processing AI job {job_id} - Type: {job.job_type}, Model: {job.model_name}")
            
            # Record start time
            start_time = timezone.now()
            
            # Process the AI job
            try:
                # Use synchronous version of processor for Celery worker
                result = processor.process_field_sync(record, field_config, context_data)
                
                # Ensure we got actual content, not a fallback
                if result.get('error') and 'processing unavailable' in result.get('content', ''):
                    logger.warning(f"AI processing returned fallback content: {result.get('error')}")
                    # Still proceed - the job completed, just with fallback content
                    
                logger.info(f"AI processing result: {len(result.get('content', ''))} chars, error: {result.get('error', 'None')}")
                
                # Calculate processing time
                processing_time = (timezone.now() - start_time).total_seconds() * 1000
                
                # Save result back to the record field
                generated_content = result.get('content', '')
                field_saved = False
                
                if generated_content and job.field_name:
                    # Try to find the correct field name (handle display name vs slug name mismatch)
                    target_field_name = None
                    
                    # First try exact match
                    if job.field_name in record.data:
                        target_field_name = job.field_name
                    else:
                        # Convert display name to slug format and look for matches
                        slug_name = job.field_name.lower().replace(' ', '_')
                        if slug_name in record.data:
                            target_field_name = slug_name
                        else:
                            # Look for partial matches in existing field names
                            for field_name in record.data.keys():
                                if field_name.lower() == slug_name:
                                    target_field_name = field_name
                                    break
                    
                    if target_field_name:
                        try:
                            # Update the record's field data
                            record.data[target_field_name] = generated_content
                            
                            # CRITICAL FIX: Prevent recursive AI processing during AI result save
                            record._skip_ai_processing = True
                            record._skip_broadcast = True  # Also skip WebSocket broadcasts to avoid conflicts
                            
                            record.save(update_fields=['data'])
                            field_saved = True
                            logger.info(f"Saved AI result to record {record.id} field '{target_field_name}' (job field: '{job.field_name}'): {len(generated_content)} chars")
                        except Exception as save_error:
                            logger.error(f"Failed to save AI result to record field '{target_field_name}': {save_error}")
                    else:
                        logger.warning(f"Could not find matching field for '{job.field_name}' in record {record.id}. Available fields: {list(record.data.keys())}")
                        # Continue processing - job completed but couldn't save to field

                # Update job with results
                with transaction.atomic():
                    job.status = 'completed'
                    job.output_data = {
                        'content': generated_content,
                        'usage': result.get('usage', {}),
                        'model': result.get('model', job.model_name),
                        'cost_cents': result.get('cost_cents', 0),
                        'saved_to_field': field_saved
                    }
                    job.tokens_used = result.get('usage', {}).get('total_tokens', 0)
                    job.cost_cents = result.get('cost_cents', 0)
                    job.processing_time_ms = int(processing_time)
                    job.completed_at = timezone.now()
                    job.save()
                
                logger.info(f"AI job {job_id} completed successfully - Tokens: {job.tokens_used}, Cost: {job.cost_cents} cents")
                
                return {
                    'status': 'completed',
                    'job_id': job_id,
                    'content': result.get('content'),
                    'tokens_used': job.tokens_used,
                    'cost_cents': job.cost_cents,
                    'processing_time_ms': job.processing_time_ms
                }
                
            except Exception as processing_error:
                logger.error(f"AI processing failed for job {job_id}: {processing_error}")
                
                # Update job with error
                with transaction.atomic():
                    job.status = 'failed'
                    job.error_message = str(processing_error)
                    job.retry_count += 1
                    job.save()
                
                # Retry if possible
                if job.can_retry():
                    logger.info(f"Retrying job {job_id} (attempt {job.retry_count + 1})")
                    # Retry after delay
                    raise self.retry(exc=processing_error, countdown=60 * (2 ** job.retry_count))
                
                return {
                    'status': 'failed',
                    'job_id': job_id,
                    'error': str(processing_error),
                    'retry_count': job.retry_count
                }
                
    except Exception as e:
        logger.error(f"Critical error processing AI job {job_id}: {e}")
        
        # Try to update job status if possible
        try:
            with schema_context(tenant_schema):
                job = AIJob.objects.get(id=job_id)
                job.status = 'failed'
                job.error_message = f"Critical error: {str(e)}"
                job.save()
        except Exception:
            pass  # If we can't update the job, log and continue
        
        return {
            'status': 'failed',
            'job_id': job_id,
            'error': f"Critical error: {str(e)}"
        }


@shared_task(bind=True, name='ai.tasks.cleanup_old_jobs')
def cleanup_old_jobs(self, days_old: int = 30):
    """
    Clean up old AI jobs to prevent database bloat
    
    Args:
        days_old: Number of days after which to clean up completed jobs
    """
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days_old)
    
    try:
        # Delete old completed jobs
        deleted_count = AIJob.objects.filter(
            status='completed',
            completed_at__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old AI jobs")
        return {'cleaned_jobs': deleted_count}
        
    except Exception as e:
        logger.error(f"Error cleaning up old AI jobs: {e}")
        return {'error': str(e)}


@shared_task(bind=True, name='ai.tasks.retry_failed_jobs')
def retry_failed_jobs(self, tenant_schema: str):
    """
    Retry failed AI jobs that can be retried
    
    Args:
        tenant_schema: Tenant schema to process
    """
    
    try:
        with schema_context(tenant_schema):
            # Find failed jobs that can be retried
            retryable_jobs = AIJob.objects.filter(
                status='failed',
                retry_count__lt=3  # Max retries
            )
            
            retry_count = 0
            for job in retryable_jobs:
                if job.can_retry():
                    # Queue for retry
                    process_ai_job.delay(job.id, tenant_schema)
                    retry_count += 1
            
            logger.info(f"Queued {retry_count} failed jobs for retry in tenant {tenant_schema}")
            return {'retried_jobs': retry_count}
            
    except Exception as e:
        logger.error(f"Error retrying failed jobs: {e}")
        return {'error': str(e)}