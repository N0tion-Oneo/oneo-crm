# Generated manually for workflow-centric duplicate management

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('duplicates', '0007_add_strip_subdomains_field'),
    ]

    operations = [
        # Update DuplicateRule action choices
        migrations.AlterField(
            model_name='duplicaterule',
            name='action_on_duplicate',
            field=models.CharField(
                choices=[
                    ('detect_only', 'Detect and Store Matches'),
                    ('disabled', 'Disable Detection'),
                ],
                default='detect_only',
                help_text='Action to take when duplicates are detected',
                max_length=50
            ),
        ),
        
        # Update DuplicateMatch status choices
        migrations.AlterField(
            model_name='duplicatematch',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending Review'),
                    ('merged', 'Records Merged'),
                    ('kept_both', 'Kept Both Records'),
                    ('ignored', 'Marked as False Positive'),
                    ('needs_review', 'Flagged for Team Review'),
                    ('resolved', 'Resolved'),
                ],
                default='pending',
                max_length=50
            ),
        ),
        
        # Update existing records to use new action values
        migrations.RunSQL(
            "UPDATE duplicates_duplicaterule SET action_on_duplicate = 'detect_only' WHERE action_on_duplicate IN ('warn', 'block', 'merge_prompt');",
            reverse_sql="UPDATE duplicates_duplicaterule SET action_on_duplicate = 'warn' WHERE action_on_duplicate = 'detect_only';"
        ),
        
        # Update existing match statuses  
        migrations.RunSQL(
            """
            UPDATE duplicates_duplicatematch 
            SET status = CASE 
                WHEN status = 'confirmed' THEN 'pending'
                WHEN status = 'false_positive' THEN 'ignored'
                WHEN status = 'auto_resolved' THEN 'resolved'
                ELSE status
            END 
            WHERE status IN ('confirmed', 'false_positive', 'auto_resolved');
            """,
            reverse_sql="""
            UPDATE duplicates_duplicatematch 
            SET status = CASE 
                WHEN status = 'ignored' THEN 'false_positive'
                ELSE status
            END;
            """
        ),
    ]