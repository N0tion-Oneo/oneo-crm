# WhatsApp Channel Implementation

## Architecture: Webhook-First with Local-Only Frontend

This directory contains the WhatsApp channel implementation following our webhook-first architecture:

1. **Webhooks** handle all real-time incoming messages (saved immediately to DB)
2. **API** used only for sending messages and historical sync
3. **Frontend** reads only from local database (never calls external APIs)

## Module Structure

```
whatsapp/
├── api_views.py          # API endpoints for WhatsApp functionality
├── client.py             # WhatsApp client wrapper for UniPile SDK
├── service.py            # Business logic and message processing
├── utils/                # Utility functions
│   ├── attendee_detection.py  # Detect and manage chat participants
│   ├── media_handler.py       # Handle media attachments
│   └── message_formatter.py   # Format messages for display
└── __init__.py           # Module exports
```

## API Endpoints

All endpoints are prefixed with `/api/v1/communications/whatsapp/`

### Account Management
- `GET /accounts/` - Get WhatsApp accounts for user

### Chats (Conversations)
- `GET /chats/` - Get all chats (from local DB)
- `GET /chats/{chat_id}/messages/` - Get messages for a chat (from local DB)
- `POST /chats/{chat_id}/send/` - Send a message (via UniPile API, saved locally)
- `PUT /chats/{chat_id}/` - Update chat metadata
- `POST /chats/{chat_id}/sync/` - Sync chat history (via UniPile API)

### Attendees
- `GET /attendees/` - Get all attendees
- `GET /attendees/{id}/picture/` - Get attendee profile picture

### Sync Operations
- `POST /sync/` - Trigger data sync for an account

## Data Flow

### Incoming Messages (Webhooks)
```
WhatsApp → UniPile → Webhook → Django Handler → PostgreSQL → WebSocket → Frontend
```

### Outgoing Messages (API)
```
Frontend → Django API → UniPile API → WhatsApp
         └─> PostgreSQL (optimistic save)
```

### Message Reading (Local Only)
```
Frontend → Django API → PostgreSQL
```

## Key Features

### ✅ Implemented
- Webhook processing with immediate DB save
- Optimistic message sending with local save
- Historical sync via API
- Attendee detection and management
- Message direction determination
- ConversationAttendee junction table
- Local-only frontend data access

### 🚀 Performance
- Near-instant message display (local queries)
- No API latency for viewing
- Optimistic updates for sending
- WebSocket for real-time updates

## Testing

```bash
# Test imports
python -c "from communications.channels.whatsapp.api_views import *"

# Test API endpoint
curl http://localhost:8000/api/v1/communications/whatsapp/accounts/

# Test webhook
curl -X POST http://localhost:8000/api/v1/webhooks/unipile/ \
  -H "Content-Type: application/json" \
  -d '{"event": "message.received", ...}'
```

## Important Notes

1. **Never poll the API** - Webhooks handle all real-time updates
2. **Always save locally** - Every API response must be saved to DB
3. **Frontend is offline-capable** - Once synced, works without internet
4. **API keys stay on backend** - Never exposed to frontend

## Migration from Legacy

This module replaces the legacy WhatsApp implementation that was moved to:
- `/communications/legacy/api/whatsapp_views_legacy_backup.py`
- `/communications/legacy/channels/whatsapp/`

The new implementation:
- Uses webhook-first architecture (no polling)
- Saves all data locally immediately
- Frontend reads only from local DB
- Properly separates concerns (direction vs attendee detection)