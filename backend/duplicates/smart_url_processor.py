"""
Smart URL Processor - Intelligent URL normalization and extraction
Handles all real-world URL variations including protocols, domains, parameters, and edge cases.
"""
import re
import logging
from urllib.parse import urlparse, parse_qs, unquote
from typing import Dict, List, Optional, Any, NamedTuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class URLTemplate:
    """Template for URL extraction with intelligent rules"""
    name: str
    domains: List[str]  # Supported domains including wildcards
    path_patterns: List[str]  # Path patterns like "/in/{username}"
    identifier_regex: str  # Regex to extract identifier
    normalization_rules: Dict[str, Any]  # Cleanup rules
    mobile_schemes: List[str] = None  # Mobile app schemes like linkedin://
    
    def __post_init__(self):
        if self.mobile_schemes is None:
            self.mobile_schemes = []


class ExtractResult(NamedTuple):
    """Result of URL extraction with processing details"""
    original: str
    normalized: str
    extracted: Optional[str]
    success: bool
    processing_steps: List[str]
    error: Optional[str] = None


class SmartURLProcessor:
    """Intelligent URL processor that handles all real-world URL variations"""
    
    def __init__(self):
        self.templates = self._load_builtin_templates()
    
    def _load_builtin_templates(self) -> Dict[str, URLTemplate]:
        """Load built-in templates for major platforms"""
        return {
            'domain': URLTemplate(
                name="Domain Name",
                domains=["*"],
                path_patterns=["/", "/{path}", "/{path}/{subpath}"],
                identifier_regex=r"([a-zA-Z0-9\-\.]+)",
                normalization_rules={
                    "remove_protocol": True,
                    "remove_www": True,
                    "remove_subdomains": [],
                    "remove_params": [],
                    "remove_trailing_slash": True,
                    "case_sensitive": False,
                    "strip_whitespace": True,
                    "normalize_separators": False,
                    "strip_subdomains": False  # NEW: Option to strip all subdomains
                }
            ),
            
            'linkedin': URLTemplate(
                name="LinkedIn Profile",
                domains=["linkedin.com", "*.linkedin.com", "lnkd.in"],
                path_patterns=["/in/{username}", "/profile/{username}"],
                identifier_regex=r"([a-zA-Z0-9\-\.\\_]+)",
                mobile_schemes=["linkedin://"],
                normalization_rules={
                    "remove_protocol": True,
                    "remove_www": True,
                    "remove_subdomains": ["za", "uk", "au", "ca", "de", "fr", "es", "it", "nl", "br"],
                    "remove_params": [
                        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
                        "trk", "originalSubdomain", "original_referer", "_l"
                    ],
                    "remove_trailing_slash": True,
                    "case_sensitive": False,
                    "strip_whitespace": True,
                    "normalize_separators": True  # Convert underscores/hyphens consistently
                }
            ),
            
            'linkedin-company': URLTemplate(
                name="LinkedIn Company",
                domains=["linkedin.com", "*.linkedin.com", "lnkd.in"],
                path_patterns=["/company/{username}", "/school/{username}", "/organization/{username}"],
                identifier_regex=r"([a-zA-Z0-9\-\.\\_]+)",
                mobile_schemes=["linkedin://"],
                normalization_rules={
                    "remove_protocol": True,
                    "remove_www": True,
                    "remove_subdomains": ["za", "uk", "au", "ca", "de", "fr", "es", "it", "nl", "br"],
                    "remove_params": [
                        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
                        "trk", "originalSubdomain", "original_referer", "_l"
                    ],
                    "remove_trailing_slash": True,
                    "case_sensitive": False,
                    "strip_whitespace": True,
                    "normalize_separators": False  # Fixed: Disable separator normalization
                }
            ),
            
            'github': URLTemplate(
                name="GitHub Profile",
                domains=["github.com", "*.github.com"],
                path_patterns=["/{username}", "/users/{username}"],
                identifier_regex=r"([a-zA-Z0-9\-\_]+)",
                normalization_rules={
                    "remove_protocol": True,
                    "remove_www": True,
                    "remove_subdomains": ["www", "api", "raw"],
                    "remove_params": ["tab", "ref", "utm_source", "utm_medium", "utm_campaign"],
                    "remove_trailing_slash": True,
                    "case_sensitive": True,  # GitHub usernames are case-sensitive
                    "strip_whitespace": True,
                    "exclude_paths": [
                        "marketplace", "pricing", "features", "enterprise", 
                        "collections", "about", "contact", "security", "orgs", "organizations"
                    ]
                }
            ),
            
            'twitter': URLTemplate(
                name="Twitter/X Profile",
                domains=["twitter.com", "x.com", "*.twitter.com", "*.x.com"],
                path_patterns=["/{username}"],
                identifier_regex=r"([a-zA-Z0-9_]+)",
                normalization_rules={
                    "remove_protocol": True,
                    "remove_www": True,
                    "remove_subdomains": ["mobile", "m"],
                    "remove_params": ["s", "t", "utm_source", "utm_medium", "ref_src", "ref_url"],
                    "remove_trailing_slash": True,
                    "case_sensitive": False,
                    "strip_whitespace": True,
                    "exclude_paths": [
                        "i", "search", "hashtag", "explore", "settings", 
                        "privacy", "help", "support", "tos", "login", "intent"
                    ]
                }
            ),
            
            'instagram': URLTemplate(
                name="Instagram Profile",
                domains=["instagram.com", "*.instagram.com", "instagr.am"],
                path_patterns=["/{username}"],
                identifier_regex=r"([a-zA-Z0-9_\.]+)",
                normalization_rules={
                    "remove_protocol": True,
                    "remove_www": True,
                    "remove_subdomains": ["m", "help"],
                    "remove_params": ["hl", "igshid", "utm_source", "utm_medium"],
                    "remove_trailing_slash": True,
                    "case_sensitive": False,
                    "strip_whitespace": True,
                    "exclude_paths": [
                        "p", "explore", "accounts", "stories", "reels", "tv", "direct",
                        "about", "help", "press", "api", "jobs", "privacy", "terms"
                    ]
                }
            ),
            
            'youtube': URLTemplate(
                name="YouTube Channel",
                domains=["youtube.com", "*.youtube.com", "youtu.be"],
                path_patterns=["/c/{username}", "/channel/{username}", "/user/{username}", "/@{username}"],
                identifier_regex=r"([a-zA-Z0-9_\-]+)",
                normalization_rules={
                    "remove_protocol": True,
                    "remove_www": True,
                    "remove_subdomains": ["m", "music", "gaming"],
                    "remove_params": [
                        "feature", "app", "utm_source", "utm_medium", "utm_campaign", 
                        "si", "t", "list", "index"
                    ],
                    "remove_trailing_slash": True,
                    "case_sensitive": True,
                    "strip_whitespace": True
                }
            ),
            
            'facebook': URLTemplate(
                name="Facebook Profile",
                domains=["facebook.com", "fb.com", "*.facebook.com", "m.facebook.com"],
                path_patterns=["/{username}", "/profile.php"],
                identifier_regex=r"([a-zA-Z0-9\.]+)",
                normalization_rules={
                    "remove_protocol": True,
                    "remove_www": True,
                    "remove_subdomains": ["m", "mobile", "touch"],
                    "remove_params": [
                        "fref", "ref", "utm_source", "utm_medium", "utm_campaign",
                        "__tn__", "__xts__", "hash", "source"
                    ],
                    "remove_trailing_slash": True,
                    "case_sensitive": False,
                    "strip_whitespace": True,
                    "exclude_paths": [
                        "pages", "groups", "events", "marketplace", "watch", 
                        "gaming", "help", "privacy", "terms"
                    ]
                }
            )
        }
    
    def normalize_url(self, url: str, template_name: str = None, custom_template: URLTemplate = None) -> ExtractResult:
        """
        Normalize URL using intelligent multi-stage processing
        
        Args:
            url: Raw URL to process
            template_name: Name of built-in template to use
            custom_template: Custom template for advanced users
            
        Returns:
            ExtractResult with original, normalized, extracted values and processing steps
        """
        if not url or not url.strip():
            return ExtractResult("", "", None, False, [], "Empty URL")
        
        original_url = url.strip()
        processing_steps = []
        
        try:
            # Determine which template to use
            if custom_template:
                # Special handling for domain templates with strip_subdomains option
                if (custom_template.name == "Domain Name" or 
                    custom_template.domains == ["*"] and 
                    custom_template.normalization_rules.get('strip_subdomains') is not None):
                    
                    strip_subdomains = custom_template.normalization_rules.get('strip_subdomains', False)
                    return self._domain_url_processing(original_url, strip_subdomains=strip_subdomains)
                
                template = custom_template
                processing_steps.append("using_custom_template")
            elif template_name == 'generic':
                # Use generic processing when explicitly requested
                return self._generic_url_processing(original_url)
            elif template_name == 'domain':
                # Use domain-specific processing when explicitly requested
                # For built-in domain template, don't strip subdomains by default
                return self._domain_url_processing(original_url, strip_subdomains=False)
            elif template_name and template_name in self.templates:
                template = self.templates[template_name]
                processing_steps.append(f"using_template_{template_name}")
            else:
                # No template specified - use generic processing
                return self._generic_url_processing(original_url)
            
            # Stage 1: Protocol & Scheme Handling
            normalized_url = self._normalize_protocol(original_url, template)
            if normalized_url != original_url:
                processing_steps.append("normalized_protocol")
            
            # Stage 2: Domain Processing
            normalized_url = self._normalize_domain(normalized_url, template)
            processing_steps.append("normalized_domain")
            
            # Stage 3: Parameter Cleanup
            cleaned_url = self._remove_tracking_params(normalized_url, template)
            if cleaned_url != normalized_url:
                processing_steps.append("removed_params")
                normalized_url = cleaned_url
            
            # Stage 4: Path Processing & Identifier Extraction
            extracted_id = self._extract_identifier(normalized_url, template)
            if extracted_id:
                processing_steps.append("extracted_identifier")
            
                # Stage 5: Identifier Normalization
                final_id = self._normalize_identifier(extracted_id, template)
                if final_id != extracted_id:
                    processing_steps.append("normalized_identifier")
                extracted_id = final_id
            
            return ExtractResult(
                original=original_url,
                normalized=normalized_url,
                extracted=extracted_id,
                success=bool(extracted_id),
                processing_steps=processing_steps,
                error=None if extracted_id else "Could not extract identifier"
            )
            
        except Exception as e:
            logger.error(f"Error processing URL {original_url}: {e}", exc_info=True)
            return ExtractResult(
                original=original_url,
                normalized=original_url,
                extracted=None,
                success=False,
                processing_steps=processing_steps,
                error=str(e)
            )
    
    def _auto_detect_template(self, url: str) -> Optional[URLTemplate]:
        """Auto-detect which template to use based on the URL domain"""
        try:
            # Handle URLs without protocol
            if not url.startswith(('http://', 'https://', 'linkedin://', 'twitter://')):
                url = f"https://{url}"
            
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www prefix for matching
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Check each template's domains
            for template in self.templates.values():
                for template_domain in template.domains:
                    if template_domain.startswith('*.'):
                        # Wildcard domain matching
                        base_domain = template_domain[2:]
                        if domain.endswith(base_domain):
                            return template
                    elif domain == template_domain:
                        return template
            
            return None
            
        except Exception as e:
            logger.error(f"Error auto-detecting template for {url}: {e}")
            return None
    
    def _normalize_protocol(self, url: str, template: URLTemplate) -> str:
        """Handle protocol variations and mobile schemes"""
        # Handle mobile schemes (linkedin://, twitter://, etc.)
        for scheme in template.mobile_schemes:
            if url.startswith(scheme):
                # Convert mobile scheme to https
                remainder = url[len(scheme):]
                return f"https://{template.domains[0]}{remainder}"
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            return f"https://{url}"
        
        # Normalize to https
        if template.normalization_rules.get('remove_protocol', False):
            if url.startswith(('http://', 'https://')):
                return url.split('://', 1)[1]
        
        return url
    
    def _normalize_domain(self, url: str, template: URLTemplate) -> str:
        """Normalize domain including www, subdomains, and locale codes"""
        try:
            # Handle URL without protocol
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www if specified
            if template.normalization_rules.get('remove_www', False) and domain.startswith('www.'):
                domain = domain[4:]
            
            # Remove locale/country subdomains
            remove_subdomains = template.normalization_rules.get('remove_subdomains', [])
            for subdomain in remove_subdomains:
                if domain.startswith(f"{subdomain}."):
                    domain = domain[len(subdomain)+1:]
                    break
            
            # Reconstruct URL
            return f"{parsed.scheme}://{domain}{parsed.path}{parsed.params}" + \
                   (f"?{parsed.query}" if parsed.query else "") + \
                   (f"#{parsed.fragment}" if parsed.fragment else "")
            
        except Exception as e:
            logger.error(f"Error normalizing domain for {url}: {e}")
            return url
    
    def _remove_tracking_params(self, url: str, template: URLTemplate) -> str:
        """Remove tracking parameters and UTM codes"""
        try:
            parsed = urlparse(url)
            if not parsed.query:
                return url
            
            params_to_remove = template.normalization_rules.get('remove_params', [])
            if not params_to_remove:
                return url
            
            # Parse query parameters
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            
            # Remove specified parameters (including wildcard matching)
            cleaned_params = {}
            for key, values in query_params.items():
                should_remove = False
                
                for param_pattern in params_to_remove:
                    if param_pattern.endswith('*'):
                        # Wildcard matching (e.g., "utm_*")
                        if key.startswith(param_pattern[:-1]):
                            should_remove = True
                            break
                    elif key == param_pattern:
                        should_remove = True
                        break
                
                if not should_remove:
                    cleaned_params[key] = values
            
            # Reconstruct query string
            if cleaned_params:
                query_pairs = []
                for key, values in cleaned_params.items():
                    for value in values:
                        query_pairs.append(f"{key}={value}")
                new_query = "&".join(query_pairs)
            else:
                new_query = ""
            
            # Reconstruct URL
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}" + \
                   (f"?{new_query}" if new_query else "")
            
        except Exception as e:
            logger.error(f"Error removing tracking params from {url}: {e}")
            return url
    
    def _extract_identifier(self, url: str, template: URLTemplate) -> Optional[str]:
        """Extract identifier from URL path using template patterns"""
        try:
            parsed = urlparse(url)
            path = parsed.path.strip('/')
            
            # DEBUG: Log the extraction process
            logger.info(f"Extracting from URL: {url}")
            logger.info(f"Path: '{path}'")
            logger.info(f"Template name: {template.name}")
            logger.info(f"Template regex: '{template.identifier_regex}'")
            
            # Remove trailing slash if specified
            if template.normalization_rules.get('remove_trailing_slash', False):
                path = path.rstrip('/')
            
            # Check excluded paths
            excluded_paths = template.normalization_rules.get('exclude_paths', [])
            path_parts = path.split('/')
            if path_parts and path_parts[0] in excluded_paths:
                return None
            
            # Try each path pattern
            for path_pattern in template.path_patterns:
                if '{username}' in path_pattern:
                    # Convert pattern to regex - strip leading slash to match path without leading slash
                    normalized_pattern = path_pattern.lstrip('/')
                    pattern_regex = normalized_pattern.replace('{username}', template.identifier_regex)
                    pattern_regex = pattern_regex.replace('/', '\\/')
                    pattern_regex = f"^{pattern_regex}$"
                    
                    logger.info(f"Testing pattern: '{path_pattern}' -> '{pattern_regex}' against path: '{path}'")
                    
                    match = re.search(pattern_regex, path, re.IGNORECASE if not template.normalization_rules.get('case_sensitive', False) else 0)
                    if match and match.groups():
                        extracted = match.group(1)
                        logger.info(f"SUCCESS: Extracted '{extracted}'")
                        return extracted
                    else:
                        logger.info(f"No match for pattern: {pattern_regex}")
            
            logger.info("No patterns matched")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting identifier from {url}: {e}")
            return None
    
    def _normalize_identifier(self, identifier: str, template: URLTemplate) -> str:
        """Final normalization of the extracted identifier"""
        if not identifier:
            return identifier
        
        normalized = identifier
        
        # Strip whitespace
        if template.normalization_rules.get('strip_whitespace', True):
            normalized = normalized.strip()
            # Handle accidental spaces within the identifier
            normalized = re.sub(r'\s+', '', normalized)
        
        # Case normalization
        if not template.normalization_rules.get('case_sensitive', False):
            normalized = normalized.lower()
        
        # Normalize separators (convert underscores to hyphens or vice versa)
        if template.normalization_rules.get('normalize_separators', False):
            # For LinkedIn, prefer hyphens; for others, keep original
            if template.name == "LinkedIn Profile":
                normalized = normalized.replace('_', '-')
        
        return normalized
    
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
    
    def _strip_subdomains_from_custom_template(self, url: str, template: URLTemplate) -> str:
        """Apply subdomain stripping when using custom template with strip_subdomains option"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Strip subdomains if enabled in template
            if template.normalization_rules.get('strip_subdomains', False):
                domain = self._strip_subdomains(domain)
            
            # Reconstruct URL with modified domain
            return f"{parsed.scheme}://{domain}{parsed.path}" + \
                   (f"?{parsed.query}" if parsed.query else "") + \
                   (f"#{parsed.fragment}" if parsed.fragment else "")
            
        except Exception as e:
            logger.error(f"Error stripping subdomains from {url}: {e}")
            return url
    
    def _generic_url_processing(self, url: str) -> ExtractResult:
        """Generic URL processing when no template matches"""
        try:
            # Basic normalization
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            path = parsed.path.strip('/')
            
            # Remove www
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Simple extraction - last part of path
            if path:
                path_parts = path.split('/')
                identifier = path_parts[-1] if path_parts else None
                normalized = f"{domain}/{path}".rstrip('/')
            else:
                identifier = None
                normalized = domain
            
            return ExtractResult(
                original=url,
                normalized=normalized,
                extracted=identifier,
                success=bool(identifier),
                processing_steps=["generic_processing"],
                error=None if identifier else "No identifier found in path"
            )
            
        except Exception as e:
            return ExtractResult(
                original=url,
                normalized=url,
                extracted=None,
                success=False,
                processing_steps=["generic_processing"],
                error=str(e)
            )
    
    def _domain_url_processing(self, url: str, strip_subdomains: bool = False) -> ExtractResult:
        """Domain-specific processing - extracts domain name as identifier"""
        try:
            # Basic normalization
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Strip subdomains if requested
            if strip_subdomains:
                domain = self._strip_subdomains(domain)
            
            # Extract domain as identifier
            identifier = domain
            normalized = domain
            
            processing_steps = ["domain_processing"]
            if strip_subdomains:
                processing_steps.append("stripped_subdomains")
            
            return ExtractResult(
                original=url,
                normalized=normalized,
                extracted=identifier,
                success=bool(identifier),
                processing_steps=processing_steps,
                error=None if identifier else "No domain found"
            )
            
        except Exception as e:
            return ExtractResult(
                original=url,
                normalized=url,
                extracted=None,
                success=False,
                processing_steps=["generic_processing"],
                error=str(e)
            )
    
    def test_urls(self, urls: List[str], template_name: str = None, custom_template: URLTemplate = None) -> Dict[str, Any]:
        """Test multiple URLs and return comprehensive results"""
        results = []
        successful_extractions = 0
        
        for url in urls:
            result = self.normalize_url(url, template_name, custom_template)
            results.append(result._asdict())
            if result.success:
                successful_extractions += 1
        
        return {
            'success_rate': successful_extractions / len(urls) if urls else 0,
            'total_tested': len(urls),
            'successful': successful_extractions,
            'failed': len(urls) - successful_extractions,
            'results': results,
            'template_used': template_name or 'auto_detect'
        }