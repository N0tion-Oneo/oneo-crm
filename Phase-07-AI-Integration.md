# Phase 07: Workflow Automation with AI Integration

## 🎯 Overview & Objectives

Build a visual workflow automation system (N8n-style) that integrates with existing Phase 3 AI infrastructure. This phase focuses on workflow automation with AI tools within workflows, leveraging the current tenant AI setup for intelligent automation.

### Primary Goals
- Visual workflow builder with drag-and-drop interface
- Workflow automation with AI-powered nodes
- Integration with existing tenant AI configuration (Phase 3)
- Real-time workflow execution with detailed logging
- Human approval and RBAC for workflow security
- For-Each/parallel processing with concurrency controls

### Success Criteria
- ✅ Visual workflow builder using React Flow
- ✅ AI nodes leveraging existing AIFieldProcessor
- ✅ Workflow triggers (record events, schedules, webhooks)
- ✅ Real-time execution logs and status updates
- ✅ Human approval workflows
- ✅ For-Each/parallel processing capabilities

## 🏗️ Technical Requirements & Dependencies

### Phase Dependencies
- ✅ **Phase 01**: Multi-tenant architecture for workflow isolation
- ✅ **Phase 02**: User permissions for workflow access control
- ✅ **Phase 03**: Pipeline system with existing AI infrastructure (AIFieldProcessor)
- ✅ **Phase 04**: Relationship system for workflow data access
- ✅ **Phase 05**: API layer for workflow endpoints
- ✅ **Phase 06**: Real-time updates for workflow execution status

### Core Technologies
- **React Flow** for visual workflow builder interface
- **Django Channels** for real-time workflow execution updates
- **Celery** for background workflow execution
- **Existing AIFieldProcessor** from Phase 3 for AI-powered nodes
- **Existing tenant AI configuration** for API keys and model settings

### Additional Dependencies
```bash
# Frontend workflow builder
npm install @xyflow/react
npm install @xyflow/node-resizer
npm install react-beautiful-dnd

# Backend workflow processing
pip install croniter==1.4.1  # For cron schedule parsing
pip install celery-beat==2.2.1  # For scheduled workflows
```

## 🗄️ Workflow System Architecture

### Workflow Models and Database Schema
```python
# workflows/models.py
from django.db import models
from django.contrib.auth import get_user_model
import uuid
from enum import Enum

User = get_user_model()

class WorkflowStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    ACTIVE = 'active', 'Active'
    PAUSED = 'paused', 'Paused'
    ARCHIVED = 'archived', 'Archived'

class WorkflowTriggerType(models.TextChoices):
    MANUAL = 'manual', 'Manual'
    RECORD_CREATED = 'record_created', 'Record Created'
    RECORD_UPDATED = 'record_updated', 'Record Updated'
    FIELD_CHANGED = 'field_changed', 'Field Changed'
    SCHEDULED = 'scheduled', 'Scheduled'
    WEBHOOK = 'webhook', 'Webhook'

class WorkflowNodeType(models.TextChoices):
    # AI Actions (leverage existing AIFieldProcessor)
    AI_PROMPT = 'ai_prompt', 'AI Prompt'
    AI_ANALYSIS = 'ai_analysis', 'AI Analysis'
    AI_CLASSIFICATION = 'ai_classification', 'AI Classification'
    
    # Record Operations
    RECORD_CREATE = 'record_create', 'Create Record'
    RECORD_UPDATE = 'record_update', 'Update Record'
    RECORD_FIND = 'record_find', 'Find Records'
    
    # Logic and Control Flow
    CONDITION = 'condition', 'Condition (If/Else)'
    FOR_EACH = 'for_each', 'For Each (Loop)'
    WAIT_DELAY = 'wait_delay', 'Wait/Delay'
    
    # External Integration
    HTTP_REQUEST = 'http_request', 'HTTP Request'
    WEBHOOK_OUT = 'webhook_out', 'Send Webhook'
    
    # Human Interaction
    APPROVAL = 'approval', 'Human Approval'
    TASK_NOTIFY = 'task_notify', 'Task/Notification'

class Workflow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Ownership
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Configuration
    status = models.CharField(max_length=20, choices=WorkflowStatus.choices)
    trigger_type = models.CharField(max_length=30, choices=WorkflowTriggerType.choices)
    trigger_config = models.JSONField(default=dict)
    
    # Workflow definition (React Flow compatible)
    workflow_definition = models.JSONField(default=dict)
    
    def __str__(self):
        return self.name
```

### Database Schema for Workflow System
```sql
-- Workflow-related tables in tenant schema

-- Workflows
CREATE TABLE workflows_workflow (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Ownership
    created_by_id INTEGER REFERENCES users_customuser(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Configuration
    status VARCHAR(20) DEFAULT 'draft',
    version INTEGER DEFAULT 1,
    trigger_type VARCHAR(30) NOT NULL,
    trigger_config JSONB DEFAULT '{}',
    
    -- Settings
    max_executions_per_hour INTEGER DEFAULT 100,
    timeout_minutes INTEGER DEFAULT 60,
    retry_count INTEGER DEFAULT 3,
    
    -- Definition
    workflow_definition JSONB DEFAULT '{}'
);

-- Workflow Executions
CREATE TABLE workflows_execution (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows_workflow(id),
    
    -- Execution metadata
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    
    -- Context
    trigger_data JSONB DEFAULT '{}',
    triggered_by_id INTEGER REFERENCES users_customuser(id),
    execution_context JSONB DEFAULT '{}',
    final_output JSONB,
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

-- Execution Logs (per node)
CREATE TABLE workflows_execution_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID REFERENCES workflows_execution(id),
    
    -- Node identification
    node_id VARCHAR(255) NOT NULL,
    node_type VARCHAR(30) NOT NULL,
    node_name VARCHAR(255),
    
    -- Execution details
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    
    -- Data
    input_data JSONB DEFAULT '{}',
    output_data JSONB,
    execution_details JSONB DEFAULT '{}',
    error_details JSONB,
    
    -- Performance
    duration_ms INTEGER
);

-- Human Approvals
CREATE TABLE workflows_approval (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID REFERENCES workflows_execution(id),
    execution_log_id UUID REFERENCES workflows_execution_log(id),
    
    -- Approval metadata
    requested_at TIMESTAMP DEFAULT NOW(),
    requested_by_id INTEGER REFERENCES users_customuser(id),
    assigned_to_id INTEGER REFERENCES users_customuser(id),
    
    -- Content
    title VARCHAR(255) NOT NULL,
    description TEXT,
    approval_data JSONB DEFAULT '{}',
    
    -- Response
    approved BOOLEAN,
    approved_at TIMESTAMP,
    approved_by_id INTEGER REFERENCES users_customuser(id),
    approval_notes TEXT
);

-- Workflow Schedules
CREATE TABLE workflows_schedule (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows_workflow(id),
    
    -- Schedule configuration
    name VARCHAR(255) NOT NULL,
    cron_expression VARCHAR(255) NOT NULL,
    timezone VARCHAR(50) DEFAULT 'UTC',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Tracking
    last_execution TIMESTAMP,
    next_execution TIMESTAMP,
    execution_count INTEGER DEFAULT 0
);

-- Performance indexes
CREATE INDEX idx_workflows_status ON workflows_workflow (status, trigger_type);
CREATE INDEX idx_executions_workflow ON workflows_execution (workflow_id, status);
CREATE INDEX idx_logs_execution ON workflows_execution_log (execution_id, node_id);
CREATE INDEX idx_approvals_assigned ON workflows_approval (assigned_to_id, approved);
CREATE INDEX idx_schedules_next ON workflows_schedule (is_active, next_execution);
```

## 🛠️ Implementation Steps

### Step 1: Workflow Engine Foundation (Day 1-3)

#### 1.1 Workflow Execution Engine
```python
# workflows/engine.py
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from django.contrib.auth import get_user_model
from django.utils import timezone
from pipelines.models import Pipeline, Record
from pipelines.ai_processor import ai_field_processor  # Leverage existing AI infrastructure
from tenants.models import Tenant
from .models import (
    Workflow, WorkflowExecution, WorkflowExecutionLog, 
    WorkflowApproval, ExecutionStatus, WorkflowNodeType
)
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class WorkflowEngine:
    """Core workflow execution engine"""
    
    def __init__(self):
        self.max_concurrent_executions = 10
        self.node_processors = self._register_node_processors()
    
    async def execute_workflow(
        self, 
        workflow: Workflow, 
        trigger_data: Dict[str, Any],
        triggered_by: User
    ) -> WorkflowExecution:
        """Execute a workflow with given trigger data"""
        
        if not workflow.can_execute():
            raise ValueError(f"Workflow {workflow.name} cannot be executed")
        
        # Create execution instance
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            trigger_data=trigger_data,
            triggered_by=triggered_by,
            status=ExecutionStatus.RUNNING,
            execution_context={}
        )
        
        try:
            # Get workflow definition
            nodes = workflow.get_nodes()
            edges = workflow.get_edges()
            
            # Build execution graph
            execution_graph = self._build_execution_graph(nodes, edges)
            
            # Execute nodes in dependency order
            await self._execute_nodes(execution, execution_graph, trigger_data)
            
            # Mark execution as successful
            execution.status = ExecutionStatus.SUCCESS
            execution.completed_at = timezone.now()
            execution.save()
            
            logger.info(f"Workflow {workflow.name} executed successfully")
            return execution
            
        except Exception as e:
            # Mark execution as failed
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = timezone.now()
            execution.save()
            
            logger.error(f"Workflow {workflow.name} execution failed: {e}")
            raise
    
    async def _execute_nodes(
        self, 
        execution: WorkflowExecution, 
        execution_graph: Dict[str, Any],
        trigger_data: Dict[str, Any]
    ):
        """Execute nodes in dependency order"""
        
        executed_nodes = set()
        context = {**trigger_data}
        
        # Find start nodes (no dependencies)
        start_nodes = [
            node_id for node_id, node_data in execution_graph.items()
            if not node_data.get('dependencies', [])
        ]
        
        # Execute using breadth-first approach
        queue = start_nodes.copy()
        
        while queue:
            node_id = queue.pop(0)
            
            if node_id in executed_nodes:
                continue
            
            node_data = execution_graph[node_id]
            
            # Check if all dependencies are satisfied
            dependencies_met = all(
                dep in executed_nodes 
                for dep in node_data.get('dependencies', [])
            )
            
            if not dependencies_met:
                # Re-queue for later execution
                queue.append(node_id)
                continue
            
            # Execute the node
            try:
                await self._execute_single_node(execution, node_data, context)
                executed_nodes.add(node_id)
                
                # Add dependent nodes to queue
                for dependent in node_data.get('dependents', []):
                    if dependent not in queue and dependent not in executed_nodes:
                        queue.append(dependent)
                        
            except Exception as e:
                logger.error(f"Node {node_id} execution failed: {e}")
                raise
    
    async def _execute_single_node(
        self, 
        execution: WorkflowExecution,
        node_data: Dict[str, Any],
        context: Dict[str, Any]
    ):
        """Execute a single workflow node"""
        
        node_id = node_data['id']
        node_type = node_data['type']
        node_config = node_data.get('data', {})
        
        # Create execution log
        log = WorkflowExecutionLog.objects.create(
            execution=execution,
            node_id=node_id,
            node_type=node_type,
            node_name=node_config.get('name', node_id),
            status=ExecutionStatus.RUNNING,
            input_data=self._prepare_node_input(node_config, context)
        )
        
        start_time = time.time()
        
        try:
            # Get node processor
            processor = self.node_processors.get(node_type)
            if not processor:
                raise ValueError(f"No processor found for node type: {node_type}")
            
            # Execute node
            result = await processor(execution, node_config, context)
            
            # Update context with node output
            if result and 'output' in result:
                context[f"node_{node_id}"] = result['output']
            
            # Update log with success
            duration_ms = int((time.time() - start_time) * 1000)
            log.status = ExecutionStatus.SUCCESS
            log.output_data = result
            log.duration_ms = duration_ms
            log.completed_at = timezone.now()
            log.save()
            
        except Exception as e:
            # Update log with error
            duration_ms = int((time.time() - start_time) * 1000)
            log.status = ExecutionStatus.FAILED
            log.error_details = {'error': str(e)}
            log.duration_ms = duration_ms
            log.completed_at = timezone.now()
            log.save()
            raise
    
    def _build_execution_graph(
        self, 
        nodes: List[Dict[str, Any]], 
        edges: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build execution graph from workflow definition"""
        
        graph = {}
        
        # Initialize nodes
        for node in nodes:
            graph[node['id']] = {
                **node,
                'dependencies': [],
                'dependents': []
            }
        
        # Add dependencies from edges
        for edge in edges:
            source = edge['source']
            target = edge['target']
            
            if source in graph and target in graph:
                graph[target]['dependencies'].append(source)
                graph[source]['dependents'].append(target)
        
        return graph
    
    def _prepare_node_input(
        self, 
        node_config: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare input data for node execution"""
        
        input_mapping = node_config.get('input_mapping', {})
        node_input = {}
        
        for input_key, context_path in input_mapping.items():
            # Support dot notation for nested context access
            value = self._get_nested_value(context, context_path)
            if value is not None:
                node_input[input_key] = value
        
        return node_input
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value from dictionary using dot notation"""
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _register_node_processors(self) -> Dict[str, callable]:
        """Register node type processors"""
        return {
            WorkflowNodeType.AI_PROMPT: self._process_ai_prompt_node,
            WorkflowNodeType.AI_ANALYSIS: self._process_ai_analysis_node,
            WorkflowNodeType.RECORD_CREATE: self._process_record_create_node,
            WorkflowNodeType.RECORD_UPDATE: self._process_record_update_node,
            WorkflowNodeType.RECORD_FIND: self._process_record_find_node,
            WorkflowNodeType.CONDITION: self._process_condition_node,
            WorkflowNodeType.FOR_EACH: self._process_for_each_node,
            WorkflowNodeType.HTTP_REQUEST: self._process_http_request_node,
            WorkflowNodeType.APPROVAL: self._process_approval_node,
            WorkflowNodeType.WAIT_DELAY: self._process_wait_delay_node,
        }
    
    async def _process_ai_prompt_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process AI prompt node using existing AIFieldProcessor"""
        
        prompt_template = node_config.get('prompt', '')
        ai_config = node_config.get('ai_config', {})
        
        # Format prompt with context data
        formatted_prompt = prompt_template.format(**context)
        
        # Use existing tenant AI configuration
        tenant = execution.workflow.created_by.tenant
        if not tenant.can_use_ai_features():
            raise ValueError("AI features not available for this tenant")
        
        # Create a temporary AI field configuration
        temp_ai_config = {
            'ai_prompt': formatted_prompt,
            'ai_model': ai_config.get('model', 'gpt-4'),
            'temperature': ai_config.get('temperature', 0.7),
            'max_tokens': ai_config.get('max_tokens', 1000),
            'enable_tools': ai_config.get('enable_tools', False),
            'allowed_tools': ai_config.get('allowed_tools', [])
        }
        
        # Process using existing AI infrastructure
        result = await ai_field_processor.process_ai_request(
            prompt=formatted_prompt,
            ai_config=temp_ai_config,
            tenant=tenant,
            user=execution.triggered_by
        )
        
        return {
            'output': result.get('content', ''),
            'ai_metadata': {
                'tokens_used': result.get('tokens_used', 0),
                'model': result.get('model', ''),
                'processing_time_ms': result.get('processing_time_ms', 0)
            }
        }
    
    async def _process_record_create_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process record creation node"""
        
        pipeline_id = node_config.get('pipeline_id')
        record_data = node_config.get('record_data', {})
        
        # Format record data with context
        formatted_data = {}
        for key, value in record_data.items():
            if isinstance(value, str) and '{' in value:
                formatted_data[key] = value.format(**context)
            else:
                formatted_data[key] = value
        
        # Create record
        pipeline = Pipeline.objects.get(id=pipeline_id)
        record = Record.objects.create(
            pipeline=pipeline,
            data=formatted_data,
            created_by=execution.triggered_by
        )
        
        return {
            'output': {
                'record_id': record.id,
                'record_data': record.data
            }
        }
```

### Step 2: Node Type Implementations (Day 4-6)

#### 2.1 Node Processors for Different Types
```python
# workflows/nodes.py
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from django.contrib.auth import get_user_model
from pipelines.models import Pipeline, Record
from .models import WorkflowApproval, ExecutionStatus
import requests
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class WorkflowNodeProcessors:
    """Extended node processors for workflow automation"""
    
    async def _process_condition_node(
        self, 
        execution: 'WorkflowExecution',
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process conditional logic node"""
        
        conditions = node_config.get('conditions', [])
        default_output = node_config.get('default_output', 'false')
        
        for condition in conditions:
            left_value = self._resolve_value(condition.get('left'), context)
            operator = condition.get('operator', '==')
            right_value = self._resolve_value(condition.get('right'), context)
            
            result = self._evaluate_condition(left_value, operator, right_value)
            
            if result:
                return {
                    'output': condition.get('output', 'true'),
                    'condition_met': True,
                    'matched_condition': condition
                }
        
        return {
            'output': default_output,
            'condition_met': False
        }
    
    async def _process_for_each_node(
        self, 
        execution: 'WorkflowExecution',
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process for-each loop node with parallel processing"""
        
        items_path = node_config.get('items_path', '')
        items = self._get_nested_value(context, items_path)
        
        if not isinstance(items, list):
            raise ValueError(f"Items path '{items_path}' did not resolve to a list")
        
        # Parallel processing configuration
        max_concurrency = node_config.get('max_concurrency', 5)
        sub_nodes = node_config.get('sub_nodes', [])
        
        # Process items in parallel batches
        results = []
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def process_item(item, index):
            async with semaphore:
                item_context = {**context, 'current_item': item, 'current_index': index}
                
                # Execute sub-nodes for this item
                item_results = {}
                for sub_node in sub_nodes:
                    processor = self.node_processors.get(sub_node['type'])
                    if processor:
                        result = await processor(execution, sub_node, item_context)
                        item_results[sub_node['id']] = result
                
                return {
                    'item': item,
                    'index': index,
                    'results': item_results
                }
        
        # Execute all items in parallel
        tasks = [process_item(item, i) for i, item in enumerate(items)]
        results = await asyncio.gather(*tasks)
        
        return {
            'output': results,
            'processed_count': len(results),
            'items_processed': [r['item'] for r in results]
        }
    
    async def _process_http_request_node(
        self, 
        execution: 'WorkflowExecution',
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process HTTP request node"""
        
        method = node_config.get('method', 'GET').upper()
        url = node_config.get('url', '').format(**context)
        headers = node_config.get('headers', {})
        body = node_config.get('body', {})
        timeout = node_config.get('timeout', 30)
        
        # Format headers and body with context
        formatted_headers = {}
        for key, value in headers.items():
            formatted_headers[key] = str(value).format(**context)
        
        formatted_body = {}
        if isinstance(body, dict):
            for key, value in body.items():
                if isinstance(value, str):
                    formatted_body[key] = value.format(**context)
                else:
                    formatted_body[key] = value
        
        try:
            # Make HTTP request
            if method == 'GET':
                response = requests.get(url, headers=formatted_headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, headers=formatted_headers, json=formatted_body, timeout=timeout)
            elif method == 'PUT':
                response = requests.put(url, headers=formatted_headers, json=formatted_body, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=formatted_headers, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Parse response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = response.text
            
            return {
                'output': {
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'data': response_data
                },
                'success': response.status_code < 400
            }
            
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            return {
                'output': {'error': str(e)},
                'success': False
            }
    
    async def _process_approval_node(
        self, 
        execution: 'WorkflowExecution',
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process human approval node"""
        
        title = node_config.get('title', 'Approval Required').format(**context)
        description = node_config.get('description', '').format(**context)
        assigned_to_id = node_config.get('assigned_to_id')
        
        if not assigned_to_id:
            raise ValueError("Approval node requires assigned_to_id")
        
        assigned_to = User.objects.get(id=assigned_to_id)
        
        # Create approval request
        approval = WorkflowApproval.objects.create(
            execution=execution,
            requested_by=execution.triggered_by,
            assigned_to=assigned_to,
            title=title,
            description=description,
            approval_data=context.copy()
        )
        
        # Pause execution until approval
        execution.status = ExecutionStatus.PAUSED
        execution.save()
        
        # This would typically be handled by a separate approval system
        # For now, we'll return a placeholder response
        return {
            'output': {
                'approval_id': str(approval.id),
                'status': 'pending_approval',
                'assigned_to': assigned_to.email
            },
            'requires_approval': True
        }
    
    async def _process_wait_delay_node(
        self, 
        execution: 'WorkflowExecution',
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process wait/delay node"""
        
        delay_type = node_config.get('delay_type', 'seconds')
        delay_value = node_config.get('delay_value', 0)
        
        if delay_type == 'seconds':
            await asyncio.sleep(delay_value)
        elif delay_type == 'minutes':
            await asyncio.sleep(delay_value * 60)
        elif delay_type == 'hours':
            await asyncio.sleep(delay_value * 3600)
        else:
            raise ValueError(f"Unsupported delay type: {delay_type}")
        
        return {
            'output': {
                'delayed_for': f"{delay_value} {delay_type}",
                'resumed_at': time.time()
            }
        }
    
    def _resolve_value(self, value_config: Any, context: Dict[str, Any]) -> Any:
        """Resolve value from context or return literal value"""
        
        if isinstance(value_config, dict) and 'context_path' in value_config:
            return self._get_nested_value(context, value_config['context_path'])
        elif isinstance(value_config, str) and value_config.startswith('{{') and value_config.endswith('}}'):
            # Template string resolution
            template = value_config[2:-2].strip()
            return context.get(template)
        else:
            return value_config
    
    def _evaluate_condition(self, left: Any, operator: str, right: Any) -> bool:
        """Evaluate condition based on operator"""
        
        try:
            if operator == '==':
                return left == right
            elif operator == '!=':
                return left != right
            elif operator == '>':
                return left > right
            elif operator == '>=':
                return left >= right
            elif operator == '<':
                return left < right
            elif operator == '<=':
                return left <= right
            elif operator == 'contains':
                return str(right).lower() in str(left).lower()
            elif operator == 'not_contains':
                return str(right).lower() not in str(left).lower()
            elif operator == 'starts_with':
                return str(left).startswith(str(right))
            elif operator == 'ends_with':
                return str(left).endswith(str(right))
            else:
                raise ValueError(f"Unsupported operator: {operator}")
                
        except Exception as e:
            logger.error(f"Condition evaluation failed: {e}")
            return False
```

### Step 3: Workflow Triggers (Day 7-8)

#### 3.1 Workflow Trigger System
```python
# workflows/triggers.py
import asyncio
from typing import Dict, Any, List
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from pipelines.models import Record
from .models import Workflow, WorkflowTriggerType
from .engine import WorkflowEngine
from croniter import croniter
from datetime import datetime
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class WorkflowTriggerManager:
    """Manages workflow triggers and execution"""
    
    def __init__(self):
        self.engine = WorkflowEngine()
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Setup Django signal handlers for record triggers"""
        
        @receiver(post_save, sender=Record)
        def handle_record_save(sender, instance, created, **kwargs):
            asyncio.create_task(self.handle_record_event(
                instance, 
                'created' if created else 'updated'
            ))
        
        @receiver(post_delete, sender=Record)
        def handle_record_delete(sender, instance, **kwargs):
            asyncio.create_task(self.handle_record_event(instance, 'deleted'))
    
    async def handle_record_event(self, record: Record, event_type: str):
        """Handle record-based workflow triggers"""
        
        trigger_type_map = {
            'created': WorkflowTriggerType.RECORD_CREATED,
            'updated': WorkflowTriggerType.RECORD_UPDATED,
            'deleted': WorkflowTriggerType.RECORD_DELETED
        }
        
        trigger_type = trigger_type_map.get(event_type)
        if not trigger_type:
            return
        
        # Find workflows that should be triggered
        workflows = Workflow.objects.filter(
            status='active',
            trigger_type=trigger_type
        )
        
        for workflow in workflows:
            try:
                # Check if workflow conditions are met
                if self._should_trigger_workflow(workflow, record, event_type):
                    trigger_data = {
                        'event_type': event_type,
                        'record_id': record.id,
                        'pipeline_id': record.pipeline_id,
                        'record_data': record.data,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    await self.engine.execute_workflow(
                        workflow=workflow,
                        trigger_data=trigger_data,
                        triggered_by=record.created_by or workflow.created_by
                    )
                    
            except Exception as e:
                logger.error(f"Failed to trigger workflow {workflow.name}: {e}")
    
    def _should_trigger_workflow(
        self, 
        workflow: Workflow, 
        record: Record, 
        event_type: str
    ) -> bool:
        """Check if workflow should be triggered based on conditions"""
        
        trigger_config = workflow.trigger_config
        
        # Check pipeline filter
        if 'pipeline_ids' in trigger_config:
            if record.pipeline_id not in trigger_config['pipeline_ids']:
                return False
        
        # Check field change conditions for updates
        if event_type == 'updated' and 'field_conditions' in trigger_config:
            # This would require tracking field changes
            # Implementation depends on how you want to track changes
            pass
        
        # Check custom conditions
        if 'conditions' in trigger_config:
            for condition in trigger_config['conditions']:
                if not self._evaluate_trigger_condition(condition, record):
                    return False
        
        return True
    
    def _evaluate_trigger_condition(
        self, 
        condition: Dict[str, Any], 
        record: Record
    ) -> bool:
        """Evaluate trigger condition against record data"""
        
        field_name = condition.get('field')
        operator = condition.get('operator', '==')
        expected_value = condition.get('value')
        
        if field_name not in record.data:
            return False
        
        actual_value = record.data[field_name]
        
        if operator == '==':
            return actual_value == expected_value
        elif operator == '!=':
            return actual_value != expected_value
        elif operator == 'contains':
            return str(expected_value).lower() in str(actual_value).lower()
        # Add more operators as needed
        
        return False

# Global trigger manager
workflow_trigger_manager = WorkflowTriggerManager()
```

### Step 4: Visual Workflow Builder (Day 9-12)

#### 4.1 React Flow Integration
```javascript
// Frontend workflow builder using React Flow
// This would be implemented in the frontend application
// Key features:
// - Drag-and-drop node palette
// - Visual connection between nodes  
// - Real-time execution visualization
// - Context mapping interface
// - Integration with existing authentication
```

### Step 5: Testing and Integration (Day 13-15)

- Unit tests for workflow engine and node processors
- Integration tests with existing Phase 3 AI infrastructure
- Performance testing for parallel node execution
- User acceptance testing for workflow builder interface
- Documentation and deployment procedures

## 🎯 Key Benefits

This Phase 7 implementation provides:

- **Leverages Existing Infrastructure**: Uses Phase 3 AIFieldProcessor and tenant AI configuration
- **Visual Workflow Automation**: N8n-style drag-and-drop workflow builder
- **AI-Powered Nodes**: Intelligent automation using tenant AI settings
- **Real-time Execution**: Live workflow status and detailed logging
- **Scalable Processing**: For-Each loops with configurable concurrency
- **Human Approval Integration**: Built-in approval workflows with RBAC
- **Flexible Triggers**: Record events, schedules, webhooks, and manual execution

The system maintains simplicity while providing powerful workflow automation capabilities that integrate seamlessly with the existing CRM infrastructure.