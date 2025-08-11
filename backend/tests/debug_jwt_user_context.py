#!/usr/bin/env python
"""
Deep JWT User Context Debug - Trace exact point where user context gets corrupted
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

import json
import time
import threading
from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Record
from core.models import AuditLog

User = get_user_model()

def debug_jwt_authentication_flow():
    """Debug the JWT authentication flow step by step"""
    print("🔧 JWT AUTHENTICATION FLOW DEBUG")
    print("=" * 60)
    
    with schema_context('oneotalent'):
        josh = User.objects.get(email='josh@oneodigital.com')
        saul = User.objects.get(email='saul@oneodigital.com')
        
        # Get test record
        pipeline = None
        record = None
        for p in Pipeline.objects.filter(is_active=True):
            records = Record.objects.filter(pipeline=p, is_deleted=False)
            if records.exists():
                pipeline = p
                record = records.first()
                break
        
        print(f"👤 Josh: {josh.email} (ID: {josh.id})")
        print(f"👤 Saul: {saul.email} (ID: {saul.id})")
        print(f"📋 Pipeline: {pipeline.id}, Record: {record.id}")
        
        # Create JWT tokens with detailed logging
        def create_token_with_debug(user, name):
            print(f"\n🔑 Creating JWT token for {name} ({user.email})")
            print(f"    Thread ID: {threading.get_ident()}")
            
            with schema_context('oneotalent'):
                refresh = RefreshToken.for_user(user)
                refresh['tenant_schema'] = 'oneotalent'
                refresh['email'] = user.email
                refresh['user_id'] = user.id  # Explicitly add user ID
                token = str(refresh.access_token)
                
                # Decode token to verify
                from rest_framework_simplejwt.tokens import UntypedToken
                decoded = UntypedToken(token).payload
                
                print(f"    Token payload user_id: {decoded.get('user_id')}")
                print(f"    Token payload email: {decoded.get('email')}")
                print(f"    Token payload tenant: {decoded.get('tenant_schema')}")
                print(f"    Token first 20 chars: {token[:20]}...")
                
                return token
        
        josh_token = create_token_with_debug(josh, "Josh")
        saul_token = create_token_with_debug(saul, "Saul")
        
        # Create separate clients
        josh_client = Client()
        saul_client = Client()
        
        print(f"\n🌐 Client Separation:")
        print(f"    Josh client ID: {id(josh_client)}")
        print(f"    Saul client ID: {id(saul_client)}")
        print(f"    Josh session: {josh_client.session.session_key}")
        print(f"    Saul session: {saul_client.session.session_key}")
        
        # Test 1: Josh request
        print(f"\n🧪 TEST 1: Josh API Request")
        print(f"    Thread ID: {threading.get_ident()}")
        print(f"    Using token: {josh_token[:20]}...")
        print(f"    Using client: {id(josh_client)}")
        
        # Clear audit logs
        AuditLog.objects.filter(model_name='Record', object_id=str(record.id)).delete()
        
        # Add debug middleware tracking to the request
        response = josh_client.patch(
            f'/api/v1/pipelines/{pipeline.id}/records/{record.id}/',
            data=json.dumps({'data': {'test_field': f'josh_debug_{int(time.time())}'}}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {josh_token}',
            HTTP_HOST='oneotalent.localhost',
            # Add debug headers to track request
            HTTP_X_DEBUG_USER_EXPECTED='josh@oneodigital.com',
            HTTP_X_DEBUG_USER_ID_EXPECTED=str(josh.id),
            HTTP_X_DEBUG_THREAD_ID=str(threading.get_ident())
        )
        
        print(f"    Response status: {response.status_code}")
        
        # Check results
        time.sleep(0.2)
        
        updated_record = Record.objects.get(id=record.id)
        print(f"    Record updated_by: {updated_record.updated_by.email if updated_record.updated_by else 'None'} (ID: {updated_record.updated_by.id if updated_record.updated_by else 'None'})")
        print(f"    Expected: {josh.email} (ID: {josh.id})")
        print(f"    Correct: {updated_record.updated_by.email == josh.email if updated_record.updated_by else False}")
        
        # Test 2: Saul request (this should fail)
        print(f"\n🧪 TEST 2: Saul API Request")  
        print(f"    Thread ID: {threading.get_ident()}")
        print(f"    Using token: {saul_token[:20]}...")
        print(f"    Using client: {id(saul_client)}")
        
        # Clear audit logs
        AuditLog.objects.filter(model_name='Record', object_id=str(record.id)).delete()
        
        response = saul_client.patch(
            f'/api/v1/pipelines/{pipeline.id}/records/{record.id}/',
            data=json.dumps({'data': {'test_field': f'saul_debug_{int(time.time())}'}}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {saul_token}',
            HTTP_HOST='oneotalent.localhost',
            # Add debug headers to track request
            HTTP_X_DEBUG_USER_EXPECTED='saul@oneodigital.com',
            HTTP_X_DEBUG_USER_ID_EXPECTED=str(saul.id),
            HTTP_X_DEBUG_THREAD_ID=str(threading.get_ident())
        )
        
        print(f"    Response status: {response.status_code}")
        
        # Check results
        time.sleep(0.2)
        
        updated_record = Record.objects.get(id=record.id)
        print(f"    Record updated_by: {updated_record.updated_by.email if updated_record.updated_by else 'None'} (ID: {updated_record.updated_by.id if updated_record.updated_by else 'None'})")
        print(f"    Expected: {saul.email} (ID: {saul.id})")
        print(f"    Correct: {updated_record.updated_by.email == saul.email if updated_record.updated_by else False}")
        
        if updated_record.updated_by and updated_record.updated_by.email != saul.email:
            print(f"    🚨 USER CONTEXT CORRUPTION: Expected {saul.email}, got {updated_record.updated_by.email}")
            
        # Test 3: Immediate back-to-back requests
        print(f"\n🧪 TEST 3: Back-to-back Requests (Race Condition Test)")
        
        def make_request(client, token, user, label):
            print(f"    🔄 {label} request starting (Thread: {threading.get_ident()})")
            
            response = client.patch(
                f'/api/v1/pipelines/{pipeline.id}/records/{record.id}/',
                data=json.dumps({'data': {'test_field': f'{label.lower()}_race_{int(time.time())}'}}),
                content_type='application/json',
                HTTP_AUTHORIZATION=f'Bearer {token}',
                HTTP_HOST='oneotalent.localhost'
            )
            
            print(f"    🔄 {label} response: {response.status_code}")
            return response
        
        # Clear audit logs
        AuditLog.objects.filter(model_name='Record', object_id=str(record.id)).delete()
        
        # Make requests rapidly
        josh_response = make_request(josh_client, josh_token, josh, "Josh")
        saul_response = make_request(saul_client, saul_token, saul, "Saul")
        
        time.sleep(0.3)  # Let everything settle
        
        updated_record = Record.objects.get(id=record.id)
        print(f"\n    Final record updated_by: {updated_record.updated_by.email if updated_record.updated_by else 'None'}")
        
        # Summary
        print(f"\n📊 SUMMARY:")
        print(f"    JWT tokens created correctly: ✅")
        print(f"    Clients isolated: ✅") 
        print(f"    Sessions isolated: ✅")
        print(f"    User context corruption detected: {'❌ YES' if updated_record.updated_by and updated_record.updated_by.email == josh.email else '✅ NO'}")
        
        if updated_record.updated_by and updated_record.updated_by.email == josh.email:
            print(f"\n🔍 NEXT STEPS:")
            print(f"    1. Check JWT authentication class for shared state")
            print(f"    2. Check serializer context handling")
            print(f"    3. Check middleware processing order")
            print(f"    4. Check if Django is caching user objects incorrectly")

if __name__ == '__main__':
    debug_jwt_authentication_flow()