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
            response = await self.client._make_request('GET', 'folders', params=params)
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
        unread_only: bool = False,
        any_email: Optional[str] = None,
        to: Optional[str] = None,
        from_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get emails from specific folder
        
        Args:
            account_id: UniPile account ID
            folder: Folder to fetch from (default INBOX)
            limit: Number of emails to return
            cursor: Pagination cursor
            unread_only: Only return unread emails
            any_email: Filter for emails to/from specific address(es)
            to: Filter for emails to specific address
            from_email: Filter for emails from specific address
        """
        try:
            params = {
                'account_id': account_id,
                'folder': folder,
                'limit': limit,
                'unread_only': str(unread_only).lower()  # Convert boolean to string for URL parameters
            }
            if cursor:
                params['cursor'] = cursor
            if any_email:
                params['any_email'] = any_email
            if to:
                params['to'] = to
            if from_email:
                params['from'] = from_email
                
            response = await self.client._make_request('GET', 'emails', params=params)
            return response
        except Exception as e:
            logger.error(f"Failed to get emails: {e}")
            raise
    
    async def update_email_read_status(
        self,
        email_id: str,
        unread: bool,
        account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update the read/unread status of an email
        
        Args:
            email_id: The UniPile email ID or provider ID
            unread: True to mark as unread, False to mark as read
            account_id: The account ID (required if using provider ID)
            
        Returns:
            Response from UniPile API
        """
        try:
            # Build the update payload
            data = {
                'unread': unread
            }
            
            # Add account_id to params if provided
            params = {}
            if account_id:
                params['account_id'] = account_id
            
            # Make the API request
            response = await self.client._make_request(
                'PUT', 
                f'emails/{email_id}', 
                data=data,
                params=params
            )
            
            logger.info(f"Updated email {email_id} read status - unread: {unread}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to update email read status for {email_id}: {e}")
            raise
    
    async def send_email(
        self, 
        account_id: str,
        to: List[Dict[str, str]],  # Changed to accept dict format
        subject: str,
        body: str,
        cc: Optional[List[Dict[str, str]]] = None,  # Changed to accept dict format
        bcc: Optional[List[Dict[str, str]]] = None,  # Changed to accept dict format
        reply_to: Optional[str] = None,  # Email ID to reply to (for threading)
        thread_id: Optional[str] = None,  # DEPRECATED - use reply_to instead
        attachments: Optional[List[Dict]] = None,
        is_html: bool = True
    ) -> Dict[str, Any]:
        """Send email
        
        Args:
            account_id: UniPile account ID
            to: List of recipient dicts with 'identifier' and optional 'display_name'
            subject: Email subject
            body: Email body (HTML or plain text)
            cc: List of CC recipient dicts
            bcc: List of BCC recipient dicts
            reply_to: UniPile or provider email ID to reply to (for threading)
            thread_id: DEPRECATED - not supported by UniPile, use reply_to instead
            attachments: List of attachment dicts with 'data' (bytes), 'filename', and 'content_type'
            is_html: Whether body is HTML
        """
        try:
            import json
            
            # Build the form data payload according to UniPile API spec
            data = {
                'account_id': account_id,
                'to': json.dumps(to),  # Convert to JSON string for form data
                'body': body,
                'is_html': str(is_html).lower()
            }
            # Always include subject - UniPile needs it for both new emails and replies
            # Even when replying, we need to send the subject (e.g., "Re: Original Subject")
            data['subject'] = subject if subject else 'No Subject'
            if cc:
                data['cc'] = json.dumps(cc)
            if bcc:
                data['bcc'] = json.dumps(bcc)
            if reply_to:
                data['reply_to'] = reply_to  # Add reply_to for email threading
            # Note: thread_id is not supported by UniPile API, only reply_to is used
            
            # Prepare files if attachments are provided
            files = None
            if attachments:
                files = {}
                # For multiple attachments, we need to track them differently
                # The UniPile API expects attachments as an array field in multipart/form-data
                # We'll try using indexed field names for multiple files
                for i, attachment in enumerate(attachments):
                    # Each attachment should have 'data' (bytes), 'filename', and optionally 'content_type'
                    file_data = attachment.get('data')
                    filename = attachment.get('filename', f'attachment_{i}')
                    content_type = attachment.get('content_type', 'application/octet-stream')
                    
                    if file_data:
                        # Convert base64 to bytes if needed
                        if isinstance(file_data, str):
                            import base64
                            try:
                                file_data = base64.b64decode(file_data)
                            except Exception as e:
                                logger.warning(f"Failed to decode base64 for attachment {filename}: {e}")
                                continue
                        
                        # Use indexed field names for multiple attachments
                        # UniPile might expect attachments[0], attachments[1], etc. for arrays
                        field_name = f'attachments[{i}]' if len(attachments) > 1 else 'attachments'
                        files[field_name] = (filename, file_data, content_type)
            
            # Use multipart/form-data if we have attachments
            if files:
                logger.info(f"📧 Sending with attachments using form data")
                logger.info(f"📧 Form data subject: {data.get('subject')}")
                response = await self.client._make_request('POST', 'emails', data=data, files=files)
            else:
                # For non-attachment emails, use regular JSON
                json_data = {
                    'account_id': account_id,
                    'to': to,
                    'subject': subject if subject else 'No Subject',  # Always include subject
                    'body': body,
                    'is_html': is_html
                }
                if cc:
                    json_data['cc'] = cc
                if bcc:
                    json_data['bcc'] = bcc
                if reply_to:
                    json_data['reply_to'] = reply_to
                
                logger.info(f"📧 Sending without attachments using JSON")
                logger.info(f"📧 JSON subject: {json_data.get('subject')}")
                logger.info(f"📧 Has reply_to: {bool(reply_to)}")
                    
                response = await self.client._make_request('POST', 'emails', data=json_data)
                
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
                # According to UniPile docs, use 'unread: false' to mark as read
                data = {
                    'unread': False  # Mark as read (UniPile uses 'unread' field, not 'is_read')
                }
                
                try:
                    # Include account_id as query parameter as per documentation
                    params = {'account_id': account_id} if account_id else None
                    response = await self.client._make_request('PUT', f'emails/{email_id}', data=data, params=params)
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
        """Move emails to folder using update endpoint"""
        try:
            # UniPile uses the update endpoint with folders parameter to move emails
            results = []
            
            for email_id in email_ids:
                try:
                    data = {
                        'folders': [folder]  # UniPile expects folder names array
                    }
                    response = await self.client._make_request('PUT', f'emails/{email_id}', data=data)
                    results.append({
                        'email_id': email_id,
                        'success': True,
                        'response': response
                    })
                except Exception as email_error:
                    logger.error(f"Failed to move email {email_id} to folder {folder}: {email_error}")
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
            logger.error(f"Failed to move emails to folder {folder}: {e}")
            raise
    
    async def delete_emails(self, account_id: str, email_ids: List[str]) -> Dict[str, Any]:
        """Delete emails using individual delete API calls"""
        try:
            results = []
            
            for email_id in email_ids:
                try:
                    # Delete each email individually using DELETE /emails/{email_id}
                    response = await self.client._make_request('DELETE', f'emails/{email_id}')
                    results.append({
                        'email_id': email_id,
                        'success': True,
                        'response': response
                    })
                except Exception as email_error:
                    logger.error(f"Failed to delete email {email_id}: {email_error}")
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
                
            response = await self.client._make_request('POST', 'drafts', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to create draft: {e}")
            raise