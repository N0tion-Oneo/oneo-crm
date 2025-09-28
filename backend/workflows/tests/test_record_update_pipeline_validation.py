"""
Test pipeline validation in RecordUpdateProcessor
"""
import pytest
import uuid
from unittest.mock import Mock, patch, AsyncMock
from workflows.nodes.data.record_ops import RecordUpdateProcessor


class TestRecordUpdatePipelineValidation:
    """Test that RecordUpdateProcessor validates pipeline_id correctly"""

    @pytest.mark.asyncio
    async def test_pipeline_validation_success(self):
        """Test that update succeeds when pipeline_id matches"""
        processor = RecordUpdateProcessor()

        # Mock record with pipeline_id
        mock_record = Mock()
        mock_record.id = uuid.uuid4()
        mock_record.pipeline_id = "pipeline-123"
        mock_record.data = {"name": "Test"}
        mock_record.updated_at = Mock(isoformat=lambda: "2024-01-01T00:00:00Z")
        mock_record.save = AsyncMock()

        config = {
            'record_id_source': str(mock_record.id),
            'pipeline_id': 'pipeline-123',  # Matching pipeline
            'update_data': {'status': 'active'},
            'merge_strategy': 'merge'
        }

        context = {}

        with patch('workflows.nodes.data.record_ops.sync_to_async') as mock_sync:
            # Mock the Record.objects.get call
            mock_sync.return_value = AsyncMock(return_value=mock_record)

            result = await processor.process(config, context)

            assert result['success'] is True
            assert result['record_id'] == str(mock_record.id)
            assert result['pipeline_id'] == 'pipeline-123'
            assert 'status' in result['updated_fields']

    @pytest.mark.asyncio
    async def test_pipeline_validation_failure(self):
        """Test that update fails when pipeline_id doesn't match"""
        processor = RecordUpdateProcessor()

        # Mock record with different pipeline_id
        mock_record = Mock()
        mock_record.id = uuid.uuid4()
        mock_record.pipeline_id = "pipeline-456"  # Different pipeline
        mock_record.data = {"name": "Test"}

        config = {
            'record_id_source': str(mock_record.id),
            'pipeline_id': 'pipeline-123',  # Mismatched pipeline
            'update_data': {'status': 'active'},
            'merge_strategy': 'merge'
        }

        context = {}

        with patch('workflows.nodes.data.record_ops.sync_to_async') as mock_sync:
            # Mock the Record.objects.get call
            mock_sync.return_value = AsyncMock(return_value=mock_record)

            with pytest.raises(ValueError) as exc_info:
                await processor.process(config, context)

            assert "belongs to pipeline pipeline-456, not pipeline-123" in str(exc_info.value)
            assert "Please ensure the correct pipeline is selected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_no_pipeline_validation_when_not_specified(self):
        """Test that update works without pipeline_id (backward compatibility)"""
        processor = RecordUpdateProcessor()

        # Mock record
        mock_record = Mock()
        mock_record.id = uuid.uuid4()
        mock_record.pipeline_id = "pipeline-456"
        mock_record.data = {"name": "Test"}
        mock_record.updated_at = Mock(isoformat=lambda: "2024-01-01T00:00:00Z")
        mock_record.save = AsyncMock()

        config = {
            'record_id_source': str(mock_record.id),
            # No pipeline_id specified
            'update_data': {'status': 'active'},
            'merge_strategy': 'merge'
        }

        context = {}

        with patch('workflows.nodes.data.record_ops.sync_to_async') as mock_sync:
            # Mock the Record.objects.get call
            mock_sync.return_value = AsyncMock(return_value=mock_record)

            result = await processor.process(config, context)

            assert result['success'] is True
            assert result['record_id'] == str(mock_record.id)
            assert result['pipeline_id'] == 'pipeline-456'  # Uses record's pipeline

    @pytest.mark.asyncio
    async def test_pipeline_id_included_in_checkpoint(self):
        """Test that pipeline_id is included in checkpoint data"""
        processor = RecordUpdateProcessor()

        node_config = {
            'data': {
                'config': {
                    'record_id_source': 'trigger.record_id',
                    'pipeline_id': 'pipeline-789',
                    'update_data': {'field': 'value'},
                    'merge_strategy': 'replace'
                }
            }
        }

        context = {'trigger': {'record_id': '123'}}

        checkpoint = await processor.create_checkpoint(node_config, context)

        assert checkpoint['pipeline_id'] == 'pipeline-789'
        assert checkpoint['record_id_source'] == 'trigger.record_id'
        assert checkpoint['merge_strategy'] == 'replace'