# Generated manually for making pipeline field required on URLExtractionRule

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('duplicates', '0008_update_workflow_actions'),
        ('pipelines', '0010_remove_fieldgroup_is_collapsed'),
    ]

    operations = [
        # Make pipeline field required (remove null=True, blank=True)
        migrations.AlterField(
            model_name='urlextractionrule',
            name='pipeline',
            field=models.ForeignKey(
                help_text='Pipeline this URL extraction rule applies to',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='url_extraction_rules',
                to='pipelines.pipeline'
            ),
        ),
    ]