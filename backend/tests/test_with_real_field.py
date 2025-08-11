#!/usr/bin/env python
"""Test user attribution with actual existing pipeline fields"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

import json
import time
from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Record
from core.models import AuditLog

User = get_user_model()

def test_with_existing_field():
    """Test user attribution using an existing pipeline field"""
    print("🧪 USER ATTRIBUTION TEST WITH REAL FIELDS")
    print("=" * 60)
    
    client = Client()
    
    with schema_context('oneotalent'):
        # Get users
        josh = User.objects.get(email='josh@oneodigital.com')
        saul = User.objects.get(email='saul@oneodigital.com')
        
        # Get pipeline and record
        pipeline = Pipeline.objects.get(id=1)
        record = Record.objects.filter(pipeline=pipeline).first()
        
        print(f"👤 Josh: {josh.email} (ID: {josh.id})")
        print(f"👤 Saul: {saul.email} (ID: {saul.id})")
        print(f"📝 Record: {record.id}")
        
        # Clear existing audit logs
        AuditLog.objects.filter(model_name='Record', object_id=str(record.id)).delete()
        print("🧹 Cleared existing audit logs")
        
        def create_token(user):
            with schema_context('oneotalent'):
                refresh = RefreshToken.for_user(user)
                refresh['tenant_schema'] = 'oneotalent'
                refresh['email'] = user.email
                return str(refresh.access_token)
        
        def test_user_update(user, field_name, new_value):
            print(f"\n🧪 Testing update by {user.email}: {field_name} = {new_value}")
            
            token = create_token(user)
            
            # Make API call with existing field
            response = client.patch(
                f'/api/v1/pipelines/{pipeline.id}/records/{record.id}/',
                data=json.dumps({'data': {field_name: new_value}}),
                content_type='application/json',
                HTTP_AUTHORIZATION=f'Bearer {token}',
                HTTP_HOST='oneotalent.localhost'
            )
            
            print(f"   API Response: {response.status_code}")
            
            time.sleep(0.2)  # Allow signal processing
            
            # Check record update
            updated_record = Record.objects.get(id=record.id)
            record_user = updated_record.updated_by
            
            print(f"   Record updated_by: {record_user.email if record_user else 'None'}")
            
            # Check audit log
            audit_log = AuditLog.objects.filter(
                model_name='Record',
                object_id=str(record.id),
                action='updated'
            ).order_by('-timestamp').first()
            
            if audit_log:
                audit_user = audit_log.user
                print(f"   Audit log user: {audit_user.email if audit_user else 'None'}")
                print(f"   ✅ Record user correct: {record_user.email == user.email if record_user else False}")
                print(f"   ✅ Audit user correct: {audit_user.email == user.email if audit_user else False}")
                
                return {
                    'record_correct': record_user.email == user.email if record_user else False,
                    'audit_correct': audit_user.email == user.email if audit_user else False
                }
            else:
                print(f"   ❌ No audit log created")
                return {'record_correct': False, 'audit_correct': False}
        
        # Test with existing field: company_name (text field)
        josh_result = test_user_update(josh, 'company_name', f'Josh Company {int(time.time())}')
        saul_result = test_user_update(saul, 'company_name', f'Saul Company {int(time.time())}')
        
        # Test activity API
        print(f"\n🔍 Testing activity API call...")
        
        token = create_token(josh)
        response = client.get(
            f'/api/v1/pipelines/{pipeline.id}/records/{record.id}/history/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
            HTTP_HOST='oneotalent.localhost'
        )
        
        if response.status_code == 200:
            activity_data = response.json()
            activities = activity_data.get('activities', [])
            
            print(f"   📊 Activities returned: {len(activities)}")
            
            if activities:
                recent_activity = activities[0]
                activity_user = recent_activity.get('user', {})
                activity_email = activity_user.get('email')
                
                print(f"   Most recent activity by: {activity_email}")
                print(f"   Expected: {saul.email} (last update)")
                print(f"   ✅ Activity user correct: {activity_email == saul.email}")
        
        print(f"\n🏁 FINAL RESULTS:")
        print(f"   Josh record attribution: {'✅ PASS' if josh_result['record_correct'] else '❌ FAIL'}")
        print(f"   Josh audit attribution: {'✅ PASS' if josh_result['audit_correct'] else '❌ FAIL'}")
        print(f"   Saul record attribution: {'✅ PASS' if saul_result['record_correct'] else '❌ FAIL'}")
        print(f"   Saul audit attribution: {'✅ PASS' if saul_result['audit_correct'] else '❌ FAIL'}")
        
        all_correct = (josh_result['record_correct'] and josh_result['audit_correct'] and 
                      saul_result['record_correct'] and saul_result['audit_correct'])
        
        if all_correct:
            print(f"\n🎉 USER ATTRIBUTION WORKING CORRECTLY!")
            print("✅ The issue was testing with non-existent fields")
            print("✅ Authentication and audit logging work perfectly with real fields")
        else:
            print(f"\n⚠️  USER ATTRIBUTION STILL HAS ISSUES")
            print("🐛 There's a deeper problem beyond field validation")

if __name__ == '__main__':
    test_with_existing_field()