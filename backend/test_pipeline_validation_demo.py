#!/usr/bin/env python
"""
Demonstration of the pipeline validation fix for RecordUpdateProcessor
"""
import os
import sys
import django
import asyncio
from unittest.mock import Mock, AsyncMock, patch

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['DJANGO_SETTINGS_MODULE'] = 'oneo_crm.settings'
django.setup()

from workflows.nodes.data.record_ops import RecordUpdateProcessor


async def test_pipeline_validation():
    """Test the pipeline validation behavior"""
    processor = RecordUpdateProcessor()

    print("=" * 60)
    print("Pipeline Validation Test for RecordUpdateProcessor")
    print("=" * 60)

    # Test Case 1: No pipeline specified (backward compatibility)
    print("\n1️⃣ Test Case 1: No pipeline_id specified")
    print("   Expected: Should work normally (backward compatibility)")

    mock_record = Mock()
    mock_record.id = "rec-123"
    mock_record.pipeline_id = "pipeline-original"
    mock_record.data = {"name": "Test Record"}
    mock_record.updated_at = Mock(isoformat=lambda: "2024-01-01T00:00:00Z")
    mock_record.save = AsyncMock()

    config = {
        'record_id_source': 'rec-123',
        'update_data': {'status': 'updated'},
        'merge_strategy': 'merge'
    }

    with patch('workflows.nodes.data.record_ops.sync_to_async') as mock_sync:
        mock_sync.return_value = AsyncMock(return_value=mock_record)

        result = await processor.process(config, {})
        print(f"   ✅ Result: {result['success']}")
        print(f"   ✅ Record pipeline: {result['pipeline_id']}")

    # Test Case 2: Matching pipeline specified
    print("\n2️⃣ Test Case 2: Matching pipeline_id specified")
    print("   Expected: Should validate and succeed")

    config_with_matching_pipeline = {
        'record_id_source': 'rec-123',
        'pipeline_id': 'pipeline-original',  # Matches the record's pipeline
        'update_data': {'status': 'verified'},
        'merge_strategy': 'merge'
    }

    with patch('workflows.nodes.data.record_ops.sync_to_async') as mock_sync:
        mock_sync.return_value = AsyncMock(return_value=mock_record)

        result = await processor.process(config_with_matching_pipeline, {})
        print(f"   ✅ Result: {result['success']}")
        print(f"   ✅ Validation passed for pipeline: {result['pipeline_id']}")

    # Test Case 3: Mismatched pipeline specified
    print("\n3️⃣ Test Case 3: Mismatched pipeline_id specified")
    print("   Expected: Should raise validation error")

    config_with_wrong_pipeline = {
        'record_id_source': 'rec-123',
        'pipeline_id': 'pipeline-wrong',  # Does NOT match the record's pipeline
        'update_data': {'status': 'failed'},
        'merge_strategy': 'merge'
    }

    with patch('workflows.nodes.data.record_ops.sync_to_async') as mock_sync:
        mock_sync.return_value = AsyncMock(return_value=mock_record)

        try:
            result = await processor.process(config_with_wrong_pipeline, {})
            print("   ❌ ERROR: Should have raised ValueError!")
        except ValueError as e:
            print(f"   ✅ Validation error raised as expected:")
            print(f"      {str(e)}")

    print("\n" + "=" * 60)
    print("✨ All tests completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_pipeline_validation())