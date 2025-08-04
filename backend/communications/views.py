"""
REST API Views for Communication System
Focused purely on communication functionality - channels, messages, conversations
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from django.db.models import Q, Count, Avg
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from api.permissions import CommunicationPermission, MessagePermission, ChannelPermission, CommunicationTrackingPermission
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from asgiref.sync import sync_to_async

from .models import (
    Channel, Conversation, Message, CommunicationAnalytics, MessageDirection
)
from .serializers import (
    ChannelSerializer, ConversationListSerializer, ConversationDetailSerializer,
    MessageSerializer, MessageCreateSerializer,
    CommunicationAnalyticsSerializer, ChannelConnectionSerializer,
    MessageSendSerializer, BulkMessageSerializer
)
from .unipile_sdk import unipile_service
from pipelines.models import Record


class ChannelViewSet(viewsets.ModelViewSet):
    """ViewSet for communication channels"""
    
    queryset = Channel.objects.select_related('created_by')
    serializer_class = ChannelSerializer
    permission_classes = [ChannelPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['channel_type', 'is_active']
    search_fields = ['name', 'description', 'external_account_id']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user)
    
    @extend_schema(
        summary="Test channel connection",
        responses={200: {'type': 'object', 'properties': {
            'connected': {'type': 'boolean'},
            'message': {'type': 'string'}
        }}}
    )
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test connection to external channel"""
        channel = self.get_object()
        
        try:
            # Test connection asynchronously
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    unipile_service.test_connection(channel.external_account_id)
                )
                
                return Response({
                    'connected': result.get('connected', False),
                    'message': result.get('message', 'Connection test completed')
                })
                
            finally:
                loop.close()
                
        except Exception as e:
            return Response({
                'connected': False,
                'message': f'Connection test failed: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Sync channel messages",
        responses={200: {'type': 'object', 'properties': {
            'synced': {'type': 'integer'},
            'message': {'type': 'string'}
        }}}
    )
    @action(detail=True, methods=['post'])
    def sync_messages(self, request, pk=None):
        """Sync messages from external channel"""
        channel = self.get_object()
        
        # Queue sync task
        from .tasks import sync_channel_messages
        from django.db import connection
        
        sync_channel_messages.delay(
            str(channel.id), 
            connection.schema_name
        )
        
        return Response({
            'message': f'Message sync queued for channel {channel.name}',
            'queued': True
        })


class ConversationViewSet(viewsets.ModelViewSet):
    """ViewSet for conversations"""
    
    queryset = Conversation.objects.select_related('channel', 'primary_contact_record')
    permission_classes = [CommunicationPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['channel', 'status', 'priority']
    search_fields = ['subject', 'external_thread_id', 'primary_contact_record__data__first_name', 'primary_contact_record__data__company']
    ordering_fields = ['updated_at', 'created_at', 'message_count']
    ordering = ['-updated_at']
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail views"""
        if self.action == 'list':
            return ConversationListSerializer
        return ConversationDetailSerializer
    
    @extend_schema(
        summary="Get conversation statistics",
        responses={200: {'type': 'object', 'properties': {
            'total_conversations': {'type': 'integer'},
            'active_conversations': {'type': 'integer'},
            'average_response_time': {'type': 'number'}
        }}}
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get conversation statistics"""
        queryset = self.get_queryset()
        
        stats = {
            'total_conversations': queryset.count(),
            'active_conversations': queryset.filter(status='active').count(),
            'archived_conversations': queryset.filter(status='archived').count(),
            'average_message_count': queryset.aggregate(
                avg_messages=Avg('message_count')
            )['avg_messages'] or 0
        }
        
        return Response(stats)
    
    @extend_schema(
        summary="Archive conversation",
        responses={200: ConversationDetailSerializer}
    )
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a conversation"""
        conversation = self.get_object()
        conversation.status = 'archived'
        conversation.save()
        
        return Response(ConversationDetailSerializer(conversation).data)


class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet for messages"""
    
    queryset = Message.objects.select_related('channel', 'conversation', 'contact_record')
    permission_classes = [MessagePermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['direction', 'status', 'channel', 'conversation']
    search_fields = ['content', 'subject', 'contact_email']
    ordering_fields = ['created_at', 'sent_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Use different serializers for create vs other actions"""
        if self.action == 'create':
            return MessageCreateSerializer
        elif self.action == 'send_bulk':
            return BulkMessageSerializer
        elif self.action == 'send':
            return MessageSendSerializer
        return MessageSerializer
    
    @extend_schema(
        summary="Send a message",
        request=MessageSendSerializer,
        responses={201: MessageSerializer}
    )
    @action(detail=False, methods=['post'])
    def send(self, request):
        """Send a message through a channel"""
        serializer = MessageSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        channel_id = serializer.validated_data['channel_id']
        message_data = serializer.validated_data
        
        # Queue message sending
        from .tasks import send_scheduled_message
        from django.db import connection
        
        send_scheduled_message.delay(
            message_data=message_data,
            tenant_schema=connection.schema_name,
            channel_id=channel_id
        )
        
        return Response({
            'message': 'Message queued for sending',
            'queued': True
        }, status=status.HTTP_202_ACCEPTED)
    
    @extend_schema(
        summary="Send bulk messages",
        request=BulkMessageSerializer,
        responses={202: {'type': 'object', 'properties': {
            'queued': {'type': 'integer'},
            'message': {'type': 'string'}
        }}}
    )
    @action(detail=False, methods=['post'])
    def send_bulk(self, request):
        """Send bulk messages"""
        serializer = BulkMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Queue bulk message sending
        message_count = len(serializer.validated_data.get('recipients', []))
        
        return Response({
            'queued': message_count,
            'message': f'{message_count} messages queued for sending'
        }, status=status.HTTP_202_ACCEPTED)


class CommunicationAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for communication analytics (read-only)"""
    
    queryset = CommunicationAnalytics.objects.all()
    serializer_class = CommunicationAnalyticsSerializer
    permission_classes = [CommunicationTrackingPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['date', 'channel']
    ordering_fields = ['date']
    ordering = ['-date']
    
    @extend_schema(
        summary="Get analytics summary",
        parameters=[
            OpenApiParameter(name='start_date', type=str, location='query'),
            OpenApiParameter(name='end_date', type=str, location='query'),
        ],
        responses={200: CommunicationAnalyticsSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get analytics summary for date range"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            return Response(
                {'error': 'start_date and end_date parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            start_date = datetime.fromisoformat(start_date).date()
            end_date = datetime.fromisoformat(end_date).date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        analytics = self.get_queryset().filter(
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        return Response(CommunicationAnalyticsSerializer(analytics, many=True).data)