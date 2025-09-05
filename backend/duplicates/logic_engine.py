"""
Boolean logic evaluation engine for duplicate detection with AND/OR conditions
"""
import re
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from pipelines.field_types import FieldType
from pipelines.models import Field
from .models import URLExtractionRule, DuplicateRule

logger = logging.getLogger(__name__)


class FieldMatcher:
    """Field-type-aware matching functions"""
    
    def __init__(self, tenant_id: Optional[int] = None):
        self.tenant_id = tenant_id
        self._url_extraction_cache = {}
    
    def match_field(self, field: Field, value1: Any, value2: Any, match_type: str, url_extraction_rules: Optional[List[int]] = None) -> bool:
        """
        Match two field values using specified match type and field configuration
        
        Args:
            field: Pipeline field object with type and configuration
            value1: First value to compare
            value2: Second value to compare  
            match_type: Type of matching to perform
            url_extraction_rules: Optional list of specific URL extraction rule IDs to use (for url_normalized match_type)
            
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
                return self._match_email_normalized(value1, value2, field.field_config)
            
            elif match_type == 'phone_normalized':
                return self._match_phone_normalized(value1, value2, field.field_config)
            
            elif match_type == 'url_normalized':
                return self._match_url_normalized(value1, value2, field.field_config, url_extraction_rules)
            
            elif match_type == 'fuzzy':
                return self._match_fuzzy(value1, value2)
            
            elif match_type == 'numeric':
                return self._match_numeric(value1, value2, field.field_config)
            
            else:
                logger.warning(f"Unknown match type: {match_type}, falling back to exact match")
                return str(value1) == str(value2)
                
        except Exception as e:
            logger.error(f"Error matching field {field.name}: {e}", exc_info=True)
            return False
    
    def _match_email_normalized(self, value1: Any, value2: Any, field_config: Dict) -> bool:
        """Email matching with normalization based on EmailFieldConfig"""
        email1, email2 = str(value1), str(value2)
        
        # Use existing EmailFieldConfig settings
        if field_config.get('auto_lowercase', True):
            email1, email2 = email1.lower(), email2.lower()
        
        if field_config.get('trim_whitespace', True):
            email1, email2 = email1.strip(), email2.strip()
        
        return email1 == email2
    
    def _match_phone_normalized(self, value1: Any, value2: Any, field_config: Dict) -> bool:
        """Phone matching with normalization"""
        phone1 = self._extract_and_normalize_phone(value1)
        phone2 = self._extract_and_normalize_phone(value2)
        return phone1 == phone2
    
    def _extract_and_normalize_phone(self, value: Any) -> str:
        """Extract phone number from various formats and normalize"""
        if not value:
            return ""
        
        # Handle dict format from phone field type
        if isinstance(value, dict):
            # Phone field stores as {'number': '782270354', 'country_code': '+27'}
            country_code = value.get('country_code', '')
            number = value.get('number', '')
            # Combine country code and number
            phone_str = f"{country_code}{number}"
        else:
            # Handle string format
            phone_str = str(value)
        
        return self._normalize_phone(phone_str)
    
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
    
    def _match_url_normalized(self, value1: Any, value2: Any, field_config: Dict, url_extraction_rules: Optional[List[int]] = None) -> bool:
        """URL matching with configurable extraction"""
        url1 = self._normalize_url(str(value1), field_config, url_extraction_rules)
        url2 = self._normalize_url(str(value2), field_config, url_extraction_rules)
        return url1 == url2
    
    def _normalize_url(self, url: str, field_config: Dict, url_extraction_rules: Optional[List[int]] = None) -> str:
        """Normalize URL using field config and extraction rules"""
        if not url:
            return ""
        
        # Basic URL field config normalization
        normalized = url
        if field_config.get('trim_whitespace', True):
            normalized = normalized.strip()
        
        if field_config.get('auto_add_protocol', True):
            if not normalized.startswith(('http://', 'https://')):
                normalized = f"https://{normalized}"
        
        # Try URL extraction rules for this tenant
        if self.tenant_id:
            try:
                extraction_rules = self._get_field_specific_extraction_rules(url_extraction_rules)
                for rule in extraction_rules:
                    extracted = self._apply_url_extraction_rule(normalized, rule)
                    if extracted:
                        return extracted
            except Exception as e:
                logger.error(f"Error processing URL extraction rules: {e}")
                # Continue with fallback normalization
        
        # Fallback: basic domain + path normalization
        try:
            parsed = urlparse(normalized)
            domain = parsed.netloc.lower()
            path = parsed.path.strip('/')
            
            # Remove www
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return f"{domain}/{path}".rstrip('/')
        except:
            return normalized.lower()
    
    def _get_url_extraction_rules(self) -> List[URLExtractionRule]:
        """Get cached URL extraction rules for tenant"""
        if not self.tenant_id:
            return []
            
        if self.tenant_id not in self._url_extraction_cache:
            # Load rules that are active and belong to this tenant
            # Note: URLExtractionRule now has both tenant and pipeline fields
            self._url_extraction_cache[self.tenant_id] = list(
                URLExtractionRule.objects.filter(
                    tenant_id=self.tenant_id,
                    is_active=True
                ).select_related('pipeline')
            )
        return self._url_extraction_cache[self.tenant_id]
    
    def _get_field_specific_extraction_rules(self, url_extraction_rules: Optional[List[int]] = None) -> List[URLExtractionRule]:
        """Get field-specific URL extraction rules or all rules if none specified"""
        if url_extraction_rules is None:
            # Default behavior: use all tenant rules
            return self._get_url_extraction_rules()
        elif url_extraction_rules == "all":
            # Explicit "all" mode: use all tenant rules  
            return self._get_url_extraction_rules()
        elif isinstance(url_extraction_rules, list):
            # Specific rules mode: filter to only specified rule IDs
            all_rules = self._get_url_extraction_rules()
            return [rule for rule in all_rules if rule.id in url_extraction_rules]
        else:
            # Invalid format: fallback to all rules
            logger.warning(f"Invalid url_extraction_rules format: {url_extraction_rules}")
            return self._get_url_extraction_rules()
    
    def _apply_url_extraction_rule(self, url: str, rule: URLExtractionRule) -> Optional[str]:
        """Apply URL extraction rule to extract identifier"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Apply subdomain stripping if enabled
            if rule.strip_subdomains:
                domain = self._strip_subdomains(domain)
            
            # Check if domain matches rule patterns
            for pattern in rule.domain_patterns:
                if pattern == domain or (pattern.startswith('*.') and domain.endswith(pattern[2:])):
                    # Apply extraction pattern
                    full_url = f"{domain}{parsed.path}"
                    match = re.search(rule.extraction_pattern, full_url, re.IGNORECASE)
                    if match:
                        identifier = match.group(1) if match.groups() else match.group(0)
                        if not rule.case_sensitive:
                            identifier = identifier.lower()
                        return rule.extraction_format.format(identifier)
            return None
        except Exception as e:
            logger.error(f"Error applying URL extraction rule {rule.name}: {e}")
            return None
    
    def _match_fuzzy(self, value1: Any, value2: Any, threshold: float = 0.8) -> bool:
        """Simple fuzzy matching using difflib"""
        from difflib import SequenceMatcher
        
        str1, str2 = str(value1).lower(), str(value2).lower()
        similarity = SequenceMatcher(None, str1, str2).ratio()
        return similarity >= threshold
    
    def _match_numeric(self, value1: Any, value2: Any, field_config: Dict) -> bool:
        """Numeric matching with type-specific handling"""
        try:
            # Handle different number formats from NumberFieldConfig
            format_type = field_config.get('format', 'integer')
            
            if format_type == 'currency':
                # Remove currency symbols and compare numeric value
                num1 = float(re.sub(r'[^\d.]', '', str(value1)))
                num2 = float(re.sub(r'[^\d.]', '', str(value2)))
                return num1 == num2
            elif format_type == 'percentage':
                # Handle percentage formats
                num1 = float(str(value1).replace('%', ''))
                num2 = float(str(value2).replace('%', ''))
                return num1 == num2
            else:
                # Standard numeric comparison
                return float(value1) == float(value2)
        except (ValueError, TypeError):
            return False
    
    def _strip_subdomains(self, domain: str) -> str:
        """Strip subdomains to keep only the main domain"""
        if not domain:
            return domain
        
        # Split domain into parts
        parts = domain.split('.')
        
        # Need at least 2 parts for a valid domain (domain.tld)
        if len(parts) < 2:
            return domain
        
        # Handle common TLD patterns
        # For .co.uk, .com.au, etc., keep 3 parts (domain.co.uk)
        common_two_part_tlds = ['co.uk', 'com.au', 'co.nz', 'co.za', 'com.br', 'co.jp', 'co.in']
        
        # Check if domain ends with a two-part TLD
        if len(parts) >= 3:
            potential_tld = '.'.join(parts[-2:])
            if potential_tld in common_two_part_tlds:
                # Keep domain.co.uk format - take last 3 parts
                return '.'.join(parts[-3:])
        
        # For regular TLDs (.com, .org, .net), keep last 2 parts
        return '.'.join(parts[-2:])


class DuplicateLogicEngine:
    """Evaluates AND/OR logic for duplicate detection rules"""
    
    def __init__(self, tenant_id: Optional[int] = None):
        self.tenant_id = tenant_id
        self.field_matcher = FieldMatcher(tenant_id)
    
    def evaluate_rule(
        self, 
        rule: DuplicateRule, 
        record1_data: Dict[str, Any], 
        record2_data: Dict[str, Any]
    ) -> bool:
        """
        Evaluate duplicate rule against two records (simple boolean result)
        
        Returns:
            bool: True if records are duplicates according to the rule
        """
        detailed_result = self._detailed_evaluate_rule(rule, record1_data, record2_data)
        return detailed_result.get('is_duplicate', False)
    
    def _evaluate_logic_node(
        self, 
        logic_node: Dict[str, Any], 
        record1_data: Dict[str, Any], 
        record2_data: Dict[str, Any],
        pipeline: Any,
        result: Dict[str, Any]
    ) -> bool:
        """Recursively evaluate a logic node (AND/OR)"""
        
        operator = logic_node.get('operator', 'AND').upper()
        
        if operator == 'AND':
            return self._evaluate_and_condition(logic_node, record1_data, record2_data, pipeline, result)
        elif operator == 'OR':
            return self._evaluate_or_condition(logic_node, record1_data, record2_data, pipeline, result)
        else:
            logger.error(f"Unknown operator: {operator}")
            return False
    
    def _evaluate_and_condition(
        self, 
        logic_node: Dict[str, Any], 
        record1_data: Dict[str, Any], 
        record2_data: Dict[str, Any],
        pipeline: Any,
        result: Dict[str, Any]
    ) -> bool:
        """Evaluate AND condition - all fields must match"""
        
        fields = logic_node.get('fields', [])
        if not fields:
            return False
        
        condition_matches = []
        all_match = True
        
        for field_config in fields:
            field_name = field_config.get('field')
            match_type = field_config.get('match_type', 'exact')
            url_extraction_rules = field_config.get('url_extraction_rules')
            
            try:
                # Get field object - handle case where field doesn't exist
                # Try by slug first (most duplicate rules use slug), then fall back to name
                try:
                    field = pipeline.fields.get(slug=field_name)
                except Exception:
                    try:
                        field = pipeline.fields.get(name=field_name)
                    except Exception as field_error:
                        logger.error(f"Field '{field_name}' not found in pipeline '{pipeline.name}' (ID: {pipeline.id}): {field_error}")
                        # Create a minimal field object for basic matching
                        from pipelines.models import Field
                        field = Field(
                            name=field_name,
                            field_type='text',
                            field_config={},
                            pipeline=pipeline
                        )
                
                # Get field values
                value1 = record1_data.get(field_name)
                value2 = record2_data.get(field_name)
                
                # Evaluate field match
                field_matches = self.field_matcher.match_field(field, value1, value2, match_type, url_extraction_rules)
                
                # Store field match result
                result['field_matches'][field_name] = {
                    'match': field_matches,
                    'match_type': match_type,
                    'value1': value1,
                    'value2': value2
                }
                
                condition_matches.append({
                    'field': field_name,
                    'match_type': match_type,
                    'result': field_matches
                })
                
                if not field_matches:
                    all_match = False
                    break  # Short-circuit for AND
                    
            except Exception as e:
                logger.error(f"Error evaluating field {field_name}: {e}", exc_info=True)
                # Store error in result for debugging
                result['field_matches'][field_name] = {
                    'match': False,
                    'match_type': match_type,
                    'value1': record1_data.get(field_name),
                    'value2': record2_data.get(field_name),
                    'error': str(e)
                }
                all_match = False
                break
        
        if all_match and condition_matches:
            result['matched_conditions'].append({
                'operator': 'AND',
                'fields': condition_matches
            })
        
        return all_match
    
    def _evaluate_or_condition(
        self, 
        logic_node: Dict[str, Any], 
        record1_data: Dict[str, Any], 
        record2_data: Dict[str, Any],
        pipeline: Any,
        result: Dict[str, Any]
    ) -> bool:
        """Evaluate OR condition - any sub-condition can match"""
        
        conditions = logic_node.get('conditions', [])
        if not conditions:
            return False
        
        for condition in conditions:
            if self._evaluate_logic_node(condition, record1_data, record2_data, pipeline, result):
                return True  # Short-circuit for OR
        
        return False
    
    def get_matched_fields(
        self, 
        rule: DuplicateRule, 
        record1_data: Dict[str, Any], 
        record2_data: Dict[str, Any]
    ) -> List[str]:
        """
        Get list of field names that matched between two records
        
        Returns:
            List of field names that matched
        """
        result = self._detailed_evaluate_rule(rule, record1_data, record2_data)
        matched_fields = []
        
        for field_name, match_info in result.get('field_matches', {}).items():
            if match_info.get('match', False):
                matched_fields.append(field_name)
        
        return matched_fields
    
    def _detailed_evaluate_rule(
        self, 
        rule: DuplicateRule, 
        record1_data: Dict[str, Any], 
        record2_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Detailed evaluation of duplicate rule against two records
        
        Returns:
            dict: {
                'is_duplicate': bool,
                'matched_conditions': list,
                'field_matches': dict,
                'execution_details': dict
            }
        """
        
        try:
            result = {
                'is_duplicate': False,
                'matched_conditions': [],
                'field_matches': {},
                'execution_details': {
                    'rule_name': rule.name,
                    'logic': rule.logic,
                    'errors': []
                }
            }
            
            if not rule.logic:
                result['execution_details']['errors'].append("Rule has no logic defined")
                return result
            
            # Evaluate the logic tree
            is_duplicate = self._evaluate_logic_node(
                rule.logic, 
                record1_data, 
                record2_data, 
                rule.pipeline,
                result
            )
            
            result['is_duplicate'] = is_duplicate
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating duplicate rule {rule.name}: {e}", exc_info=True)
            return {
                'is_duplicate': False,
                'matched_conditions': [],
                'field_matches': {},
                'execution_details': {
                    'rule_name': rule.name,
                    'errors': [f"Evaluation error: {str(e)}"]
                }
            }