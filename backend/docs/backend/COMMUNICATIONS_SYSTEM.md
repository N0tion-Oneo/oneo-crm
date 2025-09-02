# Oneo CRM Communications System Documentation

## Overview

The Oneo CRM communications system provides unified messaging capabilities across Email, WhatsApp, and LinkedIn channels. It integrates with UniPile API to handle all external communications while maintaining a local database for conversation tracking, threading, and record association.

## Architecture

### Core Components

1. **UniPile Integration** - External API service that handles actual message sending/receiving
2. **Channel Management** - Database models for tracking communication channels
3. **Conversation Threading** - Maintains conversation context and message history
4. **Record Association** - Links communications to CRM records (contacts, deals, etc.)
5. **Webhook Processing** - Receives real-time updates from UniPile

## Channel Types

### 1. Email (Gmail)

#### How Email Works

**Sending Flow:**
1. User composes email in `EmailCompose` component
2. Frontend sends POST request to `/api/v1/communications/records/{id}/send_email/`
3. Backend validates user has Gmail connection (`UserChannelConnection`)
4. Email sent via UniPile API using `EmailService`
5. Response tracked in local database (`Message` model)
6. Conversation created/updated with thread information

**Receiving Flow:**
1. UniPile sends webhook to `/webhooks/unipile/` when new email arrives
2. `EmailWebhookHandler` processes the webhook payload
3. Creates/updates `Conversation` with Gmail thread ID
4. Stores message in `Message` model with full metadata
5. Links to appropriate records via `RecordCommunicationLink`

**Key Features:**
- Thread-based conversations using Gmail thread IDs
- Support for CC, BCC, and attachments
- Reply, Reply All, and Forward functionality
- HTML email composition with rich text editor
- Automatic subject line management (Re:, Fwd:)

**Database Models:**
```python
# Email conversation example
Conversation:
  channel_type: "gmail"
  external_thread_id: "198f0d9fd98d03b2"  # Gmail thread ID
  subject: "Project Update"
  
Message:
  external_message_id: "msg_12345"  # UniPile message ID
  direction: "inbound" or "outbound"
  content: "<html>...</html>"
  metadata: {
    "from": {"email": "user@example.com"},
    "to": [{"email": "contact@example.com"}],
    "cc": [],
    "attachments": []
  }
```

### 2. WhatsApp

#### How WhatsApp Works

**Sending Flow:**
1. User composes message in `MessageCompose` component
2. Frontend sends POST to `/api/v1/communications/records/{id}/send_message/`
3. Backend checks for existing UniPile chat with recipient
   - Calls UniPile `GET /api/v1/messaging/chats?attendee_id={phone}@s.whatsapp.net`
   - If chat exists, uses existing chat_id
   - If no chat exists, creates new chat via `POST /api/v1/chats`
4. Sends message via `MessagingService.send_message()` or as part of chat creation
5. Creates/updates local `Conversation` with WhatsApp chat ID

**Receiving Flow:**
1. UniPile webhook arrives at `/webhooks/unipile/`
2. `WhatsAppWebhookHandler` processes the message
3. Matches UniPile chat_id to local `Conversation`
4. Creates `Message` record with WhatsApp-specific metadata
5. Updates conversation activity timestamps

**Phone Number Format:**
- Input: `+27720720047` or `27720720047`
- WhatsApp ID: `27720720047@s.whatsapp.net`
- No '+' symbol in the WhatsApp attendee ID

**Key Features:**
- Chat-based conversations (not threads like email)
- Automatic phone number formatting
- Media attachments support
- Prevents duplicate chat creation with same recipient
- Real-time message delivery status

**Database Models:**
```python
# WhatsApp conversation example
Conversation:
  channel_type: "whatsapp"
  external_thread_id: "gCaF0FOKW4q9vPCGw0Bjqw"  # UniPile chat ID
  subject: "Chat with +27720720047"
  
Message:
  external_message_id: "FFyKrEmJXZ2IDwIWoifBBQ"
  direction: "inbound" or "outbound"
  content: "Hello from WhatsApp"
  metadata: {
    "attendee_id": "27720720047@s.whatsapp.net",
    "chat_id": "gCaF0FOKW4q9vPCGw0Bjqw",
    "attachments": []
  }
```

### 3. LinkedIn

#### How LinkedIn Works

**Sending Flow:**
1. User composes message in `MessageCompose` component
2. Frontend sends POST to `/api/v1/communications/records/{id}/send_message/`
3. Backend checks for existing LinkedIn conversation with recipient
   - Searches by LinkedIn member URN or profile ID
   - Uses existing chat if found, creates new if not
4. Sends via `MessagingService` using UniPile LinkedIn API
5. Tracks in local database similar to WhatsApp

**Receiving Flow:**
1. UniPile webhook received at `/webhooks/unipile/`
2. `LinkedInWebhookHandler` processes the message
3. Creates/updates conversation and message records
4. Associates with CRM records

**LinkedIn Identifiers:**
- Member URNs: `urn:li:member:123456`
- Profile IDs from LinkedIn URLs
- InMail support for non-connections (with credits)

**Key Features:**
- Professional messaging platform integration
- Support for LinkedIn Sales Navigator and Recruiter
- InMail capability for reaching non-connections
- Subject lines for new conversations
- Rich text formatting support

**Database Models:**
```python
# LinkedIn conversation example
Conversation:
  channel_type: "linkedin"
  external_thread_id: "Isx3fabTX5eC1x2vMGf4NQ"  # UniPile chat ID
  subject: "Regarding your profile"
  
Message:
  external_message_id: "linkedin_msg_123"
  direction: "outbound"
  content: "Hi, I'd like to connect..."
  metadata: {
    "attendee_id": "urn:li:member:123456",
    "chat_id": "Isx3fabTX5eC1x2vMGf4NQ"
  }
```

## Unified Messaging Service

### MessagingService Class

Located in `communications/channels/messaging/service.py`, this service handles WhatsApp and LinkedIn messaging with a unified interface:

```python
class MessagingService:
    def __init__(self, channel_type: str)
    
    async def send_message(chat_id, text, attachments)
    async def start_new_chat(account_id, attendee_ids, text)
    async def find_or_create_chat(account_id, attendee_id, text)
```

**Key Methods:**

1. **find_or_create_chat**: Intelligent chat management
   - Searches for existing chat with attendee
   - Returns existing chat_id if found
   - Creates new chat only if needed
   - Prevents duplicate conversations

2. **send_message**: Sends to existing chat
   - Requires chat_id from UniPile
   - Supports text and attachments
   - Returns message_id on success

3. **start_new_chat**: Creates new conversation
   - Used when no existing chat found
   - Initial message sent with chat creation
   - Returns new chat_id

## API Endpoints

### Record-Based Communication APIs

All communication actions are performed in the context of a CRM record:

1. **Send Email**
   - `POST /api/v1/communications/records/{record_id}/send_email/`
   - Supports new emails and replies
   - Handles threading automatically

2. **Send Message** (WhatsApp/LinkedIn)
   - `POST /api/v1/communications/records/{record_id}/send_message/`
   - Intelligent chat finding/creation
   - Unified interface for both platforms

3. **Get Conversations**
   - `GET /api/v1/communications/records/{record_id}/conversations/`
   - Returns all conversations linked to a record
   - Filtered by channel type

4. **Get Messages**
   - `GET /api/v1/communications/records/{record_id}/conversation-messages/`
   - Returns messages for a specific conversation
   - Includes metadata and attachments

## User Account Connections

### UserChannelConnection Model

Stores authenticated communication accounts for each user:

```python
UserChannelConnection:
  user: ForeignKey(User)
  channel_type: "gmail", "whatsapp", "linkedin"
  unipile_account_id: "xMePXCZVQVO0VsjKprRbfg"
  account_name: "WhatsApp (27720720047)"
  is_active: True
  auth_status: "authenticated"
```

### Connection Management

1. **List Connections**
   - `GET /api/v1/communications/connections/`
   - Returns user's connected accounts
   - Used by frontend to populate account dropdowns

2. **Add Connection**
   - `POST /api/v1/communications/request-hosted-auth/`
   - Initiates UniPile OAuth flow
   - Returns hosted authentication URL

## Webhook Processing

### Webhook Flow

1. UniPile sends webhooks to `/webhooks/unipile/`
2. `UnipileWebhookView` determines event type
3. Routes to appropriate handler:
   - `EmailWebhookHandler` for Gmail events
   - `WhatsAppWebhookHandler` for WhatsApp events
   - `LinkedInWebhookHandler` for LinkedIn events

### Event Types

- `message.created`: New message received
- `message.updated`: Message status changed
- `chat.updated`: Chat metadata changed
- `account.disconnected`: Authentication lost

## Frontend Components

### EmailCompose
- Rich text editor for HTML emails
- Subject, To, CC, BCC fields
- Attachment support
- Reply/Reply All/Forward modes

### MessageCompose
- Simplified interface for WhatsApp/LinkedIn
- Account selector dropdown
- Text message input
- Attachment support
- Auto-expanding interface

### ConversationThread
- Displays message history
- Handles both email threads and chat messages
- Shows sender, timestamp, content
- Attachment downloads

## Database Schema

### Core Tables

1. **Channel**: Communication channel configuration
2. **Conversation**: Thread or chat container
3. **Message**: Individual messages
4. **Participant**: People in conversations
5. **UserChannelConnection**: User's connected accounts
6. **RecordCommunicationLink**: Links conversations to CRM records

### Relationships

```
Record ←→ RecordCommunicationLink ←→ Conversation ←→ Message
                                           ↓
                                      Participant
                                           ↓
                                    UserChannelConnection
```

## Security & Permissions

### Multi-tenant Isolation
- Each tenant has separate schema
- Communications isolated per tenant
- No cross-tenant data access

### User Permissions
- Users can only send from their own connected accounts
- Record-based access control
- Channel-specific permissions

## Best Practices

1. **Always check for existing chats** before creating new WhatsApp/LinkedIn conversations
2. **Use record context** for all communication actions
3. **Handle webhooks asynchronously** to prevent blocking
4. **Cache frequently accessed data** (conversations, messages)
5. **Validate phone numbers** before sending WhatsApp messages
6. **Monitor rate limits** for each channel type

## Troubleshooting

### Common Issues

1. **"Account not found"**: User hasn't connected the channel
2. **"Chat creation failed"**: Invalid recipient ID or phone number
3. **"Message not delivered"**: Check UniPile webhook logs
4. **"Threading broken"**: Verify external_thread_id matches

### Debug Steps

1. Check UserChannelConnection exists and is active
2. Verify UniPile account_id is correct
3. Review webhook processing logs
4. Confirm conversation external_thread_id
5. Test with UniPile API directly

## Future Enhancements

1. **SMS Support**: Add SMS channel via UniPile
2. **Teams Integration**: Microsoft Teams messaging
3. **Slack Support**: Slack workspace integration
4. **Voice/Video**: Call logging and recording
5. **AI Features**: Smart replies, sentiment analysis
6. **Templates**: Message templates for common responses