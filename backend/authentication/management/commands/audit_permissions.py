"""
Management command to audit permission enforcement across the system
"""
from django.core.management.base import BaseCommand
from django.apps import apps
from django.urls import get_resolver
from rest_framework import permissions
from rest_framework.viewsets import ModelViewSet
from django.utils.module_loading import import_string
from authentication.permissions_registry import PERMISSION_CATEGORIES
import inspect
from typing import List, Dict, Any


class Command(BaseCommand):
    help = 'Audit permission enforcement across all ViewSets and API endpoints'

    def add_arguments(self, parser):
        parser.add_argument(
            '--category',
            type=str,
            help='Specific permission category to audit (e.g., pipelines, business_rules)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about each check',
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Attempt to fix missing permission checks (creates placeholder files)',
        )

    def handle(self, *args, **options):
        self.verbose = options.get('verbose', False)
        self.fix = options.get('fix', False)
        category_filter = options.get('category')
        
        self.stdout.write(self.style.SUCCESS('\n🔍 Starting Permission Audit...\n'))
        
        # Get all permission categories to audit
        categories_to_audit = {}
        if category_filter:
            if category_filter in PERMISSION_CATEGORIES:
                categories_to_audit[category_filter] = PERMISSION_CATEGORIES[category_filter]
            else:
                self.stdout.write(self.style.ERROR(f'Category "{category_filter}" not found'))
                return
        else:
            # Audit Core Data Management categories
            core_data_categories = ['pipelines', 'records', 'fields', 'relationships', 'business_rules', 'duplicates']
            categories_to_audit = {k: v for k, v in PERMISSION_CATEGORIES.items() if k in core_data_categories}
        
        audit_results = {}
        
        # Check each category
        for category, config in categories_to_audit.items():
            self.stdout.write(f'\n📂 Auditing {config["category_display"]} ({category})...')
            audit_results[category] = self.audit_category(category, config)
        
        # Generate summary report
        self.generate_report(audit_results)
    
    def audit_category(self, category: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Audit a specific permission category"""
        results = {
            'actions': config['actions'],
            'permission_classes': [],
            'viewsets': [],
            'missing_checks': [],
            'issues': []
        }
        
        # Check for permission classes
        permission_class_paths = [
            f'api.permissions.{category}.{category.title().replace("_", "")}Permission',
            f'api.permissions.pipelines.{category.title().replace("_", "")}Permission',
            f'api.permissions.{category[:-1]}.{category.title()[:-1].replace("_", "")}Permission',  # singular form
        ]
        
        for path in permission_class_paths:
            try:
                perm_class = import_string(path)
                results['permission_classes'].append(path)
                if self.verbose:
                    self.stdout.write(self.style.SUCCESS(f'  ✅ Found permission class: {path}'))
                    
                # Analyze the permission class
                self.analyze_permission_class(perm_class, category, results)
            except ImportError:
                if self.verbose:
                    self.stdout.write(f'  ⚠️  Permission class not found: {path}')
        
        # Check for ViewSets using these permissions
        self.check_viewsets(category, results)
        
        # Check for missing action checks
        for action in config['actions']:
            if not self.check_action_coverage(category, action, results):
                results['missing_checks'].append(action)
                if self.verbose:
                    self.stdout.write(self.style.WARNING(f'  ⚠️  No permission check found for action: {action}'))
        
        return results
    
    def analyze_permission_class(self, perm_class, category: str, results: Dict[str, Any]):
        """Analyze a permission class for proper implementation"""
        # Check has_permission method
        if hasattr(perm_class, 'has_permission'):
            source = inspect.getsource(perm_class.has_permission)
            
            # Check for action coverage
            for action in results['actions']:
                if action not in source and action != 'access':  # 'access' is often implicit
                    results['issues'].append(f'Action "{action}" not checked in has_permission')
            
            # Check for permission manager usage
            if 'SyncPermissionManager' not in source and 'AsyncPermissionManager' not in source:
                results['issues'].append('Permission manager not used in has_permission')
        
        # Check has_object_permission method
        if hasattr(perm_class, 'has_object_permission'):
            source = inspect.getsource(perm_class.has_object_permission)
            
            # Check for proper object-level checks
            if 'str(obj.id)' not in source and 'pipeline_id' not in source:
                results['issues'].append('Object ID not properly converted to string for permission check')
    
    def check_viewsets(self, category: str, results: Dict[str, Any]):
        """Check ViewSets for proper permission class usage"""
        # Map categories to likely ViewSet names
        viewset_patterns = {
            'pipelines': ['PipelineViewSet'],
            'records': ['RecordViewSet'],
            'fields': ['FieldViewSet', 'PipelineFieldViewSet'],
            'relationships': ['RelationshipViewSet'],
            'business_rules': ['BusinessRuleViewSet'],
            'duplicates': ['DuplicateRuleViewSet', 'DuplicateMatchViewSet'],
        }
        
        patterns = viewset_patterns.get(category, [f'{category.title().replace("_", "")}ViewSet'])
        
        for pattern in patterns:
            # Check common locations
            viewset_paths = [
                f'api.views.{category}.{pattern}',
                f'pipelines.views.{pattern}',
                f'{category}.views.{pattern}',
                f'api.views.{pattern}',
            ]
            
            for path in viewset_paths:
                try:
                    viewset = import_string(path)
                    results['viewsets'].append(path)
                    
                    # Check if it has permission classes
                    if hasattr(viewset, 'permission_classes'):
                        perm_classes = viewset.permission_classes
                        if self.verbose:
                            self.stdout.write(self.style.SUCCESS(f'  ✅ ViewSet found: {path}'))
                            self.stdout.write(f'     Permission classes: {[p.__name__ for p in perm_classes]}')
                    else:
                        results['issues'].append(f'ViewSet {path} has no permission_classes defined')
                    
                    break  # Found the ViewSet, no need to check other paths
                except ImportError:
                    continue
    
    def check_action_coverage(self, category: str, action: str, results: Dict[str, Any]) -> bool:
        """Check if a specific action is covered by permission checks"""
        # This is a simplified check - in production, you'd want to analyze the actual code paths
        for perm_class_path in results['permission_classes']:
            try:
                perm_class = import_string(perm_class_path)
                source = inspect.getsource(perm_class)
                
                # Check if action is mentioned in the permission class
                if action in source or (action == 'execute' and 'execute' in source):
                    return True
            except:
                continue
        
        return False
    
    def generate_report(self, audit_results: Dict[str, Any]):
        """Generate a summary report of the audit"""
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
        self.stdout.write(self.style.SUCCESS('📊 PERMISSION AUDIT REPORT'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        
        total_categories = len(audit_results)
        categories_with_issues = sum(1 for r in audit_results.values() if r['issues'] or r['missing_checks'])
        
        self.stdout.write(f'\n📈 Summary:')
        self.stdout.write(f'  • Categories audited: {total_categories}')
        self.stdout.write(f'  • Categories with issues: {categories_with_issues}')
        
        # Detailed results for each category
        for category, results in audit_results.items():
            self.stdout.write(f'\n\n📁 {category.upper()}:')
            
            # Permission classes
            if results['permission_classes']:
                self.stdout.write(self.style.SUCCESS(f'  ✅ Permission Classes: {len(results["permission_classes"])}'))
                for pc in results['permission_classes']:
                    self.stdout.write(f'     • {pc}')
            else:
                self.stdout.write(self.style.ERROR('  ❌ No permission classes found'))
            
            # ViewSets
            if results['viewsets']:
                self.stdout.write(self.style.SUCCESS(f'  ✅ ViewSets: {len(results["viewsets"])}'))
                for vs in results['viewsets']:
                    self.stdout.write(f'     • {vs}')
            else:
                self.stdout.write(self.style.WARNING('  ⚠️  No ViewSets found'))
            
            # Missing action checks
            if results['missing_checks']:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Missing action checks: {", ".join(results["missing_checks"])}'))
            else:
                self.stdout.write(self.style.SUCCESS('  ✅ All actions covered'))
            
            # Issues
            if results['issues']:
                self.stdout.write(self.style.ERROR('  ❌ Issues found:'))
                for issue in results['issues']:
                    self.stdout.write(f'     • {issue}')
        
        # Recommendations
        self.stdout.write(self.style.SUCCESS('\n\n💡 RECOMMENDATIONS:'))
        
        if any(not r['permission_classes'] for r in audit_results.values()):
            self.stdout.write('  1. Create missing permission classes for categories without them')
        
        if any(r['missing_checks'] for r in audit_results.values()):
            self.stdout.write('  2. Add permission checks for all defined actions')
        
        if any(not r['viewsets'] for r in audit_results.values()):
            self.stdout.write('  3. Implement ViewSets for categories that lack them')
        
        if any(r['issues'] for r in audit_results.values()):
            self.stdout.write('  4. Fix implementation issues in existing permission classes')
        
        if self.fix:
            self.stdout.write(self.style.WARNING('\n\n🔧 Fix mode enabled - creating placeholder files...'))
            self.create_missing_files(audit_results)
        
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
        self.stdout.write(self.style.SUCCESS('Audit complete!\n'))
    
    def create_missing_files(self, audit_results: Dict[str, Any]):
        """Create placeholder files for missing permission classes"""
        # This would create actual files - for now just show what would be created
        for category, results in audit_results.items():
            if not results['permission_classes']:
                self.stdout.write(f'  Would create: api/permissions/{category}.py')
            if not results['viewsets']:
                self.stdout.write(f'  Would create: api/views/{category}.py')