"""
Contact Resolution Gateway V2 - Using Duplicate Detection System
Leverages the duplicate detection rules and normalization for contact resolution
"""
import logging
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


class ContactResolutionGatewayV2:
    """
    Gateway for resolving contacts using the duplicate detection system
    
    Key Principle: The duplicate detection rules define what makes a record unique
    in each pipeline. If a pipeline has no duplicate rules, it means there's no
    defined way to identify unique records, so we cannot match communications to it.
    
    This ensures contact resolution respects the data integrity rules defined by
    the duplicate detection system.
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
        self.logic_engine = DuplicateLogicEngine(self.tenant_id)
        self.field_matcher = FieldMatcher(self.tenant_id)
        
        # Cache settings
        self.cache_ttl = 3600  # 1 hour cache
        self.cache_prefix = f"contact_resolution_{self.tenant_id}_" if self.tenant_id else "contact_resolution_"
    
    async def resolve_contact(
        self,
        identifiers: Dict[str, Any],
        pipelines: Optional[List[Pipeline]] = None,
        min_confidence: float = None
    ) -> Dict[str, Any]:
        """
        Resolve a contact using identifiers and duplicate detection rules
        
        Args:
            identifiers: Dict with email, phone, linkedin_url, domain, etc.
            pipelines: List of pipelines to search (defaults to all pipelines)
            min_confidence: Minimum confidence score (uses rule thresholds if not specified)
            
        Returns:
            Dict with:
                - found: bool
                - record: Record object if found
                - confidence: float confidence score
                - match_details: Dict with matching field details
                - pipeline: Pipeline object if found
        """
        
        # Get pipelines to search
        if not pipelines:
            pipelines = await self._get_all_pipelines()
        
        best_match = None
        best_confidence = 0.0
        best_details = {}
        
        for pipeline in pipelines:
            # Get duplicate rules for this pipeline
            rules = await self._get_pipeline_rules(pipeline)
            
            if not rules:
                # No duplicate rules = no way to identify records in this pipeline
                # Skip this pipeline entirely
                logger.debug(f"Skipping pipeline {pipeline.name} - no duplicate rules configured")
                continue
            
            # Use duplicate rules to find matches
            match, confidence, details = await self._resolve_with_rules(
                identifiers, pipeline, rules
            )
            
            if match and confidence > best_confidence:
                best_confidence = confidence
                best_match = match
                best_details = details
                
                # Short circuit on high confidence
                if confidence >= self.HIGH_CONFIDENCE:
                    break
        
        # Track pipelines that were skipped
        pipelines_checked = []
        pipelines_skipped = []
        
        for pipeline in pipelines:
            rules = await sync_to_async(lambda p: list(
                DuplicateRule.objects.filter(
                    pipeline=p,
                    is_active=True,
                    action_on_duplicate='detect_only'
                )
            ))(pipeline)
            
            if rules:
                pipelines_checked.append(pipeline.name)
            else:
                pipelines_skipped.append(pipeline.name)
        
        return {
            'found': best_match is not None,
            'record': best_match,
            'confidence': best_confidence,
            'match_details': best_details,
            'pipeline': best_match.pipeline if best_match else None,
            'resolution_timestamp': datetime.now(timezone.utc).isoformat(),
            'pipelines_checked': pipelines_checked,
            'pipelines_skipped': pipelines_skipped,
            'skip_reason': 'No duplicate detection rules configured'
        }
    
    async def _resolve_with_rules(
        self,
        identifiers: Dict[str, Any],
        pipeline: Pipeline,
        rules: List[DuplicateRule]
    ) -> Tuple[Optional[Record], float, Dict]:
        """
        Resolve using duplicate detection rules
        """
        
        # Build a pseudo-record from identifiers
        pseudo_record = self._build_pseudo_record(identifiers, pipeline)
        
        # Get candidate records using rule field requirements
        candidates = await self._get_candidate_records(pipeline, rules, identifiers)
        
        best_match = None
        best_confidence = 0.0
        best_details = {}
        
        for candidate in candidates:
            for rule in rules:
                # Evaluate rule using the duplicate detection logic engine
                result = self.logic_engine._detailed_evaluate_rule(
                    rule, 
                    pseudo_record, 
                    candidate.data
                )
                
                if result.get('is_duplicate'):
                    # Calculate confidence based on matched fields
                    confidence = self._calculate_confidence_from_rule_match(result)
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = candidate
                        best_details = {
                            'rule': rule.name,
                            'matched_fields': result.get('matched_fields', []),
                            'field_matches': result.get('field_matches', {}),
                            'logic_tree': result.get('logic_tree', {})
                        }
                        
                        # Short circuit on perfect match
                        if confidence >= 1.0:
                            break
        
        return best_match, best_confidence, best_details
    
    # Note: Dynamic field detection method removed by design
    # Pipelines without duplicate rules cannot be used for contact resolution
    # as there's no authoritative way to identify unique records
    
    # The method below is kept for reference but should not be used
    async def _resolve_with_field_detection_DEPRECATED(
        self,
        identifiers: Dict[str, Any],
        pipeline: Pipeline
    ) -> Tuple[Optional[Record], float, Dict]:
        """
        DEPRECATED: This method is no longer used.
        
        Pipelines must have duplicate detection rules to participate in
        contact resolution. This ensures data integrity and prevents
        incorrect matches.
        """
        
        # Get pipeline fields
        fields = await sync_to_async(list)(
            Field.objects.filter(pipeline=pipeline, is_deleted=False)
        )
        
        # Build search query based on field types
        query = Q()
        field_mapping = {}
        
        for field in fields:
            # Email fields
            if identifiers.get('email') and (
                field.field_type == 'email' or 'email' in field.name.lower()
            ):
                # Use field matcher for normalized comparison
                email = identifiers['email']
                normalized_email = self.field_matcher._match_email_normalized(
                    email, email, field.field_config or {}
                )
                query |= Q(**{f'data__{field.name}__iexact': email})
                field_mapping[field.name] = ('email', email)
            
            # Phone fields  
            elif identifiers.get('phone') and (
                field.field_type == 'phone' or 'phone' in field.name.lower()
            ):
                # Use field matcher for phone normalization
                phone = identifiers['phone']
                normalized_phone = self.field_matcher._normalize_phone(phone)
                if normalized_phone:
                    query |= Q(**{f'data__{field.name}__icontains': normalized_phone[-10:]})
                    field_mapping[field.name] = ('phone', phone)
            
            # URL/LinkedIn fields
            elif identifiers.get('linkedin_url') and (
                field.field_type == 'url' or 'linkedin' in field.name.lower()
            ):
                url = identifiers['linkedin_url']
                normalized_url = self.field_matcher._normalize_url(
                    url, field.field_config or {}, None
                )
                query |= Q(**{f'data__{field.name}__icontains': normalized_url})
                field_mapping[field.name] = ('linkedin', url)
        
        if not query:
            return None, 0.0, {}
        
        # Search for matching records
        records = await sync_to_async(list)(
            Record.objects.filter(
                pipeline=pipeline,
                is_deleted=False
            ).filter(query)[:10]
        )
        
        # Calculate confidence for each match
        best_match = None
        best_confidence = 0.0
        best_details = {}
        
        for record in records:
            confidence, details = self._calculate_field_confidence(
                record, identifiers, field_mapping, fields
            )
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = record
                best_details = details
        
        return best_match, best_confidence, best_details
    
    def _build_pseudo_record(
        self,
        identifiers: Dict[str, Any],
        pipeline: Pipeline
    ) -> Dict[str, Any]:
        """
        Build a pseudo-record from identifiers for rule evaluation
        """
        pseudo_record = {}
        
        # Map common identifier types to potential field names
        field_mappings = {
            'email': ['email', 'work_email', 'personal_email', 'contact_email'],
            'phone': ['phone', 'mobile', 'work_phone', 'contact_phone'],
            'name': ['name', 'full_name', 'contact_name'],
            'linkedin_url': ['linkedin', 'linkedin_url', 'social_linkedin'],
            'domain': ['website', 'domain', 'company_domain', 'company_website']
        }
        
        for identifier_type, value in identifiers.items():
            if value and identifier_type in field_mappings:
                # Try to match with actual pipeline fields first
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
                phone_normalized = self.field_matcher._normalize_phone(identifiers['phone'])
                if phone_normalized:
                    query |= Q(**{f'data__{field_name}__icontains': phone_normalized[-10:]})
            elif 'name' in field_name.lower() and identifiers.get('name'):
                query |= Q(**{f'data__{field_name}__icontains': identifiers['name']})
            elif 'linkedin' in field_name.lower() and identifiers.get('linkedin_url'):
                query |= Q(**{f'data__{field_name}__icontains': identifiers['linkedin_url']})
        
        if not query:
            return []
        
        records = await sync_to_async(list)(
            Record.objects.filter(
                pipeline=pipeline,
                is_deleted=False
            ).filter(query)[:50]  # Get more candidates for rule evaluation
        )
        
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
        
        # Base confidence from rule match
        confidence = 0.7  # Base confidence for any rule match
        
        # Increase confidence based on matched fields
        matched_fields = rule_result.get('matched_fields', [])
        field_matches = rule_result.get('field_matches', {})
        
        # Weight different field types
        field_weights = {
            'email': 0.3,
            'phone': 0.2,
            'linkedin': 0.15,
            'name': 0.1,
            'domain': 0.1
        }
        
        for field_name, match_info in field_matches.items():
            if match_info.get('matched'):
                # Determine field type
                field_type = 'other'
                if 'email' in field_name.lower():
                    field_type = 'email'
                elif 'phone' in field_name.lower():
                    field_type = 'phone'
                elif 'linkedin' in field_name.lower():
                    field_type = 'linkedin'
                elif 'name' in field_name.lower():
                    field_type = 'name'
                elif 'domain' in field_name.lower() or 'website' in field_name.lower():
                    field_type = 'domain'
                
                # Add weight for this field
                confidence += field_weights.get(field_type, 0.05)
        
        return min(confidence, 1.0)  # Cap at 1.0
    
    def _calculate_field_confidence(
        self,
        record: Record,
        identifiers: Dict[str, Any],
        field_mapping: Dict[str, Tuple[str, Any]],
        fields: List[Field]
    ) -> Tuple[float, Dict]:
        """
        Calculate confidence for field-based matching
        """
        confidence = 0.0
        matched_fields = []
        
        weights = {
            'email': 0.5,
            'phone': 0.3,
            'linkedin': 0.2,
            'name': 0.1,
            'domain': 0.1
        }
        
        for field in fields:
            if field.name in field_mapping:
                identifier_type, identifier_value = field_mapping[field.name]
                record_value = record.data.get(field.name)
                
                if record_value:
                    # Use field matcher for proper comparison
                    is_match = False
                    
                    if identifier_type == 'email':
                        is_match = self.field_matcher._match_email_normalized(
                            identifier_value, record_value, field.field_config or {}
                        )
                    elif identifier_type == 'phone':
                        is_match = self.field_matcher._match_phone_normalized(
                            identifier_value, record_value, field.field_config or {}
                        )
                    elif identifier_type == 'linkedin':
                        is_match = self.field_matcher._match_url_normalized(
                            identifier_value, record_value, field.field_config or {}, None
                        )
                    
                    if is_match:
                        confidence += weights.get(identifier_type, 0.05)
                        matched_fields.append(field.name)
        
        return confidence, {
            'matched_fields': matched_fields,
            'confidence_breakdown': {
                field: weights.get(field_mapping.get(field, ('', ''))[0], 0)
                for field in matched_fields
            }
        }
    
    async def _get_all_pipelines(self) -> List[Pipeline]:
        """Get all active pipelines"""
        pipelines = await sync_to_async(list)(
            Pipeline.objects.filter(is_active=True)
        )
        return pipelines
    
    async def _get_pipeline_rules(self, pipeline: Pipeline) -> List[DuplicateRule]:
        """Get duplicate rules for a pipeline"""
        rules = await sync_to_async(list)(
            DuplicateRule.objects.filter(
                pipeline=pipeline,
                is_active=True,
                action_on_duplicate='detect_only'
            ).select_related('pipeline')
        )
        return rules


# Factory function for backward compatibility
def get_resolution_gateway(tenant: Optional[Tenant] = None) -> ContactResolutionGatewayV2:
    """Get or create resolution gateway for tenant"""
    return ContactResolutionGatewayV2(tenant)