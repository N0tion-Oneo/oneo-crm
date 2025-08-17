# Generated manually to add provider_preferences field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0003_rename_external_account_id_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenantunipileconfig',
            name='provider_preferences',
            field=models.JSONField(default=dict, help_text='Provider-specific preferences and feature toggles within global limits'),
        ),
        migrations.AlterField(
            model_name='channel',
            name='channel_type',
            field=models.CharField(choices=[('linkedin', 'LinkedIn'), ('gmail', 'Gmail'), ('outlook', 'Outlook'), ('mail', 'Email (Generic)'), ('whatsapp', 'WhatsApp'), ('instagram', 'Instagram'), ('messenger', 'Facebook Messenger'), ('telegram', 'Telegram'), ('twitter', 'Twitter/X')], max_length=20),
        ),
        migrations.AlterField(
            model_name='tenantunipileconfig',
            name='max_api_calls_per_hour',
            field=models.PositiveIntegerField(default=1000, help_text='Maximum UniPile API calls per hour (tenant preference within global limits)'),
        ),
        migrations.AlterField(
            model_name='userchannelconnection',
            name='channel_type',
            field=models.CharField(choices=[('linkedin', 'LinkedIn'), ('gmail', 'Gmail'), ('outlook', 'Outlook'), ('mail', 'Email (Generic)'), ('whatsapp', 'WhatsApp'), ('instagram', 'Instagram'), ('messenger', 'Facebook Messenger'), ('telegram', 'Telegram'), ('twitter', 'Twitter/X')], max_length=20),
        ),
    ]