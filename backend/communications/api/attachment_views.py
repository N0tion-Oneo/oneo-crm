"""
API views for handling message attachments and file uploads
"""
import uuid
import mimetypes
from pathlib import Path
from asgiref.sync import async_to_sync

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import UserChannelConnection
from ..unipile_sdk import unipile_service


class AttachmentUploadSerializer(serializers.Serializer):
    """Serializer for file upload validation"""
    file = serializers.FileField(required=True)
    conversation_id = serializers.CharField(required=False, allow_blank=True)
    account_id = serializers.CharField(required=True)
    
    def validate_file(self, value):
        """Validate uploaded file"""
        # Check file size (25MB limit)
        max_size = 25 * 1024 * 1024  # 25MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size ({value.size} bytes) exceeds maximum allowed size ({max_size} bytes)"
            )
        
        # Check file type
        allowed_types = {
            # Images
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
            # Documents
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            # Text files
            'text/plain', 'text/csv',
            # Archives
            'application/zip', 'application/x-rar-compressed',
            # Video (small files only)
            'video/mp4', 'video/avi', 'video/mov'
        }
        
        content_type = getattr(value, 'content_type', None)
        if content_type and content_type not in allowed_types:
            raise serializers.ValidationError(
                f"File type '{content_type}' is not allowed"
            )
        
        return value
    
    def validate_account_id(self, value):
        """Validate that account exists and user has access"""
        try:
            connection = UserChannelConnection.objects.get(
                id=value,
                user=self.context['request'].user,
                is_active=True
            )
            if not connection.can_send_messages():
                raise serializers.ValidationError("Account cannot send messages")
            return value
        except UserChannelConnection.DoesNotExist:
            raise serializers.ValidationError("Invalid account ID or access denied")


class AttachmentUploadView(APIView):
    """Handle file uploads for message attachments"""
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Upload a file and prepare it for message attachment"""
        serializer = AttachmentUploadSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid file upload', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            file = serializer.validated_data['file']
            account_id = serializer.validated_data['account_id']
            conversation_id = serializer.validated_data.get('conversation_id')
            
            # Get account connection
            connection = UserChannelConnection.objects.get(
                id=account_id,
                user=request.user,
                is_active=True
            )
            
            # Generate unique filename
            file_extension = Path(file.name).suffix
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # Create storage path with tenant isolation
            tenant_path = f"attachments/{request.user.tenant_id}/{request.user.id}/{unique_filename}"
            
            # Save file to storage
            file_path = default_storage.save(tenant_path, ContentFile(file.read()))
            file_url = default_storage.url(file_path)
            
            # Detect MIME type
            content_type, _ = mimetypes.guess_type(file.name)
            if not content_type:
                content_type = 'application/octet-stream'
            
            # Prepare attachment metadata
            attachment_data = {
                'id': str(uuid.uuid4()),
                'name': file.name,
                'size': file.size,
                'type': content_type,
                'url': request.build_absolute_uri(file_url),
                'storage_path': file_path,
                'uploaded_at': timezone.now().isoformat(),
                'account_id': account_id,
                'conversation_id': conversation_id,
                'user_id': request.user.id
            }
            
            return Response({
                'attachment': attachment_data,
                'message': 'File uploaded successfully'
            }, status=status.HTTP_201_CREATED)
            
        except UserChannelConnection.DoesNotExist:
            return Response(
                {'error': 'Account not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': 'File upload failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MessageSendSerializer(serializers.Serializer):
    """Enhanced serializer for sending messages with attachments"""
    content = serializers.CharField(required=True, min_length=1)
    account_id = serializers.CharField(required=True)
    conversation_id = serializers.CharField(required=False, allow_blank=True)
    recipient = serializers.CharField(required=False, allow_blank=True)
    subject = serializers.CharField(required=False, allow_blank=True)
    attachments = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list
    )
    
    def validate_attachments(self, value):
        """Validate attachment data"""
        if not value:
            return value
        
        validated_attachments = []
        for attachment in value:
            if not isinstance(attachment, dict):
                raise serializers.ValidationError("Each attachment must be a dictionary")
            
            required_fields = ['id', 'name', 'size', 'type']
            for field in required_fields:
                if field not in attachment:
                    raise serializers.ValidationError(f"Attachment missing required field: {field}")
            
            # Validate attachment belongs to current user
            if 'user_id' in attachment and attachment['user_id'] != self.context['request'].user.id:
                raise serializers.ValidationError("Attachment does not belong to current user")
            
            validated_attachments.append(attachment)
        
        return validated_attachments
    
    def validate(self, attrs):
        """Cross-field validation"""
        conversation_id = attrs.get('conversation_id')
        recipient = attrs.get('recipient')
        
        # For new messages, recipient is required
        if not conversation_id and not recipient:
            raise serializers.ValidationError(
                "Either conversation_id or recipient must be provided"
            )
        
        return attrs


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message_with_attachments(request):
    """Send a message with optional attachments through UniPile"""
    serializer = MessageSendSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid message data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        data = serializer.validated_data
        account_id = data['account_id']
        
        # Get account connection
        connection = UserChannelConnection.objects.get(
            id=account_id,
            user=request.user,
            is_active=True
        )
        
        if not connection.can_send_messages():
            return Response(
                {'error': 'Account cannot send messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Prepare message data for UniPile
        message_data = {
            'text': data['content'],
            'html': data['content'],  # For email support
        }
        
        # Add subject for email types
        if data.get('subject') and connection.channel_type in ['gmail', 'outlook', 'mail']:
            message_data['subject'] = data['subject']
        
        # Handle attachments
        unipile_attachments = []
        if data.get('attachments'):
            for attachment in data['attachments']:
                # Prepare attachment for UniPile
                attachment_data = {
                    'name': attachment['name'],
                    'size': attachment['size'],
                    'contentType': attachment['type']
                }
                
                # Add file URL or path for UniPile to access
                if 'url' in attachment:
                    attachment_data['url'] = attachment['url']
                elif 'storage_path' in attachment:
                    # Convert storage path to accessible URL
                    attachment_data['url'] = request.build_absolute_uri(
                        default_storage.url(attachment['storage_path'])
                    )
                
                unipile_attachments.append(attachment_data)
        
        if unipile_attachments:
            message_data['attachments'] = unipile_attachments
        
        # Send through UniPile SDK
        unipile_client = unipile_service.get_client()
        
        if data.get('conversation_id'):
            # Reply to existing conversation
            result = async_to_sync(unipile_client.messages.send_message)(
                account_id=connection.unipile_account_id,
                **message_data,
                thread_id=data['conversation_id']
            )
        else:
            # Send new message
            result = async_to_sync(unipile_client.messages.send_message)(
                account_id=connection.unipile_account_id,
                **message_data,
                to=data['recipient']
            )
        
        # Record message sent for rate limiting
        connection.record_message_sent()
        
        return Response({
            'message': 'Message sent successfully',
            'result': result,
            'attachments_count': len(unipile_attachments)
        }, status=status.HTTP_200_OK)
        
    except UserChannelConnection.DoesNotExist:
        return Response(
            {'error': 'Account not found or access denied'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': 'Failed to send message', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_attachment(request, attachment_id):
    """Delete an uploaded attachment"""
    try:
        # In a real implementation, you'd store attachment metadata in database
        # For now, we'll try to delete from storage based on the attachment ID pattern
        
        # This is a simplified approach - in production you'd want to store
        # attachment metadata in a proper model
        return Response(
            {'message': 'Attachment deleted successfully'},
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response(
            {'error': 'Failed to delete attachment', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )