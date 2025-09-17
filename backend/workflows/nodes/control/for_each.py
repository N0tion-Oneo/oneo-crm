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

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["items_path", "processing_mode"],
        "properties": {
            "items_path": {
                "type": "string",
                "description": "Path to array of items in context",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "{{records}} or node_123.results"
                }
            },
            "processing_mode": {
                "type": "string",
                "enum": ["sub_workflow", "reusable_workflow", "simple"],
                "default": "simple",
                "description": "How to process each item",
                "ui_hints": {
                    "widget": "select"
                }
            },
            "max_concurrency": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "default": 5,
                "description": "Maximum parallel processing threads"
            },
            "sub_workflow_id": {
                "type": "string",
                "description": "Sub-workflow to execute for each item",
                "ui_hints": {
                    "widget": "workflow_select",
                    "show_when": {"processing_mode": "sub_workflow"}
                }
            },
            "reusable_workflow_name": {
                "type": "string",
                "description": "Name of reusable workflow",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "process_lead",
                    "show_when": {"processing_mode": "reusable_workflow"}
                }
            },
            "processing_function": {
                "type": "string",
                "enum": ["identity", "format", "extract_field"],
                "default": "identity",
                "description": "Simple processing function",
                "ui_hints": {
                    "widget": "radio",
                    "show_when": {"processing_mode": "simple"}
                }
            },
            "format_template": {
                "type": "string",
                "description": "Template for formatting items",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "Item {index}: {item}",
                    "show_when": {"processing_function": "format"}
                }
            },
            "field_name": {
                "type": "string",
                "description": "Field to extract from each item",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "email",
                    "show_when": {"processing_function": "extract_field"}
                }
            },
            "continue_on_error": {
                "type": "boolean",
                "default": True,
                "description": "Continue processing if an item fails"
            },
            "item_timeout_seconds": {
                "type": "integer",
                "minimum": 1,
                "maximum": 3600,
                "default": 300,
                "description": "Timeout per item (seconds)"
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "for_each"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process for-each loop node with parallel processing"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        items_path = config.get('items_path', '')
        max_concurrency = config.get('max_concurrency', 5)
        sub_workflow_id = config.get('sub_workflow_id')
        processing_mode = config.get('processing_mode', 'simple')
        
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

        config = node_data.get('config', {})
        reusable_workflow_name = config.get('reusable_workflow_name')
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

        config = node_data.get('config', {})
        processing_function = config.get('processing_function', 'identity')
        
        processed_items = []
        
        for i, item in enumerate(items):
            try:
                if processing_function == 'identity':
                    # Just pass through the item
                    processed_item = item
                elif processing_function == 'format':
                    # Format item with context
                    template = config.get('format_template', '{item}')
                    item_context = {**context, 'item': item, 'index': i}
                    processed_item = template.format(**item_context)
                elif processing_function == 'extract_field':
                    # Extract specific field from item
                    field_name = config.get('field_name', '')
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
            
            # Prepare sub-workflow configuration
            reusable_config = {
                'type': 'SUB_WORKFLOW',
                'data': {
                    'workflow_name': workflow_name,
                    'is_reusable': True,
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
    
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for for-each node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Resolve items for checkpoint
        items_path = config.get('items_path', '')
        items = self._get_nested_value(context, items_path)
        
        checkpoint.update({
            'items_path': items_path,
            'items_count': len(items) if isinstance(items, list) else 0,
            'processing_mode': config.get('processing_mode', 'simple'),
            'max_concurrency': config.get('max_concurrency', 5),
            'sub_workflow_id': config.get('sub_workflow_id'),
            'reusable_workflow_name': config.get('reusable_workflow_name')
        })
        
        return checkpoint