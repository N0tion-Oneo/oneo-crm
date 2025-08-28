"""
Contact Resolution Gateway V3 - Multi-Match Support
Returns ALL matching records across different pipelines, not just the best match
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from django.core.cache import cache
from django.db.models import Q
from asgiref.sync import sync_to_async

from pipelines.models import Pipeline, Record, Field
from duplicates.logic_engine_async import AsyncDuplicateLogicEngine, AsyncFieldMatcher
from duplicates.models import DuplicateRule
from tenants.models import Tenant

logger = logging.getLogger(__name__)


class ContactResolutionGatewayV3:
    """
    Gateway for resolving contacts using the duplicate detection system
    
    Key Principles:
    1. Duplicate detection rules define what makes a record unique in each pipeline
    2. A communication can match multiple records across different pipelines
    3. All matches above the confidence threshold are returned
    """
    
    # Confidence thresholds
    HIGH_CONFIDENCE = 0.9
    MEDIUM_CONFIDENCE = 0.7
    LOW_CONFIDENCE = 0.5
    
    def __init__(self, tenant: Optional[Tenant] = None):
        """
        Initialize the resolution gateway with duplicate detection integration
        
        Args:
            tenant: Current tenant for multi-tenant isolation
        """
        self.tenant = tenant
        self.tenant_id = tenant.id if tenant else None
        # Pass tenant object to logic engine for schema context
        from duplicates.logic_engine_async import AsyncDuplicateLogicEngine, AsyncFieldMatcher
        self.logic_engine = AsyncDuplicateLogicEngine(self.tenant_id, tenant)
        self.field_matcher = AsyncFieldMatcher(self.tenant_id)
        
        # Cache settings
        self.cache_ttl = 3600  # 1 hour cache
        self.cache_prefix = f"contact_resolution_{self.tenant_id}_" if self.tenant_id else "contact_resolution_"
    
    async def resolve_contacts(
        self,
        identifiers: Dict[str, Any],
        pipelines: Optional[List[Pipeline]] = None,
        min_confidence: float = None
    ) -> Dict[str, Any]:
        """
        Resolve ALL matching contacts using identifiers and duplicate detection rules
        
        Args:
            identifiers: Dict with email, phone, linkedin_url, domain, etc.
            pipelines: List of pipelines to search (defaults to all pipelines)
            min_confidence: Minimum confidence score (defaults to LOW_CONFIDENCE)
            
        Returns:
            Dict with:
                - matches: List of match dictionaries, each containing:
                    - record: Record object
                    - pipeline: Pipeline object
                    - confidence: float confidence score
                    - match_details: Dict with matching field details
                - total_matches: int count of all matches
                - resolution_timestamp: ISO timestamp
                - pipelines_checked: List of pipeline names that were checked
                - pipelines_skipped: List of pipeline names that were skipped
        """
        
        if min_confidence is None:
            min_confidence = self.LOW_CONFIDENCE
        
        # Get pipelines to search
        if not pipelines:
            pipelines = await self._get_all_pipelines()
        
        # Collect ALL matches, not just the best
        all_matches = []
        pipelines_checked = []
        pipelines_skipped = []
        
        for pipeline in pipelines:
            # Get duplicate rules for this pipeline
            rules = await self._get_pipeline_rules(pipeline)
            
            if not rules:
                # No duplicate rules = no way to identify records in this pipeline
                logger.debug(f"Skipping pipeline {pipeline.name} - no duplicate rules configured")
                pipelines_skipped.append(pipeline.name)
                continue
            
            pipelines_checked.append(pipeline.name)
            
            # Use duplicate rules to find ALL matches in this pipeline
            pipeline_matches = await self._resolve_all_in_pipeline(
                identifiers, pipeline, rules, min_confidence
            )
            
            # Add all matches from this pipeline
            all_matches.extend(pipeline_matches)
        
        # Sort matches by confidence (highest first)
        all_matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        return {
            'matches': all_matches,
            'total_matches': len(all_matches),
            'resolution_timestamp': datetime.now(timezone.utc).isoformat(),
            'pipelines_checked': pipelines_checked,
            'pipelines_skipped': pipelines_skipped,
            'skip_reason': 'No duplicate detection rules configured' if pipelines_skipped else None
        }
    
    async def _resolve_all_in_pipeline(
        self,
        identifiers: Dict[str, Any],
        pipeline: Pipeline,
        rules: List[DuplicateRule],
        min_confidence: float
    ) -> List[Dict[str, Any]]:
        """
        Find ALL matching records in a pipeline using duplicate rules
        """
        matches = []
        
        # Build a pseudo-record from identifiers
        pseudo_record = self._build_pseudo_record(identifiers, pipeline)
        
        # Get candidate records using rule field requirements
        candidates = await self._get_candidate_records(pipeline, rules, identifiers)
        
        # Debug logging
        if candidates:
            logger.debug(f"Found {len(candidates)} candidates in pipeline {pipeline.name}")
            logger.debug(f"Pseudo record: {pseudo_record}")
        
        # Track which records we've already matched to avoid duplicates
        matched_record_ids = set()
        
        for candidate in candidates:
            # Skip if already matched
            if candidate.id in matched_record_ids:
                continue
                
            for rule in rules:
                # Evaluate rule using the async duplicate detection logic engine
                result = await self.logic_engine.evaluate_rule_async(
                    rule, 
                    pseudo_record, 
                    candidate.data
                )
                
                # Debug logging
                logger.debug(f"Evaluated candidate {candidate.id}: is_duplicate={result.get('is_duplicate')}")
                
                if result.get('is_duplicate'):
                    # Calculate confidence based on matched fields
                    confidence = self._calculate_confidence_from_rule_match(result)
                    
                    if confidence >= min_confidence:
                        matched_record_ids.add(candidate.id)
                        matches.append({
                            'record': candidate,
                            'pipeline': pipeline,
                            'confidence': confidence,
                            'match_details': {
                                'rule': rule.name,
                                'matched_fields': result.get('matched_fields', []),
                                'field_matches': result.get('field_matches', {}),
                                'logic_tree': result.get('logic_tree', {}),
                                'match_type': self._determine_match_type(result, identifiers)
                            }
                        })
                        break  # Don't evaluate other rules for this candidate
        
        return matches
    
    def _determine_match_type(self, rule_result: Dict, identifiers: Dict) -> str:
        """
        Determine the type of match (email, domain, phone, etc.)
        """
        matched_fields = rule_result.get('matched_fields', [])
        field_matches = rule_result.get('field_matches', {})
        
        match_types = []
        
        for field_name in matched_fields:
            if 'email' in field_name.lower() and identifiers.get('email'):
                match_types.append('email')
            elif 'website' in field_name.lower() or 'domain' in field_name.lower():
                if identifiers.get('domain') or '@' in str(identifiers.get('email', '')):
                    match_types.append('domain')
            elif 'phone' in field_name.lower() and identifiers.get('phone'):
                match_types.append('phone')
            elif 'linkedin' in field_name.lower() and identifiers.get('linkedin_url'):
                match_types.append('linkedin')
            elif 'name' in field_name.lower() and identifiers.get('name'):
                match_types.append('name')
        
        return ','.join(set(match_types)) if match_types else 'unknown'
    
    def _build_pseudo_record(
        self,
        identifiers: Dict[str, Any],
        pipeline: Pipeline
    ) -> Dict[str, Any]:
        """
        Build a pseudo-record from identifiers for rule evaluation
        Also extracts domain from email if present
        """
        pseudo_record = {}
        
        # Map common identifier types to potential field names
        field_mappings = {
            'email': ['email', 'work_email', 'personal_email', 'contact_email'],
            'phone': ['phone', 'phone_number', 'mobile', 'work_phone', 'contact_phone'],
            'name': ['name', 'full_name', 'contact_name', 'first_name', 'last_name'],
            'linkedin_url': ['linkedin', 'linkedin_url', 'social_linkedin'],
            'domain': ['website', 'domain', 'company_domain', 'company_website']
        }
        
        # Extract domain from email if not provided
        if identifiers.get('email') and not identifiers.get('domain'):
            email = identifiers['email']
            if '@' in email:
                domain = email.split('@')[1]
                identifiers['domain'] = domain
                # Also add as website formats
                identifiers['website'] = f"https://{domain}"
        
        for identifier_type, value in identifiers.items():
            if value and identifier_type in field_mappings:
                for potential_field in field_mappings[identifier_type]:
                    pseudo_record[potential_field] = value
        
        return pseudo_record
    
    async def _get_candidate_records(
        self,
        pipeline: Pipeline,
        rules: List[DuplicateRule],
        identifiers: Dict[str, Any]
    ) -> List[Record]:
        """
        Get candidate records based on rule field requirements
        """
        query = Q()
        
        # Extract field names from all rules
        rule_fields = set()
        for rule in rules:
            logic = rule.logic or {}
            
            # Handle both old and new logic formats
            if 'fields' in logic:
                # Simple format with just fields array
                for field_config in logic.get('fields', []):
                    field_name = field_config.get('field')
                    if field_name:
                        rule_fields.add(field_name)
            
            # Handle conditions format (new structure from UI)
            if 'conditions' in logic:
                for condition in logic.get('conditions', []):
                    for field_config in condition.get('fields', []):
                        field_name = field_config.get('field')
                        if field_name:
                            rule_fields.add(field_name)
            
            # Extract fields from AND groups
            for and_group in logic.get('and_groups', []):
                for field_config in and_group.get('fields', []):
                    field_name = field_config.get('field')
                    if field_name:
                        rule_fields.add(field_name)
            
            # Extract fields from OR groups
            for or_group in logic.get('or_groups', []):
                for field_config in or_group.get('fields', []):
                    field_name = field_config.get('field')
                    if field_name:
                        rule_fields.add(field_name)
        
        # Build query based on rule fields and identifiers
        for field_name in rule_fields:
            # Check if we have an identifier that might match this field
            if 'email' in field_name.lower() and identifiers.get('email'):
                query |= Q(**{f'data__{field_name}__iexact': identifiers['email']})
            elif 'phone' in field_name.lower() and identifiers.get('phone'):
                # Normalize phone for search
                import re
                phone_str = identifiers['phone']
                phone_normalized = re.sub(r'[^\d]', '', phone_str)  # Remove non-digits
                if phone_normalized:
                    # For searching, we need a custom query that normalizes the stored phone
                    # This is complex in Django ORM, so we'll fetch more candidates and filter in Python
                    # Search broadly then filter precisely during evaluation
                    query |= (
                        Q(**{f'data__{field_name}__icontains': phone_normalized[-10:]}) |  # String format
                        Q(**{f'data__{field_name}__icontains': phone_normalized[-9:]}) |   # Shorter match
                        Q(**{f'data__{field_name}__number__icontains': phone_normalized[-9:]}) |  # Dict format (number field)
                        Q(**{f'data__{field_name}__country_code__icontains': '27'})  # Country code match
                    )
            elif 'name' in field_name.lower() and identifiers.get('name'):
                query |= Q(**{f'data__{field_name}__icontains': identifiers['name']})
            elif 'linkedin' in field_name.lower() and identifiers.get('linkedin_url'):
                query |= Q(**{f'data__{field_name}__icontains': identifiers['linkedin_url']})
            elif ('website' in field_name.lower() or 'domain' in field_name.lower()):
                # Check both domain and website identifiers
                if identifiers.get('domain'):
                    query |= Q(**{f'data__{field_name}__icontains': identifiers['domain']})
                if identifiers.get('website'):
                    query |= Q(**{f'data__{field_name}__icontains': identifiers['website']})
        
        if not query:
            return []
        
        from django_tenants.utils import schema_context
        
        def get_records():
            with schema_context(self.tenant.schema_name if self.tenant else 'public'):
                return list(
                    Record.objects.filter(
                        pipeline=pipeline,
                        is_deleted=False
                    ).filter(query)[:100]  # Get more candidates for comprehensive matching
                )
        
        records = await sync_to_async(get_records)()
        
        return records
    
    def _calculate_confidence_from_rule_match(
        self,
        rule_result: Dict[str, Any]
    ) -> float:
        """
        Calculate confidence score from duplicate rule match result
        """
        if not rule_result.get('is_duplicate'):
            return 0.0
        
        # Use the confidence from the async logic engine if available
        if 'confidence' in rule_result and rule_result['confidence'] > 0:
            return rule_result['confidence']
        
        # Fallback calculation
        matched_fields = rule_result.get('matched_fields', [])
        if not matched_fields:
            return 0.6  # Base confidence if no field details
        
        # Weight different field types
        field_weights = {
            'email': 0.9,      # Email is strongest identifier
            'phone': 0.8,      # Phone is good
            'linkedin': 0.85,  # LinkedIn is unique
            'domain': 0.7,     # Domain is weaker (many people from same company)
            'website': 0.7,    # Same as domain
            'name': 0.6,       # Name alone is weak
        }
        
        max_confidence = 0.6  # Start with base confidence
        
        for field_name in matched_fields:
            # Determine field type
            if 'email' in field_name.lower():
                max_confidence = max(max_confidence, field_weights['email'])
            elif 'phone' in field_name.lower():
                max_confidence = max(max_confidence, field_weights['phone'])
            elif 'linkedin' in field_name.lower():
                max_confidence = max(max_confidence, field_weights['linkedin'])
            elif 'domain' in field_name.lower() or 'website' in field_name.lower():
                max_confidence = max(max_confidence, field_weights['domain'])
            elif 'name' in field_name.lower():
                max_confidence = max(max_confidence, field_weights['name'])
        
        return min(max_confidence, 1.0)  # Cap at 1.0
    
    async def _get_all_pipelines(self) -> List[Pipeline]:
        """Get all active pipelines"""
        from django_tenants.utils import schema_context
        
        def get_pipelines():
            with schema_context(self.tenant.schema_name if self.tenant else 'public'):
                return list(Pipeline.objects.filter(is_active=True))
        
        pipelines = await sync_to_async(get_pipelines)()
        return pipelines
    
    async def _get_pipeline_rules(self, pipeline: Pipeline) -> List[DuplicateRule]:
        """Get duplicate rules for a pipeline"""
        from django_tenants.utils import schema_context
        
        def get_rules():
            with schema_context(self.tenant.schema_name if self.tenant else 'public'):
                return list(
                    DuplicateRule.objects.filter(
                        pipeline=pipeline,
                        is_active=True,
                        action_on_duplicate='detect_only'
                    ).select_related('pipeline')
                )
        
        rules = await sync_to_async(get_rules)()
        return rules


# Factory function for backward compatibility
def get_resolution_gateway(tenant: Optional[Tenant] = None) -> ContactResolutionGatewayV3:
    """Get or create resolution gateway for tenant"""
    return ContactResolutionGatewayV3(tenant)