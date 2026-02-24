# Testing the Debug Branch

## Automated Testing

This branch includes a GitHub Actions workflow that automatically tests server startup:

**Workflow:** `.github/workflows/test-server-startup-debug.yml`

### What It Tests

- ✅ Dependency installation from requirements.txt
- ✅ Critical imports (uvicorn, starlette, dotenv, etc.)
- ✅ Server startup with NO environment variables
- ✅ Server process stays alive (no exit code 1)
- ✅ Configuration display shows hardcoded fallbacks
- ✅ Tools register successfully
- ✅ Uvicorn starts and binds to port

### Python Versions Tested

- Python 3.9
- Python 3.10
- Python 3.11

### Viewing Test Results

1. Go to: https://github.com/Joru-chan/assistant/actions
2. Click on "Test Server Startup (Debug Branch)"
3. View the latest workflow run
4. Download server logs from artifacts for detailed debugging

### Manual Triggering

You can manually trigger the workflow:

1. Go to: https://github.com/Joru-chan/assistant/actions/workflows/test-server-startup-debug.yml
2. Click "Run workflow"
3. Select branch: `debug-hardcoded-secrets`
4. Optionally set wait time (default: 10 seconds)
5. Click "Run workflow"

## Local Testing

### Quick Test

```bash
# Clone the debug branch
git clone -b debug-hardcoded-secrets https://github.com/Joru-chan/assistant.git
cd assistant/vm_server

# Install dependencies
pip install -r requirements.txt

# Start server (no environment variables needed!)
python server.py
```

### Expected Output

```
============================================================
🚀 Lina Serendipity MCP Server Starting
============================================================
📋 Configuration:
  Server: 0.0.0.0:8000
  Log Level: info
  Service: mcp-server.service

🔑 Secrets Status:
  🔧 port: hardcoded
  🔧 notion_token: hardcoded
  🔧 pantry_db_id: hardcoded
  🔧 serendipity_webhook: hardcoded
  🔧 admin_token: hardcoded

⚠️  WARNING: Using hardcoded fallback values!
⚠️  Set environment variables for production use.
⚠️  See .env.example for configuration template.
============================================================

📦 Registering MCP tools...
✅ Tools registered successfully

🌐 Starting server on 0.0.0.0:8000
📍 MCP endpoint: http://0.0.0.0:8000/mcp
💚 Health check: Use the health_check tool via MCP

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Success Criteria

✅ Server starts without errors  
✅ No ModuleNotFoundError  
✅ No exit code 1  
✅ Process stays alive  
✅ Can stop with Ctrl+C

## Testing with Environment Variables

Create a `.env` file to test with real configuration:

```bash
# Copy example
cp .env.example .env

# Edit with real values
nano .env

# Start server
python server.py
```

Expected: Server shows `🌍 env` for configured variables instead of `🔧 hardcoded`

## Troubleshooting

### Server Won't Start

**Check dependencies:**
```bash
pip list | grep -E '(fastmcp|uvicorn|starlette|httpx|dotenv)'
```

**Test imports:**
```bash
python -c "import fastmcp; print('OK')"
python -c "import uvicorn; print('OK')"
python -c "from dotenv import load_dotenv; print('OK')"
```

### Port Already in Use

```bash
# Use different port
PORT=9000 python server.py
```

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## What This Branch Proves

### If Tests Pass ✅

**Conclusion:** The issue was environment-variable related

**Evidence:**
- Server starts with zero configuration
- All dependencies are properly declared
- FastMCP routing works correctly
- Tools register without errors

**Next Steps:**
- Set real environment variables on VM
- Deploy with proper configuration
- Exit code 1 failures were due to missing secrets

### If Tests Fail ❌

**Conclusion:** There's a code or dependency issue

**Evidence:**
- Import errors → Missing dependency
- Syntax errors → Code bug
- Runtime errors → Logic issue

**Next Steps:**
- Review error logs carefully
- Identify specific error
- Fix underlying issue
- Re-test

## Related Documentation

- **DEBUG_SETUP.md** - Complete debugging guide
- **.env.example** - Environment variable template
- **requirements.txt** - Fixed dependency list

## CI/CD Integration

This workflow runs automatically on:
- Every push to `debug-hardcoded-secrets` branch
- Manual workflow dispatch

Results are visible in the GitHub Actions tab and help identify:
1. Whether the server code is correct
2. Whether all dependencies are declared
3. Whether the server can start without configuration
4. What errors occur if startup fails

---

**Last Updated:** February 24, 2026  
**Branch:** debug-hardcoded-secrets  
**Workflow:** test-server-startup-debug.yml
