#!/usr/bin/env python3
"""
Fix pipeline access levels script

This script updates existing pipelines from 'private' to 'internal' 
so they work with the new public forms system.
"""

import os
import sys

def fix_pipeline_access_levels():
    print("🔧 Fixing Pipeline Access Levels")
    print("=" * 50)
    
    try:
        # Set up Django environment
        backend_path = os.path.join(os.path.dirname(__file__), 'backend')
        sys.path.insert(0, backend_path)
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
        
        import django
        django.setup()
        
        from pipelines.models import Pipeline
        
        print("\n📊 Current pipeline access levels:")
        pipelines = Pipeline.objects.all()
        
        if not pipelines.exists():
            print("   No pipelines found")
            return
            
        # Show current status
        for pipeline in pipelines:
            print(f"   - {pipeline.name} ({pipeline.slug}): {pipeline.access_level}")
        
        # Count pipelines that need updating
        private_count = Pipeline.objects.filter(access_level='private').count()
        
        if private_count > 0:
            print(f"\n🔄 Updating {private_count} pipelines from 'private' to 'internal'...")
            
            # Update access levels
            updated_count = Pipeline.objects.filter(access_level='private').update(access_level='internal')
            print(f"✅ Updated {updated_count} pipelines")
            
            print("\n📊 Updated pipeline access levels:")
            for pipeline in Pipeline.objects.all():
                status = "🟢 Both forms available" if pipeline.access_level == 'public' else "🔵 Internal only"
                print(f"   - {pipeline.name} ({pipeline.slug}): {pipeline.access_level} {status}")
        else:
            print("\n✅ No pipelines need updating")
            
        print("\n📝 Next steps:")
        print("1. Access any pipeline's Business Rules page")
        print("2. Use the 'Public Forms Access' toggle to enable public forms")
        print("3. Test both internal and public forms")
        
        print("\n🎉 Pipeline access levels fixed!")
        
    except ImportError as e:
        print(f"❌ Django setup failed: {e}")
        print("\n🔧 Manual fix required:")
        print("Run this SQL command in your PostgreSQL database:")
        print()
        print("UPDATE pipelines_pipeline SET access_level = 'internal' WHERE access_level = 'private';")
        print()
        print("Or run the Django migration:")
        print("python manage.py migrate")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_pipeline_access_levels()