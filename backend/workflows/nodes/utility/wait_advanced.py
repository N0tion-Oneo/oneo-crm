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
        self.node_type = "WAIT_FOR_RESPONSE"
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
        self.node_type = "WAIT_FOR_RECORD_EVENT"
        self.supports_replay = True
        self.supports_checkpoints = True

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process wait for record event node"""

        node_data = node_config.get('data', {})

        # Extract configuration
        event_type = node_data.get('event_type', 'field_changed')  # field_changed, status_changed, record_deleted
        field_name = node_data.get('field_name', '')
        expected_value = node_data.get('expected_value')
        comparison_operator = node_data.get('comparison_operator', 'equals')  # equals, not_equals, contains, greater_than, less_than
        timeout_minutes = node_data.get('timeout_minutes', 60)
        timeout_action = node_data.get('timeout_action', 'continue')
        record_id = node_data.get('record_id') or context.get('record_id')

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

    def __init__(self):
        super().__init__()
        self.node_type = "WAIT_FOR_CONDITION"
        self.supports_replay = True
        self.supports_checkpoints = True

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process wait for condition node"""

        node_data = node_config.get('data', {})

        # Extract configuration
        condition_type = node_data.get('condition_type', 'expression')  # expression, record_count, aggregate
        expression = node_data.get('expression', '')
        check_interval_seconds = node_data.get('check_interval_seconds', 30)
        timeout_minutes = node_data.get('timeout_minutes', 60)
        timeout_action = node_data.get('timeout_action', 'continue')

        # For record_count conditions
        pipeline_id = node_data.get('pipeline_id')
        filter_conditions = node_data.get('filter_conditions', {})
        expected_count = node_data.get('expected_count', 0)
        count_operator = node_data.get('count_operator', 'greater_than')

        # For aggregate conditions
        aggregate_field = node_data.get('aggregate_field')
        aggregate_function = node_data.get('aggregate_function', 'sum')  # sum, avg, min, max, count
        aggregate_expected = node_data.get('aggregate_expected', 0)

        start_time = timezone.now()
        timeout_time = start_time + timedelta(minutes=timeout_minutes)

        try:
            # Poll for condition
            condition_met = False
            while timezone.now() < timeout_time:

                if condition_type == 'expression':
                    # Evaluate expression with context
                    try:
                        # Simple expression evaluation (can be enhanced)
                        result = eval(expression, {"context": context})
                        if result:
                            condition_met = True
                    except Exception as e:
                        logger.warning(f"Expression evaluation failed: {e}")

                elif condition_type == 'record_count' and pipeline_id:
                    # Check record count in pipeline
                    query = Q(pipeline_id=pipeline_id)

                    # Apply filters
                    for field, value in filter_conditions.items():
                        query &= Q(**{f"data__{field}": value})

                    count = await Record.objects.filter(query).acount()

                    if count_operator == 'equals' and count == expected_count:
                        condition_met = True
                    elif count_operator == 'greater_than' and count > expected_count:
                        condition_met = True
                    elif count_operator == 'less_than' and count < expected_count:
                        condition_met = True
                    elif count_operator == 'greater_or_equal' and count >= expected_count:
                        condition_met = True
                    elif count_operator == 'less_or_equal' and count <= expected_count:
                        condition_met = True

                elif condition_type == 'aggregate' and pipeline_id and aggregate_field:
                    # Calculate aggregate value
                    records = Record.objects.filter(pipeline_id=pipeline_id)

                    # Apply filters
                    for field, value in filter_conditions.items():
                        records = records.filter(**{f"data__{field}": value})

                    values = []
                    async for record in records:
                        value = record.data.get(aggregate_field)
                        if value is not None:
                            try:
                                values.append(float(value))
                            except (TypeError, ValueError):
                                pass

                    if values:
                        if aggregate_function == 'sum':
                            result = sum(values)
                        elif aggregate_function == 'avg':
                            result = sum(values) / len(values)
                        elif aggregate_function == 'min':
                            result = min(values)
                        elif aggregate_function == 'max':
                            result = max(values)
                        elif aggregate_function == 'count':
                            result = len(values)
                        else:
                            result = 0

                        if result >= aggregate_expected:
                            condition_met = True

                if condition_met:
                    break

                # Wait before checking again
                await asyncio.sleep(check_interval_seconds)

            # Handle result
            if condition_met:
                return {
                    'success': True,
                    'condition_met': True,
                    'condition_type': condition_type,
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
                        'wait_time_seconds': timeout_minutes * 60
                    }

        except Exception as e:
            logger.error(f"Wait for condition failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'condition_type': condition_type
            }