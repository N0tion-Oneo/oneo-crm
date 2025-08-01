"""
Performance tests for relationship engine
"""
import time
import json
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import override_settings
from authentication.models import UserType
from pipelines.models import Pipeline, Record
from .models import RelationshipType, Relationship
from .queries import RelationshipQueryManager

User = get_user_model()


class RelationshipPerformanceTest(TransactionTestCase):
    """Test relationship performance with large datasets"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='perftest',
            email='perf@test.com',
            password='testpass123'
        )
        
        # Create test pipelines
        self.pipeline1 = Pipeline.objects.create(
            name='People Pipeline',
            description='Test pipeline for people',
            created_by=self.user
        )
        self.pipeline2 = Pipeline.objects.create(
            name='Company Pipeline', 
            description='Test pipeline for companies',
            created_by=self.user
        )
        
        # Create relationship types
        RelationshipType.create_system_types()
        self.works_at = RelationshipType.objects.get(slug='works_at')
        self.related_to = RelationshipType.objects.get(slug='related_to')
        
        # Create test records
        self.people = []
        self.companies = []
        
        # Create 100 people records
        for i in range(100):
            person = Record.objects.create(
                pipeline=self.pipeline1,
                data={'name': f'Person {i}', 'email': f'person{i}@test.com'},
                created_by=self.user,
                updated_by=self.user
            )
            self.people.append(person)
        
        # Create 20 company records  
        for i in range(20):
            company = Record.objects.create(
                pipeline=self.pipeline2,
                data={'name': f'Company {i}', 'industry': 'Tech'},
                created_by=self.user,
                updated_by=self.user
            )
            self.companies.append(company)
    
    def test_relationship_creation_performance(self):
        """Test performance of creating many relationships"""
        start_time = time.time()
        
        # Create 500 relationships (people working at companies)
        relationships = []
        for i, person in enumerate(self.people[:50]):  # 50 people
            for j, company in enumerate(self.companies[:10]):  # 10 companies each
                relationships.append(Relationship(
                    relationship_type=self.works_at,
                    source_pipeline=self.pipeline1,
                    source_record_id=person.id,
                    target_pipeline=self.pipeline2,
                    target_record_id=company.id,
                    created_by=self.user
                ))
        
        # Bulk create for performance
        Relationship.objects.bulk_create(relationships)
        
        creation_time = time.time() - start_time
        print(f"Created {len(relationships)} relationships in {creation_time:.3f}s")
        
        # Should create 500 relationships in under 2 seconds
        self.assertLess(creation_time, 2.0)
    
    def test_traversal_query_performance(self):
        """Test performance of multi-hop traversal queries"""
        # First create some relationships
        self.test_relationship_creation_performance()
        
        # Create some person-to-person relationships for multi-hop
        for i in range(0, 30, 3):  # Every 3rd person
            for j in range(i+1, min(i+3, 30)):
                Relationship.objects.create(
                    relationship_type=self.related_to,
                    source_pipeline=self.pipeline1,
                    source_record_id=self.people[i].id,
                    target_pipeline=self.pipeline1,
                    target_record_id=self.people[j].id,
                    created_by=self.user
                )
        
        # Test traversal performance
        query_manager = RelationshipQueryManager(self.user)
        
        start_time = time.time()
        
        # Perform 10 traversal queries
        for i in range(10):
            results = query_manager.get_related_records(
                source_pipeline_id=self.pipeline1.id,
                source_record_id=self.people[i].id,
                max_depth=3,
                direction='both'
            )
            
            # Verify we get results
            self.assertIsInstance(results, dict)
            self.assertIn('relationships', results)
        
        query_time = time.time() - start_time
        avg_query_time = query_time / 10
        
        print(f"10 traversal queries completed in {query_time:.3f}s (avg: {avg_query_time:.3f}s per query)")
        
        # Each query should complete in under 100ms on average
        self.assertLess(avg_query_time, 0.1)
    
    def test_shortest_path_performance(self):
        """Test performance of shortest path finding"""
        # Create relationships first
        self.test_relationship_creation_performance()
        
        query_manager = RelationshipQueryManager(self.user)
        
        start_time = time.time()
        
        # Test 5 shortest path queries
        for i in range(5):
            source_person = self.people[i]
            target_company = self.companies[i % len(self.companies)]
            
            path = query_manager.find_shortest_path(
                source_pipeline_id=source_person.pipeline_id,
                source_record_id=source_person.id,
                target_pipeline_id=target_company.pipeline_id,
                target_record_id=target_company.id,
                max_depth=3
            )
            
            # Should find a path since we created direct relationships
            self.assertIsInstance(path, dict)
        
        path_time = time.time() - start_time
        avg_path_time = path_time / 5
        
        print(f"5 shortest path queries completed in {path_time:.3f}s (avg: {avg_path_time:.3f}s per query)")
        
        # Each path query should complete in under 50ms on average
        self.assertLess(avg_path_time, 0.05)
    
    def test_assignment_query_performance(self):
        """Test performance of user assignment queries"""
        # Create user assignments
        assignment_rel_type = RelationshipType.objects.get(slug='assigned_to')
        
        start_time = time.time()
        
        # Assign user to 50 records
        assignments = []
        for i, person in enumerate(self.people[:50]):
            assignments.append(Relationship(
                relationship_type=assignment_rel_type,
                user=self.user,
                target_pipeline=self.pipeline1,
                target_record_id=person.id,
                role='primary',
                created_by=self.user
            ))
        
        Relationship.objects.bulk_create(assignments)
        
        assignment_time = time.time() - start_time
        print(f"Created {len(assignments)} user assignments in {assignment_time:.3f}s")
        
        # Test querying assignments
        start_time = time.time()
        
        # Query user assignments 10 times
        for i in range(10):
            user_assignments = Relationship.get_user_assignments(
                user=self.user,
                relationship_type='assigned_to'
            )
            
            # Verify we get the assignments
            self.assertEqual(user_assignments.count(), 50)
        
        query_time = time.time() - start_time
        avg_query_time = query_time / 10
        
        print(f"10 assignment queries completed in {query_time:.3f}s (avg: {avg_query_time:.3f}s per query)")
        
        # Each assignment query should complete very quickly
        self.assertLess(avg_query_time, 0.01)
    
    def test_database_indexes_effectiveness(self):
        """Test that database indexes are being used effectively"""
        # Create some relationships
        self.test_relationship_creation_performance()
        
        # Test specific index usage with EXPLAIN
        with connection.cursor() as cursor:
            # Test source record index
            cursor.execute("""
                EXPLAIN (ANALYZE, BUFFERS) 
                SELECT * FROM relationships_relationship 
                WHERE source_pipeline_id = %s AND source_record_id = %s 
                AND is_deleted = FALSE
            """, [self.pipeline1.id, self.people[0].id])
            
            explain_result = cursor.fetchall()
            explain_text = '\n'.join([str(row) for row in explain_result])
            
            print(f"Source record query plan:\n{explain_text}")
            
            # Should use index scan, not sequential scan
            self.assertIn('Index', explain_text)
            self.assertNotIn('Seq Scan on relationships_relationship', explain_text)
    
    def test_memory_usage_large_dataset(self):
        """Test memory usage with large relationship datasets"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create a large number of relationships
        relationships = []
        for i in range(1000):  # 1000 relationships
            person_idx = i % len(self.people)
            company_idx = i % len(self.companies)
            
            relationships.append(Relationship(
                relationship_type=self.works_at,
                source_pipeline=self.pipeline1,
                source_record_id=self.people[person_idx].id,
                target_pipeline=self.pipeline2,
                target_record_id=self.companies[company_idx].id,
                created_by=self.user
            ))
        
        Relationship.objects.bulk_create(relationships)
        
        # Query all relationships
        query_manager = RelationshipQueryManager(self.user)
        
        for i in range(20):  # 20 queries
            results = query_manager.get_related_records(
                source_pipeline_id=self.pipeline1.id,
                source_record_id=self.people[i].id,
                max_depth=2,
                direction='both'
            )
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Memory usage: {initial_memory:.1f}MB -> {final_memory:.1f}MB (increase: {memory_increase:.1f}MB)")
        
        # Memory increase should be reasonable (under 100MB for this test)
        self.assertLess(memory_increase, 100)


class RelationshipConcurrencyTest(TransactionTestCase):
    """Test relationship operations under concurrent access"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='concurrency',
            email='concurrent@test.com', 
            password='testpass123'
        )
        
        self.pipeline = Pipeline.objects.create(
            name='Test Pipeline',
            description='Test',
            created_by=self.user
        )
        
        RelationshipType.create_system_types()
        self.rel_type = RelationshipType.objects.get(slug='related_to')
        
        # Create test records
        self.records = []
        for i in range(10):
            record = Record.objects.create(
                pipeline=self.pipeline,
                data={'name': f'Record {i}'},
                created_by=self.user,
                updated_by=self.user
            )
            self.records.append(record)
    
    def test_concurrent_relationship_creation(self):
        """Test creating relationships concurrently"""
        import threading
        
        created_relationships = []
        errors = []
        
        def create_relationships(start_idx, end_idx):
            """Create relationships in a thread"""
            try:
                for i in range(start_idx, end_idx):
                    source_record = self.records[i % len(self.records)]
                    target_record = self.records[(i + 1) % len(self.records)]
                    
                    relationship = Relationship.objects.create(
                        relationship_type=self.rel_type,
                        source_pipeline=self.pipeline,
                        source_record_id=source_record.id,
                        target_pipeline=self.pipeline,
                        target_record_id=target_record.id,
                        created_by=self.user
                    )
                    created_relationships.append(relationship)
            except Exception as e:
                errors.append(str(e))
        
        # Create 5 threads, each creating 10 relationships
        threads = []
        for i in range(5):
            thread = threading.Thread(
                target=create_relationships,
                args=(i * 10, (i + 1) * 10)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        print(f"Created {len(created_relationships)} relationships concurrently")
        print(f"Errors: {len(errors)}")
        
        # Should create most relationships successfully
        self.assertGreaterEqual(len(created_relationships), 40)  # Allow some duplicate errors
        
        # Verify no data corruption
        total_relationships = Relationship.objects.filter(
            relationship_type=self.rel_type,
            is_deleted=False
        ).count()
        
        self.assertGreaterEqual(total_relationships, 40)


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    # This would be configured in a real test environment
    print("Performance tests created. Run with: python manage.py test relationships.test_performance")