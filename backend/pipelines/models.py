"""
Pipeline models for dynamic data structures
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
import json
import logging
import re

from .field_types import FieldType, FIELD_TYPE_CONFIGS, validate_field_config
from .validation.field_validator import FieldValidator
from .validators import validate_record_data


def field_slugify(value):
    """
    Custom slugify function for field names that uses underscores instead of hyphens
    to match data key format in record.data
    
    This ensures consistency between field.slug and record.data keys
    """
    if not value:
        return ''
    
    # Convert to lowercase and replace spaces/hyphens with underscores
    slug = str(value).lower().strip()
    
    # Replace spaces and hyphens with underscores
    slug = re.sub(r'[\s\-]+', '_', slug)
    
    # Remove characters that aren't alphanumerics or underscores
    slug = re.sub(r'[^\w_]', '', slug)
    
    # Remove leading/trailing underscores
    slug = slug.strip('_')
    
    # Replace multiple consecutive underscores with single underscore
    slug = re.sub(r'_+', '_', slug)
    
    return slug

User = get_user_model()
logger = logging.getLogger(__name__)


class FieldManager(models.Manager):
    """Manager for Field model with soft delete support"""
    
    def get_queryset(self):
        """Return only non-deleted fields by default"""
        return super().get_queryset().filter(is_deleted=False)
    
    def with_deleted(self):
        """Include soft-deleted fields in queryset"""
        return super().get_queryset()
    
    def deleted_only(self):
        """Return only soft-deleted fields"""
        return super().get_queryset().filter(is_deleted=True)
    
    def scheduled_for_hard_delete(self):
        """Return fields scheduled for hard deletion"""
        return super().get_queryset().filter(scheduled_for_hard_delete__isnull=False)


class PipelineTemplate(models.Model):
    """Templates for creating new pipelines"""
    CATEGORIES = [
        ('crm', 'Customer Relationship Management'),
        ('ats', 'Applicant Tracking System'),
        ('cms', 'Content Management System'),
        ('project', 'Project Management'),
        ('inventory', 'Inventory Management'),
        ('support', 'Support Ticketing'),
        ('custom', 'Custom Template'),
    ]
    
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, choices=CATEGORIES)
    
    # Template definition (includes pipeline + fields)
    template_data = models.JSONField()
    
    # Template metadata
    is_system = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    usage_count = models.IntegerField(default=0)
    
    # Preview configuration
    preview_config = models.JSONField(default=dict)
    sample_data = models.JSONField(default=dict)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pipelines_pipelinetemplate'
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['is_system']),
            models.Index(fields=['is_public']),
            GinIndex(fields=['template_data']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.category})"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = field_slugify(self.name)
        super().save(*args, **kwargs)
    
    def create_pipeline_from_template(self, name: str, created_by: User) -> 'Pipeline':
        """Create a new pipeline from this template"""
        template_data = self.template_data
        
        # Create pipeline
        pipeline_data = template_data.get('pipeline', {})
        pipeline = Pipeline.objects.create(
            name=name,
            description=pipeline_data.get('description', ''),
            icon=pipeline_data.get('icon', 'database'),
            color=pipeline_data.get('color', '#3B82F6'),
            pipeline_type=pipeline_data.get('pipeline_type', 'custom'),
            template=self,
            settings=pipeline_data.get('settings', {}),
            created_by=created_by
        )
        
        # Create fields
        for field_data in template_data.get('fields', []):
            Field.objects.create(
                pipeline=pipeline,
                name=field_data['name'],
                slug=field_data['slug'],
                description=field_data.get('description', ''),
                field_type=field_data['field_type'],
                field_config=field_data.get('field_config', {}),
                storage_constraints=field_data.get('storage_constraints', {}),
                business_rules=field_data.get('business_rules', {}),
                display_name=field_data.get('display_name', field_data['name']),
                help_text=field_data.get('help_text', ''),
                enforce_uniqueness=field_data.get('enforce_uniqueness', False),
                create_index=field_data.get('create_index', False),
                is_searchable=field_data.get('is_searchable', True),
                is_ai_field=field_data.get('is_ai_field', False),
                display_order=field_data.get('display_order', 0),
                is_visible_in_list=field_data.get('is_visible_in_list', True),
                is_visible_in_detail=field_data.get('is_visible_in_detail', True),
                ai_config=field_data.get('ai_config', {}),
                created_by=created_by
            )
        
        # Increment usage count
        self.usage_count += 1
        self.save(update_fields=['usage_count'])
        
        return pipeline


class Pipeline(models.Model):
    """Main pipeline model - represents a data structure"""
    PIPELINE_TYPES = [
        ('crm', 'CRM Pipeline'),
        ('ats', 'ATS Pipeline'),
        ('cms', 'CMS Pipeline'),
        ('custom', 'Custom Pipeline'),
    ]
    
    ACCESS_LEVELS = [
        ('private', 'Private'),
        ('internal', 'Internal'),
        ('public', 'Public'),
    ]
    
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Visual configuration
    icon = models.CharField(max_length=50, default='database')
    color = models.CharField(max_length=7, default='#3B82F6')  # Hex color
    
    # Schema and configuration
    field_schema = models.JSONField(default=dict)  # Cached field definitions
    view_config = models.JSONField(default=dict)   # View settings
    settings = models.JSONField(default=dict)      # General settings
    
    # Pipeline classification
    pipeline_type = models.CharField(max_length=50, choices=PIPELINE_TYPES, default='custom')
    template = models.ForeignKey(PipelineTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Access control
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='internal')
    permission_config = models.JSONField(default=dict)
    
    # Status and metadata
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)
    
    # Statistics (updated by signals)
    record_count = models.IntegerField(default=0)
    last_record_created = models.DateTimeField(null=True, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pipelines_pipeline'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['pipeline_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_by']),
            GinIndex(fields=['field_schema']),
        ]
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = field_slugify(self.name)
        
        # Debug: Log the save operation
        logger.info(f"💾 Saving pipeline {self.name} (ID: {self.pk}) with access_level: {self.access_level}")
        
        # Update field schema cache
        if self.pk:  # Only if pipeline already exists
            self._update_field_schema()
        
        super().save(*args, **kwargs)
        
        logger.info(f"✅ Pipeline {self.name} saved successfully with access_level: {self.access_level}")
        
        # Broadcast pipeline update (temporarily disabled to fix toggle)
        if hasattr(self, '_skip_broadcast') and self._skip_broadcast:
            return
        
        # TODO: Re-enable broadcasting once async issues are resolved
        # try:
        #     from api.events import broadcaster
        #     broadcaster.sync_broadcast_pipeline_update(
        #         self, 
        #         event_type="updated" if self.pk else "created",
        #         user_id=getattr(self, '_current_user_id', None)
        #     )
        # except Exception as e:
        #     logger.error(f"Error handling pipeline save signal: {e}")
        #     # Don't fail save if broadcast fails
    
    def _update_field_schema(self):
        """Update cached field schema from active (non-deleted) fields only"""
        fields_data = {}
        # Only include active fields in schema cache
        for field in self.fields.filter(is_deleted=False):
            fields_data[field.slug] = {
                'name': field.name,
                'type': field.field_type,
                'config': field.field_config,
                'storage_constraints': field.storage_constraints,
                'business_rules': field.business_rules,
                'form_validation_rules': field.form_validation_rules,
                'enforce_uniqueness': field.enforce_uniqueness,
                'create_index': field.create_index,
                'searchable': field.is_searchable,
                'ai_field': field.is_ai_field,
                'visible_in_public_forms': field.is_visible_in_public_forms,
                'display_order': field.display_order,
                'display_name': field.display_name,
                'help_text': field.help_text,
            }
        self.field_schema = fields_data
    
    def get_field_by_slug(self, slug: str):
        """Get field by slug"""
        try:
            return self.fields.get(slug=slug)
        except Field.DoesNotExist:
            return None
    
    def validate_record_data(self, data: dict, context='storage') -> dict:
        """Validate record data against pipeline schema"""
        field_definitions = []
        for field in self.fields.all():
            field_definitions.append({
                'slug': field.slug,
                'field_type': field.field_type,
                'field_config': field.field_config,
                'storage_constraints': field.storage_constraints,
                'business_rules': field.business_rules,
                'ai_config': field.ai_config if field.is_ai_field else {},
            })
        
        return validate_record_data(field_definitions, data, context)
    
    def validate_stage_transition(self, record_data: dict, target_stage: str) -> tuple[bool, list]:
        """Validate if record can transition to target stage based on business rules"""
        errors = []
        
        for field in self.fields.all():
            is_valid, field_errors = field.check_business_rules(record_data, target_stage)
            if not is_valid:
                errors.extend(field_errors)
        
        return len(errors) == 0, errors
    
    def get_ai_fields(self):
        """Get all AI fields for this pipeline"""
        return self.fields.filter(is_ai_field=True)
    
    def clone(self, new_name: str, created_by: User) -> 'Pipeline':
        """Clone this pipeline with all its fields"""
        # Create new pipeline
        new_pipeline = Pipeline.objects.create(
            name=new_name,
            description=f"Clone of {self.name}",
            icon=self.icon,
            color=self.color,
            pipeline_type=self.pipeline_type,
            view_config=self.view_config.copy(),
            settings=self.settings.copy(),
            access_level=self.access_level,
            permission_config=self.permission_config.copy(),
            created_by=created_by
        )
        
        # Clone fields
        for field in self.fields.all():
            Field.objects.create(
                pipeline=new_pipeline,
                name=field.name,
                slug=field.slug,
                description=field.description,
                field_type=field.field_type,
                field_config=field.field_config.copy(),
                storage_constraints=field.storage_constraints.copy(),
                business_rules=field.business_rules.copy(),
                form_validation_rules=field.form_validation_rules.copy(),
                display_name=field.display_name,
                help_text=field.help_text,
                enforce_uniqueness=field.enforce_uniqueness,
                create_index=field.create_index,
                is_searchable=field.is_searchable,
                is_ai_field=field.is_ai_field,
                display_order=field.display_order,
                is_visible_in_list=field.is_visible_in_list,
                is_visible_in_detail=field.is_visible_in_detail,
                is_visible_in_public_forms=field.is_visible_in_public_forms,
                ai_config=field.ai_config.copy(),
                created_by=created_by
            )
        
        return new_pipeline
    
    # =============================================
    # PHASE 1: DEPENDENCY TRACKING METHODS
    # =============================================
    
    def _get_field_dependencies_from_business_rules(self, field_slug: str) -> set:
        """Extract dependencies from a specific field's business rules"""
        dependencies = set()
        
        try:
            field = self.fields.get(slug=field_slug)
            business_rules = field.business_rules or {}
            
            # New conditional_rules format
            conditional_rules = business_rules.get('conditional_rules', {})
            
            # show_when, hide_when, require_when rules
            for rule_type in ['show_when', 'hide_when', 'require_when']:
                for rule in conditional_rules.get(rule_type, []):
                    condition_field = rule.get('field')
                    if condition_field:
                        dependencies.add(condition_field)
                        print(f"🔗 {field_slug}.{rule_type} depends on {condition_field}")
            
            # Legacy conditional_requirements format
            legacy_rules = business_rules.get('conditional_requirements', [])
            for rule in legacy_rules:
                condition_field = rule.get('condition_field')
                if condition_field:
                    dependencies.add(condition_field)
                    print(f"🔗 {field_slug}.legacy_rule depends on {condition_field}")
            
            # Stage requirements don't create field dependencies (they depend on pipeline stage, not other fields)
            
        except Field.DoesNotExist:
            pass
        
        return dependencies
    
    def _get_fields_dependent_on(self, changed_field_slug: str) -> set:
        """Find all fields that depend on the changed field"""
        dependent_fields = set()
        
        for field in self.fields.all():
            field_dependencies = self._get_field_dependencies_from_business_rules(field.slug)
            if changed_field_slug in field_dependencies:
                dependent_fields.add(field.slug)
                print(f"🔗 {field.slug} depends on {changed_field_slug}")
        
        return dependent_fields
    
    def get_field_dependencies(self, changed_field_slug: str) -> list:
        """
        Get all fields that might be affected by changing this field
        
        Returns:
            List of field slugs that need validation when changed_field_slug changes
        """
        affected_fields = {changed_field_slug}  # Always include the changed field
        
        # Find fields that depend on this field
        dependent_fields = self._get_fields_dependent_on(changed_field_slug)
        affected_fields.update(dependent_fields)
        
        print(f"🧠 DEPENDENCY ANALYSIS: {changed_field_slug} affects {len(affected_fields)} field(s): {list(affected_fields)}")
        
        return list(affected_fields)
    
    def build_dependency_cache(self) -> dict:
        """
        Build and cache field dependency map for performance
        
        Returns:
            Dictionary mapping each field to its dependencies
        """
        dependency_map = {}
        
        print(f"🏗️  BUILDING DEPENDENCY CACHE for pipeline {self.id}")
        
        for field in self.fields.all():
            dependencies = self._get_field_dependencies_from_business_rules(field.slug)
            dependency_map[field.slug] = list(dependencies)
            
            if dependencies:
                print(f"   📋 {field.slug} depends on: {list(dependencies)}")
            else:
                print(f"   🆓 {field.slug} has no dependencies")
        
        # Cache this for performance
        self._dependency_cache = dependency_map
        self._dependency_cache_version = self.fields.count()
        
        return dependency_map
    
    # =============================================
    # PHASE 2: ADVANCED DEPENDENCY GRAPH
    # =============================================
    
    def get_all_affected_fields_with_cascades(self, changed_field_slug: str) -> dict:
        """
        Get all fields affected by a change, including cascade effects
        
        Returns:
            Dictionary with cascade levels and visualization data
        """
        affected_fields = {changed_field_slug}
        cascade_levels = {changed_field_slug: 0}  # Track dependency depth
        cascade_chain = []  # For visualization
        queue = [(changed_field_slug, 0)]  # (field, level)
        
        print(f"🌊 CASCADE ANALYSIS: Starting from {changed_field_slug}")
        
        while queue:
            current_field, level = queue.pop(0)
            
            # Find fields that depend on the current field
            dependent_fields = self._get_fields_dependent_on(current_field)
            
            for dependent_field in dependent_fields:
                if dependent_field not in affected_fields:
                    # New dependency found
                    affected_fields.add(dependent_field)
                    cascade_levels[dependent_field] = level + 1
                    queue.append((dependent_field, level + 1))
                    cascade_chain.append((current_field, dependent_field, level + 1))
                    print(f"   🔗 Level {level + 1}: {current_field} → {dependent_field}")
                elif cascade_levels[dependent_field] > level + 1:
                    # Found a shorter path to this field
                    cascade_levels[dependent_field] = level + 1
                    print(f"   📐 Shorter path: {current_field} → {dependent_field} (level {level + 1})")
        
        return {
            'affected_fields': list(affected_fields),
            'cascade_levels': cascade_levels,
            'cascade_chain': cascade_chain,
            'max_depth': max(cascade_levels.values()) if cascade_levels else 0
        }
    
    def build_complete_dependency_graph(self) -> dict:
        """
        Build a complete field dependency graph including reverse dependencies
        
        Returns:
            Complete graph with forward and reverse dependencies
        """
        print(f"🕸️  BUILDING COMPLETE DEPENDENCY GRAPH for pipeline {self.id}")
        
        # Forward dependencies (field X depends on field Y)
        forward_deps = {}
        # Reverse dependencies (field Y affects field X)  
        reverse_deps = {}
        
        for field in self.fields.all():
            field_slug = field.slug
            dependencies = self._get_field_dependencies_from_business_rules(field_slug)
            
            forward_deps[field_slug] = list(dependencies)
            
            # Build reverse mapping
            if field_slug not in reverse_deps:
                reverse_deps[field_slug] = []
            
            for dep_field in dependencies:
                if dep_field not in reverse_deps:
                    reverse_deps[dep_field] = []
                reverse_deps[dep_field].append(field_slug)
        
        # Detect circular dependencies
        circular_deps = self._detect_circular_dependencies(forward_deps)
        
        graph = {
            'forward_dependencies': forward_deps,
            'reverse_dependencies': reverse_deps,
            'circular_dependencies': circular_deps,
            'field_count': self.fields.count(),
            'dependency_count': sum(len(deps) for deps in forward_deps.values())
        }
        
        self._complete_dependency_graph = graph
        print(f"   📊 Graph Stats: {graph['field_count']} fields, {graph['dependency_count']} dependencies")
        
        if circular_deps:
            print(f"   ⚠️  WARNING: {len(circular_deps)} circular dependencies detected!")
            for cycle in circular_deps:
                print(f"      🔄 Cycle: {' → '.join(cycle + [cycle[0]])}")
        
        return graph
    
    def _detect_circular_dependencies(self, forward_deps: dict) -> list:
        """Detect circular dependencies using DFS"""
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node, path):
            if node in rec_stack:
                # Found a cycle - extract it
                cycle_start = path.index(node)
                cycle = path[cycle_start:]
                cycles.append(cycle)
                return True
            
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in forward_deps.get(node, []):
                if dfs(neighbor, path):
                    return True
            
            rec_stack.remove(node)
            path.pop()
            return False
        
        for field in forward_deps:
            if field not in visited:
                dfs(field, [])
        
        return cycles
    
    def visualize_dependencies(self, changed_field_slug: str = None) -> str:
        """
        Generate ASCII visualization of field dependencies
        
        Args:
            changed_field_slug: If provided, highlight cascade from this field
        """
        if not hasattr(self, '_complete_dependency_graph'):
            self.build_complete_dependency_graph()
        
        graph = self._complete_dependency_graph
        output = []
        
        output.append("📊 DEPENDENCY VISUALIZATION")
        output.append("=" * 50)
        
        if changed_field_slug:
            cascade_data = self.get_all_affected_fields_with_cascades(changed_field_slug)
            output.append(f"🌊 CASCADE FROM: {changed_field_slug}")
            output.append(f"   📈 Max Depth: {cascade_data['max_depth']}")
            output.append(f"   🎯 Affected: {len(cascade_data['affected_fields'])} fields")
            output.append("")
            
            # Show cascade chain
            for level in range(cascade_data['max_depth'] + 1):
                level_fields = [f for f, l in cascade_data['cascade_levels'].items() if l == level]
                if level_fields:
                    indent = "   " * level
                    if level == 0:
                        output.append(f"{indent}🔥 ORIGIN: {', '.join(level_fields)}")
                    else:
                        output.append(f"{indent}🔗 Level {level}: {', '.join(level_fields)}")
        else:
            output.append("🕸️  COMPLETE DEPENDENCY MAP:")
            
        output.append("")
        output.append("📋 FIELD DEPENDENCIES:")
        
        # Show forward dependencies
        forward_deps = graph['forward_dependencies']
        for field_slug in sorted(forward_deps.keys()):
            deps = forward_deps[field_slug]
            if deps:
                output.append(f"   🔗 {field_slug} ← depends on: {', '.join(deps)}")
            else:
                output.append(f"   🆓 {field_slug} ← no dependencies")
        
        output.append("")
        output.append("📋 REVERSE DEPENDENCIES:")
        
        # Show reverse dependencies
        reverse_deps = graph['reverse_dependencies']
        for field_slug in sorted(reverse_deps.keys()):
            deps = reverse_deps[field_slug]
            if deps:
                output.append(f"   📤 {field_slug} → affects: {', '.join(deps)}")
            else:
                output.append(f"   🔚 {field_slug} → affects nothing")
        
        if graph['circular_dependencies']:
            output.append("")
            output.append("⚠️  CIRCULAR DEPENDENCIES:")
            for cycle in graph['circular_dependencies']:
                output.append(f"   🔄 {' → '.join(cycle + [cycle[0]])}")
        
        return "\n".join(output)
    
    # =============================================
    # PHASE 3: REAL-TIME OPTIMIZATION
    # =============================================
    
    def categorize_business_rules_by_priority(self) -> dict:
        """
        Categorize business rules by priority for async validation
        
        Returns:
            Dictionary with 'critical' and 'non_critical' rule categories
        """
        critical_rules = []
        non_critical_rules = []
        
        for field in self.fields.all():
            business_rules = field.business_rules or {}
            field_data = {
                'field_slug': field.slug,
                'business_rules': business_rules
            }
            
            # Determine priority based on rule types - more intelligent categorization
            has_critical_rules = False
            has_non_critical_rules = False
            
            # Stage requirements are always critical (block transitions)
            stage_requirements = business_rules.get('stage_requirements', {})
            if stage_requirements:
                has_critical_rules = True
            
            # New conditional_rules format analysis
            conditional_rules = business_rules.get('conditional_rules', {})
            
            # require_when rules are critical (blocking)
            if conditional_rules.get('require_when'):
                has_critical_rules = True
            
            # show_when/hide_when rules are non-critical (UI behavior)
            if conditional_rules.get('show_when') or conditional_rules.get('hide_when'):
                has_non_critical_rules = True
            
            # Legacy conditional_requirements are critical if they require fields
            legacy_rules = business_rules.get('conditional_requirements', [])
            if legacy_rules:
                has_critical_rules = True
            
            # Warning rules are non-critical
            if business_rules.get('show_warnings') and business_rules.get('warning_message'):
                has_non_critical_rules = True
            
            # Override: If block_transitions is explicitly False, make non-critical
            if business_rules.get('block_transitions') is False:
                has_critical_rules = False
                has_non_critical_rules = True
            
            if has_critical_rules:
                critical_rules.append(field_data)
                print(f"🔴 CRITICAL: {field.slug} has blocking business rules")
            elif has_non_critical_rules:
                non_critical_rules.append(field_data)
                print(f"🟡 NON-CRITICAL: {field.slug} has display/warning rules")
            else:
                # Fields with no business rules are neither critical nor non-critical for validation
                print(f"⚪ NEUTRAL: {field.slug} has no business rules")
        
        return {
            'critical': critical_rules,
            'non_critical': non_critical_rules,
            'critical_count': len(critical_rules),
            'non_critical_count': len(non_critical_rules)
        }
    
    async def validate_non_critical_rules_async(self, data: dict, changed_field_slug: str = None) -> dict:
        """
        Asynchronously validate non-critical business rules (warnings, display logic)
        
        Args:
            data: Record data to validate
            changed_field_slug: If provided, only validate rules affected by this field
        """
        import asyncio
        from django.db import connection
        
        print(f"🟡 ASYNC VALIDATION: Starting non-critical validation for {changed_field_slug or 'all fields'}")
        
        # Get non-critical rules
        rule_categories = self.categorize_business_rules_by_priority()
        non_critical_rules = rule_categories['non_critical']
        
        if changed_field_slug:
            # Filter to only affected fields
            cascade_data = self.get_all_affected_fields_with_cascades(changed_field_slug)
            affected_fields = set(cascade_data['affected_fields'])
            non_critical_rules = [r for r in non_critical_rules if r['field_slug'] in affected_fields]
            print(f"   📊 Filtering to {len(non_critical_rules)} affected non-critical rules")
        
        # Process rules asynchronously with small delays to prevent blocking
        results = {'warnings': [], 'display_changes': [], 'suggestions': []}
        
        for rule_data in non_critical_rules:
            try:
                # Small delay to prevent database overload
                await asyncio.sleep(0.01)  
                
                field_slug = rule_data['field_slug']
                business_rules = rule_data['business_rules']
                
                # Process show_when/hide_when rules (display logic)
                conditional_rules = business_rules.get('conditional_rules', {})
                
                if conditional_rules.get('show_when') or conditional_rules.get('hide_when'):
                    display_result = await self._evaluate_display_rules_async(field_slug, data, conditional_rules)
                    if display_result:
                        results['display_changes'].append(display_result)
                
                # Process warning rules
                if business_rules.get('show_warnings') and business_rules.get('warning_message'):
                    warning_result = await self._evaluate_warning_rules_async(field_slug, data, business_rules)
                    if warning_result:
                        results['warnings'].append(warning_result)
                
                print(f"   ✅ Processed non-critical rules for {field_slug}")
                
            except Exception as e:
                print(f"   ❌ Error processing non-critical rules for {field_slug}: {e}")
                continue
        
        print(f"🟡 ASYNC VALIDATION COMPLETE: {len(results['warnings'])} warnings, {len(results['display_changes'])} display changes")
        return results
    
    async def _evaluate_display_rules_async(self, field_slug: str, data: dict, conditional_rules: dict) -> dict:
        """Evaluate show_when/hide_when rules asynchronously"""
        from .validators import _evaluate_condition
        
        result = {'field': field_slug, 'action': None, 'reason': None}
        
        # Check show_when rules
        show_when_rules = conditional_rules.get('show_when', [])
        for rule in show_when_rules:
            condition_field = rule.get('field')
            if condition_field in data:
                field_value = data[condition_field]
                condition_met = _evaluate_condition(field_value, rule.get('condition', 'equals'), rule.get('value'))
                if condition_met:
                    result['action'] = 'show'
                    result['reason'] = f"Show because {condition_field} {rule.get('condition')} {rule.get('value')}"
                    break
        
        # Check hide_when rules
        hide_when_rules = conditional_rules.get('hide_when', [])
        for rule in hide_when_rules:
            condition_field = rule.get('field')
            if condition_field in data:
                field_value = data[condition_field]
                condition_met = _evaluate_condition(field_value, rule.get('condition', 'equals'), rule.get('value'))
                if condition_met:
                    result['action'] = 'hide'
                    result['reason'] = f"Hide because {condition_field} {rule.get('condition')} {rule.get('value')}"
                    break
        
        return result if result['action'] else None
    
    async def _evaluate_warning_rules_async(self, field_slug: str, data: dict, business_rules: dict) -> dict:
        """Evaluate warning rules asynchronously"""
        # This would evaluate conditions that should show warnings but not block saving
        field_value = data.get(field_slug)
        warning_message = business_rules.get('warning_message')
        
        # Example: Check if field is empty but not required
        if not field_value and warning_message:
            return {
                'field': field_slug,
                'type': 'warning',
                'message': warning_message
            }
        
        return None
    
    def validate_critical_rules_sync(self, data: dict, context='business_rules', changed_field_slug=None) -> dict:
        """
        Synchronously validate critical business rules (blocking rules)
        
        This is optimized for speed and only validates rules that can block operations
        """
        print(f"🔴 CRITICAL VALIDATION: Starting for {changed_field_slug or 'all fields'}")
        
        # Get critical rules only
        rule_categories = self.categorize_business_rules_by_priority()
        critical_rules = rule_categories['critical']
        
        if changed_field_slug:
            # Use cascade analysis for critical rules
            cascade_data = self.get_all_affected_fields_with_cascades(changed_field_slug)
            affected_fields = set(cascade_data['affected_fields'])
            critical_rules = [r for r in critical_rules if r['field_slug'] in affected_fields]
            print(f"   📊 Filtering to {len(critical_rules)} affected critical rules")
        
        # Build field definitions for critical fields only
        critical_field_slugs = [r['field_slug'] for r in critical_rules]
        fields_to_validate = self.fields.filter(slug__in=critical_field_slugs)
        
        field_definitions = []
        for field in fields_to_validate:
            field_definitions.append({
                'slug': field.slug,
                'field_type': field.field_type,
                'field_config': field.field_config,
                'storage_constraints': field.storage_constraints,
                'business_rules': field.business_rules,
                'ai_config': field.ai_config if field.is_ai_field else {},
            })
        
        print(f"🔴 CRITICAL VALIDATION SCOPE: {len(field_definitions)} critical field(s)")
        
        # Use existing validation function but only on critical fields
        from .validators import validate_record_data
        return validate_record_data(field_definitions, data, context)
    
    def validate_record_data_optimized(self, data: dict, context='storage', changed_field_slug=None) -> dict:
        """
        Optimized validation with dependency tracking
        
        Args:
            data: Record data to validate
            context: Validation context ('storage', 'form', 'business_rules')
            changed_field_slug: If provided, optimize validation for this specific field change
        """
        print(f"🎯 OPTIMIZED VALIDATION: context={context}, changed_field={changed_field_slug}")
        
        # PHASE 3: PRIORITY-BASED VALIDATION STRATEGY
        if context == 'business_rules' and changed_field_slug:
            print(f"🚀 PHASE 3: Priority-based validation for {changed_field_slug}")
            
            # Step 1: Validate critical rules synchronously (blocking)
            critical_result = self.validate_critical_rules_sync(data, context, changed_field_slug)
            
            # Step 2: If critical validation passes, trigger async non-critical validation
            if critical_result['is_valid']:
                print(f"✅ Critical rules passed, starting async validation...")
                
                # Trigger async validation in background (don't wait for it)
                import asyncio
                try:
                    # Create task but don't await it (fire and forget)
                    loop = asyncio.get_event_loop()
                    async_task = loop.create_task(
                        self.validate_non_critical_rules_async(data, changed_field_slug)
                    )
                    print(f"🟡 Async validation task created: {async_task}")
                except RuntimeError:
                    # No event loop running, skip async validation
                    print(f"⚠️  No event loop available, skipping async validation")
                
                # Return critical validation result immediately
                return critical_result
            else:
                # Critical validation failed, no need for async validation
                print(f"❌ Critical rules failed, skipping async validation")
                return critical_result
                
        elif context == 'business_rules':
            # FULL BUSINESS RULES: Use traditional cascade validation
            cascade_data = self.get_all_affected_fields_with_cascades(changed_field_slug) if changed_field_slug else None
            if cascade_data:
                affected_fields = cascade_data['affected_fields']
                fields_to_validate = self.fields.filter(slug__in=affected_fields)
                print(f"🧠 FULL BUSINESS RULES WITH CASCADES: Validating {len(affected_fields)} field(s)")
                print(f"   🌊 Max cascade depth: {cascade_data['max_depth']}")
            else:
                fields_to_validate = self.fields.all()
                print(f"🔄 FULL BUSINESS RULES: Validating all {fields_to_validate.count()} fields")
            
        elif context == 'storage' and changed_field_slug:
            # STORAGE CONTEXT: Only validate the changed field (fastest)
            fields_to_validate = self.fields.filter(slug=changed_field_slug)
            print(f"🎯 STORAGE VALIDATION: Only validating changed field: {changed_field_slug}")
            
        else:
            # FULL VALIDATION: New records or complete updates
            fields_to_validate = self.fields.all()
            print(f"🔄 FULL VALIDATION: Validating all {fields_to_validate.count()} fields")
        
        # Build field definitions for the necessary fields
        field_definitions = []
        for field in fields_to_validate:
            field_definitions.append({
                'slug': field.slug,
                'field_type': field.field_type,
                'field_config': field.field_config,
                'storage_constraints': field.storage_constraints,
                'business_rules': field.business_rules,
                'ai_config': field.ai_config if field.is_ai_field else {},
            })
        
        print(f"🔧 VALIDATION SCOPE: Processing {len(field_definitions)} field definition(s)")
        
        # Use the existing validation function with the filtered field definitions
        return validate_record_data(field_definitions, data, context)


class Field(models.Model):
    """Field definition for pipelines"""
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name='fields')
    
    # Field identification
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    
    # Field type and configuration
    field_type = models.CharField(max_length=50, choices=[(ft.value, ft.value) for ft in FieldType])
    field_config = models.JSONField(default=dict)
    
    # Storage constraints (database-level only)
    storage_constraints = models.JSONField(default=dict)
    
    # Business rules (pipeline stage requirements, conditional logic)
    business_rules = models.JSONField(default=dict)
    
    # Form validation rules (applied at form level, not storage level)
    form_validation_rules = models.JSONField(default=dict)
    
    # Display configuration
    display_name = models.CharField(max_length=255, blank=True)
    help_text = models.TextField(blank=True)
    
    # Field behavior (storage and system behavior only)
    # NOTE: is_required removed - this belongs to forms, not database storage
    enforce_uniqueness = models.BooleanField(default=False)  # True business uniqueness only
    create_index = models.BooleanField(default=False)        # Performance optimization
    is_searchable = models.BooleanField(default=True)        # Include in search operations
    is_ai_field = models.BooleanField(default=False)         # AI-powered field flag
    
    # UI configuration
    display_order = models.IntegerField(default=0)
    is_visible_in_list = models.BooleanField(default=True)
    is_visible_in_detail = models.BooleanField(default=True)
    is_visible_in_public_forms = models.BooleanField(default=False)  # Dynamic forms: public visibility
    
    # AI configuration (for AI fields)
    ai_config = models.JSONField(default=dict)
    
    # Soft delete functionality
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_fields')
    
    # Hard delete scheduling
    scheduled_for_hard_delete = models.DateTimeField(null=True, blank=True)
    hard_delete_reason = models.TextField(blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Custom manager
    objects = FieldManager()
    
    class Meta:
        db_table = 'pipelines_field'
        unique_together = ['pipeline', 'slug']
        indexes = [
            models.Index(fields=['pipeline']),
            models.Index(fields=['field_type']),
            models.Index(fields=['display_order']),
            models.Index(fields=['is_ai_field']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['scheduled_for_hard_delete']),
            # Composite indexes for common queries
            models.Index(fields=['pipeline', 'is_deleted'], name='idx_field_pipeline_active'),
            models.Index(fields=['is_deleted', 'deleted_at'], name='idx_field_deletion_status'),
            GinIndex(fields=['field_config']),
            GinIndex(fields=['storage_constraints']),
            GinIndex(fields=['business_rules']),
            GinIndex(fields=['ai_config']),
        ]
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return f"{self.pipeline.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        # Basic field setup - use custom field_slugify for consistency with data keys
        self.slug = field_slugify(self.name)
        if not self.display_name:
            self.display_name = self.name
        
        # Basic validation only - complex logic handled by FieldOperationManager
        self.clean()
        
        super().save(*args, **kwargs)
        
        # Update pipeline schema cache - keep this simple functionality
        try:
            self.pipeline._update_field_schema()
            self.pipeline.save(update_fields=['field_schema'])
        except Exception as e:
            logger.error(f"Failed to update pipeline schema cache after field save: {e}")
    
    def clean(self):
        """Validate field configuration"""
        try:
            field_type = FieldType(self.field_type)
            validate_field_config(field_type, self.field_config)
        except Exception as e:
            raise ValidationError(f'Invalid field configuration: {e}')
        
        # Validate AI configuration if it's an AI field
        if self.is_ai_field and self.field_type == FieldType.AI_GENERATED:
            if not self.ai_config.get('prompt'):  # Fixed: use 'prompt' not 'ai_prompt'
                raise ValidationError('AI fields must have a prompt in ai_config')
    
    def get_validator(self):
        """Get validator instance for this field"""
        ai_config = self.ai_config if self.is_ai_field else None
        return FieldValidator(FieldType(self.field_type), self.field_config, ai_config)
    
    def validate_value(self, value, context=None):
        """Validate a value against this field's storage constraints"""
        # Only validate storage constraints - form and business validation handled separately
        validator = self.get_validator()
        return validator.validate_storage(value, self.storage_constraints)
    
    def check_business_rules(self, record_data, target_stage=None):
        """Check if record meets business rules for this field"""
        if not self.business_rules:
            return True, []
        
        errors = []
        value = record_data.get(self.slug)
        
        # Check stage requirements
        stage_requirements = self.business_rules.get('stage_requirements', {})
        if target_stage and target_stage in stage_requirements:
            requirements = stage_requirements[target_stage]
            if requirements.get('required') and not value:
                errors.append(f"{self.display_name} is required for {target_stage} stage")
        
        # Check conditional requirements
        conditional_rules = self.business_rules.get('conditional_requirements', [])
        for rule in conditional_rules:
            condition_field = rule.get('condition_field')
            condition_value = rule.get('condition_value')
            requires_field = rule.get('requires_field') == self.slug
            
            if (requires_field and 
                condition_field in record_data and 
                record_data[condition_field] == condition_value and 
                not value):
                errors.append(f"{self.display_name} is required when {condition_field} is {condition_value}")
        
        return len(errors) == 0, errors
    
    def soft_delete(self, user, reason=""):
        """Soft delete the field - SIMPLIFIED to delegate to FieldOperationManager"""
        try:
            from .field_operations import get_field_operation_manager
            
            manager = get_field_operation_manager(self.pipeline)
            result = manager.delete_field(self.id, user, hard_delete=False)
            
            if result.success:
                return True, "Field soft deleted successfully"
            else:
                return False, '; '.join(result.errors)
                
        except Exception as e:
            logger.error(f"Failed to soft delete field {self.slug}: {e}")
            return False, f"Field deletion failed: {str(e)}"
    
    def restore(self, user):
        """Restore soft deleted field - SIMPLIFIED to delegate to FieldOperationManager"""
        try:
            from .field_operations import get_field_operation_manager
            
            manager = get_field_operation_manager(self.pipeline)
            result = manager.restore_field(self.id, user)
            
            if result.success:
                return True, "Field restored successfully"
            else:
                return False, '; '.join(result.errors)
                
        except Exception as e:
            logger.error(f"Failed to restore field {self.slug}: {e}")
            return False, f"Field restoration failed: {str(e)}"
    
    def validate_restore(self, user, dry_run=False):
        """Validate field restore operation - SIMPLIFIED to delegate to FieldValidator"""
        try:
            from .validation.field_validator import FieldValidator
            
            validator = FieldValidator()
            validation_result = validator.validate_field_restoration(self)
            
            return {
                'can_restore': validation_result.valid,
                'errors': validation_result.errors,
                'warnings': validation_result.warnings,
                'records_with_data': validation_result.metadata.get('records_with_data', 0),
                'field_name': self.name,
                'field_slug': self.slug
            }
        except Exception as e:
            logger.error(f"Failed to validate field restoration for {self.slug}: {e}")
            return {
                'can_restore': False,
                'errors': [f"Validation failed: {str(e)}"],
                'warnings': [],
                'field_name': self.name,
                'field_slug': self.slug
            }
    
    def restore_with_validation(self, user, force=False, dry_run=False):
        """Enhanced restore with validation and dry-run support"""
        validation_result = self.validate_restore(user, dry_run)
        
        # If dry run, return validation results
        if dry_run:
            return {
                'success': validation_result['can_restore'],
                'dry_run': True,
                'validation_result': validation_result,
                'message': 'Dry run completed - no changes made'
            }
        
        # Check if restore is allowed
        if not validation_result['can_restore'] and not force:
            return {
                'success': False,
                'errors': validation_result['errors'],
                'warnings': validation_result['warnings'],
                'validation_result': validation_result
            }
        
        # Perform actual restore
        try:
            success, message = self.restore(user)
            if success:
                return {
                    'success': True,
                    'message': message,
                    'validation_result': validation_result,
                    'field_status': 'active'
                }
            else:
                return {
                    'success': False,
                    'errors': [message],
                    'validation_result': validation_result
                }
        except Exception as e:
            return {
                'success': False,
                'errors': [f'Restore failed: {str(e)}'],
                'validation_result': validation_result
            }
    
    def schedule_hard_delete(self, user, reason, delete_date=None):
        """Schedule field for permanent deletion - SIMPLIFIED"""
        from django.utils import timezone
        from datetime import timedelta
        
        if delete_date is None:
            delete_date = timezone.now() + timedelta(days=7)
        
        # Soft delete first if needed
        if not self.is_deleted:
            self.soft_delete(user, f"Scheduled for hard deletion: {reason}")
        
        # Simple scheduling
        self.scheduled_for_hard_delete = delete_date
        self.hard_delete_reason = reason
        
        self.save(update_fields=['scheduled_for_hard_delete', 'hard_delete_reason'])
        
        logger.warning(f"Field {self.slug} scheduled for hard deletion on {delete_date} by {user.username}")
        return True, f"Field scheduled for permanent deletion on {delete_date.strftime('%Y-%m-%d %H:%M')}"
    
    def can_hard_delete(self):
        """Check if field can be hard deleted"""
        from django.utils import timezone
        
        if not self.scheduled_for_hard_delete:
            return False, "Field is not scheduled for hard deletion"
        
        if timezone.now() < self.scheduled_for_hard_delete:
            remaining = self.scheduled_for_hard_delete - timezone.now()
            return False, f"Grace period remaining: {remaining.days} days"
        
        return True, "Field can be hard deleted"
    
    def get_impact_analysis(self):
        """Get impact analysis for field deletion"""
        impact = {
            'record_count': 0,
            'records_with_data': 0,
            'dependent_systems': [],
            'risk_level': 'low'
        }
        
        # Count records in this pipeline
        total_records = self.pipeline.records.count()
        impact['record_count'] = total_records
        
        # Count records that actually have data for this field
        records_with_data = self.pipeline.records.filter(
            data__has_key=self.slug
        ).exclude(data__isnull=True).count()
        impact['records_with_data'] = records_with_data
        
        # Check dependent systems (simplified for now)
        dependent_systems = []
        
        # Check if field is referenced in business rules of other fields
        dependent_fields = self.pipeline.fields.filter(
            business_rules__conditional_requirements__condition_field=self.slug
        ).exclude(id=self.id)
        
        if dependent_fields.exists():
            dependent_systems.append({
                'system': 'field_dependencies',
                'count': dependent_fields.count(),
                'details': [f.name for f in dependent_fields[:5]]  # Show first 5
            })
        
        # Check AI fields that might reference this field
        ai_fields_dependent = self.pipeline.fields.filter(
            is_ai_field=True,
            ai_config__trigger_fields__contains=[self.slug]
        ).exclude(id=self.id)
        
        if ai_fields_dependent.exists():
            dependent_systems.append({
                'system': 'ai_dependencies', 
                'count': ai_fields_dependent.count(),
                'details': [f.name for f in ai_fields_dependent[:5]]
            })
        
        impact['dependent_systems'] = dependent_systems
        
        # Determine risk level
        if records_with_data > 1000 or len(dependent_systems) > 2:
            impact['risk_level'] = 'high'
        elif records_with_data > 100 or len(dependent_systems) > 0:
            impact['risk_level'] = 'medium'
        else:
            impact['risk_level'] = 'low'
        
        return impact


class Record(models.Model):
    """Dynamic record storage"""
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name='records')
    
    # Dynamic data storage
    data = models.JSONField(default=dict)
    
    # Record metadata
    title = models.CharField(max_length=500, blank=True)  # Computed display title
    status = models.CharField(max_length=100, default='active')
    
    # System fields
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_records')
    updated_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='updated_records')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Soft delete
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_records')
    
    # Version tracking
    version = models.IntegerField(default=1)
    
    # Search and tagging
    search_vector = SearchVectorField(null=True)
    tags = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    
    # AI-generated fields
    ai_summary = models.TextField(blank=True)
    ai_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ai_last_updated = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'pipelines_record'
        indexes = [
            models.Index(fields=['pipeline']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
            models.Index(fields=['is_deleted']),
            # Composite indexes for common queries
            models.Index(fields=['pipeline', 'status'], condition=models.Q(is_deleted=False), name='idx_rec_pipe_status_active'),
            models.Index(fields=['pipeline', 'updated_at'], condition=models.Q(is_deleted=False), name='idx_rec_pipe_updated_active'),
            # JSONB indexes
            GinIndex(fields=['data']),
            GinIndex(fields=['tags']),
        ]
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.title or f"Record {self.id}"
    
    def save(self, *args, **kwargs):
        # Track if this is a new record
        is_new = self.pk is None
        
        print(f"🟢 DATABASE STEP 1: Model Save Starting")
        print(f"   🆔 Record ID: {self.pk or 'NEW'}")
        print(f"   📦 Data to save: {self.data}")
        if self.data:
            print(f"   🔑 Data contains {len(self.data)} field(s): [{', '.join(self.data.keys())}]")
            null_fields = [k for k, v in self.data.items() if v is None]
            if null_fields:
                print(f"   ⚠️  Data contains {len(null_fields)} NULL fields: [{', '.join(null_fields)}]")
        
        # Store original data for change detection
        original_data = {}
        if not is_new:
            try:
                original_record = Record.objects.get(pk=self.pk)
                original_data = original_record.data.copy()
                print(f"   📊 Original data had {len(original_data)} fields")
            except Record.DoesNotExist:
                pass
        
        # Initialize changed_fields for all cases
        changed_fields = set()
        
        # Determine validation context based on update type
        if not is_new and original_data:
            # Check what fields changed to determine if this is a partial update
            current_data = self.data or {}
            
            for field_name in set(list(original_data.keys()) + list(current_data.keys())):
                old_value = original_data.get(field_name)
                new_value = current_data.get(field_name)
                if old_value != new_value:
                    changed_fields.add(field_name)
            
            # Consider it a partial update if only a few fields changed
            is_partial_update = len(changed_fields) <= 3 and len(changed_fields) > 0
            validation_context = 'storage' if is_partial_update else 'business_rules'
            
            print(f"🔍 UPDATE ANALYSIS: {len(changed_fields)} field(s) changed: {list(changed_fields)}")
            print(f"   📋 Context: {validation_context} {'(partial update)' if is_partial_update else '(full update)'}")
        else:
            # New records always get full business rules validation
            validation_context = 'business_rules'
            print(f"🔍 NEW RECORD: Using business_rules validation context")
        
        # Determine which field(s) changed for optimized validation
        changed_field_slug = None
        if not is_new and validation_context in ['storage', 'business_rules'] and len(changed_fields) == 1:
            changed_field_slug = list(changed_fields)[0]
            print(f"🎯 SINGLE FIELD CHANGE DETECTED: {changed_field_slug}")
        
        # Use optimized validation with dependency tracking
        validation_result = self.pipeline.validate_record_data_optimized(
            self.data, 
            validation_context, 
            changed_field_slug=changed_field_slug
        )
        if not validation_result['is_valid']:
            # Flatten validation errors for Django ValidationError
            error_messages = []
            for field_name, field_errors in validation_result['errors'].items():
                if isinstance(field_errors, list):
                    error_messages.extend([f"{field_name}: {error}" for error in field_errors])
                else:
                    error_messages.append(f"{field_name}: {field_errors}")
            raise ValidationError(error_messages)
        
        # Update cleaned data - MERGE with existing data to prevent data loss
        if not is_new and original_data:
            # Merge validated fields with existing data
            merged_data = original_data.copy()
            merged_data.update(validation_result['cleaned_data'])
            self.data = merged_data
            print(f"   🔄 MERGE: Combined {len(original_data)} existing + {len(validation_result['cleaned_data'])} validated = {len(merged_data)} total fields")
        else:
            # New records or full updates can replace data entirely
            self.data = validation_result['cleaned_data']
        
        print(f"🟢 DATABASE STEP 2: After Validation")
        print(f"   📦 Cleaned data: {self.data}")
        if self.data:
            print(f"   🔑 Cleaned contains {len(self.data)} field(s): [{', '.join(self.data.keys())}]")
            null_fields = [k for k, v in self.data.items() if v is None]
            if null_fields:
                print(f"   ⚠️  Cleaned contains {len(null_fields)} NULL fields: [{', '.join(null_fields)}]")
        
        # Generate title if not provided
        if not self.title:
            self.title = self._generate_title()
        
        # Update version if data changed
        if not is_new and original_data != self.data:
            self.version += 1
        
        print(f"🟢 DATABASE STEP 3: Saving to Database")
        super().save(*args, **kwargs)
        print(f"   ✅ Database save complete for record {self.pk}")
        
        # Update search vector
        self._update_search_vector()
        
        # Update pipeline statistics
        if is_new:
            self._update_pipeline_stats()
        
        # Trigger AI field updates if data changed
        if not is_new:
            changed_fields = self._get_changed_fields(original_data, self.data)
            if changed_fields:
                self._trigger_ai_updates(changed_fields)
        
        # Broadcast record update
        from api.events import broadcaster
        if hasattr(self, '_skip_broadcast') and self._skip_broadcast:
            return
        
        try:
            import asyncio
            changes = self._get_changed_fields(original_data, self.data) if not is_new and original_data else None
            
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(broadcaster.broadcast_record_update(
                    self, 
                    event_type="created" if is_new else "updated",
                    user_id=getattr(self, '_current_user_id', None),
                    changes=changes
                ))
            else:
                broadcaster.sync_broadcast_record_update(
                    self, 
                    event_type="created" if is_new else "updated",
                    user_id=getattr(self, '_current_user_id', None),
                    changes=changes
                )
        except Exception:
            pass  # Don't fail save if broadcast fails
    
    def _generate_title(self) -> str:
        """Generate display title from record data"""
        # Look for common title fields
        title_fields = ['name', 'title', 'subject', 'company', 'company_name', 'full_name', 'first_name']
        
        for field_slug in title_fields:
            if field_slug in self.data and self.data[field_slug]:
                return str(self.data[field_slug])[:500]
        
        # Fallback to first non-empty field
        for key, value in self.data.items():
            if value and isinstance(value, (str, int, float)):
                return f"{key}: {str(value)[:100]}"
        
        # Final fallback
        return f"{self.pipeline.name} Record #{self.id or 'New'}"
    
    def _update_search_vector(self):
        """Update full-text search vector"""
        from django.contrib.postgres.search import SearchVector
        
        # Get searchable field values
        searchable_text = []
        
        for field in self.pipeline.fields.filter(is_searchable=True):
            value = self.data.get(field.slug)
            if value:
                if isinstance(value, (list, dict)):
                    searchable_text.append(str(value))
                else:
                    searchable_text.append(str(value))
        
        # Add title and tags
        if self.title:
            searchable_text.append(self.title)
        if self.tags:
            searchable_text.extend(self.tags)
        
        # Update search vector
        if searchable_text:
            search_text = ' '.join(searchable_text)
            Record.objects.filter(id=self.id).update(
                search_vector=SearchVector('title') + SearchVector(models.Value(search_text))
            )
    
    def _update_pipeline_stats(self):
        """Update pipeline statistics"""
        from django.utils import timezone
        
        Pipeline.objects.filter(id=self.pipeline_id).update(
            record_count=models.F('record_count') + 1,
            last_record_created=timezone.now()
        )
    
    def _get_changed_fields(self, old_data: dict, new_data: dict) -> list:
        """Get list of fields that changed"""
        changed_fields = []
        
        # Check for changed values
        for field_slug in set(old_data.keys()) | set(new_data.keys()):
            old_value = old_data.get(field_slug)
            new_value = new_data.get(field_slug)
            
            if old_value != new_value:
                changed_fields.append(field_slug)
        
        return changed_fields
    
    def _trigger_ai_updates(self, changed_fields: list):
        """Trigger AI field updates using the unified AI system"""
        try:
            from ai.integrations import trigger_field_ai_processing
            
            # Get the user who made the change (if available)
            user = getattr(self, '_current_user', None) or self.updated_by
            if not user:
                logger.warning(f"No user context for AI processing on record {self.id}")
                return
            
            # Trigger AI processing using the new unified system
            result = trigger_field_ai_processing(self, changed_fields, user)
            logger.info(f"AI processing triggered for record {self.id}: {len(result.get('triggered_jobs', []))} fields processed")
            
        except Exception as e:
            logger.error(f"Failed to trigger AI processing for record {self.id}: {e}")
    
    def soft_delete(self, deleted_by: User):
        """Soft delete the record"""
        from django.utils import timezone
        
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
    
    def restore(self):
        """Restore soft-deleted record"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
    
    def get_field_value(self, field_slug: str, default=None):
        """Get value for a specific field"""
        return self.data.get(field_slug, default)
    
    def set_field_value(self, field_slug: str, value):
        """Set value for a specific field"""
        self.data[field_slug] = value
    
    def to_dict(self, include_metadata=False):
        """Convert record to dictionary"""
        result = {
            'id': self.id,
            'title': self.title,
            'status': self.status,
            'data': self.data,
            'tags': self.tags,
        }
        
        if include_metadata:
            result.update({
                'created_by': self.created_by.username if self.created_by else None,
                'updated_by': self.updated_by.username if self.updated_by else None,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None,
                'version': self.version,
                'pipeline': {
                    'id': self.pipeline.id,
                    'name': self.pipeline.name,
                    'slug': self.pipeline.slug,
                }
            })
        
        return result