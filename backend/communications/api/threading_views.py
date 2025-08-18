"""
Conversation Threading API Views
Manages cross-channel conversation threading and grouping
"""
import logging
from typing import Dict, Any
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from api.permissions import CommunicationPermission
from communications.services.conversation_threading import conversation_threading_service
from pipelines.models import Record

logger = logging.getLogger(__name__)


@extend_schema(
    summary="Create unified conversation thread for a Record",
    description="Analyzes and creates unified conversation threads across all channels for a specific Record",
    parameters=[
        OpenApiParameter(name='record_id', type=int, location=OpenApiParameter.PATH, description='Record ID'),
        OpenApiParameter(name='force_rethread', type=bool, default=False, description='Force re-threading of existing conversations'),
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean'},
                'record_id': {'type': 'integer'},
                'threads_created': {'type': 'integer'},
                'messages_threaded': {'type': 'integer'},
                'conversations_updated': {'type': 'integer'},
                'threading_strategies_used': {'type': 'array'},
                'thread_metadata': {'type': 'object'},
                'analysis': {'type': 'object'}
            }
        }
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, CommunicationPermission])
def create_record_conversation_thread(request, record_id):
    """Create unified conversation thread for a Record"""
    try:
        # Validate Record exists and user has access
        try:
            record = Record.objects.get(id=record_id, is_deleted=False)
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get force_rethread parameter
        force_rethread = request.data.get('force_rethread', False)
        if isinstance(force_rethread, str):
            force_rethread = force_rethread.lower() in ('true', '1', 'yes')
        
        # Create unified conversation thread
        result = conversation_threading_service.create_unified_conversation_thread(
            record=record,
            force_rethread=force_rethread
        )
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': result.get('error', 'Threading failed')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    except Exception as e:
        logger.error(f"Error creating conversation thread for record {record_id}: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Analyze threading opportunities for a Record",
    description="Analyzes potential conversation threading opportunities without creating threads",
    parameters=[
        OpenApiParameter(name='record_id', type=int, location=OpenApiParameter.PATH, description='Record ID'),
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'record_id': {'type': 'integer'},
                'total_conversations': {'type': 'integer'},
                'total_messages': {'type': 'integer'},
                'channels_involved': {'type': 'array'},
                'time_span': {'type': 'object'},
                'threading_signals': {'type': 'object'},
                'potential_threads': {'type': 'array'},
                'recommendations': {'type': 'object'}
            }
        }
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, CommunicationPermission])
def analyze_record_threading_opportunities(request, record_id):
    """Analyze threading opportunities for a Record without creating threads"""
    try:
        # Validate Record exists and user has access
        try:
            record = Record.objects.get(id=record_id, is_deleted=False)
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get conversations and messages for analysis
        conversations = conversation_threading_service._get_record_conversations(record)
        messages = conversation_threading_service._get_record_messages(record)
        
        # Perform threading analysis
        analysis = conversation_threading_service._analyze_threading_opportunities(
            record, conversations, messages
        )
        
        # Add recommendations based on analysis
        recommendations = _generate_threading_recommendations(analysis)
        analysis['recommendations'] = recommendations
        
        return Response(analysis, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error analyzing threading opportunities for record {record_id}: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Get conversation threads for a Record",
    description="Retrieves existing conversation threads for a Record",
    parameters=[
        OpenApiParameter(name='record_id', type=int, location=OpenApiParameter.PATH, description='Record ID'),
        OpenApiParameter(name='include_analysis', type=bool, default=False, description='Include threading analysis'),
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'record_id': {'type': 'integer'},
                'threads': {'type': 'array'},
                'total_threads': {'type': 'integer'},
                'last_updated': {'type': 'string'},
                'analysis': {'type': 'object'}
            }
        }
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, CommunicationPermission])
def get_record_conversation_threads(request, record_id):
    """Get existing conversation threads for a Record"""
    try:
        # Validate Record exists and user has access
        try:
            record = Record.objects.get(id=record_id, is_deleted=False)
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        include_analysis = request.GET.get('include_analysis', 'false').lower() == 'true'
        
        # Get conversations with threading metadata
        conversations = conversation_threading_service._get_record_conversations(record)
        
        # Extract thread information from conversation metadata
        threads = {}
        for conversation in conversations:
            if conversation.metadata and 'thread_group_id' in conversation.metadata:
                thread_id = conversation.metadata['thread_group_id']
                if thread_id not in threads:
                    threads[thread_id] = {
                        'id': thread_id,
                        'type': conversation.metadata.get('thread_type', 'unknown'),
                        'strategy': conversation.metadata.get('threading_strategy', 'unknown'),
                        'conversations': [],
                        'messages': [],
                        'channels': set(),
                        'last_updated': conversation.metadata.get('thread_updated_at')
                    }
                
                threads[thread_id]['conversations'].append({
                    'id': str(conversation.id),
                    'channel_type': conversation.channel.channel_type if conversation.channel else None,
                    'status': conversation.status,
                    'created_at': conversation.created_at,
                    'updated_at': conversation.updated_at
                })
                
                if conversation.channel:
                    threads[thread_id]['channels'].add(conversation.channel.channel_type)
        
        # Convert threads to list and clean up
        thread_list = []
        for thread_data in threads.values():
            thread_data['channels'] = list(thread_data['channels'])
            thread_data['conversation_count'] = len(thread_data['conversations'])
            thread_list.append(thread_data)
        
        response_data = {
            'record_id': record_id,
            'threads': thread_list,
            'total_threads': len(thread_list),
            'last_updated': max(
                (thread['last_updated'] for thread in thread_list if thread['last_updated']),
                default=None
            )
        }
        
        # Add analysis if requested
        if include_analysis:
            messages = conversation_threading_service._get_record_messages(record)
            analysis = conversation_threading_service._analyze_threading_opportunities(
                record, conversations, messages
            )
            response_data['analysis'] = analysis
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting conversation threads for record {record_id}: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Bulk create conversation threads",
    description="Create conversation threads for multiple Records in bulk",
    request={
        'type': 'object',
        'properties': {
            'record_ids': {'type': 'array', 'items': {'type': 'integer'}},
            'force_rethread': {'type': 'boolean', 'default': False},
            'threading_strategies': {'type': 'array', 'items': {'type': 'string'}}
        },
        'required': ['record_ids']
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean'},
                'total_records': {'type': 'integer'},
                'successful_threads': {'type': 'integer'},
                'failed_threads': {'type': 'integer'},
                'results': {'type': 'array'},
                'summary': {'type': 'object'}
            }
        }
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, CommunicationPermission])
def bulk_create_conversation_threads(request):
    """Create conversation threads for multiple Records in bulk"""
    try:
        record_ids = request.data.get('record_ids', [])
        force_rethread = request.data.get('force_rethread', False)
        
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
        
        # Process each record
        results = []
        successful_threads = 0
        failed_threads = 0
        total_messages_threaded = 0
        
        for record in records:
            try:
                result = conversation_threading_service.create_unified_conversation_thread(
                    record=record,
                    force_rethread=force_rethread
                )
                
                if result['success']:
                    successful_threads += 1
                    total_messages_threaded += result.get('messages_threaded', 0)
                else:
                    failed_threads += 1
                
                results.append({
                    'record_id': record.id,
                    'success': result['success'],
                    'threads_created': result.get('threads_created', 0),
                    'messages_threaded': result.get('messages_threaded', 0),
                    'error': result.get('error')
                })
                
            except Exception as e:
                failed_threads += 1
                results.append({
                    'record_id': record.id,
                    'success': False,
                    'error': str(e)
                })
                logger.error(f"Error threading record {record.id}: {e}")
        
        summary = {
            'total_records': len(record_ids),
            'successful_threads': successful_threads,
            'failed_threads': failed_threads,
            'total_messages_threaded': total_messages_threaded,
            'success_rate': (successful_threads / len(record_ids)) * 100 if record_ids else 0
        }
        
        return Response({
            'success': True,
            'total_records': len(record_ids),
            'successful_threads': successful_threads,
            'failed_threads': failed_threads,
            'results': results,
            'summary': summary
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in bulk conversation threading: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def _generate_threading_recommendations(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Generate threading recommendations based on analysis"""
    recommendations = {
        'overall_recommendation': 'none',
        'confidence': 0.0,
        'suggested_strategies': [],
        'reasons': [],
        'potential_benefits': []
    }
    
    # Analyze threading signals
    signals = analysis.get('threading_signals', {})
    potential_threads = analysis.get('potential_threads', [])
    
    # Calculate confidence score
    confidence_factors = []
    
    # Email threading potential
    email_signals = signals.get('email_references', {})
    if email_signals.get('threading_potential') == 'high':
        confidence_factors.append(0.3)
        recommendations['suggested_strategies'].append('email_references')
        recommendations['reasons'].append('Strong email reference chains detected')
    
    # Temporal clustering
    temporal_signals = signals.get('temporal_clusters', {})
    if temporal_signals.get('threading_potential') == 'high':
        confidence_factors.append(0.25)
        recommendations['suggested_strategies'].append('temporal_proximity')
        recommendations['reasons'].append('Cross-channel temporal clustering found')
    
    # Subject similarity
    subject_signals = signals.get('subject_patterns', {})
    if subject_signals.get('potential_subject_threads', 0) > 0:
        confidence_factors.append(0.2)
        recommendations['suggested_strategies'].append('subject_similarity')
        recommendations['reasons'].append('Multiple messages with similar subjects')
    
    # Content references
    content_signals = signals.get('content_references', {})
    if content_signals.get('threading_potential') == 'high':
        confidence_factors.append(0.15)
        recommendations['suggested_strategies'].append('content_references')
        recommendations['reasons'].append('Quoted content and message references detected')
    
    # Cross-channel sequences
    sequence_signals = signals.get('cross_channel_sequences', {})
    if sequence_signals.get('threading_potential') == 'high':
        confidence_factors.append(0.1)
        recommendations['reasons'].append('Cross-channel conversation patterns detected')
    
    # Calculate overall confidence
    recommendations['confidence'] = sum(confidence_factors)
    
    # Determine overall recommendation
    if recommendations['confidence'] >= 0.7:
        recommendations['overall_recommendation'] = 'highly_recommended'
        recommendations['potential_benefits'] = [
            'Unified conversation view across channels',
            'Improved conversation context',
            'Better communication tracking',
            'Enhanced relationship intelligence'
        ]
    elif recommendations['confidence'] >= 0.4:
        recommendations['overall_recommendation'] = 'recommended'
        recommendations['potential_benefits'] = [
            'Basic conversation grouping',
            'Improved message organization',
            'Better communication history'
        ]
    elif recommendations['confidence'] >= 0.2:
        recommendations['overall_recommendation'] = 'optional'
        recommendations['potential_benefits'] = [
            'Minimal conversation grouping',
            'Basic message organization'
        ]
    else:
        recommendations['overall_recommendation'] = 'not_recommended'
        recommendations['reasons'].append('Insufficient threading signals detected')
    
    # Always suggest record-based threading as fallback
    if 'same_contact_record' not in recommendations['suggested_strategies']:
        recommendations['suggested_strategies'].append('same_contact_record')
    
    return recommendations