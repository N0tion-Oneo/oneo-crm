#!/usr/bin/env python
"""
Check production audit logs to see if they're being created normally
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from core.models import AuditLog
from django.contrib.auth import get_user_model

User = get_user_model()

def check_production_audit_logs():
    """Check what's happening with audit logs in production"""
    print("🔍 PRODUCTION AUDIT LOG ANALYSIS")
    print("=" * 50)
    
    with schema_context('oneotalent'):
        # Check recent audit logs
        recent_audits = AuditLog.objects.filter(
            model_name='Record'
        ).order_by('-timestamp')[:20]
        
        print(f"📊 Found {len(recent_audits)} recent record audit logs:")
        
        user_distribution = {}
        for audit in recent_audits:
            user_email = audit.user.email if audit.user else 'None'
            if user_email not in user_distribution:
                user_distribution[user_email] = 0
            user_distribution[user_email] += 1
            
            print(f"   📝 ID {audit.id}: Record {audit.object_id} by {user_email} at {audit.timestamp}")
            
            # Show change summary if available
            if audit.changes and 'changes_summary' in audit.changes:
                summary = audit.changes['changes_summary'][:2] if audit.changes['changes_summary'] else []
                for change in summary:
                    print(f"      🔹 {change}")
        
        print(f"\n📈 User distribution in recent audit logs:")
        total_logs = sum(user_distribution.values())
        for user_email, count in sorted(user_distribution.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_logs) * 100 if total_logs > 0 else 0
            print(f"   👤 {user_email}: {count} logs ({percentage:.1f}%)")
        
        # Check if there's a dominant user (indicating potential issue)
        if user_distribution:
            dominant_user, dominant_count = max(user_distribution.items(), key=lambda x: x[1])
            dominant_percentage = (dominant_count / total_logs) * 100
            
            if dominant_percentage > 70:
                print(f"\n⚠️  POTENTIAL ISSUE DETECTED:")
                print(f"   {dominant_user} has {dominant_percentage:.1f}% of audit logs")
                print(f"   This could indicate user attribution problems")
                
                # Check if the dominant user has recent activity
                user_recent_logs = [audit for audit in recent_audits if (audit.user.email if audit.user else 'None') == dominant_user]
                print(f"\n🔍 Recent activity for {dominant_user}:")
                for audit in user_recent_logs[:5]:
                    print(f"   📝 {audit.timestamp}: Record {audit.object_id}")
                
            else:
                print(f"\n✅ Reasonable user distribution in audit logs")
        
        # Check for any recent updates without corresponding audit logs
        from pipelines.models import Record
        recent_records = Record.objects.filter(
            updated_at__isnull=False
        ).order_by('-updated_at')[:10]
        
        print(f"\n📝 Recent record updates:")
        for record in recent_records:
            # Check if this record has corresponding audit logs
            record_audits = AuditLog.objects.filter(
                model_name='Record',
                object_id=str(record.id)
            ).count()
            
            print(f"   🆔 Record {record.id}: Updated by {record.updated_by.email if record.updated_by else 'None'}")
            print(f"      📅 Last updated: {record.updated_at}")
            print(f"      📊 Audit logs: {record_audits}")
            
            if record_audits == 0:
                print(f"      ⚠️  NO AUDIT LOGS for this record!")

if __name__ == '__main__':
    check_production_audit_logs()