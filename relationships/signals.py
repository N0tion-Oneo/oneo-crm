"""
Relationship signals for automatic relationship management
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Relationship, RelationshipPath
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Relationship)
def handle_relationship_created(sender, instance, created, **kwargs):
    """Handle relationship creation and updates"""
    if created:
        logger.info(f"New relationship created: {instance}")
        
        # Create reverse relationship if bidirectional
        if instance.relationship_type.is_bidirectional:
            reverse_rel = instance.create_reverse_relationship()
            if reverse_rel:
                logger.info(f"Created reverse relationship: {reverse_rel}")
        
        # Invalidate related path caches
        _invalidate_path_caches(instance)


@receiver(post_delete, sender=Relationship)
def handle_relationship_deleted(sender, instance, **kwargs):
    """Handle relationship deletion"""
    logger.info(f"Relationship deleted: {instance}")
    
    # Invalidate related path caches
    _invalidate_path_caches(instance)


def _invalidate_path_caches(relationship):
    """Invalidate cached paths that might be affected by relationship changes"""
    try:
        # Find and mark expired all paths that might involve this relationship
        affected_paths = RelationshipPath.objects.filter(
            path_relationships__contains=[relationship.id]
        )
        
        if affected_paths.exists():
            # Mark them as expired by setting expires_at to now
            affected_paths.update(expires_at=timezone.now())
            logger.info(f"Invalidated {affected_paths.count()} cached paths")
            
    except Exception as e:
        logger.error(f"Error invalidating path caches: {e}")


# Cleanup expired paths periodically (this could be moved to a management command)
def cleanup_expired_paths():
    """Clean up expired relationship paths"""
    try:
        expired_count = RelationshipPath.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()[0]
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired relationship paths")
            
    except Exception as e:
        logger.error(f"Error cleaning up expired paths: {e}")