"""
Account synchronization service for updating UserChannelConnection data
Fetches detailed account information from UniPile and stores it locally
"""
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from asgiref.sync import sync_to_async

from communications.unipile_sdk import unipile_service
from communications.models import UserChannelConnection

logger = logging.getLogger(__name__)


class AccountSyncService:
    """Service for synchronizing account details from UniPile API"""
    
    async def sync_account_details(self, connection: UserChannelConnection) -> Dict[str, Any]:
        """
        Fetch detailed account information from UniPile and update the connection
        
        Args:
            connection: UserChannelConnection instance to update
            
        Returns:
            Dict with sync results and updated information
        """
        try:
            logger.info(f"🔄 Syncing account details for {connection.unipile_account_id}")
            
            # Get UniPile client
            client = unipile_service.get_client()
            
            # Fetch account details from UniPile API
            account_data = await client.account.get_account(connection.unipile_account_id)
            
            if not account_data:
                return {
                    'success': False,
                    'error': 'No account data received from UniPile API'
                }
            
            # Update connection with comprehensive data
            await self._update_connection_data(connection, account_data)
            
            logger.info(f"✅ Successfully synced account details for {connection.unipile_account_id}")
            
            return {
                'success': True,
                'account_id': connection.unipile_account_id,
                'updated_fields': list(connection.connection_config.keys()) + list(connection.provider_config.keys()),
                'phone_number': account_data.get('connection_params', {}).get('im', {}).get('phone_number'),
                'account_type': account_data.get('type'),
                'messaging_status': self._get_messaging_status(account_data),
                'last_synced': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to sync account details for {connection.unipile_account_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'account_id': connection.unipile_account_id
            }
    
    async def _update_connection_data(self, connection: UserChannelConnection, account_data: Dict[str, Any]) -> None:
        """Update UserChannelConnection with comprehensive account data"""
        
        # Extract key information from account data
        phone_number = account_data.get('connection_params', {}).get('im', {}).get('phone_number')
        account_type = account_data.get('type')
        messaging_source = self._get_messaging_source(account_data)
        
        # Build comprehensive connection configuration
        connection_config = {
            'account_object_type': account_data.get('object'),
            'phone_number': phone_number,
            'account_type': account_type,
            'created_at': account_data.get('created_at'),
            'sources': account_data.get('sources', []),
            'groups': account_data.get('groups', []),
            'messaging_source_id': messaging_source.get('id') if messaging_source else None,
            'messaging_status': messaging_source.get('status') if messaging_source else None,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'full_account_response': account_data
        }
        
        # Build provider-specific configuration
        provider_config = self._build_provider_config(connection, account_data, phone_number)
        
        # Update connection fields
        connection.connection_config = connection_config
        connection.provider_config = provider_config
        
        # Update account name with phone number if available
        if phone_number:
            connection.account_name = f'{account_type.title()} ({phone_number})'
        
        # Save changes asynchronously
        await sync_to_async(connection.save)()
        
        logger.info(f"📊 Updated connection with {len(connection_config)} config keys and {len(provider_config)} provider keys")
    
    def _get_messaging_source(self, account_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract messaging source information from account data"""
        sources = account_data.get('sources', [])
        for source in sources:
            if 'MESSAGING' in source.get('id', ''):
                return source
        return None
    
    def _get_messaging_status(self, account_data: Dict[str, Any]) -> Optional[str]:
        """Get messaging status from account data"""
        messaging_source = self._get_messaging_source(account_data)
        return messaging_source.get('status') if messaging_source else None
    
    def _build_provider_config(self, connection: UserChannelConnection, account_data: Dict[str, Any], phone_number: str) -> Dict[str, Any]:
        """Build provider-specific configuration based on account type"""
        
        account_type = account_data.get('type', '').upper()
        messaging_enabled = self._get_messaging_status(account_data) == 'OK'
        
        base_config = {
            'provider_type': account_type,
            'messaging_enabled': messaging_enabled,
            'last_api_sync': datetime.now(timezone.utc).isoformat()
        }
        
        if account_type == 'WHATSAPP':
            return self._build_whatsapp_config(connection, account_data, phone_number, base_config)
        elif account_type in ['GOOGLE', 'OUTLOOK', 'MAIL']:
            return self._build_email_config(connection, account_data, base_config)
        elif account_type == 'LINKEDIN':
            return self._build_linkedin_config(connection, account_data, base_config)
        else:
            return base_config
    
    def _build_whatsapp_config(self, connection: UserChannelConnection, account_data: Dict[str, Any], phone_number: str, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Build WhatsApp-specific provider configuration"""
        
        country_code = self._extract_country_code(phone_number) if phone_number else None
        
        return {
            **base_config,
            'phone_number': phone_number,
            'webhook_events': [
                'message_received',
                'message_sent', 
                'message_delivered',
                'message_read'
            ],
            'features': {
                'send_messages': True,
                'receive_messages': True,
                'read_receipts': True,
                'delivery_status': True,
                'media_support': True,
                'group_messaging': len(account_data.get('groups', [])) > 0
            },
            'notification_preferences': {
                'new_message_alerts': True,
                'delivery_receipts': True,
                'read_receipts': True,
                'webhook_notifications': True
            },
            'rate_limits': {
                'messages_per_hour': connection.rate_limit_per_hour,
                'daily_limit': 1000,
                'burst_limit': 10
            },
            'account_metadata': {
                'display_name': account_data.get('name'),
                'country_code': country_code,
                'account_creation_date': account_data.get('created_at'),
                'groups_count': len(account_data.get('groups', [])),
                'sources_count': len(account_data.get('sources', []))
            }
        }
    
    def _build_email_config(self, connection: UserChannelConnection, account_data: Dict[str, Any], base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Build email-specific provider configuration"""
        
        return {
            **base_config,
            'features': {
                'send_emails': True,
                'receive_emails': True,
                'folder_management': True,
                'attachments': True,
                'html_emails': True
            },
            'notification_preferences': {
                'new_email_alerts': True,
                'delivery_receipts': True,
                'webhook_notifications': True
            },
            'account_metadata': {
                'display_name': account_data.get('name'),
                'account_creation_date': account_data.get('created_at')
            }
        }
    
    def _build_linkedin_config(self, connection: UserChannelConnection, account_data: Dict[str, Any], base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Build LinkedIn-specific provider configuration"""
        
        return {
            **base_config,
            'features': {
                'messaging': True,
                'job_postings': True,
                'candidate_search': True,
                'connection_requests': True,
                'inmail': True
            },
            'notification_preferences': {
                'new_message_alerts': True,
                'application_notifications': True,
                'webhook_notifications': True
            },
            'account_metadata': {
                'display_name': account_data.get('name'),
                'account_creation_date': account_data.get('created_at')
            }
        }
    
    def _extract_country_code(self, phone_number: str) -> Optional[str]:
        """Extract country code from phone number"""
        if not phone_number:
            return None
        
        # Common country code patterns
        country_codes = {
            '1': '+1',      # US/Canada
            '27': '+27',    # South Africa
            '44': '+44',    # UK
            '33': '+33',    # France
            '49': '+49',    # Germany
            '61': '+61',    # Australia
        }
        
        for code, formatted in country_codes.items():
            if phone_number.startswith(code):
                return formatted
        
        # Fallback: return first 1-3 digits as country code
        if len(phone_number) >= 2:
            return f'+{phone_number[:2]}'
        
        return None
    
    async def sync_all_connections(self) -> Dict[str, Any]:
        """Sync account details for all active connections"""
        try:
            # Get all active connections
            connections = await sync_to_async(list)(
                UserChannelConnection.objects.filter(
                    is_active=True,
                    auth_status='authenticated',
                    account_status='active'
                ).exclude(unipile_account_id='')
            )
            
            logger.info(f"🔄 Syncing account details for {len(connections)} connections")
            
            results = []
            successful_syncs = 0
            failed_syncs = 0
            
            for connection in connections:
                try:
                    result = await self.sync_account_details(connection)
                    results.append(result)
                    
                    if result.get('success'):
                        successful_syncs += 1
                    else:
                        failed_syncs += 1
                        
                except Exception as e:
                    logger.error(f"❌ Failed to sync connection {connection.id}: {e}")
                    results.append({
                        'success': False,
                        'error': str(e),
                        'account_id': connection.unipile_account_id
                    })
                    failed_syncs += 1
            
            logger.info(f"✅ Batch sync completed: {successful_syncs} successful, {failed_syncs} failed")
            
            return {
                'success': True,
                'total_connections': len(connections),
                'successful_syncs': successful_syncs,
                'failed_syncs': failed_syncs,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to sync all connections: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Global service instance
account_sync_service = AccountSyncService()