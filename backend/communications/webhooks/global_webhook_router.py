"""
Global webhook router for UniPile webhooks
Routes incoming webhooks from UniPile to the appropriate tenant
"""
import logging
import requests
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json

from tenants.models import Tenant, Domain
from communications.models import UserChannelConnection

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class GlobalWebhookRouterView(View):
    """
    Global webhook router that receives UniPile webhooks and routes them to tenants
    
    This view runs on the public/global side and routes webhooks to tenant subdomains
    """
    
    def post(self, request):
        """Handle incoming UniPile webhooks and route to appropriate tenant"""
        try:
            # Parse webhook data
            webhook_data = json.loads(request.body)
            
            # Extract account ID from webhook
            account_id = webhook_data.get('account_id')
            event_type = webhook_data.get('event_type')
            
            logger.info(f"Received global UniPile webhook: {event_type} for account {account_id}")
            
            if not account_id:
                logger.error("Webhook missing account_id")
                return JsonResponse({
                    'error': 'Missing account_id in webhook data'
                }, status=400)
            
            # Find which tenant this account belongs to
            tenant_info = self._find_tenant_for_account(account_id)
            
            if not tenant_info:
                logger.warning(f"No tenant found for UniPile account {account_id}")
                return JsonResponse({
                    'status': 'ignored',
                    'reason': f'No tenant found for account {account_id}'
                })
            
            # Route webhook to tenant
            route_result = self._route_webhook_to_tenant(
                tenant_info, webhook_data, request
            )
            
            if route_result['success']:
                return JsonResponse({
                    'status': 'routed',
                    'tenant': tenant_info['tenant_name'],
                    'target_url': route_result['target_url']
                })
            else:
                logger.error(f"Failed to route webhook to tenant: {route_result['error']}")
                return JsonResponse({
                    'error': 'Failed to route webhook to tenant',
                    'details': route_result['error']
                }, status=500)
        
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook request")
            return JsonResponse({
                'error': 'Invalid JSON in request body'
            }, status=400)
        
        except Exception as e:
            logger.error(f"Failed to process global webhook: {e}")
            return JsonResponse({
                'error': 'Failed to process webhook',
                'details': str(e)
            }, status=500)
    
    def get(self, request):
        """Health check endpoint"""
        return JsonResponse({
            'status': 'ok',
            'service': 'global_webhook_router',
            'message': 'Global UniPile webhook router is operational'
        })
    
    def _find_tenant_for_account(self, account_id: str) -> dict:
        """
        Find which tenant owns the given UniPile account ID
        
        This requires checking across all tenant schemas
        """
        try:
            # Import here to avoid circular imports
            from django_tenants.utils import get_tenant_model, get_public_schema_name
            from django.db import connection
            
            # Get all tenants
            tenant_model = get_tenant_model()
            tenants = tenant_model.objects.exclude(schema_name=get_public_schema_name())
            
            for tenant in tenants:
                # Switch to tenant schema
                connection.set_tenant(tenant)
                
                try:
                    # Look for the account in this tenant's connections
                    user_connection = UserChannelConnection.objects.filter(
                        unipile_account_id=account_id,
                        is_active=True
                    ).first()
                    
                    if user_connection:
                        # Found the account, get tenant domain
                        domain = Domain.objects.filter(tenant=tenant).first()
                        
                        return {
                            'tenant_id': tenant.id,
                            'tenant_name': tenant.name,
                            'schema_name': tenant.schema_name,
                            'domain': domain.domain if domain else f"{tenant.schema_name}.localhost",
                            'user_connection_id': str(user_connection.id),
                            'user_id': user_connection.user.id
                        }
                
                except Exception as e:
                    logger.error(f"Error checking tenant {tenant.schema_name}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find tenant for account {account_id}: {e}")
            return None
        
        finally:
            # Switch back to public schema
            from django_tenants.utils import get_public_schema_name
            from django.db import connection
            public_tenant = tenant_model.objects.get(schema_name=get_public_schema_name())
            connection.set_tenant(public_tenant)
    
    def _route_webhook_to_tenant(self, tenant_info: dict, webhook_data: dict, original_request) -> dict:
        """
        Route the webhook to the appropriate tenant's webhook endpoint
        """
        try:
            # Construct tenant webhook URL
            domain = tenant_info['domain']
            
            # Use the same port as the current request if running locally
            if 'localhost' in domain:
                # Extract port from original request
                host_header = original_request.get_host()
                if ':' in host_header:
                    port = host_header.split(':')[1]
                    target_url = f"http://{domain}:{port}/api/v1/communications/webhooks/messages/"
                else:
                    target_url = f"http://{domain}/api/v1/communications/webhooks/messages/"
            else:
                # Production URL
                target_url = f"https://{domain}/api/v1/communications/webhooks/messages/"
            
            # Add tenant context to webhook data
            enhanced_webhook_data = {
                **webhook_data,
                'tenant_info': tenant_info,
                'routed_from': 'global_webhook_router'
            }
            
            # Forward the webhook to tenant
            response = requests.post(
                target_url,
                json=enhanced_webhook_data,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'OneoCRM-Global-Webhook-Router/1.0',
                    'X-Forwarded-For': original_request.META.get('REMOTE_ADDR', ''),
                    'X-Original-Host': original_request.get_host()
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'target_url': target_url,
                    'tenant_response': response.json() if response.content else None
                }
            else:
                return {
                    'success': False,
                    'error': f'Tenant webhook returned {response.status_code}: {response.text}',
                    'target_url': target_url
                }
        
        except requests.RequestException as e:
            return {
                'success': False,
                'error': f'Failed to forward webhook to tenant: {str(e)}',
                'target_url': target_url if 'target_url' in locals() else 'unknown'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error routing webhook: {str(e)}'
            }


# Function-based view for easier URL routing
@csrf_exempt
@require_http_methods(["GET", "POST"])
def global_webhook_router(request):
    """Function-based wrapper for the global webhook router"""
    view = GlobalWebhookRouterView()
    return view.dispatch(request)


@csrf_exempt
@require_http_methods(["POST"])
def unipile_global_webhook(request):
    """
    Main UniPile webhook endpoint on the global/public side
    
    This endpoint should be registered with UniPile as the webhook URL:
    https://yourdomain.com/webhooks/unipile/
    """
    try:
        # Log the incoming webhook for debugging
        logger.info(f"Received UniPile webhook: {request.method} {request.path}")
        logger.debug(f"Webhook headers: {dict(request.headers)}")
        
        if request.content_type == 'application/json':
            webhook_data = json.loads(request.body)
            logger.debug(f"Webhook data: {webhook_data}")
        else:
            logger.warning(f"Unexpected content type: {request.content_type}")
            return JsonResponse({
                'error': 'Expected application/json content type'
            }, status=400)
        
        # Route to appropriate tenant
        router_view = GlobalWebhookRouterView()
        return router_view.post(request)
        
    except Exception as e:
        logger.error(f"Failed to process UniPile global webhook: {e}")
        return JsonResponse({
            'error': 'Failed to process webhook',
            'details': str(e)
        }, status=500)


@require_http_methods(["GET"])
def webhook_health_check(request):
    """Health check for webhook endpoints"""
    return JsonResponse({
        'status': 'healthy',
        'service': 'unipile_global_webhook_router',
        'timestamp': request.META.get('HTTP_DATE', ''),
        'endpoints': {
            'global_webhook': '/webhooks/unipile/',
            'health_check': '/webhooks/health/',
            'router': '/webhooks/router/'
        }
    })