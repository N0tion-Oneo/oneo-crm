"""
Pipeline relationship context resolver with domain validation intelligence
"""
import logging
from typing import Dict, Any, List, Optional

from django.contrib.auth import get_user_model
from pipelines.models import Pipeline, Record
from relationships.models import Relationship
from duplicates.models import DuplicateRule, URLExtractionRule

User = get_user_model()
logger = logging.getLogger(__name__)


class RelationshipContextResolver:
    """
    Resolves relationship context with domain validation across all related pipelines
    """
    
    def __init__(self, tenant_id: int):
        self.tenant_id = tenant_id
    
    def get_relationship_context(self, contact_record: Record, message_email: str = None) -> Dict[str, Any]:
        """
        Get relationship context with domain validation across all related pipelines
        
        Args:
            contact_record: The contact record to analyze
            message_email: Email from the communication for domain validation
            
        Returns:
            Dict containing relationship context and domain validation info
        """
        
        message_domain = self._extract_domain(message_email) if message_email else None
        
        logger.info(f"Getting relationship context for contact {contact_record.id}, domain: {message_domain}")
        
        # Get all relationships from this contact
        all_relationships = Relationship.objects.filter(
            source_pipeline=contact_record.pipeline,
            source_record_id=contact_record.id,
            is_deleted=False
        ).select_related('target_pipeline', 'relationship_type').order_by('-created_at')
        
        active_relationships = all_relationships.filter(status='active')
        historical_relationships = all_relationships.filter(status='inactive')
        
        logger.debug(f"Found {active_relationships.count()} active and {historical_relationships.count()} historical relationships")
        
        # Find domain-matched relationships
        domain_matched_relationships = []
        domain_validation_details = []
        
        if message_domain:
            for relationship in active_relationships:
                validation_result = self._relationship_record_domain_matches(relationship, message_domain)
                if validation_result['matches']:
                    domain_matched_relationships.append(relationship)
                    domain_validation_details.append({
                        'relationship_id': relationship.id,
                        'pipeline_name': relationship.target_pipeline.name,
                        'record_title': self._get_target_record_title(relationship),
                        'domains_found': validation_result['domains'],
                        'matched_domain': validation_result['matched_domain']
                    })
        
        return {
            'active_relationships': list(active_relationships),
            'historical_relationships': list(historical_relationships),
            'domain_matched_relationships': domain_matched_relationships,
            'domain_validated': len(domain_matched_relationships) > 0 if message_domain else True,
            'message_domain': message_domain,
            'validation_status': self._get_validation_status(
                active_relationships, 
                domain_matched_relationships, 
                message_domain
            ),
            'pipeline_context': self._get_pipeline_context(domain_matched_relationships),
            'domain_validation_details': domain_validation_details
        }
    
    def _relationship_record_domain_matches(self, relationship: Relationship, message_domain: str) -> Dict[str, Any]:
        """
        Check if relationship target record domain matches message domain
        
        Returns:
            Dict with matches (bool), domains (list), and matched_domain (str)
        """
        
        # Get target record and check if it's not soft deleted
        try:
            from pipelines.models import Record
            target_record = Record.objects.get(
                id=relationship.target_record_id,
                pipeline=relationship.target_pipeline,
                is_deleted=False
            )
        except Record.DoesNotExist:
            return {'matches': False, 'domains': [], 'matched_domain': None}
        
        # Check if target pipeline has domain-based duplicate rules
        domain_rules = DuplicateRule.objects.filter(
            pipeline=relationship.target_pipeline,
            action_on_duplicate='detect_only'
        )
        
        all_domains = []
        matched_domain = None
        
        for rule in domain_rules:
            if self._rule_uses_domain_template(rule):
                record_domains = self._extract_domains_from_record(target_record, rule)
                all_domains.extend(record_domains)
                
                for record_domain in record_domains:
                    if record_domain.lower() == message_domain.lower():
                        matched_domain = record_domain
                        return {
                            'matches': True,
                            'domains': all_domains,
                            'matched_domain': matched_domain
                        }
        
        return {
            'matches': False,
            'domains': all_domains,
            'matched_domain': None
        }
    
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
        potential_domain_fields = ['website', 'domain', 'url', 'email', 'company_website', 'company_domain', 'site', 'homepage']
        
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
        
        # Remove duplicates while preserving order
        seen = set()
        unique_domains = []
        for domain in domains:
            if domain not in seen:
                seen.add(domain)
                unique_domains.append(domain)
        
        return unique_domains
    
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
        from urllib.parse import urlparse
        
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
    
    def _get_validation_status(self, active_relationships, domain_matched_relationships, message_domain) -> str:
        """Get human-readable validation status"""
        
        if not message_domain:
            return 'no_domain_to_validate'
        
        if not active_relationships.exists():
            return 'no_related_records'
        
        if domain_matched_relationships:
            return 'domain_validated'
        
        return 'domain_mismatch_warning'  # Contact has relationships but email domain doesn't match
    
    def _get_pipeline_context(self, domain_matched_relationships) -> List[Dict[str, Any]]:
        """Get context about which pipelines validated the domain"""
        
        return [
            {
                'pipeline_name': rel.target_pipeline.name,
                'pipeline_id': rel.target_pipeline.id,
                'relationship_type': rel.relationship_type.name,
                'relationship_type_slug': rel.relationship_type.slug,
                'record_title': self._get_target_record_title(rel),
                'record_id': self._get_target_record_id(rel)
            }
            for rel in domain_matched_relationships
        ]
    
    def _extract_domain(self, email: str) -> Optional[str]:
        """Extract domain from email address"""
        if not email or '@' not in email:
            return None
        return email.split('@')[1].lower()
    
    def _get_target_record_title(self, relationship) -> Optional[str]:
        """Get target record title if record exists and is not soft deleted"""
        try:
            from pipelines.models import Record
            target_record = Record.objects.get(
                id=relationship.target_record_id,
                pipeline=relationship.target_pipeline,
                is_deleted=False
            )
            return target_record.title
        except Record.DoesNotExist:
            return None
    
    def _get_target_record_id(self, relationship) -> Optional[str]:
        """Get target record ID if record exists and is not soft deleted"""
        try:
            from pipelines.models import Record
            Record.objects.get(
                id=relationship.target_record_id,
                pipeline=relationship.target_pipeline,
                is_deleted=False
            )
            return str(relationship.target_record_id)
        except Record.DoesNotExist:
            return None
    
    def resolve_company_from_email_domain(self, contact_record: Record, email: str) -> Optional[Record]:
        """
        Resolve company/organization from email domain using pipeline relationships
        
        This is a helper method for finding related pipeline records based on email domain
        """
        
        domain = self._extract_domain(email) if email else None
        if not domain:
            return None
        
        # Get active relationships to pipelines with domain rules
        relationships = Relationship.objects.filter(
            source_pipeline=contact_record.pipeline,
            source_record_id=contact_record.id,
            status='active',
            is_deleted=False
        ).select_related('target_pipeline')
        
        # Check each relationship for domain match
        for relationship in relationships:
            validation_result = self._relationship_record_domain_matches(relationship, domain)
            if validation_result['matches']:
                # Return target record if it exists and is not soft deleted
                try:
                    from pipelines.models import Record
                    return Record.objects.get(
                        id=relationship.target_record_id,
                        pipeline=relationship.target_pipeline,
                        is_deleted=False
                    )
                except Record.DoesNotExist:
                    continue
        
        return None