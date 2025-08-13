# Generated manually for intended_recipient_email field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sharing', '0005_make_accessor_fields_required'),
    ]

    operations = [
        # First add the field as nullable
        migrations.AddField(
            model_name='sharedrecord',
            name='intended_recipient_email',
            field=models.EmailField(null=True, blank=True, help_text="Email address of the intended recipient who can access this share"),
        ),
        # Add indexes for the new field
        migrations.AddIndex(
            model_name='sharedrecord',
            index=models.Index(fields=['intended_recipient_email'], name='sharing_sha_intende_ed73a0_idx'),
        ),
        migrations.AddIndex(
            model_name='sharedrecord',
            index=models.Index(fields=['intended_recipient_email', 'is_active'], name='sharing_sha_intende_7f2b45_idx'),
        ),
        # Set a default value for existing records (use a placeholder email)
        migrations.RunSQL(
            "UPDATE sharing_shared_records SET intended_recipient_email = 'legacy@system.local' WHERE intended_recipient_email IS NULL;",
            reverse_sql="UPDATE sharing_shared_records SET intended_recipient_email = NULL;"
        ),
        # Now make the field non-nullable
        migrations.AlterField(
            model_name='sharedrecord',
            name='intended_recipient_email',
            field=models.EmailField(help_text="Email address of the intended recipient who can access this share"),
        ),
    ]