"""
Management command to test URL extraction rules with comprehensive test cases
"""
import re
from django.core.management.base import BaseCommand
from tenants.models import Tenant
from duplicates.models import URLExtractionRule


class Command(BaseCommand):
    help = 'Test URL extraction rules with comprehensive test cases'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant-name',
            type=str,
            help='Test rules for specific tenant only'
        )
        parser.add_argument(
            '--rule-name',
            type=str,
            help='Test specific rule only'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed test results'
        )
    
    def handle(self, *args, **options):
        tenant_name = options.get('tenant_name')
        rule_name = options.get('rule_name')
        verbose = options.get('verbose', False)
        
        if tenant_name:
            try:
                tenant = Tenant.objects.get(name=tenant_name)
                self.stdout.write(f"Testing URL extraction rules for tenant: {tenant_name}")
            except Tenant.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Tenant '{tenant_name}' not found"))
                return
        else:
            try:
                tenant = Tenant.objects.filter(name__in=['oneotalent', 'demo', 'test']).first()
                if not tenant:
                    tenant = Tenant.objects.first()
                self.stdout.write(f"Testing URL extraction rules for tenant: {tenant.name}")
            except:
                self.stdout.write(self.style.ERROR("No tenant found"))
                return
        
        # Get rules to test
        rules_query = URLExtractionRule.objects.filter(tenant=tenant, is_active=True)
        if rule_name:
            rules_query = rules_query.filter(name=rule_name)
        
        rules = list(rules_query)
        if not rules:
            self.stdout.write(self.style.ERROR("No URL extraction rules found"))
            return
        
        self.stdout.write(f"Found {len(rules)} rules to test\n")
        
        # Comprehensive test cases
        test_cases = self.get_comprehensive_test_cases()
        
        total_tests = 0
        total_passed = 0
        total_failed = 0
        
        for rule in rules:
            self.stdout.write(f"{'='*60}")
            self.stdout.write(f"Testing Rule: {rule.name}")
            self.stdout.write(f"{'='*60}")
            
            rule_tests = test_cases.get(rule.name, {})
            if not rule_tests:
                self.stdout.write(self.style.WARNING(f"No test cases defined for {rule.name}"))
                continue
            
            rule_passed = 0
            rule_failed = 0
            
            # Test positive cases (should match)
            positive_cases = rule_tests.get('should_match', [])
            for test_case in positive_cases:
                url = test_case['url']
                expected = test_case['expected']
                
                result = self.test_url_extraction(rule, url)
                total_tests += 1
                
                if result == expected:
                    rule_passed += 1
                    total_passed += 1
                    if verbose:
                        self.stdout.write(f"  ✅ {url} → {result}")
                else:
                    rule_failed += 1
                    total_failed += 1
                    self.stdout.write(f"  ❌ {url}")
                    self.stdout.write(f"     Expected: {expected}")
                    self.stdout.write(f"     Got: {result}")
            
            # Test negative cases (should NOT match)
            negative_cases = rule_tests.get('should_not_match', [])
            for url in negative_cases:
                result = self.test_url_extraction(rule, url)
                total_tests += 1
                
                if result is None:
                    rule_passed += 1
                    total_passed += 1
                    if verbose:
                        self.stdout.write(f"  ✅ {url} → (no match)")
                else:
                    rule_failed += 1
                    total_failed += 1
                    self.stdout.write(f"  ❌ {url}")
                    self.stdout.write(f"     Expected: (no match)")
                    self.stdout.write(f"     Got: {result}")
            
            # Rule summary
            rule_total = rule_passed + rule_failed
            rule_pass_rate = (rule_passed / rule_total * 100) if rule_total > 0 else 0
            
            if rule_pass_rate >= 90:
                status_style = self.style.SUCCESS
            elif rule_pass_rate >= 70:
                status_style = self.style.WARNING  
            else:
                status_style = self.style.ERROR
            
            self.stdout.write(f"\n{rule.name} Results:")
            self.stdout.write(status_style(f"  Passed: {rule_passed}/{rule_total} ({rule_pass_rate:.1f}%)"))
            if rule_failed > 0:
                self.stdout.write(f"  Failed: {rule_failed}")
            self.stdout.write()
        
        # Overall summary
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"OVERALL TEST RESULTS")
        self.stdout.write(f"{'='*60}")
        
        overall_pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        if overall_pass_rate >= 90:
            summary_style = self.style.SUCCESS
        elif overall_pass_rate >= 70:
            summary_style = self.style.WARNING
        else:
            summary_style = self.style.ERROR
            
        self.stdout.write(f"Total Tests: {total_tests}")
        self.stdout.write(summary_style(f"Passed: {total_passed} ({overall_pass_rate:.1f}%)"))
        if total_failed > 0:
            self.stdout.write(self.style.ERROR(f"Failed: {total_failed}"))
        
        if overall_pass_rate < 90:
            self.stdout.write(f"\n{self.style.WARNING('⚠️  Some rules need improvement!')}")
            self.stdout.write("Consider running with --verbose to see detailed failures")
    
    def test_url_extraction(self, rule, url):
        """Test URL extraction for a specific rule and URL"""
        try:
            # Simulate the URL normalization process
            normalized_url = self.normalize_url(url, rule)
            
            # Apply the extraction pattern
            for pattern in rule.domain_patterns:
                if self.domain_matches(normalized_url, pattern):
                    match = re.search(rule.extraction_pattern, normalized_url)
                    if match:
                        # Find the first non-empty group (for patterns with multiple groups)
                        identifier = None
                        for group in match.groups():
                            if group is not None:
                                identifier = group
                                break
                        
                        # Fallback to group 1 or 0
                        if identifier is None:
                            identifier = match.group(1) if match.groups() else match.group(0)
                        
                        if not rule.case_sensitive:
                            identifier = identifier.lower()
                        return rule.extraction_format.format(identifier)
            
            return None
        except Exception as e:
            return f"ERROR: {str(e)}"
    
    def normalize_url(self, url, rule):
        """Normalize URL according to rule settings"""
        normalized = url.strip()
        
        # Add protocol if missing
        if not normalized.startswith(('http://', 'https://')):
            normalized = f"https://{normalized}"
        
        # Parse and apply normalization
        from urllib.parse import urlparse
        parsed = urlparse(normalized)
        
        domain = parsed.netloc
        if rule.remove_www and domain.startswith('www.'):
            domain = domain[4:]
        
        path = parsed.path
        query = parsed.query if not rule.remove_query_params else ''
        fragment = parsed.fragment if not rule.remove_fragments else ''
        
        result = domain + path
        if query:
            result += '?' + query
        if fragment:
            result += '#' + fragment
            
        return result
    
    def domain_matches(self, url, pattern):
        """Check if URL domain matches pattern"""
        from urllib.parse import urlparse
        try:
            domain = urlparse(f"https://{url}").netloc if not url.startswith('http') else urlparse(url).netloc
            domain = domain.lower()
            
            if pattern.startswith('*.'):
                # Wildcard pattern
                suffix = pattern[2:]
                return domain == suffix or domain.endswith('.' + suffix)
            else:
                # Exact pattern
                return domain == pattern.lower()
        except:
            return False
    
    def get_comprehensive_test_cases(self):
        """Define comprehensive test cases for each rule"""
        return {
            'LinkedIn Profile': {
                'should_match': [
                    {'url': 'https://linkedin.com/in/john-doe', 'expected': 'linkedin:john-doe'},
                    {'url': 'www.linkedin.com/in/jane-smith', 'expected': 'linkedin:jane-smith'},
                    {'url': 'linkedin.com/in/user123', 'expected': 'linkedin:user123'},
                    {'url': 'https://www.linkedin.com/in/john-doe/', 'expected': 'linkedin:john-doe'},
                    {'url': 'linkedin.com/in/user.name', 'expected': 'linkedin:user.name'},
                    {'url': 'linkedin.com/in/user-name-123', 'expected': 'linkedin:user-name-123'},
                    {'url': 'https://linkedin.com/in/username?trk=profile', 'expected': 'linkedin:username'},
                    {'url': 'linkedin.com/in/username#education', 'expected': 'linkedin:username'},
                ],
                'should_not_match': [
                    'linkedin.com/company/microsoft',
                    'linkedin.com/school/stanford-university', 
                    'linkedin.com/jobs/search',
                    'linkedin.com/pulse/article-title',
                    'linkedin.com/learning/course-name',
                    'linkedin.com/sales/people',
                    'linkedin.com/feed/',
                    'linkedin.com/messaging/',
                ]
            },
            
            'GitHub Profile': {
                'should_match': [
                    {'url': 'github.com/username', 'expected': 'github:username'},
                    {'url': 'https://github.com/user-name', 'expected': 'github:user-name'},
                    {'url': 'www.github.com/user123', 'expected': 'github:user123'},
                    {'url': 'github.com/Username', 'expected': 'github:username'},  # case insensitive
                    {'url': 'github.com/user_name', 'expected': 'github:user_name'},
                ],
                'should_not_match': [
                    'github.com/user/repository',
                    'github.com/user/repo/issues',
                    'github.com/orgs/organization',
                    'github.com/marketplace',
                    'github.com/pricing',
                    'github.com/features',
                    'github.com/enterprise',
                    'github.com/collections',
                ]
            },
            
            'Twitter/X Profile': {
                'should_match': [
                    {'url': 'twitter.com/username', 'expected': 'twitter:username'},
                    {'url': 'x.com/username', 'expected': 'twitter:username'},
                    {'url': 'https://twitter.com/user_name', 'expected': 'twitter:user_name'},
                    {'url': 'www.x.com/Username', 'expected': 'twitter:username'},
                    {'url': 'twitter.com/username/status/123', 'expected': 'twitter:username'},  # Should extract user from status
                ],
                'should_not_match': [
                    'twitter.com/i/flow/login',
                    'twitter.com/search?q=test',
                    'twitter.com/hashtag/trending',
                    'x.com/explore',
                    'twitter.com/settings',
                    'twitter.com/privacy',
                ]
            },
            
            'Instagram Profile': {
                'should_match': [
                    {'url': 'instagram.com/username', 'expected': 'instagram:username'},
                    {'url': 'https://instagram.com/user_name', 'expected': 'instagram:user_name'},
                    {'url': 'www.instagram.com/user.name', 'expected': 'instagram:user.name'},
                    {'url': 'instagram.com/Username', 'expected': 'instagram:username'},
                ],
                'should_not_match': [
                    'instagram.com/p/ABC123DEF',  # Post
                    'instagram.com/explore/',
                    'instagram.com/accounts/login',
                    'instagram.com/stories/username',
                    'instagram.com/reels/trending',
                    'instagram.com/tv/',
                ]
            },
            
            'Facebook Profile': {
                'should_match': [
                    {'url': 'facebook.com/username', 'expected': 'facebook:username'},
                    {'url': 'fb.com/username', 'expected': 'facebook:username'},
                    {'url': 'https://facebook.com/user.name', 'expected': 'facebook:user.name'},
                    {'url': 'www.facebook.com/Username', 'expected': 'facebook:username'},
                ],
                'should_not_match': [
                    'facebook.com/pages/Business-Name/123456',
                    'facebook.com/groups/groupname',
                    'facebook.com/events/123456',
                    'facebook.com/marketplace',
                    'facebook.com/watch',
                    'facebook.com/gaming',
                    'facebook.com/profile.php?id=123456',  # Currently not handled
                ]
            },
            
            'YouTube Channel': {
                'should_match': [
                    {'url': 'youtube.com/@username', 'expected': 'youtube:username'},
                    {'url': 'youtube.com/c/channelname', 'expected': 'youtube:channelname'},
                    {'url': 'youtube.com/user/username', 'expected': 'youtube:username'},
                    {'url': 'youtube.com/channel/UC1234567890', 'expected': 'youtube:UC1234567890'},
                    {'url': 'https://www.youtube.com/@creator', 'expected': 'youtube:creator'},
                ],
                'should_not_match': [
                    'youtube.com/watch?v=ABC123',
                    'youtube.com/playlist?list=PL123',
                    'youtube.com/results?search_query=test',
                    'youtube.com/trending',
                    'youtu.be/ABC123',  # Short video links
                ]
            }
        }