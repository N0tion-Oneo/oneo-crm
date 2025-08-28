"""
Email Folder Synchronization
Manages email folder structure and metadata
"""
import logging
from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.db import transaction
from asgiref.sync import async_to_sync

from ..service import EmailService
from .config import EMAIL_SYNC_CONFIG

logger = logging.getLogger(__name__)


class EmailFolderSyncService:
    """Service for syncing email folder structure"""
    
    def __init__(
        self,
        channel: Any,
        connection: Optional[Any] = None,
        progress_tracker: Optional[Any] = None
    ):
        self.channel = channel
        self.connection = connection
        self.progress_tracker = progress_tracker
        self.service = EmailService(channel=channel)
        self.folders_synced = 0
    
    def sync_folders(self) -> Dict[str, Any]:
        """
        Sync email folder structure for the account
        
        Returns:
            Sync statistics and folder data
        """
        stats = {
            'folders_synced': 0,
            'folders': [],
            'errors': []
        }
        
        try:
            # Get account ID
            account_id = self.connection.unipile_account_id if self.connection else None
            if not account_id:
                raise ValueError("No account ID available for folder sync")
            
            # Fetch folders from API
            result = async_to_sync(self.service.get_folders)(account_id)
            
            if isinstance(result, dict) and result.get('error'):
                error_msg = f"Failed to fetch folders: {result.get('error')}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
                return stats
            
            # Process folders
            folders = result.get('items', []) if isinstance(result, dict) else []
            processed_folders = []
            
            for folder_data in folders:
                try:
                    folder_info = self._process_folder(folder_data)
                    processed_folders.append(folder_info)
                    stats['folders_synced'] += 1
                    
                except Exception as e:
                    error_msg = f"Failed to process folder: {e}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
            
            # Store folders in channel metadata
            self._update_channel_folders(processed_folders)
            
            stats['folders'] = processed_folders
            self.folders_synced = stats['folders_synced']
            
            logger.info(f"✅ Synced {stats['folders_synced']} email folders")
            
        except Exception as e:
            error_msg = f"Folder sync failed: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
        
        return stats
    
    def _process_folder(self, folder_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single folder
        
        Args:
            folder_data: Folder data from API
            
        Returns:
            Processed folder information
        """
        return {
            'id': folder_data.get('id'),
            'name': folder_data.get('name'),
            'role': folder_data.get('role', 'unknown'),
            'total_count': folder_data.get('total_count', 0),
            'unread_count': folder_data.get('unread_count', 0),
            'provider_id': folder_data.get('provider_id')
        }
    
    def _update_channel_folders(self, folders: List[Dict[str, Any]]) -> None:
        """
        Update channel with folder information
        
        Args:
            folders: List of processed folders
        """
        if not self.channel:
            return
        
        # Update channel metadata
        if not self.channel.metadata:
            self.channel.metadata = {}
        
        self.channel.metadata['folders'] = folders
        self.channel.metadata['folders_synced_at'] = timezone.now().isoformat()
        self.channel.metadata['folder_count'] = len(folders)
        
        # Extract folder roles for quick access
        folder_roles = {}
        for folder in folders:
            role = folder.get('role')
            if role:
                folder_roles[role] = {
                    'id': folder.get('id'),
                    'name': folder.get('name'),
                    'unread_count': folder.get('unread_count', 0)
                }
        
        self.channel.metadata['folder_roles'] = folder_roles
        
        # Save channel
        self.channel.save(update_fields=['metadata'])
        
        logger.debug(f"Updated channel with {len(folders)} folders")
    
    def get_folder_by_role(self, role: str) -> Optional[Dict[str, Any]]:
        """
        Get folder information by role
        
        Args:
            role: Folder role (inbox, sent, drafts, etc.)
            
        Returns:
            Folder information or None
        """
        if not self.channel or not self.channel.metadata:
            return None
        
        folder_roles = self.channel.metadata.get('folder_roles', {})
        return folder_roles.get(role)
    
    def get_folders_to_sync(self) -> List[str]:
        """
        Get list of folders that should be synced
        
        Returns:
            List of folder identifiers to sync
        """
        # Get configured folders
        configured_folders = EMAIL_SYNC_CONFIG.get('folders_to_sync', ['inbox', 'sent'])
        
        if not self.channel or not self.channel.metadata:
            return configured_folders
        
        # Get actual folder IDs for the configured roles
        folder_roles = self.channel.metadata.get('folder_roles', {})
        folder_ids = []
        
        for role in configured_folders:
            folder_info = folder_roles.get(role)
            if folder_info and folder_info.get('id'):
                folder_ids.append(folder_info['id'])
        
        return folder_ids if folder_ids else configured_folders