"""
Contact Resolution and Auto-Creation Service for Phase 8
Automatically resolves and creates contact records from communication activities
"""
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.utils import timezone as django_timezone
from django.db import transaction
from asgiref.sync import sync_to_async

from pipelines.models import Pipeline, Record, Field
from .models import UserChannelConnection, Conversation, Message
from .services import communication_service

logger = logging.getLogger(__name__)
User = get_user_model()


class ContactResolutionService:
    """Service for resolving and auto-creating contact records"""
    
    def __init__(self):
        self.email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        self.phone_pattern = re.compile(r'^[\+]?[1-9][\d\s\-\(\)]{7,15}$')
        self.linkedin_pattern = re.compile(r'linkedin\.com/in/([a-zA-Z0-9\-]+)')
    
    async def resolve_contact_from_message(
        self,
        message_data: Dict[str, Any],
        user_channel: UserChannelConnection,
        direction: str = 'inbound'
    ) -> Dict[str, Any]:
        """Resolve or create contact from message data"""
        
        try:
            # Extract contact information from message
            contact_info = await self._extract_contact_info(message_data, user_channel.channel_type)
            
            if not contact_info['identifiers']:
                return {
                    'success': False,
                    'error': 'No valid contact identifiers found in message'
                }
            
            # Get tenant configuration
            tenant_config = user_channel.get_tenant_config()
            if not tenant_config or not tenant_config.auto_create_contacts:
                return {
                    'success': False,
                    'error': 'Auto-contact creation disabled for tenant'
                }
            
            # Search for existing contact
            existing_contact = await self._find_existing_contact(
                contact_info, tenant_config.default_contact_pipeline
            )
            
            if existing_contact:
                # Update existing contact with new information
                updated_contact = await self._update_existing_contact(
                    existing_contact, contact_info, message_data
                )
                
                return {
                    'success': True,
                    'contact_id': str(updated_contact.id),
                    'contact_record': updated_contact,
                    'created': False,
                    'updated_fields': contact_info.get('updated_fields', [])
                }
            else:
                # Create new contact
                new_contact = await self._create_new_contact(
                    contact_info, message_data, tenant_config, user_channel.user
                )
                
                return {
                    'success': True,
                    'contact_id': str(new_contact.id),
                    'contact_record': new_contact,
                    'created': True,
                    'contact_data': new_contact.data
                }
                
        except Exception as e:
            logger.error(f"Contact resolution failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def resolve_contact_from_conversation(
        self,
        conversation: Conversation,
        force_update: bool = False
    ) -> Dict[str, Any]:
        """Resolve contact from conversation participants"""
        
        try:
            if conversation.primary_contact and not force_update:
                return {
                    'success': True,
                    'contact_id': str(conversation.primary_contact.id),
                    'contact_record': conversation.primary_contact,
                    'created': False,
                    'message': 'Contact already linked to conversation'
                }
            
            # Extract contact info from participants
            best_participant = self._select_best_participant(conversation.participants)
            if not best_participant:
                return {
                    'success': False,
                    'error': 'No valid participants found in conversation'
                }
            
            # Get channel connection for tenant config
            user_channel = conversation.get_effective_channel()
            if not user_channel:
                return {
                    'success': False,
                    'error': 'No valid channel connection found'
                }
            
            tenant_config = user_channel.get_tenant_config()
            if not tenant_config:
                return {
                    'success': False,
                    'error': 'No tenant configuration found'
                }
            
            # Prepare contact info
            contact_info = {
                'identifiers': {},
                'profile_data': best_participant.copy(),
                'source': 'conversation_participant'
            }
            
            # Extract identifiers
            if best_participant.get('email'):
                contact_info['identifiers']['email'] = best_participant['email']
            if best_participant.get('phone'):
                contact_info['identifiers']['phone'] = best_participant['phone']
            if best_participant.get('linkedin_url'):
                contact_info['identifiers']['linkedin_url'] = best_participant['linkedin_url']
            
            # Search for existing contact
            existing_contact = await self._find_existing_contact(
                contact_info, tenant_config.default_contact_pipeline
            )
            
            if existing_contact:
                # Link conversation to existing contact
                conversation.primary_contact = existing_contact
                await sync_to_async(conversation.save)()
                
                return {
                    'success': True,
                    'contact_id': str(existing_contact.id),
                    'contact_record': existing_contact,
                    'created': False,
                    'linked_to_conversation': True
                }
            else:
                # Create new contact if auto-creation enabled
                if tenant_config.auto_create_contacts:
                    new_contact = await self._create_new_contact(
                        contact_info, best_participant, tenant_config, user_channel.user
                    )
                    
                    # Link conversation to new contact
                    conversation.primary_contact = new_contact
                    await sync_to_async(conversation.save)()
                    
                    return {
                        'success': True,
                        'contact_id': str(new_contact.id),
                        'contact_record': new_contact,
                        'created': True,
                        'linked_to_conversation': True
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Contact not found and auto-creation disabled'
                    }
                    
        except Exception as e:
            logger.error(f"Conversation contact resolution failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def batch_resolve_contacts(
        self,
        conversations: List[Conversation],
        max_concurrent: int = 10
    ) -> Dict[str, Any]:
        """Batch resolve contacts for multiple conversations"""
        
        import asyncio
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def resolve_single(conversation):
            async with semaphore:
                return await self.resolve_contact_from_conversation(conversation)
        
        try:
            tasks = [resolve_single(conv) for conv in conversations]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            success_count = 0
            created_count = 0
            error_count = 0
            errors = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_count += 1
                    errors.append(f"Conversation {conversations[i].id}: {str(result)}")
                elif result.get('success'):
                    success_count += 1
                    if result.get('created'):
                        created_count += 1
                else:
                    error_count += 1
                    errors.append(f"Conversation {conversations[i].id}: {result.get('error', 'Unknown error')}")
            
            return {
                'success': True,
                'total_processed': len(conversations),
                'successful_resolutions': success_count,
                'contacts_created': created_count,
                'errors': error_count,
                'error_details': errors[:10]  # Limit error details
            }
            
        except Exception as e:
            logger.error(f"Batch contact resolution failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def enrich_contact_from_external_sources(
        self,
        contact: Record,
        sources: List[str] = ['clearbit', 'hunter', 'linkedin']
    ) -> Dict[str, Any]:
        """Enrich contact data from external sources"""
        
        try:
            enrichment_data = {}
            
            # Get contact identifiers
            email = contact.data.get('email')
            company = contact.data.get('company')
            
            # Enrich from each source
            for source in sources:
                try:
                    if source == 'clearbit' and email:
                        clearbit_data = await self._enrich_from_clearbit(email)
                        enrichment_data.update(clearbit_data)
                    
                    elif source == 'hunter' and (email or company):
                        hunter_data = await self._enrich_from_hunter(email, company)
                        enrichment_data.update(hunter_data)
                    
                    elif source == 'linkedin' and contact.data.get('linkedin_url'):
                        linkedin_data = await self._enrich_from_linkedin(contact.data['linkedin_url'])
                        enrichment_data.update(linkedin_data)
                    
                except Exception as e:
                    logger.warning(f"Failed to enrich from {source}: {e}")
                    continue
            
            if enrichment_data:
                # Update contact with enriched data
                original_data = contact.data.copy()
                
                # Merge enrichment data (don't overwrite existing data)
                for key, value in enrichment_data.items():
                    if key not in contact.data or not contact.data[key]:
                        contact.data[key] = value
                
                # Add enrichment metadata
                contact.data['_enrichment'] = {
                    'sources': sources,
                    'enriched_at': datetime.now(timezone.utc).isoformat(),
                    'fields_added': list(enrichment_data.keys())
                }
                
                await sync_to_async(contact.save)()
                
                return {
                    'success': True,
                    'contact_id': str(contact.id),
                    'fields_enriched': list(enrichment_data.keys()),
                    'enrichment_data': enrichment_data
                }
            else:
                return {
                    'success': True,
                    'contact_id': str(contact.id),
                    'fields_enriched': [],
                    'message': 'No enrichment data found'
                }
                
        except Exception as e:
            logger.error(f"Contact enrichment failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def deduplicate_contacts(
        self,
        pipeline: Pipeline,
        similarity_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """Find and merge duplicate contacts"""
        
        try:
            # Get all contacts from pipeline
            contacts = await sync_to_async(list)(
                Record.objects.filter(
                    pipeline=pipeline,
                    is_deleted=False
                ).order_by('created_at')
            )
            
            if len(contacts) < 2:
                return {
                    'success': True,
                    'duplicates_found': 0,
                    'contacts_merged': 0,
                    'message': 'Not enough contacts to check for duplicates'
                }
            
            duplicates = []
            processed_ids = set()
            
            # Compare each contact with others
            for i, contact1 in enumerate(contacts):
                if str(contact1.id) in processed_ids:
                    continue
                
                similar_contacts = []
                
                for j, contact2 in enumerate(contacts[i+1:], i+1):
                    if str(contact2.id) in processed_ids:
                        continue
                    
                    similarity = self._calculate_contact_similarity(contact1, contact2)
                    
                    if similarity >= similarity_threshold:
                        similar_contacts.append({
                            'contact': contact2,
                            'similarity': similarity
                        })
                        processed_ids.add(str(contact2.id))
                
                if similar_contacts:
                    duplicates.append({
                        'primary_contact': contact1,
                        'duplicates': similar_contacts
                    })
                    processed_ids.add(str(contact1.id))
            
            # Merge duplicates
            merged_count = 0
            merge_results = []
            
            for duplicate_group in duplicates:
                try:
                    merge_result = await self._merge_duplicate_contacts(duplicate_group)
                    merge_results.append(merge_result)
                    if merge_result['success']:
                        merged_count += 1
                except Exception as e:
                    logger.error(f"Failed to merge duplicate group: {e}")
                    merge_results.append({
                        'success': False,
                        'error': str(e)
                    })
            
            return {
                'success': True,
                'duplicates_found': len(duplicates),
                'contacts_merged': merged_count,
                'merge_results': merge_results
            }
            
        except Exception as e:
            logger.error(f"Contact deduplication failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _extract_contact_info(
        self,
        message_data: Dict[str, Any],
        channel_type: str
    ) -> Dict[str, Any]:
        """Extract contact information from message data"""
        
        contact_info = {
            'identifiers': {},
            'profile_data': {},
            'source': f'{channel_type}_message'
        }
        
        # Extract sender information
        sender = message_data.get('sender', {})
        
        # Email extraction
        sender_email = sender.get('email') or message_data.get('from_email')
        if sender_email and self.email_pattern.match(sender_email):
            contact_info['identifiers']['email'] = sender_email
            contact_info['profile_data']['email'] = sender_email
        
        # Name extraction
        sender_name = sender.get('name') or message_data.get('from_name')
        if sender_name:
            contact_info['profile_data']['name'] = sender_name
            
            # Try to split into first/last name
            name_parts = sender_name.strip().split()
            if len(name_parts) >= 2:
                contact_info['profile_data']['first_name'] = name_parts[0]
                contact_info['profile_data']['last_name'] = ' '.join(name_parts[1:])
            elif len(name_parts) == 1:
                contact_info['profile_data']['first_name'] = name_parts[0]
        
        # Phone extraction
        sender_phone = sender.get('phone') or message_data.get('from_phone')
        if sender_phone and self.phone_pattern.match(sender_phone):
            contact_info['identifiers']['phone'] = sender_phone
            contact_info['profile_data']['phone'] = sender_phone
        
        # LinkedIn extraction
        if channel_type == 'linkedin':
            linkedin_url = sender.get('profile_url') or message_data.get('sender_profile')
            if linkedin_url:
                contact_info['identifiers']['linkedin_url'] = linkedin_url
                contact_info['profile_data']['linkedin_url'] = linkedin_url
                
                # Extract LinkedIn username
                match = self.linkedin_pattern.search(linkedin_url)
                if match:
                    contact_info['profile_data']['linkedin_username'] = match.group(1)
        
        # Company extraction from email domain
        if contact_info['identifiers'].get('email'):
            domain = contact_info['identifiers']['email'].split('@')[1]
            if domain and domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                contact_info['profile_data']['company_domain'] = domain
                contact_info['profile_data']['company'] = domain.split('.')[0].title()
        
        # Extract additional metadata
        contact_info['profile_data']['message_metadata'] = {
            'first_contact_channel': channel_type,
            'first_contact_date': datetime.now(timezone.utc).isoformat(),
            'message_id': message_data.get('id'),
            'thread_id': message_data.get('thread_id')
        }
        
        return contact_info
    
    async def _find_existing_contact(
        self,
        contact_info: Dict[str, Any],
        default_pipeline: Optional[Pipeline]
    ) -> Optional[Record]:
        """Find existing contact by identifiers"""
        
        if not default_pipeline:
            return None
        
        identifiers = contact_info.get('identifiers', {})
        
        # Search by email (most reliable)
        if identifiers.get('email'):
            contact = await sync_to_async(
                Record.objects.filter(
                    pipeline=default_pipeline,
                    data__email__iexact=identifiers['email'],
                    is_deleted=False
                ).first
            )()
            if contact:
                return contact
        
        # Search by phone
        if identifiers.get('phone'):
            # Normalize phone number for search
            normalized_phone = re.sub(r'[\s\-\(\)]', '', identifiers['phone'])
            
            contact = await sync_to_async(
                Record.objects.filter(
                    pipeline=default_pipeline,
                    data__phone__icontains=normalized_phone[-10:],  # Last 10 digits
                    is_deleted=False
                ).first
            )()
            if contact:
                return contact
        
        # Search by LinkedIn URL
        if identifiers.get('linkedin_url'):
            contact = await sync_to_async(
                Record.objects.filter(
                    pipeline=default_pipeline,
                    data__linkedin_url__icontains=identifiers['linkedin_url'],
                    is_deleted=False
                ).first
            )()
            if contact:
                return contact
        
        return None
    
    async def _create_new_contact(
        self,
        contact_info: Dict[str, Any],
        message_data: Dict[str, Any],
        tenant_config,
        created_by_user: User
    ) -> Record:
        """Create new contact record"""
        
        if not tenant_config.default_contact_pipeline:
            raise ValueError("No default contact pipeline configured")
        
        # Prepare contact data
        contact_data = contact_info.get('profile_data', {}).copy()
        
        # Add default status from tenant config
        if tenant_config.default_contact_status:
            contact_data['status'] = tenant_config.default_contact_status
        
        # Add source tracking
        contact_data['source'] = contact_info.get('source', 'auto_created')
        contact_data['created_from_communication'] = True
        contact_data['auto_created_at'] = datetime.now(timezone.utc).isoformat()
        
        # Add tags
        tags = contact_data.get('tags', [])
        tags.extend(['auto-created', f'from-{contact_info.get("source", "unknown")}'])
        contact_data['tags'] = list(set(tags))
        
        # Create the record
        async with sync_to_async(transaction.atomic)():
            contact = await sync_to_async(Record.objects.create)(
                pipeline=tenant_config.default_contact_pipeline,
                data=contact_data,
                created_by=created_by_user
            )
        
        logger.info(f"Auto-created contact {contact.id} from {contact_info.get('source')}")
        
        return contact
    
    async def _update_existing_contact(
        self,
        contact: Record,
        contact_info: Dict[str, Any],
        message_data: Dict[str, Any]
    ) -> Record:
        """Update existing contact with new information"""
        
        profile_data = contact_info.get('profile_data', {})
        updated_fields = []
        
        # Update empty fields with new data
        for key, value in profile_data.items():
            if key not in contact.data or not contact.data[key]:
                contact.data[key] = value
                updated_fields.append(key)
        
        # Update communication metadata
        if 'communication_history' not in contact.data:
            contact.data['communication_history'] = []
        
        contact.data['communication_history'].append({
            'channel': contact_info.get('source', 'unknown'),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'message_id': message_data.get('id'),
            'updated_fields': updated_fields
        })
        
        # Update last contact date
        contact.data['last_contact_date'] = datetime.now(timezone.utc).isoformat()
        
        if updated_fields:
            await sync_to_async(contact.save)()
            logger.info(f"Updated contact {contact.id} with fields: {updated_fields}")
        
        contact_info['updated_fields'] = updated_fields
        return contact
    
    def _select_best_participant(self, participants: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Select the best participant for contact creation"""
        
        if not participants:
            return None
        
        # Score participants based on data completeness
        scored_participants = []
        
        for participant in participants:
            score = 0
            
            # Email gets highest score
            if participant.get('email') and self.email_pattern.match(participant['email']):
                score += 10
            
            # Name adds to score
            if participant.get('name'):
                score += 5
            
            # Phone adds to score
            if participant.get('phone') and self.phone_pattern.match(participant['phone']):
                score += 3
            
            # LinkedIn profile adds to score
            if participant.get('linkedin_url'):
                score += 2
            
            # Company info adds to score
            if participant.get('company'):
                score += 1
            
            if score > 0:
                scored_participants.append((score, participant))
        
        if scored_participants:
            # Return participant with highest score
            scored_participants.sort(key=lambda x: x[0], reverse=True)
            return scored_participants[0][1]
        
        # Fallback to first participant
        return participants[0]
    
    def _calculate_contact_similarity(self, contact1: Record, contact2: Record) -> float:
        """Calculate similarity score between two contacts"""
        
        similarity_score = 0.0
        comparisons = 0
        
        data1 = contact1.data
        data2 = contact2.data
        
        # Email comparison (highest weight)
        if data1.get('email') and data2.get('email'):
            if data1['email'].lower() == data2['email'].lower():
                similarity_score += 0.4
            comparisons += 1
        
        # Phone comparison
        if data1.get('phone') and data2.get('phone'):
            phone1 = re.sub(r'[\s\-\(\)]', '', data1['phone'])
            phone2 = re.sub(r'[\s\-\(\)]', '', data2['phone'])
            
            if phone1[-10:] == phone2[-10:]:  # Compare last 10 digits
                similarity_score += 0.3
            comparisons += 1
        
        # Name comparison
        if data1.get('name') and data2.get('name'):
            name1 = data1['name'].lower().strip()
            name2 = data2['name'].lower().strip()
            
            if name1 == name2:
                similarity_score += 0.2
            elif self._names_similar(name1, name2):
                similarity_score += 0.1
            comparisons += 1
        
        # Company comparison
        if data1.get('company') and data2.get('company'):
            company1 = data1['company'].lower().strip()
            company2 = data2['company'].lower().strip()
            
            if company1 == company2:
                similarity_score += 0.1
            comparisons += 1
        
        # Return average similarity if we have comparisons
        return similarity_score / max(comparisons, 1) if comparisons > 0 else 0.0
    
    def _names_similar(self, name1: str, name2: str) -> bool:
        """Check if two names are similar"""
        
        # Split names into parts
        parts1 = set(name1.split())
        parts2 = set(name2.split())
        
        # Check for common parts
        common_parts = parts1.intersection(parts2)
        
        # Similar if they share at least one significant part (length > 2)
        return any(len(part) > 2 for part in common_parts)
    
    async def _merge_duplicate_contacts(self, duplicate_group: Dict[str, Any]) -> Dict[str, Any]:
        """Merge duplicate contacts into primary contact"""
        
        try:
            primary = duplicate_group['primary_contact']
            duplicates = duplicate_group['duplicates']
            
            merged_data = primary.data.copy()
            merged_ids = [str(primary.id)]
            
            # Merge data from duplicates
            for dup_info in duplicates:
                duplicate = dup_info['contact']
                merged_ids.append(str(duplicate.id))
                
                # Merge non-empty fields
                for key, value in duplicate.data.items():
                    if value and (key not in merged_data or not merged_data[key]):
                        merged_data[key] = value
                
                # Mark duplicate as deleted
                duplicate.is_deleted = True
                duplicate.deleted_at = django_timezone.now()
                await sync_to_async(duplicate.save)()
            
            # Update primary contact with merged data
            merged_data['_merge_info'] = {
                'merged_contacts': merged_ids,
                'merged_at': datetime.now(timezone.utc).isoformat(),
                'merge_count': len(duplicates)
            }
            
            primary.data = merged_data
            await sync_to_async(primary.save)()
            
            return {
                'success': True,
                'primary_contact_id': str(primary.id),
                'merged_contact_ids': merged_ids[1:],
                'merge_count': len(duplicates)
            }
            
        except Exception as e:
            logger.error(f"Failed to merge duplicate contacts: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _enrich_from_clearbit(self, email: str) -> Dict[str, Any]:
        """Enrich contact data from Clearbit API"""
        # Placeholder for Clearbit integration
        # Would require Clearbit API key and proper implementation
        return {}
    
    async def _enrich_from_hunter(self, email: Optional[str], company: Optional[str]) -> Dict[str, Any]:
        """Enrich contact data from Hunter.io API"""
        # Placeholder for Hunter.io integration
        # Would require Hunter.io API key and proper implementation
        return {}
    
    async def _enrich_from_linkedin(self, linkedin_url: str) -> Dict[str, Any]:
        """Enrich contact data from LinkedIn"""
        # Placeholder for LinkedIn integration
        # Would require LinkedIn API access and proper implementation
        return {}


# Global contact resolver instance
contact_resolver = ContactResolutionService()