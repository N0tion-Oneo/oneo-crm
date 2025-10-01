#!/usr/bin/env python
"""
Test to make actual API calls to test live WebSocket updates
"""
import os
import django
import sys
import requests
import json
import time

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context

def test_live_websocket_updates():
    """Test WebSocket updates by making real API calls"""

    print('=== LIVE WEBSOCKET UPDATE TEST ===')
    print('This test will make actual API calls to trigger WebSocket updates')
    print('Make sure both backend and frontend are running!')
    print()

    # API endpoint configuration
    BASE_URL = 'http://oneotalent.localhost:8000'

    # You'll need to get a valid JWT token
    # This is a placeholder - you'd need to implement proper authentication
    headers = {
        'Content-Type': 'application/json',
        # 'Authorization': 'Bearer YOUR_JWT_TOKEN_HERE'
    }

    print("📋 Test Plan:")
    print("1. Check current record data via API")
    print("2. Update relationship via API call")
    print("3. Monitor backend logs for WebSocket transmissions")
    print("4. Check if frontend receives updates")
    print()

    # Test data
    company_record_id = 516
    contact_record_id = 518

    with schema_context('oneotalent'):
        from pipelines.models import Record

        # Get current record data
        company_record = Record.objects.get(id=company_record_id)
        print(f"📊 Current company record contacts: {company_record.data.get('contacts', [])}")

        # Test 1: Add relationship
        print("\n=== TEST 1: Adding Relationship ===")
        print(f"Setting contacts = [{contact_record_id}] on company record {company_record_id}")

        company_record.data = company_record.data or {}
        company_record.data['contacts'] = [contact_record_id]
        company_record.save()

        print("✅ Relationship added via direct record save")
        print("👀 Check backend logs for WebSocket broadcasts")
        print("👀 Check frontend for real-time updates")

        time.sleep(2)  # Give time for processing

        # Test 2: Remove relationship
        print("\n=== TEST 2: Removing Relationship ===")
        print("Setting contacts = [] on company record")

        company_record.data['contacts'] = []
        company_record.save()

        print("✅ Relationship removed via direct record save")
        print("👀 Check backend logs for WebSocket broadcasts")
        print("👀 Check frontend for real-time updates")

        time.sleep(2)  # Give time for processing

        print("\n=== MONITORING INSTRUCTIONS ===")
        print("1. Watch the backend logs for WebSocket broadcast messages")
        print("2. Look for these specific log patterns:")
        print("   - '📡 Broadcasting record update to WebSocket channels...'")
        print("   - '📡 → Pipeline channel: pipeline_records_24'")
        print("   - '📡 → Pipeline channel: pipeline_records_23'")
        print("   - Any ERROR messages about WebSocket transmission")
        print()
        print("3. Check if the frontend receives updates:")
        print("   - Open browser dev tools > Network > WS")
        print("   - Look for WebSocket messages")
        print("   - Verify record lists update in real-time")
        print()
        print("4. Verify channel subscriptions:")
        print("   - Backend should broadcast to: pipeline_records_24, pipeline_records_23")
        print("   - Frontend should be subscribed to the same channels")
        print()

        # Display final relationship status
        company_record.refresh_from_db()
        print(f"📊 Final company record contacts: {company_record.data.get('contacts', [])}")

if __name__ == '__main__':
    test_live_websocket_updates()