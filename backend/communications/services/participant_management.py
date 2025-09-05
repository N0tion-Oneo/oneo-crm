"""
Participant Management Service
Handles participant-to-record relationships with intelligent field mapping
"""
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from communications.models import Participant, Conversation
from pipelines.models import Pipeline, Field, Record
from pipelines.field_types import FieldType
from pipelines.validation.field_validator import FieldValidator
from duplicates.models import DuplicateRule
# RecordCommunicationLink removed - using participant-based linking instead

logger = logging.getLogger(__name__)


class ParticipantManagementError(Exception):
    """Base exception for participant management"""
    pass


class FieldMappingError(ParticipantManagementError):
    """Error in field mapping process"""
    pass


class RecordCreationError(ParticipantManagementError):
    """Error creating record from participant"""
    pass


class FieldValidationError(ParticipantManagementError):
    """Field validation error"""
    def __init__(self, field_errors):
        self.field_errors = field_errors
        super().__init__(str(field_errors))


class ParticipantManagementService:
    """
    Service for managing participant-to-record relationships
    with intelligent field mapping based on duplicate detection rules
    """
    
    def __init__(self, tenant=None):
        self.tenant = tenant
        self.field_validator = FieldValidator()
        # Load participant settings for name field configuration
        from communications.models import ParticipantSettings
        self.settings = ParticipantSettings.get_or_create_for_tenant()
        
    def get_identifying_fields_from_duplicate_rules(self, pipeline: Pipeline) -> Dict[str, List[str]]:
        """
        Extract identifying fields from duplicate detection rules
        
        Returns:
            Dictionary categorizing fields by their purpose:
            {
                'email_fields': ['email_address', 'contact_email'],
                'phone_fields': ['mobile_phone', 'phone_number'],
                'name_fields': ['full_name', 'contact_name'],
                'url_fields': ['linkedin_url', 'website'],
                'id_fields': ['customer_id', 'account_number']
            }
        """
        field_purposes = {
            'email_fields': [],
            'phone_fields': [],
            'name_fields': [],
            'url_fields': [],
            'id_fields': [],
            'text_fields': []
        }
        
        # Get active duplicate rules for this pipeline
        rules = DuplicateRule.objects.filter(
            pipeline=pipeline,
            is_active=True
        )
        
        for rule in rules:
            if rule.logic:
                self._parse_rule_logic(rule.logic, field_purposes)
        
        # Remove duplicates from each list
        for key in field_purposes:
            field_purposes[key] = list(set(field_purposes[key]))
        
        logger.info(f"Identified fields for pipeline {pipeline.name}: {field_purposes}")
        return field_purposes
    
    def _parse_rule_logic(self, logic_node: Dict[str, Any], field_purposes: Dict[str, List[str]]):
        """
        Recursively parse duplicate rule logic to extract field purposes
        """
        # Handle fields at this level
        if 'fields' in logic_node:
            for field_config in logic_node['fields']:
                field_name = field_config.get('field')
                match_type = field_config.get('match_type', 'exact')
                
                if not field_name:
                    continue
                
                # Categorize by match type
                if match_type == 'email_normalized':
                    field_purposes['email_fields'].append(field_name)
                elif match_type == 'phone_normalized':
                    field_purposes['phone_fields'].append(field_name)
                elif match_type == 'url_normalized':
                    field_purposes['url_fields'].append(field_name)
                elif match_type in ['fuzzy', 'case_insensitive']:
                    # These are often used for names
                    field_purposes['name_fields'].append(field_name)
                elif match_type == 'exact':
                    field_purposes['id_fields'].append(field_name)
                else:
                    field_purposes['text_fields'].append(field_name)
        
        # Handle nested conditions (for OR/AND logic)
        if 'conditions' in logic_node:
            for condition in logic_node['conditions']:
                self._parse_rule_logic(condition, field_purposes)
    
    def preview_field_mapping(
        self, 
        participant: Participant, 
        pipeline: Pipeline,
        overrides: Optional[Dict[str, Any]] = None,
        link_type: str = 'primary'
    ) -> List[Dict[str, Any]]:
        """
        Generate field mapping preview with validation
        
        Returns:
            List of field mapping dictionaries with validation status
        """
        field_purposes = self.get_identifying_fields_from_duplicate_rules(pipeline)
        mappings = []
        is_secondary = link_type == 'secondary'
        
        for field in pipeline.fields.filter(is_deleted=False).order_by('display_order'):
            # Get the value from participant
            raw_value = self._get_participant_value_for_field(
                participant, field, field_purposes, is_secondary=is_secondary
            )
            
            # Apply overrides if provided
            if overrides and field.slug in overrides:
                raw_value = overrides[field.slug]
            
            # Skip if no value or empty string
            if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
                continue
            
            # Format the value according to field type
            try:
                formatted_value = self._format_value_for_field(raw_value, field)
                is_valid = True
                validation_errors = []
                
                # Validate the formatted value
                try:
                    self._validate_field_value(formatted_value, field)
                except ValidationError as e:
                    is_valid = False
                    validation_errors = [str(e)]
                    
            except Exception as e:
                import traceback
                logger.error(f"Error formatting field {field.slug}: {e}\n{traceback.format_exc()}")
                formatted_value = raw_value
                is_valid = False
                validation_errors = [f"Formatting error: {str(e)}"]
            
            # Determine source of mapping
            source = 'unknown'
            if field.slug in field_purposes['email_fields']:
                source = 'duplicate_rule_email'
            elif field.slug in field_purposes['phone_fields']:
                source = 'duplicate_rule_phone'
            elif field.slug in field_purposes['name_fields']:
                source = 'duplicate_rule_name'
            elif field.slug in field_purposes['url_fields']:
                source = 'duplicate_rule_url'
            elif field.slug in field_purposes['id_fields']:
                source = 'duplicate_rule_id'
            elif raw_value is not None:
                source = 'field_name_match'
            
            mappings.append({
                'field_name': field.name,
                'field_slug': field.slug,
                'field_type': field.field_type,
                'source': source,
                'participant_value': raw_value,
                'formatted_value': formatted_value,
                'is_valid': is_valid,
                'validation_errors': validation_errors,
                'is_required': field.field_config.get('required', False)
            })
        
        return mappings
    
    def create_record_from_participant(
        self,
        participant: Participant,
        pipeline: Pipeline,
        user,
        overrides: Optional[Dict[str, Any]] = None,
        link_conversations: bool = True,
        link_type: str = 'primary'
    ) -> Record:
        """
        Create CRM record from participant data with field validation
        
        Args:
            participant: The participant to create a record from
            pipeline: Target pipeline for the record
            user: User creating the record
            overrides: Optional field value overrides
            link_conversations: Whether to link participant's conversations to the record
            link_type: 'primary' for contact record or 'secondary' for organization/company
            
        Returns:
            Created Record instance
            
        Raises:
            RecordCreationError: If record creation fails
            FieldValidationError: If field validation fails
        """
        # Get field mappings
        mappings = self.preview_field_mapping(participant, pipeline, overrides, link_type)
        
        # Check for validation errors
        field_errors = {}
        for mapping in mappings:
            if not mapping['is_valid']:
                field_errors[mapping['field_slug']] = mapping['validation_errors']
        
        if field_errors:
            raise FieldValidationError(field_errors)
        
        # Build record data
        record_data = {}
        for mapping in mappings:
            if mapping['is_valid']:
                record_data[mapping['field_slug']] = mapping['formatted_value']
        
        # Create the record
        try:
            with transaction.atomic():
                record = Record.objects.create(
                    pipeline=pipeline,
                    data=record_data,
                    created_by=user,
                    updated_by=user
                )
                
                # Link participant to record based on link type
                if link_type == 'secondary':
                    participant.secondary_record = record
                else:
                    participant.contact_record = record
                participant.resolution_confidence = 1.0
                participant.resolution_method = 'manual_creation'
                participant.resolved_at = timezone.now()
                participant.save()
                
                # Link conversations if requested
                if link_conversations:
                    self._link_participant_conversations(participant, record)
                
                logger.info(
                    f"Created record {record.id} from participant {participant.id} "
                    f"in pipeline {pipeline.name}"
                )
                
                return record
                
        except Exception as e:
            logger.error(f"Failed to create record from participant: {e}")
            raise RecordCreationError(f"Failed to create record: {str(e)}")
    
    def link_participant_to_record(
        self,
        participant: Participant,
        record: Record,
        user,
        confidence: float = 1.0,
        link_conversations: bool = True,
        link_type: str = 'primary'
    ):
        """
        Link participant to existing record
        """
        try:
            with transaction.atomic():
                # Link based on link type
                if link_type == 'secondary':
                    participant.secondary_record = record
                else:
                    participant.contact_record = record
                participant.resolution_confidence = confidence
                participant.resolution_method = 'manual_link'
                participant.resolved_at = timezone.now()
                participant.save()
                
                # Link conversations if requested
                if link_conversations:
                    self._link_participant_conversations(participant, record)
                
                logger.info(f"Linked participant {participant.id} to record {record.id}")
                
        except Exception as e:
            logger.error(f"Failed to link participant to record: {e}")
            raise ParticipantManagementError(f"Failed to link: {str(e)}")
    
    def unlink_participant(self, participant: Participant, user):
        """
        Remove participant's record link
        """
        try:
            previous_record = participant.contact_record
            
            participant.contact_record = None
            participant.secondary_record = None
            participant.resolution_confidence = 0.0  # Set to 0 instead of None
            participant.resolution_method = ''  # Set to empty string instead of None
            participant.resolved_at = None
            participant.save()
            
            # Remove conversation links
            if previous_record:
                RecordCommunicationLink.objects.filter(
                    participant=participant,
                    record=previous_record
                ).delete()
            
            logger.info(f"Unlinked participant {participant.id} from record")
            
        except Exception as e:
            logger.error(f"Failed to unlink participant: {e}")
            raise ParticipantManagementError(f"Failed to unlink: {str(e)}")
    
    def bulk_create_records(
        self,
        participant_ids: List[str],
        pipeline: Pipeline,
        user
    ) -> Dict[str, Any]:
        """
        Create records for multiple participants
        
        Returns:
            Dictionary with success/failure counts and details
        """
        results = {
            'success_count': 0,
            'failure_count': 0,
            'created_records': [],
            'errors': []
        }
        
        participants = Participant.objects.filter(
            id__in=participant_ids,
            contact_record__isnull=True
        )
        
        for participant in participants:
            try:
                record = self.create_record_from_participant(
                    participant, pipeline, user
                )
                results['success_count'] += 1
                results['created_records'].append({
                    'participant_id': str(participant.id),
                    'record_id': str(record.id),
                    'participant_name': participant.get_display_name()
                })
            except Exception as e:
                results['failure_count'] += 1
                results['errors'].append({
                    'participant_id': str(participant.id),
                    'participant_name': participant.get_display_name(),
                    'error': str(e)
                })
        
        return results
    
    def _split_name(self, full_name: str) -> Dict[str, str]:
        """
        Split a full name into first and last name based on strategy
        
        Returns:
            Dictionary with 'first_name' and 'last_name' keys
        """
        if not full_name:
            return {'first_name': '', 'last_name': ''}
        
        name_parts = full_name.strip().split()
        
        if not name_parts:
            return {'first_name': '', 'last_name': ''}
        
        if len(name_parts) == 1:
            # Only one name part - use as first name
            return {'first_name': name_parts[0], 'last_name': ''}
        
        strategy = self.settings.name_split_strategy
        
        if strategy == 'first_space':
            # Everything before first space is first name, rest is last name
            return {
                'first_name': name_parts[0],
                'last_name': ' '.join(name_parts[1:])
            }
        elif strategy == 'last_space':
            # Everything before last space is first name, last part is last name
            return {
                'first_name': ' '.join(name_parts[:-1]),
                'last_name': name_parts[-1]
            }
        else:  # smart strategy
            # Handle common patterns
            if len(name_parts) == 2:
                return {'first_name': name_parts[0], 'last_name': name_parts[1]}
            
            # Check for common name prefixes (Mr., Dr., etc.)
            prefixes = ['mr', 'mrs', 'ms', 'dr', 'prof']
            if name_parts[0].lower().rstrip('.') in prefixes:
                name_parts = name_parts[1:]
            
            if len(name_parts) >= 3:
                # Check for common middle name patterns (single letter, Jr., Sr., etc.)
                suffixes = ['jr', 'sr', 'ii', 'iii', 'iv']
                if name_parts[-1].lower().rstrip('.') in suffixes:
                    # Last part is suffix, use second-to-last as last name
                    return {
                        'first_name': ' '.join(name_parts[:-2]),
                        'last_name': name_parts[-2]
                    }
                
                # Default: first part is first name, last part is last name, middle ignored
                return {
                    'first_name': name_parts[0],
                    'last_name': name_parts[-1]
                }
            
            # Fallback
            return {
                'first_name': name_parts[0] if name_parts else '',
                'last_name': name_parts[-1] if len(name_parts) > 1 else ''
            }
    
    def _extract_domain_from_email(self, email: str) -> Optional[str]:
        """
        Extract domain from email address
        """
        if not email or '@' not in email:
            return None
        
        domain = email.split('@')[1].lower()
        
        # Remove common free email domains
        free_domains = [
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 
            'icloud.com', 'me.com', 'mac.com', 'live.com', 'msn.com',
            'aol.com', 'protonmail.com', 'zoho.com', 'yandex.com'
        ]
        
        if domain in free_domains:
            return None
            
        return domain
    
    def _get_participant_value_for_field(
        self,
        participant: Participant,
        field: Field,
        field_purposes: Dict[str, List[str]],
        is_secondary: bool = False
    ) -> Optional[Any]:
        """
        Map participant data to appropriate field
        
        Note: Name fields are handled via settings configuration (not duplicate rules)
        since duplicate detection typically only identifies email/phone fields.
        
        Args:
            participant: The participant to map
            field: The field to map to
            field_purposes: Field categorization from duplicate rules (email, phone, url)
            is_secondary: Whether this is for secondary (org/company) record creation
        """
        field_slug = field.slug
        
        # For secondary records, handle company-specific fields
        if is_secondary:
            field_name_lower = field_slug.lower()
            
            # Check if this is the configured company name field
            if self.settings.company_name_field and field_slug == self.settings.company_name_field:
                domain = self._extract_domain_from_email(participant.email)
                if domain:
                    # Format domain as company name (e.g., "example.com" -> "Example")
                    company_name = domain.split('.')[0].title()
                    return company_name
            
            # Check for domain/website fields
            if any(x in field_name_lower for x in ['domain', 'website', 'url', 'web']):
                domain = self._extract_domain_from_email(participant.email)
                if domain:
                    # Format as URL if it's a URL field
                    if field.field_type in ['url', FieldType.URL]:
                        return f"https://{domain}"
                    return domain
        
        # Check for configured name field mappings FIRST (these are NOT from duplicate rules)
        if participant.name:
            # Check if this is the configured full name field
            if self.settings.full_name_field and field_slug == self.settings.full_name_field:
                return participant.name
            
            # Check if this is a configured first/last name field
            if self.settings.first_name_field and field_slug == self.settings.first_name_field:
                name_parts = self._split_name(participant.name)
                return name_parts['first_name']
            
            if self.settings.last_name_field and field_slug == self.settings.last_name_field:
                name_parts = self._split_name(participant.name)
                return name_parts['last_name']
        
        # Now check fields identified by duplicate rules
        if field_slug in field_purposes['email_fields']:
            return participant.email if participant.email else None
        elif field_slug in field_purposes['phone_fields']:
            return participant.phone if participant.phone else None
        elif field_slug in field_purposes['url_fields']:
            # Handle social URLs only if the field is identified for URLs
            if participant.linkedin_member_urn and 'linkedin' in field_slug.lower():
                return f"linkedin.com/in/{participant.linkedin_member_urn}"
            elif participant.instagram_username and 'instagram' in field_slug.lower():
                return participant.instagram_username
            elif participant.twitter_handle and 'twitter' in field_slug.lower():
                return participant.twitter_handle
            return None
        
        # No fallback - field must be identified by duplicate rules
        return None
    
    def _format_value_for_field(self, value: Any, field: Field) -> Any:
        """
        Transform value according to field type and config
        """
        if value is None:
            return None
        
        field_type = str(field.field_type)  # Ensure it's a string for comparison
        field_config = field.field_config or {}
        
        if field_type == 'email' or field_type == FieldType.EMAIL:
            # Respect EmailFieldConfig
            if field_config.get('auto_lowercase', True):
                value = str(value).lower()
            if field_config.get('trim_whitespace', True):
                value = value.strip()
            return value
            
        elif field_type == 'phone' or field_type == FieldType.PHONE:
            # If value is already a properly formatted phone object, return it
            if isinstance(value, dict) and 'number' in value:
                # Ensure both country_code and number are strings
                return {
                    'country_code': str(value.get('country_code', '')),
                    'number': str(value.get('number', ''))
                }
            
            # Format as phone field expects
            phone_str = str(value).strip()
            
            # If empty, return None to avoid validation errors
            if not phone_str:
                return None
                
            # Extract country code and number
            if phone_str.startswith('+'):
                # Try to parse country code (simple approach)
                if len(phone_str) > 10:
                    # Assume first 2-3 digits after + are country code
                    if phone_str[1:3] in ['27', '44', '61', '91']:  # Common 2-digit codes
                        return {
                            'country_code': phone_str[:3],
                            'number': phone_str[3:]
                        }
                    else:  # 1-digit code like US/Canada
                        return {
                            'country_code': phone_str[:2],
                            'number': phone_str[2:]
                        }
            
            # If we have a phone number without country code, still format it properly
            if phone_str:
                return {
                    'country_code': '',
                    'number': phone_str
                }
            
            return None
            
        elif field_type in ['text', 'single_line_text'] or field_type == FieldType.TEXT:
            # Respect text field config
            if field_config.get('trim_whitespace', True):
                value = str(value).strip()
            max_length = field_config.get('max_length')
            if max_length and len(value) > max_length:
                value = value[:max_length]
            return value
            
        elif field_type == 'url' or field_type == FieldType.URL:
            # Format URLs properly
            url = str(value)
            if 'linkedin' in url and not url.startswith('http'):
                url = f"https://linkedin.com/in/{url.split('/')[-1]}"
            elif not url.startswith('http'):
                url = f"https://{url}"
            return url
            
        elif field_type == 'name':
            # Handle name fields
            value = str(value)
            if field_config.get('capitalize', False):
                value = value.title()
            return value
            
        else:
            # For other field types, return as string
            return str(value)
    
    def _validate_field_value(self, value: Any, field: Field):
        """
        Validate value against field rules
        """
        # Check required fields
        if field.field_config.get('required') and not value:
            raise ValidationError(f"{field.name} is required")
        
        # Skip validation if no value
        if value is None or value == '':
            return
        
        # Type-specific validation
        field_type = str(field.field_type)
        if field_type == 'email' or field_type == FieldType.EMAIL:
            if '@' not in str(value):
                raise ValidationError("Invalid email format")
                
        elif field_type == 'url' or field_type == FieldType.URL:
            url = str(value)
            if not url.startswith(('http://', 'https://')):
                raise ValidationError("URL must start with http:// or https://")
        
        # Additional validation can be added here
    
    def _link_participant_conversations(self, participant: Participant, record: Record):
        """
        Link all participant's conversations to the record
        [DEPRECATED: No longer creates RecordCommunicationLinks, 
         using participant-based linking instead]
        """
        # This method is no longer needed as we're using participant-based linking
        # Conversations are linked through participants, not RecordCommunicationLinks
        logger.info(
            f"Participant {participant.id} linked to record {record.id} - "
            f"conversations accessible through participant relationship"
        )