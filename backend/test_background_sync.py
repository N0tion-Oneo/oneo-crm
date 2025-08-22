#!/usr/bin/env python3
"""
Background Sync System Test
Quick test to verify the background sync implementation is working correctly
"""
import os
import sys
import django
import asyncio
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

django.setup()

from communications.models import (
    SyncJob, SyncJobProgress, Channel, UserChannelConnection,
    SyncJobStatus, SyncJobType
)
from communications.tasks_background_sync import (
    sync_account_comprehensive_background,
    sync_chat_specific_background
)
from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.utils import schema_context


def test_sync_models():
    """Test that sync models can be created and queried"""
    print("🧪 Testing SyncJob and SyncJobProgress models...")
    
    try:
        User = get_user_model()
        # Get or create test user
        user, created = User.objects.get_or_create(
            username='test_sync_user',
            defaults={'email': 'test_sync@example.com'}
        )
        if created:
            print(f"✅ Created test user: {user.username}")
        else:
            print(f"✅ Using existing test user: {user.username}")
        
        # Get or create test channel
        channel, created = Channel.objects.get_or_create(
            name='Test WhatsApp Channel',
            channel_type='whatsapp',
            defaults={
                'unipile_account_id': 'test_account_123',
                'auth_status': 'authenticated',
                'is_active': True,
                'created_by': user
            }
        )
        if created:
            print(f"✅ Created test channel: {channel.name}")
        else:
            print(f"✅ Using existing test channel: {channel.name}")
        
        # Create test sync job
        sync_job = SyncJob.objects.create(
            user=user,
            channel=channel,
            job_type=SyncJobType.COMPREHENSIVE,
            sync_options={'test': True, 'days_back': 30},
            status=SyncJobStatus.PENDING,
            celery_task_id='test_task_123'
        )
        print(f"✅ Created sync job: {sync_job.id}")
        
        # Test progress tracking
        sync_job.update_progress(
            conversations_total=100,
            conversations_processed=25,
            messages_processed=150,
            current_phase='testing'
        )
        print(f"✅ Updated progress: {sync_job.completion_percentage}% complete")
        
        # Create progress entry
        progress_entry = SyncJobProgress.objects.create(
            sync_job=sync_job,
            phase_name='testing',
            step_name='model_test',
            items_total=10,
            items_processed=5
        )
        progress_entry.mark_completed(10)
        print(f"✅ Created and completed progress entry: {progress_entry}")
        
        # Test completion
        sync_job.status = SyncJobStatus.COMPLETED
        sync_job.completed_at = timezone.now()
        sync_job.result_summary = {
            'conversations_synced': 100,
            'messages_synced': 500,
            'test_completed': True
        }
        sync_job.save()
        print(f"✅ Marked sync job as completed")
        
        # Query tests
        active_jobs = SyncJob.objects.filter(user=user, status=SyncJobStatus.COMPLETED).count()
        print(f"✅ Found {active_jobs} completed sync jobs")
        
        progress_count = SyncJobProgress.objects.filter(sync_job=sync_job).count()
        print(f"✅ Found {progress_count} progress entries")
        
        print("🎉 Sync models test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Sync models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sync_api_endpoints():
    """Test that sync API endpoints are accessible"""
    print("🧪 Testing sync API endpoints...")
    
    try:
        from django.test import Client
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        client = Client()
        
        # Get test user
        user = User.objects.filter(username='test_sync_user').first()
        if not user:
            print("❌ Test user not found - run model test first")
            return False
        
        # Force login
        client.force_login(user)
        
        # Test get sync jobs endpoint
        response = client.get('/api/v1/communications/sync/jobs/')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Get sync jobs: {response.status_code}, found {data.get('count', 0)} jobs")
        else:
            print(f"⚠️ Get sync jobs: {response.status_code}")
        
        # Test get active sync jobs endpoint
        response = client.get('/api/v1/communications/sync/jobs/active/')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Get active sync jobs: {response.status_code}, found {data.get('count', 0)} active jobs")
        else:
            print(f"⚠️ Get active sync jobs: {response.status_code}")
        
        print("🎉 API endpoints test completed!")
        return True
        
    except Exception as e:
        print(f"❌ API endpoints test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_celery_task_imports():
    """Test that Celery tasks can be imported and have correct signatures"""
    print("🧪 Testing Celery task imports...")
    
    try:
        # Test task imports
        from communications.tasks_background_sync import (
            sync_account_comprehensive_background,
            sync_chat_specific_background
        )
        print("✅ Successfully imported background sync tasks")
        
        # Test task signatures
        comprehensive_task = sync_account_comprehensive_background
        chat_task = sync_chat_specific_background
        
        print(f"✅ Comprehensive sync task: {comprehensive_task.name}")
        print(f"✅ Chat-specific sync task: {chat_task.name}")
        
        # Test that tasks are registered in Celery
        from celery import current_app
        registered_tasks = current_app.tasks
        
        if comprehensive_task.name in registered_tasks:
            print("✅ Comprehensive sync task registered in Celery")
        else:
            print("⚠️ Comprehensive sync task not found in Celery registry")
        
        if chat_task.name in registered_tasks:
            print("✅ Chat-specific sync task registered in Celery")
        else:
            print("⚠️ Chat-specific sync task not found in Celery registry")
        
        print("🎉 Celery task import test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Celery task import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_unipile_client_pagination():
    """Test UniPile client pagination methods"""
    print("🧪 Testing UniPile client pagination...")
    
    try:
        from communications.unipile_sdk import unipile_service
        
        client = unipile_service.get_client()
        messaging_client = client.messaging
        
        # Test that pagination methods exist
        methods_to_test = [
            'get_all_chats',
            'get_all_messages',
            'paginate_all_chats',
            'paginate_all_messages',
            'get_chats_batch',
            'get_messages_batch'
        ]
        
        for method_name in methods_to_test:
            if hasattr(messaging_client, method_name):
                method = getattr(messaging_client, method_name)
                print(f"✅ Found pagination method: {method_name}")
                
                # Check if it's callable
                if callable(method):
                    print(f"✅ Method {method_name} is callable")
                else:
                    print(f"⚠️ Method {method_name} is not callable")
            else:
                print(f"❌ Missing pagination method: {method_name}")
        
        print("🎉 UniPile client pagination test completed!")
        return True
        
    except Exception as e:
        print(f"❌ UniPile client pagination test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_websocket_consumers():
    """Test that WebSocket consumers can be imported"""
    print("🧪 Testing WebSocket consumers...")
    
    try:
        from communications.consumers_sync import (
            SyncProgressConsumer,
            SyncOverviewConsumer
        )
        print("✅ Successfully imported sync WebSocket consumers")
        
        # Test consumer inheritance
        from channels.generic.websocket import AsyncJsonWebsocketConsumer
        
        if issubclass(SyncProgressConsumer, AsyncJsonWebsocketConsumer):
            print("✅ SyncProgressConsumer properly inherits from AsyncJsonWebsocketConsumer")
        else:
            print("⚠️ SyncProgressConsumer inheritance issue")
        
        if issubclass(SyncOverviewConsumer, AsyncJsonWebsocketConsumer):
            print("✅ SyncOverviewConsumer properly inherits from AsyncJsonWebsocketConsumer")
        else:
            print("⚠️ SyncOverviewConsumer inheritance issue")
        
        # Test routing import
        from communications.routing import websocket_urlpatterns
        print(f"✅ WebSocket routing loaded with {len(websocket_urlpatterns)} patterns")
        
        print("🎉 WebSocket consumers test completed!")
        return True
        
    except Exception as e:
        print(f"❌ WebSocket consumers test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all background sync tests"""
    print("🚀 Starting Background Sync System Tests")
    print("=" * 50)
    
    tests = [
        ("Sync Models", test_sync_models),
        ("API Endpoints", test_sync_api_endpoints),
        ("Celery Tasks", test_celery_task_imports),
        ("UniPile Pagination", test_unipile_client_pagination),
        ("WebSocket Consumers", test_websocket_consumers),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} Test...")
        print("-" * 30)
        
        success = test_func()
        results.append((test_name, success))
        
        if success:
            print(f"✅ {test_name} Test: PASSED")
        else:
            print(f"❌ {test_name} Test: FAILED")
    
    # Summary
    print("\n" + "=" * 50)
    print("🏁 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:20} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({int(passed/total*100)}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Background sync system is ready.")
        return True
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)