"""
Participant Resolution Service
Unified service for resolving participants to contacts across all channels
"""
import logging
from typing import Dict, Any, List, Tuple, Optional
from django.utils import timezone
from django.db import models, transaction
from asgiref.sync import sync_to_async, async_to_sync

from communications.models import Participant, ConversationParticipant
# Resolution gateway was removed - using stub for now
def get_resolution_gateway(tenant):
    """Stub for removed resolution gateway"""
    class StubGateway:
        async def resolve_contacts(self, identifiers, min_confidence=0):
            return {'matches': []}  # No matches for now
    return StubGateway()

logger = logging.getLogger(__name__)

# Personal email domains to exclude from company matching
PERSONAL_EMAIL_DOMAINS = [
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'mail.com', 'protonmail.com', 'yandex.com', 'live.com'
]

# Default confidence threshold for automatic contact matching
DEFAULT_CONFIDENCE_THRESHOLD = 0.7


class ParticipantResolutionService:
    """
    Unified service for resolving participants to contacts
    Works across all UniPile channels
    """
    
    def __init__(self, tenant=None, confidence_threshold=None):
        self.tenant = tenant
        self.confidence_threshold = confidence_threshold or DEFAULT_CONFIDENCE_THRESHOLD
        self.gateway = get_resolution_gateway(tenant)
    
    async def resolve_or_create_participant(
        self,
        identifier_data: Dict[str, Any],
        channel_type: str = None
    ) -> Tuple[Participant, bool]:
        """
        Find or create participant, then attempt contact resolution
        
        Args:
            identifier_data: Dict with channel-specific identifiers
                - email: Email address
                - phone: Phone number
                - linkedin_member_urn: LinkedIn member URN
                - instagram_username: Instagram handle
                - name: Display name
                - avatar_url: Profile picture URL
            channel_type: Optional channel type for context
            
        Returns:
            Tuple of (Participant, was_created)
        """
        # Try to find existing participant
        participant = await self.find_existing_participant(identifier_data)
        
        if not participant:
            participant = await self.create_participant(identifier_data)
            created = True
        else:
            # Update participant with any new information
            await self.update_participant(participant, identifier_data)
            created = False
        
        # Attempt resolution if not already resolved (check both contact and secondary)
        # Check if records exist in async-safe way with schema context
        from django_tenants.utils import schema_context
        
        def check_existing_resolution():
            with schema_context(self.tenant.schema_name if self.tenant else 'public'):
                # Skip resolution if already has either contact or secondary record
                return bool(participant.contact_record_id or participant.secondary_record_id)
        
        has_existing_resolution = await sync_to_async(check_existing_resolution)()
        if not has_existing_resolution:
            await self.resolve_to_contact(participant, identifier_data)
        
        return participant, created
    
    async def find_existing_participant(self, identifier_data: Dict) -> Optional[Participant]:
        """
        Find existing participant by any available identifier
        """
        from django_tenants.utils import schema_context
        
        # Build query conditions
        conditions = models.Q()
        
        if identifier_data.get('email'):
            conditions |= models.Q(email=identifier_data['email'])
        if identifier_data.get('phone'):
            conditions |= models.Q(phone=identifier_data['phone'])
        if identifier_data.get('linkedin_member_urn'):
            conditions |= models.Q(linkedin_member_urn=identifier_data['linkedin_member_urn'])
        if identifier_data.get('instagram_username'):
            conditions |= models.Q(instagram_username=identifier_data['instagram_username'])
        if identifier_data.get('facebook_id'):
            conditions |= models.Q(facebook_id=identifier_data['facebook_id'])
        if identifier_data.get('telegram_id'):
            conditions |= models.Q(telegram_id=identifier_data['telegram_id'])
        if identifier_data.get('twitter_handle'):
            conditions |= models.Q(twitter_handle=identifier_data['twitter_handle'])
        
        if not conditions:
            return None
        
        # Get first matching participant within tenant schema
        def get_participant():
            with schema_context(self.tenant.schema_name if self.tenant else 'public'):
                return Participant.objects.filter(conditions).first()
        
        participant = await sync_to_async(get_participant)()
        
        return participant
    
    async def create_participant(self, identifier_data: Dict) -> Participant:
        """
        Create new participant from identifier data
        """
        from django_tenants.utils import schema_context
        
        def create_in_schema():
            with schema_context(self.tenant.schema_name if self.tenant else 'public'):
                return Participant.objects.create(
                    email=identifier_data.get('email', ''),
                    phone=identifier_data.get('phone', ''),
                    linkedin_member_urn=identifier_data.get('linkedin_member_urn', ''),
                    instagram_username=identifier_data.get('instagram_username', ''),
                    facebook_id=identifier_data.get('facebook_id', ''),
                    telegram_id=identifier_data.get('telegram_id', ''),
                    twitter_handle=identifier_data.get('twitter_handle', ''),
                    name=identifier_data.get('name', ''),
                    avatar_url=identifier_data.get('avatar_url', ''),
                    metadata=identifier_data.get('metadata', {})
                )
        
        participant = await sync_to_async(create_in_schema)()
        
        logger.info(f"Created new participant: {participant.get_display_name()}")
        return participant
    
    async def update_participant(self, participant: Participant, identifier_data: Dict):
        """
        Update participant with new information
        """
        updated = False
        
        # Update name if better one is available
        if identifier_data.get('name') and not participant.name:
            participant.name = identifier_data['name']
            updated = True
        
        # Update avatar if not set
        if identifier_data.get('avatar_url') and not participant.avatar_url:
            participant.avatar_url = identifier_data['avatar_url']
            updated = True
        
        # Add any missing identifiers
        for field in ['email', 'phone', 'linkedin_member_urn', 'instagram_username',
                      'facebook_id', 'telegram_id', 'twitter_handle']:
            if identifier_data.get(field) and not getattr(participant, field):
                setattr(participant, field, identifier_data[field])
                updated = True
        
        if updated:
            participant.last_seen = timezone.now()
            from django_tenants.utils import schema_context
            
            def save_in_schema():
                with schema_context(self.tenant.schema_name):
                    participant.save()
            
            await sync_to_async(save_in_schema)()
    
    async def resolve_to_contact(self, participant: Participant, identifier_data: Dict):
        """
        Try to match participant to CRM records (both primary contact and secondary via domain)
        """
        # Build resolution identifiers
        identifiers = {}
        
        if participant.email:
            identifiers['email'] = participant.email
            # Extract domain for secondary matching (e.g., company/organization)
            domain = participant.email.split('@')[1] if '@' in participant.email else None
            if domain and domain not in PERSONAL_EMAIL_DOMAINS:
                identifiers['domain'] = domain
        
        if participant.phone:
            identifiers['phone'] = participant.phone
        
        if participant.linkedin_member_urn:
            identifiers['linkedin_url'] = f"linkedin.com/in/{participant.linkedin_member_urn}"
        
        if not identifiers:
            return
        
        # Use resolution gateway to find matches across ALL pipelines
        resolution = await self.gateway.resolve_contacts(
            identifiers,
            min_confidence=self.confidence_threshold
        )
        
        if resolution.get('matches'):
            from pipelines.models import Pipeline
            
            # Separate matches by type
            contact_matches = []
            secondary_matches = []
            
            # Get pipeline info for all matches
            @sync_to_async
            def get_pipeline_slug(record_id):
                with schema_context(self.tenant.schema_name):
                    from pipelines.models import Record
                    record = Record.objects.select_related('pipeline').get(id=record_id)
                    return record.pipeline.slug, record.pipeline.name
            
            for match in resolution['matches']:
                # Get pipeline info
                try:
                    pipeline_slug, pipeline_name = await get_pipeline_slug(match['record'].id)
                except:
                    pipeline_slug = ''
                    pipeline_name = ''
                
                match_type = match['match_details'].get('match_type', '')
                matched_field = match['match_details'].get('matched_field', '')
                
                # Store pipeline info in match for later use
                match['pipeline_slug'] = pipeline_slug
                match['pipeline_name'] = pipeline_name
                
                # If matched on email or in a contact-type pipeline
                if 'email' in match_type or 'email' in matched_field or pipeline_slug in ['contacts', 'people', 'candidates']:
                    contact_matches.append(match)
                # If matched on domain or URL field  
                elif 'domain' in match_type or 'domain' in matched_field or 'url' in matched_field or pipeline_slug in ['companies', 'organizations']:
                    secondary_matches.append(match)
                else:
                    # Default: treat as contact if confidence is high
                    contact_matches.append(match)
            
            # Link best contact match
            if contact_matches and contact_matches[0]['confidence'] >= self.confidence_threshold:
                best_contact = contact_matches[0]
                participant.contact_record = best_contact['record']
                participant.resolution_confidence = best_contact['confidence']
                participant.resolution_method = best_contact['match_details'].get('match_type', 'unknown')
                participant.resolved_at = timezone.now()
                
                logger.info(
                    f"Resolved participant {participant.get_display_name()} to contact "
                    f"{best_contact['record'].id} with confidence {best_contact['confidence']}"
                )
            
            # Link best secondary match (e.g., company via domain)
            if secondary_matches and secondary_matches[0]['confidence'] >= self.confidence_threshold:
                best_secondary = secondary_matches[0]
                participant.secondary_record = best_secondary['record']
                participant.secondary_confidence = best_secondary['confidence']
                participant.secondary_resolution_method = best_secondary['match_details'].get('match_type', 'domain')
                participant.secondary_pipeline = best_secondary.get('pipeline_name', '')
                
                logger.info(
                    f"Resolved participant {participant.get_display_name()} to {participant.secondary_pipeline} "
                    f"{best_secondary['record'].id} via {participant.secondary_resolution_method} "
                    f"with confidence {best_secondary['confidence']}"
                )
            
            # Save if any matches were made
            if participant.contact_record or participant.secondary_record:
                from django_tenants.utils import schema_context
                def save_in_schema():
                    with schema_context(self.tenant.schema_name):
                        participant.save()
                
                await sync_to_async(save_in_schema)()
    
    async def resolve_conversation_participants(
        self,
        conversation_data: Dict,
        channel_type: str
    ) -> List[Participant]:
        """
        Extract and resolve all participants from conversation data
        
        Args:
            conversation_data: Raw conversation data from UniPile
            channel_type: Channel type (gmail, whatsapp, linkedin, etc.)
            
        Returns:
            List of resolved Participant objects
        """
        
        # Extract participant identifiers based on channel type
        participant_identifiers = self.extract_participants(conversation_data, channel_type)
        
        # Resolve each participant
        resolved_participants = []
        for identifier_data in participant_identifiers:
            participant, _ = await self.resolve_or_create_participant(
                identifier_data,
                channel_type
            )
            resolved_participants.append(participant)
        
        return resolved_participants
    
    def extract_participants(self, conversation_data: Dict, channel_type: str) -> List[Dict]:
        """
        Extract participant identifiers from conversation data based on channel type
        """
        participants = []
        
        if channel_type in ['gmail', 'outlook', 'mail', 'email']:
            participants = self.extract_email_participants(conversation_data)
        elif channel_type == 'whatsapp':
            participants = self.extract_whatsapp_participants(conversation_data)
        elif channel_type == 'linkedin':
            participants = self.extract_linkedin_participants(conversation_data)
        elif channel_type == 'instagram':
            participants = self.extract_instagram_participants(conversation_data)
        elif channel_type == 'messenger':
            participants = self.extract_messenger_participants(conversation_data)
        elif channel_type == 'telegram':
            participants = self.extract_telegram_participants(conversation_data)
        elif channel_type == 'twitter':
            participants = self.extract_twitter_participants(conversation_data)
        
        return participants
    
    def extract_email_participants(self, email_data: Dict) -> List[Dict]:
        """
        Extract participants from email data (FROM, TO, CC, BCC)
        """
        participants = []
        
        # Extract FROM
        from_data = email_data.get('from_attendee') or email_data.get('from', {})
        if from_data:
            email = from_data.get('identifier', '')
            name = from_data.get('display_name', '')
            participants.append({
                'email': email,
                'name': name,
                'role': 'sender',
                'metadata': {'original_data': from_data}
            })
        
        # Extract TO
        for to in email_data.get('to_attendees', []) or email_data.get('to', []):
            email = to.get('identifier', '')
            name = to.get('display_name', '')
            participants.append({
                'email': email,
                'name': name,
                'role': 'recipient',
                'metadata': {'original_data': to}
            })
        
        # Extract CC
        for cc in email_data.get('cc_attendees', []) or email_data.get('cc', []):
            participants.append({
                'email': cc.get('identifier', ''),
                'name': cc.get('display_name', ''),
                'role': 'cc',
                'metadata': {'original_data': cc}
            })
        
        # Extract BCC (if available)
        for bcc in email_data.get('bcc_attendees', []) or email_data.get('bcc', []):
            participants.append({
                'email': bcc.get('identifier', ''),
                'name': bcc.get('display_name', ''),
                'role': 'bcc',
                'metadata': {'original_data': bcc}
            })
        return participants
    
    def extract_whatsapp_participants(self, chat_data: Dict) -> List[Dict]:
        """
        Extract participants from WhatsApp chat data
        """
        participants = []
        
        # Extract attendees from chat
        for attendee in chat_data.get('attendees', []):
            phone = attendee.get('provider_id', '').replace('@s.whatsapp.net', '')
            if phone:
                phone = phone if phone.startswith('+') else f"+{phone}"
            
            participants.append({
                'phone': phone,
                'name': attendee.get('name', ''),
                'avatar_url': attendee.get('picture_url', ''),
                'role': 'member',
                'metadata': {
                    'is_self': attendee.get('is_self', False),
                    'original_data': attendee
                }
            })
        
        return participants
    
    def extract_linkedin_participants(self, conversation_data: Dict) -> List[Dict]:
        """
        Extract participants from LinkedIn conversation
        """
        participants = []
        
        for attendee in conversation_data.get('attendees', []):
            participants.append({
                'linkedin_member_urn': attendee.get('member_urn', ''),
                'name': attendee.get('name', ''),
                'avatar_url': attendee.get('picture_url', ''),
                'role': 'member',
                'metadata': {
                    'occupation': attendee.get('occupation', ''),
                    'location': attendee.get('location', ''),
                    'original_data': attendee
                }
            })
        
        return participants
    
    def extract_instagram_participants(self, conversation_data: Dict) -> List[Dict]:
        """
        Extract participants from Instagram conversation
        """
        participants = []
        
        for attendee in conversation_data.get('attendees', []):
            participants.append({
                'instagram_username': attendee.get('public_identifier', ''),
                'name': attendee.get('name', ''),
                'avatar_url': attendee.get('picture_url', ''),
                'role': 'member',
                'metadata': {'original_data': attendee}
            })
        
        return participants
    
    def extract_messenger_participants(self, conversation_data: Dict) -> List[Dict]:
        """
        Extract participants from Facebook Messenger conversation
        """
        participants = []
        
        for attendee in conversation_data.get('attendees', []):
            participants.append({
                'facebook_id': attendee.get('provider_id', ''),
                'name': attendee.get('name', ''),
                'avatar_url': attendee.get('picture_url', ''),
                'role': 'member',
                'metadata': {'original_data': attendee}
            })
        
        return participants
    
    def extract_telegram_participants(self, conversation_data: Dict) -> List[Dict]:
        """
        Extract participants from Telegram conversation
        """
        participants = []
        
        for attendee in conversation_data.get('attendees', []):
            participants.append({
                'telegram_id': attendee.get('provider_id', ''),
                'name': attendee.get('name', ''),
                'phone': attendee.get('phone', ''),  # Telegram sometimes provides phone
                'avatar_url': attendee.get('picture_url', ''),
                'role': 'member',
                'metadata': {'original_data': attendee}
            })
        
        return participants
    
    def extract_twitter_participants(self, conversation_data: Dict) -> List[Dict]:
        """
        Extract participants from Twitter/X conversation
        """
        participants = []
        
        for attendee in conversation_data.get('attendees', []):
            handle = attendee.get('public_identifier', '')
            if handle and not handle.startswith('@'):
                handle = f"@{handle}"
            
            participants.append({
                'twitter_handle': handle,
                'name': attendee.get('name', ''),
                'avatar_url': attendee.get('picture_url', ''),
                'role': 'member',
                'metadata': {'original_data': attendee}
            })
        
        return participants


class ConversationStorageDecider:
    """
    Decides whether to store a conversation based on participants
    """
    
    def __init__(self, tenant=None, confidence_threshold=None):
        self.tenant = tenant
        self.confidence_threshold = confidence_threshold or DEFAULT_CONFIDENCE_THRESHOLD
        self.resolution_service = ParticipantResolutionService(tenant, confidence_threshold)
    
    async def should_store_conversation(
        self,
        conversation_data: Dict,
        channel_type: str
    ) -> Tuple[bool, List[Participant]]:
        """
        Determine if conversation should be stored based on participant resolution
        
        Store if ANY participant has a linked contact record
        
        Returns:
            Tuple of (should_store, resolved_participants)
        """
        # Resolve all participants
        resolved_participants = await self.resolution_service.resolve_conversation_participants(
            conversation_data,
            channel_type
        )
        
        # Check if any participant has a contact OR secondary record match
        # Need to check async-safe with schema context
        from django_tenants.utils import schema_context
        
        def check_records():
            with schema_context(self.tenant.schema_name if self.tenant else 'public'):
                # Store if participant has either contact or secondary record
                return [bool(p.contact_record_id or p.secondary_record_id) for p in resolved_participants]
        
        record_checks = await sync_to_async(check_records)()
        has_record_match = any(record_checks)
        
        logger.info(
            f"Storage decision for conversation: {has_record_match} "
            f"({len(resolved_participants)} participants, "
            f"{sum(record_checks)} with linked records)"
        )
        
        return has_record_match, resolved_participants
    
    async def link_participants_to_conversation(
        self,
        conversation,
        participants: List[Participant],
        participant_roles: Dict[str, str] = None
    ):
        """
        Create ConversationParticipant records to link participants to conversation
        
        Args:
            conversation: Conversation model instance
            participants: List of Participant instances
            participant_roles: Optional dict mapping participant IDs to roles
        """
        for participant in participants:
            role = 'member'  # Default role
            if participant_roles:
                role = participant_roles.get(str(participant.id), 'member')
            
            # Create or update conversation participant link
            await sync_to_async(ConversationParticipant.objects.update_or_create)(
                conversation=conversation,
                participant=participant,
                defaults={
                    'role': role,
                    'is_active': True,
                    'joined_at': timezone.now()
                }
            )