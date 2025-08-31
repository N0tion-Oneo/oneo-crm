# Generated manually to clear stored titles for dynamic generation

from django.db import migrations


def clear_stored_titles(apps, schema_editor):
    """Clear all stored titles to enable fully dynamic title generation"""
    Record = apps.get_model('pipelines', 'Record')
    
    # Update all records to have empty titles
    # This enables dynamic title generation in serializers
    Record.objects.update(title='')
    
    print(f"✅ Cleared titles for {Record.objects.count()} records to enable dynamic generation")


def restore_titles(apps, schema_editor):
    """Reverse migration - regenerate titles if needed"""
    # Note: This is a one-way migration since titles will be dynamic
    # If we need to rollback, titles will be generated on-the-fly
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('pipelines', '0016_update_pipeline_types'),
    ]

    operations = [
        migrations.RunPython(clear_stored_titles, restore_titles),
    ]