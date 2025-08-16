# Cloudflare Tunnel Configuration for UniPile Integration

## Overview

The Oneo CRM system is configured to work with Cloudflare tunnel through `oneocrm.com` for UniPile hosted authentication. This allows UniPile to reach your localhost development environment.

## Configuration Details

### 1. Tunnel Domain Setup
- **Main Domain**: `oneocrm.com` (points to localhost:8000)
- **Webhooks Subdomain**: `webhooks.oneocrm.com` (for UniPile webhooks)
- **Tenant Subdomains**: `{tenant}.oneocrm.com` (for multi-tenant access)

### 2. Backend Configuration

**Callback URLs** (automatically configured):
- Success: `https://oneocrm.com/api/v1/communications/auth/callback/success/`
- Failure: `https://oneocrm.com/api/v1/communications/auth/callback/failure/`

**Webhook URL** (configured in settings):
- Development: `https://webhooks.oneocrm.com/webhooks/unipile/`
- Production: `https://oneocrm.com/webhooks/unipile/`

**Frontend Redirect**:
- Success: `https://oneocrm.com/communications?success=true`
- Error: `https://oneocrm.com/communications?error=true`

### 3. ALLOWED_HOSTS Configuration
```python
ALLOWED_HOSTS = [
    'localhost', 
    '127.0.0.1',
    '.localhost',      # *.localhost for development
    'oneocrm.com',     # Cloudflare tunnel domain
    '.oneocrm.com',    # *.oneocrm.com for subdomains
]
```

### 4. CORS Configuration
```python
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://.*\.localhost:3000$",   # Local development
    r"^https://.*\.oneocrm\.com$",    # Tunnel subdomains
    r"^https://oneocrm\.com$",        # Tunnel main domain
]
```

## UniPile Hosted Auth Flow

### 1. User-Initiated Flow
1. User visits `https://demo.oneocrm.com/communications` (or any tenant subdomain)
2. Clicks "Connect Account" → selects provider (LinkedIn, Gmail, etc.)
3. Frontend calls `POST /api/v1/communications/request-hosted-auth/`

### 2. Backend Processing
1. Backend generates hosted auth URL from UniPile
2. Adds callback URLs pointing to `oneocrm.com`
3. Adds state parameter with connection ID for linking
4. Returns hosted auth URL to frontend

### 3. UniPile Authentication
1. User redirected to UniPile hosted auth (popup window)
2. User completes OAuth flow with provider (LinkedIn, Gmail, etc.)
3. UniPile redirects back to success/failure callback
4. UniPile sends webhook to `webhooks.oneocrm.com/webhooks/unipile/`

### 4. Callback Processing
1. Success callback updates connection status
2. Links UniPile account ID to user connection
3. Redirects user back to frontend with success parameters
4. Frontend shows success message and refreshes connection list

## Development URLs

**Frontend Access:**
- Main: `https://oneocrm.com/` (if Cloudflare configured for frontend)
- Local: `http://localhost:3000/` (with API calls to tunnel)

**Backend Access:**
- API: `https://oneocrm.com/api/v1/`
- Admin: `https://oneocrm.com/admin/`
- Health: `https://oneocrm.com/health/`

**Tenant Access:**
- Demo: `https://demo.oneocrm.com/`
- Test: `https://test.oneocrm.com/`

## Required Environment Variables

```env
# UniPile Configuration
UNIPILE_DSN=https://your-subdomain.unipile.com
UNIPILE_API_KEY=your-api-key

# Webhook Domain for callbacks
WEBHOOK_DOMAIN=oneocrm.com

# Optional: Additional allowed hosts
ALLOWED_HOSTS=additional-domain.com,another-domain.com
```

## Testing the Integration

### 1. Test API Accessibility
```bash
curl -H "Host: demo.oneocrm.com" https://oneocrm.com/api/v1/communications/connections/
# Should return: {"detail":"Authentication credentials were not provided."}
```

### 2. Test Webhook Endpoint
```bash
curl -X POST https://webhooks.oneocrm.com/webhooks/unipile/ \
  -H "Content-Type: application/json" \
  -d '{"event": "test", "account_id": "test123"}'
```

### 3. Test Frontend Access
- Visit: `https://demo.oneocrm.com/communications`
- Should load the communications page
- Click "Add Account" to test hosted auth flow

## Troubleshooting

### Common Issues:

1. **404 on API calls**: Check ALLOWED_HOSTS includes `oneocrm.com`
2. **CORS errors**: Verify CORS_ALLOWED_ORIGIN_REGEXES includes tunnel domain
3. **Webhook not received**: Check UniPile webhook URL configuration
4. **Callback not working**: Verify callback URLs use `https://oneocrm.com`

### Debug Commands:
```bash
# Check Django can serve tunnel domain
curl -H "Host: demo.oneocrm.com" http://localhost:8000/health/

# Check webhook routing
curl -X POST http://localhost:8000/webhooks/unipile/ \
  -H "Content-Type: application/json" \
  -d '{"event": "test"}'
```

## Production Deployment

When moving to production:
1. Update `WEBHOOK_DOMAIN` to your production domain
2. Configure CORS for production origins
3. Set `DEBUG=False`
4. Update UniPile webhook URL in their dashboard
5. Update callback URLs if using different domain

This configuration ensures seamless integration between your localhost development environment and UniPile's hosted authentication system via the Cloudflare tunnel.