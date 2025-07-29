"""
Simple ASGI config for testing - without WebSocket complexity
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')

application = get_asgi_application()