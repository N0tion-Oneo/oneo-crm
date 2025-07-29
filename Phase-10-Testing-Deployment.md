# Phase 10: Testing & Deployment

## Overview
Comprehensive testing strategy, CI/CD pipeline, production deployment, monitoring, and maintenance procedures for the Oneo CRM system.

## Dependencies
- All previous phases (1-9) completed
- Docker and Kubernetes knowledge
- AWS/GCP infrastructure access
- Testing frameworks configured

## Technical Requirements

### Testing Infrastructure
- **Unit Testing**: Django TestCase, Jest/Vitest
- **Integration Testing**: Django TransactionTestCase, Playwright
- **Load Testing**: Locust, Artillery
- **Security Testing**: OWASP ZAP, Bandit
- **Performance Testing**: Django Debug Toolbar, New Relic

### CI/CD Pipeline
- **Version Control**: Git with feature branch workflow
- **CI Platform**: GitHub Actions or GitLab CI
- **Container Registry**: Docker Hub or AWS ECR
- **Deployment**: Kubernetes with Helm charts

### Production Infrastructure
- **Container Orchestration**: Kubernetes
- **Database**: PostgreSQL with read replicas
- **Cache**: Redis Cluster
- **CDN**: CloudFlare or AWS CloudFront
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack or similar

## Database Schema

### Test Data Management
```sql
-- Test fixtures for multi-tenant scenarios
CREATE TABLE test_fixtures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenant(id),
    fixture_type VARCHAR(50) NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance test metrics
CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_run_id UUID NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10,3) NOT NULL,
    threshold DECIMAL(10,3),
    passed BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Deployment tracking
CREATE TABLE deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(50) NOT NULL,
    environment VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    deployed_by UUID,
    deployed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    rollback_version VARCHAR(50),
    notes TEXT
);
```

## Implementation Steps

### 1. Unit Testing Framework

```python
# tests/conftest.py
import pytest
from django.test import TestCase, TransactionTestCase
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import tenant_context
from channels.testing import WebsocketCommunicator
from unittest.mock import patch, MagicMock

@pytest.fixture
def tenant_factory():
    """Factory for creating test tenants"""
    def _create_tenant(name="test", domain="test.localhost"):
        from apps.tenants.models import Tenant
        tenant = Tenant.objects.create(
            name=name,
            schema_name=name.lower(),
            domain_url=domain
        )
        return tenant
    return _create_tenant

@pytest.fixture
def user_factory():
    """Factory for creating test users"""
    def _create_user(tenant, email="test@example.com", user_type="admin"):
        from apps.authentication.models import CustomUser
        with tenant_context(tenant):
            user = CustomUser.objects.create_user(
                email=email,
                password="testpass123",
                user_type=user_type
            )
            return user
    return _create_user

@pytest.fixture
def pipeline_factory():
    """Factory for creating test pipelines"""
    def _create_pipeline(tenant, user, name="Test Pipeline"):
        from apps.pipelines.models import Pipeline
        with tenant_context(tenant):
            pipeline = Pipeline.objects.create(
                name=name,
                created_by=user,
                schema_definition={
                    "fields": [
                        {
                            "name": "name",
                            "type": "text",
                            "required": True
                        }
                    ]
                }
            )
            return pipeline
    return _create_pipeline

class BaseTenantTestCase(TenantTestCase):
    """Base test case for tenant-aware tests"""
    
    def setUp(self):
        super().setUp()
        self.tenant = self.get_test_tenant()
        self.user = self.create_test_user()
    
    def create_test_user(self):
        from apps.authentication.models import CustomUser
        return CustomUser.objects.create_user(
            email="test@example.com",
            password="testpass123",
            user_type="admin"
        )
```

```python
# tests/test_pipelines.py
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.pipelines.models import Pipeline, Field, Record
from apps.pipelines.validators import FieldValidator
from tests.conftest import BaseTenantTestCase

class PipelineModelTest(BaseTenantTestCase):
    """Test pipeline CRUD operations"""
    
    def test_create_pipeline(self):
        pipeline = Pipeline.objects.create(
            name="Test CRM",
            created_by=self.user,
            schema_definition={
                "fields": [
                    {
                        "name": "company_name",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "revenue",
                        "type": "number",
                        "required": False
                    }
                ]
            }
        )
        
        self.assertEqual(pipeline.name, "Test CRM")
        self.assertEqual(len(pipeline.schema_definition["fields"]), 2)
    
    def test_dynamic_field_creation(self):
        pipeline = Pipeline.objects.create(
            name="Test Pipeline",
            created_by=self.user,
            schema_definition={"fields": []}
        )
        
        field = Field.objects.create(
            pipeline=pipeline,
            name="dynamic_field",
            field_type="text",
            configuration={"required": True}
        )
        
        self.assertEqual(field.pipeline, pipeline)
        self.assertTrue(field.configuration["required"])
    
    def test_record_validation(self):
        pipeline = Pipeline.objects.create(
            name="Validation Test",
            created_by=self.user,
            schema_definition={
                "fields": [
                    {
                        "name": "email",
                        "type": "email",
                        "required": True
                    }
                ]
            }
        )
        
        # Valid record
        record = Record.objects.create(
            pipeline=pipeline,
            data={"email": "test@example.com"},
            created_by=self.user
        )
        self.assertIsNotNone(record.id)
        
        # Invalid record should raise validation error
        with self.assertRaises(ValidationError):
            Record.objects.create(
                pipeline=pipeline,
                data={"email": "invalid-email"},
                created_by=self.user
            )

class FieldValidatorTest(TestCase):
    """Test field validation logic"""
    
    def setUp(self):
        self.validator = FieldValidator()
    
    def test_email_validation(self):
        field_config = {"type": "email", "required": True}
        
        # Valid emails
        self.assertTrue(self.validator.validate_field("test@example.com", field_config))
        
        # Invalid emails
        with self.assertRaises(ValidationError):
            self.validator.validate_field("invalid-email", field_config)
    
    def test_number_validation(self):
        field_config = {"type": "number", "min": 0, "max": 100}
        
        # Valid numbers
        self.assertTrue(self.validator.validate_field(50, field_config))
        
        # Out of range
        with self.assertRaises(ValidationError):
            self.validator.validate_field(150, field_config)
```

### 2. Integration Testing

```python
# tests/test_api_integration.py
import pytest
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.authentication.models import CustomUser
from apps.pipelines.models import Pipeline
from tests.conftest import BaseTenantTestCase

class APIIntegrationTest(BaseTenantTestCase):
    """Test API endpoints integration"""
    
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    def test_pipeline_crud_workflow(self):
        # Create pipeline
        pipeline_data = {
            "name": "Integration Test Pipeline",
            "schema_definition": {
                "fields": [
                    {
                        "name": "title",
                        "type": "text",
                        "required": True
                    }
                ]
            }
        }
        
        response = self.client.post('/api/pipelines/', pipeline_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        pipeline_id = response.data['id']
        
        # Read pipeline
        response = self.client.get(f'/api/pipelines/{pipeline_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Integration Test Pipeline")
        
        # Update pipeline
        update_data = {"name": "Updated Pipeline Name"}
        response = self.client.patch(f'/api/pipelines/{pipeline_id}/', update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Updated Pipeline Name")
        
        # Delete pipeline
        response = self.client.delete(f'/api/pipelines/{pipeline_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    
    def test_record_creation_with_relationships(self):
        # Create two pipelines
        company_pipeline = Pipeline.objects.create(
            name="Companies",
            created_by=self.user,
            schema_definition={"fields": [{"name": "name", "type": "text"}]}
        )
        
        contact_pipeline = Pipeline.objects.create(
            name="Contacts",
            created_by=self.user,
            schema_definition={"fields": [{"name": "name", "type": "text"}]}
        )
        
        # Create company record
        company_data = {"data": {"name": "Acme Corp"}}
        response = self.client.post(
            f'/api/pipelines/{company_pipeline.id}/records/',
            company_data,
            format='json'
        )
        company_id = response.data['id']
        
        # Create contact record with relationship
        contact_data = {
            "data": {"name": "John Doe"},
            "relationships": [
                {
                    "target_pipeline": str(company_pipeline.id),
                    "target_record": company_id,
                    "relationship_type": "works_at"
                }
            ]
        }
        
        response = self.client.post(
            f'/api/pipelines/{contact_pipeline.id}/records/',
            contact_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['relationships']), 1)

class WebSocketIntegrationTest(TransactionTestCase):
    """Test WebSocket real-time features"""
    
    async def test_collaborative_editing(self):
        from channels.testing import WebsocketCommunicator
        from oneo.asgi import application
        
        # Connect two users to same record
        communicator1 = WebsocketCommunicator(
            application,
            f"/ws/records/{self.record.id}/"
        )
        communicator2 = WebsocketCommunicator(
            application,
            f"/ws/records/{self.record.id}/"
        )
        
        connected1, _ = await communicator1.connect()
        connected2, _ = await communicator2.connect()
        
        self.assertTrue(connected1)
        self.assertTrue(connected2)
        
        # User 1 makes an edit
        await communicator1.send_json_to({
            "type": "field_update",
            "field": "name",
            "value": "Updated Name",
            "operation_id": "op-123"
        })
        
        # User 2 should receive the update
        response = await communicator2.receive_json_from()
        self.assertEqual(response["type"], "field_update")
        self.assertEqual(response["field"], "name")
        self.assertEqual(response["value"], "Updated Name")
        
        await communicator1.disconnect()
        await communicator2.disconnect()
```

### 3. Performance Testing

```python
# tests/test_performance.py
import time
import pytest
from django.test import TransactionTestCase
from django.test.utils import override_settings
from django.db import connection
from apps.pipelines.models import Pipeline, Record
from apps.relationships.models import Relationship
from tests.conftest import BaseTenantTestCase

class PerformanceTest(BaseTenantTestCase):
    """Test system performance under load"""
    
    def setUp(self):
        super().setUp()
        self.pipeline = Pipeline.objects.create(
            name="Performance Test",
            created_by=self.user,
            schema_definition={
                "fields": [
                    {"name": "title", "type": "text"},
                    {"name": "description", "type": "textarea"},
                    {"name": "score", "type": "number"}
                ]
            }
        )
    
    def test_bulk_record_creation(self):
        """Test creating 1000 records"""
        start_time = time.time()
        
        records = []
        for i in range(1000):
            records.append(Record(
                pipeline=self.pipeline,
                data={
                    "title": f"Record {i}",
                    "description": f"Description for record {i}",
                    "score": i % 100
                },
                created_by=self.user
            ))
        
        Record.objects.bulk_create(records)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Should create 1000 records in less than 5 seconds
        self.assertLess(creation_time, 5.0)
        self.assertEqual(Record.objects.count(), 1000)
    
    def test_relationship_traversal_performance(self):
        """Test multi-hop relationship queries"""
        # Create pipeline hierarchy: Company -> Department -> Employee
        company_pipeline = Pipeline.objects.create(
            name="Companies", created_by=self.user,
            schema_definition={"fields": [{"name": "name", "type": "text"}]}
        )
        dept_pipeline = Pipeline.objects.create(
            name="Departments", created_by=self.user,
            schema_definition={"fields": [{"name": "name", "type": "text"}]}
        )
        emp_pipeline = Pipeline.objects.create(
            name="Employees", created_by=self.user,
            schema_definition={"fields": [{"name": "name", "type": "text"}]}
        )
        
        # Create test data
        company = Record.objects.create(
            pipeline=company_pipeline,
            data={"name": "Acme Corp"},
            created_by=self.user
        )
        
        departments = []
        for i in range(10):
            dept = Record.objects.create(
                pipeline=dept_pipeline,
                data={"name": f"Department {i}"},
                created_by=self.user
            )
            departments.append(dept)
            
            # Link to company
            Relationship.objects.create(
                source_pipeline=dept_pipeline,
                source_record=dept,
                target_pipeline=company_pipeline,
                target_record=company,
                relationship_type="belongs_to"
            )
        
        # Create employees
        for dept in departments:
            for i in range(50):
                emp = Record.objects.create(
                    pipeline=emp_pipeline,
                    data={"name": f"Employee {i}"},
                    created_by=self.user
                )
                
                Relationship.objects.create(
                    source_pipeline=emp_pipeline,
                    source_record=emp,
                    target_pipeline=dept_pipeline,
                    target_record=dept,
                    relationship_type="works_in"
                )
        
        # Test multi-hop query performance
        start_time = time.time()
        
        # Find all employees for a company (2-hop relationship)
        from apps.relationships.services import RelationshipService
        relationship_service = RelationshipService()
        
        employees = relationship_service.traverse_relationships(
            source_record=company,
            path=["belongs_to", "works_in"],
            max_depth=2
        )
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Should complete in less than 1 second
        self.assertLess(query_time, 1.0)
        self.assertEqual(len(employees), 500)  # 10 depts * 50 employees
    
    def test_concurrent_record_updates(self):
        """Test concurrent record modifications"""
        import threading
        import queue
        
        record = Record.objects.create(
            pipeline=self.pipeline,
            data={"title": "Concurrent Test", "score": 0},
            created_by=self.user
        )
        
        results = queue.Queue()
        
        def update_record(thread_id):
            try:
                for i in range(100):
                    record.refresh_from_db()
                    current_score = record.data.get("score", 0)
                    record.data["score"] = current_score + 1
                    record.save()
                results.put(("success", thread_id))
            except Exception as e:
                results.put(("error", thread_id, str(e)))
        
        # Start 5 concurrent threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=update_record, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check final score (should be 500)
        record.refresh_from_db()
        final_score = record.data.get("score", 0)
        
        # Allow for some race conditions but should be close to 500
        self.assertGreaterEqual(final_score, 450)
        self.assertLessEqual(final_score, 500)
```

### 4. Load Testing with Locust

```python
# tests/locustfile.py
from locust import HttpUser, task, between
import json
import random

class OneoUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login and setup"""
        response = self.client.post("/api/auth/login/", {
            "email": "test@example.com",
            "password": "testpass123"
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.client.headers.update({
                "Authorization": f"Bearer {self.token}"
            })
    
    @task(3)
    def view_pipelines(self):
        """View pipeline list"""
        self.client.get("/api/pipelines/")
    
    @task(5)
    def view_records(self):
        """View records in a pipeline"""
        pipeline_id = random.choice([1, 2, 3, 4, 5])
        self.client.get(f"/api/pipelines/{pipeline_id}/records/")
    
    @task(2)
    def create_record(self):
        """Create a new record"""
        pipeline_id = random.choice([1, 2, 3])
        data = {
            "data": {
                "title": f"Load Test Record {random.randint(1, 1000)}",
                "description": "Created during load test",
                "score": random.randint(1, 100)
            }
        }
        
        self.client.post(
            f"/api/pipelines/{pipeline_id}/records/",
            json=data
        )
    
    @task(1)
    def update_record(self):
        """Update an existing record"""
        pipeline_id = random.choice([1, 2, 3])
        record_id = random.randint(1, 100)
        
        data = {
            "data": {
                "score": random.randint(1, 100)
            }
        }
        
        self.client.patch(
            f"/api/pipelines/{pipeline_id}/records/{record_id}/",
            json=data
        )
    
    @task(1)
    def search_records(self):
        """Search records"""
        query = random.choice(["test", "record", "sample", "data"])
        self.client.get(f"/api/search/?q={query}")

class AdminUser(HttpUser):
    """Simulate admin user behavior"""
    wait_time = between(2, 5)
    weight = 1  # Less frequent than regular users
    
    def on_start(self):
        response = self.client.post("/api/auth/login/", {
            "email": "admin@example.com",
            "password": "adminpass123"
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.client.headers.update({
                "Authorization": f"Bearer {self.token}"
            })
    
    @task(2)
    def view_analytics(self):
        """View system analytics"""
        self.client.get("/api/analytics/dashboard/")
    
    @task(1)
    def manage_users(self):
        """User management operations"""
        self.client.get("/api/admin/users/")
    
    @task(1)
    def system_health(self):
        """Check system health"""
        self.client.get("/api/health/")

# Run with: locust -f tests/locustfile.py --host=http://localhost:8000
```

### 5. CI/CD Pipeline Configuration

```yaml
# .github/workflows/test-and-deploy.yml
name: Test and Deploy

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  POSTGRES_PASSWORD: postgres
  POSTGRES_DB: test_oneo_crm
  REDIS_URL: redis://localhost:6379

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_oneo_crm
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run linting
      run: |
        flake8 apps/
        black --check apps/
        isort --check-only apps/
    
    - name: Run security checks
      run: |
        bandit -r apps/
        safety check
    
    - name: Run tests
      run: |
        python manage.py migrate --settings=oneo.settings.test
        pytest --cov=apps --cov-report=xml --cov-report=html
    
    - name: Upload coverage
      uses: codecov/codecov-action@v4
      with:
        file: ./coverage.xml
    
    - name: Run load tests
      run: |
        python manage.py runserver --settings=oneo.settings.test &
        sleep 10
        locust -f tests/locustfile.py --host=http://localhost:8000 --users=10 --spawn-rate=2 --run-time=60s --headless

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Login to DockerHub
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKERHUB_USERNAME }}
        password: ${{ secrets.DOCKERHUB_TOKEN }}
    
    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        push: true
        tags: oneo-crm/backend:${{ github.sha }},oneo-crm/backend:latest
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    
    steps:
    - name: Deploy to staging
      run: |
        echo "Deploying to staging environment"
        # Add your staging deployment logic here

  deploy-production:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
    - name: Deploy to production
      run: |
        echo "Deploying to production environment"
        # Add your production deployment logic here
```

### 6. Kubernetes Deployment

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: oneo-crm

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: oneo-config
  namespace: oneo-crm
data:
  DJANGO_SETTINGS_MODULE: "oneo.settings.production"
  ALLOWED_HOSTS: "api.oneo-crm.com"
  CORS_ALLOWED_ORIGINS: "https://app.oneo-crm.com"

---
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: oneo-secrets
  namespace: oneo-crm
type: Opaque
data:
  DATABASE_URL: <base64-encoded-database-url>
  REDIS_URL: <base64-encoded-redis-url>
  SECRET_KEY: <base64-encoded-secret-key>
  OPENAI_API_KEY: <base64-encoded-openai-key>

---
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oneo-backend
  namespace: oneo-crm
spec:
  replicas: 3
  selector:
    matchLabels:
      app: oneo-backend
  template:
    metadata:
      labels:
        app: oneo-backend
    spec:
      containers:
      - name: backend
        image: oneo-crm/backend:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: oneo-config
        - secretRef:
            name: oneo-secrets
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready/
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"

---
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: oneo-backend-service
  namespace: oneo-crm
spec:
  selector:
    app: oneo-backend
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP

---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: oneo-ingress
  namespace: oneo-crm
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/websocket-services: "oneo-backend-service"
spec:
  tls:
  - hosts:
    - api.oneo-crm.com
    secretName: oneo-tls
  rules:
  - host: api.oneo-crm.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: oneo-backend-service
            port:
              number: 80
```

### 7. Monitoring & Observability

```python
# monitoring/health_checks.py
from django.http import JsonResponse
from django.views import View
from django.db import connection
from django.core.cache import cache
import redis
import time

class HealthCheckView(View):
    """Comprehensive health check endpoint"""
    
    def get(self, request):
        checks = {
            "database": self._check_database(),
            "redis": self._check_redis(),
            "disk_space": self._check_disk_space(),
            "memory": self._check_memory()
        }
        
        overall_status = "healthy" if all(
            check["status"] == "healthy" for check in checks.values()
        ) else "unhealthy"
        
        response_data = {
            "status": overall_status,
            "timestamp": time.time(),
            "checks": checks
        }
        
        status_code = 200 if overall_status == "healthy" else 503
        return JsonResponse(response_data, status=status_code)
    
    def _check_database(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return {"status": "healthy", "message": "Database connection OK"}
        except Exception as e:
            return {"status": "unhealthy", "message": f"Database error: {str(e)}"}
    
    def _check_redis(self):
        try:
            cache.set("health_check", "ok", timeout=1)
            result = cache.get("health_check")
            if result == "ok":
                return {"status": "healthy", "message": "Redis connection OK"}
            else:
                return {"status": "unhealthy", "message": "Redis test failed"}
        except Exception as e:
            return {"status": "unhealthy", "message": f"Redis error: {str(e)}"}
    
    def _check_disk_space(self):
        import shutil
        try:
            _, _, free = shutil.disk_usage("/")
            free_gb = free // (1024**3)
            
            if free_gb > 10:  # More than 10GB free
                return {"status": "healthy", "message": f"{free_gb}GB free"}
            else:
                return {"status": "unhealthy", "message": f"Low disk space: {free_gb}GB"}
        except Exception as e:
            return {"status": "unhealthy", "message": f"Disk check error: {str(e)}"}
    
    def _check_memory(self):
        import psutil
        try:
            memory = psutil.virtual_memory()
            if memory.percent < 90:
                return {"status": "healthy", "message": f"Memory usage: {memory.percent}%"}
            else:
                return {"status": "unhealthy", "message": f"High memory usage: {memory.percent}%"}
        except Exception as e:
            return {"status": "unhealthy", "message": f"Memory check error: {str(e)}"}

class ReadinessCheckView(View):
    """Readiness check for Kubernetes"""
    
    def get(self, request):
        # Check if all critical services are ready
        checks = [
            self._check_database_migrations(),
            self._check_required_services()
        ]
        
        if all(checks):
            return JsonResponse({"status": "ready"}, status=200)
        else:
            return JsonResponse({"status": "not_ready"}, status=503)
    
    def _check_database_migrations(self):
        from django.db.migrations.executor import MigrationExecutor
        try:
            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            return len(plan) == 0  # No pending migrations
        except:
            return False
    
    def _check_required_services(self):
        # Add checks for required external services
        return True
```

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'oneo-backend'
    static_configs:
      - targets: ['oneo-backend-service:80']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx-exporter:9113']
```

### 8. Backup and Recovery

```python
# management/commands/backup_system.py
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
import boto3
import os
import gzip
import datetime

class Command(BaseCommand):
    help = 'Create system backup including database and media files'
    
    def add_arguments(self, parser):
        parser.add_argument('--s3-bucket', type=str, help='S3 bucket for backup storage')
        parser.add_argument('--compress', action='store_true', help='Compress backup files')
    
    def handle(self, *args, **options):
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f'/tmp/backup_{timestamp}'
        os.makedirs(backup_dir, exist_ok=True)
        
        try:
            # Backup database
            self.stdout.write('Creating database backup...')
            db_backup_file = os.path.join(backup_dir, 'database.sql')
            
            with open(db_backup_file, 'w') as f:
                call_command('dbbackup', '--output-filename', db_backup_file)
            
            # Backup media files
            self.stdout.write('Backing up media files...')
            media_backup_file = os.path.join(backup_dir, 'media.tar.gz')
            os.system(f'tar -czf {media_backup_file} {settings.MEDIA_ROOT}')
            
            # Compress if requested
            if options['compress']:
                self._compress_files(backup_dir)
            
            # Upload to S3 if bucket specified
            if options['s3_bucket']:
                self._upload_to_s3(backup_dir, options['s3_bucket'], timestamp)
            
            self.stdout.write(
                self.style.SUCCESS(f'Backup completed: {backup_dir}')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Backup failed: {str(e)}')
            )
    
    def _compress_files(self, backup_dir):
        for filename in os.listdir(backup_dir):
            filepath = os.path.join(backup_dir, filename)
            if not filename.endswith('.gz'):
                with open(filepath, 'rb') as f_in:
                    with gzip.open(f'{filepath}.gz', 'wb') as f_out:
                        f_out.writelines(f_in)
                os.remove(filepath)
    
    def _upload_to_s3(self, backup_dir, bucket_name, timestamp):
        s3_client = boto3.client('s3')
        
        for filename in os.listdir(backup_dir):
            filepath = os.path.join(backup_dir, filename)
            s3_key = f'backups/{timestamp}/{filename}'
            
            self.stdout.write(f'Uploading {filename} to S3...')
            s3_client.upload_file(filepath, bucket_name, s3_key)
```

## Testing Strategy

### Unit Tests
- **Coverage Target**: 90%+ code coverage
- **Test Types**: Models, views, services, utilities
- **Mocking**: External APIs, AI services, email services
- **Fixtures**: Reusable test data for complex scenarios

### Integration Tests
- **API Testing**: All REST and GraphQL endpoints
- **WebSocket Testing**: Real-time collaboration features
- **Database Testing**: Multi-tenant isolation, relationship queries
- **Authentication Testing**: RBAC, permission inheritance

### Performance Tests
- **Load Testing**: 1000+ concurrent users
- **Stress Testing**: Resource exhaustion scenarios
- **Volume Testing**: Large datasets (100k+ records)
- **Endurance Testing**: 24-hour continuous operation

### Security Tests
- **Penetration Testing**: OWASP Top 10 vulnerabilities
- **Authentication Testing**: JWT security, session management
- **Authorization Testing**: RBAC bypass attempts
- **Input Validation**: SQL injection, XSS prevention

## Deployment Strategy

### Blue-Green Deployment
1. **Preparation**: Deploy new version to green environment
2. **Testing**: Run smoke tests on green environment
3. **Switch**: Update load balancer to point to green
4. **Verification**: Monitor health metrics
5. **Rollback**: Keep blue environment for instant rollback

### Database Migrations
- **Zero-downtime**: Backward-compatible migrations only
- **Multi-step**: Break complex changes into multiple releases
- **Rollback**: Always include rollback scripts
- **Testing**: Test migrations on production data copies

### Monitoring & Alerting
- **Application Metrics**: Response times, error rates
- **Infrastructure Metrics**: CPU, memory, disk usage
- **Business Metrics**: User activity, system utilization
- **Alerting**: PagerDuty integration for critical issues

## Todo Checklist

### Testing Setup
- [ ] Configure Django test settings
- [ ] Set up test database with multi-tenant support
- [ ] Create test fixtures for common scenarios
- [ ] Configure coverage reporting
- [ ] Set up continuous integration pipeline

### Unit Testing
- [ ] Write tests for all model classes
- [ ] Test field validation logic
- [ ] Test permission and RBAC systems
- [ ] Test AI service integrations (mocked)
- [ ] Test relationship traversal logic

### Integration Testing
- [ ] Test all API endpoints
- [ ] Test WebSocket real-time features
- [ ] Test email and notification systems
- [ ] Test multi-tenant isolation
- [ ] Test third-party integrations

### Performance Testing
- [ ] Set up load testing with Locust
- [ ] Test concurrent user scenarios
- [ ] Test large dataset performance
- [ ] Test relationship query optimization
- [ ] Profile database query performance

### Security Testing
- [ ] Run OWASP security scans
- [ ] Test authentication and authorization
- [ ] Test input validation and sanitization
- [ ] Test multi-tenant data isolation
- [ ] Perform penetration testing

### Deployment Infrastructure
- [ ] Create Docker containers
- [ ] Set up Kubernetes manifests
- [ ] Configure CI/CD pipelines
- [ ] Set up monitoring and alerting
- [ ] Create backup and recovery procedures

### Production Readiness
- [ ] Configure production database
- [ ] Set up Redis cluster
- [ ] Configure CDN and static files
- [ ] Set up SSL certificates
- [ ] Configure domain and DNS

### Monitoring & Maintenance
- [ ] Set up application monitoring
- [ ] Configure log aggregation
- [ ] Create health check endpoints
- [ ] Set up automated backups
- [ ] Create runbooks for common issues

## Success Metrics

### Performance Targets
- **Response Time**: < 200ms for 95% of API requests
- **Throughput**: Support 1000+ concurrent users
- **Uptime**: 99.9% availability
- **Database**: < 100ms for complex relationship queries

### Quality Metrics
- **Test Coverage**: > 90% code coverage
- **Bug Rate**: < 1 critical bug per release
- **Security**: Zero high-severity vulnerabilities
- **Documentation**: 100% API endpoint documentation

### Operational Metrics
- **Deployment**: < 5 minute deployment time
- **Recovery**: < 15 minute recovery from failures
- **Backup**: Daily automated backups with weekly tests
- **Monitoring**: < 1 minute alert response time

This comprehensive testing and deployment strategy ensures the Oneo CRM system is production-ready, scalable, and maintainable.