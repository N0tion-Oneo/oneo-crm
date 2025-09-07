#!/bin/bash

# Start Celery worker with proper configuration for macOS
# This script includes the fork safety fix needed for macOS

# Activate virtual environment
source ../venv/bin/activate

# Set environment variable to fix macOS fork() safety issue
# This prevents "objc[pid]: +[NSString initialize] may have been in progress" errors
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# Get tenant schema from first argument, default to 'oneotalent'
TENANT_SCHEMA=${1:-oneotalent}

# Determine queues based on tenant
SYNC_QUEUE="${TENANT_SCHEMA}_sync"
BACKGROUND_SYNC_QUEUE="${TENANT_SCHEMA}_background_sync"

echo "Starting Celery worker for tenant: $TENANT_SCHEMA"
echo "Queues: $SYNC_QUEUE, $BACKGROUND_SYNC_QUEUE"

# Start the worker
celery -A oneo_crm worker \
    --loglevel=info \
    --hostname=${TENANT_SCHEMA}_worker@%h \
    --queues=$SYNC_QUEUE,$BACKGROUND_SYNC_QUEUE \
    --concurrency=2 \
    --max-tasks-per-child=100