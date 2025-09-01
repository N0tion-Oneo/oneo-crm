"""
Service to extract communication identifiers from records using duplicate rules
"""
import re
import logging
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

from django.db.models import Q
from pipelines.models import Record, Field
from duplicates.models import DuplicateRule

logger = logging.getLogger(__name__)


class RecordIdentifierExtractor:
    """Extract communication identifiers from records using duplicate rule configuration"""
    
    def extract_identifiers_from_record(self, record: Record) -> Dict[str, List[str]]:
        """
        Extract all communication identifiers from a record.
        Uses duplicate rules to identify which fields contain unique identifiers.
        
        Returns:
            Dict with keys: email, phone, linkedin, domain, other
        """
        identifiers = {
            'email': [],
            'phone': [],
            'linkedin': [],
            'domain': [],
            'other': []
        }
        
        # Get active duplicate rules for this pipeline
        duplicate_rules = DuplicateRule.objects.filter(
            pipeline=record.pipeline,
            is_active=True
        )
        
        # Collect all fields used in duplicate rules
        identifier_fields = set()
        
        for rule in duplicate_rules:
            logic = rule.logic or {}
            
            # Handle simple 'fields' format
            if 'fields' in logic:
                for field_config in logic['fields']:
                    field_slug = field_config.get('field')
                    if field_slug:
                        identifier_fields.add(field_slug)
            
            # Handle 'conditions' format (OR/AND groups)
            if 'conditions' in logic:
                for condition in logic.get('conditions', []):
                    for field_config in condition.get('fields', []):
                        field_slug = field_config.get('field')
                        if field_slug:
                            identifier_fields.add(field_slug)
        
        # Extract values from identified fields
        for field_slug in identifier_fields:
            field_value = record.data.get(field_slug)
            if not field_value:
                continue
            
            # Get field definition to understand field type
            try:
                field = Field.objects.get(
                    pipeline=record.pipeline, 
                    slug=field_slug,
                    is_deleted=False
                )
                
                # Categorize based on field type and content
                categorized_value = self._categorize_identifier(
                    field_value, 
                    field.field_type,
                    field.field_config
                )
                
                for category, values in categorized_value.items():
                    if values:
                        if isinstance(values, list):
                            identifiers[category].extend(values)
                        else:
                            identifiers[category].append(values)
                            
            except Field.DoesNotExist:
                logger.warning(f"Field {field_slug} not found for pipeline {record.pipeline_id}")
                continue
        
        # Remove duplicates and clean up
        for key in identifiers:
            identifiers[key] = list(set(filter(None, identifiers[key])))
        
        logger.info(f"Extracted identifiers for record {record.id}: {identifiers}")
        return identifiers
    
    def _categorize_identifier(
        self, 
        value: Any, 
        field_type: str,
        field_config: Dict
    ) -> Dict[str, Any]:
        """Categorize a field value into communication identifier types"""
        result = {
            'email': [],
            'phone': [],
            'linkedin': [],
            'domain': [],
            'other': []
        }
        
        # Handle different field types
        if field_type == 'email':
            email = self._normalize_email(value)
            if email:
                result['email'] = [email]
                # Also extract domain
                domain = self._extract_domain_from_email(email)
                if domain:
                    result['domain'] = [domain]
                    
        elif field_type == 'phone':
            phone = self._normalize_phone(value)
            if phone:
                result['phone'] = [phone]
                
        elif field_type in ['url', 'website']:
            url_str = str(value).strip()
            
            # Check if it's a LinkedIn URL
            if 'linkedin.com' in url_str.lower():
                linkedin_id = self._extract_linkedin_id(url_str)
                if linkedin_id:
                    result['linkedin'] = [linkedin_id]
            
            # Extract domain from URLs
            domain = self._extract_domain_from_url(url_str)
            if domain and domain not in ['linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com']:
                result['domain'] = [domain]
                
        elif field_type in ['text', 'textarea']:
            # Check if text contains email, phone patterns, or URLs
            text = str(value)
            
            # Check for LinkedIn URLs in text
            if 'linkedin.com' in text.lower():
                linkedin_id = self._extract_linkedin_id(text)
                if linkedin_id:
                    result['linkedin'] = [linkedin_id]
            
            # Extract emails from text
            emails = self._extract_emails_from_text(text)
            if emails:
                result['email'] = emails
                for email in emails:
                    domain = self._extract_domain_from_email(email)
                    if domain:
                        result['domain'].append(domain)
            
            # Extract phones from text
            phones = self._extract_phones_from_text(text)
            if phones:
                result['phone'] = phones
                
        return result
    
    def _normalize_email(self, email: Any) -> Optional[str]:
        """Normalize email address"""
        if not email:
            return None
        
        email_str = str(email).strip().lower()
        
        # Basic email validation
        if '@' in email_str and '.' in email_str.split('@')[1]:
            return email_str
        
        return None
    
    def _normalize_phone(self, phone: Any) -> Optional[str]:
        """Normalize phone number"""
        if not phone:
            return None
        
        # Handle dict format from phone field type
        if isinstance(phone, dict):
            country_code = phone.get('country_code', '')
            number = phone.get('number', '')
            phone_str = f"{country_code}{number}"
        else:
            phone_str = str(phone)
        
        # Remove all non-digit characters
        digits_only = re.sub(r'[^\d]', '', phone_str)
        
        # Ensure minimum length
        if len(digits_only) >= 7:
            return digits_only
        
        return None
    
    def _extract_domain_from_email(self, email: str) -> Optional[str]:
        """Extract domain from email address"""
        if '@' in email:
            domain = email.split('@')[1].lower()
            # Remove common free email providers
            if domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                return domain
        return None
    
    def _extract_domain_from_url(self, url: str) -> Optional[str]:
        """Extract domain from URL"""
        if not url:
            return None
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Remove port if present
            if ':' in domain:
                domain = domain.split(':')[0]
            
            return domain if domain else None
        except:
            return None
    
    def _extract_linkedin_id(self, url: str) -> Optional[str]:
        """Extract LinkedIn profile ID from URL"""
        patterns = [
            r'linkedin\.com/in/([a-zA-Z0-9\-]+)',
            r'linkedin\.com/company/([a-zA-Z0-9\-]+)',
            r'linkedin\.com/sales/people/([a-zA-Z0-9\-,]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)  # Just return the username without prefix
        
        return None
    
    def _extract_emails_from_text(self, text: str) -> List[str]:
        """Extract email addresses from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return [email.lower() for email in emails]
    
    def _extract_phones_from_text(self, text: str) -> List[str]:
        """Extract phone numbers from text"""
        # Simple pattern for phone numbers (digits with optional formatting)
        phone_pattern = r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,5}[-\s\.]?[0-9]{1,5}'
        phones = re.findall(phone_pattern, text)
        
        normalized = []
        for phone in phones:
            normalized_phone = self._normalize_phone(phone)
            if normalized_phone:
                normalized.append(normalized_phone)
        
        return normalized
    
    def get_identifier_fields(self, pipeline_id: int) -> List[str]:
        """
        Get list of field slugs that are used as identifiers in duplicate rules
        
        Returns:
            List of field slugs
        """
        duplicate_rules = DuplicateRule.objects.filter(
            pipeline_id=pipeline_id,
            is_active=True
        )
        
        identifier_fields = set()
        
        for rule in duplicate_rules:
            logic = rule.logic or {}
            
            # Extract field slugs from logic
            if 'fields' in logic:
                for field_config in logic['fields']:
                    field_slug = field_config.get('field')
                    if field_slug:
                        identifier_fields.add(field_slug)
            
            if 'conditions' in logic:
                for condition in logic.get('conditions', []):
                    for field_config in condition.get('fields', []):
                        field_slug = field_config.get('field')
                        if field_slug:
                            identifier_fields.add(field_slug)
        
        return list(identifier_fields)
    
    def find_records_by_identifiers(
        self, 
        identifiers: Dict[str, List[str]], 
        pipeline_id: Optional[int] = None
    ) -> List[Record]:
        """
        Find records that match the given identifiers.
        Uses the same fields that duplicate rules use.
        
        Args:
            identifiers: Dict with email, phone, linkedin, domain lists
            pipeline_id: Optional pipeline to restrict search to
            
        Returns:
            List of matching Record objects
        """
        from ..models import RecordCommunicationProfile
        
        # Build query for RecordCommunicationProfile
        query = Q()
        
        # Use __contains for JSONB array fields instead of __overlap
        # __overlap doesn't work reliably with PostgreSQL JSONB arrays
        if identifiers.get('email'):
            for email in identifiers['email']:
                query |= Q(communication_identifiers__email__contains=email)
        
        if identifiers.get('phone'):
            for phone in identifiers['phone']:
                query |= Q(communication_identifiers__phone__contains=phone)
        
        if identifiers.get('linkedin'):
            for linkedin in identifiers['linkedin']:
                query |= Q(communication_identifiers__linkedin__contains=linkedin)
        
        if identifiers.get('domain'):
            for domain in identifiers['domain']:
                query |= Q(communication_identifiers__domain__contains=domain)
        
        if not query:
            return []
        
        profiles = RecordCommunicationProfile.objects.filter(query)
        
        if pipeline_id:
            profiles = profiles.filter(pipeline_id=pipeline_id)
        
        # Get unique records
        record_ids = profiles.values_list('record_id', flat=True).distinct()
        return list(Record.objects.filter(id__in=record_ids))
    
    def find_company_records_by_domain(
        self,
        domain: str,
        pipeline_slugs: Optional[List[str]] = None
    ) -> List[Record]:
        """
        Find company/organization records that match the given domain.
        
        Args:
            domain: Domain to search for (e.g., 'oneodigital.com')
            pipeline_slugs: Optional list of pipeline slugs to restrict search to
                          (defaults to common company pipeline names)
            
        Returns:
            List of matching Record objects
        """
        from ..models import RecordCommunicationProfile
        
        if not domain:
            return []
        
        # Default to common company/organization pipeline slugs
        if not pipeline_slugs:
            pipeline_slugs = ['companies', 'organizations', 'company', 'organization', 'accounts']
        
        # Remove www. prefix if present for better matching
        clean_domain = domain.lower()
        if clean_domain.startswith('www.'):
            clean_domain = clean_domain[4:]
        
        # Build query for RecordCommunicationProfile
        # Search for domain in the communication_identifiers JSONB field
        query = Q(communication_identifiers__domain__contains=clean_domain)
        
        profiles = RecordCommunicationProfile.objects.filter(query)
        
        # Filter by pipeline if specified
        if pipeline_slugs:
            from pipelines.models import Pipeline
            target_pipelines = Pipeline.objects.filter(slug__in=pipeline_slugs)
            if target_pipelines.exists():
                profiles = profiles.filter(pipeline__in=target_pipelines)
        
        # Get unique records
        record_ids = profiles.values_list('record_id', flat=True).distinct()
        return list(Record.objects.filter(id__in=record_ids))