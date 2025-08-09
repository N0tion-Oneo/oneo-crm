#!/usr/bin/env python
"""Check available test data"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Record

def check_data():
    with schema_context('oneotalent'):
        pipelines = Pipeline.objects.all()
        print(f"📋 Pipelines ({pipelines.count()}):")
        for p in pipelines:
            print(f"  {p.id}: {p.name} (active: {p.is_active})")
            
        records = Record.objects.all()
        print(f"\n📝 Records ({records.count()}):")
        for r in records[:5]:
            print(f"  {r.id}: Pipeline {r.pipeline_id} (deleted: {r.is_deleted})")

if __name__ == '__main__':
    check_data()