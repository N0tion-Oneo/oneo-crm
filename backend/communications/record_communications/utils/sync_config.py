"""
Sync Configuration - Configuration for record sync behavior

Centralized configuration for sync parameters.
"""
from typing import Dict, Any, Optional
from django.conf import settings


class SyncConfig:
    """Configuration for record communication sync"""
    
    # Default sync parameters
    DEFAULT_HISTORICAL_DAYS = 0  # 0 = no date limit, fetch all history
    DEFAULT_MAX_MESSAGES_PER_RECORD = 0  # 0 = no limit, fetch all messages
    DEFAULT_MAX_CONVERSATIONS_PER_RECORD = 0  # 0 = no limit, fetch all conversations
    DEFAULT_BATCH_SIZE = 100  # Larger batch size for better performance
    
    # Channel-specific defaults - NO LIMITS
    CHANNEL_DEFAULTS = {
        'email': {
            'enabled': True,
            'historical_days': 0,  # 0 = no limit, fetch all emails
            'max_messages': 0,  # 0 = no limit, fetch all emails
            'batch_size': 100  # Larger batch for better performance
        },
        'gmail': {
            'enabled': True,
            'historical_days': 0,  # 0 = no limit, fetch all emails
            'max_messages': 10,  # 0 = no limit, fetch all emails
            'batch_size': 100  # Larger batch for better performance
        },
        'whatsapp': {
            'enabled': True,
            'historical_days': 0,  # 0 = no limit, fetch all messages
            'max_messages': 0,  # 0 = no limit, fetch all messages
            'batch_size': 100  # Larger batch for better performance
        },
        'linkedin': {
            'enabled': True,
            'historical_days': 0,  # 0 = no limit, fetch all messages
            'max_messages': 0,  # 0 = no limit, fetch all messages
            'batch_size': 100  # Larger batch for better performance
        },
        'telegram': {
            'enabled': True,
            'historical_days': 0,  # 0 = no limit, fetch all messages
            'max_messages': 0,  # 0 = no limit, fetch all messages
            'batch_size': 100  # Larger batch for better performance
        },
        'instagram': {
            'enabled': True,
            'historical_days': 0,  # 0 = no limit, fetch all messages
            'max_messages': 0,  # 0 = no limit, fetch all messages
            'batch_size': 100  # Larger batch for better performance
        }
    }
    
    def __init__(self, config_override: Optional[Dict[str, Any]] = None):
        """
        Initialize sync configuration
        
        Args:
            config_override: Optional configuration overrides
        """
        self.config = self._load_config()
        
        if config_override:
            self.config.update(config_override)
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from settings or use defaults"""
        # Try to load from Django settings
        from_settings = getattr(settings, 'RECORD_SYNC_CONFIG', {})
        
        # Build base config
        config = {
            'historical_days': from_settings.get(
                'historical_days',
                self.DEFAULT_HISTORICAL_DAYS
            ),
            'max_messages_per_record': from_settings.get(
                'max_messages_per_record',
                self.DEFAULT_MAX_MESSAGES_PER_RECORD
            ),
            'max_conversations_per_record': from_settings.get(
                'max_conversations_per_record',
                self.DEFAULT_MAX_CONVERSATIONS_PER_RECORD
            ),
            'batch_size': from_settings.get(
                'batch_size',
                self.DEFAULT_BATCH_SIZE
            ),
            'channels': {}
        }
        
        # Load channel-specific config
        channels_config = from_settings.get('channels', {})
        
        for channel, defaults in self.CHANNEL_DEFAULTS.items():
            channel_config = channels_config.get(channel, {})
            
            config['channels'][channel] = {
                'enabled': channel_config.get('enabled', defaults['enabled']),
                'historical_days': channel_config.get(
                    'historical_days',
                    defaults['historical_days']
                ),
                'max_messages': channel_config.get(
                    'max_messages',
                    defaults['max_messages']
                ),
                'batch_size': channel_config.get(
                    'batch_size',
                    defaults['batch_size']
                )
            }
        
        return config
    
    def get_channel_config(self, channel_type: str) -> Dict[str, Any]:
        """
        Get configuration for a specific channel
        
        Args:
            channel_type: Type of channel
            
        Returns:
            Channel configuration dict
        """
        return self.config['channels'].get(
            channel_type,
            self.CHANNEL_DEFAULTS.get(channel_type, {})
        )
    
    def is_channel_enabled(self, channel_type: str) -> bool:
        """
        Check if a channel is enabled for sync
        
        Args:
            channel_type: Type of channel
            
        Returns:
            True if channel is enabled
        """
        channel_config = self.get_channel_config(channel_type)
        return channel_config.get('enabled', False)
    
    def get_historical_days(self, channel_type: Optional[str] = None) -> int:
        """
        Get number of historical days to sync
        
        Args:
            channel_type: Optional channel type for channel-specific config
            
        Returns:
            Number of days
        """
        if channel_type:
            channel_config = self.get_channel_config(channel_type)
            return channel_config.get(
                'historical_days',
                self.config['historical_days']
            )
        
        return self.config['historical_days']
    
    def get_max_messages(self, channel_type: Optional[str] = None) -> int:
        """
        Get maximum messages to sync
        
        Args:
            channel_type: Optional channel type for channel-specific config
            
        Returns:
            Maximum message count
        """
        if channel_type:
            channel_config = self.get_channel_config(channel_type)
            return channel_config.get(
                'max_messages',
                self.config['max_messages_per_record']
            )
        
        return self.config['max_messages_per_record']
    
    def get_batch_size(self, channel_type: Optional[str] = None) -> int:
        """
        Get batch size for API calls
        
        Args:
            channel_type: Optional channel type for channel-specific config
            
        Returns:
            Batch size
        """
        if channel_type:
            channel_config = self.get_channel_config(channel_type)
            return channel_config.get(
                'batch_size',
                self.config['batch_size']
            )
        
        return self.config['batch_size']


# Global instance
_sync_config = None


def get_sync_config(config_override: Optional[Dict[str, Any]] = None) -> SyncConfig:
    """
    Get global sync configuration instance
    
    Args:
        config_override: Optional configuration overrides
        
    Returns:
        SyncConfig instance
    """
    global _sync_config
    
    if _sync_config is None or config_override:
        _sync_config = SyncConfig(config_override)
    
    return _sync_config