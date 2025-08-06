"""
Workflow execution engine for Phase 7
Integrates with existing Phase 3 AI infrastructure
"""
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from django.contrib.auth import get_user_model
from django.utils import timezone
from pipelines.models import Pipeline, Record, Field
from .ai_integration import workflow_ai_processor  # Leverage existing AI infrastructure
from tenants.models import Tenant
from .models import (
    Workflow, WorkflowExecution, WorkflowExecutionLog, 
    WorkflowApproval, ExecutionStatus, WorkflowNodeType
)
import logging
from channels.layers import get_channel_layer

User = get_user_model()
logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


class WorkflowEngine:
    """Core workflow execution engine"""
    
    def __init__(self):
        self.max_concurrent_executions = 10
        self.node_processors = self._register_node_processors()
        
        # Initialize broadcaster
        if channel_layer:
            from realtime.consumers import WorkflowExecutionBroadcaster
            self.broadcaster = WorkflowExecutionBroadcaster(channel_layer)
        else:
            self.broadcaster = None
    
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
        
        # Broadcast execution started
        if self.broadcaster:
            await self.broadcaster.broadcast_execution_started(execution)
        
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
            
            # Broadcast execution completed
            if self.broadcaster:
                await self.broadcaster.broadcast_execution_completed(execution)
            
            logger.info(f"Workflow {workflow.name} executed successfully")
            return execution
            
        except Exception as e:
            # Mark execution as failed
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = timezone.now()
            execution.save()
            
            # Broadcast execution completed (with error)
            if self.broadcaster:
                await self.broadcaster.broadcast_execution_completed(execution)
            
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
        
        # Broadcast node started
        if self.broadcaster:
            await self.broadcaster.broadcast_node_started(log)
        
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
            
            # Broadcast node completed
            if self.broadcaster:
                await self.broadcaster.broadcast_node_completed(log)
            
        except Exception as e:
            # Update log with error
            duration_ms = int((time.time() - start_time) * 1000)
            log.status = ExecutionStatus.FAILED
            log.error_details = {'error': str(e)}
            log.duration_ms = duration_ms
            log.completed_at = timezone.now()
            log.save()
            
            # Broadcast node completed (with error)
            if self.broadcaster:
                await self.broadcaster.broadcast_node_completed(log)
            
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
            WorkflowNodeType.AI_CLASSIFICATION: self._process_ai_classification_node,
            WorkflowNodeType.RECORD_CREATE: self._process_record_create_node,
            WorkflowNodeType.RECORD_UPDATE: self._process_record_update_node,
            WorkflowNodeType.RECORD_FIND: self._process_record_find_node,
            WorkflowNodeType.CONDITION: self._process_condition_node,
            WorkflowNodeType.FOR_EACH: self._process_for_each_node,
            WorkflowNodeType.HTTP_REQUEST: self._process_http_request_node,
            WorkflowNodeType.WEBHOOK_OUT: self._process_webhook_out_node,
            WorkflowNodeType.APPROVAL: self._process_approval_node,
            WorkflowNodeType.TASK_NOTIFY: self._process_task_notify_node,
            WorkflowNodeType.WAIT_DELAY: self._process_wait_delay_node,
            WorkflowNodeType.SUB_WORKFLOW: self._process_sub_workflow_node,
            WorkflowNodeType.MERGE_DATA: self._process_merge_data_node,
            
            # Communication nodes
            WorkflowNodeType.UNIPILE_SEND_EMAIL: self._process_unipile_send_email_node,
            WorkflowNodeType.UNIPILE_SEND_LINKEDIN: self._process_unipile_send_linkedin_node,
            WorkflowNodeType.UNIPILE_SEND_WHATSAPP: self._process_unipile_send_whatsapp_node,
            WorkflowNodeType.UNIPILE_SEND_SMS: self._process_unipile_send_sms_node,
            WorkflowNodeType.UNIPILE_SYNC_MESSAGES: self._process_unipile_sync_messages_node,
            WorkflowNodeType.LOG_COMMUNICATION: self._process_log_communication_node,
            WorkflowNodeType.RESOLVE_CONTACT: self._process_resolve_contact_node,
            WorkflowNodeType.UPDATE_CONTACT_STATUS: self._process_update_contact_status_node,
            WorkflowNodeType.CREATE_FOLLOW_UP_TASK: self._process_create_follow_up_task_node,
            WorkflowNodeType.ANALYZE_COMMUNICATION: self._process_analyze_communication_node,
            WorkflowNodeType.SCORE_ENGAGEMENT: self._process_score_engagement_node,
        }
    
    async def _process_ai_prompt_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process AI prompt node using ai.integrations.AIIntegrationManager"""
        
        prompt_template = node_config.get('prompt', '')
        ai_config = node_config.get('ai_config', {})
        
        # Format prompt with context data
        formatted_prompt = prompt_template.format(**context)
        
        # Get tenant from workflow creator
        from django.db import connection
        tenant = connection.tenant
        
        if not tenant.can_use_ai_features():
            raise ValueError("AI features not available for this tenant")
        
        # Create a temporary record for AI processing
        temp_record_data = {
            'workflow_context': context,
            'prompt_input': formatted_prompt
        }
        
        # Use existing AI field processor
        try:
            result = await workflow_ai_processor.process_ai_field_async(
                record_data=temp_record_data,
                field_config={
                    'ai_prompt': formatted_prompt,
                    'ai_model': ai_config.get('model', 'gpt-4'),
                    'temperature': ai_config.get('temperature', 0.7),
                    'max_tokens': ai_config.get('max_tokens', 1000),
                    'enable_tools': ai_config.get('enable_tools', False),
                    'allowed_tools': ai_config.get('allowed_tools', [])
                },
                tenant=tenant,
                user=execution.triggered_by
            )
            
            return {
                'output': result.get('content', ''),
                'ai_metadata': {
                    'tokens_used': result.get('tokens_used', 0),
                    'model': result.get('model', ''),
                    'processing_time_ms': result.get('processing_time_ms', 0),
                    'cost_cents': result.get('cost_cents', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"AI prompt node failed: {e}")
            return {
                'output': f"AI processing failed: {str(e)}",
                'error': True
            }
    
    async def _process_ai_analysis_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process AI analysis node"""
        
        analysis_type = node_config.get('analysis_type', 'general')
        data_source = node_config.get('data_source', '')
        
        # Get data to analyze
        data_to_analyze = self._get_nested_value(context, data_source)
        
        if analysis_type == 'sentiment':
            prompt = f"Analyze the sentiment of this text and return 'positive', 'negative', or 'neutral': {data_to_analyze}"
        elif analysis_type == 'summary':
            prompt = f"Provide a concise summary of: {data_to_analyze}"
        elif analysis_type == 'classification':
            categories = node_config.get('categories', [])
            prompt = f"Classify this content into one of these categories {categories}: {data_to_analyze}"
        else:
            prompt = f"Analyze this data: {data_to_analyze}"
        
        # Reuse AI prompt processing
        return await self._process_ai_prompt_node(
            execution, 
            {'prompt': prompt, 'ai_config': node_config.get('ai_config', {})}, 
            context
        )
    
    async def _process_ai_classification_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process AI classification node"""
        
        data_source = node_config.get('data_source', '')
        categories = node_config.get('categories', [])
        
        if not categories:
            raise ValueError("Classification node requires categories")
        
        data_to_classify = self._get_nested_value(context, data_source)
        categories_str = ", ".join(categories)
        
        prompt = f"""Classify the following content into one of these categories: {categories_str}

Content: {data_to_classify}

Return only the category name."""
        
        return await self._process_ai_prompt_node(
            execution, 
            {'prompt': prompt, 'ai_config': node_config.get('ai_config', {})}, 
            context
        )
    
    async def _process_record_create_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process record creation node"""
        
        pipeline_id = node_config.get('pipeline_id')
        record_data = node_config.get('record_data', {})
        
        if not pipeline_id:
            raise ValueError("Record create node requires pipeline_id")
        
        # Format record data with context
        formatted_data = {}
        for key, value in record_data.items():
            if isinstance(value, str) and '{' in value:
                try:
                    formatted_data[key] = value.format(**context)
                except KeyError as e:
                    logger.warning(f"Context key not found for formatting: {e}")
                    formatted_data[key] = value
            else:
                formatted_data[key] = value
        
        # Create record
        try:
            pipeline = Pipeline.objects.get(id=pipeline_id)
            record = Record.objects.create(
                pipeline=pipeline,
                data=formatted_data,
                created_by=execution.triggered_by
            )
            
            return {
                'output': {
                    'record_id': record.id,
                    'record_data': record.data,
                    'success': True
                }
            }
            
        except Pipeline.DoesNotExist:
            raise ValueError(f"Pipeline {pipeline_id} not found")
        except Exception as e:
            logger.error(f"Record creation failed: {e}")
            return {
                'output': {
                    'error': str(e),
                    'success': False
                }
            }
    
    async def _process_record_update_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process record update node"""
        
        record_id_source = node_config.get('record_id_source', '')
        update_data = node_config.get('update_data', {})
        
        # Get record ID from context
        record_id = self._get_nested_value(context, record_id_source)
        if not record_id:
            raise ValueError("Record update node requires record_id")
        
        # Format update data with context
        formatted_data = {}
        for key, value in update_data.items():
            if isinstance(value, str) and '{' in value:
                try:
                    formatted_data[key] = value.format(**context)
                except KeyError:
                    formatted_data[key] = value
            else:
                formatted_data[key] = value
        
        try:
            record = Record.objects.get(id=record_id, is_deleted=False)
            
            # Update record data
            record.data.update(formatted_data)
            record.save()
            
            return {
                'output': {
                    'record_id': record.id,
                    'updated_fields': list(formatted_data.keys()),
                    'success': True
                }
            }
            
        except Record.DoesNotExist:
            raise ValueError(f"Record {record_id} not found")
    
    async def _process_record_find_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process record find node"""
        
        pipeline_id = node_config.get('pipeline_id')
        search_criteria = node_config.get('search_criteria', {})
        limit = node_config.get('limit', 10)
        
        try:
            query = Record.objects.filter(
                pipeline_id=pipeline_id,
                is_deleted=False
            )
            
            # Apply search criteria
            for field, value in search_criteria.items():
                if isinstance(value, str) and '{' in value:
                    value = value.format(**context)
                
                # Search in JSON data field
                query = query.filter(data__contains={field: value})
            
            records = list(query[:limit])
            
            return {
                'output': {
                    'records': [
                        {
                            'id': r.id,
                            'data': r.data,
                            'created_at': r.created_at.isoformat()
                        } for r in records
                    ],
                    'count': len(records)
                }
            }
            
        except Exception as e:
            logger.error(f"Record find failed: {e}")
            return {
                'output': {
                    'records': [],
                    'count': 0,
                    'error': str(e)
                }
            }
    
    async def _process_condition_node(
        self, 
        execution: WorkflowExecution,
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
        execution: WorkflowExecution,
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
        sub_workflow_id = node_config.get('sub_workflow_id')
        
        if not sub_workflow_id:
            # Simple item processing without sub-workflow
            return {
                'output': {
                    'items': items,
                    'count': len(items)
                }
            }
        
        # Process items in parallel batches
        results = []
        semaphore = asyncio.Semaphore(max_concurrency)
        
        try:
            sub_workflow = Workflow.objects.get(id=sub_workflow_id)
        except Workflow.DoesNotExist:
            raise ValueError(f"Sub-workflow {sub_workflow_id} not found")
        
        async def process_item(item, index):
            async with semaphore:
                item_context = {
                    **context, 
                    'current_item': item, 
                    'current_index': index
                }
                
                # Execute sub-workflow for this item
                try:
                    sub_execution = await self.execute_workflow(
                        workflow=sub_workflow,
                        trigger_data=item_context,
                        triggered_by=execution.triggered_by
                    )
                    
                    return {
                        'item': item,
                        'index': index,
                        'success': sub_execution.status == ExecutionStatus.SUCCESS,
                        'execution_id': str(sub_execution.id)
                    }
                    
                except Exception as e:
                    return {
                        'item': item,
                        'index': index,
                        'success': False,
                        'error': str(e)
                    }
        
        # Execute all items in parallel
        tasks = [process_item(item, i) for i, item in enumerate(items)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and count successes
        processed_results = []
        success_count = 0
        
        for result in results:
            if isinstance(result, Exception):
                processed_results.append({
                    'success': False,
                    'error': str(result)
                })
            else:
                processed_results.append(result)
                if result.get('success'):
                    success_count += 1
        
        return {
            'output': {
                'results': processed_results,
                'total_items': len(items),
                'success_count': success_count,
                'failure_count': len(items) - success_count
            }
        }
    
    async def _process_http_request_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process HTTP request node"""
        
        import aiohttp
        
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
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                if method == 'GET':
                    async with session.get(url, headers=formatted_headers) as response:
                        response_data = await self._parse_response(response)
                elif method == 'POST':
                    async with session.post(url, headers=formatted_headers, json=formatted_body) as response:
                        response_data = await self._parse_response(response)
                elif method == 'PUT':
                    async with session.put(url, headers=formatted_headers, json=formatted_body) as response:
                        response_data = await self._parse_response(response)
                elif method == 'DELETE':
                    async with session.delete(url, headers=formatted_headers) as response:
                        response_data = await self._parse_response(response)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
            
            return {
                'output': response_data,
                'success': response_data['status_code'] < 400
            }
            
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            return {
                'output': {'error': str(e), 'status_code': 0},
                'success': False
            }
    
    async def _parse_response(self, response):
        """Parse HTTP response"""
        try:
            if 'application/json' in response.headers.get('content-type', ''):
                data = await response.json()
            else:
                data = await response.text()
        except:
            data = await response.text()
        
        return {
            'status_code': response.status,
            'headers': dict(response.headers),
            'data': data
        }
    
    async def _process_webhook_out_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process outgoing webhook node"""
        
        # Reuse HTTP request processing for webhooks
        webhook_config = {
            'method': 'POST',
            'url': node_config.get('webhook_url', ''),
            'headers': {
                'Content-Type': 'application/json',
                **node_config.get('headers', {})
            },
            'body': {
                'workflow_id': str(execution.workflow.id),
                'execution_id': str(execution.id),
                'timestamp': timezone.now().isoformat(),
                'data': context,
                **node_config.get('payload', {})
            },
            'timeout': node_config.get('timeout', 30)
        }
        
        return await self._process_http_request_node(execution, webhook_config, context)
    
    async def _process_approval_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process human approval node"""
        
        title = node_config.get('title', 'Approval Required').format(**context)
        description = node_config.get('description', '').format(**context)
        assigned_to_id = node_config.get('assigned_to_id')
        
        if not assigned_to_id:
            raise ValueError("Approval node requires assigned_to_id")
        
        try:
            assigned_to = User.objects.get(id=assigned_to_id)
        except User.DoesNotExist:
            raise ValueError(f"User {assigned_to_id} not found")
        
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
        
        return {
            'output': {
                'approval_id': str(approval.id),
                'status': 'pending_approval',
                'assigned_to': assigned_to.email,
                'title': title
            },
            'requires_approval': True
        }
    
    async def _process_task_notify_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process task/notification node"""
        
        notification_type = node_config.get('type', 'info')
        message = node_config.get('message', '').format(**context)
        recipients = node_config.get('recipients', [])
        
        # This would integrate with a notification system
        # For now, we'll just log the notification
        logger.info(f"Workflow notification [{notification_type}]: {message}")
        
        return {
            'output': {
                'notification_type': notification_type,
                'message': message,
                'recipients': recipients,
                'sent_at': timezone.now().isoformat()
            }
        }
    
    async def _process_wait_delay_node(
        self, 
        execution: WorkflowExecution,
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
                'resumed_at': timezone.now().isoformat()
            }
        }
    
    async def _process_sub_workflow_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process sub-workflow call node"""
        
        sub_workflow_id = node_config.get('sub_workflow_id')
        input_mapping = node_config.get('input_mapping', {})
        
        if not sub_workflow_id:
            raise ValueError("Sub-workflow node requires sub_workflow_id")
        
        try:
            sub_workflow = Workflow.objects.get(id=sub_workflow_id)
        except Workflow.DoesNotExist:
            raise ValueError(f"Sub-workflow {sub_workflow_id} not found")
        
        # Prepare sub-workflow context
        sub_context = {}
        for key, context_path in input_mapping.items():
            value = self._get_nested_value(context, context_path)
            if value is not None:
                sub_context[key] = value
        
        # Execute sub-workflow
        sub_execution = await self.execute_workflow(
            workflow=sub_workflow,
            trigger_data=sub_context,
            triggered_by=execution.triggered_by
        )
        
        return {
            'output': {
                'sub_execution_id': str(sub_execution.id),
                'status': sub_execution.status,
                'success': sub_execution.status == ExecutionStatus.SUCCESS,
                'final_output': sub_execution.final_output
            }
        }
    
    async def _process_merge_data_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process data merge node"""
        
        merge_sources = node_config.get('merge_sources', [])
        merge_strategy = node_config.get('merge_strategy', 'combine')
        
        merged_data = {}
        
        for source in merge_sources:
            source_data = self._get_nested_value(context, source)
            if isinstance(source_data, dict):
                if merge_strategy == 'combine':
                    merged_data.update(source_data)
                elif merge_strategy == 'override':
                    merged_data = {**merged_data, **source_data}
            elif source_data is not None:
                merged_data[source] = source_data
        
        return {
            'output': merged_data
        }
    
    # Communication node processors
    async def _process_unipile_send_email_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process UniPile send email node"""
        from communications.models import UserChannelConnection, ChannelType
        
        user_id = node_config.get('user_id') or context.get('user_id')
        recipient_email = node_config.get('recipient_email', '').format(**context)
        subject = node_config.get('subject', '').format(**context)
        content = node_config.get('content', '').format(**context)
        
        if not all([user_id, recipient_email, subject, content]):
            raise ValueError("Email node requires user_id, recipient_email, subject, and content")
        
        try:
            # Get user's email channel connection
            user_channel = UserChannelConnection.objects.filter(
                user_id=user_id,
                channel_type=ChannelType.EMAIL,
                is_active=True,
                auth_status='connected'
            ).first()
            
            if not user_channel:
                return {
                    'output': {
                        'success': False,
                        'error': 'No active email channel found for user'
                    }
                }
            
            # Integrate with UniPile SDK to send email
            from communications.unipile_sdk import unipile_service
            
            result = await unipile_service.send_message(
                user_channel_connection=user_channel,
                recipient=recipient_email,
                content=f"Subject: {subject}\n\n{content}",
                message_type='email'
            )
            
            if result['success']:
                return {
                    'output': {
                        'success': True,
                        'message_id': result.get('message_id'),
                        'recipient': recipient_email,
                        'subject': subject,
                        'channel': user_channel.name
                    }
                }
            else:
                return {
                    'output': {
                        'success': False,
                        'error': result.get('error', 'Email send failed')
                    }
                }
            
            # Fallback return for non-SDK mode
            return {
                'output': {
                    'success': True,
                    'message_id': f'email_{timezone.now().timestamp()}',
                    'recipient': recipient_email,
                    'subject': subject,
                    'channel': user_channel.name
                }
            }
            
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return {
                'output': {
                    'success': False,
                    'error': str(e)
                }
            }
    
    async def _process_unipile_send_linkedin_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process UniPile send LinkedIn message node"""
        from communications.models import UserChannelConnection, ChannelType
        
        user_id = node_config.get('user_id') or context.get('user_id')
        recipient_profile = node_config.get('recipient_profile', '').format(**context)
        message_content = node_config.get('message_content', '').format(**context)
        
        if not all([user_id, recipient_profile, message_content]):
            raise ValueError("LinkedIn node requires user_id, recipient_profile, and message_content")
        
        try:
            user_channel = UserChannelConnection.objects.filter(
                user_id=user_id,
                channel_type=ChannelType.LINKEDIN,
                is_active=True,
                auth_status='connected'
            ).first()
            
            if not user_channel:
                return {
                    'output': {
                        'success': False,
                        'error': 'No active LinkedIn channel found for user'
                    }
                }
            
            # Integrate with UniPile SDK to send LinkedIn message
            from communications.unipile_sdk import unipile_service
            
            result = await unipile_service.send_message(
                user_channel_connection=user_channel,
                recipient=recipient_profile,
                content=message_content,
                message_type='linkedin'
            )
            
            if result['success']:
                return {
                    'output': {
                        'success': True,
                        'message_id': result.get('message_id'),
                        'recipient': recipient_profile,
                        'content': message_content,
                        'channel': user_channel.name
                    }
                }
            else:
                return {
                    'output': {
                        'success': False,
                        'error': result.get('error', 'LinkedIn message send failed')
                    }
                }
            
        except Exception as e:
            logger.error(f"LinkedIn message send failed: {e}")
            return {
                'output': {
                    'success': False,
                    'error': str(e)
                }
            }
    
    async def _process_unipile_send_whatsapp_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process UniPile send WhatsApp message node"""
        from communications.models import UserChannelConnection, ChannelType
        
        user_id = node_config.get('user_id') or context.get('user_id')
        recipient_phone = node_config.get('recipient_phone', '').format(**context)
        message_content = node_config.get('message_content', '').format(**context)
        
        if not all([user_id, recipient_phone, message_content]):
            raise ValueError("WhatsApp node requires user_id, recipient_phone, and message_content")
        
        try:
            user_channel = UserChannelConnection.objects.filter(
                user_id=user_id,
                channel_type=ChannelType.WHATSAPP,
                is_active=True,
                auth_status='connected'
            ).first()
            
            if not user_channel:
                return {
                    'output': {
                        'success': False,
                        'error': 'No active WhatsApp channel found for user'
                    }
                }
            
            # Integrate with UniPile SDK to send WhatsApp message
            from communications.unipile_sdk import unipile_service
            
            result = await unipile_service.send_message(
                user_channel_connection=user_channel,
                recipient=recipient_phone,
                content=message_content,
                message_type='whatsapp'
            )
            
            if result['success']:
                return {
                    'output': {
                        'success': True,
                        'message_id': result.get('message_id'),
                        'recipient': recipient_phone,
                        'content': message_content,
                        'channel': user_channel.name
                    }
                }
            else:
                return {
                    'output': {
                        'success': False,
                        'error': result.get('error', 'WhatsApp message send failed')
                    }
                }
            
        except Exception as e:
            logger.error(f"WhatsApp message send failed: {e}")
            return {
                'output': {
                    'success': False,
                    'error': str(e)
                }
            }
    
    async def _process_unipile_send_sms_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process UniPile send SMS node"""
        from communications.models import UserChannelConnection, ChannelType
        
        user_id = node_config.get('user_id') or context.get('user_id')
        recipient_phone = node_config.get('recipient_phone', '').format(**context)
        message_content = node_config.get('message_content', '').format(**context)
        
        if not all([user_id, recipient_phone, message_content]):
            raise ValueError("SMS node requires user_id, recipient_phone, and message_content")
        
        try:
            user_channel = UserChannelConnection.objects.filter(
                user_id=user_id,
                channel_type=ChannelType.SMS,
                is_active=True,
                auth_status='connected'
            ).first()
            
            if not user_channel:
                return {
                    'output': {
                        'success': False,
                        'error': 'No active SMS channel found for user'
                    }
                }
            
            # Integrate with UniPile SDK to send SMS
            from communications.unipile_sdk import unipile_service
            
            result = await unipile_service.send_message(
                user_channel_connection=user_channel,
                recipient=recipient_phone,
                content=message_content,
                message_type='sms'
            )
            
            if result['success']:
                return {
                    'output': {
                        'success': True,
                        'message_id': result.get('message_id'),
                        'recipient': recipient_phone,
                        'content': message_content,
                        'channel': user_channel.name
                    }
                }
            else:
                return {
                    'output': {
                        'success': False,
                        'error': result.get('error', 'SMS send failed')
                    }
                }
            
        except Exception as e:
            logger.error(f"SMS send failed: {e}")
            return {
                'output': {
                    'success': False,
                    'error': str(e)
                }
            }
    
    async def _process_unipile_sync_messages_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process UniPile message sync node"""
        from communications.models import UserChannelConnection
        
        user_id = node_config.get('user_id') or context.get('user_id')
        channel_types = node_config.get('channel_types', [])
        
        if not user_id:
            raise ValueError("Sync messages node requires user_id")
        
        try:
            # Get user's active channels
            query = UserChannelConnection.objects.filter(
                user_id=user_id,
                is_active=True,
                auth_status='connected'
            )
            
            if channel_types:
                query = query.filter(channel_type__in=channel_types)
            
            channels = list(query)
            
            # Integrate with UniPile SDK to sync messages
            from communications.unipile_sdk import unipile_service
            
            synced_channels = []
            for channel in channels:
                sync_result = await unipile_service.sync_messages(
                    user_channel_connection=channel,
                    since=channel.last_sync_at,
                    limit=100
                )
                
                synced_channels.append({
                    'channel_id': str(channel.id),
                    'channel_type': channel.channel_type,
                    'messages_synced': sync_result.get('processed_count', 0),
                    'last_sync': timezone.now().isoformat(),
                    'success': sync_result['success']
                })
            
            return {
                'output': {
                    'success': True,
                    'channels_synced': len(synced_channels),
                    'details': synced_channels
                }
            }
            
        except Exception as e:
            logger.error(f"Message sync failed: {e}")
            return {
                'output': {
                    'success': False,
                    'error': str(e)
                }
            }
    
    async def _process_log_communication_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process communication logging node"""
        
        activity_type = node_config.get('activity_type', 'communication')
        description = node_config.get('description', '').format(**context)
        contact_id = self._get_nested_value(context, node_config.get('contact_id_path', ''))
        
        # This would integrate with activity logging system
        return {
            'output': {
                'success': True,
                'activity_id': f'activity_{timezone.now().timestamp()}',
                'activity_type': activity_type,
                'description': description,
                'contact_id': contact_id,
                'logged_at': timezone.now().isoformat()
            }
        }
    
    async def _process_resolve_contact_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process contact resolution/creation node"""
        from pipelines.models import Pipeline, Record
        
        email = node_config.get('email', '').format(**context) or self._get_nested_value(context, 'email')
        phone = node_config.get('phone', '').format(**context) or self._get_nested_value(context, 'phone')
        name = node_config.get('name', '').format(**context) or self._get_nested_value(context, 'name')
        pipeline_id = node_config.get('pipeline_id')
        
        if not any([email, phone]) or not pipeline_id:
            raise ValueError("Contact resolution requires email or phone, and pipeline_id")
        
        try:
            pipeline = Pipeline.objects.get(id=pipeline_id)
            
            # Try to find existing contact
            query_filters = {}
            if email:
                query_filters['data__email__icontains'] = email
            elif phone:
                query_filters['data__phone__icontains'] = phone
            
            existing_contact = Record.objects.filter(
                pipeline=pipeline,
                **query_filters,
                is_deleted=False
            ).first()
            
            if existing_contact:
                return {
                    'output': {
                        'contact_id': str(existing_contact.id),
                        'created': False,
                        'contact_data': existing_contact.data
                    }
                }
            else:
                # Create new contact
                contact_data = {}
                if email:
                    contact_data['email'] = email
                if phone:
                    contact_data['phone'] = phone
                if name:
                    contact_data['name'] = name
                
                new_contact = Record.objects.create(
                    pipeline=pipeline,
                    data=contact_data,
                    created_by=execution.triggered_by
                )
                
                return {
                    'output': {
                        'contact_id': str(new_contact.id),
                        'created': True,
                        'contact_data': new_contact.data
                    }
                }
                
        except Pipeline.DoesNotExist:
            raise ValueError(f"Pipeline {pipeline_id} not found")
        except Exception as e:
            logger.error(f"Contact resolution failed: {e}")
            return {
                'output': {
                    'success': False,
                    'error': str(e)
                }
            }
    
    async def _process_update_contact_status_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process contact status update node"""
        
        contact_id = self._get_nested_value(context, node_config.get('contact_id_path', ''))
        new_status = node_config.get('new_status', '').format(**context)
        
        if not contact_id or not new_status:
            raise ValueError("Contact status update requires contact_id and new_status")
        
        try:
            from pipelines.models import Record
            
            contact = Record.objects.get(id=contact_id, is_deleted=False)
            contact.data['status'] = new_status
            contact.save()
            
            return {
                'output': {
                    'success': True,
                    'contact_id': contact_id,
                    'previous_status': contact.data.get('previous_status'),
                    'new_status': new_status,
                    'updated_at': timezone.now().isoformat()
                }
            }
            
        except Record.DoesNotExist:
            raise ValueError(f"Contact {contact_id} not found")
    
    async def _process_create_follow_up_task_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process follow-up task creation node"""
        
        task_title = node_config.get('task_title', '').format(**context)
        task_description = node_config.get('task_description', '').format(**context)
        due_date = node_config.get('due_date', '').format(**context)
        assigned_to_id = node_config.get('assigned_to_id')
        
        # This would integrate with task management system
        return {
            'output': {
                'success': True,
                'task_id': f'task_{timezone.now().timestamp()}',
                'title': task_title,
                'description': task_description,
                'due_date': due_date,
                'assigned_to': assigned_to_id,
                'created_at': timezone.now().isoformat()
            }
        }
    
    async def _process_analyze_communication_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process communication analysis node"""
        
        analysis_type = node_config.get('analysis_type', 'sentiment')
        communication_data = self._get_nested_value(context, node_config.get('data_path', ''))
        
        if not communication_data:
            raise ValueError("Communication analysis requires communication data")
        
        # Use existing AI prompt processing for analysis
        if analysis_type == 'sentiment':
            prompt = f"Analyze the sentiment of this communication and return 'positive', 'negative', or 'neutral' with a confidence score: {communication_data}"
        elif analysis_type == 'intent':
            prompt = f"Analyze the intent of this communication and categorize it: {communication_data}"
        elif analysis_type == 'engagement':
            prompt = f"Score the engagement level of this communication from 1-10: {communication_data}"
        else:
            prompt = f"Analyze this communication: {communication_data}"
        
        return await self._process_ai_prompt_node(
            execution, 
            {'prompt': prompt, 'ai_config': node_config.get('ai_config', {})}, 
            context
        )
    
    async def _process_score_engagement_node(
        self, 
        execution: WorkflowExecution,
        node_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process engagement scoring node"""
        
        contact_id = self._get_nested_value(context, node_config.get('contact_id_path', ''))
        scoring_criteria = node_config.get('scoring_criteria', {})
        
        if not contact_id:
            raise ValueError("Engagement scoring requires contact_id")
        
        # This would integrate with engagement scoring system
        engagement_score = 7.5  # Placeholder calculation
        
        return {
            'output': {
                'success': True,
                'contact_id': contact_id,
                'engagement_score': engagement_score,
                'scoring_criteria': scoring_criteria,
                'calculated_at': timezone.now().isoformat()
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
                return float(left) > float(right)
            elif operator == '>=':
                return float(left) >= float(right)
            elif operator == '<':
                return float(left) < float(right)
            elif operator == '<=':
                return float(left) <= float(right)
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


# Global workflow engine instance
workflow_engine = WorkflowEngine()