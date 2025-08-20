"""
Management command to sync account details from UniPile API
"""
import asyncio
from django.core.management.base import BaseCommand
from django_tenants.utils import tenant_context
from tenants.models import Tenant
from communications.services.account_sync import account_sync_service
from communications.models import UserChannelConnection
from asgiref.sync import sync_to_async


class Command(BaseCommand):
    help = 'Sync account details from UniPile API for all or specific connections'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Specific tenant schema name to sync (default: all tenants)'
        )
        parser.add_argument(
            '--account-id',
            type=str,
            help='Specific UniPile account ID to sync (default: all accounts)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔄 Starting Account Details Sync'))
        
        # Run async sync operation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if options['tenant']:
                result = loop.run_until_complete(self.sync_tenant(options['tenant'], options))
            else:
                result = loop.run_until_complete(self.sync_all_tenants(options))
            
            # Display results
            if result.get('success'):
                self.stdout.write(self.style.SUCCESS(f"✅ Sync completed successfully"))
                self.stdout.write(f"   Total connections processed: {result.get('total_processed', 0)}")
                self.stdout.write(f"   Successful syncs: {result.get('successful_syncs', 0)}")
                self.stdout.write(f"   Failed syncs: {result.get('failed_syncs', 0)}")
            else:
                self.stdout.write(self.style.ERROR(f"❌ Sync failed: {result.get('error')}"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Sync error: {e}"))
        finally:
            loop.close()

    async def sync_tenant(self, tenant_schema: str, options):
        """Sync accounts for a specific tenant"""
        try:
            tenant = await sync_to_async(Tenant.objects.get)(schema_name=tenant_schema)
            
            self.stdout.write(f"🏢 Processing tenant: {tenant.name} ({tenant_schema})")
            
            with tenant_context(tenant):
                if options['account_id']:
                    return await self.sync_specific_account(options['account_id'], options)
                else:
                    return await self.sync_tenant_accounts(options)
                    
        except Tenant.DoesNotExist:
            return {
                'success': False,
                'error': f'Tenant {tenant_schema} not found'
            }
    
    async def sync_specific_account(self, account_id: str, options):
        """Sync a specific account by UniPile account ID"""
        try:
            connection = await sync_to_async(UserChannelConnection.objects.get)(unipile_account_id=account_id)
            
            self.stdout.write(f"🔗 Found connection: {connection.account_name}")
            
            if options['dry_run']:
                self.stdout.write(self.style.WARNING("   [DRY RUN] Would sync account details"))
                return {
                    'success': True,
                    'total_processed': 1,
                    'successful_syncs': 0,
                    'failed_syncs': 0,
                    'dry_run': True
                }
            
            result = await account_sync_service.sync_account_details(connection)
            
            if result.get('success'):
                self.stdout.write(self.style.SUCCESS(f"   ✅ Synced successfully"))
                self.stdout.write(f"      Phone: {result.get('phone_number')}")
                self.stdout.write(f"      Type: {result.get('account_type')}")
                self.stdout.write(f"      Status: {result.get('messaging_status')}")
                return {
                    'success': True,
                    'total_processed': 1,
                    'successful_syncs': 1,
                    'failed_syncs': 0
                }
            else:
                self.stdout.write(self.style.ERROR(f"   ❌ Sync failed: {result.get('error')}"))
                return {
                    'success': True,
                    'total_processed': 1,
                    'successful_syncs': 0,
                    'failed_syncs': 1
                }
                
        except UserChannelConnection.DoesNotExist:
            return {
                'success': False,
                'error': f'Connection with account ID {account_id} not found'
            }
    
    async def sync_tenant_accounts(self, options):
        """Sync all accounts for current tenant"""
        connections = await sync_to_async(list)(UserChannelConnection.objects.filter(
            is_active=True,
            auth_status='authenticated',
            account_status='active'
        ).exclude(unipile_account_id=''))
        
        self.stdout.write(f"🔗 Found {len(connections)} active connections")
        
        if options['dry_run']:
            for conn in connections:
                self.stdout.write(self.style.WARNING(f"   [DRY RUN] Would sync: {conn.account_name} ({conn.unipile_account_id})"))
            return {
                'success': True,
                'total_processed': len(connections),
                'successful_syncs': 0,
                'failed_syncs': 0,
                'dry_run': True
            }
        
        successful_syncs = 0
        failed_syncs = 0
        
        for connection in connections:
            self.stdout.write(f"   🔄 Syncing: {connection.account_name}")
            
            try:
                result = await account_sync_service.sync_account_details(connection)
                
                if result.get('success'):
                    self.stdout.write(self.style.SUCCESS(f"      ✅ Success"))
                    successful_syncs += 1
                else:
                    self.stdout.write(self.style.ERROR(f"      ❌ Failed: {result.get('error')}"))
                    failed_syncs += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"      ❌ Error: {e}"))
                failed_syncs += 1
        
        return {
            'success': True,
            'total_processed': len(connections),
            'successful_syncs': successful_syncs,
            'failed_syncs': failed_syncs
        }
    
    async def sync_all_tenants(self, options):
        """Sync accounts for all tenants"""
        tenants = await sync_to_async(list)(Tenant.objects.exclude(schema_name='public'))
        
        self.stdout.write(f"🏢 Found {len(tenants)} tenants to process")
        
        total_processed = 0
        total_successful = 0
        total_failed = 0
        
        for tenant in tenants:
            self.stdout.write(f"\n🏢 Processing tenant: {tenant.name} ({tenant.schema_name})")
            
            with tenant_context(tenant):
                try:
                    result = await self.sync_tenant_accounts(options)
                    
                    if result.get('success'):
                        total_processed += result.get('total_processed', 0)
                        total_successful += result.get('successful_syncs', 0)
                        total_failed += result.get('failed_syncs', 0)
                    else:
                        self.stdout.write(self.style.ERROR(f"   ❌ Tenant sync failed: {result.get('error')}"))
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ Tenant error: {e}"))
        
        return {
            'success': True,
            'total_processed': total_processed,
            'successful_syncs': total_successful,
            'failed_syncs': total_failed
        }