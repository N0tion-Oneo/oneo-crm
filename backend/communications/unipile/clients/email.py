"""
UniPile Email Client
Handles email operations including sending, receiving, and folder management
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class UnipileEmailClient:
    """Email-specific UniPile client for advanced email features"""
    
    def __init__(self, client):
        self.client = client
    
    async def get_folders(self, account_id: str) -> Dict[str, Any]:
        """Get email folders for account"""
        try:
            params = {'account_id': account_id}
            response = await self.client._make_request('GET', 'mails/folders', params=params)
            return response
        except Exception as e:
            logger.error(f"Failed to get email folders: {e}")
            raise
    
    async def get_emails(
        self, 
        account_id: str,
        folder: str = "INBOX",
        limit: int = 50,
        cursor: Optional[str] = None,
        unread_only: bool = False
    ) -> Dict[str, Any]:
        """Get emails from specific folder"""
        try:
            params = {
                'account_id': account_id,
                'folder': folder,
                'limit': limit,
                'unread_only': str(unread_only).lower()  # Convert boolean to string for URL parameters
            }
            if cursor:
                params['cursor'] = cursor
                
            response = await self.client._make_request('GET', 'emails', params=params)
            return response
        except Exception as e:
            logger.error(f"Failed to get emails: {e}")
            raise
    
    async def send_email(
        self, 
        account_id: str,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict]] = None,
        is_html: bool = True
    ) -> Dict[str, Any]:
        """Send email"""
        try:
            data = {
                'account_id': account_id,
                'to': to,
                'subject': subject,
                'body': body,
                'is_html': is_html
            }
            if cc:
                data['cc'] = cc
            if bcc:
                data['bcc'] = bcc
            if attachments:
                data['attachments'] = attachments
                
            response = await self.client._make_request('POST', 'emails', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise
    
    async def mark_as_read(self, account_id: str, email_ids: List[str]) -> Dict[str, Any]:
        """Mark emails as read using individual email update API calls"""
        try:
            results = []
            
            for email_id in email_ids:
                # Update each email individually using PUT /emails/{email_id}
                data = {
                    'is_read': True  # Mark as read
                }
                
                try:
                    response = await self.client._make_request('PUT', f'emails/{email_id}', data=data)
                    results.append({
                        'email_id': email_id,
                        'success': True,
                        'response': response
                    })
                except Exception as email_error:
                    logger.error(f"Failed to mark email {email_id} as read: {email_error}")
                    results.append({
                        'email_id': email_id,
                        'success': False,
                        'error': str(email_error)
                    })
            
            # Return summary of results
            successful_count = sum(1 for result in results if result['success'])
            return {
                'account_id': account_id,
                'total_emails': len(email_ids),
                'successful': successful_count,
                'failed': len(email_ids) - successful_count,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Failed to mark emails as read: {e}")
            raise
    
    async def move_to_folder(
        self, 
        account_id: str, 
        email_ids: List[str], 
        folder: str
    ) -> Dict[str, Any]:
        """Move emails to folder"""
        try:
            data = {
                'account_id': account_id,
                'email_ids': email_ids,
                'folder': folder
            }
            response = await self.client._make_request('POST', 'mails/move', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to move emails to folder {folder}: {e}")
            raise
    
    async def delete_emails(self, account_id: str, email_ids: List[str]) -> Dict[str, Any]:
        """Delete emails"""
        try:
            data = {
                'account_id': account_id,
                'email_ids': email_ids
            }
            response = await self.client._make_request('DELETE', 'mails', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to delete emails: {e}")
            raise
    
    async def create_draft(
        self, 
        account_id: str,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create email draft"""
        try:
            data = {
                'account_id': account_id,
                'to': to,
                'subject': subject,
                'body': body
            }
            if cc:
                data['cc'] = cc
            if bcc:
                data['bcc'] = bcc
                
            response = await self.client._make_request('POST', 'mails/drafts', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to create draft: {e}")
            raise