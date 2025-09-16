"""
Management command to migrate existing workflows to use trigger nodes
"""
import json
import uuid
from django.core.management.base import BaseCommand
from django.db import transaction
from workflows.models import Workflow, WorkflowTrigger
from workflows.trigger_registry import trigger_registry

class Command(BaseCommand):
    help = 'Migrate existing workflows to use trigger nodes instead of WorkflowTrigger models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving them',
        )
        parser.add_argument(
            '--workflow-id',
            type=str,
            help='Migrate specific workflow by ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        workflow_id = options['workflow_id']

        if workflow_id:
            workflows = Workflow.objects.filter(id=workflow_id)
        else:
            workflows = Workflow.objects.all()

        self.stdout.write(f"Found {workflows.count()} workflows to process")

        migrated_count = 0
        skipped_count = 0

        for workflow in workflows:
            with transaction.atomic():
                result = self.migrate_workflow(workflow, dry_run)
                if result == 'migrated':
                    migrated_count += 1
                elif result == 'skipped':
                    skipped_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Migration complete: {migrated_count} workflows migrated, {skipped_count} skipped"
        ))

    def migrate_workflow(self, workflow, dry_run):
        """Migrate a single workflow to use trigger nodes"""

        # Skip if already has trigger nodes
        if workflow.workflow_definition:
            nodes = workflow.workflow_definition.get('nodes', [])
            has_trigger_nodes = any(
                'trigger' in node.get('type', '').lower()
                for node in nodes
            )
            if has_trigger_nodes:
                self.stdout.write(f"  Skipping {workflow.name} - already has trigger nodes")
                return 'skipped'

        # Get existing triggers
        triggers = WorkflowTrigger.objects.filter(workflow=workflow)

        if not triggers.exists():
            # No triggers to migrate, but add a manual trigger node as default
            trigger_node = self.create_manual_trigger_node()
            if not dry_run:
                self.add_trigger_node_to_workflow(workflow, trigger_node)
                self.stdout.write(self.style.SUCCESS(
                    f"  Added default manual trigger to {workflow.name}"
                ))
            else:
                self.stdout.write(
                    f"  [DRY RUN] Would add manual trigger to {workflow.name}"
                )
            return 'migrated'

        # Convert each WorkflowTrigger to a trigger node
        for trigger in triggers:
            trigger_node = self.convert_trigger_to_node(trigger)

            if dry_run:
                self.stdout.write(
                    f"  [DRY RUN] Would add {trigger.trigger_type} trigger node to {workflow.name}"
                )
            else:
                self.add_trigger_node_to_workflow(workflow, trigger_node)
                # Mark old trigger as migrated (but don't delete yet)
                trigger.is_migrated = True
                trigger.save()
                self.stdout.write(self.style.SUCCESS(
                    f"  Added {trigger.trigger_type} trigger node to {workflow.name}"
                ))

        # Register workflow with new trigger registry
        if not dry_run:
            trigger_registry.register_workflow(workflow)
            self.stdout.write(f"  Registered {workflow.name} with trigger registry")

        return 'migrated'

    def convert_trigger_to_node(self, trigger):
        """Convert a WorkflowTrigger model to a trigger node definition"""

        node_type_map = {
            'manual': 'trigger_manual',
            'form_submission': 'trigger_form_submitted',
            'schedule': 'trigger_schedule',
            'webhook': 'trigger_webhook',
            'record_created': 'trigger_record_created',
            'record_updated': 'trigger_record_updated',
            'email': 'trigger_email_received',
        }

        node_type = node_type_map.get(trigger.trigger_type, 'trigger_manual')

        # Create trigger node
        node = {
            'id': str(uuid.uuid4()),
            'type': node_type,
            'position': {'x': 100, 'y': 100},  # Default position
            'data': {
                'label': trigger.name or f"{trigger.trigger_type} Trigger",
                'config': trigger.trigger_config or {},
                'migrated_from': str(trigger.id)
            }
        }

        # Add specific configuration based on trigger type
        if trigger.trigger_type == 'form_submission':
            node['data']['config']['pipeline_id'] = trigger.trigger_config.get('pipeline_id')
            node['data']['config']['form_mode'] = trigger.trigger_config.get('form_mode', 'create')
        elif trigger.trigger_type == 'schedule':
            node['data']['config']['schedule'] = trigger.trigger_config.get('cron_expression')
        elif trigger.trigger_type == 'webhook':
            node['data']['config']['path'] = trigger.trigger_config.get('webhook_path')

        return node

    def create_manual_trigger_node(self):
        """Create a default manual trigger node"""
        return {
            'id': str(uuid.uuid4()),
            'type': 'trigger_manual',
            'position': {'x': 100, 'y': 100},
            'data': {
                'label': 'Manual Trigger',
                'config': {}
            }
        }

    def add_trigger_node_to_workflow(self, workflow, trigger_node):
        """Add a trigger node to the workflow definition"""

        if not workflow.workflow_definition:
            workflow.workflow_definition = {'nodes': [], 'edges': []}

        nodes = workflow.workflow_definition.get('nodes', [])
        edges = workflow.workflow_definition.get('edges', [])

        # Add the trigger node
        nodes.insert(0, trigger_node)

        # Connect trigger node to existing entry nodes
        entry_nodes = self.find_entry_nodes(nodes[1:], edges)  # Skip the trigger we just added

        for entry_node in entry_nodes:
            edge = {
                'id': str(uuid.uuid4()),
                'source': trigger_node['id'],
                'target': entry_node['id'],
                'sourceHandle': 'source',
                'targetHandle': 'target'
            }
            edges.append(edge)

        # Update workflow definition
        workflow.workflow_definition['nodes'] = nodes
        workflow.workflow_definition['edges'] = edges
        workflow.save()

    def find_entry_nodes(self, nodes, edges):
        """Find nodes with no incoming edges (entry points)"""

        # Get all node IDs that have incoming edges
        target_node_ids = {edge['target'] for edge in edges}

        # Entry nodes are those without incoming edges
        entry_nodes = [
            node for node in nodes
            if node['id'] not in target_node_ids
        ]

        # If no entry nodes found, return the first node
        if not entry_nodes and nodes:
            entry_nodes = [nodes[0]]

        return entry_nodes