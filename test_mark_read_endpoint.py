#!/usr/bin/env python
"""
Test the mark_read endpoint to ensure it's working
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.record_communications.api import RecordCommunicationsViewSet
from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model
from pipelines.models import Record
from communications.models import Message, MessageStatus, MessageDirection

def test_mark_read_endpoint():
    """Test the mark_read endpoint"""
    
    with schema_context('oneotalent'):
        User = get_user_model()
        user = User.objects.filter(is_superuser=True).first()
        
        # Find a record with unread messages
        from communications.record_communications.models import RecordCommunicationLink
        
        # Get a record that has unread messages
        link_with_unread = RecordCommunicationLink.objects.filter(
            conversation__messages__direction=MessageDirection.INBOUND,
            conversation__messages__status=MessageStatus.DELIVERED
        ).first()
        
        if not link_with_unread:
            print("No records with unread messages found")
            return
        
        record = link_with_unread.record
        
        # Count unread messages before
        conversation_ids = RecordCommunicationLink.objects.filter(
            record=record
        ).values_list('conversation_id', flat=True)
        
        unread_before = Message.objects.filter(
            conversation_id__in=conversation_ids,
            direction=MessageDirection.INBOUND,
            status=MessageStatus.DELIVERED
        ).count()
        
        print(f"Testing mark_read endpoint for record {record.id}")
        print(f"Unread messages before: {unread_before}")
        
        if user:
            # Test the mark_read endpoint (with underscore)
            factory = APIRequestFactory()
            request = factory.post(f'/api/v1/communications/records/{record.id}/mark_read/', {})
            request.user = user
            
            view = RecordCommunicationsViewSet()
            view.request = request
            
            try:
                response = view.mark_read(request, pk=str(record.id))
                print(f"Response status: {response.status_code}")
                print(f"Response data: {response.data}")
                
                # Count unread messages after
                unread_after = Message.objects.filter(
                    conversation__recordcommunicationlink__record=record,
                    direction=MessageDirection.INBOUND,
                    status=MessageStatus.DELIVERED
                ).count()
                
                print(f"Unread messages after: {unread_after}")
                
                if response.status_code == 200:
                    print("✅ SUCCESS: mark_read endpoint is working!")
                    print(f"   Marked {response.data.get('messages_updated', 0)} messages as read")
                else:
                    print("❌ FAILED: Endpoint returned non-200 status")
                    
            except Exception as e:
                print(f"❌ ERROR calling endpoint: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("No superuser found")

if __name__ == "__main__":
    test_mark_read_endpoint()
    
    print("\n" + "="*50)
    print("ENDPOINT COMPATIBILITY STATUS")
    print("="*50)
    print("\nThe frontend is calling: POST /api/v1/communications/records/{id}/mark_read/")
    print("The backend now provides this endpoint for compatibility.")
    print("\nIf it's still not working from the frontend, check:")
    print("1. Authentication - is the JWT token valid?")
    print("2. CORS - are cross-origin requests allowed?")
    print("3. Network tab - what's the actual error response?")
    print("4. Console - any JavaScript errors?")