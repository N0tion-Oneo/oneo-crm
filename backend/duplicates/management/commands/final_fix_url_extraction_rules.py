"""
Management command to apply final fixes to URL extraction rules
"""
from django.core.management.base import BaseCommand
from tenants.models import Tenant
from duplicates.models import URLExtractionRule


class Command(BaseCommand):
    help = 'Apply final fixes to URL extraction rules for remaining edge cases'
    
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
                self.stdout.write(f"Applying final fixes for tenant: {tenant_name}")
            except Tenant.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Tenant '{tenant_name}' not found"))
                return
        else:
            tenants = Tenant.objects.all()
            self.stdout.write("Applying final fixes for all tenants")
        
        # Define final fixes with exclusion lists for known service URLs
        final_fixes = {
            'GitHub Profile': {
                'extraction_pattern': r'github\.com/(?!(?:marketplace|pricing|features|enterprise|collections|about|contact|security|orgs|organizations)(?:/|$))([a-zA-Z0-9\-\_]+)(?:/?)$',
            },
            'Twitter/X Profile': {
                'extraction_pattern': r'(?:twitter|x)\.com/(?!(?:i|search|hashtag|explore|settings|privacy|help|support|tos|login)(?:/|$))([a-zA-Z0-9_]+)(?:/(?:status/\d+|following|followers)?/?)?$',
            },
            'Instagram Profile': {
                'extraction_pattern': r'instagram\.com/(?!(?:p|explore|accounts|stories|reels|tv|direct)(?:/|$))([a-zA-Z0-9_\.]+)(?:/?)$',
            },
            'Facebook Profile': {
                'extraction_pattern': r'(?:facebook|fb)\.com/(?!(?:pages|groups|events|marketplace|watch|gaming|profile\.php)(?:/|$))([a-zA-Z0-9\.]+)(?:/?)$',
            },
        }
        
        rules_updated = 0
        rules_skipped = 0
        
        for tenant in tenants:
            self.stdout.write(f"\nProcessing tenant: {tenant.name}")
            
            for rule_name, rule_data in final_fixes.items():
                # Find existing rule
                try:
                    existing_rule = URLExtractionRule.objects.get(
                        tenant=tenant,
                        name=rule_name
                    )
                    
                    # Update the rule with improved pattern
                    existing_rule.extraction_pattern = rule_data['extraction_pattern']
                    existing_rule.save()
                    
                    self.stdout.write(self.style.SUCCESS(f"  - Final fix applied to '{rule_name}'"))
                    rules_updated += 1
                    
                except URLExtractionRule.DoesNotExist:
                    self.stdout.write(f"  - Skipped '{rule_name}' (doesn't exist)")
                    rules_skipped += 1
                    continue
        
        self.stdout.write(f"\nSummary:")
        self.stdout.write(self.style.SUCCESS(f"  - Updated: {rules_updated} rules"))
        self.stdout.write(f"  - Skipped: {rules_skipped} rules (didn't exist)")
        
        # Show final regex improvements
        self.stdout.write(f"\nFinal Regex Improvements:")
        self.stdout.write("  - Added negative lookahead patterns to exclude known service URLs")
        self.stdout.write("  - GitHub: Excludes marketplace, pricing, features, etc.")
        self.stdout.write("  - Twitter/X: Excludes i, search, settings, etc.")
        self.stdout.write("  - Instagram: Excludes p, explore, accounts, etc.")
        self.stdout.write("  - Facebook: Excludes pages, groups, events, etc.")
        
        self.stdout.write(f"\nFinal URL extraction rules fixes complete!")