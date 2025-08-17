"""
API views for message draft management
Handles draft saving, auto-save, and recovery functionality
"""
from django.utils import timezone
from django.db import transaction
from rest_framework import status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from ..models_drafts import MessageDraft, DraftAutoSaveSettings


class MessageDraftSerializer(serializers.ModelSerializer):
    """Serializer for message drafts"""
    attachments_count = serializers.SerializerMethodField()
    content_preview = serializers.SerializerMethodField()
    is_stale = serializers.SerializerMethodField()
    
    class Meta:
        model = MessageDraft
        fields = [
            'id', 'subject', 'content', 'recipient', 'account_connection_id',
            'conversation_id', 'recipient_type', 'draft_name', 'auto_saved',
            'attachments_data', 'attachments_count', 'content_preview',
            'is_stale', 'created_at', 'updated_at', 'last_auto_save'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_auto_save']
    
    def get_attachments_count(self, obj):
        return obj.get_attachments_count()
    
    def get_content_preview(self, obj):
        return obj.get_content_preview()
    
    def get_is_stale(self, obj):
        return obj.is_stale()


class DraftAutoSaveSettingsSerializer(serializers.ModelSerializer):
    """Serializer for draft auto-save settings"""
    
    class Meta:
        model = DraftAutoSaveSettings
        fields = [
            'auto_save_enabled', 'auto_save_interval', 'max_auto_saves',
            'auto_delete_after_days', 'show_draft_recovery_prompt',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class MessageDraftViewSet(ModelViewSet):
    """ViewSet for managing message drafts"""
    serializer_class = MessageDraftSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter drafts to current user only"""
        return MessageDraft.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Set the user when creating a draft"""
        serializer.save(user=self.request.user)
    
    def perform_update(self, serializer):
        """Update timestamps when modifying a draft"""
        serializer.save(user=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auto_save_draft(request):
    """
    Auto-save a draft message
    Creates or updates an auto-save draft
    """
    try:
        data = request.data
        user = request.user
        
        # Validate required fields
        if not data.get('content', '').strip():
            return Response(
                {'error': 'Content is required for auto-save'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create unique auto-save identifier
        conversation_id = data.get('conversation_id', '')
        account_connection_id = data.get('account_connection_id', '')
        recipient = data.get('recipient', '')
        
        # Find existing auto-save draft for this context
        auto_save_filter = {
            'user': user,
            'auto_saved': True,
            'conversation_id': conversation_id,
            'account_connection_id': account_connection_id,
        }
        
        # If it's a new message, also match by recipient
        if not conversation_id:
            auto_save_filter['recipient'] = recipient
        
        with transaction.atomic():
            # Try to find existing auto-save
            existing_draft = MessageDraft.objects.filter(**auto_save_filter).first()
            
            if existing_draft:
                # Update existing auto-save
                existing_draft.subject = data.get('subject', '')
                existing_draft.content = data.get('content', '')
                existing_draft.recipient = recipient
                existing_draft.attachments_data = data.get('attachments', [])
                existing_draft.recipient_type = data.get('recipient_type', 'new')
                existing_draft.save()
                
                draft = existing_draft
            else:
                # Create new auto-save
                draft = MessageDraft.objects.create(
                    user=user,
                    subject=data.get('subject', ''),
                    content=data.get('content', ''),
                    recipient=recipient,
                    account_connection_id=account_connection_id,
                    conversation_id=conversation_id,
                    recipient_type=data.get('recipient_type', 'new'),
                    attachments_data=data.get('attachments', []),
                    auto_saved=True
                )
            
            # Clean up old auto-saves
            settings = DraftAutoSaveSettings.get_or_create_for_user(user)
            _cleanup_old_auto_saves(user, settings.max_auto_saves, conversation_id, account_connection_id)
        
        return Response({
            'success': True,
            'draft_id': str(draft.id),
            'message': 'Draft auto-saved successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': 'Failed to auto-save draft', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_manual_draft(request):
    """
    Manually save a draft with a custom name
    """
    try:
        data = request.data
        user = request.user
        
        # Validate required fields
        if not data.get('content', '').strip():
            return Response(
                {'error': 'Content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        draft_name = data.get('draft_name', '').strip()
        if not draft_name:
            return Response(
                {'error': 'Draft name is required for manual save'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create manual draft
        draft = MessageDraft.objects.create(
            user=user,
            subject=data.get('subject', ''),
            content=data.get('content', ''),
            recipient=data.get('recipient', ''),
            account_connection_id=data.get('account_connection_id', ''),
            conversation_id=data.get('conversation_id', ''),
            recipient_type=data.get('recipient_type', 'new'),
            attachments_data=data.get('attachments', []),
            draft_name=draft_name,
            auto_saved=False
        )
        
        return Response({
            'success': True,
            'draft_id': str(draft.id),
            'message': f'Draft "{draft_name}" saved successfully'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': 'Failed to save draft', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_draft_for_context(request):
    """
    Get the most recent draft for a specific context
    Used for draft recovery when opening message composer
    """
    conversation_id = request.query_params.get('conversation_id', '')
    account_connection_id = request.query_params.get('account_connection_id', '')
    recipient = request.query_params.get('recipient', '')
    
    # Build filter for context
    filter_kwargs = {
        'user': request.user,
        'conversation_id': conversation_id,
        'account_connection_id': account_connection_id,
    }
    
    # For new messages, also filter by recipient
    if not conversation_id:
        filter_kwargs['recipient'] = recipient
    
    # Get the most recent draft for this context
    draft = MessageDraft.objects.filter(**filter_kwargs).first()
    
    if draft:
        serializer = MessageDraftSerializer(draft)
        return Response({
            'has_draft': True,
            'draft': serializer.data
        })
    else:
        return Response({
            'has_draft': False,
            'draft': None
        })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_draft(request, draft_id):
    """Delete a specific draft"""
    try:
        draft = MessageDraft.objects.get(id=draft_id, user=request.user)
        draft.delete()
        
        return Response({
            'success': True,
            'message': 'Draft deleted successfully'
        })
        
    except MessageDraft.DoesNotExist:
        return Response(
            {'error': 'Draft not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': 'Failed to delete draft', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cleanup_stale_drafts(request):
    """Clean up old auto-save drafts"""
    try:
        user = request.user
        settings = DraftAutoSaveSettings.get_or_create_for_user(user)
        
        # Delete stale auto-saves
        stale_threshold = timezone.now() - timezone.timedelta(days=settings.auto_delete_after_days)
        deleted_count = MessageDraft.objects.filter(
            user=user,
            auto_saved=True,
            last_auto_save__lt=stale_threshold
        ).delete()[0]
        
        return Response({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Cleaned up {deleted_count} stale drafts'
        })
        
    except Exception as e:
        return Response(
            {'error': 'Failed to cleanup drafts', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class DraftSettingsView(APIView):
    """Manage user's draft auto-save settings"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current user's draft settings"""
        settings = DraftAutoSaveSettings.get_or_create_for_user(request.user)
        serializer = DraftAutoSaveSettingsSerializer(settings)
        return Response(serializer.data)
    
    def patch(self, request):
        """Update user's draft settings"""
        settings = DraftAutoSaveSettings.get_or_create_for_user(request.user)
        serializer = DraftAutoSaveSettingsSerializer(settings, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def _cleanup_old_auto_saves(user, max_auto_saves, conversation_id, account_connection_id):
    """Helper function to clean up old auto-saves"""
    # Get auto-saves for this context, ordered by newest first
    auto_saves = MessageDraft.objects.filter(
        user=user,
        auto_saved=True,
        conversation_id=conversation_id,
        account_connection_id=account_connection_id
    ).order_by('-updated_at')
    
    # Delete excess auto-saves
    if auto_saves.count() > max_auto_saves:
        excess_drafts = auto_saves[max_auto_saves:]
        for draft in excess_drafts:
            draft.delete()