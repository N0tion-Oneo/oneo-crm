# Multi-User Authentication Issues - Comprehensive Fix Plan

## Root Cause Analysis Summary

After conducting a deep dive into the authentication system, I've identified **7 critical issues** causing incorrect user identification in multi-user scenarios:

---

## Issue 1: JWT Authentication Race Condition ⚠️ HIGH PRIORITY

**Location**: `/Users/joshcowan/Oneo CRM/backend/authentication/jwt_authentication.py:32-34`

**Problem**: 
```python
self._current_request = request  # ❌ Shared instance variable
```
This creates a race condition where multiple simultaneous requests overwrite each other's request context.

**Impact**: User A's request could end up with User B's context, causing incorrect audit log entries.

**Fix**:
```python
# Replace lines 32-34 in jwt_authentication.py
def get_user(self, validated_token):
    try:
        user_id = validated_token['user_id']
        token_tenant_schema = validated_token.get('tenant_schema')
        
        # ✅ Get tenant from thread-local or context, not instance variable
        from django.db import connection
        current_schema = connection.schema_name if hasattr(connection, 'schema_name') else None
        
        logger.debug(f"JWT token validation - User ID: {user_id}, Token tenant: {token_tenant_schema}, Current tenant: {current_schema}")
        
        # Validate tenant context matches token
        if token_tenant_schema and current_schema and token_tenant_schema != current_schema:
            logger.warning(f"Tenant mismatch - Token tenant: {token_tenant_schema}, Current tenant: {current_schema}")
            raise InvalidToken("Token not valid for current tenant")
        
        # Use current tenant schema for user lookup
        if current_schema:
            with schema_context(current_schema):
                try:
                    user = User.objects.get(id=user_id)
                    logger.debug(f"Found user {user.email} (ID: {user.id}) in tenant {current_schema}")
                    return user
                except User.DoesNotExist:
                    logger.error(f"User {user_id} not found in tenant {current_schema}")
                    raise InvalidToken("User not found in tenant")
        
        # Remove authenticate method's _current_request completely
```

---

## Issue 2: Non-Tenant-Aware User Caching ⚠️ HIGH PRIORITY

**Location**: `/Users/joshcowan/Oneo CRM/backend/realtime/auth.py:98`

**Problem**:
```python
cache_key = f"user:{user_id}"  # ❌ Missing tenant isolation
```
Users from different tenants with the same ID can overwrite each other's cached data.

**Fix**:
```python
async def get_user_by_id(user_id: int):
    """Get user by ID with tenant-aware caching"""
    from asgiref.sync import sync_to_async
    from django.db import connection
    
    # ✅ Include tenant schema in cache key
    tenant_schema = getattr(connection, 'schema_name', 'public')
    cache_key = f"user:{tenant_schema}:{user_id}"
    
    user_data = cache.get(cache_key)
    
    if user_data:
        try:
            # Ensure we're in the correct tenant context for lookup
            with schema_context(tenant_schema):
                user = await sync_to_async(User.objects.get)(id=user_id)
                return user
        except User.DoesNotExist:
            cache.delete(cache_key)
            return None
    
    # Get from database with tenant context
    try:
        with schema_context(tenant_schema):
            user = await sync_to_async(User.objects.get)(id=user_id, is_active=True)
            
            # Cache with tenant-specific key
            cache.set(cache_key, {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'tenant_schema': tenant_schema,  # ✅ Include tenant in cache
            }, 300)
            
            return user
    except User.DoesNotExist:
        return None
```

---

## Issue 3: Session + JWT Authentication Conflicts ⚠️ MEDIUM PRIORITY

**Location**: `/Users/joshcowan/Oneo CRM/backend/oneo_crm/settings.py:198-201`

**Problem**: Your app uses both JWT and Session authentication simultaneously:
```python
'DEFAULT_AUTHENTICATION_CLASSES': [
    'authentication.jwt_authentication.TenantAwareJWTAuthentication',
    'rest_framework.authentication.SessionAuthentication',  # ❌ Conflict potential
],
```

**Impact**: User context can get mixed between session-based and JWT-based authentication.

**Fix**:
```python
# Create separate authentication classes for different endpoints
# In settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'authentication.jwt_authentication.TenantAwareJWTAuthentication',
        # Remove SessionAuthentication from default
    ],
    # ... rest of config
}

# For admin/browsable API endpoints that need sessions, override per-view:
class BrowsableAPIViewSet(viewsets.ModelViewSet):
    authentication_classes = [
        TenantAwareJWTAuthentication,
        SessionAuthentication,  # Only for browsable API
    ]
```

---

## Issue 4: Disabled Tenant-Aware Middleware ⚠️ MEDIUM PRIORITY

**Location**: `/Users/joshcowan/Oneo CRM/backend/oneo_crm/settings.py:129-132`

**Problem**: Critical async middleware is commented out:
```python
# Temporarily disabled async middleware for testing
# 'authentication.middleware.AsyncSessionAuthenticationMiddleware',  # ❌ Disabled
# 'authentication.middleware.AsyncTenantMiddleware',  # ❌ Disabled
# 'authentication.middleware.AsyncPermissionMiddleware',  # ❌ Disabled
```

**Fix**: Re-enable with proper error handling:
```python
MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',  # Must be first
    'core.middleware.MaintenanceModeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # ✅ Re-enable with fixes
    'authentication.middleware.AsyncTenantMiddleware',  # Tenant context for async
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'authentication.middleware.AsyncPermissionMiddleware',  # Permission context
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.monitoring.PerformanceMiddleware',
]
```

---

## Issue 5: Serializer User Context Race Condition ⚠️ LOW-MEDIUM PRIORITY

**Location**: `/Users/joshcowan/Oneo CRM/backend/api/serializers.py:105`

**Problem**: Serializer depends on `self.context['request'].user` which can be inconsistent across concurrent requests.

**Current Pattern**:
```python
def update(self, instance, validated_data):
    validated_data['updated_by'] = self.context['request'].user  # ❌ Potential race condition
    return super().update(instance, validated_data)
```

**Fix**: Add validation to ensure user context integrity:
```python
def update(self, instance, validated_data):
    request = self.context.get('request')
    if not request or not hasattr(request, 'user') or not request.user.is_authenticated:
        raise serializers.ValidationError("Invalid user context")
    
    # ✅ Validate user belongs to current tenant
    from django.db import connection
    current_tenant = getattr(connection, 'schema_name', None)
    if current_tenant:
        # Verify user exists in current tenant context
        with schema_context(current_tenant):
            try:
                User.objects.get(id=request.user.id, is_active=True)
            except User.DoesNotExist:
                logger.error(f"User {request.user.id} not found in tenant {current_tenant}")
                raise serializers.ValidationError("User not valid for current tenant")
    
    validated_data['updated_by'] = request.user
    return super().update(instance, validated_data)
```

---

## Issue 6: WebSocket Authentication Tenant Validation Missing ⚠️ MEDIUM PRIORITY

**Location**: `/Users/joshcowan/Oneo CRM/backend/realtime/auth.py:17-47`

**Problem**: WebSocket authentication doesn't validate that the JWT token's tenant matches the current tenant context.

**Fix**: Add tenant validation to WebSocket authentication:
```python
async def authenticate_websocket_jwt(token: str, tenant_schema: str = None):
    """Authenticate JWT token for WebSocket connections with tenant validation"""
    if not token:
        return None
    
    try:
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Validate JWT token
        access_token = AccessToken(token)
        user_id = access_token['user_id']
        token_tenant_schema = access_token.get('tenant_schema')
        
        # ✅ Validate tenant context
        if tenant_schema and token_tenant_schema and tenant_schema != token_tenant_schema:
            logger.warning(f"WebSocket tenant mismatch - Expected: {tenant_schema}, Token: {token_tenant_schema}")
            return None
        
        # Get user with tenant-aware caching
        user = await get_user_by_id(int(user_id))
        if not user or not user.is_active:
            logger.warning(f"User {user_id} not found or inactive")
            return None
        
        # ✅ Final validation: user exists in current tenant
        if tenant_schema:
            with schema_context(tenant_schema):
                try:
                    await sync_to_async(User.objects.get)(id=user_id, is_active=True)
                except User.DoesNotExist:
                    logger.error(f"WebSocket user {user_id} not found in tenant {tenant_schema}")
                    return None
        
        return user
        
    except (InvalidToken, TokenError, KeyError) as e:
        logger.warning(f"WebSocket JWT authentication failed: {e}")
        return None
```

---

## Issue 7: Signal Handler User Context Validation Missing ⚠️ LOW PRIORITY

**Location**: `/Users/joshcowan/Oneo CRM/backend/pipelines/signals.py:121`

**Problem**: Audit log creation doesn't validate that `instance.updated_by` is still valid.

**Fix**: Add user validation in signal handlers:
```python
@receiver(post_save, sender=Record)
def handle_record_save(sender, instance, created, **kwargs):
    """Handle record save events with user validation"""
    
    if not created and hasattr(instance, '_original_data'):
        try:
            # ✅ Validate user context before creating audit log
            if not instance.updated_by:
                logger.warning(f"No updated_by user for record {instance.id}")
                return
            
            if not instance.updated_by.is_authenticated:
                logger.warning(f"Invalid user context for record {instance.id}: {instance.updated_by}")
                return
                
            # ✅ Verify user exists in current tenant context
            from django.db import connection
            current_tenant = getattr(connection, 'schema_name', None)
            if current_tenant:
                try:
                    with schema_context(current_tenant):
                        User.objects.get(id=instance.updated_by.id, is_active=True)
                except User.DoesNotExist:
                    logger.error(f"Audit log user {instance.updated_by.id} not found in tenant {current_tenant}")
                    return
            
            # Proceed with existing audit log creation...
            original_data = getattr(instance, '_original_data', {})
            # ... rest of existing code
```

---

## Priority Implementation Order

1. **Issue 1** - JWT Authentication Race Condition (Critical - fix immediately)
2. **Issue 2** - Non-Tenant-Aware User Caching (Critical - fix immediately) 
3. **Issue 4** - Re-enable Tenant-Aware Middleware (High)
4. **Issue 3** - Session + JWT Authentication Conflicts (Medium)
5. **Issue 6** - WebSocket Authentication Tenant Validation (Medium)
6. **Issue 5** - Serializer User Context Race Condition (Low-Medium)
7. **Issue 7** - Signal Handler User Context Validation (Low)

---

## Testing the Fixes

After implementing these fixes, test with:

1. **Multiple simultaneous users** updating different records
2. **Same user in multiple browser tabs** 
3. **Cross-tenant access attempts**
4. **WebSocket connections with concurrent HTTP requests**
5. **Session + JWT authentication mix scenarios**

Expected result: Audit logs should correctly show the actual user who performed each action.

---

## Additional Monitoring

Add this monitoring code to detect when issues occur:

```python
# In pipelines/signals.py
@receiver(post_save, sender=Record)  
def handle_record_save(sender, instance, created, **kwargs):
    if not created:
        # ✅ Add monitoring for user context issues
        from django.db import connection
        current_tenant = getattr(connection, 'schema_name', 'unknown')
        
        logger.info(f"AUDIT_CONTEXT: Record {instance.id} updated by user {instance.updated_by.id if instance.updated_by else 'None'} in tenant {current_tenant}")
        
        # Monitor for potential context mismatches
        if instance.updated_by and hasattr(instance.updated_by, 'last_login'):
            time_since_login = timezone.now() - (instance.updated_by.last_login or timezone.now())
            if time_since_login.total_seconds() > 3600:  # 1 hour
                logger.warning(f"STALE_USER_CONTEXT: User {instance.updated_by.id} last login was {time_since_login} ago")
```

This comprehensive fix addresses all the root causes of incorrect user identification in your multi-tenant authentication system.