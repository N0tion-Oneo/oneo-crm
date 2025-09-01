#!/usr/bin/env python
"""
Check if we can see any webhook activity in logs or identify configuration issues
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from django.utils import timezone

print("=" * 80)
print("WEBHOOK CONFIGURATION CHECK")
print("=" * 80)

# Check what the webhook URL should be
print("\n1. Webhook URL Configuration:")
print("-" * 40)

# Get the current host
import socket
try:
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
except:
    hostname = "localhost"
    local_ip = "127.0.0.1"

print(f"Local hostname: {hostname}")
print(f"Local IP: {local_ip}")
print(f"\nWebhook URL should be configured in UniPile as:")
print(f"  Development: http://localhost:8000/webhooks/unipile/")
print(f"  Production: https://your-domain.com/webhooks/unipile/")
print(f"\n  OR if using ngrok/tunnel:")
print(f"  https://your-tunnel.ngrok.io/webhooks/unipile/")

# Check if we're running in DEBUG mode
from django.conf import settings
print(f"\n2. Django Settings:")
print("-" * 40)
print(f"DEBUG: {settings.DEBUG}")
print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")

# Check webhook secret configuration
print(f"\n3. Webhook Security:")
print("-" * 40)
webhook_secret = getattr(settings, 'UNIPILE_WEBHOOK_SECRET', None)
if webhook_secret:
    print(f"✅ Webhook secret is configured (length: {len(webhook_secret)})")
else:
    print("⚠️ No webhook secret configured (webhooks may be rejected)")

# Check UniPile configuration
with schema_context('oneotalent'):
    from communications.models import UserChannelConnection
    
    print(f"\n4. UniPile Account Configuration:")
    print("-" * 40)
    
    gmail_conn = UserChannelConnection.objects.filter(
        channel_type='gmail',
        is_active=True
    ).first()
    
    if gmail_conn:
        print(f"✅ Gmail account connected")
        print(f"   Account ID: {gmail_conn.unipile_account_id}")
        print(f"   Last sync: {gmail_conn.last_sync_at}")
        
        # Check if webhooks are enabled
        if gmail_conn.connection_config:
            webhook_enabled = gmail_conn.connection_config.get('webhook_enabled', False)
            webhook_url = gmail_conn.connection_config.get('webhook_url', '')
            print(f"\n   Webhook enabled: {webhook_enabled}")
            print(f"   Webhook URL in config: {webhook_url}")
        else:
            print(f"\n   ⚠️ No connection config found")
    
    print(f"\n5. Testing Webhook Endpoint:")
    print("-" * 40)
    
    # Test if the webhook endpoint is accessible
    import requests
    test_url = "http://localhost:8000/webhooks/health/"
    
    try:
        response = requests.get(test_url, timeout=2)
        if response.status_code == 200:
            print(f"✅ Webhook health endpoint is accessible")
            print(f"   Response: {response.json()}")
        else:
            print(f"⚠️ Webhook health endpoint returned status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to webhook endpoint at {test_url}")
        print(f"   Make sure the Django server is running")
    except Exception as e:
        print(f"❌ Error testing webhook: {e}")

print("\n" + "=" * 80)
print("NEXT STEPS:")
print("=" * 80)
print("\n1. Check UniPile Dashboard:")
print("   - Go to your UniPile account dashboard")
print("   - Check if webhooks are enabled for your Gmail account")
print("   - Verify the webhook URL is correctly configured")
print("   - Check if there are any webhook delivery errors")
print("\n2. If using local development:")
print("   - UniPile cannot reach localhost directly")
print("   - Use ngrok or similar tunnel service:")
print("     ngrok http 8000")
print("   - Configure the ngrok URL in UniPile")
print("\n3. Test webhook manually:")
print("   - Use the test scripts to verify the endpoint works")
print("   - Check Django server logs for incoming requests")
print("=" * 80)