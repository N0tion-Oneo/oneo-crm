"""
Test AI Field Excluded Fields Security Fix
Tests that excluded_fields configuration is properly respected in AI field processing
"""
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from datetime import timedelta

from tenants.models import Tenant
from pipelines.models import Pipeline, Record, Field
from ai.processors import AIFieldProcessor

User = get_user_model()


class AIExcludedFieldsTest(TenantTestCase):
    """Test AI field processing respects excluded_fields configuration"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
            schema_name="test_ai_excluded",
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test pipeline
        self.pipeline = Pipeline.objects.create(
            name='Test Pipeline',
            description='Pipeline for testing excluded fields',
            created_by=self.user
        )
        
        # Create test record with sensitive data
        self.record_data = {
            'company_name': 'TechCorp Inc',
            'contact_person': 'John Smith',
            'email': 'john@techcorp.com',        # SENSITIVE - should be excluded
            'phone': '+1-555-123-4567',          # SENSITIVE - should be excluded  
            'ssn': '123-45-6789',                # SENSITIVE - should be excluded
            'credit_card': '4111-1111-1111-1111', # SENSITIVE - should be excluded
            'industry': 'technology',
            'deal_value': 50000,
            'notes': 'Interested in our enterprise solution'
        }
        
        self.record = Record.objects.create(
            pipeline=self.pipeline,
            data=self.record_data,
            created_by=self.user,
            updated_by=self.user
        )
    
    @patch('ai.processors.AIFieldProcessor._get_tenant_api_key')
    def test_excluded_fields_in_build_context(self, mock_api_key):
        """Test that _build_context excludes configured sensitive fields"""
        mock_api_key.return_value = 'test-api-key'
        
        processor = AIFieldProcessor(self.tenant, self.user)
        
        # Test with excluded fields configuration
        field_config = {
            'excluded_fields': ['email', 'ssn', 'credit_card', 'phone'],
            'include_all_fields': True,
            'prompt': 'Analyze this record: {*}'
        }
        
        context = processor._build_context(self.record, field_config, {})
        
        # Verify excluded fields are NOT in context
        self.assertNotIn('email', context)
        self.assertNotIn('ssn', context)
        self.assertNotIn('credit_card', context)
        self.assertNotIn('phone', context)
        
        # Verify non-excluded fields ARE in context
        self.assertIn('company_name', context)
        self.assertIn('contact_person', context)
        self.assertIn('industry', context)
        self.assertIn('deal_value', context)
        self.assertIn('notes', context)
        
        # Verify metadata is included
        self.assertIn('record_id', context)
        self.assertIn('pipeline_name', context)
        self.assertIn('tenant_name', context)
    
    @patch('ai.processors.AIFieldProcessor._get_tenant_api_key')
    def test_excluded_fields_in_star_expansion(self, mock_api_key):
        """Test that {*} expansion excludes configured sensitive fields"""
        mock_api_key.return_value = 'test-api-key'
        
        processor = AIFieldProcessor(self.tenant, self.user)
        
        # Test with excluded fields configuration
        field_config = {
            'excluded_fields': ['email', 'ssn', 'credit_card', 'phone'],
            'include_all_fields': True,
            'prompt': 'Analyze this complete record: {*}'
        }
        
        template = "Analyze this complete record: {*}"
        processed_template = processor._preprocess_template(template, self.record, field_config)
        
        # Verify excluded fields are NOT in the {*} expansion
        self.assertNotIn('john@techcorp.com', processed_template)
        self.assertNotIn('123-45-6789', processed_template)
        self.assertNotIn('4111-1111-1111-1111', processed_template)
        self.assertNotIn('+1-555-123-4567', processed_template)
        
        # Verify non-excluded fields ARE in the {*} expansion
        self.assertIn('TechCorp Inc', processed_template)
        self.assertIn('John Smith', processed_template)
        self.assertIn('technology', processed_template)
        self.assertIn('50000', processed_template)
        self.assertIn('enterprise solution', processed_template)
    
    @patch('ai.processors.AIFieldProcessor._get_tenant_api_key')
    def test_no_excluded_fields_includes_all(self, mock_api_key):
        """Test that when no excluded_fields are configured, all fields are included"""
        mock_api_key.return_value = 'test-api-key'
        
        processor = AIFieldProcessor(self.tenant, self.user)
        
        # Test with no excluded fields
        field_config = {
            'excluded_fields': [],
            'include_all_fields': True,
            'prompt': 'Analyze this record: {*}'
        }
        
        context = processor._build_context(self.record, field_config, {})
        template = "Analyze this record: {*}"
        processed_template = processor._preprocess_template(template, self.record, field_config)
        
        # Verify ALL fields are included when no exclusions
        for field_name, field_value in self.record_data.items():
            self.assertIn(field_name, context)
            self.assertIn(str(field_value), processed_template)
    
    @patch('ai.processors.AIFieldProcessor._get_tenant_api_key')
    def test_individual_field_references_respect_exclusions(self, mock_api_key):
        """Test that individual {field_name} references respect excluded fields"""
        mock_api_key.return_value = 'test-api-key'
        
        processor = AIFieldProcessor(self.tenant, self.user)
        
        field_config = {
            'excluded_fields': ['email', 'ssn'],
            'include_all_fields': True,
            'prompt': 'Contact: {contact_person}, Email: {email}, Company: {company_name}'
        }
        
        context = processor._build_context(self.record, field_config, {})
        
        # Test individual field access
        self.assertEqual(context.get('contact_person'), 'John Smith')
        self.assertEqual(context.get('company_name'), 'TechCorp Inc')
        
        # Excluded fields should not be in context
        self.assertIsNone(context.get('email'))
        self.assertIsNone(context.get('ssn'))
    
    @patch('ai.processors.AIFieldProcessor._get_tenant_api_key')
    @patch('ai.processors.openai.OpenAI')
    def test_full_processing_with_excluded_fields(self, mock_openai_client, mock_api_key):
        """Test full AI processing pipeline with excluded fields"""
        mock_api_key.return_value = 'test-api-key'
        
        # Mock OpenAI response
        mock_client_instance = MagicMock()
        mock_openai_client.return_value = mock_client_instance
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Analysis complete"
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 100
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.completion_tokens = 50
        mock_client_instance.chat.completions.create.return_value = mock_response
        
        processor = AIFieldProcessor(self.tenant, self.user)
        
        field_config = {
            'prompt_template': 'Analyze this lead data: {*}. Focus on {company_name} and exclude sensitive info.',
            'model': 'gpt-4o-mini',
            'temperature': 0.3,
            'excluded_fields': ['email', 'ssn', 'credit_card', 'phone'],
            'include_all_fields': True
        }
        
        # Process the field
        result = processor.process_field_sync(self.record, field_config)
        
        # Verify OpenAI was called
        self.assertTrue(mock_client_instance.chat.completions.create.called)
        
        # Get the actual prompt sent to OpenAI
        call_args = mock_client_instance.chat.completions.create.call_args
        messages = call_args[1]['messages']
        user_message = next(msg for msg in messages if msg['role'] == 'user')
        actual_prompt = user_message['content']
        
        # Verify excluded fields are NOT in the prompt sent to OpenAI
        self.assertNotIn('john@techcorp.com', actual_prompt)
        self.assertNotIn('123-45-6789', actual_prompt)
        self.assertNotIn('4111-1111-1111-1111', actual_prompt)
        self.assertNotIn('+1-555-123-4567', actual_prompt)
        
        # Verify non-excluded fields ARE in the prompt
        self.assertIn('TechCorp Inc', actual_prompt)
        self.assertIn('John Smith', actual_prompt)
        self.assertIn('technology', actual_prompt)
        
        # Verify result structure
        self.assertIn('content', result)
        self.assertEqual(result['content'], 'Analysis complete')
        
    @patch('ai.processors.AIFieldProcessor._get_tenant_api_key')
    def test_empty_excluded_fields_list(self, mock_api_key):
        """Test that empty excluded_fields list includes all fields"""
        mock_api_key.return_value = 'test-api-key'
        
        processor = AIFieldProcessor(self.tenant, self.user)
        
        field_config = {
            'excluded_fields': [],  # Empty list
            'prompt': 'Data: {*}'
        }
        
        template = "Data: {*}"
        processed_template = processor._preprocess_template(template, self.record, field_config)
        
        # All fields should be included
        for field_value in self.record_data.values():
            self.assertIn(str(field_value), processed_template)
    
    @patch('ai.processors.AIFieldProcessor._get_tenant_api_key')
    def test_missing_excluded_fields_config(self, mock_api_key):
        """Test that missing excluded_fields config defaults to no exclusions"""
        mock_api_key.return_value = 'test-api-key'
        
        processor = AIFieldProcessor(self.tenant, self.user)
        
        field_config = {
            # excluded_fields key is missing
            'prompt': 'Data: {*}'
        }
        
        template = "Data: {*}"
        processed_template = processor._preprocess_template(template, self.record, field_config)
        
        # All fields should be included when excluded_fields is missing
        for field_value in self.record_data.values():
            self.assertIn(str(field_value), processed_template)