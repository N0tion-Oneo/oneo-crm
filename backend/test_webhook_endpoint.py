#!/usr/bin/env python
"""
Test the webhook endpoint directly
"""
import requests
import json
from datetime import datetime

def test_webhook_endpoint():
    """Test sending a webhook directly to our endpoint"""
    
    # Sample email webhook payload based on UniPile documentation
    webhook_payload = {
        "account_id": "xMePXCZVQVO0VsjKprRbfg",
        "account_type": "gmail",
        "webhook_name": "mail_received",
        "event": "mail_received",  # This is what the webhook view looks for
        "email_id": "test_email_123",
        "date": datetime.now().isoformat(),
        "from_attendee": {
            "identifier": "test@example.com",
            "name": "Test Sender"
        },
        "to_attendees": [
            {
                "identifier": "josh@oneodigital.com",
                "name": "Josh Cowan"
            }
        ],
        "subject": "🧪 Test HTML Email Formatting " + str(int(datetime.now().timestamp())),
        "body": {
            "html": "<div style='font-family: Arial, sans-serif;'><h2 style='color: #2563eb;'>🧪 Test HTML Email</h2><p>This is a <strong>test email</strong> with <em>HTML formatting</em> to verify that:</p><ul><li>HTML content is <b>properly rendered</b></li><li>Styles are <span style='color: green;'>preserved</span></li><li>Lists and formatting work correctly</li></ul><blockquote style='border-left: 4px solid #e5e7eb; padding-left: 16px; margin: 16px 0; font-style: italic;'>This is a blockquote to test email formatting</blockquote><p><a href='#' style='color: #3b82f6;'>Links should be styled properly</a></p></div>",
            "text": "🧪 Test HTML Email\n\nThis is a test email with HTML formatting to verify that:\n• HTML content is properly rendered\n• Styles are preserved\n• Lists and formatting work correctly\n\nThis is a blockquote to test email formatting\n\nLinks should be styled properly"
        },
        "message_id": "test_html_message_" + str(int(datetime.now().timestamp())),
        "thread_id": "test_html_thread_" + str(int(datetime.now().timestamp())),
        "is_complete": True,
        "has_attachments": False,
        "attachments": [],
        "folders": ["INBOX"],
        "role": "receiver",
        "origin": "received"
    }
    
    # Test both the direct webhook endpoint and the global router
    test_urls = [
        "http://localhost:8000/webhooks/unipile/",  # Direct to local server
        "https://webhooks.oneocrm.com/webhooks/unipile/"  # Cloudflare tunnel
    ]
    
    for url in test_urls:
        print(f"\n🧪 Testing webhook URL: {url}")
        
        try:
            response = requests.post(
                url,
                json=webhook_payload,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'UniPile-Test-Webhook/1.0'
                },
                timeout=10
            )
            
            print(f"✅ Status Code: {response.status_code}")
            print(f"✅ Response: {response.text}")
            
            if response.status_code == 200:
                print(f"🎉 Webhook endpoint is working!")
            else:
                print(f"⚠️ Webhook returned non-200 status: {response.status_code}")
                
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection failed: {e}")
        except requests.exceptions.Timeout as e:
            print(f"❌ Request timeout: {e}")
        except Exception as e:
            print(f"❌ Error testing webhook: {e}")

if __name__ == "__main__":
    print("🧪 Testing webhook endpoints...")
    test_webhook_endpoint()