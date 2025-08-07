"""
Relationship models for managing bidirectional, multi-hop relationships between records
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from pipelines.models import Pipeline, Record, field_slugify
from authentication.models import UserType
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class RelationshipType(models.Model):
    """Defines types of relationships between records"""
    
    CARDINALITY_CHOICES = [
        ('one_to_one', 'One to One'),
        ('one_to_many', 'One to Many'),
        ('many_to_many', 'Many to Many'),
    ]
    
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Relationship configuration
    cardinality = models.CharField(max_length=20, choices=CARDINALITY_CHOICES, default='many_to_many')
    is_bidirectional = models.BooleanField(default=True)
    
    # Pipeline constraints
    source_pipeline = models.ForeignKey(
        Pipeline, 
        on_delete=models.CASCADE, 
        related_name='outgoing_relationship_types',
        null=True, blank=True,  # Null means any pipeline
        help_text="Source pipeline constraint (null = any pipeline)"
    )
    target_pipeline = models.ForeignKey(
        Pipeline, 
        on_delete=models.CASCADE, 
        related_name='incoming_relationship_types',
        null=True, blank=True,  # Null means any pipeline
        help_text="Target pipeline constraint (null = any pipeline)"
    )
    
    # Display labels
    forward_label = models.CharField(max_length=255, help_text="e.g., 'works at', 'applied to'")
    reverse_label = models.CharField(max_length=255, blank=True, help_text="e.g., 'employs', 'has applicant'")
    
    # Permission settings
    requires_permission = models.BooleanField(default=True)
    permission_config = models.JSONField(default=dict)
    
    # Behavior settings
    cascade_delete = models.BooleanField(default=False)
    allow_self_reference = models.BooleanField(default=False)
    allow_user_relationships = models.BooleanField(
        default=False,
        help_text="Allow this relationship type to be used for user-to-record assignments"
    )
    
    # Metadata
    is_system = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'relationships_relationshiptype'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['source_pipeline', 'target_pipeline']),
            models.Index(fields=['is_system']),
        ]
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = field_slugify(self.name)
        if not self.reverse_label and self.is_bidirectional:
            self.reverse_label = f"reverse_{self.forward_label}"
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate relationship type configuration"""
        if self.source_pipeline and self.target_pipeline:
            if self.source_pipeline == self.target_pipeline and not self.allow_self_reference:
                raise ValidationError("Self-reference not allowed for this relationship type")
    
    def can_create_relationship(self, source_pipeline, target_pipeline):
        """Check if this relationship type can be used between given pipelines"""
        if self.source_pipeline and self.source_pipeline != source_pipeline:
            return False
        if self.target_pipeline and self.target_pipeline != target_pipeline:
            return False
        return True
    
    @classmethod
    def create_system_types(cls):
        """Create common system relationship types"""
        # Record-to-record relationship types
        record_types = [
            {
                'name': 'Works At',
                'slug': 'works_at',
                'forward_label': 'works at',
                'reverse_label': 'employs',
                'cardinality': 'many_to_one',
                'description': 'Employment relationship between person and company',
                'allow_user_relationships': False
            },
            {
                'name': 'Applied To',
                'slug': 'applied_to',
                'forward_label': 'applied to',
                'reverse_label': 'received application from',
                'cardinality': 'many_to_many',
                'description': 'Job application relationship',
                'allow_user_relationships': False
            },
            {
                'name': 'Related To',
                'slug': 'related_to',
                'forward_label': 'related to',
                'reverse_label': 'related to',
                'cardinality': 'many_to_many',
                'description': 'General relationship between any records',
                'allow_user_relationships': False
            },
            {
                'name': 'Parent Of',
                'slug': 'parent_of',
                'forward_label': 'parent of',
                'reverse_label': 'child of',
                'cardinality': 'one_to_many',
                'description': 'Hierarchical parent-child relationship',
                'allow_user_relationships': False
            }
        ]
        
        # User-to-record assignment types
        assignment_types = [
            {
                'name': 'Assigned To',
                'slug': 'assigned_to',
                'forward_label': 'assigned to',
                'reverse_label': 'assigned',
                'cardinality': 'many_to_many',
                'description': 'User assigned to record',
                'allow_user_relationships': True
            },
            {
                'name': 'Owns',
                'slug': 'owns',
                'forward_label': 'owns',
                'reverse_label': 'owned by',
                'cardinality': 'many_to_one',
                'description': 'User owns/is responsible for record',
                'allow_user_relationships': True
            },
            {
                'name': 'Collaborates On',
                'slug': 'collaborates_on',
                'forward_label': 'collaborates on', 
                'reverse_label': 'collaborated on by',
                'cardinality': 'many_to_many',
                'description': 'User collaborates on record',
                'allow_user_relationships': True
            },
            {
                'name': 'Manages',
                'slug': 'manages',
                'forward_label': 'manages',
                'reverse_label': 'managed by',
                'cardinality': 'many_to_many',
                'description': 'User manages/oversees record',
                'allow_user_relationships': True
            },
            {
                'name': 'Reviews',
                'slug': 'reviews',
                'forward_label': 'reviews',
                'reverse_label': 'reviewed by',
                'cardinality': 'many_to_many', 
                'description': 'User reviews/approves record',
                'allow_user_relationships': True
            }
        ]
        
        # Combine all system types
        system_types = record_types + assignment_types
        
        for type_data in system_types:
            cls.objects.get_or_create(
                slug=type_data['slug'],
                defaults={**type_data, 'is_system': True}
            )


class Relationship(models.Model):
    """Individual relationship instance between records or between user and record"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending'),
    ]
    
    ROLE_CHOICES = [
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
        ('viewer', 'Viewer'),
        ('collaborator', 'Collaborator'),
    ]
    
    relationship_type = models.ForeignKey(RelationshipType, on_delete=models.CASCADE)
    
    # User (optional - for user-to-record relationships)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='relationships',
        help_text="User involved in this relationship (for user-to-record relationships)"
    )
    
    # Source record (optional when user is specified)
    source_pipeline = models.ForeignKey(
        Pipeline, 
        on_delete=models.CASCADE, 
        related_name='outgoing_relationships',
        null=True,
        blank=True
    )
    source_record_id = models.IntegerField(null=True, blank=True)
    
    # Target record (required)
    target_pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name='incoming_relationships')
    target_record_id = models.IntegerField()
    
    # Relationship metadata
    metadata = models.JSONField(default=dict)
    strength = models.DecimalField(max_digits=3, decimal_places=2, default=1.0)
    
    # Role (for user assignments)
    role = models.CharField(
        max_length=50, 
        choices=ROLE_CHOICES, 
        default='primary',
        help_text="Role of the user in this relationship (for user-to-record relationships)"
    )
    
    # Status
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='active')
    is_verified = models.BooleanField(default=False)
    
    # Permissions (for user assignments)
    can_edit = models.BooleanField(default=True)
    can_delete = models.BooleanField(default=False)
    
    # Lifecycle
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Soft delete
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_relationships')
    
    class Meta:
        db_table = 'relationships_relationship'
        constraints = [
            # Ensure either user+target OR source+target combination
            models.CheckConstraint(
                check=(
                    models.Q(user__isnull=False, source_pipeline__isnull=True, source_record_id__isnull=True) |
                    models.Q(user__isnull=True, source_pipeline__isnull=False, source_record_id__isnull=False)
                ),
                name='relationship_source_constraint'
            ),
        ]
        unique_together = [
            # Record-to-record relationships
            ['relationship_type', 'source_pipeline', 'source_record_id', 
             'target_pipeline', 'target_record_id'],
            # User-to-record relationships
            ['relationship_type', 'user', 'target_pipeline', 'target_record_id', 'role']
        ]
        indexes = [
            models.Index(fields=['source_pipeline', 'source_record_id']),
            models.Index(fields=['target_pipeline', 'target_record_id']),
            models.Index(fields=['relationship_type']),
            models.Index(fields=['status']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['user']),
            models.Index(fields=['role']),
            models.Index(fields=['created_at']),
            # Composite indexes for bidirectional queries
            models.Index(
                fields=['source_pipeline', 'source_record_id', 'relationship_type'], 
                condition=models.Q(is_deleted=False, user__isnull=True),
                name='idx_rel_src_type_active'
            ),
            models.Index(
                fields=['target_pipeline', 'target_record_id', 'relationship_type'], 
                condition=models.Q(is_deleted=False, user__isnull=True),
                name='idx_rel_tgt_type_active'
            ),
            # User assignment indexes
            models.Index(
                fields=['user', 'relationship_type', 'status'], 
                condition=models.Q(is_deleted=False, user__isnull=False),
                name='idx_user_rel_status_active'
            ),
            models.Index(
                fields=['target_pipeline', 'target_record_id', 'user'], 
                condition=models.Q(is_deleted=False, user__isnull=False),
                name='idx_target_user_active'
            ),
            models.Index(
                fields=['user', 'role'], 
                condition=models.Q(is_deleted=False, user__isnull=False),
                name='idx_user_role_active'
            ),
            # Performance indexes for graph traversal
            models.Index(
                fields=['relationship_type', 'status'], 
                condition=models.Q(is_deleted=False),
                name='idx_type_status_active'
            ),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        if self.user:
            return f"{self.user.email} -> {self.relationship_type.name} -> {self.target_pipeline.name}:{self.target_record_id}"
        else:
            return f"{self.source_pipeline.name}:{self.source_record_id} -> {self.target_pipeline.name}:{self.target_record_id}"
    
    @property
    def source_record(self):
        """Get the source record"""
        try:
            return Record.objects.get(
                pipeline=self.source_pipeline,
                id=self.source_record_id,
                is_deleted=False
            )
        except Record.DoesNotExist:
            return None
    
    @property
    def target_record(self):
        """Get the target record"""
        try:
            return Record.objects.get(
                pipeline=self.target_pipeline,
                id=self.target_record_id,
                is_deleted=False
            )
        except Record.DoesNotExist:
            return None
    
    def clean(self):
        """Validate relationship"""
        # Ensure either user or source is provided
        if self.user and (self.source_pipeline or self.source_record_id):
            raise ValidationError("Cannot specify both user and source record")
        
        if not self.user and not (self.source_pipeline and self.source_record_id):
            raise ValidationError("Must specify either user or source record")
        
        # User relationship validation
        if self.user:
            if not self.relationship_type.allow_user_relationships:
                raise ValidationError("This relationship type does not support user assignments")
        else:
            # Record-to-record relationship validation
            if not self.relationship_type.can_create_relationship(
                self.source_pipeline, self.target_pipeline
            ):
                raise ValidationError("Relationship type not compatible with these pipelines")
            
            # Check self-reference
            if (self.source_pipeline == self.target_pipeline and 
                self.source_record_id == self.target_record_id and 
                not self.relationship_type.allow_self_reference):
                raise ValidationError("Self-reference not allowed for this relationship type")
        
        # Check cardinality constraints
        self._validate_cardinality()
    
    def _validate_cardinality(self):
        """Validate cardinality constraints"""
        if self.user:
            # User relationship cardinality validation
            if self.relationship_type.cardinality == 'one_to_one':
                existing = Relationship.objects.filter(
                    relationship_type=self.relationship_type,
                    target_pipeline=self.target_pipeline,
                    target_record_id=self.target_record_id,
                    user__isnull=False,
                    is_deleted=False
                ).exclude(id=self.id if self.id else None)
                
                if existing.exists():
                    raise ValidationError("Target record can only have one user assignment of this type")
            
            elif self.relationship_type.cardinality == 'many_to_one':
                existing = Relationship.objects.filter(
                    relationship_type=self.relationship_type,
                    user=self.user,
                    target_pipeline=self.target_pipeline,
                    is_deleted=False
                ).exclude(id=self.id if self.id else None)
                
                if existing.exists():
                    raise ValidationError("User can only have one assignment of this type per pipeline")
        else:
            # Record-to-record cardinality validation
            if self.relationship_type.cardinality == 'one_to_one':
                existing = Relationship.objects.filter(
                    relationship_type=self.relationship_type,
                    source_pipeline=self.source_pipeline,
                    source_record_id=self.source_record_id,
                    user__isnull=True,
                    is_deleted=False
                ).exclude(id=self.id if self.id else None)
                
                if existing.exists():
                    raise ValidationError("One-to-one relationship already exists for source record")
            
            elif self.relationship_type.cardinality == 'one_to_many':
                existing = Relationship.objects.filter(
                    relationship_type=self.relationship_type,
                    target_pipeline=self.target_pipeline,
                    target_record_id=self.target_record_id,
                    user__isnull=True,
                    is_deleted=False
                ).exclude(id=self.id if self.id else None)
                
                if existing.exists():
                    raise ValidationError("Target record can only have one relationship of this type")
    
    def delete(self, soft=True):
        """Soft or hard delete relationship"""
        if soft:
            self.is_deleted = True
            self.deleted_at = timezone.now()
            self.save(update_fields=['is_deleted', 'deleted_at'])
        else:
            super().delete()
    
    def create_reverse_relationship(self):
        """Create reverse relationship if bidirectional"""
        if not self.relationship_type.is_bidirectional:
            return None
        
        # Check if reverse already exists
        reverse_exists = Relationship.objects.filter(
            relationship_type=self.relationship_type,
            source_pipeline=self.target_pipeline,
            source_record_id=self.target_record_id,
            target_pipeline=self.source_pipeline,
            target_record_id=self.source_record_id,
            is_deleted=False
        ).exists()
        
        if reverse_exists:
            return None
        
        # Create reverse relationship
        reverse_rel = Relationship.objects.create(
            relationship_type=self.relationship_type,
            source_pipeline=self.target_pipeline,
            source_record_id=self.target_record_id,
            target_pipeline=self.source_pipeline,
            target_record_id=self.source_record_id,
            metadata=self.metadata,
            strength=self.strength,
            status=self.status,
            created_by=self.created_by
        )
        
        return reverse_rel
    
    @classmethod
    def assign_user(cls, user, pipeline, record_id, relationship_type='assigned_to', role='primary', created_by=None):
        """Helper method to assign a user to a record"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if isinstance(relationship_type, str):
            rel_type = RelationshipType.objects.get(slug=relationship_type)
        else:
            rel_type = relationship_type
        
        return cls.objects.create(
            relationship_type=rel_type,
            user=user,
            target_pipeline=pipeline,
            target_record_id=record_id,
            role=role,
            created_by=created_by or user
        )
    
    @classmethod
    def reassign_user(cls, pipeline, record_id, from_user, to_user, relationship_type='assigned_to', role='primary', created_by=None):
        """Helper method to reassign a record from one user to another"""
        if isinstance(relationship_type, str):
            rel_type = RelationshipType.objects.get(slug=relationship_type)
        else:
            rel_type = relationship_type
        
        # Remove old assignment
        old_assignments = cls.objects.filter(
            relationship_type=rel_type,
            user=from_user,
            target_pipeline=pipeline,
            target_record_id=record_id,
            is_deleted=False
        )
        for assignment in old_assignments:
            assignment.delete(soft=True)
        
        # Create new assignment
        return cls.assign_user(to_user, pipeline, record_id, rel_type, role, created_by)
    
    @classmethod
    def get_user_assignments(cls, user, relationship_type=None, pipeline=None):
        """Get all records assigned to a user"""
        queryset = cls.objects.filter(
            user=user,
            is_deleted=False,
            status='active'
        )
        
        if relationship_type:
            if isinstance(relationship_type, str):
                queryset = queryset.filter(relationship_type__slug=relationship_type)
            else:
                queryset = queryset.filter(relationship_type=relationship_type)
        
        if pipeline:
            queryset = queryset.filter(target_pipeline=pipeline)
        
        return queryset
    
    @classmethod
    def get_record_assignees(cls, pipeline, record_id, relationship_type=None):
        """Get all users assigned to a record"""
        queryset = cls.objects.filter(
            target_pipeline=pipeline,
            target_record_id=record_id,
            user__isnull=False,
            is_deleted=False,
            status='active'
        )
        
        if relationship_type:
            if isinstance(relationship_type, str):
                queryset = queryset.filter(relationship_type__slug=relationship_type)
            else:
                queryset = queryset.filter(relationship_type=relationship_type)
        
        return queryset


# UserRelationship model removed - functionality unified into Relationship model above


class PermissionTraversal(models.Model):
    """Permission configuration for relationship traversal per user type"""
    
    user_type = models.ForeignKey(UserType, on_delete=models.CASCADE)
    relationship_type = models.ForeignKey(RelationshipType, on_delete=models.CASCADE)
    
    # Traversal permissions
    can_traverse_forward = models.BooleanField(default=True)
    can_traverse_reverse = models.BooleanField(default=True)
    max_depth = models.IntegerField(default=3)
    
    # Field visibility configuration
    visible_fields = models.JSONField(default=dict, help_text="Fields visible through this relationship")
    restricted_fields = models.JSONField(default=dict, help_text="Fields to hide through this relationship")
    
    # Traversal conditions
    traversal_conditions = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'relationships_permissiontraversal'
        unique_together = ['user_type', 'relationship_type']
        indexes = [
            models.Index(fields=['user_type']),
            models.Index(fields=['relationship_type']),
        ]
    
    def __str__(self):
        return f"{self.user_type.name} - {self.relationship_type.name}"


class RelationshipPath(models.Model):
    """Materialized relationship paths for efficient multi-hop queries"""
    
    # Path endpoints
    source_pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name='outgoing_paths')
    source_record_id = models.IntegerField()
    target_pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name='incoming_paths')
    target_record_id = models.IntegerField()
    
    # Path metadata
    path_length = models.IntegerField()
    path_relationships = ArrayField(models.IntegerField(), help_text="Array of relationship IDs in path")
    path_types = ArrayField(models.IntegerField(), help_text="Array of relationship type IDs")
    
    # Path scoring
    path_strength = models.DecimalField(max_digits=5, decimal_places=3, default=1.0)
    path_weight = models.IntegerField(default=1)
    
    # Caching metadata
    computed_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'relationships_relationshippath'
        unique_together = [
            ['source_pipeline', 'source_record_id', 
             'target_pipeline', 'target_record_id', 'path_length']
        ]
        indexes = [
            models.Index(fields=['source_pipeline', 'source_record_id']),
            models.Index(fields=['target_pipeline', 'target_record_id']),
            models.Index(fields=['path_length']),
            models.Index(fields=['expires_at']),
            # GIN indexes for array columns
            GinIndex(fields=['path_relationships']),
            GinIndex(fields=['path_types']),
        ]
        ordering = ['path_length', '-path_strength']
    
    def __str__(self):
        return f"Path: {self.source_pipeline.name}:{self.source_record_id} -> {self.target_pipeline.name}:{self.target_record_id} ({self.path_length} hops)"
    
    def is_expired(self):
        """Check if path cache has expired"""
        return timezone.now() > self.expires_at
