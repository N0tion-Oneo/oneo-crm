# Migration to add required field to ChannelParticipantSettings
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0027_add_company_name_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='channelparticipantsettings',
            name='required',
            field=models.BooleanField(
                default=False, 
                help_text='Require this channel to be present for auto-creation'
            ),
        ),
    ]