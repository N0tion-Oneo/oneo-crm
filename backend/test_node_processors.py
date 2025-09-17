#!/usr/bin/env python
"""
Quick test of all workflow node processors
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

import asyncio
from django_tenants.utils import schema_context
from workflows.models import Workflow
from workflows.engine import workflow_engine
from django.contrib.auth import get_user_model
from tenants.models import Tenant
from asgiref.sync import sync_to_async

User = get_user_model()

async def test_all_processors():
    """Test all registered processors"""

    # Get all registered processors
    all_processors = sorted(list(workflow_engine.node_processors.keys()))

    print(f'Found {len(all_processors)} registered processors')
    print('=' * 60)

    # Categorize them
    triggers = [p for p in all_processors if p.startswith('trigger_')]
    non_triggers = [p for p in all_processors if not p.startswith('trigger_')]

    print(f'Triggers: {len(triggers)}')
    for t in triggers:
        print(f'  - {t}')

    print(f'\nNon-trigger nodes: {len(non_triggers)}')

    # Test that each processor can be instantiated
    results = {'found': 0, 'missing': 0}

    print('\nProcessor Registration Check:')
    print('-' * 40)

    for node_type in all_processors:
        processor = workflow_engine.node_processors.get(node_type)
        if processor:
            print(f'✅ {node_type:<35} -> {processor.__class__.__name__}')
            results['found'] += 1
        else:
            print(f'❌ {node_type:<35} -> NOT FOUND')
            results['missing'] += 1

    print('=' * 60)
    print(f'SUMMARY:')
    print(f'  Registered: {results["found"]}')
    print(f'  Missing: {results["missing"]}')
    print(f'  Total: {len(all_processors)}')

    # Quick execution test with minimal configs
    print('\nQuick Execution Test (first 5 non-triggers):')
    print('-' * 40)

    @sync_to_async
    def get_user_and_tenant():
        with schema_context('oneotalent'):
            user = User.objects.filter(is_superuser=True).first()
            tenant = Tenant.objects.get(schema_name='oneotalent')
            return user, tenant

    user, tenant = await get_user_and_tenant()

    test_nodes = non_triggers[:5]
    for node_type in test_nodes:
        try:
            # Create minimal workflow
            @sync_to_async
            def create_workflow():
                with schema_context('oneotalent'):
                    return Workflow.objects.create(
                        tenant=tenant,
                        name=f'Test {node_type}',
                        status='active',
                        created_by=user,
                        workflow_definition={
                            'nodes': [{
                                'id': 'test',
                                'type': node_type,
                                'data': {'name': 'Test', 'config': {}}
                            }],
                            'edges': []
                        }
                    )

            workflow = await create_workflow()

            # Try to execute
            execution = await workflow_engine.execute_workflow(
                workflow=workflow,
                trigger_data={'test': True},
                triggered_by=user,
                start_node_id='test'
            )

            print(f'✅ {node_type:<30} - Executed')

            # Cleanup
            @sync_to_async
            def delete_workflow():
                with schema_context('oneotalent'):
                    workflow.delete()
            await delete_workflow()

        except Exception as e:
            if 'validation' in str(e).lower():
                print(f'⚠️  {node_type:<30} - Needs config (expected)')
            else:
                print(f'❌ {node_type:<30} - {str(e)[:30]}')

if __name__ == '__main__':
    asyncio.run(test_all_processors())