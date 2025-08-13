#!/usr/bin/env python3
"""
Test script for encrypted share links workflow
Tests the complete flow: generate share link -> access shared record
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TENANT_URL = "http://demo.localhost:8000"

def test_share_links_workflow():
    """Test the complete share links workflow"""
    
    print("🧪 Testing Encrypted Share Links Workflow")
    print("=" * 50)
    
    # Step 1: Test authentication
    print("\n1. Testing authentication...")
    
    # Test login endpoint
    login_data = {
        "email": "admin@demo.com",
        "password": "admin123"
    }
    
    try:
        login_response = requests.post(
            f"{TENANT_URL}/auth/login/",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        if login_response.status_code == 200:
            auth_data = login_response.json()
            access_token = auth_data.get('access')
            if access_token:
                print(f"✅ Authentication successful")
                headers = {"Authorization": f"Bearer {access_token}"}
            else:
                print(f"❌ No access token in response: {auth_data}")
                return False
        else:
            print(f"❌ Authentication failed: {login_response.status_code} - {login_response.text}")
            return False
    
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to server at {TENANT_URL}")
        print("   Make sure the Django development server is running:")
        print("   cd backend && python manage.py runserver")
        return False
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False
    
    # Step 2: Get available pipelines
    print("\n2. Getting available pipelines...")
    
    try:
        pipelines_response = requests.get(
            f"{TENANT_URL}/api/v1/pipelines/",
            headers=headers
        )
        
        if pipelines_response.status_code == 200:
            pipelines_data = pipelines_response.json()
            if pipelines_data.get('results'):
                pipeline = pipelines_data['results'][0]
                pipeline_id = pipeline['id']
                print(f"✅ Found pipeline: {pipeline['name']} (ID: {pipeline_id})")
            else:
                print("❌ No pipelines found. Creating a test pipeline...")
                # Create a simple test pipeline
                create_pipeline_data = {
                    "name": "Test Share Pipeline",
                    "description": "Pipeline for testing share links",
                    "access_level": "internal"
                }
                
                create_response = requests.post(
                    f"{TENANT_URL}/api/v1/pipelines/",
                    json=create_pipeline_data,
                    headers=headers
                )
                
                if create_response.status_code == 201:
                    pipeline = create_response.json()
                    pipeline_id = pipeline['id']
                    print(f"✅ Created test pipeline: {pipeline['name']} (ID: {pipeline_id})")
                else:
                    print(f"❌ Failed to create pipeline: {create_response.status_code} - {create_response.text}")
                    return False
        else:
            print(f"❌ Failed to get pipelines: {pipelines_response.status_code} - {pipelines_response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Pipeline retrieval error: {e}")
        return False
    
    # Step 3: Get existing records or create one
    print("\n3. Getting or creating a test record...")
    
    try:
        records_response = requests.get(
            f"{TENANT_URL}/api/v1/pipelines/{pipeline_id}/records/",
            headers=headers
        )
        
        if records_response.status_code == 200:
            records_data = records_response.json()
            if records_data.get('results'):
                record = records_data['results'][0]
                record_id = record['id']
                print(f"✅ Found existing record (ID: {record_id})")
            else:
                print("   No records found, creating a test record...")
                # Create a test record
                create_record_data = {
                    "data": {
                        "name": "Test Share Record",
                        "description": "Record for testing share links",
                        "status": "active"
                    }
                }
                
                create_record_response = requests.post(
                    f"{TENANT_URL}/api/v1/pipelines/{pipeline_id}/records/",
                    json=create_record_data,
                    headers=headers
                )
                
                if create_record_response.status_code == 201:
                    record = create_record_response.json()
                    record_id = record['id']
                    print(f"✅ Created test record (ID: {record_id})")
                else:
                    print(f"❌ Failed to create record: {create_record_response.status_code} - {create_record_response.text}")
                    return False
        else:
            print(f"❌ Failed to get records: {records_response.status_code} - {records_response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Record retrieval error: {e}")
        return False
    
    # Step 4: Generate share link
    print("\n4. Generating encrypted share link...")
    
    try:
        share_response = requests.post(
            f"{TENANT_URL}/api/v1/pipelines/{pipeline_id}/records/{record_id}/generate_share_link/",
            headers=headers
        )
        
        if share_response.status_code == 200:
            share_data = share_response.json()
            share_url = share_data.get('share_url')
            encrypted_token = share_data.get('encrypted_token')
            expires_at = share_data.get('expires_at')
            
            if share_url and encrypted_token:
                print(f"✅ Share link generated successfully")
                print(f"   📎 Share URL: {share_url}")
                print(f"   🔐 Token length: {len(encrypted_token)} characters")
                print(f"   ⏰ Expires: {datetime.fromtimestamp(expires_at).strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"❌ Invalid share link response: {share_data}")
                return False
        else:
            print(f"❌ Failed to generate share link: {share_response.status_code} - {share_response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Share link generation error: {e}")
        return False
    
    # Step 5: Access shared record (without authentication)
    print("\n5. Accessing shared record via encrypted link...")
    
    try:
        # Extract the encrypted token from the share URL
        # URL format: http://demo.localhost:8000/api/v1/shared-records/{encrypted_token}/
        token_from_url = share_url.split('/shared-records/')[-1].rstrip('/')
        
        shared_access_response = requests.get(
            f"{TENANT_URL}/api/v1/shared-records/{token_from_url}/",
            # No authentication headers - public access via encrypted token
        )
        
        if shared_access_response.status_code == 200:
            shared_data = shared_access_response.json()
            print(f"✅ Shared record accessed successfully")
            print(f"   📝 Record ID: {shared_data['record']['id']}")
            print(f"   📊 Pipeline: {shared_data['record']['pipeline']['name']}")
            print(f"   👤 Shared by: {shared_data['shared_by']}")
            print(f"   ⏱️ Time remaining: {shared_data['time_remaining_seconds']} seconds")
            print(f"   📅 Working days remaining: {shared_data['working_days_remaining']}")
            
            # Check if form schema is included
            if 'form_schema' in shared_data:
                form_schema = shared_data['form_schema']
                print(f"   📋 Form schema included with {len(form_schema.get('fields', []))} fields")
            else:
                print("   ⚠️ No form schema in response")
        else:
            print(f"❌ Failed to access shared record: {shared_access_response.status_code} - {shared_access_response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Shared record access error: {e}")
        return False
    
    # Step 6: Test analytics endpoint
    print("\n6. Testing access analytics...")
    
    try:
        analytics_response = requests.get(
            f"{TENANT_URL}/api/v1/shared-records/{token_from_url}/analytics/",
        )
        
        if analytics_response.status_code == 200:
            analytics_data = analytics_response.json()
            print(f"✅ Analytics accessed successfully")
            print(f"   📊 Access count: {analytics_data['access_count']}")
            print(f"   🌐 Unique IPs: {analytics_data['unique_ips']}")
            print(f"   ⏰ Last access: {analytics_data.get('last_access', 'N/A')}")
        else:
            print(f"❌ Failed to get analytics: {analytics_response.status_code} - {analytics_response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Analytics access error: {e}")
        return False
    
    # Step 7: Test preview endpoint
    print("\n7. Testing preview shared form...")
    
    try:
        preview_response = requests.get(
            f"{TENANT_URL}/api/v1/pipelines/{pipeline_id}/records/{record_id}/preview_shared_form/",
            headers=headers
        )
        
        if preview_response.status_code == 200:
            preview_data = preview_response.json()
            print(f"✅ Preview accessed successfully")
            print(f"   📋 Form has {len(preview_data['form_schema']['fields'])} fields")
            print(f"   🔗 Can generate shareable link: {preview_data['can_share']}")
        else:
            print(f"❌ Failed to get preview: {preview_response.status_code} - {preview_response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Preview access error: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All share link workflow tests passed!")
    print("\nNext steps:")
    print("- Share the URL with recipients")
    print("- Recipients can access without authentication")
    print("- Link expires automatically after 5 working days")
    print("- Access is tracked for analytics")
    
    return True

if __name__ == "__main__":
    success = test_share_links_workflow()
    sys.exit(0 if success else 1)