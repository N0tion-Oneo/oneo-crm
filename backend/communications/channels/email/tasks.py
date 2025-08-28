"""
Background tasks for email processing
"""
import logging
from celery import shared_task
from django_tenants.utils import schema_context
from asgiref.sync import async_to_sync
from datetime import datetime, timedelta

from communications.models import (
    UserChannelConnection, Conversation, Message, Channel,
    Participant, ConversationParticipant
)

logger = logging.getLogger(__name__)


@shared_task
def auto_store_pending_emails(tenant_schema_name=None, account_id=None):
    """
    Background task to automatically store emails that match CRM contacts
    This runs periodically to find and store pending conversations
    """
    try:
        from tenants.models import Tenant
        from communications.channels.email.inbox_views import fetch_email_inbox
        from communications.services import ParticipantResolutionService
        from communications.unipile.clients.email import UnipileEmailClient
        from communications.unipile_sdk import unipile_service
        
        # Get tenant
        if tenant_schema_name:
            tenant = Tenant.objects.filter(schema_name=tenant_schema_name).first()
        else:
            # Process all tenants
            tenants = Tenant.objects.exclude(schema_name='public')
            for tenant in tenants:
                auto_store_pending_emails.delay(tenant.schema_name)
            return f"Triggered storage for {tenants.count()} tenants"
        
        if not tenant:
            logger.error(f"Tenant {tenant_schema_name} not found")
            return
        
        stored_count = 0
        
        with schema_context(tenant.schema_name):
            # Get all email connections for this tenant
            if account_id:
                connections = UserChannelConnection.objects.filter(
                    unipile_account_id=account_id,
                    channel_type__in=['gmail', 'outlook', 'mail', 'email'],
                    auth_status='authenticated'
                )
            else:
                connections = UserChannelConnection.objects.filter(
                    channel_type__in=['gmail', 'outlook', 'mail', 'email'],
                    auth_status='authenticated'
                )
            
            for connection in connections:
                logger.info(f"Processing pending emails for {connection.account_name}")
                
                # Fetch inbox to find pending threads
                conversations = async_to_sync(fetch_email_inbox)(
                    connection=connection,
                    tenant=tenant,
                    limit=50,  # Process up to 50 at a time
                    offset=0,
                    search=''
                )
                
                # Find threads that should be stored but aren't
                pending_threads = [
                    conv for conv in conversations
                    if conv.get('should_store') and not conv.get('stored')
                ]
                
                if not pending_threads:
                    logger.info(f"No pending threads for {connection.account_name}")
                    continue
                
                logger.info(f"Found {len(pending_threads)} pending threads to store for {connection.account_name}")
                
                # Get or create channel (handle duplicates)
                channel = Channel.objects.filter(
                    unipile_account_id=connection.unipile_account_id
                ).first()
                
                if not channel:
                    channel = Channel.objects.create(
                        unipile_account_id=connection.unipile_account_id,
                        name=connection.account_name,
                        channel_type=connection.channel_type,
                        is_active=True
                    )
                
                # Initialize UniPile client
                client = unipile_service.get_client()
                email_client = UnipileEmailClient(client)
                resolution_service = ParticipantResolutionService(tenant)
                
                # Fetch all emails once to avoid multiple API calls
                logger.info(f"Fetching all emails for {connection.account_name} to extract thread messages")
                all_emails_result = async_to_sync(email_client.get_emails)(
                    account_id=connection.unipile_account_id,
                    folder='INBOX',
                    limit=200  # Get more emails to cover all threads
                )
                
                all_emails = []
                if all_emails_result and 'items' in all_emails_result:
                    all_emails = all_emails_result.get('items', [])
                    logger.info(f"Fetched {len(all_emails)} emails total")
                else:
                    logger.warning(f"Could not fetch emails for message extraction")
                
                # Store each pending thread
                for thread_data in pending_threads:
                    try:
                        thread_id = thread_data['id']
                        
                        # Check if already stored (race condition prevention)
                        if Conversation.objects.filter(
                            external_thread_id=thread_id,
                            channel=channel
                        ).exists():
                            continue
                        
                        # Create a conversation with basic thread info
                        conversation = Conversation.objects.create(
                            channel=channel,
                            external_thread_id=thread_id,
                            subject=thread_data.get('subject', '(no subject)'),
                            metadata={
                                'folder': 'INBOX',
                                'stored_from': 'auto_background',
                                'storage_reason': thread_data.get('storage_reason', 'contact_match'),
                                'message_count': thread_data.get('message_count', 0),
                                'auto_stored_at': datetime.now().isoformat(),
                                'last_message_at': thread_data.get('last_message_at'),
                                'participants': thread_data.get('participants', [])
                            }
                        )
                        
                        # Get messages for this thread from pre-fetched emails
                        try:
                            # Filter messages belonging to this thread from pre-fetched emails
                            thread_messages = [
                                msg for msg in all_emails
                                if msg.get('thread_id') == thread_id
                            ]
                            
                            if thread_messages:
                                # Store real messages
                                for msg_data in thread_messages:
                                    Message.objects.create(
                                        conversation=conversation,
                                        channel=channel,
                                        external_message_id=msg_data.get('id'),
                                        content=msg_data.get('body', '') or msg_data.get('body_plain', ''),
                                        subject=msg_data.get('subject', ''),
                                        contact_email=msg_data.get('from_attendee', {}).get('identifier', ''),
                                        sent_at=msg_data.get('date'),
                                        direction='inbound' if msg_data.get('from_attendee', {}).get('identifier') != connection.account_name else 'outbound',
                                        metadata={
                                            'sender_name': msg_data.get('from_attendee', {}).get('display_name', ''),
                                            'to_attendees': msg_data.get('to_attendees', []),
                                            'cc_attendees': msg_data.get('cc_attendees', []),
                                            'bcc_attendees': msg_data.get('bcc_attendees', []),
                                            'attachments': msg_data.get('attachments', []),
                                            'labels': msg_data.get('labels', [])
                                        }
                                    )
                                logger.info(f"Stored {len(thread_messages)} real messages for thread {thread_id}")
                            else:
                                logger.warning(f"No messages found for thread {thread_id} in pre-fetched emails")
                                # Create a minimal message so the conversation isn't empty
                                participants = thread_data.get('participants', [])
                                sender_email = participants[0].get('email', '') if participants else ''
                                sender_name = participants[0].get('name', '') if participants else ''
                                
                                Message.objects.create(
                                    conversation=conversation,
                                    channel=channel,
                                    external_message_id=f"{thread_id}_minimal",
                                    content='(Message content not available)',
                                    contact_email=sender_email,
                                    sent_at=thread_data.get('last_message_at'),
                                    direction='inbound',
                                    metadata={'sender_name': sender_name}
                                )
                                
                        except Exception as e:
                            logger.error(f"Error fetching messages for thread {thread_id}: {e}")
                            # Continue without messages rather than fail the whole thread
                        
                        # Link participants from the thread data
                        for participant_data in thread_data.get('participants', []):
                            email = participant_data.get('email')
                            if email:
                                participant, _ = async_to_sync(resolution_service.resolve_or_create_participant)(
                                    {'email': email, 'name': participant_data.get('name')},
                                    'email'
                                )
                                
                                ConversationParticipant.objects.get_or_create(
                                    conversation=conversation,
                                    participant=participant
                                )
                        
                        stored_count += 1
                        logger.info(f"Auto-stored thread {thread_id}: {thread_data.get('subject', 'No subject')}")
                        
                        # Broadcast storage status update via WebSocket
                        from channels.layers import get_channel_layer
                        channel_layer = get_channel_layer()
                        
                        # Broadcast to user's email channel
                        try:
                            async_to_sync(channel_layer.group_send)(
                                f"user_{connection.user.id}_email",
                                {
                                    "type": "email_thread_stored",
                                    "thread_id": thread_id,
                                    "stored": True,
                                    "subject": thread_data.get('subject', 'No subject'),
                                    "conversation_id": str(conversation.id)
                                }
                            )
                            logger.info(f"Broadcast storage update for thread {thread_id} to user_{connection.user.id}_email")
                        except Exception as e:
                            logger.error(f"Failed to broadcast storage update: {e}")
                        
                    except Exception as e:
                        logger.error(f"Failed to store thread {thread_data.get('id')}: {e}")
                        continue
        
        logger.info(f"Auto-stored {stored_count} pending email threads for tenant {tenant_schema_name}")
        return f"Stored {stored_count} threads"
        
    except Exception as e:
        logger.error(f"Error in auto_store_pending_emails: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error: {str(e)}"


@shared_task
def check_and_store_new_matches(tenant_schema_name):
    """
    Periodically check for new contact matches and store their conversations
    This handles cases where a contact is created after emails were received
    """
    try:
        from tenants.models import Tenant
        
        tenant = Tenant.objects.filter(schema_name=tenant_schema_name).first()
        if not tenant:
            return
        
        with schema_context(tenant.schema_name):
            # Check recent emails that aren't stored yet
            # This would look for emails from the last week that now match contacts
            # but weren't stored initially
            
            # For now, just trigger the regular auto-store
            auto_store_pending_emails.delay(tenant_schema_name)
            
        return "Check complete"
        
    except Exception as e:
        logger.error(f"Error checking new matches: {e}")
        return f"Error: {str(e)}"