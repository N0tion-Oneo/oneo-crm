# Debug Share Button 403 Error

## Quick Debug Steps

1. **Open the frontend application** in your browser (http://localhost:3000 or http://demo.localhost:3000)
2. **Login** with your credentials
3. **Open Developer Tools** (F12)
4. **Go to Console tab**
5. **Copy and paste the contents** of `debug_share_api.js` into the console
6. **Press Enter** to run the debug script

## What the Debug Script Tests

1. ✅ **Authentication**: Checks if JWT token is available
2. ✅ **Basic API Access**: Tests if user can access pipelines
3. ✅ **Record Access**: Tests if user can access records  
4. ✅ **Share Endpoint**: Tests both URL patterns for share link generation:
   - `/api/pipelines/{id}/records/{id}/generate_share_link/`
   - `/api/v1/pipelines/{id}/records/{id}/generate_share_link/`

## Expected Output

The script will show detailed information about each step and identify where the 403 error is coming from.

## Possible Issues & Solutions

### 1. Authentication Issues
- **Symptom**: No access token found
- **Solution**: Make sure you're logged in and check if JWT tokens are being stored correctly

### 2. Permission Issues  
- **Symptom**: 403 on pipelines or records API
- **Solution**: Check user permissions in the admin panel

### 3. Missing Endpoint
- **Symptom**: 404 on share link endpoint
- **Solution**: Verify the backend `generate_share_link` action is properly registered

### 4. CORS Issues
- **Symptom**: Network errors or CORS policy errors
- **Solution**: Check that both frontend (3000) and backend (8000) servers are running

## Alternative Manual Test

If the debug script doesn't work, try manually:

1. Open Network tab in Developer Tools
2. Try to generate a share link using the Share button
3. Look at the failed request details
4. Check the request headers, URL, and response

## Next Steps

Based on the debug output, we can:
- Fix authentication issues
- Add missing permissions
- Correct API endpoint URLs
- Resolve any backend configuration issues