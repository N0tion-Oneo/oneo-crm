"""
Signal handlers for Content Management System
Automatically track content usage and maintain analytics
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import ContentAsset, ContentUsage, ContentTag

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ContentAsset)
def update_tag_usage_counts(sender, instance, created, **kwargs):
    """Update tag usage counts when assets are created/updated"""
    
    if created:
        # Increment usage count for all tags associated with this asset
        for tag in instance.tags.all():
            tag.usage_count += 1
            tag.save(update_fields=['usage_count'])
        
        logger.debug(f"Updated tag usage counts for new asset: {instance.name}")


@receiver(post_delete, sender=ContentAsset)
def decrement_tag_usage_counts(sender, instance, **kwargs):
    """Decrement tag usage counts when assets are deleted"""
    
    for tag in instance.tags.all():
        if tag.usage_count > 0:
            tag.usage_count -= 1
            tag.save(update_fields=['usage_count'])
    
    logger.debug(f"Decremented tag usage counts for deleted asset: {instance.name}")


@receiver(post_save, sender=ContentUsage)
def update_content_performance_score(sender, instance, created, **kwargs):
    """Update content performance score based on usage analytics"""
    
    if not created and instance.success_rate is not None:
        content_asset = instance.content_asset
        
        # Calculate performance score based on usage count, success rate, and recency
        from django.utils import timezone
        from datetime import timedelta
        
        # Base score from success rate (0-100)
        success_score = float(instance.success_rate)
        
        # Usage frequency bonus (0-20 points)
        usage_score = min(content_asset.usage_count / 10, 20)
        
        # Recency bonus (0-10 points)
        recency_score = 0
        if content_asset.last_used_at:
            days_since_use = (timezone.now() - content_asset.last_used_at).days
            if days_since_use <= 7:
                recency_score = 10
            elif days_since_use <= 30:
                recency_score = 5
        
        # Combined performance score
        performance_score = success_score + usage_score + recency_score
        performance_score = min(performance_score, 100)  # Cap at 100
        
        content_asset.performance_score = round(performance_score, 2)
        content_asset.save(update_fields=['performance_score'])
        
        logger.debug(f"Updated performance score for {content_asset.name}: {performance_score}")


def track_workflow_content_usage(workflow_execution, node_results):
    """
    Track content usage during workflow execution
    This function should be called from the workflow engine
    """
    from .manager import content_manager
    
    try:
        for node_id, result in node_results.items():
            # Check if this node used content from the library
            if result.get('content_asset_id'):
                try:
                    content_asset = ContentAsset.objects.get(
                        id=result['content_asset_id'],
                        is_current_version=True
                    )
                    
                    # Track the usage
                    content_manager.track_content_usage(
                        content_asset=content_asset,
                        workflow_id=str(workflow_execution.workflow.id),
                        workflow_name=workflow_execution.workflow.name,
                        node_id=node_id,
                        node_type=result.get('node_type', 'unknown'),
                        usage_type=result.get('usage_type', 'template'),
                        variables_used=result.get('variables_used', {})
                    )
                    
                    # Record execution
                    content_manager.record_content_execution(
                        content_asset=content_asset,
                        workflow_id=str(workflow_execution.workflow.id),
                        node_id=node_id,
                        success=result.get('success', True),
                        execution_metadata={
                            'execution_id': str(workflow_execution.id),
                            'execution_time': result.get('execution_time'),
                            'node_output': result.get('output', {})
                        }
                    )
                    
                except ContentAsset.DoesNotExist:
                    logger.warning(f"Content asset {result['content_asset_id']} not found for workflow {workflow_execution.id}")
                except Exception as e:
                    logger.error(f"Error tracking content usage: {e}")
    
    except Exception as e:
        logger.error(f"Error in track_workflow_content_usage: {e}")