"""
Management command to process scheduled workflows
Run this as a cron job or use Celery Beat for production
"""
import asyncio
from django.core.management.base import BaseCommand
from django.utils import timezone
# Import for task execution
from workflows.tasks import execute_workflow_async
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process scheduled workflows that are due for execution'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be executed without actually running workflows',
        )
        parser.add_argument(
            '--max-executions',
            type=int,
            default=50,
            help='Maximum number of workflows to execute in one run',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(f'Starting scheduled workflow processing at {timezone.now()}')
        )
        
        dry_run = options['dry_run']
        max_executions = options['max_executions']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No workflows will be executed'))
        
        try:
            # Process scheduled workflows
            self._process_scheduled_workflows(dry_run, max_executions)
            
        except Exception as e:
            logger.error(f"Scheduled workflow processing failed: {e}")
            self.stdout.write(
                self.style.ERROR(f'Error processing scheduled workflows: {e}')
            )
            raise
    
    def _process_scheduled_workflows(self, dry_run: bool, max_executions: int):
        """Process scheduled workflows asynchronously"""
        
        from workflows.models import WorkflowSchedule
        
        # Get due schedules
        now = timezone.now()
        due_schedules = WorkflowSchedule.objects.filter(
            is_active=True,
            next_execution__lte=now
        ).select_related('workflow')[:max_executions]
        
        if not due_schedules:
            self.stdout.write('No scheduled workflows due for execution')
            return
        
        self.stdout.write(f'Found {len(due_schedules)} scheduled workflows due for execution')
        
        for schedule in due_schedules:
            workflow = schedule.workflow
            
            if dry_run:
                self.stdout.write(
                    f'  [DRY RUN] Would execute: {workflow.name} (schedule: {schedule.name})'
                )
                continue
            
            try:
                self.stdout.write(f'  Executing: {workflow.name} (schedule: {schedule.name})')
                
                # Execute the scheduled workflow using Celery task
                execute_workflow_async.delay(
                    str(workflow.id),
                    trigger_data={'scheduled': True, 'schedule_id': str(schedule.id)},
                    triggered_by_user_id=None  # System triggered
                )
                
                # Update next execution time
                from croniter import croniter
                from datetime import datetime
                import pytz
                
                tz = pytz.timezone(schedule.timezone) if schedule.timezone else timezone.get_current_timezone()
                now = timezone.now().astimezone(tz)
                cron = croniter(schedule.cron_expression, now)
                schedule.next_execution = cron.get_next(datetime)
                schedule.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f'    ✓ Successfully executed {workflow.name}')
                )
                
            except Exception as e:
                logger.error(f"Failed to execute scheduled workflow {workflow.name}: {e}")
                self.stdout.write(
                    self.style.ERROR(f'    ✗ Failed to execute {workflow.name}: {e}')
                )
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS('Scheduled workflow processing completed')
            )