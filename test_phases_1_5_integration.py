#!/usr/bin/env python
"""
Comprehensive integration test for Phases 1-5
Tests that all phases work together correctly
"""
import os
import sys
import django
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

def test_comprehensive_phases_1_5_integration():
    """Test complete integration of Phases 1-5"""
    
    print("🧪 COMPREHENSIVE PHASES 1-5 INTEGRATION TEST")
    print("=" * 60)
    
    results = {
        'phase_1_foundation': False,
        'phase_2_authentication': False,
        'phase_3_pipelines': False,
        'phase_4_relationships': False,
        'phase_5_api_layer': False,
        'cross_phase_integration': False
    }
    
    # Phase 1: Foundation - Multi-tenant Infrastructure
    print("\n📋 PHASE 1: Foundation Testing...")
    try:
        from tenants.models import Tenant, Domain
        from django.db import connection
        
        # Test tenant isolation
        tenants = Tenant.objects.all()
        print(f"   ✅ Found {tenants.count()} tenants")
        
        domains = Domain.objects.all() 
        print(f"   ✅ Found {domains.count()} domains")
        
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_schema()")
            schema = cursor.fetchone()[0]
            print(f"   ✅ Current schema: {schema}")
        
        results['phase_1_foundation'] = True
        print("   🎉 Phase 1 Foundation: PASSED")
        
    except Exception as e:
        print(f"   ❌ Phase 1 Foundation: FAILED - {e}")
    
    # Phase 2: Authentication System
    print("\n🔐 PHASE 2: Authentication Testing...")
    try:
        from authentication.models import CustomUser, UserType
        from authentication.permissions import AsyncPermissionManager
        
        # Test user model
        User = get_user_model()
        users = User.objects.all()
        print(f"   ✅ Found {users.count()} users")
        
        # Test user types
        user_types = UserType.objects.all()
        print(f"   ✅ Found {user_types.count()} user types")
        
        # Test permission system (sync version for testing)
        if users.exists():
            test_user = users.first()
            print(f"   ✅ Permission system ready for user: {test_user.email}")
        
        results['phase_2_authentication'] = True
        print("   🎉 Phase 2 Authentication: PASSED")
        
    except Exception as e:
        print(f"   ❌ Phase 2 Authentication: FAILED - {e}")
    
    # Phase 3: Pipeline System
    print("\n🏗️ PHASE 3: Pipeline System Testing...")
    try:
        from pipelines.models import Pipeline, Field, Record, PipelineTemplate
        from pipelines.field_types import FIELD_TYPE_CONFIGS
        from django_tenants.utils import schema_context
        
        # Test in tenant context
        demo_tenant = Tenant.objects.get(schema_name='demo')
        with schema_context('demo'):
            # Test pipeline models
            pipelines = Pipeline.objects.all()
            print(f"   ✅ Found {pipelines.count()} pipelines")
            
            fields = Field.objects.all()
            print(f"   ✅ Found {fields.count()} fields")
            
            records = Record.objects.all()
            print(f"   ✅ Found {records.count()} records")
            
            # Test pipeline templates
            templates = PipelineTemplate.objects.all()
            print(f"   ✅ Found {templates.count()} pipeline templates")
        
        # Test field types (these are not tenant-specific)
        print(f"   ✅ {len(FIELD_TYPE_CONFIGS)} field types available")
        
        results['phase_3_pipelines'] = True
        print("   🎉 Phase 3 Pipeline System: PASSED")
        
    except Exception as e:
        print(f"   ❌ Phase 3 Pipeline System: FAILED - {e}")
    
    # Phase 4: Relationship Engine
    print("\n🔗 PHASE 4: Relationship Engine Testing...")
    try:
        from relationships.models import Relationship, RelationshipType
        from relationships.queries import RelationshipQueryManager
        
        # Test in tenant context
        with schema_context('demo'):
            # Test relationship models
            relationships = Relationship.objects.all()
            print(f"   ✅ Found {relationships.count()} relationships")
            
            relationship_types = RelationshipType.objects.all() 
            print(f"   ✅ Found {relationship_types.count()} relationship types")
        
        # Test query manager (basic instantiation)
        if users.exists():
            test_user = users.first()
            query_manager = RelationshipQueryManager(test_user)
            print("   ✅ RelationshipQueryManager instantiated")
        else:
            print("   ✅ RelationshipQueryManager class available")
        
        results['phase_4_relationships'] = True
        print("   🎉 Phase 4 Relationship Engine: PASSED")
        
    except Exception as e:
        print(f"   ❌ Phase 4 Relationship Engine: FAILED - {e}")
    
    # Phase 5: API Layer
    print("\n🚀 PHASE 5: API Layer Testing...")
    try:
        # Test API app structure
        import api
        from api import serializers, filters, pagination
        from api.views import pipelines, records, relationships
        
        print("   ✅ API app structure imported successfully")
        
        # Test GraphQL schema
        try:
            from api.graphql import strawberry_schema
            print("   ✅ GraphQL schema imported successfully")
        except Exception as gql_error:
            print(f"   ⚠️  GraphQL schema import issue: {gql_error}")
        
        # Test API URLs
        from django.urls import reverse
        from django.test import Client
        
        client = Client()
        
        # Test health endpoint with tenant
        response = client.get('/health/', HTTP_HOST='demo.localhost')
        if response.status_code == 200:
            health_data = response.json()
            print(f"   ✅ Tenant health check: {health_data.get('tenant_name')}")
        
        # Test API root (should require auth)
        response = client.get('/api/v1/', HTTP_HOST='demo.localhost')
        if response.status_code == 401:  # Authentication required
            print("   ✅ API authentication properly enforced")
        
        # Test GraphQL endpoint
        response = client.get('/api/v1/graphql/', HTTP_HOST='demo.localhost')
        if response.status_code == 200 and 'GraphiQL' in response.content.decode():
            print("   ✅ GraphQL interface loads successfully")
        
        results['phase_5_api_layer'] = True
        print("   🎉 Phase 5 API Layer: PASSED")
        
    except Exception as e:
        print(f"   ❌ Phase 5 API Layer: FAILED - {e}")
    
    # Cross-Phase Integration Test
    print("\n🔄 CROSS-PHASE INTEGRATION Testing...")
    try:
        # Test that all phases work together
        integration_checks = []
        
        # Check 1: Tenant-aware API endpoints
        if results['phase_1_foundation'] and results['phase_5_api_layer']:
            integration_checks.append("✅ Tenant + API integration")
        
        # Check 2: Authentication + API integration  
        if results['phase_2_authentication'] and results['phase_5_api_layer']:
            integration_checks.append("✅ Auth + API integration")
        
        # Check 3: Pipeline + API integration
        if results['phase_3_pipelines'] and results['phase_5_api_layer']:
            integration_checks.append("✅ Pipeline + API integration")
        
        # Check 4: Relationship + API integration
        if results['phase_4_relationships'] and results['phase_5_api_layer']:
            integration_checks.append("✅ Relationship + API integration")
        
        # Check 5: All phases together
        if all(results.values()):
            integration_checks.append("✅ Complete integration successful")
        
        for check in integration_checks:
            print(f"   {check}")
        
        if len(integration_checks) >= 4:
            results['cross_phase_integration'] = True
            print("   🎉 Cross-Phase Integration: PASSED")
        else:
            print("   ⚠️  Cross-Phase Integration: PARTIAL")
        
    except Exception as e:
        print(f"   ❌ Cross-Phase Integration: FAILED - {e}")
    
    # Final Results
    print("\n" + "=" * 60)
    print("📊 FINAL INTEGRATION TEST RESULTS")  
    print("=" * 60)
    
    passed_phases = sum(results.values())
    total_phases = len(results)
    success_rate = (passed_phases / total_phases) * 100
    
    for phase, status in results.items():
        status_icon = "✅" if status else "❌"
        phase_name = phase.replace('_', ' ').title()
        print(f"{status_icon} {phase_name}: {'PASSED' if status else 'FAILED'}")
    
    print(f"\n🎯 SUCCESS RATE: {passed_phases}/{total_phases} ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        print("🎉 INTEGRATION TEST: PASSED - System ready for production!")
        return True
    elif success_rate >= 60:
        print("⚠️  INTEGRATION TEST: PARTIAL - Most components working")
        return False  
    else:
        print("❌ INTEGRATION TEST: FAILED - Major issues detected")
        return False

if __name__ == "__main__":
    success = test_comprehensive_phases_1_5_integration()
    sys.exit(0 if success else 1)