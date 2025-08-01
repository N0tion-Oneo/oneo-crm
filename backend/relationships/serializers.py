"""
Serializers for relationship management API
"""
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from pipelines.models import Pipeline, Record
from authentication.models import UserType
from .models import (
    RelationshipType, 
    Relationship, 
    PermissionTraversal, 
    RelationshipPath
)


class RelationshipTypeSerializer(serializers.ModelSerializer):
    """Serializer for relationship types"""
    
    source_pipeline_name = serializers.CharField(source='source_pipeline.name', read_only=True)
    target_pipeline_name = serializers.CharField(source='target_pipeline.name', read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    
    class Meta:
        model = RelationshipType
        fields = [
            'id', 'name', 'slug', 'description', 'cardinality', 'is_bidirectional',
            'source_pipeline', 'source_pipeline_name', 'target_pipeline', 'target_pipeline_name',
            'forward_label', 'reverse_label', 'requires_permission', 'permission_config',
            'cascade_delete', 'allow_self_reference', 'is_system', 'created_by', 'created_by_email',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'is_system', 'created_by', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate relationship type configuration"""
        try:
            # Create a temporary instance for validation
            temp_instance = RelationshipType(**data)
            temp_instance.clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict)
        
        return data


class RelationshipCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating relationships"""
    
    source_record = serializers.IntegerField(source='source_record_id')
    target_record = serializers.IntegerField(source='target_record_id')
    
    class Meta:
        model = Relationship
        fields = [
            'relationship_type', 'source_pipeline', 'source_record',
            'target_pipeline', 'target_record', 'metadata', 'strength'
        ]
    
    def validate(self, data):
        """Validate relationship creation"""
        # Check if source record exists
        try:
            source_record = Record.objects.get(
                pipeline=data['source_pipeline'],
                id=data['source_record_id'],
                is_deleted=False
            )
        except Record.DoesNotExist:
            raise serializers.ValidationError("Source record does not exist")
        
        # Check if target record exists
        try:
            target_record = Record.objects.get(
                pipeline=data['target_pipeline'],
                id=data['target_record_id'],
                is_deleted=False
            )
        except Record.DoesNotExist:
            raise serializers.ValidationError("Target record does not exist")
        
        # Validate relationship constraints
        try:
            temp_instance = Relationship(**data)
            temp_instance.clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict)
        
        return data
    
    def create(self, validated_data):
        """Create relationship with automatic reverse creation"""
        relationship = Relationship.objects.create(
            created_by=self.context['request'].user,
            **validated_data
        )
        
        # Create reverse relationship if bidirectional
        if relationship.relationship_type.is_bidirectional:
            relationship.create_reverse_relationship()
        
        return relationship


class RelationshipSerializer(serializers.ModelSerializer):
    """Serializer for relationship display and updates"""
    
    relationship_type_name = serializers.CharField(source='relationship_type.name', read_only=True)
    source_pipeline_name = serializers.CharField(source='source_pipeline.name', read_only=True)
    target_pipeline_name = serializers.CharField(source='target_pipeline.name', read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    
    # Include record data if available
    source_record_data = serializers.SerializerMethodField()
    target_record_data = serializers.SerializerMethodField()
    
    class Meta:
        model = Relationship
        fields = [
            'id', 'relationship_type', 'relationship_type_name',
            'source_pipeline', 'source_pipeline_name', 'source_record_id', 'source_record_data',
            'target_pipeline', 'target_pipeline_name', 'target_record_id', 'target_record_data',
            'metadata', 'strength', 'status', 'is_verified', 'created_by', 'created_by_email',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_by', 'created_at', 'updated_at', 'source_record_data', 'target_record_data'
        ]
    
    def get_source_record_data(self, obj):
        """Get source record data if accessible"""
        if hasattr(obj, '_source_record_data'):
            return obj._source_record_data
        return None
    
    def get_target_record_data(self, obj):
        """Get target record data if accessible"""
        if hasattr(obj, '_target_record_data'):
            return obj._target_record_data
        return None


class RelationshipTraversalSerializer(serializers.Serializer):
    """Serializer for relationship traversal requests"""
    
    pipeline_id = serializers.IntegerField()
    record_id = serializers.IntegerField()
    relationship_types = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Filter by specific relationship type IDs"
    )
    direction = serializers.ChoiceField(
        choices=['forward', 'reverse', 'both'],
        default='both',
        help_text="Direction of traversal"
    )
    max_depth = serializers.IntegerField(
        default=2,
        min_value=1,
        max_value=5,
        help_text="Maximum traversal depth"
    )
    include_record_data = serializers.BooleanField(
        default=False,
        help_text="Include full record data in response"
    )
    status_filter = serializers.ChoiceField(
        choices=['active', 'inactive', 'pending', 'all'],
        default='active',
        help_text="Filter relationships by status"
    )


class RelationshipPathSerializer(serializers.ModelSerializer):
    """Serializer for relationship paths"""
    
    source_pipeline_name = serializers.CharField(source='source_pipeline.name', read_only=True)
    target_pipeline_name = serializers.CharField(source='target_pipeline.name', read_only=True)
    relationship_names = serializers.SerializerMethodField()
    
    class Meta:
        model = RelationshipPath
        fields = [
            'id', 'source_pipeline', 'source_pipeline_name', 'source_record_id',
            'target_pipeline', 'target_pipeline_name', 'target_record_id',
            'path_length', 'path_relationships', 'path_types', 'relationship_names',
            'path_strength', 'path_weight', 'computed_at', 'expires_at'
        ]
        read_only_fields = ['id', 'computed_at']
    
    def get_relationship_names(self, obj):
        """Get names of relationship types in the path"""
        try:
            relationship_types = RelationshipType.objects.filter(
                id__in=obj.path_types
            ).values_list('name', flat=True)
            return list(relationship_types)
        except:
            return []


class PermissionTraversalSerializer(serializers.ModelSerializer):
    """Serializer for permission traversal configuration"""
    
    user_type_name = serializers.CharField(source='user_type.name', read_only=True)
    relationship_type_name = serializers.CharField(source='relationship_type.name', read_only=True)
    
    class Meta:
        model = PermissionTraversal
        fields = [
            'id', 'user_type', 'user_type_name', 'relationship_type', 'relationship_type_name',
            'can_traverse_forward', 'can_traverse_reverse', 'max_depth',
            'visible_fields', 'restricted_fields', 'traversal_conditions',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RelationshipStatsSerializer(serializers.Serializer):
    """Serializer for relationship statistics"""
    
    total_relationships = serializers.IntegerField()
    active_relationships = serializers.IntegerField()
    relationship_types_count = serializers.IntegerField()
    most_connected_records = serializers.ListField()
    relationship_distribution = serializers.DictField()
    recent_activity = serializers.ListField()


# UserRelationship serializers removed - functionality unified into Relationship serializers above


class AssignmentSerializer(serializers.Serializer):
    """Simplified serializer for basic assignment operations"""
    
    user_id = serializers.IntegerField()
    pipeline_id = serializers.IntegerField()
    record_id = serializers.IntegerField()
    relationship_type = serializers.CharField(default='assigned_to')
    role = serializers.ChoiceField(
        choices=Relationship.ROLE_CHOICES, 
        default='primary'
    )
    
    def validate_relationship_type(self, value):
        """Validate relationship type exists and allows user relationships"""
        try:
            rel_type = RelationshipType.objects.get(
                slug=value, 
                allow_user_relationships=True
            )
            return rel_type
        except RelationshipType.DoesNotExist:
            raise serializers.ValidationError(
                f"Relationship type '{value}' not found or doesn't support user assignments"
            )
    
    def create(self, validated_data):
        """Create assignment using simplified interface"""
        from authentication.models import CustomUser
        
        try:
            user = CustomUser.objects.get(id=validated_data['user_id'])
            pipeline = Pipeline.objects.get(id=validated_data['pipeline_id'])
            
            # Check if record exists
            record = Record.objects.get(
                pipeline=pipeline,
                id=validated_data['record_id'],
                is_deleted=False
            )
            
            # Create or update user relationship using unified Relationship model
            user_rel, created = Relationship.objects.update_or_create(
                relationship_type=validated_data['relationship_type'],
                user=user,
                target_pipeline=pipeline,
                target_record_id=validated_data['record_id'],
                defaults={
                    'role': validated_data['role'],
                    'created_by': self.context['request'].user,
                    'status': 'active',
                    'is_deleted': False
                }
            )
            
            return {
                'id': user_rel.id,
                'user': user.email,
                'record': record.title,
                'relationship': validated_data['relationship_type'].name,
                'role': user_rel.role,
                'created': created
            }
            
        except Exception as e:
            raise serializers.ValidationError(f"Assignment failed: {str(e)}")