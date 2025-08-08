"""
Management command to set up default URL extraction rules
"""
from django.core.management.base import BaseCommand
from tenants.models import Tenant
from duplicates.rule_models import URLExtractionRule


class Command(BaseCommand):
    help = 'Set up default URL extraction rules for all tenants'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant-name',
            type=str,
            help='Set up rules for specific tenant only'
        )
    
    def handle(self, *args, **options):
        tenant_name = options.get('tenant_name')
        
        if tenant_name:
            try:
                tenants = [Tenant.objects.get(name=tenant_name)]
                self.stdout.write(f"Setting up URL extraction rules for tenant: {tenant_name}")
            except Tenant.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Tenant '{tenant_name}' not found"))
                return
        else:
            tenants = Tenant.objects.all()
            self.stdout.write("Setting up URL extraction rules for all tenants")
        
        # Define default URL extraction rules
        default_rules = [
            {
                'name': 'LinkedIn Profile',
                'description': 'Extract LinkedIn profile usernames from various LinkedIn URL formats',
                'domain_patterns': ['linkedin.com', '*.linkedin.com'],
                'extraction_pattern': r'linkedin\.com/(?:in/|pub/)?([^/?#]+)',
                'extraction_format': 'linkedin:{}',
                'case_sensitive': False,
                'remove_protocol': True,
                'remove_www': True,
                'remove_query_params': True,
                'remove_fragments': True,
            },
            {
                'name': 'GitHub Profile',
                'description': 'Extract GitHub usernames from GitHub profile URLs',
                'domain_patterns': ['github.com'],
                'extraction_pattern': r'github\.com/([^/?#]+)',
                'extraction_format': 'github:{}',
                'case_sensitive': False,
                'remove_protocol': True,
                'remove_www': True,
                'remove_query_params': True,
                'remove_fragments': True,
            },
            {
                'name': 'Twitter/X Profile',
                'description': 'Extract Twitter/X usernames from profile URLs',
                'domain_patterns': ['twitter.com', 'x.com'],
                'extraction_pattern': r'(?:twitter|x)\.com/([^/?#]+)',
                'extraction_format': 'twitter:{}',
                'case_sensitive': False,
                'remove_protocol': True,
                'remove_www': True,
                'remove_query_params': True,
                'remove_fragments': True,
            },
            {
                'name': 'Instagram Profile',
                'description': 'Extract Instagram usernames from profile URLs',
                'domain_patterns': ['instagram.com'],
                'extraction_pattern': r'instagram\.com/([^/?#]+)',
                'extraction_format': 'instagram:{}',
                'case_sensitive': False,
                'remove_protocol': True,
                'remove_www': True,
                'remove_query_params': True,
                'remove_fragments': True,
            },
            {
                'name': 'Facebook Profile',
                'description': 'Extract Facebook profile identifiers',
                'domain_patterns': ['facebook.com', 'fb.com'],
                'extraction_pattern': r'(?:facebook|fb)\.com/([^/?#]+)',
                'extraction_format': 'facebook:{}',
                'case_sensitive': False,
                'remove_protocol': True,
                'remove_www': True,
                'remove_query_params': True,
                'remove_fragments': True,
            },
            {
                'name': 'YouTube Channel',
                'description': 'Extract YouTube channel identifiers',
                'domain_patterns': ['youtube.com', 'youtu.be'],
                'extraction_pattern': r'youtube\.com/(?:c/|channel/|user/|@)?([^/?#]+)',
                'extraction_format': 'youtube:{}',
                'case_sensitive': False,
                'remove_protocol': True,
                'remove_www': True,
                'remove_query_params': True,
                'remove_fragments': True,
            }
        ]
        
        rules_created = 0
        rules_skipped = 0
        
        for tenant in tenants:
            self.stdout.write(f"\nProcessing tenant: {tenant.name}")
            
            for rule_data in default_rules:
                # Check if rule already exists
                existing_rule = URLExtractionRule.objects.filter(
                    tenant=tenant,
                    name=rule_data['name']
                ).first()
                
                if existing_rule:
                    self.stdout.write(f"  - Skipped '{rule_data['name']}' (already exists)")
                    rules_skipped += 1
                    continue
                
                # Create the rule
                URLExtractionRule.objects.create(
                    tenant=tenant,
                    **rule_data
                )
                
                self.stdout.write(self.style.SUCCESS(f"  - Created '{rule_data['name']}'"))
                rules_created += 1
        
        self.stdout.write(f"\nSummary:")
        self.stdout.write(self.style.SUCCESS(f"  - Created: {rules_created} rules"))
        self.stdout.write(f"  - Skipped: {rules_skipped} rules (already existed)")
        
        # Show test examples for LinkedIn
        self.stdout.write(f"\nLinkedIn URL Examples that will be handled:")
        linkedin_examples = [
            'https://www.linkedin.com/in/username',
            'http://www.linkedin.com/in/username',
            'www.linkedin.com/in/username',
            'linkedin.com/in/username',
            'linkedin.com/in/username/',
            'linkedin.com/username',
            'https://linkedin.com/username',
            'linkedin.com/in/username?trk=...',
            'https://linkedin.com/in/username/extra-path'
        ]
        
        for example in linkedin_examples:
            self.stdout.write(f"  - {example} → linkedin:username")
        
        self.stdout.write(f"\nURL extraction rules setup complete!")