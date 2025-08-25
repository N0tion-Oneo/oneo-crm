# Communications System Architecture

## Overview
The communications system manages multi-channel messaging (WhatsApp, LinkedIn, Email, etc.) through UniPile API integration. It follows a hierarchical structure from Channels → Conversations → Messages, with Attendees participating across conversations.

## Core Models and Relationships

### 1. **Channel** (Organization Level)
Represents a connected communication account (e.g., a WhatsApp Business account, LinkedIn account, Gmail account).

```python
Channel:
  - id: UUID
  - name: "Sales WhatsApp Account"
  - channel_type: "whatsapp"
  - unipile_account_id: "mp9Gis3IRtuh9V5oSxZdSA"
  - is_active: true
  - metadata: {phone: "+27720720047", features: {...}}
```

**Purpose:**
- One Channel = One external account (WhatsApp number, LinkedIn profile, etc.)
- Organization can have multiple channels of the same type
- Channels are tenant-scoped (each tenant has their own channels)

**Relationships:**
- Has many Conversations
- Has many Messages (through Conversations)
- Has many ChatAttendees (directory of all contacts)
- Connected to UserChannelConnections (who can access this channel)

### 2. **Conversation** (Thread Level)
Represents a chat thread, email thread, or conversation.

```python
Conversation:
  - id: UUID
  - channel: Channel (FK)
  - external_thread_id: "chat_123" (UniPile chat ID)
  - subject: "Product Support"
  - type: "group" / "direct" / "broadcast"
  - last_message_at: DateTime
  - unread_count: 5
  - metadata: {participants_count: 3, ...}
```

**Purpose:**
- Groups related messages together
- Maintains conversation state (read/unread, archived, etc.)
- Can be 1-on-1, group chat, or broadcast list

**Relationships:**
- Belongs to one Channel
- Has many Messages
- Has many ChatAttendees (through ConversationAttendee)
- Linked to Contact Records (CRM integration)

### 3. **ChatAttendee** (Contact Level)
Represents a person/contact across the entire channel.

```python
ChatAttendee:
  - id: UUID
  - channel: Channel (FK)
  - external_attendee_id: "user_456" (UniPile ID)
  - provider_id: "27123456789@s.whatsapp.net"
  - name: "John Doe"
  - phone_number: "+27123456789"
  - email: "john@example.com"
  - picture_url: "https://..."
  - is_self: false (is this the account owner?)
  - contact_record: Record (FK) (linked CRM contact)
```

**Purpose:**
- Master directory of all contacts for a channel
- One record per unique contact per channel
- Deduplicates contact information
- Links to CRM contact records

**Relationships:**
- Belongs to one Channel
- Participates in many Conversations (through ConversationAttendee)
- Sends/receives many Messages
- Linked to CRM Contact Record

### 4. **ConversationAttendee** (Participation Level) - NEW
Links attendees to specific conversations with conversation-specific metadata.

```python
ConversationAttendee:
  - id: UUID
  - conversation: Conversation (FK)
  - attendee: ChatAttendee (FK)
  - joined_at: DateTime
  - left_at: DateTime (nullable)
  - role: "admin" / "member" / "viewer"
  - is_active: true
  - last_read_at: DateTime
  - notification_settings: JSON
```

**Purpose:**
- Tracks who is in which conversation
- Maintains conversation-specific roles and permissions
- Tracks join/leave history for group chats
- Per-conversation notification preferences

**Relationships:**
- Links Conversation to ChatAttendee (many-to-many)
- Tracks participation timeline

### 5. **Message** (Content Level)
Individual messages within conversations.

```python
Message:
  - id: UUID
  - conversation: Conversation (FK)
  - channel: Channel (FK) (denormalized for performance)
  - external_message_id: "msg_789"
  - sender: ChatAttendee (FK) (who sent this)
  - direction: "inbound" / "outbound"
  - content: "Hello, how can I help?"
  - status: "delivered" / "read" / "failed"
  - sent_at: DateTime
  - received_at: DateTime
  - metadata: {attachments: [...], reactions: [...]}
```

**Purpose:**
- Stores actual message content
- Tracks delivery and read status
- Handles attachments and rich media
- Maintains message timeline

**Relationships:**
- Belongs to one Conversation
- Belongs to one Channel (denormalized)
- Sent by one ChatAttendee
- May have parent Message (for replies)

### 6. **MessageDraft** (Composition Level) - NEW
Unsent message drafts for conversations.

```python
MessageDraft:
  - id: UUID
  - conversation: Conversation (FK)
  - channel: Channel (FK)
  - user: User (FK) (who's composing)
  - content: "I was thinking we could..."
  - reply_to: Message (FK) (nullable)
  - metadata: {attachments: [...], mentions: [...]}
  - created_at: DateTime
  - updated_at: DateTime
```

**Purpose:**
- Save unsent messages
- Support collaborative drafting
- Preserve work across sessions
- Handle complex message composition

**Relationships:**
- Belongs to one Conversation
- Created by one User
- May reply to a Message

## Data Flow Examples

### 1. Receiving a WhatsApp Message
```
1. Webhook receives message from UniPile
2. Find/Create Channel (by unipile_account_id)
3. Find/Create Conversation (by external_thread_id)
4. Find/Create ChatAttendee (by external_attendee_id)
5. Link Attendee to Conversation (ConversationAttendee)
6. Determine Message Direction:
   - Get business_account_id from Channel metadata
   - Use determine_whatsapp_direction(message_data, business_account_id)
   - Direction = 'inbound' if sender != business account
   - Direction = 'outbound' if sender == business account
7. Create Message with:
   - sender = ChatAttendee
   - direction = determined direction
8. Update Conversation.last_message_at
9. Broadcast to WebSocket for real-time updates
```

### 2. Sending a Message
```
1. User composes message in UI
2. Save as MessageDraft (optional)
3. Send via UniPile API
4. Create Message with direction = "outbound"
5. Update Message status based on delivery
6. Delete MessageDraft after successful send
```

### 3. Syncing Chat History
```
1. Fetch chats from UniPile API
2. For each chat:
   - Create/Update Conversation
   - Fetch attendees → Create/Update ChatAttendees
   - Create ConversationAttendee links
   - Fetch messages → Create Messages
3. Update sync timestamps
```

## Key Design Decisions

### Message Direction vs Attendee Detection
These are **separate concerns** that must not be conflated:

**Message Direction** (`determine_message_direction`):
- Determines if a message is inbound or outbound
- Requires the **account owner's identifier** (business phone, email, profile ID)
- Compares sender with account owner
- Critical for:
  - Proper message routing
  - Notification triggers (only notify on inbound)
  - Analytics (response times, etc.)
  - UI display (left vs right alignment)

**Attendee Detection** (`ChatAttendee`):
- Identifies all participants in a conversation
- Creates a directory of contacts
- Links contacts to CRM records
- Tracks participation over time
- Does NOT determine message direction

**Example:**
```python
# WhatsApp Business Account: +27720720047
# Customer: +27123456789

# Message from customer → business
sender = ChatAttendee(phone="+27123456789")  # Customer attendee
direction = determine_whatsapp_direction(
    message_data, 
    business_account_id="+27720720047@s.whatsapp.net"
)  # Returns 'in' (inbound)

# Message from business → customer (sent outside system)
sender = ChatAttendee(phone="+27720720047")  # Business attendee
direction = determine_whatsapp_direction(
    message_data,
    business_account_id="+27720720047@s.whatsapp.net"
)  # Returns 'out' (outbound)
```

This separation ensures messages sent from outside the system (e.g., directly from WhatsApp Business app) are correctly marked as outbound.

### Why Channel → ChatAttendee → Conversation?
- **Deduplication**: One ChatAttendee record per contact per channel
- **History**: Preserve contact info even if they leave conversations
- **Performance**: Avoid duplicating contact data across conversations
- **Flexibility**: Contacts can join/leave/rejoin conversations

### Why ConversationAttendee Junction Table?
- **Temporal Data**: Track when someone joined/left a group
- **Roles**: Admin vs member status per conversation
- **Settings**: Per-conversation notification preferences
- **Analytics**: Participation patterns and engagement

### Why Denormalize Channel on Message?
- **Performance**: Avoid joining through Conversation for common queries
- **Indexing**: Efficient channel-wide message searches
- **Sharding**: Future ability to partition by channel

## Migration Path

### Step 1: Add ConversationAttendee Model
```python
class ConversationAttendee(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    attendee = models.ForeignKey(ChatAttendee, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    role = models.CharField(max_length=20, default='member')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['conversation', 'attendee']
```

### Step 2: Add Relationship to Conversation
```python
class Conversation(models.Model):
    attendees = models.ManyToManyField(
        'ChatAttendee',
        through='ConversationAttendee',
        related_name='conversations'
    )
```

### Step 3: Add Sender to Message
```python
class Message(models.Model):
    sender = models.ForeignKey(
        'ChatAttendee',
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_messages'
    )
```

### Step 4: Add MessageDraft Model
```python
class MessageDraft(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    reply_to = models.ForeignKey(Message, null=True, on_delete=models.SET_NULL)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

## Query Patterns

### Get all attendees in a conversation
```python
attendees = conversation.attendees.filter(
    conversationattendee__is_active=True
).select_related('contact_record')
```

### Get all conversations for an attendee
```python
conversations = attendee.conversations.filter(
    conversationattendee__is_active=True
).order_by('-last_message_at')
```

### Get unread messages for a user
```python
messages = Message.objects.filter(
    conversation__attendees__contact_record__user=user,
    created_at__gt=F('conversation__conversationattendee__last_read_at'),
    direction='inbound'
)
```

## Benefits of This Architecture

1. **Scalability**: Can handle millions of messages with proper indexing
2. **Flexibility**: Supports any messaging platform through UniPile
3. **Data Integrity**: Clear relationships prevent orphaned data
4. **Performance**: Denormalization where needed for common queries
5. **Multi-tenancy**: Complete isolation between tenants
6. **Real-time**: WebSocket support for live updates
7. **History**: Full conversation and participation history
8. **Integration**: Clean integration with CRM (pipelines) system