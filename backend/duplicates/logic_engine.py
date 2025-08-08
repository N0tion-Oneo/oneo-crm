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
    
    def match_field(self, field: Field, value1: Any, value2: Any, match_type: str) -> bool:
        """
        Match two field values using specified match type and field configuration
        
        Args:
            field: Pipeline field object with type and configuration
            value1: First value to compare
            value2: Second value to compare  
            match_type: Type of matching to perform
            
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
                return self._match_url_normalized(value1, value2, field.field_config)
            
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
        """URL matching with configurable extraction"""
        url1 = self._normalize_url(str(value1), field_config)
        url2 = self._normalize_url(str(value2), field_config)
        return url1 == url2
    
    def _normalize_url(self, url: str, field_config: Dict) -> str:
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
            extraction_rules = self._get_url_extraction_rules()
            for rule in extraction_rules:
                extracted = self._apply_url_extraction_rule(normalized, rule)
                if extracted:
                    return extracted
        
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
        if self.tenant_id not in self._url_extraction_cache:
            self._url_extraction_cache[self.tenant_id] = list(
                URLExtractionRule.objects.filter(
                    tenant_id=self.tenant_id,
                    is_active=True
                )
            )
        return self._url_extraction_cache[self.tenant_id]
    
    def _apply_url_extraction_rule(self, url: str, rule: URLExtractionRule) -> Optional[str]:
        """Apply URL extraction rule to extract identifier"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
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
            
            try:
                # Get field object
                field = pipeline.fields.get(name=field_name)
                
                # Get field values
                value1 = record1_data.get(field_name)
                value2 = record2_data.get(field_name)
                
                # Evaluate field match
                field_matches = self.field_matcher.match_field(field, value1, value2, match_type)
                
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
                logger.error(f"Error evaluating field {field_name}: {e}")
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