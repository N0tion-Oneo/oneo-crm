"""
Base classes for trigger validators
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any
from ..types import TriggerContext, TriggerValidationResult

logger = logging.getLogger(__name__)


class BaseTriggerValidator(ABC):
    """Base class for all trigger validators"""
    
    def __init__(self):
        self.validator_type = ""
        self.validator_name = self.__class__.__name__
    
    @abstractmethod
    async def validate(self, trigger, context: TriggerContext) -> TriggerValidationResult:
        """Validate trigger configuration and context"""
        pass
    
    async def validate_config(self, trigger_config: Dict[str, Any]) -> TriggerValidationResult:
        """Validate trigger configuration (override if needed)"""
        return TriggerValidationResult(valid=True)
    
    async def validate_conditions(self, trigger) -> TriggerValidationResult:
        """Validate trigger conditions (override if needed)"""
        return TriggerValidationResult(valid=True)
    
    def get_supported_trigger_type(self) -> str:
        """Get the trigger type this validator supports"""
        return self.validator_type


class StandardTriggerValidator(BaseTriggerValidator):
    """Standard validator for most trigger types"""
    
    def __init__(self, trigger_type: str):
        super().__init__()
        self.validator_type = trigger_type
    
    async def validate(self, trigger, context: TriggerContext) -> TriggerValidationResult:
        """Standard validation logic"""
        
        errors = []
        warnings = []
        suggestions = []
        
        try:
            # Validate basic trigger properties
            if not trigger.name:
                errors.append("Trigger name is required")
            
            if not trigger.workflow:
                errors.append("Trigger must be associated with a workflow")
            
            if not trigger.workflow.status == 'active':
                warnings.append("Associated workflow is not active")
            
            # Validate configuration
            config_result = await self.validate_config(trigger.trigger_config)
            errors.extend(config_result.errors)
            warnings.extend(config_result.warnings)
            suggestions.extend(config_result.suggestions)
            
            # Validate conditions
            conditions_result = await self.validate_conditions(trigger)
            errors.extend(conditions_result.errors)
            warnings.extend(conditions_result.warnings)
            suggestions.extend(conditions_result.suggestions)
            
            # Validate rate limiting settings
            if trigger.max_executions_per_minute <= 0:
                suggestions.append("Consider setting a reasonable per-minute execution limit")
            
            if trigger.max_executions_per_hour <= 0:
                suggestions.append("Consider setting a reasonable per-hour execution limit")
            
            return TriggerValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Error validating trigger {trigger.id}: {e}")
            return TriggerValidationResult(
                valid=False,
                errors=[f"Validation error: {str(e)}"]
            )
    
    async def validate_config(self, trigger_config: Dict[str, Any]) -> TriggerValidationResult:
        """Validate trigger configuration"""
        
        errors = []
        warnings = []
        suggestions = []
        
        # Basic config validation
        if not isinstance(trigger_config, dict):
            errors.append("Trigger configuration must be a dictionary")
            return TriggerValidationResult(valid=False, errors=errors)
        
        # Check for time conditions
        if 'time_conditions' in trigger_config:
            time_conditions = trigger_config['time_conditions']
            
            if 'start_time' in time_conditions and 'end_time' in time_conditions:
                try:
                    from datetime import datetime
                    datetime.strptime(time_conditions['start_time'], '%H:%M')
                    datetime.strptime(time_conditions['end_time'], '%H:%M')
                except ValueError:
                    errors.append("Invalid time format in time_conditions (use HH:MM)")
            
            if 'days_of_week' in time_conditions:
                days = time_conditions['days_of_week']
                if not isinstance(days, list) or not all(isinstance(d, int) and 0 <= d <= 6 for d in days):
                    errors.append("days_of_week must be a list of integers 0-6 (Monday=0)")
        
        return TriggerValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    async def validate_conditions(self, trigger) -> TriggerValidationResult:
        """Validate trigger conditions"""
        
        errors = []
        warnings = []
        suggestions = []
        
        conditions = trigger.conditions
        if not conditions:
            return TriggerValidationResult(valid=True)
        
        for i, condition in enumerate(conditions):
            # Validate condition structure
            if not isinstance(condition, dict):
                errors.append(f"Condition {i+1} must be a dictionary")
                continue
            
            if 'field' not in condition:
                errors.append(f"Condition {i+1} must have a 'field' property")
            
            if 'operator' not in condition:
                warnings.append(f"Condition {i+1} missing operator, will default to '=='")
            else:
                valid_operators = ['==', '!=', '>', '>=', '<', '<=', 'contains', 'not_contains', 
                                 'starts_with', 'ends_with', 'in', 'not_in', 'regex', 'exists', 'not_exists']
                if condition['operator'] not in valid_operators:
                    errors.append(f"Condition {i+1} has invalid operator: {condition['operator']}")
            
            if 'value' not in condition and condition.get('operator') not in ['exists', 'not_exists']:
                warnings.append(f"Condition {i+1} missing value")
        
        return TriggerValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )