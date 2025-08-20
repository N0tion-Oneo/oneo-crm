"""
Webhook views for UniPile integration
"""
import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.utils import timezone
from communications.webhooks.dispatcher import webhook_dispatcher
from communications.webhooks.validators import webhook_validator
# Backward compatibility alias
webhook_handler = webhook_dispatcher
from communications.models import UserChannelConnection

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def unipile_webhook(request):
    """
    Main UniPile webhook endpoint
    Receives all webhook events and routes them to appropriate tenants
    """
    try:
        # Get raw body for signature validation
        raw_body = request.body
        
        # Validate webhook signature
        signature = webhook_validator.extract_signature(request)
        if signature and not webhook_validator.validate_signature(raw_body, signature):
            logger.warning("Invalid webhook signature")
            return JsonResponse({'error': 'Invalid signature'}, status=401)
        
        # Parse JSON data
        try:
            data = json.loads(raw_body.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook: {e}")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        # Extract event type
        event_type = data.get('event', data.get('type', 'unknown'))
        
        logger.info(f"Received webhook: {event_type}")
        logger.debug(f"Webhook data: {data}")
        
        # Process the webhook using unified dispatcher
        result = webhook_dispatcher.process_webhook(event_type, data)
        
        # Also process with legacy handler for backward compatibility during transition
        # TODO: Remove this after confirming new dispatcher works correctly
        if not result.get('success'):
            logger.info(f"Falling back to legacy handler for {event_type}")
            fallback_result = webhook_handler.process_webhook(event_type, data)
            if fallback_result.get('success'):
                logger.warning(f"Legacy handler succeeded where new dispatcher failed for {event_type}")
                result = fallback_result
        
        if result.get('success'):
            logger.info(f"Successfully processed webhook: {event_type}")
            return JsonResponse({
                'success': True,
                'message': 'Webhook processed successfully',
                'result': result
            })
        else:
            logger.error(f"Failed to process webhook: {result.get('error')}")
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            }, status=400)
    
    except Exception as e:
        logger.error(f"Unexpected error processing webhook: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def webhook_health(request):
    """
    Webhook health check endpoint
    """
    return JsonResponse({
        'status': 'healthy',
        'service': 'unipile-webhook',
        'timestamp': request.GET.get('timestamp', 'none')
    })


@csrf_exempt
@require_http_methods(["GET"])
def hosted_auth_success_callback(request):
    """
    Handle successful hosted authentication callback from UniPile via webhook domain
    """
    try:
        # Extract parameters from callback
        account_id = request.GET.get('account_id')
        provider = request.GET.get('provider')
        state = request.GET.get('state')  # Connection ID or user identifier
        
        logger.info(f"Webhook hosted auth success: account_id={account_id}, provider={provider}, state={state}")
        
        if not account_id:
            logger.error("No account_id in webhook success callback")
            return HttpResponse("Missing account_id parameter", status=400)
        
        if not state:
            logger.error("No state parameter in webhook success callback")
            return HttpResponse("Missing state parameter", status=400)
        
        # Find and update the pending connection using the state parameter
        updated_connection = None
        tenant_name = None
        
        if state:
            try:
                # Need to search across all tenant schemas for the connection
                # Import schema context manager
                from django_tenants.utils import tenant_context
                from tenants.models import Tenant
                
                # Search all tenants for the connection
                found_connection = None
                found_tenant = None
                
                for tenant in Tenant.objects.all():
                    try:
                        with tenant_context(tenant):
                            connection = UserChannelConnection.objects.get(id=state)
                            found_connection = connection
                            found_tenant = tenant
                            break
                    except UserChannelConnection.DoesNotExist:
                        continue
                    except Exception as e:
                        # Skip tenants that don't have the communications tables yet
                        logger.debug(f"Skipping tenant {tenant.schema_name}: {e}")
                        continue
                
                if found_connection and found_tenant:
                    # Update connection with successful auth in the correct tenant context
                    with tenant_context(found_tenant):
                        connection = UserChannelConnection.objects.get(id=state)
                        connection.unipile_account_id = account_id
                        connection.account_status = 'active'
                        connection.auth_status = 'authenticated'
                        connection.hosted_auth_url = ''
                        connection.last_sync_at = timezone.now()
                        connection.save()
                        
                        updated_connection = connection
                        tenant_name = found_tenant.schema_name
                        
                        logger.info(f"Updated connection {state} with account {account_id} in tenant {tenant_name}")
                else:
                    logger.error(f"Connection {state} not found in any tenant")
                
            except Exception as e:
                logger.error(f"Error finding connection across tenants: {e}")
        
        # Fail fast if we couldn't determine tenant
        if not tenant_name:
            logger.error(f"Could not determine tenant for connection {state}")
            return HttpResponse("Unable to determine tenant for callback", status=500)
        
        # Redirect to frontend
        redirect_url = f"http://{tenant_name}.localhost:3000/communications?success=true&account_id={account_id}"
        if provider:
            redirect_url += f"&provider={provider}"
        if updated_connection:
            redirect_url += f"&connection_id={updated_connection.id}"
        
        # Return HTML redirect page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Successful</title>
            <meta http-equiv="refresh" content="2;url={redirect_url}">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }}
                .success {{ color: #28a745; }}
                .loading {{ margin-top: 20px; }}
            </style>
        </head>
        <body>
            <h1 class="success">✅ Authentication Successful!</h1>
            <p>Your {provider.title() if provider else 'account'} has been connected successfully.</p>
            <p class="loading">Redirecting you back to Oneo CRM...</p>
            <script>
                setTimeout(function() {{
                    window.location.href = "{redirect_url}";
                }}, 2000);
            </script>
        </body>
        </html>
        """
        
        return HttpResponse(html_content, content_type='text/html')
        
    except Exception as e:
        logger.error(f"Error in webhook hosted auth success callback: {e}")
        error_redirect = f"http://demo.localhost:3000/communications?error=callback_failed&message={str(e)}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Error</title>
            <meta http-equiv="refresh" content="3;url={error_redirect}">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }}
                .error {{ color: #dc3545; }}
                .loading {{ margin-top: 20px; }}
            </style>
        </head>
        <body>
            <h1 class="error">❌ Authentication Error</h1>
            <p>There was an error processing your authentication.</p>
            <p class="loading">Redirecting you back to Oneo CRM...</p>
            <script>
                setTimeout(function() {{
                    window.location.href = "{error_redirect}";
                }}, 3000);
            </script>
        </body>
        </html>
        """
        
        return HttpResponse(html_content, content_type='text/html', status=500)


@csrf_exempt
@require_http_methods(["GET"])
def hosted_auth_failure_callback(request):
    """
    Handle failed hosted authentication callback from UniPile via webhook domain
    """
    try:
        error = request.GET.get('error', 'Unknown error')
        error_description = request.GET.get('error_description', '')
        state = request.GET.get('state')
        provider = request.GET.get('provider')
        
        logger.warning(f"Webhook hosted auth failure: error={error}, provider={provider}, state={state}")
        
        if not state:
            logger.error("No state parameter in webhook failure callback")
            return HttpResponse("Missing state parameter", status=400)
        
        # Update connection status if we can identify it
        tenant_name = None
        
        if state:
            try:
                # Need to search across all tenant schemas for the connection
                from django_tenants.utils import tenant_context
                from tenants.models import Tenant
                
                # Search all tenants for the connection
                found_tenant = None
                
                for tenant in Tenant.objects.all():
                    try:
                        with tenant_context(tenant):
                            connection = UserChannelConnection.objects.get(id=state)
                            found_tenant = tenant
                            break
                    except UserChannelConnection.DoesNotExist:
                        continue
                    except Exception as e:
                        # Skip tenants that don't have the communications tables yet
                        logger.debug(f"Skipping tenant {tenant.schema_name}: {e}")
                        continue
                
                if found_tenant:
                    # Update connection with failure status in the correct tenant context
                    with tenant_context(found_tenant):
                        connection = UserChannelConnection.objects.get(id=state)
                        connection.account_status = 'failed'
                        connection.auth_status = 'failed'
                        connection.last_error = f"{error}: {error_description}"
                        connection.hosted_auth_url = ''
                        connection.save()
                        
                        tenant_name = found_tenant.schema_name
                        
                        logger.info(f"Updated connection {state} with failure status in tenant {tenant_name}")
                else:
                    logger.error(f"Connection {state} not found in any tenant for failure callback")
                
            except Exception as e:
                logger.error(f"Error finding connection across tenants for failure: {e}")
        
        # Fail fast if we couldn't determine tenant
        if not tenant_name:
            logger.error(f"Could not determine tenant for failed connection {state}")
            return HttpResponse("Unable to determine tenant for failure callback", status=500)
        
        # Redirect to frontend
        redirect_url = f"http://{tenant_name}.localhost:3000/communications?error={error}"
        if error_description:
            redirect_url += f"&description={error_description}"
        if provider:
            redirect_url += f"&provider={provider}"
        
        # Return HTML failure page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Failed</title>
            <meta http-equiv="refresh" content="3;url={redirect_url}">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }}
                .error {{ color: #dc3545; }}
                .loading {{ margin-top: 20px; }}
                .description {{ color: #666; font-style: italic; }}
            </style>
        </head>
        <body>
            <h1 class="error">❌ Authentication Failed</h1>
            <p>Failed to connect your {provider.title() if provider else 'account'}.</p>
            {f'<p class="description">{error_description}</p>' if error_description else ''}
            <p class="loading">Redirecting you back to Oneo CRM...</p>
            <script>
                setTimeout(function() {{
                    window.location.href = "{redirect_url}";
                }}, 3000);
            </script>
        </body>
        </html>
        """
        
        return HttpResponse(html_content, content_type='text/html')
        
    except Exception as e:
        logger.error(f"Error in webhook hosted auth failure callback: {e}")
        error_redirect = f"http://demo.localhost:3000/communications?error=callback_processing_failed&message={str(e)}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Callback Error</title>
            <meta http-equiv="refresh" content="3;url={error_redirect}">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }}
                .error {{ color: #dc3545; }}
                .loading {{ margin-top: 20px; }}
            </style>
        </head>
        <body>
            <h1 class="error">❌ Callback Processing Error</h1>
            <p>There was an error processing the authentication callback.</p>
            <p class="loading">Redirecting you back to Oneo CRM...</p>
            <script>
                setTimeout(function() {{
                    window.location.href = "{error_redirect}";
                }}, 3000);
            </script>
        </body>
        </html>
        """
        
        return HttpResponse(html_content, content_type='text/html', status=500)