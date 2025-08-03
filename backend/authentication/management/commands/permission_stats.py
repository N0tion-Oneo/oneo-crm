"""
Management command to view permission prefetch performance statistics
"""
from django.core.management.base import BaseCommand
from django.apps import apps
from django.core.cache import cache
import json


class Command(BaseCommand):
    help = 'View permission prefetch performance statistics and cache status'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='View cache status for specific user ID'
        )
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear all permission prefetch caches'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed cache contents (for debugging)'
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        clear_cache = options.get('clear_cache')
        detailed = options.get('detailed')

        if clear_cache:
            self.clear_all_caches()
            return

        if user_id:
            self.show_user_cache_status(user_id, detailed)
        else:
            self.show_global_stats()

    def show_global_stats(self):
        """Show global permission prefetch statistics"""
        self.stdout.write(
            self.style.SUCCESS('🔍 Permission Prefetch Performance Statistics')
        )
        self.stdout.write('=' * 60)

        # Try to get middleware instance stats (this is a simplified approach)
        # In production, you might store stats in cache or database
        self.stdout.write('📊 Performance Metrics:')
        
        # Cache hit ratio analysis
        cache_keys = cache.keys('prefetch_permissions_*_summary')
        total_cached_users = len([k for k in cache_keys if '_summary' in k])
        
        self.stdout.write(f'   • Users with cached permissions: {total_cached_users}')
        
        # Show recent cache activity
        self.stdout.write('\n🕒 Recent Cache Activity:')
        
        # Get timestamp info for cached users
        for key in cache_keys[:10]:  # Show first 10
            if '_summary' in key:
                user_id = key.split('_')[2]  # Extract user ID from key
                cached_data = cache.get(key)
                if cached_data and 'prefetched_at' in cached_data:
                    import datetime
                    timestamp = datetime.datetime.fromtimestamp(cached_data['prefetched_at'])
                    self.stdout.write(f'   • User {user_id}: {timestamp.strftime("%Y-%m-%d %H:%M:%S")}')

        self.stdout.write('\n💡 Tips:')
        self.stdout.write('   • Use --user-id <ID> to view specific user cache')
        self.stdout.write('   • Use --clear-cache to reset all caches')
        self.stdout.write('   • Use --detailed to see cache contents')

    def show_user_cache_status(self, user_id, detailed=False):
        """Show cache status for specific user"""
        self.stdout.write(
            self.style.SUCCESS(f'👤 Permission Cache Status for User {user_id}')
        )
        self.stdout.write('=' * 50)

        # Check for cached data
        cache_key = f'prefetch_permissions_{user_id}_summary'
        timestamp_key = f'prefetch_permissions_{user_id}_timestamp'
        
        cached_data = cache.get(cache_key)
        timestamp_data = cache.get(timestamp_key)

        if cached_data:
            self.stdout.write(self.style.SUCCESS('✅ Cache Status: CACHED'))
            
            if 'prefetched_at' in cached_data:
                import datetime
                timestamp = datetime.datetime.fromtimestamp(cached_data['prefetched_at'])
                self.stdout.write(f'📅 Cached at: {timestamp.strftime("%Y-%m-%d %H:%M:%S")}')
            
            if 'user_type_id' in cached_data:
                self.stdout.write(f'👥 User Type ID: {cached_data["user_type_id"]}')
            
            # Show permission summary
            permissions = cached_data.get('permissions', {})
            if permissions:
                self.stdout.write('\n🔐 Cached Permissions:')
                for perm, value in permissions.items():
                    status = '✅' if value else '❌'
                    self.stdout.write(f'   • {perm}: {status}')
            
            # Show accessible resources
            resources = cached_data.get('accessible_resources', {})
            if resources:
                self.stdout.write('\n📦 Accessible Resources:')
                for resource_type, access in resources.items():
                    if access == 'all':
                        self.stdout.write(f'   • {resource_type}: All (unlimited access)')
                    elif isinstance(access, list):
                        self.stdout.write(f'   • {resource_type}: {len(access)} specific items')
                    else:
                        self.stdout.write(f'   • {resource_type}: {access}')
            
            if detailed:
                self.stdout.write('\n🔍 Detailed Cache Contents:')
                self.stdout.write(json.dumps(cached_data, indent=2, default=str))
        
        else:
            self.stdout.write(self.style.WARNING('❌ Cache Status: NOT CACHED'))
            self.stdout.write('💡 This user\'s permissions have not been prefetched')

    def clear_all_caches(self):
        """Clear all permission prefetch caches"""
        self.stdout.write('🧹 Clearing all permission prefetch caches...')
        
        # Get all prefetch cache keys
        cache_keys = cache.keys('prefetch_permissions_*')
        async_cache_keys = cache.keys('async_prefetch_permissions_*')
        
        all_keys = list(cache_keys) + list(async_cache_keys)
        
        if all_keys:
            # Clear all keys
            for key in all_keys:
                cache.delete(key)
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Cleared {len(all_keys)} cache entries')
            )
        else:
            self.stdout.write(
                self.style.WARNING('ℹ️  No permission caches found to clear')
            )
        
        self.stdout.write('🔄 Permission caches will be rebuilt on next request')