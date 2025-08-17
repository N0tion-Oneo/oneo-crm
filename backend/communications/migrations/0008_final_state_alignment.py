# Generated manually to align Django's migration state with actual database schema
# This migration tells Django that the database is already in the expected state

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0007_correct_model_state'),
    ]

    operations = [
        # Use RunSQL with state_operations to update Django's understanding
        # without running actual SQL (since database is already correct)
        migrations.RunSQL(
            sql=migrations.RunSQL.noop,  # No actual SQL to run
            reverse_sql=migrations.RunSQL.noop,
            state_operations=[
                # Tell Django that these fields already exist in UserChannelConnection
                migrations.AddField(
                    model_name='userchannelconnection',
                    name='messages_sent_count',
                    field=models.IntegerField(default=0),
                    preserve_default=False,
                ),
                migrations.AddField(
                    model_name='userchannelconnection',
                    name='provider_config',
                    field=models.JSONField(default=dict),
                    preserve_default=False,
                ),
                
                # Tell Django that external_account_id was removed and unipile_account_id was added
                migrations.RemoveField(
                    model_name='userchannelconnection',
                    name='external_account_id',
                ),
                migrations.AddField(
                    model_name='userchannelconnection',
                    name='unipile_account_id',
                    field=models.CharField(blank=True, default='', help_text='UniPile account ID', max_length=255),
                    preserve_default=False,
                ),
                
                # Update the unique_together constraint
                migrations.AlterUniqueTogether(
                    name='userchannelconnection',
                    unique_together={('user', 'channel_type', 'unipile_account_id')},
                ),
                
                # Handle the index renames for MessageDraft
                migrations.RunSQL(
                    sql="-- Index renames handled automatically",
                    reverse_sql="-- Index renames handled automatically",
                ),
            ]
        ),
    ]