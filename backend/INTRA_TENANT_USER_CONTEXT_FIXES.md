# Intra-Tenant User Context Corruption - Critical Fix Analysis

## The Real Problem: Same Tenant, Wrong Users

You're experiencing **user context bleeding within the same tenant** where User A's actions are being recorded as performed by User B (or vice versa). This is a **critical authentication integrity issue**.

---

## Root Cause #1: JWT Authentication Instance Variable Race Condition ⚠️ CRITICAL

**Location**: `authentication/jwt_authentication.py:87`

**The Smoking Gun**:
```python
def authenticate(self, request):
    try:
        # Store request for tenant context access
        self._current_request = request  # ❌ SHARED INSTANCE VARIABLE
```

**What's Happening**:
1. User A makes request → `self._current_request = User A's request`
2. **Milliseconds later**, User B makes request → `self._current_request = User B's request` (overwrites User A)
3. User A's authentication continues using User B's request context
4. **Result**: User A's action gets logged with User B's user ID

**Proof This Is The Issue**:
- Line 114: `user = self.get_user(validated_token)` calls `get_user()` 
- Line 32 in `get_user()`: `request = getattr(self, '_current_request', None)` - **gets whatever was set last**

**Critical Fix**:
```python
# Replace the entire authenticate method in jwt_authentication.py
def authenticate(self, request):
    """Authenticate request with proper request isolation"""
    try:
        # ✅ NEVER store request in instance variable
        # Get tenant context directly from thread-local connection
        from django.db import connection
        tenant = getattr(connection, 'tenant', None)
        tenant_schema = tenant.schema_name if tenant else None
        
        logger.debug(f"JWT authenticate called - Tenant: {tenant_schema}")
        logger.debug(f"Request host: {request.get_host()}")
        
        # Get the header and extract the token
        header = self.get_header(request)
        if header is None:
            return None
        
        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None
        
        # Validate the token
        validated_token = self.get_validated_token(raw_token)
        
        # ✅ Pass request directly to get_user, don't store in instance
        user = self.get_user_with_request(validated_token, request, tenant_schema)
        
        if user:
            logger.info(f"JWT authentication successful for user: {user.email} (ID: {user.id})")
            return (user, validated_token)
        
        return None
        
    except TokenError as e:
        logger.debug(f"JWT token error: {e}")
        return None
    except Exception as e:
        logger.error(f"JWT authentication error: {e}")
        return None

def get_user_with_request(self, validated_token, request, tenant_schema):
    """Get user from validated token with request context passed directly"""
    try:
        user_id = validated_token['user_id']
        token_tenant_schema = validated_token.get('tenant_schema')
        
        # Validate tenant context matches token
        if token_tenant_schema and tenant_schema and token_tenant_schema != tenant_schema:
            logger.warning(f"Tenant mismatch - Token: {token_tenant_schema}, Current: {tenant_schema}")
            raise InvalidToken("Token not valid for current tenant")
        
        if tenant_schema:
            with schema_context(tenant_schema):
                try:
                    user = User.objects.get(id=user_id)
                    logger.debug(f"Found user {user.email} (ID: {user.id}) in tenant {tenant_schema}")
                    return user
                except User.DoesNotExist:
                    logger.error(f"User {user_id} not found in tenant {tenant_schema}")
                    raise InvalidToken("User not found in tenant")
        
        # Fallback without tenant context
        try:
            user = User.objects.get(id=user_id)
            return user
        except User.DoesNotExist:
            raise InvalidToken("User not found")
            
    except KeyError as e:
        logger.error(f"Missing required field in token: {e}")
        raise InvalidToken("Token contained no recognizable user identification")
```

---

## Root Cause #2: DRF Authentication Class Instance Sharing ⚠️ CRITICAL

**The Deeper Issue**: Django REST Framework **reuses authentication class instances** across requests for performance. Your `TenantAwareJWTAuthentication` class is being shared between all concurrent requests within the same tenant.

**Evidence**:
- DRF creates one instance of `TenantAwareJWTAuthentication` per process
- Multiple requests use the **same instance** simultaneously
- Any instance variables (`self._current_request`) get corrupted

**Why This Happens**:
```python
# In settings.py - DRF reuses this class instance
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'authentication.jwt_authentication.TenantAwareJWTAuthentication',  # ❌ Single shared instance
    ]
}
```

---

## Root Cause #3: User Caching Without Request Context ⚠️ HIGH

**Location**: `realtime/auth.py:98-121`

**Problem**: Even though this is for WebSocket auth, if any part of your system uses this caching, it's not request-aware:

```python
cache_key = f"user:{user_id}"  # ❌ No request isolation
```

If two users have the same ID in cache race conditions, wrong user data could be retrieved.

**Fix**:
```python
async def get_user_by_id(user_id: int, request_id: str = None):
    """Get user by ID with request-aware caching"""
    from asgiref.sync import sync_to_async
    from django.db import connection
    
    # ✅ Include request context in cache key for safety
    tenant_schema = getattr(connection, 'schema_name', 'default')
    cache_key = f"user:{tenant_schema}:{user_id}:{request_id or 'norequestid'}"
    
    # Always fetch fresh from DB for now to avoid cache corruption
    # TODO: Re-enable caching once user context issues are resolved
    try:
        with schema_context(tenant_schema):
            user = await sync_to_async(User.objects.get)(id=user_id, is_active=True)
            return user
    except User.DoesNotExist:
        return None
```

---

## Root Cause #4: Serializer Context Corruption ⚠️ HIGH

**Location**: `api/serializers.py:105`

**Problem**: When DRF processes concurrent requests, the serializer context can get mixed up:

```python
def update(self, instance, validated_data):
    validated_data['updated_by'] = self.context['request'].user  # ❌ Context can be wrong request
    return super().update(instance, validated_data)
```

**The Issue**: If serializer instances are reused or if there's any delay between context setting and usage, `self.context['request']` might point to a different request's user.

**Fix**:
```python
def update(self, instance, validated_data):
    request = self.context.get('request')
    
    # ✅ Extensive validation of user context
    if not request:
        raise serializers.ValidationError("No request context available")
    
    if not hasattr(request, 'user') or not request.user:
        raise serializers.ValidationError("No user in request context")
    
    if not request.user.is_authenticated:
        raise serializers.ValidationError("User is not authenticated")
    
    # ✅ Log for debugging
    logger.info(f"SERIALIZER_UPDATE: Record {instance.id if instance else 'NEW'} being updated by user {request.user.id} ({request.user.email})")
    
    # ✅ Additional integrity check - verify user ID hasn't changed
    expected_user_id = getattr(request, '_original_user_id', None)
    if expected_user_id and expected_user_id != request.user.id:
        logger.error(f"USER_CONTEXT_CORRUPTION: Expected user {expected_user_id}, got {request.user.id}")
        raise serializers.ValidationError("User context corruption detected")
    
    validated_data['updated_by'] = request.user
    return super().update(instance, validated_data)

def get_serializer_context(self):
    """Add user ID tracking to context"""
    context = super().get_serializer_context()
    if 'request' in context and hasattr(context['request'], 'user'):
        # ✅ Store original user ID for integrity checking
        context['request']._original_user_id = context['request'].user.id
    return context
```

---

## Root Cause #5: Signal Handler Timing Issues ⚠️ MEDIUM

**Location**: `pipelines/signals.py:121`

**Problem**: By the time the signal handler runs, `instance.updated_by` might have been corrupted by one of the above race conditions.

**Fix**: Add validation and logging:
```python
@receiver(post_save, sender=Record)
def handle_record_save(sender, instance, created, **kwargs):
    """Handle record save events with extensive user context validation"""
    
    if not created and hasattr(instance, '_original_data'):
        # ✅ Validate user context integrity
        if not instance.updated_by:
            logger.error(f"SIGNAL_ERROR: No updated_by user for record {instance.id}")
            return
        
        if not hasattr(instance.updated_by, 'id') or not instance.updated_by.id:
            logger.error(f"SIGNAL_ERROR: Invalid updated_by user object for record {instance.id}: {instance.updated_by}")
            return
        
        # ✅ Log for debugging user context
        logger.info(f"AUDIT_LOG_CREATION: Record {instance.id} updated by user {instance.updated_by.id} ({instance.updated_by.email})")
        
        try:
            # ... existing audit log creation code ...
            audit_log = AuditLog.objects.create(
                user=instance.updated_by,
                action='updated',
                model_name='Record',
                object_id=str(instance.id),
                changes={
                    'record_title': instance.title,
                    'pipeline_name': instance.pipeline.name,
                    'field_changes': changes,
                    'changes_summary': field_changes_summary,
                    'total_changes': len(changes),
                    # ✅ Add debugging info
                    'debug_user_id': instance.updated_by.id,
                    'debug_user_email': instance.updated_by.email,
                    'debug_timestamp': timezone.now().isoformat()
                }
            )
            
            logger.info(f"AUDIT_LOG_CREATED: ID {audit_log.id} for record {instance.id} by user {instance.updated_by.id}")
            
        except Exception as e:
            logger.error(f"AUDIT_LOG_FAILED: Record {instance.id}, User {instance.updated_by.id}: {e}")
```

---

## Immediate Action Plan

### Step 1: Fix JWT Authentication Race Condition (DO THIS FIRST)
Replace the `authenticate` method in `authentication/jwt_authentication.py` with the fixed version above.

### Step 2: Add Debug Logging
Add this to your Django logging settings:
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'user_context_debug.log',
        },
    },
    'loggers': {
        'authentication.jwt_authentication': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'api.serializers': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'pipelines.signals': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### Step 3: Test With Multiple Users
1. Open 2-3 browser tabs/windows
2. Log in as different users in each
3. Have them edit different records simultaneously
4. Monitor the logs for user context corruption

### Step 4: Verify Fix
After implementing the JWT auth fix, you should see in the logs:
- Each request gets its own user context
- No more "User X action logged as User Y"
- Consistent user IDs throughout the request lifecycle

---

## The Bottom Line

The **primary issue** is the JWT authentication class storing request context in a shared instance variable (`self._current_request`). This single issue can explain all your user context corruption problems because:

1. User A starts authentication
2. User B starts authentication (overwrites A's context)
3. User A continues with User B's context
4. User A's actions get attributed to User B

Fix this one issue and your audit log problems should resolve immediately.