#!/usr/bin/env python
"""
Script to diagnose and fix Celery unacknowledged messages issue
"""
import redis
import json
from celery import Celery
from django.conf import settings
import os

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
import django
django.setup()

def check_unacked_messages():
    """Check for unacknowledged messages in Redis"""
    r = redis.Redis(host='localhost', port=6379, db=0)
    
    print("Checking for unacknowledged messages...")
    
    # Check unacked hash
    unacked_count = r.hlen('unacked')
    unacked_index_count = r.zcard('unacked_index')
    
    print(f"Found {unacked_count} messages in 'unacked' hash")
    print(f"Found {unacked_index_count} messages in 'unacked_index' zset")
    
    if unacked_count > 0:
        print("\nSample unacked messages:")
        # Get first few unacked messages
        unacked = r.hgetall('unacked')
        for i, (delivery_tag, message) in enumerate(list(unacked.items())[:3]):
            print(f"\nMessage {i+1}:")
            print(f"  Delivery tag: {delivery_tag.decode() if isinstance(delivery_tag, bytes) else delivery_tag}")
            # Try to parse message content
            try:
                msg_str = message.decode() if isinstance(message, bytes) else message
                # Extract JSON body if present
                if '[' in msg_str and ']' in msg_str:
                    start = msg_str.index('[')
                    end = msg_str.rindex(']') + 1
                    body = json.loads(msg_str[start:end])
                    if body and len(body) > 0:
                        task_info = body[0]
                        print(f"  Task: {task_info.get('task', 'unknown')}")
                        print(f"  ID: {task_info.get('id', 'unknown')}")
            except Exception as e:
                print(f"  Error parsing: {e}")
    
    return unacked_count

def clear_unacked_messages():
    """Clear all unacknowledged messages"""
    r = redis.Redis(host='localhost', port=6379, db=0)
    
    print("\nClearing unacknowledged messages...")
    
    # Delete unacked keys
    deleted = 0
    deleted += r.delete('unacked')
    deleted += r.delete('unacked_index')
    
    print(f"Deleted {deleted} unacked-related keys")
    
    # Also check for any other unacked keys
    for key in r.keys('*unack*'):
        key_str = key.decode() if isinstance(key, bytes) else key
        if key_str not in ['unacked', 'unacked_index']:
            r.delete(key)
            print(f"Also deleted: {key_str}")
            deleted += 1
    
    return deleted

def check_queue_status():
    """Check status of Celery queues"""
    r = redis.Redis(host='localhost', port=6379, db=0)
    
    print("\nChecking Celery queues:")
    
    queues = ['background_sync', 'communications', 'ai_processing', 'maintenance']
    for queue in queues:
        # Check different possible queue key formats
        for prefix in ['celery.', '_kombu.binding.']:
            key = f"{prefix}{queue}"
            if r.exists(key):
                queue_type = r.type(key).decode()
                if queue_type == 'list':
                    length = r.llen(key)
                    print(f"  {queue}: {length} messages")
                elif queue_type == 'set':
                    length = r.scard(key)
                    print(f"  {queue} (binding): {length} bindings")

def restart_recommendation():
    """Provide recommendations for restarting Celery"""
    print("\n" + "="*60)
    print("RECOMMENDATIONS:")
    print("="*60)
    print()
    print("1. The unacknowledged messages have been cleared.")
    print()
    print("2. To prevent this issue in the future, consider:")
    print("   - Setting task_acks_late=False in Celery config")
    print("   - OR ensuring tasks have proper error handling")
    print("   - OR using task_reject_on_worker_lost=True")
    print()
    print("3. Restart Celery workers with:")
    print("   pkill -f 'celery.*worker'")
    print("   Then restart using ./start-backend.sh")
    print()
    print("4. Monitor for new unacked messages with:")
    print("   redis-cli hlen unacked")
    print()

if __name__ == "__main__":
    print("Celery Unacknowledged Messages Diagnostic Tool")
    print("=" * 60)
    
    # Check current status
    unacked_count = check_unacked_messages()
    
    if unacked_count > 0:
        # Clear unacked messages
        response = input("\nDo you want to clear these unacked messages? (y/n): ")
        if response.lower() == 'y':
            clear_unacked_messages()
            print("\n✅ Unacked messages cleared!")
    else:
        print("\n✅ No unacknowledged messages found!")
    
    # Check queue status
    check_queue_status()
    
    # Provide recommendations
    restart_recommendation()