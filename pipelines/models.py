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

from .field_types import FieldType, FIELD_TYPE_CONFIGS, validate_field_config
from .validators import FieldValidator, validate_record_data

User = get_user_model()
logger = logging.getLogger(__name__)


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
            self.slug = slugify(self.name)
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
                display_name=field_data.get('display_name', field_data['name']),
                help_text=field_data.get('help_text', ''),
                placeholder=field_data.get('placeholder', ''),
                is_required=field_data.get('is_required', False),
                is_unique=field_data.get('is_unique', False),
                is_indexed=field_data.get('is_indexed', False),
                is_searchable=field_data.get('is_searchable', True),
                is_ai_field=field_data.get('is_ai_field', False),
                display_order=field_data.get('display_order', 0),
                width=field_data.get('width', 'full'),
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
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='private')
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
            self.slug = slugify(self.name)
        
        # Update field schema cache
        if self.pk:  # Only if pipeline already exists
            self._update_field_schema()
        
        super().save(*args, **kwargs)
        
        # Broadcast pipeline update
        from api.events import broadcaster
        if hasattr(self, '_skip_broadcast') and self._skip_broadcast:
            return
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(broadcaster.broadcast_pipeline_update(
                    self, 
                    event_type="updated" if self.pk else "created",
                    user_id=getattr(self, '_current_user_id', None)
                ))
            else:
                broadcaster.sync_broadcast_pipeline_update(
                    self, 
                    event_type="updated" if self.pk else "created",
                    user_id=getattr(self, '_current_user_id', None)
                )
        except Exception:
            pass  # Don't fail save if broadcast fails
    
    def _update_field_schema(self):
        """Update cached field schema from related fields"""
        fields_data = {}
        for field in self.fields.all():
            fields_data[field.slug] = {
                'name': field.name,
                'type': field.field_type,
                'config': field.field_config,
                'required': field.is_required,
                'indexed': field.is_indexed,
                'searchable': field.is_searchable,
                'ai_field': field.is_ai_field,
            }
        self.field_schema = fields_data
    
    def get_field_by_slug(self, slug: str):
        """Get field by slug"""
        try:
            return self.fields.get(slug=slug)
        except Field.DoesNotExist:
            return None
    
    def validate_record_data(self, data: dict) -> dict:
        """Validate record data against pipeline schema"""
        field_definitions = []
        for field in self.fields.all():
            field_definitions.append({
                'slug': field.slug,
                'field_type': field.field_type,
                'field_config': field.field_config,
                'ai_config': field.ai_config if field.is_ai_field else {},
                'is_required': field.is_required,
            })
        
        return validate_record_data(field_definitions, data)
    
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
                validation_rules=field.validation_rules.copy(),
                display_name=field.display_name,
                help_text=field.help_text,
                placeholder=field.placeholder,
                is_required=field.is_required,
                is_unique=field.is_unique,
                is_indexed=field.is_indexed,
                is_searchable=field.is_searchable,
                is_ai_field=field.is_ai_field,
                display_order=field.display_order,
                width=field.width,
                is_visible_in_list=field.is_visible_in_list,
                is_visible_in_detail=field.is_visible_in_detail,
                ai_config=field.ai_config.copy(),
                created_by=created_by
            )
        
        return new_pipeline


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
    validation_rules = models.JSONField(default=dict)
    
    # Display configuration
    display_name = models.CharField(max_length=255, blank=True)
    help_text = models.TextField(blank=True)
    placeholder = models.CharField(max_length=255, blank=True)
    
    # Field behavior
    is_required = models.BooleanField(default=False)
    is_unique = models.BooleanField(default=False)
    is_indexed = models.BooleanField(default=False)
    is_searchable = models.BooleanField(default=True)
    is_ai_field = models.BooleanField(default=False)
    
    # UI configuration
    display_order = models.IntegerField(default=0)
    width = models.CharField(max_length=20, default='full')  # 'quarter', 'half', 'full'
    is_visible_in_list = models.BooleanField(default=True)
    is_visible_in_detail = models.BooleanField(default=True)
    
    # AI configuration (for AI fields)
    ai_config = models.JSONField(default=dict)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pipelines_field'
        unique_together = ['pipeline', 'slug']
        indexes = [
            models.Index(fields=['pipeline']),
            models.Index(fields=['field_type']),
            models.Index(fields=['display_order']),
            models.Index(fields=['is_ai_field']),
            GinIndex(fields=['field_config']),
            GinIndex(fields=['ai_config']),
        ]
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return f"{self.pipeline.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.display_name:
            self.display_name = self.name
        
        # Validate field configuration
        self.clean()
        
        super().save(*args, **kwargs)
        
        # Update pipeline field schema cache
        self.pipeline._update_field_schema()
        self.pipeline.save(update_fields=['field_schema'])
    
    def clean(self):
        """Validate field configuration"""
        try:
            field_type = FieldType(self.field_type)
            validate_field_config(field_type, self.field_config)
        except Exception as e:
            raise ValidationError(f'Invalid field configuration: {e}')
        
        # Validate AI configuration if it's an AI field
        if self.is_ai_field and self.field_type == FieldType.AI_FIELD:
            if not self.ai_config.get('ai_prompt'):
                raise ValidationError('AI fields must have an ai_prompt in ai_config')
    
    def get_validator(self):
        """Get validator instance for this field"""
        return FieldValidator(FieldType(self.field_type), self.field_config)
    
    def validate_value(self, value, is_required=None):
        """Validate a value against this field"""
        if is_required is None:
            is_required = self.is_required
        
        validator = self.get_validator()
        return validator.validate(value, is_required)


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
        
        # Store original data for change detection
        original_data = {}
        if not is_new:
            try:
                original_record = Record.objects.get(pk=self.pk)
                original_data = original_record.data.copy()
            except Record.DoesNotExist:
                pass
        
        # Validate data against pipeline schema
        validation_result = self.pipeline.validate_record_data(self.data)
        if not validation_result['is_valid']:
            # Flatten validation errors for Django ValidationError
            error_messages = []
            for field_name, field_errors in validation_result['errors'].items():
                if isinstance(field_errors, list):
                    error_messages.extend([f"{field_name}: {error}" for error in field_errors])
                else:
                    error_messages.append(f"{field_name}: {field_errors}")
            raise ValidationError(error_messages)
        
        # Update cleaned data
        self.data = validation_result['cleaned_data']
        
        # Generate title if not provided
        if not self.title:
            self.title = self._generate_title()
        
        # Update version if data changed
        if not is_new and original_data != self.data:
            self.version += 1
        
        super().save(*args, **kwargs)
        
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
        """Trigger AI field updates based on changed fields"""
        # This will be implemented in the AI processor
        # For now, just log the trigger
        logger.info(f"Record {self.id} changed fields: {changed_fields} - triggering AI updates")
    
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