"""
Email Fetcher V2 - Optimized email fetching that properly uses thread_id

Groups emails by thread_id and uses the complete email data from get_emails response.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from django.utils import timezone
from collections import defaultdict

logger = logging.getLogger(__name__)


class EmailFetcherV2:
    """Optimized email fetcher that groups by thread_id"""
    
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
        days_back: int = 0,
        max_emails: int = 500
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch emails and group them by thread
        
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
                        'thread_id': 'thread_123',
                        'subject': 'Thread subject',
                        'messages': [email1, email2, ...],
                        'participants': [...],
                        'latest_date': '2025-01-01T00:00:00Z'
                    }
                ]
            }
        """
        logger.info(f"=== EMAIL SYNC START ===")
        logger.info(f"Account ID: {account_id}")
        logger.info(f"Email addresses to sync: {email_addresses}")
        logger.info(f"Days back: {days_back} (0=all history)")
        logger.info(f"Max emails per address: {max_emails}")
        
        result = {}
        
        # Calculate date filter
        after_date = None
        if days_back > 0:
            after_date = (timezone.now() - timedelta(days=days_back)).isoformat()
            logger.info(f"Date filter: After {after_date}")
        else:
            logger.info(f"Date filter: None (fetching all history)")
        
        for email_address in email_addresses:
            logger.info(f"\n--- Processing email: {email_address} ---")
            try:
                threads = self._fetch_and_group_emails(
                    email_address,
                    account_id,
                    after_date,
                    max_emails
                )
                
                result[email_address] = threads
                
                # Log summary statistics
                total_messages = sum(len(t['messages']) for t in threads)
                logger.info(f"✓ SUCCESS for {email_address}:")
                logger.info(f"  - Threads: {len(threads)}")
                logger.info(f"  - Total messages: {total_messages}")
                if threads:
                    logger.info(f"  - Latest thread: {threads[0].get('subject', 'No subject')[:50]}")
                    
            except Exception as e:
                logger.error(f"✗ FAILED for {email_address}: {e}", exc_info=True)
                result[email_address] = []
        
        logger.info(f"=== EMAIL SYNC COMPLETE ===")
        return result
    
    def _fetch_and_group_emails(
        self,
        email_address: str,
        account_id: str,
        after_date: Optional[str],
        max_emails: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch emails and group them by thread_id
        
        Args:
            email_address: Email address to search for
            account_id: UniPile account ID
            after_date: Optional date filter (ISO format)
            max_emails: Maximum number of emails to fetch (0 = no limit)
            
        Returns:
            List of thread dictionaries with grouped emails
        """
        from asgiref.sync import async_to_sync
        
        # Collect all emails
        all_emails = []
        cursor = None
        total_fetched = 0
        page = 1
        
        # If max_emails is 0, fetch everything
        fetch_all = (max_emails == 0)
        
        while fetch_all or total_fetched < max_emails:
            try:
                # Determine batch size
                if fetch_all:
                    batch_size = 100  # Use max batch size when fetching all
                else:
                    batch_size = min(100, max_emails - total_fetched)
                
                # Build request params
                params = {
                    'account_id': account_id,
                    'any_email': email_address,
                    'limit': batch_size
                }
                
                if cursor:
                    params['cursor'] = cursor
                
                logger.info(f"  Fetching page {page} for {email_address} (batch size: {batch_size}, cursor: {cursor[:20] if cursor else 'None'}...)")
                
                response = async_to_sync(self.unipile_client.email.get_emails)(**params)
                
                if not response or 'items' not in response:
                    logger.info(f"  No response or items for page {page}")
                    break
                
                emails = response.get('items', [])
                if not emails:
                    logger.debug(f"No emails in page {page}")
                    break
                
                # Filter to ensure email is actually involved
                batch_added = 0
                for email in emails:
                    if self._is_email_involved(email_address, email):
                        all_emails.append(email)
                        batch_added += 1
                        total_fetched += 1
                        
                        # Only check limit if we're not fetching all
                        if not fetch_all and total_fetched >= max_emails:
                            break
                
                logger.info(f"  Page {page}: Added {batch_added} emails (total: {total_fetched})")
                
                # Check for more pages via cursor
                cursor = response.get('cursor')
                if not cursor:
                    logger.info(f"  No cursor returned - all emails fetched")
                    break
                
                # If we're not fetching all and hit the limit, stop
                if not fetch_all and total_fetched >= max_emails:
                    break
                    
                page += 1
                    
            except Exception as e:
                logger.error(f"Error fetching emails on page {page}: {e}")
                break
        
        logger.info(f"Fetched {total_fetched} emails for {email_address} across {page} pages")
        
        # Group emails by thread_id
        threads_dict = defaultdict(list)
        
        for email in all_emails:
            thread_id = email.get('thread_id')
            
            # If no thread_id, use message_id as thread_id (single email thread)
            if not thread_id:
                thread_id = email.get('message_id') or email.get('id')
            
            threads_dict[thread_id].append(email)
        
        # Convert to list of thread objects
        threads = []
        for thread_id, emails in threads_dict.items():
            # Sort emails by date
            emails.sort(key=lambda x: x.get('date', ''))
            
            # Extract thread subject from first email
            subject = emails[0].get('subject', 'No subject')
            
            # Collect all participants
            participants = self._extract_participants(emails)
            
            # Get latest date
            latest_date = emails[-1].get('date', '')
            
            thread = {
                'thread_id': thread_id,
                'subject': subject,
                'messages': emails,
                'participants': participants,
                'latest_date': latest_date,
                'message_count': len(emails)
            }
            
            threads.append(thread)
        
        # Sort threads by latest date (newest first)
        threads.sort(key=lambda x: x.get('latest_date', ''), reverse=True)
        
        return threads
    
    def _is_email_involved(self, email_address: str, email_data: Dict[str, Any]) -> bool:
        """
        Check if an email address is involved in an email
        
        Args:
            email_address: Email to check for
            email_data: Email data from UniPile
            
        Returns:
            True if email is involved in the email
        """
        email_lower = email_address.lower()
        
        # Check from
        from_attendee = email_data.get('from_attendee', {})
        if from_attendee.get('identifier', '').lower() == email_lower:
            return True
        
        # Check to
        for attendee in email_data.get('to_attendees', []):
            if attendee.get('identifier', '').lower() == email_lower:
                return True
        
        # Check cc
        for attendee in email_data.get('cc_attendees', []):
            if attendee.get('identifier', '').lower() == email_lower:
                return True
        
        # Check bcc
        for attendee in email_data.get('bcc_attendees', []):
            if attendee.get('identifier', '').lower() == email_lower:
                return True
        
        return False
    
    def _extract_participants(self, emails: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Extract unique participants from a list of emails
        
        Args:
            emails: List of email dictionaries
            
        Returns:
            List of unique participant dictionaries
        """
        participants_set = set()
        participants = []
        
        for email in emails:
            # Add from
            from_attendee = email.get('from_attendee', {})
            if from_attendee:
                identifier = from_attendee.get('identifier', '')
                if identifier and identifier not in participants_set:
                    participants_set.add(identifier)
                    participants.append({
                        'email': identifier,
                        'name': from_attendee.get('display_name', ''),
                        'type': 'from'
                    })
            
            # Add to/cc/bcc
            for field, field_type in [
                ('to_attendees', 'to'),
                ('cc_attendees', 'cc'),
                ('bcc_attendees', 'bcc')
            ]:
                for attendee in email.get(field, []):
                    identifier = attendee.get('identifier', '')
                    if identifier and identifier not in participants_set:
                        participants_set.add(identifier)
                        participants.append({
                            'email': identifier,
                            'name': attendee.get('display_name', ''),
                            'type': field_type
                        })
        
        return participants