"""
Sub-Workflow Node Processor - Execute child workflows within parent workflows
"""
import logging
from typing import Dict, Any
from asgiref.sync import sync_to_async
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class SubWorkflowProcessor(AsyncNodeProcessor):
    """Process sub-workflow execution nodes"""
    
    def __init__(self):
        super().__init__()
        self.node_type = "SUB_WORKFLOW"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process sub-workflow call node"""
        
        node_data = node_config.get('data', {})
        
        # Extract configuration
        sub_workflow_id = node_data.get('sub_workflow_id')
        input_mapping = node_data.get('input_mapping', {})
        output_mapping = node_data.get('output_mapping', {})
        inherit_context = node_data.get('inherit_context', True)
        wait_for_completion = node_data.get('wait_for_completion', True)
        timeout_minutes = node_data.get('timeout_minutes', 60)
        
        # Get execution context
        execution = context.get('execution')
        if not execution:
            raise ValueError("Execution context required for sub-workflow node")
        
        # Validate sub-workflow ID
        if not sub_workflow_id:
            raise ValueError("Sub-workflow node requires sub_workflow_id")
        
        try:
            # Get sub-workflow
            from workflows.models import Workflow
            sub_workflow = await sync_to_async(Workflow.objects.get)(id=sub_workflow_id)
            
            # Check if sub-workflow can be executed
            if not await sync_to_async(sub_workflow.can_execute)():
                raise ValueError(f"Sub-workflow {sub_workflow.name} cannot be executed")
            
            # Prepare sub-workflow context
            sub_context = await self._prepare_sub_workflow_context(
                context, input_mapping, inherit_context
            )
            
            # Execute sub-workflow
            if wait_for_completion:
                result = await self._execute_sub_workflow_sync(
                    sub_workflow=sub_workflow,
                    trigger_data=sub_context,
                    triggered_by=execution.triggered_by,
                    timeout_minutes=timeout_minutes
                )
            else:
                result = await self._execute_sub_workflow_async(
                    sub_workflow=sub_workflow,
                    trigger_data=sub_context,
                    triggered_by=execution.triggered_by
                )
            
            # Apply output mapping if specified
            if output_mapping and result.get('success'):
                result = await self._apply_output_mapping(result, output_mapping)
            
            return result
            
        except Exception as e:
            logger.error(f"Sub-workflow execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'sub_workflow_id': sub_workflow_id
            }
    
    async def _prepare_sub_workflow_context(
        self, 
        parent_context: Dict[str, Any], 
        input_mapping: Dict[str, str],
        inherit_context: bool
    ) -> Dict[str, Any]:
        """Prepare context for sub-workflow execution"""
        
        sub_context = {}
        
        # Inherit parent context if requested
        if inherit_context:
            # Filter out internal keys
            sub_context = {
                k: v for k, v in parent_context.items() 
                if not k.startswith('_') and k not in ['execution']
            }
        
        # Apply input mapping
        for sub_key, parent_path in input_mapping.items():
            value = self._get_nested_value(parent_context, parent_path)
            if value is not None:
                sub_context[sub_key] = value
        
        return sub_context
    
    async def _execute_sub_workflow_sync(
        self, 
        sub_workflow, 
        trigger_data: Dict[str, Any], 
        triggered_by,
        timeout_minutes: int
    ) -> Dict[str, Any]:
        """Execute sub-workflow synchronously and wait for completion"""
        
        try:
            # Import here to avoid circular imports
            from workflows.engine import WorkflowEngine
            engine = WorkflowEngine()
            
            # Execute sub-workflow
            sub_execution = await engine.execute_workflow(
                workflow=sub_workflow,
                trigger_data=trigger_data,
                triggered_by=triggered_by
            )
            
            from workflows.models import ExecutionStatus
            
            return {
                'success': sub_execution.status == ExecutionStatus.SUCCESS,
                'sub_execution_id': str(sub_execution.id),
                'sub_workflow_id': str(sub_workflow.id),
                'sub_workflow_name': sub_workflow.name,
                'status': sub_execution.status,
                'final_output': sub_execution.execution_context.get('final_output', {}),
                'error_message': sub_execution.error_message,
                'execution_time_ms': self._calculate_execution_time(sub_execution),
                'completed_at': sub_execution.completed_at.isoformat() if sub_execution.completed_at else None
            }
            
        except Exception as e:
            logger.error(f"Synchronous sub-workflow execution failed: {e}")
            raise
    
    async def _execute_sub_workflow_async(
        self, 
        sub_workflow, 
        trigger_data: Dict[str, Any], 
        triggered_by
    ) -> Dict[str, Any]:
        """Execute sub-workflow asynchronously without waiting"""
        
        try:
            # Import here to avoid circular imports
            from workflows.engine import WorkflowEngine
            from workflows.models import ExecutionStatus
            
            engine = WorkflowEngine()
            
            # Start sub-workflow execution (don't await completion)
            from workflows.models import WorkflowExecution
            
            # Create execution instance but don't run it yet
            sub_execution = await sync_to_async(WorkflowExecution.objects.create)(
                workflow=sub_workflow,
                trigger_data=trigger_data,
                triggered_by=triggered_by,
                status=ExecutionStatus.PENDING
            )
            
            # TODO: Queue the execution for background processing
            # This would typically use Celery or similar task queue
            
            return {
                'success': True,
                'sub_execution_id': str(sub_execution.id),
                'sub_workflow_id': str(sub_workflow.id),
                'sub_workflow_name': sub_workflow.name,
                'status': 'queued',
                'async_execution': True,
                'message': 'Sub-workflow queued for asynchronous execution'
            }
            
        except Exception as e:
            logger.error(f"Asynchronous sub-workflow execution failed: {e}")
            raise
    
    async def _apply_output_mapping(
        self, 
        sub_workflow_result: Dict[str, Any], 
        output_mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """Apply output mapping to sub-workflow results"""
        
        mapped_output = {}
        final_output = sub_workflow_result.get('final_output', {})
        
        for target_key, source_path in output_mapping.items():
            value = self._get_nested_value(final_output, source_path)
            if value is not None:
                mapped_output[target_key] = value
        
        # Merge mapped outputs with original result
        result = {**sub_workflow_result}
        result['mapped_output'] = mapped_output
        
        return result
    
    def _calculate_execution_time(self, execution) -> int:
        """Calculate execution time in milliseconds"""
        
        if execution.completed_at and execution.created_at:
            delta = execution.completed_at - execution.created_at
            return int(delta.total_seconds() * 1000)
        
        return 0
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate sub-workflow node inputs"""
        node_data = node_config.get('data', {})
        
        # Check required fields
        if not node_data.get('sub_workflow_id'):
            return False
        
        # Validate input mapping
        input_mapping = node_data.get('input_mapping', {})
        if not isinstance(input_mapping, dict):
            return False
        
        # Validate output mapping
        output_mapping = node_data.get('output_mapping', {})
        if not isinstance(output_mapping, dict):
            return False
        
        # Validate timeout
        timeout_minutes = node_data.get('timeout_minutes', 60)
        if not isinstance(timeout_minutes, (int, float)) or timeout_minutes <= 0:
            return False
        
        # Validate boolean flags
        for flag in ['inherit_context', 'wait_for_completion']:
            value = node_data.get(flag)
            if value is not None and not isinstance(value, bool):
                return False
        
        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for sub-workflow node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        node_data = node_config.get('data', {})
        
        # Get sub-workflow info safely
        sub_workflow_name = 'unknown'
        try:
            sub_workflow_id = node_data.get('sub_workflow_id')
            if sub_workflow_id:
                from workflows.models import Workflow
                sub_workflow = await sync_to_async(Workflow.objects.get)(id=sub_workflow_id)
                sub_workflow_name = sub_workflow.name
        except:
            pass
        
        checkpoint.update({
            'sub_workflow_config': {
                'sub_workflow_id': node_data.get('sub_workflow_id'),
                'sub_workflow_name': sub_workflow_name,
                'input_mapping_count': len(node_data.get('input_mapping', {})),
                'output_mapping_count': len(node_data.get('output_mapping', {})),
                'inherit_context': node_data.get('inherit_context', True),
                'wait_for_completion': node_data.get('wait_for_completion', True),
                'timeout_minutes': node_data.get('timeout_minutes', 60)
            }
        })
        
        return checkpoint