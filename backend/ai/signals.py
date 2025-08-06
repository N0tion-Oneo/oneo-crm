"""
AI app signal handlers for integrating with the CRM system.
"""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import AIJob, AIUsageAnalytics


@receiver(post_save, sender=AIJob)
def handle_ai_job_completion(sender, instance, created, **kwargs):
    """
    Handle AI job completion to update usage analytics.
    """
    if not created and instance.status == 'completed' and instance.completed_at:
        try:
            # Create usage analytics record for completed job
            AIUsageAnalytics.objects.create(
                user=instance.created_by,
                ai_provider=instance.ai_provider,
                model_name=instance.model_name,
                operation_type=instance.job_type,
                tokens_used=instance.tokens_used,
                cost_cents=instance.cost_cents,
                response_time_ms=instance.processing_time_ms,
                pipeline=instance.pipeline,
                record_id=instance.record_id,
                created_at=instance.completed_at,
                date=instance.completed_at.date() if instance.completed_at else timezone.now().date()
            )
            print(f"✅ Created analytics record for completed AI job {instance.id}")
        except Exception as e:
            print(f"❌ Failed to create analytics for job {instance.id}: {e}")


@receiver(post_save, sender=AIJob)
def handle_ai_job_failure(sender, instance, created, **kwargs):
    """
    Handle AI job failure to track failed attempts.
    """
    if not created and instance.status == 'failed':
        try:
            # Create usage analytics entry for failed job (0 tokens, 0 cost)
            AIUsageAnalytics.objects.create(
                user=instance.created_by,
                ai_provider=instance.ai_provider,
                model_name=instance.model_name,
                operation_type=f"{instance.job_type}_failed",
                tokens_used=0,  # Failed jobs don't consume tokens
                cost_cents=0,   # Failed jobs don't incur costs
                response_time_ms=instance.processing_time_ms,
                pipeline=instance.pipeline,
                record_id=instance.record_id,
                created_at=instance.updated_at,
                date=instance.updated_at.date() if instance.updated_at else timezone.now().date()
            )
            print(f"✅ Created analytics record for failed AI job {instance.id}")
        except Exception as e:
            print(f"❌ Failed to create analytics for failed job {instance.id}: {e}")