"""
Focused tests for FieldValidator - consolidated validation logic
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from pipelines.models import Pipeline, Field, Record
from pipelines.validation.field_validator import FieldValidator, FieldValidationResult

User = get_user_model()


class FieldValidatorDetailedTestCase(TestCase):
    """Detailed tests for FieldValidator functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.pipeline = Pipeline.objects.create(
            name='Validator Test Pipeline',
            slug='validator-test',
            pipeline_type='crm',
            created_by=self.user
        )
        self.validator = FieldValidator()
    
    # =============================================================================
    # FIELD CREATION VALIDATION TESTS
    # =============================================================================
    
    def test_field_creation_valid_text_field(self):
        """Test valid text field creation"""
        config = {
            'name': 'Valid Text Field',
            'field_type': 'text',
            'field_config': {'max_length': 255},
            'is_required': False
        }
        
        result = self.validator.validate_field_creation(config, self.pipeline)
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_field_creation_valid_number_field(self):
        """Test valid number field creation"""
        config = {
            'name': 'Valid Number Field',
            'field_type': 'number',
            'field_config': {'min_value': 0, 'max_value': 100},
            'storage_constraints': {'precision': 2}
        }
        
        result = self.validator.validate_field_creation(config, self.pipeline)
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_field_creation_valid_select_field(self):
        """Test valid select field creation"""
        config = {
            'name': 'Valid Select Field',
            'field_type': 'select',
            'field_config': {'options': ['Option 1', 'Option 2', 'Option 3']},
            'is_required': True
        }
        
        result = self.validator.validate_field_creation(config, self.pipeline)
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_field_creation_missing_name(self):
        """Test field creation fails without name"""
        config = {
            'field_type': 'text'
        }
        
        result = self.validator.validate_field_creation(config, self.pipeline)
        self.assertFalse(result.valid)
        self.assertTrue(any('name' in error.lower() for error in result.errors))
    
    def test_field_creation_invalid_field_type(self):
        """Test field creation fails with invalid field type"""
        config = {
            'name': 'Invalid Field',
            'field_type': 'invalid_type'
        }
        
        result = self.validator.validate_field_creation(config, self.pipeline)
        self.assertFalse(result.valid)
        self.assertTrue(any('field_type' in error.lower() for error in result.errors))
    
    def test_field_creation_empty_name(self):
        """Test field creation fails with empty name"""
        config = {
            'name': '',
            'field_type': 'text'
        }
        
        result = self.validator.validate_field_creation(config, self.pipeline)
        self.assertFalse(result.valid)
        self.assertTrue(any('name' in error.lower() and 'empty' in error.lower() for error in result.errors))
    
    def test_field_creation_duplicate_name(self):
        """Test field creation fails with duplicate name"""
        # Create existing field
        Field.objects.create(
            pipeline=self.pipeline,
            name='Existing Field',
            field_type='text',
            created_by=self.user
        )
        
        # Try to create duplicate
        config = {
            'name': 'Existing Field',
            'field_type': 'number'
        }
        
        result = self.validator.validate_field_creation(config, self.pipeline)
        self.assertFalse(result.valid)
        self.assertTrue(any('already exists' in error.lower() for error in result.errors))
    
    def test_field_creation_select_without_options(self):
        """Test select field creation fails without options"""
        config = {
            'name': 'Select Field',
            'field_type': 'select'
            # Missing options in field_config
        }
        
        result = self.validator.validate_field_creation(config, self.pipeline)
        self.assertFalse(result.valid)
        self.assertTrue(any('options' in error.lower() for error in result.errors))
    
    def test_field_creation_select_empty_options(self):
        """Test select field creation fails with empty options"""
        config = {
            'name': 'Select Field',
            'field_type': 'select',
            'field_config': {'options': []}
        }
        
        result = self.validator.validate_field_creation(config, self.pipeline)
        self.assertFalse(result.valid)
        self.assertTrue(any('options' in error.lower() for error in result.errors))
    
    def test_field_creation_invalid_ai_config(self):
        """Test AI field creation with invalid configuration"""
        config = {
            'name': 'AI Field',
            'field_type': 'ai',
            'is_ai_field': True,
            'ai_config': {}  # Missing required prompt
        }
        
        result = self.validator.validate_field_creation(config, self.pipeline)
        self.assertFalse(result.valid)
        self.assertTrue(any('prompt' in error.lower() for error in result.errors))
    
    # =============================================================================
    # FIELD UPDATE VALIDATION TESTS
    # =============================================================================
    
    def test_field_update_valid_name_change(self):
        """Test valid field name update"""
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Original Name',
            field_type='text',
            created_by=self.user
        )
        
        changes = {'name': 'Updated Name'}
        result = self.validator.validate_field_update(field, changes)
        
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_field_update_valid_config_change(self):
        """Test valid field config update"""
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Text Field',
            field_type='text',
            field_config={'max_length': 100},
            created_by=self.user
        )
        
        changes = {
            'field_config': {'max_length': 200}
        }
        result = self.validator.validate_field_update(field, changes)
        
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_field_update_risky_type_change(self):
        """Test field type change generates warnings"""
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Type Change Field',
            field_type='text',
            created_by=self.user
        )
        
        # Create record with data that might not convert well
        Record.objects.create(
            pipeline=self.pipeline,
            title='Test Record',
            data={field.slug: 'not a number'},
            created_by=self.user
        )
        
        changes = {'field_type': 'number'}
        result = self.validator.validate_field_update(field, changes)
        
        # Should be valid but with warnings
        self.assertTrue(result.valid)
        self.assertTrue(len(result.warnings) > 0)
        self.assertTrue(any('conversion' in warning.lower() for warning in result.warnings))
    
    def test_field_update_invalid_name_to_existing(self):
        """Test field update fails when changing to existing name"""
        # Create two fields
        field1 = Field.objects.create(
            pipeline=self.pipeline,
            name='Field One',
            field_type='text',
            created_by=self.user
        )
        Field.objects.create(
            pipeline=self.pipeline,
            name='Field Two',
            field_type='text',
            created_by=self.user
        )
        
        # Try to rename field1 to field2's name
        changes = {'name': 'Field Two'}
        result = self.validator.validate_field_update(field1, changes)
        
        self.assertFalse(result.valid)
        self.assertTrue(any('already exists' in error.lower() for error in result.errors))
    
    def test_field_update_empty_name(self):
        """Test field update fails with empty name"""
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Valid Field',
            field_type='text',
            created_by=self.user
        )
        
        changes = {'name': ''}
        result = self.validator.validate_field_update(field, changes)
        
        self.assertFalse(result.valid)
        self.assertTrue(any('name' in error.lower() for error in result.errors))
    
    def test_field_update_constraint_tightening(self):
        """Test field update with constraint tightening generates warnings"""
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Constraint Field',
            field_type='text',
            storage_constraints={'max_storage_length': 255},
            created_by=self.user
        )
        
        # Create record with long data
        Record.objects.create(
            pipeline=self.pipeline,
            title='Test Record',
            data={field.slug: 'a' * 200},  # 200 characters
            created_by=self.user
        )
        
        # Tighten constraint
        changes = {
            'storage_constraints': {'max_storage_length': 100}
        }
        result = self.validator.validate_field_update(field, changes)
        
        # Should be valid but with warnings
        self.assertTrue(result.valid)
        self.assertTrue(len(result.warnings) > 0)
        self.assertTrue(any('truncation' in warning.lower() for warning in result.warnings))
    
    # =============================================================================
    # FIELD DELETION VALIDATION TESTS
    # =============================================================================
    
    def test_field_deletion_valid(self):
        """Test valid field deletion"""
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Field to Delete',
            field_type='text',
            created_by=self.user
        )
        
        result = self.validator.validate_field_deletion(field, hard_delete=False)
        
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_field_deletion_with_data_warning(self):
        """Test field deletion with data generates warnings"""
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Field with Data',
            field_type='text',
            created_by=self.user
        )
        
        # Create records with data
        for i in range(5):
            Record.objects.create(
                pipeline=self.pipeline,
                title=f'Record {i}',
                data={field.slug: f'value {i}'},
                created_by=self.user
            )
        
        result = self.validator.validate_field_deletion(field, hard_delete=False)
        
        self.assertTrue(result.valid)
        self.assertTrue(len(result.warnings) > 0)
        self.assertTrue(any('data will be lost' in warning.lower() for warning in result.warnings))
    
    def test_field_hard_deletion_already_soft_deleted(self):
        """Test hard deletion of already soft-deleted field"""
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Soft Deleted Field',
            field_type='text',
            is_deleted=True,
            created_by=self.user
        )
        
        result = self.validator.validate_field_deletion(field, hard_delete=True)
        
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_field_deletion_already_deleted(self):
        """Test deletion of already deleted field fails"""
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Already Deleted Field',
            field_type='text',
            is_deleted=True,
            created_by=self.user
        )
        
        result = self.validator.validate_field_deletion(field, hard_delete=False)
        
        self.assertFalse(result.valid)
        self.assertTrue(any('already deleted' in error.lower() for error in result.errors))
    
    # =============================================================================
    # FIELD RESTORATION VALIDATION TESTS
    # =============================================================================
    
    def test_field_restoration_valid(self):
        """Test valid field restoration"""
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Deleted Field',
            field_type='text',
            is_deleted=True,
            created_by=self.user
        )
        
        result = self.validator.validate_field_restoration(field)
        
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_field_restoration_not_deleted(self):
        """Test restoration of non-deleted field fails"""
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Active Field',
            field_type='text',
            is_deleted=False,
            created_by=self.user
        )
        
        result = self.validator.validate_field_restoration(field)
        
        self.assertFalse(result.valid)
        self.assertTrue(any('not deleted' in error.lower() for error in result.errors))
    
    def test_field_restoration_name_conflict(self):
        """Test restoration fails when name conflicts with existing field"""
        # Create active field
        Field.objects.create(
            pipeline=self.pipeline,
            name='Existing Field',
            field_type='text',
            created_by=self.user
        )
        
        # Create deleted field with same name
        deleted_field = Field.objects.create(
            pipeline=self.pipeline,
            name='Existing Field',
            field_type='number',
            is_deleted=True,
            created_by=self.user
        )
        
        result = self.validator.validate_field_restoration(deleted_field)
        
        self.assertFalse(result.valid)
        self.assertTrue(any('name conflict' in error.lower() or 'already exists' in error.lower() 
                           for error in result.errors))
    
    # =============================================================================
    # MIGRATION SAFETY VALIDATION TESTS
    # =============================================================================
    
    def test_migration_safety_denied_changes(self):
        """Test that certain changes are denied for safety"""
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='Safety Test Field',
            field_type='text',
            created_by=self.user
        )
        
        # Create records with data
        for i in range(10):
            Record.objects.create(
                pipeline=self.pipeline,
                title=f'Record {i}',
                data={field.slug: f'important data {i}'},
                created_by=self.user
            )
        
        # Test highly risky change that might be denied
        changes = {
            'field_type': 'file',  # Very different type
            'storage_constraints': {'max_file_size': 1000}
        }
        
        result = self.validator.validate_field_update(field, changes)
        
        # Depending on implementation, this might be denied or have severe warnings
        if not result.valid:
            self.assertTrue(any('risky' in error.lower() or 'denied' in error.lower() 
                               for error in result.errors))
        else:
            # If allowed, should have serious warnings
            self.assertTrue(len(result.warnings) > 0)
    
    def test_migration_safety_record_count_impact(self):
        """Test validation considers number of affected records"""
        field = Field.objects.create(
            pipeline=self.pipeline,
            name='High Impact Field',
            field_type='text',
            created_by=self.user
        )
        
        # Create many records
        for i in range(1000):
            Record.objects.create(
                pipeline=self.pipeline,
                title=f'Record {i}',
                data={field.slug: f'data {i}'},
                created_by=self.user
            )
        
        # Risky change affecting many records
        changes = {'field_type': 'number'}
        result = self.validator.validate_field_update(field, changes)
        
        # Should have warnings about high impact
        if result.valid:
            self.assertTrue(len(result.warnings) > 0)
            self.assertTrue(any(str(1000) in warning or 'many records' in warning.lower() 
                               for warning in result.warnings))
    
    # =============================================================================
    # VALIDATION RESULT TESTS
    # =============================================================================
    
    def test_validation_result_structure(self):
        """Test ValidationResult contains expected fields"""
        config = {
            'name': 'Test Field',
            'field_type': 'text'
        }
        
        result = self.validator.validate_field_creation(config, self.pipeline)
        
        # Check result has expected attributes
        self.assertTrue(hasattr(result, 'valid'))
        self.assertTrue(hasattr(result, 'errors'))
        self.assertTrue(hasattr(result, 'warnings'))
        self.assertIsInstance(result.valid, bool)
        self.assertIsInstance(result.errors, list)
        self.assertIsInstance(result.warnings, list)
    
    def test_validation_accumulates_multiple_errors(self):
        """Test validation can accumulate multiple errors"""
        config = {
            # Multiple issues: no name, invalid type, invalid config
            'field_type': 'invalid_type',
            'field_config': 'not_a_dict'
        }
        
        result = self.validator.validate_field_creation(config, self.pipeline)
        
        self.assertFalse(result.valid)
        # Should have multiple errors
        self.assertGreater(len(result.errors), 1)
    
    def test_validation_performance(self):
        """Test validation performance is reasonable"""
        import time
        
        config = {
            'name': 'Performance Test Field',
            'field_type': 'text',
            'field_config': {'max_length': 255}
        }
        
        start_time = time.time()
        
        # Run validation many times
        for i in range(100):
            result = self.validator.validate_field_creation(config, self.pipeline)
            self.assertTrue(result.valid)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete quickly (< 1 second for 100 validations)
        self.assertLess(duration, 1.0, f"100 validations took {duration:.3f} seconds")