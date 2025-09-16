"""
Factory for creating trigger validators
"""
import logging
from typing import Dict, Optional
from .base import BaseTriggerValidator, StandardTriggerValidator
from ...models import WorkflowTriggerType

logger = logging.getLogger(__name__)


class TriggerValidatorFactory:
    """Factory for creating and managing trigger validators"""
    
    def __init__(self):
        self._validators: Dict[str, BaseTriggerValidator] = {}
        self._register_validators()
    
    def _register_validators(self):
        """Register all trigger validators"""
        
        # Register standard validators for all trigger types
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
            validator = StandardTriggerValidator(trigger_type)
            self.register_validator(validator)
        
        # Register specialized validators if available
        try:
            self._register_specialized_validators()
        except ImportError:
            logger.info("Specialized validators not available, using standard validators")
    
    def _register_specialized_validators(self):
        """Register specialized validators that override standard ones"""
        
        # Try to import specialized validators
        try:
            from .record_validators import RecordEventValidator, FieldChangeValidator
            from .communication_validators import CommunicationValidator
            from .engagement_validators import EngagementAnalysisValidator
            from .date_validators import DateBasedValidator
            from .workflow_validators import WorkflowOrchestrationValidator
            
            # Register specialized validators
            specialized_validators = [
                RecordEventValidator(),
                FieldChangeValidator(),
                CommunicationValidator(),
                EngagementAnalysisValidator(),
                DateBasedValidator(),
                WorkflowOrchestrationValidator()
            ]
            
            for validator in specialized_validators:
                self.register_validator(validator)
                
        except ImportError as e:
            logger.debug(f"Could not import specialized validators: {e}")
    
    def register_validator(self, validator: BaseTriggerValidator):
        """Register a trigger validator"""
        
        validator_type = validator.get_supported_trigger_type()
        if validator_type:
            self._validators[validator_type] = validator
            logger.debug(f"Registered validator for trigger type: {validator_type}")
        else:
            logger.warning(f"Validator {validator.__class__.__name__} has no trigger type")
    
    def get_validator(self, trigger_type: str) -> Optional[BaseTriggerValidator]:
        """Get validator for a trigger type"""
        
        validator = self._validators.get(trigger_type)
        if not validator:
            logger.warning(f"No validator found for trigger type: {trigger_type}")
            # Return a standard validator as fallback
            validator = StandardTriggerValidator(trigger_type)
            self.register_validator(validator)
        
        return validator
    
    def get_all_validators(self) -> Dict[str, BaseTriggerValidator]:
        """Get all registered validators"""
        return self._validators.copy()
    
    async def validate_trigger(self, trigger, context) -> 'TriggerValidationResult':
        """Validate a trigger using appropriate validator"""
        
        validator = self.get_validator(trigger.trigger_type)
        if validator:
            return await validator.validate(trigger, context)
        else:
            from ..types import TriggerValidationResult
            return TriggerValidationResult(
                valid=False,
                errors=[f"No validator available for trigger type: {trigger.trigger_type}"]
            )
    
    def get_validator_info(self, trigger_type: str) -> Dict[str, str]:
        """Get information about a validator"""
        
        validator = self._validators.get(trigger_type)
        if validator:
            return {
                'trigger_type': trigger_type,
                'validator_name': validator.validator_name,
                'validator_class': validator.__class__.__name__
            }
        return {}
    
    def list_supported_trigger_types(self) -> list:
        """List all supported trigger types"""
        return list(self._validators.keys())