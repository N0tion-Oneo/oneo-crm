from django.test import TestCase
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context
from tenants.models import Tenant, Domain
from django.contrib.auth.models import User


class TenantModelTest(TestCase):
    def test_tenant_creation(self):
        """Test basic tenant creation"""
        tenant = Tenant.objects.create(
            name="Test Company",
            schema_name="test_company"
        )
        self.assertEqual(tenant.name, "Test Company")
        self.assertEqual(tenant.schema_name, "test_company")
        self.assertTrue(tenant.auto_create_schema)
        self.assertEqual(tenant.max_users, 100)

    def test_domain_creation(self):
        """Test domain association with tenant"""
        tenant = Tenant.objects.create(
            name="Test Company",
            schema_name="test_company"
        )
        domain = Domain.objects.create(
            domain="test.example.com",
            tenant=tenant,
            is_primary=True
        )
        self.assertEqual(domain.tenant, tenant)
        self.assertTrue(domain.is_primary)


class SchemaIsolationTest(TenantTestCase):
    def test_tenant_data_isolation(self):
        """Test that tenant data is properly isolated"""
        # Create two tenants
        tenant1 = Tenant.objects.create(name="Tenant 1", schema_name="tenant1")
        tenant2 = Tenant.objects.create(name="Tenant 2", schema_name="tenant2")
        
        # Create user in tenant1
        with schema_context(tenant1.schema_name):
            user1 = User.objects.create_user(
                username="user1",
                email="user1@tenant1.com"
            )
        
        # Create user in tenant2
        with schema_context(tenant2.schema_name):
            user2 = User.objects.create_user(
                username="user2", 
                email="user2@tenant2.com"
            )
            
            # Verify tenant2 cannot see tenant1's user
            self.assertEqual(User.objects.count(), 1)
            self.assertEqual(User.objects.first().username, "user2")
