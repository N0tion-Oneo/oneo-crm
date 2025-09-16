"""
Celery tasks for processing scheduled workflow triggers
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from celery import shared_task
from celery.schedules import crontab
from django.utils import timezone
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from asgiref.sync import async_to_sync
import pytz

from workflows.models import Workflow, WorkflowSchedule, WorkflowExecution
from workflows.engine import workflow_engine
from tenants.models import Tenant

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(name='workflows.process_scheduled_triggers')
def process_scheduled_triggers():
    """
    Process all scheduled workflow triggers across all tenants
    Runs every minute to check for workflows that need to be triggered
    """
    logger.info("Processing scheduled workflow triggers")

    # Get all active tenants
    tenants = Tenant.objects.filter(is_active=True)
    total_triggered = 0

    for tenant in tenants:
        with schema_context(tenant.schema_name):
            try:
                triggered_count = process_tenant_scheduled_triggers(tenant)
                total_triggered += triggered_count
            except Exception as e:
                logger.error(f"Error processing scheduled triggers for tenant {tenant.schema_name}: {e}")

    logger.info(f"Processed scheduled triggers: {total_triggered} workflows triggered")
    return total_triggered


def process_tenant_scheduled_triggers(tenant: Tenant) -> int:
    """
    Process scheduled triggers for a specific tenant
    """
    triggered_count = 0
    current_time = timezone.now()

    # Get all active workflows with schedule triggers
    workflows = Workflow.objects.filter(
        status='active',
        triggers__contains=[{'type': 'schedule'}]
    )

    for workflow in workflows:
        try:
            # Check each schedule trigger
            for trigger in workflow.triggers or []:
                if trigger.get('type') == 'schedule' and trigger.get('enabled', True):
                    if should_trigger_workflow(trigger, current_time):
                        trigger_scheduled_workflow.delay(
                            workflow_id=str(workflow.id),
                            tenant_id=str(tenant.id),
                            trigger_config=trigger
                        )
                        triggered_count += 1

                        # Update last triggered time
                        update_trigger_last_run(workflow, trigger, current_time)

        except Exception as e:
            logger.error(f"Error checking workflow {workflow.id} schedule: {e}")

    return triggered_count


def should_trigger_workflow(trigger: Dict[str, Any], current_time: datetime) -> bool:
    """
    Check if a workflow should be triggered based on its schedule configuration
    """
    config = trigger.get('config', {})
    cron_expr = config.get('cron')
    timezone_str = config.get('timezone', 'UTC')
    last_run = trigger.get('last_triggered_at')

    if not cron_expr:
        return False

    try:
        # Parse cron expression
        cron_parts = cron_expr.split()
        if len(cron_parts) != 5:
            logger.warning(f"Invalid cron expression: {cron_expr}")
            return False

        # Convert to target timezone
        tz = pytz.timezone(timezone_str)
        local_time = current_time.astimezone(tz)

        # Check if it's time to run
        minute, hour, day, month, weekday = cron_parts

        # Simple cron matching (can be enhanced with croniter library)
        if not match_cron_field(minute, local_time.minute):
            return False
        if not match_cron_field(hour, local_time.hour):
            return False
        if not match_cron_field(day, local_time.day):
            return False
        if not match_cron_field(month, local_time.month):
            return False
        if not match_cron_weekday(weekday, local_time.weekday()):
            return False

        # Check if already triggered in this minute
        if last_run:
            last_run_dt = datetime.fromisoformat(last_run)
            if (current_time - last_run_dt).total_seconds() < 60:
                return False

        return True

    except Exception as e:
        logger.error(f"Error evaluating cron expression {cron_expr}: {e}")
        return False


def match_cron_field(field: str, value: int) -> bool:
    """
    Match a single cron field against a value
    """
    if field == '*':
        return True

    # Handle ranges (e.g., "1-5")
    if '-' in field:
        start, end = field.split('-')
        return int(start) <= value <= int(end)

    # Handle lists (e.g., "1,3,5")
    if ',' in field:
        return str(value) in field.split(',')

    # Handle step values (e.g., "*/5")
    if field.startswith('*/'):
        step = int(field[2:])
        return value % step == 0

    # Direct match
    return str(value) == field


def match_cron_weekday(field: str, value: int) -> bool:
    """
    Match cron weekday field (0-6 or MON-SUN)
    Python weekday: 0=Monday, 6=Sunday
    Cron weekday: 0=Sunday, 6=Saturday
    """
    # Convert Python weekday to cron weekday
    cron_weekday = (value + 1) % 7

    if field == '*':
        return True

    # Handle day names
    day_map = {
        'SUN': 0, 'MON': 1, 'TUE': 2, 'WED': 3,
        'THU': 4, 'FRI': 5, 'SAT': 6
    }

    # Replace day names with numbers
    for name, num in day_map.items():
        field = field.replace(name, str(num))

    return match_cron_field(field, cron_weekday)


def update_trigger_last_run(workflow: Workflow, trigger: Dict, current_time: datetime):
    """
    Update the last triggered time for a schedule trigger
    """
    try:
        # Update trigger's last_triggered_at
        trigger['last_triggered_at'] = current_time.isoformat()

        # Save workflow
        workflow.save(update_fields=['triggers', 'updated_at'])

    except Exception as e:
        logger.error(f"Error updating trigger last run time: {e}")


@shared_task(name='workflows.trigger_scheduled_workflow')
def trigger_scheduled_workflow(
    workflow_id: str,
    tenant_id: str,
    trigger_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Trigger a scheduled workflow execution
    """
    try:
        tenant = Tenant.objects.get(id=tenant_id)

        with schema_context(tenant.schema_name):
            workflow = Workflow.objects.get(id=workflow_id)

            # Get system user for scheduled triggers
            system_user = User.objects.filter(email='scheduler@oneo.com').first()
            if not system_user:
                system_user = User.objects.create(
                    email='scheduler@oneo.com',
                    username='scheduler',
                    first_name='Scheduler',
                    last_name='System',
                    is_active=True
                )

            # Prepare trigger data
            trigger_data = {
                'trigger_type': 'schedule',
                'trigger_config': trigger_config,
                'triggered_at': timezone.now().isoformat(),
                'timezone': trigger_config.get('config', {}).get('timezone', 'UTC'),
                'cron_expression': trigger_config.get('config', {}).get('cron')
            }

            # Execute workflow
            execution = async_to_sync(workflow_engine.execute_workflow)(
                workflow=workflow,
                trigger_data=trigger_data,
                triggered_by=system_user,
                tenant=tenant
            )

            logger.info(f"Scheduled workflow {workflow_id} triggered successfully, execution ID: {execution.id}")

            return {
                'success': True,
                'execution_id': str(execution.id),
                'workflow_id': str(workflow.id),
                'workflow_name': workflow.name
            }

    except Exception as e:
        logger.error(f"Failed to trigger scheduled workflow {workflow_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'workflow_id': workflow_id
        }


@shared_task(name='workflows.cleanup_old_schedules')
def cleanup_old_schedules():
    """
    Clean up old workflow schedule records
    Runs daily to remove schedules older than 90 days
    """
    cutoff_date = timezone.now() - timedelta(days=90)
    deleted_count = 0

    for tenant in Tenant.objects.filter(is_active=True):
        with schema_context(tenant.schema_name):
            try:
                count, _ = WorkflowSchedule.objects.filter(
                    created_at__lt=cutoff_date
                ).delete()
                deleted_count += count
            except Exception as e:
                logger.error(f"Error cleaning up schedules for tenant {tenant.schema_name}: {e}")

    logger.info(f"Cleaned up {deleted_count} old workflow schedules")
    return deleted_count


@shared_task(name='workflows.validate_workflow_schedules')
def validate_workflow_schedules():
    """
    Validate all workflow schedules and disable invalid ones
    Runs weekly to ensure schedule configurations are valid
    """
    validated_count = 0
    disabled_count = 0

    for tenant in Tenant.objects.filter(is_active=True):
        with schema_context(tenant.schema_name):
            workflows = Workflow.objects.filter(
                status='active',
                triggers__contains=[{'type': 'schedule'}]
            )

            for workflow in workflows:
                try:
                    modified = False
                    for trigger in workflow.triggers or []:
                        if trigger.get('type') == 'schedule':
                            if not validate_schedule_config(trigger):
                                trigger['enabled'] = False
                                modified = True
                                disabled_count += 1
                                logger.warning(f"Disabled invalid schedule trigger for workflow {workflow.id}")
                            else:
                                validated_count += 1

                    if modified:
                        workflow.save(update_fields=['triggers'])

                except Exception as e:
                    logger.error(f"Error validating workflow {workflow.id} schedules: {e}")

    logger.info(f"Validated {validated_count} schedules, disabled {disabled_count} invalid ones")
    return {'validated': validated_count, 'disabled': disabled_count}


def validate_schedule_config(trigger: Dict[str, Any]) -> bool:
    """
    Validate a schedule trigger configuration
    """
    config = trigger.get('config', {})
    cron_expr = config.get('cron')
    timezone_str = config.get('timezone', 'UTC')

    if not cron_expr:
        return False

    # Validate cron expression format
    cron_parts = cron_expr.split()
    if len(cron_parts) != 5:
        return False

    # Validate timezone
    try:
        pytz.timezone(timezone_str)
    except pytz.exceptions.UnknownTimeZoneError:
        return False

    return True