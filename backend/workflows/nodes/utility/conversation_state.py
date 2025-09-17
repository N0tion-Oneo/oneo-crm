"""
Conversation State Manager Node - Track and manage conversation state across workflow
"""
import logging
from typing import Dict, Any, List, Optional
from workflows.nodes.base import AsyncNodeProcessor
from django.utils import timezone
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class ConversationStateProcessor(AsyncNodeProcessor):
    """Manage conversation state and context across workflow nodes"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["action"],
        "properties": {
            "action": {
                "type": "string",
                "enum": ["update", "reset", "merge", "checkpoint"],
                "default": "update",
                "description": "State management action",
                "ui_hints": {
                    "widget": "radio"
                }
            },
            "state_key": {
                "type": "string",
                "default": "conversation_state",
                "description": "Key for state storage in context",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "conversation_state or custom_state"
                }
            },
            "max_history_size": {
                "type": "integer",
                "minimum": 5,
                "maximum": 100,
                "default": 20,
                "description": "Maximum conversation history entries"
            },
            "custom_fields": {
                "type": "object",
                "description": "Custom fields to track from context",
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 4,
                    "placeholder": '{\n  "intent": "detected_intent",\n  "sentiment": "sentiment_score"\n}'
                }
            },
            "track_metrics": {
                "type": "boolean",
                "default": True,
                "description": "Track conversation metrics"
            },
            "track_flags": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["needs_escalation", "conversation_complete", "opt_out_detected", "objective_achieved"]
                },
                "description": "Flags to automatically track",
                "ui_hints": {
                    "widget": "multiselect"
                }
            },
            "merge_strategy": {
                "type": "string",
                "enum": ["overwrite", "deep_merge", "append"],
                "default": "deep_merge",
                "description": "How to merge states",
                "ui_hints": {
                    "widget": "select",
                    "show_when": {"action": "merge"}
                }
            },
            "checkpoint_name": {
                "type": "string",
                "description": "Name for state checkpoint",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "before_escalation",
                    "show_when": {"action": "checkpoint"}
                }
            },
            "persist_to_storage": {
                "type": "boolean",
                "default": False,
                "description": "Persist state to external storage",
                "ui_hints": {
                    "section": "advanced"
                }
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "conversation_state"
        self.supports_replay = True
        self.supports_checkpoints = True

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process conversation state management"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Extract configuration
        action = config.get('action', 'update')
        state_key = config.get('state_key', 'conversation_state')

        # State operations
        if action == 'update':
            result = await self._update_state(node_data, context, state_key)
        elif action == 'reset':
            result = await self._reset_state(node_data, context, state_key)
        elif action == 'merge':
            result = await self._merge_state(node_data, context, state_key)
        elif action == 'checkpoint':
            result = await self._checkpoint_state(node_data, context, state_key)
        else:
            result = {'success': False, 'error': f'Unknown action: {action}'}

        return result

    async def _update_state(self, node_data: Dict, context: Dict, state_key: str) -> Dict[str, Any]:
        """Update conversation state with new information"""

        # Get existing state
        current_state = context.get(state_key, {})
        if not isinstance(current_state, dict):
            current_state = {}

        # Track conversation metrics
        if 'conversation_metrics' not in current_state:
            current_state['conversation_metrics'] = {
                'message_count': 0,
                'start_time': timezone.now().isoformat(),
                'last_update': timezone.now().isoformat(),
                'channels_used': set(),
                'participant_responses': 0
            }

        # Update metrics
        metrics = current_state['conversation_metrics']
        metrics['message_count'] = metrics.get('message_count', 0) + 1
        metrics['last_update'] = timezone.now().isoformat()

        # Track channel if available
        if 'channel' in context:
            if isinstance(metrics['channels_used'], set):
                metrics['channels_used'].add(context['channel'])
            else:
                metrics['channels_used'] = {context['channel']}

        # Add message to history
        if 'conversation_history' not in current_state:
            current_state['conversation_history'] = []

        # Append new message if available
        if 'last_message' in context or 'generated_message' in context:
            new_entry = {
                'timestamp': timezone.now().isoformat(),
                'type': 'received' if 'last_message' in context else 'sent',
                'content': context.get('last_message') or context.get('generated_message'),
                'channel': context.get('channel', 'unknown'),
                'sender': context.get('sender', 'system')
            }
            current_state['conversation_history'].append(new_entry)

            # Limit history size
            max_history = node_data.get('config', {}).get('max_history_size', 20)
            if len(current_state['conversation_history']) > max_history:
                current_state['conversation_history'] = current_state['conversation_history'][-max_history:]

        # Update objective progress if available
        if 'evaluation_result' in context:
            if 'objective_progress' not in current_state:
                current_state['objective_progress'] = []

            current_state['objective_progress'].append({
                'timestamp': timezone.now().isoformat(),
                'score': context['evaluation_result'].get('score', 0),
                'insights': context.get('evaluation_insights', [])
            })

        # Store custom fields
        custom_fields = node_data.get('config', {}).get('custom_fields', {})
        for field_name, field_source in custom_fields.items():
            if field_source in context:
                current_state[field_name] = context[field_source]

        # Handle participant information
        if 'participant_info' in context:
            current_state['participant_info'] = context['participant_info']

        # Track conversation flags
        flags = current_state.get('flags', {})

        # Auto-detect certain conditions
        if context.get('evaluation_outcome', {}).get('recommended_action') == 'escalate':
            flags['needs_escalation'] = True

        if context.get('should_continue') is False:
            flags['conversation_complete'] = True

        if 'opt_out' in str(context.get('last_message', '')).lower():
            flags['opt_out_detected'] = True

        current_state['flags'] = flags

        # Calculate conversation duration
        if 'start_time' in metrics:
            start = datetime.fromisoformat(metrics['start_time'].replace('Z', '+00:00'))
            duration = (timezone.now() - start).total_seconds()
            metrics['duration_seconds'] = duration

        # Convert sets to lists for JSON serialization
        if isinstance(metrics.get('channels_used'), set):
            metrics['channels_used'] = list(metrics['channels_used'])

        # Update context with new state
        context[state_key] = current_state

        # Also update specific context fields for other nodes
        context['conversation_history'] = current_state.get('conversation_history', [])
        context['conversation_metrics'] = metrics
        context['conversation_flags'] = flags

        return {
            'success': True,
            'action': 'update',
            'state_key': state_key,
            'metrics': metrics,
            'flags': flags,
            'history_size': len(current_state.get('conversation_history', [])),
            'state_size': len(json.dumps(current_state))
        }

    async def _reset_state(self, node_data: Dict, context: Dict, state_key: str) -> Dict[str, Any]:
        """Reset conversation state"""

        # Preserve certain fields if requested
        preserve_fields = node_data.get('preserve_fields', [])
        current_state = context.get(state_key, {})
        preserved = {}

        for field in preserve_fields:
            if field in current_state:
                preserved[field] = current_state[field]

        # Create new state
        new_state = {
            'conversation_metrics': {
                'message_count': 0,
                'start_time': timezone.now().isoformat(),
                'last_update': timezone.now().isoformat(),
                'channels_used': [],
                'participant_responses': 0
            },
            'conversation_history': [],
            'flags': {}
        }

        # Restore preserved fields
        new_state.update(preserved)

        # Update context
        context[state_key] = new_state
        context['conversation_history'] = []
        context['conversation_metrics'] = new_state['conversation_metrics']
        context['conversation_flags'] = {}

        return {
            'success': True,
            'action': 'reset',
            'state_key': state_key,
            'preserved_fields': preserve_fields,
            'new_state_initialized': True
        }

    async def _merge_state(self, node_data: Dict, context: Dict, state_key: str) -> Dict[str, Any]:
        """Merge state from multiple sources"""

        current_state = context.get(state_key, {})
        merge_sources = node_data.get('merge_sources', [])
        merge_strategy = node_data.get('merge_strategy', 'combine')  # combine, override, append

        for source_key in merge_sources:
            if source_key in context:
                source_data = context[source_key]

                if merge_strategy == 'override':
                    current_state.update(source_data)
                elif merge_strategy == 'append':
                    for key, value in source_data.items():
                        if key in current_state and isinstance(current_state[key], list):
                            current_state[key].extend(value if isinstance(value, list) else [value])
                        else:
                            current_state[key] = value
                else:  # combine
                    for key, value in source_data.items():
                        if key not in current_state:
                            current_state[key] = value

        context[state_key] = current_state

        return {
            'success': True,
            'action': 'merge',
            'state_key': state_key,
            'merged_sources': merge_sources,
            'merge_strategy': merge_strategy,
            'resulting_keys': list(current_state.keys())
        }

    async def _checkpoint_state(self, node_data: Dict, context: Dict, state_key: str) -> Dict[str, Any]:
        """Create a checkpoint of current state"""

        current_state = context.get(state_key, {})
        checkpoint_key = node_data.get('checkpoint_key', f'{state_key}_checkpoint_{timezone.now().timestamp()}')

        # Create checkpoint
        checkpoint = {
            'timestamp': timezone.now().isoformat(),
            'state': current_state.copy(),
            'context_keys': list(context.keys()),
            'checkpoint_reason': node_data.get('reason', 'manual')
        }

        # Store checkpoint
        context[checkpoint_key] = checkpoint

        # Optionally store in conversation state
        if node_data.get('store_in_state', True):
            if 'checkpoints' not in current_state:
                current_state['checkpoints'] = []

            # Limit checkpoint history
            max_checkpoints = node_data.get('max_checkpoints', 5)
            current_state['checkpoints'].append({
                'key': checkpoint_key,
                'timestamp': checkpoint['timestamp'],
                'reason': checkpoint['checkpoint_reason']
            })

            if len(current_state['checkpoints']) > max_checkpoints:
                current_state['checkpoints'] = current_state['checkpoints'][-max_checkpoints:]

        return {
            'success': True,
            'action': 'checkpoint',
            'checkpoint_key': checkpoint_key,
            'checkpoint_created': True,
            'state_size': len(json.dumps(checkpoint))
        }

    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate node inputs"""
        node_data = node_config.get('data', {})

        # Check action type
        valid_actions = ['update', 'reset', 'merge', 'checkpoint']
        if node_data.get('action', 'update') not in valid_actions:
            return False

        # Validate merge sources if merging
        if node_data.get('action') == 'merge':
            merge_sources = node_data.get('merge_sources', [])
            if not merge_sources or not isinstance(merge_sources, list):
                return False

        return True