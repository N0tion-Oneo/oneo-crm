"""
Workflow Trigger Registry
Manages the registration and execution of workflow triggers based on nodes
"""
import logging
from typing import Dict, List, Optional, Any
from django.db.models import Q
from workflows.models import Workflow

logger = logging.getLogger(__name__)


class WorkflowTriggerRegistry:
    """
    Central registry for workflow triggers.
    Scans workflow definitions for trigger nodes and manages their execution.
    """

    def __init__(self):
        self._registry: Dict[str, List[Dict]] = {
            'form_submitted': [],
            'schedule': [],
            'webhook': [],
            'record_created': [],
            'record_updated': [],
            'email_received': [],
        }

    def register_workflow(self, workflow: Workflow) -> None:
        """
        Scan a workflow for trigger nodes and register them.
        Called when a workflow is saved/updated.
        """
        if not workflow.workflow_definition:
            return

        nodes = workflow.workflow_definition.get('nodes', [])

        # Clear existing registrations for this workflow
        self._unregister_workflow(workflow.id)

        # Find and register trigger nodes
        for node in nodes:
            node_type = node.get('type', '').lower()

            if 'trigger' in node_type:
                self._register_trigger_node(workflow, node)

    def _register_trigger_node(self, workflow: Workflow, node: Dict) -> None:
        """Register a single trigger node"""
        node_type = node.get('type', '').lower()
        node_data = node.get('data', {})

        trigger_info = {
            'workflow_id': str(workflow.id),
            'workflow_name': workflow.name,
            'node_id': node.get('id'),
            'node_config': node_data,
            'is_active': workflow.status == 'active'
        }

        if node_type == 'trigger_form_submitted':
            # Register form trigger
            pipeline_id = node_data.get('pipeline_id')
            form_mode = node_data.get('form_mode')

            if pipeline_id:
                trigger_info['pipeline_id'] = pipeline_id
                trigger_info['form_mode'] = form_mode
                self._registry['form_submitted'].append(trigger_info)
                logger.info(f"Registered form trigger for workflow {workflow.name}")

        elif node_type == 'trigger_schedule':
            # Register schedule trigger
            schedule = node_data.get('schedule')
            if schedule:
                trigger_info['schedule'] = schedule
                self._registry['schedule'].append(trigger_info)
                logger.info(f"Registered schedule trigger for workflow {workflow.name}")

        elif node_type == 'trigger_webhook':
            # Register webhook trigger
            webhook_path = node_data.get('path')
            if webhook_path:
                trigger_info['path'] = webhook_path
                self._registry['webhook'].append(trigger_info)
                logger.info(f"Registered webhook trigger for workflow {workflow.name}")

    def _unregister_workflow(self, workflow_id: str) -> None:
        """Remove all trigger registrations for a workflow"""
        for trigger_type in self._registry:
            self._registry[trigger_type] = [
                t for t in self._registry[trigger_type]
                if t['workflow_id'] != workflow_id
            ]

    def find_workflows_for_trigger(self, trigger_type: str, **kwargs) -> List[Dict]:
        """
        Find workflows that should be triggered by an event.

        Args:
            trigger_type: Type of trigger (form_submitted, schedule, etc.)
            **kwargs: Trigger-specific parameters to match

        Returns:
            List of workflow info dicts that should be triggered
        """
        matching_workflows = []

        for trigger_info in self._registry.get(trigger_type, []):
            if not trigger_info['is_active']:
                continue

            # Check if this trigger matches the event
            if self._matches_trigger(trigger_type, trigger_info, kwargs):
                matching_workflows.append(trigger_info)

        return matching_workflows

    def _matches_trigger(self, trigger_type: str, trigger_info: Dict, event_data: Dict) -> bool:
        """Check if a trigger matches an event"""

        if trigger_type == 'form_submitted':
            # Match by pipeline_id and optionally form_mode
            return (
                trigger_info.get('pipeline_id') == event_data.get('pipeline_id') and
                (not trigger_info.get('form_mode') or
                 trigger_info.get('form_mode') == event_data.get('form_mode'))
            )

        elif trigger_type == 'webhook':
            # Match by webhook path
            return trigger_info.get('path') == event_data.get('path')

        elif trigger_type == 'schedule':
            # Schedule matching would be handled by cron
            return True

        return False

    async def trigger_workflows(self, trigger_type: str, trigger_data: Dict) -> List[str]:
        """
        Trigger all workflows matching an event.

        Args:
            trigger_type: Type of trigger event
            trigger_data: Data from the trigger event

        Returns:
            List of execution IDs
        """
        from workflows.engine import workflow_engine

        matching_workflows = self.find_workflows_for_trigger(
            trigger_type,
            **trigger_data
        )

        execution_ids = []

        for trigger_info in matching_workflows:
            try:
                # Load the workflow
                workflow = await Workflow.objects.select_related('tenant').aget(
                    id=trigger_info['workflow_id']
                )

                # Prepare execution context with trigger node as start
                execution_context = {
                    'trigger_type': trigger_type,
                    'trigger_node_id': trigger_info['node_id'],
                    'trigger_data': trigger_data
                }

                # Execute the workflow starting from the trigger node
                execution = await workflow_engine.execute_workflow(
                    workflow=workflow,
                    trigger_data=execution_context,
                    triggered_by=None,  # System trigger
                    start_node_id=trigger_info['node_id']  # Start from trigger node
                )

                execution_ids.append(str(execution.id))
                logger.info(f"Triggered workflow {workflow.name} from {trigger_type}")

            except Exception as e:
                logger.error(f"Failed to trigger workflow {trigger_info['workflow_id']}: {e}")

        return execution_ids


# Global registry instance
trigger_registry = WorkflowTriggerRegistry()