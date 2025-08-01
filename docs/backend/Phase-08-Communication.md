# Phase 08: Communication Layer & UniPile Integration

## 🎯 Overview & Objectives

Implement a comprehensive omni-channel communication system using UniPile APIs for unified messaging across email, WhatsApp, LinkedIn, and other platforms. Build intelligent AI-powered sequences that adapt content, timing, and channel selection based on engagement patterns and recipient behavior.

### Primary Goals
- Unified inbox with omni-channel message threading
- AI-driven communication sequences with adaptive behavior
- Intelligent channel selection and timing optimization
- Real-time conversation analytics and sentiment tracking
- Automated follow-up workflows with human handoff
- Integration with CRM/ATS pipelines for contextual messaging

### Success Criteria
- ✅ Support for 5+ communication channels (Email, WhatsApp, LinkedIn, SMS, Slack)
- ✅ Real-time message synchronization and threading
- ✅ AI sequences with 90%+ delivery success rate
- ✅ Sub-500ms message routing and processing
- ✅ Contextual messaging with CRM/ATS data integration
- ✅ Comprehensive analytics and ROI tracking

## 🏗️ Technical Requirements & Dependencies

### Phase Dependencies
- ✅ **Phase 01**: Multi-tenant infrastructure and background job processing
- ✅ **Phase 02**: User authentication and permission system
- ✅ **Phase 03**: Pipeline system for contact and lead management
- ✅ **Phase 04**: Relationship system for contact connections
- ✅ **Phase 05**: API layer for real-time message updates
- ✅ **Phase 06**: Real-time system for live message notifications
- ✅ **Phase 07**: AI integration for intelligent sequence behavior

### Core Technologies
- **UniPile API** for omni-channel messaging
- **Celery** for asynchronous message processing
- **WebSockets** for real-time message updates
- **AI Services** for intelligent sequence optimization
- **Redis** for message queuing and rate limiting

### Additional Dependencies
```bash
pip install unipile-python==1.2.0
pip install email-validator==2.1.0
pip install python-whatsapp-web==1.3.0
pip install linkedin-api==2.2.0
pip install twilio==8.10.0
pip install sendgrid==6.11.0
pip install mailgun==1.0.0
```

## 🗄️ Communication System Architecture

### Database Schema Design

#### {tenant}.communications_channel
```sql
CREATE TABLE communications_channel (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    channel_type VARCHAR(50) NOT NULL, -- 'email', 'whatsapp', 'linkedin', 'sms', 'slack'
    
    -- UniPile configuration
    unipile_account_id VARCHAR(100) UNIQUE,
    provider_name VARCHAR(100), -- 'gmail', 'outlook', 'whatsapp_business', etc.
    provider_config JSONB DEFAULT '{}',
    
    -- Channel settings
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    rate_limit_per_hour INTEGER DEFAULT 100,
    
    -- Authentication and credentials
    auth_status VARCHAR(20) DEFAULT 'disconnected', -- 'connected', 'disconnected', 'error'
    auth_expires_at TIMESTAMP,
    last_sync_at TIMESTAMP,
    
    -- Metadata
    created_by_id INTEGER REFERENCES users_customuser(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Conversations (message threads)
CREATE TABLE communications_conversation (
    id SERIAL PRIMARY KEY,
    
    -- Conversation identification
    external_thread_id VARCHAR(255), -- Platform-specific thread ID
    channel_id INTEGER REFERENCES communications_channel(id),
    
    -- Participants
    participants JSONB DEFAULT '[]', -- Array of participant info
    primary_contact_id INTEGER REFERENCES pipelines_record(id), -- Link to contact record
    
    -- Conversation metadata
    subject VARCHAR(500),
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'archived', 'closed'
    priority VARCHAR(20) DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'
    
    -- AI analysis
    sentiment VARCHAR(20), -- 'positive', 'negative', 'neutral'
    sentiment_score DECIMAL(3,2),
    intent VARCHAR(100), -- Detected conversation intent
    language VARCHAR(10) DEFAULT 'en',
    
    -- Tracking
    last_message_at TIMESTAMP,
    last_inbound_at TIMESTAMP,
    last_outbound_at TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    
    -- Assignment
    assigned_to_id INTEGER REFERENCES users_customuser(id),
    assigned_at TIMESTAMP,
    
    -- Pipeline integration
    pipeline_id INTEGER REFERENCES pipelines_pipeline(id),
    record_id INTEGER REFERENCES pipelines_record(id),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Individual messages
CREATE TABLE communications_message (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES communications_conversation(id),
    
    -- Message identification
    external_message_id VARCHAR(255) UNIQUE,
    thread_id VARCHAR(255),
    
    -- Message content
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text', -- 'text', 'html', 'markdown'
    
    -- Message metadata
    direction VARCHAR(10) NOT NULL, -- 'inbound', 'outbound'
    message_type VARCHAR(50) DEFAULT 'message', -- 'message', 'reply', 'forward'
    
    -- Sender/recipient info
    sender_email VARCHAR(255),
    sender_name VARCHAR(255),
    sender_phone VARCHAR(50),
    recipient_info JSONB DEFAULT '{}',
    
    -- Delivery tracking
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'sent', 'delivered', 'read', 'failed'
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    read_at TIMESTAMP,
    failed_reason TEXT,
    
    -- AI analysis
    sentiment VARCHAR(20),
    intent VARCHAR(100),
    entities JSONB DEFAULT '{}', -- Extracted entities (names, dates, etc.)
    
    -- Attachments
    attachments JSONB DEFAULT '[]',
    
    -- Sequence tracking
    sequence_id INTEGER REFERENCES communications_sequence(id),
    sequence_step INTEGER,
    
    -- Metadata
    created_by_id INTEGER REFERENCES users_customuser(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- AI-powered communication sequences
CREATE TABLE communications_sequence (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Sequence configuration
    sequence_type VARCHAR(50) DEFAULT 'nurture', -- 'nurture', 'outreach', 'follow_up', 'onboarding'
    objective VARCHAR(255), -- Human-readable objective
    
    -- AI configuration
    ai_enabled BOOLEAN DEFAULT TRUE,
    ai_optimization_level VARCHAR(20) DEFAULT 'medium', -- 'low', 'medium', 'high'
    
    -- Sequence steps
    steps JSONB NOT NULL, -- Array of sequence step configurations
    
    -- Targeting and triggers
    trigger_conditions JSONB DEFAULT '{}',
    target_audience JSONB DEFAULT '{}',
    
    -- Timing and delivery
    default_timezone VARCHAR(50) DEFAULT 'UTC',
    business_hours_only BOOLEAN DEFAULT TRUE,
    respect_do_not_disturb BOOLEAN DEFAULT TRUE,
    
    -- Performance tracking
    success_metrics JSONB DEFAULT '{}',
    
    -- Status and lifecycle
    is_active BOOLEAN DEFAULT TRUE,
    is_template BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_by_id INTEGER REFERENCES users_customuser(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Sequence enrollments (contacts in sequences)
CREATE TABLE communications_sequence_enrollment (
    id SERIAL PRIMARY KEY,
    sequence_id INTEGER REFERENCES communications_sequence(id),
    
    -- Target contact
    contact_record_id INTEGER REFERENCES pipelines_record(id),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    
    -- Enrollment details
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'paused', 'completed', 'failed', 'opted_out'
    current_step INTEGER DEFAULT 0,
    
    -- Timing
    enrolled_at TIMESTAMP DEFAULT NOW(),
    next_action_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- AI personalization
    personalization_data JSONB DEFAULT '{}',
    engagement_score DECIMAL(3,2) DEFAULT 0.0,
    
    -- Performance tracking
    messages_sent INTEGER DEFAULT 0,
    messages_opened INTEGER DEFAULT 0,
    messages_clicked INTEGER DEFAULT 0,
    messages_replied INTEGER DEFAULT 0,
    
    -- Metadata
    enrolled_by_id INTEGER REFERENCES users_customuser(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX idx_conversation_contact ON communications_conversation (primary_contact_id);
CREATE INDEX idx_conversation_assigned ON communications_conversation (assigned_to_id);
CREATE INDEX idx_conversation_status ON communications_conversation (status);
CREATE INDEX idx_message_conversation ON communications_message (conversation_id);
CREATE INDEX idx_message_external ON communications_message (external_message_id);
CREATE INDEX idx_message_direction ON communications_message (direction);
CREATE INDEX idx_sequence_enrollment_contact ON communications_sequence_enrollment (contact_record_id);
CREATE INDEX idx_sequence_enrollment_status ON communications_sequence_enrollment (status);
CREATE INDEX idx_sequence_enrollment_next_action ON communications_sequence_enrollment (next_action_at) WHERE status = 'active';
```

## 🛠️ Implementation Steps

### Step 1: UniPile Integration Foundation (Day 1-4)

#### 1.1 UniPile Service Layer
```python
# communications/unipile_service.py
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from .models import Channel, Conversation, Message
import logging

logger = logging.getLogger(__name__)

class UniPileService:
    """Service for interacting with UniPile API"""
    
    def __init__(self):
        self.api_key = settings.UNIPILE_API_KEY
        self.base_url = "https://api.unipile.com/v1"
        self.rate_limiter = {}  # Per-account rate limiting
    
    async def connect_account(
        self, 
        user: 'User', 
        provider: str, 
        auth_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Connect a new communication account via UniPile"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'provider': provider,
                    'auth': auth_data
                }
                
                async with session.post(
                    f"{self.base_url}/accounts",
                    headers=headers,
                    json=payload
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # Create channel record
                        channel = Channel.objects.create(
                            name=f"{provider.title()} Account",
                            channel_type=self._get_channel_type(provider),
                            unipile_account_id=result['account_id'],
                            provider_name=provider,
                            provider_config=result.get('config', {}),
                            auth_status='connected',
                            created_by=user
                        )
                        
                        # Start initial sync
                        await self.sync_account_messages(channel)
                        
                        return {
                            'success': True,
                            'channel_id': channel.id,
                            'account_id': result['account_id']
                        }
                    else:
                        error_data = await response.json()
                        logger.error(f"UniPile account connection failed: {error_data}")
                        return {
                            'success': False,
                            'error': error_data.get('message', 'Connection failed')
                        }
                        
        except Exception as e:
            logger.error(f"UniPile connection error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def sync_account_messages(
        self, 
        channel: 'Channel', 
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Sync messages from UniPile account"""
        try:
            import aiohttp
            
            if not channel.unipile_account_id:
                return {'success': False, 'error': 'No UniPile account ID'}
            
            # Apply rate limiting
            await self._apply_rate_limit(channel.unipile_account_id)
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
                
                params = {
                    'account_id': channel.unipile_account_id,
                    'limit': 100
                }
                
                if since:
                    params['since'] = since.isoformat()
                
                async with session.get(
                    f"{self.base_url}/messages",
                    headers=headers,
                    params=params
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        messages_data = data.get('messages', [])
                        
                        # Process messages
                        processed_count = 0
                        for message_data in messages_data:
                            if await self._process_message(channel, message_data):
                                processed_count += 1
                        
                        # Update sync timestamp
                        channel.last_sync_at = datetime.now(timezone.utc)
                        channel.save()
                        
                        return {
                            'success': True,
                            'processed_count': processed_count,
                            'total_messages': len(messages_data)
                        }
                    else:
                        error_data = await response.json()
                        logger.error(f"UniPile sync failed: {error_data}")
                        return {
                            'success': False,
                            'error': error_data.get('message', 'Sync failed')
                        }
                        
        except Exception as e:
            logger.error(f"UniPile sync error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def send_message(
        self, 
        channel: 'Channel',
        recipient: str,
        content: str,
        message_type: str = 'text',
        thread_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send message via UniPile"""
        try:
            import aiohttp
            
            await self._apply_rate_limit(channel.unipile_account_id)
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'account_id': channel.unipile_account_id,
                    'recipient': recipient,
                    'content': content,
                    'type': message_type
                }
                
                if thread_id:
                    payload['thread_id'] = thread_id
                    
                if metadata:
                    payload['metadata'] = metadata
                
                async with session.post(
                    f"{self.base_url}/messages/send",
                    headers=headers,
                    json=payload
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # Create local message record
                        message = await self._create_outbound_message(
                            channel=channel,
                            recipient=recipient,
                            content=content,
                            external_id=result.get('message_id'),
                            thread_id=thread_id
                        )
                        
                        return {
                            'success': True,
                            'message_id': message.id,
                            'external_message_id': result.get('message_id')
                        }
                    else:
                        error_data = await response.json()
                        logger.error(f"UniPile send failed: {error_data}")
                        return {
                            'success': False,
                            'error': error_data.get('message', 'Send failed')
                        }
                        
        except Exception as e:
            logger.error(f"UniPile send error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _process_message(
        self, 
        channel: 'Channel', 
        message_data: Dict[str, Any]
    ) -> bool:
        """Process a single message from UniPile sync"""
        try:
            external_id = message_data.get('id')
            
            # Check if message already exists
            if Message.objects.filter(external_message_id=external_id).exists():
                return False  # Already processed
            
            # Get or create conversation
            thread_id = message_data.get('thread_id')
            conversation = await self._get_or_create_conversation(
                channel=channel,
                thread_id=thread_id,
                participants=message_data.get('participants', [])
            )
            
            # Create message record
            message = Message.objects.create(
                conversation=conversation,
                external_message_id=external_id,
                thread_id=thread_id,
                content=message_data.get('content', ''),
                content_type=message_data.get('content_type', 'text'),
                direction='inbound' if message_data.get('direction') == 'incoming' else 'outbound',
                sender_email=message_data.get('sender', {}).get('email'),
                sender_name=message_data.get('sender', {}).get('name'),
                recipient_info=message_data.get('recipients', {}),
                status='delivered',
                sent_at=self._parse_datetime(message_data.get('sent_at')),
                attachments=message_data.get('attachments', [])
            )
            
            # Update conversation
            conversation.last_message_at = message.created_at
            if message.direction == 'inbound':
                conversation.last_inbound_at = message.created_at
            else:
                conversation.last_outbound_at = message.created_at
            conversation.message_count += 1
            conversation.save()
            
            # Trigger AI analysis
            await self._analyze_message_ai(message)
            
            # Broadcast real-time update
            await self._broadcast_message_update(message)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            return False
    
    async def _get_or_create_conversation(
        self, 
        channel: 'Channel',
        thread_id: str,
        participants: List[Dict[str, Any]]
    ) -> 'Conversation':
        """Get or create conversation for thread"""
        
        # Try to find existing conversation
        conversation = Conversation.objects.filter(
            channel=channel,
            external_thread_id=thread_id
        ).first()
        
        if conversation:
            return conversation
        
        # Create new conversation
        conversation = Conversation.objects.create(
            external_thread_id=thread_id,
            channel=channel,
            participants=participants,
            subject=self._extract_subject(participants)
        )
        
        # Try to link to existing contact
        await self._link_conversation_to_contact(conversation, participants)
        
        return conversation
    
    async def _create_outbound_message(
        self,
        channel: 'Channel',
        recipient: str,
        content: str,
        external_id: str,
        thread_id: Optional[str] = None
    ) -> 'Message':
        """Create outbound message record"""
        
        # Get or create conversation
        if thread_id:
            conversation = await self._get_or_create_conversation(
                channel=channel,
                thread_id=thread_id,
                participants=[{'email': recipient}]
            )
        else:
            # Create new conversation
            conversation = Conversation.objects.create(
                channel=channel,
                participants=[{'email': recipient}]
            )
        
        # Create message
        message = Message.objects.create(
            conversation=conversation,
            external_message_id=external_id,
            thread_id=thread_id,
            content=content,
            direction='outbound',
            recipient_info={'email': recipient},
            status='sent',
            sent_at=datetime.now(timezone.utc)
        )
        
        # Update conversation
        conversation.last_message_at = message.created_at
        conversation.last_outbound_at = message.created_at
        conversation.message_count += 1
        conversation.save()
        
        return message
    
    def _get_channel_type(self, provider: str) -> str:
        """Map provider to channel type"""
        mapping = {
            'gmail': 'email',
            'outlook': 'email',
            'whatsapp_business': 'whatsapp',
            'linkedin': 'linkedin',
            'slack': 'slack',
            'twilio': 'sms'
        }
        return mapping.get(provider, 'email')
    
    async def _apply_rate_limit(self, account_id: str):
        """Apply rate limiting for account"""
        # Simplified rate limiting - production would use Redis
        now = datetime.now(timezone.utc)
        if account_id not in self.rate_limiter:
            self.rate_limiter[account_id] = []
        
        # Remove old requests (older than 1 hour)
        hour_ago = now.timestamp() - 3600
        self.rate_limiter[account_id] = [
            req_time for req_time in self.rate_limiter[account_id] 
            if req_time > hour_ago
        ]
        
        # Check if we're at the limit (100 requests per hour)
        if len(self.rate_limiter[account_id]) >= 100:
            sleep_time = 3600 / 100  # Spread requests evenly
            await asyncio.sleep(sleep_time)
        
        # Add current request
        self.rate_limiter[account_id].append(now.timestamp())
    
    def _parse_datetime(self, dt_string: str) -> Optional[datetime]:
        """Parse datetime string to datetime object"""
        if not dt_string:
            return None
        
        try:
            return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        except:
            return None
    
    def _extract_subject(self, participants: List[Dict[str, Any]]) -> str:
        """Extract conversation subject from participants"""
        # Simplified subject extraction
        if participants:
            return f"Conversation with {participants[0].get('name', participants[0].get('email', 'Unknown'))}"
        return "New Conversation"
    
    async def _link_conversation_to_contact(
        self, 
        conversation: 'Conversation', 
        participants: List[Dict[str, Any]]
    ):
        """Link conversation to existing contact record"""
        # This would search for existing contacts in pipelines
        # and link the conversation to the appropriate record
        pass
    
    async def _analyze_message_ai(self, message: 'Message'):
        """Analyze message with AI for sentiment and intent"""
        from ai.services import openai_service
        
        try:
            # Analyze sentiment
            sentiment_result = await openai_service.classify_text(
                message.content,
                ['positive', 'negative', 'neutral']
            )
            
            message.sentiment = sentiment_result['category']
            
            # Extract intent (simplified)
            intent_prompt = f"""Analyze this message and determine the sender's intent. Choose from: question, complaint, request, compliment, booking, other.

Message: {message.content}

Return only the intent category."""
            
            intent_result = await openai_service.generate_completion(
                prompt=intent_prompt,
                temperature=0.1
            )
            
            message.intent = intent_result['content'].strip().lower()
            message.save()
            
        except Exception as e:
            logger.error(f"AI analysis failed for message {message.id}: {e}")
    
    async def _broadcast_message_update(self, message: 'Message'):
        """Broadcast real-time message update"""
        from channels.layers import get_channel_layer
        
        channel_layer = get_channel_layer()
        if channel_layer:
            await channel_layer.group_send(
                f"conversation_{message.conversation_id}",
                {
                    'type': 'message_update',
                    'message': {
                        'id': message.id,
                        'content': message.content,
                        'direction': message.direction,
                        'sender_name': message.sender_name,
                        'created_at': message.created_at.isoformat()
                    }
                }
            )

# Global UniPile service instance
unipile_service = UniPileService()
```

### Step 2: AI-Powered Sequence Engine (Day 5-9)

#### 2.1 Sequence Management System
```python
# communications/sequence_engine.py
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from django.contrib.auth import get_user_model
from django.db import transaction
from pipelines.models import Record
from .models import Sequence, SequenceEnrollment, Message, Channel
from .unipile_service import unipile_service
from ai.services import openai_service
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class SequenceEngine:
    """AI-powered communication sequence engine"""
    
    def __init__(self):
        self.processing_lock = asyncio.Lock()
    
    async def enroll_contact(
        self, 
        sequence: 'Sequence',
        contact_record: 'Record',
        user: 'User',
        custom_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Enroll a contact in a sequence"""
        try:
            # Validate contact eligibility
            eligibility = await self._check_contact_eligibility(sequence, contact_record)
            if not eligibility['eligible']:
                return {
                    'success': False,
                    'error': eligibility['reason']
                }
            
            # Generate personalization data
            personalization_data = await self._generate_personalization_data(
                sequence, contact_record, custom_data
            )
            
            # Calculate next action time
            next_action_at = await self._calculate_next_action_time(
                sequence, 0, contact_record
            )
            
            # Create enrollment
            enrollment = SequenceEnrollment.objects.create(
                sequence=sequence,
                contact_record=contact_record,
                contact_email=contact_record.data.get('email'),
                contact_phone=contact_record.data.get('phone'),
                status='active',
                current_step=0,
                next_action_at=next_action_at,
                personalization_data=personalization_data,
                enrolled_by=user
            )
            
            logger.info(f"Enrolled contact {contact_record.id} in sequence {sequence.id}")
            
            return {
                'success': True,
                'enrollment_id': enrollment.id,
                'next_action_at': next_action_at
            }
            
        except Exception as e:
            logger.error(f"Failed to enroll contact: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def process_due_actions(self) -> Dict[str, Any]:
        """Process all due sequence actions"""
        async with self.processing_lock:
            try:
                now = datetime.now(timezone.utc)
                
                # Get due enrollments
                due_enrollments = SequenceEnrollment.objects.filter(
                    status='active',
                    next_action_at__lte=now
                ).select_related('sequence', 'contact_record')[:100]  # Process in batches
                
                processed_count = 0
                failed_count = 0
                
                for enrollment in due_enrollments:
                    try:
                        await self._process_sequence_step(enrollment)
                        processed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to process enrollment {enrollment.id}: {e}")
                        failed_count += 1
                
                return {
                    'success': True,
                    'processed': processed_count,
                    'failed': failed_count
                }
                
            except Exception as e:
                logger.error(f"Sequence processing error: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
    
    async def _process_sequence_step(self, enrollment: 'SequenceEnrollment'):
        """Process a single sequence step for an enrollment"""
        sequence = enrollment.sequence
        steps = sequence.steps
        current_step = enrollment.current_step
        
        if current_step >= len(steps):
            # Sequence completed
            enrollment.status = 'completed'
            enrollment.completed_at = datetime.now(timezone.utc)
            enrollment.save()
            return
        
        step_config = steps[current_step]
        step_type = step_config.get('type', 'message')
        
        if step_type == 'message':
            await self._process_message_step(enrollment, step_config)
        elif step_type == 'wait':
            await self._process_wait_step(enrollment, step_config)
        elif step_type == 'condition':
            await self._process_condition_step(enrollment, step_config)
        elif step_type == 'action':
            await self._process_action_step(enrollment, step_config)
        else:
            logger.warning(f"Unknown step type: {step_type}")
            await self._advance_to_next_step(enrollment)
    
    async def _process_message_step(
        self, 
        enrollment: 'SequenceEnrollment', 
        step_config: Dict[str, Any]
    ):
        """Process a message step in the sequence"""
        try:
            # Generate personalized content
            content = await self._generate_step_content(enrollment, step_config)
            
            # Select optimal channel
            channel = await self._select_optimal_channel(enrollment, step_config)
            
            if not channel:
                raise Exception("No suitable channel available")
            
            # Determine recipient
            recipient = self._get_recipient_address(enrollment, channel)
            
            # Send message
            send_result = await unipile_service.send_message(
                channel=channel,
                recipient=recipient,
                content=content,
                metadata={
                    'sequence_id': enrollment.sequence_id,
                    'enrollment_id': enrollment.id,
                    'step': enrollment.current_step
                }
            )
            
            if send_result['success']:
                # Update enrollment
                enrollment.messages_sent += 1
                await self._advance_to_next_step(enrollment)
                
                logger.info(f"Sent sequence message for enrollment {enrollment.id}")
            else:
                raise Exception(f"Message send failed: {send_result['error']}")
                
        except Exception as e:
            logger.error(f"Message step failed for enrollment {enrollment.id}: {e}")
            # Handle failure - could retry or mark as failed
            await self._handle_step_failure(enrollment, str(e))
    
    async def _generate_step_content(
        self, 
        enrollment: 'SequenceEnrollment', 
        step_config: Dict[str, Any]
    ) -> str:
        """Generate personalized content for sequence step"""
        
        base_template = step_config.get('content_template', '')
        use_ai_enhancement = step_config.get('ai_enhanced', False) and enrollment.sequence.ai_enabled
        
        # Replace personalization variables
        personalized_content = await self._apply_personalization(
            template=base_template,
            enrollment=enrollment
        )
        
        if use_ai_enhancement:
            # Use AI to enhance and personalize content
            personalized_content = await self._enhance_content_with_ai(
                content=personalized_content,
                enrollment=enrollment,
                step_config=step_config
            )
        
        return personalized_content
    
    async def _apply_personalization(
        self, 
        template: str, 
        enrollment: 'SequenceEnrollment'
    ) -> str:
        """Apply personalization variables to template"""
        
        # Get contact data
        contact_data = enrollment.contact_record.data
        personalization_data = enrollment.personalization_data
        
        # Merge data sources
        variables = {
            **contact_data,
            **personalization_data,
            'first_name': contact_data.get('first_name', 'there'),
            'company_name': contact_data.get('company_name', contact_data.get('company', '')),
            'contact_name': f"{contact_data.get('first_name', '')} {contact_data.get('last_name', '')}".strip()
        }
        
        # Apply variables to template
        try:
            return template.format(**variables)
        except KeyError as e:
            logger.warning(f"Missing personalization variable: {e}")
            # Return template with unfilled variables
            return template
    
    async def _enhance_content_with_ai(
        self, 
        content: str, 
        enrollment: 'SequenceEnrollment',
        step_config: Dict[str, Any]
    ) -> str:
        """Enhance content using AI based on contact context"""
        
        try:
            # Gather context about the contact
            contact_context = self._build_contact_context(enrollment)
            
            # Generate AI enhancement prompt
            enhancement_prompt = f"""
You are helping personalize a business communication message. Here's the context:

CONTACT INFORMATION:
{contact_context}

CURRENT MESSAGE:
{content}

SEQUENCE OBJECTIVE:
{enrollment.sequence.objective}

Please enhance this message to be more personalized and effective while maintaining professionalism. Keep the same general structure and intent, but make it more engaging and relevant to this specific contact.

Return only the enhanced message content:
"""
            
            result = await openai_service.generate_completion(
                prompt=enhancement_prompt,
                temperature=0.7,
                max_tokens=500
            )
            
            return result['content'].strip()
            
        except Exception as e:
            logger.error(f"AI content enhancement failed: {e}")
            return content  # Fallback to original content
    
    async def _select_optimal_channel(
        self, 
        enrollment: 'SequenceEnrollment', 
        step_config: Dict[str, Any]
    ) -> Optional['Channel']:
        """Select the optimal communication channel for this step"""
        
        # Get available channels
        available_channels = Channel.objects.filter(
            is_active=True,
            auth_status='connected'
        )
        
        # Check step-specific channel preferences
        preferred_channels = step_config.get('preferred_channels', [])
        if preferred_channels:
            available_channels = available_channels.filter(
                channel_type__in=preferred_channels
            )
        
        if not available_channels.exists():
            return None
        
        # AI-powered channel selection based on contact engagement
        if enrollment.sequence.ai_enabled:
            return await self._ai_select_channel(enrollment, available_channels)
        else:
            # Default to first available channel
            return available_channels.first()
    
    async def _ai_select_channel(
        self, 
        enrollment: 'SequenceEnrollment', 
        channels: List['Channel']
    ) -> 'Channel':
        """Use AI to select optimal channel based on contact behavior"""
        
        try:
            # Analyze contact's historical engagement by channel
            engagement_data = await self._analyze_contact_engagement(enrollment)
            
            # Simple scoring: prefer channels with higher engagement
            best_channel = channels[0]  # Default
            best_score = 0
            
            for channel in channels:
                channel_engagement = engagement_data.get(channel.channel_type, {})
                
                # Calculate engagement score
                open_rate = channel_engagement.get('open_rate', 0.5)
                click_rate = channel_engagement.get('click_rate', 0.1)
                reply_rate = channel_engagement.get('reply_rate', 0.05)
                
                score = (open_rate * 0.4) + (click_rate * 0.3) + (reply_rate * 0.3)
                
                if score > best_score:
                    best_score = score
                    best_channel = channel
            
            return best_channel
            
        except Exception as e:
            logger.error(f"AI channel selection failed: {e}")
            return channels[0]  # Fallback to first channel
    
    async def _advance_to_next_step(self, enrollment: 'SequenceEnrollment'):
        """Advance enrollment to next step"""
        
        enrollment.current_step += 1
        
        # Check if sequence is complete
        if enrollment.current_step >= len(enrollment.sequence.steps):
            enrollment.status = 'completed'
            enrollment.completed_at = datetime.now(timezone.utc)
            enrollment.next_action_at = None
        else:
            # Calculate next action time
            enrollment.next_action_at = await self._calculate_next_action_time(
                enrollment.sequence,
                enrollment.current_step,
                enrollment.contact_record
            )
        
        enrollment.save()
    
    async def _calculate_next_action_time(
        self, 
        sequence: 'Sequence',
        step_index: int,
        contact_record: 'Record'
    ) -> datetime:
        """Calculate when the next action should occur"""
        
        if step_index >= len(sequence.steps):
            return datetime.now(timezone.utc)  # Immediate if no more steps
        
        step_config = sequence.steps[step_index]
        delay_config = step_config.get('delay', {'type': 'immediate'})
        
        base_time = datetime.now(timezone.utc)
        
        if delay_config['type'] == 'immediate':
            return base_time
        elif delay_config['type'] == 'delay':
            delay_minutes = delay_config.get('minutes', 0)
            delay_hours = delay_config.get('hours', 0)
            delay_days = delay_config.get('days', 0)
            
            total_delay = timedelta(
                minutes=delay_minutes,
                hours=delay_hours,
                days=delay_days
            )
            
            next_time = base_time + total_delay
            
            # Respect business hours if configured
            if sequence.business_hours_only:
                next_time = self._adjust_for_business_hours(next_time, sequence.default_timezone)
            
            return next_time
        else:
            return base_time
    
    def _adjust_for_business_hours(
        self, 
        target_time: datetime, 
        timezone_str: str = 'UTC'
    ) -> datetime:
        """Adjust time to fall within business hours"""
        
        # Simplified business hours: 9 AM - 5 PM, Monday-Friday
        import pytz
        
        try:
            tz = pytz.timezone(timezone_str)
            local_time = target_time.astimezone(tz)
            
            # If weekend, move to Monday
            if local_time.weekday() >= 5:  # Saturday or Sunday
                days_to_monday = 7 - local_time.weekday()
                local_time = local_time + timedelta(days=days_to_monday)
                local_time = local_time.replace(hour=9, minute=0, second=0, microsecond=0)
            
            # If outside business hours, adjust
            elif local_time.hour < 9:
                local_time = local_time.replace(hour=9, minute=0, second=0, microsecond=0)
            elif local_time.hour >= 17:
                # Move to next business day at 9 AM
                local_time = local_time + timedelta(days=1)
                local_time = local_time.replace(hour=9, minute=0, second=0, microsecond=0)
                
                # Check if next day is weekend
                if local_time.weekday() >= 5:
                    days_to_monday = 7 - local_time.weekday()
                    local_time = local_time + timedelta(days=days_to_monday)
            
            return local_time.astimezone(timezone.utc)
            
        except Exception as e:
            logger.error(f"Business hours adjustment failed: {e}")
            return target_time
    
    def _build_contact_context(self, enrollment: 'SequenceEnrollment') -> str:
        """Build context string about contact for AI"""
        
        contact_data = enrollment.contact_record.data
        context_parts = []
        
        # Basic info
        if contact_data.get('first_name'):
            context_parts.append(f"Name: {contact_data['first_name']} {contact_data.get('last_name', '')}")
        
        if contact_data.get('company_name') or contact_data.get('company'):
            context_parts.append(f"Company: {contact_data.get('company_name', contact_data.get('company'))}")
        
        if contact_data.get('position') or contact_data.get('job_title'):
            context_parts.append(f"Position: {contact_data.get('position', contact_data.get('job_title'))}")
        
        if contact_data.get('industry'):
            context_parts.append(f"Industry: {contact_data['industry']}")
        
        # Engagement history
        context_parts.append(f"Messages sent: {enrollment.messages_sent}")
        context_parts.append(f"Engagement score: {enrollment.engagement_score}")
        
        return "\n".join(context_parts)
    
    async def _analyze_contact_engagement(
        self, 
        enrollment: 'SequenceEnrollment'
    ) -> Dict[str, Dict[str, float]]:
        """Analyze contact's engagement patterns by channel"""
        
        # Get historical messages for this contact
        contact_messages = Message.objects.filter(
            conversation__primary_contact_id=enrollment.contact_record_id
        ).select_related('conversation__channel')
        
        # Analyze by channel type
        channel_stats = {}
        
        for message in contact_messages:
            channel_type = message.conversation.channel.channel_type
            
            if channel_type not in channel_stats:
                channel_stats[channel_type] = {
                    'sent': 0,
                    'opened': 0,
                    'clicked': 0,
                    'replied': 0
                }
            
            if message.direction == 'outbound':
                channel_stats[channel_type]['sent'] += 1
                
                if message.status in ['delivered', 'read']:
                    channel_stats[channel_type]['opened'] += 1
                
                # Check for replies within 48 hours
                reply_exists = Message.objects.filter(
                    conversation=message.conversation,
                    direction='inbound',
                    created_at__gt=message.created_at,
                    created_at__lt=message.created_at + timedelta(hours=48)
                ).exists()
                
                if reply_exists:
                    channel_stats[channel_type]['replied'] += 1
        
        # Calculate rates
        engagement_data = {}
        for channel_type, stats in channel_stats.items():
            sent = stats['sent']
            if sent > 0:
                engagement_data[channel_type] = {
                    'open_rate': stats['opened'] / sent,
                    'click_rate': stats['clicked'] / sent,
                    'reply_rate': stats['replied'] / sent
                }
        
        return engagement_data
    
    # Additional helper methods would be implemented here...

# Global sequence engine instance
sequence_engine = SequenceEngine()
```

This comprehensive Phase 08 document establishes the sophisticated communication layer with UniPile integration and AI-powered sequences. The system provides intelligent message routing, adaptive sequence behavior, and comprehensive analytics.

Would you like me to complete the final 2 phases (09-10) to finish the comprehensive implementation plan?