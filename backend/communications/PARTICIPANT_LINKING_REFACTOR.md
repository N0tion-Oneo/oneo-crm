# Communication System Refactor: Participant-Based Linking

## Overview

This document outlines the refactor of the communication system from a dual-linking architecture (RecordCommunicationLink + Participant.contact_record) to a simplified single-linking system through participants only.

## Current Architecture Problems

1. **Dual Linking Confusion**: Two separate systems for linking conversations to records
2. **Data Inconsistency**: Conversations linked to records but participants aren't
3. **Complex Queries**: Multiple joins and checks needed
4. **Maintenance Overhead**: Two systems to maintain and debug

## New Architecture

### Simplified Model Hierarchy
```
Record (CRM Contact/Lead)
    ↓ (via contact_record ForeignKey)
Participant (Email address, Phone number, LinkedIn profile)
    ↓ (via ConversationParticipant junction)
Conversation (Email thread, WhatsApp chat, LinkedIn conversation)
    ↓ (via conversation ForeignKey)
Message (Individual message)
```

### Key Principles

1. **Single Source of Truth**: Participants are the only link between records and conversations
2. **Natural Hierarchy**: Records own participants, participants join conversations
3. **Channel Isolation**: Each participant represents one communication channel identity
4. **Automatic Propagation**: Linking a participant to a record automatically associates all their conversations

## Implementation Plan

### Phase 1: Update Participant Resolution (Day 1-2)

#### 1.1 Update ParticipantResolutionService

**File**: `communications/services/participant_resolution.py`

Current behavior: Creates participants but rarely links them to records.

**Changes needed**:
```python
async def resolve_to_contact(self, participant: Participant, identifier_data: Dict):
    """
    Enhanced resolution that actively links participants to records
    """
    # Find matching records by identifiers
    records = self.find_records_by_identifiers(identifier_data)
    
    if records and len(records) == 1:
        # High confidence match - single record found
        participant.contact_record = records[0]
        participant.resolution_confidence = 0.95
        participant.resolution_method = self.determine_match_type(identifier_data)
        participant.resolved_at = timezone.now()
        await sync_to_async(participant.save)()
        
        logger.info(f"Linked participant {participant.id} to record {records[0].id}")
```

#### 1.2 Update Webhook Handlers

**Files to update**:
- `communications/webhooks/email_handler.py`
- `communications/webhooks/handlers/whatsapp.py`
- `communications/webhooks/handlers/linkedin.py`

**Email Handler Changes**:
```python
# After creating/finding participant
if participant:
    # Try to find matching record
    from communications.record_communications.services import RecordIdentifierExtractor
    extractor = RecordIdentifierExtractor()
    
    if participant.email:
        records = extractor.find_records_by_email(participant.email)
        if records and len(records) == 1:
            participant.contact_record = records[0]
            participant.resolution_confidence = 0.95
            participant.resolution_method = 'email_webhook'
            participant.resolved_at = timezone.now()
            participant.save()
            
    # Remove RecordCommunicationLink creation
    # DELETE all code creating RecordCommunicationLink
```

**WhatsApp Handler Changes**:
```python
# Similar pattern for phone number matching
if participant.phone:
    records = extractor.find_records_by_phone(participant.phone)
    if records and len(records) == 1:
        participant.contact_record = records[0]
        participant.resolution_confidence = 0.90
        participant.resolution_method = 'phone_webhook'
        participant.resolved_at = timezone.now()
        participant.save()
```

**LinkedIn Handler Changes**:
```python
# Match by LinkedIn URN or email from profile
if participant.linkedin_member_urn:
    records = extractor.find_records_by_linkedin(participant.linkedin_member_urn)
    # ... same pattern
```

#### 1.3 Update Sync Process

**File**: `communications/record_communications/services/record_sync_orchestrator.py`

**Changes**:
```python
def sync_record(self, record_id: int, ...):
    # ... existing setup ...
    
    # After fetching messages, link all matching participants
    all_participants = self._get_all_participants_from_conversations(conversations)
    
    for participant in all_participants:
        if self._participant_matches_record(participant, identifiers):
            if not participant.contact_record:
                participant.contact_record = record
                participant.resolution_confidence = 0.85
                participant.resolution_method = 'sync_identifier_match'
                participant.resolved_at = timezone.now()
                participant.save()
                
    # REMOVE all RecordCommunicationLink creation
    # DELETE calls to LinkManager.create_link()
```

### Phase 2: Replace LinkManager (Day 3-4)

#### 2.1 Simplify LinkManager

**File**: `communications/record_communications/storage/link_manager.py`

**New simplified version**:
```python
class ParticipantLinkManager:
    """Manages linking participants to records"""
    
    def link_participant_to_record(
        self,
        participant: Participant,
        record: Record,
        confidence: float = 0.9,
        method: str = 'manual'
    ) -> bool:
        """
        Link a participant to a record
        
        Returns:
            True if newly linked, False if already linked
        """
        if participant.contact_record_id == record.id:
            return False
            
        participant.contact_record = record
        participant.resolution_confidence = confidence
        participant.resolution_method = method
        participant.resolved_at = timezone.now()
        participant.save()
        
        logger.info(f"Linked participant {participant.id} to record {record.id}")
        return True
    
    def unlink_participant(self, participant: Participant) -> bool:
        """Unlink a participant from their record"""
        if not participant.contact_record:
            return False
            
        record_id = participant.contact_record_id
        participant.contact_record = None
        participant.resolution_confidence = 0
        participant.resolution_method = ''
        participant.resolved_at = None
        participant.save()
        
        logger.info(f"Unlinked participant {participant.id} from record {record_id}")
        return True
    
    def get_record_participants(self, record: Record) -> QuerySet:
        """Get all participants linked to a record"""
        return Participant.objects.filter(contact_record=record)
```

#### 2.2 Remove RecordCommunicationLink Creation

**Files to clean**:
- Remove all `RecordCommunicationLink.objects.create()` calls
- Remove all `RecordCommunicationLink.objects.get_or_create()` calls
- Remove imports of RecordCommunicationLink

### Phase 3: Update Query Logic (Day 4-5)

#### 3.1 Update API Views

**File**: `communications/record_communications/api.py`

**Current**:
```python
def get_record_conversations(self, request, record_id):
    links = RecordCommunicationLink.objects.filter(record_id=record_id)
    conversation_ids = links.values_list('conversation_id', flat=True)
    conversations = Conversation.objects.filter(id__in=conversation_ids)
```

**New**:
```python
def get_record_conversations(self, request, record_id):
    # Get all participants linked to this record
    participants = Participant.objects.filter(contact_record_id=record_id)
    
    # Get their conversations
    conversations = Conversation.objects.filter(
        conversation_participants__participant__in=participants
    ).distinct().order_by('-last_message_at')
    
    return Response(ConversationSerializer(conversations, many=True).data)
```

#### 3.2 Update Record Communication Views

**File**: `communications/views.py`

Update all methods that query RecordCommunicationLink to use participant-based queries.

#### 3.3 Update Frontend API Calls

**File**: `frontend/src/lib/api.ts`

No changes needed - API endpoints remain the same, only backend implementation changes.

### Phase 4: Clean Sweep (Day 6)

#### 4.1 Remove Models

1. Delete `RecordCommunicationLink` model from `communications/record_communications/models.py`
2. Delete `RecordCommunicationProfile` if not needed for identifier extraction
3. Create migration to drop tables:

```python
# communications/migrations/00XX_remove_record_communication_link.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('communications', '00XX_previous_migration'),
    ]
    
    operations = [
        migrations.DeleteModel(
            name='RecordCommunicationLink',
        ),
        # Optional: Remove RecordCommunicationProfile if not needed
    ]
```

#### 4.2 Clean Management Commands

**File**: `communications/management/commands/clear_communication_data.py`

Remove all references to RecordCommunicationLink.

#### 4.3 Remove Unused Imports

Search and remove all imports of RecordCommunicationLink throughout the codebase.

### Phase 5: Fresh Sync (Day 7)

#### 5.1 Clear All Communication Data

```bash
python manage.py clear_communication_data --all --confirm
```

#### 5.2 Run Fresh Sync for Test Records

```bash
# Test with a few records first
python manage.py sync_record_communications --record-id 93
```

#### 5.3 Verify Results

```python
# Verification script
from communications.models import Participant, Conversation
from pipelines.models import Record

# Check participants are linked
record = Record.objects.get(id=93)
participants = Participant.objects.filter(contact_record=record)
print(f"Found {participants.count()} participants linked to record 93")

# Check conversations are accessible
conversations = Conversation.objects.filter(
    conversation_participants__participant__in=participants
).distinct()
print(f"Found {conversations.count()} conversations via participants")
```

## Testing Plan

### Unit Tests to Update

1. **Test participant linking on creation**
2. **Test conversation retrieval via participants**
3. **Test unlinking participants**
4. **Test bulk participant operations**

### Integration Tests

1. **Webhook → Participant → Record flow**
2. **Sync → Participant → Record flow**
3. **API queries for record conversations**
4. **Frontend communication timeline**

## Rollback Plan

If issues arise:

1. **Keep RecordCommunicationLink model** in migration (don't drop table)
2. **Revert query logic** to use RecordCommunicationLink
3. **Re-enable link creation** in webhooks/sync
4. **Clear and re-sync** with old system

## Success Metrics

1. **Simplified codebase**: ~500 lines of code removed
2. **Query performance**: Single join instead of multiple
3. **Data consistency**: All participants properly linked
4. **Frontend functionality**: Communication timeline working

## Timeline

- **Day 1-2**: Update participant resolution everywhere
- **Day 3-4**: Replace LinkManager, remove link creation
- **Day 4-5**: Update all queries to use participants
- **Day 6**: Clean sweep - remove models
- **Day 7**: Fresh sync and testing

Total: **1 week**

## Notes

- All changes are backwards-compatible until Phase 4
- Frontend remains unchanged - only backend implementation changes
- Fresh sync means no data migration complexity
- Monitoring in place to track query performance