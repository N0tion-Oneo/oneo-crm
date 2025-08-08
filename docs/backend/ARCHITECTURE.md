# Oneo CRM Multi-tenant Architecture

## Architecture Overview

Oneo CRM uses a **schema-per-tenant** architecture for complete data isolation between tenants. This approach provides the highest level of security and customization while maintaining performance.

## Key Architectural Decisions

### 1. Schema-per-Tenant Isolation

**Decision**: Each tenant gets its own PostgreSQL schema
**Rationale**: 
- Complete data isolation
- No cross-tenant data leakage risk
- Allows per-tenant customization
- Scales better than shared schema approaches

**Implementation**:
- `django-tenants` library for schema management
- Automatic schema creation on tenant provisioning
- Tenant routing via domain/subdomain

### 2. Domain-based Tenant Resolution

**Decision**: Use domains/subdomains to identify tenants
**Rationale**:
- Clean URL structure
- No tenant ID in URLs
- Natural separation for different customers

**Implementation**:
```
tenant1.localhost:8000 → tenant1 schema
tenant2.localhost:8000 → tenant2 schema
localhost:8000 → public schema (admin)
```

### 3. JSONB for Flexible Data

**Decision**: Use PostgreSQL JSONB fields for customizable data
**Rationale**:
- Pipeline-as-database flexibility
- No schema migrations for field changes
- Rich querying capabilities with GIN indexes

**Implementation**:
- Tenant settings in JSONB
- User metadata in JSONB
- Future pipeline fields in JSONB

### 4. Redis for Tenant-Isolated Caching

**Decision**: Use Redis with tenant-specific cache keys
**Rationale**:
- High performance caching
- Session storage
- Future real-time features support

**Implementation**:
```python
cache_key = f"{tenant_schema}:{key}"
```

### 5. Database Connection Strategy

**Decision**: Single database with multiple schemas
**Rationale**:
- Simpler deployment and management
- Cost-effective for smaller scale
- Easy backup and maintenance

**Trade-offs**:
- Single point of failure (mitigated by HA setup)
- Shared resources (mitigated by connection pooling)

## Data Flow Architecture

```
Request → TenantMainMiddleware → Schema Selection → Application Logic → Response
```

1. **Request Routing**: Domain determines tenant
2. **Schema Context**: Database queries routed to tenant schema
3. **Cache Isolation**: Cache keys prefixed with tenant
4. **Response**: Tenant-specific data returned

## Security Architecture

### Schema Isolation
- PostgreSQL row-level security not needed (schema isolation)
- No cross-schema foreign keys
- Tenant context always maintained

### Permission Model
- Public schema: Admin access only
- Tenant schema: Tenant users only
- No shared user accounts between tenants

### Cache Security
- Tenant-prefixed cache keys
- No cache key collisions possible
- Automatic cache invalidation per tenant

## Scalability Considerations

### Current Scale (Phase 01)
- Supports 100+ tenants per instance
- Single database server
- Single Redis instance

### Future Scale (Phases 6-10)
- Database sharding by tenant groups
- Redis clustering
- Horizontal scaling with load balancers

## Migration Strategy

### Schema Migrations
- Shared apps: Apply to public schema
- Tenant apps: Apply to all tenant schemas
- Custom migration commands handle both

### Data Migrations
- Tenant-specific data migrations
- Bulk operations across all tenants
- Safe rollback procedures

## Monitoring and Observability

### Tenant-level Metrics
- Per-tenant request counts
- Schema-specific query performance
- Tenant resource usage tracking

### System-level Metrics
- Database connection pooling
- Redis memory usage
- Overall system performance

## Backup and Recovery

### Database Backups
- Full database backup (all schemas)
- Per-tenant schema exports possible
- Point-in-time recovery supported

### Redis Persistence
- RDB snapshots for cache persistence
- AOF for cache recovery if needed

## Development Considerations

### Local Development
- Docker Compose for consistency
- Multiple tenant domains via /etc/hosts
- Automated setup scripts

### Testing Strategy
- Schema isolation tests critical
- Multi-tenant test cases
- Performance testing with multiple tenants

## Future Architecture Evolution

### Phase 02-05: Core Features
- Same architecture foundation
- Additional tenant-specific features
- Enhanced permission models

### Phase 06-10: Scale and Production
- Database sharding options
- CDN integration for static assets
- Advanced monitoring and alerting
- High availability configurations

## Technology Stack Rationale

### Django + PostgreSQL
- Mature ecosystem
- Strong ORM with multi-tenant support
- PostgreSQL JSONB for flexibility
- Excellent schema management

### Redis
- High-performance caching
- Session storage
- Future real-time features
- Simple setup and maintenance

### Docker
- Consistent development environment
- Easy deployment
- Service isolation
- Scalability preparation