"""
Contact identification using duplicate rule logic with pipeline relationship domain validation
"""
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from pipelines.models import Pipeline, Record
from relationships.models import Relationship
from duplicates.models import DuplicateRule, URLExtractionRule
from duplicates.logic_engine import FieldMatcher, DuplicateLogicEngine

User = get_user_model()
logger = logging.getLogger(__name__)


class ContactIdentifier:
    """
    Identifies contacts using duplicate rule logic WITHOUT creating duplicate matches.
    Validates email domains against related pipeline records through relationships.
    """
    
    def __init__(self, tenant_id: int):
        self.tenant_id = tenant_id
        self.field_matcher = FieldMatcher(tenant_id=tenant_id)
    
    def identify_contact(self, message_data: dict) -> Optional[Record]:
        """
        Identify contact with pipeline relationship domain validation
        
        Args:
            message_data: Dict containing email, phone, linkedin_url, name, etc.
            
        Returns:
            Record if valid contact found, None otherwise
        """
        
        # Get all pipelines with active duplicate rules
        pipelines_with_rules = Pipeline.objects.filter(
            duplicate_rules__action_on_duplicate='detect_only',
            duplicate_rules__tenant_id=self.tenant_id
        ).distinct()
        
        message_email = message_data.get('email')
        message_domain = self._extract_domain(message_email)
        
        logger.info(f"Identifying contact for message data: {list(message_data.keys())}, domain: {message_domain}")
        
        # Try each pipeline until we find a valid match
        for pipeline in pipelines_with_rules:
            potential_contacts = self._identify_in_pipeline(pipeline, message_data)
            
            for contact in potential_contacts:
                if self._validate_contact_domain_via_relationships(contact, message_domain):
                    logger.info(f"Valid contact found: {contact.id} in pipeline {pipeline.name}")
                    return contact
        
        logger.info("No valid contact found with domain validation")
        return None
    
    def _identify_in_pipeline(self, pipeline: Pipeline, message_data: dict) -> List[Record]:
        """Find potential contacts in a specific pipeline using duplicate rule logic"""
        
        rules = pipeline.duplicate_rules.filter(action_on_duplicate='detect_only')
        matches = []
        
        for rule in rules:
            try:
                rule_matches = self._find_matches_using_rule_logic(rule, message_data)
                matches.extend(rule_matches)
            except Exception as e:
                logger.warning(f"Error applying rule {rule.name}: {e}")
                continue
        
        # Remove duplicates while preserving order
        seen = set()
        unique_matches = []
        for match in matches:
            if match.id not in seen:
                seen.add(match.id)
                unique_matches.append(match)
        
        return unique_matches
    
    def _find_matches_using_rule_logic(self, rule: DuplicateRule, message_data: dict) -> List[Record]:
        """Find matches using duplicate rule logic without creating DuplicateMatch records"""
        
        pipeline_records = Record.objects.filter(
            pipeline=rule.pipeline, 
            is_deleted=False
        )
        
        matches = []
        
        for record in pipeline_records:
            try:
                if self._evaluate_rule_logic(rule, message_data, record.data):
                    matches.append(record)
            except Exception as e:
                logger.warning(f"Error evaluating rule for record {record.id}: {e}")
                continue
        
        return matches
    
    def _evaluate_rule_logic(self, rule: DuplicateRule, message_data: dict, record_data: dict) -> bool:
        """Use existing DuplicateLogicEngine with proper URL extraction rule support"""
        
        try:
            logic_engine = DuplicateLogicEngine(tenant_id=self.tenant_id)
            
            return logic_engine.evaluate_rule(rule, message_data, record_data)
        except Exception as e:
            logger.warning(f"Error in rule evaluation: {e}")
            return False
    
    def _validate_contact_domain_via_relationships(self, contact: Record, message_domain: str) -> bool:
        """Validate message domain against domains from related pipeline records"""
        
        if not message_domain:
            logger.debug(f"No domain to validate for contact {contact.id}")
            return True  # No domain to validate, allow match
        
        # Get all active relationships from this contact
        relationships = Relationship.objects.filter(
            source_pipeline=contact.pipeline,
            source_record_id=contact.id,
            status='active',
            is_deleted=False
        ).select_related('target_pipeline')
        
        # If no relationships, allow the match (standalone contact)
        if not relationships.exists():
            logger.debug(f"No relationships for contact {contact.id}, allowing match")
            return True
        
        # Check each related pipeline record for domain matches
        for relationship in relationships:
            if self._related_record_domain_matches(relationship, message_domain):
                logger.info(f"Domain {message_domain} matches related record in pipeline {relationship.target_pipeline.name}")
                return True
        
        # No related pipeline record domains match - potential mismatch
        logger.warning(f"Domain {message_domain} does not match any related pipeline records for contact {contact.id}")
        return False
    
    def _related_record_domain_matches(self, relationship: Relationship, message_domain: str) -> bool:
        """Check if related pipeline record domain matches message domain"""
        
        target_pipeline = relationship.target_pipeline
        # Get target record and check if it's not soft deleted
        try:
            target_record = Record.objects.get(
                id=relationship.target_record_id,
                pipeline=relationship.target_pipeline,
                is_deleted=False
            )
        except Record.DoesNotExist:
            logger.debug(f"Target record {relationship.target_record_id} not found or soft deleted for relationship {relationship.id}")
            return False
        
        # Check if target pipeline has domain-based duplicate rules
        domain_rules = DuplicateRule.objects.filter(
            pipeline=target_pipeline,
            action_on_duplicate='detect_only'
        )
        
        # Look for duplicate rules that use domain template URL extraction
        for rule in domain_rules:
            if self._rule_uses_domain_template(rule):
                # Get domain from target record using this rule's field configuration
                record_domains = self._extract_domains_from_record(target_record, rule)
                
                for record_domain in record_domains:
                    if self._domains_match(record_domain, message_domain):
                        logger.debug(f"Domain match found: {record_domain} == {message_domain}")
                        return True
        
        return False
    
    def _rule_uses_domain_template(self, rule: DuplicateRule) -> bool:
        """Check if duplicate rule uses domain template URL extraction"""
        
        # Look for URL extraction rules with domain template for this pipeline
        url_extraction_rules = URLExtractionRule.objects.filter(
            pipeline=rule.pipeline,
            template_type='domain',
            is_active=True
        )
        
        return url_extraction_rules.exists()
    
    def _extract_domains_from_record(self, record: Record, rule: DuplicateRule) -> List[str]:
        """Extract domains from record data using duplicate rule field configuration"""
        
        domains = []
        record_data = record.data
        
        # Get fields that could contain domains
        potential_domain_fields = ['website', 'domain', 'url', 'email', 'company_website', 'company_domain']
        
        for field_name in potential_domain_fields:
            if field_name in record_data:
                field_value = record_data[field_name]
                if field_value:
                    domain = self._normalize_domain_using_extraction_rules(
                        field_value, 
                        rule.pipeline
                    )
                    if domain:
                        domains.append(domain)
        
        return domains
    
    def _normalize_domain_using_extraction_rules(self, value: str, pipeline: Pipeline) -> Optional[str]:
        """Use pipeline's URL extraction rules for domain normalization"""
        
        # Get domain template extraction rules for this pipeline
        domain_extraction_rules = URLExtractionRule.objects.filter(
            pipeline=pipeline,
            template_type='domain',
            is_active=True
        )
        
        if domain_extraction_rules.exists():
            # Use first available domain extraction rule
            rule = domain_extraction_rules.first()
            
            # Apply URL extraction logic using smart processor
            try:
                from duplicates.smart_url_processor import SmartURLProcessor
                processor = SmartURLProcessor()
                
                # Use the domain template from smart processor
                result = processor.normalize_url(value, template_name='domain')
                
                return result.extracted if result.success else None
            except Exception as e:
                logger.warning(f"Error using smart URL processor: {e}")
                # Fallback to simple domain extraction
                return self._simple_domain_extraction(value)
        
        # No domain extraction rules, use simple extraction
        return self._simple_domain_extraction(value)
    
    def _simple_domain_extraction(self, value: str) -> Optional[str]:
        """Simple domain extraction fallback"""
        
        try:
            # Handle email addresses
            if '@' in value:
                return value.split('@')[1].lower()
            
            # Handle URLs
            if not value.startswith(('http://', 'https://')):
                value = f"https://{value}"
            
            parsed = urlparse(value)
            domain = parsed.netloc.lower()
            
            # Remove www prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return domain
        except Exception as e:
            logger.warning(f"Error in simple domain extraction for '{value}': {e}")
            return None
    
    def _domains_match(self, record_domain: str, message_domain: str) -> bool:
        """Compare domains for match"""
        return record_domain.lower() == message_domain.lower()
    
    def _extract_domain(self, email: str) -> Optional[str]:
        """Extract domain from email address"""
        if not email or '@' not in email:
            return None
        return email.split('@')[1].lower()