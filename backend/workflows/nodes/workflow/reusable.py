"""
Reusable Workflow Node Processor - Execute reusable workflows as nodes
"""
import json
import jsonschema
from typing import Dict, Any, Optional
from django.db import transaction
from asgiref.sync import sync_to_async

from workflows.models import WorkflowExecution, ExecutionStatus
from workflows.reusable.models import ReusableWorkflow, ReusableWorkflowExecution
from workflows.nodes.base import AsyncNodeProcessor
from workflows.core.engine import workflow_engine


class ReusableWorkflowProcessor(AsyncNodeProcessor):
    """Process reusable workflow nodes"""
    
    def __init__(self):
        super().__init__()
        self.node_type = "REUSABLE_WORKFLOW"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate inputs against reusable workflow schema"""
        try:
            # Get reusable workflow configuration
            workflow_name = node_config.get('data', {}).get('workflow_name')
            version = node_config.get('data', {}).get('version', 'latest')
            
            if not workflow_name:
                return False
            
            # Get the reusable workflow
            reusable_workflow = await self._get_reusable_workflow(workflow_name, version)
            if not reusable_workflow:
                return False
            
            # Validate inputs against schema
            input_data = await self.prepare_inputs(node_config, context)
            
            try:
                jsonschema.validate(input_data, reusable_workflow.input_schema)
                return True
            except jsonschema.ValidationError:
                return False
                
        except Exception:
            return False
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a reusable workflow as a node"""
        
        # 1. Resolve the reusable workflow
        workflow_name = node_config['data']['workflow_name']
        version = node_config['data'].get('version', 'latest')
        reusable_workflow = await self._get_reusable_workflow(workflow_name, version)
        
        if not reusable_workflow:
            raise ValueError(f"Reusable workflow '{workflow_name}' version '{version}' not found")
        
        # 2. Prepare and validate inputs
        input_data = await self._prepare_reusable_inputs(
            node_config['data'].get('inputs', {}), 
            context, 
            reusable_workflow.input_schema
        )
        
        # 3. Create execution tracking record
        parent_execution = context.get('execution')
        reusable_execution = await self._create_reusable_execution(
            parent_execution, reusable_workflow, node_config.get('id'), input_data
        )
        
        try:
            # 4. Create execution context for reusable workflow
            reusable_context = {
                'trigger_data': input_data,
                'parent_context': context,
                'reusable_workflow_id': str(reusable_workflow.id),
                'parent_execution_id': str(parent_execution.id) if parent_execution else None,
                'reusable_execution': reusable_execution
            }
            
            # 5. Execute the reusable workflow
            result = await self._execute_reusable_workflow(reusable_workflow, reusable_context)
            
            # 6. Map outputs back to parent workflow context
            outputs = await self._map_outputs(
                result, 
                node_config['data'].get('outputs', []),
                reusable_workflow.output_schema
            )
            
            # 7. Mark execution as completed
            await sync_to_async(reusable_execution.mark_completed)(outputs)
            
            # 8. Update usage statistics
            await sync_to_async(reusable_workflow.increment_usage)()
            
            return {
                'success': True,
                'outputs': outputs,
                'reusable_execution_id': str(reusable_execution.id),
                'execution_time_ms': result.get('execution_time_ms', 0)
            }
            
        except Exception as e:
            # Mark execution as failed
            error_details = {
                'error': str(e),
                'error_type': type(e).__name__,
                'phase': 'reusable_workflow_execution'
            }
            await sync_to_async(reusable_execution.mark_failed)(error_details)
            raise
    
    async def _get_reusable_workflow(self, name: str, version: str) -> Optional[ReusableWorkflow]:
        """Get reusable workflow by name and version"""
        try:
            if version == 'latest':
                # Get the latest version
                return await sync_to_async(
                    ReusableWorkflow.objects.filter(
                        name=name, 
                        is_active=True
                    ).order_by('-version').first
                )()
            else:
                return await sync_to_async(
                    ReusableWorkflow.objects.filter(
                        name=name, 
                        version=version,
                        is_active=True
                    ).first
                )()
        except Exception:
            return None
    
    async def _prepare_reusable_inputs(
        self, 
        inputs_config: Dict[str, Any], 
        context: Dict[str, Any],
        input_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare and validate inputs for reusable workflow"""
        
        prepared_inputs = {}
        
        # Process each configured input
        for input_key, input_source in inputs_config.items():
            if isinstance(input_source, str):
                # Handle template variable like {trigger_data.contact_email}
                value = self._get_nested_value(context, input_source)
            else:
                # Direct value
                value = input_source
            
            if value is not None:
                prepared_inputs[input_key] = value
        
        # Add default values from schema
        schema_properties = input_schema.get('properties', {})
        for prop_name, prop_config in schema_properties.items():
            if prop_name not in prepared_inputs and 'default' in prop_config:
                prepared_inputs[prop_name] = prop_config['default']
        
        # Validate against schema
        try:
            jsonschema.validate(prepared_inputs, input_schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"Input validation failed: {e.message}")
        
        return prepared_inputs
    
    async def _create_reusable_execution(
        self,
        parent_execution: WorkflowExecution,
        reusable_workflow: ReusableWorkflow,
        parent_node_id: str,
        input_data: Dict[str, Any]
    ) -> ReusableWorkflowExecution:
        """Create tracking record for reusable workflow execution"""
        
        return await sync_to_async(ReusableWorkflowExecution.objects.create)(
            parent_execution=parent_execution,
            reusable_workflow=reusable_workflow,
            parent_node_id=parent_node_id,
            input_data=input_data,
            status=ExecutionStatus.RUNNING
        )
    
    async def _execute_reusable_workflow(
        self, 
        reusable_workflow: ReusableWorkflow, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the reusable workflow using the workflow engine"""
        
        # Create a temporary workflow execution for the reusable workflow
        # This allows us to reuse the existing workflow engine
        
        workflow_definition = reusable_workflow.workflow_definition
        
        # Use the workflow engine to execute the reusable workflow
        # We'll need to create a mock workflow object for this
        from workflows.models import Workflow
        
        # Create temporary workflow (not saved to DB)
        temp_workflow = Workflow(
            name=f"[Reusable] {reusable_workflow.name}",
            workflow_definition=workflow_definition
        )
        
        # Execute using the workflow engine
        # Note: This is a simplified version - in practice, we'd want to
        # create a more sophisticated execution context
        
        nodes = workflow_definition.get('nodes', [])
        edges = workflow_definition.get('edges', [])
        
        # Build execution graph
        execution_graph = workflow_engine._build_execution_graph(nodes, edges)
        
        # Execute nodes in dependency order
        execution_results = {}
        completed_nodes = set()
        
        # Find start nodes (nodes with no dependencies)
        start_nodes = [
            node_id for node_id, node_data in execution_graph.items()
            if not node_data['dependencies'] or node_data['type'] == 'start'
        ]
        
        # Simple sequential execution for now
        # In practice, this would be more sophisticated with parallel execution
        for start_node_id in start_nodes:
            await self._execute_node_sequence(
                execution_graph, start_node_id, context, 
                execution_results, completed_nodes
            )
        
        return {
            'success': True,
            'execution_results': execution_results,
            'completed_nodes': list(completed_nodes)
        }
    
    async def _execute_node_sequence(
        self,
        execution_graph: Dict[str, Any],
        node_id: str,
        context: Dict[str, Any],
        execution_results: Dict[str, Any],
        completed_nodes: set
    ):
        """Execute a sequence of nodes starting from the given node"""
        
        if node_id in completed_nodes:
            return
        
        node_data = execution_graph[node_id]
        
        # Check if all dependencies are completed
        for dep_id in node_data['dependencies']:
            if dep_id not in completed_nodes:
                return  # Wait for dependencies
        
        # Execute the node
        if node_data['type'] not in ['start', 'end']:
            # Get the appropriate node processor
            processor = workflow_engine.node_processors.get(node_data['type'])
            if processor:
                try:
                    result = await processor(node_data, context)
                    execution_results[node_id] = result
                    
                    # Update context with node results
                    context[f'node_{node_id}'] = result
                    
                except Exception as e:
                    execution_results[node_id] = {
                        'success': False,
                        'error': str(e)
                    }
        
        completed_nodes.add(node_id)
        
        # Execute dependent nodes
        for dependent_id in node_data['dependents']:
            await self._execute_node_sequence(
                execution_graph, dependent_id, context,
                execution_results, completed_nodes
            )
    
    async def _map_outputs(
        self, 
        execution_result: Dict[str, Any], 
        output_mappings: list,
        output_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map execution results to output format"""
        
        outputs = {}
        execution_results = execution_result.get('execution_results', {})
        
        # If no specific output mappings provided, try to extract from final nodes
        if not output_mappings:
            # Look for end nodes or nodes that match output schema
            schema_properties = output_schema.get('properties', {})
            for prop_name in schema_properties.keys():
                # Try to find this property in any execution result
                for node_id, node_result in execution_results.items():
                    if isinstance(node_result, dict) and prop_name in node_result:
                        outputs[prop_name] = node_result[prop_name]
                        break
        else:
            # Use explicit output mappings
            for output_key in output_mappings:
                # Look for this output in execution results
                for node_id, node_result in execution_results.items():
                    if isinstance(node_result, dict) and output_key in node_result:
                        outputs[output_key] = node_result[output_key]
                        break
        
        # Validate outputs against schema
        try:
            jsonschema.validate(outputs, output_schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"Output validation failed: {e.message}")
        
        return outputs
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for reusable workflow node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        # Add reusable workflow specific data
        checkpoint.update({
            'workflow_name': node_config['data'].get('workflow_name'),
            'version': node_config['data'].get('version'),
            'input_data': await self._prepare_reusable_inputs(
                node_config['data'].get('inputs', {}), 
                context,
                {}  # We don't have schema here, but this is for checkpoint
            )
        })
        
        return checkpoint