"""
Comprehensive tests for the unified field management architecture

Tests the complete integration of:
- FieldOperationManager (single entry point)
- FieldValidator (consolidated validation)
- DataMigrator (unified migration engine)
- FieldStateManager (thread-safe state management)
- API integration
- Signal integration
"""
import json
import uuid
from unittest.mock import patch, MagicMock
from datetime import timedelta
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from rest_framework.test import APITestCase
from rest_framework import status

from pipelines.models import Pipeline, Field, Record
from pipelines.field_operations import (
    FieldOperationManager, FieldOperationResult, get_field_operation_manager
)
from pipelines.validation.field_validator import FieldValidator, FieldValidationResult
from pipelines.migration.data_migrator import DataMigrator
from pipelines.state.field_state_manager import (
    FieldStateManager, get_field_state_manager
)

User = get_user_model()


class FieldStateManagerTestCase(TestCase):
    """Test FieldStateManager functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.pipeline = Pipeline.objects.create(
            name='Test Pipeline',
            slug='test-pipeline',
            pipeline_type='crm',
            created_by=self.user
        )
        self.field = Field.objects.create(
            pipeline=self.pipeline,
            name='Test Field',
            field_type='text',
            created_by=self.user
        )
        self.state_manager = get_field_state_manager()
    
    def test_capture_field_state(self):
        """Test capturing field state before operations"""
        operation_id = "test_op_001"
        
        # Capture state
        success = self.state_manager.capture_field_state(self.field.id, operation_id)
        self.assertTrue(success)
        
        # Retrieve state
        state = self.state_manager.get_field_state(self.field.id, operation_id)
        self.assertIsNotNone(state)
        self.assertFalse(state['was_deleted'])
        self.assertTrue(state['was_active'])
        self.assertEqual(state['original_config']['name'], 'Test Field')
        self.assertEqual(state['original_config']['field_type'], 'text')
    
    def test_field_change_detection(self):
        """Test detecting field changes that require migration"""
        operation_id = "test_op_002"
        
        # Capture initial state
        self.state_manager.capture_field_state(self.field.id, operation_id)
        
        # Modify field
        self.field.field_type = 'number'
        self.field.name = 'Modified Field'
        
        # Analyze changes
        changes = self.state_manager.get_field_changes(self.field.id, self.field, operation_id)
        
        self.assertIsNotNone(changes)
        self.assertTrue(changes['requires_migration'])
        self.assertIn('type_change', changes['migration_types'])
        self.assertEqual(changes['risk_level'], 'high')
        self.assertTrue(len(changes['change_details']) > 0)
    
    def test_state_cleanup(self):
        """Test cleanup of operation states"""
        operation_id = "test_op_003"
        
        # Capture state
        self.state_manager.capture_field_state(self.field.id, operation_id)
        
        # Verify state exists
        state = self.state_manager.get_field_state(self.field.id, operation_id)
        self.assertIsNotNone(state)
        
        # Cleanup
        self.state_manager.cleanup_operation_state(operation_id)
        
        # Verify state is gone
        state = self.state_manager.get_field_state(self.field.id, operation_id)
        self.assertIsNone(state)
    
    def test_memory_usage_tracking(self):
        """Test memory usage monitoring"""
        operation_id = "test_op_004"
        
        # Initial memory info
        initial_info = self.state_manager.get_memory_usage_info()
        initial_count = initial_info['active_operations']
        
        # Capture state
        self.state_manager.capture_field_state(self.field.id, operation_id)
        
        # Check memory info updated
        updated_info = self.state_manager.get_memory_usage_info()
        self.assertEqual(updated_info['active_operations'], initial_count + 1)
        
        # Cleanup
        self.state_manager.cleanup_operation_state(operation_id)
        
        # Check memory info back to initial
        final_info = self.state_manager.get_memory_usage_info()
        self.assertEqual(final_info['active_operations'], initial_count)


class FieldValidatorTestCase(TestCase):
    """Test FieldValidator functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.pipeline = Pipeline.objects.create(
            name='Test Pipeline',
            slug='test-pipeline',
            pipeline_type='crm',
            created_by=self.user
        )
        self.validator = FieldValidator()
    
    def test_field_creation_validation_success(self):
        """Test successful field creation validation"""
        field_config = {
            'name': 'Valid Field',
            'field_type': 'text',
            'field_config': {'max_length': 255},
            'is_required': False
        }
        
        result = self.validator.validate_field_creation(field_config, self.pipeline)
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_field_creation_validation_failure(self):
        """Test field creation validation with errors"""
        # Missing required name
        field_config = {
            'field_type': 'text'
        }
        
        result = self.validator.validate_field_creation(field_config, self.pipeline)
        self.assertFalse(result.valid)
        self.assertTrue(len(result.errors) > 0)
    
    def test_duplicate_field_name_validation(self):
        """Test validation prevents duplicate field names"""
        # Create existing field
        Field.objects.create(
            pipeline=self.pipeline,
            name='Existing Field',
            field_type='text',
            created_by=self.user
        )
        
        # Try to create duplicate
        field_config = {
            'name': 'Existing Field',
            'field_type': 'number'
        }
        
        result = self.validator.validate_field_creation(field_config, self.pipeline)
        self.assertFalse(result.valid)
        self.assertTrue(any('name already exists' in error.lower() for error in result.errors))
    
    def test_field_update_validation(self):
        """Test field update validation"""
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Test Field',
            field_type='text',
            created_by=self.user
        )
        
        # Valid update
        changes = {'name': 'Updated Field'}
        result = self.validator.validate_field_update(field, changes)
        self.assertTrue(result.valid)
        
        # Invalid update (empty name)
        changes = {'name': ''}
        result = self.validator.validate_field_update(field, changes)
        self.assertFalse(result.valid)
    
    def test_risky_migration_detection(self):
        """Test detection of risky field type changes"""
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Test Field',
            field_type='text',
            created_by=self.user
        )
        
        # Create some records with data
        Record.objects.create(
            pipeline=self.pipeline,
            title='Test Record 1',
            data={'test_field': 'text value'},
            created_by=self.user
        )
        Record.objects.create(
            pipeline=self.pipeline,
            title='Test Record 2',
            data={'test_field': 'another text'},
            created_by=self.user
        )
        
        # Test risky change (text to number)
        changes = {'field_type': 'number'}
        result = self.validator.validate_field_update(field, changes)
        
        # Should have warnings about data compatibility
        self.assertTrue(len(result.warnings) > 0)


class DataMigratorTestCase(TransactionTestCase):
    """Test DataMigrator functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.pipeline = Pipeline.objects.create(
            name='Test Pipeline',
            slug='test-pipeline',
            pipeline_type='crm',
            created_by=self.user
        )
        self.migrator = DataMigrator(self.pipeline)
    
    def test_field_rename_migration(self):
        """Test migrating data when field name changes"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Old Name',
            field_type='text',
            created_by=self.user
        )
        
        # Create records with data
        record1 = Record.objects.create(
            pipeline=self.pipeline,
            title='Record 1',
            data={field.slug: 'test value 1'},
            created_by=self.user
        )
        record2 = Record.objects.create(
            pipeline=self.pipeline,
            title='Record 2',
            data={field.slug: 'test value 2'},
            created_by=self.user
        )
        
        # Simulate field rename
        original_config = {
            'slug': field.slug,
            'name': 'Old Name',
            'field_type': 'text'
        }
        
        change_analysis = {
            'requires_migration': True,
            'migration_types': ['field_rename'],
            'risk_level': 'medium',
            'affected_records_estimate': 2
        }
        
        # Update field name/slug
        field.name = 'New Name'
        field.save()  # This will regenerate slug
        
        operation_id = "test_migration_001"
        
        # Perform migration
        result = self.migrator.migrate_field_data(
            field, original_config, change_analysis, operation_id
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.records_processed, 2)
        
        # Verify data was migrated
        record1.refresh_from_db()
        record2.refresh_from_db()
        
        # Old key should be gone, new key should have the data
        self.assertNotIn(original_config['slug'], record1.data)
        self.assertNotIn(original_config['slug'], record2.data)
        self.assertIn(field.slug, record1.data)
        self.assertIn(field.slug, record2.data)
        self.assertEqual(record1.data[field.slug], 'test value 1')
        self.assertEqual(record2.data[field.slug], 'test value 2')
    
    def test_field_type_migration(self):
        """Test migrating data when field type changes"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Number Field',
            field_type='text',
            created_by=self.user
        )
        
        # Create records with numeric text data
        record1 = Record.objects.create(
            pipeline=self.pipeline,
            title='Record 1',
            data={field.slug: '123'},
            created_by=self.user
        )
        record2 = Record.objects.create(
            pipeline=self.pipeline,
            title='Record 2',
            data={field.slug: '456.78'},
            created_by=self.user
        )
        
        # Simulate type change
        original_config = {
            'slug': field.slug,
            'name': 'Number Field',
            'field_type': 'text'
        }
        
        change_analysis = {
            'requires_migration': True,
            'migration_types': ['type_change'],
            'risk_level': 'high',
            'affected_records_estimate': 2
        }
        
        # Change field type
        field.field_type = 'number'
        field.save()
        
        operation_id = "test_migration_002"
        
        # Perform migration
        result = self.migrator.migrate_field_data(
            field, original_config, change_analysis, operation_id
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.records_processed, 2)
        
        # Verify data was converted
        record1.refresh_from_db()
        record2.refresh_from_db()
        
        # Data should be converted to numbers
        self.assertEqual(record1.data[field.slug], 123)
        self.assertEqual(record2.data[field.slug], 456.78)
    
    def test_migration_rollback_on_error(self):
        """Test rollback when migration fails"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Test Field',
            field_type='text',
            created_by=self.user
        )
        
        # Create record with invalid data for number conversion
        record = Record.objects.create(
            pipeline=self.pipeline,
            title='Record 1',
            data={field.slug: 'not a number'},
            created_by=self.user
        )
        
        original_config = {
            'slug': field.slug,
            'name': 'Test Field',
            'field_type': 'text'
        }
        
        change_analysis = {
            'requires_migration': True,
            'migration_types': ['type_change'],
            'risk_level': 'high',
            'affected_records_estimate': 1
        }
        
        # Change field type to number (should fail)
        field.field_type = 'number'
        field.save()
        
        operation_id = "test_migration_003"
        
        # Perform migration (should fail and rollback)
        result = self.migrator.migrate_field_data(
            field, original_config, change_analysis, operation_id
        )
        
        self.assertFalse(result.success)
        self.assertTrue(len(result.errors) > 0)
        
        # Verify data wasn't corrupted
        record.refresh_from_db()
        self.assertEqual(record.data[field.slug], 'not a number')


class FieldOperationManagerTestCase(TransactionTestCase):
    """Test FieldOperationManager functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.pipeline = Pipeline.objects.create(
            name='Test Pipeline',
            slug='test-pipeline',
            pipeline_type='crm',
            created_by=self.user
        )
        self.field_manager = get_field_operation_manager(self.pipeline)
    
    def test_create_field_success(self):
        """Test successful field creation"""
        field_config = {
            'name': 'New Field',
            'field_type': 'text',
            'field_config': {'max_length': 100},
            'is_required': True
        }
        
        result = self.field_manager.create_field(field_config, self.user)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.field)
        self.assertEqual(result.field.name, 'New Field')
        self.assertEqual(result.field.field_type, 'text')
        self.assertTrue(result.field.is_required)
        self.assertEqual(result.field.created_by, self.user)
        self.assertIsNotNone(result.operation_id)
    
    def test_create_field_validation_error(self):
        """Test field creation with validation errors"""
        field_config = {
            'field_type': 'text'
            # Missing required name
        }
        
        result = self.field_manager.create_field(field_config, self.user)
        
        self.assertFalse(result.success)
        self.assertIsNone(result.field)
        self.assertTrue(len(result.errors) > 0)
        self.assertIsNotNone(result.operation_id)
    
    def test_update_field_simple_change(self):
        """Test updating field without migration"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Original Field',
            field_type='text',
            created_by=self.user
        )
        
        # Simple update that doesn't require migration
        changes = {
            'display_name': 'Updated Display Name',
            'is_required': True
        }
        
        result = self.field_manager.update_field(field.id, changes, self.user)
        
        self.assertTrue(result.success)
        self.assertEqual(result.field.display_name, 'Updated Display Name')
        self.assertTrue(result.field.is_required)
        self.assertIsNotNone(result.operation_id)
        
        # Should not require migration
        migration_required = result.metadata.get('migration_required', False)
        self.assertFalse(migration_required)
    
    def test_update_field_with_migration(self):
        """Test updating field that requires migration"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Test Field',
            field_type='text',
            created_by=self.user
        )
        
        # Create record with data
        Record.objects.create(
            pipeline=self.pipeline,
            title='Test Record',
            data={field.slug: 'test value'},
            created_by=self.user
        )
        
        # Update that requires migration
        changes = {'name': 'Renamed Field'}
        
        result = self.field_manager.update_field(field.id, changes, self.user)
        
        self.assertTrue(result.success)
        self.assertEqual(result.field.name, 'Renamed Field')
        self.assertIsNotNone(result.operation_id)
        
        # Should require migration
        migration_required = result.metadata.get('migration_required', False)
        self.assertTrue(migration_required)
        
        # Verify migration types
        migration_types = result.metadata.get('migration_types', [])
        self.assertIn('field_rename', migration_types)
    
    def test_soft_delete_field(self):
        """Test soft deleting a field"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Field to Delete',
            field_type='text',
            created_by=self.user
        )
        
        original_field_count = Field.objects.count()
        
        result = self.field_manager.delete_field(field.id, self.user, hard_delete=False)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.operation_id)
        self.assertEqual(result.metadata['deletion_type'], 'soft')
        
        # Field should still exist but be marked deleted
        self.assertEqual(Field.objects.count(), original_field_count)
        field.refresh_from_db()
        self.assertTrue(field.is_deleted)
        self.assertIsNotNone(field.deleted_at)
        self.assertEqual(field.deleted_by, self.user)
    
    def test_restore_field(self):
        """Test restoring a soft-deleted field"""
        # Create and soft delete field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Field to Restore',
            field_type='text',
            created_by=self.user
        )
        
        # Soft delete first
        delete_result = self.field_manager.delete_field(field.id, self.user, hard_delete=False)
        self.assertTrue(delete_result.success)
        
        # Now restore
        restore_result = self.field_manager.restore_field(field.id, self.user)
        
        self.assertTrue(restore_result.success)
        self.assertIsNotNone(restore_result.operation_id)
        self.assertEqual(restore_result.metadata['operation_type'], 'restore')
        
        # Field should be active again
        field.refresh_from_db()
        self.assertFalse(field.is_deleted)
        self.assertIsNone(field.deleted_at)
        self.assertIsNone(field.deleted_by)
    
    def test_hard_delete_field(self):
        """Test hard deleting a field"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Field to Hard Delete',
            field_type='text',
            created_by=self.user
        )
        
        field_id = field.id
        original_field_count = Field.objects.count()
        
        result = self.field_manager.delete_field(field.id, self.user, hard_delete=True)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.operation_id)
        self.assertEqual(result.metadata['deletion_type'], 'hard')
        
        # Field should be completely removed
        self.assertEqual(Field.objects.count(), original_field_count - 1)
        with self.assertRaises(Field.DoesNotExist):
            Field.objects.get(id=field_id)
    
    def test_operation_id_generation(self):
        """Test that operation IDs are unique"""
        field_config = {
            'name': 'Test Field 1',
            'field_type': 'text'
        }
        
        result1 = self.field_manager.create_field(field_config, self.user)
        
        field_config['name'] = 'Test Field 2'
        result2 = self.field_manager.create_field(field_config, self.user)
        
        self.assertTrue(result1.success)
        self.assertTrue(result2.success)
        self.assertNotEqual(result1.operation_id, result2.operation_id)
    
    def test_pipeline_schema_update(self):
        """Test that pipeline schema is updated after operations"""
        initial_schema = self.pipeline.field_schema.copy() if self.pipeline.field_schema else {}
        
        field_config = {
            'name': 'Schema Test Field',
            'field_type': 'number'
        }
        
        result = self.field_manager.create_field(field_config, self.user)
        self.assertTrue(result.success)
        
        # Refresh pipeline
        self.pipeline.refresh_from_db()
        
        # Schema should be updated
        self.assertIsNotNone(self.pipeline.field_schema)
        self.assertNotEqual(self.pipeline.field_schema, initial_schema)


class UnifiedFieldManagementAPITestCase(APITestCase):
    """Test API integration with unified field management"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.pipeline = Pipeline.objects.create(
            name='Test Pipeline',
            slug='test-pipeline',
            pipeline_type='crm',
            created_by=self.user
        )
        self.client.force_authenticate(user=self.user)
    
    def test_api_create_field_success(self):
        """Test API field creation using FieldOperationManager"""
        url = f'/api/v1/pipelines/{self.pipeline.id}/add_field/'
        data = {
            'name': 'API Test Field',
            'field_type': 'text',
            'is_required': True
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIsNotNone(response.data['field'])
        self.assertIsNotNone(response.data['operation_id'])
        self.assertEqual(response.data['field']['name'], 'API Test Field')
    
    def test_api_create_field_validation_error(self):
        """Test API field creation with validation errors"""
        url = f'/api/v1/pipelines/{self.pipeline.id}/add_field/'
        data = {
            'field_type': 'text'
            # Missing required name
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertTrue(len(response.data['errors']) > 0)
        self.assertIsNotNone(response.data['operation_id'])
    
    def test_api_update_field(self):
        """Test API field update using FieldOperationManager"""
        # Create field via API first
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Field to Update',
            field_type='text',
            created_by=self.user
        )
        
        url = f'/api/v1/fields/{field.id}/'
        data = {
            'name': 'Updated Field Name',
            'is_required': True
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['field']['name'], 'Updated Field Name')
        self.assertTrue(response.data['field']['is_required'])
        self.assertIsNotNone(response.data['operation_id'])
    
    def test_api_field_management_actions(self):
        """Test API field management actions"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Field to Manage',
            field_type='text',
            created_by=self.user
        )
        
        url = f'/api/v1/fields/{field.id}/manage/'
        
        # Test soft delete
        data = {'action': 'soft_delete', 'reason': 'API test deletion'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['field_status'], 'soft_deleted')
        self.assertIsNotNone(response.data['operation_id'])
        
        # Test restore
        data = {'action': 'restore'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['field_status'], 'active')
        self.assertIsNotNone(response.data['operation_id'])
    
    def test_api_bulk_operations(self):
        """Test API bulk field operations"""
        # Create multiple fields
        field1 = Field.objects.create(
            pipeline=self.pipeline,
            name='Bulk Field 1',
            field_type='text',
            created_by=self.user
        )
        field2 = Field.objects.create(
            pipeline=self.pipeline,
            name='Bulk Field 2',
            field_type='number',
            created_by=self.user
        )
        
        url = '/api/v1/fields/bulk_operations/'
        data = {
            'operation': 'soft_delete',
            'field_ids': [field1.id, field2.id],
            'pipeline_id': self.pipeline.id
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['operation'], 'soft_delete')
        self.assertEqual(response.data['summary']['processed'], 2)
        self.assertEqual(response.data['summary']['successful'], 2)
        self.assertEqual(response.data['summary']['failed'], 0)
    
    def test_api_migration_dry_run(self):
        """Test API migration dry run functionality"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Migration Test Field',
            field_type='text',
            created_by=self.user
        )
        
        # Create record with data
        Record.objects.create(
            pipeline=self.pipeline,
            title='Test Record',
            data={field.slug: 'test data'},
            created_by=self.user
        )
        
        url = f'/api/v1/fields/{field.id}/migrate_schema/'
        data = {
            'new_config': {
                'name': 'Renamed Field',
                'field_type': 'text'
            },
            'dry_run': True
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertTrue(response.data['dry_run'])
        self.assertIn('impact_analysis', response.data)
        
        # Verify field wasn't actually changed
        field.refresh_from_db()
        self.assertEqual(field.name, 'Migration Test Field')


class SignalIntegrationTestCase(TransactionTestCase):
    """Test signal integration with unified system"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.pipeline = Pipeline.objects.create(
            name='Test Pipeline',
            slug='test-pipeline',
            pipeline_type='crm',
            created_by=self.user
        )
    
    @patch('pipelines.field_operations.get_field_operation_manager')
    def test_field_save_signal_delegation(self, mock_get_manager):
        """Test that field save signals delegate to FieldOperationManager"""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        
        # Create field (triggers signal)
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Signal Test Field',
            field_type='text',
            created_by=self.user
        )
        
        # Verify signal called FieldOperationManager
        mock_get_manager.assert_called_with(self.pipeline)
        mock_manager.handle_field_save_signal.assert_called_with(field, True)
    
    def test_pipeline_schema_update_on_field_save(self):
        """Test pipeline schema is updated when field is saved"""
        initial_schema = self.pipeline.field_schema
        
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Schema Update Test',
            field_type='text',
            created_by=self.user
        )
        
        # Refresh pipeline
        self.pipeline.refresh_from_db()
        
        # Schema should be updated
        self.assertNotEqual(self.pipeline.field_schema, initial_schema)
        self.assertIsNotNone(self.pipeline.field_schema)
    
    def test_audit_log_creation_on_field_operations(self):
        """Test audit logs are created for field operations"""
        from core.models import AuditLog
        
        initial_log_count = AuditLog.objects.count()
        
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Audit Test Field',
            field_type='text',
            created_by=self.user
        )
        
        # Soft delete field (triggers audit log)
        field.is_deleted = True
        field.deleted_by = self.user
        field.deleted_at = timezone.now()
        field.save()
        
        # Check audit log was created
        final_log_count = AuditLog.objects.count()
        self.assertGreater(final_log_count, initial_log_count)


class PerformanceTestCase(TransactionTestCase):
    """Test performance characteristics of unified system"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.pipeline = Pipeline.objects.create(
            name='Performance Test Pipeline',
            slug='performance-test',
            pipeline_type='crm',
            created_by=self.user
        )
        self.field_manager = get_field_operation_manager(self.pipeline)
    
    def test_bulk_field_creation_performance(self):
        """Test performance of creating multiple fields"""
        import time
        
        field_configs = []
        for i in range(50):
            field_configs.append({
                'name': f'Performance Field {i}',
                'field_type': 'text',
                'field_config': {'max_length': 255}
            })
        
        start_time = time.time()
        
        results = []
        for config in field_configs:
            result = self.field_manager.create_field(config, self.user)
            results.append(result)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # All operations should succeed
        successful = sum(1 for r in results if r.success)
        self.assertEqual(successful, 50)
        
        # Performance should be reasonable (< 30 seconds for 50 fields)
        self.assertLess(duration, 30.0, f"Bulk creation took {duration:.2f} seconds")
        
        # Average should be < 0.6 seconds per field
        avg_per_field = duration / 50
        self.assertLess(avg_per_field, 0.6, f"Average per field: {avg_per_field:.3f} seconds")
    
    def test_state_manager_memory_efficiency(self):
        """Test memory efficiency of state management"""
        state_manager = get_field_state_manager()
        
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Memory Test Field',
            field_type='text',
            created_by=self.user
        )
        
        # Capture states for many operations
        operation_ids = []
        for i in range(100):
            operation_id = f"memory_test_{i}"
            operation_ids.append(operation_id)
            state_manager.capture_field_state(field.id, operation_id)
        
        # Check memory usage
        memory_info = state_manager.get_memory_usage_info()
        self.assertEqual(memory_info['active_operations'], 100)
        
        # Cleanup half
        for i in range(50):
            state_manager.cleanup_operation_state(operation_ids[i])
        
        # Memory usage should reduce
        updated_memory_info = state_manager.get_memory_usage_info()
        self.assertEqual(updated_memory_info['active_operations'], 50)
        
        # Memory should be reasonably bounded
        estimated_memory = updated_memory_info['estimated_memory_bytes']
        self.assertLess(estimated_memory, 1024 * 1024, "Memory usage exceeds 1MB")