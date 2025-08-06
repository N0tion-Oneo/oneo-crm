"""
AI Integration Layer - Unified AI Processing for Pipelines and Workflows
Handles AI field processing, workflow AI nodes, and cross-system AI operations
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import AIJob
from .tasks import process_ai_job
from .processors import AIFieldProcessor

logger = logging.getLogger(__name__)
User = get_user_model()


class AIIntegrationManager:
    """
    Unified AI manager for pipelines and workflows
    Handles AI field processing and workflow AI operations
    """
    
    def __init__(self, tenant, user: User):
        self.tenant = tenant
        self.user = user
        self.processor = AIFieldProcessor(tenant, user)
    
    async def process_field_ai(
        self, 
        field_config: Dict[str, Any], 
        record_data: Dict[str, Any],
        field_name: str,
        record_id: Optional[int] = None,
        pipeline_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process AI for a pipeline field
        
        Args:
            field_config: AI field configuration from field.ai_config
            record_data: Complete record data for context
            field_name: Name of the field being processed
            record_id: ID of the record (for tracking)
            pipeline_id: ID of the pipeline (for context)
            
        Returns:
            Dict with AI processing result
        """
        
        try:
            # Create AI job for tracking
            job = await self._create_field_job(
                field_config, record_data, field_name, record_id, pipeline_id
            )
            
            # For real-time fields, process immediately
            if field_config.get('realtime', False):
                return await self._process_field_realtime(job, field_config, record_data)
            
            # For async fields, queue for background processing
            else:
                return await self._queue_field_processing(job)
                
        except Exception as e:
            logger.error(f"AI field processing failed for {field_name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'value': field_config.get('fallback_value', '')
            }
    
    async def process_workflow_ai(
        self,
        workflow_context: Dict[str, Any],
        ai_node_config: Dict[str, Any],
        execution_id: str
    ) -> Dict[str, Any]:
        """
        Process AI for workflow nodes
        
        Args:
            workflow_context: Current workflow execution context
            ai_node_config: AI node configuration
            execution_id: Workflow execution ID
            
        Returns:
            Dict with AI processing result for workflow
        """
        
        try:
            # Create AI job for workflow tracking
            job = await self._create_workflow_job(
                ai_node_config, workflow_context, execution_id
            )
            
            # Process workflow AI (always async to not block workflow execution)
            return await self._queue_workflow_processing(job)
            
        except Exception as e:
            logger.error(f"Workflow AI processing failed for execution {execution_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'output': ai_node_config.get('fallback_output', {})
            }
    
    async def _create_field_job(
        self, 
        field_config: Dict[str, Any], 
        record_data: Dict[str, Any],
        field_name: str,
        record_id: Optional[int],
        pipeline_id: Optional[str]
    ) -> AIJob:
        """Create AI job for field processing"""
        
        # Prepare prompt with record context
        prompt_template = field_config.get('prompt', '')
        
        # Replace field placeholders in prompt
        context_data = record_data.copy()
        context_data['field_name'] = field_name
        
        job_data = {
            'job_type': 'field_generation',
            'ai_provider': 'openai',
            'model_name': field_config.get('model', 'gpt-4o-mini'),
            'prompt_template': prompt_template,
            'ai_config': {
                'temperature': field_config.get('temperature', 0.3),
                'max_tokens': field_config.get('max_tokens', 1000),
                'output_type': field_config.get('output_type', 'text'),
                'tools': field_config.get('tools', [])
            },
            'input_data': {
                'content': str(record_data),  # Full record context
                'field_name': field_name,
                'record_id': record_id,
                'pipeline_id': pipeline_id,
                'context': context_data
            },
            'created_by': self.user,
            'status': 'pending'
        }
        
        # Add pipeline/record references
        if pipeline_id:
            job_data['ai_config']['pipeline_id'] = pipeline_id
        if record_id:
            job_data['ai_config']['record_id'] = record_id
        
        return AIJob.objects.create(**job_data)
    
    async def _create_workflow_job(
        self,
        ai_node_config: Dict[str, Any],
        workflow_context: Dict[str, Any],
        execution_id: str
    ) -> AIJob:
        """Create AI job for workflow processing"""
        
        job_data = {
            'job_type': ai_node_config.get('job_type', 'classification'),
            'ai_provider': 'openai',
            'model_name': ai_node_config.get('model', 'gpt-4o-mini'),
            'prompt_template': ai_node_config.get('prompt', ''),
            'ai_config': {
                'temperature': ai_node_config.get('temperature', 0.3),
                'max_tokens': ai_node_config.get('max_tokens', 1000),
                'output_type': ai_node_config.get('output_type', 'json'),
                'tools': ai_node_config.get('tools', [])
            },
            'input_data': {
                'workflow_context': workflow_context,
                'execution_id': execution_id,
                'node_id': ai_node_config.get('node_id'),
                'content': str(workflow_context)  # Context for AI
            },
            'created_by': self.user,
            'status': 'pending'
        }
        
        return AIJob.objects.create(**job_data)
    
    async def _process_field_realtime(
        self, 
        job: AIJob, 
        field_config: Dict[str, Any], 
        record_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process field AI in real-time (synchronous)"""
        
        try:
            # Prepare field configuration for processor
            processor_config = {
                'prompt_template': job.prompt_template,
                'model': job.model_name,
                'temperature': job.ai_config.get('temperature', 0.3),
                'max_tokens': job.ai_config.get('max_tokens', 1000),
                'tools': job.ai_config.get('tools', [])
            }
            
            # Process with the unified AI processor
            result = await self.processor._process_with_tools(processor_config, job.input_data)
            
            # Update job with results
            job.status = 'completed'
            job.output_data = result
            job.tokens_used = result.get('usage', {}).get('total_tokens', 0)
            job.cost_cents = result.get('cost_cents', 0)
            job.completed_at = timezone.now()
            job.save()
            
            return {
                'success': True,
                'value': result.get('content', ''),
                'job_id': job.id,
                'tokens_used': job.tokens_used,
                'cost_cents': job.cost_cents
            }
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.save()
            
            return {
                'success': False,
                'error': str(e),
                'value': field_config.get('fallback_value', ''),
                'job_id': job.id
            }
    
    async def _queue_field_processing(self, job: AIJob) -> Dict[str, Any]:
        """Queue field AI processing for background execution"""
        
        try:
            # Queue the job using our new AI task system
            from django.db import connection
            tenant_schema = connection.tenant.schema_name
            
            task_result = process_ai_job.delay(job.id, tenant_schema)
            
            # Store task ID for tracking
            job.ai_config['celery_task_id'] = task_result.id
            job.save(update_fields=['ai_config'])
            
            logger.info(f"Queued field AI job {job.id} with task {task_result.id}")
            
            return {
                'success': True,
                'queued': True,
                'job_id': job.id,
                'task_id': task_result.id,
                'status': 'pending'
            }
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.save()
            
            return {
                'success': False,
                'error': str(e),
                'job_id': job.id
            }
    
    async def _queue_workflow_processing(self, job: AIJob) -> Dict[str, Any]:
        """Queue workflow AI processing for background execution"""
        # Same as field processing but with workflow-specific logging
        return await self._queue_field_processing(job)
    
    def get_job_status(self, job_id: int) -> Dict[str, Any]:
        """Get status of an AI job"""
        try:
            job = AIJob.objects.get(id=job_id)
            
            result = {
                'job_id': job_id,
                'status': job.status,
                'created_at': job.created_at,
                'updated_at': job.updated_at
            }
            
            if job.status == 'completed':
                result.update({
                    'output': job.output_data,
                    'tokens_used': job.tokens_used,
                    'cost_cents': job.cost_cents,
                    'completed_at': job.completed_at
                })
            elif job.status == 'failed':
                result.update({
                    'error': job.error_message,
                    'retry_count': job.retry_count
                })
            
            return result
            
        except AIJob.DoesNotExist:
            return {'error': 'Job not found', 'job_id': job_id}


# Convenience functions for pipeline integration
def trigger_field_ai_processing(record, changed_fields: List[str], user: User) -> Dict[str, Any]:
    """
    Trigger AI processing for fields affected by record changes
    Called from pipeline record save signals
    """
    
    from django.db import connection
    tenant = connection.tenant
    
    # Initialize AI manager
    ai_manager = AIIntegrationManager(tenant, user)
    
    # Get AI fields that should be triggered
    ai_fields = record.pipeline.fields.filter(
        field_type='ai_generated'
    )
    
    triggered_jobs = []
    
    for field in ai_fields:
        try:
            field_config = field.ai_config or {}
            
            # Check if this field should be triggered by the changed fields
            trigger_fields = field_config.get('trigger_fields', [])
            
            should_trigger = False
            if not trigger_fields:  # No specific triggers = trigger on any change
                should_trigger = True
            else:
                # Check if any trigger fields were changed
                should_trigger = any(trigger in changed_fields for trigger in trigger_fields)
            
            if should_trigger:
                # Queue AI field processing via Celery (async)
                try:
                    from ai.tasks import process_ai_job
                    from ai.models import AIJob
                    
                    # Create AI job for this field
                    ai_job = AIJob.objects.create(
                        job_type='field_generation',
                        pipeline=record.pipeline,
                        record_id=record.id,
                        field_name=field.name,
                        ai_provider='openai',  # Default provider
                        model_name=field_config.get('model', 'gpt-4o-mini'),
                        prompt_template=field_config.get('prompt', ''),
                        ai_config=field_config,
                        input_data={'record_data': record.data},
                        status='pending',
                        created_by=user
                    )
                    
                    # Queue the job for processing
                    process_ai_job.delay(ai_job.id, tenant.schema_name)
                    
                    triggered_jobs.append({
                        'field': field.name,
                        'job_id': str(ai_job.id),
                        'status': 'queued'
                    })
                    
                    logger.info(f"AI job {ai_job.id} queued for field {field.name}")
                    
                except Exception as e:
                    logger.error(f"Failed to queue AI job for field {field.name}: {e}")
                    triggered_jobs.append({
                        'field': field.name,
                        'error': str(e)
                    })
                    
        except Exception as e:
            logger.error(f"Error processing field {field.name}: {e}")
    
    # All AI processing is now async via Celery - no immediate record updates
    logger.info(f"Queued AI processing for {len(triggered_jobs)} fields in record {record.id}")
    
    return {
        'triggered_jobs': triggered_jobs,
        'record_id': record.id,
        'processing_mode': 'async'
    }


# Workflow integration function (for future use)
async def process_workflow_ai_node(workflow_context: Dict[str, Any], ai_node_config: Dict[str, Any], user: User) -> Dict[str, Any]:
    """
    Process AI for workflow nodes
    Called from workflow engine AI nodes
    """
    
    from django.db import connection
    tenant = connection.tenant
    
    ai_manager = AIIntegrationManager(tenant, user)
    
    return await ai_manager.process_workflow_ai(
        workflow_context=workflow_context,
        ai_node_config=ai_node_config,
        execution_id=workflow_context.get('execution_id', 'unknown')
    )
