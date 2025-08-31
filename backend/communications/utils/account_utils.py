"""
Utility functions for handling account owner information
"""
from typing import Optional, Dict, Any
from communications.models import UserChannelConnection, Channel


def get_account_owner_name(
    channel: Optional[Channel] = None,
    unipile_account_id: Optional[str] = None,
    channel_type: Optional[str] = None
) -> str:
    """
    Get the actual account owner's name from UserChannelConnection.
    
    This function ensures we always display the real account owner's name
    (e.g., "John Smith") instead of generic placeholders like "You".
    
    Args:
        channel: Channel object to get the account from
        unipile_account_id: Direct UniPile account ID
        channel_type: Type of channel (whatsapp, linkedin, gmail, etc.)
    
    Returns:
        The account owner's actual name, never "You"
    """
    # Try to get UniPile account ID from channel if not provided
    if not unipile_account_id and channel:
        unipile_account_id = channel.unipile_account_id
        if not channel_type:
            channel_type = channel.channel_type
    
    if not unipile_account_id:
        # If we still don't have an account ID, try to get from channel name
        if channel and channel.name:
            return channel.name
        return "Unknown Account"
    
    # Look up the UserChannelConnection
    try:
        filters = {'unipile_account_id': unipile_account_id}
        if channel_type:
            filters['channel_type'] = channel_type
            
        connection = UserChannelConnection.objects.filter(**filters).first()
        
        if connection:
            # Priority order for getting the account owner's name:
            # 1. Check connection_config for stored account owner name
            if connection.connection_config:
                account_owner_name = (
                    connection.connection_config.get('account_owner_name') or
                    connection.connection_config.get('user_name') or
                    connection.connection_config.get('display_name')
                )
                if account_owner_name:
                    return account_owner_name
            
            # 2. Check provider_config for stored account owner name  
            if connection.provider_config:
                account_owner_name = (
                    connection.provider_config.get('account_owner_name') or
                    connection.provider_config.get('user_name') or
                    connection.provider_config.get('display_name')
                )
                if account_owner_name:
                    return account_owner_name
            
            # 3. Use the account_name field (this should be set during connection)
            if connection.account_name:
                return connection.account_name
            
            # 4. If the connection has a user, use their name
            if connection.user:
                if connection.user.first_name or connection.user.last_name:
                    full_name = f"{connection.user.first_name} {connection.user.last_name}".strip()
                    if full_name:
                        return full_name
                if connection.user.username:
                    return connection.user.username
                if connection.user.email:
                    # Use email prefix as last resort
                    return connection.user.email.split('@')[0]
    except Exception as e:
        # Log the error but don't crash
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error getting account owner name: {e}")
    
    # Final fallback - use channel name if available
    if channel and channel.name:
        return channel.name
    
    return "Unknown Account"


def get_account_owner_info(
    channel: Optional[Channel] = None,
    unipile_account_id: Optional[str] = None,
    channel_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get comprehensive account owner information.
    
    Returns:
        Dict with 'name', 'email', 'phone', and other account details
    """
    info = {
        'name': get_account_owner_name(channel, unipile_account_id, channel_type),
        'email': None,
        'phone': None,
        'avatar_url': None
    }
    
    # Try to get UniPile account ID from channel if not provided
    if not unipile_account_id and channel:
        unipile_account_id = channel.unipile_account_id
        if not channel_type:
            channel_type = channel.channel_type
    
    if unipile_account_id:
        try:
            filters = {'unipile_account_id': unipile_account_id}
            if channel_type:
                filters['channel_type'] = channel_type
                
            connection = UserChannelConnection.objects.filter(**filters).first()
            
            if connection:
                # Get email
                if connection.connection_config:
                    info['email'] = connection.connection_config.get('email')
                if not info['email'] and connection.provider_config:
                    info['email'] = connection.provider_config.get('email')
                
                # Get phone (for WhatsApp)
                if connection.connection_config:
                    info['phone'] = connection.connection_config.get('phone_number')
                if not info['phone'] and connection.provider_config:
                    info['phone'] = connection.provider_config.get('phone')
                
                # Get avatar
                if connection.connection_config:
                    info['avatar_url'] = connection.connection_config.get('avatar_url')
                if not info['avatar_url'] and connection.provider_config:
                    info['avatar_url'] = connection.provider_config.get('picture_url')
                    
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error getting account owner info: {e}")
    
    return info


def store_account_owner_name(
    connection: UserChannelConnection,
    name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None
) -> None:
    """
    Store the account owner's name in the UserChannelConnection.
    This should be called when we get the account info from UniPile.
    
    Args:
        connection: The UserChannelConnection to update
        name: The account owner's actual name
        email: The account owner's email (optional)
        phone: The account owner's phone (optional)
    """
    if not connection.connection_config:
        connection.connection_config = {}
    
    # Store the account owner's name
    connection.connection_config['account_owner_name'] = name
    
    # Store email if provided
    if email:
        connection.connection_config['email'] = email
    
    # Store phone if provided
    if phone:
        connection.connection_config['phone_number'] = phone
    
    # Also update the account_name field if it's not set
    if not connection.account_name or connection.account_name == "Unknown":
        connection.account_name = name
    
    connection.save(update_fields=['connection_config', 'account_name'])