#!/usr/bin/env python
"""
Debug the frontend sync endpoint
"""
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from django.contrib.auth import get_user_model
from communications.models import UserChannelConnection, Channel
from communications.channels.whatsapp.background_sync import _run_comprehensive_sync_simplified
from django.utils import timezone as django_timezone

User = get_user_model()

def test_sync_debug():
    """Debug the sync process"""
    
    # Switch to oneotalent schema
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print("\n🔍 Debugging Frontend Sync")
        print("=" * 60)
        
        # Get a user
        user = User.objects.filter(is_active=True).first()
        if not user:
            print("❌ No active user found")
            return
            
        print(f"✅ User: {user.username}")
        
        # Get WhatsApp connections
        whatsapp_connections = UserChannelConnection.objects.filter(
            user=user,
            channel_type='whatsapp',
            is_active=True,
            unipile_account_id__isnull=False
        )
        
        print(f"📊 Found {whatsapp_connections.count()} connections")
        
        if not whatsapp_connections.exists():
            print("❌ No active WhatsApp connections found")
            return
        
        sync_results = []
        
        for connection in whatsapp_connections:
            print(f"\n🔄 Processing connection: {connection.account_name}")
            
            try:
                # Get or create channel
                channel, created = Channel.objects.get_or_create(
                    unipile_account_id=connection.unipile_account_id,
                    channel_type='whatsapp',
                    defaults={
                        'name': f"WhatsApp Account {connection.account_name}",
                        'auth_status': 'authenticated',
                        'is_active': True,
                        'created_by': user
                    }
                )
                
                print(f"   Channel: {channel.name} (created: {created})")
                
                # Run sync
                print(f"   Running sync...")
                
                sync_options = {
                    'days_back': 30,
                    'max_messages_per_chat': 100,
                }
                
                try:
                    stats = _run_comprehensive_sync_simplified(
                        channel=channel,
                        options=sync_options,
                        connection=connection
                    )
                    
                    print(f"   ✅ Sync completed:")
                    print(f"      Chats synced: {stats.get('chats_synced', 0)}")
                    print(f"      Messages synced: {stats.get('messages_synced', 0)}")
                    print(f"      Attendees synced: {stats.get('attendees_synced', 0)}")
                    print(f"      Conversations created: {stats.get('conversations_created', 0)}")
                    print(f"      Conversations updated: {stats.get('conversations_updated', 0)}")
                    
                    if stats.get('errors'):
                        print(f"   ⚠️ Errors:")
                        for error in stats['errors']:
                            print(f"      - {error}")
                    
                    # Update connection sync status
                    connection.last_sync_at = django_timezone.now()
                    connection.sync_error_count = 0
                    connection.last_error = ''
                    connection.save(update_fields=['last_sync_at', 'sync_error_count', 'last_error'])
                    
                    sync_results.append({
                        'account_id': connection.unipile_account_id,
                        'connection_id': str(connection.id),
                        'success': True,
                        'attendees_synced': stats.get('attendees_synced', 0),
                        'conversations_synced': stats.get('chats_synced', 0),
                        'conversations_created': stats.get('conversations_created', 0),
                        'conversations_updated': stats.get('conversations_updated', 0),
                        'messages_synced': stats.get('messages_synced', 0),
                        'errors': stats.get('errors', [])
                    })
                    
                except Exception as sync_error:
                    print(f"   ❌ Sync failed: {sync_error}")
                    import traceback
                    traceback.print_exc()
                    
                    connection.sync_error_count += 1
                    connection.last_error = str(sync_error)
                    connection.save(update_fields=['sync_error_count', 'last_error'])
                    
                    sync_results.append({
                        'account_id': connection.unipile_account_id,
                        'connection_id': str(connection.id),
                        'success': False,
                        'error': str(sync_error),
                        'attendees_synced': 0,
                        'conversations_synced': 0,
                        'messages_synced': 0
                    })
                    
            except Exception as e:
                print(f"   ❌ Error processing connection: {e}")
                import traceback
                traceback.print_exc()
        
        # Summary
        successful_syncs = sum(1 for result in sync_results if result['success'])
        total_attendees = sum(result.get('attendees_synced', 0) for result in sync_results)
        total_conversations = sum(result.get('conversations_synced', 0) for result in sync_results)
        total_messages = sum(result.get('messages_synced', 0) for result in sync_results)
        
        print(f"\n📊 Summary:")
        print(f"   Successful syncs: {successful_syncs}/{len(sync_results)}")
        print(f"   Total attendees synced: {total_attendees}")
        print(f"   Total conversations synced: {total_conversations}")
        print(f"   Total messages synced: {total_messages}")

if __name__ == "__main__":
    test_sync_debug()