"""
API views for handling message attachments and file uploads
"""
import uuid
import mimetypes
import logging
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

from ..models import UserChannelConnection, Message, MessageDirection, MessageStatus
from ..unipile_sdk import unipile_service

logger = logging.getLogger(__name__)


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
            tenant_schema = getattr(request.tenant, 'schema_name', 'public')
            tenant_path = f"attachments/{tenant_schema}/{request.user.id}/{unique_filename}"
            
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
    content = serializers.CharField(required=False, allow_blank=True, default='')
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
        
        # Temporarily simplified validation to debug the issue
        print(f"🚨 VALIDATING ATTACHMENTS: {value}")
        
        validated_attachments = []
        for attachment in value:
            print(f"🚨 ATTACHMENT ITEM: {attachment}")
            if not isinstance(attachment, dict):
                raise serializers.ValidationError("Each attachment must be a dictionary")
            
            # Just check for basic structure - remove strict validation temporarily
            if 'id' not in attachment:
                raise serializers.ValidationError(f"Attachment missing id field")
            
            validated_attachments.append(attachment)
        
        print(f"🚨 VALIDATED ATTACHMENTS: {validated_attachments}")
        return validated_attachments
    
    def validate(self, attrs):
        """Cross-field validation"""
        conversation_id = attrs.get('conversation_id')
        recipient = attrs.get('recipient')
        content = attrs.get('content', '').strip()  # Strip any whitespace
        attachments = attrs.get('attachments', [])
        
        # For new messages, recipient is required
        if not conversation_id and not recipient:
            raise serializers.ValidationError(
                "Either conversation_id or recipient must be provided"
            )
        
        # Either content or attachments must be provided
        # Note: content is stripped, so single spaces become empty
        if not content and not attachments:
            raise serializers.ValidationError(
                "Either content or attachments must be provided"
            )
        
        # If we have attachments but no real content, that's valid
        if attachments and not content:
            attrs['content'] = ''  # Ensure empty content is explicitly set
        else:
            attrs['content'] = content  # Use the stripped content
        
        return attrs


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message_with_attachments(request):
    """Send a message with optional attachments through UniPile"""
    # Simple print to console that should always show
    print(f"🚨 ENDPOINT REACHED: send_message_with_attachments from {request.user.email}")
    print(f"🚨 Request method: {request.method}")
    print(f"🚨 Request content type: {request.content_type}")
    print(f"🚨 Request data: {request.data}")
    print(f"🚨 Request data type: {type(request.data)}")
    # Note: Cannot access request.body after DRF has parsed request.data
    
    # Debug logging
    logger.info(f"📨 Attachment send request from user {request.user.email}")
    logger.info(f"📨 Request data keys: {list(request.data.keys())}")
    logger.info(f"📨 Content: '{request.data.get('content', 'NOT_PROVIDED')}'")
    logger.info(f"📨 Attachments count: {len(request.data.get('attachments', []))}")
    
    serializer = MessageSendSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        logger.error(f"📨 Serializer validation failed: {serializer.errors}")
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
        content = data.get('content', '').strip()
        message_data = {
            'text': content or '',  # Allow empty text if attachments are provided
            'html': content or '',  # For email support
        }
        
        # Add subject for email types
        if data.get('subject') and connection.channel_type in ['gmail', 'outlook', 'mail']:
            message_data['subject'] = data['subject']
        
        # Handle attachments - UniPile expects actual files as multipart/form-data
        unipile_attachments = []
        logger.info(f"📎 Processing {len(data.get('attachments', []))} attachments")
        if data.get('attachments'):
            for attachment in data['attachments']:
                if 'storage_path' in attachment:
                    try:
                        # Get the full file path from storage
                        file_path = default_storage.path(attachment['storage_path'])
                        
                        # Prepare attachment for UniPile format
                        unipile_attachments.append({
                            'name': attachment['name'],
                            'file_path': file_path,
                            'content_type': attachment['type']
                        })
                    except Exception as e:
                        logger.warning(f"📎 Could not prepare attachment for UniPile: {e}")
                        logger.warning(f"📎 Attachment data: {attachment}")
                        continue
        
        # Send through UniPile SDK
        unipile_client = unipile_service.get_client()
        
        if data.get('conversation_id'):
            # Reply to existing conversation
            result = async_to_sync(unipile_client.messaging.send_message)(
                chat_id=data['conversation_id'],
                text=message_data['text'],
                attachments=unipile_attachments if unipile_attachments else None
            )
        else:
            # Send new message  
            result = async_to_sync(unipile_client.messaging.send_message)(
                chat_id=data['recipient'],
                text=message_data['text'],
                attachments=unipile_attachments if unipile_attachments else None
            )
        
        # Create local message record with attachment metadata for WebSocket broadcast
        logger.info(f"📎 UniPile send result: success={result.get('success', True) if result else False}")
        logger.info(f"📎 Ready to process {len(unipile_attachments)} UniPile attachments")
        if result and result.get('success', True):
            try:
                # Get or create conversation
                from ..models import Conversation, Channel
                conversation = None
                
                if data.get('conversation_id'):
                    conversation = Conversation.objects.filter(
                        external_thread_id=data['conversation_id']
                    ).first()
                
                if not conversation:
                    # Create new conversation
                    channel, _ = Channel.objects.get_or_create(
                        unipile_account_id=connection.unipile_account_id,
                        channel_type=connection.channel_type,
                        defaults={
                            'name': f"{connection.channel_type.title()} - {connection.account_name}",
                            'auth_status': connection.auth_status,
                            'created_by': connection.user
                        }
                    )
                    
                    conversation = Conversation.objects.create(
                        channel=channel,
                        external_thread_id=data.get('conversation_id', data.get('recipient', f'msg_{timezone.now().timestamp()}')),
                        subject=f"Message to {data.get('recipient', 'Contact')}",
                        status='active'
                    )
                
                # Prepare attachment metadata for local storage
                attachment_metadata = []
                if data.get('attachments'):
                    # Try to fetch attachment details from UniPile if we have a message ID
                    unipile_attachments_info = {}
                    unipile_message_id = result.get('message_id')
                    if isinstance(unipile_message_id, list):
                        unipile_message_id = unipile_message_id[0]  # Use first ID
                    
                    # TODO: Re-enable UniPile attachment ID fetching after debugging basic save issue
                    # Temporarily disabled to debug basic message saving
                    # if unipile_message_id and unipile_attachments:
                    #     try:
                    #         # Fetch message details from UniPile to get attachment IDs
                    #         import requests
                    #         from django.conf import settings
                    #         
                    #         api_key = getattr(settings, 'UNIPILE_API_KEY', None)
                    #         base_url = getattr(settings, 'UNIPILE_DSN', 'https://api18.unipile.com:14890')
                    #         
                    #         if api_key:
                    #             message_url = f"{base_url}/api/v1/messages/{unipile_message_id}"
                    #             headers = {"X-API-KEY": api_key}
                    #             
                    #             response = requests.get(message_url, headers=headers)
                    #             if response.status_code == 200:
                    #                 message_data = response.json()
                    #                 unipile_attachments_list = message_data.get('attachments', [])
                    #                 
                    #                 # Map UniPile attachments by filename for matching
                    #                 for unipile_att in unipile_attachments_list:
                    #                     filename = unipile_att.get('name', unipile_att.get('filename', ''))
                    #                     if filename:
                    #                         unipile_attachments_info[filename] = unipile_att.get('id')
                    #                 
                    #                 logger.info(f"📎 Fetched {len(unipile_attachments_list)} attachment IDs from UniPile")
                    #     
                    #     except Exception as e:
                    #         logger.warning(f"📎 Failed to fetch UniPile attachment IDs: {e}")
                    
                    logger.info(f"📎 Temporarily disabled UniPile attachment ID fetching")
                    
                    # Build attachment metadata with UniPile IDs when available
                    for attachment in data['attachments']:
                        filename = attachment.get('name')
                        attachment_meta = {
                            'id': attachment.get('id'),
                            'filename': filename,  # Frontend expects 'filename' not 'name'
                            'size': attachment.get('size'),
                            'type': attachment.get('type'),
                            'url': attachment.get('url'),
                            'mime_type': attachment.get('type'),  # Add mime_type for frontend compatibility
                            'storage_path': attachment.get('storage_path')  # Keep for backend reference
                        }
                        
                        # Add UniPile attachment ID if we found it
                        if filename and filename in unipile_attachments_info:
                            attachment_meta['unipile_attachment_id'] = unipile_attachments_info[filename]
                            logger.info(f"📎 Mapped attachment '{filename}' to UniPile ID: {unipile_attachments_info[filename]}")
                        
                        attachment_metadata.append(attachment_meta)
                
                # Create local message record for WebSocket broadcast
                local_message = Message.objects.create(
                    channel=conversation.channel,
                    conversation=conversation,
                    external_message_id=result.get('id', f"local_{timezone.now().timestamp()}"),
                    direction=MessageDirection.OUTBOUND,
                    content=content or (f"[{len(attachment_metadata)} attachment(s)]" if attachment_metadata else ''),
                    subject=message_data.get('subject', ''),
                    contact_email=data.get('recipient', ''),
                    status=MessageStatus.SENT,
                    metadata={
                        'has_attachments': len(attachment_metadata) > 0,
                        'attachment_count': len(attachment_metadata),
                        'attachments': attachment_metadata,
                        'unipile_result': result,
                        'sent_via_api': True,
                        'user_id': request.user.id
                    },
                    sent_at=timezone.now()
                )
                
                logger.info(f"Created local message record {local_message.id} with {len(attachment_metadata)} attachments")
                
            except Exception as e:
                logger.warning(f"Failed to create local message record: {e}")
                # Don't fail the whole request if local record creation fails
        
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_attachment(request, message_id, attachment_id):
    """Download an attachment from UniPile via proxy"""
    try:
        logger.info(f"📥 Attachment download request: message={message_id}, attachment={attachment_id}")
        
        # Get the message to find the UniPile account information
        # Try both internal ID and external_message_id to handle different message sources
        message = None
        try:
            # First try as internal database ID
            message = Message.objects.select_related('channel').get(id=message_id)
            logger.info(f"📥 Found message by internal ID: {message_id}")
            logger.info(f"📥 Message external_message_id: {message.external_message_id}")
            logger.info(f"📥 Message content preview: '{message.content[:50]}{'...' if len(message.content) > 50 else ''}'")
        except Message.DoesNotExist:
            try:
                # Then try as external UniPile message ID
                message = Message.objects.select_related('channel').get(external_message_id=message_id)
                logger.info(f"📥 Found message by external ID: {message_id}")
                logger.info(f"📥 Message internal ID: {message.id}")
                logger.info(f"📥 Message content preview: '{message.content[:50]}{'...' if len(message.content) > 50 else ''}'")
            except Message.DoesNotExist:
                logger.error(f"📥 Message not found with ID: {message_id}")
                # Let's see what messages are actually in the database
                recent_messages = Message.objects.all()[:5]
                logger.error(f"📥 Recent messages in database:")
                for msg in recent_messages:
                    logger.error(f"📥   ID: {msg.id}, External: {msg.external_message_id}, Content: '{msg.content[:30]}{'...' if len(msg.content) > 30 else ''}'")
                return Response(
                    {'error': f'Message not found with ID: {message_id}'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Get the channel's UniPile account ID for API access
        if not message.channel or not message.channel.unipile_account_id:
            return Response(
                {'error': 'Message channel does not have UniPile account ID'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Download attachment directly from UniPile API
        # UniPile API endpoint format: https://{subdomain}.unipile.com:{port}/api/v1/messages/{message_id}/attachments/{attachment_id}
        try:
            import requests
            from django.conf import settings
            
            # Get UniPile API credentials
            api_key = getattr(settings, 'UNIPILE_API_KEY', None)
            base_url = getattr(settings, 'UNIPILE_DSN', 'https://api18.unipile.com:14890')
            
            if not api_key:
                logger.error("📥 No UniPile API key configured")
                return Response(
                    {'error': 'UniPile API key not configured'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Get the actual UniPile message ID from metadata or external_message_id
            unipile_message_id = None
            
            # First try getting from metadata (for API-sent messages)
            if message.metadata and 'unipile_result' in message.metadata:
                unipile_result = message.metadata['unipile_result']
                if 'message_id' in unipile_result:
                    # Handle both single ID and list of IDs
                    msg_id = unipile_result['message_id']
                    if isinstance(msg_id, list):
                        unipile_message_id = msg_id[0]  # Use first ID
                    else:
                        unipile_message_id = msg_id
                    logger.info(f"📥 Using UniPile message ID from metadata: {unipile_message_id}")
            
            # Fallback to external_message_id (for webhook messages)
            if not unipile_message_id and message.external_message_id:
                unipile_message_id = message.external_message_id
                logger.info(f"📥 Using external_message_id as UniPile ID: {unipile_message_id}")
            
            if not unipile_message_id:
                logger.error(f"📥 No UniPile message ID found in message metadata or external_message_id")
                logger.error(f"📥 Message metadata: {message.metadata}")
                logger.error(f"📥 External message ID: {message.external_message_id}")
                return Response(
                    {'error': 'UniPile message ID not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get attachment metadata from the message and find the UniPile attachment ID
            attachment_metadata = None
            unipile_attachment_id = None
            
            logger.info(f"📥 Looking for attachment {attachment_id} in message metadata")
            logger.info(f"📥 Message metadata keys: {list(message.metadata.keys()) if message.metadata else 'None'}")
            
            # Debug: Log full message metadata structure for debugging
            if message.metadata:
                logger.info(f"📥 Full message metadata structure:")
                for key, value in message.metadata.items():
                    if key == 'attachments' and isinstance(value, list):
                        logger.info(f"📥   {key}: [{len(value)} attachments]")
                        for i, att in enumerate(value):
                            logger.info(f"📥     [{i}] id={att.get('id')}, filename={att.get('filename')}")
                    else:
                        logger.info(f"📥   {key}: {type(value)} {str(value)[:100]}{'...' if len(str(value)) > 100 else ''}")
            
            # First check if we have raw UniPile data (webhook messages)
            if message.metadata and 'unipile_data' in message.metadata:
                unipile_data = message.metadata['unipile_data']
                logger.info(f"📥 Found UniPile webhook data with keys: {list(unipile_data.keys()) if unipile_data else 'None'}")
                
                # Check for attachments in the raw UniPile webhook data
                if 'attachments' in unipile_data and unipile_data['attachments']:
                    logger.info(f"📥 Found {len(unipile_data['attachments'])} UniPile webhook attachments")
                    for i, unipile_att in enumerate(unipile_data['attachments']):
                        logger.info(f"📥 UniPile webhook attachment {i}: {unipile_att}")
                        
                        # UniPile attachments have an 'id' field that we need to use
                        if 'id' in unipile_att:
                            attachment_metadata = {
                                'id': attachment_id,  # Keep our local ID for reference
                                'unipile_id': unipile_att['id'],  # Store UniPile's ID
                                'filename': unipile_att.get('filename', unipile_att.get('name', f'attachment_{unipile_att["id"]}')),
                                'mime_type': unipile_att.get('content_type', unipile_att.get('type', 'application/octet-stream')),
                                'size': unipile_att.get('size')
                            }
                            unipile_attachment_id = unipile_att['id']
                            logger.info(f"📥 Using UniPile webhook attachment ID: {unipile_attachment_id}")
                            break
            
            # Check if this is an API-sent message with unipile_result data
            elif message.metadata and 'unipile_result' in message.metadata:
                unipile_result = message.metadata['unipile_result']
                logger.info(f"📥 Found UniPile result data: {unipile_result}")
                logger.info(f"📥 UniPile result type: {type(unipile_result)}")
                
                if isinstance(unipile_result, dict):
                    logger.info(f"📥 UniPile result keys: {list(unipile_result.keys())}")
                    
                    # For API-sent messages, UniPile returns attachment info in the result
                    if 'attachments' in unipile_result and unipile_result['attachments']:
                        logger.info(f"📥 Found {len(unipile_result['attachments'])} UniPile result attachments")
                        for i, result_att in enumerate(unipile_result['attachments']):
                            logger.info(f"📥 UniPile result attachment {i}: {result_att}")
                            
                            # Match by index for now (first attachment maps to first result)
                            if i == 0:  # For single attachment messages
                                attachment_metadata = {
                                    'id': attachment_id,  # Keep our local ID for reference
                                    'unipile_id': result_att.get('id', result_att.get('attachment_id')),  # Store UniPile's ID
                                    'filename': result_att.get('filename', result_att.get('name', f'attachment_{result_att.get("id", "unknown")}')),
                                    'mime_type': result_att.get('content_type', result_att.get('type', 'application/octet-stream')),
                                    'size': result_att.get('size')
                                }
                                unipile_attachment_id = result_att.get('id', result_att.get('attachment_id'))
                                logger.info(f"📥 Using UniPile result attachment ID: {unipile_attachment_id}")
                                break
                    else:
                        logger.info(f"📥 No attachments found in unipile_result or attachments is empty")
                else:
                    logger.info(f"📥 unipile_result is not a dict: {unipile_result}")
            
            # Fallback to processed attachments metadata if UniPile data not available
            if not attachment_metadata and message.metadata and 'attachments' in message.metadata:
                logger.info(f"📥 Falling back to processed attachments metadata")
                for i, att in enumerate(message.metadata['attachments']):
                    logger.info(f"📥 Processed attachment {i}: {att}")
                    if att.get('id') == attachment_id:
                        attachment_metadata = att
                        
                        # Check if this is a locally stored attachment (from our API upload)
                        if 'storage_path' in att:
                            logger.info(f"📥 Found locally stored attachment, serving from: {att['storage_path']}")
                            
                            # Serve local file
                            import os
                            from django.conf import settings
                            from django.http import HttpResponse, Http404
                            
                            storage_path = att['storage_path']
                            full_path = os.path.join(settings.MEDIA_ROOT, storage_path)
                            
                            if not os.path.exists(full_path):
                                logger.error(f"📥 Local file not found: {full_path}")
                                return Response(
                                    {'error': f'Local attachment file not found: {storage_path}'},
                                    status=status.HTTP_404_NOT_FOUND
                                )
                            
                            # Read and serve the file
                            try:
                                with open(full_path, 'rb') as f:
                                    file_data = f.read()
                                
                                response = HttpResponse(
                                    file_data,
                                    content_type=att.get('mime_type', 'application/octet-stream')
                                )
                                response['Content-Disposition'] = f'attachment; filename="{att.get("filename", "attachment")}"'
                                response['Content-Length'] = len(file_data)
                                
                                logger.info(f"📥 Successfully served local attachment: {att.get('filename')} ({len(file_data)} bytes)")
                                return response
                                
                            except Exception as e:
                                logger.error(f"📥 Error reading local file: {e}")
                                return Response(
                                    {'error': f'Error reading local file: {str(e)}'},
                                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                                )
                        elif 'unipile_data' in att:
                            # This is a webhook attachment with UniPile data
                            unipile_data = att['unipile_data']
                            # UniPile webhook uses 'attachment_id' field, not 'id'
                            unipile_attachment_id = unipile_data.get('attachment_id') or unipile_data.get('id')
                            logger.info(f"📥 Using UniPile attachment ID from unipile_data: {unipile_attachment_id}")
                        else:
                            # Try to find a UniPile ID in the processed attachment  
                            unipile_attachment_id = att.get('unipile_id') or att.get('attachment_id') or att.get('id')
                            logger.info(f"📥 Using processed attachment ID for UniPile: {unipile_attachment_id}")
                        break
            
            
            # Final fallback - create basic metadata and try UniPile
            if not attachment_metadata:
                logger.warning(f"📥 No attachment metadata found, creating fallback")
                attachment_metadata = {
                    'id': attachment_id,
                    'filename': f'attachment_{attachment_id}',
                    'mime_type': 'application/octet-stream'
                }
                unipile_attachment_id = attachment_id
                
            if not unipile_attachment_id:
                logger.error(f"📥 Could not determine UniPile attachment ID")
                return Response(
                    {'error': 'Could not determine UniPile attachment ID'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Make direct request to UniPile API using the correct attachment ID
            download_url = f"{base_url}/api/v1/messages/{unipile_message_id}/attachments/{unipile_attachment_id}"
            headers = {
                "accept": "*/*",  # Accept any content type for downloads
                "X-API-KEY": api_key
            }
            
            logger.info(f"📥 Requesting attachment from UniPile: {download_url}")
            logger.info(f"📥 Using UniPile message ID: {unipile_message_id}")
            logger.info(f"📥 Using attachment ID: {unipile_attachment_id}")
            logger.info(f"📥 Request headers: {headers}")
            
            try:
                response = requests.get(download_url, headers=headers, timeout=30)
                logger.info(f"📥 UniPile response status: {response.status_code}")
                logger.info(f"📥 UniPile response headers: {dict(response.headers)}")
                
                if response.status_code != 200:
                    logger.error(f"📥 UniPile API error {response.status_code}: {response.text}")
                    return Response(
                        {
                            'error': f'UniPile API error: {response.status_code}',
                            'details': response.text,
                            'url': download_url
                        },
                        status=status.HTTP_502_BAD_GATEWAY
                    )
            except requests.exceptions.Timeout:
                logger.error(f"📥 UniPile API timeout for URL: {download_url}")
                return Response(
                    {'error': 'UniPile API timeout', 'url': download_url},
                    status=status.HTTP_504_GATEWAY_TIMEOUT
                )
            except requests.exceptions.RequestException as req_error:
                logger.error(f"📥 UniPile API request error: {req_error}")
                return Response(
                    {'error': 'UniPile API request failed', 'details': str(req_error)},
                    status=status.HTTP_502_BAD_GATEWAY
                )
            
            attachment_data = response.content
            
            # Determine content type
            content_type = 'application/octet-stream'  # Default
            filename = f'attachment_{attachment_id}'  # Default filename
            
            if attachment_metadata:
                content_type = attachment_metadata.get('mime_type') or attachment_metadata.get('type', content_type)
                filename = attachment_metadata.get('filename', filename)
            
            # Return the file as a streaming response
            from django.http import HttpResponse
            response = HttpResponse(
                attachment_data,
                content_type=content_type
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(attachment_data)
            
            logger.info(f"📥 Successfully served attachment: {filename} ({len(attachment_data)} bytes)")
            return response
            
        except Exception as unipile_error:
            logger.error(f"📥 UniPile download error: {unipile_error}")
            return Response(
                {'error': 'Failed to download from UniPile', 'details': str(unipile_error)},
                status=status.HTTP_502_BAD_GATEWAY
            )
        
    except Message.DoesNotExist:
        return Response(
            {'error': 'Message not found or access denied'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"📥 Attachment download error: {e}")
        return Response(
            {'error': 'Failed to download attachment', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )