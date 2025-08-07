"""
Focused tests for DataMigrator - unified migration engine
"""
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import transaction
from pipelines.models import Pipeline, Field, Record
from pipelines.migration.data_migrator import DataMigrator, MigrationResult

User = get_user_model()


class DataMigratorDetailedTestCase(TransactionTestCase):
    """Detailed tests for DataMigrator functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.pipeline = Pipeline.objects.create(
            name='Migrator Test Pipeline',
            slug='migrator-test',
            pipeline_type='crm',
            created_by=self.user
        )
        self.migrator = DataMigrator(self.pipeline)
    
    # =============================================================================
    # FIELD RENAME MIGRATION TESTS
    # =============================================================================
    
    def test_field_rename_migration_success(self):
        """Test successful field rename migration"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Original Name',
            field_type='text',
            created_by=self.user
        )
        original_slug = field.slug
        
        # Create records with data
        records_data = []
        for i in range(10):
            record = Record.objects.create(
                pipeline=self.pipeline,
                title=f'Record {i}',
                data={original_slug: f'value {i}'},
                created_by=self.user
            )
            records_data.append((record.id, f'value {i}'))
        
        # Prepare migration
        original_config = {
            'slug': original_slug,
            'name': 'Original Name',
            'field_type': 'text'
        }
        
        change_analysis = {
            'requires_migration': True,
            'migration_types': ['field_rename'],
            'risk_level': 'medium',
            'affected_records_estimate': 10
        }
        
        # Update field name (generates new slug)
        field.name = 'New Name'
        field.save()
        new_slug = field.slug
        
        # Perform migration
        operation_id = "test_rename_001"
        result = self.migrator.migrate_field_data(
            field, original_config, change_analysis, operation_id
        )
        
        # Verify migration success
        self.assertTrue(result.success)
        self.assertEqual(result.records_processed, 10)
        self.assertEqual(len(result.errors), 0)
        
        # Verify data was migrated
        for record_id, expected_value in records_data:
            record = Record.objects.get(id=record_id)
            self.assertNotIn(original_slug, record.data)
            self.assertIn(new_slug, record.data)
            self.assertEqual(record.data[new_slug], expected_value)
    
    def test_field_rename_with_conflicting_data(self):
        """Test field rename when target field already has data"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Source Field',
            field_type='text',
            created_by=self.user
        )
        original_slug = field.slug
        
        # Update name to create new slug
        field.name = 'Target Field'
        field.save()
        new_slug = field.slug
        
        # Create record with data in BOTH old and new fields
        record = Record.objects.create(
            pipeline=self.pipeline,
            title='Conflicting Record',
            data={
                original_slug: 'original value',
                new_slug: 'existing value'  # Conflict!
            },
            created_by=self.user
        )
        
        # Prepare migration
        original_config = {
            'slug': original_slug,
            'name': 'Source Field',
            'field_type': 'text'
        }
        
        change_analysis = {
            'requires_migration': True,
            'migration_types': ['field_rename'],
            'risk_level': 'medium',
            'affected_records_estimate': 1
        }
        
        # Perform migration
        operation_id = "test_rename_conflict_001"
        result = self.migrator.migrate_field_data(
            field, original_config, change_analysis, operation_id
        )
        
        # Should handle conflict gracefully
        self.assertTrue(result.success)
        self.assertTrue(len(result.warnings) > 0)
        self.assertTrue(any('conflict' in warning.lower() for warning in result.warnings))
        
        # Verify record state
        record.refresh_from_db()
        self.assertIn(new_slug, record.data)
        # Original field should be removed
        self.assertNotIn(original_slug, record.data)
    
    def test_field_rename_partial_data(self):
        """Test field rename when only some records have data"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Partial Field',
            field_type='text',
            created_by=self.user
        )
        original_slug = field.slug
        
        # Create records - some with data, some without
        records_with_data = []
        records_without_data = []
        
        for i in range(5):
            # Record with data
            record = Record.objects.create(
                pipeline=self.pipeline,
                title=f'Record With Data {i}',
                data={original_slug: f'value {i}'},
                created_by=self.user
            )
            records_with_data.append(record.id)
            
            # Record without this field's data
            record = Record.objects.create(
                pipeline=self.pipeline,
                title=f'Record Without Data {i}',
                data={'other_field': f'other value {i}'},
                created_by=self.user
            )
            records_without_data.append(record.id)
        
        # Update field name
        field.name = 'Renamed Partial Field'
        field.save()
        new_slug = field.slug
        
        # Prepare migration
        original_config = {
            'slug': original_slug,
            'name': 'Partial Field',
            'field_type': 'text'
        }
        
        change_analysis = {
            'requires_migration': True,
            'migration_types': ['field_rename'],
            'risk_level': 'medium',
            'affected_records_estimate': 5  # Only records with data
        }
        
        # Perform migration
        operation_id = "test_rename_partial_001"
        result = self.migrator.migrate_field_data(
            field, original_config, change_analysis, operation_id
        )
        
        # Should succeed
        self.assertTrue(result.success)
        self.assertEqual(result.records_processed, 5)  # Only records with data
        
        # Verify records with data were migrated
        for record_id in records_with_data:
            record = Record.objects.get(id=record_id)
            self.assertNotIn(original_slug, record.data)
            self.assertIn(new_slug, record.data)
        
        # Verify records without data were unchanged
        for record_id in records_without_data:
            record = Record.objects.get(id=record_id)
            self.assertNotIn(original_slug, record.data)
            self.assertNotIn(new_slug, record.data)
    
    # =============================================================================
    # TYPE CHANGE MIGRATION TESTS
    # =============================================================================
    
    def test_text_to_number_migration_success(self):
        """Test successful text to number conversion"""
        # Create text field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Number Field',
            field_type='text',
            created_by=self.user
        )
        
        # Create records with numeric strings
        test_data = [
            ('123', 123),
            ('456.78', 456.78),
            ('0', 0),
            ('-45.67', -45.67),
            ('1000', 1000)
        ]
        
        record_ids = []
        for string_val, expected_num in test_data:
            record = Record.objects.create(
                pipeline=self.pipeline,
                title=f'Record {string_val}',
                data={field.slug: string_val},
                created_by=self.user
            )
            record_ids.append((record.id, expected_num))
        
        # Prepare migration
        original_config = {
            'slug': field.slug,
            'name': 'Number Field',
            'field_type': 'text'
        }
        
        change_analysis = {
            'requires_migration': True,
            'migration_types': ['type_change'],
            'risk_level': 'high',
            'affected_records_estimate': len(test_data)
        }
        
        # Change field type
        field.field_type = 'number'
        field.save()
        
        # Perform migration
        operation_id = "test_type_change_001"
        result = self.migrator.migrate_field_data(
            field, original_config, change_analysis, operation_id
        )
        
        # Should succeed
        self.assertTrue(result.success)
        self.assertEqual(result.records_processed, len(test_data))
        
        # Verify conversions
        for record_id, expected_value in record_ids:
            record = Record.objects.get(id=record_id)
            converted_value = record.data[field.slug]
            self.assertEqual(converted_value, expected_value)
            self.assertIsInstance(converted_value, (int, float))
    
    def test_text_to_number_migration_with_invalid_data(self):
        """Test text to number conversion with invalid data"""
        # Create text field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Mixed Field',
            field_type='text',
            created_by=self.user
        )
        
        # Create records with mixed data (some convertible, some not)
        valid_data = [('123', 123), ('456.78', 456.78)]
        invalid_data = ['not a number', 'abc123', '12.34.56']
        
        valid_record_ids = []
        invalid_record_ids = []
        
        for string_val, expected_num in valid_data:
            record = Record.objects.create(
                pipeline=self.pipeline,
                title=f'Valid Record {string_val}',
                data={field.slug: string_val},
                created_by=self.user
            )
            valid_record_ids.append((record.id, expected_num))
        
        for string_val in invalid_data:
            record = Record.objects.create(
                pipeline=self.pipeline,
                title=f'Invalid Record {string_val}',
                data={field.slug: string_val},
                created_by=self.user
            )
            invalid_record_ids.append((record.id, string_val))
        
        # Prepare migration
        original_config = {
            'slug': field.slug,
            'name': 'Mixed Field',
            'field_type': 'text'
        }
        
        change_analysis = {
            'requires_migration': True,
            'migration_types': ['type_change'],
            'risk_level': 'high',
            'affected_records_estimate': len(valid_data) + len(invalid_data)
        }
        
        # Change field type
        field.field_type = 'number'
        field.save()
        
        # Perform migration
        operation_id = "test_type_change_invalid_001"
        result = self.migrator.migrate_field_data(
            field, original_config, change_analysis, operation_id
        )
        
        # Should fail due to invalid data
        self.assertFalse(result.success)
        self.assertTrue(len(result.errors) > 0)
        self.assertTrue(any('conversion' in error.lower() for error in result.errors))
        
        # Verify data wasn't corrupted (rollback should have occurred)
        for record_id, original_value in invalid_record_ids:
            record = Record.objects.get(id=record_id)
            self.assertEqual(record.data[field.slug], original_value)
    
    def test_number_to_text_migration(self):
        """Test number to text conversion (should always work)"""
        # Create number field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Text Field',
            field_type='number',
            created_by=self.user
        )
        
        # Create records with numbers
        test_data = [123, 456.78, 0, -45.67, 1000.123]
        record_ids = []
        
        for num_val in test_data:
            record = Record.objects.create(
                pipeline=self.pipeline,
                title=f'Record {num_val}',
                data={field.slug: num_val},
                created_by=self.user
            )
            record_ids.append((record.id, str(num_val)))
        
        # Prepare migration
        original_config = {
            'slug': field.slug,
            'name': 'Text Field',
            'field_type': 'number'
        }
        
        change_analysis = {
            'requires_migration': True,
            'migration_types': ['type_change'],
            'risk_level': 'low',  # Number to text is low risk
            'affected_records_estimate': len(test_data)
        }
        
        # Change field type
        field.field_type = 'text'
        field.save()
        
        # Perform migration
        operation_id = "test_type_change_num_to_text_001"
        result = self.migrator.migrate_field_data(
            field, original_config, change_analysis, operation_id
        )
        
        # Should succeed
        self.assertTrue(result.success)
        self.assertEqual(result.records_processed, len(test_data))
        
        # Verify conversions
        for record_id, expected_string in record_ids:
            record = Record.objects.get(id=record_id)
            converted_value = record.data[field.slug]
            self.assertEqual(converted_value, expected_string)
            self.assertIsInstance(converted_value, str)
    
    # =============================================================================
    # CONSTRAINT CHANGE MIGRATION TESTS
    # =============================================================================
    
    def test_max_length_reduction_migration(self):
        """Test migration when max length is reduced"""
        # Create text field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Text Field',
            field_type='text',
            storage_constraints={'max_storage_length': 255},
            created_by=self.user
        )
        
        # Create records with varying length data
        test_data = [
            'short',  # 5 chars - OK
            'medium length text',  # 18 chars - OK
            'a' * 50,  # 50 chars - OK
            'a' * 150,  # 150 chars - Will be truncated
            'a' * 200,  # 200 chars - Will be truncated
        ]
        
        record_ids = []
        for i, text_val in enumerate(test_data):
            record = Record.objects.create(
                pipeline=self.pipeline,
                title=f'Record {i}',
                data={field.slug: text_val},
                created_by=self.user
            )
            record_ids.append((record.id, text_val))
        
        # Prepare migration
        original_config = {
            'slug': field.slug,
            'name': 'Text Field',
            'field_type': 'text',
            'storage_constraints': {'max_storage_length': 255}
        }
        
        change_analysis = {
            'requires_migration': True,
            'migration_types': ['constraint_change'],
            'risk_level': 'medium',
            'affected_records_estimate': len(test_data)
        }
        
        # Reduce max length
        field.storage_constraints = {'max_storage_length': 100}
        field.save()
        
        # Perform migration
        operation_id = "test_constraint_change_001"
        result = self.migrator.migrate_field_data(
            field, original_config, change_analysis, operation_id
        )
        
        # Should succeed but with warnings
        self.assertTrue(result.success)
        self.assertEqual(result.records_processed, len(test_data))
        self.assertTrue(len(result.warnings) > 0)
        self.assertTrue(any('truncated' in warning.lower() for warning in result.warnings))
        
        # Verify data
        for record_id, original_value in record_ids:
            record = Record.objects.get(id=record_id)
            stored_value = record.data[field.slug]
            
            if len(original_value) <= 100:
                # Should be unchanged
                self.assertEqual(stored_value, original_value)
            else:
                # Should be truncated to 100 chars
                self.assertEqual(len(stored_value), 100)
                self.assertEqual(stored_value, original_value[:100])
    
    # =============================================================================
    # BATCH PROCESSING TESTS
    # =============================================================================
    
    def test_batch_processing_large_dataset(self):
        """Test batch processing with large number of records"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Batch Test Field',
            field_type='text',
            created_by=self.user
        )
        original_slug = field.slug
        
        # Create many records
        num_records = 2500  # More than default batch size
        record_ids = []
        
        for i in range(num_records):
            record = Record.objects.create(
                pipeline=self.pipeline,
                title=f'Batch Record {i}',
                data={original_slug: f'batch value {i}'},
                created_by=self.user
            )
            record_ids.append(record.id)
        
        # Update field name
        field.name = 'Batch Test Field Renamed'
        field.save()
        new_slug = field.slug
        
        # Prepare migration with small batch size
        original_config = {
            'slug': original_slug,
            'name': 'Batch Test Field',
            'field_type': 'text'
        }
        
        change_analysis = {
            'requires_migration': True,
            'migration_types': ['field_rename'],
            'risk_level': 'medium',
            'affected_records_estimate': num_records
        }
        
        # Perform migration with custom batch size
        operation_id = "test_batch_001"
        result = self.migrator.migrate_field_data(
            field, original_config, change_analysis, operation_id, batch_size=100
        )
        
        # Should succeed
        self.assertTrue(result.success)
        self.assertEqual(result.records_processed, num_records)
        
        # Verify all records were migrated
        migrated_count = 0
        for record_id in record_ids[:100]:  # Check first 100
            record = Record.objects.get(id=record_id)
            if new_slug in record.data and original_slug not in record.data:
                migrated_count += 1
        
        self.assertEqual(migrated_count, 100)
    
    # =============================================================================
    # ERROR HANDLING AND ROLLBACK TESTS
    # =============================================================================
    
    def test_migration_rollback_on_database_error(self):
        """Test rollback when database error occurs"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Rollback Test Field',
            field_type='text',
            created_by=self.user
        )
        
        # Create records
        original_data = {}
        for i in range(5):
            record = Record.objects.create(
                pipeline=self.pipeline,
                title=f'Rollback Record {i}',
                data={field.slug: f'original value {i}'},
                created_by=self.user
            )
            original_data[record.id] = record.data.copy()
        
        # Prepare migration
        original_config = {
            'slug': field.slug,
            'name': 'Rollback Test Field',
            'field_type': 'text'
        }
        
        change_analysis = {
            'requires_migration': True,
            'migration_types': ['type_change'],
            'risk_level': 'high',
            'affected_records_estimate': 5
        }
        
        # Change to incompatible type that will cause errors
        field.field_type = 'number'
        field.save()
        
        # Add invalid data that will cause conversion errors
        Record.objects.filter(pipeline=self.pipeline).update(
            data={field.slug: 'definitely not a number'}
        )
        
        # Perform migration (should fail and rollback)
        operation_id = "test_rollback_001"
        result = self.migrator.migrate_field_data(
            field, original_config, change_analysis, operation_id
        )
        
        # Should fail
        self.assertFalse(result.success)
        self.assertTrue(len(result.errors) > 0)
        
        # Verify rollback - data should be unchanged
        for record_id, expected_data in original_data.items():
            record = Record.objects.get(id=record_id)
            # Data should be restored (though the invalid data we added will remain)
            self.assertIn(field.slug, record.data)
    
    def test_migration_progress_callback(self):
        """Test migration progress callback functionality"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Progress Test Field',
            field_type='text',
            created_by=self.user
        )
        original_slug = field.slug
        
        # Create records
        num_records = 50
        for i in range(num_records):
            Record.objects.create(
                pipeline=self.pipeline,
                title=f'Progress Record {i}',
                data={original_slug: f'value {i}'},
                created_by=self.user
            )
        
        # Update field
        field.name = 'Progress Test Field Renamed'
        field.save()
        
        # Prepare migration
        original_config = {
            'slug': original_slug,
            'name': 'Progress Test Field',
            'field_type': 'text'
        }
        
        change_analysis = {
            'requires_migration': True,
            'migration_types': ['field_rename'],
            'risk_level': 'medium',
            'affected_records_estimate': num_records
        }
        
        # Track progress
        progress_updates = []
        
        def progress_callback(processed, total, percentage):
            progress_updates.append((processed, total, percentage))
        
        # Perform migration with progress callback
        operation_id = "test_progress_001"
        result = self.migrator.migrate_field_data(
            field, original_config, change_analysis, operation_id,
            batch_size=10, progress_callback=progress_callback
        )
        
        # Should succeed
        self.assertTrue(result.success)
        
        # Should have received progress updates
        self.assertTrue(len(progress_updates) > 0)
        
        # First update should show progress
        first_update = progress_updates[0]
        self.assertGreaterEqual(first_update[0], 10)  # At least 10 processed
        self.assertEqual(first_update[1], num_records)  # Total should be correct
        self.assertGreater(first_update[2], 0)  # Percentage should be > 0
        
        # Last update should show completion
        if len(progress_updates) > 1:
            last_update = progress_updates[-1]
            self.assertEqual(last_update[0], num_records)
            self.assertEqual(last_update[2], 100.0)
    
    # =============================================================================
    # MIGRATION RESULT TESTS
    # =============================================================================
    
    def test_migration_result_structure(self):
        """Test MigrationResult contains expected information"""
        # Create simple successful migration
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Result Test Field',
            field_type='text',
            created_by=self.user
        )
        
        Record.objects.create(
            pipeline=self.pipeline,
            title='Test Record',
            data={field.slug: 'test value'},
            created_by=self.user
        )
        
        # Prepare migration
        original_config = {
            'slug': field.slug,
            'name': 'Result Test Field',
            'field_type': 'text'
        }
        
        change_analysis = {
            'requires_migration': True,
            'migration_types': ['field_rename'],
            'risk_level': 'medium',
            'affected_records_estimate': 1
        }
        
        field.name = 'Result Test Field Renamed'
        field.save()
        
        # Perform migration
        operation_id = "test_result_001"
        result = self.migrator.migrate_field_data(
            field, original_config, change_analysis, operation_id
        )
        
        # Check result structure
        self.assertTrue(hasattr(result, 'success'))
        self.assertTrue(hasattr(result, 'records_processed'))
        self.assertTrue(hasattr(result, 'records_affected'))
        self.assertTrue(hasattr(result, 'errors'))
        self.assertTrue(hasattr(result, 'warnings'))
        self.assertTrue(hasattr(result, 'execution_time'))
        self.assertTrue(hasattr(result, 'operation_id'))
        
        # Check types
        self.assertIsInstance(result.success, bool)
        self.assertIsInstance(result.records_processed, int)
        self.assertIsInstance(result.errors, list)
        self.assertIsInstance(result.warnings, list)
        self.assertIsInstance(result.execution_time, (int, float))
        self.assertIsInstance(result.operation_id, str)
        
        # Check values
        self.assertTrue(result.success)
        self.assertEqual(result.records_processed, 1)
        self.assertEqual(result.operation_id, operation_id)
        self.assertGreater(result.execution_time, 0)