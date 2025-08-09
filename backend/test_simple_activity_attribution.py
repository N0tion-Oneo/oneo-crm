#!/usr/bin/env python
"""
Simple test to check activity log user attribution using existing records
"""

import os
import sys
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from pipelines.models import Pipeline, Record
from core.models import AuditLog
from api.views.records import RecordViewSet
from django.test import RequestFactory
import json

User = get_user_model()

def test_activity_log_attribution():
    """Test activity log attribution with existing data"""
    print("🧪 Simple Activity Log Attribution Test")
    print("=" * 50)
    
    with schema_context('oneotalent'):
        # Get users
        users = list(User.objects.filter(is_active=True).order_by('id'))
        if len(users) < 2:
            print("❌ Need at least 2 users")
            return
            
        user1 = users[0]  # Josh
        user2 = users[1]  # Saul or Admin
        
        print(f"👤 User 1: {user1.email} (ID: {user1.id})")
        print(f"👤 User 2: {user2.email} (ID: {user2.id})")
        
        # Get an existing record
        record = Record.objects.filter(is_deleted=False).first()
        if not record:
            print("❌ No records found")
            return
            
        print(f"📝 Using record: {record.id}")
        
        # Check recent audit logs for this record
        recent_logs = AuditLog.objects.filter(
            model_name='Record',
            object_id=str(record.id)
        ).order_by('-timestamp')[:5]
        
        print(f"\n📊 Recent audit logs for record {record.id}:")
        for i, log in enumerate(recent_logs):
            user_info = f"{log.user.email} (ID: {log.user.id})" if log.user else "No user"
            print(f"  {i+1}. {log.action} by {user_info} at {log.timestamp}")
        
        # Simulate the API call that the frontend makes
        print(f"\n🔍 Testing activity API response...")
        
        factory = RequestFactory()
        request = factory.get(f'/api/pipelines/{record.pipeline_id}/records/{record.id}/history/')
        request.user = user1  # Simulating that user1 is making the API call
        
        # Create the view and call history method
        view = RecordViewSet()
        view.request = request
        view.kwargs = {'pipeline_pk': record.pipeline_id, 'pk': record.id}
        
        # Mock get_object to return our record
        view.get_object = lambda: record
        
        response = view.history(request, pk=record.id, pipeline_pk=record.pipeline_id)
        
        if response.status_code != 200:
            print(f"❌ API call failed: {response.status_code}")
            return
            
        activities = response.data.get('activities', [])
        print(f"📋 API returned {len(activities)} activities:")
        
        for i, activity in enumerate(activities[:3]):  # Show first 3
            user_info = activity.get('user', {})
            if user_info:
                user_email = user_info.get('email', 'Unknown')
                user_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip()
                print(f"  {i+1}. {activity['type']} by {user_email} ({user_name}) - {activity['message'][:50]}...")
            else:
                print(f"  {i+1}. {activity['type']} by System - {activity['message'][:50]}...")
        
        # Check if there's a mismatch
        if activities and len(recent_logs) > 0:
            api_first_user = activities[0].get('user', {}).get('email')
            db_first_user = recent_logs[0].user.email if recent_logs[0].user else None
            
            if api_first_user != db_first_user:
                print(f"\n⚠️  POTENTIAL ISSUE DETECTED:")
                print(f"    API shows: {api_first_user}")
                print(f"    DB shows:  {db_first_user}")
            else:
                print(f"\n✅ API and DB user attribution match: {api_first_user}")

if __name__ == '__main__':
    test_activity_log_attribution()