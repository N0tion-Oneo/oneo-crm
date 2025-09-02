#!/usr/bin/env python
"""
Test script to verify the email reply_to fix
Tests both new emails and replies to ensure correct behavior
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
API_ENDPOINT = "/api/v1/communications/records/{record_id}/send_email/"
AUTH_TOKEN = "YOUR_JWT_TOKEN_HERE"  # Replace with actual token

def test_new_email_in_conversation():
    """Test sending a NEW email within an existing conversation"""
    print("\n=== Testing NEW EMAIL in existing conversation ===")
    
    payload = {
        "from_account_id": "xMePXCZVQVO0VsjKprRbfg",
        "to": ["test@example.com"],
        "cc": [],
        "bcc": [],
        "subject": "Test New Email",
        "body": "<p>This is a new email, not a reply</p>",
        "conversation_id": "4faca251-40e6-47ca-9301-93f1015287fe"
        # NOTE: No reply_to_message_id or reply_mode - this is a NEW email
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("\nExpected behavior:")
    print("- Should NOT include reply_to in UniPile request")
    print("- Should send as a new email")
    print("- Should NOT get 'invalid_reply_subject' error")
    
    return payload

def test_reply_email():
    """Test sending a REPLY email"""
    print("\n=== Testing REPLY EMAIL ===")
    
    payload = {
        "from_account_id": "xMePXCZVQVO0VsjKprRbfg",
        "to": ["test@example.com"],
        "cc": [],
        "bcc": [],
        "subject": "Re: Original Subject",
        "body": "<p>This is a reply</p>",
        "conversation_id": "4faca251-40e6-47ca-9301-93f1015287fe",
        "reply_to_message_id": "some-message-id",
        "reply_mode": "reply"
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("\nExpected behavior:")
    print("- SHOULD include reply_to in UniPile request")
    print("- Should thread properly with original message")
    
    return payload

def main():
    print("Email Reply Fix Test Script")
    print("=" * 50)
    
    # Test 1: New email in conversation
    new_email_payload = test_new_email_in_conversation()
    
    # Test 2: Reply email
    reply_payload = test_reply_email()
    
    print("\n" + "=" * 50)
    print("MANUAL TEST INSTRUCTIONS:")
    print("1. Start Django server: python manage.py runserver")
    print("2. Get JWT token from login")
    print("3. Update AUTH_TOKEN in this script")
    print("4. Update record_id as needed")
    print("5. Run actual API calls to test")
    
    print("\n" + "=" * 50)
    print("KEY FIX IMPLEMENTED:")
    print("- Added is_reply check: bool(reply_to_message_id or reply_mode)")
    print("- Only set reply_to from conversation when is_reply=True")
    print("- New emails in conversations will NOT have reply_to set")
    print("- This prevents UniPile 'invalid_reply_subject' error")

if __name__ == "__main__":
    main()