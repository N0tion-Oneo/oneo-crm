"""
UniPile Account Management Client
Handles account connections, authentication, and management
"""
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class UnipileAccountClient:
    """UniPile account management client"""
    
    def __init__(self, client):
        self.client = client
    
    async def get_accounts(self) -> List[Dict[str, Any]]:
        """Get all connected accounts"""
        try:
            response = await self.client._make_request('GET', 'accounts')
            # UniPile returns a list directly, not wrapped in 'accounts' key
            return response if isinstance(response, list) else response.get('accounts', [])
        except Exception as e:
            logger.error(f"Failed to get accounts: {e}")
            raise
    
    async def request_hosted_link(self, 
                                  providers: Union[str, List[str]], 
                                  success_redirect_url: Optional[str] = None,
                                  failure_redirect_url: Optional[str] = None,
                                  name: Optional[str] = None,
                                  notify_url: Optional[str] = None,
                                  account_id: Optional[str] = None) -> Dict[str, Any]:
        """Request hosted authentication link with proper UniPile format"""
        try:
            # Convert provider to UniPile format (exact provider names from UniPile docs)
            # Supported: LINKEDIN | WHATSAPP | INSTAGRAM | MESSENGER | TELEGRAM | GOOGLE | OUTLOOK | MAIL | TWITTER
            if isinstance(providers, str):
                provider_lower = providers.lower()
                if provider_lower == 'linkedin':
                    provider_list = ['LINKEDIN']
                elif provider_lower in ['gmail', 'google']:
                    provider_list = ['GOOGLE']
                elif provider_lower == 'outlook':
                    provider_list = ['OUTLOOK']
                elif provider_lower in ['email', 'mail']:
                    provider_list = ['MAIL']
                elif provider_lower == 'whatsapp':
                    provider_list = ['WHATSAPP']
                elif provider_lower == 'instagram':
                    provider_list = ['INSTAGRAM']
                elif provider_lower in ['messenger', 'facebook']:
                    provider_list = ['MESSENGER']
                elif provider_lower == 'telegram':
                    provider_list = ['TELEGRAM']
                elif provider_lower == 'twitter':
                    provider_list = ['TWITTER']
                else:
                    # For unknown providers, try uppercase
                    provider_list = [providers.upper()]
            else:
                # Convert list of providers
                provider_list = []
                for p in providers:
                    p_lower = p.lower()
                    if p_lower == 'linkedin':
                        provider_list.append('LINKEDIN')
                    elif p_lower in ['gmail', 'google']:
                        provider_list.append('GOOGLE')
                    elif p_lower == 'outlook':
                        provider_list.append('OUTLOOK')
                    elif p_lower in ['email', 'mail']:
                        provider_list.append('MAIL')
                    elif p_lower == 'whatsapp':
                        provider_list.append('WHATSAPP')
                    elif p_lower == 'instagram':
                        provider_list.append('INSTAGRAM')
                    elif p_lower in ['messenger', 'facebook']:
                        provider_list.append('MESSENGER')
                    elif p_lower == 'telegram':
                        provider_list.append('TELEGRAM')
                    elif p_lower == 'twitter':
                        provider_list.append('TWITTER')
                    else:
                        provider_list.append(p.upper())
            
            # Set expiration to 24 hours from now with proper ISO format
            expires_dt = datetime.now(timezone.utc) + timedelta(days=1)
            expires_on = expires_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            
            # Create the request data
            data = {
                'type': 'reconnect' if account_id else 'create',
                'api_url': self.client.dsn,  # Use the DSN as the API URL
                'expiresOn': expires_on,
                'providers': provider_list
            }
            
            if account_id:
                data['reconnect_account'] = account_id
            
            if name:
                data['name'] = name
            
            if success_redirect_url:
                data['success_redirect_url'] = success_redirect_url
                
            if failure_redirect_url:
                data['failure_redirect_url'] = failure_redirect_url
                
            if notify_url:
                data['notify_url'] = notify_url
                
            response = await self.client._make_request('POST', 'hosted/accounts/link', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to request hosted link for {providers}: {e}")
            raise
    
    async def get_account(self, account_id: str) -> Dict[str, Any]:
        """Get specific account details"""
        try:
            response = await self.client._make_request('GET', f'accounts/{account_id}')
            return response
        except Exception as e:
            logger.error(f"Failed to get account {account_id}: {e}")
            raise
    
    async def connect_linkedin(self, username: str, password: str) -> Dict[str, Any]:
        """Connect LinkedIn account"""
        try:
            data = {
                'provider': 'linkedin',
                'username': username,
                'password': password
            }
            response = await self.client._make_request('POST', 'accounts/connect', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to connect LinkedIn account: {e}")
            raise
    
    async def connect_whatsapp(self) -> Dict[str, Any]:
        """Connect WhatsApp account (returns QR code)"""
        try:
            data = {'provider': 'whatsapp'}
            response = await self.client._make_request('POST', 'accounts/connect', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to connect WhatsApp account: {e}")
            raise
    
    async def connect_gmail(self, email: str, password: str) -> Dict[str, Any]:
        """Connect Gmail account"""
        try:
            data = {
                'provider': 'gmail',
                'email': email,
                'password': password
            }
            response = await self.client._make_request('POST', 'accounts/connect', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to connect Gmail account: {e}")
            raise
    
    async def connect_outlook(self, email: str, password: str) -> Dict[str, Any]:
        """Connect Outlook account"""
        try:
            data = {
                'provider': 'outlook',
                'email': email,
                'password': password
            }
            response = await self.client._make_request('POST', 'accounts/connect', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to connect Outlook account: {e}")
            raise
    
    async def disconnect_account(self, account_id: str) -> Dict[str, Any]:
        """Disconnect account"""
        try:
            response = await self.client._make_request('DELETE', f'accounts/{account_id}')
            return response
        except Exception as e:
            logger.error(f"Failed to disconnect account {account_id}: {e}")
            raise
    
    async def get_account_status(self, account_id: str) -> Dict[str, Any]:
        """Get account connection status"""
        try:
            response = await self.client._make_request('GET', f'accounts/{account_id}/status')
            return response
        except Exception as e:
            logger.error(f"Failed to get account status {account_id}: {e}")
            raise
    
    async def restart_account(self, account_id: str) -> Dict[str, Any]:
        """Restart an account"""
        try:
            response = await self.client._make_request('POST', f'accounts/{account_id}/restart')
            return response
        except Exception as e:
            logger.error(f"Failed to restart account {account_id}: {e}")
            raise
    
    async def resync_account(self, account_id: str) -> Dict[str, Any]:
        """Resynchronize account messaging data"""
        try:
            # Correct endpoint per Unipile API docs: GET /api/v1/accounts/{account_id}/sync
            response = await self.client._make_request('GET', f'accounts/{account_id}/sync')
            return response
        except Exception as e:
            logger.error(f"Failed to resync account {account_id}: {e}")
            raise
    
    async def solve_checkpoint(self, account_id: str, code: str) -> Dict[str, Any]:
        """Solve a code checkpoint"""
        try:
            data = {'code': code}
            response = await self.client._make_request('POST', f'accounts/{account_id}/checkpoint/solve', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to solve checkpoint for account {account_id}: {e}")
            raise
    
    async def resend_checkpoint(self, account_id: str) -> Dict[str, Any]:
        """Resend checkpoint notification"""
        try:
            response = await self.client._make_request('POST', f'accounts/{account_id}/checkpoint/resend')
            return response
        except Exception as e:
            logger.error(f"Failed to resend checkpoint for account {account_id}: {e}")
            raise
    
    async def reconnect_account(self, account_id: str) -> Dict[str, Any]:
        """Reconnect an account"""
        try:
            response = await self.client._make_request('POST', f'accounts/{account_id}/reconnect')
            return response
        except Exception as e:
            logger.error(f"Failed to reconnect account {account_id}: {e}")
            raise