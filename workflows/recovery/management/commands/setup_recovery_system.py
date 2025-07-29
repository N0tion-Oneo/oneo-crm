"""
Management command to set up the workflow recovery system
Creates default recovery strategies and configurations
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from workflows.recovery.models import (
    RecoveryStrategy, RecoveryConfiguration,
    RecoveryStrategyType, CheckpointType
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up workflow recovery system with default strategies and configuration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing recovery system setup'
        )
        parser.add_argument(
            '--admin-user',
            type=str,
            help='Username of admin user to assign as creator'
        )
    
    def handle(self, *args, **options):
        reset = options['reset']
        admin_username = options.get('admin_user')
        
        # Get admin user
        admin_user = None
        if admin_username:
            try:
                admin_user = User.objects.get(username=admin_username)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'Admin user "{admin_username}" not found, proceeding without creator')
                )
        
        if reset:
            self.stdout.write('Resetting recovery system setup...')
            RecoveryStrategy.objects.all().delete()
            RecoveryConfiguration.objects.all().delete()
        
        # Create default recovery configuration
        self.create_default_configuration(admin_user)
        
        # Create default recovery strategies
        self.create_default_strategies(admin_user)
        
        self.stdout.write(
            self.style.SUCCESS('Successfully set up workflow recovery system')
        )
    
    def create_default_configuration(self, admin_user):
        """Create default recovery configuration"""
        config, created = RecoveryConfiguration.objects.get_or_create(
            config_name='default_recovery_config',
            defaults={
                'description': 'Default recovery system configuration',
                'auto_checkpoint_enabled': True,
                'checkpoint_interval_nodes': 5,
                'max_checkpoints_per_execution': 20,
                'checkpoint_retention_days': 30,
                'auto_recovery_enabled': True,
                'max_recovery_attempts': 3,
                'recovery_delay_minutes': 5,
                'replay_enabled': True,
                'max_concurrent_replays': 5,
                'replay_timeout_hours': 24,
                'auto_cleanup_enabled': True,
                'cleanup_interval_days': 7,
                'is_active': True,
                'created_by': admin_user
            }
        )
        
        if created:
            self.stdout.write(f'Created default recovery configuration: {config.config_name}')
        else:
            self.stdout.write(f'Default recovery configuration already exists: {config.config_name}')
    
    def create_default_strategies(self, admin_user):
        """Create default recovery strategies"""
        strategies = [
            {
                'name': 'Global Retry Strategy',
                'description': 'Default retry strategy for all workflow failures',
                'strategy_type': RecoveryStrategyType.RETRY,
                'workflow': None,  # Global strategy
                'node_type': '',
                'error_patterns': [],
                'max_retry_attempts': 3,
                'retry_delay_seconds': 60,
                'recovery_actions': [
                    {'action': 'retry_from_checkpoint', 'parameters': {'use_latest': True}}
                ],
                'priority': 50,
                'is_active': True
            },
            {
                'name': 'Timeout Error Retry',
                'description': 'Retry strategy for timeout errors with increased delay',
                'strategy_type': RecoveryStrategyType.RETRY,
                'workflow': None,
                'node_type': '',
                'error_patterns': ['timeout', 'timed out', 'connection timeout'],
                'max_retry_attempts': 2,
                'retry_delay_seconds': 120,
                'recovery_actions': [
                    {'action': 'retry_from_checkpoint', 'parameters': {'use_latest': True, 'increase_timeout': True}}
                ],
                'priority': 70,
                'is_active': True
            },
            {
                'name': 'Network Error Rollback',
                'description': 'Rollback strategy for network-related errors',
                'strategy_type': RecoveryStrategyType.ROLLBACK,
                'workflow': None,
                'node_type': '',
                'error_patterns': ['network', 'connection', 'dns', 'unreachable'],
                'max_retry_attempts': 1,
                'retry_delay_seconds': 180,
                'recovery_actions': [
                    {'action': 'rollback_to_stable', 'parameters': {'steps_back': 1}}
                ],
                'priority': 75,
                'is_active': True
            },
            {
                'name': 'Validation Error Skip',
                'description': 'Skip strategy for validation errors that can be bypassed',
                'strategy_type': RecoveryStrategyType.SKIP,
                'workflow': None,
                'node_type': '',
                'error_patterns': ['validation', 'invalid format', 'schema error'],
                'max_retry_attempts': 1,
                'retry_delay_seconds': 30,
                'recovery_actions': [
                    {'action': 'skip_node', 'parameters': {'log_skip_reason': True}}
                ],
                'priority': 60,
                'is_active': True
            },
            {
                'name': 'HTTP API Error Retry',
                'description': 'Specialized retry for HTTP API node failures',
                'strategy_type': RecoveryStrategyType.RETRY,
                'workflow': None,
                'node_type': 'http_request',
                'error_patterns': ['http', 'api', '500', '502', '503', '504'],
                'max_retry_attempts': 3,
                'retry_delay_seconds': 90,
                'recovery_actions': [
                    {'action': 'retry_from_checkpoint', 'parameters': {'exponential_backoff': True}}
                ],
                'priority': 80,
                'is_active': True
            },
            {
                'name': 'Email Send Retry',
                'description': 'Retry strategy for email sending failures',
                'strategy_type': RecoveryStrategyType.RETRY,
                'workflow': None,
                'node_type': 'email_send',
                'error_patterns': ['email', 'smtp', 'mail server', 'delivery failed'],
                'max_retry_attempts': 2,
                'retry_delay_seconds': 300,  # 5 minutes
                'recovery_actions': [
                    {'action': 'retry_from_checkpoint', 'parameters': {'check_email_config': True}}
                ],
                'priority': 85,
                'is_active': True
            },
            {
                'name': 'Database Error Rollback',
                'description': 'Rollback strategy for database-related errors',
                'strategy_type': RecoveryStrategyType.ROLLBACK,
                'workflow': None,
                'node_type': '',
                'error_patterns': ['database', 'sql', 'connection pool', 'deadlock'],
                'max_retry_attempts': 2,
                'retry_delay_seconds': 60,
                'recovery_actions': [
                    {'action': 'rollback_to_stable', 'parameters': {'clear_cache': True}}
                ],
                'priority': 90,
                'is_active': True
            },
            {
                'name': 'Critical System Error Manual',
                'description': 'Manual intervention required for critical system errors',
                'strategy_type': RecoveryStrategyType.MANUAL,
                'workflow': None,
                'node_type': '',
                'error_patterns': ['system error', 'critical', 'fatal', 'exception'],
                'max_retry_attempts': 0,
                'retry_delay_seconds': 0,
                'recovery_actions': [
                    {'action': 'require_manual_intervention', 'parameters': {'notify_admin': True}}
                ],
                'priority': 95,
                'is_active': True
            }
        ]
        
        created_count = 0
        for strategy_data in strategies:
            strategy, created = RecoveryStrategy.objects.get_or_create(
                name=strategy_data['name'],
                defaults={
                    **strategy_data,
                    'created_by': admin_user
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'Created recovery strategy: {strategy.name}')
            else:
                self.stdout.write(f'Recovery strategy already exists: {strategy.name}')
        
        self.stdout.write(f'Created {created_count} new recovery strategies')
    
    def create_workflow_specific_strategies(self, admin_user):
        """Create workflow-specific strategies (placeholder)"""
        # This could be extended to create strategies for specific workflows
        # based on their common failure patterns
        pass