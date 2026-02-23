# Deployment Health Check Fix - Configuration Guide

## Overview

This document explains the deployment health check fixes and how they work with your existing configuration.

## What Was Fixed

### 1. Health Endpoint Registration (server.py)

**Before:**
```python
app = mcp.http_app(stateless_http=True)

def _register_health_route(server: FastMCP) -> bool:
    app = getattr(server, "app", None)  # ❌ Returns None - app never attached to server
    if app is None:
        return False
    # This code never runs!
```

**After:**
```python
app = mcp.http_app(stateless_http=True)

@app.get("/health")
async def health() -> dict:
    """Health check endpoint for monitoring."""
    return {"ok": True, "status": "healthy"}
```

### 2. Workflow Health Check Logic (deploy.yml)

**Before:**
- Tried to call non-existent MCP tool `health_check` via JSON-RPC
- No URL validation
- Poor error messages

**After:**
- Direct HTTP GET request to `/health` endpoint
- URL validation before making requests
- Constructs health URL from existing `VMMCPURL` secret
- Clear error messages with troubleshooting steps

## How It Works

### URL Construction

The workflow now automatically constructs the health check URL from your existing `VMMCPURL` secret:

1. Takes the `VMMCPURL` value (e.g., `http://192.168.1.100:8000`)
2. Removes any trailing slashes
3. Appends `/health` to create the health check URL
4. Validates the URL format before use

**Example:**
- `VMMCPURL` = `http://192.168.1.100:8000` → Health URL = `http://192.168.1.100:8000/health`
- `VMMCPURL` = `http://192.168.1.100:8000/` → Health URL = `http://192.168.1.100:8000/health`
- `VMMCPURL` = `https://mcp.example.com` → Health URL = `https://mcp.example.com/health`

### No Configuration Changes Required

✅ **You don't need to update any secrets!** The workflow uses your existing `VMMCPURL` configuration.

## Required Secrets

Your existing secrets should already be configured. For reference:

- `VMMCPURL` - Your MCP server URL (e.g., `http://your-vm:8000`)
- `VM_HOST` - Your VM hostname or IP
- `VM_USER` - SSH username for deployment
- `VM_SERVICE` - Systemd service name (e.g., `mcp-server`)
- `VMDEST_DIR` - Deployment directory on VM
- `VM_VENV_PY` - Path to Python in venv
- `VMSSHPRIVATE_KEY_B64` - Base64-encoded SSH private key

### Verify Your VMMCPURL Secret

Make sure your `VMMCPURL` secret is in one of these formats:

✅ `http://hostname:8000`  
✅ `http://192.168.1.100:8000`  
✅ `https://mcp.yourdomain.com`  
✅ `http://hostname:8000/` (trailing slash is OK, will be removed)  

❌ `hostname:8000` (missing http://)  
❌ `192.168.1.100` (missing http:// and port)  

## Testing the Fix

### 1. Test Health Endpoint Locally

SSH into your VM and test:

```bash
# Check if service is running
sudo systemctl status mcp-server  # or your service name

# Test health endpoint
curl http://localhost:8000/health

# Expected response:
# {"ok":true,"status":"healthy"}
```

### 2. Test from GitHub Actions

After merging this PR, trigger a deployment:

1. Push a change to `vm_server/` directory, or
2. Manually trigger the workflow from Actions tab

The workflow should now:
- ✅ Complete successfully
- ✅ Show "✅ HTTP health check successful (HTTP 200)"
- ✅ Display the constructed health URL
- ✅ No more "URL rejected" or "HTTP 400" errors

## Troubleshooting

### Issue: "VMMCPURL secret is empty or not set"

**Cause:** The secret is not configured in repository settings.

**Solution:**
```
1. Go to: Settings → Secrets and variables → Actions
2. Add or update VMMCPURL
3. Set to: http://your-vm-ip:8000
```

### Issue: "Invalid URL format: [URL]"

**Cause:** `VMMCPURL` doesn't start with `http://` or `https://`.

**Solution:**
- Update `VMMCPURL` to include the protocol
- Example: Change `192.168.1.100:8000` to `http://192.168.1.100:8000`

### Issue: "URL rejected: Malformed input to a URL function"

**Cause:** URL contains invalid characters or formatting.

**Solution:**
- Check for spaces or special characters in VMMCPURL
- Ensure proper URL encoding
- Verify hostname/IP is valid

### Issue: "HTTP health check failed (HTTP 000)"

**Cause:** Server is not reachable or not running.

**Solution:**
```bash
# On your VM:
# 1. Check service status
sudo systemctl status mcp-server

# 2. Check if port is listening
sudo netstat -tlnp | grep :8000

# 3. Check firewall
sudo ufw status
sudo ufw allow 8000/tcp  # if needed

# 4. View logs
sudo journalctl -u mcp-server -n 50 --no-pager
```

### Issue: "Could not resolve host"

**Cause:** Hostname in VMMCPURL cannot be resolved.

**Solution:**
- Verify the hostname is correct
- Consider using IP address instead
- Check DNS configuration

### Issue: "HTTP 404 Not Found"

**Cause:** Health endpoint is not registered (old version of server.py).

**Solution:**
- Ensure you've merged this PR
- Redeploy to update server.py
- Restart the service

### Issue: "HTTP 500 Internal Server Error"

**Cause:** Application error in health endpoint.

**Solution:**
```bash
# Check application logs
sudo journalctl -u mcp-server -n 50 --no-pager

# Look for Python exceptions or errors
```

## Health Endpoint Details

### Endpoint: GET /health

**URL:** `http://your-server:8000/health`

**Response (Success):**
```json
{
  "ok": true,
  "status": "healthy"
}
```

**Status Code:** 200 OK

**Headers:**
- `Content-Type: application/json`

### Usage Examples

#### curl
```bash
curl http://localhost:8000/health
```

#### Python
```python
import requests
response = requests.get("http://localhost:8000/health")
print(response.json())
# {'ok': True, 'status': 'healthy'}
```

#### Monitoring Tools

You can use this endpoint with monitoring services like:
- UptimeRobot
- Pingdom
- StatusCake
- Custom monitoring scripts

Set the monitoring URL to: `http://your-vm:8000/health`

## Deployment Flow

After this fix, the deployment flow is:

1. **Code Sync** - rsync files to VM
2. **Dependencies** - Install/update Python packages
3. **Service Restart** - Restart systemd service
4. **Service Status Check** - Verify service is active
5. **URL Construction** - Build health URL from VMMCPURL
6. **URL Validation** - Check health URL is properly formatted
7. **Health Check** - GET request to /health endpoint (with retries)
8. **Success** ✅ or **Failure** ❌ with detailed diagnostics

## What Changed vs Previous Documentation

**Previous version** (now outdated):
- Required creating a new `VM_HEALTH_URL` secret
- Two separate secrets to manage

**Current version** (this fix):
- ✅ Uses existing `VMMCPURL` secret
- ✅ Automatically constructs health URL
- ✅ No secret changes required
- ✅ Simpler configuration

## Testing Checklist

Before merging, verify:

- [ ] `VMMCPURL` secret exists and is properly formatted
- [ ] `VMMCPURL` starts with `http://` or `https://`
- [ ] Server is accessible at the URL in `VMMCPURL`
- [ ] `/health` endpoint responds with 200 OK locally

After merging:

- [ ] Deployment completes successfully
- [ ] Health check passes
- [ ] Workflow logs show constructed health URL
- [ ] No URL validation errors

## Questions?

If you encounter issues:

1. Check the deployment logs in GitHub Actions
2. Review this troubleshooting guide
3. SSH to VM and check service status/logs
4. Verify `VMMCPURL` secret configuration

---

**Last Updated:** 2026-02-23  
**PR:** #8  
**Related Files:**
- `vm_server/server.py`
- `.github/workflows/deploy.yml`
