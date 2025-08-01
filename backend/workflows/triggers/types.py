"""
Type definitions and data structures for the trigger system
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from datetime import datetime


class TriggerCategory(Enum):
    """Categories for organizing triggers"""
    USER_INITIATED = "user_initiated"
    DATA_EVENTS = "data_events"
    TIME_BASED = "time_based"
    EXTERNAL_INTEGRATION = "external_integration"
    COMMUNICATION = "communication"
    USER_INTERACTION = "user_interaction"
    LOGIC_BASED = "logic_based"
    ANALYTICS_BASED = "analytics_based"
    WORKFLOW_ORCHESTRATION = "workflow_orchestration"


class TriggerPriority(Enum):
    """Priority levels for trigger processing"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TriggerType:
    """Basic trigger type information"""
    code: str
    display_name: str
    description: str
    category: TriggerCategory


@dataclass
class TriggerDefinition:
    """Complete definition of a trigger type with metadata and validation"""
    trigger_type: str
    display_name: str
    description: str
    category: TriggerCategory
    config_schema: Dict[str, Any]
    required_fields: List[str] = field(default_factory=list)
    supports_conditions: bool = True
    supports_rate_limiting: bool = True
    supports_time_conditions: bool = True
    is_real_time: bool = True
    priority: TriggerPriority = TriggerPriority.MEDIUM
    examples: List[Dict[str, Any]] = field(default_factory=list)
    handler_class: str = ""
    processor_class: str = ""
    validator_class: str = ""


@dataclass
class TriggerContext:
    """Context information for trigger processing"""
    trigger_id: str
    workflow_id: str
    tenant_schema: str
    triggered_by_user_id: Optional[str] = None
    execution_id: Optional[str] = None
    parent_execution_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TriggerResult:
    """Result of trigger processing"""
    success: bool
    trigger_id: str
    workflow_id: str
    execution_id: Optional[str] = None
    message: str = ""
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: int = 0
    created_at: Optional[datetime] = None


@dataclass
class TriggerValidationResult:
    """Result of trigger configuration validation"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class TriggerEvent:
    """Event data structure for trigger processing"""
    event_type: str
    event_data: Dict[str, Any]
    source: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RateLimitConfig:
    """Rate limiting configuration for triggers"""
    max_per_minute: int = 10
    max_per_hour: int = 100
    max_per_day: int = 1000
    burst_allowance: int = 5
    cooldown_seconds: int = 60


@dataclass
class ConditionConfig:
    """Configuration for trigger conditions"""
    field: str
    operator: str
    value: Any
    data_type: str = "string"
    case_sensitive: bool = False
    allow_missing: bool = False
    default_value: Any = None