"""
Tests for workflow automation system
"""
import json
import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import AsyncMock, patch
from .models import (
    Workflow, WorkflowExecution, WorkflowTriggerType, 
    WorkflowStatus, ExecutionStatus
)
from .engine import workflow_engine
from .triggers.manager import TriggerManager

User = get_user_model()


class WorkflowModelTests(TestCase):
    """Test workflow models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_workflow_creation(self):
        """Test creating a workflow"""
        workflow = Workflow.objects.create(
            name='Test Workflow',
            description='A test workflow',
            created_by=self.user,
            trigger_type=WorkflowTriggerType.MANUAL,
            workflow_definition={
                'nodes': [
                    {
                        'id': 'node1',
                        'type': 'ai_prompt',
                        'data': {'name': 'Test Node'}
                    }
                ],
                'edges': []
            }
        )
        
        self.assertEqual(workflow.name, 'Test Workflow')
        self.assertEqual(workflow.created_by, self.user)
        self.assertEqual(workflow.status, WorkflowStatus.DRAFT)
        self.assertTrue(workflow.can_execute() == False)  # Draft workflows can't execute
    
    def test_workflow_activation(self):
        """Test workflow activation"""
        workflow = Workflow.objects.create(
            name='Test Workflow',
            created_by=self.user,
            trigger_type=WorkflowTriggerType.MANUAL,
            status=WorkflowStatus.ACTIVE,
            workflow_definition={'nodes': [], 'edges': []}
        )
        
        self.assertTrue(workflow.can_execute())
    
    def test_workflow_execution_creation(self):
        """Test creating workflow execution"""
        workflow = Workflow.objects.create(
            name='Test Workflow',
            created_by=self.user,
            trigger_type=WorkflowTriggerType.MANUAL,
            workflow_definition={'nodes': [], 'edges': []}
        )
        
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            triggered_by=self.user,
            trigger_data={'test': 'data'}
        )
        
        self.assertEqual(execution.workflow, workflow)
        self.assertEqual(execution.triggered_by, self.user)
        self.assertEqual(execution.status, ExecutionStatus.PENDING)
        self.assertTrue(execution.is_running() == False)


class WorkflowEngineTests(TestCase):
    """Test workflow engine functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_simple_workflow_definition(self):
        """Test workflow definition validation"""
        workflow = Workflow.objects.create(
            name='Simple Workflow',
            created_by=self.user,
            trigger_type=WorkflowTriggerType.MANUAL,
            status=WorkflowStatus.ACTIVE,
            workflow_definition={
                'nodes': [
                    {
                        'id': 'start',
                        'type': 'condition',
                        'data': {
                            'name': 'Start Node',
                            'conditions': [{
                                'left': 'test_value',
                                'operator': '==',
                                'right': 'success',
                                'output': 'passed'
                            }],
                            'default_output': 'failed'
                        }
                    }
                ],
                'edges': []
            }
        )
        
        nodes = workflow.get_nodes()
        edges = workflow.get_edges()
        
        self.assertEqual(len(nodes), 1)
        self.assertEqual(len(edges), 0)
        self.assertEqual(nodes[0]['id'], 'start')
    
    def test_execution_graph_building(self):
        """Test execution graph building"""
        nodes = [
            {'id': 'node1', 'type': 'condition'},
            {'id': 'node2', 'type': 'ai_prompt'},
            {'id': 'node3', 'type': 'record_create'}
        ]
        
        edges = [
            {'source': 'node1', 'target': 'node2'},
            {'source': 'node2', 'target': 'node3'}
        ]
        
        graph = workflow_engine._build_execution_graph(nodes, edges)
        
        # Check dependencies
        self.assertEqual(graph['node1']['dependencies'], [])
        self.assertEqual(graph['node2']['dependencies'], ['node1'])
        self.assertEqual(graph['node3']['dependencies'], ['node2'])
        
        # Check dependents
        self.assertEqual(graph['node1']['dependents'], ['node2'])
        self.assertEqual(graph['node2']['dependents'], ['node3'])
        self.assertEqual(graph['node3']['dependents'], [])
    
    def test_condition_evaluation(self):
        """Test condition evaluation"""
        # Test equality
        result = workflow_engine._evaluate_condition('test', '==', 'test')
        self.assertTrue(result)
        
        result = workflow_engine._evaluate_condition('test', '==', 'different')
        self.assertFalse(result)
        
        # Test numeric comparison
        result = workflow_engine._evaluate_condition(10, '>', 5)
        self.assertTrue(result)
        
        result = workflow_engine._evaluate_condition(5, '>', 10)
        self.assertFalse(result)
        
        # Test string operations
        result = workflow_engine._evaluate_condition('hello world', 'contains', 'world')
        self.assertTrue(result)
        
        result = workflow_engine._evaluate_condition('hello', 'starts_with', 'he')
        self.assertTrue(result)


class WorkflowTriggerTests(TestCase):
    """Test workflow triggers"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_trigger_condition_evaluation(self):
        """Test trigger condition evaluation"""
        from pipelines.models import Pipeline, Record
        
        # Create a mock record
        pipeline = Pipeline.objects.create(
            name='Test Pipeline',
            created_by=self.user
        )
        
        record = Record.objects.create(
            pipeline=pipeline,
            data={'status': 'active', 'value': 100},
            created_by=self.user
        )
        
        # Test condition
        condition = {
            'field': 'status',
            'operator': '==',
            'value': 'active'
        }
        
        result = workflow_trigger_manager._evaluate_trigger_condition(condition, record)
        self.assertTrue(result)
        
        # Test numeric condition
        condition = {
            'field': 'value',
            'operator': '>',
            'value': 50
        }
        
        result = workflow_trigger_manager._evaluate_trigger_condition(condition, record)
        self.assertTrue(result)


class WorkflowAPITests(TestCase):
    """Test workflow API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_workflow_serialization(self):
        """Test workflow serialization"""
        from .serializers import WorkflowSerializer
        
        workflow = Workflow.objects.create(
            name='Test Workflow',
            description='Test Description',
            created_by=self.user,
            trigger_type=WorkflowTriggerType.MANUAL,
            workflow_definition={
                'nodes': [{'id': 'test', 'type': 'condition'}],
                'edges': []
            }
        )
        
        serializer = WorkflowSerializer(workflow)
        data = serializer.data
        
        self.assertEqual(data['name'], 'Test Workflow')
        self.assertEqual(data['description'], 'Test Description')
        self.assertEqual(data['trigger_type'], WorkflowTriggerType.MANUAL)
        self.assertIn('workflow_definition', data)


class WorkflowAIIntegrationTests(TestCase):
    """Test AI integration with workflows"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    @patch('workflows.ai_integration.workflow_ai_processor.process_ai_request')
    async def test_ai_node_processing(self, mock_ai_process):
        """Test AI node processing"""
        # Mock AI response
        mock_ai_process.return_value = {
            'content': 'AI generated response',
            'tokens_used': 50,
            'model': 'gpt-4',
            'processing_time_ms': 1000,
            'cost_cents': 5
        }
        
        workflow = Workflow.objects.create(
            name='AI Workflow',
            created_by=self.user,
            trigger_type=WorkflowTriggerType.MANUAL,
            status=WorkflowStatus.ACTIVE,
            workflow_definition={
                'nodes': [
                    {
                        'id': 'ai_node',
                        'type': 'ai_prompt',
                        'data': {
                            'name': 'AI Node',
                            'prompt': 'Analyze this: {input_text}',
                            'ai_config': {
                                'model': 'gpt-4',
                                'temperature': 0.7
                            }
                        }
                    }
                ],
                'edges': []
            }
        )
        
        # Test that AI integration would be called
        self.assertEqual(workflow.workflow_definition['nodes'][0]['type'], 'ai_prompt')
        
        # Mock execution would call AI processor
        mock_ai_process.assert_not_called()  # Not called yet
    
    def test_cost_estimation(self):
        """Test AI cost estimation"""
        from .ai_integration import workflow_ai_processor
        
        cost_estimate = workflow_ai_processor.estimate_ai_cost(
            prompt="This is a test prompt for cost estimation",
            model="gpt-4",
            max_tokens=100
        )
        
        self.assertIn('estimated_cost_usd', cost_estimate)
        self.assertIn('estimated_total_tokens', cost_estimate)
        self.assertGreater(cost_estimate['estimated_cost_usd'], 0)


class WorkflowIntegrationTests(TestCase):
    """Integration tests for complete workflow functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_simple_workflow_structure(self):
        """Test creating a complete workflow structure"""
        workflow = Workflow.objects.create(
            name='Complete Workflow',
            description='A complete workflow for testing',
            created_by=self.user,
            trigger_type=WorkflowTriggerType.RECORD_CREATED,
            status=WorkflowStatus.ACTIVE,
            trigger_config={
                'pipeline_ids': [1, 2],
                'conditions': [
                    {
                        'field': 'status',
                        'operator': '==',
                        'value': 'new'
                    }
                ]
            },
            workflow_definition={
                'nodes': [
                    {
                        'id': 'trigger',
                        'type': 'trigger',
                        'data': {'name': 'Record Created'}
                    },
                    {
                        'id': 'condition',
                        'type': 'condition',
                        'data': {
                            'name': 'Check Status',
                            'conditions': [{
                                'left': {'context_path': 'record_data.priority'},
                                'operator': '==',
                                'right': 'high',
                                'output': 'high_priority'
                            }],
                            'default_output': 'normal_priority'
                        }
                    },
                    {
                        'id': 'ai_analysis',
                        'type': 'ai_prompt',
                        'data': {
                            'name': 'AI Analysis',
                            'prompt': 'Analyze this record: {record_data}',
                            'ai_config': {
                                'model': 'gpt-4',
                                'temperature': 0.3
                            }
                        }
                    },
                    {
                        'id': 'update_record',
                        'type': 'record_update',
                        'data': {
                            'name': 'Update Record',
                            'record_id_source': 'record_id',
                            'update_data': {
                                'ai_analysis': '{node_ai_analysis}',
                                'processed_at': '{timestamp}'
                            }
                        }
                    }
                ],
                'edges': [
                    {'id': 'e1', 'source': 'trigger', 'target': 'condition'},
                    {'id': 'e2', 'source': 'condition', 'target': 'ai_analysis'},
                    {'id': 'e3', 'source': 'ai_analysis', 'target': 'update_record'}
                ]
            }
        )
        
        # Validate structure
        self.assertEqual(workflow.name, 'Complete Workflow')
        self.assertEqual(len(workflow.get_nodes()), 4)
        self.assertEqual(len(workflow.get_edges()), 3)
        self.assertTrue(workflow.can_execute())
        
        # Validate trigger configuration
        self.assertEqual(workflow.trigger_config['pipeline_ids'], [1, 2])
        self.assertEqual(len(workflow.trigger_config['conditions']), 1)