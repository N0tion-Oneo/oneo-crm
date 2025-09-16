# Generated migration for adding tenant field to workflow models

from django.db import migrations, models
import django.db.models.deletion


def set_default_tenant(apps, schema_editor):
    """Set default tenant for existing workflows (if any)"""
    Tenant = apps.get_model('tenants', 'Tenant')
    Workflow = apps.get_model('workflows', 'Workflow')
    WorkflowExecution = apps.get_model('workflows', 'WorkflowExecution')
    WorkflowExecutionLog = apps.get_model('workflows', 'WorkflowExecutionLog')
    WorkflowApproval = apps.get_model('workflows', 'WorkflowApproval')
    WorkflowSchedule = apps.get_model('workflows', 'WorkflowSchedule')
    WorkflowTemplate = apps.get_model('workflows', 'WorkflowTemplate')
    WorkflowVersion = apps.get_model('workflows', 'WorkflowVersion')
    WorkflowTrigger = apps.get_model('workflows', 'WorkflowTrigger')
    WorkflowAnalytics = apps.get_model('workflows', 'WorkflowAnalytics')
    WorkflowEvent = apps.get_model('workflows', 'WorkflowEvent')

    # Get or create a default tenant for existing data
    try:
        default_tenant = Tenant.objects.get(schema_name='public')
    except Tenant.DoesNotExist:
        # If no public tenant exists, try to get the first tenant
        default_tenant = Tenant.objects.first()
        if not default_tenant:
            # No tenants exist yet, migration will be run when first tenant is created
            return

    # Update existing records with default tenant
    Workflow.objects.filter(tenant__isnull=True).update(tenant=default_tenant)
    WorkflowExecution.objects.filter(tenant__isnull=True).update(tenant=default_tenant)
    WorkflowExecutionLog.objects.filter(tenant__isnull=True).update(tenant=default_tenant)
    WorkflowApproval.objects.filter(tenant__isnull=True).update(tenant=default_tenant)
    WorkflowSchedule.objects.filter(tenant__isnull=True).update(tenant=default_tenant)
    WorkflowTemplate.objects.filter(tenant__isnull=True).update(tenant=default_tenant)
    WorkflowVersion.objects.filter(tenant__isnull=True).update(tenant=default_tenant)
    WorkflowTrigger.objects.filter(tenant__isnull=True).update(tenant=default_tenant)
    WorkflowAnalytics.objects.filter(tenant__isnull=True).update(tenant=default_tenant)
    WorkflowEvent.objects.filter(tenant__isnull=True).update(tenant=default_tenant)


def reverse_set_default_tenant(apps, schema_editor):
    """Reverse operation - does nothing as we're removing the field"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
        ('workflows', '0001_initial'),
    ]

    operations = [
        # Add tenant field to Workflow (nullable first)
        migrations.AddField(
            model_name='workflow',
            name='tenant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflows',
                to='tenants.tenant'
            ),
        ),

        # Add tenant field to WorkflowExecution (nullable first)
        migrations.AddField(
            model_name='workflowexecution',
            name='tenant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflow_executions',
                to='tenants.tenant'
            ),
        ),

        # Add tenant field to WorkflowExecutionLog (nullable first)
        migrations.AddField(
            model_name='workflowexecutionlog',
            name='tenant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflow_execution_logs',
                to='tenants.tenant'
            ),
        ),

        # Add tenant field to WorkflowApproval (nullable first)
        migrations.AddField(
            model_name='workflowapproval',
            name='tenant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflow_approvals',
                to='tenants.tenant'
            ),
        ),

        # Add tenant field to WorkflowSchedule (nullable first)
        migrations.AddField(
            model_name='workflowschedule',
            name='tenant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflow_schedules',
                to='tenants.tenant'
            ),
        ),

        # Add tenant field to WorkflowTemplate (nullable - system templates don't have tenant)
        migrations.AddField(
            model_name='workflowtemplate',
            name='tenant',
            field=models.ForeignKey(
                blank=True,
                help_text='Null for system templates',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflow_templates',
                to='tenants.tenant'
            ),
        ),

        # Add tenant field to WorkflowVersion (nullable first)
        migrations.AddField(
            model_name='workflowversion',
            name='tenant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflow_versions',
                to='tenants.tenant'
            ),
        ),

        # Add tenant field to WorkflowTrigger (nullable first)
        migrations.AddField(
            model_name='workflowtrigger',
            name='tenant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflow_triggers',
                to='tenants.tenant'
            ),
        ),

        # Add tenant field to WorkflowAnalytics (nullable first)
        migrations.AddField(
            model_name='workflowanalytics',
            name='tenant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflow_analytics',
                to='tenants.tenant'
            ),
        ),

        # Add tenant field to WorkflowEvent (nullable first)
        migrations.AddField(
            model_name='workflowevent',
            name='tenant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflow_events',
                to='tenants.tenant'
            ),
        ),

        # Run data migration to set default tenant
        migrations.RunPython(set_default_tenant, reverse_set_default_tenant),

        # Now make tenant fields non-nullable (except WorkflowTemplate)
        migrations.AlterField(
            model_name='workflow',
            name='tenant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflows',
                to='tenants.tenant'
            ),
        ),

        migrations.AlterField(
            model_name='workflowexecution',
            name='tenant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflow_executions',
                to='tenants.tenant'
            ),
        ),

        migrations.AlterField(
            model_name='workflowexecutionlog',
            name='tenant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflow_execution_logs',
                to='tenants.tenant'
            ),
        ),

        migrations.AlterField(
            model_name='workflowapproval',
            name='tenant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflow_approvals',
                to='tenants.tenant'
            ),
        ),

        migrations.AlterField(
            model_name='workflowschedule',
            name='tenant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflow_schedules',
                to='tenants.tenant'
            ),
        ),

        migrations.AlterField(
            model_name='workflowversion',
            name='tenant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflow_versions',
                to='tenants.tenant'
            ),
        ),

        migrations.AlterField(
            model_name='workflowtrigger',
            name='tenant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflow_triggers',
                to='tenants.tenant'
            ),
        ),

        migrations.AlterField(
            model_name='workflowanalytics',
            name='tenant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflow_analytics',
                to='tenants.tenant'
            ),
        ),

        migrations.AlterField(
            model_name='workflowevent',
            name='tenant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflow_events',
                to='tenants.tenant'
            ),
        ),
    ]