"""
Basic relationship functionality tests
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from authentication.models import UserType
from pipelines.models import Pipeline, Record
from .models import RelationshipType, Relationship

User = get_user_model()


class BasicRelationshipTest(TestCase):
    """Test basic relationship functionality without complex permissions"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.pipeline1 = Pipeline.objects.create(
            name='Test Pipeline 1',
            description='Test pipeline',
            created_by=self.user
        )
        self.pipeline2 = Pipeline.objects.create(
            name='Test Pipeline 2', 
            description='Test pipeline',
            created_by=self.user
        )
        
        self.record1 = Record.objects.create(
            pipeline=self.pipeline1,
            data={'name': 'John Doe'},
            created_by=self.user
        )
        self.record2 = Record.objects.create(
            pipeline=self.pipeline2,
            data={'name': 'Acme Corp'},
            created_by=self.user
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
        self.assertTrue(rel_type.is_bidirectional)
    
    def test_relationship_creation(self):
        """Test creating a relationship"""
        rel_type = RelationshipType.objects.create(
            name='Works At',
            forward_label='works at',
            reverse_label='employs',
            cardinality='many_to_one',
            created_by=self.user
        )
        
        relationship = Relationship.objects.create(
            relationship_type=rel_type,
            source_pipeline=self.pipeline1,
            source_record_id=self.record1.id,
            target_pipeline=self.pipeline2,
            target_record_id=self.record2.id,
            created_by=self.user
        )
        
        self.assertEqual(relationship.source_record, self.record1)
        self.assertEqual(relationship.target_record, self.record2)
        self.assertEqual(relationship.status, 'active')
    
    def test_system_relationship_types(self):
        """Test creating system relationship types"""
        initial_count = RelationshipType.objects.filter(is_system=True).count()
        RelationshipType.create_system_types()
        final_count = RelationshipType.objects.filter(is_system=True).count()
        
        self.assertGreater(final_count, initial_count)
        
        # Check specific types exist
        works_at = RelationshipType.objects.filter(slug='works_at', is_system=True).first()
        self.assertIsNotNone(works_at)
        self.assertEqual(works_at.name, 'Works At')
        
    def test_relationship_queries(self):
        """Test basic relationship queries"""
        # Create relationship type and relationships
        rel_type = RelationshipType.objects.create(
            name='Works At',
            forward_label='works at',
            reverse_label='employs',
            cardinality='many_to_one',
            created_by=self.user
        )
        
        relationship = Relationship.objects.create(
            relationship_type=rel_type,
            source_pipeline=self.pipeline1,
            source_record_id=self.record1.id,
            target_pipeline=self.pipeline2,
            target_record_id=self.record2.id,
            created_by=self.user
        )
        
        # Test querying relationships
        relationships = Relationship.objects.filter(
            source_pipeline=self.pipeline1,
            source_record_id=self.record1.id
        )
        
        self.assertEqual(relationships.count(), 1)
        self.assertEqual(relationships.first(), relationship)
        
        # Test reverse querying
        reverse_relationships = Relationship.objects.filter(
            target_pipeline=self.pipeline2,
            target_record_id=self.record2.id
        )
        
        self.assertEqual(reverse_relationships.count(), 1)
        self.assertEqual(reverse_relationships.first(), relationship)