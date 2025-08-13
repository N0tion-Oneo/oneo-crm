# Generated manually for adding strip_subdomains field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('duplicates', '0006_populate_url_extraction_rule_pipelines'),
    ]

    operations = [
        migrations.AddField(
            model_name='urlextractionrule',
            name='strip_subdomains',
            field=models.BooleanField(default=False, help_text='Strip all subdomains to keep only main domain (e.g., blog.apple.com → apple.com)'),
        ),
    ]