# Oneo CRM API Documentation

## Overview

The Oneo CRM API provides a RESTful interface for managing multi-tenant CRM operations. All API endpoints are tenant-aware and require proper domain routing.

## Base URLs

- **Development**: `http://localhost:8000`
- **Production**: `https://your-domain.com`

## Authentication

All tenant-specific API calls require authentication. Public schema endpoints (tenant management) require admin privileges.

### Tenant Context

API requests are automatically routed to the correct tenant based on the domain:
- `tenant1.localhost:8000/api/` → Routes to tenant1 schema
- `tenant2.localhost:8000/api/` → Routes to tenant2 schema
- `localhost:8000/admin/` → Routes to public schema (tenant management)

## API Endpoints (Planned)

### Public Schema Endpoints
- `GET /health/` - System health check
- `GET /admin/` - Django admin interface for tenant management

### Tenant Schema Endpoints  
- `GET /health/` - Tenant-specific health check
- `GET /api/v1/` - API root (future implementation)

## Response Format

All API responses follow a consistent format:

```json
{
  "success": true,
  "data": {},
  "message": "Success message",
  "errors": null,
  "tenant": "tenant_schema_name"
}
```

## Error Handling

Standard HTTP status codes are used:
- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden (cross-tenant access)
- `404` - Not Found
- `500` - Internal Server Error

## Rate Limiting

API rate limiting will be implemented per tenant in future phases.

## Versioning

API versioning follows the pattern `/api/v{version}/` (e.g., `/api/v1/`).

## Future Endpoints

Additional endpoints will be added in subsequent phases:
- Phase 02: Authentication endpoints
- Phase 03: Pipeline management endpoints
- Phase 04: Relationship management endpoints
- Phase 05: Complete REST/GraphQL API layer