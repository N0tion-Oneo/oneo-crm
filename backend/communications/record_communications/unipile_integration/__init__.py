"""
UniPile API Integration Layer for Record-Level Communications

This module handles all direct interactions with the UniPile API.
No business logic or data persistence should happen here.
"""

from .attendee_resolver import AttendeeResolver
from .email_fetcher import EmailFetcher
from .message_fetcher import MessageFetcher
from .data_transformer import DataTransformer

__all__ = [
    'AttendeeResolver',
    'EmailFetcher', 
    'MessageFetcher',
    'DataTransformer'
]