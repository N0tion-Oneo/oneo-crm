# UniPile SDK - Modular Architecture

This directory contains the refactored UniPile SDK with a clean, modular architecture.

## Directory Structure

```
unipile/
├── __init__.py              # Main package exports
├── core/                    # Core functionality
│   ├── __init__.py
│   ├── client.py           # Main UnipileClient class
│   └── exceptions.py       # All UniPile exceptions
├── clients/                 # Specialized client modules
│   ├── __init__.py
│   ├── account.py          # Account management (connect, disconnect, sync)
│   ├── messaging.py        # Chat and message operations
│   ├── users.py            # User profile and search
│   ├── webhooks.py         # Webhook management
│   ├── linkedin.py         # LinkedIn-specific operations
│   ├── email.py            # Email operations
│   └── calendar.py         # Calendar operations
├── services/                # High-level Django integration
│   ├── __init__.py
│   └── service.py          # UnipileService for Django integration
└── utils/                   # Utility classes
    ├── __init__.py
    └── request.py          # Custom request client
```

## Usage

### Recommended (New) Import Pattern

```python
# For most use cases
from communications.unipile import unipile_service, UnipileClient

# For specific exceptions
from communications.unipile.core.exceptions import UnipileConnectionError

# For direct client access
from communications.unipile.clients.account import UnipileAccountClient
```

### Legacy Import Pattern (Still Supported)

```python
# This still works but shows deprecation warning
from communications.unipile_sdk import unipile_service, UnipileClient
```

## Benefits of Modular Architecture

1. **Better Organization**: Related functionality grouped together
2. **Easier Maintenance**: Smaller, focused files are easier to understand
3. **Improved Testing**: Individual modules can be tested independently
4. **Better Performance**: Lazy loading of client modules
5. **Future Extensibility**: Easy to add new client types

## Backward Compatibility

All existing imports continue to work unchanged. The original `unipile_sdk.py` now serves as a compatibility layer that redirects to the new modular structure.

## Migration Guide

While not required immediately, you can gradually migrate to the new import patterns:

**Before:**
```python
from communications.unipile_sdk import unipile_service, UnipileClient
```

**After:**
```python
from communications.unipile import unipile_service, UnipileClient
```

The functionality remains identical - only the import path changes.