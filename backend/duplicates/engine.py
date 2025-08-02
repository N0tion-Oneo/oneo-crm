"""
Advanced duplicate detection engine with fuzzy matching algorithms
Multi-tenant support with comprehensive matching strategies
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime
from dataclasses import dataclass
from difflib import SequenceMatcher
import unicodedata

from django.db.models import Q
from django.utils import timezone
from django.conf import settings

# Optional imports for advanced algorithms - graceful fallback if not available
try:
    from fuzzywuzzy import fuzz
    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False

try:
    import phonetics
    PHONETICS_AVAILABLE = True
except ImportError:
    PHONETICS_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from pipelines.models import Record
from .models import (
    DuplicateRule, DuplicateFieldRule, DuplicateMatch, 
    DuplicateAnalytics, DuplicateExclusion
)


logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of a field match comparison"""
    field_name: str
    match_type: str
    score: float
    value1: Any
    value2: Any
    normalized_value1: str = ""
    normalized_value2: str = ""
    algorithm_used: str = ""
    execution_time_ms: float = 0.0


@dataclass
class DuplicateCandidate:
    """Potential duplicate record candidate"""
    record_id: str
    record_data: Dict[str, Any]
    overall_score: float
    field_matches: List[MatchResult]
    confidence_breakdown: Dict[str, float]


class DuplicateDetectionEngine:
    """
    Advanced duplicate detection engine with multiple matching algorithms
    Supports fuzzy matching, phonetic matching, and semantic similarity
    """
    
    def __init__(self, tenant_id: Optional[int] = None):
        self.tenant_id = tenant_id
        self._initialize_algorithms()
    
    def _initialize_algorithms(self):
        """Initialize available matching algorithms"""
        self.algorithms = {
            'exact': self._exact_match,
            'case_insensitive': self._case_insensitive_match,
            'levenshtein': self._levenshtein_match,
            'jaro_winkler': self._jaro_winkler_match,
            'fuzzy': self._fuzzy_match,
            'soundex': self._soundex_match,
            'metaphone': self._metaphone_match,
            'cosine': self._cosine_similarity_match,
            'jaccard': self._jaccard_similarity_match,
            'partial': self._partial_match,
            'email_domain': self._email_domain_match,
            'phone_normalized': self._phone_normalized_match,
            'regex': self._regex_match,
        }
    
    async def detect_duplicates(
        self, 
        record_data: Dict[str, Any], 
        pipeline_id: int,
        exclude_record_id: Optional[str] = None,
        rule_id: Optional[int] = None
    ) -> List[DuplicateCandidate]:
        """
        Main entry point for duplicate detection
        
        Args:
            record_data: Data of the record to check for duplicates
            pipeline_id: Pipeline ID to search within
            exclude_record_id: Record ID to exclude from search (for updates)
            rule_id: Specific rule ID to use, or None for all active rules
            
        Returns:
            List of potential duplicate candidates with scores
        """
        start_time = datetime.now()
        
        try:
            # Get applicable duplicate rules
            rules_query = DuplicateRule.objects.filter(
                tenant_id=self.tenant_id,
                pipeline_id=pipeline_id,
                is_active=True
            )
            
            if rule_id:
                rules_query = rules_query.filter(id=rule_id)
            
            rules = list(rules_query.prefetch_related('field_rules__field'))
            
            if not rules:
                logger.info(f"No duplicate rules found for pipeline {pipeline_id}")
                return []
            
            all_candidates = []
            
            # Process each rule
            for rule in rules:
                candidates = await self._process_rule(
                    rule, record_data, exclude_record_id
                )
                all_candidates.extend(candidates)
            
            # Deduplicate and sort candidates
            unique_candidates = self._deduplicate_candidates(all_candidates)
            sorted_candidates = sorted(
                unique_candidates, 
                key=lambda x: x.overall_score, 
                reverse=True
            )
            
            # Log execution time
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds() * 1000
            logger.info(f"Duplicate detection completed in {execution_time:.2f}ms")
            
            return sorted_candidates
            
        except Exception as e:
            logger.error(f"Duplicate detection error: {e}", exc_info=True)
            return []
    
    async def _process_rule(
        self,
        rule: DuplicateRule,
        record_data: Dict[str, Any],
        exclude_record_id: Optional[str] = None
    ) -> List[DuplicateCandidate]:
        """Process a single duplicate rule"""
        
        # Get field rules
        field_rules = list(rule.field_rules.filter(is_active=True))
        if not field_rules:
            return []
        
        # Get potential candidate records
        candidates = await self._get_candidate_records(
            rule, record_data, field_rules, exclude_record_id
        )
        
        if not candidates:
            return []
        
        # Score each candidate
        scored_candidates = []
        for candidate_record in candidates:
            candidate = await self._score_candidate(
                rule, field_rules, record_data, candidate_record
            )
            if candidate and candidate.overall_score >= rule.confidence_threshold:
                scored_candidates.append(candidate)
        
        return scored_candidates
    
    async def _get_candidate_records(
        self,
        rule: DuplicateRule,
        record_data: Dict[str, Any],
        field_rules: List[DuplicateFieldRule],
        exclude_record_id: Optional[str] = None
    ) -> List[Record]:
        """Get potential candidate records for comparison"""
        
        # Build query for potential matches
        query = Q(pipeline_id=rule.pipeline_id)
        
        if exclude_record_id:
            query &= ~Q(id=exclude_record_id)
        
        # Add field-specific filters for performance
        for field_rule in field_rules:
            field_name = field_rule.field.name
            field_value = record_data.get(field_name)
            
            if not field_value:
                continue
            
            # Add database-level filters for exact/partial matches
            if field_rule.match_type in ['exact', 'case_insensitive']:
                if field_rule.match_type == 'case_insensitive':
                    query &= Q(**{f'data__{field_name}__iexact': field_value})
                else:
                    query &= Q(**{f'data__{field_name}': field_value})
            elif field_rule.match_type == 'partial':
                query &= Q(**{f'data__{field_name}__icontains': field_value})
        
        # Execute query with limit for performance
        candidates = list(
            Record.objects.filter(query)
            .select_related('pipeline')
            .order_by('-updated_at')[:1000]  # Limit candidates for performance
        )
        
        return candidates
    
    async def _score_candidate(
        self,
        rule: DuplicateRule,
        field_rules: List[DuplicateFieldRule],
        record_data: Dict[str, Any],
        candidate_record: Record
    ) -> Optional[DuplicateCandidate]:
        """Score a candidate record against the input data"""
        
        field_matches = []
        total_weighted_score = 0.0
        total_weight = 0.0
        confidence_breakdown = {}
        
        # Process each field rule
        for field_rule in field_rules:
            field_name = field_rule.field.name
            input_value = record_data.get(field_name)
            candidate_value = candidate_record.data.get(field_name)
            
            # Skip if either value is empty and not required
            if not input_value and not candidate_value:
                continue
            
            if field_rule.is_required and (not input_value or not candidate_value):
                # Required field missing - candidate fails
                return None
            
            # Calculate field match score
            match_result = await self._calculate_field_match(
                field_rule, input_value, candidate_value
            )
            
            field_matches.append(match_result)
            
            # Weight the score
            weighted_score = match_result.score * field_rule.weight
            total_weighted_score += weighted_score
            total_weight += field_rule.weight
            
            confidence_breakdown[field_name] = {
                'score': match_result.score,
                'weight': field_rule.weight,
                'weighted_score': weighted_score,
                'match_type': match_result.match_type,
                'algorithm': match_result.algorithm_used
            }
        
        # Calculate overall score
        if total_weight == 0:
            return None
        
        overall_score = total_weighted_score / total_weight
        
        # Apply rule-specific adjustments
        if rule.enable_fuzzy_matching and overall_score < rule.confidence_threshold:
            # Try fuzzy enhancement
            overall_score = self._enhance_with_fuzzy_logic(
                field_matches, overall_score, rule
            )
        
        return DuplicateCandidate(
            record_id=candidate_record.id,
            record_data=candidate_record.data,
            overall_score=overall_score,
            field_matches=field_matches,
            confidence_breakdown=confidence_breakdown
        )
    
    async def _calculate_field_match(
        self,
        field_rule: DuplicateFieldRule,
        value1: Any,
        value2: Any
    ) -> MatchResult:
        """Calculate match score for a specific field"""
        start_time = datetime.now()
        
        # Initialize result
        result = MatchResult(
            field_name=field_rule.field.name,
            match_type=field_rule.match_type,
            score=0.0,
            value1=value1,
            value2=value2
        )
        
        try:
            # Preprocess values
            processed_value1 = self._preprocess_value(
                value1, field_rule.preprocessing_rules
            )
            processed_value2 = self._preprocess_value(
                value2, field_rule.preprocessing_rules
            )
            
            result.normalized_value1 = processed_value1
            result.normalized_value2 = processed_value2
            
            # Get matching algorithm
            algorithm = self.algorithms.get(field_rule.match_type)
            if not algorithm:
                logger.warning(f"Unknown match type: {field_rule.match_type}")
                return result
            
            # Calculate match score
            result.score = algorithm(
                processed_value1, 
                processed_value2, 
                field_rule
            )
            result.algorithm_used = field_rule.match_type
            
        except Exception as e:
            logger.error(f"Field match calculation error: {e}", exc_info=True)
            result.score = 0.0
        
        # Calculate execution time
        end_time = datetime.now()
        result.execution_time_ms = (end_time - start_time).total_seconds() * 1000
        
        return result
    
    def _preprocess_value(self, value: Any, preprocessing_rules: Dict[str, Any]) -> str:
        """Preprocess value according to rules"""
        if value is None:
            return ""
        
        str_value = str(value)
        
        # Apply preprocessing rules
        if preprocessing_rules.get('normalize_case', True):
            str_value = str_value.lower()
        
        if preprocessing_rules.get('remove_punctuation', False):
            str_value = re.sub(r'[^\w\s]', '', str_value)
        
        if preprocessing_rules.get('normalize_whitespace', True):
            str_value = re.sub(r'\s+', ' ', str_value.strip())
        
        if preprocessing_rules.get('remove_accents', False):
            str_value = self._remove_accents(str_value)
        
        if preprocessing_rules.get('normalize_phone', False):
            str_value = self._normalize_phone(str_value)
        
        if preprocessing_rules.get('normalize_company', False):
            str_value = self._normalize_company_name(str_value)
        
        return str_value
    
    # Matching algorithms
    def _exact_match(self, value1: str, value2: str, field_rule: DuplicateFieldRule) -> float:
        """Exact string match"""
        return 1.0 if value1 == value2 else 0.0
    
    def _case_insensitive_match(self, value1: str, value2: str, field_rule: DuplicateFieldRule) -> float:
        """Case-insensitive match"""
        return 1.0 if value1.lower() == value2.lower() else 0.0
    
    def _levenshtein_match(self, value1: str, value2: str, field_rule: DuplicateFieldRule) -> float:
        """Levenshtein distance-based matching"""
        if not value1 or not value2:
            return 0.0
        
        if FUZZYWUZZY_AVAILABLE:
            return fuzz.ratio(value1, value2) / 100.0
        else:
            # Fallback implementation using SequenceMatcher
            return SequenceMatcher(None, value1, value2).ratio()
    
    def _jaro_winkler_match(self, value1: str, value2: str, field_rule: DuplicateFieldRule) -> float:
        """Jaro-Winkler similarity"""
        if FUZZYWUZZY_AVAILABLE:
            return fuzz.token_sort_ratio(value1, value2) / 100.0
        else:
            # Fallback to basic similarity
            return SequenceMatcher(None, value1, value2).ratio()
    
    def _fuzzy_match(self, value1: str, value2: str, field_rule: DuplicateFieldRule) -> float:
        """Fuzzy string matching with multiple algorithms"""
        if not value1 or not value2:
            return 0.0
        
        if FUZZYWUZZY_AVAILABLE:
            # Use multiple fuzzy algorithms and take the best score
            scores = [
                fuzz.ratio(value1, value2),
                fuzz.partial_ratio(value1, value2),
                fuzz.token_sort_ratio(value1, value2),
                fuzz.token_set_ratio(value1, value2)
            ]
            return max(scores) / 100.0
        else:
            return SequenceMatcher(None, value1, value2).ratio()
    
    def _soundex_match(self, value1: str, value2: str, field_rule: DuplicateFieldRule) -> float:
        """Soundex phonetic matching"""
        if not value1 or not value2:
            return 0.0
        
        if PHONETICS_AVAILABLE:
            soundex1 = phonetics.soundex(value1)
            soundex2 = phonetics.soundex(value2)
            return 1.0 if soundex1 == soundex2 else 0.0
        else:
            # Simple fallback soundex implementation
            return 1.0 if self._simple_soundex(value1) == self._simple_soundex(value2) else 0.0
    
    def _metaphone_match(self, value1: str, value2: str, field_rule: DuplicateFieldRule) -> float:
        """Metaphone phonetic matching"""
        if not value1 or not value2:
            return 0.0
        
        if PHONETICS_AVAILABLE:
            metaphone1 = phonetics.metaphone(value1)
            metaphone2 = phonetics.metaphone(value2)
            return 1.0 if metaphone1 == metaphone2 else 0.0
        else:
            # Fallback to soundex
            return self._soundex_match(value1, value2, field_rule)
    
    def _cosine_similarity_match(self, value1: str, value2: str, field_rule: DuplicateFieldRule) -> float:
        """Cosine similarity using TF-IDF vectors"""
        if not value1 or not value2:
            return 0.0
        
        if SKLEARN_AVAILABLE:
            try:
                vectorizer = TfidfVectorizer(ngram_range=(1, 2))
                tfidf_matrix = vectorizer.fit_transform([value1, value2])
                similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
                return float(similarity[0][0])
            except:
                pass
        
        # Fallback to token-based similarity
        return self._token_similarity(value1, value2)
    
    def _jaccard_similarity_match(self, value1: str, value2: str, field_rule: DuplicateFieldRule) -> float:
        """Jaccard similarity coefficient"""
        if not value1 or not value2:
            return 0.0
        
        set1 = set(value1.lower().split())
        set2 = set(value2.lower().split())
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _partial_match(self, value1: str, value2: str, field_rule: DuplicateFieldRule) -> float:
        """Partial string matching"""
        if not value1 or not value2:
            return 0.0
        
        if FUZZYWUZZY_AVAILABLE:
            return fuzz.partial_ratio(value1, value2) / 100.0
        else:
            # Check if one string is contained in the other
            v1_lower = value1.lower()
            v2_lower = value2.lower()
            
            if v1_lower in v2_lower or v2_lower in v1_lower:
                return min(len(v1_lower), len(v2_lower)) / max(len(v1_lower), len(v2_lower))
            
            return 0.0
    
    def _email_domain_match(self, value1: str, value2: str, field_rule: DuplicateFieldRule) -> float:
        """Email domain matching"""
        if not value1 or not value2:
            return 0.0
        
        try:
            domain1 = value1.split('@')[1].lower() if '@' in value1 else value1.lower()
            domain2 = value2.split('@')[1].lower() if '@' in value2 else value2.lower()
            return 1.0 if domain1 == domain2 else 0.0
        except IndexError:
            return 0.0
    
    def _phone_normalized_match(self, value1: str, value2: str, field_rule: DuplicateFieldRule) -> float:
        """Normalized phone number matching"""
        if not value1 or not value2:
            return 0.0
        
        norm1 = self._normalize_phone(value1)
        norm2 = self._normalize_phone(value2)
        
        return 1.0 if norm1 == norm2 else 0.0
    
    def _regex_match(self, value1: str, value2: str, field_rule: DuplicateFieldRule) -> float:
        """Custom regex-based matching"""
        if not value1 or not value2:
            return 0.0
        
        pattern = field_rule.custom_regex
        if not pattern:
            return 0.0
        
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            match1 = regex.search(value1)
            match2 = regex.search(value2)
            
            if match1 and match2:
                return 1.0 if match1.group() == match2.group() else 0.0
            
            return 0.0
        except re.error:
            logger.warning(f"Invalid regex pattern: {pattern}")
            return 0.0
    
    # Helper methods
    def _token_similarity(self, value1: str, value2: str) -> float:
        """Simple token-based similarity"""
        tokens1 = set(value1.lower().split())
        tokens2 = set(value2.lower().split())
        
        if not tokens1 and not tokens2:
            return 1.0
        
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        
        return intersection / union if union > 0 else 0.0
    
    def _simple_soundex(self, text: str) -> str:
        """Simple Soundex implementation"""
        if not text:
            return ""
        
        text = text.upper()
        soundex = text[0]
        
        # Mapping of letters to soundex codes
        mapping = {
            'BFPV': '1', 'CGJKQSXZ': '2', 'DT': '3',
            'L': '4', 'MN': '5', 'R': '6'
        }
        
        for char in text[1:]:
            for letters, code in mapping.items():
                if char in letters:
                    if soundex[-1] != code:
                        soundex += code
                    break
        
        # Pad with zeros or truncate to 4 characters
        soundex = soundex + '000'
        return soundex[:4]
    
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
    
    def _normalize_company_name(self, company: str) -> str:
        """Normalize company name for comparison"""
        if not company:
            return ""
        
        normalized = company.lower().strip()
        
        # Remove common suffixes
        suffixes = [
            'inc', 'inc.', 'incorporated', 'corp', 'corp.', 'corporation',
            'llc', 'l.l.c.', 'ltd', 'ltd.', 'limited', 'co', 'co.',
            'company', 'lp', 'l.p.'
        ]
        
        for suffix in suffixes:
            if normalized.endswith(f' {suffix}'):
                normalized = normalized[:-len(suffix)-1].strip()
        
        # Remove punctuation and normalize whitespace
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized
    
    def _remove_accents(self, text: str) -> str:
        """Remove accented characters"""
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
    
    def _enhance_with_fuzzy_logic(
        self, 
        field_matches: List[MatchResult], 
        base_score: float, 
        rule: DuplicateRule
    ) -> float:
        """Apply fuzzy logic enhancement to improve matching"""
        
        # Look for high-confidence matches in key fields
        high_confidence_fields = []
        for match in field_matches:
            if match.score > 0.9:  # Very high confidence
                high_confidence_fields.append(match)
        
        # Boost score if we have strong matches in multiple fields
        if len(high_confidence_fields) >= 2:
            boost = min(0.1, len(high_confidence_fields) * 0.05)
            return min(1.0, base_score + boost)
        
        return base_score
    
    def _deduplicate_candidates(
        self, 
        candidates: List[DuplicateCandidate]
    ) -> List[DuplicateCandidate]:
        """Remove duplicate candidates from different rules"""
        seen_records = set()
        unique_candidates = []
        
        for candidate in candidates:
            if candidate.record_id not in seen_records:
                seen_records.add(candidate.record_id)
                unique_candidates.append(candidate)
            else:
                # If we've seen this record, keep the one with higher score
                for i, existing in enumerate(unique_candidates):
                    if existing.record_id == candidate.record_id:
                        if candidate.overall_score > existing.overall_score:
                            unique_candidates[i] = candidate
                        break
        
        return unique_candidates