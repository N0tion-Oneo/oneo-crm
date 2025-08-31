"""
Email Fetcher - Retrieves emails for specific email addresses

Handles fetching historical email data from UniPile for record-specific email addresses.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)


class EmailFetcher:
    """Fetches emails for specific email addresses from UniPile"""
    
    def __init__(self, unipile_client):
        """
        Initialize with UniPile client
        
        Args:
            unipile_client: Instance of UnipileClient with email capabilities
        """
        self.unipile_client = unipile_client
    
    def fetch_emails_for_addresses(
        self,
        email_addresses: List[str],
        account_id: str,
        days_back: int = 30,
        max_emails: int = 500
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch historical emails for specific email addresses
        
        Args:
            email_addresses: List of email addresses to fetch emails for
            account_id: UniPile account ID for the email connection
            days_back: Number of days of history to fetch (0 = all)
            max_emails: Maximum number of emails to fetch per address
            
        Returns:
            Dict mapping email addresses to their email threads:
            {
                'john@example.com': [
                    {
                        'id': 'thread_id',
                        'subject': 'Email subject',
                        'messages': [...],
                        'participants': [...],
                        ...
                    }
                ]
            }
        """
        email_data = {}
        
        # Calculate date filter
        after_date = None
        if days_back > 0:
            after_date = (timezone.now() - timedelta(days=days_back)).isoformat()
        
        for email_address in email_addresses:
            try:
                threads = self._fetch_threads_for_email(
                    email_address,
                    account_id,
                    after_date,
                    max_emails
                )
                
                if threads:
                    email_data[email_address] = threads
                    logger.info(f"Fetched {len(threads)} threads for {email_address}")
                else:
                    email_data[email_address] = []
                    logger.info(f"No threads found for {email_address}")
                    
            except Exception as e:
                logger.error(f"Failed to fetch emails for {email_address}: {e}")
                email_data[email_address] = []
        
        return email_data
    
    def _fetch_threads_for_email(
        self,
        email_address: str,
        account_id: str,
        after_date: Optional[str],
        max_threads: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch email threads involving a specific email address
        
        Args:
            email_address: Email address to search for
            account_id: UniPile account ID
            after_date: Optional date filter (ISO format)
            max_threads: Maximum number of threads to fetch
            
        Returns:
            List of email thread dictionaries
        """
        from asgiref.sync import async_to_sync
        
        threads = []
        cursor = None
        total_fetched = 0
        
        while total_fetched < max_threads:
            try:
                # Build query parameters
                params = {
                    'account_id': account_id,
                    'limit': min(50, max_threads - total_fetched)  # Batch size
                }
                
                if cursor:
                    params['cursor'] = cursor
                
                if after_date:
                    params['after'] = after_date
                
                # Search for threads involving this email
                # Fetch emails from UniPile with the email address filter
                response = async_to_sync(self.unipile_client.email.get_emails)(
                    account_id=account_id,
                    limit=params.get('limit', 50),
                    cursor=params.get('cursor'),
                    folder='INBOX',  # You might want to search other folders too
                    any_email=email_address  # Filter for emails to/from this address
                )
                
                if not response or 'items' not in response:
                    break
                
                # Process each thread
                for thread_data in response['items']:
                    # Check if email is actually involved (to, from, cc)
                    if self._is_email_involved(email_address, thread_data):
                        # The email data from get_emails already contains everything we need
                        # No need to fetch additional thread details
                        threads.append(thread_data)
                        total_fetched += 1
                        
                        if total_fetched >= max_threads:
                            break
                
                # Check for more pages
                cursor = response.get('cursor')
                if not cursor:
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching threads: {e}")
                break
        
        return threads
    
    def _is_email_involved(self, email_address: str, thread_data: Dict[str, Any]) -> bool:
        """
        Check if an email address is involved in a thread
        
        Args:
            email_address: Email to check for
            thread_data: Thread data from UniPile
            
        Returns:
            True if email is involved in the thread
        """
        email_lower = email_address.lower()
        
        # Check participants
        for participant in thread_data.get('participants', []):
            if participant.get('email', '').lower() == email_lower:
                return True
        
        # Check from/to/cc fields if available
        if thread_data.get('from', {}).get('email', '').lower() == email_lower:
            return True
        
        for recipient in thread_data.get('to', []):
            if recipient.get('email', '').lower() == email_lower:
                return True
        
        for cc in thread_data.get('cc', []):
            if cc.get('email', '').lower() == email_lower:
                return True
        
        return False
    
    def _fetch_thread_details(
        self,
        thread_id: str,
        account_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch full details of an email thread including messages
        
        Args:
            thread_id: UniPile thread ID
            account_id: UniPile account ID
            
        Returns:
            Complete thread data with messages
        """
        from asgiref.sync import async_to_sync
        
        try:
            # Fetch the full thread
            thread = async_to_sync(self.unipile_client.email.get_thread)(
                thread_id=thread_id,
                account_id=account_id
            )
            
            if not thread:
                return None
            
            # Fetch messages for this thread
            messages = self._fetch_thread_messages(thread_id, account_id)
            
            # Combine thread and messages
            thread['messages'] = messages
            
            return thread
            
        except Exception as e:
            logger.error(f"Failed to fetch thread details for {thread_id}: {e}")
            return None
    
    def _fetch_thread_messages(
        self,
        thread_id: str,
        account_id: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch all messages in a thread
        
        Args:
            thread_id: UniPile thread ID
            account_id: UniPile account ID
            
        Returns:
            List of message dictionaries
        """
        from asgiref.sync import async_to_sync
        
        messages = []
        cursor = None
        
        while True:
            try:
                params = {
                    'thread_id': thread_id,
                    'account_id': account_id,
                    'limit': 50
                }
                
                if cursor:
                    params['cursor'] = cursor
                
                # Fetch messages from thread
                response = async_to_sync(self.unipile_client.email.get_thread_messages)(
                    **params
                )
                
                if not response or 'items' not in response:
                    break
                
                messages.extend(response['items'])
                
                # Check for more pages
                cursor = response.get('cursor')
                if not cursor:
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching messages for thread {thread_id}: {e}")
                break
        
        return messages
    
    def fetch_single_email(
        self,
        email_id: str,
        account_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a single email by ID
        
        Args:
            email_id: UniPile email ID
            account_id: UniPile account ID
            
        Returns:
            Email data or None
        """
        from asgiref.sync import async_to_sync
        
        try:
            email = async_to_sync(self.unipile_client.email.get_email)(
                email_id=email_id,
                account_id=account_id
            )
            return email
            
        except Exception as e:
            logger.error(f"Failed to fetch email {email_id}: {e}")
            return None