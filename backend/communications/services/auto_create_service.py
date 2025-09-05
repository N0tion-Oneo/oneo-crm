"""
Service for automatic contact creation from participants
"""
import re
import logging
from typing import Tuple, Dict, Any, List, Optional
from datetime import timedelta

from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model

from pipelines.models import Record, Pipeline
from communications.models import (
    Participant, 
    ParticipantSettings, 
    ParticipantBlacklist,
    ParticipantOverride,
    ChannelParticipantSettings
)
from communications.services.participant_management import ParticipantManagementService
from communications.record_communications.services.identifier_extractor import RecordIdentifierExtractor

logger = logging.getLogger(__name__)
User = get_user_model()


class AutoCreateContactService:
    """
    Service for automatic contact creation from participants
    Handles blacklist checking, duplicate detection, and company linking
    """
    
    # Personal email domains to exclude from company creation
    PERSONAL_EMAIL_DOMAINS = [
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 
        'icloud.com', 'me.com', 'aol.com', 'msn.com', 'live.com',
        'mail.com', 'protonmail.com', 'yandex.com', 'zoho.com'
    ]
    
    # Role-based email prefixes to exclude
    ROLE_EMAIL_PREFIXES = [
        'info', 'support', 'help', 'admin', 'noreply', 'no-reply',
        'donotreply', 'sales', 'billing', 'contact', 'hello',
        'team', 'notifications', 'alerts', 'system', 'automated'
    ]
    
    def __init__(self, tenant=None):
        """Initialize the service with tenant settings"""
        self.settings = ParticipantSettings.get_or_create_for_tenant()
        self.blacklist_cache = {}
        self.participant_service = ParticipantManagementService(tenant)
        self.identifier_extractor = RecordIdentifierExtractor()
        self._load_blacklist_cache()
        self.creation_count_cache_key = f"auto_create_count_{tenant.id if tenant else 'default'}"
    
    def _load_blacklist_cache(self):
        """Load active blacklist entries into cache for performance"""
        blacklist_entries = ParticipantBlacklist.objects.filter(is_active=True)
        for entry in blacklist_entries:
            if entry.entry_type not in self.blacklist_cache:
                self.blacklist_cache[entry.entry_type] = []
            self.blacklist_cache[entry.entry_type].append(entry.value.lower())
    
    def should_auto_create(self, participant: Participant) -> Tuple[bool, str]:
        """
        Check if participant should trigger auto-creation
        
        Returns:
            Tuple of (should_create: bool, reason: str)
        """
        # Check master enable
        if not self.settings.auto_create_enabled:
            return False, "Auto-creation disabled"
        
        # Check if already linked
        if participant.contact_record:
            return False, "Already linked to contact"
        
        # Check override settings
        if hasattr(participant, 'override_settings'):
            override = participant.override_settings
            if override.never_auto_create:
                return False, "Participant has never_auto_create override"
            if override.always_auto_create:
                return True, "Participant has always_auto_create override"
        
        # Check rate limiting
        if not self.check_rate_limit():
            return False, f"Rate limit exceeded ({self.settings.max_creates_per_hour}/hour)"
        
        # Check blacklist
        if self.is_blacklisted(participant):
            return False, "Participant is blacklisted"
        
        # Check role-based email exclusion
        if self.is_role_email(participant.email):
            return False, "Role-based email address"
        
        # Check minimum messages
        if participant.total_messages < self.settings.min_messages_before_create:
            return False, f"Only {participant.total_messages} messages, need {self.settings.min_messages_before_create}"
        
        # Check required fields
        if self.settings.require_email and not participant.email:
            return False, "Email required but not present"
        
        if self.settings.require_phone and not participant.phone:
            return False, "Phone required but not present"
        
        # Check channel-specific settings
        channel_eligible, channel_reason = self.check_channel_eligibility(participant)
        if not channel_eligible:
            return False, channel_reason
        
        # Check creation delay
        if self.settings.creation_delay_hours > 0:
            min_time = timezone.now() - timedelta(hours=self.settings.creation_delay_hours)
            if participant.first_seen > min_time:
                return False, f"Participant too new, waiting {self.settings.creation_delay_hours} hours"
        
        return True, "Eligible for auto-creation"
    
    def is_blacklisted(self, participant: Participant) -> bool:
        """Check if participant matches any blacklist entry"""
        
        # Check email blacklist
        if participant.email:
            email_lower = participant.email.lower()
            
            # Check exact email match
            if 'email' in self.blacklist_cache:
                if email_lower in self.blacklist_cache['email']:
                    logger.info(f"Participant {participant.id} blacklisted by email: {email_lower}")
                    return True
            
            # Check domain
            if '@' in email_lower:
                domain = email_lower.split('@')[-1]
                if 'domain' in self.blacklist_cache:
                    if domain in self.blacklist_cache['domain']:
                        logger.info(f"Participant {participant.id} blacklisted by domain: {domain}")
                        return True
            
            # Check email patterns
            if 'email_pattern' in self.blacklist_cache:
                for pattern in self.blacklist_cache['email_pattern']:
                    if self.matches_pattern(email_lower, pattern):
                        logger.info(f"Participant {participant.id} blacklisted by email pattern: {pattern}")
                        return True
        
        # Check phone blacklist
        if participant.phone and 'phone' in self.blacklist_cache:
            phone_normalized = re.sub(r'[^0-9]', '', participant.phone)
            for blacklisted_phone in self.blacklist_cache['phone']:
                blacklisted_normalized = re.sub(r'[^0-9]', '', blacklisted_phone)
                if phone_normalized == blacklisted_normalized:
                    logger.info(f"Participant {participant.id} blacklisted by phone: {participant.phone}")
                    return True
        
        # Check name patterns
        if participant.name and 'name_pattern' in self.blacklist_cache:
            name_lower = participant.name.lower()
            for pattern in self.blacklist_cache['name_pattern']:
                if self.matches_pattern(name_lower, pattern):
                    logger.info(f"Participant {participant.id} blacklisted by name pattern: {pattern}")
                    return True
        
        return False
    
    def is_role_email(self, email: str) -> bool:
        """Check if email is a role-based address"""
        if not email:
            return False
        
        email_lower = email.lower()
        local_part = email_lower.split('@')[0]
        
        for prefix in self.ROLE_EMAIL_PREFIXES:
            if local_part == prefix or local_part.startswith(f"{prefix}@"):
                return True
        
        return False
    
    def matches_pattern(self, text: str, pattern: str) -> bool:
        """Check if text matches a pattern (supports wildcards)"""
        # Convert wildcard pattern to regex
        regex_pattern = pattern.replace('*', '.*').replace('?', '.')
        try:
            return bool(re.match(f"^{regex_pattern}$", text, re.IGNORECASE))
        except re.error:
            logger.error(f"Invalid pattern: {pattern}")
            return False
    
    def check_rate_limit(self) -> bool:
        """
        Check if we're within the rate limit for auto-creation
        
        Returns:
            True if within rate limit, False otherwise
        """
        if self.settings.max_creates_per_hour <= 0:
            return True  # No rate limit
        
        from django.core.cache import cache
        
        # Get current hour's count
        current_count = cache.get(self.creation_count_cache_key, 0)
        
        if current_count >= self.settings.max_creates_per_hour:
            logger.warning(f"Rate limit reached: {current_count}/{self.settings.max_creates_per_hour} creates this hour")
            return False
        
        return True
    
    def increment_creation_count(self):
        """Increment the creation count for rate limiting"""
        from django.core.cache import cache
        
        # Get current count
        current_count = cache.get(self.creation_count_cache_key, 0)
        
        # Increment with 1 hour expiry
        cache.set(self.creation_count_cache_key, current_count + 1, 3600)
    
    def is_two_way_conversation(self, participant: Participant) -> bool:
        """
        Check if participant has both sent and received messages
        
        Args:
            participant: The participant to check
            
        Returns:
            True if conversation is two-way, False otherwise
        """
        from communications.models import Message, Conversation
        
        # Get conversations involving this participant
        conversations = Conversation.objects.filter(conversation_participants__participant=participant)
        
        for conversation in conversations:
            # Check if there are both inbound and outbound messages
            messages = Message.objects.filter(conversation=conversation)
            
            has_inbound = messages.filter(direction='inbound').exists()
            has_outbound = messages.filter(direction='outbound').exists()
            
            if has_inbound and has_outbound:
                return True
        
        return False
    
    def check_channel_eligibility(self, participant: Participant) -> Tuple[bool, str]:
        """Check channel-specific eligibility rules"""
        
        # Determine participant's primary channel
        channel_type = None
        if participant.email:
            channel_type = 'email'
        elif participant.phone:
            channel_type = 'whatsapp'
        elif participant.linkedin_member_urn:
            channel_type = 'linkedin'
        
        if not channel_type:
            return True, "No specific channel identified"
        
        # Check channel-specific settings
        try:
            channel_settings = ChannelParticipantSettings.objects.get(
                settings=self.settings,
                channel_type=channel_type
            )
            
            if not channel_settings.enabled:
                return False, f"Auto-creation disabled for {channel_type}"
            
            if participant.total_messages < channel_settings.min_messages:
                return False, f"Need {channel_settings.min_messages} messages for {channel_type}"
            
            if channel_settings.require_two_way:
                # Check if conversation is two-way
                if not self.is_two_way_conversation(participant):
                    return False, f"Two-way conversation required for {channel_type}"
            
        except ChannelParticipantSettings.DoesNotExist:
            # No specific settings for this channel, use defaults
            pass
        
        return True, "Channel eligible"
    
    def check_for_duplicates(self, participant: Participant) -> Optional[Record]:
        """
        Check if a matching contact already exists using the duplicate detection system
        
        Returns:
            Existing Record if duplicate found, None otherwise
        """
        if not self.settings.check_duplicates_before_create:
            return None
        
        # Get the pipeline to check against
        pipeline = self.settings.default_contact_pipeline
        if not pipeline:
            return None
        
        # Build the record data that would be created
        # This uses the participant service to get proper field mappings
        field_mappings = self.participant_service.preview_field_mapping(
            participant, 
            pipeline
        )
        
        # Build data dict from field mappings
        new_record_data = {}
        for mapping in field_mappings:
            if mapping['has_value'] and mapping['is_valid']:
                new_record_data[mapping['field_slug']] = mapping['formatted_value']
        
        if not new_record_data:
            # No data to check against
            return None
        
        # Import duplicate detection components
        from duplicates.models import DuplicateRule
        from duplicates.logic_engine import DuplicateLogicEngine
        from django.db import connection
        from tenants.models import Tenant
        
        # Get tenant context
        try:
            if not hasattr(connection, 'tenant') or not connection.tenant:
                logger.debug("No tenant context found, skipping duplicate checking")
                return None
            
            tenant_schema = connection.tenant.schema_name
            if tenant_schema == 'public':
                return None
                
            tenant = Tenant.objects.get(schema_name=tenant_schema)
        except Exception as e:
            logger.error(f"Error getting tenant context: {e}")
            return None
        
        # Get active duplicate rules for this pipeline
        rules = DuplicateRule.objects.filter(
            tenant=tenant,
            pipeline=pipeline,
            is_active=True
        )
        
        if not rules:
            return None
        
        # Initialize the logic engine
        engine = DuplicateLogicEngine(tenant_id=tenant.id)
        
        # For performance, first try to narrow down potential duplicates using database queries
        # This is much faster than checking every record
        from django.db.models import Q
        
        # Build a query to find potential duplicates based on key fields
        potential_query = Q()
        
        # Check for email fields
        if participant.email:
            # Find fields that might contain this email
            for field_slug in ['personal_email', 'email_address', 'work_email', 'email']:
                potential_query |= Q(data__contains={field_slug: participant.email})
        
        # Check for phone fields  
        if participant.phone:
            # Find fields that might contain this phone
            for field_slug in ['phone_number', 'mobile_phone', 'phone']:
                potential_query |= Q(data__contains={field_slug: participant.phone})
        
        # Check for LinkedIn
        if participant.linkedin_member_urn:
            for field_slug in ['linkedin', 'linkedin_url']:
                potential_query |= Q(data__contains={field_slug: participant.linkedin_member_urn})
        
        # Get potential duplicates - this narrows down the search significantly
        if potential_query:
            potential_duplicates = Record.objects.filter(pipeline=pipeline).filter(potential_query)
        else:
            # No identifiers to check, check recent records only
            potential_duplicates = Record.objects.filter(pipeline=pipeline).order_by('-created_at')[:100]
        
        # Now check these potential duplicates with the duplicate detection engine
        for existing_record in potential_duplicates:
            for rule in rules:
                try:
                    # Use the duplicate detection engine to check if it's a duplicate
                    # We pass the new record data and existing record data
                    is_duplicate = engine.evaluate_rule(
                        rule=rule,
                        record1_data=new_record_data,
                        record2_data=existing_record.data
                    )
                    
                    if is_duplicate:
                        logger.info(f"Found duplicate record {existing_record.id} for participant {participant.id} using rule {rule.name}")
                        return existing_record
                        
                except Exception as e:
                    logger.error(f"Error evaluating duplicate rule {rule.name}: {e}")
                    continue
        
        return None
    
    def create_contact_from_participant(
        self,
        participant: Participant,
        user: Optional[User] = None,
        force: bool = False
    ) -> Record:
        """
        Create contact record from participant
        
        Args:
            participant: The participant to create a contact from
            user: User performing the creation (optional)
            force: Force creation even if not eligible
            
        Returns:
            Created Record instance
            
        Raises:
            ValueError: If participant is not eligible for creation
        """
        # Check eligibility unless forced
        if not force:
            should_create, reason = self.should_auto_create(participant)
            if not should_create:
                raise ValueError(f"Cannot auto-create: {reason}")
        
        # Check for duplicates
        existing = self.check_for_duplicates(participant)
        if existing:
            # Link to existing record instead of creating new
            logger.info(f"Found existing record {existing.id} for participant {participant.id}")
            participant.contact_record = existing
            participant.resolution_confidence = self.settings.duplicate_confidence_threshold
            participant.resolution_method = 'duplicate_match'
            participant.resolved_at = timezone.now()
            participant.save()
            return existing
        
        # Get or validate pipeline
        pipeline = self.settings.default_contact_pipeline
        if not pipeline:
            # Try to find a contacts pipeline
            try:
                pipeline = Pipeline.objects.get(slug='contacts')
            except Pipeline.DoesNotExist:
                raise ValueError("No default contact pipeline configured")
        
        # Ensure we have a user for creation
        if not user:
            raise ValueError("User is required for record creation")
        
        # Create the record
        with transaction.atomic():
            record = self.participant_service.create_record_from_participant(
                participant=participant,
                pipeline=pipeline,
                user=user,
                link_conversations=True
            )
            
            logger.info(f"Created contact record {record.id} from participant {participant.id}")
            
            # Increment creation count for rate limiting
            self.increment_creation_count()
            
            # Handle company linking if enabled
            if self.settings.auto_link_by_domain and participant.email:
                self.link_to_company(participant, record, user=user)
            
            return record
    
    def link_to_company(self, participant: Participant, contact_record: Optional[Record] = None, user: Optional[User] = None):
        """
        Link participant to company based on email domain
        
        Args:
            participant: The participant to link
            contact_record: The contact record (optional)
            user: User performing the operation
        """
        if not participant.email:
            return
        
        email_lower = participant.email.lower()
        domain = email_lower.split('@')[-1]
        
        # Skip personal domains
        if domain in self.PERSONAL_EMAIL_DOMAINS:
            logger.debug(f"Skipping personal domain: {domain}")
            return
        
        # Skip if already has secondary record
        if participant.secondary_record:
            return
        
        # Find existing company by domain
        company_records = self.identifier_extractor.find_company_records_by_domain(
            domain=domain,
            pipeline_slugs=['companies', 'organizations', 'accounts']
        )
        
        if company_records:
            # Link to existing company
            company = company_records[0]
            participant.secondary_record = company
            participant.secondary_confidence = 0.9
            participant.secondary_resolution_method = 'domain_match'
            participant.save()
            logger.info(f"Linked participant {participant.id} to company {company.id} via domain {domain}")
            
        elif self.settings.create_company_if_missing:
            # Check if we have enough employees to create company
            employee_count = Participant.objects.filter(
                email__iendswith=f'@{domain}'
            ).exclude(id=participant.id).count()
            
            if employee_count >= (self.settings.min_employees_for_company - 1):
                # Create company record
                company = self.create_company_from_domain(domain, participant, user=user)
                if company:
                    # Link all participants with this domain
                    participants_to_link = Participant.objects.filter(
                        email__iendswith=f'@{domain}',
                        secondary_record__isnull=True
                    )
                    for p in participants_to_link:
                        p.secondary_record = company
                        p.secondary_confidence = 0.8
                        p.secondary_resolution_method = 'domain_match_auto'
                        p.save()
                    
                    logger.info(f"Created company {company.id} for domain {domain} and linked {participants_to_link.count()} participants")
    
    def create_company_from_domain(self, domain: str, participant: Participant, user: Optional[User] = None) -> Optional[Record]:
        """
        Create a company record from domain
        
        Args:
            domain: The email domain
            participant: Sample participant from this company
            user: User performing the operation
            
        Returns:
            Created company Record or None
        """
        if not self.settings.default_company_pipeline:
            logger.warning("No default company pipeline configured")
            return None
        
        # Extract company name from domain
        company_name = domain.split('.')[0].title()
        
        # Create a temporary participant-like object for field mapping
        # This allows us to use the existing field mapping logic
        from types import SimpleNamespace
        temp_participant = SimpleNamespace(
            email=f"info@{domain}",  # Use a generic email for the domain
            name=company_name,
            phone=None,
            secondary_record=None
        )
        
        # Use participant service to get proper field mappings
        pipeline = self.settings.default_company_pipeline
        field_purposes = self.participant_service.get_identifying_fields_from_duplicate_rules(pipeline)
        
        # Build company data using field mappings
        company_data = {}
        
        # Map company name to the configured field
        if self.settings.company_name_field:
            company_data[self.settings.company_name_field] = company_name
        
        # Map other fields using the participant service logic
        for field in pipeline.fields.filter(is_deleted=False):
            # Get value for this field (will use duplicate rule identified fields)
            value = self.participant_service._get_participant_value_for_field(
                temp_participant, 
                field, 
                field_purposes,
                is_secondary=True  # This is for a secondary (company) record
            )
            
            if value is not None:
                # Format the value according to field type
                formatted_value = self.participant_service._format_value_for_field(value, field)
                if formatted_value is not None:
                    company_data[field.slug] = formatted_value
        
        # Check for existing company with duplicate detection before creating
        if self.settings.check_duplicates_before_create and company_data:
            from duplicates.models import DuplicateRule
            from duplicates.logic_engine import DuplicateLogicEngine
            from django.db import connection
            from tenants.models import Tenant
            
            try:
                # Get tenant context
                if hasattr(connection, 'tenant') and connection.tenant:
                    tenant_schema = connection.tenant.schema_name
                    if tenant_schema != 'public':
                        tenant = Tenant.objects.get(schema_name=tenant_schema)
                        
                        # Get duplicate rules for company pipeline
                        rules = DuplicateRule.objects.filter(
                            tenant=tenant,
                            pipeline=pipeline,
                            is_active=True
                        )
                        
                        if rules:
                            # Initialize the logic engine
                            engine = DuplicateLogicEngine(tenant_id=tenant.id)
                            
                            # Check for existing companies with this domain
                            # Use domain/URL fields for quick filtering
                            from django.db.models import Q
                            potential_query = Q()
                            
                            # Look for domain in common fields
                            for field_slug in ['domain', 'company_website', 'website', 'url']:
                                if field_slug in company_data:
                                    potential_query |= Q(data__contains={field_slug: company_data[field_slug]})
                            
                            # Also check by company name
                            if self.settings.company_name_field and company_name:
                                potential_query |= Q(data__contains={self.settings.company_name_field: company_name})
                            
                            if potential_query:
                                potential_duplicates = Record.objects.filter(
                                    pipeline=pipeline
                                ).filter(potential_query)
                                
                                # Check each potential duplicate
                                for existing_record in potential_duplicates:
                                    for rule in rules:
                                        try:
                                            is_duplicate = engine.evaluate_rule(
                                                rule=rule,
                                                record1_data=company_data,
                                                record2_data=existing_record.data
                                            )
                                            
                                            if is_duplicate:
                                                logger.info(f"Found existing company record {existing_record.id} for domain {domain}")
                                                return existing_record
                                                
                                        except Exception as e:
                                            logger.error(f"Error checking company duplicate: {e}")
                                            continue
                                            
            except Exception as e:
                logger.error(f"Error in company duplicate checking: {e}")
                # Continue with creation if duplicate check fails
        
        try:
            with transaction.atomic():
                company = Record.objects.create(
                    pipeline=pipeline,
                    title=company_name,
                    data=company_data,
                    created_by=user,  # Use the provided user
                    updated_by=user  # Also set updated_by
                )
                
                logger.info(f"Created company record {company.id} for domain {domain} with data: {company_data}")
                return company
                
        except Exception as e:
            logger.error(f"Failed to create company for domain {domain}: {e}")
            return None
    
    def process_batch(self, batch_size: Optional[int] = None, user: Optional[User] = None) -> Dict[str, int]:
        """
        Process batch of participants for auto-creation
        
        Args:
            batch_size: Number of participants to process (uses settings default if None)
            user: User performing the batch operation
            
        Returns:
            Dictionary with results: created, skipped, errors
        """
        batch_size = batch_size or self.settings.batch_size
        
        # Find eligible participants
        eligible = Participant.objects.filter(
            contact_record__isnull=True
        ).exclude(
            override_settings__never_auto_create=True
        ).order_by('first_seen')[:batch_size]
        
        results = {
            'created': 0,
            'contacts_created': 0,
            'companies_created': 0,
            'companies_linked': 0,
            'skipped': 0,
            'errors': 0,
            'duplicates': 0
        }
        
        for participant in eligible:
            try:
                should_create, reason = self.should_auto_create(participant)
                if should_create:
                    # Track company state before creation
                    had_company_before = participant.secondary_record is not None
                    
                    record = self.create_contact_from_participant(participant, user=user)
                    if record:
                        results['created'] += 1
                        results['contacts_created'] += 1
                        
                        # Reload participant to get updated secondary_record
                        participant.refresh_from_db()
                        
                        # Check if company was created or linked
                        if participant.secondary_record and not had_company_before:
                            # Check if it was newly created vs existing
                            # We'll check by seeing if the company was created in the last minute
                            from django.utils import timezone
                            from datetime import timedelta
                            recent_threshold = timezone.now() - timedelta(minutes=1)
                            if participant.secondary_record.created_at >= recent_threshold:
                                results['companies_created'] += 1
                            else:
                                results['companies_linked'] += 1
                else:
                    logger.debug(f"Skipping participant {participant.id}: {reason}")
                    results['skipped'] += 1
                    
            except ValueError as e:
                if 'duplicate' in str(e).lower():
                    results['duplicates'] += 1
                else:
                    results['skipped'] += 1
                logger.debug(f"Skipping participant {participant.id}: {e}")
                
            except Exception as e:
                logger.error(f"Error creating contact for participant {participant.id}: {e}")
                results['errors'] += 1
        
        logger.info(f"Batch processing complete: {results}")
        return results
    
    def get_creation_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get statistics about auto-creation performance
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with statistics
        """
        since = timezone.now() - timedelta(days=days)
        
        # Count participants created in timeframe
        auto_created = Participant.objects.filter(
            resolved_at__gte=since,
            resolution_method__in=['auto_creation', 'duplicate_match']
        ).count()
        
        # Count blacklisted
        blacklist_count = ParticipantBlacklist.objects.filter(
            is_active=True
        ).count()
        
        # Count overrides
        override_count = ParticipantOverride.objects.filter(
            never_auto_create=True
        ).count()
        
        # Count unlinked
        unlinked = Participant.objects.filter(
            contact_record__isnull=True
        ).count()
        
        return {
            'auto_created': auto_created,
            'blacklist_entries': blacklist_count,
            'override_count': override_count,
            'unlinked_participants': unlinked,
            'period_days': days
        }