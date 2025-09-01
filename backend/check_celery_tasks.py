#!/usr/bin/env python
"""
Check Celery tasks for tenant context issues
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from celery import current_app
from kombu import Queue
import json

def check_pending_tasks():
    """Check pending Celery tasks for missing tenant_schema"""
    
    print("=" * 60)
    print("Checking Pending Celery Tasks")
    print("=" * 60)
    
    # Connect to Celery
    app = current_app
    
    # Get connection to broker
    with app.connection_or_acquire() as conn:
        # Check each queue
        for queue_name in ['celery', 'default']:
            try:
                # Create a queue object
                queue = Queue(queue_name, connection=conn)
                
                # Try to peek at messages (this is limited)
                print(f"\n📋 Queue: {queue_name}")
                
                # Note: This is a simplified check - proper monitoring would use Flower or similar
                simple_queue = conn.SimpleQueue(queue_name)
                
                # Try to get a message without consuming it
                message_count = 0
                try:
                    # This will timeout if empty
                    msg = simple_queue.get(block=False)
                    if msg:
                        # Put it back
                        simple_queue.put(msg)
                        message_count += 1
                        
                        # Check if it's a sync task
                        if 'sync_record_communications' in str(msg):
                            print(f"   ⚠️ Found sync task in queue")
                except:
                    pass
                
                print(f"   Messages visible: {message_count}")
                
            except Exception as e:
                print(f"   Could not check queue: {e}")
    
    print("\n" + "=" * 60)
    print("Note: For full monitoring, use Celery Flower or inspect commands")
    print("=" * 60)

if __name__ == "__main__":
    check_pending_tasks()