# Data migration to move require_email/phone to channel settings
from django.db import migrations

def migrate_required_settings(apps, schema_editor):
    """
    Migrate require_email and require_phone settings to channel-specific required fields
    """
    ParticipantSettings = apps.get_model('communications', 'ParticipantSettings')
    ChannelParticipantSettings = apps.get_model('communications', 'ChannelParticipantSettings')
    
    # Process each tenant's settings
    for settings in ParticipantSettings.objects.all():
        # Update email channel settings if require_email is True
        if settings.require_email:
            email_settings, created = ChannelParticipantSettings.objects.get_or_create(
                settings=settings,
                channel_type='email',
                defaults={'enabled': True, 'required': True}
            )
            if not created and not email_settings.required:
                email_settings.required = True
                email_settings.save()
        
        # Update whatsapp channel settings if require_phone is True
        if settings.require_phone:
            whatsapp_settings, created = ChannelParticipantSettings.objects.get_or_create(
                settings=settings,
                channel_type='whatsapp',
                defaults={'enabled': True, 'required': True}
            )
            if not created and not whatsapp_settings.required:
                whatsapp_settings.required = True
                whatsapp_settings.save()

def reverse_migration(apps, schema_editor):
    """
    Reverse the migration by setting require_email/phone based on channel settings
    """
    ParticipantSettings = apps.get_model('communications', 'ParticipantSettings')
    ChannelParticipantSettings = apps.get_model('communications', 'ChannelParticipantSettings')
    
    for settings in ParticipantSettings.objects.all():
        # Check email channel
        try:
            email_settings = ChannelParticipantSettings.objects.get(
                settings=settings,
                channel_type='email'
            )
            settings.require_email = email_settings.required
        except ChannelParticipantSettings.DoesNotExist:
            settings.require_email = False
        
        # Check whatsapp channel for phone
        try:
            whatsapp_settings = ChannelParticipantSettings.objects.get(
                settings=settings,
                channel_type='whatsapp'
            )
            settings.require_phone = whatsapp_settings.required
        except ChannelParticipantSettings.DoesNotExist:
            settings.require_phone = False
        
        settings.save()

class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0028_add_channel_required_field'),
    ]

    operations = [
        migrations.RunPython(migrate_required_settings, reverse_migration),
    ]