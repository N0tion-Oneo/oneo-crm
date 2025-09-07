"""
Dynamic Worker Management System for Multi-tenant Celery
Manages dedicated workers per tenant with centralized code
"""
import os
import subprocess
import signal
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import redis
from django.conf import settings
from django_tenants.utils import get_tenant_model

logger = logging.getLogger(__name__)


@dataclass
class WorkerConfig:
    """Configuration for a tenant-specific worker"""
    tenant_schema: str
    worker_name: str
    queues: List[str]
    concurrency: int = 2
    max_tasks_per_child: int = 100
    autoscale: Optional[Tuple[int, int]] = None  # (min, max) workers
    
    @property
    def queue_string(self):
        """Generate comma-separated queue string for celery command"""
        return ','.join(self.queues)
    
    @property
    def worker_id(self):
        """Unique worker identifier"""
        return self.worker_name


class TenantWorkerManager:
    """
    Manages lifecycle of tenant-specific Celery workers
    Each tenant gets dedicated workers that only process their queues
    """
    
    def __init__(self):
        from urllib.parse import urlparse
        
        # Parse the CELERY_BROKER_URL to get Redis connection details
        broker_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
        parsed = urlparse(broker_url)
        
        self.redis_client = redis.Redis(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 6379,
            db=int(parsed.path.lstrip('/')) if parsed.path else 0,
            decode_responses=True
        )
        self.workers: Dict[str, subprocess.Popen] = {}
        self.worker_configs: Dict[str, WorkerConfig] = {}
        
    # Define worker types and their associated queues
    WORKER_TYPES = {
        'sync': {
            'queues': ['sync', 'background_sync'],
            'concurrency': 2,
            'description': 'Handles data synchronization'
        },
        'workflows': {
            'queues': ['workflows', 'triggers'],
            'concurrency': 2,
            'description': 'Executes workflows and triggers'
        },
        'ai': {
            'queues': ['ai_processing'],
            'concurrency': 1,
            'description': 'Processes AI tasks'
        },
        'communications': {
            'queues': ['communications', 'communications_maintenance', 'contact_resolution', 'realtime'],
            'concurrency': 2,
            'description': 'Manages communications'
        },
        'analytics': {
            'queues': ['analytics'],
            'concurrency': 1,
            'description': 'Generates reports and analytics'
        },
        'operations': {
            'queues': ['general', 'maintenance', 'bulk_operations'],
            'concurrency': 2,
            'description': 'General operations and maintenance'
        }
    }
    
    def get_tenant_queues(self, tenant_schema: str, worker_type: str = None) -> List[str]:
        """
        Get queue names for a specific tenant and worker type
        Format: {tenant_schema}_{queue_type}
        """
        if worker_type and worker_type in self.WORKER_TYPES:
            base_queues = self.WORKER_TYPES[worker_type]['queues']
        else:
            # Get all queues if no specific type
            base_queues = []
            for wt in self.WORKER_TYPES.values():
                base_queues.extend(wt['queues'])
            base_queues = list(set(base_queues))  # Remove duplicates
        
        return [f"{tenant_schema}_{queue}" for queue in base_queues]
    
    def create_worker_config(self, tenant_schema: str, worker_type: str = None, **kwargs) -> WorkerConfig:
        """
        Create worker configuration for a tenant
        Can be customized based on tenant plan/size
        """
        Tenant = get_tenant_model()
        try:
            tenant = Tenant.objects.get(schema_name=tenant_schema)
            
            # Get default config for worker type
            if worker_type and worker_type in self.WORKER_TYPES:
                type_config = self.WORKER_TYPES[worker_type]
                default_concurrency = type_config['concurrency']
                worker_suffix = worker_type
            else:
                default_concurrency = 2
                worker_suffix = 'general'
            
            # Determine worker resources based on tenant plan
            # This could be stored in tenant model or settings
            if hasattr(tenant, 'worker_config'):
                config_data = tenant.worker_config
            else:
                # Default configuration
                config_data = {
                    'concurrency': default_concurrency,
                    'max_tasks_per_child': 100,
                }
            
            # Override with any provided kwargs
            config_data.update(kwargs)
            
            return WorkerConfig(
                tenant_schema=tenant_schema,
                worker_name=f"{tenant_schema}_{worker_suffix}",
                queues=self.get_tenant_queues(tenant_schema, worker_type),
                concurrency=config_data.get('concurrency', 2),
                max_tasks_per_child=config_data.get('max_tasks_per_child', 100),
                autoscale=config_data.get('autoscale')
            )
            
        except Tenant.DoesNotExist:
            logger.error(f"Tenant {tenant_schema} not found")
            raise
    
    def start_worker(self, tenant_schema: str, worker_type: str = None, **kwargs) -> bool:
        """
        Start a dedicated worker for a tenant
        Returns True if successful
        """
        try:
            # Generate worker key based on tenant and type
            worker_key = f"{tenant_schema}_{worker_type}" if worker_type else tenant_schema
            
            # Check if worker already exists
            if worker_key in self.workers:
                if self.is_worker_running(worker_key):
                    logger.info(f"Worker {worker_key} already running")
                    return True
                else:
                    # Clean up dead worker
                    self.stop_worker(worker_key)
            
            # Create worker configuration
            config = self.create_worker_config(tenant_schema, worker_type, **kwargs)
            self.worker_configs[worker_key] = config
            
            # Build celery worker command
            cmd = self._build_worker_command(config)
            
            # Start the worker process
            logger.info(f"Starting worker {worker_key}: {' '.join(cmd)}")
            
            # Set environment for worker
            env = os.environ.copy()
            env['TENANT_SCHEMA'] = tenant_schema
            if worker_type:
                env['WORKER_TYPE'] = worker_type
            
            # Fix for macOS fork() safety issue with Objective-C runtime
            # This prevents "objc[pid]: +[NSString initialize] may have been in progress" errors
            env['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
            
            # Get the backend directory
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Create log file for debugging
            log_file_path = os.path.join(backend_dir, f'worker_{worker_key}.log')
            log_file = open(log_file_path, 'w')
            
            # Start worker as subprocess
            process = subprocess.Popen(
                cmd,
                env=env,
                cwd=backend_dir,  # Set working directory to backend
                stdout=log_file,
                stderr=subprocess.STDOUT,  # Combine stderr with stdout for easier debugging
                preexec_fn=os.setsid  # Create new process group for clean shutdown
            )
            
            self.workers[worker_key] = process
            
            # Store worker info in Redis for monitoring
            self._store_worker_info(worker_key, config, process.pid)
            
            logger.info(f"Started worker for {tenant_schema} with PID {process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start worker for {tenant_schema}: {e}")
            return False
    
    def stop_worker(self, tenant_schema: str, timeout: int = 10) -> bool:
        """
        Gracefully stop a tenant's worker
        """
        try:
            if tenant_schema not in self.workers:
                logger.warning(f"No worker found for {tenant_schema}")
                return False
            
            process = self.workers[tenant_schema]
            
            if process.poll() is not None:
                # Process already dead
                logger.info(f"Worker for {tenant_schema} already stopped")
                del self.workers[tenant_schema]
                self._remove_worker_info(tenant_schema)
                return True
            
            logger.info(f"Stopping worker for {tenant_schema} (PID: {process.pid})")
            
            # Send SIGTERM for graceful shutdown
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            
            # Wait for graceful shutdown
            try:
                process.wait(timeout=timeout)
                logger.info(f"Worker for {tenant_schema} stopped gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown fails
                logger.warning(f"Force killing worker for {tenant_schema}")
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait()
            
            # Clean up
            del self.workers[tenant_schema]
            if tenant_schema in self.worker_configs:
                del self.worker_configs[tenant_schema]
            self._remove_worker_info(tenant_schema)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop worker for {tenant_schema}: {e}")
            return False
    
    def restart_worker(self, tenant_schema: str) -> bool:
        """Restart a tenant's worker"""
        logger.info(f"Restarting worker for {tenant_schema}")
        self.stop_worker(tenant_schema)
        return self.start_worker(tenant_schema)
    
    def is_worker_running(self, tenant_schema: str) -> bool:
        """Check if a tenant's worker is running"""
        if tenant_schema not in self.workers:
            return False
        
        process = self.workers[tenant_schema]
        return process.poll() is None
    
    def scale_worker(self, tenant_schema: str, concurrency: int) -> bool:
        """
        Scale a tenant's worker concurrency
        Requires restart to take effect
        """
        try:
            if tenant_schema in self.worker_configs:
                self.worker_configs[tenant_schema].concurrency = concurrency
                return self.restart_worker(tenant_schema)
            else:
                return self.start_worker(tenant_schema, concurrency=concurrency)
        except Exception as e:
            logger.error(f"Failed to scale worker for {tenant_schema}: {e}")
            return False
    
    def get_worker_logs(self, tenant_schema: str, lines: int = 50) -> str:
        """Get recent output from a worker process"""
        if tenant_schema not in self.workers:
            return f"No worker found for {tenant_schema}"
        
        process = self.workers[tenant_schema]
        if process.stdout:
            try:
                # Non-blocking read of available output
                import select
                if select.select([process.stdout], [], [], 0)[0]:
                    output = process.stdout.read(1024 * 10).decode('utf-8', errors='ignore')
                    return output[-lines*100:] if output else "No output available"
                else:
                    return "No new output available"
            except:
                return "Could not read worker output"
        return "No output stream available"
    
    def get_worker_status(self, tenant_schema: str) -> Dict:
        """Get status information for a tenant's worker"""
        status = {
            'tenant': tenant_schema,
            'running': False,
            'pid': None,
            'config': None,
            'stats': {}
        }
        
        if tenant_schema in self.workers:
            process = self.workers[tenant_schema]
            is_running = process.poll() is None
            
            status['running'] = is_running
            status['pid'] = process.pid if is_running else None
            
            if tenant_schema in self.worker_configs:
                config = self.worker_configs[tenant_schema]
                status['config'] = {
                    'queues': config.queues,
                    'concurrency': config.concurrency,
                    'max_tasks_per_child': config.max_tasks_per_child
                }
        
        # Get stats from Redis
        worker_info = self._get_worker_info(tenant_schema)
        if worker_info:
            status['stats'] = worker_info
        
        return status
    
    def get_all_workers_status(self) -> List[Dict]:
        """Get status for all managed workers"""
        statuses = []
        
        # Get all tenant schemas
        Tenant = get_tenant_model()
        for tenant in Tenant.objects.exclude(schema_name='public'):
            status = self.get_worker_status(tenant.schema_name)
            statuses.append(status)
        
        return statuses
    
    def _build_worker_command(self, config: WorkerConfig) -> List[str]:
        """Build the celery worker command"""
        import sys
        
        # Use the same Python executable that's running Django
        python_executable = sys.executable
        
        cmd = [
            python_executable, '-m', 'celery',
            '-A', 'oneo_crm',
            'worker',
            '--loglevel=info',
            f'--hostname={config.worker_id}@%h',
            f'--queues={config.queue_string}',
            f'--concurrency={config.concurrency}',
            f'--max-tasks-per-child={config.max_tasks_per_child}',
        ]
        
        # Add autoscaling if configured
        if config.autoscale:
            min_workers, max_workers = config.autoscale
            cmd.append(f'--autoscale={max_workers},{min_workers}')
        
        return cmd
    
    def _store_worker_info(self, tenant_schema: str, config: WorkerConfig, pid: int):
        """Store worker information in Redis for monitoring"""
        key = f"celery:worker:{tenant_schema}"
        info = {
            'tenant_schema': tenant_schema,
            'worker_name': config.worker_name,
            'queues': config.queues,
            'concurrency': config.concurrency,
            'pid': pid,
            'started_at': datetime.now().isoformat(),
            'status': 'running'
        }
        self.redis_client.setex(
            key,
            3600 * 24,  # 24 hour TTL
            json.dumps(info)
        )
    
    def _get_worker_info(self, tenant_schema: str) -> Optional[Dict]:
        """Get worker information from Redis"""
        key = f"celery:worker:{tenant_schema}"
        data = self.redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    
    def _remove_worker_info(self, tenant_schema: str):
        """Remove worker information from Redis"""
        key = f"celery:worker:{tenant_schema}"
        self.redis_client.delete(key)
    
    def start_all_tenant_workers(self):
        """Start workers for all active tenants"""
        Tenant = get_tenant_model()
        for tenant in Tenant.objects.exclude(schema_name='public'):
            if tenant.is_active:  # Assuming you have an is_active field
                self.start_worker(tenant.schema_name)
    
    def start_all_workers_for_tenant(self, tenant_schema: str) -> Dict[str, bool]:
        """
        Start all worker types for a specific tenant
        Returns dict of worker_type -> success status
        """
        results = {}
        for worker_type in self.WORKER_TYPES.keys():
            success = self.start_worker(tenant_schema, worker_type)
            results[worker_type] = success
            if success:
                logger.info(f"Started {worker_type} worker for {tenant_schema}")
            else:
                logger.error(f"Failed to start {worker_type} worker for {tenant_schema}")
        return results
    
    def stop_all_workers_for_tenant(self, tenant_schema: str) -> None:
        """
        Stop all workers for a specific tenant
        """
        workers_to_stop = []
        for key in list(self.workers.keys()):
            if key.startswith(tenant_schema):
                workers_to_stop.append(key)
        
        for worker_key in workers_to_stop:
            self.stop_worker(worker_key)
            logger.info(f"Stopped worker {worker_key}")
    
    def stop_all_workers(self):
        """Stop all managed workers"""
        worker_keys = list(self.workers.keys())
        for worker_key in worker_keys:
            self.stop_worker(worker_key)


# Singleton instance
worker_manager = TenantWorkerManager()