#!/usr/bin/env python
"""
Management command to configure AI settings for a tenant
"""
import getpass
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from tenants.models import Tenant


class Command(BaseCommand):
    help = 'Configure AI settings for a tenant'

    def add_arguments(self, parser):
        parser.add_argument('tenant_name', type=str, help='Name of the tenant')
        parser.add_argument('--api-key', type=str, help='OpenAI API key (will prompt if not provided)')
        parser.add_argument('--enable', action='store_true', help='Enable AI features for this tenant')
        parser.add_argument('--disable', action='store_true', help='Disable AI features for this tenant')
        parser.add_argument('--usage-limit', type=float, help='Monthly usage limit in USD')
        parser.add_argument('--reset-usage', action='store_true', help='Reset current month usage to 0')
        parser.add_argument('--show-config', action='store_true', help='Show current AI configuration')

    def handle(self, *args, **options):
        tenant_name = options['tenant_name']
        
        # Get the tenant
        try:
            tenant = Tenant.objects.get(name=tenant_name)
        except Tenant.DoesNotExist:
            raise CommandError(f'Tenant "{tenant_name}" does not exist')
        
        if options['show_config']:
            self.show_config(tenant)
            return
        
        if options['enable'] and options['disable']:
            raise CommandError('Cannot both enable and disable AI features')
        
        # Update AI configuration
        updated = False
        
        if options['enable']:
            tenant.ai_enabled = True
            updated = True
            self.stdout.write(f'✅ AI features enabled for tenant "{tenant_name}"')
        
        if options['disable']:
            tenant.ai_enabled = False
            updated = True
            self.stdout.write(f'❌ AI features disabled for tenant "{tenant_name}"')
        
        if options['usage_limit'] is not None:
            tenant.ai_usage_limit = options['usage_limit']
            updated = True
            self.stdout.write(f'💰 Monthly usage limit set to ${options["usage_limit"]:.2f}')
        
        if options['reset_usage']:
            tenant.reset_monthly_usage()
            updated = True
            self.stdout.write(f'🔄 Monthly usage reset to $0.00')
        
        # Handle API key
        api_key = options.get('api_key')
        if api_key or (options['enable'] and not tenant.get_openai_api_key()):
            if not api_key:
                api_key = getpass.getpass('Enter OpenAI API key: ')
            
            if api_key:
                if tenant.set_openai_api_key(api_key):
                    updated = True
                    self.stdout.write('🔑 OpenAI API key configured successfully')
                else:
                    self.stderr.write('❌ Failed to store OpenAI API key')
        
        if updated:
            tenant.save()
            self.stdout.write(f'✅ Tenant "{tenant_name}" AI configuration updated')
        
        # Show final configuration
        self.show_config(tenant)
    
    def show_config(self, tenant):
        """Show current AI configuration for tenant"""
        self.stdout.write(f'\n🤖 AI Configuration for tenant "{tenant.name}":')
        self.stdout.write(f'   Schema: {tenant.schema_name}')
        self.stdout.write(f'   AI Enabled: {"✅ Yes" if tenant.ai_enabled else "❌ No"}')
        self.stdout.write(f'   API Key Configured: {"✅ Yes" if tenant.get_openai_api_key() else "❌ No"}')
        self.stdout.write(f'   Usage Limit: ${tenant.ai_usage_limit:.2f}/month')
        self.stdout.write(f'   Current Usage: ${tenant.ai_current_usage:.2f}')
        self.stdout.write(f'   Can Use AI: {"✅ Yes" if tenant.can_use_ai_features() else "❌ No"}')
        
        # Show model preferences
        preferences = tenant.get_ai_model_preferences()
        self.stdout.write(f'   Default Model: {preferences["default_model"]}')
        self.stdout.write(f'   Temperature: {preferences["temperature"]}')
        self.stdout.write(f'   Timeout: {preferences["timeout"]}s')