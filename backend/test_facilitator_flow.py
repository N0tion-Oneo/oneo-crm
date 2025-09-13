#!/usr/bin/env python
"""
Test script for the complete facilitator meeting flow
"""
import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from authentication.models import CustomUser as User
from communications.scheduling.models import MeetingType, FacilitatorBooking
from pipelines.models import Pipeline, Record

def test_facilitator_flow():
    """Test the complete facilitator meeting flow"""
    
    # Use oneotalent tenant for testing
    tenant_schema = 'oneotalent'
    
    with schema_context(tenant_schema):
        print("🧪 Testing Facilitator Meeting Flow")
        print("=" * 50)
        
        # 1. Check for existing facilitator meeting type
        print("\n1️⃣ Checking for facilitator meeting type...")
        
        try:
            # Get the admin user
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                print("❌ No admin user found. Please create one first.")
                return
            
            # Get or create a facilitator meeting type
            meeting_type = MeetingType.objects.filter(
                meeting_mode='facilitator',
                is_active=True
            ).first()
            
            if meeting_type:
                print(f"✅ Found facilitator meeting type: {meeting_type.name}")
            else:
                print("❌ No facilitator meeting type found. Please create one in the UI.")
                return
            
            # 2. Check for pipeline and records
            print("\n2️⃣ Checking for pipeline and records...")
            
            if not meeting_type.pipeline_id:
                print("❌ Meeting type has no pipeline configured.")
                return
            
            pipeline = Pipeline.objects.filter(id=meeting_type.pipeline_id).first()
            if not pipeline:
                print("❌ Pipeline not found.")
                return
            
            print(f"✅ Found pipeline: {pipeline.name}")
            
            # Get some records
            records = Record.objects.filter(pipeline=pipeline, is_deleted=False)[:5]
            if records.count() < 2:
                print("❌ Need at least 2 records in the pipeline to test.")
                print("   Creating test records...")
                
                # Create test records
                Record.objects.create(
                    pipeline=pipeline,
                    data={
                        'name': 'Test Participant 1',
                        'email': 'participant1@test.com',
                        'phone': '555-0001'
                    }
                )
                Record.objects.create(
                    pipeline=pipeline,
                    data={
                        'name': 'Test Participant 2',
                        'email': 'participant2@test.com',
                        'phone': '555-0002'
                    }
                )
                records = Record.objects.filter(pipeline=pipeline, is_deleted=False)[:2]
            
            print(f"✅ Found {records.count()} records")
            
            # 3. Check facilitator bookings
            print("\n3️⃣ Checking existing facilitator bookings...")
            
            bookings = FacilitatorBooking.objects.filter(
                meeting_type=meeting_type
            ).order_by('-created_at')[:5]
            
            if bookings:
                print(f"✅ Found {bookings.count()} existing bookings:")
                for booking in bookings:
                    print(f"   - {booking.status}: P1={booking.participant_1_name}, P2={booking.participant_2_name}")
                    print(f"     Created: {booking.created_at}")
                    if booking.status == 'pending_p1':
                        print(f"     P1 Token URL: /book/facilitator/{booking.participant_1_token}/participant1/")
                    elif booking.status == 'pending_p2':
                        print(f"     P2 Token URL: /book/facilitator/{booking.participant_2_token}/")
            else:
                print("ℹ️ No existing bookings found.")
            
            # 4. Test creating a new booking
            print("\n4️⃣ Testing booking creation...")
            
            # Extract data from first two records
            r1 = records[0]
            r2 = records[1]
            
            # Look for email fields
            r1_email = None
            r1_name = None
            r2_email = None
            r2_name = None
            
            for field, value in r1.data.items():
                if 'email' in field.lower() and value:
                    r1_email = value
                if 'name' in field.lower() and value:
                    r1_name = value
            
            for field, value in r2.data.items():
                if 'email' in field.lower() and value:
                    r2_email = value
                if 'name' in field.lower() and value:
                    r2_name = value
            
            if not r1_email or not r2_email:
                print("⚠️ Records don't have email fields. Using test emails.")
                r1_email = r1_email or 'test.p1@example.com'
                r2_email = r2_email or 'test.p2@example.com'
            
            print(f"   Creating booking between:")
            print(f"   - P1: {r1_name or 'Unknown'} ({r1_email})")
            print(f"   - P2: {r2_name or 'Unknown'} ({r2_email})")
            
            # Create a test booking
            from django.utils import timezone
            from datetime import timedelta
            
            booking = FacilitatorBooking.objects.create(
                meeting_type=meeting_type,
                facilitator=admin_user,
                
                # Participant 1
                participant_1_record_id=str(r1.id),
                participant_1_email=r1_email,
                participant_1_name=r1_name or '',
                participant_1_data=r1.data,
                
                # Participant 2
                participant_2_record_id=str(r2.id),
                participant_2_email=r2_email,
                participant_2_name=r2_name or '',
                participant_2_data=r2.data,
                
                # Status and expiry
                status='pending_p1',
                expires_at=timezone.now() + timedelta(hours=72)
            )
            
            print(f"✅ Booking created successfully!")
            print(f"   Booking ID: {booking.id}")
            print(f"   Status: {booking.status}")
            print(f"   P1 Token: {booking.participant_1_token}")
            print(f"   P2 Token: {booking.participant_2_token}")
            
            # 5. Display test URLs
            print("\n5️⃣ Test URLs:")
            print("=" * 50)
            print(f"Dashboard (Facilitator): http://localhost:3000/settings/communications/scheduling")
            print(f"P1 Configuration: http://localhost:3000/book/facilitator/{booking.participant_1_token}/participant1/")
            print(f"P2 Selection: http://localhost:3000/book/facilitator/{booking.participant_2_token}/")
            
            print("\n✅ Test complete! You can now:")
            print("1. Go to the dashboard and click 'Send' on the facilitator meeting")
            print("2. Select two participants from the pipeline records")
            print("3. Use the P1 URL to configure the meeting")
            print("4. Use the P2 URL to select a time")
            
        except Exception as e:
            print(f"❌ Error during test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_facilitator_flow()