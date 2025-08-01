from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from drf_spectacular.utils import extend_schema
from drf_spectacular.openapi import AutoSchema
from api.docs import get_api_documentation_context, generate_graphql_docs
import json


@extend_schema(
    summary="API Documentation",
    description="Interactive API documentation with examples and testing capabilities.",
    tags=['Documentation']
)
@api_view(['GET'])
@permission_classes([AllowAny])
def api_docs_view(request):
    """
    Serve comprehensive API documentation.
    """
    context = get_api_documentation_context()
    
    if request.accepted_renderer.format == 'json':
        return Response(context)
    
    # Render HTML documentation
    return render(request, 'api/docs.html', context)


@extend_schema(
    summary="OpenAPI Schema",
    description="Get the OpenAPI 3.0 schema specification for the REST API.",
    tags=['Documentation']
)
@api_view(['GET'])
@permission_classes([AllowAny])
def openapi_schema_view(request):
    """
    Return OpenAPI schema for the API.
    """
    from drf_spectacular.openapi import AutoSchema
    from django.urls import get_resolver
    
    # This would be handled by drf-spectacular's built-in view
    # but we can customize it here if needed
    return Response({
        'message': 'Use /api/schema/ endpoint for OpenAPI schema'
    })


@extend_schema(
    summary="GraphQL Schema Documentation",
    description="Get GraphQL schema introspection and documentation.",
    tags=['Documentation', 'GraphQL']
)
@api_view(['GET'])
@permission_classes([AllowAny])
def graphql_docs_view(request):
    """
    Return GraphQL schema documentation.
    """
    docs = generate_graphql_docs()
    return Response(docs)


@extend_schema(
    summary="API Health Check",
    description="Check API health and availability of services.",
    tags=['Monitoring']
)
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check_view(request):
    """
    API health check endpoint.
    """
    from django.db import connection
    from django.core.cache import cache
    from channels.layers import get_channel_layer
    import redis
    
    health_status = {
        'status': 'healthy',
        'timestamp': request.META.get('HTTP_DATE', ''),
        'services': {}
    }
    
    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['services']['database'] = 'healthy'
    except Exception as e:
        health_status['services']['database'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'degraded'
    
    # Check cache
    try:
        cache.set('health_check', 'ok', 30)
        cache.get('health_check')
        health_status['services']['cache'] = 'healthy'
    except Exception as e:
        health_status['services']['cache'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'degraded'
    
    # Check Redis/Channels
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            health_status['services']['websockets'] = 'healthy'
        else:
            health_status['services']['websockets'] = 'not configured'
    except Exception as e:
        health_status['services']['websockets'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'degraded'
    
    # Set HTTP status based on health
    http_status = status.HTTP_200_OK if health_status['status'] == 'healthy' else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return Response(health_status, status=http_status)


@extend_schema(
    summary="API Metrics",
    description="Get API usage metrics and performance statistics.",
    tags=['Monitoring']
)
@api_view(['GET'])
@permission_classes([AllowAny])  # You might want to restrict this
def metrics_view(request):
    """
    Return API metrics for monitoring.
    """
    from django.core.cache import cache
    from django.contrib.auth import get_user_model
    from pipelines.models import Pipeline, Record
    
    User = get_user_model()
    
    # Basic metrics
    metrics = {
        'api': {
            'version': '1.0',
            'uptime': '24h',  # You'd calculate this based on start time
        },
        'database': {
            'users': User.objects.count(),
            'pipelines': Pipeline.objects.filter(is_active=True).count(),
            'records': Record.objects.filter(is_deleted=False).count(),
        },
        'cache': {
            'hit_rate': '95%',  # You'd get this from cache stats
        }
    }
    
    return Response(metrics)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_examples_view(request):
    """
    Return API usage examples and code samples.
    """
    examples = {
        'rest_api': {
            'authentication': {
                'curl': '''
                # Using JWT token
                curl -H "Authorization: Bearer <your-jwt-token>" \\
                     https://api.example.com/api/v1/pipelines/
                
                # Using API key
                curl -H "X-API-Key: <your-api-key>" \\
                     https://api.example.com/api/v1/pipelines/
                ''',
                'python': '''
                import requests
                
                # JWT authentication
                headers = {'Authorization': 'Bearer YOUR_JWT_TOKEN'}
                response = requests.get('https://api.example.com/api/v1/pipelines/', headers=headers)
                
                # API key authentication
                headers = {'X-API-Key': 'YOUR_API_KEY'}
                response = requests.get('https://api.example.com/api/v1/pipelines/', headers=headers)
                ''',
                'javascript': '''
                // Using fetch with JWT
                const response = await fetch('https://api.example.com/api/v1/pipelines/', {
                    headers: {
                        'Authorization': 'Bearer YOUR_JWT_TOKEN',
                        'Content-Type': 'application/json'
                    }
                });
                
                // Using axios with API key
                const response = await axios.get('https://api.example.com/api/v1/pipelines/', {
                    headers: {'X-API-Key': 'YOUR_API_KEY'}
                });
                '''
            },
            'crud_operations': {
                'create_pipeline': '''
                # Create a new pipeline
                curl -X POST "https://api.example.com/api/v1/pipelines/" \\
                     -H "Authorization: Bearer <token>" \\
                     -H "Content-Type: application/json" \\
                     -d '{
                         "name": "Sales Pipeline",
                         "description": "Track sales opportunities",
                         "pipeline_type": "crm"
                     }'
                ''',
                'create_record': '''
                # Create a new record
                curl -X POST "https://api.example.com/api/v1/pipelines/{pipeline_id}/records/" \\
                     -H "Authorization: Bearer <token>" \\
                     -H "Content-Type: application/json" \\
                     -d '{
                         "data": {
                             "company_name": "Acme Corp",
                             "contact_email": "john@acme.com",
                             "deal_value": 50000
                         }
                     }'
                '''
            }
        },
        'graphql': {
            'basic_query': '''
            query GetPipelines {
                pipelines {
                    id
                    name
                    recordCount
                }
            }
            ''',
            'query_with_variables': '''
            query GetPipelineRecords($pipelineId: ID!, $limit: Int) {
                pipeline(id: $pipelineId) {
                    name
                    records(limit: $limit) {
                        id
                        title
                        data
                    }
                }
            }
            ''',
            'mutation': '''
            mutation CreateRecord($pipelineId: ID!, $input: CreateRecordInput!) {
                createRecord(pipelineId: $pipelineId, input: $input) {
                    success
                    record {
                        id
                        title
                        data
                    }
                    errors
                }
            }
            ''',
            'subscription': '''
            subscription RecordUpdates($pipelineId: String) {
                recordUpdates(pipelineId: $pipelineId) {
                    id
                    title
                    data
                    updatedAt
                }
            }
            '''
        },
        'websocket': {
            'javascript_client': '''
            // Connect to WebSocket for real-time updates
            const ws = new WebSocket('wss://api.example.com/ws/sse/?token=YOUR_JWT_TOKEN');
            
            ws.onopen = function() {
                // Subscribe to record updates
                ws.send(JSON.stringify({
                    type: 'subscribe',
                    subscription: 'record_updates',
                    id: 'records_sub',
                    filters: {
                        pipeline_id: 'your-pipeline-id'
                    }
                }));
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                console.log('Received update:', data);
            };
            ''',
            'python_client': '''
            import asyncio
            import websockets
            import json
            
            async def subscribe_to_updates():
                uri = "wss://api.example.com/ws/sse/?token=YOUR_JWT_TOKEN"
                
                async with websockets.connect(uri) as websocket:
                    # Subscribe to updates
                    await websocket.send(json.dumps({
                        "type": "subscribe",
                        "subscription": "record_updates",
                        "id": "records_sub"
                    }))
                    
                    # Listen for updates
                    async for message in websocket:
                        data = json.loads(message)
                        print(f"Received: {data}")
            
            asyncio.run(subscribe_to_updates())
            '''
        }
    }
    
    return Response(examples)


@api_view(['GET'])
def rate_limits_info_view(request):
    """
    Return information about API rate limits.
    """
    rate_limits = {
        'authenticated_users': {
            'burst': '60 requests per minute',
            'sustained': '1000 requests per hour',
            'note': 'Rate limits are per user account'
        },
        'api_keys': {
            'rate': '10,000 requests per hour',
            'note': 'Higher limits available for enterprise plans'
        },
        'graphql': {
            'rate': '100 requests per minute',
            'complexity_limiting': 'Complex queries count more towards limit',
            'note': 'Query complexity is analyzed automatically'
        },
        'websockets': {
            'connections': '10 concurrent connections per user',
            'messages': '60 messages per minute per connection'
        },
        'headers': {
            'X-RateLimit-Limit': 'Shows your rate limit',
            'X-RateLimit-Remaining': 'Shows remaining requests',
            'X-RateLimit-Reset': 'Shows when limit resets'
        },
        'error_codes': {
            '429': 'Too Many Requests - rate limit exceeded',
            '4029': 'WebSocket rate limit exceeded (closes connection)'
        }
    }
    
    return Response(rate_limits)