"""
Operational Transform implementation for collaborative editing
"""
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from django.core.cache import cache
from dataclasses import dataclass
from enum import Enum
import logging
import time
import uuid

logger = logging.getLogger(__name__)

class OperationType(Enum):
    INSERT = "insert"
    DELETE = "delete"
    RETAIN = "retain"
    REPLACE = "replace"

@dataclass
class Operation:
    """Represents a single operation in operational transform"""
    type: OperationType
    position: int
    content: Optional[str] = None
    length: Optional[int] = None
    author: Optional[int] = None
    timestamp: Optional[float] = None
    operation_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.operation_id:
            self.operation_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = time.time()

class OperationalTransform:
    """Implements operational transform for collaborative editing"""
    
    def __init__(self, document_id: str, field_name: str):
        self.document_id = document_id
        self.field_name = field_name
        self.operation_log_key = f"ot_log:{document_id}:{field_name}"
        self.document_state_key = f"ot_state:{document_id}:{field_name}"
        self.operation_counter_key = f"ot_counter:{document_id}:{field_name}"
        self.max_operations = 1000  # Keep last 1000 operations
        
    async def transform_operation(self, operation: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Transform an operation against concurrent operations"""
        op = self._parse_operation(operation, user_id)
        
        # Get operations that happened since this operation was created
        concurrent_ops = await self._get_concurrent_operations(op.timestamp)
        
        # Transform against each concurrent operation
        transformed_op = op
        for concurrent_op in concurrent_ops:
            if concurrent_op.author != op.author:  # Don't transform against own operations
                transformed_op = self._transform_against_operation(transformed_op, concurrent_op)
        
        # Store the transformed operation
        await self._store_operation(transformed_op)
        
        # Update document state
        await self._apply_operation_to_state(transformed_op)
        
        return self._serialize_operation(transformed_op)
    
    def _parse_operation(self, operation: Dict[str, Any], user_id: int) -> Operation:
        """Parse operation from dictionary"""
        return Operation(
            type=OperationType(operation['type']),
            position=operation['position'],
            content=operation.get('content'),
            length=operation.get('length', len(operation.get('content', ''))),
            author=user_id,
            timestamp=operation.get('timestamp', time.time()),
            operation_id=operation.get('id')
        )
    
    def _serialize_operation(self, operation: Operation) -> Dict[str, Any]:
        """Serialize operation to dictionary"""
        return {
            'type': operation.type.value,
            'position': operation.position,
            'content': operation.content,
            'length': operation.length,
            'author': operation.author,
            'timestamp': operation.timestamp,
            'id': operation.operation_id
        }
    
    async def _get_concurrent_operations(self, since_timestamp: float) -> List[Operation]:
        """Get operations that happened since the given timestamp"""
        # Get operation log from cache
        operation_log = cache.get(self.operation_log_key, [])
        
        # Filter operations since timestamp
        concurrent_ops = []
        for op_data in operation_log:
            if op_data['timestamp'] > since_timestamp:
                concurrent_ops.append(Operation(
                    type=OperationType(op_data['type']),
                    position=op_data['position'],
                    content=op_data.get('content'),
                    length=op_data.get('length'),
                    author=op_data['author'],
                    timestamp=op_data['timestamp'],
                    operation_id=op_data.get('id')
                ))
        
        # Sort by timestamp to ensure correct order
        concurrent_ops.sort(key=lambda op: op.timestamp)
        return concurrent_ops
    
    async def _store_operation(self, operation: Operation):
        """Store operation in the operation log"""
        operation_log = cache.get(self.operation_log_key, [])
        operation_log.append(self._serialize_operation(operation))
        
        # Keep only recent operations
        if len(operation_log) > self.max_operations:
            operation_log = operation_log[-self.max_operations:]
        
        # Store with extended TTL for operation log
        cache.set(self.operation_log_key, operation_log, 3600)  # 1 hour
    
    async def _apply_operation_to_state(self, operation: Operation):
        """Apply operation to document state"""
        current_state = cache.get(self.document_state_key, "")
        
        try:
            if operation.type == OperationType.INSERT:
                # Insert content at position
                new_state = (
                    current_state[:operation.position] + 
                    operation.content + 
                    current_state[operation.position:]
                )
            elif operation.type == OperationType.DELETE:
                # Delete content at position
                end_pos = operation.position + (operation.length or 0)
                new_state = (
                    current_state[:operation.position] +
                    current_state[end_pos:]
                )
            elif operation.type == OperationType.REPLACE:
                # Replace content at position
                end_pos = operation.position + (operation.length or 0)
                new_state = (
                    current_state[:operation.position] +
                    (operation.content or '') +
                    current_state[end_pos:]
                )
            else:
                # RETAIN operation - no change to content
                new_state = current_state
            
            cache.set(self.document_state_key, new_state, 3600)
            logger.debug(f"Applied {operation.type.value} operation to document {self.document_id}:{self.field_name}")
            
        except Exception as e:
            logger.error(f"Error applying operation {operation.operation_id}: {e}")
    
    def _transform_against_operation(self, op1: Operation, op2: Operation) -> Operation:
        """Transform op1 against op2 using operational transform rules"""
        if op1.type == OperationType.INSERT and op2.type == OperationType.INSERT:
            return self._transform_insert_insert(op1, op2)
        elif op1.type == OperationType.INSERT and op2.type == OperationType.DELETE:
            return self._transform_insert_delete(op1, op2)
        elif op1.type == OperationType.DELETE and op2.type == OperationType.INSERT:
            return self._transform_delete_insert(op1, op2)
        elif op1.type == OperationType.DELETE and op2.type == OperationType.DELETE:
            return self._transform_delete_delete(op1, op2)
        elif op1.type == OperationType.REPLACE or op2.type == OperationType.REPLACE:
            return self._transform_with_replace(op1, op2)
        else:
            # RETAIN operations don't change position
            return op1
    
    def _transform_insert_insert(self, op1: Operation, op2: Operation) -> Operation:
        """Transform insert against insert"""
        if op2.position <= op1.position:
            # op2 happened before op1's position, shift op1 right
            return Operation(
                type=op1.type,
                position=op1.position + len(op2.content or ''),
                content=op1.content,
                author=op1.author,
                timestamp=op1.timestamp,
                operation_id=op1.operation_id
            )
        else:
            # op2 happened after op1's position, no change needed
            return op1
    
    def _transform_insert_delete(self, op1: Operation, op2: Operation) -> Operation:
        """Transform insert against delete"""
        delete_end = op2.position + (op2.length or 0)
        
        if op2.position <= op1.position:
            if delete_end <= op1.position:
                # Delete is completely before insert, shift insert left
                return Operation(
                    type=op1.type,
                    position=max(0, op1.position - (op2.length or 0)),
                    content=op1.content,
                    author=op1.author,
                    timestamp=op1.timestamp,
                    operation_id=op1.operation_id
                )
            else:
                # Delete overlaps with insert position, place at delete start
                return Operation(
                    type=op1.type,
                    position=op2.position,
                    content=op1.content,
                    author=op1.author,
                    timestamp=op1.timestamp,
                    operation_id=op1.operation_id
                )
        else:
            # Delete happened after insert, no change needed
            return op1
    
    def _transform_delete_insert(self, op1: Operation, op2: Operation) -> Operation:
        """Transform delete against insert"""
        if op2.position <= op1.position:
            # Insert happened before delete, shift delete right
            return Operation(
                type=op1.type,
                position=op1.position + len(op2.content or ''),
                length=op1.length,
                author=op1.author,
                timestamp=op1.timestamp,
                operation_id=op1.operation_id
            )
        elif op2.position < op1.position + (op1.length or 0):
            # Insert happened within delete range, extend delete length
            return Operation(
                type=op1.type,
                position=op1.position,
                length=(op1.length or 0) + len(op2.content or ''),
                author=op1.author,
                timestamp=op1.timestamp,
                operation_id=op1.operation_id
            )
        else:
            # Insert happened after delete, no change needed
            return op1
    
    def _transform_delete_delete(self, op1: Operation, op2: Operation) -> Operation:
        """Transform delete against delete"""
        op1_end = op1.position + (op1.length or 0)
        op2_end = op2.position + (op2.length or 0)
        
        if op2_end <= op1.position:
            # op2 delete is completely before op1, shift op1 left
            return Operation(
                type=op1.type,
                position=max(0, op1.position - (op2.length or 0)),
                length=op1.length,
                author=op1.author,
                timestamp=op1.timestamp,
                operation_id=op1.operation_id
            )
        elif op2.position >= op1_end:
            # op2 delete is completely after op1, no change needed
            return op1
        else:
            # Deletes overlap, need to adjust
            if op2.position <= op1.position:
                # op2 starts before or at op1
                overlap_start = op1.position
                overlap_end = min(op1_end, op2_end)
                overlap_length = max(0, overlap_end - overlap_start)
                
                return Operation(
                    type=op1.type,
                    position=op2.position,
                    length=max(0, (op1.length or 0) - overlap_length),
                    author=op1.author,
                    timestamp=op1.timestamp,
                    operation_id=op1.operation_id
                )
            else:
                # op2 starts after op1 begins
                overlap_length = min(op1_end, op2_end) - op2.position
                
                return Operation(
                    type=op1.type,
                    position=op1.position,
                    length=max(0, (op1.length or 0) - overlap_length),
                    author=op1.author,
                    timestamp=op1.timestamp,
                    operation_id=op1.operation_id
                )
    
    def _transform_with_replace(self, op1: Operation, op2: Operation) -> Operation:
        """Handle transformations involving REPLACE operations"""
        # Convert REPLACE to DELETE + INSERT for easier transformation
        if op1.type == OperationType.REPLACE:
            # Transform as delete then insert
            delete_op = Operation(
                type=OperationType.DELETE,
                position=op1.position,
                length=op1.length,
                author=op1.author,
                timestamp=op1.timestamp
            )
            
            insert_op = Operation(
                type=OperationType.INSERT,
                position=op1.position,
                content=op1.content,
                author=op1.author,
                timestamp=op1.timestamp
            )
            
            # Transform delete first, then insert
            transformed_delete = self._transform_against_operation(delete_op, op2)
            transformed_insert = self._transform_against_operation(insert_op, op2)
            
            # Combine back into replace
            return Operation(
                type=OperationType.REPLACE,
                position=transformed_delete.position,
                content=transformed_insert.content,
                length=transformed_delete.length,
                author=op1.author,
                timestamp=op1.timestamp,
                operation_id=op1.operation_id
            )
        
        elif op2.type == OperationType.REPLACE:
            # Transform op1 against a replace operation
            # Treat replace as delete + insert
            delete_equiv = Operation(
                type=OperationType.DELETE,
                position=op2.position,
                length=op2.length,
                author=op2.author,
                timestamp=op2.timestamp
            )
            
            insert_equiv = Operation(
                type=OperationType.INSERT,
                position=op2.position,
                content=op2.content,
                author=op2.author,
                timestamp=op2.timestamp
            )
            
            # Transform against delete first
            temp_op = self._transform_against_operation(op1, delete_equiv)
            # Then against insert
            return self._transform_against_operation(temp_op, insert_equiv)
        
        return op1
    
    async def get_document_state(self) -> str:
        """Get current document state"""
        return cache.get(self.document_state_key, "")
    
    async def set_document_state(self, content: str):
        """Set document state"""
        cache.set(self.document_state_key, content, 3600)
    
    async def reset_document_state(self, initial_content: str = ""):
        """Reset document state and operation log"""
        cache.set(self.document_state_key, initial_content, 3600)
        cache.delete(self.operation_log_key)
        cache.delete(self.operation_counter_key)
        logger.info(f"Reset document state for {self.document_id}:{self.field_name}")
    
    async def get_operation_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent operation history"""
        operation_log = cache.get(self.operation_log_key, [])
        return operation_log[-limit:] if operation_log else []
    
    async def cleanup_old_operations(self, max_age_hours: int = 24):
        """Remove operations older than specified hours"""
        operation_log = cache.get(self.operation_log_key, [])
        if not operation_log:
            return
        
        cutoff_time = time.time() - (max_age_hours * 3600)
        filtered_ops = [
            op for op in operation_log 
            if op.get('timestamp', 0) > cutoff_time
        ]
        
        if len(filtered_ops) != len(operation_log):
            cache.set(self.operation_log_key, filtered_ops, 3600)
            logger.info(f"Cleaned up {len(operation_log) - len(filtered_ops)} old operations")
    
    def _validate_operation(self, operation: Operation, document_length: int) -> bool:
        """Validate that operation is valid for current document state"""
        if operation.position < 0:
            return False
        
        if operation.type in [OperationType.DELETE, OperationType.REPLACE]:
            if operation.position + (operation.length or 0) > document_length:
                return False
        elif operation.type == OperationType.INSERT:
            if operation.position > document_length:
                return False
        
        return True