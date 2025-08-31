"""
API endpoints for record-centric communications
"""
import logging
from datetime import datetime, timedelta

from django.db.models import Q, Count, Max, Prefetch
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter

from pipelines.models import Record
from communications.models import (
    Conversation, Message, Participant, UserChannelConnection
)
from rest_framework.permissions import IsAuthenticated

from .models import (
    RecordCommunicationProfile, RecordCommunicationLink, RecordSyncJob,
    RecordAttendeeMapping
)
from .serializers import (
    RecordCommunicationProfileSerializer,
    RecordConversationSerializer,
    RecordMessageSerializer,
    RecordCommunicationLinkSerializer,
    RecordSyncJobSerializer,
    RecordCommunicationStatsSerializer,
    SyncTriggerSerializer,
    QuickReplySerializer,
    RecordAttendeeMappingSerializer
)
from .services import RecordIdentifierExtractor, MessageMapper
from .services.record_sync_orchestrator import RecordSyncOrchestrator

logger = logging.getLogger(__name__)


class RecordCommunicationsViewSet(viewsets.ViewSet):
    """
    ViewSet for record-centric communication management.
    All communications are accessed through the record context.
    """
    
    permission_classes = [IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.identifier_extractor = RecordIdentifierExtractor()
        # Note: RecordSyncOrchestrator is instantiated per request with UniPile client
        self.message_mapper = MessageMapper()
    
    @extend_schema(
        summary="Get communication profile for a record",
        responses={200: RecordCommunicationProfileSerializer}
    )
    @action(detail=True, methods=['get'])
    def profile(self, request, pk=None):
        """Get or create communication profile for a record"""
        try:
            record = Record.objects.get(pk=pk)
            
            # Get or create profile
            profile, created = RecordCommunicationProfile.objects.get_or_create(
                record=record,
                defaults={
                    'pipeline': record.pipeline,
                    'created_by': request.user
                }
            )
            
            # Extract identifiers if newly created or empty
            if created or not profile.communication_identifiers:
                identifiers = self.identifier_extractor.extract_identifiers_from_record(record)
                identifier_fields = self.identifier_extractor.get_identifier_fields(record.pipeline_id)
                
                profile.communication_identifiers = identifiers
                profile.identifier_fields = identifier_fields
                profile.save()
            
            serializer = RecordCommunicationProfileSerializer(profile)
            return Response(serializer.data)
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        summary="Get all conversations for a record with smart loading",
        parameters=[
            OpenApiParameter(name='mode', type=str, default='smart',
                           description='Loading mode: smart (default), all, or single channel'),
            OpenApiParameter(name='channel_type', type=str, required=False,
                           description='Filter by channel type when mode is not smart'),
            OpenApiParameter(name='limit', type=int, default=20),
            OpenApiParameter(name='offset', type=int, default=0),
        ],
        responses={200: RecordConversationSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def conversations(self, request, pk=None):
        """Get conversations with smart loading strategy:
        - WhatsApp/LinkedIn: All conversations (few expected)
        - Email: Last 10 conversations only (many expected)
        """
        try:
            record = Record.objects.get(pk=pk)
            
            # Get query parameters
            mode = request.query_params.get('mode', 'smart')
            channel_type = request.query_params.get('channel_type')
            limit = int(request.query_params.get('limit', 20))
            offset = int(request.query_params.get('offset', 0))
            
            # Get all conversation links for this record
            links = RecordCommunicationLink.objects.filter(
                record=record
            ).select_related('conversation', 'conversation__channel')
            
            # Get unique conversation IDs
            conversation_ids = links.values_list('conversation_id', flat=True).distinct()
            
            if mode == 'smart':
                # Smart loading: All WhatsApp/LinkedIn + last 10 emails
                conversations_query = Conversation.objects.filter(
                    id__in=conversation_ids
                ).select_related('channel')
                
                # Get all WhatsApp and LinkedIn conversations
                social_conversations = conversations_query.filter(
                    channel__channel_type__in=['whatsapp', 'linkedin']
                )
                
                # Get last 10 email conversations (gmail, email, or any email-like channel)
                email_conversations = conversations_query.filter(
                    channel__channel_type__in=['email', 'gmail', 'outlook', 'office365']
                ).order_by('-last_message_at')[:10]
                
                # Combine and order by last message
                from django.db.models import Q
                combined_ids = list(social_conversations.values_list('id', flat=True)) + \
                              list(email_conversations.values_list('id', flat=True))
                
                conversations = Conversation.objects.filter(
                    id__in=combined_ids
                ).select_related('channel').order_by('-last_message_at')
                
                total_count = len(combined_ids)
                
            else:
                # Standard mode with optional channel filter
                conversations_query = Conversation.objects.filter(
                    id__in=conversation_ids
                ).select_related('channel')
                
                if channel_type:
                    conversations_query = conversations_query.filter(
                        channel__channel_type=channel_type
                    )
                
                total_count = conversations_query.count()
                conversations = conversations_query.order_by('-last_message_at')[offset:offset + limit]
            
            serializer = RecordConversationSerializer(conversations, many=True)
            
            # Return with pagination metadata
            return Response({
                'count': total_count,
                'next': offset + limit < total_count if mode != 'smart' else False,
                'previous': offset > 0 if mode != 'smart' else False,
                'results': serializer.data,
                'mode': mode
            })
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        summary="Get messages for a specific conversation",
        parameters=[
            OpenApiParameter(name='conversation_id', type=str, required=True),
            OpenApiParameter(name='limit', type=int, default=30),
            OpenApiParameter(name='offset', type=int, default=0),
        ],
        responses={200: RecordMessageSerializer(many=True)}
    )
    @action(detail=True, methods=['get'], url_path='conversation-messages')
    def conversation_messages(self, request, pk=None):
        """Get messages for a specific conversation with pagination"""
        try:
            record = Record.objects.get(pk=pk)
            conversation_id = request.query_params.get('conversation_id')
            
            if not conversation_id:
                return Response(
                    {'error': 'conversation_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify the conversation is linked to this record
            link_exists = RecordCommunicationLink.objects.filter(
                record=record,
                conversation_id=conversation_id
            ).exists()
            
            if not link_exists:
                return Response(
                    {'error': 'Conversation not found for this record'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get pagination parameters
            limit = int(request.query_params.get('limit', 30))
            offset = int(request.query_params.get('offset', 0))
            
            # Get messages for the conversation (chronological order for reading)
            messages = Message.objects.filter(
                conversation_id=conversation_id
            ).select_related(
                'sender_participant', 'conversation', 'channel'
            ).order_by('created_at')[offset:offset + limit]
            
            # Get total count
            total_count = Message.objects.filter(
                conversation_id=conversation_id
            ).count()
            
            serializer = RecordMessageSerializer(messages, many=True)
            
            return Response({
                'count': total_count,
                'next': offset + limit < total_count,
                'previous': offset > 0,
                'results': serializer.data
            })
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        summary="Get unified timeline of all communications",
        parameters=[
            OpenApiParameter(name='limit', type=int, default=100),
            OpenApiParameter(name='offset', type=int, default=0),
            OpenApiParameter(name='channel_type', type=str, required=False)
        ],
        responses={200: RecordMessageSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        """Get unified timeline of all messages for this record"""
        try:
            record = Record.objects.get(pk=pk)
            
            # Get query parameters
            limit = int(request.query_params.get('limit', 100))
            offset = int(request.query_params.get('offset', 0))
            channel_type = request.query_params.get('channel_type')
            
            # Get all participants linked to this record
            participant_ids = Participant.objects.filter(
                Q(contact_record=record) | Q(secondary_record=record)
            ).values_list('id', flat=True)
            
            # Get all messages involving these participants
            messages = Message.objects.filter(
                Q(sender_participant_id__in=participant_ids) |
                Q(conversation__conversation_participants__participant_id__in=participant_ids)
            ).distinct()
            
            # Filter by channel type if specified
            if channel_type:
                messages = messages.filter(channel__channel_type=channel_type)
            
            # Order by time and apply pagination
            messages = messages.select_related(
                'sender_participant', 'conversation', 'channel'
            ).order_by('-created_at')[offset:offset + limit]
            
            serializer = RecordMessageSerializer(messages, many=True)
            return Response(serializer.data)
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        summary="Get communication statistics for a record",
        responses={200: RecordCommunicationStatsSerializer}
    )
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get communication statistics for this record"""
        try:
            record = Record.objects.get(pk=pk)
            
            # Get profile for basic stats
            profile = RecordCommunicationProfile.objects.filter(
                record=record
            ).first()
            
            if not profile:
                # No communications yet
                return Response({
                    'total_conversations': 0,
                    'total_messages': 0,
                    'total_unread': 0,
                    'last_activity': None,
                    'channels': [],
                    'participants_count': 0
                })
            
            # Get all linked conversations
            links = RecordCommunicationLink.objects.filter(record=record)
            conversation_ids = links.values_list('conversation_id', flat=True).distinct()
            
            # Get channel breakdown
            channel_stats = Conversation.objects.filter(
                id__in=conversation_ids
            ).values('channel__channel_type').annotate(
                count=Count('id'),
                messages=Count('messages')
            )
            
            channel_breakdown = {
                stat['channel__channel_type']: {
                    'conversations': stat['count'],
                    'messages': stat['messages']
                }
                for stat in channel_stats
            }
            
            # Get unique participants
            participants = Participant.objects.filter(
                Q(contact_record=record) | Q(secondary_record=record)
            ).distinct()
            
            # Activity timeline (last 30 days)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            daily_activity = Message.objects.filter(
                conversation_id__in=conversation_ids,
                created_at__gte=thirty_days_ago
            ).extra(
                select={'day': 'date(created_at)'}
            ).values('day').annotate(
                count=Count('id')
            ).order_by('day')
            
            stats = {
                'total_conversations': profile.total_conversations,
                'total_messages': profile.total_messages,
                'total_unread': profile.total_unread,
                'last_activity': profile.last_message_at,
                'channels': list(channel_breakdown.keys()),
                'participants_count': participants.count(),
                'channel_breakdown': channel_breakdown,
                'activity_timeline': list(daily_activity)
            }
            
            serializer = RecordCommunicationStatsSerializer(stats)
            return Response(serializer.data)
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        summary="Trigger sync for a record",
        request=SyncTriggerSerializer,
        responses={200: RecordSyncJobSerializer}
    )
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Trigger communication sync for this record"""
        logger.info(f"Sync requested for record {pk}")
        logger.info(f"Request data: {request.data}")
        try:
            record = Record.objects.get(pk=pk)
            
            # Check if sync is already in progress
            profile, _ = RecordCommunicationProfile.objects.get_or_create(
                record=record,
                defaults={'pipeline': record.pipeline}
            )
            
            if profile.sync_in_progress:
                return Response(
                    {'error': 'Sync already in progress for this record'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if recently synced (unless forced)
            # Handle empty request body
            serializer = SyncTriggerSerializer(data=request.data if request.data else {})
            serializer.is_valid(raise_exception=True)
            
            force = serializer.validated_data.get('force', False)
            if not force and profile.last_full_sync:
                time_since_sync = timezone.now() - profile.last_full_sync
                if time_since_sync.total_seconds() < 3600:  # 1 hour
                    return Response(
                        {'error': 'Record was synced recently. Use force=true to sync again.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Queue sync task
            from communications.record_communications.tasks import sync_record_communications
            from django.db import connection
            
            result = sync_record_communications.delay(
                record_id=record.id,
                tenant_schema=connection.schema_name,
                triggered_by_id=request.user.id,
                trigger_reason='Manual API trigger'
            )
            
            # Create sync job record
            sync_job = RecordSyncJob.objects.create(
                record=record,
                profile=profile,
                job_type='full_history',
                status='pending',
                triggered_by=request.user,
                trigger_reason='Manual API trigger',
                celery_task_id=result.id
            )
            
            serializer = RecordSyncJobSerializer(sync_job)
            return Response(serializer.data)
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in sync endpoint: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Sync failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Get sync status for a record",
        responses={200: RecordSyncJobSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def sync_status(self, request, pk=None):
        """Get sync job history for this record"""
        try:
            record = Record.objects.get(pk=pk)
            
            # Get recent sync jobs
            jobs = RecordSyncJob.objects.filter(
                record=record
            ).order_by('-created_at')[:10]
            
            serializer = RecordSyncJobSerializer(jobs, many=True)
            return Response(serializer.data)
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        summary="Send a quick reply from record context",
        request=QuickReplySerializer,
        responses={200: {'description': 'Message sent successfully'}}
    )
    @action(detail=True, methods=['post'])
    def quick_reply(self, request, pk=None):
        """Send a quick reply to a conversation or start a new one"""
        try:
            record = Record.objects.get(pk=pk)
            
            serializer = QuickReplySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            data = serializer.validated_data
            conversation_id = data.get('conversation_id')
            channel_type = data['channel_type']
            content = data['content']
            
            # TODO: Implement actual message sending via UniPile
            # This would use the appropriate channel client to send the message
            
            return Response({
                'status': 'success',
                'message': 'Message sent successfully'
            })
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        summary="Mark conversations as read",
        responses={200: {'description': 'Marked as read'}}
    )
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark all conversations for this record as read"""
        try:
            record = Record.objects.get(pk=pk)
            
            # Get profile and reset unread count
            profile = RecordCommunicationProfile.objects.filter(
                record=record
            ).first()
            
            if profile:
                profile.total_unread = 0
                profile.save(update_fields=['total_unread'])
            
            # TODO: Mark actual messages as read in the conversation
            
            return Response({
                'status': 'success',
                'message': 'All conversations marked as read'
            })
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )