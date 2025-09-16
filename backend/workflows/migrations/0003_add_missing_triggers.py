# Generated manually to add missing triggers
from django.db import migrations


def create_missing_triggers(apps, schema_editor):
    """Create WorkflowTrigger records for workflows that don't have them"""
    Workflow = apps.get_model('workflows', 'Workflow')
    WorkflowTrigger = apps.get_model('workflows', 'WorkflowTrigger')

    # Get schema name
    schema = schema_editor.connection.schema_name

    # Skip public schema
    if schema == 'public':
        return

    # Process all workflows that don't have triggers
    for workflow in Workflow.objects.all():
        # Check if workflow already has triggers
        if not WorkflowTrigger.objects.filter(workflow=workflow).exists():
            # Create a default trigger based on workflow's trigger_type field
            WorkflowTrigger.objects.create(
                tenant=workflow.tenant,
                workflow=workflow,
                trigger_type=workflow.trigger_type or 'manual',
                name=f"{workflow.name} - Primary Trigger",
                description=f"Auto-generated trigger for {workflow.name}",
                trigger_config=workflow.trigger_config or {},
                is_active=(workflow.status == 'active')
            )
            print(f"Created trigger for workflow: {workflow.name}")


def reverse_func(apps, schema_editor):
    """Remove auto-generated triggers"""
    WorkflowTrigger = apps.get_model('workflows', 'WorkflowTrigger')

    # Remove triggers with auto-generated description
    WorkflowTrigger.objects.filter(
        description__startswith="Auto-generated trigger for"
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('workflows', '0002_add_tenant_field'),
    ]

    operations = [
        migrations.RunPython(create_missing_triggers, reverse_func),
    ]