# Generated migration for adding name field settings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0024_add_participant_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='participantsettings',
            name='full_name_field',
            field=models.CharField(
                max_length=100,
                blank=True,
                default='',
                help_text='Field slug for full name (e.g., "full_name", "contact_name")'
            ),
        ),
        migrations.AddField(
            model_name='participantsettings',
            name='first_name_field',
            field=models.CharField(
                max_length=100,
                blank=True,
                default='',
                help_text='Field slug for first name (used if full_name_field is not set)'
            ),
        ),
        migrations.AddField(
            model_name='participantsettings',
            name='last_name_field',
            field=models.CharField(
                max_length=100,
                blank=True,
                default='',
                help_text='Field slug for last name (used with first_name_field)'
            ),
        ),
        migrations.AddField(
            model_name='participantsettings',
            name='name_split_strategy',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('first_space', 'Split at first space'),
                    ('last_space', 'Split at last space'),
                    ('smart', 'Smart detection (handles middle names)'),
                ],
                default='smart',
                help_text='How to split full names into first/last when needed'
            ),
        ),
    ]