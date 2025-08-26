"""
Trigger Manager - Central coordinator for all trigger processing
"""
import asyncio
import logging
import threading
import queue
from typing import Dict, Any, List, Optional, Type
from datetime import datetime
from django.utils import timezone
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

from .types import TriggerContext, TriggerResult, TriggerEvent, TriggerPriority
from .registry import TriggerRegistry
from .handlers.factory import TriggerHandlerFactory
from .processors.factory import TriggerProcessorFactory
from .validators.factory import TriggerValidatorFactory
from ..models import WorkflowTrigger, WorkflowTriggerType, WorkflowStatus

logger = logging.getLogger(__name__)
User = get_user_model()


class TriggerManager:
    """Central manager for all trigger processing with clean separation of concerns"""
    
    def __init__(self):
        self.registry = TriggerRegistry()
        self.handler_factory = TriggerHandlerFactory()
        self.processor_factory = TriggerProcessorFactory()
        self.validator_factory = TriggerValidatorFactory()
        
        # Processing queues by priority (initialized lazily)
        self.priority_queues = None
        self._processors_started = False
        
        # Track original record values for change detection
        self.original_record_values = {}
        
        # Event queue for signal-triggered events
        self.signal_event_queue = queue.Queue()
        self._signal_processor_thread = None
        self._signal_processor_running = False
        
        # Initialize signal handlers
        self._setup_signal_handlers()
        
        # Start background signal processor
        self._start_signal_processor()
    
    def _start_signal_processor(self):
        """Start background thread to process signal events"""
        if not self._signal_processor_running:
            self._signal_processor_running = True
            self._signal_processor_thread = threading.Thread(
                target=self._signal_processor_worker,
                daemon=True,
                name="TriggerSignalProcessor"
            )
            self._signal_processor_thread.start()
            logger.debug("Started trigger signal processor thread")
    
    def _signal_processor_worker(self):
        """Background worker that processes signal events"""
        logger.debug("Trigger signal processor worker started")
        
        while self._signal_processor_running:
            try:
                # Get event from queue (blocking with timeout)
                try:
                    event = self.signal_event_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Process the event asynchronously
                try:
                    # Create new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Run the async processing
                    loop.run_until_complete(self.process_event(event))
                    
                    # Clean up the loop
                    loop.close()
                    
                except Exception as e:
                    logger.error(f"Failed to process event {event.event_type}: {e}")
                finally:
                    # Mark task as done
                    self.signal_event_queue.task_done()
                    
            except Exception as e:
                logger.error(f"Signal processor worker error: {e}")
        
        logger.debug("Trigger signal processor worker stopped")
    
    def stop_signal_processor(self):
        """Stop the background signal processor"""
        if self._signal_processor_running:
            self._signal_processor_running = False
            if self._signal_processor_thread:
                self._signal_processor_thread.join(timeout=5.0)
            logger.info("Stopped trigger signal processor")
    
    def _setup_signal_handlers(self):
        """Setup Django signal handlers for automatic trigger detection"""
        
        @receiver(pre_save, sender='pipelines.Record')
        def capture_original_values(sender, instance, **kwargs):
            """Capture original record values before save"""
            if instance.pk:
                try:
                    from pipelines.models import Record
                    original = Record.objects.get(pk=instance.pk)
                    self.original_record_values[instance.pk] = {
                        'data': original.data.copy() if original.data else {},
                        'status': getattr(original, 'status', None),
                        'title': original.title,
                        'pipeline_id': original.pipeline_id,
                        'updated_at': original.updated_at
                    }
                except Exception as e:
                    logger.debug(f"Could not capture original values: {e}")
        
        @receiver(post_save, sender='pipelines.Record')
        def handle_record_save(sender, instance, created, **kwargs):
            """Handle record save events"""
            try:
                event_type = 'created' if created else 'updated'
                
                # Create trigger event
                event = TriggerEvent(
                    event_type=f'record_{event_type}',
                    event_data={
                        'record': instance,
                        'created': created,
                        'original_values': self.original_record_values.get(instance.pk, {})
                    },
                    source='django_signal',
                    timestamp=timezone.now()
                )
                
                # Queue for background processing
                self.signal_event_queue.put(event)
                
                # Clean up original values
                if not created and instance.pk in self.original_record_values:
                    del self.original_record_values[instance.pk]
                    
            except Exception as e:
                logger.error(f"Failed to handle record save: {e}")
        
        @receiver(post_delete, sender='pipelines.Record')
        def handle_record_delete(sender, instance, **kwargs):
            """Handle record delete events"""
            try:
                event = TriggerEvent(
                    event_type='record_deleted',
                    event_data={'record': instance},
                    source='django_signal',
                    timestamp=timezone.now()
                )
                
                asyncio.create_task(self.process_event(event))
                
            except Exception as e:
                logger.error(f"Failed to handle record delete: {e}")
    
    def _initialize_queues(self):
        """Initialize async queues (called when needed)"""
        if self.priority_queues is None:
            self.priority_queues = {
                TriggerPriority.CRITICAL: asyncio.Queue(),
                TriggerPriority.HIGH: asyncio.Queue(),
                TriggerPriority.MEDIUM: asyncio.Queue(),
                TriggerPriority.LOW: asyncio.Queue()
            }
    
    async def _start_background_processors(self):
        """Start background task processors for each priority queue"""
        if self._processors_started:
            return
            
        self._initialize_queues()
        
        async def process_priority_queue(priority: TriggerPriority):
            """Process triggers from a specific priority queue"""
            queue = self.priority_queues[priority]
            
            while True:
                try:
                    # Get next trigger context from queue
                    context = await queue.get()
                    
                    # Process the trigger
                    result = await self._process_trigger_context(context)
                    
                    # Log result
                    if result.success:
                        logger.info(f"Processed {priority.name} priority trigger: {result.trigger_id}")
                    else:
                        logger.error(f"Failed to process trigger {result.trigger_id}: {result.error}")
                    
                    # Mark task as done
                    queue.task_done()
                    
                except Exception as e:
                    logger.error(f"Error in {priority.name} priority processor: {e}")
                    # Continue processing other triggers
                    continue
        
        # Start processor tasks for each priority level
        for priority in TriggerPriority:
            asyncio.create_task(process_priority_queue(priority))
            
        self._processors_started = True
    
    async def process_event(self, event: TriggerEvent):
        """Process a trigger event and queue relevant triggers"""
        
        # Initialize queues if not already done
        self._initialize_queues()
        
        # Start processors if not already started
        if not self._processors_started:
            await self._start_background_processors()
        
        try:
            # Find matching triggers for this event
            matching_triggers = await self._find_matching_triggers(event)
            
            for trigger in matching_triggers:
                # Create trigger context
                context = TriggerContext(
                    trigger_id=str(trigger.id),
                    workflow_id=str(trigger.workflow.id),
                    tenant_schema=self._get_current_schema(),
                    metadata={
                        'event': event,
                        'trigger_config': trigger.trigger_config,
                        'trigger_type': trigger.trigger_type
                    }
                )
                
                # Get priority for this trigger type
                trigger_def = self.registry.get(trigger.trigger_type)
                priority = trigger_def.priority if trigger_def else TriggerPriority.MEDIUM
                
                # Queue for processing
                await self.priority_queues[priority].put(context)
                
        except Exception as e:
            logger.error(f"Failed to process event {event.event_type}: {e}")
    
    async def _find_matching_triggers(self, event: TriggerEvent) -> List:
        """Find triggers that match the given event"""
        
        # Map event types to trigger types
        event_to_trigger_map = {
            'record_created': WorkflowTriggerType.RECORD_CREATED,
            'record_updated': WorkflowTriggerType.RECORD_UPDATED,
            'record_deleted': WorkflowTriggerType.RECORD_DELETED,
            'field_changed': WorkflowTriggerType.FIELD_CHANGED,
            'email_received': WorkflowTriggerType.EMAIL_RECEIVED,
            'message_received': WorkflowTriggerType.MESSAGE_RECEIVED,
            'form_submitted': WorkflowTriggerType.FORM_SUBMITTED,
            'webhook_received': WorkflowTriggerType.WEBHOOK,
            'api_endpoint_called': WorkflowTriggerType.API_ENDPOINT,
            'workflow_completed': WorkflowTriggerType.WORKFLOW_COMPLETED
        }
        
        trigger_type = event_to_trigger_map.get(event.event_type)
        if not trigger_type:
            return []
        
        # Find active triggers of this type
        triggers = await sync_to_async(list)(
            WorkflowTrigger.objects.filter(
                trigger_type=trigger_type,
                is_active=True,
                workflow__status=WorkflowStatus.ACTIVE
            ).select_related('workflow')
        )
        
        # Filter triggers based on their specific conditions
        matching_triggers = []
        for trigger in triggers:
            if await self._trigger_matches_event(trigger, event):
                matching_triggers.append(trigger)
        
        return matching_triggers
    
    async def _trigger_matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if a specific trigger matches the event"""
        
        try:
            # Get the appropriate handler for this trigger type
            handler = self.handler_factory.get_handler(trigger.trigger_type)
            if not handler:
                logger.warning(f"No handler found for trigger type: {trigger.trigger_type}")
                return False
            
            # Use handler to check if trigger matches
            return await handler.matches_event(trigger, event)
            
        except Exception as e:
            logger.error(f"Error checking trigger match: {e}")
            return False
    
    async def _process_trigger_context(self, context: TriggerContext) -> TriggerResult:
        """Process a trigger context and execute the workflow"""
        
        start_time = timezone.now()
        
        try:
            # Get trigger and workflow
            trigger = await sync_to_async(WorkflowTrigger.objects.select_related('workflow').get)(
                id=context.trigger_id
            )
            
            # Validate trigger configuration
            validator = self.validator_factory.get_validator(trigger.trigger_type)
            if validator:
                validation_result = await validator.validate(trigger, context)
                if not validation_result.valid:
                    return TriggerResult(
                        success=False,
                        trigger_id=context.trigger_id,
                        workflow_id=context.workflow_id,
                        error=f"Validation failed: {'; '.join(validation_result.errors)}",
                        processing_time_ms=self._calculate_processing_time(start_time)
                    )
            
            # Get processor for this trigger type
            processor = self.processor_factory.get_processor(trigger.trigger_type)
            if not processor:
                return TriggerResult(
                    success=False,
                    trigger_id=context.trigger_id,
                    workflow_id=context.workflow_id,
                    error=f"No processor found for trigger type: {trigger.trigger_type}",
                    processing_time_ms=self._calculate_processing_time(start_time)
                )
            
            # Execute trigger processing
            process_result = await processor.process(trigger, context)
            
            if process_result.success:
                # Execute workflow
                execution_id = await self._execute_workflow(trigger, context, process_result.data)
                
                # Update trigger statistics
                await self._update_trigger_stats(trigger, True)
                
                return TriggerResult(
                    success=True,
                    trigger_id=context.trigger_id,
                    workflow_id=context.workflow_id,
                    execution_id=execution_id,
                    message="Trigger processed successfully",
                    data=process_result.data,
                    processing_time_ms=self._calculate_processing_time(start_time),
                    created_at=timezone.now()
                )
            else:
                # Update trigger statistics for failure
                await self._update_trigger_stats(trigger, False)
                
                return TriggerResult(
                    success=False,
                    trigger_id=context.trigger_id,
                    workflow_id=context.workflow_id,
                    error=process_result.error,
                    processing_time_ms=self._calculate_processing_time(start_time)
                )
                
        except Exception as e:
            logger.error(f"Failed to process trigger context: {e}")
            return TriggerResult(
                success=False,
                trigger_id=context.trigger_id,
                workflow_id=context.workflow_id,
                error=str(e),
                processing_time_ms=self._calculate_processing_time(start_time)
            )
    
    async def _execute_workflow(self, trigger, context: TriggerContext, trigger_data: Dict[str, Any]) -> str:
        """Execute the workflow for a processed trigger"""
        
        from ..tasks import execute_workflow_async
        
        # Prepare enhanced trigger data
        enhanced_trigger_data = {
            'trigger_id': str(trigger.id),
            'trigger_type': trigger.trigger_type,
            'trigger_name': trigger.name,
            'context': context.metadata,
            **trigger_data
        }
        
        # Execute workflow asynchronously
        result = execute_workflow_async.delay(
            tenant_schema=context.tenant_schema,
            workflow_id=context.workflow_id,
            trigger_data=enhanced_trigger_data,
            triggered_by_id=context.triggered_by_user_id or trigger.workflow.created_by.id
        )
        
        return str(result.id)
    
    async def _update_trigger_stats(self, trigger, success: bool):
        """Update trigger execution statistics"""
        
        try:
            trigger.execution_count += 1
            trigger.last_triggered_at = timezone.now()
            await sync_to_async(trigger.save)(update_fields=['execution_count', 'last_triggered_at'])
            
            # Log trigger event
            from ..models import WorkflowEvent
            await sync_to_async(WorkflowEvent.objects.create)(
                workflow=trigger.workflow,
                event_type='trigger_executed' if success else 'trigger_failed',
                event_data={
                    'trigger_id': str(trigger.id),
                    'trigger_type': trigger.trigger_type,
                    'success': success
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to update trigger stats: {e}")
    
    def _calculate_processing_time(self, start_time: datetime) -> int:
        """Calculate processing time in milliseconds"""
        return int((timezone.now() - start_time).total_seconds() * 1000)
    
    def _get_current_schema(self) -> str:
        """Get current tenant schema"""
        try:
            from django.db import connection
            return connection.schema_name
        except:
            return 'public'
    
    # Public API methods
    
    async def trigger_manual(self, workflow_id: str, user_id: str, data: Dict[str, Any] = None) -> TriggerResult:
        """Manually trigger a workflow"""
        
        context = TriggerContext(
            trigger_id='manual',
            workflow_id=workflow_id,
            tenant_schema=self._get_current_schema(),
            triggered_by_user_id=user_id,
            metadata={'manual_data': data or {}}
        )
        
        return await self._process_manual_trigger(context)
    
    async def _process_manual_trigger(self, context: TriggerContext) -> TriggerResult:
        """Process a manual trigger"""
        
        start_time = timezone.now()
        
        try:
            # Execute workflow directly for manual triggers
            execution_id = await self._execute_workflow(None, context, context.metadata)
            
            return TriggerResult(
                success=True,
                trigger_id='manual',
                workflow_id=context.workflow_id,
                execution_id=execution_id,
                message="Manual trigger executed successfully",
                processing_time_ms=self._calculate_processing_time(start_time),
                created_at=timezone.now()
            )
            
        except Exception as e:
            return TriggerResult(
                success=False,
                trigger_id='manual',
                workflow_id=context.workflow_id,
                error=str(e),
                processing_time_ms=self._calculate_processing_time(start_time)
            )
    
    async def process_webhook(self, workflow_id: str, payload: Dict[str, Any], headers: Dict[str, str]) -> TriggerResult:
        """Process webhook trigger"""
        
        event = TriggerEvent(
            event_type='webhook_received',
            event_data={
                'payload': payload,
                'headers': headers,
                'workflow_id': workflow_id
            },
            source='webhook',
            timestamp=timezone.now()
        )
        
        await self.process_event(event)
        
        return TriggerResult(
            success=True,
            trigger_id='webhook',
            workflow_id=workflow_id,
            message="Webhook processed successfully"
        )
    
    async def process_api_call(self, endpoint: str, method: str, data: Dict[str, Any]) -> TriggerResult:
        """Process API endpoint trigger"""
        
        event = TriggerEvent(
            event_type='api_endpoint_called',
            event_data={
                'endpoint': endpoint,
                'method': method,
                'data': data
            },
            source='api',
            timestamp=timezone.now()
        )
        
        await self.process_event(event)
        
        return TriggerResult(
            success=True,
            trigger_id='api',
            workflow_id='',
            message="API call processed successfully"
        )
    
    def get_trigger_statistics(self) -> Dict[str, Any]:
        """Get trigger processing statistics"""
        
        return {
            'queue_sizes': {
                priority.name: queue.qsize() 
                for priority, queue in self.priority_queues.items()
            },
            'registered_triggers': len(self.registry.get_all()),
            'active_handlers': len(self.handler_factory._handlers),
            'active_processors': len(self.processor_factory._processors)
        }