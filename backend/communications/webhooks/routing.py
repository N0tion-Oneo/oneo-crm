"""
Account-to-tenant routing for UniPile webhooks
"""
import logging
from typing import Optional, Callable, Any
from django.db import connection
from django_tenants.utils import schema_context
from communications.models import UserChannelConnection

logger = logging.getLogger(__name__)


class AccountTenantRouter:
    """Routes webhook events to the correct tenant based on account ID"""
    
    @staticmethod
    def get_tenant_for_account(account_id: str) -> Optional[str]:
        """
        Find which tenant owns the given UniPile account ID
        
        Args:
            account_id: UniPile account ID from webhook
            
        Returns:
            Optional[str]: Tenant schema name or None if not found
        """
        try:
            # Search across all tenants for this account using Tenant model
            from tenants.models import Tenant
            
            # Get all tenant schemas (excluding public)
            tenants = Tenant.objects.exclude(schema_name='public')
            
            # Check each tenant schema for the account
            for tenant in tenants:
                try:
                    with schema_context(tenant.schema_name):
                        connection_exists = UserChannelConnection.objects.filter(
                            unipile_account_id=account_id
                        ).exists()
                        
                        if connection_exists:
                            logger.info(f"Found account {account_id} in tenant {tenant.schema_name}")
                            return tenant.schema_name
                except Exception as tenant_error:
                    logger.warning(f"Error checking tenant {tenant.schema_name}: {tenant_error}")
                    continue
                
            logger.warning(f"Account {account_id} not found in any tenant")
            return None
                
        except Exception as e:
            logger.error(f"Error finding tenant for account {account_id}: {e}")
            return None
    
    @staticmethod
    def process_with_tenant_context(account_id: str, handler_func: Callable, *args, **kwargs) -> Any:
        """
        Process webhook event in the correct tenant context
        
        Args:
            account_id: UniPile account ID from webhook
            handler_func: Function to call in tenant context
            *args, **kwargs: Arguments to pass to handler function
            
        Returns:
            Any: Result from handler function or None if routing failed
        """
        tenant_schema = AccountTenantRouter.get_tenant_for_account(account_id)
        
        if not tenant_schema:
            logger.error(f"Cannot route webhook for account {account_id} - no tenant found")
            return None
        
        try:
            # Switch to the correct tenant schema and process
            with schema_context(tenant_schema):
                logger.info(f"Processing webhook for account {account_id} in tenant {tenant_schema}")
                return handler_func(account_id, *args, **kwargs)
                
        except Exception as e:
            logger.error(f"Error processing webhook for account {account_id} in tenant {tenant_schema}: {e}")
            return None
    
    @staticmethod
    def get_user_connection(account_id: str) -> Optional[UserChannelConnection]:
        """
        Get the UserChannelConnection for an account ID (must be called within tenant context)
        
        Args:
            account_id: UniPile account ID
            
        Returns:
            Optional[UserChannelConnection]: Connection object or None
        """
        try:
            return UserChannelConnection.objects.filter(
                unipile_account_id=account_id
            ).first()
        except Exception as e:
            logger.error(f"Error getting user connection for account {account_id}: {e}")
            return None


# Global router instance
account_router = AccountTenantRouter()