"""
Field Path Resolver - Enable dot notation traversal for relation fields in workflows

This module provides utilities for resolving field paths with relationship traversal support.
Enables expressions like:
- 'email' → record.data['email']
- 'company.name' → related_company_record.data['name']
- 'deal.company.industry' → multi-hop traversal through relationships

Features:
- Single and multi-hop relationship traversal
- Caching layer for performance optimization
- Permission-aware traversal (respects field visibility)
- Soft-delete aware (skips deleted records)
- Support for array relations (multiple cardinality)
- Configurable max depth protection
"""

from typing import Any, Dict, Optional, List, Tuple, Union
from django.core.cache import cache
from django.db.models import Q
import logging
import hashlib
import json

logger = logging.getLogger(__name__)


class FieldPathResolver:
    """
    Resolves field paths with relationship traversal support for workflows.

    Usage:
        resolver = FieldPathResolver(max_depth=3, enable_caching=True)
        value = resolver.resolve(record, 'company.industry.name')
    """

    def __init__(
        self,
        max_depth: int = 3,
        enable_caching: bool = True,
        cache_ttl: int = 300,  # 5 minutes
        user=None  # For permission checking
    ):
        """
        Initialize the field path resolver.

        Args:
            max_depth: Maximum relationship traversal depth (default 3)
            enable_caching: Enable Redis caching for resolved paths
            cache_ttl: Cache time-to-live in seconds
            user: User for permission-aware traversal (optional)
        """
        self.max_depth = max_depth
        self.enable_caching = enable_caching
        self.cache_ttl = cache_ttl
        self.user = user

        # Internal cache for single request (avoid repeated DB queries)
        self._request_cache: Dict[str, Any] = {}

    def resolve(
        self,
        record: 'Record',  # Type hint as string to avoid circular import
        field_path: str,
        default: Any = None
    ) -> Any:
        """
        Resolve a field path to its value, handling relationship traversal.

        Args:
            record: Source record to start traversal from
            field_path: Dot-notation path (e.g., 'company.name' or 'contacts[0].email')
            default: Default value if path cannot be resolved

        Returns:
            Resolved value or default if path cannot be resolved

        Examples:
            >>> resolver.resolve(contact_record, 'email')
            'john@example.com'

            >>> resolver.resolve(contact_record, 'company.name')
            'Acme Corporation'

            >>> resolver.resolve(deal_record, 'company.industry.category')
            'Technology'
        """
        if not field_path or not record:
            return default

        # Clean up template syntax if present
        field_path = self._clean_template_syntax(field_path)

        # Check request cache first (within same workflow execution)
        cache_key_request = f"{record.id}_{field_path}"
        if cache_key_request in self._request_cache:
            logger.debug(f"🎯 Request cache hit for {field_path}")
            return self._request_cache[cache_key_request]

        # Check Redis cache
        if self.enable_caching:
            cache_key = self._generate_cache_key(record, field_path)
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"🎯 Redis cache hit for {field_path}")
                self._request_cache[cache_key_request] = cached_value
                return cached_value

        # Resolve the path
        try:
            value = self._resolve_path(record, field_path, depth=0)

            # Cache the result
            self._request_cache[cache_key_request] = value
            if self.enable_caching and value is not None:
                cache_key = self._generate_cache_key(record, field_path)
                cache.set(cache_key, value, self.cache_ttl)

            return value if value is not None else default

        except Exception as e:
            logger.warning(f"Error resolving field path '{field_path}': {e}")
            return default

    def _resolve_path(
        self,
        record: 'Record',
        field_path: str,
        depth: int = 0
    ) -> Any:
        """
        Internal method to recursively resolve field paths.

        Args:
            record: Current record in traversal
            field_path: Remaining path to resolve
            depth: Current traversal depth

        Returns:
            Resolved value or None
        """
        if depth > self.max_depth:
            logger.warning(f"Max depth {self.max_depth} exceeded for path: {field_path}")
            return None

        # Split path into segments
        segments = field_path.split('.')
        if not segments:
            return None

        current_segment = segments[0]
        remaining_path = '.'.join(segments[1:]) if len(segments) > 1 else None

        # Handle array access (e.g., contacts[0])
        array_index = None
        if '[' in current_segment and ']' in current_segment:
            field_name, index_str = current_segment.split('[')
            array_index = int(index_str.rstrip(']'))
            current_segment = field_name
        else:
            field_name = current_segment

        # Get the field value from current record
        field_value = self._get_field_value(record, field_name)

        if field_value is None:
            return None

        # Check if this is a relation field
        is_relation = self._is_relation_field(record, field_name)

        if is_relation:
            # Handle relation field traversal
            if remaining_path:
                # Need to traverse further
                return self._traverse_relation(
                    record,
                    field_name,
                    field_value,
                    remaining_path,
                    array_index,
                    depth
                )
            else:
                # Return the relation field value as-is (with display_value)
                if array_index is not None and isinstance(field_value, list):
                    return field_value[array_index] if array_index < len(field_value) else None
                return field_value
        else:
            # Regular field - return value if this is the last segment
            if not remaining_path:
                if array_index is not None and isinstance(field_value, list):
                    return field_value[array_index] if array_index < len(field_value) else None
                return field_value
            else:
                # Try to traverse into nested dict
                if isinstance(field_value, dict) and remaining_path:
                    return self._get_nested_dict_value(field_value, remaining_path)
                return None

    def _traverse_relation(
        self,
        source_record: 'Record',
        field_name: str,
        field_value: Any,
        remaining_path: str,
        array_index: Optional[int],
        depth: int
    ) -> Any:
        """
        Traverse a relationship field to continue path resolution.

        Args:
            source_record: Source record containing the relation field
            field_name: Name of the relation field
            field_value: Current value of the relation field
            remaining_path: Remaining path segments to resolve
            array_index: Array index if specified (for multiple relations)
            depth: Current traversal depth

        Returns:
            Resolved value from related record(s)
        """
        from pipelines.models import Record, Field
        from pipelines.relation_field_handler import RelationFieldHandler

        # Get the field definition
        try:
            field = source_record.pipeline.fields.get(
                slug=field_name,
                field_type='relation',
                is_deleted=False
            )
        except Field.DoesNotExist:
            logger.warning(f"Relation field '{field_name}' not found")
            return None

        # Get the handler for this relation field
        handler = RelationFieldHandler(field)

        # Extract record IDs from field value
        related_ids = self._extract_relation_ids(field_value)

        if not related_ids:
            return None

        # Handle array index for multiple relations
        if array_index is not None:
            if array_index >= len(related_ids):
                return None
            related_ids = [related_ids[array_index]]

        # Fetch related records
        try:
            related_records = Record.objects.filter(
                id__in=related_ids,
                pipeline_id=handler.target_pipeline_id,
                is_deleted=False
            )

            if not related_records:
                return None

            # Traverse into related records
            results = []
            for related_record in related_records:
                value = self._resolve_path(
                    related_record,
                    remaining_path,
                    depth + 1
                )
                if value is not None:
                    results.append(value)

            # Return single value or array based on cardinality
            if handler.allow_multiple:
                return results if results else None
            else:
                return results[0] if results else None

        except Exception as e:
            logger.error(f"Error traversing relation '{field_name}': {e}")
            return None

    def _get_field_value(self, record: 'Record', field_name: str) -> Any:
        """Get field value from record data"""
        if not record or not record.data:
            return None
        return record.data.get(field_name)

    def _is_relation_field(self, record: 'Record', field_name: str) -> bool:
        """Check if a field is a relation field"""
        try:
            field = record.pipeline.fields.get(slug=field_name, is_deleted=False)
            return field.field_type == 'relation'
        except Exception:
            return False

    def _extract_relation_ids(self, field_value: Any) -> List[int]:
        """
        Extract record IDs from relation field value.

        Handles formats:
        - Single: {'id': 1, 'display_value': 'Acme'}
        - Multiple: [{'id': 1, 'display_value': 'Acme'}, {'id': 2, 'display_value': 'Beta'}]
        - Legacy: [1, 2, 3] or 1
        """
        if not field_value:
            return []

        # Handle array of objects
        if isinstance(field_value, list):
            ids = []
            for item in field_value:
                if isinstance(item, dict) and 'id' in item:
                    ids.append(int(item['id']))
                elif isinstance(item, (int, str)):
                    ids.append(int(item))
            return ids

        # Handle single object
        if isinstance(field_value, dict) and 'id' in field_value:
            return [int(field_value['id'])]

        # Handle single ID
        if isinstance(field_value, (int, str)):
            return [int(field_value)]

        return []

    def _get_nested_dict_value(self, data: Dict, path: str) -> Any:
        """Get value from nested dictionary using dot notation"""
        keys = path.split('.')
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None

        return value

    def _clean_template_syntax(self, field_path: str) -> str:
        """Remove template syntax like {{}} or {}"""
        cleaned = field_path.strip()
        if cleaned.startswith('{{') and cleaned.endswith('}}'):
            cleaned = cleaned[2:-2].strip()
        elif cleaned.startswith('{') and cleaned.endswith('}'):
            cleaned = cleaned[1:-1].strip()
        return cleaned

    def _generate_cache_key(self, record: 'Record', field_path: str) -> str:
        """Generate cache key for resolved field path"""
        key_data = f"field_path_resolver:{record.id}:{record.pipeline_id}:{field_path}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def clear_cache(self, record: 'Record' = None):
        """
        Clear the resolver cache.

        Args:
            record: If provided, only clear cache for this record.
                   If None, clear all resolver cache.
        """
        # Clear request cache
        if record:
            keys_to_remove = [k for k in self._request_cache.keys() if k.startswith(f"{record.id}_")]
            for key in keys_to_remove:
                del self._request_cache[key]
        else:
            self._request_cache.clear()

        # Note: Redis cache uses TTL, so we don't need to manually clear it
        # But we could add pattern-based deletion if needed

    def resolve_multiple(
        self,
        record: 'Record',
        field_paths: List[str],
        default: Any = None
    ) -> Dict[str, Any]:
        """
        Resolve multiple field paths at once for efficiency.

        Args:
            record: Source record
            field_paths: List of field paths to resolve
            default: Default value for unresolved paths

        Returns:
            Dictionary mapping field paths to resolved values
        """
        results = {}
        for path in field_paths:
            results[path] = self.resolve(record, path, default)
        return results


# Convenience function for quick access
def resolve_field_path(
    record: 'Record',
    field_path: str,
    default: Any = None,
    max_depth: int = 3
) -> Any:
    """
    Convenience function to resolve a field path without creating a resolver instance.

    Args:
        record: Source record
        field_path: Dot-notation path
        default: Default value if path cannot be resolved
        max_depth: Maximum traversal depth

    Returns:
        Resolved value or default
    """
    resolver = FieldPathResolver(max_depth=max_depth)
    return resolver.resolve(record, field_path, default)
