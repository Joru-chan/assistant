# Deployment Health Check Fix - Configuration Guide

## Overview

This document explains the deployment health check fixes and how to configure your secrets correctly.

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
- Used `VMMCPURL` which pointed to MCP endpoint

**After:**
- Direct HTTP GET request to `/health` endpoint
- URL validation before making requests
- Clear error messages with troubleshooting steps
- Uses `VM_HEALTH_URL` which points to health endpoint

## Required Configuration

### GitHub Secrets

You need to configure the following secrets in your repository settings:

#### VM_HEALTH_URL (Required - New/Updated)

This should point to your server's health endpoint:

```
http://your-vm-ip-or-hostname:8000/health
```

**Example:**
```
http://192.168.1.100:8000/health
```

or with domain:
```
https://mcp.yourdomain.com/health
```

#### VMMCPURL (Optional - Can be removed)

This is **no longer used** by the workflow. You can safely delete this secret.

If you need it for other purposes, it should point to your MCP endpoint:
```
http://your-vm-ip-or-hostname:8000/mcp/v1
```

### Other Required Secrets

These should already be configured:

- `VM_HOST` - Your VM hostname or IP
- `VM_USER` - SSH username for deployment
- `VM_SERVICE` - Systemd service name (e.g., `mcp-server`)
- `VMDEST_DIR` - Deployment directory on VM
- `VM_VENV_PY` - Path to Python in venv
- `VMSSHPRIVATE_KEY_B64` - Base64-encoded SSH private key

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
- ✅ No more "URL rejected" or "HTTP 400" errors

## Troubleshooting

### Issue: "URL rejected: Malformed input to a URL function"

**Cause:** `VM_HEALTH_URL` secret is not properly formatted.

**Solution:** 
- Ensure URL starts with `http://` or `https://`
- No spaces or special characters
- Valid hostname/IP and port

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

## Deployment Flow

After this fix, the deployment flow is:

1. **Code Sync** - rsync files to VM
2. **Dependencies** - Install/update Python packages
3. **Service Restart** - Restart systemd service
4. **Service Status Check** - Verify service is active
5. **URL Validation** - Check health URL is properly formatted
6. **Health Check** - GET request to /health endpoint (with retries)
7. **Success** ✅ or **Failure** ❌ with detailed diagnostics

## Migration Steps

If you're updating from the old configuration:

1. **Merge this PR**
2. **Update `VM_HEALTH_URL` secret:**
   - Go to: Settings → Secrets and variables → Actions
   - Update or create `VM_HEALTH_URL`
   - Set to: `http://your-vm:8000/health`
3. **Optional: Remove `VMMCPURL` secret** (no longer needed)
4. **Trigger a deployment** to test

## Questions?

If you encounter issues:

1. Check the deployment logs in GitHub Actions
2. Review this troubleshooting guide
3. SSH to VM and check service status/logs
4. Verify secret configuration

---

**Last Updated:** 2026-02-23  
**PR:** #8  
**Related Files:**
- `vm_server/server.py`
- `.github/workflows/deploy.yml`
