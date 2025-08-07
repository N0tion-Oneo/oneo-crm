#!/usr/bin/env python3
"""
Quick Check: Verify New Field Creation
Check the "new field" that was just added to verify our slug fix worked
"""

import os
import sys

# Add the parent directory to the Python path
sys.path.append('/Users/joshcowan/Oneo CRM/backend')

# Set up Django environment  
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = '1'

import django
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Field, Record, field_slugify

with schema_context('oneotalent'):
    pipeline = Pipeline.objects.filter(name__icontains='sales').first()
    if pipeline:
        print(f'📊 Pipeline: {pipeline.name} (ID: {pipeline.id})')
        
        # Look for the new field
        new_field = pipeline.fields.filter(name__icontains='new field').first()
        if new_field:
            print(f'\n✅ Found "new field":')
            print(f'   Field Name: "{new_field.name}"')
            print(f'   Field Slug: "{new_field.slug}"')
            print(f'   Created At: {new_field.created_at}')
            print(f'   Field Type: {new_field.field_type}')
            
            # Verify slug format
            expected_slug = field_slugify(new_field.name)
            actual_slug = new_field.slug
            
            print(f'\n🔍 Slug Analysis:')
            print(f'   Expected slug: "{expected_slug}"')
            print(f'   Actual slug: "{actual_slug}"')
            print(f'   Match: {"✅ YES" if expected_slug == actual_slug else "❌ NO"}')
            
            # Check format
            has_hyphens = '-' in actual_slug
            has_underscores = '_' in actual_slug
            
            if has_hyphens:
                print(f'   Format: ❌ USES HYPHENS (PROBLEM!)')
            elif has_underscores:
                print(f'   Format: ✅ USES UNDERSCORES (CORRECT)')
            else:
                print(f'   Format: ⚠️  SINGLE WORD (NO SEPARATORS)')
            
            # Overall assessment
            print(f'\n📊 FINAL ASSESSMENT:')
            if expected_slug == actual_slug and not has_hyphens:
                print(f'   🎉 SUCCESS: Field slug correctly uses underscores!')
                print(f'   ✅ Our fix is working properly')
            else:
                print(f'   ❌ FAILED: Field slug format is incorrect')
                print(f'   ⚠️  Our fix needs investigation')
        else:
            print(f'\n❌ No field containing "new field" found')
            print(f'\nRecent fields in pipeline:')
            for field in pipeline.fields.order_by('-created_at')[:10]:
                print(f'   - "{field.name}" (slug: "{field.slug}") - {field.created_at}')
    else:
        print('❌ No Sales Pipeline found')