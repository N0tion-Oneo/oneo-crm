# Record Communication Sync System

## Overview
The record communication sync system automatically synchronizes communications (emails, messages, etc.) when records are created or updated with identifier fields. These identifier fields are determined by the duplicate detection rules configured for each pipeline.

## How It Works

### 1. Identifier Fields
- Identifier fields are extracted from duplicate detection rules
- Common identifiers: `personal_email`, `phone_number`, `linkedin`, `work_email`
- These fields are used to match communications to records

### 2. Automatic Sync Triggers
The sync automatically triggers when:
- **New Record Created**: If the record has any populated identifier fields
- **Existing Record Updated**: If any identifier field is added or changed
- **Manual Trigger**: Via API endpoint `/api/records/{record_id}/sync/`

### 3. Channel-Specific Sync (Optimized)
The system now syncs ONLY the relevant channels based on which identifier changed:
- **Email fields** (`personal_email`, `work_email`) → Syncs only Gmail/Email channels
- **Phone fields** (`phone_number`, `mobile`) → Syncs only WhatsApp channel
- **LinkedIn fields** (`linkedin`, `linkedin_url`) → Syncs only LinkedIn channel

This optimization reduces unnecessary API calls and improves sync performance.

### 4. Sync Process Flow
```
Record Save → Signal Handler → Check Identifier Fields → Queue Celery Task → Sync Communications
```

### 5. Components

#### Signal Handler (`communications/record_communications/signals.py`)
- Listens to Record `post_save` signal
- Detects changes in identifier fields
- Creates RecordCommunicationProfile
- Queues sync task via Celery

#### Celery Task (`communications/record_communications/tasks/sync_tasks.py`)
- `sync_record_communications`: Main sync task
- Runs in `background_sync` queue
- Uses RecordSyncOrchestrator for actual sync

#### Models
- `RecordCommunicationProfile`: Stores extracted identifiers and sync status
- `RecordSyncJob`: Tracks individual sync jobs and their results
- `RecordCommunicationLink`: Links conversations to records

## Configuration

### Duplicate Rules
Duplicate rules define which fields trigger sync:
```python
# Example duplicate rule logic
{
    "operator": "OR",
    "conditions": [
        {"operator": "AND", "fields": [{"field": "personal_email", "match_type": "exact"}]},
        {"operator": "AND", "fields": [{"field": "phone_number", "match_type": "phone_normalized"}]},
        {"operator": "AND", "fields": [{"field": "linkedin", "match_type": "url_normalized"}]}
    ]
}
```

### Sync Throttling
- Automatic syncs are throttled to prevent excessive API calls
- Default: 5-minute cooldown between syncs
- Manual syncs can override throttling with `force=true`

## Testing

### Test Scripts
1. `test_auto_sync_trigger.py` - Tests automatic trigger on record changes
2. `test_auto_sync_execution.py` - Tests actual sync execution
3. `run_sync.py` - Manual sync for specific records

### Running Tests
```bash
# Test automatic triggers
python test_auto_sync_trigger.py

# Test sync execution
python test_auto_sync_execution.py

# Manual sync
python run_sync.py --record-id 66 --tenant oneotalent
```

## API Endpoints

### Trigger Manual Sync
```
POST /api/records/{record_id}/sync/
{
    "force": false  // Set true to override throttling
}
```

### Get Sync Status
```
GET /api/records/{record_id}/sync_status/
```

### Get Communication Profile
```
GET /api/records/{record_id}/profile/
```

## Monitoring

### Check Sync Jobs
```python
from communications.record_communications.models import RecordSyncJob

# Recent sync jobs
jobs = RecordSyncJob.objects.order_by('-created_at')[:10]
for job in jobs:
    print(f"{job.record_id}: {job.status} - {job.trigger_reason}")
```

### Check Celery Queue
```bash
# Monitor background_sync queue
celery -A oneo_crm inspect active --queue=background_sync
```

## Troubleshooting

### Sync Not Triggering
1. Check if duplicate rules exist for the pipeline
2. Verify identifier fields are configured in duplicate rules
3. Check if sync is throttled (recently synced)
4. Verify Celery workers are running

### Sync Failing
1. Check RecordSyncJob.error_message
2. Verify UniPile API credentials
3. Check network connectivity
4. Review Celery worker logs

### No Communications Found
1. Verify identifier values match communication data
2. Check if communications exist in the system
3. Verify webhooks are receiving new messages

## Future Enhancements

1. **Configurable Sync Rules**: Allow custom sync triggers beyond duplicate fields
2. **Sync Scheduling**: Schedule periodic syncs for important records
3. **Selective Channel Sync**: Choose which communication channels to sync
4. **Sync Analytics**: Track sync performance and success rates
5. **Webhook Priority**: Prioritize real-time webhook updates over batch sync