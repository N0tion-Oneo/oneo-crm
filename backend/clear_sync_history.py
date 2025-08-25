#!/usr/bin/env python
"""Clear all sync history and related data"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import SyncJob, SyncJobProgress

def clear_sync_history():
    """Clear all sync jobs and progress entries"""
    
    # Use oneotalent tenant context
    with schema_context('oneotalent'):
        print("🗑️ Clearing sync history in oneotalent tenant...")
        
        # Count existing records
        sync_jobs_count = SyncJob.objects.count()
        progress_count = SyncJobProgress.objects.count()
        
        print(f"📊 Found {sync_jobs_count} sync jobs")
        print(f"📊 Found {progress_count} progress entries")
        
        if sync_jobs_count > 0 or progress_count > 0:
            # Delete all sync job progress entries first (due to foreign key)
            deleted_progress = SyncJobProgress.objects.all().delete()
            print(f"✅ Deleted {deleted_progress[0]} progress entries")
            
            # Delete all sync jobs
            deleted_jobs = SyncJob.objects.all().delete()
            print(f"✅ Deleted {deleted_jobs[0]} sync jobs")
            
            print("\n🎉 Sync history cleared successfully!")
        else:
            print("ℹ️ No sync history to clear")
        
        # Verify deletion
        remaining_jobs = SyncJob.objects.count()
        remaining_progress = SyncJobProgress.objects.count()
        
        if remaining_jobs == 0 and remaining_progress == 0:
            print("✅ Verification: All sync history cleared")
        else:
            print(f"⚠️ Warning: {remaining_jobs} jobs and {remaining_progress} progress entries remain")

if __name__ == '__main__':
    clear_sync_history()