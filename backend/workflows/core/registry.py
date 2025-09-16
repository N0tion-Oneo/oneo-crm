"""
Node and Trigger Registry for workflow system
Centralized registration and discovery of processors
"""
import importlib
import inspect
from typing import Dict, Type, Any, List
from django.conf import settings
from workflows.nodes.base import BaseNodeProcessor
from workflows.models import WorkflowNodeType


class NodeRegistry:
    """Registry for workflow node processors"""
    
    def __init__(self):
        self._processors: Dict[str, BaseNodeProcessor] = {}
        self._processor_classes: Dict[str, Type[BaseNodeProcessor]] = {}
        self._auto_discover_processors()
    
    def register_processor(self, node_type: str, processor_class: Type[BaseNodeProcessor]):
        """Register a node processor class"""
        if not issubclass(processor_class, BaseNodeProcessor):
            raise ValueError(f"Processor must inherit from BaseNodeProcessor")
        
        self._processor_classes[node_type] = processor_class
        self._processors[node_type] = processor_class()
    
    def get_processor(self, node_type: str) -> BaseNodeProcessor:
        """Get processor instance for node type"""
        if node_type not in self._processors:
            raise ValueError(f"No processor registered for node type: {node_type}")
        return self._processors[node_type]
    
    def get_available_node_types(self) -> List[str]:
        """Get list of all registered node types"""
        return list(self._processors.keys())
    
    def _auto_discover_processors(self):
        """Automatically discover and register processors"""
        
        # Define processor modules to scan
        processor_modules = [
            # AI processors
            'workflows.nodes.ai.prompt',
            'workflows.nodes.ai.analysis',
            'workflows.nodes.ai.message_generator',
            'workflows.nodes.ai.response_evaluator',

            # Data processors
            'workflows.nodes.data.record_ops',
            'workflows.nodes.data.merge',

            # Control flow processors
            'workflows.nodes.control.condition',
            'workflows.nodes.control.for_each',
            'workflows.nodes.control.workflow_loop',

            # Communication processors
            'workflows.nodes.communication.email',
            'workflows.nodes.communication.linkedin',
            'workflows.nodes.communication.whatsapp',
            'workflows.nodes.communication.sms',
            'workflows.nodes.communication.sync',
            'workflows.nodes.communication.logging',
            'workflows.nodes.communication.analysis',
            'workflows.nodes.communication.ai_conversation_loop',

            # External integration processors
            'workflows.nodes.external.http',
            'workflows.nodes.external.webhook',

            # Workflow management processors
            'workflows.nodes.workflow.approval',
            'workflows.nodes.workflow.sub_workflow',
            'workflows.nodes.workflow.reusable',

            # CRM processors
            'workflows.nodes.crm.contact',
            'workflows.nodes.crm.status_update',

            # Utility processors
            'workflows.nodes.utility.wait',
            'workflows.nodes.utility.wait_advanced',
            'workflows.nodes.utility.notification',
            'workflows.nodes.utility.conversation_state',
        ]
        
        for module_name in processor_modules:
            try:
                self._discover_processors_in_module(module_name)
            except ImportError:
                # Module doesn't exist yet - that's okay during development
                continue
    
    def _discover_processors_in_module(self, module_name: str):
        """Discover processors in a specific module"""
        try:
            module = importlib.import_module(module_name)
            
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseNodeProcessor) and 
                    obj != BaseNodeProcessor and
                    hasattr(obj, 'node_type')):
                    
                    # Get the node type from the processor class
                    processor_instance = obj()
                    if processor_instance.node_type:
                        self.register_processor(processor_instance.node_type, obj)
                        
        except Exception as e:
            # Log the error but don't fail the entire registry
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to discover processors in {module_name}: {e}")


class TriggerRegistry:
    """Registry for workflow triggers"""
    
    def __init__(self):
        self._triggers: Dict[str, Any] = {}
        self._auto_discover_triggers()
    
    def register_trigger(self, trigger_type: str, trigger_class: Type):
        """Register a trigger class"""
        self._triggers[trigger_type] = trigger_class
    
    def get_trigger(self, trigger_type: str):
        """Get trigger class for trigger type"""
        if trigger_type not in self._triggers:
            raise ValueError(f"No trigger registered for type: {trigger_type}")
        return self._triggers[trigger_type]
    
    def get_available_trigger_types(self) -> List[str]:
        """Get list of all registered trigger types"""
        return list(self._triggers.keys())
    
    def _auto_discover_triggers(self):
        """Automatically discover and register triggers"""
        
        trigger_modules = [
            'workflows.triggers.time_based',
            'workflows.triggers.event_based',
            'workflows.triggers.webhook',
            'workflows.triggers.conditional',
            'workflows.triggers.api',
        ]
        
        for module_name in trigger_modules:
            try:
                self._discover_triggers_in_module(module_name)
            except ImportError:
                continue
    
    def _discover_triggers_in_module(self, module_name: str):
        """Discover triggers in a specific module"""
        try:
            module = importlib.import_module(module_name)
            
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    hasattr(obj, 'trigger_type')):
                    
                    # Register the trigger
                    trigger_instance = obj()
                    if hasattr(trigger_instance, 'trigger_type'):
                        self.register_trigger(trigger_instance.trigger_type, obj)
                        
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to discover triggers in {module_name}: {e}")


class TemplateRegistry:
    """Registry for workflow templates"""
    
    def __init__(self):
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._auto_discover_templates()
    
    def register_template(self, template_id: str, template_data: Dict[str, Any]):
        """Register a workflow template"""
        self._templates[template_id] = template_data
    
    def get_template(self, template_id: str) -> Dict[str, Any]:
        """Get template by ID"""
        if template_id not in self._templates:
            raise ValueError(f"No template found with ID: {template_id}")
        return self._templates[template_id]
    
    def get_available_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get all available templates"""
        return self._templates.copy()
    
    def get_templates_by_category(self, category: str) -> Dict[str, Dict[str, Any]]:
        """Get templates filtered by category"""
        return {
            template_id: template_data
            for template_id, template_data in self._templates.items()
            if template_data.get('category') == category
        }
    
    def _auto_discover_templates(self):
        """Automatically discover templates"""
        
        template_modules = [
            'workflows.templates.communication',
            'workflows.templates.crm',
            'workflows.templates.ats',
            'workflows.templates.cms',
            'workflows.templates.ecommerce',
        ]
        
        for module_name in template_modules:
            try:
                self._discover_templates_in_module(module_name)
            except ImportError:
                continue
    
    def _discover_templates_in_module(self, module_name: str):
        """Discover templates in a specific module"""
        try:
            module = importlib.import_module(module_name)
            
            # Look for template dictionaries and template functions
            for name, obj in inspect.getmembers(module):
                if isinstance(obj, dict) and name.endswith('_TEMPLATE'):
                    # Direct template dictionary
                    template_id = name.lower().replace('_template', '')
                    self.register_template(template_id, obj)
                elif callable(obj) and name.startswith('create_') and name.endswith('_template'):
                    # Template creation function
                    template_id = name.replace('create_', '').replace('_template', '')
                    try:
                        # Call the function to get template data
                        template_data = obj()
                        if isinstance(template_data, dict):
                            self.register_template(template_id, template_data)
                    except Exception:
                        # Skip if template creation fails
                        continue
                        
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to discover templates in {module_name}: {e}")


# Global registry instances
node_registry = NodeRegistry()
trigger_registry = TriggerRegistry()
template_registry = TemplateRegistry()


def get_node_processor(node_type: str) -> BaseNodeProcessor:
    """Get a node processor instance"""
    return node_registry.get_processor(node_type)


def get_available_node_types() -> List[str]:
    """Get all available node types"""
    return node_registry.get_available_node_types()


def register_node_processor(node_type: str, processor_class: Type[BaseNodeProcessor]):
    """Register a custom node processor"""
    node_registry.register_processor(node_type, processor_class)


def get_workflow_template(template_id: str) -> Dict[str, Any]:
    """Get a workflow template"""
    return template_registry.get_template(template_id)


def get_available_templates() -> Dict[str, Dict[str, Any]]:
    """Get all available workflow templates"""
    return template_registry.get_available_templates()