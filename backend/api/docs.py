from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.openapi import AutoSchema
from rest_framework import serializers
from django.utils.decorators import method_decorator
from typing import Dict, Any, List
import json


class CustomAutoSchema(AutoSchema):
    """
    Enhanced AutoSchema for better API documentation generation.
    """
    
    def get_operation_id(self, path, method):
        """Generate more descriptive operation IDs."""
        # Extract meaningful parts from path
        path_parts = [part for part in path.split('/') if part and not part.startswith('{')]
        
        # Use view name if available
        if hasattr(self.view, '__class__'):
            view_name = self.view.__class__.__name__.replace('ViewSet', '').replace('View', '')
            
            if method.lower() == 'get' and path.endswith('/'):
                operation = 'list'
            elif method.lower() == 'get':
                operation = 'retrieve'
            elif method.lower() == 'post':
                operation = 'create'
            elif method.lower() == 'put':
                operation = 'update'
            elif method.lower() == 'patch':
                operation = 'partial_update'
            elif method.lower() == 'delete':
                operation = 'destroy'
            else:
                operation = method.lower()
            
            return f"{view_name.lower()}_{operation}"
        
        return super().get_operation_id(path, method)
    
    def get_tags(self):
        """Generate tags from view class."""
        if hasattr(self.view, '__class__'):
            view_name = self.view.__class__.__name__
            if 'Pipeline' in view_name:
                return ['Pipelines']
            elif 'Record' in view_name:
                return ['Records']
            elif 'Relationship' in view_name:
                return ['Relationships']
            elif 'User' in view_name:
                return ['Users']
            elif 'Auth' in view_name:
                return ['Authentication']
        
        return super().get_tags()


# Common parameter definitions
PAGINATION_PARAMETERS = [
    OpenApiParameter(
        name='page',
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description='Page number for pagination'
    ),
    OpenApiParameter(
        name='page_size',
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description='Number of items per page (max 1000)'
    ),
]

SEARCH_PARAMETERS = [
    OpenApiParameter(
        name='search',
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description='Search query string'
    ),
]

FILTER_PARAMETERS = [
    OpenApiParameter(
        name='status',
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description='Filter by status'
    ),
    OpenApiParameter(
        name='created_at__gte',
        type=OpenApiTypes.DATETIME,
        location=OpenApiParameter.QUERY,
        description='Filter by creation date (greater than or equal)'
    ),
    OpenApiParameter(
        name='updated_at__gte',
        type=OpenApiTypes.DATETIME,
        location=OpenApiParameter.QUERY,
        description='Filter by update date (greater than or equal)'
    ),
]


# Schema decorators for common endpoint patterns

def pipeline_list_schema():
    """Schema decorator for pipeline list endpoint."""
    return extend_schema(
        summary="List Pipelines",
        description="Retrieve a paginated list of pipelines accessible to the current user.",
        parameters=PAGINATION_PARAMETERS + SEARCH_PARAMETERS + [
            OpenApiParameter(
                name='pipeline_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by pipeline type (crm, ats, cms, custom)'
            ),
            OpenApiParameter(
                name='is_active',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter by active status'
            ),
        ],
        tags=['Pipelines'],
    )


def pipeline_detail_schema():
    """Schema decorator for pipeline detail endpoint."""
    return extend_schema(
        summary="Get Pipeline",
        description="Retrieve detailed information about a specific pipeline.",
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Pipeline ID'
            ),
        ],
        tags=['Pipelines'],
    )


def record_list_schema():
    """Schema decorator for record list endpoint."""
    return extend_schema(
        summary="List Records",
        description="Retrieve a paginated list of records from a specific pipeline.",
        parameters=PAGINATION_PARAMETERS + SEARCH_PARAMETERS + FILTER_PARAMETERS + [
            OpenApiParameter(
                name='pipeline_pk',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Pipeline ID'
            ),
        ],
        tags=['Records'],
    )


def record_create_schema():
    """Schema decorator for record creation endpoint."""
    return extend_schema(
        summary="Create Record",
        description="Create a new record in the specified pipeline.",
        parameters=[
            OpenApiParameter(
                name='pipeline_pk',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Pipeline ID'
            ),
        ],
        tags=['Records'],
    )


def global_search_schema():
    """Schema decorator for global search endpoint."""
    return extend_schema(
        summary="Global Search",
        description="Search across all accessible records and pipelines.",
        parameters=[
            OpenApiParameter(
                name='q',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search query string',
                required=True
            ),
            OpenApiParameter(
                name='pipeline_ids',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Comma-separated list of pipeline IDs to search within'
            ),
            OpenApiParameter(
                name='limit',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Maximum number of results to return (default: 50)'
            ),
        ],
        tags=['Search'],
    )


# Response schema definitions

class ErrorResponseSerializer(serializers.Serializer):
    """Standard error response format."""
    error = serializers.CharField(help_text="Error message")
    code = serializers.CharField(help_text="Error code", required=False)
    details = serializers.DictField(help_text="Additional error details", required=False)


class PaginationResponseSerializer(serializers.Serializer):
    """Standard pagination response format."""
    count = serializers.IntegerField(help_text="Total number of items")
    next = serializers.URLField(help_text="URL for next page", allow_null=True)
    previous = serializers.URLField(help_text="URL for previous page", allow_null=True)
    results = serializers.ListField(help_text="List of items for current page")


class SuccessResponseSerializer(serializers.Serializer):
    """Standard success response format."""
    success = serializers.BooleanField(help_text="Operation success status")
    message = serializers.CharField(help_text="Success message", required=False)
    data = serializers.DictField(help_text="Response data", required=False)


# GraphQL documentation helpers

def generate_graphql_docs() -> Dict[str, Any]:
    """
    Generate documentation for GraphQL schema.
    """
    from api.graphql.strawberry_schema import schema
    
    # Get schema introspection
    introspection_query = """
    query IntrospectionQuery {
        __schema {
            queryType { name }
            mutationType { name }
            subscriptionType { name }
            types {
                ...FullType
            }
        }
    }
    
    fragment FullType on __Type {
        kind
        name
        description
        fields(includeDeprecated: true) {
            name
            description
            args {
                ...InputValue
            }
            type {
                ...TypeRef
            }
            isDeprecated
            deprecationReason
        }
        inputFields {
            ...InputValue
        }
        interfaces {
            ...TypeRef
        }
        enumValues(includeDeprecated: true) {
            name
            description
            isDeprecated
            deprecationReason
        }
        possibleTypes {
            ...TypeRef
        }
    }
    
    fragment InputValue on __InputValue {
        name
        description
        type { ...TypeRef }
        defaultValue
    }
    
    fragment TypeRef on __Type {
        kind
        name
        ofType {
            kind
            name
            ofType {
                kind
                name
                ofType {
                    kind
                    name
                    ofType {
                        kind
                        name
                        ofType {
                            kind
                            name
                            ofType {
                                kind
                                name
                                ofType {
                                    kind
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    try:
        result = schema.execute_sync(introspection_query)
        return {
            'schema': result.data,
            'queries': _extract_queries(result.data),
            'mutations': _extract_mutations(result.data),
            'subscriptions': _extract_subscriptions(result.data),
        }
    except Exception as e:
        return {'error': str(e)}


def _extract_queries(schema_data: Dict) -> List[Dict]:
    """Extract query operations from schema."""
    queries = []
    query_type = schema_data.get('__schema', {}).get('queryType', {})
    
    if query_type:
        query_type_name = query_type.get('name')
        # Find the query type in types
        for type_def in schema_data.get('__schema', {}).get('types', []):
            if type_def.get('name') == query_type_name:
                for field in type_def.get('fields', []):
                    queries.append({
                        'name': field.get('name'),
                        'description': field.get('description'),
                        'args': field.get('args', []),
                        'type': field.get('type', {}),
                    })
                break
    
    return queries


def _extract_mutations(schema_data: Dict) -> List[Dict]:
    """Extract mutation operations from schema."""
    mutations = []
    mutation_type = schema_data.get('__schema', {}).get('mutationType', {})
    
    if mutation_type:
        mutation_type_name = mutation_type.get('name')
        for type_def in schema_data.get('__schema', {}).get('types', []):
            if type_def.get('name') == mutation_type_name:
                for field in type_def.get('fields', []):
                    mutations.append({
                        'name': field.get('name'),
                        'description': field.get('description'),
                        'args': field.get('args', []),
                        'type': field.get('type', {}),
                    })
                break
    
    return mutations


def _extract_subscriptions(schema_data: Dict) -> List[Dict]:
    """Extract subscription operations from schema."""
    subscriptions = []
    subscription_type = schema_data.get('__schema', {}).get('subscriptionType', {})
    
    if subscription_type:
        subscription_type_name = subscription_type.get('name')
        for type_def in schema_data.get('__schema', {}).get('types', []):
            if type_def.get('name') == subscription_type_name:
                for field in type_def.get('fields', []):
                    subscriptions.append({
                        'name': field.get('name'),
                        'description': field.get('description'),
                        'args': field.get('args', []),
                        'type': field.get('type', {}),
                    })
                break
    
    return subscriptions


# Example usage documentation

EXAMPLE_REQUESTS = {
    'create_pipeline': {
        'description': 'Create a new CRM pipeline',
        'request': {
            'name': 'Sales Pipeline',
            'description': 'Track sales opportunities',
            'pipeline_type': 'crm',
            'icon': 'dollar-sign',
            'color': '#10B981'
        },
        'response': {
            'id': 'uuid-here',
            'name': 'Sales Pipeline',
            'slug': 'sales-pipeline',
            'created_at': '2025-01-01T00:00:00Z'
        }
    },
    'create_record': {
        'description': 'Create a new record in a pipeline',
        'request': {
            'data': {
                'company_name': 'Acme Corp',
                'contact_email': 'john@acme.com',
                'deal_value': 50000,
                'status': 'qualified'
            }
        },
        'response': {
            'id': 'uuid-here',
            'title': 'Acme Corp',
            'data': {
                'company_name': 'Acme Corp',
                'contact_email': 'john@acme.com',
                'deal_value': 50000,
                'status': 'qualified'
            },
            'created_at': '2025-01-01T00:00:00Z'
        }
    },
    'graphql_query': {
        'description': 'GraphQL query to fetch pipelines and records',
        'query': '''
        query GetPipelinesWithRecords {
            pipelines {
                id
                name
                recordCount
                records(limit: 10) {
                    id
                    title
                    data
                    createdAt
                }
            }
        }
        ''',
        'response': {
            'data': {
                'pipelines': [
                    {
                        'id': 'uuid-here',
                        'name': 'Sales Pipeline',
                        'recordCount': 25,
                        'records': [
                            {
                                'id': 'uuid-here',
                                'title': 'Acme Corp',
                                'data': {'company_name': 'Acme Corp'},
                                'createdAt': '2025-01-01T00:00:00Z'
                            }
                        ]
                    }
                ]
            }
        }
    }
}


def get_api_documentation_context() -> Dict[str, Any]:
    """
    Generate complete API documentation context.
    """
    return {
        'rest_api': {
            'base_url': '/api/v1/',
            'authentication': {
                'methods': ['JWT Token', 'Session Auth', 'API Key'],
                'headers': {
                    'Authorization': 'Bearer <token>',
                    'X-API-Key': '<api_key>'
                }
            },
            'rate_limits': {
                'authenticated': '1000 requests/hour',
                'burst': '60 requests/minute',
                'api_key': '10000 requests/hour'
            }
        },
        'graphql_api': {
            'endpoint': '/graphql/',
            'subscriptions_endpoint': '/ws/graphql/',
            'introspection': generate_graphql_docs()
        },
        'websocket_api': {
            'endpoints': {
                'sse': '/ws/sse/',
                'graphql': '/ws/graphql/',
                'pipelines': '/ws/pipelines/<pipeline_id>/',
                'records': '/ws/records/<record_id>/'
            },
            'authentication': 'JWT token in query parameter or Authorization header'
        },
        'examples': EXAMPLE_REQUESTS
    }