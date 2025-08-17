# Generated manually to add draft models only
# This migration only adds MessageDraft and DraftAutoSaveSettings models
# without touching any existing fields to avoid conflicts

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('communications', '0004_add_provider_preferences'),
    ]

    operations = [
        migrations.CreateModel(
            name='MessageDraft',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('account_connection_id', models.CharField(blank=True, help_text='UserChannelConnection ID for sending account', max_length=255)),
                ('subject', models.CharField(blank=True, max_length=500)),
                ('content', models.TextField()),
                ('recipient', models.CharField(blank=True, max_length=500)),
                ('conversation_id', models.CharField(blank=True, max_length=255)),
                ('recipient_type', models.CharField(choices=[('new', 'New Message'), ('reply', 'Reply')], default='new', max_length=20)),
                ('draft_name', models.CharField(blank=True, help_text='User-friendly name for the draft', max_length=200)),
                ('auto_saved', models.BooleanField(default=True, help_text='True if this is an auto-save, False if manually saved')),
                ('attachments_data', models.JSONField(default=list, help_text='List of attachment metadata for the draft')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_auto_save', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='message_drafts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='DraftAutoSaveSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('auto_save_enabled', models.BooleanField(default=True)),
                ('auto_save_interval', models.PositiveIntegerField(default=30, help_text='Auto-save interval in seconds')),
                ('max_auto_saves', models.PositiveIntegerField(default=5, help_text='Maximum number of auto-saves to keep per conversation')),
                ('auto_delete_after_days', models.PositiveIntegerField(default=30, help_text='Auto-delete drafts after this many days')),
                ('show_draft_recovery_prompt', models.BooleanField(default=True, help_text='Show prompt to recover drafts when reopening composer')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='draft_settings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Draft Auto-Save Settings',
                'verbose_name_plural': 'Draft Auto-Save Settings',
            },
        ),
        migrations.AddIndex(
            model_name='messagedraft',
            index=models.Index(fields=['user', 'created_at'], name='communicati_user_id_ca9b3b_idx'),
        ),
        migrations.AddIndex(
            model_name='messagedraft',
            index=models.Index(fields=['user', 'auto_saved'], name='communicati_user_id_e4a0f1_idx'),
        ),
        migrations.AddIndex(
            model_name='messagedraft',
            index=models.Index(fields=['user', 'conversation_id'], name='communicati_user_id_b9e4c1_idx'),
        ),
        migrations.AddIndex(
            model_name='messagedraft',
            index=models.Index(fields=['last_auto_save'], name='communicati_last_au_d2e45a_idx'),
        ),
    ]