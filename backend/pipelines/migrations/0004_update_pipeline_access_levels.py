# Generated manually to update pipeline access levels

from django.db import migrations


def update_access_levels(apps, schema_editor):
    """Update pipelines with 'private' access level to 'internal'"""
    Pipeline = apps.get_model('pipelines', 'Pipeline')
    
    # Update all pipelines with 'private' access level to 'internal'
    updated_count = Pipeline.objects.filter(access_level='private').update(access_level='internal')
    
    print(f"Updated {updated_count} pipelines from 'private' to 'internal' access level")


def reverse_access_levels(apps, schema_editor):
    """Reverse: Update pipelines with 'internal' access level back to 'private'"""
    Pipeline = apps.get_model('pipelines', 'Pipeline')
    
    # Only update back to private if they were originally private
    # Since we can't track this, we'll update all internal back to private
    updated_count = Pipeline.objects.filter(access_level='internal').update(access_level='private')
    
    print(f"Reversed {updated_count} pipelines from 'internal' to 'private' access level")


class Migration(migrations.Migration):

    dependencies = [
        ('pipelines', '0003_add_public_forms_fields'),
    ]

    operations = [
        migrations.RunPython(update_access_levels, reverse_access_levels),
    ]