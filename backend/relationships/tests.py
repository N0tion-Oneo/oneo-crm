"""
Comprehensive test suite for relationships system
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
import json

from authentication.models import UserType
from pipelines.models import Pipeline, Record
from .models import (
    RelationshipType, 
    Relationship, 
    PermissionTraversal,
    RelationshipPath
)
from .permissions import RelationshipPermissionManager
from .queries import RelationshipQueryManager

User = get_user_model()


class RelationshipTypeModelTest(TestCase):
    """Test RelationshipType model functionality"""
    
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
    
    def test_relationship_type_creation(self):
        """Test basic relationship type creation"""
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
        self.assertFalse(rel_type.is_system)
    
    def test_slug_auto_generation(self):
        """Test automatic slug generation"""
        rel_type = RelationshipType.objects.create(
            name='Test Relationship Type',
            forward_label='test relation',
            created_by=self.user
        )
        
        self.assertEqual(rel_type.slug, 'test-relationship-type')
    
    def test_reverse_label_auto_generation(self):
        """Test automatic reverse label generation"""
        rel_type = RelationshipType.objects.create(
            name='Parent Of',
            forward_label='parent of',
            created_by=self.user
        )
        
        self.assertEqual(rel_type.reverse_label, 'reverse_parent of')
    
    def test_pipeline_constraint_validation(self):
        """Test pipeline constraint validation"""
        rel_type = RelationshipType.objects.create(
            name='Same Pipeline Relation',
            forward_label='related to',
            source_pipeline=self.pipeline1,
            target_pipeline=self.pipeline1,
            allow_self_reference=False,
            created_by=self.user
        )
        
        with self.assertRaises(ValidationError):
            rel_type.clean()
    
    def test_can_create_relationship_method(self):
        """Test can_create_relationship method"""
        rel_type = RelationshipType.objects.create(
            name='Constrained Relation',
            forward_label='related to',
            source_pipeline=self.pipeline1,
            target_pipeline=self.pipeline2,
            created_by=self.user
        )
        
        self.assertTrue(rel_type.can_create_relationship(self.pipeline1, self.pipeline2))
        self.assertFalse(rel_type.can_create_relationship(self.pipeline2, self.pipeline1))
    
    def test_system_types_creation(self):
        """Test creation of system relationship types"""
        initial_count = RelationshipType.objects.filter(is_system=True).count()
        RelationshipType.create_system_types()
        final_count = RelationshipType.objects.filter(is_system=True).count()
        
        self.assertGreater(final_count, initial_count)
        
        # Check specific system types exist
        self.assertTrue(
            RelationshipType.objects.filter(slug='works_at', is_system=True).exists()
        )
        self.assertTrue(
            RelationshipType.objects.filter(slug='related_to', is_system=True).exists()
        )


class RelationshipModelTest(TestCase):
    """Test Relationship model functionality"""
    
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
        
        # Create test records
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
        
        # Create relationship type
        self.rel_type = RelationshipType.objects.create(
            name='Works At',
            forward_label='works at',
            reverse_label='employs',
            cardinality='many_to_one',
            created_by=self.user
        )
    
    def test_relationship_creation(self):
        """Test basic relationship creation"""
        relationship = Relationship.objects.create(
            relationship_type=self.rel_type,
            source_pipeline=self.pipeline1,
            source_record_id=self.record1.id,
            target_pipeline=self.pipeline2,
            target_record_id=self.record2.id,
            created_by=self.user
        )
        
        self.assertEqual(relationship.source_record, self.record1)
        self.assertEqual(relationship.target_record, self.record2)
        self.assertEqual(relationship.status, 'active')
        self.assertFalse(relationship.is_deleted)
    
    def test_relationship_unique_constraint(self):
        """Test unique constraint on relationships"""
        # Create first relationship
        Relationship.objects.create(
            relationship_type=self.rel_type,
            source_pipeline=self.pipeline1,
            source_record_id=self.record1.id,
            target_pipeline=self.pipeline2,
            target_record_id=self.record2.id,
            created_by=self.user
        )
        
        # Try to create duplicate - should raise IntegrityError
        with self.assertRaises(IntegrityError):
            Relationship.objects.create(
                relationship_type=self.rel_type,
                source_pipeline=self.pipeline1,
                source_record_id=self.record1.id,
                target_pipeline=self.pipeline2,
                target_record_id=self.record2.id,
                created_by=self.user
            )
    
    def test_cardinality_validation(self):
        """Test cardinality constraint validation"""
        # Create one-to-one relationship type
        one_to_one_type = RelationshipType.objects.create(
            name='One to One',
            forward_label='linked to',
            cardinality='one_to_one',
            created_by=self.user
        )
        
        # Create first relationship
        rel1 = Relationship(
            relationship_type=one_to_one_type,
            source_pipeline=self.pipeline1,
            source_record_id=self.record1.id,
            target_pipeline=self.pipeline2,
            target_record_id=self.record2.id,
            created_by=self.user
        )
        rel1.save()
        
        # Create another record and try to create another relationship from same source
        record3 = Record.objects.create(
            pipeline=self.pipeline2,
            data={'name': 'Another Corp'},
            created_by=self.user
        )
        
        rel2 = Relationship(
            relationship_type=one_to_one_type,
            source_pipeline=self.pipeline1,
            source_record_id=self.record1.id,
            target_pipeline=self.pipeline2,
            target_record_id=record3.id,
            created_by=self.user
        )
        
        with self.assertRaises(ValidationError):
            rel2.clean()
    
    def test_soft_delete(self):
        """Test soft delete functionality"""
        relationship = Relationship.objects.create(
            relationship_type=self.rel_type,
            source_pipeline=self.pipeline1,
            source_record_id=self.record1.id,
            target_pipeline=self.pipeline2,
            target_record_id=self.record2.id,
            created_by=self.user
        )
        
        # Soft delete
        relationship.delete(soft=True)
        
        self.assertTrue(relationship.is_deleted)
        self.assertIsNotNone(relationship.deleted_at)
        
        # Should still exist in database
        self.assertTrue(
            Relationship.objects.filter(id=relationship.id).exists()
        )
        
        # Should not appear in default queryset
        self.assertFalse(
            Relationship.objects.filter(is_deleted=False, id=relationship.id).exists()
        )
    
    def test_reverse_relationship_creation(self):
        """Test automatic reverse relationship creation"""
        relationship = Relationship.objects.create(
            relationship_type=self.rel_type,
            source_pipeline=self.pipeline1,
            source_record_id=self.record1.id,
            target_pipeline=self.pipeline2,
            target_record_id=self.record2.id,
            created_by=self.user
        )
        
        reverse_rel = relationship.create_reverse_relationship()
        
        self.assertIsNotNone(reverse_rel)
        self.assertEqual(reverse_rel.source_pipeline, self.pipeline2)
        self.assertEqual(reverse_rel.source_record_id, self.record2.id)
        self.assertEqual(reverse_rel.target_pipeline, self.pipeline1)
        self.assertEqual(reverse_rel.target_record_id, self.record1.id)


class RelationshipPermissionTest(TestCase):
    """Test relationship permission system"""
    
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
        self.user.user_type = self.user_type
        self.user.save()
        
        self.rel_type = RelationshipType.objects.create(
            name='Test Relation',
            forward_label='related to',
            created_by=self.user
        )
    
    def test_permission_traversal_creation(self):
        """Test permission traversal configuration"""
        perm_traversal = PermissionTraversal.objects.create(
            user_type=self.user_type,
            relationship_type=self.rel_type,
            can_traverse_forward=True,
            can_traverse_reverse=False,
            max_depth=2,
            visible_fields={'name': True, 'email': True},
            restricted_fields={'salary': True}
        )
        
        self.assertTrue(perm_traversal.can_traverse_forward)
        self.assertFalse(perm_traversal.can_traverse_reverse)
        self.assertEqual(perm_traversal.max_depth, 2)
    
    def test_permission_manager(self):
        """Test relationship permission manager"""
        # Create permission configuration
        PermissionTraversal.objects.create(
            user_type=self.user_type,
            relationship_type=self.rel_type,
            can_traverse_forward=True,
            can_traverse_reverse=False,
            max_depth=3
        )
        
        perm_manager = RelationshipPermissionManager(self.user)
        
        # Test permission checking
        self.assertTrue(
            perm_manager.can_traverse_relationship(self.rel_type, 'forward')
        )
        self.assertFalse(
            perm_manager.can_traverse_relationship(self.rel_type, 'reverse')
        )


class RelationshipQueryTest(TransactionTestCase):
    """Test relationship query and traversal functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create pipelines
        self.person_pipeline = Pipeline.objects.create(
            name='Person',
            description='Person records',
            created_by=self.user
        )
        self.company_pipeline = Pipeline.objects.create(
            name='Company',
            description='Company records',
            created_by=self.user
        )
        
        # Create records
        self.john = Record.objects.create(
            pipeline=self.person_pipeline,
            data={'name': 'John Doe'},
            created_by=self.user
        )
        self.jane = Record.objects.create(
            pipeline=self.person_pipeline,
            data={'name': 'Jane Smith'},
            created_by=self.user
        )
        self.acme = Record.objects.create(
            pipeline=self.company_pipeline,
            data={'name': 'Acme Corp'},
            created_by=self.user
        )
        
        # Create relationship types
        self.works_at = RelationshipType.objects.create(
            name='Works At',
            forward_label='works at',
            reverse_label='employs',
            cardinality='many_to_one',
            created_by=self.user
        )
        
        # Create relationships
        Relationship.objects.create(
            relationship_type=self.works_at,
            source_pipeline=self.person_pipeline,
            source_record_id=self.john.id,
            target_pipeline=self.company_pipeline,
            target_record_id=self.acme.id,
            created_by=self.user
        )
        Relationship.objects.create(
            relationship_type=self.works_at,
            source_pipeline=self.person_pipeline,
            source_record_id=self.jane.id,
            target_pipeline=self.company_pipeline,
            target_record_id=self.acme.id,
            created_by=self.user
        )
    
    def test_basic_relationship_traversal(self):
        """Test basic relationship traversal"""
        query_manager = RelationshipQueryManager()
        
        # Find who works at Acme
        results = query_manager.find_related_records(
            pipeline_id=self.company_pipeline.id,
            record_id=self.acme.id,
            relationship_type_id=self.works_at.id,
            direction='reverse'
        )
        
        self.assertEqual(len(results), 2)
        record_ids = [r['record_id'] for r in results]
        self.assertIn(self.john.id, record_ids)
        self.assertIn(self.jane.id, record_ids)
    
    def test_multi_hop_traversal(self):
        """Test multi-hop relationship traversal"""
        # Create another company and person
        beta_corp = Record.objects.create(
            pipeline=self.company_pipeline,
            data={'name': 'Beta Corp'},
            created_by=self.user
        )
        bob = Record.objects.create(
            pipeline=self.person_pipeline,
            data={'name': 'Bob Johnson'},
            created_by=self.user
        )
        
        # Create colleague relationship type
        colleagues = RelationshipType.objects.create(
            name='Colleagues',
            forward_label='colleague of',
            reverse_label='colleague of',
            cardinality='many_to_many',
            created_by=self.user
        )
        
        # Bob works at Beta Corp
        Relationship.objects.create(
            relationship_type=self.works_at,
            source_pipeline=self.person_pipeline,
            source_record_id=bob.id,
            target_pipeline=self.company_pipeline,
            target_record_id=beta_corp.id,
            created_by=self.user
        )
        
        # John and Bob are colleagues
        Relationship.objects.create(
            relationship_type=colleagues,
            source_pipeline=self.person_pipeline,
            source_record_id=self.john.id,
            target_pipeline=self.person_pipeline,
            target_record_id=bob.id,
            created_by=self.user
        )
        
        query_manager = RelationshipQueryManager()
        
        # Find companies connected to John through 2-hop traversal
        results = query_manager.traverse_relationships(
            pipeline_id=self.person_pipeline.id,
            record_id=self.john.id,
            max_depth=2,
            user=self.user
        )
        
        # Should find both Acme (direct) and Beta Corp (through colleague Bob)
        companies_found = []
        for hop in results.get('paths', []):
            if hop.get('target_pipeline_id') == self.company_pipeline.id:
                companies_found.append(hop['target_record_id'])
        
        self.assertIn(self.acme.id, companies_found)
        self.assertIn(beta_corp.id, companies_found)


class RelationshipAPITest(APITestCase):
    """Test relationship API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
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
            data={'name': 'Test Record 1'},
            created_by=self.user
        )
        self.record2 = Record.objects.create(
            pipeline=self.pipeline2,
            data={'name': 'Test Record 2'},
            created_by=self.user
        )
    
    def test_relationship_type_crud(self):
        """Test relationship type CRUD operations"""
        # Create
        data = {
            'name': 'Test Relation',
            'forward_label': 'related to',
            'reverse_label': 'related from',
            'cardinality': 'many_to_many'
        }
        response = self.client.post('/relationships/api/v1/types/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        rel_type_id = response.data['id']
        
        # Read
        response = self.client.get(f'/relationships/api/v1/types/{rel_type_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Relation')
        
        # Update
        update_data = {'description': 'Updated description'}
        response = self.client.patch(f'/relationships/api/v1/types/{rel_type_id}/', update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['description'], 'Updated description')
        
        # Delete
        response = self.client.delete(f'/relationships/api/v1/types/{rel_type_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    
    def test_relationship_creation(self):
        """Test relationship creation via API"""
        # Create relationship type first
        rel_type = RelationshipType.objects.create(
            name='Test Relation',
            forward_label='related to',
            created_by=self.user
        )
        
        # Create relationship
        data = {
            'relationship_type': rel_type.id,
            'source_pipeline': self.pipeline1.id,
            'source_record': self.record1.id,
            'target_pipeline': self.pipeline2.id,
            'target_record': self.record2.id,
            'metadata': {'test': 'data'},
            'strength': 0.8
        }
        
        response = self.client.post('/relationships/api/v1/relationships/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['strength'], '0.80')
    
    def test_relationship_traversal_api(self):
        """Test relationship traversal API"""
        # Create relationship type and relationship
        rel_type = RelationshipType.objects.create(
            name='Test Relation',
            forward_label='related to',
            created_by=self.user
        )
        
        Relationship.objects.create(
            relationship_type=rel_type,
            source_pipeline=self.pipeline1,
            source_record_id=self.record1.id,
            target_pipeline=self.pipeline2,
            target_record_id=self.record2.id,
            created_by=self.user
        )
        
        # Test traversal
        data = {
            'pipeline_id': self.pipeline1.id,
            'record_id': self.record1.id,
            'direction': 'forward',
            'max_depth': 2,
            'include_record_data': True
        }
        
        response = self.client.post('/relationships/api/v1/relationships/traverse/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('paths', response.data)
    
    def test_relationship_stats_api(self):
        """Test relationship statistics API"""
        response = self.client.get('/relationships/api/v1/relationships/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        expected_fields = [
            'total_relationships',
            'active_relationships', 
            'relationship_types_count',
            'most_connected_records',
            'relationship_distribution',
            'recent_activity'
        ]
        
        for field in expected_fields:
            self.assertIn(field, response.data)


class RelationshipPathTest(TestCase):
    """Test relationship path caching functionality"""
    
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
            data={'name': 'Test Record 1'},
            created_by=self.user
        )
        self.record2 = Record.objects.create(
            pipeline=self.pipeline2,
            data={'name': 'Test Record 2'},
            created_by=self.user
        )
    
    def test_relationship_path_creation(self):
        """Test relationship path model"""
        from django.utils import timezone
        from datetime import timedelta
        
        path = RelationshipPath.objects.create(
            source_pipeline=self.pipeline1,
            source_record_id=self.record1.id,
            target_pipeline=self.pipeline2,
            target_record_id=self.record2.id,
            path_length=1,
            path_relationships=[1],
            path_types=[1],
            path_strength=1.0,
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        self.assertEqual(path.path_length, 1)
        self.assertFalse(path.is_expired())
    
    def test_path_expiration(self):
        """Test path expiration functionality"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Create expired path
        expired_path = RelationshipPath.objects.create(
            source_pipeline=self.pipeline1,
            source_record_id=self.record1.id,
            target_pipeline=self.pipeline2,
            target_record_id=self.record2.id,
            path_length=1,
            path_relationships=[1],
            path_types=[1],
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        self.assertTrue(expired_path.is_expired())
