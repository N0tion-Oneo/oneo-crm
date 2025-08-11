#!/usr/bin/env python
"""
Test browser-level session isolation to investigate user context corruption
This test simulates multiple browser sessions to identify cross-contamination
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

import json
import time
import uuid
from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Record
from core.models import AuditLog
from django.contrib.sessions.models import Session
from django.conf import settings

User = get_user_model()

class BrowserSessionIsolationTest:
    """Test browser session isolation and cookie sharing"""
    
    def __init__(self):
        self.test_log = []
        
    def log(self, message, **data):
        """Log test events"""
        entry = {
            'timestamp': time.time(),
            'message': message,
            'data': data
        }
        self.test_log.append(entry)
        print(f"🔍 {message}")
        for key, value in data.items():
            print(f"    {key}: {value}")
    
    def setup_test_environment(self):
        """Setup test environment with users and pipeline"""
        with schema_context('oneotalent'):
            # Get test users
            josh = User.objects.get(email='josh@oneodigital.com')
            saul = User.objects.get(email='saul@oneodigital.com')
            
            # Get test data - find pipeline with records
            pipeline = None
            record = None
            
            for p in Pipeline.objects.filter(is_active=True):
                records = Record.objects.filter(pipeline=p, is_deleted=False)
                if records.exists():
                    pipeline = p
                    record = records.first()
                    break
            
            if not pipeline:
                raise Exception("No active pipeline found")
                
            if not record:
                raise Exception("No active record found")
            
            self.josh = josh
            self.saul = saul
            self.pipeline = pipeline
            self.record = record
            
            self.log("Test environment setup", 
                    josh_id=josh.id, josh_email=josh.email,
                    saul_id=saul.id, saul_email=saul.email,
                    pipeline_id=pipeline.id, record_id=record.id)
    
    def create_isolated_browser_client(self, user_name):
        """Create a completely isolated browser client (simulates separate browser)"""
        # Create new client with unique session
        client = Client()
        
        # Force new session by accessing it
        session = client.session
        session_key = client.session.session_key
        
        self.log(f"Created isolated browser client for {user_name}",
                session_key=session_key,
                client_id=id(client))
        
        return client
    
    def create_user_token(self, user):
        """Create JWT token for user"""
        with schema_context('oneotalent'):
            refresh = RefreshToken.for_user(user)
            refresh['tenant_schema'] = 'oneotalent'
            refresh['email'] = user.email
            token = str(refresh.access_token)
            
            self.log(f"Created JWT token for {user.email}",
                    user_id=user.id,
                    token_preview=token[:20] + '...')
            
            return token
    
    def simulate_browser_login(self, client, user, browser_name):
        """Simulate complete browser login process"""
        self.log(f"Simulating {browser_name} browser login for {user.email}")
        
        # Step 1: Create JWT token
        token = self.create_user_token(user)
        
        # Step 2: Store session info (what browser would do)
        session = client.session
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['tenant_schema'] = 'oneotalent'
        session.save()
        
        self.log(f"{browser_name} browser session created",
                session_key=client.session.session_key,
                user_id=user.id,
                user_email=user.email)
        
        return token
    
    def make_api_request(self, client, user, token, browser_name, test_value):
        """Make API request and track user context"""
        self.log(f"Making API request from {browser_name} browser as {user.email}")
        
        # Clear audit logs
        with schema_context('oneotalent'):
            AuditLog.objects.filter(model_name='Record', object_id=str(self.record.id)).delete()
        
        # Make the API call
        response = client.patch(
            f'/api/v1/pipelines/{self.pipeline.id}/records/{self.record.id}/',
            data=json.dumps({'data': {'company_name': test_value}}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
            HTTP_HOST='oneotalent.localhost'
        )
        
        self.log(f"{browser_name} API response",
                status_code=response.status_code,
                expected_user=user.email,
                test_value=test_value)
        
        # Check results
        time.sleep(0.2)  # Allow signal processing
        
        with schema_context('oneotalent'):
            # Check record update
            updated_record = Record.objects.get(id=self.record.id)
            record_user = updated_record.updated_by
            
            # Check audit log
            audit_log = AuditLog.objects.filter(
                model_name='Record',
                object_id=str(self.record.id),
                action='updated'
            ).order_by('-timestamp').first()
            
            result = {
                'browser': browser_name,
                'expected_user': user.email,
                'expected_user_id': user.id,
                'record_updated_by': record_user.email if record_user else None,
                'record_updated_by_id': record_user.id if record_user else None,
                'audit_user': audit_log.user.email if audit_log and audit_log.user else None,
                'audit_user_id': audit_log.user.id if audit_log and audit_log.user else None,
                'record_correct': record_user.email == user.email if record_user else False,
                'audit_correct': audit_log.user.email == user.email if audit_log and audit_log.user else False,
                'test_value': test_value,
                'session_key': client.session.session_key
            }
            
            self.log(f"{browser_name} results",
                    record_user_correct=result['record_correct'],
                    audit_user_correct=result['audit_correct'],
                    record_user=result['record_updated_by'],
                    audit_user=result['audit_user'])
            
            return result
    
    def test_session_isolation(self):
        """Test session isolation between different browser clients"""
        self.log("Starting session isolation test")
        
        # Create two completely isolated browser clients
        josh_browser = self.create_isolated_browser_client("Josh Normal")
        saul_browser = self.create_isolated_browser_client("Saul Private")
        
        # Simulate browser logins
        josh_token = self.simulate_browser_login(josh_browser, self.josh, "Josh Normal")
        saul_token = self.simulate_browser_login(saul_browser, self.saul, "Saul Private")
        
        # Verify isolation
        josh_session_key = josh_browser.session.session_key
        saul_session_key = saul_browser.session.session_key
        
        self.log("Session isolation check",
                josh_session_key=josh_session_key,
                saul_session_key=saul_session_key,
                sessions_isolated=josh_session_key != saul_session_key)
        
        # Make API calls
        test_timestamp = int(time.time())
        
        josh_result = self.make_api_request(
            josh_browser, self.josh, josh_token, "Josh Normal", 
            f"josh_test_{test_timestamp}"
        )
        
        saul_result = self.make_api_request(
            saul_browser, self.saul, saul_token, "Saul Private", 
            f"saul_test_{test_timestamp + 1}"
        )
        
        return josh_result, saul_result
    
    def test_cookie_sharing(self):
        """Test if cookies might be shared between browsers"""
        self.log("Testing cookie sharing simulation")
        
        # Create clients
        browser1 = self.create_isolated_browser_client("Browser1")
        browser2 = self.create_isolated_browser_client("Browser2")
        
        # Login Josh in browser1
        josh_token = self.create_user_token(self.josh)
        
        # Manually simulate cookie sharing (what could happen in browser)
        josh_session = browser1.session
        josh_session['user_id'] = self.josh.id
        josh_session['user_email'] = self.josh.email
        josh_session.save()
        
        # Try to use Josh's session key in browser2 (simulates cookie sharing)
        browser2.session = josh_session
        saul_token = self.create_user_token(self.saul)
        
        self.log("Cookie sharing test setup",
                browser1_session=browser1.session.session_key,
                browser2_session=browser2.session.session_key,
                sessions_shared=browser1.session.session_key == browser2.session.session_key)
        
        # Make API calls with different tokens but potentially shared session
        test_timestamp = int(time.time())
        
        josh_result = self.make_api_request(
            browser1, self.josh, josh_token, "Browser1 Josh", 
            f"josh_cookie_test_{test_timestamp}"
        )
        
        saul_result = self.make_api_request(
            browser2, self.saul, saul_token, "Browser2 Saul", 
            f"saul_cookie_test_{test_timestamp + 1}"
        )
        
        return josh_result, saul_result
    
    def test_session_database_state(self):
        """Test session database state"""
        self.log("Testing session database state")
        
        # Check Django sessions in database
        sessions = Session.objects.all()
        self.log("Active sessions in database",
                session_count=sessions.count())
        
        for i, session in enumerate(sessions):
            session_data = session.get_decoded()
            self.log(f"Session {i+1}",
                    session_key=session.session_key[:10] + '...',
                    expire_date=session.expire_date,
                    has_user_id='user_id' in session_data,
                    user_id=session_data.get('user_id'),
                    user_email=session_data.get('user_email'))
        
        return sessions
    
    def analyze_results(self, josh_result, saul_result, test_name):
        """Analyze test results for cross-contamination"""
        self.log(f"Analyzing {test_name} results")
        
        # Check for cross-contamination
        contamination_issues = []
        
        # Josh's request attributed to wrong user
        if not josh_result['record_correct']:
            contamination_issues.append(f"Josh's record update attributed to {josh_result['record_updated_by']}")
        
        if not josh_result['audit_correct']:
            contamination_issues.append(f"Josh's audit log attributed to {josh_result['audit_user']}")
        
        # Saul's request attributed to wrong user  
        if not saul_result['record_correct']:
            contamination_issues.append(f"Saul's record update attributed to {saul_result['record_updated_by']}")
        
        if not saul_result['audit_correct']:
            contamination_issues.append(f"Saul's audit log attributed to {saul_result['audit_user']}")
        
        # Check for cross-user attribution
        if (josh_result['record_updated_by'] == self.saul.email or 
            josh_result['audit_user'] == self.saul.email):
            contamination_issues.append("Josh's actions attributed to Saul")
            
        if (saul_result['record_updated_by'] == self.josh.email or 
            saul_result['audit_user'] == self.josh.email):
            contamination_issues.append("Saul's actions attributed to Josh")
        
        success = len(contamination_issues) == 0
        
        self.log(f"{test_name} analysis complete",
                success=success,
                contamination_issues=contamination_issues,
                josh_record_correct=josh_result['record_correct'],
                josh_audit_correct=josh_result['audit_correct'],
                saul_record_correct=saul_result['record_correct'],
                saul_audit_correct=saul_result['audit_correct'])
        
        return {
            'success': success,
            'contamination_issues': contamination_issues,
            'josh_result': josh_result,
            'saul_result': saul_result
        }

def main():
    """Run browser session isolation tests"""
    print("🔍 BROWSER SESSION ISOLATION INVESTIGATION")
    print("=" * 70)
    
    test = BrowserSessionIsolationTest()
    
    try:
        # Setup
        test.setup_test_environment()
        
        # Test 1: Session isolation
        print("\n📋 TEST 1: SESSION ISOLATION")
        josh_result1, saul_result1 = test.test_session_isolation()
        analysis1 = test.analyze_results(josh_result1, saul_result1, "Session Isolation")
        
        # Test 2: Cookie sharing simulation
        print("\n📋 TEST 2: COOKIE SHARING SIMULATION")
        josh_result2, saul_result2 = test.test_cookie_sharing()
        analysis2 = test.analyze_results(josh_result2, saul_result2, "Cookie Sharing")
        
        # Test 3: Session database state
        print("\n📋 TEST 3: SESSION DATABASE STATE")
        sessions = test.test_session_database_state()
        
        # Final analysis
        print("\n" + "=" * 70)
        print("🏁 BROWSER SESSION INVESTIGATION SUMMARY")
        print("=" * 70)
        
        print(f"📊 Session Isolation Test: {'✅ PASSED' if analysis1['success'] else '❌ FAILED'}")
        if analysis1['contamination_issues']:
            for issue in analysis1['contamination_issues']:
                print(f"    • {issue}")
        
        print(f"📊 Cookie Sharing Test: {'✅ PASSED' if analysis2['success'] else '❌ FAILED'}")
        if analysis2['contamination_issues']:
            for issue in analysis2['contamination_issues']:
                print(f"    • {issue}")
        
        print(f"📊 Active Django Sessions: {sessions.count()}")
        
        if analysis1['success'] and analysis2['success']:
            print(f"\n🎉 BROWSER SESSION ISOLATION: WORKING CORRECTLY")
            print("✅ No cross-contamination detected at Django session level")
            print("🔍 The issue likely exists at frontend cookie/storage level")
        else:
            print(f"\n⚠️  BROWSER SESSION ISOLATION: ISSUES DETECTED")
            print("🐛 Cross-contamination confirmed at Django session level")
            
            # Identify the specific pattern
            if (analysis1['josh_result']['audit_user'] == test.saul.email or 
                analysis1['saul_result']['audit_user'] == test.josh.email):
                print("🚨 USER CONTEXT CORRUPTION: Backend session mixing detected")
            elif (analysis2['josh_result']['audit_user'] == test.saul.email or 
                  analysis2['saul_result']['audit_user'] == test.josh.email):
                print("🚨 COOKIE SHARING: Browser cookie sharing causing issues")
                
        print(f"\n📋 Next Investigation Steps:")
        print("1. Check browser cookie domain settings (*.localhost vs specific domains)")
        print("2. Investigate frontend localStorage/sessionStorage state persistence")
        print("3. Test with completely different domains/ports")
        print("4. Check WebSocket connection user context")
        print("5. Verify JWT token isolation between browser windows")
        
    except Exception as e:
        test.log("Test failed with exception", error=str(e))
        print(f"❌ Test failed: {e}")

if __name__ == '__main__':
    main()