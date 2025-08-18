"""
Unified Inbox API Views - Record-centric communication endpoints
"""
import logging
from typing import Dict, Any
from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from api.permissions import CommunicationPermission
from communications.services.unified_inbox import UnifiedInboxService
from communications.models import UserChannelConnection, ChannelType

logger = logging.getLogger(__name__)
User = get_user_model()


@extend_schema(
    summary="Get unified inbox with Record-grouped conversations",
    description="Returns all Records with communication activity, grouped by Record with channel summaries",
    parameters=[
        OpenApiParameter(name='limit', type=int, default=50, description='Number of records to return'),
        OpenApiParameter(name='offset', type=int, default=0, description='Pagination offset'),
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'records': {'type': 'array'},
                'total_count': {'type': 'integer'},
                'has_next': {'type': 'boolean'},
                'has_previous': {'type': 'boolean'},
                'current_page': {'type': 'integer'},
                'total_pages': {'type': 'integer'}
            }
        }
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, CommunicationPermission])
def get_unified_inbox(request):
    """Get unified inbox with Record-grouped conversations"""
    try:
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        
        # Validate pagination parameters
        if limit < 1 or limit > 100:
            return Response(
                {'error': 'Limit must be between 1 and 100'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if offset < 0:
            return Response(
                {'error': 'Offset must be non-negative'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Initialize service and get Record conversations
        inbox_service = UnifiedInboxService(request.user)
        result = inbox_service.get_record_conversations(limit=limit, offset=offset)
        
        if 'error' in result:
            return Response(
                {'error': result['error']},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response(
            {'error': f'Invalid parameter format: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error getting unified inbox: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Get unified conversation timeline for a Record",
    description="Returns all messages for a specific Record across all communication channels in chronological order",
    parameters=[
        OpenApiParameter(name='record_id', type=int, location=OpenApiParameter.PATH, description='Record ID'),
        OpenApiParameter(name='limit', type=int, default=50, description='Number of messages to return'),
        OpenApiParameter(name='offset', type=int, default=0, description='Pagination offset'),
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'record': {'type': 'object'},
                'messages': {'type': 'array'},
                'available_channels': {'type': 'array'},
                'pagination': {'type': 'object'}
            }
        }
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, CommunicationPermission])
def get_record_timeline(request, record_id):
    """Get unified conversation timeline for a specific Record"""
    try:
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        
        # Validate pagination parameters
        if limit < 1 or limit > 100:
            return Response(
                {'error': 'Limit must be between 1 and 100'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if offset < 0:
            return Response(
                {'error': 'Offset must be non-negative'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get timeline for Record
        inbox_service = UnifiedInboxService(request.user)
        result = inbox_service.get_record_conversation_timeline(
            record_id=record_id,
            limit=limit,
            offset=offset
        )
        
        if 'error' in result:
            if result['error'] == 'Record not found':
                return Response(
                    {'error': 'Record not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            else:
                return Response(
                    {'error': result['error']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response(
            {'error': f'Invalid parameter format: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error getting record timeline for {record_id}: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Get communication statistics for a Record",
    description="Returns analytics and statistics for communication with a specific Record",
    parameters=[
        OpenApiParameter(name='record_id', type=int, location=OpenApiParameter.PATH, description='Record ID'),
        OpenApiParameter(name='days', type=int, default=30, description='Number of days to analyze'),
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'record_id': {'type': 'integer'},
                'period_days': {'type': 'integer'},
                'total_messages': {'type': 'integer'},
                'sent_messages': {'type': 'integer'},
                'received_messages': {'type': 'integer'},
                'response_rate': {'type': 'number'},
                'avg_response_time_hours': {'type': 'number'},
                'channel_breakdown': {'type': 'object'},
                'first_contact_date': {'type': 'string'},
                'last_activity': {'type': 'string'}
            }
        }
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, CommunicationPermission])
def get_record_stats(request, record_id):
    """Get communication statistics for a Record"""
    try:
        days = int(request.GET.get('days', 30))
        
        # Validate days parameter
        if days < 1 or days > 365:
            return Response(
                {'error': 'Days must be between 1 and 365'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get stats for Record
        inbox_service = UnifiedInboxService(request.user)
        result = inbox_service.get_record_communication_stats(
            record_id=record_id,
            days=days
        )
        
        if 'error' in result:
            if result['error'] == 'Record not found':
                return Response(
                    {'error': 'Record not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            else:
                return Response(
                    {'error': result['error']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response(
            {'error': f'Invalid parameter format: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error getting record stats for {record_id}: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Mark Record conversation as read for specific channel",
    description="Mark all messages in a Record's conversation for a specific channel as read",
    request={
        'type': 'object',
        'properties': {
            'channel_type': {'type': 'string', 'enum': [choice[0] for choice in ChannelType.choices]}
        },
        'required': ['channel_type']
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean'},
                'updated_count': {'type': 'integer'},
                'record_id': {'type': 'integer'},
                'channel_type': {'type': 'string'}
            }
        }
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, CommunicationPermission])
def mark_record_conversation_read(request, record_id):
    """Mark Record conversation as read for specific channel"""
    try:
        channel_type = request.data.get('channel_type')
        
        if not channel_type:
            return Response(
                {'error': 'channel_type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate channel type
        valid_channels = [choice[0] for choice in ChannelType.choices]
        if channel_type not in valid_channels:
            return Response(
                {'error': f'Invalid channel_type. Must be one of: {valid_channels}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Mark as read
        inbox_service = UnifiedInboxService(request.user)
        result = inbox_service.mark_conversation_as_read(
            record_id=record_id,
            channel_type=channel_type
        )
        
        if 'error' in result:
            if result['error'] == 'Record not found':
                return Response(
                    {'error': 'Record not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            else:
                return Response(
                    {'error': result['error']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error marking conversation as read for record {record_id}: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Get user's available communication channels",
    description="Returns list of communication channels the user has connected and their status",
    responses={
        200: {
            'type': 'object',
            'properties': {
                'channels': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'type': {'type': 'string'},
                            'name': {'type': 'string'},
                            'account_name': {'type': 'string'},
                            'status': {'type': 'string'},
                            'can_send': {'type': 'boolean'},
                            'last_sync': {'type': 'string'},
                            'unipile_account_id': {'type': 'string'}
                        }
                    }
                }
            }
        }
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, CommunicationPermission])
def get_user_channels(request):
    """Get user's available communication channels"""
    try:
        # Get user's channel connections
        connections = UserChannelConnection.objects.filter(
            user=request.user,
            is_active=True
        ).order_by('channel_type', '-created_at')
        
        channels = []
        for connection in connections:
            status_info = connection.get_status_display_info()
            
            channels.append({
                'id': str(connection.id),
                'type': connection.channel_type,
                'name': connection.get_channel_type_display(),
                'account_name': connection.account_name,
                'status': connection.account_status,
                'status_display': status_info['display'],
                'can_send': status_info['can_send'],
                'needs_action': status_info['needs_action'],
                'action_type': status_info['action_type'],
                'last_sync': connection.last_sync_at,
                'unipile_account_id': connection.unipile_account_id,
                'created_at': connection.created_at,
                'updated_at': connection.updated_at
            })
        
        return Response({'channels': channels}, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting user channels: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Send message to Record via optimal channel",
    description="Send a message to a Record using the best available communication channel",
    request={
        'type': 'object',
        'properties': {
            'content': {'type': 'string'},
            'subject': {'type': 'string'},
            'channel_type': {'type': 'string', 'description': 'Optional: specific channel to use'},
            'attachments': {'type': 'array', 'items': {'type': 'object'}}
        },
        'required': ['content']
    },
    responses={
        201: {
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean'},
                'message_id': {'type': 'string'},
                'channel_used': {'type': 'string'},
                'record_id': {'type': 'integer'}
            }
        }
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, CommunicationPermission])
def send_message_to_record(request, record_id):
    """Send message to Record via optimal channel"""
    try:
        content = request.data.get('content')
        subject = request.data.get('subject', '')
        channel_type = request.data.get('channel_type')
        attachments = request.data.get('attachments', [])
        
        if not content:
            return Response(
                {'error': 'content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # This would implement the message sending logic
        # For now, return a placeholder response
        return Response(
            {
                'success': True,
                'message_id': 'pending_implementation',
                'channel_used': channel_type or 'auto_selected',
                'record_id': record_id,
                'note': 'Message sending implementation in progress'
            },
            status=status.HTTP_201_CREATED
        )
        
    except Exception as e:
        logger.error(f"Error sending message to record {record_id}: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )