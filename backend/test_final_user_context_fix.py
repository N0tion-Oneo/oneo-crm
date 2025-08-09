#!/usr/bin/env python
"""
Final User Context Fix - Test with actual existing field to identify the exact issue
"""

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

def test_user_context_with_real_field():
    """Test user context corruption with real existing field"""
    print("🔧 FINAL USER CONTEXT TEST WITH REAL FIELD")
    print("=" * 60)
    
    with schema_context('oneotalent'):
        josh = User.objects.get(email='josh@oneodigital.com')
        saul = User.objects.get(email='saul@oneodigital.com')
        
        # Get pipeline 2 and its record
        pipeline = Pipeline.objects.get(id=2)
        record = Record.objects.filter(pipeline=pipeline, is_deleted=False).first()
        
        print(f"👤 Josh: {josh.email} (ID: {josh.id})")
        print(f"👤 Saul: {saul.email} (ID: {saul.id})")
        print(f"📋 Pipeline: {pipeline.id} ({pipeline.name})")
        print(f"📝 Record: {record.id}")
        print(f"🔧 Using existing field: email_2 (email field type)")
        
        def create_token(user):
            with schema_context('oneotalent'):
                refresh = RefreshToken.for_user(user)
                refresh['tenant_schema'] = 'oneotalent'
                refresh['email'] = user.email
                return str(refresh.access_token)
        
        # Create tokens and clients
        josh_token = create_token(josh)
        saul_token = create_token(saul)
        
        josh_client = Client()
        saul_client = Client()
        
        print(f"\n🧪 TEST: Josh Update with Real Field")
        
        # Clear audit logs
        AuditLog.objects.filter(model_name='Record', object_id=str(record.id)).delete()
        
        josh_response = josh_client.patch(
            f'/api/v1/pipelines/{pipeline.id}/records/{record.id}/',
            data=json.dumps({'data': {'email_2': f'josh.test.{int(time.time())}@example.com'}}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {josh_token}',
            HTTP_HOST='oneotalent.localhost'
        )
        
        print(f"Josh response: {josh_response.status_code}")
        
        time.sleep(0.2)
        
        # Check record
        updated_record = Record.objects.get(id=record.id)
        josh_record_correct = updated_record.updated_by and updated_record.updated_by.email == josh.email
        
        print(f"Josh record updated_by: {updated_record.updated_by.email if updated_record.updated_by else 'None'}")
        print(f"Josh record correct: {josh_record_correct}")
        
        # Check audit log
        audit_log = AuditLog.objects.filter(
            model_name='Record',
            object_id=str(record.id),
            action='updated'
        ).order_by('-timestamp').first()
        
        josh_audit_correct = audit_log and audit_log.user and audit_log.user.email == josh.email
        print(f"Josh audit user: {audit_log.user.email if audit_log and audit_log.user else 'None'}")
        print(f"Josh audit correct: {josh_audit_correct}")
        
        print(f"\n🧪 TEST: Saul Update with Real Field")
        
        # Clear audit logs
        AuditLog.objects.filter(model_name='Record', object_id=str(record.id)).delete()
        
        saul_response = saul_client.patch(
            f'/api/v1/pipelines/{pipeline.id}/records/{record.id}/',
            data=json.dumps({'data': {'email_2': f'saul.test.{int(time.time())}@example.com'}}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {saul_token}',
            HTTP_HOST='oneotalent.localhost'
        )
        
        print(f"Saul response: {saul_response.status_code}")
        
        time.sleep(0.2)
        
        # Check record
        updated_record = Record.objects.get(id=record.id)
        saul_record_correct = updated_record.updated_by and updated_record.updated_by.email == saul.email
        
        print(f"Saul record updated_by: {updated_record.updated_by.email if updated_record.updated_by else 'None'}")
        print(f"Saul record correct: {saul_record_correct}")
        
        # Check audit log
        audit_log = AuditLog.objects.filter(
            model_name='Record',
            object_id=str(record.id),
            action='updated'
        ).order_by('-timestamp').first()
        
        saul_audit_correct = audit_log and audit_log.user and audit_log.user.email == saul.email
        print(f"Saul audit user: {audit_log.user.email if audit_log and audit_log.user else 'None'}")
        print(f"Saul audit correct: {saul_audit_correct}")
        
        print(f"\n📊 FINAL ANALYSIS:")
        print(f"Josh record attribution: {'✅' if josh_record_correct else '❌'}")
        print(f"Josh audit attribution: {'✅' if josh_audit_correct else '❌'}")
        print(f"Saul record attribution: {'✅' if saul_record_correct else '❌'}")
        print(f"Saul audit attribution: {'✅' if saul_audit_correct else '❌'}")
        
        if not saul_record_correct:
            print(f"\n🚨 CONFIRMED: User context corruption exists!")
            print(f"   Expected: {saul.email}")
            print(f"   Got: {updated_record.updated_by.email if updated_record.updated_by else 'None'}")
            
            if updated_record.updated_by and updated_record.updated_by.email == josh.email:
                print(f"   🔍 Saul's actions are being attributed to Josh")
                print(f"   🐛 This confirms the user's bug report")
        else:
            print(f"\n✅ User context working correctly with real field updates")

if __name__ == '__main__':
    test_user_context_with_real_field()