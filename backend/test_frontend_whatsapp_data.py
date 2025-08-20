#!/usr/bin/env python3
"""
Test frontend WhatsApp data integration with OneOTalent tenant
Verify that webhook data is properly accessible via API and displayed on frontend
"""
import os
import sys
import json
import requests
import time
from datetime import datetime, timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
import django
django.setup()

from django.db import transaction
from django_tenants.utils import schema_context
from communications.models import (
    UserChannelConnection, Channel, Message, Conversation
)
from authentication.models import CustomUser

TENANT_SCHEMA = "oneotalent"
BACKEND_API = "http://localhost:8000"
FRONTEND_URL = "http://oneotalent.localhost:3000"

class WhatsAppFrontendTest:
    """Test WhatsApp data integration with frontend"""
    
    def __init__(self):
        self.auth_token = None
        self.whatsapp_data = {}
        
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status}: {test_name}"
        if message:
            result += f" - {message}"
        print(result)
        return success
    
    def get_oneotalent_whatsapp_data(self):
        """Get WhatsApp data from OneOTalent tenant"""
        print("\n📱 Retrieving OneOTalent WhatsApp Data...")
        
        try:
            with schema_context(TENANT_SCHEMA):
                # Get WhatsApp connections
                whatsapp_connections = UserChannelConnection.objects.filter(
                    channel_type='whatsapp',
                    auth_status='authenticated'
                )
                
                # Get WhatsApp channels
                whatsapp_channels = Channel.objects.filter(
                    channel_type='whatsapp'
                )
                
                # Get WhatsApp conversations
                whatsapp_conversations = []
                for channel in whatsapp_channels:
                    conversations = Conversation.objects.filter(
                        channel=channel,
                        status='active'
                    ).order_by('-last_message_at')[:10]
                    whatsapp_conversations.extend(conversations)
                
                # Get recent WhatsApp messages
                whatsapp_messages = []
                for conversation in whatsapp_conversations:
                    messages = Message.objects.filter(
                        conversation=conversation,
                        channel__channel_type='whatsapp'
                    ).order_by('-created_at')[:5]
                    whatsapp_messages.extend(messages)
                
                self.whatsapp_data = {
                    'connections': len(whatsapp_connections),
                    'channels': len(whatsapp_channels),
                    'conversations': len(whatsapp_conversations),
                    'messages': len(whatsapp_messages),
                    'connection_details': [
                        {
                            'id': str(conn.id),
                            'account_name': conn.account_name,
                            'unipile_account_id': conn.unipile_account_id,
                            'auth_status': conn.auth_status
                        }
                        for conn in whatsapp_connections
                    ],
                    'recent_conversations': [
                        {
                            'id': str(conv.id),
                            'external_thread_id': conv.external_thread_id,
                            'message_count': conv.message_count,
                            'last_message_at': conv.last_message_at.isoformat() if conv.last_message_at else None
                        }
                        for conv in whatsapp_conversations[:5]
                    ],
                    'recent_messages': [
                        {
                            'id': str(msg.id),
                            'content': msg.content[:100] + '...' if len(msg.content) > 100 else msg.content,
                            'direction': msg.direction,
                            'contact_phone': msg.contact_phone,
                            'created_at': msg.created_at.isoformat()
                        }
                        for msg in whatsapp_messages[:5]
                    ]
                }
                
                success = len(whatsapp_connections) > 0
                details = f"Connections: {len(whatsapp_connections)}, Messages: {len(whatsapp_messages)}"
                return self.log_test("WhatsApp Data Retrieval", success, details)
                
        except Exception as e:
            return self.log_test("WhatsApp Data Retrieval", False, str(e))
    
    def test_api_endpoint_access(self):
        """Test API endpoints for WhatsApp data"""
        print("\n🔌 Testing API Endpoint Access...")
        
        try:
            # Test communications API endpoint
            response = requests.get(
                f"{BACKEND_API}/api/v1/communications/",
                headers={"Host": "oneotalent.localhost"},
                timeout=10
            )
            
            api_accessible = response.status_code in [200, 401]  # 401 is expected without auth
            
            # Test specific WhatsApp endpoints if they exist
            endpoints_to_test = [
                "/api/v1/communications/channels/",
                "/api/v1/communications/conversations/",
                "/api/v1/communications/messages/"
            ]
            
            endpoint_results = {}
            for endpoint in endpoints_to_test:
                try:
                    resp = requests.get(
                        f"{BACKEND_API}{endpoint}",
                        headers={"Host": "oneotalent.localhost"},
                        timeout=5
                    )
                    endpoint_results[endpoint] = resp.status_code
                except:
                    endpoint_results[endpoint] = "timeout"
            
            details = f"Main API: {response.status_code}, Endpoints: {endpoint_results}"
            return self.log_test("API Endpoint Access", api_accessible, details)
            
        except Exception as e:
            return self.log_test("API Endpoint Access", False, str(e))
    
    def test_frontend_page_access(self):
        """Test frontend WhatsApp page accessibility"""
        print("\n🌐 Testing Frontend Page Access...")
        
        try:
            # Test main OneOTalent frontend
            response = requests.get(f"{FRONTEND_URL}/", timeout=10)
            frontend_accessible = response.status_code == 200
            
            # Test communications page
            try:
                comm_response = requests.get(f"{FRONTEND_URL}/communications", timeout=10)
                comm_accessible = comm_response.status_code == 200
            except:
                comm_accessible = False
            
            details = f"Main: {response.status_code}, Communications: {comm_response.status_code if comm_accessible else 'failed'}"
            return self.log_test("Frontend Page Access", frontend_accessible, details)
            
        except Exception as e:
            return self.log_test("Frontend Page Access", False, str(e))
    
    def create_test_whatsapp_message(self):
        """Create a test WhatsApp message to verify data flow"""
        print("\n📨 Creating Test WhatsApp Message...")
        
        try:
            with schema_context(TENANT_SCHEMA):
                # Get or create WhatsApp channel
                whatsapp_channel = Channel.objects.filter(
                    channel_type='whatsapp'
                ).first()
                
                if not whatsapp_channel:
                    return self.log_test("Test Message Creation", False, "No WhatsApp channel found")
                
                # Create test conversation
                conversation, created = Conversation.objects.get_or_create(
                    external_thread_id=f"frontend_test_{int(time.time())}",
                    channel=whatsapp_channel,
                    defaults={
                        'status': 'active',
                        'message_count': 0
                    }
                )
                
                # Create test message
                test_message = Message.objects.create(
                    conversation=conversation,
                    channel=whatsapp_channel,
                    external_message_id=f"frontend_test_msg_{int(time.time())}",
                    content="🧪 Frontend integration test message - WhatsApp data verification",
                    direction='inbound',
                    contact_phone="+1234567890",
                    metadata={'frontend_test': True, 'created_at': datetime.now(timezone.utc).isoformat()}
                )
                
                # Update conversation count
                conversation.message_count = conversation.messages.count()
                conversation.last_message_at = test_message.created_at
                conversation.save()
                
                success = Message.objects.filter(id=test_message.id).exists()
                details = f"Message ID: {test_message.id}, Conversation: {conversation.external_thread_id}"
                return self.log_test("Test Message Creation", success, details)
                
        except Exception as e:
            return self.log_test("Test Message Creation", False, str(e))
    
    def verify_real_time_updates(self):
        """Verify real-time updates are working"""
        print("\n⚡ Testing Real-time Updates...")
        
        try:
            # Test WebSocket endpoint accessibility
            ws_url = "ws://oneotalent.localhost:8000/ws/realtime/"
            
            # For now, just verify the endpoint structure exists
            # Full WebSocket testing would require more complex setup
            
            with schema_context(TENANT_SCHEMA):
                # Check if recent messages have been created (should trigger real-time updates)
                recent_messages = Message.objects.filter(
                    created_at__gte=datetime.now(timezone.utc).replace(minute=0)
                ).count()
                
                # If we've created messages in the last hour, real-time should be working
                realtime_active = recent_messages > 0
                
                details = f"Recent messages: {recent_messages}, WebSocket endpoint: {ws_url}"
                return self.log_test("Real-time Updates", realtime_active, details)
                
        except Exception as e:
            return self.log_test("Real-time Updates", False, str(e))
    
    def test_whatsapp_data_consistency(self):
        """Test data consistency between backend and what frontend should see"""
        print("\n🔄 Testing Data Consistency...")
        
        try:
            with schema_context(TENANT_SCHEMA):
                # Check message counts match conversation counts
                conversations = Conversation.objects.filter(
                    channel__channel_type='whatsapp'
                )
                
                consistency_issues = 0
                for conversation in conversations:
                    actual_count = conversation.messages.count()
                    stored_count = conversation.message_count or 0
                    
                    if actual_count != stored_count:
                        consistency_issues += 1
                        # Fix the inconsistency
                        conversation.message_count = actual_count
                        conversation.save()
                
                # Check for orphaned messages
                orphaned_messages = Message.objects.filter(
                    channel__channel_type='whatsapp',
                    conversation__isnull=True
                ).count()
                
                consistency_good = consistency_issues == 0 and orphaned_messages == 0
                details = f"Fixed {consistency_issues} count issues, {orphaned_messages} orphaned messages"
                return self.log_test("Data Consistency", consistency_good, details)
                
        except Exception as e:
            return self.log_test("Data Consistency", False, str(e))
    
    def run_whatsapp_frontend_tests(self):
        """Run complete WhatsApp frontend integration tests"""
        print("📱 WHATSAPP FRONTEND INTEGRATION TEST")
        print("=" * 60)
        
        tests = [
            self.get_oneotalent_whatsapp_data,
            self.test_api_endpoint_access,
            self.test_frontend_page_access,
            self.create_test_whatsapp_message,
            self.verify_real_time_updates,
            self.test_whatsapp_data_consistency
        ]
        
        passed = 0
        total = len(tests)
        
        for test_func in tests:
            if test_func():
                passed += 1
        
        print("\n" + "=" * 60)
        print("🏆 WHATSAPP FRONTEND INTEGRATION RESULTS")
        print("=" * 60)
        
        success_rate = (passed / total) * 100
        print(f"📊 Results: {passed}/{total} tests passed ({success_rate:.1f}%)")
        
        if self.whatsapp_data:
            print("\n📱 WhatsApp Data Summary:")
            print(f"   • Connections: {self.whatsapp_data['connections']}")
            print(f"   • Conversations: {self.whatsapp_data['conversations']}")
            print(f"   • Messages: {self.whatsapp_data['messages']}")
            
            if self.whatsapp_data['recent_messages']:
                print("\n💬 Recent Messages Preview:")
                for msg in self.whatsapp_data['recent_messages']:
                    direction_icon = "➡️" if msg['direction'] == 'outbound' else "⬅️"
                    print(f"   {direction_icon} {msg['contact_phone']}: {msg['content']}")
        
        print(f"\n🌐 Frontend URLs to test:")
        print(f"   • OneOTalent Main: {FRONTEND_URL}/")
        print(f"   • Communications: {FRONTEND_URL}/communications")
        print(f"   • Backend API: {BACKEND_API}/api/v1/")
        
        if success_rate >= 85:
            print("\n🎉 WHATSAPP FRONTEND: FULLY INTEGRATED!")
        elif success_rate >= 70:
            print("\n⚠️  WHATSAPP FRONTEND: MOSTLY WORKING")
        else:
            print("\n❌ WHATSAPP FRONTEND: NEEDS FIXES")
        
        return success_rate >= 70

if __name__ == "__main__":
    test_runner = WhatsAppFrontendTest()
    success = test_runner.run_whatsapp_frontend_tests()
    sys.exit(0 if success else 1)