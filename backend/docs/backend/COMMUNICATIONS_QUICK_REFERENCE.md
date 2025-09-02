# Communications System - Quick Reference

## API Quick Reference

### Send Email
```bash
POST /api/v1/communications/records/{record_id}/send_email/
{
  "from_account_id": "xMePXCZVQVO0VsjKprRbfg",  # UniPile account ID
  "to": "contact@example.com",
  "subject": "Meeting Tomorrow",
  "body": "<p>Let's meet at 3pm</p>",
  "cc": ["cc@example.com"],
  "bcc": ["bcc@example.com"],
  "conversation_id": "uuid",  # Optional - for replies
  "reply_mode": "reply"  # reply, reply-all, forward
}
```

### Send WhatsApp/LinkedIn Message
```bash
POST /api/v1/communications/records/{record_id}/send_message/
{
  "from_account_id": "mp9Gis3IRtuh9V5oSxZdSA",  # UniPile account ID
  "text": "Hello from Oneo CRM",
  "to": "+27720720047",  # Phone for WhatsApp, URN for LinkedIn
  "conversation_id": "uuid"  # Optional - for existing chats
}
```

### Get Conversations
```bash
GET /api/v1/communications/records/{record_id}/conversations/?channel_type=whatsapp
```

### Get Messages
```bash
GET /api/v1/communications/records/{record_id}/conversation-messages/?conversation_id=uuid
```

## Channel-Specific Formats

### WhatsApp
```python
# Phone number formats
Input:      "+27720720047" or "27720720047" or "+1-555-123-4567"
Formatted:  "27720720047@s.whatsapp.net"  # No + symbol

# Example attendee IDs
US:  "15551234567@s.whatsapp.net"
UK:  "447700900123@s.whatsapp.net"
SA:  "27720720047@s.whatsapp.net"
```

### LinkedIn
```python
# Member URN format
"urn:li:member:123456789"

# Profile URL extraction
"https://linkedin.com/in/john-doe" → Extract profile ID
```

### Email (Gmail)
```python
# Thread IDs
"198f0d9fd98d03b2"  # Gmail native thread ID

# Message IDs
"<CAHk=wz...@mail.gmail.com>"  # RFC 2822 format
```

## Key Services & Classes

### Backend Services
```python
# Email Service
from communications.channels.email.service import EmailService
service = EmailService()
await service.send_email(...)

# Messaging Service (WhatsApp/LinkedIn)
from communications.channels.messaging.service import MessagingService
service = MessagingService(channel_type='whatsapp')
await service.find_or_create_chat(...)
await service.send_message(...)
```

### Frontend Components
```typescript
// Email Composition
import { EmailCompose } from '@/components/communications/record/EmailCompose'

// WhatsApp/LinkedIn Messaging
import { MessageCompose } from '@/components/communications/record/MessageCompose'

// Conversation Display
import { ConversationThread } from '@/components/communications/record/ConversationThread'
```

## Database Models

### Key Models
```python
from communications.models import (
    Channel,              # Communication channel config
    Conversation,         # Thread/chat container
    Message,             # Individual messages
    UserChannelConnection # User's connected accounts
)

from communications.record_communications.models import (
    RecordCommunicationLink,    # Links convos to records
    RecordCommunicationProfile   # Record comm stats
)
```

## Webhook Events

### UniPile Webhook Types
```python
# Email events
"email.received"
"email.sent"
"email.bounced"

# WhatsApp events  
"messaging.message"  # New message
"messaging.chat"     # Chat update
"messaging.status"   # Delivery status

# LinkedIn events
"messaging.message"
"messaging.connection"
```

## Common Patterns

### Check for Existing Chat (WhatsApp/LinkedIn)
```python
# Before creating new chat, always check for existing
result = await service.find_or_create_chat(
    account_id=account_id,
    attendee_id=attendee_id,
    text=message_text  # Only creates if not found
)

if result['found']:
    # Use existing chat_id
    chat_id = result['chat_id']
elif result['created']:
    # New chat was created
    chat_id = result['chat_id']
```

### Handle Webhook
```python
# In webhook handler
def handle_message_webhook(data):
    # 1. Extract chat/thread ID
    external_id = data.get('chat_id') or data.get('thread_id')
    
    # 2. Find or create conversation
    conversation = Conversation.objects.get_or_create(
        external_thread_id=external_id,
        channel_type=channel_type
    )
    
    # 3. Create message
    Message.objects.create(
        conversation=conversation,
        external_message_id=data['message_id'],
        content=data['text'],
        direction='inbound'
    )
```

## Testing

### Test Email Sending
```bash
# Using curl
curl -X POST http://oneotalent.localhost:8000/api/v1/communications/records/83/send_email/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "from_account_id": "xMePXCZVQVO0VsjKprRbfg",
    "to": "test@example.com",
    "subject": "Test",
    "body": "Test email"
  }'
```

### Test WhatsApp Sending
```bash
curl -X POST http://oneotalent.localhost:8000/api/v1/communications/records/83/send_message/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "from_account_id": "mp9Gis3IRtuh9V5oSxZdSA",
    "text": "Test message",
    "to": "+27720720047"
  }'
```

## Debug Checklist

### Message Not Sending
- [ ] User has connected account? Check `UserChannelConnection`
- [ ] Account is active? Check `is_active` field
- [ ] Correct UniPile account ID? Check `unipile_account_id`
- [ ] Valid recipient format? Phone for WhatsApp, email for Gmail
- [ ] API credentials valid? Check `UNIPILE_API_KEY` in settings

### Message Not Appearing
- [ ] Webhook received? Check webhook logs
- [ ] Conversation created? Check `external_thread_id`
- [ ] Message linked? Check `conversation_id` on Message
- [ ] Record linked? Check `RecordCommunicationLink`

### Account Not in Dropdown
- [ ] API returns connections? Test `/api/v1/communications/connections/`
- [ ] Correct channel type? Filter by `channelType`
- [ ] Account active? Check `isActive` field
- [ ] Frontend handling pagination? Check for `results` array

## Environment Variables

```bash
# Required for communications
UNIPILE_API_KEY=your_api_key
UNIPILE_DSN=https://api18.unipile.com:14890

# Webhook configuration (production)
WEBHOOK_BASE_URL=https://your-domain.com

# Webhook configuration (development with tunnel)
WEBHOOK_BASE_URL=https://webhooks.oneocrm.com
```

## Rate Limits

### UniPile Limits
- Email: 500 per day per account
- WhatsApp: Based on WhatsApp Business tier
- LinkedIn: 100 messages per day (varies by subscription)

### Internal Limits
- API calls: 1000 per hour per user
- Webhook processing: 100 per second
- Database queries: Connection pooling limits

## Error Codes

### Common API Errors
- `404`: Account/Record/Conversation not found
- `400`: Invalid request data (missing fields, wrong format)
- `401`: Authentication required
- `403`: Permission denied (not your account)
- `502`: UniPile API error
- `429`: Rate limit exceeded