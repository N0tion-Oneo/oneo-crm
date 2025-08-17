"""
Provider configuration API views for communications settings
"""
import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from communications.models import TenantUniPileConfig
from authentication.jwt_authentication import TenantAwareJWTAuthentication

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_provider_configurations(request):
    """
    Get global provider configurations and tenant preferences
    """
    try:
        # Get global provider settings
        global_config = getattr(settings, 'UNIPILE_SETTINGS', None)
        if not global_config:
            return Response(
                {'error': 'UniPile settings not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        provider_configs = {}
        
        # Get or create tenant config
        tenant_config = TenantUniPileConfig.get_or_create_for_tenant()
        
        for provider_type in global_config.get_supported_providers():
            global_provider_config = global_config.get_provider_config(provider_type)
            tenant_prefs = tenant_config.get_provider_preferences(provider_type)
            
            # Merge global configuration with tenant preferences
            provider_configs[provider_type] = {
                'global': {
                    'name': global_provider_config.get('name', provider_type.title()),
                    'icon': global_provider_config.get('icon', '📢'),
                    'features': global_provider_config.get('features', {}),
                    'rate_limits': global_provider_config.get('rate_limits', {}),
                    'auth_methods': global_provider_config.get('auth_methods', ['hosted']),
                    'supported_endpoints': global_provider_config.get('supported_endpoints', [])
                },
                'tenant_preferences': tenant_prefs or tenant_config.get_default_provider_preferences().get(provider_type, {}),
                'is_configured': global_config.is_configured(),
                'can_connect': global_config.is_configured() and tenant_config.is_active
            }
        
        return Response({
            'success': True,
            'providers': provider_configs,
            'global_settings': {
                'dsn': global_config.dsn,
                'is_configured': global_config.is_configured(),
                'webhook_url': global_config.get_webhook_url()
            },
            'tenant_config': {
                'is_active': tenant_config.is_active,
                'auto_create_contacts': tenant_config.auto_create_contacts,
                'sync_historical_days': tenant_config.sync_historical_days,
                'enable_real_time_sync': tenant_config.enable_real_time_sync,
                'max_api_calls_per_hour': tenant_config.max_api_calls_per_hour
            }
        })
        
    except Exception as e:
        import traceback
        logger.error(f"Error getting provider configurations: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return Response(
            {'error': f'Failed to get provider configurations: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_provider_preferences(request):
    """
    Update tenant provider preferences
    """
    try:
        provider_type = request.data.get('provider_type')
        preferences = request.data.get('preferences', {})
        
        if not provider_type:
            return Response(
                {'error': 'Provider type is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get tenant config
        tenant_config = TenantUniPileConfig.get_or_create_for_tenant()
        
        # Validate and set preferences
        try:
            tenant_config.set_provider_preferences(provider_type, preferences)
            
            return Response({
                'success': True,
                'message': f'Preferences updated for {provider_type}',
                'preferences': tenant_config.get_provider_preferences(provider_type)
            })
            
        except ValueError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
    except Exception as e:
        logger.error(f"Error updating provider preferences: {e}")
        return Response(
            {'error': 'Failed to update provider preferences'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_tenant_config(request):
    """
    Update general tenant UniPile configuration
    """
    try:
        # Get tenant config
        tenant_config = TenantUniPileConfig.get_or_create_for_tenant()
        
        # Update allowed fields
        allowed_fields = [
            'auto_create_contacts', 'sync_historical_days', 
            'enable_real_time_sync', 'max_api_calls_per_hour'
        ]
        
        updated_fields = []
        for field in allowed_fields:
            if field in request.data:
                setattr(tenant_config, field, request.data[field])
                updated_fields.append(field)
        
        if updated_fields:
            tenant_config.save(update_fields=updated_fields)
        
        return Response({
            'success': True,
            'message': 'Tenant configuration updated',
            'updated_fields': updated_fields,
            'config': {
                'auto_create_contacts': tenant_config.auto_create_contacts,
                'sync_historical_days': tenant_config.sync_historical_days,
                'enable_real_time_sync': tenant_config.enable_real_time_sync,
                'max_api_calls_per_hour': tenant_config.max_api_calls_per_hour
            }
        })
        
    except Exception as e:
        logger.error(f"Error updating tenant config: {e}")
        return Response(
            {'error': 'Failed to update tenant configuration'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_provider_rate_limits(request, provider_type):
    """
    Get effective rate limits for a specific provider
    """
    try:
        global_config = getattr(settings, 'UNIPILE_SETTINGS', None)
        if not global_config:
            return Response(
                {'error': 'UniPile settings not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        tenant_config = TenantUniPileConfig.get_or_create_for_tenant()
        
        if provider_type not in global_config.get_supported_providers():
            return Response(
                {'error': f'Provider {provider_type} not supported'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        global_limits = global_config.get_provider_rate_limits(provider_type)
        effective_limits = {}
        
        for limit_type, global_limit in global_limits.items():
            effective_limit = tenant_config.get_provider_rate_limit(provider_type, limit_type)
            effective_limits[limit_type] = {
                'global_limit': global_limit,
                'effective_limit': effective_limit,
                'is_reduced': effective_limit < global_limit
            }
        
        return Response({
            'success': True,
            'provider': provider_type,
            'rate_limits': effective_limits
        })
        
    except Exception as e:
        logger.error(f"Error getting provider rate limits: {e}")
        return Response(
            {'error': 'Failed to get provider rate limits'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_provider_features(request, provider_type):
    """
    Get enabled features for a specific provider
    """
    try:
        global_config = getattr(settings, 'UNIPILE_SETTINGS', None)
        if not global_config:
            return Response(
                {'error': 'UniPile settings not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        tenant_config = TenantUniPileConfig.get_or_create_for_tenant()
        
        if provider_type not in global_config.get_supported_providers():
            return Response(
                {'error': f'Provider {provider_type} not supported'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        global_features = global_config.get_provider_features(provider_type)
        enabled_features = {}
        
        for feature, globally_enabled in global_features.items():
            tenant_enabled = tenant_config.is_provider_feature_enabled(provider_type, feature)
            enabled_features[feature] = {
                'globally_enabled': globally_enabled,
                'tenant_enabled': tenant_enabled,
                'available': globally_enabled and tenant_enabled
            }
        
        return Response({
            'success': True,
            'provider': provider_type,
            'features': enabled_features
        })
        
    except Exception as e:
        logger.error(f"Error getting provider features: {e}")
        return Response(
            {'error': 'Failed to get provider features'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )