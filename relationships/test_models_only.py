"""
Test relationships models in isolation
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from authentication.models import UserType
from .models import RelationshipType, PermissionTraversal

User = get_user_model()


class RelationshipModelOnlyTest(TestCase):
    """Test relationship models without external dependencies"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.user_type = UserType.objects.create(
            name='Test User Type',
            slug='test_user',
            base_permissions={'test': 'permissions'}
        )
    
    def test_relationship_type_creation(self):
        """Test creating a relationship type"""
        rel_type = RelationshipType.objects.create(
            name='Works At',
            forward_label='works at',
            reverse_label='employs',
            cardinality='many_to_one',
            created_by=self.user
        )
        
        self.assertEqual(rel_type.name, 'Works At')
        self.assertEqual(rel_type.slug, 'works-at')
        self.assertEqual(rel_type.forward_label, 'works at')
        self.assertEqual(rel_type.reverse_label, 'employs')
        self.assertEqual(rel_type.cardinality, 'many_to_one')
        self.assertTrue(rel_type.is_bidirectional)
        self.assertFalse(rel_type.is_system)
    
    def test_relationship_type_slug_generation(self):
        """Test automatic slug generation"""
        rel_type = RelationshipType.objects.create(
            name='Test Relationship Type',
            forward_label='test relation',
            created_by=self.user
        )
        
        self.assertEqual(rel_type.slug, 'test-relationship-type')
    
    def test_relationship_type_reverse_label_generation(self):
        """Test automatic reverse label generation"""
        rel_type = RelationshipType.objects.create(
            name='Parent Of',
            forward_label='parent of',
            created_by=self.user
        )
        
        self.assertEqual(rel_type.reverse_label, 'reverse_parent of')
    
    def test_system_relationship_types_creation(self):
        """Test creating system relationship types"""
        initial_count = RelationshipType.objects.filter(is_system=True).count()
        RelationshipType.create_system_types()
        final_count = RelationshipType.objects.filter(is_system=True).count()
        
        self.assertGreater(final_count, initial_count)
        
        # Check specific system types exist
        works_at = RelationshipType.objects.filter(slug='works_at', is_system=True).first()
        self.assertIsNotNone(works_at)
        self.assertEqual(works_at.name, 'Works At')
        self.assertEqual(works_at.forward_label, 'works at')
        self.assertEqual(works_at.reverse_label, 'employs')
        
        related_to = RelationshipType.objects.filter(slug='related_to', is_system=True).first()
        self.assertIsNotNone(related_to)
        self.assertEqual(related_to.name, 'Related To')
    
    def test_permission_traversal_creation(self):
        """Test permission traversal configuration"""
        rel_type = RelationshipType.objects.create(
            name='Test Relation',
            forward_label='related to',
            created_by=self.user
        )
        
        perm_traversal = PermissionTraversal.objects.create(
            user_type=self.user_type,
            relationship_type=rel_type,
            can_traverse_forward=True,
            can_traverse_reverse=False,
            max_depth=2,
            visible_fields={'name': True, 'email': True},
            restricted_fields={'salary': True}
        )
        
        self.assertTrue(perm_traversal.can_traverse_forward)
        self.assertFalse(perm_traversal.can_traverse_reverse)
        self.assertEqual(perm_traversal.max_depth, 2)
        self.assertEqual(perm_traversal.visible_fields, {'name': True, 'email': True})
        self.assertEqual(perm_traversal.restricted_fields, {'salary': True})
    
    def test_relationship_type_str_representation(self):
        """Test string representation of relationship type"""
        rel_type = RelationshipType.objects.create(
            name='Works At',
            forward_label='works at',
            created_by=self.user
        )
        
        self.assertEqual(str(rel_type), 'Works At')
    
    def test_permission_traversal_str_representation(self):
        """Test string representation of permission traversal"""
        rel_type = RelationshipType.objects.create(
            name='Test Relation',
            forward_label='related to',
            created_by=self.user
        )
        
        perm_traversal = PermissionTraversal.objects.create(
            user_type=self.user_type,
            relationship_type=rel_type
        )
        
        expected_str = f"{self.user_type.name} - {rel_type.name}"
        self.assertEqual(str(perm_traversal), expected_str)
    
    def test_relationship_type_cardinality_choices(self):
        """Test all cardinality choices work"""
        cardinalities = ['one_to_one', 'one_to_many', 'many_to_many']
        
        for cardinality in cardinalities:
            rel_type = RelationshipType.objects.create(
                name=f'Test {cardinality}',
                forward_label='test',
                cardinality=cardinality,
                created_by=self.user
            )
            self.assertEqual(rel_type.cardinality, cardinality)
    
    def test_relationship_type_defaults(self):
        """Test default values for relationship type"""
        rel_type = RelationshipType.objects.create(
            name='Test Defaults',
            forward_label='test',
            created_by=self.user
        )
        
        # Test defaults
        self.assertEqual(rel_type.cardinality, 'many_to_many')
        self.assertTrue(rel_type.is_bidirectional)
        self.assertTrue(rel_type.requires_permission)
        self.assertFalse(rel_type.cascade_delete)
        self.assertFalse(rel_type.allow_self_reference)
        self.assertFalse(rel_type.is_system)
        self.assertEqual(rel_type.permission_config, {})
    
    def test_permission_traversal_defaults(self):
        """Test default values for permission traversal"""
        rel_type = RelationshipType.objects.create(
            name='Test Relation',
            forward_label='related to',
            created_by=self.user
        )
        
        perm_traversal = PermissionTraversal.objects.create(
            user_type=self.user_type,
            relationship_type=rel_type
        )
        
        # Test defaults
        self.assertTrue(perm_traversal.can_traverse_forward)
        self.assertTrue(perm_traversal.can_traverse_reverse)
        self.assertEqual(perm_traversal.max_depth, 3)
        self.assertEqual(perm_traversal.visible_fields, {})
        self.assertEqual(perm_traversal.restricted_fields, {})
        self.assertEqual(perm_traversal.traversal_conditions, {})