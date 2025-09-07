"""
Django signals for automatic worker management
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django_tenants.utils import get_tenant_model

from .worker_manager import worker_manager

logger = logging.getLogger(__name__)
Tenant = get_tenant_model()


@receiver(post_save, sender=Tenant)
def start_worker_on_tenant_create(sender, instance, created, **kwargs):
    """
    Automatically start a worker when a new tenant is created
    """
    if created and instance.schema_name != 'public':
        logger.info(f"New tenant created: {instance.schema_name}, starting worker...")
        try:
            worker_manager.start_worker(instance.schema_name)
            logger.info(f"Worker started for new tenant {instance.schema_name}")
        except Exception as e:
            logger.error(f"Failed to start worker for {instance.schema_name}: {e}")


@receiver(post_delete, sender=Tenant)
def stop_worker_on_tenant_delete(sender, instance, **kwargs):
    """
    Stop and clean up worker when a tenant is deleted
    """
    if instance.schema_name != 'public':
        logger.info(f"Tenant deleted: {instance.schema_name}, stopping worker...")
        try:
            worker_manager.stop_worker(instance.schema_name)
            logger.info(f"Worker stopped for deleted tenant {instance.schema_name}")
        except Exception as e:
            logger.error(f"Failed to stop worker for {instance.schema_name}: {e}")


def handle_tenant_status_change(tenant, is_active):
    """
    Start or stop worker based on tenant active status
    """
    if is_active:
        if not worker_manager.is_worker_running(tenant.schema_name):
            logger.info(f"Tenant {tenant.schema_name} activated, starting worker...")
            worker_manager.start_worker(tenant.schema_name)
    else:
        if worker_manager.is_worker_running(tenant.schema_name):
            logger.info(f"Tenant {tenant.schema_name} deactivated, stopping worker...")
            worker_manager.stop_worker(tenant.schema_name)