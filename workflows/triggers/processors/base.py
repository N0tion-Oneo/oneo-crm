"""
Base classes for trigger processors
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any
from ..types import TriggerContext, TriggerResult

logger = logging.getLogger(__name__)


class BaseTriggerProcessor(ABC):
    """Base class for all trigger processors"""
    
    def __init__(self):
        self.processor_type = ""
        self.processor_name = self.__class__.__name__
    
    @abstractmethod
    async def process(self, trigger, context: TriggerContext) -> TriggerResult:
        """Process the trigger and return result"""
        pass
    
    async def prepare_data(self, trigger, context: TriggerContext) -> Dict[str, Any]:
        """Prepare data for workflow execution (override if needed)"""
        return context.metadata
    
    async def post_process(self, trigger, context: TriggerContext, result: TriggerResult) -> TriggerResult:
        """Post-process the result (override if needed)"""
        return result
    
    def get_supported_trigger_type(self) -> str:
        """Get the trigger type this processor supports"""
        return self.processor_type


class StandardTriggerProcessor(BaseTriggerProcessor):
    """Standard processor for most trigger types"""
    
    def __init__(self, trigger_type: str):
        super().__init__()
        self.processor_type = trigger_type
    
    async def process(self, trigger, context: TriggerContext) -> TriggerResult:
        """Standard processing logic"""
        
        try:
            # Prepare data for workflow
            processed_data = await self.prepare_data(trigger, context)
            
            # Standard validation
            if await self._validate_processing_conditions(trigger, context):
                
                result = TriggerResult(
                    success=True,
                    trigger_id=context.trigger_id,
                    workflow_id=context.workflow_id,
                    message=f"Trigger {trigger.trigger_type} processed successfully",
                    data=processed_data
                )
            else:
                result = TriggerResult(
                    success=False,
                    trigger_id=context.trigger_id,
                    workflow_id=context.workflow_id,
                    error="Processing conditions not met"
                )
            
            # Post-process if needed
            return await self.post_process(trigger, context, result)
            
        except Exception as e:
            logger.error(f"Error processing trigger {context.trigger_id}: {e}")
            return TriggerResult(
                success=False,
                trigger_id=context.trigger_id,
                workflow_id=context.workflow_id,
                error=str(e)
            )
    
    async def _validate_processing_conditions(self, trigger, context: TriggerContext) -> bool:
        """Validate that processing conditions are met"""
        
        # Check rate limiting
        if not await self._check_rate_limits(trigger):
            return False
        
        # Check time conditions
        if not await self._check_time_conditions(trigger):
            return False
        
        return True
    
    async def _check_rate_limits(self, trigger) -> bool:
        """Check if trigger is within rate limits"""
        
        from django.utils import timezone
        from datetime import timedelta
        from asgiref.sync import sync_to_async
        
        now = timezone.now()
        
        # Check per-minute limit
        if trigger.max_executions_per_minute > 0:
            one_minute_ago = now - timedelta(minutes=1)
            from ...models import WorkflowExecution
            recent_count = await sync_to_async(
                WorkflowExecution.objects.filter(
                    workflow=trigger.workflow,
                    started_at__gte=one_minute_ago
                ).count
            )()
            if recent_count >= trigger.max_executions_per_minute:
                logger.warning(f"Trigger {trigger.id} minute rate limit exceeded")
                return False
        
        return True
    
    async def _check_time_conditions(self, trigger) -> bool:
        """Check time-based conditions"""
        
        time_conditions = trigger.trigger_config.get('time_conditions', {})
        if not time_conditions:
            return True
        
        from django.utils import timezone
        from datetime import datetime
        
        now = timezone.now()
        
        # Check time range
        if 'start_time' in time_conditions and 'end_time' in time_conditions:
            try:
                start_time = datetime.strptime(time_conditions['start_time'], '%H:%M').time()
                end_time = datetime.strptime(time_conditions['end_time'], '%H:%M').time()
                current_time = now.time()
                
                if start_time <= end_time:
                    if not (start_time <= current_time <= end_time):
                        return False
                else:  # Time range crosses midnight
                    if not (current_time >= start_time or current_time <= end_time):
                        return False
            except ValueError:
                logger.warning(f"Invalid time format in trigger {trigger.id}")
        
        # Check days of week
        if 'days_of_week' in time_conditions:
            allowed_days = time_conditions['days_of_week']
            if now.weekday() not in allowed_days:
                return False
        
        return True