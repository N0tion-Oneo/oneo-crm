"""
UniPile SDK Exception Classes
"""


class UnipileConnectionError(Exception):
    """Raised when UniPile connection fails"""
    pass


class UnipileAuthenticationError(Exception):
    """Raised when UniPile authentication fails"""
    pass


class UnipileRateLimitError(Exception):
    """Raised when UniPile rate limit is exceeded"""
    pass