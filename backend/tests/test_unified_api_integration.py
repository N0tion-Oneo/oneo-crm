"""
Tests for API integration with unified field management system
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock

from pipelines.models import Pipeline, Field, Record
from pipelines.field_operations import FieldOperationResult

User = get_user_model()


class UnifiedAPIIntegrationTestCase(APITestCase):
    """Test API endpoints use the unified field management system"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.pipeline = Pipeline.objects.create(
            name='API Test Pipeline',
            slug='api-test-pipeline',
            pipeline_type='crm',
            created_by=self.user
        )
        
        self.client.force_authenticate(user=self.user)
    
    # =============================================================================
    # PIPELINE ADD_FIELD ENDPOINT TESTS
    # =============================================================================
    
    @patch('pipelines.views.get_field_operation_manager')
    def test_pipeline_add_field_success(self, mock_get_manager):
        """Test pipeline add_field endpoint uses FieldOperationManager"""
        # Mock successful field creation
        mock_manager = MagicMock()
        mock_field = Field(
            id=1,
            pipeline=self.pipeline,
            name='API Test Field',
            field_type='text',
            created_by=self.user
        )
        
        mock_result = FieldOperationResult(
            success=True,
            field=mock_field,
            operation_id='test_op_001',
            warnings=['Test warning'],
            metadata={'operation_type': 'create'}
        )
        
        mock_manager.create_field.return_value = mock_result
        mock_get_manager.return_value = mock_manager
        
        # Make API call
        url = f'/api/v1/pipelines/{self.pipeline.id}/add_field/'
        data = {
            'name': 'API Test Field',
            'field_type': 'text',
            'is_required': False
        }
        
        response = self.client.post(url, data, format='json')
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['operation_id'], 'test_op_001')
        self.assertEqual(response.data['warnings'], ['Test warning'])
        
        # Verify FieldOperationManager was called
        mock_get_manager.assert_called_once_with(self.pipeline)
        mock_manager.create_field.assert_called_once_with(data, self.user)
    
    @patch('pipelines.views.get_field_operation_manager')
    def test_pipeline_add_field_validation_error(self, mock_get_manager):
        """Test pipeline add_field handles validation errors"""
        # Mock validation error
        mock_manager = MagicMock()
        mock_result = FieldOperationResult(
            success=False,
            operation_id='test_op_002',
            errors=['Field name is required'],
            warnings=['Test warning']
        )
        
        mock_manager.create_field.return_value = mock_result
        mock_get_manager.return_value = mock_manager
        
        # Make API call with invalid data
        url = f'/api/v1/pipelines/{self.pipeline.id}/add_field/'
        data = {
            'field_type': 'text'
            # Missing required name
        }
        
        response = self.client.post(url, data, format='json')
        
        # Verify error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['errors'], ['Field name is required'])
        self.assertEqual(response.data['operation_id'], 'test_op_002')
    
    @patch('pipelines.views.get_field_operation_manager')
    def test_pipeline_add_field_exception_handling(self, mock_get_manager):
        """Test pipeline add_field handles exceptions"""
        # Mock exception
        mock_get_manager.side_effect = Exception('Test exception')
        
        # Make API call
        url = f'/api/v1/pipelines/{self.pipeline.id}/add_field/'
        data = {
            'name': 'Test Field',
            'field_type': 'text'
        }
        
        response = self.client.post(url, data, format='json')
        
        # Verify error response
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertFalse(response.data['success'])
        self.assertIn('Field creation failed', response.data['errors'][0])
    
    # =============================================================================
    # FIELD VIEWSET CRUD TESTS
    # =============================================================================
    
    @patch('pipelines.views.get_field_operation_manager')
    def test_field_create_endpoint(self, mock_get_manager):
        """Test field creation endpoint uses FieldOperationManager"""
        # Mock successful creation
        mock_manager = MagicMock()
        mock_field = Field(
            id=1,
            pipeline=self.pipeline,
            name='Create Test Field',
            field_type='number',
            created_by=self.user
        )
        
        mock_result = FieldOperationResult(
            success=True,
            field=mock_field,
            operation_id='create_op_001'
        )
        
        mock_manager.create_field.return_value = mock_result
        mock_get_manager.return_value = mock_manager
        
        # Make API call
        url = '/api/v1/fields/'
        data = {
            'pipeline': self.pipeline.id,
            'name': 'Create Test Field',
            'field_type': 'number'
        }
        
        response = self.client.post(url, data, format='json')
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['operation_id'], 'create_op_001')
    
    @patch('pipelines.views.get_field_operation_manager')
    def test_field_update_endpoint(self, mock_get_manager):
        """Test field update endpoint uses FieldOperationManager"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Update Test Field',
            field_type='text',
            created_by=self.user
        )
        
        # Mock successful update
        mock_manager = MagicMock()
        field.name = 'Updated Test Field'  # Simulate update
        
        mock_result = FieldOperationResult(
            success=True,
            field=field,
            operation_id='update_op_001',
            metadata={
                'operation_type': 'update',
                'migration_required': False
            }
        )
        
        mock_manager.update_field.return_value = mock_result
        mock_get_manager.return_value = mock_manager
        
        # Make API call
        url = f'/api/v1/fields/{field.id}/'
        data = {
            'name': 'Updated Test Field',
            'is_required': True
        }
        
        response = self.client.patch(url, data, format='json')
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['operation_id'], 'update_op_001')
        self.assertFalse(response.data['metadata']['migration_required'])
        
        # Verify FieldOperationManager was called
        mock_manager.update_field.assert_called_once_with(field.id, data, self.user)
    
    @patch('pipelines.views.get_field_operation_manager')
    def test_field_update_with_migration(self, mock_get_manager):
        """Test field update that requires migration"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Migration Test Field',
            field_type='text',
            created_by=self.user
        )
        
        # Mock successful update with migration
        mock_manager = MagicMock()
        field.field_type = 'number'  # Simulate type change
        
        mock_result = FieldOperationResult(
            success=True,
            field=field,
            operation_id='update_migration_001',
            warnings=['Data conversion may affect existing records'],
            metadata={
                'operation_type': 'update',
                'migration_required': True,
                'migration_types': ['type_change'],
                'migration_result': {'success': True, 'records_processed': 5}
            }
        )
        
        mock_manager.update_field.return_value = mock_result
        mock_get_manager.return_value = mock_manager
        
        # Make API call
        url = f'/api/v1/fields/{field.id}/'
        data = {'field_type': 'number'}
        
        response = self.client.patch(url, data, format='json')
        
        # Verify response includes migration info
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertTrue(response.data['metadata']['migration_required'])
        self.assertIn('type_change', response.data['metadata']['migration_types'])
        self.assertTrue(len(response.data['warnings']) > 0)
    
    @patch('pipelines.views.get_field_operation_manager')
    def test_field_delete_endpoint(self, mock_get_manager):
        """Test field deletion endpoint uses FieldOperationManager"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Delete Test Field',
            field_type='text',
            created_by=self.user
        )
        
        # Mock successful deletion
        mock_manager = MagicMock()
        mock_result = FieldOperationResult(
            success=True,
            operation_id='delete_op_001',
            metadata={
                'operation_type': 'delete',
                'deletion_type': 'soft'
            }
        )
        
        mock_manager.delete_field.return_value = mock_result
        mock_get_manager.return_value = mock_manager
        
        # Make API call
        url = f'/api/v1/fields/{field.id}/'
        response = self.client.delete(url)
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['operation_id'], 'delete_op_001')
        
        # Verify FieldOperationManager was called
        mock_manager.delete_field.assert_called_once_with(field.id, self.user, hard_delete=False)
    
    # =============================================================================
    # FIELD MANAGEMENT ACTION TESTS
    # =============================================================================
    
    @patch('pipelines.views.get_field_operation_manager')
    def test_field_manage_soft_delete(self, mock_get_manager):
        """Test field management soft delete action"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Manage Test Field',
            field_type='text',
            created_by=self.user
        )
        
        # Mock successful soft delete
        mock_manager = MagicMock()
        mock_result = FieldOperationResult(
            success=True,
            operation_id='manage_delete_001',
            metadata={'deletion_type': 'soft'}
        )
        
        mock_manager.delete_field.return_value = mock_result
        mock_get_manager.return_value = mock_manager
        
        # Make API call
        url = f'/api/v1/fields/{field.id}/manage/'
        data = {
            'action': 'soft_delete',
            'reason': 'API test deletion'
        }
        
        response = self.client.post(url, data, format='json')
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['field_status'], 'soft_deleted')
        self.assertEqual(response.data['operation_id'], 'manage_delete_001')
    
    @patch('pipelines.views.get_field_operation_manager')
    def test_field_manage_restore(self, mock_get_manager):
        """Test field management restore action"""
        # Create soft-deleted field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Restore Test Field',
            field_type='text',
            is_deleted=True,
            created_by=self.user
        )
        
        # Mock successful restore
        mock_manager = MagicMock()
        mock_result = FieldOperationResult(
            success=True,
            operation_id='manage_restore_001',
            metadata={'operation_type': 'restore'}
        )
        
        mock_manager.restore_field.return_value = mock_result
        mock_get_manager.return_value = mock_manager
        
        # Make API call
        url = f'/api/v1/fields/{field.id}/manage/'
        data = {'action': 'restore'}
        
        response = self.client.post(url, data, format='json')
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['field_status'], 'active')
        self.assertEqual(response.data['operation_id'], 'manage_restore_001')
    
    @patch('pipelines.views.get_field_operation_manager')
    def test_field_manage_hard_delete(self, mock_get_manager):
        """Test field management hard delete action"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Hard Delete Test Field',
            field_type='text',
            created_by=self.user
        )
        
        # Mock successful hard delete
        mock_manager = MagicMock()
        mock_result = FieldOperationResult(
            success=True,
            operation_id='manage_hard_delete_001',
            metadata={'deletion_type': 'hard'}
        )
        
        mock_manager.delete_field.return_value = mock_result
        mock_get_manager.return_value = mock_manager
        
        # Make API call
        url = f'/api/v1/fields/{field.id}/manage/'
        data = {
            'action': 'schedule_hard_delete',
            'reason': 'API test hard deletion',
            'grace_days': 7
        }
        
        response = self.client.post(url, data, format='json')
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['field_status'], 'hard_deleted')
        self.assertEqual(response.data['operation_id'], 'manage_hard_delete_001')
        
        # Verify hard delete was called
        mock_manager.delete_field.assert_called_once_with(field.id, self.user, hard_delete=True)
    
    # =============================================================================
    # MIGRATION ENDPOINT TESTS
    # =============================================================================
    
    @patch('pipelines.views.get_field_operation_manager')
    def test_migrate_schema_dry_run(self, mock_get_manager):
        """Test migrate_schema endpoint dry run functionality"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Migration Dry Run Field',
            field_type='text',
            created_by=self.user
        )
        
        # Mock dry run response - no actual FieldOperationManager call needed for dry run
        # The endpoint handles dry run internally using FieldValidator and FieldStateManager
        
        # Make API call
        url = f'/api/v1/fields/{field.id}/migrate_schema/'
        data = {
            'new_config': {
                'name': 'Renamed Field',
                'field_type': 'text'
            },
            'dry_run': True
        }
        
        response = self.client.post(url, data, format='json')
        
        # Verify dry run response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertTrue(response.data['dry_run'])
        self.assertIn('impact_analysis', response.data)
        self.assertEqual(response.data['message'], 'Dry run completed - no changes made')
        
        # Verify field wasn't actually changed
        field.refresh_from_db()
        self.assertEqual(field.name, 'Migration Dry Run Field')
    
    @patch('pipelines.views.get_field_operation_manager')
    def test_migrate_schema_actual_migration(self, mock_get_manager):
        """Test migrate_schema endpoint actual migration"""
        # Create field
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Migration Test Field',
            field_type='text',
            created_by=self.user
        )
        
        # Mock successful migration
        mock_manager = MagicMock()
        field.name = 'Migrated Field'  # Simulate change
        
        mock_result = FieldOperationResult(
            success=True,
            field=field,
            operation_id='migration_001',
            metadata={
                'migration_required': True,
                'migration_types': ['field_rename']
            }
        )
        
        mock_manager.update_field.return_value = mock_result
        mock_get_manager.return_value = mock_manager
        
        # Make API call
        url = f'/api/v1/fields/{field.id}/migrate_schema/'
        data = {
            'new_config': {
                'name': 'Migrated Field',
                'field_type': 'text'
            },
            'dry_run': False
        }
        
        response = self.client.post(url, data, format='json')
        
        # Verify migration response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertFalse(response.data.get('dry_run', False))
        self.assertEqual(response.data['operation_id'], 'migration_001')
        self.assertIn('Field updated successfully', response.data['message'])
        
        # Verify FieldOperationManager was called
        mock_manager.update_field.assert_called_once()
    
    # =============================================================================
    # BULK OPERATIONS TESTS
    # =============================================================================
    
    @patch('pipelines.views.get_field_operation_manager')
    def test_bulk_operations_soft_delete(self, mock_get_manager):
        """Test bulk soft delete operations"""
        # Create fields
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
        
        # Mock successful bulk operations
        mock_manager = MagicMock()
        
        # Mock results for each field
        mock_result1 = FieldOperationResult(
            success=True,
            operation_id='bulk_delete_001'
        )
        mock_result2 = FieldOperationResult(
            success=True,
            operation_id='bulk_delete_002'
        )
        
        mock_manager.delete_field.side_effect = [mock_result1, mock_result2]
        mock_get_manager.return_value = mock_manager
        
        # Make API call
        url = '/api/v1/fields/bulk_operations/'
        data = {
            'operation': 'soft_delete',
            'field_ids': [field1.id, field2.id],
            'pipeline_id': self.pipeline.id
        }
        
        response = self.client.post(url, data, format='json')
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['operation'], 'soft_delete')
        self.assertEqual(response.data['summary']['processed'], 2)
        self.assertEqual(response.data['summary']['successful'], 2)
        self.assertEqual(response.data['summary']['failed'], 0)
        
        # Verify individual results
        self.assertEqual(len(response.data['results']), 2)
        for result in response.data['results']:
            self.assertTrue(result['success'])
            self.assertIn(result['field_id'], [field1.id, field2.id])
    
    @patch('pipelines.views.get_field_operation_manager')
    def test_bulk_operations_restore(self, mock_get_manager):
        """Test bulk restore operations"""
        # Create soft-deleted fields
        field1 = Field.objects.create(
            pipeline=self.pipeline,
            name='Bulk Restore Field 1',
            field_type='text',
            is_deleted=True,
            created_by=self.user
        )
        field2 = Field.objects.create(
            pipeline=self.pipeline,
            name='Bulk Restore Field 2',
            field_type='number',
            is_deleted=True,
            created_by=self.user
        )
        
        # Mock successful restore operations
        mock_manager = MagicMock()
        
        mock_result1 = FieldOperationResult(
            success=True,
            operation_id='bulk_restore_001'
        )
        mock_result2 = FieldOperationResult(
            success=True,
            operation_id='bulk_restore_002'
        )
        
        mock_manager.restore_field.side_effect = [mock_result1, mock_result2]
        mock_get_manager.return_value = mock_manager
        
        # Make API call
        url = '/api/v1/fields/bulk_operations/'
        data = {
            'operation': 'restore',
            'field_ids': [field1.id, field2.id],
            'pipeline_id': self.pipeline.id
        }
        
        response = self.client.post(url, data, format='json')
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['operation'], 'restore')
        self.assertEqual(response.data['summary']['processed'], 2)
        self.assertEqual(response.data['summary']['successful'], 2)
        
        # Verify restore_field was called for both fields
        self.assertEqual(mock_manager.restore_field.call_count, 2)
    
    def test_bulk_operations_validation_errors(self):
        """Test bulk operations validation errors"""
        # Missing operation
        url = '/api/v1/fields/bulk_operations/'
        data = {
            'field_ids': [1, 2, 3]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('Operation is required', response.data['errors'])
        
        # Missing field IDs
        data = {
            'operation': 'soft_delete'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('Field IDs are required', response.data['errors'])
    
    @patch('pipelines.views.get_field_operation_manager')
    def test_bulk_operations_partial_failure(self, mock_get_manager):
        """Test bulk operations with partial failures"""
        # Create fields
        field1 = Field.objects.create(
            pipeline=self.pipeline,
            name='Success Field',
            field_type='text',
            created_by=self.user
        )
        field2 = Field.objects.create(
            pipeline=self.pipeline,
            name='Failure Field',
            field_type='number',
            created_by=self.user
        )
        
        # Mock mixed results
        mock_manager = MagicMock()
        
        mock_success_result = FieldOperationResult(
            success=True,
            operation_id='bulk_success_001'
        )
        mock_failure_result = FieldOperationResult(
            success=False,
            operation_id='bulk_failure_001',
            errors=['Validation failed']
        )
        
        mock_manager.delete_field.side_effect = [mock_success_result, mock_failure_result]
        mock_get_manager.return_value = mock_manager
        
        # Make API call
        url = '/api/v1/fields/bulk_operations/'
        data = {
            'operation': 'soft_delete',
            'field_ids': [field1.id, field2.id],
            'pipeline_id': self.pipeline.id
        }
        
        response = self.client.post(url, data, format='json')
        
        # Verify mixed results
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])  # Overall operation succeeds
        self.assertEqual(response.data['summary']['processed'], 2)
        self.assertEqual(response.data['summary']['successful'], 1)
        self.assertEqual(response.data['summary']['failed'], 1)
        
        # Check individual results
        results = response.data['results']
        success_result = next(r for r in results if r['success'])
        failure_result = next(r for r in results if not r['success'])
        
        self.assertEqual(success_result['field_id'], field1.id)
        self.assertEqual(failure_result['field_id'], field2.id)
        self.assertEqual(failure_result['errors'], ['Validation failed'])
    
    # =============================================================================
    # ERROR HANDLING TESTS
    # =============================================================================
    
    def test_api_error_handling_field_not_found(self):
        """Test API error handling when field not found"""
        # Try to update non-existent field
        url = '/api/v1/fields/99999/'
        data = {'name': 'Updated Name'}
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_api_error_handling_permission_denied(self):
        """Test API error handling for permission denied"""
        # Create field owned by different user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        other_pipeline = Pipeline.objects.create(
            name='Other Pipeline',
            slug='other-pipeline',
            pipeline_type='crm',
            created_by=other_user
        )
        field = Field.objects.create(
            pipeline=other_pipeline,
            name='Other Field',
            field_type='text',
            created_by=other_user
        )
        
        # Try to update field without permission
        url = f'/api/v1/fields/{field.id}/'
        data = {'name': 'Unauthorized Update'}
        
        response = self.client.patch(url, data, format='json')
        
        # Should return 404 (field filtered out by permissions) or 403
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
    
    def test_api_response_format_consistency(self):
        """Test that all API responses follow consistent format"""
        # Create field for testing
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Format Test Field',
            field_type='text',
            created_by=self.user
        )
        
        # Test various endpoints and verify response format
        endpoints_to_test = [
            (f'/api/v1/pipelines/{self.pipeline.id}/add_field/', 'POST', {
                'name': 'Format Test Add Field',
                'field_type': 'text'
            }),
            (f'/api/v1/fields/{field.id}/manage/', 'POST', {
                'action': 'soft_delete',
                'reason': 'Format test'
            })
        ]
        
        for url, method, data in endpoints_to_test:
            if method == 'POST':
                response = self.client.post(url, data, format='json')
            
            # All responses should have consistent structure
            if response.status_code in [200, 201]:
                self.assertIn('success', response.data)
                self.assertIsInstance(response.data['success'], bool)
                
                if 'operation_id' in response.data:
                    self.assertIsInstance(response.data['operation_id'], str)
                
                if 'errors' in response.data:
                    self.assertIsInstance(response.data['errors'], list)
                
                if 'warnings' in response.data:
                    self.assertIsInstance(response.data['warnings'], list)