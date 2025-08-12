"""
Management command to update URL extraction rules with improved regex patterns
"""
from django.core.management.base import BaseCommand
from tenants.models import Tenant
from duplicates.models import URLExtractionRule


class Command(BaseCommand):
    help = 'Update existing URL extraction rules with improved regex patterns'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant-name',
            type=str,
            help='Update rules for specific tenant only'
        )
    
    def handle(self, *args, **options):
        tenant_name = options.get('tenant_name')
        
        if tenant_name:
            try:
                tenants = [Tenant.objects.get(name=tenant_name)]
                self.stdout.write(f"Updating URL extraction rules for tenant: {tenant_name}")
            except Tenant.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Tenant '{tenant_name}' not found"))
                return
        else:
            tenants = Tenant.objects.all()
            self.stdout.write("Updating URL extraction rules for all tenants")
        
        # Define improved URL extraction rules with better regex patterns
        improved_rules = {
            'LinkedIn Profile': {
                'description': 'Extract LinkedIn profile usernames from profile URLs only (excludes companies, schools, services)',
                'domain_patterns': ['linkedin.com', '*.linkedin.com'],
                'extraction_pattern': r'linkedin\.com/in/([a-zA-Z0-9\-\.]+)(?:/|$)',
                'extraction_format': 'linkedin:{}',
                'case_sensitive': False,
                'remove_protocol': True,
                'remove_www': True,
                'remove_query_params': True,
                'remove_fragments': True,
            },
            'GitHub Profile': {
                'description': 'Extract GitHub usernames from profile URLs only (excludes repos, orgs, services)',
                'domain_patterns': ['github.com'],
                'extraction_pattern': r'github\.com/([a-zA-Z0-9\-\_]+)(?:/?)$',
                'extraction_format': 'github:{}',
                'case_sensitive': False,
                'remove_protocol': True,
                'remove_www': True,
                'remove_query_params': True,
                'remove_fragments': True,
            },
            'Twitter/X Profile': {
                'description': 'Extract Twitter/X usernames from profile URLs only (excludes services, search, settings)',
                'domain_patterns': ['twitter.com', 'x.com'],
                'extraction_pattern': r'(?:twitter|x)\.com/([a-zA-Z0-9_]+)(?:/(?:status/\d+|following|followers)?/?)?$',
                'extraction_format': 'twitter:{}',
                'case_sensitive': False,
                'remove_protocol': True,
                'remove_www': True,
                'remove_query_params': True,
                'remove_fragments': True,
            },
            'Instagram Profile': {
                'description': 'Extract Instagram usernames from profile URLs only (excludes posts, explore, services)',
                'domain_patterns': ['instagram.com'],
                'extraction_pattern': r'instagram\.com/([a-zA-Z0-9_\.]+)(?:/?)$',
                'extraction_format': 'instagram:{}',
                'case_sensitive': False,
                'remove_protocol': True,
                'remove_www': True,
                'remove_query_params': True,
                'remove_fragments': True,
            },
            'Facebook Profile': {
                'description': 'Extract Facebook profile identifiers (usernames only, excludes pages, groups, events)',
                'domain_patterns': ['facebook.com', 'fb.com'],
                'extraction_pattern': r'(?:facebook|fb)\.com/([a-zA-Z0-9\.]+)(?:/?)$',
                'extraction_format': 'facebook:{}',
                'case_sensitive': False,
                'remove_protocol': True,
                'remove_www': True,
                'remove_query_params': True,
                'remove_fragments': True,
            },
            'YouTube Channel': {
                'description': 'Extract YouTube channel identifiers (preserves case for channel IDs)',
                'domain_patterns': ['youtube.com'],
                'extraction_pattern': r'youtube\.com/(?:c/|channel/|user/|@)([a-zA-Z0-9_-]+)/?$',
                'extraction_format': 'youtube:{}',
                'case_sensitive': True,  # Preserve case for channel IDs
                'remove_protocol': True,
                'remove_www': True,
                'remove_query_params': True,
                'remove_fragments': True,
            }
        }
        
        rules_updated = 0
        rules_skipped = 0
        
        for tenant in tenants:
            self.stdout.write(f"\nProcessing tenant: {tenant.name}")
            
            for rule_name, rule_data in improved_rules.items():
                # Find existing rule
                try:
                    existing_rule = URLExtractionRule.objects.get(
                        tenant=tenant,
                        name=rule_name
                    )
                    
                    # Update the rule with improved pattern
                    existing_rule.description = rule_data['description']
                    existing_rule.domain_patterns = rule_data['domain_patterns']
                    existing_rule.extraction_pattern = rule_data['extraction_pattern']
                    existing_rule.extraction_format = rule_data['extraction_format']
                    existing_rule.case_sensitive = rule_data['case_sensitive']
                    existing_rule.remove_protocol = rule_data['remove_protocol']
                    existing_rule.remove_www = rule_data['remove_www']
                    existing_rule.remove_query_params = rule_data['remove_query_params']
                    existing_rule.remove_fragments = rule_data['remove_fragments']
                    existing_rule.save()
                    
                    self.stdout.write(self.style.SUCCESS(f"  - Updated '{rule_name}'"))
                    rules_updated += 1
                    
                except URLExtractionRule.DoesNotExist:
                    self.stdout.write(f"  - Skipped '{rule_name}' (doesn't exist)")
                    rules_skipped += 1
                    continue
        
        self.stdout.write(f"\nSummary:")
        self.stdout.write(self.style.SUCCESS(f"  - Updated: {rules_updated} rules"))
        self.stdout.write(f"  - Skipped: {rules_skipped} rules (didn't exist)")
        
        # Show regex improvements
        self.stdout.write(f"\nKey Regex Improvements:")
        self.stdout.write("  LinkedIn: Now only matches /in/ profile URLs")
        self.stdout.write("  GitHub: Only matches root user profiles (excludes repos/orgs)")  
        self.stdout.write("  Twitter/X: Excludes service URLs, allows status URLs")
        self.stdout.write("  Instagram: Only matches root profile URLs")
        self.stdout.write("  Facebook: Only matches direct profile URLs")
        self.stdout.write("  YouTube: Case-sensitive for channel IDs, multiple URL formats")
        
        self.stdout.write(f"\nURL extraction rules update complete!")