# Generated migration to remove RecordCommunicationLink model
# This completes the participant linking refactor

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0022_remove_deprecated_models'),
    ]

    operations = [
        # Remove RecordCommunicationLink model
        migrations.DeleteModel(
            name='RecordCommunicationLink',
        ),
    ]