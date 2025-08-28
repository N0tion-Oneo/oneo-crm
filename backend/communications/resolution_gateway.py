"""
Contact Resolution Gateway for Selective Communication Storage
Uses duplicate detection system to identify contacts before storing communications
"""
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from django.core.cache import cache
from django.db.models import Q
from asgiref.sync import sync_to_async

from pipelines.models import Pipeline, Record, Field
from duplicates.logic_engine import DuplicateLogicEngine, FieldMatcher
from duplicates.models import DuplicateRule
from tenants.models import Tenant

logger = logging.getLogger(__name__)


class ContactResolutionGateway:
    """
    Gateway for resolving contacts using duplicate detection before storage
    """
    
    # Confidence thresholds
    HIGH_CONFIDENCE = 0.9
    MEDIUM_CONFIDENCE = 0.7
    LOW_CONFIDENCE = 0.5
    
    def __init__(self, tenant: Optional[Tenant] = None):
        """
        Initialize the resolution gateway
        
        Args:
            tenant: Current tenant for multi-tenant isolation
        """
        self.tenant = tenant
        self.tenant_id = tenant.id if tenant else None
        self.logic_engine = DuplicateLogicEngine(self.tenant_id)
        self.field_matcher = FieldMatcher(self.tenant_id)
        
        # Cache settings
        self.cache_ttl = 3600  # 1 hour cache
        self.cache_prefix = f"contact_resolution_{self.tenant_id}_" if self.tenant_id else "contact_resolution_"
    
    async def resolve_contact(
        self,
        identifiers: Dict[str, Any],
        pipelines: Optional[List[Pipeline]] = None,
        min_confidence: float = MEDIUM_CONFIDENCE
    ) -> Dict[str, Any]:
        """
        Resolve a contact using identifiers
        
        Args:
            identifiers: Dict with email, phone, linkedin_url, domain, etc.
            pipelines: List of pipelines to search (defaults to all contact-type pipelines)
            min_confidence: Minimum confidence score to consider a match
            
        Returns:
            Dict with:
                - found: bool
                - record: Record object if found
                - confidence: float confidence score
                - match_details: Dict with matching field details
                - pipeline: Pipeline object if found
        """
        
        # Check cache first
        cache_key = self._get_cache_key(identifiers)
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for identifiers: {identifiers}")
            return cached_result
        
        # Get pipelines to search
        if not pipelines:
            pipelines = await self._get_contact_pipelines()
        
        best_match = None
        best_confidence = 0.0
        match_details = {}
        
        for pipeline in pipelines:
            # Search for records using identifiers
            records = await self._search_records(pipeline, identifiers)
            
            for record in records:
                # Calculate confidence score
                confidence, details = await self._calculate_confidence(
                    record, identifiers, pipeline
                )
                
                if confidence > best_confidence and confidence >= min_confidence:
                    best_confidence = confidence
                    best_match = record
                    match_details = details
                    
                    # Short circuit on high confidence match
                    if confidence >= self.HIGH_CONFIDENCE:
                        break
            
            if best_confidence >= self.HIGH_CONFIDENCE:
                break
        
        result = {
            'found': best_match is not None,
            'record': best_match,
            'confidence': best_confidence,
            'match_details': match_details,
            'pipeline': best_match.pipeline if best_match else None,
            'resolution_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Cache the result
        if result['found']:
            cache.set(cache_key, result, self.cache_ttl)
        
        return result
    
    async def resolve_from_message(
        self,
        message_data: Dict[str, Any],
        channel_type: str
    ) -> Dict[str, Any]:
        """
        Resolve contact from message data (email, WhatsApp, etc.)
        
        Args:
            message_data: Message data from UniPile or other source
            channel_type: Type of communication channel
            
        Returns:
            Resolution result dict
        """
        
        # Extract identifiers from message
        identifiers = await self._extract_identifiers(message_data, channel_type)
        
        if not identifiers:
            return {
                'found': False,
                'confidence': 0.0,
                'error': 'No valid identifiers found in message'
            }
        
        # Resolve using identifiers
        return await self.resolve_contact(identifiers)
    
    async def batch_resolve(
        self,
        identifier_list: List[Dict[str, Any]],
        max_concurrent: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Resolve multiple contacts in batch
        
        Args:
            identifier_list: List of identifier dicts
            max_concurrent: Max concurrent resolutions
            
        Returns:
            List of resolution results
        """
        import asyncio
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def resolve_single(identifiers):
            async with semaphore:
                return await self.resolve_contact(identifiers)
        
        tasks = [resolve_single(ids) for ids in identifier_list]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def should_store_communication(
        self,
        message_data: Dict[str, Any],
        channel_type: str,
        auto_threshold: float = MEDIUM_CONFIDENCE
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Determine if a communication should be stored based on contact resolution
        
        Args:
            message_data: Message data from communication channel
            channel_type: Type of channel (email, whatsapp, etc.)
            auto_threshold: Confidence threshold for automatic storage
            
        Returns:
            Tuple of (should_store, resolution_details)
        """
        
        # Resolve contact from message
        resolution = await self.resolve_from_message(message_data, channel_type)
        
        # Determine storage decision
        should_store = resolution.get('found', False) and \
                      resolution.get('confidence', 0) >= auto_threshold
        
        # Add storage metadata
        resolution['storage_decision'] = {
            'should_store': should_store,
            'reason': self._get_storage_reason(resolution, auto_threshold),
            'threshold_used': auto_threshold,
            'channel_type': channel_type
        }
        
        return should_store, resolution
    
    async def _get_contact_pipelines(self) -> List[Pipeline]:
        """Get pipelines that likely contain contact records"""
        
        # Get pipelines with contact-like names or types
        pipelines = await sync_to_async(list)(
            Pipeline.objects.filter(
                Q(name__icontains='contact') |
                Q(name__icontains='people') |
                Q(name__icontains='person') |
                Q(name__icontains='customer') |
                Q(name__icontains='account') |
                Q(name__icontains='company'),
                is_active=True
            )
        )
        
        # If no contact-specific pipelines, get all pipelines
        if not pipelines:
            pipelines = await sync_to_async(list)(
                Pipeline.objects.filter(
                    is_active=True
                )
            )
        
        return pipelines
    
    async def _search_records(
        self,
        pipeline: Pipeline,
        identifiers: Dict[str, Any]
    ) -> List[Record]:
        """Search for records matching identifiers using duplicate detection rules"""
        
        # Get duplicate rules for this pipeline
        rules = await sync_to_async(list)(
            DuplicateRule.objects.filter(
                pipeline=pipeline,
                is_active=True,
                action_on_duplicate='detect_only'
            )
        )
        
        # If no rules, use dynamic field detection
        if not rules:
            return await self._search_records_by_field_type(pipeline, identifiers)
        
        # Build query from duplicate rules
        query = Q()
        
        for rule in rules:
            rule_logic = rule.logic or {}
            
            # Process AND groups
            for and_group in rule_logic.get('and_groups', []):
                group_query = Q()
                for field_rule in and_group.get('fields', []):
                    field_name = field_rule.get('field')
                    match_type = field_rule.get('match_type', 'exact')
                    
                    # Map identifiers to field rules
                    if identifiers.get('email') and 'email' in field_name.lower():
                        email = identifiers['email'].lower()
                        if match_type == 'exact':
                            group_query &= Q(**{f'data__{field_name}__iexact': email})
                        else:
                            group_query &= Q(**{f'data__{field_name}__icontains': email})
                    
                    elif identifiers.get('phone') and 'phone' in field_name.lower():
                        phone_digits = re.sub(r'[^\d]', '', identifiers['phone'])[-10:]
                        group_query &= Q(**{f'data__{field_name}__icontains': phone_digits})
                    
                    elif identifiers.get('name') and 'name' in field_name.lower():
                        name = identifiers['name']
                        if match_type == 'fuzzy':
                            group_query &= Q(**{f'data__{field_name}__icontains': name.split()[0]})
                        else:
                            group_query &= Q(**{f'data__{field_name}__iexact': name})
                
                if group_query:
                    query |= group_query
        
        if not query:
            # Fallback to field type detection
            return await self._search_records_by_field_type(pipeline, identifiers)
        
        records = await sync_to_async(list)(
            Record.objects.filter(
                pipeline=pipeline,
                is_deleted=False
            ).filter(query)[:20]  # Increased limit for better matching
        )
        
        return records
    
    async def _search_records_by_field_type(
        self,
        pipeline: Pipeline,
        identifiers: Dict[str, Any]
    ) -> List[Record]:
        """Fallback search using field type detection"""
        
        # Get fields from pipeline
        fields = await sync_to_async(list)(
            Field.objects.filter(pipeline=pipeline, is_deleted=False)
        )
        
        query = Q()
        
        # Email search - find all email type fields
        if identifiers.get('email'):
            email = identifiers['email'].lower()
            email_fields = [f.name for f in fields if f.field_type == 'email' or 'email' in f.name.lower()]
            
            for field_name in email_fields:
                query |= Q(**{f'data__{field_name}__iexact': email})
        
        # Phone search - find all phone type fields
        if identifiers.get('phone'):
            phone_digits = re.sub(r'[^\d]', '', identifiers['phone'])[-10:]
            phone_fields = [f.name for f in fields if f.field_type == 'phone' or 'phone' in f.name.lower()]
            
            for field_name in phone_fields:
                query |= Q(**{f'data__{field_name}__icontains': phone_digits})
        
        # Name search - find name fields
        if identifiers.get('name'):
            name = identifiers['name']
            name_fields = [f.name for f in fields if f.field_type in ['text', 'name'] or 'name' in f.name.lower()]
            
            for field_name in name_fields:
                query |= Q(**{f'data__{field_name}__iexact': name})
        
        if not query:
            return []
        
        records = await sync_to_async(list)(
            Record.objects.filter(
                pipeline=pipeline,
                is_deleted=False
            ).filter(query)[:20]
        )
        
        return records
    
    async def _calculate_confidence(
        self,
        record: Record,
        identifiers: Dict[str, Any],
        pipeline: Pipeline
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate confidence score for a record match
        
        Returns:
            Tuple of (confidence_score, match_details)
        """
        
        confidence = 0.0
        weights = {
            'email': 0.4,
            'phone': 0.3,
            'linkedin': 0.2,
            'domain': 0.15,
            'name': 0.1
        }
        match_details = {
            'matched_fields': [],
            'field_scores': {}
        }
        
        record_data = record.data or {}
        
        # Get fields from pipeline for dynamic matching
        fields = await sync_to_async(list)(
            Field.objects.filter(pipeline=pipeline, is_deleted=False)
        )
        
        # Email matching (highest confidence)
        if identifiers.get('email'):
            email = identifiers['email'].lower()
            email_fields = [f.name for f in fields if f.field_type == 'email' or 'email' in f.name.lower()]
            
            # Also include common field names as fallback
            if not email_fields:
                email_fields = ['email', 'work_email', 'personal_email', 'contact_email']
            
            for field_name in email_fields:
                field_value = str(record_data.get(field_name, '')).lower()
                if field_value == email:
                    confidence += weights['email']
                    match_details['matched_fields'].append(field_name)
                    match_details['field_scores'][field_name] = weights['email']
                    break
        
        # Phone matching
        if identifiers.get('phone'):
            phone_digits = re.sub(r'[^\d]', '', identifiers['phone'])[-10:]
            phone_fields = [f.name for f in fields if f.field_type == 'phone' or 'phone' in f.name.lower()]
            
            # Fallback to common names
            if not phone_fields:
                phone_fields = ['phone', 'mobile', 'work_phone', 'contact_phone']
            
            for field_name in phone_fields:
                record_phone = record_data.get(field_name, '')
                if record_phone:
                    record_digits = re.sub(r'[^\d]', '', record_phone)[-10:]
                    if record_digits == phone_digits:
                        confidence += weights['phone']
                        match_details['matched_fields'].append(field_name)
                        match_details['field_scores'][field_name] = weights['phone']
                        break
        
        # LinkedIn matching
        if identifiers.get('linkedin_url'):
            linkedin_fields = ['linkedin', 'linkedin_url']
            
            for field_name in linkedin_fields:
                record_linkedin = record_data.get(field_name, '')
                if record_linkedin and identifiers['linkedin_url'] in record_linkedin:
                    confidence += weights['linkedin']
                    match_details['matched_fields'].append(field_name)
                    match_details['field_scores'][field_name] = weights['linkedin']
                    break
        
        # Domain matching (for company records)
        if identifiers.get('domain'):
            domain = identifiers['domain'].lower()
            domain_fields = ['website', 'domain', 'company_domain']
            
            for field_name in domain_fields:
                record_domain = record_data.get(field_name, '').lower()
                if record_domain and domain in record_domain:
                    confidence += weights['domain']
                    match_details['matched_fields'].append(field_name)
                    match_details['field_scores'][field_name] = weights['domain']
                    break
        
        # Name matching (fuzzy, lower confidence)
        if identifiers.get('name'):
            name = identifiers['name'].lower()
            name_fields = ['name', 'full_name']
            
            for field_name in name_fields:
                record_name = record_data.get(field_name, '').lower()
                if record_name:
                    # Exact match
                    if record_name == name:
                        confidence += weights['name']
                        match_details['matched_fields'].append(field_name)
                        match_details['field_scores'][field_name] = weights['name']
                        break
                    # Fuzzy match (partial score)
                    elif self._names_similar(record_name, name):
                        partial_score = weights['name'] * 0.5
                        confidence += partial_score
                        match_details['matched_fields'].append(f"{field_name} (partial)")
                        match_details['field_scores'][field_name] = partial_score
                        break
        
        # Apply duplicate rules if available
        duplicate_rules = await self._get_applicable_duplicate_rules(pipeline)
        if duplicate_rules:
            rule_confidence = await self._apply_duplicate_rules(
                record, identifiers, duplicate_rules
            )
            # Average with field-based confidence
            confidence = (confidence + rule_confidence) / 2
            match_details['duplicate_rule_applied'] = True
            match_details['rule_confidence'] = rule_confidence
        
        match_details['total_confidence'] = confidence
        return confidence, match_details
    
    async def _extract_identifiers(
        self,
        message_data: Dict[str, Any],
        channel_type: str
    ) -> Dict[str, Any]:
        """Extract identifiers from message data"""
        
        identifiers = {}
        
        # Email channel
        if channel_type in ['email', 'gmail', 'outlook']:
            sender = message_data.get('sender', {})
            
            # Email
            email = sender.get('email') or message_data.get('from_email')
            if email and '@' in email:
                identifiers['email'] = email.lower()
                
                # Extract domain from email
                domain = email.split('@')[1]
                if domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                    identifiers['domain'] = domain
            
            # Name
            name = sender.get('name') or message_data.get('from_name')
            if name:
                identifiers['name'] = name
        
        # WhatsApp channel
        elif channel_type in ['whatsapp', 'whatsapp_business']:
            sender = message_data.get('sender', {})
            
            # Phone
            phone = sender.get('phone') or message_data.get('from_phone')
            if phone:
                identifiers['phone'] = phone
            
            # Name
            name = sender.get('name') or message_data.get('sender_name')
            if name:
                identifiers['name'] = name
        
        # LinkedIn channel
        elif channel_type == 'linkedin':
            sender = message_data.get('sender', {})
            
            # LinkedIn URL
            linkedin_url = sender.get('profile_url') or message_data.get('sender_profile')
            if linkedin_url:
                identifiers['linkedin_url'] = linkedin_url
            
            # Name
            name = sender.get('name') or message_data.get('sender_name')
            if name:
                identifiers['name'] = name
        
        return identifiers
    
    async def _get_applicable_duplicate_rules(self, pipeline: Pipeline) -> List[DuplicateRule]:
        """Get duplicate rules for the pipeline"""
        
        rules = await sync_to_async(list)(
            DuplicateRule.objects.filter(
                pipeline=pipeline,
                is_active=True,
                action_on_duplicate='detect_only'
            )
        )
        
        return rules
    
    async def _apply_duplicate_rules(
        self,
        record: Record,
        identifiers: Dict[str, Any],
        rules: List[DuplicateRule]
    ) -> float:
        """Apply duplicate rules and return confidence"""
        
        # Create pseudo-record from identifiers for comparison
        pseudo_record_data = identifiers.copy()
        
        max_confidence = 0.0
        
        for rule in rules:
            try:
                # Use logic engine to evaluate
                matches = self.logic_engine.evaluate_rule(
                    rule, record.data, pseudo_record_data
                )
                
                if matches:
                    # Rule matched, high confidence
                    max_confidence = max(max_confidence, 0.95)
            except Exception as e:
                logger.warning(f"Error applying duplicate rule {rule.id}: {e}")
                continue
        
        return max_confidence
    
    def _names_similar(self, name1: str, name2: str) -> bool:
        """Check if two names are similar"""
        
        # Split names into parts
        parts1 = set(name1.lower().split())
        parts2 = set(name2.lower().split())
        
        # Check for common parts
        common_parts = parts1.intersection(parts2)
        
        # Similar if they share at least one significant part (length > 2)
        return any(len(part) > 2 for part in common_parts)
    
    def _get_cache_key(self, identifiers: Dict[str, Any]) -> str:
        """Generate cache key from identifiers"""
        
        # Sort identifiers for consistent cache key
        sorted_items = sorted(identifiers.items())
        identifier_str = '_'.join([f"{k}:{v}" for k, v in sorted_items])
        
        # Hash for shorter key
        import hashlib
        hash_obj = hashlib.md5(identifier_str.encode())
        
        return f"{self.cache_prefix}{hash_obj.hexdigest()}"
    
    def _get_storage_reason(self, resolution: Dict[str, Any], threshold: float) -> str:
        """Generate human-readable storage reason"""
        
        if not resolution.get('found'):
            return 'no_contact_found'
        
        confidence = resolution.get('confidence', 0)
        
        if confidence >= self.HIGH_CONFIDENCE:
            return 'high_confidence_match'
        elif confidence >= threshold:
            return 'confidence_above_threshold'
        else:
            return 'confidence_below_threshold'
    
    def clear_cache(self, identifiers: Optional[Dict[str, Any]] = None):
        """Clear resolution cache"""
        
        if identifiers:
            cache_key = self._get_cache_key(identifiers)
            cache.delete(cache_key)
        else:
            # Clear all resolution cache for tenant
            # Note: This is a simplified version, production would need better cache management
            logger.info(f"Clearing all resolution cache for tenant {self.tenant_id}")


# Global gateway instance (will be initialized per request with tenant)
resolution_gateway = None

def get_resolution_gateway(tenant: Optional[Tenant] = None) -> ContactResolutionGateway:
    """Get or create resolution gateway for tenant"""
    global resolution_gateway
    
    if not resolution_gateway or (tenant and resolution_gateway.tenant_id != tenant.id):
        resolution_gateway = ContactResolutionGateway(tenant)
    
    return resolution_gateway