"""
Signal handlers for participant auto-creation
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

logger = logging.getLogger(__name__)


@receiver(post_save, sender='communications.Participant')
def check_participant_auto_creation(sender, instance, created, **kwargs):
    """
    Check if participant should trigger auto-creation after save
    This runs after participant is created or updated
    """
    # Skip if participant already has a contact
    if instance.contact_record:
        return
    
    # Skip if this is just being created (likely has 0 messages)
    # We'll check again when messages are added
    if created and instance.total_messages == 0:
        return
    
    # Import here to avoid circular imports
    from communications.models import ParticipantSettings
    from communications.services.auto_create_service import AutoCreateContactService
    
    try:
        # Get settings for current tenant
        settings = ParticipantSettings.get_or_create_for_tenant()
        
        # Skip if auto-creation is disabled
        if not settings.auto_create_enabled:
            return
        
        # Skip if batch mode only (not real-time)
        if not settings.enable_real_time_creation:
            logger.debug(f"Skipping real-time creation for participant {instance.id} - batch mode only")
            return
        
        # Check if participant is eligible
        service = AutoCreateContactService()
        should_create, reason = service.should_auto_create(instance)
        
        if should_create:
            logger.info(f"Auto-creating contact for participant {instance.id}: {reason}")
            
            # Use transaction to ensure atomicity
            with transaction.atomic():
                try:
                    record = service.create_contact_from_participant(
                        participant=instance,
                        user=None,  # System-created
                        force=False
                    )
                    logger.info(f"Successfully created contact {record.id} for participant {instance.id}")
                except Exception as e:
                    logger.error(f"Failed to auto-create contact for participant {instance.id}: {e}")
        else:
            logger.debug(f"Participant {instance.id} not eligible for auto-creation: {reason}")
            
    except Exception as e:
        logger.error(f"Error checking auto-creation for participant {instance.id}: {e}")


@receiver(post_save, sender='communications.Message')
def check_auto_creation_on_message(sender, instance, created, **kwargs):
    """
    Check if new message should trigger participant auto-creation
    This handles the case where a participant reaches the message threshold
    """
    if not created:
        return
    
    # Import here to avoid circular imports
    from communications.models import ParticipantSettings, ConversationParticipant
    from communications.services.auto_create_service import AutoCreateContactService
    
    try:
        # Get settings
        settings = ParticipantSettings.get_or_create_for_tenant()
        
        # Skip if auto-creation is disabled or not real-time
        if not settings.auto_create_enabled or not settings.enable_real_time_creation:
            return
        
        # Find participants in this conversation
        conversation_participants = ConversationParticipant.objects.filter(
            conversation=instance.conversation,
            is_active=True
        ).select_related('participant')
        
        service = AutoCreateContactService()
        
        for conv_participant in conversation_participants:
            participant = conv_participant.participant
            
            # Skip if already has contact
            if participant.contact_record:
                continue
            
            # Update message count (in case it's not updated yet)
            participant.total_messages = participant.total_messages + 1
            participant.save(update_fields=['total_messages', 'last_seen'])
            
            # Check if now eligible
            should_create, reason = service.should_auto_create(participant)
            
            if should_create:
                logger.info(f"Message {instance.id} triggered auto-creation for participant {participant.id}")
                
                with transaction.atomic():
                    try:
                        record = service.create_contact_from_participant(
                            participant=participant,
                            user=None,
                            force=False
                        )
                        logger.info(f"Created contact {record.id} from message trigger")
                    except Exception as e:
                        logger.error(f"Failed to create contact on message trigger: {e}")
                        
    except Exception as e:
        logger.error(f"Error in message auto-creation check: {e}")


@receiver(post_save, sender='communications.ConversationParticipant')
def check_auto_creation_on_conversation_join(sender, instance, created, **kwargs):
    """
    Check auto-creation when participant joins a conversation
    This helps catch participants who might already have messages
    """
    if not created or not instance.is_active:
        return
    
    # Import here to avoid circular imports
    from communications.models import ParticipantSettings
    from communications.services.auto_create_service import AutoCreateContactService
    
    try:
        settings = ParticipantSettings.get_or_create_for_tenant()
        
        if not settings.auto_create_enabled or not settings.enable_real_time_creation:
            return
        
        participant = instance.participant
        
        # Skip if already has contact
        if participant.contact_record:
            return
        
        # Check eligibility
        service = AutoCreateContactService()
        should_create, reason = service.should_auto_create(participant)
        
        if should_create:
            logger.info(f"Conversation join triggered auto-creation for participant {participant.id}")
            
            with transaction.atomic():
                try:
                    record = service.create_contact_from_participant(
                        participant=participant,
                        user=None,
                        force=False
                    )
                    logger.info(f"Created contact {record.id} from conversation join")
                except Exception as e:
                    logger.error(f"Failed to create contact on conversation join: {e}")
                    
    except Exception as e:
        logger.error(f"Error in conversation join auto-creation check: {e}")