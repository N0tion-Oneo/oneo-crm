"""
Management command for tenant-specific Celery workers
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django_tenants.utils import get_tenant_model

from celery_workers import worker_manager


class Command(BaseCommand):
    help = 'Manage tenant-specific Celery workers'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=['start', 'stop', 'restart', 'status', 'start-all', 'stop-all'],
            help='Action to perform'
        )
        
        parser.add_argument(
            '--tenant',
            type=str,
            help='Tenant schema name (required for single tenant actions)'
        )
        
        parser.add_argument(
            '--concurrency',
            type=int,
            default=2,
            help='Number of concurrent tasks (default: 2)'
        )
        
        parser.add_argument(
            '--autoscale',
            type=str,
            help='Autoscale min,max workers (e.g., "2,4")'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        tenant_schema = options.get('tenant')
        
        if action == 'start-all':
            self.start_all_workers()
        elif action == 'stop-all':
            self.stop_all_workers()
        elif action == 'status':
            if tenant_schema:
                self.show_worker_status(tenant_schema)
            else:
                self.show_all_workers_status()
        else:
            # Single tenant actions
            if not tenant_schema:
                self.stdout.write(
                    self.style.ERROR('--tenant is required for this action')
                )
                return
            
            if action == 'start':
                self.start_worker(tenant_schema, options)
            elif action == 'stop':
                self.stop_worker(tenant_schema)
            elif action == 'restart':
                self.restart_worker(tenant_schema)
    
    def start_worker(self, tenant_schema, options):
        """Start workers for a specific tenant"""
        self.stdout.write(f'Starting workers for tenant: {tenant_schema}')
        
        kwargs = {
            'concurrency': options['concurrency']
        }
        
        if options['autoscale']:
            parts = options['autoscale'].split(',')
            if len(parts) == 2:
                kwargs['autoscale'] = (int(parts[0]), int(parts[1]))
        
        # Start all worker types for the tenant
        results = worker_manager.start_all_workers_for_tenant(tenant_schema)
        
        # Display results
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        for worker_type, success in results.items():
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ {worker_type} worker started')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ {worker_type} worker failed')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Started {success_count}/{total_count} workers for {tenant_schema}')
        )
    
    def stop_worker(self, tenant_schema):
        """Stop all workers for a specific tenant"""
        self.stdout.write(f'Stopping all workers for tenant: {tenant_schema}')
        
        worker_manager.stop_all_workers_for_tenant(tenant_schema)
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ All workers stopped for {tenant_schema}')
        )
    
    def restart_worker(self, tenant_schema):
        """Restart all workers for a specific tenant"""
        self.stdout.write(f'Restarting workers for tenant: {tenant_schema}')
        
        # Stop all workers
        worker_manager.stop_all_workers_for_tenant(tenant_schema)
        
        # Wait a moment for cleanup
        import time
        time.sleep(1)
        
        # Start all workers
        results = worker_manager.start_all_workers_for_tenant(tenant_schema)
        
        # Display results
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        self.stdout.write(
            self.style.SUCCESS(f'Restarted {success_count}/{total_count} workers for {tenant_schema}')
        )
    
    def start_all_workers(self):
        """Start workers for all active tenants"""
        self.stdout.write('Starting workers for all active tenants...')
        
        Tenant = get_tenant_model()
        count = 0
        
        for tenant in Tenant.objects.exclude(schema_name='public'):
            # You might want to check if tenant is active
            if worker_manager.start_worker(tenant.schema_name):
                count += 1
                self.stdout.write(f'  ✓ Started worker for {tenant.schema_name}')
            else:
                self.stdout.write(
                    self.style.WARNING(f'  ✗ Failed to start worker for {tenant.schema_name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Started {count} workers')
        )
    
    def stop_all_workers(self):
        """Stop all tenant workers"""
        self.stdout.write('Stopping all tenant workers...')
        
        worker_manager.stop_all_workers()
        
        self.stdout.write(
            self.style.SUCCESS('All workers stopped')
        )
    
    def show_worker_status(self, tenant_schema):
        """Show status for a specific tenant's worker"""
        status = worker_manager.get_worker_status(tenant_schema)
        
        self.stdout.write(f'\nWorker Status for {tenant_schema}:')
        self.stdout.write('-' * 40)
        
        if status['running']:
            self.stdout.write(
                self.style.SUCCESS(f'Status: RUNNING (PID: {status["pid"]})')
            )
            if status['config']:
                self.stdout.write(f'Queues: {", ".join(status["config"]["queues"])}')
                self.stdout.write(f'Concurrency: {status["config"]["concurrency"]}')
        else:
            self.stdout.write(
                self.style.WARNING('Status: NOT RUNNING')
            )
        
        if status['stats']:
            self.stdout.write('\nStatistics:')
            for key, value in status['stats'].items():
                self.stdout.write(f'  {key}: {value}')
    
    def show_all_workers_status(self):
        """Show status for all tenant workers"""
        statuses = worker_manager.get_all_workers_status()
        
        self.stdout.write('\nTenant Workers Status:')
        self.stdout.write('=' * 60)
        
        running_count = 0
        for status in statuses:
            tenant = status['tenant']
            is_running = status['running']
            
            if is_running:
                running_count += 1
                self.stdout.write(
                    f'{tenant:20} {self.style.SUCCESS("RUNNING"):15} PID: {status["pid"]}'
                )
            else:
                self.stdout.write(
                    f'{tenant:20} {self.style.WARNING("STOPPED"):15}'
                )
        
        self.stdout.write('=' * 60)
        self.stdout.write(f'Total: {len(statuses)} tenants, {running_count} running')