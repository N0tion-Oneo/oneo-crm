"""
Clean Field State Management
Replaces global _field_states_cache with request-scoped, thread-safe storage
"""
import logging
import threading
from typing import Dict, Any, Optional
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


class FieldStateManager:
    """
    Thread-safe field state management with request-scoped storage
    
    Replaces the global _field_states_cache from signals.py with clean architecture
    Provides automatic cleanup and prevents memory leaks
    """
    
    def __init__(self):
        self._state_storage = {}  # operation_id -> field_states
        self._state_timestamps = {}  # operation_id -> timestamp  
        self._lock = threading.RLock()
        self._cleanup_threshold = timedelta(hours=2)  # Clean up old states after 2 hours
    
    def capture_field_state(self, field_id: int, operation_id: str) -> bool:
        """
        Capture field state before operation
        
        Args:
            field_id: ID of field to capture state for
            operation_id: Unique operation identifier
            
        Returns:
            bool: True if state captured successfully
        """
        try:
            from ..models import Field
            
            with self._lock:
                # Get field with deleted fields included
                try:
                    field = Field.objects.with_deleted().get(pk=field_id)
                except Field.DoesNotExist:
                    logger.warning(f"Cannot capture state: field {field_id} not found")
                    return False
                
                # Initialize operation storage if needed
                if operation_id not in self._state_storage:
                    self._state_storage[operation_id] = {}
                    self._state_timestamps[operation_id] = timezone.now()
                
                # Capture field state
                field_state = {
                    'was_active': not field.is_deleted,
                    'was_deleted': field.is_deleted,
                    'original_config': {
                        'name': field.name,
                        'slug': field.slug,
                        'field_type': field.field_type,
                        'field_config': field.field_config.copy() if field.field_config else {},
                        'storage_constraints': field.storage_constraints.copy() if field.storage_constraints else {},
                        'business_rules': field.business_rules.copy() if field.business_rules else {},
                        'form_validation_rules': field.form_validation_rules.copy() if field.form_validation_rules else {},
                        'display_name': field.display_name,
                        'help_text': field.help_text,
                        'is_ai_field': field.is_ai_field,
                        'ai_config': field.ai_config.copy() if field.ai_config else {},
                        'is_deleted': field.is_deleted,
                        'enforce_uniqueness': field.enforce_uniqueness,
                        'create_index': field.create_index,
                        'is_searchable': field.is_searchable,
                        'is_visible_in_public_forms': field.is_visible_in_public_forms
                    }
                }
                
                self._state_storage[operation_id][field_id] = field_state
                
                logger.debug(f"Captured field state for operation {operation_id}: field {field_id} ({field.name})")
                return True
                
        except Exception as e:
            logger.error(f"Failed to capture field state for field {field_id}: {e}")
            return False
    
    def get_field_state(self, field_id: int, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get captured field state for operation
        
        Args:
            field_id: ID of field
            operation_id: Operation identifier
            
        Returns:
            Dict with field state or None if not found
        """
        with self._lock:
            operation_states = self._state_storage.get(operation_id, {})
            field_state = operation_states.get(field_id)
            
            if field_state:
                logger.debug(f"Retrieved field state for operation {operation_id}: field {field_id}")
                return field_state.copy()  # Return copy to prevent external modification
            
            return None
    
    def get_field_changes(self, field_id: int, current_field, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Detect what changed between captured state and current field
        
        Args:
            field_id: ID of field
            current_field: Current field instance
            operation_id: Operation identifier
            
        Returns:
            Dict with change analysis or None if no original state
        """
        field_state = self.get_field_state(field_id, operation_id)
        if not field_state or not field_state.get('original_config'):
            return None
        
        original_config = field_state['original_config']
        
        changes = {
            'requires_migration': False,
            'migration_types': [],
            'risk_level': 'low',
            'change_details': [],
            'affected_records_estimate': 0
        }
        
        # Check for name/slug changes that require field data migration
        if original_config['slug'] != current_field.slug:
            changes['requires_migration'] = True
            changes['migration_types'].append('field_rename')
            changes['risk_level'] = 'medium'
            changes['change_details'].append(f"Field renamed from '{original_config['slug']}' to '{current_field.slug}'")
        
        # Check for type changes that require data transformation
        if original_config['field_type'] != current_field.field_type:
            changes['requires_migration'] = True
            changes['migration_types'].append('type_change')
            changes['risk_level'] = 'high'  # Type changes are always risky
            changes['change_details'].append(f"Field type changed from '{original_config['field_type']}' to '{current_field.field_type}'")
        
        # Check for storage constraint changes
        old_constraints = original_config.get('storage_constraints', {})
        new_constraints = current_field.storage_constraints or {}
        
        if old_constraints != new_constraints:
            constraint_changes = self._check_constraint_changes(old_constraints, new_constraints)
            if constraint_changes['requires_migration']:
                changes['requires_migration'] = True
                changes['migration_types'].append('constraint_change')
                changes['risk_level'] = max(changes['risk_level'], constraint_changes['risk_level'], 
                                          key=lambda x: ['low', 'medium', 'high'].index(x))
                changes['change_details'].extend(constraint_changes['details'])
        
        # Check for field configuration changes that might affect data
        old_config = original_config.get('field_config', {})
        new_config = current_field.field_config or {}
        
        if old_config != new_config:
            config_changes = self._check_field_config_changes(old_config, new_config, current_field.field_type)
            if config_changes['requires_migration']:
                changes['requires_migration'] = True
                changes['migration_types'].append('config_change')
                changes['risk_level'] = max(changes['risk_level'], config_changes['risk_level'], 
                                          key=lambda x: ['low', 'medium', 'high'].index(x))
                changes['change_details'].extend(config_changes['details'])
        
        # Estimate affected records if migration is required
        if changes['requires_migration']:
            try:
                from ..models import Record
                
                # Count records with data for this field (using original slug)
                affected_count = Record.objects.filter(
                    pipeline=current_field.pipeline,
                    is_deleted=False,
                    data__has_key=original_config['slug']
                ).count()
                
                changes['affected_records_estimate'] = affected_count
                
            except Exception as e:
                logger.error(f"Failed to estimate affected records: {e}")
                changes['affected_records_estimate'] = 0
        
        logger.debug(f"Field change analysis for operation {operation_id}: {changes}")
        return changes
    
    def cleanup_operation_state(self, operation_id: str):
        """
        Clean up state for completed operation
        
        Args:
            operation_id: Operation identifier to clean up
        """
        with self._lock:
            if operation_id in self._state_storage:
                del self._state_storage[operation_id]
                logger.debug(f"Cleaned up state for operation {operation_id}")
            
            if operation_id in self._state_timestamps:
                del self._state_timestamps[operation_id]
    
    def cleanup_old_states(self):
        """Clean up old operation states to prevent memory leaks"""
        current_time = timezone.now()
        expired_operations = []
        
        with self._lock:
            for operation_id, timestamp in self._state_timestamps.items():
                if current_time - timestamp > self._cleanup_threshold:
                    expired_operations.append(operation_id)
            
            for operation_id in expired_operations:
                if operation_id in self._state_storage:
                    del self._state_storage[operation_id]
                if operation_id in self._state_timestamps:
                    del self._state_timestamps[operation_id]
                
                logger.debug(f"Cleaned up expired state for operation {operation_id}")
        
        if expired_operations:
            logger.info(f"Cleaned up {len(expired_operations)} expired operation states")
    
    def get_operation_count(self) -> int:
        """Get number of active operations (for monitoring)"""
        with self._lock:
            return len(self._state_storage)
    
    def get_memory_usage_info(self) -> Dict[str, Any]:
        """Get memory usage information for monitoring"""
        import sys
        
        with self._lock:
            total_operations = len(self._state_storage)
            total_field_states = sum(len(states) for states in self._state_storage.values())
            
            # Rough memory estimation
            storage_size = sys.getsizeof(self._state_storage)
            timestamp_size = sys.getsizeof(self._state_timestamps)
            
            return {
                'active_operations': total_operations,
                'total_field_states': total_field_states,
                'estimated_memory_bytes': storage_size + timestamp_size,
                'cleanup_threshold_hours': self._cleanup_threshold.total_seconds() / 3600
            }
    
    # =============================================================================
    # PRIVATE HELPER METHODS
    # =============================================================================
    
    def _check_constraint_changes(self, old_constraints: Dict[str, Any], 
                                 new_constraints: Dict[str, Any]) -> Dict[str, Any]:
        """Check if constraint changes require migration"""
        result = {
            'requires_migration': False,
            'risk_level': 'low',
            'details': []
        }
        
        # Check max length reduction
        old_max = old_constraints.get('max_storage_length')
        new_max = new_constraints.get('max_storage_length')
        if old_max and new_max and new_max < old_max:
            result['requires_migration'] = True
            result['risk_level'] = 'medium'
            result['details'].append(f"Maximum length reduced from {old_max} to {new_max} - data truncation risk")
        
        # Check uniqueness enforcement
        old_unique = old_constraints.get('enforce_uniqueness', False)
        new_unique = new_constraints.get('enforce_uniqueness', False)
        if not old_unique and new_unique:
            result['requires_migration'] = True
            result['risk_level'] = 'high'
            result['details'].append("Uniqueness constraint added - duplicate data may be lost")
        
        return result
    
    def _check_field_config_changes(self, old_config: Dict[str, Any], 
                                   new_config: Dict[str, Any], field_type: str) -> Dict[str, Any]:
        """Check if field configuration changes require migration"""
        result = {
            'requires_migration': False,
            'risk_level': 'low',
            'details': []
        }
        
        # Check select/multiselect option changes
        if field_type in ['select', 'multiselect']:
            old_options = set(old_config.get('options', []))
            new_options = set(new_config.get('options', []))
            
            removed_options = old_options - new_options
            if removed_options:
                result['requires_migration'] = True
                result['risk_level'] = 'medium'
                result['details'].append(f"Select options removed: {', '.join(removed_options)} - data may become invalid")
        
        return result


# =============================================================================
# GLOBAL FIELD STATE MANAGER INSTANCE
# =============================================================================

# Global instance - thread-safe and shared across the application
_field_state_manager = FieldStateManager()


def get_field_state_manager() -> FieldStateManager:
    """Get global FieldStateManager instance"""
    return _field_state_manager


def capture_field_state(field_id: int, operation_id: str) -> bool:
    """Convenience function to capture field state"""
    return _field_state_manager.capture_field_state(field_id, operation_id)


def get_field_state(field_id: int, operation_id: str) -> Optional[Dict[str, Any]]:
    """Convenience function to get field state"""
    return _field_state_manager.get_field_state(field_id, operation_id)


def get_field_changes(field_id: int, current_field, operation_id: str) -> Optional[Dict[str, Any]]:
    """Convenience function to get field changes"""
    return _field_state_manager.get_field_changes(field_id, current_field, operation_id)


def cleanup_operation_state(operation_id: str):
    """Convenience function to clean up operation state"""
    _field_state_manager.cleanup_operation_state(operation_id)