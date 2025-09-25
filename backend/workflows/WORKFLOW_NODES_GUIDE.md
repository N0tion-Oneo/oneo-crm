# Workflow Nodes Complete Guide

## 📋 Table of Contents
1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Node Categories](#node-categories)
4. [Node Catalog](#node-catalog)
5. [Development Guidelines](#development-guidelines)
6. [Integration Patterns](#integration-patterns)
7. [Advanced Topics](#advanced-topics)
8. [Implementation Roadmap](#implementation-roadmap)
9. [API Reference](#api-reference)
10. [Examples & Templates](#examples--templates)
11. [Troubleshooting Guide](#troubleshooting-guide)

---

## Executive Summary

The Oneo CRM Workflow System is a sophisticated, enterprise-grade automation platform featuring 45+ specialized node types organized into 9 categories. Built on an async architecture with comprehensive error handling, checkpoint recovery, and multi-tenant isolation, it enables complex business process automation with reliability and scale.

### Key Capabilities
- **45+ Node Types**: Comprehensive coverage of business automation needs
- **Async Processing**: Non-blocking execution with parallel processing support
- **Schema Validation**: JSON Schema-based configuration validation
- **Checkpoint & Recovery**: Automatic state snapshots for resilience
- **Multi-tenant**: Complete data isolation per tenant
- **Extensible**: Plugin architecture for custom nodes

### Architecture Principles
1. **Modularity**: Self-contained nodes with clear interfaces
2. **Reusability**: Nodes work across different workflows
3. **Configurability**: Extensive options without code changes
4. **Observability**: Detailed logging and metrics
5. **Resilience**: Built-in error handling and recovery

---

## System Architecture

### Core Components

```
┌─────────────────────────────────────────────┐
│           Workflow Engine                    │
├─────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Trigger  │→ │  Node    │→ │ Recovery │  │
│  │ System   │  │Processor │  │  System  │  │
│  └──────────┘  └──────────┘  └──────────┘  │
│                      ↓                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Context  │  │  Schema  │  │ Registry │  │
│  │ Manager  │  │Validator │  │  System  │  │
│  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────┘
```

### Processing Flow
1. **Trigger Activation**: Event or schedule initiates workflow
2. **Context Creation**: Execution context initialized with trigger data
3. **Node Execution**: Sequential/parallel processing based on edges
4. **State Management**: Context passed between nodes
5. **Checkpoint Creation**: State snapshots at key points
6. **Error Handling**: Automatic recovery or manual intervention
7. **Completion**: Results stored, analytics updated

---

## Node Categories

### Distribution by Category
- **Trigger Nodes**: 14 types (31%)
- **Control Flow**: 9 types (20%)
- **Communication**: 9 types (20%)
- **AI Nodes**: 5 types (11%)
- **Data Operations**: 5 types (11%)
- **CRM**: 3 types (7%)
- **External Integration**: 2 types (4%)
- **Workflow Management**: 2 types (4%)
- **Utility**: 2 types (4%)

---

## Node Catalog

## 🎯 TRIGGER NODES (14 types)

### 1. trigger_manual
**Purpose**: Manual workflow initiation by user action
**Use Cases**: Admin processes, one-off tasks, testing
**Configuration**:
```json
{
  "require_confirmation": true,
  "confirmation_message": "Execute workflow?",
  "allowed_user_types": ["admin", "manager"],
  "button_text": "Run Workflow"
}
```

### 2. trigger_record_created
**Purpose**: Activate when new record created
**Use Cases**: Lead automation, onboarding flows
**Configuration**:
```json
{
  "pipeline_ids": ["leads", "contacts"],
  "field_filters": {
    "source": "website",
    "score": {"$gte": 50}
  },
  "delay_seconds": 60,
  "batch_processing": false
}
```

### 3. trigger_record_updated
**Purpose**: Respond to record modifications
**Use Cases**: Status change automation, data sync
**Configuration**:
```json
{
  "pipeline_ids": ["deals"],
  "watch_all_fields": false,
  "specific_fields": ["status", "amount"],
  "update_types": ["field_change", "status_change"],
  "debounce_seconds": 5
}
```

### 4. trigger_record_deleted
**Purpose**: Handle record deletion events
**Use Cases**: Cleanup tasks, archival processes
**Configuration**:
```json
{
  "pipeline_ids": ["*"],
  "soft_delete_only": true,
  "archive_before_delete": true
}
```

### 5. trigger_form_submitted
**Purpose**: Process form submissions
**Use Cases**: Lead capture, surveys, applications
**Configuration**:
```json
{
  "form_ids": ["contact_form", "demo_request"],
  "validation_rules": ["email_required", "phone_valid"],
  "auto_create_record": true
}
```

### 6. trigger_scheduled
**Purpose**: Time-based workflow execution
**Use Cases**: Reports, batch processing, maintenance
**Configuration**:
```json
{
  "cron_expression": "0 9 * * MON",
  "timezone": "America/New_York",
  "max_concurrent": 1,
  "catch_up_on_failure": false
}
```

### 7. trigger_webhook
**Purpose**: External system integration
**Use Cases**: Third-party events, API callbacks
**Configuration**:
```json
{
  "webhook_url": "/api/workflows/webhook/abc123",
  "secret_key": "webhook_secret",
  "allowed_ips": ["192.168.1.0/24"],
  "validate_payload": true
}
```

### 8. trigger_email_received
**Purpose**: Email-triggered automation
**Use Cases**: Support tickets, email parsing
**Configuration**:
```json
{
  "email_addresses": ["support@company.com"],
  "subject_filters": ["urgent", "critical"],
  "sender_whitelist": ["@customer.com"],
  "parse_attachments": true
}
```

### 9. trigger_linkedin_message
**Purpose**: LinkedIn message automation
**Use Cases**: Social selling, recruitment
**Configuration**:
```json
{
  "message_types": ["InMail", "message"],
  "sender_filters": {"connection_degree": [1, 2]},
  "keyword_filters": ["interested", "demo"]
}
```

### 10. trigger_whatsapp_message
**Purpose**: WhatsApp message handling
**Use Cases**: Customer service, notifications
**Configuration**:
```json
{
  "phone_numbers": ["+1234567890"],
  "message_types": ["text", "media"],
  "auto_acknowledge": true
}
```

### 11. trigger_date_reached
**Purpose**: Date/time-based triggers
**Use Cases**: Reminders, expirations, deadlines
**Configuration**:
```json
{
  "date_field": "contract_expiry",
  "days_before": 30,
  "time_of_day": "09:00",
  "skip_weekends": true
}
```

### 12. trigger_pipeline_stage_changed
**Purpose**: Pipeline stage transitions
**Use Cases**: Sales process automation
**Configuration**:
```json
{
  "pipeline_id": "sales",
  "from_stages": ["qualified"],
  "to_stages": ["proposal", "negotiation"],
  "direction": "forward"
}
```

### 13. trigger_workflow_completed
**Purpose**: Chain workflows together
**Use Cases**: Multi-step processes, dependencies
**Configuration**:
```json
{
  "source_workflow_ids": ["workflow_1", "workflow_2"],
  "success_only": true,
  "pass_context": true,
  "merge_outputs": false
}
```

### 14. trigger_condition_met
**Purpose**: Complex conditional triggers
**Use Cases**: Threshold monitoring, alerts
**Configuration**:
```json
{
  "conditions": [
    {
      "field": "temperature",
      "operator": "gt",
      "value": 100,
      "duration_minutes": 5
    }
  ],
  "evaluation_frequency": "1m",
  "require_all": true
}
```

---

## 🤖 AI NODES (5 types)

### 1. ai_prompt
**Purpose**: Execute AI prompts with context
**Use Cases**: Content generation, analysis, extraction
**Configuration**:
```json
{
  "prompt": "Summarize this deal: {{record.description}}",
  "model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 500,
  "system_prompt": "You are a business analyst",
  "tools_enabled": ["web_search", "calculator"],
  "output_format": "markdown",
  "retry_on_failure": true,
  "cache_ttl_minutes": 60
}
```

### 2. ai_analysis
**Purpose**: Analyze data with AI
**Use Cases**: Sentiment analysis, categorization, scoring
**Configuration**:
```json
{
  "analysis_type": "sentiment",
  "input_data": "{{record.feedback}}",
  "model": "gpt-3.5-turbo",
  "categories": ["positive", "negative", "neutral"],
  "confidence_threshold": 0.8,
  "include_reasoning": true,
  "batch_size": 10
}
```

### 3. ai_message_generator
**Purpose**: Generate personalized messages
**Use Cases**: Email campaigns, follow-ups, responses
**Configuration**:
```json
{
  "message_type": "email",
  "tone": "professional",
  "length": "medium",
  "personalization_fields": ["name", "company", "interest"],
  "template_style": "sales_followup",
  "include_cta": true,
  "localization": "en-US"
}
```

### 4. ai_response_evaluator
**Purpose**: Evaluate responses and decide next actions
**Use Cases**: Lead qualification, conversation routing
**Configuration**:
```json
{
  "evaluation_criteria": {
    "intent": ["purchase", "support", "information"],
    "sentiment": ["positive", "negative"],
    "urgency": ["high", "medium", "low"]
  },
  "decision_tree": {
    "purchase": "route_to_sales",
    "support": "create_ticket"
  },
  "confidence_required": 0.7
}
```

### 5. ai_conversation_loop
**Purpose**: Manage multi-turn AI conversations
**Use Cases**: Chatbots, qualification flows, surveys
**Configuration**:
```json
{
  "max_turns": 10,
  "conversation_goal": "qualify_lead",
  "context_window": 5,
  "exit_conditions": [
    "goal_achieved",
    "max_turns_reached",
    "user_exit"
  ],
  "fallback_to_human": true,
  "save_transcript": true
}
```

---

## 📊 DATA OPERATION NODES (5 types)

### 1. create_record
**Purpose**: Create new records in pipelines
**Use Cases**: Lead creation, task generation
**Configuration**:
```json
{
  "pipeline_id": "contacts",
  "record_data": {
    "name": "{{trigger.name}}",
    "email": "{{trigger.email}}",
    "source": "workflow"
  },
  "skip_validation": false,
  "check_duplicates": true,
  "merge_if_exists": false
}
```

### 2. update_record
**Purpose**: Modify existing records
**Use Cases**: Status updates, data enrichment
**Configuration**:
```json
{
  "record_id": "{{context.record_id}}",
  "pipeline_id": "deals",
  "update_fields": {
    "status": "qualified",
    "score": "{{context.ai_score}}",
    "last_contacted": "{{now}}"
  },
  "increment_fields": {"touch_count": 1},
  "append_to_arrays": {"tags": ["processed"]}
}
```

### 3. find_records
**Purpose**: Search and retrieve records
**Use Cases**: Lookups, filtering, aggregation
**Configuration**:
```json
{
  "pipeline_id": "contacts",
  "filters": {
    "status": "active",
    "score": {"$gte": 50},
    "created_at": {"$gte": "{{last_week}}"}
  },
  "sort": {"score": -1},
  "limit": 100,
  "include_fields": ["id", "name", "email"],
  "aggregate": false
}
```

### 4. delete_record
**Purpose**: Remove records from pipelines
**Use Cases**: Cleanup, GDPR compliance
**Configuration**:
```json
{
  "record_id": "{{context.record_id}}",
  "pipeline_id": "leads",
  "soft_delete": true,
  "archive_before_delete": true,
  "cascade_delete": false
}
```

### 5. merge_data
**Purpose**: Combine data from multiple sources
**Use Cases**: Data enrichment, consolidation
**Configuration**:
```json
{
  "merge_sources": [
    {"source": "context", "path": "record_data"},
    {"source": "api_response", "path": "enrichment"},
    {"source": "static", "data": {"processed": true}}
  ],
  "merge_strategy": "deep",
  "conflict_resolution": "latest_wins",
  "remove_nulls": true
}
```

---

## 🔀 CONTROL FLOW NODES (9 types)

### 1. condition
**Purpose**: Conditional branching (if/else)
**Use Cases**: Decision trees, routing logic
**Configuration**:
```json
{
  "conditions": [
    {
      "if": "{{record.score}} > 80",
      "then": "high_value_path",
      "label": "High Value Lead"
    },
    {
      "elif": "{{record.score}} > 50",
      "then": "medium_value_path",
      "label": "Medium Value Lead"
    },
    {
      "else": "low_value_path",
      "label": "Low Value Lead"
    }
  ],
  "evaluation_mode": "first_match"
}
```

### 2. for_each
**Purpose**: Iterate over collections
**Use Cases**: Batch processing, list operations
**Configuration**:
```json
{
  "items_source": "{{context.records}}",
  "item_variable": "current_record",
  "max_iterations": 1000,
  "batch_size": 10,
  "parallel_processing": true,
  "continue_on_error": true,
  "accumulator": {
    "enabled": true,
    "initial_value": [],
    "operation": "append"
  }
}
```

### 3. workflow_loop_controller
**Purpose**: Control workflow iterations
**Use Cases**: Retry logic, conversation loops
**Configuration**:
```json
{
  "loop_key": "main_loop",
  "loop_type": "conditional",
  "max_iterations": 10,
  "exit_conditions": [
    {
      "type": "context_value",
      "path": "success",
      "expected_value": true
    }
  ],
  "loop_back_to": "loop_start",
  "exit_to": "loop_complete"
}
```

### 4. workflow_loop_breaker
**Purpose**: Exit loops based on conditions
**Use Cases**: Early termination, success conditions
**Configuration**:
```json
{
  "loop_key": "main_loop",
  "break_conditions": [
    {
      "condition": "{{context.attempts}} > 3",
      "reason": "max_attempts_exceeded"
    }
  ],
  "cleanup_on_break": true
}
```

### 5. wait_delay
**Purpose**: Pause execution for specified time
**Use Cases**: Rate limiting, scheduled delays
**Configuration**:
```json
{
  "delay_seconds": 300,
  "delay_type": "fixed",
  "randomize": {
    "enabled": true,
    "min_seconds": 240,
    "max_seconds": 360
  }
}
```

### 6. wait_for_response
**Purpose**: Wait for user or system response
**Use Cases**: Approvals, confirmations
**Configuration**:
```json
{
  "response_type": "user_action",
  "timeout_minutes": 1440,
  "reminder_intervals": [360, 720],
  "timeout_action": "proceed",
  "expected_responses": ["approve", "reject"],
  "response_channel": "email"
}
```

### 7. wait_for_record_event
**Purpose**: Wait for record changes
**Use Cases**: Status monitoring, synchronization
**Configuration**:
```json
{
  "record_id": "{{context.record_id}}",
  "pipeline_id": "deals",
  "event_types": ["status_change", "field_update"],
  "specific_fields": ["status"],
  "expected_values": ["closed_won", "closed_lost"],
  "timeout_hours": 72
}
```

### 8. wait_for_condition
**Purpose**: Wait until condition is met
**Use Cases**: Threshold waiting, state changes
**Configuration**:
```json
{
  "condition": "{{context.temperature}} < 50",
  "check_interval_seconds": 60,
  "max_wait_minutes": 60,
  "timeout_action": "fail"
}
```

### 9. conversation_state
**Purpose**: Manage conversation context
**Use Cases**: Chatbots, multi-turn interactions
**Configuration**:
```json
{
  "state_key": "chat_session",
  "operation": "update",
  "state_data": {
    "current_step": "qualification",
    "messages_count": "{{increment}}",
    "last_message": "{{now}}"
  },
  "persist_to_record": true,
  "ttl_minutes": 30
}
```

---

## 📨 COMMUNICATION NODES (9 types)

### 1. unipile_send_email
**Purpose**: Send emails via UniPile
**Use Cases**: Outreach, notifications, campaigns
**Configuration**:
```json
{
  "to": ["{{record.email}}"],
  "cc": [],
  "bcc": [],
  "subject": "{{template.subject}}",
  "body": "{{template.body}}",
  "body_type": "html",
  "attachments": [],
  "track_opens": true,
  "track_clicks": true,
  "send_time": "optimal",
  "reply_to": "sales@company.com"
}
```

### 2. unipile_send_linkedin
**Purpose**: Send LinkedIn messages
**Use Cases**: Social selling, recruitment
**Configuration**:
```json
{
  "recipient_id": "{{record.linkedin_id}}",
  "message_type": "message",
  "message": "{{template.linkedin_message}}",
  "connection_request": false,
  "connection_note": "",
  "schedule_send": true,
  "optimal_time": true
}
```

### 3. unipile_send_whatsapp
**Purpose**: Send WhatsApp messages
**Use Cases**: Customer service, notifications
**Configuration**:
```json
{
  "phone_number": "{{record.phone}}",
  "message": "{{template.whatsapp_message}}",
  "media_url": null,
  "message_type": "text",
  "template_name": "order_confirmation",
  "template_params": ["{{order_id}}", "{{amount}}"]
}
```

### 4. unipile_send_sms
**Purpose**: Send SMS messages
**Use Cases**: Alerts, OTP, reminders
**Configuration**:
```json
{
  "phone_number": "{{record.phone}}",
  "message": "{{template.sms_message}}",
  "sender_id": "COMPANY",
  "unicode": false,
  "flash": false,
  "delivery_report": true
}
```

### 5. unipile_sync_messages
**Purpose**: Sync messages from communication channels
**Use Cases**: Inbox management, conversation tracking
**Configuration**:
```json
{
  "channels": ["email", "linkedin", "whatsapp"],
  "sync_direction": "both",
  "since_timestamp": "{{last_sync}}",
  "max_messages": 1000,
  "auto_mark_read": false,
  "create_records": true
}
```

### 6. log_communication
**Purpose**: Log communication activities
**Use Cases**: Activity tracking, compliance
**Configuration**:
```json
{
  "activity_type": "email_sent",
  "record_id": "{{context.record_id}}",
  "details": {
    "subject": "{{email.subject}}",
    "status": "delivered",
    "timestamp": "{{now}}"
  },
  "update_last_contacted": true,
  "increment_touch_count": true
}
```

### 7. analyze_communication
**Purpose**: Analyze communication patterns
**Use Cases**: Engagement insights, optimization
**Configuration**:
```json
{
  "analysis_type": "engagement",
  "record_id": "{{context.record_id}}",
  "time_period_days": 30,
  "metrics": [
    "open_rate",
    "response_rate",
    "response_time"
  ],
  "compare_to_average": true,
  "generate_recommendations": true
}
```

### 8. score_engagement
**Purpose**: Calculate engagement scores
**Use Cases**: Lead scoring, prioritization
**Configuration**:
```json
{
  "record_id": "{{context.record_id}}",
  "scoring_factors": {
    "email_opens": 5,
    "email_clicks": 10,
    "replies": 25,
    "meeting_scheduled": 50
  },
  "decay_rate": 0.9,
  "time_window_days": 90,
  "normalize_score": true,
  "max_score": 100
}
```

---

## 👥 CRM NODES (3 types)

### 1. resolve_contact
**Purpose**: Find or create contact records
**Use Cases**: Data deduplication, record matching
**Configuration**:
```json
{
  "match_criteria": {
    "email": "{{trigger.email}}",
    "phone": "{{trigger.phone}}"
  },
  "match_strategy": "any",
  "create_if_not_found": true,
  "update_existing": true,
  "merge_duplicates": true,
  "confidence_threshold": 0.8
}
```

### 2. update_contact_status
**Purpose**: Update contact lifecycle status
**Use Cases**: Lead progression, lifecycle management
**Configuration**:
```json
{
  "record_id": "{{context.contact_id}}",
  "new_status": "customer",
  "update_timestamp": true,
  "trigger_status_workflows": true,
  "update_related_records": true,
  "notification_list": ["sales_team"]
}
```

### 3. create_follow_up_task
**Purpose**: Generate follow-up tasks
**Use Cases**: Sales activities, reminders
**Configuration**:
```json
{
  "task_type": "call",
  "title": "Follow up on proposal",
  "description": "Check if they have questions",
  "due_date": "{{date.add_days(3)}}",
  "assigned_to": "{{record.owner}}",
  "priority": "high",
  "related_record": "{{context.record_id}}",
  "reminder_before_minutes": 15
}
```

---

## 🌐 EXTERNAL INTEGRATION NODES (2 types)

### 1. http_request
**Purpose**: Make HTTP API calls
**Use Cases**: Third-party integrations, webhooks
**Configuration**:
```json
{
  "method": "POST",
  "url": "https://api.service.com/endpoint",
  "headers": {
    "Authorization": "Bearer {{secrets.api_key}}",
    "Content-Type": "application/json"
  },
  "body": {
    "data": "{{context.payload}}"
  },
  "timeout_seconds": 30,
  "retry_count": 3,
  "retry_backoff": "exponential",
  "error_handling": "continue"
}
```

### 2. webhook_out
**Purpose**: Send webhooks to external systems
**Use Cases**: Event notifications, system sync
**Configuration**:
```json
{
  "webhook_url": "{{config.webhook_endpoint}}",
  "payload": {
    "event": "record_updated",
    "data": "{{context.record}}"
  },
  "secret": "{{secrets.webhook_secret}}",
  "signature_header": "X-Signature",
  "compression": "gzip",
  "async": true
}
```

---

## 🔧 WORKFLOW MANAGEMENT NODES (2 types)

### 1. sub_workflow
**Purpose**: Execute another workflow
**Use Cases**: Workflow composition, reusability
**Configuration**:
```json
{
  "workflow_id": "email_campaign_workflow",
  "pass_context": true,
  "context_mapping": {
    "parent_record": "{{context.record_id}}"
  },
  "wait_for_completion": true,
  "timeout_minutes": 60,
  "inherit_permissions": true
}
```

### 2. approval
**Purpose**: Human approval step
**Use Cases**: Process gates, authorization
**Configuration**:
```json
{
  "approval_title": "Approve discount request",
  "approval_description": "Customer requesting 20% discount",
  "assigned_to": "{{manager_email}}",
  "approval_data": {
    "customer": "{{record.name}}",
    "amount": "{{record.deal_value}}",
    "discount": "{{requested_discount}}"
  },
  "timeout_hours": 48,
  "timeout_action": "reject",
  "escalation_path": ["manager", "director"],
  "require_comments": true
}
```

---

## 🛠️ UTILITY NODES (2 types)

### 1. task_notify
**Purpose**: Send notifications
**Use Cases**: Alerts, updates, reminders
**Configuration**:
```json
{
  "notification_type": "email",
  "recipients": ["{{record.owner}}", "{{manager}}"],
  "title": "New high-value lead assigned",
  "message": "Lead {{record.name}} requires attention",
  "priority": "high",
  "channels": ["email", "slack"],
  "include_link": true,
  "link_url": "{{record.url}}"
}
```

### 2. generate_form_link
**Purpose**: Create form links
**Use Cases**: Surveys, data collection
**Configuration**:
```json
{
  "form_id": "customer_feedback",
  "prefill_data": {
    "customer_id": "{{record.id}}",
    "email": "{{record.email}}"
  },
  "expiry_days": 7,
  "single_use": true,
  "redirect_url": "https://company.com/thank-you",
  "track_completion": true
}
```

---

## Development Guidelines

### Creating a New Node Processor

#### 1. File Structure
```python
# backend/workflows/nodes/category/my_node.py
from workflows.nodes.base import AsyncNodeProcessor

class MyNodeProcessor(AsyncNodeProcessor):
    """Node processor description"""

    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["field1"],
        "properties": {
            "field1": {
                "type": "string",
                "description": "Field description"
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "my_node"
        self.supports_replay = True
        self.supports_checkpoints = True

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the node"""
        # Implementation
        return {
            "success": True,
            "output": result
        }
```

#### 2. Schema Definition Standards
- Use JSON Schema Draft 7
- Include descriptions for all fields
- Add UI hints for frontend rendering
- Specify default values where appropriate
- Use enums for limited choices
- Add validation constraints

#### 3. Testing Requirements
```python
# backend/workflows/tests/test_my_node.py
import pytest
from workflows.nodes.category.my_node import MyNodeProcessor

@pytest.mark.asyncio
async def test_my_node_processing():
    processor = MyNodeProcessor()
    config = {"field1": "value"}
    context = {"record": {"id": "123"}}

    result = await processor.process(config, context)

    assert result["success"] == True
    assert "output" in result
```

#### 4. Error Handling Patterns
```python
async def process(self, node_config, context):
    try:
        # Main processing
        result = await self.do_work()
        return {"success": True, "output": result}
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "validation",
            "continue_execution": False
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            "success": False,
            "error": "Internal error",
            "error_type": "system",
            "retry_recommended": True
        }
```

#### 5. Performance Considerations
- Use async/await for I/O operations
- Implement connection pooling for external services
- Cache frequently accessed data
- Use batch operations where possible
- Implement timeouts for external calls
- Monitor memory usage for large datasets

---

## Integration Patterns

### 1. Sequential Processing
```json
{
  "nodes": [
    {"id": "1", "type": "trigger_manual"},
    {"id": "2", "type": "find_records"},
    {"id": "3", "type": "ai_analysis"},
    {"id": "4", "type": "update_record"}
  ],
  "edges": [
    {"source": "1", "target": "2"},
    {"source": "2", "target": "3"},
    {"source": "3", "target": "4"}
  ]
}
```

### 2. Conditional Branching
```json
{
  "nodes": [
    {"id": "1", "type": "trigger_record_created"},
    {"id": "2", "type": "condition"},
    {"id": "3", "type": "high_value_flow"},
    {"id": "4", "type": "standard_flow"}
  ],
  "edges": [
    {"source": "1", "target": "2"},
    {"source": "2", "target": "3", "condition": "high_value"},
    {"source": "2", "target": "4", "condition": "standard"}
  ]
}
```

### 3. Loop Implementation
```json
{
  "nodes": [
    {"id": "1", "type": "find_records"},
    {"id": "2", "type": "for_each"},
    {"id": "3", "type": "process_record"},
    {"id": "4", "type": "aggregate_results"}
  ],
  "edges": [
    {"source": "1", "target": "2"},
    {"source": "2", "target": "3", "loop": true},
    {"source": "3", "target": "2", "loop_back": true},
    {"source": "2", "target": "4", "loop_complete": true}
  ]
}
```

### 4. Error Recovery Flow
```json
{
  "nodes": [
    {"id": "1", "type": "http_request"},
    {"id": "2", "type": "error_handler"},
    {"id": "3", "type": "retry_logic"},
    {"id": "4", "type": "fallback_action"}
  ],
  "error_handling": {
    "retry_count": 3,
    "retry_delay": 1000,
    "fallback_on_failure": true
  }
}
```

### 5. Parallel Processing
```json
{
  "nodes": [
    {"id": "1", "type": "trigger"},
    {"id": "2", "type": "split"},
    {"id": "3", "type": "path_a"},
    {"id": "4", "type": "path_b"},
    {"id": "5", "type": "merge"}
  ],
  "edges": [
    {"source": "1", "target": "2"},
    {"source": "2", "target": "3", "parallel": true},
    {"source": "2", "target": "4", "parallel": true},
    {"source": "3", "target": "5"},
    {"source": "4", "target": "5"}
  ]
}
```

---

## Advanced Topics

### Checkpoint and Recovery System

#### Checkpoint Creation
```python
checkpoint = {
    "node_id": node_config.get("id"),
    "node_type": self.node_type,
    "context_snapshot": context.copy(),
    "timestamp": timezone.now().isoformat(),
    "sequence_number": execution.checkpoint_count + 1
}
```

#### Recovery Strategies
1. **Retry**: Re-execute from last checkpoint
2. **Rollback**: Revert to previous state
3. **Skip**: Skip failed node and continue
4. **Manual**: Wait for manual intervention
5. **Restart**: Start workflow from beginning

### Replay Functionality
- Complete execution replay with parameter modification
- Comparison analysis between runs
- Debug mode for troubleshooting
- Time-travel debugging

### Performance Optimization

#### Node-Level Optimization
- Minimize context size
- Use streaming for large datasets
- Implement pagination
- Cache external API calls

#### Workflow-Level Optimization
- Parallel node execution where possible
- Lazy loading of data
- Connection pooling
- Async I/O operations

### Multi-tenant Considerations
- Tenant context isolation
- Resource quotas per tenant
- Separate execution queues
- Tenant-specific configuration

### Security Best Practices
- Input validation on all nodes
- Secret management for credentials
- Rate limiting for external calls
- Audit logging for sensitive operations
- Encrypted context storage

---

## Implementation Roadmap

### Current State (v1.0)
- ✅ 45+ node types implemented
- ✅ Async processing architecture
- ✅ Schema validation system
- ✅ Basic error handling
- ✅ Multi-tenant support

### Short-term Improvements (v1.1)
- [ ] Enhanced error recovery
- [ ] Performance monitoring dashboard
- [ ] Node testing framework
- [ ] Visual workflow debugger
- [ ] Extended webhook support

### Medium-term Enhancements (v1.2)
- [ ] Custom node plugin system
- [ ] Advanced analytics nodes
- [ ] Machine learning nodes
- [ ] Real-time collaboration
- [ ] Workflow versioning

### Long-term Vision (v2.0)
- [ ] Auto-optimization of workflows
- [ ] Predictive error prevention
- [ ] Natural language workflow creation
- [ ] Cross-tenant workflow sharing
- [ ] Enterprise integration hub

### Priority Improvements
1. **Performance**: Optimize high-usage nodes
2. **Reliability**: Enhanced error handling
3. **Observability**: Better logging and metrics
4. **Usability**: Improved configuration UI
5. **Testing**: Comprehensive test coverage

### New Node Proposals
1. **Database Query Node**: Direct SQL/NoSQL queries
2. **File Processing Node**: CSV, Excel, PDF handling
3. **Translation Node**: Multi-language support
4. **Encryption Node**: Data security operations
5. **Scheduling Node**: Complex scheduling logic

---

## API Reference

### BaseNodeProcessor Interface

```python
class BaseNodeProcessor(ABC):
    CONFIG_SCHEMA: Dict  # JSON Schema for configuration

    @abstractmethod
    async def process(self, node_config: Dict, context: Dict) -> Dict:
        """Process node with configuration and context"""

    async def validate_inputs(self, node_config: Dict, context: Dict) -> bool:
        """Validate inputs before processing"""

    async def create_checkpoint(self, node_config: Dict, context: Dict) -> Dict:
        """Create checkpoint for recovery"""

    async def handle_error(self, node_config: Dict, context: Dict, error: Exception) -> Dict:
        """Handle processing errors"""
```

### Context Structure
```python
context = {
    "trigger_data": {},      # Data from trigger
    "record": {},            # Current record being processed
    "workflow": {},          # Workflow metadata
    "execution": {},         # Execution details
    "variables": {},         # User-defined variables
    "loop_state": {},        # Loop iteration data
    "checkpoints": [],       # Checkpoint history
    "outputs": {}           # Node outputs
}
```

### Schema Validation
```python
schema = {
    "type": "object",
    "required": ["field_name"],
    "properties": {
        "field_name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
            "pattern": "^[a-zA-Z0-9_]+$",
            "description": "Field description",
            "default": "default_value",
            "enum": ["option1", "option2"]
        }
    }
}
```

### Registry System
```python
from workflows.core.registry import node_registry

# Register new node
node_registry.register_processor("my_node", MyNodeProcessor)

# Get processor
processor = node_registry.get_processor("my_node")

# List available nodes
nodes = node_registry.get_available_node_types()
```

---

## Examples & Templates

### Lead Qualification Workflow
```json
{
  "name": "Lead Qualification",
  "nodes": [
    {"id": "1", "type": "trigger_record_created", "config": {"pipeline_id": "leads"}},
    {"id": "2", "type": "ai_analysis", "config": {"analysis_type": "lead_scoring"}},
    {"id": "3", "type": "condition", "config": {"threshold": 70}},
    {"id": "4", "type": "update_contact_status", "config": {"status": "qualified"}},
    {"id": "5", "type": "create_follow_up_task", "config": {"type": "call"}},
    {"id": "6", "type": "unipile_send_email", "config": {"template": "welcome"}}
  ]
}
```

### Customer Onboarding Workflow
```json
{
  "name": "Customer Onboarding",
  "nodes": [
    {"id": "1", "type": "trigger_record_updated", "config": {"status": "customer"}},
    {"id": "2", "type": "create_record", "config": {"pipeline": "onboarding_tasks"}},
    {"id": "3", "type": "unipile_send_email", "config": {"template": "welcome_email"}},
    {"id": "4", "type": "wait_delay", "config": {"days": 1}},
    {"id": "5", "type": "task_notify", "config": {"message": "Schedule onboarding call"}},
    {"id": "6", "type": "generate_form_link", "config": {"form": "satisfaction_survey"}}
  ]
}
```

### Support Ticket Workflow
```json
{
  "name": "Support Ticket Handler",
  "nodes": [
    {"id": "1", "type": "trigger_email_received", "config": {"address": "support@"}},
    {"id": "2", "type": "ai_analysis", "config": {"extract": ["urgency", "category"]}},
    {"id": "3", "type": "create_record", "config": {"pipeline": "tickets"}},
    {"id": "4", "type": "condition", "config": {"check": "urgency"}},
    {"id": "5", "type": "task_notify", "config": {"urgent": true}},
    {"id": "6", "type": "unipile_send_email", "config": {"auto_reply": true}}
  ]
}
```

---

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Node Timeout
**Problem**: Node execution exceeds timeout
**Solution**:
- Increase timeout in node configuration
- Optimize processing logic
- Use batch processing for large datasets
- Implement pagination

#### 2. Context Size Limit
**Problem**: Context too large for processing
**Solution**:
- Store large data in external storage
- Use references instead of embedding data
- Clean up context between nodes
- Implement data streaming

#### 3. Rate Limiting
**Problem**: External API rate limits hit
**Solution**:
- Implement exponential backoff
- Use connection pooling
- Cache API responses
- Batch API requests

#### 4. Memory Issues
**Problem**: High memory usage during processing
**Solution**:
- Process data in chunks
- Clear unused variables
- Use generators for large datasets
- Monitor memory usage

### Debugging Techniques

#### 1. Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### 2. Use Checkpoint Analysis
```python
checkpoints = execution.checkpoints.all()
for checkpoint in checkpoints:
    print(f"Node: {checkpoint.node_id}")
    print(f"State: {checkpoint.execution_state}")
```

#### 3. Context Inspection
```python
# Add debug node to inspect context
class DebugNode(AsyncNodeProcessor):
    async def process(self, config, context):
        logger.debug(f"Context: {json.dumps(context, indent=2)}")
        return {"success": True}
```

#### 4. Performance Profiling
```python
import time

start = time.time()
result = await processor.process(config, context)
duration = time.time() - start
logger.info(f"Processing took {duration}s")
```

### Log Analysis

#### Key Log Patterns
```
INFO: Node execution started
DEBUG: Input validation passed
DEBUG: Context snapshot created
INFO: Processing completed in Xms
ERROR: Node failed with error: Y
```

#### Monitoring Queries
```sql
-- Failed executions
SELECT * FROM workflow_execution_log
WHERE status = 'FAILED'
ORDER BY started_at DESC;

-- Slow nodes
SELECT node_type, AVG(duration_ms) as avg_duration
FROM workflow_execution_log
GROUP BY node_type
HAVING AVG(duration_ms) > 5000;

-- Error patterns
SELECT error_details->>'error_type', COUNT(*)
FROM workflow_execution_log
WHERE status = 'FAILED'
GROUP BY error_details->>'error_type';
```

---

## Conclusion

The Oneo CRM Workflow System provides a comprehensive, enterprise-grade automation platform with 45+ specialized nodes. This guide serves as the definitive reference for understanding, implementing, and extending the workflow system.

### Key Takeaways
- **Modular Architecture**: Each node is self-contained and reusable
- **Extensive Configuration**: Rich configuration options for all nodes
- **Robust Error Handling**: Multiple recovery strategies
- **Performance Optimized**: Async processing with caching
- **Enterprise Ready**: Multi-tenant, secure, scalable

### Next Steps
1. Review node implementations for your use case
2. Design workflow patterns for your business processes
3. Implement custom nodes as needed
4. Set up monitoring and analytics
5. Create workflow templates for common scenarios

### Resources
- Source Code: `/backend/workflows/nodes/`
- Tests: `/backend/workflows/tests/`
- Admin Interface: `/admin/workflows/`
- API Documentation: `/api/v1/workflows/docs/`

---

*Last Updated: 2024-12-24*
*Version: 1.0*
*Contributors: Oneo CRM Development Team*