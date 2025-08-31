# Field Implementation Guide

## Overview
This guide documents the comprehensive field population system implemented for the communications app. All previously unused fields are now properly populated through a combination of service managers, signal handlers, webhook processors, and scheduled tasks.

## Implementation Components

### 1. Field Manager Service (`services/field_manager.py`)
Central service that provides methods to properly populate all model fields:

#### TenantUniPileConfig Methods:
- `update_webhook_status()` - Updates webhook tracking fields
- `set_provider_preferences()` - Sets provider-specific preferences

#### UserChannelConnection Methods:
- `store_tokens()` - Encrypts and stores authentication tokens
- `get_decrypted_token()` - Retrieves decrypted tokens
- `record_message_sent()` - Tracks messages for rate limiting
- `set_custom_rate_limit()` - Sets custom rate limits

#### Conversation Methods:
- `detect_conversation_type()` - Auto-detects type (direct/group/broadcast/channel)
- `set_conversation_priority()` - Sets conversation priority
- `mark_conversation_hot()` - Marks frequently accessed conversations
- `update_conversation_sync_status()` - Updates sync status with error tracking

#### Message Methods:
- `set_message_timestamps()` - Sets sent_at and received_at properly
- `set_message_subject()` - Sets subject for email messages
- `mark_message_local_only()` - Marks unsync messages

#### Participant Methods:
- `set_participant_social_handles()` - Sets Instagram, Facebook, Telegram, Twitter handles
- `record_participant_resolution()` - Records contact resolution details
- `record_secondary_resolution()` - Records company/org resolution
- `update_participant_stats()` - Updates conversation and message counts

#### ConversationParticipant Methods:
- `set_provider_participant_id()` - Sets provider-specific ID
- `mark_participant_left()` - Marks when participant leaves
- `update_participant_activity()` - Updates message count and last activity
- `mark_messages_read()` - Marks messages as read
- `increment_unread()` - Increments unread count

#### Analytics Methods:
- `create_daily_analytics()` - Generates daily analytics records

### 2. Signal Handlers (`signals/field_population.py`)
Automatic field population through Django signals:

#### Message Signals:
- Sets `received_at` for inbound messages
- Updates conversation `message_count` and `last_message_at`
- Updates participant activity in conversations
- Increments unread counts for recipients
- Tracks rate limiting for outbound messages

#### Conversation Signals:
- Detects conversation type on creation
- Updates participant count when members change

#### Participant Signals:
- Sets `first_seen` and `last_seen` timestamps
- Extracts social handles from metadata
- Updates statistics after save

#### Connection Signals:
- Initializes rate limiting fields
- Updates sync status on successful connections

### 3. Webhook Field Updater (`webhooks/field_updates.py`)
Processes webhook data to populate fields:

- `process_auth_webhook()` - Handles authentication webhooks
- `process_message_webhook()` - Extracts message metadata
- `process_conversation_webhook()` - Updates conversation metadata
- `process_participant_webhook()` - Updates participant data
- `process_read_receipt_webhook()` - Handles read receipts
- `process_typing_indicator_webhook()` - Manages typing indicators
- `process_participant_left_webhook()` - Handles participant departures

### 4. Scheduled Tasks (`tasks/field_maintenance.py`)
Celery tasks for periodic field updates:

#### Scheduled Every Hour:
- `detect_hot_conversations` - Identifies frequently accessed conversations
- `process_scheduled_syncs` - Processes auto-sync for records

#### Scheduled Every 4-6 Hours:
- `update_channel_statistics` - Updates channel message counts
- `update_participant_statistics` - Updates participant stats

#### Scheduled Every 12 Hours:
- `cleanup_expired_tokens` - Marks expired tokens
- `update_conversation_types` - Corrects conversation types

#### Scheduled Daily:
- `generate_daily_analytics` - Creates analytics records
- `verify_communication_links` - Updates verification timestamps

## Usage Examples

### Example 1: Recording Message Sent
```python
from communications.services.field_manager import field_manager

# When sending a message
field_manager.record_message_sent(connection)
```

### Example 2: Storing Authentication Tokens
```python
# When receiving OAuth tokens
field_manager.store_tokens(
    connection,
    access_token=response['access_token'],
    refresh_token=response['refresh_token'],
    expires_in=response['expires_in']
)
```

### Example 3: Detecting Conversation Type
```python
# After adding participants to conversation
field_manager.detect_conversation_type(conversation)
```

### Example 4: Recording Participant Resolution
```python
# When resolving participant to contact
field_manager.record_participant_resolution(
    participant,
    record=contact_record,
    confidence=0.95,
    method='email_match'
)
```

### Example 5: Processing Webhook Data
```python
from communications.webhooks.field_updates import webhook_field_updater

# In webhook handler
webhook_field_updater.process_message_webhook(webhook_data)
webhook_field_updater.record_webhook_received()
```

## Field Population Status

### ✅ Now Properly Populated:

#### TenantUniPileConfig:
- `webhook_secret` - Set via field_manager
- `default_contact_status` - Used in contact creation
- `provider_preferences` - Set with defaults on creation
- `last_webhook_received` - Updated on webhook reception
- `webhook_failures` - Tracked on webhook failures

#### UserChannelConnection:
- `access_token` - Encrypted and stored
- `refresh_token` - Encrypted and stored
- `token_expires_at` - Set with token storage
- `messages_sent_count` - Incremented on message send
- `messages_sent_today` - Daily counter with reset
- `rate_limit_per_hour` - Customizable per connection
- `last_rate_limit_reset` - Updated daily

#### Channel:
- `description` - Can be set via API
- `sync_settings` - Populated via field_manager
- `message_count` - Updated by scheduled task
- `last_message_at` - Updated on new messages
- `last_sync_at` - Updated after sync

#### Conversation:
- `conversation_type` - Auto-detected based on participants
- `participant_count` - Updated via signals
- `priority` - Can be set via field_manager
- `sync_error_count` - Incremented on errors
- `sync_error_message` - Set with error details
- `is_hot` - Detected by scheduled task
- `last_accessed_at` - Auto-updated

#### Message:
- `subject` - Set for email messages
- `received_at` - Set for inbound messages
- `is_local_only` - Managed for draft messages

#### Participant:
- `instagram_username` - Set from webhook data
- `facebook_id` - Set from webhook data
- `telegram_id` - Set from webhook data
- `twitter_handle` - Set from webhook data
- `resolution_method` - Set on resolution
- `resolved_at` - Set on resolution
- `secondary_confidence` - Set for company resolution
- `secondary_resolution_method` - Set for company resolution
- `secondary_pipeline` - Set for company resolution
- `total_conversations` - Updated by scheduled task
- `total_messages` - Updated by scheduled task

#### ConversationParticipant:
- `provider_participant_id` - Set from provider data
- `left_at` - Set when participant leaves
- `message_count` - Incremented on messages
- `last_message_at` - Updated on messages
- `last_read_at` - Updated on read receipts
- `unread_count` - Managed via signals

#### CommunicationAnalytics:
- All fields populated by daily scheduled task

#### RecordCommunicationProfile:
- `sync_frequency_hours` - Used for auto-sync scheduling
- `auto_sync_enabled` - Triggers scheduled syncs

#### RecordCommunicationLink:
- `last_verified` - Updated by daily task
- `linked_by` - Set on manual linking

#### RecordSyncJob:
- `trigger_reason` - Set with meaningful context
- `accounts_synced` - Properly tracked during sync

## Integration Points

### 1. Django Apps Configuration
The signal handlers are registered in `communications/apps.py`:
```python
def ready(self):
    from .signals import field_population  # Registers all handlers
```

### 2. Celery Beat Schedule
All scheduled tasks are configured in `oneo_crm/celery.py` with appropriate intervals.

### 3. Webhook Processing
The webhook view in `webhooks/views.py` calls `webhook_field_updater.record_webhook_received()` on successful processing.

## Testing Checklist

- [ ] Send a message and verify rate limiting fields update
- [ ] Create a group conversation and verify type detection
- [ ] Process a webhook and verify reception timestamp
- [ ] Wait for scheduled tasks and verify analytics creation
- [ ] Add participants and verify count updates
- [ ] Mark messages as read and verify unread counts
- [ ] Resolve participant to contact and verify resolution fields
- [ ] Check hot conversation detection after activity
- [ ] Verify token expiration cleanup
- [ ] Test auto-sync scheduling for records

## Migration Considerations

No new migrations are needed as all fields already exist in the database. The implementation only adds logic to properly populate existing fields.

## Performance Impact

- Signal handlers are lightweight and use `update_fields` for efficiency
- Scheduled tasks run at appropriate intervals to avoid overload
- Field manager uses batch operations where possible
- Analytics generation is done daily during off-peak hours

## Monitoring

Monitor these areas for proper field population:
1. Celery task execution logs for scheduled updates
2. Signal handler logs for automatic field updates
3. Webhook processing logs for external data updates
4. Analytics table for daily record creation

## Future Enhancements

1. Add field validation to ensure required fields are populated
2. Create management command to backfill historical data
3. Add field population metrics to monitoring dashboard
4. Implement field audit trail for sensitive data