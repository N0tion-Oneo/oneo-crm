"""
Email Service
Wrapper around UniPile email client for email operations
"""
import logging
from typing import Dict, Any, List, Optional
from asgiref.sync import sync_to_async
from communications.unipile import unipile_service
from communications.models import Channel, UserChannelConnection
from django.conf import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for handling email operations via UniPile"""
    
    def __init__(self, channel: Optional[Channel] = None, account_identifier: Optional[str] = None):
        """
        Initialize email service
        
        Args:
            channel: Channel instance for this email account
            account_identifier: Email address of the account owner
        """
        self.channel = channel
        self.account_identifier = account_identifier
        
        # Use the global unipile_service like WhatsApp does
        self.client = unipile_service.get_client()
    
    async def get_folders(self, account_id: str) -> Dict[str, Any]:
        """Get email folders for account"""
        try:
            return await self.client.email.get_folders(account_id)
        except Exception as e:
            logger.error(f"Failed to get email folders: {e}")
            return {'folders': [], 'error': str(e)}
    
    async def get_emails(
        self, 
        account_id: str,
        folder: Optional[str] = None,
        thread_id: Optional[str] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
        meta_only: bool = False,
        include_headers: bool = False,
        before: Optional[str] = None,
        after: Optional[str] = None,
        from_email: Optional[str] = None,
        to_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get emails from account with various filters
        
        Args:
            account_id: UniPile account ID
            folder: Folder provider_id to filter
            thread_id: Thread ID to get specific conversation
            limit: Number of emails to fetch (max 250)
            cursor: Pagination cursor
            meta_only: Only fetch metadata (faster)
            include_headers: Include email headers
            before/after: Date filters
            from_email/to_email: Email address filters
            
        Returns:
            Dictionary with emails and cursor
        """
        try:
            params = {
                'account_id': account_id,
                'limit': min(limit, 250),  # Enforce API limit
                'meta_only': str(meta_only).lower()
            }
            
            if cursor:
                params['cursor'] = cursor
            if folder:
                params['folder'] = folder
            if thread_id:
                params['thread_id'] = thread_id
            if include_headers and not meta_only:
                params['include_headers'] = 'true'
            if before:
                params['before'] = before
            if after:
                params['after'] = after
            if from_email:
                params['from'] = from_email
            if to_email:
                params['to'] = to_email
            
            response = await self.client._make_request('GET', 'emails', params=params)
            
            # Ensure we have the expected structure
            if not isinstance(response, dict):
                response = {'items': [], 'cursor': None}
            
            return {
                'emails': response.get('items', []),
                'cursor': response.get('cursor'),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Failed to get emails: {e}")
            return {
                'emails': [],
                'cursor': None,
                'success': False,
                'error': str(e)
            }
    
    async def send_email(
        self,
        account_id: str,
        to: List[Dict[str, str]],
        subject: str,
        body: str,
        from_email: Optional[Dict[str, str]] = None,
        cc: Optional[List[Dict[str, str]]] = None,
        bcc: Optional[List[Dict[str, str]]] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """
        Send an email
        
        Args:
            account_id: UniPile account ID
            to: List of recipient dicts with 'identifier' and optional 'display_name'
            subject: Email subject
            body: HTML body content
            from_email: Sender info (optional, uses account default)
            cc/bcc: Additional recipients
            reply_to: Email ID to reply to
            attachments: List of attachment files
            
        Returns:
            Send result with tracking_id
        """
        try:
            # Prepare multipart form data
            data = {
                'account_id': account_id,
                'to': to,
                'subject': subject,
                'body': body
            }
            
            if from_email:
                data['from'] = from_email
            if cc:
                data['cc'] = cc
            if bcc:
                data['bcc'] = bcc
            if reply_to:
                data['reply_to'] = reply_to
            
            # Note: Attachments need special handling with multipart/form-data
            # This would need to be implemented in the UnipileClient
            
            response = await self.client._make_request('POST', 'emails', data=data)
            
            return {
                'success': True,
                'tracking_id': response.get('tracking_id'),
                'response': response
            }
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def update_email(
        self,
        email_id: str,
        account_id: Optional[str] = None,
        unread: Optional[bool] = None,
        folders: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Update an email (mark read/unread, move to folder)
        
        Args:
            email_id: UniPile email ID or provider ID
            account_id: Required when using provider ID
            unread: Mark as unread (True) or read (False)
            folders: Folder names to move email to
            
        Returns:
            Update result
        """
        try:
            data = {}
            if unread is not None:
                data['unread'] = unread
            if folders:
                data['folders'] = folders
            
            params = {}
            if account_id:
                params['account_id'] = account_id
            
            response = await self.client._make_request(
                'PUT', 
                f'emails/{email_id}',
                data=data,
                params=params
            )
            
            return {
                'success': True,
                'response': response
            }
            
        except Exception as e:
            logger.error(f"Failed to update email {email_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def delete_email(self, email_id: str, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Delete an email (move to trash)
        
        Args:
            email_id: UniPile email ID or provider ID
            account_id: Required when using provider ID
            
        Returns:
            Delete result
        """
        try:
            params = {}
            if account_id:
                params['account_id'] = account_id
            
            response = await self.client._make_request(
                'DELETE',
                f'emails/{email_id}',
                params=params
            )
            
            return {
                'success': True,
                'response': response
            }
            
        except Exception as e:
            logger.error(f"Failed to delete email {email_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_email(self, email_id: str, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a single email by ID
        
        Args:
            email_id: UniPile email ID or provider ID
            account_id: Required when using provider ID
            
        Returns:
            Email data
        """
        try:
            params = {}
            if account_id:
                params['account_id'] = account_id
            
            response = await self.client._make_request(
                'GET',
                f'emails/{email_id}',
                params=params
            )
            
            return {
                'success': True,
                'email': response
            }
            
        except Exception as e:
            logger.error(f"Failed to get email {email_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_account_email(self) -> Optional[str]:
        """
        Get the email address for this account
        
        Returns:
            Email address or None
        """
        if self.account_identifier:
            return self.account_identifier
        
        if self.channel and self.channel.connection_config:
            # Try to get from channel configuration
            return self.channel.connection_config.get('email_address')
        
        return None