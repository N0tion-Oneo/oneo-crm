"""
For Each Node Processor - Parallel processing of items with sub-workflows
"""
import asyncio
import logging
from typing import Dict, Any, List
from asgiref.sync import sync_to_async
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class ForEachProcessor(AsyncNodeProcessor):
    """Process for-each loop nodes with configurable parallel processing"""
    
    def __init__(self):
        super().__init__()
        self.node_type = "FOR_EACH"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process for-each loop node with parallel processing"""
        
        node_data = node_config.get('data', {})
        items_path = node_data.get('items_path', '')
        max_concurrency = node_data.get('max_concurrency', 5)
        sub_workflow_id = node_data.get('sub_workflow_id')
        processing_mode = node_data.get('processing_mode', 'sub_workflow')  # 'sub_workflow' or 'reusable_workflow'
        
        # Get items to process
        items = self._get_nested_value(context, items_path)
        
        if not isinstance(items, list):
            raise ValueError(f"Items path '{items_path}' did not resolve to a list")
        
        if not items:
            return {
                'success': True,
                'items_processed': 0,
                'results': [],
                'message': 'No items to process'
            }
        
        # Choose processing method based on mode
        if processing_mode == 'sub_workflow':
            return await self._process_with_sub_workflow(
                items, sub_workflow_id, max_concurrency, context, node_data
            )
        elif processing_mode == 'reusable_workflow':
            return await self._process_with_reusable_workflow(
                items, node_data, max_concurrency, context
            )
        else:
            # Simple item processing without workflows
            return await self._process_items_simple(items, node_data, context)
    
    async def _process_with_sub_workflow(
        self, 
        items: List[Any], 
        sub_workflow_id: str, 
        max_concurrency: int, 
        context: Dict[str, Any],
        node_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process items using sub-workflow execution"""
        
        if not sub_workflow_id:
            raise ValueError("sub_workflow_id required for sub_workflow processing mode")
        
        # Get execution context
        execution = context.get('execution')
        if not execution:
            raise ValueError("Execution context required for sub-workflow processing")
        
        try:
            from workflows.models import Workflow
            sub_workflow = await sync_to_async(Workflow.objects.get)(id=sub_workflow_id)
        except Exception:
            raise ValueError(f"Sub-workflow {sub_workflow_id} not found")
        
        # Process items in parallel with semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def process_single_item(item, index):
            async with semaphore:
                return await self._execute_sub_workflow_for_item(
                    sub_workflow, item, index, context, execution
                )
        
        # Execute all items in parallel
        tasks = [process_single_item(item, i) for i, item in enumerate(items)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        return self._compile_results(results, items, 'sub_workflow')
    
    async def _process_with_reusable_workflow(
        self, 
        items: List[Any], 
        node_data: Dict[str, Any], 
        max_concurrency: int, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process items using reusable workflow"""
        
        reusable_workflow_name = node_data.get('reusable_workflow_name')
        if not reusable_workflow_name:
            raise ValueError("reusable_workflow_name required for reusable_workflow processing mode")
        
        # Get reusable workflow processor
        from workflows.nodes.workflow.reusable import ReusableWorkflowProcessor
        reusable_processor = ReusableWorkflowProcessor()
        
        # Process items in parallel
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def process_single_item(item, index):
            async with semaphore:
                return await self._execute_reusable_workflow_for_item(
                    reusable_processor, reusable_workflow_name, item, index, context, node_data
                )
        
        # Execute all items in parallel
        tasks = [process_single_item(item, i) for i, item in enumerate(items)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        return self._compile_results(results, items, 'reusable_workflow')
    
    async def _process_items_simple(
        self, 
        items: List[Any], 
        node_data: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simple item processing without workflows"""
        
        processing_function = node_data.get('processing_function', 'identity')
        
        processed_items = []
        
        for i, item in enumerate(items):
            try:
                if processing_function == 'identity':
                    # Just pass through the item
                    processed_item = item
                elif processing_function == 'format':
                    # Format item with context
                    template = node_data.get('format_template', '{item}')
                    item_context = {**context, 'item': item, 'index': i}
                    processed_item = template.format(**item_context)
                elif processing_function == 'extract_field':
                    # Extract specific field from item
                    field_name = node_data.get('field_name', '')
                    if isinstance(item, dict) and field_name in item:
                        processed_item = item[field_name]
                    else:
                        processed_item = None
                else:
                    processed_item = item
                
                processed_items.append({
                    'original_item': item,
                    'processed_item': processed_item,
                    'index': i,
                    'success': True
                })
                
            except Exception as e:
                processed_items.append({
                    'original_item': item,
                    'index': i,
                    'success': False,
                    'error': str(e)
                })
        
        success_count = sum(1 for result in processed_items if result.get('success'))
        
        return {
            'success': True,
            'items_processed': len(items),
            'success_count': success_count,
            'failure_count': len(items) - success_count,
            'results': processed_items,
            'processing_mode': 'simple'
        }
    
    async def _execute_sub_workflow_for_item(
        self, 
        sub_workflow, 
        item: Any, 
        index: int, 
        context: Dict[str, Any], 
        execution
    ) -> Dict[str, Any]:
        """Execute sub-workflow for a single item"""
        
        try:
            # Create item-specific context
            item_context = {
                **context,
                'current_item': item,
                'current_index': index,
                'parent_execution_id': str(execution.id)
            }
            
            # Import here to avoid circular imports
            from workflows.engine import WorkflowEngine
            engine = WorkflowEngine()
            
            # Execute sub-workflow
            sub_execution = await engine.execute_workflow(
                workflow=sub_workflow,
                trigger_data=item_context,
                triggered_by=execution.triggered_by
            )
            
            from workflows.models import ExecutionStatus
            
            return {
                'item': item,
                'index': index,
                'success': sub_execution.status == ExecutionStatus.SUCCESS,
                'execution_id': str(sub_execution.id),
                'sub_workflow_id': str(sub_workflow.id),
                'error_message': sub_execution.error_message if sub_execution.error_message else None
            }
            
        except Exception as e:
            logger.error(f"Sub-workflow execution failed for item {index}: {e}")
            return {
                'item': item,
                'index': index,
                'success': False,
                'error': str(e)
            }
    
    async def _execute_reusable_workflow_for_item(
        self, 
        reusable_processor, 
        workflow_name: str, 
        item: Any, 
        index: int, 
        context: Dict[str, Any],
        node_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute reusable workflow for a single item"""
        
        try:
            # Create item-specific context
            item_context = {
                **context,
                'current_item': item,
                'current_index': index
            }
            
            # Prepare reusable workflow configuration
            reusable_config = {
                'type': 'REUSABLE_WORKFLOW',
                'data': {
                    'workflow_name': workflow_name,
                    'inputs': node_data.get('item_inputs', {}),
                    **node_data.get('reusable_workflow_config', {})
                }
            }
            
            # Execute reusable workflow
            result = await reusable_processor.process(reusable_config, item_context)
            
            return {
                'item': item,
                'index': index,
                'success': result.get('success', False),
                'workflow_result': result,
                'workflow_name': workflow_name
            }
            
        except Exception as e:
            logger.error(f"Reusable workflow execution failed for item {index}: {e}")
            return {
                'item': item,
                'index': index,
                'success': False,
                'error': str(e)
            }
    
    def _compile_results(self, results: List[Any], items: List[Any], processing_mode: str) -> Dict[str, Any]:
        """Compile and analyze processing results"""
        
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
            'success': True,
            'items_processed': len(items),
            'success_count': success_count,
            'failure_count': len(items) - success_count,
            'success_rate': (success_count / len(items)) * 100 if items else 0,
            'results': processed_results,
            'processing_mode': processing_mode
        }
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate for-each node inputs"""
        node_data = node_config.get('data', {})
        
        # Check required fields
        if not node_data.get('items_path'):
            return False
        
        # Validate processing mode
        processing_mode = node_data.get('processing_mode', 'sub_workflow')
        valid_modes = ['sub_workflow', 'reusable_workflow', 'simple']
        if processing_mode not in valid_modes:
            return False
        
        # Mode-specific validation
        if processing_mode == 'sub_workflow':
            if not node_data.get('sub_workflow_id'):
                return False
        elif processing_mode == 'reusable_workflow':
            if not node_data.get('reusable_workflow_name'):
                return False
        
        # Validate max_concurrency
        max_concurrency = node_data.get('max_concurrency', 5)
        if not isinstance(max_concurrency, int) or max_concurrency <= 0:
            return False
        
        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for for-each node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        node_data = node_config.get('data', {})
        
        # Resolve items for checkpoint
        items_path = node_data.get('items_path', '')
        items = self._get_nested_value(context, items_path)
        
        checkpoint.update({
            'items_path': items_path,
            'items_count': len(items) if isinstance(items, list) else 0,
            'processing_mode': node_data.get('processing_mode', 'sub_workflow'),
            'max_concurrency': node_data.get('max_concurrency', 5),
            'sub_workflow_id': node_data.get('sub_workflow_id'),
            'reusable_workflow_name': node_data.get('reusable_workflow_name')
        })
        
        return checkpoint