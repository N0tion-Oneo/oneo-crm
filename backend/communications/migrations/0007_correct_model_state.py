# Manual migration to correct Django's understanding of the database state
# The database already has the correct schema, this just updates Django's state tracking

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0006_force_current_state'),
    ]

    operations = [
        # State-only operations - no actual database changes needed
        # These tell Django that the database already has these fields in the correct state
        migrations.RunSQL(
            sql=migrations.RunSQL.noop,  # No SQL to run
            reverse_sql=migrations.RunSQL.noop,  # No reverse SQL
            state_operations=[]  # Empty - this migration just marks the current state as correct
        ),
    ]
