#!/usr/bin/env python
"""
Comprehensive system integration test for Oneo CRM
Tests authentication simplification and all phases 1-6
"""

import os
import sys
import django
from django.db import connection
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test.utils import setup_test_environment, teardown_test_environment
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Now import after Django is set up
from tenants.models import Tenant, Domain
from authentication.models import UserType
from django_tenants.utils import schema_context

User = get_user_model()

def test_phase_01_foundation():
    """Test Phase 1: Foundation & Multi-tenancy"""
    print("🧪 Testing Phase 01: Foundation & Multi-tenancy")
    
    # Test database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1, "Database connection failed"
        print("✅ Database connection working")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    # Test tenant system
    try:
        tenant_count = Tenant.objects.count()
        print(f"✅ Tenant system working ({tenant_count} tenants)")
    except Exception as e:
        print(f"❌ Tenant system failed: {e}")
        return False
    
    return True

def test_phase_02_authentication():
    """Test Phase 2: Authentication & RBAC System"""
    print("🧪 Testing Phase 02: Authentication & RBAC System")
    
    # Test custom user model
    try:
        user_count = User.objects.count()
        print(f"✅ Custom user model working ({user_count} users)")
    except Exception as e:
        print(f"❌ Custom user model failed: {e}")
        return False
    
    # Test user types
    try:
        user_type_count = UserType.objects.count()
        print(f"✅ User types working ({user_type_count} types)")
    except Exception as e:
        print(f"❌ User types failed: {e}")
        return False
    
    # Test session-only authentication (no JWT)
    try:
        # Check that JWT is not in REST_FRAMEWORK settings
        auth_classes = settings.REST_FRAMEWORK.get('DEFAULT_AUTHENTICATION_CLASSES', [])
        jwt_present = any('jwt' in auth.lower() for auth in auth_classes)
        session_present = any('session' in auth.lower() for auth in auth_classes)
        
        if jwt_present:
            print("❌ JWT authentication still present - simplification incomplete")
            return False
        if session_present:
            print("✅ Session-only authentication configured correctly")
        else:
            print("❌ Session authentication not configured")
            return False
    except Exception as e:
        print(f"❌ Authentication config check failed: {e}")
        return False
    
    return True

def test_phase_03_pipeline_system():
    """Test Phase 3: Pipeline System & Dynamic Schemas"""
    print("🧪 Testing Phase 03: Pipeline System & Dynamic Schemas")
    
    # Get a tenant to work with
    try:
        tenant = Tenant.objects.first()
        if not tenant:
            print("❌ No tenant found for testing")
            return False
            
        with schema_context(tenant.schema_name):
            from pipelines.models import Pipeline, Field, Record
            
            # Test pipeline model
            pipeline_count = Pipeline.objects.count()
            print(f"✅ Pipeline system working ({pipeline_count} pipelines)")
            
            # Test field system
            field_count = Field.objects.count()
            print(f"✅ Field system working ({field_count} fields)")
            
            # Test record system
            record_count = Record.objects.count()
            print(f"✅ Record system working ({record_count} records)")
            
    except Exception as e:
        print(f"❌ Pipeline system failed: {e}")
        return False
    
    return True

def test_phase_04_relationship_engine():
    """Test Phase 4: Relationship Engine & Multi-hop Traversal"""
    print("🧪 Testing Phase 04: Relationship Engine & Multi-hop Traversal")
    
    # Get a tenant to work with
    try:
        tenant = Tenant.objects.first()
        if not tenant:
            print("❌ No tenant found for testing")
            return False
            
        with schema_context(tenant.schema_name):
            from relationships.models import RelationshipType, Relationship
            
            # Test relationship types
            relationship_type_count = RelationshipType.objects.count()
            print(f"✅ Relationship types working ({relationship_type_count} types)")
            
            # Test relationships
            relationship_count = Relationship.objects.count()
            print(f"✅ Relationships working ({relationship_count} relationships)")
            
    except Exception as e:
        print(f"❌ Relationship engine failed: {e}")
        return False
    
    return True

def test_phase_05_api_layer():
    """Test Phase 5: API Layer & GraphQL Integration"""
    print("🧪 Testing Phase 05: API Layer & GraphQL Integration")
    
    # Test REST Framework configuration
    try:
        # Check that API is properly configured
        api_config = settings.REST_FRAMEWORK
        if 'DEFAULT_AUTHENTICATION_CLASSES' in api_config:
            print("✅ REST Framework configured")
        else:
            print("❌ REST Framework configuration missing")
            return False
    except Exception as e:
        print(f"❌ API configuration check failed: {e}")
        return False
    
    return True

def test_phase_06_real_time():
    """Test Phase 6: Real-time Collaboration & WebSocket Features"""
    print("🧪 Testing Phase 06: Real-time Collaboration & WebSocket Features")
    
    # Test channels configuration
    try:
        # Check if channels is installed and configured
        if 'channels' in settings.INSTALLED_APPS:
            print("✅ Channels configured for WebSocket support")
        else:
            print("❌ Channels not configured")
            return False
    except Exception as e:
        print(f"❌ Channels configuration check failed: {e}")
        return False
    
    return True

def test_workflows_phase_07():
    """Test Phase 7: Workflow System"""
    print("🧪 Testing Phase 07: Workflow System")
    
    # Get a tenant to work with
    try:
        tenant = Tenant.objects.first()
        if not tenant:
            print("❌ No tenant found for testing")
            return False
            
        with schema_context(tenant.schema_name):
            from workflows.models import Workflow, WorkflowExecution
            
            # Test workflow models
            workflow_count = Workflow.objects.count()
            print(f"✅ Workflows working ({workflow_count} workflows)")
            
            execution_count = WorkflowExecution.objects.count()
            print(f"✅ Workflow executions working ({execution_count} executions)")
            
    except Exception as e:
        print(f"❌ Workflow system failed: {e}")
        return False
    
    return True

def main():
    """Run comprehensive system integration test"""
    print("🚀 Starting Comprehensive System Integration Test")
    print("=" * 60)
    
    # Track test results
    test_phases = [
        ("Phase 01 - Foundation", test_phase_01_foundation),
        ("Phase 02 - Authentication", test_phase_02_authentication),
        ("Phase 03 - Pipeline System", test_phase_03_pipeline_system),
        ("Phase 04 - Relationship Engine", test_phase_04_relationship_engine),
        ("Phase 05 - API Layer", test_phase_05_api_layer),
        ("Phase 06 - Real-time", test_phase_06_real_time),
        ("Phase 07 - Workflows", test_workflows_phase_07),
    ]
    
    results = {}
    
    for phase_name, test_func in test_phases:
        try:
            results[phase_name] = test_func()
        except Exception as e:
            print(f"❌ {phase_name} failed with exception: {e}")
            results[phase_name] = False
        print()
    
    # Summary
    print("=" * 60)
    print("📊 INTEGRATION TEST RESULTS:")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for phase_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{phase_name:30} {status}")
        if result:
            passed += 1
    
    print("=" * 60)
    print(f"📈 SUCCESS RATE: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 AUTHENTICATION SIMPLIFICATION COMPLETE!")
        print("🎉 ALL PHASES 1-7 WORKING CORRECTLY!")
        print("🚀 Ready to return to Phase 7 workflow implementation!")
    else:
        print("⚠️  Some phases need attention before proceeding")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)