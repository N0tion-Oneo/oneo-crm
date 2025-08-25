# Legacy Communications Code

This directory contains deprecated communication code that has been moved out of production.

## Deprecated Files

### WhatsApp Legacy Code
- **api/whatsapp_views_legacy_backup.py** - Old WhatsApp API views (replaced by whatsapp_views_local_first.py)
- **channels/whatsapp/views.py** - Old WhatsApp channel views (functionality moved to API layer)
- **channels/whatsapp/webhooks.py** - Old webhook handler (replaced by webhooks/handlers/whatsapp.py)
- **channels/whatsapp/utils/attendee_detection_old.py** - Old attendee detection logic (replaced by improved architecture)

## Migration Notes

### Date: 2025-08-24
- Moved old WhatsApp implementation to legacy after implementing improved attendee-conversation architecture
- New architecture properly separates:
  - Message direction determination from attendee detection
  - Channel-level attendees from conversation-specific participation
  - Business logic (sender) from display logic (direction)

### Current Production Code
- **API Layer**: `communications/api/whatsapp_views_local_first.py`
- **Webhook Handler**: `communications/webhooks/handlers/whatsapp.py`
- **Attendee Detection**: `communications/channels/whatsapp/utils/attendee_detection.py`
- **Message Direction**: `communications/utils/message_direction.py`

## DO NOT USE
This code is deprecated and should not be imported or used in production.