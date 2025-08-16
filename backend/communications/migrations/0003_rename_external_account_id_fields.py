# Generated manually to rename external_account_id fields to unipile_account_id

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0002_add_hosted_auth_fields'),
    ]

    operations = [
        migrations.RenameField(
            model_name='channel',
            old_name='external_account_id',
            new_name='unipile_account_id',
        ),
    ]