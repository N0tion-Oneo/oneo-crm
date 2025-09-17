"""
Advanced Wait Node Processors - Wait for responses, events, and conditions
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from workflows.nodes.base import AsyncNodeProcessor
from communications.models import Message, Conversation
from pipelines.models import Record

logger = logging.getLogger(__name__)


class WaitForResponseProcessor(AsyncNodeProcessor):
    """Wait for a response to a communication before continuing"""

    def __init__(self):
        super().__init__()
        self.node_type = "wait_for_response"
        self.supports_replay = True
        self.supports_checkpoints = True

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process wait for response node"""

        node_data = node_config.get('data', {})

        # Extract configuration
        wait_for = node_data.get('wait_for', 'any_response')  # any_response, specific_contact, contains_keyword
        channel = node_data.get('channel', 'any')  # any, email, whatsapp, linkedin
        timeout_minutes = node_data.get('timeout_minutes', 60)
        timeout_action = node_data.get('timeout_action', 'continue')  # continue, fail, branch
        contains_keyword = node_data.get('contains_keyword', '')
        specific_contact_id = node_data.get('specific_contact_id')

        # Get the last sent message from context
        last_message_id = context.get('last_sent_message_id')
        conversation_id = context.get('conversation_id')
        record_id = context.get('record_id')

        if not any([last_message_id, conversation_id, record_id]):
            raise ValueError("No message, conversation, or record context found to wait for response")

        start_time = timezone.now()
        timeout_time = start_time + timedelta(minutes=timeout_minutes)

        try:
            # Poll for response
            response_message = None
            while timezone.now() < timeout_time:
                # Check for new messages in the conversation
                query = Q()

                if conversation_id:
                    query &= Q(conversation_id=conversation_id)
                elif last_message_id:
                    # Get conversation from last message
                    try:
                        last_msg = await Message.objects.aget(id=last_message_id)
                        query &= Q(conversation_id=last_msg.conversation_id)
                    except Message.DoesNotExist:
                        pass
                elif record_id:
                    # Get conversations for this record
                    query &= Q(conversation__record_id=record_id)

                # Filter by channel if specified
                if channel != 'any':
                    query &= Q(channel=channel)

                # Filter by direction (incoming messages only)
                query &= Q(direction='inbound')

                # Filter by timestamp (messages after we started waiting)
                query &= Q(created_at__gt=start_time)

                # Check for response
                async for message in Message.objects.filter(query).order_by('created_at'):
                    # Check wait conditions
                    if wait_for == 'any_response':
                        response_message = message
                        break
                    elif wait_for == 'specific_contact' and specific_contact_id:
                        if str(message.from_contact_id) == str(specific_contact_id):
                            response_message = message
                            break
                    elif wait_for == 'contains_keyword' and contains_keyword:
                        if contains_keyword.lower() in message.content.lower():
                            response_message = message
                            break

                if response_message:
                    break

                # Wait before checking again
                await asyncio.sleep(10)  # Check every 10 seconds

            # Handle result
            if response_message:
                return {
                    'success': True,
                    'response_received': True,
                    'response_message_id': str(response_message.id),
                    'response_content': response_message.content,
                    'response_from': response_message.from_email or response_message.from_contact_id,
                    'response_channel': response_message.channel,
                    'wait_time_seconds': (timezone.now() - start_time).total_seconds()
                }
            else:
                # Timeout reached
                if timeout_action == 'fail':
                    raise TimeoutError(f"No response received within {timeout_minutes} minutes")
                else:
                    return {
                        'success': True,
                        'response_received': False,
                        'timeout_reached': True,
                        'timeout_action': timeout_action,
                        'wait_time_seconds': timeout_minutes * 60
                    }

        except Exception as e:
            logger.error(f"Wait for response failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'wait_for': wait_for,
                'channel': channel
            }


class WaitForRecordEventProcessor(AsyncNodeProcessor):
    """Wait for a specific event to occur on a record"""

    def __init__(self):
        super().__init__()
        self.node_type = "wait_for_record_event"
        self.supports_replay = True
        self.supports_checkpoints = True

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process wait for record event node"""

        node_data = node_config.get('data', {})

        # Extract configuration
        field_name = config.get('field_name', '')
        expected_value = config.get('expected_value')
        comparison_operator = config.get('comparison_operator', 'equals')
        timeout_minutes = config.get('timeout_minutes', 60)
        timeout_action = config.get('timeout_action', 'continue')
        poll_interval_seconds = config.get('poll_interval_seconds', 30)
        record_id_source = config.get('record_id_source', '')
        record_id = self._get_nested_value(context, record_id_source) if record_id_source else context.get('record_id')

        if not record_id:
            raise ValueError("No record ID specified to monitor for events")

        start_time = timezone.now()
        timeout_time = start_time + timedelta(minutes=timeout_minutes)

        try:
            # Get initial record state
            initial_record = await Record.objects.aget(id=record_id)
            initial_value = initial_record.data.get(field_name) if field_name else None

            # Poll for changes
            event_occurred = False
            while timezone.now() < timeout_time:
                # Check record state
                try:
                    current_record = await Record.objects.aget(id=record_id)
                except Record.DoesNotExist:
                    if event_type == 'record_deleted':
                        event_occurred = True
                        break
                    else:
                        raise

                if event_type == 'field_changed' and field_name:
                    current_value = current_record.data.get(field_name)

                    # Check if field changed
                    if current_value != initial_value:
                        # Apply comparison if expected value specified
                        if expected_value is not None:
                            if comparison_operator == 'equals' and current_value == expected_value:
                                event_occurred = True
                            elif comparison_operator == 'not_equals' and current_value != expected_value:
                                event_occurred = True
                            elif comparison_operator == 'contains' and expected_value in str(current_value):
                                event_occurred = True
                            elif comparison_operator == 'greater_than' and current_value > expected_value:
                                event_occurred = True
                            elif comparison_operator == 'less_than' and current_value < expected_value:
                                event_occurred = True
                        else:
                            # Any change is sufficient
                            event_occurred = True

                elif event_type == 'status_changed':
                    current_status = current_record.data.get('status')
                    initial_status = initial_record.data.get('status')

                    if current_status != initial_status:
                        if expected_value and current_status == expected_value:
                            event_occurred = True
                        elif not expected_value:
                            event_occurred = True

                if event_occurred:
                    break

                # Wait before checking again
                await asyncio.sleep(5)  # Check every 5 seconds

            # Handle result
            if event_occurred:
                return {
                    'success': True,
                    'event_occurred': True,
                    'event_type': event_type,
                    'record_id': str(record_id),
                    'wait_time_seconds': (timezone.now() - start_time).total_seconds()
                }
            else:
                # Timeout reached
                if timeout_action == 'fail':
                    raise TimeoutError(f"Event did not occur within {timeout_minutes} minutes")
                else:
                    return {
                        'success': True,
                        'event_occurred': False,
                        'timeout_reached': True,
                        'timeout_action': timeout_action,
                        'wait_time_seconds': timeout_minutes * 60
                    }

        except Exception as e:
            logger.error(f"Wait for record event failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'event_type': event_type,
                'record_id': str(record_id)
            }


class WaitForConditionProcessor(AsyncNodeProcessor):
    """Wait for a complex condition to be met"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["conditions"],
        "properties": {
            "conditions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {
                            "type": "string",
                            "description": "Field to check"
                        },
                        "operator": {
                            "type": "string",
                            "description": "Comparison operator"
                        },
                        "value": {
                            "description": "Value to compare against"
                        }
                    }
                },
                "description": "Conditions to wait for",
                "ui_hints": {
                    "widget": "condition_builder",
                    "help_text": "Define conditions that must be met before proceeding"
                }
            },
            "check_interval_seconds": {
                "type": "integer",
                "minimum": 5,
                "maximum": 300,
                "default": 30,
                "description": "How often to check condition (seconds)"
            },
            "timeout_minutes": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10080,
                "default": 60,
                "description": "Timeout in minutes (max 7 days)"
            },
            "timeout_action": {
                "type": "string",
                "enum": ["continue", "fail", "branch"],
                "default": "continue",
                "description": "Action when timeout is reached",
                "ui_hints": {
                    "widget": "radio"
                }
            },
            "refresh_context": {
                "type": "boolean",
                "default": True,
                "description": "Refresh context data on each check"
            },
            "external_check": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["api", "database", "cache"]
                    },
                    "endpoint": {"type": "string"},
                    "query": {"type": "string"}
                },
                "description": "External source to check",
                "ui_hints": {
                    "widget": "external_check_config",
                    "section": "advanced"
                }
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "wait_for_condition"
        self.supports_replay = True
        self.supports_checkpoints = True

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process wait for condition node"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Extract configuration
        conditions = config.get('conditions', [])
        logic_operator = config.get('logic_operator', 'AND')
        group_operators = config.get('group_operators', {})
        check_interval_seconds = config.get('check_interval_seconds', 30)
        timeout_minutes = config.get('timeout_minutes', 60)
        timeout_action = config.get('timeout_action', 'continue')
        refresh_context = config.get('refresh_context', True)
        external_check = config.get('external_check', {})

        start_time = timezone.now()
        timeout_time = start_time + timedelta(minutes=timeout_minutes)

        try:
            from workflows.utils.condition_evaluator import condition_evaluator

            # Poll for condition
            condition_met = False
            evaluation_details = None

            while timezone.now() < timeout_time:
                # Refresh context if needed
                current_context = context
                if refresh_context:
                    # Could refresh from database or external source
                    current_context = dict(context)  # Create a fresh copy

                # Check if we need to make an external API call first
                if external_check.get('enabled'):
                    # Make external API call and add result to context
                    api_url = external_check.get('api_url')
                    if api_url:
                        try:
                            import aiohttp
                            async with aiohttp.ClientSession() as session:
                                async with session.get(api_url) as response:
                                    if response.status == 200:
                                        api_data = await response.json()
                                        current_context['external_data'] = api_data
                        except Exception as e:
                            logger.warning(f"External API check failed: {e}")

                # Evaluate conditions using the grouped condition evaluator
                if conditions:
                    condition_met, evaluation_details = condition_evaluator.evaluate(
                        conditions=conditions,
                        data=current_context,
                        logic_operator=logic_operator,
                        group_operators=group_operators
                    )

                if condition_met:
                    break

                # Wait before checking again
                await asyncio.sleep(check_interval_seconds)

            # Handle result
            if condition_met:
                return {
                    'success': True,
                    'condition_met': True,
                    'evaluation_details': evaluation_details,
                    'wait_time_seconds': (timezone.now() - start_time).total_seconds()
                }
            else:
                # Timeout reached
                if timeout_action == 'fail':
                    raise TimeoutError(f"Condition not met within {timeout_minutes} minutes")
                else:
                    return {
                        'success': True,
                        'condition_met': False,
                        'timeout_reached': True,
                        'timeout_action': timeout_action,
                        'evaluation_details': evaluation_details,
                        'wait_time_seconds': timeout_minutes * 60
                    }

        except Exception as e:
            logger.error(f"Wait for condition failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }