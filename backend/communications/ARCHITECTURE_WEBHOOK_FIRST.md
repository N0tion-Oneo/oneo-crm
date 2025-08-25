# Communications Architecture: Webhook-First with Local Frontend

## Core Architecture Principles

### 1. **Webhooks for Real-time Updates (RECEIVE)**
- All incoming messages arrive via webhooks from UniPile
- Webhooks are the **primary** source of real-time data
- Every webhook payload is **immediately saved** to local database
- No polling for new messages - webhooks handle 100% of real-time updates

### 2. **API for Sending and Historical Sync (SEND/SYNC)**
- UniPile API used for:
  - **Sending messages** (POST operations)
  - **Historical sync** (initial load, gap filling)
  - **Account management** (connections, settings)
- API calls are made only when necessary, not for polling

### 3. **Frontend is Local-Only (READ)**
- Frontend **NEVER** calls external APIs directly
- All data comes from local PostgreSQL database
- Real-time updates via WebSocket from Django (fed by webhooks)
- Zero external API calls from browser

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     INCOMING MESSAGES                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│   UniPile Webhook  ──►  Django Handler  ──►  PostgreSQL     │
│                                          │                   │
│                                          └──► WebSocket ──►  │
└─────────────────────────────────────────────────────────────┘
                                                      │
                                                      ▼
                                           ┌──────────────────┐
                                           │    Frontend      │
                                           │  (Local Only)    │
                                           └──────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     OUTGOING MESSAGES                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Frontend  ──►  Django API  ──►  UniPile API  ──►  WhatsApp │
│     │                │                                       │
│     └────────────────┴──► PostgreSQL (save sent message)    │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Details

### Webhook Processing (`/communications/webhooks/`)
```python
# webhooks/handlers/whatsapp.py
class WhatsAppWebhookHandler:
    def handle_message_received(self, data):
        # 1. Parse webhook payload
        # 2. Create/update local database records
        # 3. Broadcast via WebSocket
        # 4. Return success to UniPile
```

**Key Requirements:**
- ✅ Save all data locally immediately
- ✅ Never defer processing
- ✅ Acknowledge webhook quickly (<3s)
- ✅ Broadcast to WebSocket for real-time UI updates

### API Usage (`/communications/api/`)
```python
# api/whatsapp_views_local_first.py
def send_message_local_first(request):
    # 1. Call UniPile API to send
    # 2. Save to local DB
    # 3. Return local record to frontend
    
def sync_chat_history(request):
    # 1. Call UniPile API for historical data
    # 2. Save all to local DB
    # 3. Return success status
```

**Key Requirements:**
- ✅ API calls only for sending and historical sync
- ✅ Always save responses to local DB
- ✅ Never use API for real-time polling

### Frontend Data Access (`/frontend/`)
```typescript
// All data queries go to local Django API
const getChats = () => fetch('/api/v1/communications/whatsapp/chats/')
const getMessages = () => fetch('/api/v1/communications/whatsapp/chats/{id}/messages/')

// WebSocket for real-time updates
const ws = new WebSocket('ws://localhost:8000/ws/communications/')
```

**Key Requirements:**
- ✅ Zero external API calls
- ✅ All data from Django REST API (local DB)
- ✅ WebSocket for real-time updates
- ✅ Offline-capable (works without internet once synced)

## Database Models

### Core Models for Local Storage
- **Channel** - Communication channel configuration
- **Conversation** - Chat/thread container
- **Message** - Individual messages (saved from webhooks)
- **ChatAttendee** - Participants in conversations
- **ConversationAttendee** - Links attendees to specific conversations

### Data Persistence Strategy
1. **Webhook receives message** → Save immediately to Message model
2. **User sends message** → Save optimistically, update after API confirms
3. **Historical sync** → Bulk insert messages, update conversation metadata
4. **Gap detection** → Compare local vs remote, fetch missing via API

## Benefits of This Architecture

### 1. **Performance**
- Near-instant message display (local DB queries)
- No API latency for viewing messages
- Efficient bulk operations on local data

### 2. **Reliability**
- Works offline for viewing
- Webhook retries ensure no lost messages
- Local database as source of truth for UI

### 3. **Cost Efficiency**
- Minimal API calls (only sending + initial sync)
- No polling overhead
- Reduced bandwidth usage

### 4. **Security**
- API keys never exposed to frontend
- All external communication through backend
- Data validation at multiple layers

## Current Implementation Status

### ✅ Implemented
- Webhook handlers save to database
- Local-first API endpoints
- WebSocket broadcasting
- Message and conversation models
- Attendee architecture

### 🔄 In Progress
- Historical sync optimization
- Gap detection improvements

### ❌ To Be Removed/Deprecated
- Any polling mechanisms
- Direct API calls from frontend
- Aggressive sync tasks

## Testing the Architecture

### Verify Webhook Saving
```bash
# Check webhook handler saves data
curl -X POST http://localhost:8000/api/v1/webhooks/unipile/ \
  -H "Content-Type: application/json" \
  -d '{"event": "message.received", ...}'

# Verify in database
python manage.py shell
>>> from communications.models import Message
>>> Message.objects.filter(external_message_id='...').exists()
```

### Verify Local-Only Frontend
```bash
# Monitor network tab in browser
# Should see ONLY:
# - Requests to localhost:8000
# - WebSocket to ws://localhost:8000
# Should NOT see:
# - Requests to api.unipile.com
# - Any external API calls
```

## Migration Path

1. **Phase 1**: Ensure all webhooks save data ✅
2. **Phase 2**: Update frontend to use local endpoints only
3. **Phase 3**: Remove any remaining polling tasks
4. **Phase 4**: Optimize historical sync for large datasets