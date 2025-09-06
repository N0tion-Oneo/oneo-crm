"""
Account management API views for frontend communication interface
"""
import logging
from asgiref.sync import sync_to_async, async_to_sync
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from communications.models import UserChannelConnection, ChannelType
from communications.api.serializers import UserChannelConnectionSerializer
from communications.unipile_sdk import unipile_service
from oneo_crm.settings import unipile_settings
from authentication.jwt_authentication import TenantAwareJWTAuthentication
from authentication.permissions import SyncPermissionManager

logger = logging.getLogger(__name__)


class CommunicationAccountsPermission(BasePermission):
    """Permission for communication accounts settings"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        # Check communication_settings accounts permission
        return permission_manager.has_permission('action', 'communication_settings', 'accounts', None)


class CommunicationConnectionViewSet(ModelViewSet):
    """ViewSet for managing user communication connections"""
    
    serializer_class = UserChannelConnectionSerializer
    authentication_classes = [TenantAwareJWTAuthentication]
    permission_classes = [CommunicationAccountsPermission]
    
    def get_queryset(self):
        """Filter connections to current user"""
        return UserChannelConnection.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Associate connection with current user"""
        serializer.save(user=self.request.user)


@api_view(['POST'])
@permission_classes([CommunicationAccountsPermission])
def request_hosted_auth(request):
    """
    Request a hosted authentication URL for connecting communication accounts
    """
    try:
        logger.info(f"Hosted auth request from user {request.user.id}")
        logger.info(f"Request data: {request.data}")
        data = request.data
        providers = data.get('providers', [])
        account_id = data.get('account_id')  # For reconnection
        name = data.get('name', f"{request.user.first_name or 'User'} Account")
        
        if not providers:
            return Response(
                {'error': 'At least one provider must be specified'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create a pending connection record for tracking
        provider = providers[0] if isinstance(providers, list) else providers
        
        # Check if this is a reconnection
        if account_id:
            try:
                connection = UserChannelConnection.objects.get(
                    id=account_id,
                    user=request.user
                )
                connection.account_status = 'pending'
                connection.save()
            except UserChannelConnection.DoesNotExist:
                return Response(
                    {'error': 'Connection not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Create new pending connection
            connection = UserChannelConnection.objects.create(
                user=request.user,
                channel_type=provider.lower(),
                account_name=name,  # Use the provided name
                account_status='pending',
                auth_status='pending'
            )
        
        # Get UniPile client
        client = unipile_service.get_client()
        
        # Build callback URLs - use Cloudflare tunnel for UniPile callbacks
        host = request.get_host()
        if 'localhost' in host or '127.0.0.1' in host:
            # For local development, use Cloudflare tunnel domain for UniPile callbacks
            # UniPile cannot reach localhost, so we use the tunnel domain
            # Based on cloudflare.log, the tunnel uses webhooks.oneocrm.com for API endpoints
            base_url = "https://webhooks.oneocrm.com"
        else:
            # For production, use the actual domain
            base_url = request.build_absolute_uri('/').rstrip('/')
        
        success_redirect_url = f"{base_url}/webhooks/api/v1/communications/auth/callback/success/?state={connection.id}"
        failure_redirect_url = f"{base_url}/webhooks/api/v1/communications/auth/callback/failure/?state={connection.id}"
        
        # Set notify URL for webhook callbacks
        notify_url = unipile_settings.get_webhook_url()
        
        # Request hosted authentication link from UniPile
        try:
            # Get UniPile client and request real hosted auth URL
            client = unipile_service.get_client()
            
            # Call the actual UniPile hosted auth API (use async_to_sync for ASGI compatibility)
            hosted_auth_result = async_to_sync(client.account.request_hosted_link)(
                providers=providers,
                success_redirect_url=success_redirect_url,
                failure_redirect_url=failure_redirect_url,
                notify_url=notify_url,
                name=name
            )
            logger.info(f"UniPile hosted auth response: {hosted_auth_result}")
            
            # UniPile should return a hosted authentication URL
            hosted_url = hosted_auth_result.get('url') or hosted_auth_result.get('hosted_url')
            if hosted_url:
                # Store the hosted URL in the connection for tracking
                connection.hosted_auth_url = hosted_url
                connection.save()
                
                logger.info(f"Generated hosted auth URL for user {request.user.id}, connection {connection.id}")
                
                return Response({
                    'url': hosted_url,
                    'connection_id': str(connection.id),
                    'account_id': hosted_auth_result.get('account_id'),
                    'providers': providers,
                    'status': 'pending'
                })
            else:
                logger.error(f"No hosted URL in UniPile response: {hosted_auth_result}")
                return Response(
                    {'error': 'Failed to generate authentication URL'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"UniPile hosted auth request failed: {e}")
            return Response(
                {'error': f'Authentication request failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    except Exception as e:
        logger.error(f"Error in request_hosted_auth: {e}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return Response(
            {'error': f'Internal server error: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([CommunicationAccountsPermission])
def list_connections(request):
    """
    List all communication connections for the current user
    """
    try:
        connections = UserChannelConnection.objects.filter(user=request.user)
        serializer = UserChannelConnectionSerializer(connections, many=True)
        
        return Response({
            'results': serializer.data,
            'count': connections.count()
        })
    
    except Exception as e:
        logger.error(f"Error listing connections: {e}")
        return Response(
            {'error': 'Failed to load connections'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([CommunicationAccountsPermission])
async def delete_connection(request, connection_id):
    """
    Delete a communication connection
    """
    try:
        connection = UserChannelConnection.objects.get(
            id=connection_id, 
            user=request.user
        )
        
        # Optionally disconnect from UniPile
        try:
            if connection.unipile_account_id:
                client = unipile_service.get_client()
                await client.account.delete_account(connection.unipile_account_id)
        except Exception as e:
            logger.warning(f"Failed to disconnect from UniPile: {e}")
        
        connection.delete()
        
        return Response({'message': 'Connection deleted successfully'})
    
    except UserChannelConnection.DoesNotExist:
        return Response(
            {'error': 'Connection not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error deleting connection: {e}")
        return Response(
            {'error': 'Failed to delete connection'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([CommunicationAccountsPermission])
async def account_status(request, connection_id):
    """
    Get current status of a communication account
    """
    try:
        connection = UserChannelConnection.objects.get(
            id=connection_id, 
            user=request.user
        )
        
        # Check status with UniPile
        try:
            client = unipile_service.get_client()
            account_info = await client.account.get_account(connection.unipile_account_id)
            
            # Update local connection status
            if account_info:
                connection.account_status = account_info.get('status', connection.account_status)
                connection.auth_status = 'authenticated' if account_info.get('connected') else 'failed'
                connection.save()
            
        except Exception as e:
            logger.warning(f"Failed to check UniPile status: {e}")
        
        serializer = UserChannelConnectionSerializer(connection)
        return Response(serializer.data)
    
    except UserChannelConnection.DoesNotExist:
        return Response(
            {'error': 'Connection not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error getting account status: {e}")
        return Response(
            {'error': 'Failed to get account status'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([])  # Allow anonymous access for UniPile callbacks
def hosted_auth_success_callback(request):
    """
    Handle successful hosted authentication callback from UniPile
    """
    try:
        # Extract parameters from callback
        account_id = request.GET.get('account_id')
        provider = request.GET.get('provider')
        state = request.GET.get('state')  # Can be used to link to specific user/connection
        
        logger.info(f"Hosted auth success callback: account_id={account_id}, provider={provider}, state={state}")
        
        if not account_id:
            logger.error("No account_id in success callback")
            return Response(
                {'error': 'Missing account_id parameter'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find and update the pending connection
        # We'll need to link this based on the state parameter or provider type
        updated_connection = None
        
        if state:
            # State should contain connection ID or user ID to link
            try:
                connection_id = state
                connection = UserChannelConnection.objects.get(id=connection_id)
                
                # Update connection with successful auth
                connection.unipile_account_id = account_id
                connection.account_status = 'active'
                connection.auth_status = 'authenticated'
                connection.hosted_auth_url = ''  # Clear the hosted URL
                connection.last_sync_at = timezone.now()
                connection.save()
                
                # Automatically fetch and store comprehensive account details
                try:
                    from communications.services.account_sync import account_sync_service
                    sync_result = async_to_sync(account_sync_service.sync_account_details)(connection)
                    if sync_result.get('success'):
                        logger.info(f"✅ Auto-synced account details for {account_id}: {sync_result.get('phone_number', 'N/A')}")
                    else:
                        logger.warning(f"⚠️ Failed to auto-sync account details for {account_id}: {sync_result.get('error')}")
                except Exception as sync_error:
                    logger.error(f"❌ Error during auto-sync for {account_id}: {sync_error}")
                
                updated_connection = connection
                logger.info(f"Updated connection {connection_id} with account {account_id}")
                
            except UserChannelConnection.DoesNotExist:
                logger.error(f"Connection not found for state: {state}")
        
        # If no state or connection not found, try to find by provider and recent creation
        if not updated_connection and provider:
            # Find most recent pending connection for this provider
            recent_connections = UserChannelConnection.objects.filter(
                channel_type=provider.lower(),
                account_status='pending',
                created_at__gte=timezone.now() - timezone.timedelta(minutes=30)
            ).order_by('-created_at')
            
            if recent_connections.exists():
                connection = recent_connections.first()
                connection.unipile_account_id = account_id
                connection.account_status = 'active'
                connection.auth_status = 'authenticated'
                connection.hosted_auth_url = ''
                connection.last_sync_at = timezone.now()
                connection.save()
                
                # Automatically fetch and store comprehensive account details
                try:
                    from communications.services.account_sync import account_sync_service
                    sync_result = async_to_sync(account_sync_service.sync_account_details)(connection)
                    if sync_result.get('success'):
                        logger.info(f"✅ Auto-synced account details for {account_id}: {sync_result.get('phone_number', 'N/A')}")
                    else:
                        logger.warning(f"⚠️ Failed to auto-sync account details for {account_id}: {sync_result.get('error')}")
                except Exception as sync_error:
                    logger.error(f"❌ Error during auto-sync for {account_id}: {sync_error}")
                
                updated_connection = connection
                logger.info(f"Linked account {account_id} to recent {provider} connection")
        
        # Prepare frontend redirect with success parameters
        # Always redirect to localhost frontend for development
        # Extract tenant from the request or connection - fail fast if not found
        tenant_name = None
        
        # Try to get tenant from the connection's user
        if updated_connection and hasattr(updated_connection.user, 'tenant'):
            tenant_name = updated_connection.user.tenant.schema_name
        
        # Try to get tenant from request (django-tenants sets connection.tenant)
        elif hasattr(request, 'tenant'):
            tenant_name = request.tenant.schema_name
        
        if not tenant_name:
            logger.error("Cannot determine tenant for callback redirect")
            raise ValueError("Tenant information not available for callback redirect")
        
        # Always use localhost frontend for development (users are developing locally)
        default_frontend = f'http://{tenant_name}.localhost:3000/communications'
        
        frontend_url = request.GET.get('frontend_url', default_frontend)
        if updated_connection:
            redirect_url = f"{frontend_url}?success=true&account_id={account_id}&provider={provider}&connection_id={updated_connection.id}"
        else:
            redirect_url = f"{frontend_url}?success=true&account_id={account_id}&provider={provider}&warning=not_linked"
        
        # Return HTML redirect page instead of JSON
        from django.http import HttpResponseRedirect
        from django.template.response import TemplateResponse
        
        # Create a simple HTML page that auto-redirects
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
            <p>Your {provider.title()} account has been connected successfully.</p>
            <p class="loading">Redirecting you back to Oneo CRM...</p>
            <script>
                setTimeout(function() {{
                    window.location.href = "{redirect_url}";
                }}, 2000);
            </script>
        </body>
        </html>
        """
        
        from django.http import HttpResponse
        return HttpResponse(html_content, content_type='text/html')
        
    except Exception as e:
        logger.error(f"Error in hosted auth success callback: {e}")
        # Always redirect to localhost frontend for development
        # Extract tenant from request - fail fast if not available
        if not hasattr(request, 'tenant'):
            logger.error("Cannot determine tenant for error callback redirect")
            raise ValueError("Tenant information not available for error callback redirect")
        
        tenant_name = request.tenant.schema_name
        default_frontend = f'http://{tenant_name}.localhost:3000/communications'
        
        frontend_url = request.GET.get('frontend_url', default_frontend)
        error_redirect = f"{frontend_url}?error=callback_failed&message={str(e)}"
        
        # Return HTML error page
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
        
        from django.http import HttpResponse
        return HttpResponse(html_content, content_type='text/html', status=500)


@api_view(['GET'])
@permission_classes([])  # Allow anonymous access for UniPile callbacks
def hosted_auth_failure_callback(request):
    """
    Handle failed hosted authentication callback from UniPile
    """
    try:
        error = request.GET.get('error', 'Unknown error')
        error_description = request.GET.get('error_description', '')
        state = request.GET.get('state')
        provider = request.GET.get('provider')
        
        logger.warning(f"Hosted auth failure callback: error={error}, provider={provider}, state={state}")
        
        # Update connection status if we can identify it
        if state:
            try:
                connection = UserChannelConnection.objects.get(id=state)
                connection.account_status = 'failed'
                connection.auth_status = 'failed'
                connection.last_error = f"{error}: {error_description}"
                connection.hosted_auth_url = ''
                connection.save()
                
                logger.info(f"Updated connection {state} with failure status")
                
            except UserChannelConnection.DoesNotExist:
                logger.error(f"Connection not found for failed auth state: {state}")
        
        # Prepare frontend redirect
        # Always redirect to localhost frontend for development
        # Extract tenant from request - fail fast if not available
        if not hasattr(request, 'tenant'):
            logger.error("Cannot determine tenant for failure callback redirect")
            raise ValueError("Tenant information not available for failure callback redirect")
        
        tenant_name = request.tenant.schema_name
        default_frontend = f'http://{tenant_name}.localhost:3000/communications'
        
        frontend_url = request.GET.get('frontend_url', default_frontend)
        redirect_url = f"{frontend_url}?error={error}&description={error_description}&provider={provider}"
        
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
        
        from django.http import HttpResponse
        return HttpResponse(html_content, content_type='text/html')
        
    except Exception as e:
        logger.error(f"Error in hosted auth failure callback: {e}")
        # Extract tenant from request - fail fast if not available
        if not hasattr(request, 'tenant'):
            logger.error("Cannot determine tenant for failure callback error redirect")
            raise ValueError("Tenant information not available for failure callback error redirect")
        
        tenant_name = request.tenant.schema_name
        default_frontend = f'http://{tenant_name}.localhost:3000/communications'
        
        frontend_url = request.GET.get('frontend_url', default_frontend)
        error_redirect = f"{frontend_url}?error=callback_processing_failed&message={str(e)}"
        
        # Return HTML error page
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
        
        from django.http import HttpResponse
        return HttpResponse(html_content, content_type='text/html', status=500)


@api_view(['POST'])
@permission_classes([CommunicationAccountsPermission])
async def solve_checkpoint(request, connection_id):
    """
    Submit checkpoint/2FA code for account verification
    """
    try:
        connection = UserChannelConnection.objects.get(
            id=connection_id,
            user=request.user
        )
        
        code = request.data.get('code')
        if not code:
            return Response(
                {'error': 'Verification code is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Submit code to UniPile
        try:
            client = unipile_service.get_client()
            result = await client.account.solve_checkpoint(
                connection.unipile_account_id, 
                code
            )
            
            # Update connection status based on result
            if result.get('success') or result.get('status') == 'success':
                connection.account_status = 'active'
                connection.auth_status = 'authenticated'
                connection.checkpoint_data = {}
                connection.last_error = ''
                connection.save()
                
                # Automatically sync account details after successful checkpoint
                try:
                    from communications.services.account_sync import account_sync_service
                    sync_result = await account_sync_service.sync_account_details(connection)
                    if sync_result.get('success'):
                        logger.info(f"✅ Auto-synced account details after checkpoint for {connection.unipile_account_id}")
                    else:
                        logger.warning(f"⚠️ Failed to auto-sync after checkpoint: {sync_result.get('error')}")
                except Exception as sync_error:
                    logger.error(f"❌ Error during auto-sync after checkpoint: {sync_error}")
                
                logger.info(f"Checkpoint solved for connection {connection_id}")
                
                return Response({
                    'success': True,
                    'message': 'Account verified successfully',
                    'connection_status': 'active'
                })
            else:
                # Checkpoint failed
                error_msg = result.get('error', 'Invalid verification code')
                connection.last_error = error_msg
                connection.save()
                
                return Response({
                    'success': False,
                    'error': error_msg
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Failed to solve checkpoint: {e}")
            connection.last_error = str(e)
            connection.save()
            
            return Response(
                {'error': f'Checkpoint submission failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    except UserChannelConnection.DoesNotExist:
        return Response(
            {'error': 'Connection not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error solving checkpoint: {e}")
        return Response(
            {'error': 'Internal server error'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([CommunicationAccountsPermission])
async def resend_checkpoint(request, connection_id):
    """
    Request resend of checkpoint/2FA code
    """
    try:
        connection = UserChannelConnection.objects.get(
            id=connection_id,
            user=request.user
        )
        
        # Request checkpoint resend from UniPile
        try:
            client = unipile_service.get_client()
            result = await client.account.resend_checkpoint(connection.unipile_account_id)
            
            if result.get('success') or result.get('status') == 'success':
                logger.info(f"Checkpoint resent for connection {connection_id}")
                
                return Response({
                    'success': True,
                    'message': 'Verification code sent successfully'
                })
            else:
                error_msg = result.get('error', 'Failed to resend verification code')
                return Response({
                    'success': False,
                    'error': error_msg
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Failed to resend checkpoint: {e}")
            return Response(
                {'error': f'Failed to resend verification code: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    except UserChannelConnection.DoesNotExist:
        return Response(
            {'error': 'Connection not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error resending checkpoint: {e}")
        return Response(
            {'error': 'Internal server error'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([CommunicationAccountsPermission])
async def reconnect_account(request, connection_id):
    """
    Attempt to reconnect a failed or expired account
    """
    try:
        connection = UserChannelConnection.objects.get(
            id=connection_id,
            user=request.user
        )
        
        # Try to reconnect via UniPile
        try:
            client = unipile_service.get_client()
            result = await client.account.reconnect_account(connection.unipile_account_id)
            
            if result.get('success') or result.get('status') == 'success':
                connection.account_status = 'active'
                connection.auth_status = 'authenticated'
                connection.last_error = ''
                connection.last_sync_at = timezone.now()
                connection.save()
                
                # Automatically sync account details after successful reconnection
                try:
                    from communications.services.account_sync import account_sync_service
                    sync_result = await account_sync_service.sync_account_details(connection)
                    if sync_result.get('success'):
                        logger.info(f"✅ Auto-synced account details after reconnection for {connection.unipile_account_id}")
                    else:
                        logger.warning(f"⚠️ Failed to auto-sync after reconnection: {sync_result.get('error')}")
                except Exception as sync_error:
                    logger.error(f"❌ Error during auto-sync after reconnection: {sync_error}")
                
                logger.info(f"Account reconnected for connection {connection_id}")
                
                return Response({
                    'success': True,
                    'message': 'Account reconnected successfully',
                    'connection_status': 'active'
                })
            else:
                # Reconnection failed, might need hosted auth
                error_msg = result.get('error', 'Reconnection failed')
                connection.last_error = error_msg
                connection.save()
                
                # Check if we got a hosted auth URL for re-authentication
                hosted_url = result.get('hosted_url')
                if hosted_url:
                    connection.hosted_auth_url = hosted_url
                    connection.account_status = 'pending'
                    connection.save()
                    
                    return Response({
                        'success': False,
                        'error': 'Re-authentication required',
                        'hosted_auth_url': hosted_url,
                        'requires_reauth': True
                    })
                
                return Response({
                    'success': False,
                    'error': error_msg
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Failed to reconnect account: {e}")
            return Response(
                {'error': f'Reconnection failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    except UserChannelConnection.DoesNotExist:
        return Response(
            {'error': 'Connection not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error reconnecting account: {e}")
        return Response(
            {'error': 'Internal server error'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )