"""
Channel Availability API Views
Manages Record-level channel availability tracking and recommendations
"""
import logging
from typing import Dict, Any, List
from datetime import timedelta
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from api.permissions import CommunicationPermission
from communications.services.channel_availability import get_channel_availability_tracker
from pipelines.models import Record

logger = logging.getLogger(__name__)


@extend_schema(
    summary="Get channel availability for a Record",
    description="Analyzes and returns available communication channels for a specific Record",
    parameters=[
        OpenApiParameter(name='record_id', type=int, location=OpenApiParameter.PATH, description='Record ID'),
        OpenApiParameter(name='refresh_cache', type=bool, default=False, description='Force refresh of cached data'),
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'record_id': {'type': 'integer'},
                'record_title': {'type': 'string'},
                'last_updated': {'type': 'string'},
                'contact_info': {'type': 'object'},
                'available_channels': {'type': 'array'},
                'recommendations': {'type': 'object'},
                'summary': {'type': 'object'}
            }
        }
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, CommunicationPermission])
def get_record_channel_availability(request, record_id):
    """Get channel availability for a specific Record"""
    try:
        # Validate Record exists and user has access
        try:
            record = Record.objects.get(id=record_id, is_deleted=False)
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get refresh_cache parameter
        refresh_cache = request.GET.get('refresh_cache', 'false').lower() == 'true'
        
        # Get channel availability
        tracker = get_channel_availability_tracker(request.user)
        availability = tracker.get_record_channel_availability(
            record=record,
            refresh_cache=refresh_cache
        )
        
        if 'error' in availability:
            return Response(
                {'error': availability['error']},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response(availability, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting channel availability for record {record_id}: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Get channel recommendations for a Record",
    description="Get smart channel recommendations for communicating with a Record",
    parameters=[
        OpenApiParameter(name='record_id', type=int, location=OpenApiParameter.PATH, description='Record ID'),
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'record_id': {'type': 'integer'},
                'primary_channel': {'type': 'object'},
                'alternative_channels': {'type': 'array'},
                'setup_recommendations': {'type': 'array'},
                'engagement_strategy': {'type': 'object'},
                'reasoning': {'type': 'array'}
            }
        }
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, CommunicationPermission])
def get_record_channel_recommendations(request, record_id):
    """Get smart channel recommendations for a Record"""
    try:
        # Validate Record exists and user has access
        try:
            record = Record.objects.get(id=record_id, is_deleted=False)
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get channel availability (which includes recommendations)
        tracker = get_channel_availability_tracker(request.user)
        availability = tracker.get_record_channel_availability(record)
        
        if 'error' in availability:
            return Response(
                {'error': availability['error']},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Extract just the recommendations
        recommendations = availability.get('recommendations', {})
        recommendations['record_id'] = record_id
        recommendations['record_title'] = record.title
        
        return Response(recommendations, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting channel recommendations for record {record_id}: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Bulk analyze channel availability",
    description="Analyze channel availability for multiple Records in bulk",
    request={
        'type': 'object',
        'properties': {
            'record_ids': {'type': 'array', 'items': {'type': 'integer'}},
            'include_recommendations': {'type': 'boolean', 'default': True}
        },
        'required': ['record_ids']
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean'},
                'total_records': {'type': 'integer'},
                'successful_analyses': {'type': 'integer'},
                'failed_analyses': {'type': 'integer'},
                'results': {'type': 'object'},
                'failed_records': {'type': 'array'},
                'summary': {'type': 'object'}
            }
        }
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, CommunicationPermission])
def bulk_analyze_channel_availability(request):
    """Analyze channel availability for multiple Records in bulk"""
    try:
        record_ids = request.data.get('record_ids', [])
        include_recommendations = request.data.get('include_recommendations', True)
        
        if not record_ids:
            return Response(
                {'error': 'record_ids is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(record_ids) > 100:  # Limit bulk operations
            return Response(
                {'error': 'Maximum 100 records allowed per bulk operation'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate all records exist
        records = Record.objects.filter(id__in=record_ids, is_deleted=False)
        if len(records) != len(record_ids):
            found_ids = set(record.id for record in records)
            missing_ids = set(record_ids) - found_ids
            return Response(
                {'error': f'Records not found: {list(missing_ids)}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Perform bulk analysis
        tracker = get_channel_availability_tracker(request.user)
        bulk_result = tracker.bulk_analyze_channel_availability(record_ids)
        
        # Process results to optionally exclude recommendations
        if not include_recommendations:
            for record_id, result in bulk_result.get('results', {}).items():
                if 'recommendations' in result:
                    # Keep only summary of recommendations
                    result['recommendations'] = {
                        'has_recommendations': bool(result['recommendations'].get('primary_channel')),
                        'setup_actions_needed': len(result['recommendations'].get('setup_recommendations', []))
                    }
        
        # Add summary statistics
        if bulk_result['success']:
            summary = _calculate_bulk_summary(bulk_result['results'])
            bulk_result['summary'] = summary
        
        return Response(bulk_result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in bulk channel availability analysis: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Get channel availability summary for user",
    description="Get overall channel availability statistics for the current user",
    parameters=[
        OpenApiParameter(name='include_setup_recommendations', type=bool, default=True, 
                        description='Include setup recommendations in response'),
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'user_id': {'type': 'integer'},
                'connected_channels': {'type': 'array'},
                'total_records_with_communication': {'type': 'integer'},
                'channel_utilization': {'type': 'object'},
                'setup_recommendations': {'type': 'array'},
                'overall_readiness_score': {'type': 'number'}
            }
        }
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, CommunicationPermission])
def get_user_channel_summary(request):
    """Get overall channel availability summary for the current user"""
    try:
        include_setup = request.GET.get('include_setup_recommendations', 'true').lower() == 'true'
        
        tracker = get_channel_availability_tracker(request.user)
        
        # Get user's connected channels
        user_channels = tracker._get_user_connected_channels()
        
        # Get Records with communication activity
        records_with_communication = Record.objects.filter(
            is_deleted=False
        ).filter(
            Q(primary_conversations__isnull=False) |
            Q(message_contact_records__isnull=False)
        ).distinct()
        
        # Calculate channel utilization
        channel_utilization = _calculate_channel_utilization(user_channels, records_with_communication)
        
        # Generate setup recommendations if requested
        setup_recommendations = []
        if include_setup:
            setup_recommendations = _generate_user_setup_recommendations(user_channels, channel_utilization)
        
        # Calculate overall readiness score
        readiness_score = _calculate_user_readiness_score(user_channels, channel_utilization)
        
        summary = {
            'user_id': request.user.id,
            'connected_channels': [
                {
                    'type': ch['type'],
                    'name': ch['name'],
                    'status': ch['status'],
                    'can_send': ch['can_send'],
                    'last_sync': ch['last_sync']
                }
                for ch in user_channels
            ],
            'total_records_with_communication': records_with_communication.count(),
            'channel_utilization': channel_utilization,
            'setup_recommendations': setup_recommendations,
            'overall_readiness_score': readiness_score,
            'last_updated': timezone.now()
        }
        
        return Response(summary, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting user channel summary: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Invalidate channel availability cache",
    description="Invalidate cached channel availability data for specific Records",
    request={
        'type': 'object',
        'properties': {
            'record_ids': {'type': 'array', 'items': {'type': 'integer'}},
            'invalidate_all': {'type': 'boolean', 'default': False}
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean'},
                'invalidated_records': {'type': 'array'},
                'message': {'type': 'string'}
            }
        }
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, CommunicationPermission])
def invalidate_channel_cache(request):
    """Invalidate channel availability cache for Records"""
    try:
        record_ids = request.data.get('record_ids', [])
        invalidate_all = request.data.get('invalidate_all', False)
        
        tracker = get_channel_availability_tracker(request.user)
        invalidated_records = []
        
        if invalidate_all:
            # This would be expensive - implement with caution
            return Response(
                {'error': 'Global cache invalidation not supported. Use specific record_ids.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not record_ids:
            return Response(
                {'error': 'record_ids is required when invalidate_all is false'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate records exist
        existing_records = Record.objects.filter(id__in=record_ids, is_deleted=False)
        existing_record_ids = list(existing_records.values_list('id', flat=True))
        
        # Invalidate cache for existing records
        for record_id in existing_record_ids:
            tracker.invalidate_record_cache(record_id)
            invalidated_records.append(record_id)
        
        # Report any missing records
        missing_ids = set(record_ids) - set(existing_record_ids)
        message = f"Invalidated cache for {len(invalidated_records)} records"
        if missing_ids:
            message += f". Records not found: {list(missing_ids)}"
        
        return Response({
            'success': True,
            'invalidated_records': invalidated_records,
            'missing_records': list(missing_ids),
            'message': message
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error invalidating channel cache: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Helper functions

def _calculate_bulk_summary(results: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate summary statistics for bulk analysis results"""
    if not results:
        return {}
    
    total_records = len(results)
    records_with_available_channels = 0
    records_with_recommendations = 0
    total_available_channels = 0
    channel_type_usage = {}
    
    for record_result in results.values():
        available_channels = [
            ch for ch in record_result.get('available_channels', [])
            if ch['status'] == 'available'
        ]
        
        if available_channels:
            records_with_available_channels += 1
            total_available_channels += len(available_channels)
            
            # Count channel type usage
            for channel in available_channels:
                channel_type = channel['channel_type']
                channel_type_usage[channel_type] = channel_type_usage.get(channel_type, 0) + 1
        
        if record_result.get('recommendations', {}).get('primary_channel'):
            records_with_recommendations += 1
    
    return {
        'total_analyzed': total_records,
        'records_with_available_channels': records_with_available_channels,
        'records_with_recommendations': records_with_recommendations,
        'average_available_channels': total_available_channels / total_records if total_records > 0 else 0,
        'channel_type_distribution': channel_type_usage,
        'readiness_percentage': (records_with_available_channels / total_records * 100) if total_records > 0 else 0
    }


def _calculate_channel_utilization(user_channels: List[Dict[str, Any]], 
                                 records: Any) -> Dict[str, Any]:
    """Calculate channel utilization statistics"""
    from communications.models import Message, ChannelType
    
    utilization = {
        'total_connected_channels': len(user_channels),
        'active_channels': len([ch for ch in user_channels if ch['can_send']]),
        'channel_breakdown': {},
        'message_volume_by_channel': {}
    }
    
    # Analyze message volume by channel
    for channel_choice in ChannelType.choices:
        channel_type = channel_choice[0]  # Get the value from (value, label) tuple
        message_count = Message.objects.filter(
            Q(channel__channel_type=channel_type) |
            Q(conversation__channel__channel_type=channel_type),
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        utilization['message_volume_by_channel'][channel_type] = message_count
        
        # Channel breakdown
        user_channel = next((ch for ch in user_channels if ch['type'] == channel_type), None)
        utilization['channel_breakdown'][channel_type] = {
            'connected': bool(user_channel),
            'can_send': user_channel['can_send'] if user_channel else False,
            'recent_messages': message_count,
            'status': user_channel['status'] if user_channel else 'not_connected'
        }
    
    return utilization


def _generate_user_setup_recommendations(user_channels: List[Dict[str, Any]], 
                                       utilization: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate setup recommendations for the user"""
    from communications.models import ChannelType
    
    recommendations = []
    
    # Check for missing high-priority channels
    connected_types = {ch['type'] for ch in user_channels if ch['can_send']}
    high_priority_channels = ['whatsapp', 'linkedin', 'gmail']
    
    for channel_type in high_priority_channels:
        if channel_type not in connected_types:
            recommendations.append({
                'action': 'connect_channel',
                'channel_type': channel_type,
                'priority': 'high',
                'description': f"Connect {channel_type.title()} for broader communication reach",
                'estimated_impact': 'high'
            })
    
    # Check for channels needing attention
    for channel in user_channels:
        if channel['needs_action']:
            recommendations.append({
                'action': 'fix_channel',
                'channel_type': channel['type'],
                'priority': 'medium',
                'description': f"Fix {channel['name']} connection issues",
                'details': f"Account status: {channel['status']}",
                'estimated_impact': 'medium'
            })
    
    return recommendations


def _calculate_user_readiness_score(user_channels: List[Dict[str, Any]], 
                                  utilization: Dict[str, Any]) -> float:
    """Calculate overall communication readiness score for user"""
    score = 0.0
    max_score = 10.0
    
    # Active channels score (40% of total)
    active_channels = utilization['active_channels']
    total_possible_channels = 6  # Approximate number of important channels
    channel_score = min(4.0, (active_channels / total_possible_channels) * 4.0)
    score += channel_score
    
    # High-priority channels bonus (30% of total)
    connected_types = {ch['type'] for ch in user_channels if ch['can_send']}
    high_priority_channels = {'whatsapp', 'linkedin', 'gmail', 'outlook'}
    priority_coverage = len(connected_types & high_priority_channels) / len(high_priority_channels)
    score += priority_coverage * 3.0
    
    # Recent activity bonus (20% of total)
    total_recent_messages = sum(utilization['message_volume_by_channel'].values())
    activity_score = min(2.0, (total_recent_messages / 50) * 2.0)  # Scale based on 50 messages/month
    score += activity_score
    
    # Channel health bonus (10% of total)
    healthy_channels = len([ch for ch in user_channels if ch['can_send'] and not ch['needs_action']])
    if user_channels:
        health_ratio = healthy_channels / len(user_channels)
        score += health_ratio * 1.0
    
    return min(max_score, score)