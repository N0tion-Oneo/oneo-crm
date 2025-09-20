"""
Trigger Registry - Centralized management and discovery of trigger types
"""
import logging
from typing import Dict, List, Optional, Type, Any
from .types import TriggerDefinition, TriggerCategory, TriggerPriority, TriggerValidationResult
from ..models import WorkflowTriggerType

logger = logging.getLogger(__name__)


class TriggerRegistry:
    """Registry for all workflow trigger types with validation and metadata"""
    
    def __init__(self):
        self.triggers: Dict[str, TriggerDefinition] = {}
        self._register_all_triggers()
    
    def _register_all_triggers(self):
        """Register all available trigger types"""
        self._register_core_triggers()
        self._register_enhanced_triggers()
    
    def _register_core_triggers(self):
        """Register core workflow triggers"""
        
        # Manual triggers
        self.register(TriggerDefinition(
            trigger_type=WorkflowTriggerType.MANUAL,
            display_name="Manual Trigger",
            description="Manually trigger workflow execution by user action",
            category=TriggerCategory.USER_INITIATED,
            config_schema={
                "type": "object",
                "properties": {
                    "require_confirmation": {"type": "boolean", "default": False},
                    "allowed_user_types": {"type": "array", "items": {"type": "string"}},
                    "confirmation_message": {"type": "string"},
                    "button_text": {"type": "string", "default": "Execute Workflow"}
                }
            },
            required_fields=[],
            supports_conditions=False,
            supports_time_conditions=False,
            priority=TriggerPriority.HIGH,
            handler_class="ManualTriggerHandler",
            examples=[
                {
                    "name": "Admin Manual Trigger",
                    "config": {
                        "require_confirmation": True,
                        "confirmation_message": "Are you sure you want to execute this workflow?",
                        "allowed_user_types": ["admin", "manager"]
                    }
                }
            ]
        ))
        
        # Record-based triggers
        self.register(TriggerDefinition(
            trigger_type=WorkflowTriggerType.RECORD_CREATED,
            display_name="Record Created",
            description="Trigger when a new record is created in specified pipelines",
            category=TriggerCategory.DATA_EVENTS,
            config_schema={
                "type": "object",
                "properties": {
                    "pipeline_ids": {"type": "array", "items": {"type": "string"}},
                    "record_types": {"type": "array", "items": {"type": "string"}},
                    "field_filters": {"type": "object"},
                    "delay_seconds": {"type": "integer", "minimum": 0, "default": 0},
                    "batch_processing": {"type": "boolean", "default": False}
                }
            },
            required_fields=[],
            priority=TriggerPriority.HIGH,
            handler_class="RecordEventHandler",
            processor_class="RecordEventProcessor",
            examples=[
                {
                    "name": "New Lead Created",
                    "config": {
                        "pipeline_ids": ["leads"],
                        "field_filters": {"source": "website"}
                    }
                }
            ]
        ))
        
        self.register(TriggerDefinition(
            trigger_type=WorkflowTriggerType.RECORD_UPDATED,
            display_name="Record Updated",
            description="Trigger when an existing record is modified",
            category=TriggerCategory.DATA_EVENTS,
            config_schema={
                "type": "object",
                "properties": {
                    "pipeline_ids": {"type": "array", "items": {"type": "string"}},
                    "watch_all_fields": {"type": "boolean", "default": True},
                    "specific_fields": {"type": "array", "items": {"type": "string"}},
                    "ignore_fields": {"type": "array", "items": {"type": "string"}},
                    "require_actual_changes": {"type": "boolean", "default": True},
                    "minimum_change_threshold": {"type": "number"}
                }
            },
            required_fields=[],
            handler_class="RecordEventHandler",
            processor_class="RecordEventProcessor"
        ))
        
        # DEPRECATED - Use RECORD_UPDATED with specific_fields instead
        # self.register(TriggerDefinition(
        #     trigger_type=WorkflowTriggerType.FIELD_CHANGED,
        #     display_name="Field Changed",
        #     description="Trigger when specific record fields change values",
        #     category=TriggerCategory.DATA_EVENTS,
        #     config_schema={
        #         "type": "object",
        #         "properties": {
        #             "watched_fields": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        #             "change_types": {"type": "array", "items": {"type": "string"}, "default": ["any"]},
        #             "value_filters": {"type": "object"},
        #             "change_threshold": {"type": "number"},
        #             "ignore_null_changes": {"type": "boolean", "default": True}
        #         }
        #     },
        #     required_fields=["watched_fields"],
        #     handler_class="FieldChangeHandler",
        #     processor_class="FieldChangeProcessor"
        # ))
        
        # Time-based triggers
        self.register(TriggerDefinition(
            trigger_type=WorkflowTriggerType.SCHEDULED,
            display_name="Scheduled",
            description="Trigger on a recurring schedule using cron expressions",
            category=TriggerCategory.TIME_BASED,
            config_schema={
                "type": "object",
                "properties": {
                    "cron_expression": {"type": "string"},
                    "timezone": {"type": "string", "default": "UTC"},
                    "max_instances": {"type": "integer", "default": 1},
                    "overlap_policy": {"type": "string", "enum": ["skip", "queue", "replace"], "default": "skip"},
                    "jitter_seconds": {"type": "integer", "default": 0}
                }
            },
            required_fields=["cron_expression"],
            supports_conditions=False,
            supports_time_conditions=False,
            is_real_time=False,
            priority=TriggerPriority.MEDIUM,
            handler_class="ScheduledTriggerHandler",
            processor_class="ScheduledTriggerProcessor"
        ))
        
        # External integration triggers
        self.register(TriggerDefinition(
            trigger_type=WorkflowTriggerType.WEBHOOK,
            display_name="Webhook",
            description="Trigger via external webhook HTTP requests",
            category=TriggerCategory.EXTERNAL_INTEGRATION,
            config_schema={
                "type": "object",
                "properties": {
                    "webhook_secret": {"type": "string"},
                    "require_authentication": {"type": "boolean", "default": True},
                    "allowed_ips": {"type": "array", "items": {"type": "string"}},
                    "signature_header": {"type": "string", "default": "X-Webhook-Signature"},
                    "payload_validation": {"type": "object"},
                    "response_template": {"type": "object"}
                }
            },
            required_fields=[],
            priority=TriggerPriority.HIGH,
            handler_class="WebhookTriggerHandler",
            processor_class="WebhookTriggerProcessor"
        ))
    
    def _register_enhanced_triggers(self):
        """Register enhanced trigger types"""
        
        # API endpoint triggers
        self.register(TriggerDefinition(
            trigger_type=WorkflowTriggerType.API_ENDPOINT,
            display_name="API Endpoint",
            description="Trigger via custom REST API endpoint calls",
            category=TriggerCategory.EXTERNAL_INTEGRATION,
            config_schema={
                "type": "object",
                "properties": {
                    "endpoint_path": {"type": "string"},
                    "http_methods": {"type": "array", "items": {"type": "string"}, "default": ["POST"]},
                    "require_api_key": {"type": "boolean", "default": True},
                    "rate_limit_per_hour": {"type": "integer", "default": 100},
                    "request_validation": {"type": "object"},
                    "response_format": {"type": "string", "enum": ["json", "xml", "plain"], "default": "json"}
                }
            },
            required_fields=["endpoint_path"],
            priority=TriggerPriority.HIGH,
            handler_class="ApiEndpointHandler",
            processor_class="ApiEndpointProcessor"
        ))
        
        # Communication triggers
        self.register(TriggerDefinition(
            trigger_type=WorkflowTriggerType.EMAIL_RECEIVED,
            display_name="Email Received",
            description="Trigger when emails are received on monitored addresses",
            category=TriggerCategory.COMMUNICATION,
            config_schema={
                "type": "object",
                "properties": {
                    "email_addresses": {"type": "array", "items": {"type": "string"}},
                    "sender_filters": {"type": "array", "items": {"type": "string"}},
                    "subject_patterns": {"type": "array", "items": {"type": "string"}},
                    "body_patterns": {"type": "array", "items": {"type": "string"}},
                    "attachment_handling": {"type": "string", "enum": ["ignore", "require", "process"], "default": "ignore"},
                    "auto_reply_template": {"type": "string"}
                }
            },
            required_fields=["email_addresses"],
            handler_class="EmailReceivedHandler",
            processor_class="CommunicationProcessor"
        ))
        
        self.register(TriggerDefinition(
            trigger_type=WorkflowTriggerType.MESSAGE_RECEIVED,
            display_name="Message Received",
            description="Trigger when messages are received via SMS, chat, or other channels",
            category=TriggerCategory.COMMUNICATION,
            config_schema={
                "type": "object",
                "properties": {
                    "channels": {"type": "array", "items": {"type": "string"}},
                    "message_types": {"type": "array", "items": {"type": "string"}},
                    "keyword_triggers": {"type": "array", "items": {"type": "string"}},
                    "sender_patterns": {"type": "array", "items": {"type": "string"}},
                    "business_hours_only": {"type": "boolean", "default": False},
                    "auto_respond": {"type": "boolean", "default": False}
                }
            },
            required_fields=["channels"],
            handler_class="MessageReceivedHandler",
            processor_class="CommunicationProcessor"
        ))
        
        # Form and user interaction triggers
        self.register(TriggerDefinition(
            trigger_type=WorkflowTriggerType.FORM_SUBMITTED,
            display_name="Form Submitted",
            description="Trigger when web forms or surveys are submitted",
            category=TriggerCategory.USER_INTERACTION,
            config_schema={
                "type": "object",
                "properties": {
                    "form_ids": {"type": "array", "items": {"type": "string"}},
                    "required_fields": {"type": "array", "items": {"type": "string"}},
                    "spam_detection": {"type": "boolean", "default": True},
                    "duplicate_prevention": {"type": "boolean", "default": True},
                    "auto_create_record": {"type": "boolean", "default": True},
                    "notification_email": {"type": "string"}
                }
            },
            required_fields=["form_ids"],
            handler_class="FormSubmissionHandler",
            processor_class="FormSubmissionProcessor"
        ))
        
        # Advanced logic-based triggers
        self.register(TriggerDefinition(
            trigger_type=WorkflowTriggerType.CONDITION_MET,
            display_name="Condition Met",
            description="Trigger when complex multi-field conditions are satisfied",
            category=TriggerCategory.LOGIC_BASED,
            config_schema={
                "type": "object",
                "properties": {
                    "conditions": {"type": "array", "items": {"type": "object"}},
                    "evaluation_frequency": {"type": "string", "enum": ["real_time", "hourly", "daily"], "default": "real_time"},
                    "condition_logic": {"type": "string", "enum": ["AND", "OR", "CUSTOM"], "default": "AND"},
                    "custom_logic_expression": {"type": "string"},
                    "reset_on_trigger": {"type": "boolean", "default": True},
                    "persistent_state": {"type": "boolean", "default": False}
                }
            },
            required_fields=["conditions"],
            handler_class="ConditionalTriggerHandler",
            processor_class="ConditionalTriggerProcessor"
        ))
        
        # Date and time-based triggers
        self.register(TriggerDefinition(
            trigger_type=WorkflowTriggerType.DATE_REACHED,
            display_name="Date Reached",
            description="Trigger when specific dates or deadlines are reached",
            category=TriggerCategory.TIME_BASED,
            config_schema={
                "type": "object",
                "properties": {
                    "date_field": {
                        "type": "string",
                        "description": "Field containing the target date (for dynamic dates)"
                    },
                    "target_date": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Static target date (ISO format) - alternative to date_field"
                    },
                    "offset_days": {"type": "integer", "default": 0, "minimum": -365, "maximum": 365},
                    "offset_hours": {"type": "integer", "default": 0, "minimum": -24, "maximum": 24},
                    "business_days_only": {"type": "boolean", "default": False},
                    "timezone": {"type": "string", "default": "UTC"},
                    "reminder_type": {"type": "string", "enum": ["before", "on", "after"], "default": "on"},
                    "recurring": {"type": "boolean", "default": False},
                    "recurrence_pattern": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly", "yearly"],
                        "description": "How often to repeat (if recurring)"
                    },
                    "max_occurrences": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1000,
                        "description": "Maximum number of occurrences (if recurring)"
                    }
                },
                "oneOf": [
                    {"required": ["date_field"]},
                    {"required": ["target_date"]}
                ]
            },
            required_fields=[],  # No strict requirements - oneOf handles validation
            is_real_time=False,
            handler_class="DateReachedHandler",
            processor_class="DateBasedProcessor"
        ))
        
        # Analytics and engagement triggers
        self.register(TriggerDefinition(
            trigger_type=WorkflowTriggerType.ENGAGEMENT_THRESHOLD,
            display_name="Engagement Threshold",
            description="Trigger when contact engagement metrics cross thresholds",
            category=TriggerCategory.ANALYTICS_BASED,
            config_schema={
                "type": "object",
                "properties": {
                    "engagement_score_min": {"type": "number"},
                    "engagement_score_max": {"type": "number"},
                    "activity_count_min": {"type": "integer"},
                    "days_since_last_contact_max": {"type": "integer"},
                    "email_open_rate_min": {"type": "number"},
                    "response_rate_min": {"type": "number"},
                    "evaluation_period_days": {"type": "integer", "default": 30},
                    "reevaluation_frequency": {"type": "string", "enum": ["daily", "weekly"], "default": "daily"}
                }
            },
            required_fields=[],
            is_real_time=False,
            handler_class="EngagementTriggerHandler",
            processor_class="EngagementAnalysisProcessor"
        ))
        
        # Status and stage change triggers
        # DEPRECATED - Use RECORD_UPDATED with update_type='status_only' instead
        # self.register(TriggerDefinition(
        #     trigger_type=WorkflowTriggerType.STATUS_CHANGED,
        #     display_name="Status Changed",
        #     description="Trigger when record status transitions between specific values",
        #     category=TriggerCategory.DATA_EVENTS,
        #     config_schema={
        #         "type": "object",
        #         "properties": {
        #             "from_statuses": {"type": "array", "items": {"type": "string"}},
        #             "to_statuses": {"type": "array", "items": {"type": "string"}},
        #             "pipeline_ids": {"type": "array", "items": {"type": "string"}},
        #             "status_fields": {"type": "array", "items": {"type": "string"}, "default": ["status"]},
        #             "track_duration": {"type": "boolean", "default": True},
        #             "minimum_duration_hours": {"type": "integer", "default": 0}
        #         }
        #     },
        #     required_fields=["to_statuses"],
        #     handler_class="StatusChangeHandler",
        #     processor_class="StatusChangeProcessor"
        # ))
        
        self.register(TriggerDefinition(
            trigger_type=WorkflowTriggerType.PIPELINE_STAGE_CHANGED,
            display_name="Pipeline Stage Changed",
            description="Trigger when records move between pipeline stages",
            category=TriggerCategory.DATA_EVENTS,
            config_schema={
                "type": "object",
                "properties": {
                    "pipeline_ids": {"type": "array", "items": {"type": "string"}},
                    "from_stages": {"type": "array", "items": {"type": "string"}},
                    "to_stages": {"type": "array", "items": {"type": "string"}},
                    "stage_direction": {"type": "string", "enum": ["forward", "backward", "any"], "default": "any"},
                    "track_stage_duration": {"type": "boolean", "default": True},
                    "minimum_stage_time_hours": {"type": "integer", "default": 0}
                }
            },
            required_fields=["pipeline_ids"],
            handler_class="PipelineStageHandler",
            processor_class="PipelineStageProcessor"
        ))
        
        # Workflow orchestration triggers
        self.register(TriggerDefinition(
            trigger_type=WorkflowTriggerType.WORKFLOW_COMPLETED,
            display_name="Workflow Completed",
            description="Trigger when other workflows complete execution",
            category=TriggerCategory.WORKFLOW_ORCHESTRATION,
            config_schema={
                "type": "object",
                "properties": {
                    "source_workflow_ids": {"type": "array", "items": {"type": "string"}},
                    "completion_statuses": {"type": "array", "items": {"type": "string"}, "default": ["success"]},
                    "pass_execution_data": {"type": "boolean", "default": True},
                    "delay_seconds": {"type": "integer", "default": 0},
                    "same_trigger_context": {"type": "boolean", "default": True},
                    "cascade_failures": {"type": "boolean", "default": False}
                }
            },
            required_fields=["source_workflow_ids"],
            priority=TriggerPriority.HIGH,
            handler_class="WorkflowCompletionHandler",
            processor_class="WorkflowOrchestrationProcessor"
        ))
    
    def register(self, trigger_def: TriggerDefinition):
        """Register a trigger definition"""
        self.triggers[trigger_def.trigger_type] = trigger_def
        logger.debug(f"Registered trigger: {trigger_def.trigger_type}")
    
    def get(self, trigger_type: str) -> Optional[TriggerDefinition]:
        """Get trigger definition by type"""
        return self.triggers.get(trigger_type)
    
    def get_all(self) -> Dict[str, TriggerDefinition]:
        """Get all registered triggers"""
        return self.triggers.copy()
    
    def get_by_category(self, category: TriggerCategory) -> Dict[str, TriggerDefinition]:
        """Get triggers filtered by category"""
        return {
            trigger_type: trigger_def
            for trigger_type, trigger_def in self.triggers.items()
            if trigger_def.category == category
        }
    
    def get_categories(self) -> List[TriggerCategory]:
        """Get all trigger categories"""
        return list(set(trigger_def.category for trigger_def in self.triggers.values()))
    
    def get_real_time_triggers(self) -> Dict[str, TriggerDefinition]:
        """Get triggers that process in real-time"""
        return {
            trigger_type: trigger_def
            for trigger_type, trigger_def in self.triggers.items()
            if trigger_def.is_real_time
        }
    
    def get_scheduled_triggers(self) -> Dict[str, TriggerDefinition]:
        """Get triggers that require scheduled processing"""
        return {
            trigger_type: trigger_def
            for trigger_type, trigger_def in self.triggers.items()
            if not trigger_def.is_real_time
        }
    
    def validate_config(self, trigger_type: str, config: Dict[str, Any]) -> TriggerValidationResult:
        """Validate trigger configuration against schema"""
        
        trigger_def = self.get(trigger_type)
        if not trigger_def:
            return TriggerValidationResult(
                valid=False,
                errors=[f"Unknown trigger type: {trigger_type}"]
            )
        
        errors = []
        warnings = []
        suggestions = []
        
        # Check required fields
        for field in trigger_def.required_fields:
            if field not in config:
                errors.append(f"Required field missing: '{field}'")
        
        # Check for deprecated or unknown fields
        schema_properties = trigger_def.config_schema.get('properties', {})
        for field in config:
            if field not in schema_properties:
                warnings.append(f"Unknown configuration field: '{field}'")
        
        # Add suggestions based on trigger type
        if not config and trigger_def.examples:
            suggestions.append("Consider using one of the provided examples as a starting point")
        
        return TriggerValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def get_examples(self, trigger_type: str) -> List[Dict[str, Any]]:
        """Get example configurations for a trigger type"""
        trigger_def = self.get(trigger_type)
        return trigger_def.examples if trigger_def else []
    
    def get_metadata(self, trigger_type: str) -> Dict[str, Any]:
        """Get comprehensive metadata for a trigger type"""
        trigger_def = self.get(trigger_type)
        if not trigger_def:
            return {}
        
        return {
            "trigger_type": trigger_def.trigger_type,
            "display_name": trigger_def.display_name,
            "description": trigger_def.description,
            "category": trigger_def.category.value,
            "priority": trigger_def.priority.value,
            "config_schema": trigger_def.config_schema,
            "required_fields": trigger_def.required_fields,
            "supports_conditions": trigger_def.supports_conditions,
            "supports_rate_limiting": trigger_def.supports_rate_limiting,
            "supports_time_conditions": trigger_def.supports_time_conditions,
            "is_real_time": trigger_def.is_real_time,
            "handler_class": trigger_def.handler_class,
            "processor_class": trigger_def.processor_class,
            "validator_class": trigger_def.validator_class,
            "examples": trigger_def.examples
        }
    
    def search(self, query: str) -> List[TriggerDefinition]:
        """Search triggers by name, description, or category"""
        query_lower = query.lower()
        results = []
        
        for trigger_def in self.triggers.values():
            if (query_lower in trigger_def.display_name.lower() or
                query_lower in trigger_def.description.lower() or
                query_lower in trigger_def.category.value.lower()):
                results.append(trigger_def)
        
        return results