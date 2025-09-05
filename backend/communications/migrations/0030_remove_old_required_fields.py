# Migration to remove require_email and require_phone from ParticipantSettings
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0029_migrate_required_settings_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='participantsettings',
            name='require_email',
        ),
        migrations.RemoveField(
            model_name='participantsettings',
            name='require_phone',
        ),
    ]