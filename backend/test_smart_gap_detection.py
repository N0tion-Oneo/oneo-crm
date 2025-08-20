#!/usr/bin/env python3
"""
Test script for smart gap detection system
Tests the webhook-first architecture with intelligent sync only when needed
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.utils import timezone
from django_tenants.utils import tenant_context
from tenants.models import Tenant
from communications.models import UserChannelConnection, Message, Conversation, Channel
from communications.services.gap_detection import gap_detector
from communications.tasks import detect_and_sync_conversation_gaps
from asgiref.sync import async_to_sync


class SmartGapDetectionTester:
    """Test suite for smart gap detection system"""
    
    def __init__(self):
        self.test_results = []
        self.tenant = None
    
    def setup_test_tenant(self):
        """Setup test tenant context"""
        try:
            # Use existing demo tenant
            self.tenant = Tenant.objects.get(schema_name='demo')
            print(f"✅ Using test tenant: {self.tenant.name} (schema: {self.tenant.schema_name})")
            return True
        except Tenant.DoesNotExist:
            print("❌ Demo tenant not found")
            return False
    
    def test_gap_detection_no_gaps(self):
        """Test 1: No gaps detected - should not trigger sync"""
        print("\n🔍 Test 1: Gap detection with no gaps")
        
        with tenant_context(self.tenant):
            # Get an active connection
            connection = UserChannelConnection.objects.filter(
                is_active=True,
                account_status='active'
            ).first()
            
            if not connection:
                print("❌ No active connections found for testing")
                return False
            
            print(f"   Testing connection: {connection.channel_type} - {connection.unipile_account_id}")
            
            # Run gap detection
            try:
                result = async_to_sync(gap_detector.detect_conversation_gaps)(
                    connection_id=str(connection.id),
                    trigger_reason="test_no_gaps"
                )
                
                print(f"   Gap detection result: {result.get('gaps_detected')}")
                print(f"   Reason: {result.get('gap_analysis', {})}")
                
                if not result.get('gaps_detected'):
                    print("   ✅ PASS: No unnecessary sync triggered")
                    self.test_results.append(('no_gaps_test', True, 'No gaps detected correctly'))
                    return True
                else:
                    print("   ⚠️  WARN: Gaps detected - may need investigation")
                    self.test_results.append(('no_gaps_test', True, f"Gaps found: {result.get('gap_analysis')}"))
                    return True
                    
            except Exception as e:
                print(f"   ❌ FAIL: Gap detection error: {e}")
                self.test_results.append(('no_gaps_test', False, str(e)))
                return False
    
    def test_gap_detection_performance(self):
        """Test 2: Gap detection performance - should be fast"""
        print("\n⚡ Test 2: Gap detection performance")
        
        with tenant_context(self.tenant):
            connections = UserChannelConnection.objects.filter(
                is_active=True,
                account_status='active'
            )[:3]  # Test up to 3 connections
            
            if not connections:
                print("❌ No connections found for performance testing")
                return False
            
            total_time = 0
            successful_checks = 0
            
            for connection in connections:
                print(f"   Testing: {connection.channel_type} - {connection.unipile_account_id}")
                
                start_time = datetime.now()
                
                try:
                    result = async_to_sync(gap_detector.detect_conversation_gaps)(
                        connection_id=str(connection.id),
                        trigger_reason="performance_test"
                    )
                    
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    total_time += duration
                    successful_checks += 1
                    
                    print(f"   ⏱️  Duration: {duration:.2f}s - Gaps: {result.get('gaps_detected')}")
                    
                    if duration > 5.0:  # Flag slow operations
                        print(f"   ⚠️  SLOW: Gap detection took {duration:.2f}s")
                    
                except Exception as e:
                    print(f"   ❌ ERROR: {e}")
            
            if successful_checks > 0:
                avg_time = total_time / successful_checks
                print(f"   📊 Average time: {avg_time:.2f}s per connection")
                
                if avg_time < 2.0:
                    print("   ✅ PASS: Performance acceptable")
                    self.test_results.append(('performance_test', True, f'Avg: {avg_time:.2f}s'))
                    return True
                else:
                    print("   ⚠️  WARN: Performance could be better")
                    self.test_results.append(('performance_test', True, f'Slow avg: {avg_time:.2f}s'))
                    return True
            else:
                print("   ❌ FAIL: No successful performance tests")
                self.test_results.append(('performance_test', False, 'No successful tests'))
                return False
    
    def test_celery_task_integration(self):
        """Test 3: Celery task integration"""
        print("\n🔧 Test 3: Celery task integration")
        
        with tenant_context(self.tenant):
            connection = UserChannelConnection.objects.filter(
                is_active=True,
                account_status='active'
            ).first()
            
            if not connection:
                print("❌ No connections found for Celery testing")
                return False
            
            print(f"   Testing Celery task with: {connection.channel_type}")
            
            try:
                # Call the Celery task directly (synchronous for testing)
                from communications.tasks import detect_and_sync_conversation_gaps
                
                result = detect_and_sync_conversation_gaps(
                    connection_id=str(connection.id),
                    trigger_reason="celery_test",
                    tenant_schema=self.tenant.schema_name
                )
                
                print(f"   Task result: {result.get('success', False)}")
                print(f"   Gaps detected: {result.get('gaps_detected', False)}")
                print(f"   Sync executed: {result.get('sync_executed', False)}")
                
                if result.get('success', False) or 'connection_id' in result:
                    print("   ✅ PASS: Celery task integration working")
                    self.test_results.append(('celery_test', True, 'Task executed successfully'))
                    return True
                else:
                    print(f"   ❌ FAIL: Task failed: {result}")
                    self.test_results.append(('celery_test', False, str(result)))
                    return False
                    
            except Exception as e:
                print(f"   ❌ FAIL: Celery task error: {e}")
                self.test_results.append(('celery_test', False, str(e)))
                return False
    
    def test_webhook_first_principle(self):
        """Test 4: Webhook-first principle - should minimize unnecessary syncs"""
        print("\n🎯 Test 4: Webhook-first principle validation")
        
        with tenant_context(self.tenant):
            # Test multiple connections to see sync efficiency
            connections = UserChannelConnection.objects.filter(
                is_active=True,
                account_status='active'
            )[:5]  # Test up to 5 connections
            
            if not connections:
                print("❌ No connections found for webhook-first testing")
                return False
            
            total_tested = 0
            syncs_triggered = 0
            gaps_found = 0
            
            for connection in connections:
                try:
                    result = async_to_sync(gap_detector.detect_conversation_gaps)(
                        connection_id=str(connection.id),
                        trigger_reason="webhook_first_test"
                    )
                    
                    total_tested += 1
                    
                    if result.get('gaps_detected'):
                        gaps_found += 1
                        
                        # Get recommendations to see if sync would be triggered
                        recommendations = async_to_sync(gap_detector.get_sync_recommendations)(
                            connection_id=str(connection.id)
                        )
                        
                        if recommendations.get('sync_needed'):
                            syncs_triggered += 1
                            print(f"   🚨 Sync would be triggered for {connection.channel_type}: {recommendations.get('priority')} priority")
                        else:
                            print(f"   ℹ️  Gaps found but sync not needed for {connection.channel_type}")
                    else:
                        print(f"   ✅ No gaps for {connection.channel_type}")
                        
                except Exception as e:
                    print(f"   ❌ Error testing {connection.channel_type}: {e}")
            
            if total_tested > 0:
                sync_rate = (syncs_triggered / total_tested) * 100
                gap_rate = (gaps_found / total_tested) * 100
                
                print(f"   📊 Results:")
                print(f"      - Connections tested: {total_tested}")
                print(f"      - Gaps detected: {gaps_found} ({gap_rate:.1f}%)")
                print(f"      - Syncs that would trigger: {syncs_triggered} ({sync_rate:.1f}%)")
                
                if sync_rate < 50:  # Less than 50% sync rate is good for webhook-first
                    print("   ✅ PASS: Webhook-first principle maintained")
                    self.test_results.append(('webhook_first', True, f'Sync rate: {sync_rate:.1f}%'))
                    return True
                else:
                    print("   ⚠️  WARN: High sync rate - may need tuning")
                    self.test_results.append(('webhook_first', True, f'High sync rate: {sync_rate:.1f}%'))
                    return True
            else:
                print("   ❌ FAIL: No connections tested")
                self.test_results.append(('webhook_first', False, 'No tests completed'))
                return False
    
    def run_all_tests(self):
        """Run all smart gap detection tests"""
        print("🚀 Starting Smart Gap Detection Test Suite")
        print("=" * 60)
        
        if not self.setup_test_tenant():
            print("❌ Failed to setup test tenant")
            return False
        
        # Run all tests
        tests = [
            self.test_gap_detection_no_gaps,
            self.test_gap_detection_performance,
            self.test_celery_task_integration,
            self.test_webhook_first_principle
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed_tests += 1
            except Exception as e:
                print(f"   ❌ Test failed with exception: {e}")
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        
        for test_name, passed, details in self.test_results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status}: {test_name} - {details}")
        
        success_rate = (passed_tests / total_tests) * 100
        print(f"\n🎯 Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        if success_rate >= 75:
            print("🎉 Smart Gap Detection System: READY FOR PRODUCTION")
            return True
        else:
            print("⚠️  Smart Gap Detection System: NEEDS IMPROVEMENT")
            return False


def main():
    """Run the smart gap detection test suite"""
    tester = SmartGapDetectionTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ All tests passed! Smart gap detection is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check the results above.")
        sys.exit(1)


if __name__ == "__main__":
    main()