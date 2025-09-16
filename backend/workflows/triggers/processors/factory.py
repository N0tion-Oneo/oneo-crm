"""
Factory for creating trigger processors
"""
import logging
from typing import Dict, Optional
from .base import BaseTriggerProcessor, StandardTriggerProcessor
from ...models import WorkflowTriggerType

logger = logging.getLogger(__name__)


class TriggerProcessorFactory:
    """Factory for creating and managing trigger processors"""
    
    def __init__(self):
        self._processors: Dict[str, BaseTriggerProcessor] = {}
        self._register_processors()
    
    def _register_processors(self):
        """Register all trigger processors"""
        
        # Register standard processors for all trigger types
        trigger_types = [
            WorkflowTriggerType.MANUAL,
            WorkflowTriggerType.RECORD_CREATED,
            WorkflowTriggerType.RECORD_UPDATED,
            WorkflowTriggerType.RECORD_DELETED,
            # WorkflowTriggerType.FIELD_CHANGED,  # Deprecated - use RECORD_UPDATED
            WorkflowTriggerType.SCHEDULED,
            WorkflowTriggerType.WEBHOOK,
            WorkflowTriggerType.API_ENDPOINT,
            WorkflowTriggerType.FORM_SUBMITTED,
            WorkflowTriggerType.EMAIL_RECEIVED,
            WorkflowTriggerType.MESSAGE_RECEIVED,
            # WorkflowTriggerType.STATUS_CHANGED,  # Deprecated - use RECORD_UPDATED
            WorkflowTriggerType.DATE_REACHED,
            WorkflowTriggerType.CONDITION_MET,
            WorkflowTriggerType.PIPELINE_STAGE_CHANGED,
            WorkflowTriggerType.ENGAGEMENT_THRESHOLD,
            WorkflowTriggerType.WORKFLOW_COMPLETED
        ]
        
        for trigger_type in trigger_types:
            processor = StandardTriggerProcessor(trigger_type)
            self.register_processor(processor)
        
        # Register specialized processors if available
        try:
            self._register_specialized_processors()
        except ImportError:
            logger.info("Specialized processors not available, using standard processors")
    
    def _register_specialized_processors(self):
        """Register specialized processors that override standard ones"""
        
        # Try to import specialized processors
        try:
            from .record_processors import RecordEventProcessor, FieldChangeProcessor
            from .communication_processors import CommunicationProcessor
            from .engagement_processors import EngagementAnalysisProcessor
            from .date_processors import DateBasedProcessor
            from .workflow_processors import WorkflowOrchestrationProcessor
            
            # Register specialized processors
            specialized_processors = [
                RecordEventProcessor(),
                FieldChangeProcessor(),
                CommunicationProcessor(),
                EngagementAnalysisProcessor(),
                DateBasedProcessor(),
                WorkflowOrchestrationProcessor()
            ]
            
            for processor in specialized_processors:
                self.register_processor(processor)
                
        except ImportError as e:
            logger.debug(f"Could not import specialized processors: {e}")
    
    def register_processor(self, processor: BaseTriggerProcessor):
        """Register a trigger processor"""
        
        processor_type = processor.get_supported_trigger_type()
        if processor_type:
            self._processors[processor_type] = processor
            logger.debug(f"Registered processor for trigger type: {processor_type}")
        else:
            logger.warning(f"Processor {processor.__class__.__name__} has no trigger type")
    
    def get_processor(self, trigger_type: str) -> Optional[BaseTriggerProcessor]:
        """Get processor for a trigger type"""
        
        processor = self._processors.get(trigger_type)
        if not processor:
            logger.warning(f"No processor found for trigger type: {trigger_type}")
            # Return a standard processor as fallback
            processor = StandardTriggerProcessor(trigger_type)
            self.register_processor(processor)
        
        return processor
    
    def get_all_processors(self) -> Dict[str, BaseTriggerProcessor]:
        """Get all registered processors"""
        return self._processors.copy()