"""
Celery tasks for participant auto-creation and batch processing
"""
import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django_tenants.utils import schema_context
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(name='communications.process_participant_auto_creation')
def process_participant_auto_creation(schema_name=None, batch_size=None):
    """
    Process batch of participants for auto-creation
    Runs periodically to check for eligible participants
    """
    if not schema_name:
        logger.error("No schema_name provided for auto-creation task")
        return {'error': 'schema_name required'}
        
    try:
        with schema_context(schema_name):
            from communications.services.auto_create_service import AutoCreateContactService
            from communications.models import ParticipantSettings
            
            # Get settings
            settings = ParticipantSettings.get_or_create_for_tenant()
            
            if not settings.auto_create_enabled:
                logger.info(f"Auto-creation is disabled for tenant {schema_name}")
                return {'status': 'disabled'}
            
            # Create service
            service = AutoCreateContactService()
            
            # Process batch
            results = service.process_batch(batch_size=batch_size)
            
            logger.info(f"Auto-creation batch completed for {schema_name}: {results}")
            return results
            
    except Exception as e:
        logger.error(f"Error in auto-creation batch for {schema_name}: {e}")
        return {'error': str(e)}


@shared_task(name='communications.sync_participant_company_links')
def sync_participant_company_links(schema_name=None):
    """
    Sync company links for participants based on email domains
    """
    if not schema_name:
        logger.error("No schema_name provided for company linking task")
        return {'error': 'schema_name required'}
        
    try:
        with schema_context(schema_name):
            from communications.services.auto_create_service import AutoCreateContactService
            from communications.models import Participant, ParticipantSettings
            
            settings = ParticipantSettings.get_or_create_for_tenant()
            
            if not settings.auto_link_by_domain:
                logger.info(f"Domain-based company linking is disabled for {schema_name}")
                return {'status': 'disabled'}
            
            service = AutoCreateContactService()
            
            # Find participants with email but no secondary record
            participants = Participant.objects.filter(
                email__isnull=False,
                secondary_record__isnull=True
            ).exclude(email='')[:100]  # Process in batches
            
            linked_count = 0
            for participant in participants:
                try:
                    service.link_to_company(participant)
                    if participant.secondary_record:
                        linked_count += 1
                except Exception as e:
                    logger.error(f"Failed to link participant {participant.id}: {e}")
            
            logger.info(f"Company linking completed for {schema_name}: {linked_count} participants linked")
            return {
                'linked': linked_count,
                'processed': participants.count()
            }
            
    except Exception as e:
        logger.error(f"Error in company linking for {schema_name}: {e}")
        return {'error': str(e)}


@shared_task(name='communications.cleanup_expired_blacklist')
def cleanup_expired_blacklist(schema_name=None):
    """
    Clean up expired blacklist entries
    """
    if not schema_name:
        logger.error("No schema_name provided for blacklist cleanup")
        return {'error': 'schema_name required'}
        
    try:
        with schema_context(schema_name):
            from communications.models import ParticipantBlacklist
            
            expired = ParticipantBlacklist.objects.filter(
                expires_at__isnull=False,
                expires_at__lt=timezone.now(),
                is_active=True
            )
            
            count = expired.count()
            expired.update(is_active=False)
            
            logger.info(f"Deactivated {count} expired blacklist entries for {schema_name}")
            return {'deactivated': count}
            
    except Exception as e:
        logger.error(f"Error cleaning up blacklist for {schema_name}: {e}")
        return {'error': str(e)}


@shared_task(name='communications.check_participant_duplicates')
def check_participant_duplicates(schema_name, participant_id):
    """
    Check for duplicate records for a specific participant
    """
    if not schema_name:
        logger.error("No schema_name provided for duplicate check")
        return {'error': 'schema_name required'}
        
    try:
        with schema_context(schema_name):
            from communications.models import Participant, ParticipantSettings
            from communications.services.auto_create_service import AutoCreateContactService
            
            participant = Participant.objects.get(id=participant_id)
            settings = ParticipantSettings.get_or_create_for_tenant()
            
            if not settings.check_duplicates_before_create:
                return {'status': 'disabled'}
            
            service = AutoCreateContactService()
            duplicate = service.check_for_duplicates(participant)
            
            if duplicate:
                # Link to existing record
                participant.contact_record = duplicate
                participant.resolution_confidence = settings.duplicate_confidence_threshold
                participant.resolution_method = 'duplicate_found'
                participant.resolved_at = timezone.now()
                participant.save()
                
                logger.info(f"Found and linked duplicate record {duplicate.id} for participant {participant_id} in {schema_name}")
                return {
                    'duplicate_found': True,
                    'record_id': str(duplicate.id)
                }
            
            return {'duplicate_found': False}
            
    except Participant.DoesNotExist:
        logger.error(f"Participant {participant_id} not found in {schema_name}")
        return {'error': 'Participant not found'}
    except Exception as e:
        logger.error(f"Error checking duplicates in {schema_name}: {e}")
        return {'error': str(e)}


@shared_task(name='communications.retroactive_auto_creation')
def retroactive_auto_creation(schema_name, start_date=None, end_date=None):
    """
    Retroactively process participants for auto-creation
    Useful when enabling auto-creation for existing data
    """
    if not schema_name:
        logger.error("No schema_name provided for retroactive processing")
        return {'error': 'schema_name required'}
        
    try:
        with schema_context(schema_name):
            from communications.models import Participant
            from communications.services.auto_create_service import AutoCreateContactService
            
            # Build query
            queryset = Participant.objects.filter(
                contact_record__isnull=True
            )
            
            if start_date:
                queryset = queryset.filter(first_seen__gte=start_date)
            if end_date:
                queryset = queryset.filter(first_seen__lte=end_date)
            
            service = AutoCreateContactService()
            
            created = 0
            skipped = 0
            errors = 0
            
            for participant in queryset.iterator():
                try:
                    should_create, reason = service.should_auto_create(participant)
                    if should_create:
                        service.create_contact_from_participant(participant)
                        created += 1
                    else:
                        logger.debug(f"Skipping {participant.id}: {reason}")
                        skipped += 1
                except Exception as e:
                    logger.error(f"Error processing participant {participant.id}: {e}")
                    errors += 1
            
            logger.info(f"Retroactive processing complete for {schema_name}: created={created}, skipped={skipped}, errors={errors}")
            return {
                'created': created,
                'skipped': skipped,
                'errors': errors
            }
            
    except Exception as e:
        logger.error(f"Error in retroactive processing for {schema_name}: {e}")
        return {'error': str(e)}


@shared_task(name='communications.update_participant_stats')
def update_participant_stats(schema_name=None):
    """
    Update participant statistics (message counts, last activity, etc.)
    """
    if not schema_name:
        logger.error("No schema_name provided for stats update")
        return {'error': 'schema_name required'}
        
    try:
        with schema_context(schema_name):
            from communications.models import Participant, ConversationParticipant
            from django.db.models import Count, Max
            
            # Update participants with conversation stats
            participants = Participant.objects.annotate(
                conv_count=Count('conversation_participations'),
                last_conv=Max('conversation_participations__joined_at')
            ).filter(conv_count__gt=0)
            
            updated = 0
            for participant in participants:
                participant.total_messages = participant.conv_count
                participant.last_seen = participant.last_conv or participant.last_seen
                participant.save(update_fields=['total_messages', 'last_seen'])
                updated += 1
            
            logger.info(f"Updated stats for {updated} participants in {schema_name}")
            return {'updated': updated}
            
    except Exception as e:
        logger.error(f"Error updating participant stats in {schema_name}: {e}")
        return {'error': str(e)}


@shared_task(name='communications.process_all_tenants_auto_creation')
def process_all_tenants_auto_creation():
    """
    Process auto-creation for all active tenants
    """
    try:
        from tenants.models import Tenant
        
        results = {}
        active_tenants = Tenant.objects.filter(is_active=True)
        
        for tenant in active_tenants:
            try:
                result = process_participant_auto_creation.delay(
                    schema_name=tenant.schema_name
                )
                results[tenant.schema_name] = 'scheduled'
            except Exception as e:
                logger.error(f"Failed to schedule auto-creation for {tenant.schema_name}: {e}")
                results[tenant.schema_name] = f'error: {str(e)}'
        
        return results
        
    except Exception as e:
        logger.error(f"Error processing all tenants: {e}")
        return {'error': str(e)}