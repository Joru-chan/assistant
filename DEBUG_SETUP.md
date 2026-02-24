# Debug Setup with Hardcoded Fallbacks

## 🎯 Purpose

This branch (`debug-hardcoded-secrets`) eliminates ALL environment variable configuration issues by providing **hardcoded fallback values** for every environment variable the server uses.

**Goal:** Determine if exit code 1 failures are caused by:
- ✅ Missing/incorrect environment variables → Fixed by this branch
- ❌ Actual code bugs, import errors, or runtime issues → Will still fail

---

## 🔧 Changes Made

### 1. **Removed NUCLEAR OPTION Debug Mode** ✅

**Before:**
```python
# Responded to ALL requests with 200 OK, bypassing normal routing
async def respond_to_everything(scope, receive, send):
    # ... debug response ...
app = respond_to_everything  # Replaced normal routing
```

**After:**
```python
# Normal FastMCP routing restored
mcp = FastMCP("Lina Serendipity MCP Server")
register_tools(mcp)
mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
```

**Impact:** Server now uses proper FastMCP routing and tool registration

---

### 2. **Fixed requirements.txt** ✅

**CRITICAL DEPENDENCIES ADDED:**

```txt
# BEFORE (incomplete - caused ModuleNotFoundError!)
fastmcp
httpx
aiofiles

# AFTER (complete with versions)
fastmcp>=3.0.0
uvicorn[standard]>=0.30.0    # CRITICAL - needed to run server!
starlette>=0.37.0            # Used for responses, was missing!
httpx>=0.27.0
aiofiles>=23.0.0
python-dotenv>=1.0.0         # Imported but was missing!
```

**Why Critical:** Missing `uvicorn`, `starlette`, and `python-dotenv` would cause:
```
ModuleNotFoundError: No module named 'uvicorn'
ModuleNotFoundError: No module named 'starlette'
ModuleNotFoundError: No module named 'dotenv'
→ Exit code: 1
```

---

### 3. **Added Hardcoded Fallbacks in server.py** ✅

**New `get_config()` function:**
```python
def get_config():
    """Get server configuration with hardcoded fallbacks for debugging."""
    return {
        # Server configuration
        'port': int(os.getenv('PORT', '8000')),
        'host': os.getenv('HOST', '0.0.0.0'),
        'log_level': os.getenv('LOG_LEVEL', 'info'),
        
        # Notion integration (HARDCODED FALLBACKS)
        'notion_token': os.getenv('NOTION_TOKEN', 'debug-notion-token-12345'),
        'pantry_db_id': os.getenv('PANTRY_DB_ID', 'debug-pantry-database-id-67890'),
        
        # Serendipity (HARDCODED FALLBACK)
        'serendipity_webhook_url': os.getenv(
            'SERENDIPITY_EVENT_WEBHOOK_URL',
            'http://localhost:5678/webhook/debug-serendipity'
        ),
        
        # Admin (HARDCODED FALLBACK)
        'admin_token': os.getenv('ADMIN_TOKEN', 'debug-admin-token-abcdef'),
        
        # Pantry property mappings (all defaults)
        'pantry_props': { ... }
    }
```

**Startup Display:**
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
```

---

### 4. **Updated All Tool Files** ✅

#### **notion_editor.py:**
```python
# HARDCODED FALLBACK
DEBUG_NOTION_TOKEN = "debug-notion-token-12345"

def _get_notion_token() -> str:
    return os.getenv("NOTION_TOKEN", DEBUG_NOTION_TOKEN)

# Tools detect debug mode:
if token == DEBUG_NOTION_TOKEN:
    return {
        "summary": "Notion search unavailable in debug mode.",
        "result": {"items": [], "debug_mode": True},
        "errors": ["⚠️  Using DEBUG Notion token - set NOTION_TOKEN for real API"],
    }
```

#### **serendipity.py:**
```python
# HARDCODED FALLBACK
DEBUG_SERENDIPITY_WEBHOOK = "http://localhost:5678/webhook/debug-serendipity"

def _get_serendipity_webhook() -> str:
    return os.getenv("SERENDIPITY_EVENT_WEBHOOK_URL", DEBUG_SERENDIPITY_WEBHOOK)

# Tool detects debug mode:
if webhook_url == DEBUG_SERENDIPITY_WEBHOOK:
    return {
        "ok": False,
        "debug_mode": True,
        "error": "⚠️  Using DEBUG webhook URL",
        "would_have_sent": { ... }  # Shows what would be sent
    }
```

#### **admin.py:**
```python
# HARDCODED FALLBACKS
DEBUG_ADMIN_TOKEN = "debug-admin-token-abcdef"
DEBUG_SERVICE_NAME = "mcp-server.service"
DEBUG_PORT = "8000"

def _get_admin_token() -> str:
    return os.getenv("ADMIN_TOKEN", DEBUG_ADMIN_TOKEN)

# Authorization shows warnings when using debug token
```

---

### 5. **Created .env.example** ✅

Complete documentation of all environment variables:
- Server configuration (HOST, PORT, LOG_LEVEL)
- MCP configuration (MCP_SERVER_NAME, MCP_SERVICE_NAME)
- Notion integration (NOTION_TOKEN, PANTRY_DB_ID)
- All 13 PANTRY_PROP_* variables
- Serendipity webhook (SERENDIPITY_EVENT_WEBHOOK_URL)
- Admin authentication (ADMIN_TOKEN)

**Location:** `vm_server/.env.example`

---

## 📊 Hardcoded Fallback Values

### **Security Tokens (For Debugging ONLY!)**

| Variable | Hardcoded Fallback | Real Value Needed? |
|----------|-------------------|-------------------|
| `NOTION_TOKEN` | `debug-notion-token-12345` | ✅ Yes, for Notion API |
| `PANTRY_DB_ID` | `debug-pantry-database-id-67890` | ✅ Yes, for pantry tool |
| `SERENDIPITY_EVENT_WEBHOOK_URL` | `http://localhost:5678/webhook/debug-serendipity` | ✅ Yes, for event logging |
| `ADMIN_TOKEN` | `debug-admin-token-abcdef` | ✅ Yes, for admin operations |

### **Server Configuration**

| Variable | Hardcoded Fallback | Real Value Needed? |
|----------|-------------------|-------------------|
| `PORT` | `8000` | ⚠️  Optional, default OK |
| `HOST` | `0.0.0.0` | ⚠️  Optional, default OK |
| `LOG_LEVEL` | `info` | ⚠️  Optional, default OK |
| `MCP_SERVER_NAME` | `Lina Serendipity MCP Server` | ⚠️  Optional, default OK |
| `MCP_SERVICE_NAME` | `mcp-server.service` | ⚠️  Optional, default OK |

### **Pantry Property Mappings**

All 13 `PANTRY_PROP_*` variables have defaults matching standard Notion property names.

---

## 🧪 Testing Instructions

### **Test 1: Server Starts with ZERO Environment Variables**

```bash
# Checkout the debug branch
git checkout debug-hardcoded-secrets

# Install dependencies
cd vm_server
pip install -r requirements.txt

# Run server with NO .env file and NO environment variables
python server.py
```

**Expected Output:**
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

**✅ Success Criteria:**
- Server starts without errors
- No ModuleNotFoundError
- No exit code 1
- Uvicorn shows "running on http://0.0.0.0:8000"
- Can press Ctrl+C to stop cleanly

**❌ If It Fails:**
- Check the error message carefully
- Look for import errors → Dependency issue
- Look for syntax errors → Code issue
- Look for runtime errors → Logic issue
- **The failure is NOT environment variable related!**

---

### **Test 2: Verify Tools Work in Debug Mode**

```bash
# Start the server (in another terminal)
python server.py

# In another terminal, test MCP endpoints
# (You'll need an MCP client or curl with JSON-RPC)

# Example: Call a tool that uses environment variables
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "generate_serendipity_nudge",
      "arguments": {"mood": "curious"}
    },
    "id": 1
  }'
```

**Expected:** Tool returns result (even with debug values)

---

### **Test 3: Test with Environment Variables**

```bash
# Create .env file from example
cp .env.example .env

# Edit .env and set real values
nano .env

# Run server - should use env vars instead of hardcoded
PORT=9000 ADMIN_TOKEN=my-real-token python server.py
```

**Expected Output:**
```
🔑 Secrets Status:
  🌍 port: env              ← From environment
  🔧 notion_token: hardcoded  ← Still hardcoded (not in env)
  🔧 pantry_db_id: hardcoded
  🔧 serendipity_webhook: hardcoded
  🌍 admin_token: env        ← From environment
```

**✅ Success Criteria:**
- Variables set in environment show `🌍 env`
- Variables not set show `🔧 hardcoded`
- Environment variables properly override hardcoded values

---

## 🎯 Expected Outcomes

### **Scenario 1: All Tests Pass** ✅

**Conclusion:**
- ✅ Server code is correct
- ✅ Dependencies are properly declared
- ✅ FastMCP integration works
- ✅ Tools register correctly
- ✅ Normal routing functions properly
- ✅ Server can start and run successfully

**Next Steps:**
- Exit code 1 failures on VM are environment-specific
- Check: systemd service configuration
- Check: VM firewall/port settings
- Check: File permissions on VM
- Check: Python version on VM
- Check: Actual environment variables on VM

### **Scenario 2: Import Errors** ❌

**Example:**
```
ModuleNotFoundError: No module named 'XXX'
```

**Conclusion:**
- ❌ Missing dependency in requirements.txt
- ❌ Need to add to requirements.txt and retry

**Action:**
- Identify missing module
- Add to requirements.txt
- Commit and test again

### **Scenario 3: Runtime Errors** ❌

**Example:**
```
AttributeError: 'FastMCP' object has no attribute 'XXX'
TypeError: XXX() missing required argument
```

**Conclusion:**
- ❌ Code bug or API incompatibility
- ❌ FastMCP version issue
- ❌ Logic error in code

**Action:**
- Review error traceback
- Fix code issue
- Test fix

### **Scenario 4: Port Binding Error** ❌

**Example:**
```
OSError: [Errno 98] Address already in use
```

**Conclusion:**
- ❌ Port 8000 already in use
- ❌ Environment-specific issue

**Action:**
- Change PORT environment variable
- Or stop conflicting service
- Or use different port

---

## 🔐 Security Warning

### **⚠️ HARDCODED VALUES ARE FOR DEBUGGING ONLY!**

The following hardcoded values are **NOT SECURE** for production:

```python
# DEBUG VALUES (DO NOT USE IN PRODUCTION!)
NOTION_TOKEN = "debug-notion-token-12345"
PANTRY_DB_ID = "debug-pantry-database-id-67890"
SERENDIPITY_EVENT_WEBHOOK_URL = "http://localhost:5678/webhook/debug-serendipity"
ADMIN_TOKEN = "debug-admin-token-abcdef"
```

**In Production:**
- ❌ Never use these debug values
- ✅ Always set real secrets via environment variables
- ✅ Use `.env` file or systemd environment
- ✅ Rotate tokens regularly
- ✅ Use strong, random tokens for ADMIN_TOKEN

---

## 🛠️ Tool Behavior in Debug Mode

### **Notion Tools** (notion_editor.py)

When `NOTION_TOKEN` is not set (using debug value):
```json
{
  "summary": "Notion search unavailable in debug mode.",
  "result": {
    "items": [],
    "debug_mode": true
  },
  "errors": ["⚠️  Using DEBUG Notion token - set NOTION_TOKEN for real API"],
  "next_actions": ["Set NOTION_TOKEN environment variable to enable Notion integration."]
}
```

**Impact:** Tools return helpful message instead of crashing

### **Serendipity Tool** (serendipity.py)

When `SERENDIPITY_EVENT_WEBHOOK_URL` is not set:
```json
{
  "ok": false,
  "debug_mode": true,
  "error": "⚠️  Using DEBUG webhook URL",
  "would_have_sent": {
    "event_timestamp": "...",
    "mood_input": "...",
    ...
  }
}
```

**Impact:** Shows what would have been sent without actually calling webhook

### **Admin Tools** (admin.py)

When `ADMIN_TOKEN` is not set:
```json
{
  "summary": "Service mcp-server.service status: active.",
  "result": {
    "debug_mode": true,
    "warning": "Using debug admin token",
    ...
  },
  "errors": ["⚠️  Using DEBUG admin token - set ADMIN_TOKEN for production"]
}
```

**Impact:** Tools still work but indicate debug mode

### **Other Tools**

- **weather.py:** No secrets needed, works fully
- **mood.py, hello.py, basic.py, system_overview.py:** No secrets needed
- **health.py:** Works without secrets
- **receipt_photo_pantry_inventory.py:** Uses NOTION_TOKEN + PANTRY_DB_ID (returns preview in debug mode)

---

## 🔍 Troubleshooting

### **Problem: Server Won't Start**

**Check:**
1. Are dependencies installed?
   ```bash
   pip install -r requirements.txt
   ```

2. Any import errors?
   ```bash
   python -c "from fastmcp import FastMCP; print('FastMCP OK')"
   python -c "import uvicorn; print('uvicorn OK')"
   python -c "from starlette.responses import JSONResponse; print('starlette OK')"
   ```

3. Any syntax errors?
   ```bash
   python -m py_compile server.py
   ```

4. Check Python version:
   ```bash
   python --version  # Should be 3.10+
   ```

### **Problem: Port Already in Use**

```bash
# Check what's on port 8000
sudo lsof -i :8000
sudo netstat -tlnp | grep :8000

# Use a different port
PORT=9000 python server.py
```

### **Problem: Tools Don't Work**

**This is EXPECTED with debug values!**

The hardcoded secrets are fake and won't actually connect to:
- Notion API (will return 401 unauthorized)
- n8n webhooks (will fail to connect)

**But the server should still START and REGISTER tools successfully.**

---

## 📈 What This Branch Tests

### **✅ Tests That WILL Work:**

1. **Server startup** - Does the server start without crashing?
2. **Import resolution** - Are all dependencies importable?
3. **Tool registration** - Do all tools register without errors?
4. **Configuration loading** - Does get_config() work?
5. **FastMCP integration** - Does mcp.run() execute?
6. **Port binding** - Can the server bind to port 8000?

### **❌ Tests That WON'T Work (Expected):**

1. **Notion API calls** - Debug token won't authenticate
2. **Webhook calls** - Debug URL won't receive events
3. **Admin systemctl commands** - Won't have real service
4. **Database queries** - Debug database ID doesn't exist

**This is OK!** We're testing **startup**, not **functionality**.

---

## 🚀 Deployment Testing

### **On the VM:**

```bash
# SSH to your VM
ssh ubuntu@your-vm-ip

# Clone this branch
git clone -b debug-hardcoded-secrets https://github.com/Joru-chan/assistant.git debug-test
cd debug-test/vm_server

# Install dependencies
pip install -r requirements.txt

# Run server
python server.py

# Watch for:
# ✅ Server starts successfully
# ✅ No ModuleNotFoundError
# ✅ No exit code 1
# ✅ Uvicorn running message appears
# ✅ Can stop with Ctrl+C
```

### **Via Systemd:**

```bash
# Update service to use debug branch
sudo systemctl stop mcp-server.service

# Update code to debug branch
cd /path/to/mcp/server
git fetch origin
git checkout debug-hardcoded-secrets
pip install -r requirements.txt

# Start service
sudo systemctl start mcp-server.service

# Check status
sudo systemctl status mcp-server.service

# If it shows "active (running)" → SUCCESS!
# If it shows "failed" with exit code 1 → Check logs:
sudo journalctl -u mcp-server.service -n 100
```

---

## 📝 Next Steps After Testing

### **If Tests Pass** ✅

**Conclusion:** Exit code 1 failures were environment variable related

**Action Plan:**
1. Set real environment variables on VM
2. Create /path/to/mcp/server/.env file with real values
3. Update systemd service to load .env file
4. Switch back to main branch
5. Deploy with proper configuration

### **If Tests Fail** ❌

**Conclusion:** Exit code 1 failures are code/dependency related

**Action Plan:**
1. Review error logs carefully
2. Identify specific error (import, syntax, runtime)
3. Fix the underlying issue
4. Commit fix to this branch
5. Re-test until server starts
6. Merge fix to main

---

## 🔄 Reverting to Production

Once debugging is complete:

```bash
# Switch back to main branch
git checkout main

# Set REAL environment variables
nano /path/to/mcp/server/.env

# Add:
# NOTION_TOKEN=secret_your_real_token
# PANTRY_DB_ID=your_real_database_id
# SERENDIPITY_EVENT_WEBHOOK_URL=https://your-n8n-instance/webhook/serendipity
# ADMIN_TOKEN=$(openssl rand -hex 32)

# Test with real values
python server.py
```

---

## 📚 Related Files

- **vm_server/server.py** - Main server with hardcoded fallbacks
- **vm_server/requirements.txt** - Fixed dependencies
- **vm_server/.env.example** - Environment variable template
- **vm_server/tools/notion_editor.py** - Updated with fallbacks
- **vm_server/tools/serendipity.py** - Updated with fallbacks
- **vm_server/tools/admin.py** - Updated with fallbacks
- **.github/workflows/test-mcp-server.yml** - CI/CD testing workflow

---

## ✅ Success Indicators

### **Server Starts Successfully:**
- ✅ No import errors
- ✅ No syntax errors  
- ✅ No runtime errors
- ✅ Uvicorn starts
- ✅ Server listens on port 8000
- ✅ Process stays alive
- ✅ Can stop cleanly with Ctrl+C

### **Startup Logs Show:**
- ✅ Configuration display with all fallbacks
- ✅ "Tools registered successfully"
- ✅ "Starting server on 0.0.0.0:8000"
- ✅ "Uvicorn running on http://0.0.0.0:8000"
- ⚠️ Warnings about hardcoded values (expected!)

### **Tool Responses Show:**
- ✅ Debug mode indicators in responses
- ✅ Helpful error messages
- ✅ No crashes or stack traces
- ✅ Tools return structured responses

---

## 🎓 Learning Outcomes

This debug setup helps answer:

1. **Does the server code work?**
   - If yes → Environment issue on VM
   - If no → Code/dependency issue

2. **Are all dependencies declared?**
   - If server starts → Yes, requirements.txt is complete
   - If import errors → No, add missing dependencies

3. **Does FastMCP routing work?**
   - If tools are accessible → Yes, routing works
   - If 404 errors → No, routing issue

4. **Is the problem environment-specific?**
   - If works locally but fails on VM → Yes, VM environment issue
   - If fails everywhere → No, code issue

---

**Last Updated:** February 24, 2026  
**Branch:** debug-hardcoded-secrets  
**Status:** Ready for testing
