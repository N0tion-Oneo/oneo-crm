"""
Email Thread Synchronization
Groups emails by thread_id for conversation view
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from asgiref.sync import async_to_sync

from communications.models import Conversation, Channel
from ..service import EmailService
from .config import EMAIL_SYNC_CONFIG

logger = logging.getLogger(__name__)


class EmailThreadSyncService:
    """Service for syncing email threads as conversations"""
    
    def __init__(
        self,
        channel: Channel,
        connection: Optional[Any] = None,
        progress_tracker: Optional[Any] = None
    ):
        self.channel = channel
        self.connection = connection
        self.progress_tracker = progress_tracker
        self.service = EmailService(channel=channel)
        self.threads_synced = 0
        self.threads_created = 0
        self.threads_updated = 0
    
    def sync_email_threads(
        self,
        folder: str = 'inbox',
        limit: int = 100,
        since_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Sync email threads from a specific folder
        
        Args:
            folder: Folder to sync from
            limit: Maximum threads to sync
            since_date: Only sync emails after this date
            
        Returns:
            Sync statistics
        """
        stats = {
            'threads_synced': 0,
            'threads_created': 0,
            'threads_updated': 0,
            'errors': []
        }
        
        try:
            # Get account ID from connection
            account_id = self.connection.unipile_account_id if self.connection else None
            if not account_id:
                raise ValueError("No account ID available for sync")
            
            # Fetch emails with thread grouping
            after = since_date.isoformat() if since_date else None
            
            # First, get emails with meta_only to identify threads quickly
            result = async_to_sync(self.service.get_emails)(
                account_id=account_id,
                folder=folder,
                limit=limit,
                meta_only=True,  # Faster initial fetch
                after=after
            )
            
            if not result.get('success'):
                error_msg = f"Failed to fetch emails: {result.get('error')}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
                return stats
            
            emails = result.get('emails', [])
            
            # Group emails by thread_id
            threads = self._group_emails_by_thread(emails)
            
            # Process each thread
            for thread_id, thread_emails in threads.items():
                try:
                    self._process_thread(thread_id, thread_emails)
                    stats['threads_synced'] += 1
                    
                    # Update progress
                    if self.progress_tracker:
                        self.progress_tracker.increment_stat('threads_synced', 1)
                    
                except Exception as e:
                    error_msg = f"Failed to process thread {thread_id}: {e}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
            
            stats['threads_created'] = self.threads_created
            stats['threads_updated'] = self.threads_updated
            
        except Exception as e:
            error_msg = f"Thread sync failed: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
        
        return stats
    
    def _group_emails_by_thread(self, emails: List[Dict[str, Any]]) -> Dict[str, List]:
        """
        Group emails by their thread_id
        
        Args:
            emails: List of email data
            
        Returns:
            Dictionary mapping thread_id to list of emails
        """
        threads = {}
        
        for email in emails:
            thread_id = email.get('thread_id')
            
            # If no thread_id, use message_id as thread (single email thread)
            if not thread_id:
                thread_id = email.get('message_id') or email.get('id')
            
            if thread_id not in threads:
                threads[thread_id] = []
            threads[thread_id].append(email)
        
        # Sort emails within each thread by date
        for thread_id in threads:
            threads[thread_id].sort(
                key=lambda e: e.get('date', ''),
                reverse=False  # Oldest first
            )
        
        return threads
    
    def _process_thread(self, thread_id: str, emails: List[Dict[str, Any]]) -> None:
        """
        Process a single email thread
        
        Args:
            thread_id: Thread identifier
            emails: List of emails in this thread
        """
        if not emails:
            return
        
        # Use the latest email for thread metadata
        latest_email = emails[-1]
        first_email = emails[0]
        
        # Extract thread subject (usually consistent across thread)
        subject = latest_email.get('subject', 'No Subject')
        
        # Extract participants from all emails in thread
        participants = self._extract_thread_participants(emails)
        
        # Determine thread folder (use latest email's folder)
        folder = self._get_primary_folder(latest_email)
        
        # Calculate thread timestamps
        thread_created_at = self._parse_date(first_email.get('date'))
        thread_updated_at = self._parse_date(latest_email.get('date'))
        
        # Check if conversation exists
        with transaction.atomic():
            conversation, created = Conversation.objects.update_or_create(
                channel=self.channel,
                external_thread_id=thread_id,
                defaults={
                    'subject': subject[:255] if subject else 'No Subject',
                    'last_message_at': thread_updated_at,
                    'participant_count': len(participants),
                    'message_count': len(emails),
                    'metadata': {
                        'folder': folder,
                        'participants': participants,
                        'has_attachments': any(e.get('has_attachments') for e in emails),
                        'thread_id': thread_id,
                        'first_message_id': first_email.get('id'),
                        'latest_message_id': latest_email.get('id')
                    }
                }
            )
            
            if created:
                self.threads_created += 1
                conversation.created_at = thread_created_at
                conversation.save(update_fields=['created_at'])
                logger.debug(f"Created thread conversation: {subject[:50]}")
            else:
                self.threads_updated += 1
                logger.debug(f"Updated thread conversation: {subject[:50]}")
    
    def _extract_thread_participants(self, emails: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Extract unique participants from thread emails
        
        Args:
            emails: List of emails in thread
            
        Returns:
            List of unique participants
        """
        participants = {}
        
        for email in emails:
            # Add from attendee
            from_attendee = email.get('from_attendee', {})
            if from_attendee and isinstance(from_attendee, dict):
                email_addr = from_attendee.get('identifier')
                if email_addr:
                    participants[email_addr] = {
                        'email': email_addr,
                        'name': from_attendee.get('display_name', ''),
                        'role': 'sender'
                    }
            
            # Add to attendees
            for attendee in email.get('to_attendees', []):
                if isinstance(attendee, dict):
                    email_addr = attendee.get('identifier')
                    if email_addr and email_addr not in participants:
                        participants[email_addr] = {
                            'email': email_addr,
                            'name': attendee.get('display_name', ''),
                            'role': 'recipient'
                        }
            
            # Add cc attendees
            for attendee in email.get('cc_attendees', []):
                if isinstance(attendee, dict):
                    email_addr = attendee.get('identifier')
                    if email_addr and email_addr not in participants:
                        participants[email_addr] = {
                            'email': email_addr,
                            'name': attendee.get('display_name', ''),
                            'role': 'cc'
                        }
        
        return list(participants.values())
    
    def _get_primary_folder(self, email: Dict[str, Any]) -> str:
        """
        Get the primary folder for an email
        
        Args:
            email: Email data
            
        Returns:
            Primary folder name
        """
        # Use 'role' field if available
        role = email.get('role')
        if role:
            return role
        
        # Fall back to folders array
        folders = email.get('folders', [])
        if folders and isinstance(folders, list):
            return folders[0]
        
        return 'inbox'  # Default
    
    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse ISO date string to datetime
        
        Args:
            date_str: ISO format date string
            
        Returns:
            Parsed datetime or now
        """
        if not date_str:
            return timezone.now()
        
        try:
            # Remove microseconds if present for compatibility
            if '.' in date_str:
                date_str = date_str.split('.')[0] + 'Z'
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse date: {date_str}")
            return timezone.now()
    
    def get_threads_for_sync(self, limit: int = 100) -> List[Conversation]:
        """
        Get email thread conversations that need syncing
        
        Args:
            limit: Maximum conversations to return
            
        Returns:
            List of Conversation objects
        """
        return Conversation.objects.filter(
            channel=self.channel
        ).order_by('-last_message_at')[:limit]