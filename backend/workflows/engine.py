"""
Workflow execution engine for Phase 7
Integrates with existing Phase 3 AI infrastructure and uses actual processor classes
"""
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Record, Field
from tenants.models import Tenant
from .models import (
    Workflow, WorkflowExecution, WorkflowExecutionLog,
    WorkflowApproval, ExecutionStatus, WorkflowNodeType
)
import logging
from channels.layers import get_channel_layer

# Import all node processors
from .nodes.ai.prompt import AIPromptProcessor
from .nodes.ai.analysis import AIAnalysisProcessor
from .nodes.communication.email import EmailProcessor
from .nodes.communication.whatsapp import WhatsAppProcessor
from .nodes.communication.linkedin import LinkedInProcessor
from .nodes.communication.sms import SMSProcessor
from .nodes.communication.sync import MessageSyncProcessor
from .nodes.communication.logging import CommunicationLoggingProcessor
from .nodes.communication.analysis import CommunicationAnalysisProcessor
from .nodes.communication.ai_conversation_loop import AIConversationLoopProcessor
from .nodes.crm.contact import ContactResolveProcessor
from .nodes.crm.status_update import ContactStatusUpdateProcessor
from .nodes.data.record_ops import (
    RecordCreateProcessor, RecordUpdateProcessor,
    RecordFindProcessor, RecordDeleteProcessor
)
from .nodes.data.merge import MergeDataProcessor
from .nodes.control.condition import ConditionProcessor
from .nodes.control.for_each import ForEachProcessor
from .nodes.utility.wait import WaitDelayProcessor
from .nodes.utility.wait_advanced import (
    WaitForResponseProcessor, WaitForRecordEventProcessor, WaitForConditionProcessor
)
from .nodes.external.http import HTTPRequestProcessor
from .nodes.external.webhook import WebhookOutProcessor
from .nodes.workflow.approval import ApprovalProcessor
from .nodes.workflow.sub_workflow import SubWorkflowProcessor
# Removed ReusableWorkflowProcessor - merged into SubWorkflowProcessor
from .nodes.utility.notification import TaskNotificationProcessor
# Import trigger node processors
from .nodes.triggers import (
    TriggerFormSubmittedProcessor,
    TriggerScheduleProcessor,
    TriggerWebhookProcessor,
    TriggerRecordEventProcessor,
    TriggerEmailReceivedProcessor
)

User = get_user_model()
logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


class WorkflowEngine:
    """Core workflow execution engine using actual processor classes"""

    def __init__(self):
        self.max_concurrent_executions = 10
        self.node_processors = self._register_node_processors()

        # Initialize broadcaster
        if channel_layer:
            from .broadcasting import WorkflowExecutionBroadcaster
            self.broadcaster = WorkflowExecutionBroadcaster(channel_layer)
        else:
            self.broadcaster = None

    def _register_node_processors(self) -> Dict[str, Any]:
        """Register all node type processors with their actual classes"""
        return {
            # Trigger Processors
            'trigger_form_submitted': TriggerFormSubmittedProcessor(),
            'trigger_schedule': TriggerScheduleProcessor(),
            'trigger_webhook': TriggerWebhookProcessor(),
            'trigger_record_created': TriggerRecordEventProcessor(),
            'trigger_record_updated': TriggerRecordEventProcessor(),
            'trigger_record_deleted': TriggerRecordEventProcessor(),
            'trigger_email_received': TriggerEmailReceivedProcessor(),

            # AI Processors
            WorkflowNodeType.AI_PROMPT: AIPromptProcessor(),
            WorkflowNodeType.AI_ANALYSIS: AIAnalysisProcessor(),
            WorkflowNodeType.AI_CLASSIFICATION: AIAnalysisProcessor(),  # Deprecated - uses AI_ANALYSIS
            WorkflowNodeType.AI_CONVERSATION_LOOP: AIConversationLoopProcessor(),

            # Record Operations
            WorkflowNodeType.RECORD_CREATE: RecordCreateProcessor(),
            WorkflowNodeType.RECORD_UPDATE: RecordUpdateProcessor(),
            WorkflowNodeType.RECORD_DELETE: RecordDeleteProcessor(),
            WorkflowNodeType.RECORD_FIND: RecordFindProcessor(),

            # Control Flow
            WorkflowNodeType.CONDITION: ConditionProcessor(),
            WorkflowNodeType.FOR_EACH: ForEachProcessor(),
            WorkflowNodeType.WAIT_DELAY: WaitDelayProcessor(),
            WorkflowNodeType.WAIT_FOR_RESPONSE: WaitForResponseProcessor(),
            WorkflowNodeType.WAIT_FOR_RECORD_EVENT: WaitForRecordEventProcessor(),
            WorkflowNodeType.WAIT_FOR_CONDITION: WaitForConditionProcessor(),

            # External Integration
            WorkflowNodeType.HTTP_REQUEST: HTTPRequestProcessor(),
            WorkflowNodeType.WEBHOOK_OUT: WebhookOutProcessor(),

            # Workflow Control
            WorkflowNodeType.APPROVAL: ApprovalProcessor(),
            WorkflowNodeType.TASK_NOTIFY: TaskNotificationProcessor(),
            WorkflowNodeType.SUB_WORKFLOW: SubWorkflowProcessor(),
            # REUSABLE_WORKFLOW merged into SUB_WORKFLOW - map for backward compatibility
            WorkflowNodeType.REUSABLE_WORKFLOW: SubWorkflowProcessor(),

            # Data Operations
            WorkflowNodeType.MERGE_DATA: MergeDataProcessor(),

            # Communication Nodes (UniPile Integration)
            WorkflowNodeType.UNIPILE_SEND_EMAIL: EmailProcessor(),
            WorkflowNodeType.UNIPILE_SEND_LINKEDIN: LinkedInProcessor(),
            WorkflowNodeType.UNIPILE_SEND_WHATSAPP: WhatsAppProcessor(),
            WorkflowNodeType.UNIPILE_SEND_SMS: SMSProcessor(),
            WorkflowNodeType.UNIPILE_SYNC_MESSAGES: MessageSyncProcessor(),

            # CRM Operations
            WorkflowNodeType.LOG_COMMUNICATION: CommunicationLoggingProcessor(),
            WorkflowNodeType.RESOLVE_CONTACT: ContactResolveProcessor(),
            WorkflowNodeType.UPDATE_CONTACT_STATUS: ContactStatusUpdateProcessor(),
            WorkflowNodeType.CREATE_FOLLOW_UP_TASK: TaskNotificationProcessor(),  # Reuse notification

            # Analytics
            WorkflowNodeType.ANALYZE_COMMUNICATION: CommunicationAnalysisProcessor(),
            WorkflowNodeType.SCORE_ENGAGEMENT: CommunicationAnalysisProcessor(),  # Reuse analysis
        }

    async def execute_workflow(
        self,
        workflow: Workflow,
        trigger_data: Dict[str, Any],
        triggered_by: User,
        tenant: Optional[Tenant] = None,
        start_node_id: Optional[str] = None
    ) -> WorkflowExecution:
        """Execute a workflow with given trigger data and tenant context"""

        if not workflow.can_execute():
            raise ValueError(f"Workflow {workflow.name} cannot be executed")

        # Get tenant from workflow if not provided
        if not tenant:
            tenant = workflow.tenant

        # Ensure we're in the right tenant context
        with schema_context(tenant.schema_name):
            # Create execution instance
            execution = WorkflowExecution.objects.create(
                tenant=tenant,
                workflow=workflow,
                trigger_data=trigger_data,
                triggered_by=triggered_by,
                status=ExecutionStatus.RUNNING,
                execution_context={}
            )

            # Broadcast execution started
            if self.broadcaster:
                await self.broadcaster.broadcast_execution_started(execution)

            try:
                # Get workflow definition
                nodes = workflow.get_nodes()
                edges = workflow.get_edges()

                # Build execution graph
                execution_graph = self._build_execution_graph(nodes, edges)

                # Add tenant to context
                context = {
                    **trigger_data,
                    'tenant_schema': tenant.schema_name,
                    'tenant_id': str(tenant.id),
                    'execution_id': str(execution.id),
                    'workflow_id': str(workflow.id)
                }

                # Execute nodes in dependency order
                await self._execute_nodes(execution, execution_graph, context, start_node_id)

                # Mark execution as successful
                execution.status = ExecutionStatus.SUCCESS
                execution.completed_at = timezone.now()
                execution.save()

                # Update workflow metrics
                execution_time_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000)
                workflow.update_performance_metrics(execution_time_ms, True)
                workflow.save()

                # Broadcast execution completed
                if self.broadcaster:
                    await self.broadcaster.broadcast_execution_completed(execution)

                logger.info(f"Workflow {workflow.name} executed successfully in tenant {tenant.schema_name}")
                return execution

            except Exception as e:
                # Mark execution as failed
                execution.status = ExecutionStatus.FAILED
                execution.error_message = str(e)
                execution.completed_at = timezone.now()
                execution.save()

                # Update workflow metrics
                execution_time_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000)
                workflow.update_performance_metrics(execution_time_ms, False)
                workflow.save()

                # Broadcast execution completed (with error)
                if self.broadcaster:
                    await self.broadcaster.broadcast_execution_completed(execution)

                logger.error(f"Workflow {workflow.name} execution failed in tenant {tenant.schema_name}: {e}")
                raise

    async def _execute_nodes(
        self,
        execution: WorkflowExecution,
        execution_graph: Dict[str, Any],
        context: Dict[str, Any],
        start_node_id: Optional[str] = None
    ):
        """Execute nodes in dependency order"""

        executed_nodes = set()

        # Determine starting point
        if start_node_id:
            # Start from specified node (e.g., trigger node)
            start_nodes = [start_node_id] if start_node_id in execution_graph else []
            if not start_nodes:
                logger.warning(f"Start node {start_node_id} not found in workflow definition")
        else:
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
                result = await self._execute_single_node(execution, node_data, context)
                executed_nodes.add(node_id)

                # Update context with node output
                if result and isinstance(result, dict):
                    context[f"node_{node_id}"] = result
                    # Also add specific outputs to context
                    if 'output' in result:
                        context[f"node_{node_id}_output"] = result['output']

                # Add dependent nodes to queue
                for dependent in node_data.get('dependents', []):
                    if dependent not in queue and dependent not in executed_nodes:
                        queue.append(dependent)

            except Exception as e:
                logger.error(f"Node {node_id} execution failed: {e}")
                # Check if node has error handling
                if node_data.get('data', {}).get('error_handling', {}).get('continue_on_error'):
                    executed_nodes.add(node_id)
                    continue
                raise

    async def _execute_single_node(
        self,
        execution: WorkflowExecution,
        node_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single workflow node using the appropriate processor"""

        node_id = node_data['id']
        node_type = node_data['type']
        node_config = node_data.get('data', {})

        # Get tenant from context
        tenant_schema = context.get('tenant_schema')

        # Create execution log
        with schema_context(tenant_schema):
            log = WorkflowExecutionLog.objects.create(
                tenant_id=context.get('tenant_id'),
                execution=execution,
                node_id=node_id,
                node_type=node_type,
                node_name=node_config.get('name', node_id),
                status=ExecutionStatus.RUNNING,
                input_data=self._prepare_node_input(node_config, context)
            )

        # Broadcast node started
        if self.broadcaster:
            await self.broadcaster.broadcast_node_started(log)

        start_time = time.time()

        try:
            # Get node processor
            processor = self.node_processors.get(node_type)
            if not processor:
                raise ValueError(f"No processor found for node type: {node_type}")

            # Execute node with processor
            # Pass the full node_data as node_config to the processor
            result = await processor.execute(node_data, context)

            # Update log with success
            duration_ms = int((time.time() - start_time) * 1000)

            with schema_context(tenant_schema):
                log.status = ExecutionStatus.SUCCESS
                log.output_data = result
                log.duration_ms = duration_ms
                log.completed_at = timezone.now()
                log.save()

            # Broadcast node completed
            if self.broadcaster:
                await self.broadcaster.broadcast_node_completed(log)

            return result

        except Exception as e:
            # Update log with error
            duration_ms = int((time.time() - start_time) * 1000)

            with schema_context(tenant_schema):
                log.status = ExecutionStatus.FAILED
                log.error_details = {'error': str(e), 'type': type(e).__name__}
                log.duration_ms = duration_ms
                log.completed_at = timezone.now()
                log.save()

            # Broadcast node completed (with error)
            if self.broadcaster:
                await self.broadcaster.broadcast_node_completed(log)

            # Check if we should retry
            retry_config = node_config.get('error_handling', {})
            if retry_config.get('retry_count', 0) > 0:
                # TODO: Implement retry logic
                pass

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
        if not path:
            return None

        keys = path.split('.')
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current


# Global workflow engine instance
workflow_engine = WorkflowEngine()