"""
Async-safe logic evaluation engine for duplicate detection
"""
import re
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from asgiref.sync import sync_to_async
from pipelines.field_types import FieldType
from pipelines.models import Field
from .models import URLExtractionRule, DuplicateRule

logger = logging.getLogger(__name__)


class AsyncFieldMatcher:
    """Async-safe field matching functions"""
    
    def __init__(self, tenant_id: Optional[int] = None):
        self.tenant_id = tenant_id
        self._url_extraction_cache = {}
    
    def match_field(self, field_config: Dict, value1: Any, value2: Any, match_type: str, field_type: str = 'text') -> bool:
        """
        Match two field values using specified match type
        
        Args:
            field_config: Field configuration dictionary
            value1: First value to compare
            value2: Second value to compare  
            match_type: Type of matching to perform
            field_type: Type of field (email, phone, url, etc.)
            
        Returns:
            bool: True if values match according to the rule
        """
        
        if not value1 or not value2:
            return False
        
        try:
            if match_type == 'exact':
                return str(value1) == str(value2)
            
            elif match_type == 'case_insensitive':
                return str(value1).lower() == str(value2).lower()
            
            elif match_type == 'email_normalized':
                return self._match_email_normalized(value1, value2, field_config)
            
            elif match_type == 'phone_normalized':
                return self._match_phone_normalized(value1, value2)
            
            elif match_type == 'url_normalized':
                return self._match_url_normalized(value1, value2, field_config)
            
            elif match_type == 'fuzzy':
                return self._match_fuzzy(value1, value2)
            
            elif match_type == 'numeric':
                return self._match_numeric(value1, value2)
            
            else:
                logger.warning(f"Unknown match type: {match_type}, falling back to case-insensitive")
                return str(value1).lower() == str(value2).lower()
                
        except Exception as e:
            logger.error(f"Error matching field: {e}")
            return False
    
    def _match_email_normalized(self, value1: Any, value2: Any, field_config: Dict) -> bool:
        """Email matching with normalization"""
        email1, email2 = str(value1), str(value2)
        
        # Normalize emails
        email1 = email1.lower().strip()
        email2 = email2.lower().strip()
        
        return email1 == email2
    
    def _match_phone_normalized(self, value1: Any, value2: Any) -> bool:
        """Phone matching with normalization"""
        phone1 = self._normalize_phone(str(value1))
        phone2 = self._normalize_phone(str(value2))
        return phone1 == phone2
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number for comparison"""
        if not phone:
            return ""
        
        # Remove all non-digit characters
        digits_only = re.sub(r'[^\d]', '', phone)
        
        # Remove leading 1 if present (US numbers)
        if digits_only.startswith('1') and len(digits_only) == 11:
            digits_only = digits_only[1:]
        
        return digits_only
    
    def _match_url_normalized(self, value1: Any, value2: Any, field_config: Dict) -> bool:
        """URL matching with normalization"""
        url1 = self._normalize_url(str(value1))
        url2 = self._normalize_url(str(value2))
        return url1 == url2
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison"""
        if not url:
            return ""
        
        # Basic normalization
        normalized = url.strip().lower()
        
        # Add protocol if missing
        if not normalized.startswith(('http://', 'https://')):
            normalized = f"https://{normalized}"
        
        try:
            parsed = urlparse(normalized)
            domain = parsed.netloc.lower()
            
            # Remove www
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return domain
        except:
            return normalized.lower()
    
    def _match_fuzzy(self, value1: Any, value2: Any, threshold: float = 0.8) -> bool:
        """Fuzzy string matching"""
        s1, s2 = str(value1).lower(), str(value2).lower()
        
        # Simple fuzzy match - check if one contains the other
        if s1 in s2 or s2 in s1:
            return True
        
        # Check similarity (simplified)
        if len(s1) == 0 or len(s2) == 0:
            return False
        
        # Check if they share significant substring
        min_len = min(len(s1), len(s2))
        if min_len >= 3:
            for i in range(len(s1) - 2):
                if s1[i:i+3] in s2:
                    return True
        
        return False
    
    def _match_numeric(self, value1: Any, value2: Any) -> bool:
        """Numeric matching"""
        try:
            num1 = float(str(value1).replace(',', ''))
            num2 = float(str(value2).replace(',', ''))
            return abs(num1 - num2) < 0.01
        except:
            return False


class AsyncDuplicateLogicEngine:
    """Async-safe duplicate detection logic engine"""
    
    def __init__(self, tenant_id: Optional[int] = None, tenant=None):
        self.tenant_id = tenant_id
        self.field_matcher = AsyncFieldMatcher(tenant_id)
        self._tenant = tenant
        self._tenant_schema = tenant.schema_name if tenant else None
    
    async def evaluate_rule_async(
        self, 
        rule: DuplicateRule, 
        record1_data: Dict[str, Any], 
        record2_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Async-safe rule evaluation
        
        Returns:
            Dict with evaluation details
        """
        result = {
            'is_duplicate': False,
            'matched_fields': [],
            'field_matches': {},
            'confidence': 0.0
        }
        
        logic = rule.logic or {}
        
        # Get pipeline fields asynchronously
        from django_tenants.utils import get_tenant_model, schema_context
        pipeline = rule.pipeline
        
        # Get tenant schema if not cached
        if not self._tenant_schema and self.tenant_id:
            tenant_model = get_tenant_model()
            def get_tenant():
                return tenant_model.objects.filter(id=self.tenant_id).first()
            self._tenant = await sync_to_async(get_tenant)()
            if self._tenant:
                self._tenant_schema = self._tenant.schema_name
        
        # Get fields within tenant schema
        def get_fields():
            schema_name = self._tenant_schema or 'public'
            with schema_context(schema_name):
                return list(Field.objects.filter(pipeline=pipeline, is_deleted=False))
        
        fields_list = await sync_to_async(get_fields)()
        
        # Create field lookup
        field_lookup = {field.name: field for field in fields_list}
        
        # Handle simple format with just 'fields' array
        if 'fields' in logic:
            result['is_duplicate'] = await self._evaluate_fields_async(
                logic.get('fields', []),
                record1_data,
                record2_data,
                field_lookup,
                result
            )
        
        # Handle AND groups
        elif 'and_groups' in logic:
            for and_group in logic.get('and_groups', []):
                if await self._evaluate_fields_async(
                    and_group.get('fields', []),
                    record1_data,
                    record2_data,
                    field_lookup,
                    result
                ):
                    result['is_duplicate'] = True
                    break
        
        # Handle OR groups
        elif 'or_groups' in logic:
            for or_group in logic.get('or_groups', []):
                if await self._evaluate_fields_async(
                    or_group.get('fields', []),
                    record1_data,
                    record2_data,
                    field_lookup,
                    result
                ):
                    result['is_duplicate'] = True
                    break
        
        # Calculate confidence based on matched fields
        if result['is_duplicate']:
            result['confidence'] = self._calculate_confidence(result['field_matches'])
        
        return result
    
    async def _evaluate_fields_async(
        self,
        fields: List[Dict],
        record1_data: Dict[str, Any],
        record2_data: Dict[str, Any],
        field_lookup: Dict[str, Field],
        result: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a list of fields (AND logic)
        """
        if not fields:
            return False
        
        all_match = True
        
        for field_config in fields:
            field_name = field_config.get('field')
            match_type = field_config.get('match_type', 'exact')
            
            # Get field object or use defaults
            field = field_lookup.get(field_name)
            field_type = field.field_type if field else 'text'
            field_cfg = field.field_config if field else {}
            
            # Get values
            value1 = record1_data.get(field_name)
            value2 = record2_data.get(field_name)
            
            # Perform matching
            field_matches = self.field_matcher.match_field(
                field_cfg,
                value1,
                value2,
                match_type,
                field_type
            )
            
            # Store result
            result['field_matches'][field_name] = {
                'matched': field_matches,
                'match_type': match_type,
                'value1': value1,
                'value2': value2
            }
            
            if field_matches:
                result['matched_fields'].append(field_name)
            else:
                all_match = False
                # For AND logic, if one field doesn't match, the whole condition fails
                if 'operator' not in field_config or field_config.get('operator', 'AND') == 'AND':
                    break
        
        return all_match
    
    def _calculate_confidence(self, field_matches: Dict) -> float:
        """
        Calculate confidence score based on field matches
        """
        if not field_matches:
            return 0.0
        
        matched_count = sum(1 for match in field_matches.values() if match.get('matched'))
        total_count = len(field_matches)
        
        if total_count == 0:
            return 0.0
        
        # Base confidence from match ratio
        confidence = matched_count / total_count
        
        # Boost confidence for certain field types
        for field_name, match_info in field_matches.items():
            if match_info.get('matched'):
                if 'email' in field_name.lower():
                    confidence = min(1.0, confidence + 0.2)
                elif 'phone' in field_name.lower():
                    confidence = min(1.0, confidence + 0.1)
                elif 'website' in field_name.lower() or 'domain' in field_name.lower():
                    confidence = min(1.0, confidence + 0.1)
        
        return confidence