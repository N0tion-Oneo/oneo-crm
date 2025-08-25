"""
WhatsApp Media Handler
Handles media attachments for WhatsApp messages
"""
import logging
import mimetypes
import os
from typing import Dict, Any, Optional, List, BinaryIO
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import requests

logger = logging.getLogger(__name__)


class WhatsAppMediaHandler:
    """Handles WhatsApp media attachments"""
    
    # WhatsApp supported media types
    SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    SUPPORTED_VIDEO_FORMATS = ['.mp4', '.3gp', '.avi', '.mov']
    SUPPORTED_AUDIO_FORMATS = ['.aac', '.m4a', '.amr', '.mp3', '.ogg', '.opus']
    SUPPORTED_DOCUMENT_FORMATS = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv']
    
    # Size limits (in bytes)
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_VIDEO_SIZE = 16 * 1024 * 1024  # 16MB
    MAX_AUDIO_SIZE = 16 * 1024 * 1024  # 16MB
    MAX_DOCUMENT_SIZE = 100 * 1024 * 1024  # 100MB
    
    def process_outgoing_attachment(self, file_path: str, caption: Optional[str] = None) -> Dict[str, Any]:
        """
        Process an attachment for sending via WhatsApp
        
        Args:
            file_path: Path to the file
            caption: Optional caption for the media
            
        Returns:
            Processed attachment data ready for sending
        """
        try:
            # Determine media type
            media_type = self.get_media_type(file_path)
            
            # Validate file
            validation = self.validate_media(file_path, media_type)
            if not validation['valid']:
                raise ValueError(validation['error'])
            
            # Prepare attachment data
            attachment = {
                'type': media_type,
                'path': file_path,
                'caption': caption,
                'mime_type': mimetypes.guess_type(file_path)[0],
                'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
            }
            
            return attachment
            
        except Exception as e:
            logger.error(f"Failed to process outgoing attachment: {e}")
            raise
    
    def process_incoming_media(self, media_data: Dict[str, Any], chat_id: str, message_id: str) -> Dict[str, Any]:
        """
        Process incoming media from WhatsApp webhook
        
        Args:
            media_data: Media data from webhook
            chat_id: WhatsApp chat ID
            message_id: Message ID
            
        Returns:
            Processed media information
        """
        try:
            media_url = media_data.get('url')
            media_type = media_data.get('type', 'document')
            media_id = media_data.get('id')
            caption = media_data.get('caption')
            filename = media_data.get('filename') or media_data.get('name')
            
            if not media_url:
                logger.warning(f"No media URL found for message {message_id}")
                return {}
            
            # Download and store media
            stored_path = self.download_and_store_media(
                media_url, 
                chat_id, 
                message_id,
                media_type,
                filename
            )
            
            return {
                'type': media_type,
                'url': media_url,
                'local_path': stored_path,
                'caption': caption,
                'media_id': media_id,
                'filename': filename
            }
            
        except Exception as e:
            logger.error(f"Failed to process incoming media: {e}")
            return {
                'type': 'error',
                'error': str(e)
            }
    
    def download_and_store_media(
        self, 
        media_url: str, 
        chat_id: str, 
        message_id: str,
        media_type: str = 'document',
        filename: Optional[str] = None
    ) -> str:
        """
        Download media from URL and store locally
        
        Args:
            media_url: URL to download media from
            chat_id: WhatsApp chat ID
            message_id: Message ID
            media_type: Type of media
            filename: Original filename
            
        Returns:
            Path to stored media file
        """
        try:
            # Download media
            response = requests.get(media_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Determine filename
            if not filename:
                # Try to get from content-disposition header
                content_disposition = response.headers.get('content-disposition')
                if content_disposition:
                    import re
                    filename_match = re.search(r'filename="?(.+)"?', content_disposition)
                    if filename_match:
                        filename = filename_match.group(1)
                
                # Fallback to generating filename
                if not filename:
                    ext = self._get_extension_for_type(media_type)
                    filename = f"{message_id}{ext}"
            
            # Create storage path
            storage_path = f"whatsapp/{chat_id}/{message_id}/{filename}"
            
            # Store file
            content = ContentFile(response.content)
            saved_path = default_storage.save(storage_path, content)
            
            logger.info(f"✅ Stored WhatsApp media: {saved_path}")
            return saved_path
            
        except Exception as e:
            logger.error(f"Failed to download and store media: {e}")
            raise
    
    def get_media_type(self, file_path: str) -> str:
        """
        Determine media type from file path
        
        Args:
            file_path: Path to file
            
        Returns:
            Media type (image, video, audio, document)
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in self.SUPPORTED_IMAGE_FORMATS:
            return 'image'
        elif ext in self.SUPPORTED_VIDEO_FORMATS:
            return 'video'
        elif ext in self.SUPPORTED_AUDIO_FORMATS:
            return 'audio'
        elif ext in self.SUPPORTED_DOCUMENT_FORMATS:
            return 'document'
        else:
            # Default to document for unknown types
            return 'document'
    
    def validate_media(self, file_path: str, media_type: str) -> Dict[str, Any]:
        """
        Validate media file for WhatsApp compatibility
        
        Args:
            file_path: Path to file
            media_type: Type of media
            
        Returns:
            Validation result
        """
        result = {'valid': True, 'error': None}
        
        # Check file exists
        if not os.path.exists(file_path):
            result['valid'] = False
            result['error'] = 'File not found'
            return result
        
        # Check file size
        file_size = os.path.getsize(file_path)
        max_size = self._get_max_size_for_type(media_type)
        
        if file_size > max_size:
            result['valid'] = False
            result['error'] = f'File too large. Maximum size for {media_type} is {max_size / (1024*1024):.1f}MB'
            return result
        
        # Check file extension
        ext = os.path.splitext(file_path)[1].lower()
        supported_formats = self._get_supported_formats_for_type(media_type)
        
        if ext not in supported_formats:
            result['valid'] = False
            result['error'] = f'Unsupported format. Supported formats for {media_type}: {", ".join(supported_formats)}'
            return result
        
        return result
    
    def generate_thumbnail(self, image_path: str, max_size: tuple = (150, 150)) -> Optional[str]:
        """
        Generate thumbnail for image
        
        Args:
            image_path: Path to image
            max_size: Maximum thumbnail dimensions
            
        Returns:
            Path to thumbnail or None
        """
        try:
            from PIL import Image
            
            # Open image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                
                # Generate thumbnail
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save thumbnail
                thumb_path = f"{os.path.splitext(image_path)[0]}_thumb.jpg"
                img.save(thumb_path, 'JPEG', quality=85)
                
                return thumb_path
                
        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            return None
    
    def _get_max_size_for_type(self, media_type: str) -> int:
        """Get maximum file size for media type"""
        size_limits = {
            'image': self.MAX_IMAGE_SIZE,
            'video': self.MAX_VIDEO_SIZE,
            'audio': self.MAX_AUDIO_SIZE,
            'document': self.MAX_DOCUMENT_SIZE
        }
        return size_limits.get(media_type, self.MAX_DOCUMENT_SIZE)
    
    def _get_supported_formats_for_type(self, media_type: str) -> List[str]:
        """Get supported formats for media type"""
        format_map = {
            'image': self.SUPPORTED_IMAGE_FORMATS,
            'video': self.SUPPORTED_VIDEO_FORMATS,
            'audio': self.SUPPORTED_AUDIO_FORMATS,
            'document': self.SUPPORTED_DOCUMENT_FORMATS
        }
        return format_map.get(media_type, self.SUPPORTED_DOCUMENT_FORMATS)
    
    def _get_extension_for_type(self, media_type: str) -> str:
        """Get default extension for media type"""
        default_extensions = {
            'image': '.jpg',
            'video': '.mp4',
            'audio': '.mp3',
            'document': '.pdf'
        }
        return default_extensions.get(media_type, '.bin')
    
    def cleanup_old_media(self, days_old: int = 30) -> int:
        """
        Clean up old media files
        
        Args:
            days_old: Delete media older than this many days
            
        Returns:
            Number of files deleted
        """
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            deleted_count = 0
            # Implementation would iterate through stored media and delete old files
            
            logger.info(f"Cleaned up {deleted_count} old media files")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old media: {e}")
            return 0