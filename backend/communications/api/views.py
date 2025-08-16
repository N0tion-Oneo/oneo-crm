"""
API views for communications account management
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter

from communications.models import UserChannelConnection
from communications.unipile_sdk import unipile_service
from .serializers import (
    AccountConnectionSerializer, StartConnectionSerializer,
    HandleCallbackSerializer, SolveCheckpointSerializer,
    AccountStatusSerializer
)

logger = logging.getLogger(__name__)


class AccountConnectionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing user account connections"""
    
    serializer_class = AccountConnectionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return connections for current user"""
        return UserChannelConnection.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Create connection for current user"""
        serializer.save(user=self.request.user)
    
    @extend_schema(
        summary="Start account connection",
        description="Initialize hosted authentication flow for connecting an account",
        request=StartConnectionSerializer,
        responses={200: AccountConnectionSerializer}
    )
    @action(detail=False, methods=['post'])
    def start_connection(self, request):
        """Start hosted authentication flow"""
        serializer = StartConnectionSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        channel_type = serializer.validated_data['channel_type']
        account_name = serializer.validated_data.get('account_name', f"{channel_type.title()} Account")
        redirect_url = serializer.validated_data['redirect_url']
        
        try:
            # Create pending connection record
            connection = UserChannelConnection.objects.create(
                user=request.user,
                channel_type=channel_type,
                account_name=account_name,
                external_account_id='',  # Will be filled after auth
                account_status='pending'
            )
            
            # Request hosted authentication link from UniPile
            client = unipile_service.get_client()
            import asyncio
            hosted_result = asyncio.run(client.account.request_hosted_link(
                provider=self._map_channel_to_provider(channel_type),
                redirect_url=redirect_url
            ))
            
            # Store hosted auth URL
            connection.hosted_auth_url = hosted_result.get('url', '')
            connection.save()
            
            logger.info(f"Started connection for user {request.user.id}, channel {channel_type}")
            
            return Response({
                'success': True,
                'connection': AccountConnectionSerializer(connection).data,
                'auth_url': connection.hosted_auth_url,
                'message': 'Authentication URL generated successfully'
            })
            
        except Exception as e:
            logger.error(f"Failed to start connection: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Handle authentication callback",
        description="Process callback from hosted authentication",
        request=HandleCallbackSerializer,
        responses={200: AccountConnectionSerializer}
    )
    @action(detail=False, methods=['post'])
    def handle_callback(self, request):
        """Handle authentication callback"""
        serializer = HandleCallbackSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        connection_id = serializer.validated_data['connection_id']
        provider_data = serializer.validated_data.get('provider_data', {})
        
        try:
            connection = UserChannelConnection.objects.get(
                id=connection_id,
                user=request.user
            )
            
            # Extract account ID from provider data or callback
            account_id = provider_data.get('account_id') or request.data.get('account_id')
            
            if account_id:
                # Update connection with account details
                connection.external_account_id = account_id
                connection.account_status = 'active'
                connection.auth_status = 'authenticated'
                connection.hosted_auth_url = ''  # Clear temp URL
                connection.save()
                
                logger.info(f"Successfully connected account {account_id} for user {request.user.id}")
                
                return Response({
                    'success': True,
                    'connection': AccountConnectionSerializer(connection).data,
                    'message': 'Account connected successfully'
                })
            else:
                connection.account_status = 'failed'
                connection.last_error = 'No account ID received from callback'
                connection.save()
                
                return Response({
                    'success': False,
                    'error': 'No account ID received from authentication'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except UserChannelConnection.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Connection not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Failed to handle callback: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Solve checkpoint",
        description="Solve 2FA/verification checkpoint",
        request=SolveCheckpointSerializer,
        responses={200: AccountConnectionSerializer}
    )
    @action(detail=False, methods=['post'])
    def solve_checkpoint(self, request):
        """Solve authentication checkpoint"""
        serializer = SolveCheckpointSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        connection_id = serializer.validated_data['connection_id']
        verification_code = serializer.validated_data['verification_code']
        
        try:
            connection = UserChannelConnection.objects.get(
                id=connection_id,
                user=request.user
            )
            
            # Send checkpoint solution to UniPile
            client = unipile_service.get_client()
            import asyncio
            result = asyncio.run(client.account.solve_checkpoint(
                account_id=connection.external_account_id,
                code=verification_code
            ))
            
            if result.get('success'):
                connection.account_status = 'active'
                connection.checkpoint_data = {}
                connection.save()
                
                return Response({
                    'success': True,
                    'connection': AccountConnectionSerializer(connection).data,
                    'message': 'Checkpoint solved successfully'
                })
            else:
                return Response({
                    'success': False,
                    'error': result.get('error', 'Failed to solve checkpoint')
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Failed to solve checkpoint: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Reconnect account",
        description="Reconnect a failed or expired account",
        responses={200: AccountConnectionSerializer}
    )
    @action(detail=True, methods=['post'])
    def reconnect(self, request, pk=None):
        """Reconnect a failed account"""
        connection = self.get_object()
        
        try:
            # Attempt to reconnect via UniPile
            client = unipile_service.get_client()
            import asyncio
            result = asyncio.run(client.account.reconnect_account(connection.external_account_id))
            
            if result.get('success'):
                connection.account_status = 'active'
                connection.sync_error_count = 0
                connection.last_error = ''
                connection.save()
                
                return Response({
                    'success': True,
                    'connection': AccountConnectionSerializer(connection).data,
                    'message': 'Account reconnected successfully'
                })
            else:
                # If reconnect fails, start new hosted auth flow
                hosted_result = asyncio.run(client.account.request_hosted_link(
                    provider=self._map_channel_to_provider(connection.channel_type),
                    redirect_url=request.build_absolute_uri('/auth/callback'),
                    account_id=connection.external_account_id
                ))
                
                connection.hosted_auth_url = hosted_result.get('url', '')
                connection.account_status = 'pending'
                connection.save()
                
                return Response({
                    'success': True,
                    'connection': AccountConnectionSerializer(connection).data,
                    'auth_url': connection.hosted_auth_url,
                    'message': 'Reconnection requires re-authentication'
                })
                
        except Exception as e:
            logger.error(f"Failed to reconnect account: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Get account status",
        description="Get current status of account connection",
        responses={200: AccountStatusSerializer}
    )
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get account status"""
        connection = self.get_object()
        
        # Optionally refresh status from UniPile
        if request.query_params.get('refresh') == 'true':
            try:
                client = unipile_service.get_client()
                import asyncio
                status_result = asyncio.run(client.account.get_account_status(connection.external_account_id))
                
                # Update local status based on UniPile response
                unipile_status = status_result.get('status', '')
                if unipile_status == 'active':
                    connection.account_status = 'active'
                elif unipile_status in ['failed', 'error']:
                    connection.account_status = 'failed'
                elif unipile_status == 'checkpoint_required':
                    connection.account_status = 'checkpoint_required'
                
                connection.save()
                
            except Exception as e:
                logger.warning(f"Failed to refresh status from UniPile: {e}")
        
        return Response(AccountStatusSerializer(connection).data)
    
    def _map_channel_to_provider(self, channel_type: str) -> str:
        """Map our channel types to UniPile provider names"""
        mapping = {
            'email': 'gmail',  # Default to Gmail, could be configurable
            'linkedin': 'linkedin',
            'whatsapp': 'whatsapp',
            'sms': 'sms'
        }
        return mapping.get(channel_type, channel_type)