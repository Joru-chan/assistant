# Location Tracking Setup Guide

A comprehensive guide to setting up location tracking with OwnTracks, n8n, and the Lina Serendipity MCP Server.

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Prerequisites](#prerequisites)
- [Part 1: MCP Server Setup](#part-1-mcp-server-setup)
- [Part 2: n8n Installation & Configuration](#part-2-n8n-installation--configuration)
- [Part 3: OwnTracks Integration](#part-3-owntracks-integration)
- [Part 4: Notion Integration (Optional)](#part-4-notion-integration-optional)
- [Part 5: Testing & Verification](#part-5-testing--verification)
- [Part 6: Maintenance & Troubleshooting](#part-6-maintenance--troubleshooting)
- [Advanced Configuration](#advanced-configuration)

---

## Overview

This system tracks your location via the **OwnTracks** mobile app and processes it through an automated pipeline:

```
OwnTracks App → n8n Webhook → Filter & Transform → MCP Server → Notion/Storage
                                    ↓
                            Context-aware processing
                            (mood, serendipity nudges)
```

**Key Features:**
- Privacy-first: You control all the data
- Smart filtering: Only meaningful location changes are processed
- Context integration: Location data enriches mood tracking and serendipity nudges
- Self-hosted: Runs on your own infrastructure

---

## System Architecture

### Components

1. **OwnTracks Mobile App** (iOS/Android)
   - Tracks your GPS location
   - Sends updates via HTTP POST to n8n webhook

2. **n8n Automation Server**
   - Receives location data from OwnTracks
   - Filters based on accuracy and distance
   - Forwards to MCP server or other destinations

3. **Lina Serendipity MCP Server** (This repository)
   - FastMCP-based Python server
   - Processes location data
   - Integrates with mood tracking and serendipity system
   - Stores data in Notion (optional)

4. **Notion** (Optional)
   - Acts as your personal database
   - Stores location history, mood logs, serendipity events

### Data Flow

```
┌─────────────────┐
│  OwnTracks App  │
│   (Your Phone)  │
└────────┬────────┘
         │ POST /webhook/owntracks
         ↓
┌─────────────────┐
│   n8n Server    │
│  (Your VM/VPS)  │
│                 │
│ 1. Validate GPS │
│ 2. Check accuracy (>50m? skip) │
│ 3. Check distance (>20m? send) │
└────────┬────────┘
         │ HTTP POST
         ↓
┌─────────────────┐
│   MCP Server    │
│  (Your VM/VPS)  │
│                 │
│ 1. Process location │
│ 2. Update context   │
│ 3. Log to Notion    │
└─────────────────┘
```

---

## Prerequisites

### Required Software

#### On Your Development Machine (optional)
- **Python 3.11+**: `python3 --version`
- **uv** (Python package installer): [Install instructions](https://docs.astral.sh/uv/getting-started/installation/)
- **Git**: `git --version`

#### On Your Server (VM/VPS)
- **Ubuntu 20.04+** or similar Linux distribution
- **Python 3.11+** (installation instructions below)
- **Node.js 18+** (for n8n)
- **npm or pnpm** (Node package manager)
- **systemd** (for service management)
- **sudo access** (for service setup)

##### Python 3.11 Installation

**For Ubuntu 20.04 users:**

> **Note:** Ubuntu 20.04 requires the deadsnakes PPA for Python 3.11, as it's not available in the default repositories.

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-distutils
```

**For Ubuntu 22.04+ users:**

```bash
sudo apt install -y python3.11 python3.11-venv
```

#### On Your Phone
- **OwnTracks app**: [iOS](https://apps.apple.com/app/owntracks/id692424691) | [Android](https://play.google.com/store/apps/details?id=org.owntracks.android)

### Required Accounts & Keys
- **GitHub Account**: For repository access
- **Notion Account** (optional): For data storage
  - Create a Notion integration: https://www.notion.so/my-integrations
  - Get your integration token
- **Domain/DDNS** (recommended): For webhook URLs (e.g., `your-domain.com`)

### Server Requirements
- **1-2 GB RAM**: Minimum for n8n + MCP server
- **10 GB disk space**: For applications and data
- **Open ports**: 
  - `5678` (n8n web interface)
  - `8000` (MCP server)
  - `80/443` (if using reverse proxy)

---

## Part 1: MCP Server Setup

### 1.1 Install Python and uv

On your server (SSH into your VM/VPS):

```bash
# Install Python 3.11+ if not present
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install uv (recommended Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Reload your shell
source $HOME/.cargo/env

# Verify installation
uv --version
```

### 1.2 Clone the Repository

```bash
# Create a directory for the MCP server
mkdir -p ~/mcp-server-template
cd ~/mcp-server-template

# Clone this repository
git clone https://github.com/Joru-chan/assistant.git src
cd src
```

### 1.3 Create Virtual Environment & Install Dependencies

```bash
# Create virtual environment with uv
uv venv --python 3.11 .venv

# Activate the virtual environment
source .venv/bin/activate

# Install dependencies
cd vm_server
uv pip install -r requirements.txt
```

**Expected output:**
```
Resolved X packages in Xms
Installed X packages in Xms
```

### 1.4 Configure Environment Variables

Create a `.env` file in the `vm_server/` directory:

```bash
cd ~/mcp-server-template/src/vm_server
nano .env
```

Add the following configuration:

```bash
# Server Configuration
PORT=8000

# Notion Integration (Optional)
NOTION_TOKEN=your_notion_integration_token_here
PANTRY_DB_ID=your_pantry_database_id_here
TOOL_REQUESTS_DB_ID=your_tool_requests_database_id_here

# Webhook URLs (will be set after n8n setup)
MOOD_MEMORY_WEBHOOK_URL=http://localhost:5678/webhook/mood-pulse
SERENDIPITY_EVENT_WEBHOOK_URL=http://localhost:5678/webhook/serendipity-event
LOCATION_TRACKING_WEBHOOK_URL=http://localhost:5678/webhook/location-update

# Location Tracking Settings
MIN_ACCURACY=50          # Minimum GPS accuracy in meters
MIN_DISTANCE=20          # Minimum distance change in meters
```

**Security Note:** Never commit the `.env` file to version control. It's already in `.gitignore`.

### 1.5 Test the MCP Server

Run the server manually to verify it works:

```bash
cd ~/mcp-server-template/src/vm_server
source ../.venv/bin/activate
python3 server.py
```

**Expected output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

Test the health endpoint (in another terminal):

```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{"ok": true}
```

Press `Ctrl+C` to stop the server. We'll set it up as a systemd service next.

### 1.6 Create systemd Service

Create a service file for automatic startup:

```bash
sudo nano /etc/systemd/system/mcp-server.service
```

Add the following content:

```ini
[Unit]
Description=Lina Serendipity MCP Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/mcp-server-template/src/vm_server
Environment="PATH=/home/ubuntu/mcp-server-template/src/.venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/home/ubuntu/mcp-server-template/src/vm_server/.env
ExecStart=/home/ubuntu/mcp-server-template/src/.venv/bin/python3 server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Adjust paths** if you installed in a different location or use a different user than `ubuntu`.

Enable and start the service:

```bash
# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable mcp-server.service

# Start the service
sudo systemctl start mcp-server.service

# Check status
sudo systemctl status mcp-server.service
```

**Expected output:**
```
● mcp-server.service - Lina Serendipity MCP Server
     Loaded: loaded (/etc/systemd/system/mcp-server.service; enabled)
     Active: active (running) since Mon 2024-02-19 10:00:00 UTC; 5s ago
```

View logs:

```bash
# Follow logs in real-time
sudo journalctl -u mcp-server.service -f

# View last 50 lines
sudo journalctl -u mcp-server.service -n 50
```

---

## Part 2: n8n Installation & Configuration

n8n is an automation server that will receive location data from OwnTracks, filter it, and forward it to the MCP server.

### 2.1 Install Node.js

```bash
# Install Node.js 18.x
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installation
node --version  # Should be v18.x or higher
npm --version
```

### 2.2 Install n8n

```bash
# Install n8n globally
sudo npm install -g n8n

# Verify installation
n8n --version
```

### 2.3 Create n8n systemd Service

```bash
sudo nano /etc/systemd/system/n8n.service
```

Add the following content:

```ini
[Unit]
Description=n8n Workflow Automation
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu
Environment="N8N_PORT=5678"
Environment="N8N_PROTOCOL=http"
Environment="N8N_HOST=0.0.0.0"
Environment="WEBHOOK_URL=http://your-domain.com"
Environment="N8N_BASIC_AUTH_ACTIVE=true"
Environment="N8N_BASIC_AUTH_USER=admin"
Environment="N8N_BASIC_AUTH_PASSWORD=your-secure-password-here"
ExecStart=/usr/bin/n8n start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Important:** Change the following:
- `WEBHOOK_URL`: Your public domain or IP (e.g., `http://mcp-lina.duckdns.org`)
- `N8N_BASIC_AUTH_PASSWORD`: Set a strong password

Enable and start n8n:

```bash
sudo systemctl daemon-reload
sudo systemctl enable n8n.service
sudo systemctl start n8n.service
sudo systemctl status n8n.service
```

Access n8n web interface:
```
http://your-server-ip:5678
```

Log in with the credentials you set in the service file.

### 2.4 Generate n8n API Key

The automated deployment workflow needs an API key to create workflows programmatically.

1. Open n8n in your browser: `http://your-server-ip:5678`
2. Go to **Settings** (gear icon in the sidebar)
3. Click **API**
4. Click **Create an API Key**
5. Give it a name: "GitHub Actions Deployment"
6. Copy the generated API key (you'll need it later)

### 2.5 Configure GitHub Secrets

For automated deployment via GitHub Actions, add these secrets to your repository:

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

| Secret Name | Value | Description |
|------------|-------|-------------|
| `N8N_API_KEY` | `your_n8n_api_key` | API key from step 2.4 |
| `VM_HOST` | `your-server-ip` | Server IP or domain |
| `VM_USER` | `ubuntu` | SSH username |
| `VMSSHPRIVATE_KEY_B64` | `base64_encoded_ssh_key` | Your SSH private key (base64 encoded) |

To encode your SSH key:
```bash
cat ~/.ssh/id_rsa | base64 -w 0 > ssh_key_b64.txt
# Copy the content and add as secret
```

---

## Part 3: OwnTracks Integration

### 3.1 Deploy OwnTracks Workflow to n8n

This repository includes an automated deployment workflow for OwnTracks integration.

**Option A: Automatic Deployment (Recommended)**

1. Go to your GitHub repository
2. Click **Actions** tab
3. Select **Deploy Owntracks n8n Workflow** from the left sidebar
4. Click **Run workflow** button
5. Configure parameters:
   - **Min GPS Accuracy**: `50` (meters, higher = less accurate)
   - **Min Distance Change**: `20` (meters)
   - **Update existing workflow**: ✓ (checked)
   - **Activate workflow**: ✓ (checked)
6. Click **Run workflow**

Wait for the workflow to complete (1-2 minutes). The summary will show your webhook URL.

**Option B: Manual Deployment**

If automated deployment fails, you can create the workflow manually in n8n:

1. Open n8n web interface
2. Click **+ Add workflow**
3. Copy the workflow JSON from `.github/workflows/deploy-owntracks-n8n.yml` (starting from the `nodes` section)
4. Paste into n8n's workflow JSON editor
5. Save and activate the workflow

### 3.2 Get Your Webhook URL

After deployment, your webhook URL will be:

```
http://your-domain.com:5678/webhook/owntracks
```

**For testing**, use the test webhook:
```
http://your-domain.com:5678/webhook-test/owntracks
```

You can find the exact URL in:
- GitHub Actions deployment summary
- n8n workflow → Webhook node → Webhook URL field

### 3.3 Configure OwnTracks App

#### iOS/Android Setup

1. **Install OwnTracks** from App Store or Google Play
2. **Open the app** and go to Settings (⚙️ icon)

#### Connection Settings

1. Navigate to: **Settings → Connection**
2. Set the following:

```
Mode: HTTP
URL: http://your-domain.com:5678/webhook/owntracks
Method: POST
Authentication: None (or set if you configured it)
Device ID: JF (or your initials)
Tracker ID: JF (same as Device ID)
```

#### Privacy & Accuracy Settings

1. Navigate to: **Settings → Reporting**

```
Publish: On
Publish interval: 5 minutes
```

2. Navigate to: **Settings → Advanced**

```
Ignore inaccurate locations below: 50 meters
Distance filter: 20 meters
Monitoring mode: Significant changes (iOS) or Move (Android)
```

#### Regions & Geofences (Optional)

You can set up geofences for home, work, etc.:

1. Go to **Regions** tab
2. Tap **+** to add a new region
3. Set name (e.g., "Home"), radius (e.g., 100m)
4. When you enter/exit regions, OwnTracks will send events

### 3.4 Testing OwnTracks Integration

Send a test location update:

**Manual test from command line:**

```bash
curl -X POST http://your-domain.com:5678/webhook-test/owntracks \
  -H "Content-Type: application/json" \
  -d '{
    "_type": "location",
    "lat": 48.8566,
    "lon": 2.3522,
    "acc": 10,
    "tst": 1708290000,
    "alt": 35,
    "vel": 0,
    "batt": 85,
    "tid": "JF",
    "t": "u"
  }'
```

**From OwnTracks app:**

1. Make sure Location Services are enabled
2. Open OwnTracks
3. Tap the **Send** button (📍 icon)
4. This forces an immediate location update

**Verify in n8n:**

1. Open n8n web interface
2. Go to **Executions** (clock icon in sidebar)
3. You should see a new execution for "Owntracks Location Tracker"
4. Click on it to see the data flow

---

## Part 4: Notion Integration (Optional)

If you want to store location history, mood logs, and serendipity events in Notion:

### 4.1 Create Notion Integration

1. Go to https://www.notion.so/my-integrations
2. Click **+ New integration**
3. Name it: "Lina MCP Server"
4. Select your workspace
5. Click **Submit**
6. Copy the **Internal Integration Token** (starts with `secret_`)

### 4.2 Create Notion Databases

You'll need three databases (or adapt to your needs):

#### Location History Database

Create a database with these properties:

| Property Name | Type | Description |
|--------------|------|-------------|
| **Title** | Title | Location identifier |
| **Timestamp** | Date | When the location was recorded |
| **Latitude** | Number | Latitude coordinate |
| **Longitude** | Number | Longitude coordinate |
| **Accuracy** | Number | GPS accuracy in meters |
| **Source** | Select | "owntracks", "manual", etc. |
| **Context** | Text | Additional context or notes |

#### Mood Tracking Database

| Property Name | Type | Description |
|--------------|------|-------------|
| **Title** | Title | Mood summary |
| **Timestamp** | Date | When the mood was logged |
| **Mood Input** | Text | Raw mood description |
| **Poke Reaction** | Text | AI response/reaction |
| **Poke Action** | Select | "sent_nudge", "none", "logged_only" |
| **Source** | Select | "poke-mcp", "manual" |
| **Location** | Relation | Link to Location History |

#### Serendipity Events Database

| Property Name | Type | Description |
|--------------|------|-------------|
| **Title** | Title | Event summary |
| **Event Timestamp** | Date | When the event occurred |
| **Event Type** | Select | "micro_nudge", "reflection", etc. |
| **Message** | Text | Message sent to user |
| **Tags** | Multi-select | Event tags |
| **Related Mood** | Relation | Link to Mood Tracking |

### 4.3 Share Databases with Integration

For each database:

1. Open the database in Notion
2. Click **⋯** (three dots) in the top right
3. Select **Add connections**
4. Find and select "Lina MCP Server"
5. Click **Confirm**

### 4.4 Get Database IDs

For each database:

1. Open the database in your browser
2. Copy the URL, which looks like:
   ```
   https://www.notion.so/workspace/xxxxxxxxxxxxxxxxxxxxx?v=yyyyyyyyy
   ```
3. The database ID is the long string: `xxxxxxxxxxxxxxxxxxxxx`

### 4.5 Update MCP Server Environment

Edit your `.env` file:

```bash
nano ~/mcp-server-template/src/vm_server/.env
```

Add/update these lines:

```bash
# Notion Integration
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxx
LOCATION_HISTORY_DB_ID=xxxxxxxxxxxxxxxxxxxxx
MOOD_TRACKING_DB_ID=xxxxxxxxxxxxxxxxxxxxx
SERENDIPITY_DB_ID=xxxxxxxxxxxxxxxxxxxxx
```

Restart the MCP server:

```bash
sudo systemctl restart mcp-server.service
```

### 4.6 Create Location Tracking Tool

Create a new tool for location tracking in `vm_server/tools/location.py`:

```python
from __future__ import annotations

import os
from datetime import datetime

import httpx
from fastmcp import FastMCP

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
LOCATION_DB_ID = os.getenv("LOCATION_HISTORY_DB_ID")


def register(mcp: FastMCP) -> None:
    @mcp.tool
    async def log_location_update(
        latitude: float,
        longitude: float,
        accuracy: float | None = None,
        timestamp: str | None = None,
        source: str = "owntracks",
        context: str | None = None,
    ) -> dict:
        """
        Log a location update to Notion.

        This tool receives location data from OwnTracks via n8n
        and stores it in the Notion Location History database.
        """

        if not NOTION_TOKEN or not LOCATION_DB_ID:
            return {
                "ok": False,
                "error": "Notion integration not configured",
            }

        # Validate coordinates
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            return {
                "ok": False,
                "error": f"Invalid coordinates: lat={latitude}, lon={longitude}",
            }

        # Parse timestamp or use current time
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except Exception:
                dt = datetime.now()
        else:
            dt = datetime.now()

        # Create Notion page
        url = "https://api.notion.com/v1/pages"
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        # Format title with coordinates
        title = f"📍 {latitude:.4f}, {longitude:.4f}"

        payload = {
            "parent": {"database_id": LOCATION_DB_ID},
            "properties": {
                "Title": {
                    "title": [{"text": {"content": title}}]
                },
                "Timestamp": {
                    "date": {"start": dt.isoformat()}
                },
                "Latitude": {
                    "number": latitude
                },
                "Longitude": {
                    "number": longitude
                },
                "Accuracy": {
                    "number": accuracy if accuracy else None
                },
                "Source": {
                    "select": {"name": source}
                },
                "Context": {
                    "rich_text": [{"text": {"content": context or ""}}]
                },
            },
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload, headers=headers)

            if resp.status_code in (200, 201):
                return {
                    "ok": True,
                    "page_id": resp.json().get("id"),
                    "location": title,
                }
            else:
                return {
                    "ok": False,
                    "error": f"Notion API error: {resp.status_code}",
                    "details": resp.text[:500],
                }

        except Exception as exc:
            return {
                "ok": False,
                "error": f"Failed to log location: {exc!r}",
            }
```

### 4.7 Register the Location Tool

Edit `vm_server/tools/registry.py`:

```python
from tools import (
    # ... existing imports ...
    location,  # Add this line
)

def register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools with the server."""
    for module in (
        # ... existing modules ...
        location,  # Add this line
    ):
        module.register(mcp)
```

Restart the MCP server:

```bash
sudo systemctl restart mcp-server.service
```

### 4.8 Update n8n Workflow to Call MCP

In your n8n OwnTracks workflow:

1. Add a new **HTTP Request** node after "Send to Poke"
2. Configure it:

```
Method: POST
URL: http://localhost:8000/mcp
Authentication: None
Send Headers: Yes
Headers:
  - Content-Type: application/json
  - Accept: application/json

Body (JSON):
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "log_location_update",
    "arguments": {
      "latitude": {{ $json.poke_payload.location.latitude }},
      "longitude": {{ $json.poke_payload.location.longitude }},
      "accuracy": {{ $json.poke_payload.location.accuracy }},
      "timestamp": "{{ $json.poke_payload.timestamp }}",
      "source": "owntracks"
    }
  }
}
```

Save and activate the workflow.

---

## Part 5: Testing & Verification

### 5.1 End-to-End Test

Test the complete pipeline:

```bash
# 1. Test MCP server health
curl http://localhost:8000/health

# 2. Test MCP tool directly
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "log_location_update",
      "arguments": {
        "latitude": 48.8566,
        "longitude": 2.3522,
        "accuracy": 10,
        "source": "test"
      }
    }
  }'

# 3. Test n8n webhook
curl -X POST http://localhost:5678/webhook-test/owntracks \
  -H "Content-Type: application/json" \
  -d '{
    "_type": "location",
    "lat": 48.8566,
    "lon": 2.3522,
    "acc": 10,
    "tst": 1708290000,
    "tid": "JF",
    "t": "u"
  }'
```

### 5.2 Verify Data Flow

1. **Check n8n Executions:**
   - Open n8n UI → Executions
   - Look for successful executions
   - Inspect each node's output

2. **Check MCP Server Logs:**
   ```bash
   sudo journalctl -u mcp-server.service -f
   ```

3. **Check Notion:**
   - Open your Location History database
   - Verify a new entry was created

### 5.3 Test from OwnTracks App

1. Open OwnTracks app
2. Force a location update (tap 📍 icon)
3. Wait 10-30 seconds
4. Check n8n executions
5. Check Notion for new entry

### 5.4 Monitor Logs

**n8n logs:**
```bash
# If using systemd
sudo journalctl -u n8n.service -f

# If running manually
# Logs appear in the terminal where n8n is running
```

**MCP server logs:**
```bash
sudo journalctl -u mcp-server.service -f
```

**Filter for location-related logs:**
```bash
sudo journalctl -u mcp-server.service | grep -i location
```

---

## Part 6: Maintenance & Troubleshooting

### 6.1 Common Issues & Solutions

#### Issue: OwnTracks not sending data

**Symptoms:**
- No executions in n8n
- OwnTracks shows "Last publish: Never"

**Solutions:**
1. Check OwnTracks settings:
   - Mode: HTTP
   - URL is correct
   - Internet connection is active
2. Check firewall:
   ```bash
   sudo ufw status
   sudo ufw allow 5678/tcp  # If needed
   ```
3. Test webhook directly from command line
4. Check n8n is running:
   ```bash
   sudo systemctl status n8n.service
   ```

#### Issue: n8n workflow not executing

**Symptoms:**
- Webhook receives data but workflow doesn't run
- Execution shows "Workflow not found"

**Solutions:**
1. Verify workflow is **active** in n8n UI
2. Check webhook path matches OwnTracks URL
3. Restart n8n:
   ```bash
   sudo systemctl restart n8n.service
   ```

#### Issue: MCP server not receiving location data

**Symptoms:**
- n8n execution succeeds but MCP server logs show no activity
- Notion database not updating

**Solutions:**
1. Check MCP server is running:
   ```bash
   sudo systemctl status mcp-server.service
   ```
2. Test MCP endpoint directly:
   ```bash
   curl http://localhost:8000/health
   ```
3. Check `.env` file has correct Notion credentials
4. Restart MCP server:
   ```bash
   sudo systemctl restart mcp-server.service
   ```

#### Issue: Location data filtered out

**Symptoms:**
- n8n execution shows "Skipped: Low accuracy" or "Skipped: Small distance"

**This is expected behavior!** The filter prevents spam from:
- Inaccurate GPS readings (>50m accuracy)
- Tiny movements (<20m distance)

**To adjust filtering:**
1. Edit n8n workflow
2. Modify the "Filter Location Data" code node
3. Change `MIN_ACCURACY` or `MIN_DISTANCE` values

#### Issue: Notion API errors

**Symptoms:**
- MCP server logs show "Notion API error: 401" or "404"

**Solutions:**
1. **401 Unauthorized:**
   - Check `NOTION_TOKEN` in `.env`
   - Verify integration has access to databases
   - Regenerate integration token if needed

2. **404 Not Found:**
   - Check database IDs in `.env`
   - Ensure databases are shared with integration

3. **400 Bad Request:**
   - Check database properties match code
   - Verify property types (e.g., "Select" vs "Multi-select")

### 6.2 Service Management

**Restart services:**
```bash
sudo systemctl restart mcp-server.service
sudo systemctl restart n8n.service
```

**Stop services:**
```bash
sudo systemctl stop mcp-server.service
sudo systemctl stop n8n.service
```

**Enable/disable auto-start:**
```bash
sudo systemctl enable mcp-server.service  # Start on boot
sudo systemctl disable mcp-server.service  # Don't start on boot
```

**View service status:**
```bash
sudo systemctl status mcp-server.service
sudo systemctl status n8n.service
```

### 6.3 Log Management

**View recent logs:**
```bash
sudo journalctl -u mcp-server.service -n 100
sudo journalctl -u n8n.service -n 100
```

**Follow logs in real-time:**
```bash
sudo journalctl -u mcp-server.service -f
```

**Filter logs by date:**
```bash
sudo journalctl -u mcp-server.service --since "1 hour ago"
sudo journalctl -u mcp-server.service --since "2024-02-19 10:00:00"
```

**Export logs to file:**
```bash
sudo journalctl -u mcp-server.service > mcp-logs.txt
```

### 6.4 Updating the System

**Update MCP server code:**

```bash
cd ~/mcp-server-template/src
git pull origin main
source .venv/bin/activate
cd vm_server
uv pip install -r requirements.txt
sudo systemctl restart mcp-server.service
```

**Or use automated deployment** (if GitHub Actions configured):
```bash
# Just push to main branch
git push origin main
# GitHub Actions will deploy automatically
```

**Update n8n:**

```bash
sudo npm update -g n8n
sudo systemctl restart n8n.service
```

### 6.5 Backup & Restore

**Backup Notion databases:**
- Notion automatically versions all changes
- Export databases: Settings → Export → Select databases

**Backup n8n workflows:**
```bash
# Export workflows from n8n UI
# Settings → Import/Export → Export workflows

# Or backup n8n data directory
sudo tar -czf n8n-backup-$(date +%Y%m%d).tar.gz ~/.n8n/
```

**Backup MCP server config:**
```bash
cd ~/mcp-server-template/src
cp vm_server/.env vm_server/.env.backup-$(date +%Y%m%d)
```

### 6.6 Security Best Practices

1. **Use HTTPS:** Set up a reverse proxy (nginx/caddy) with SSL
2. **Firewall:** Only open necessary ports
   ```bash
   sudo ufw enable
   sudo ufw allow 22/tcp    # SSH
   sudo ufw allow 80/tcp    # HTTP
   sudo ufw allow 443/tcp   # HTTPS
   ```
3. **Authentication:** Enable n8n basic auth (already configured)
4. **API Keys:** Rotate Notion integration tokens periodically
5. **Environment Variables:** Never commit `.env` files to Git
6. **Updates:** Keep all software up to date

---

## Advanced Configuration

### Reverse Proxy with Nginx & SSL

For production use, set up a reverse proxy with HTTPS:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx

# Configure nginx
sudo nano /etc/nginx/sites-available/mcp-lina
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL certificates (will be added by certbot)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # n8n
    location /n8n/ {
        proxy_pass http://localhost:5678/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # MCP server
    location /mcp {
        proxy_pass http://localhost:8000/mcp;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # MCP health endpoint
    location /health {
        proxy_pass http://localhost:8000/health;
    }
}
```

Enable the site and get SSL certificate:

```bash
sudo ln -s /etc/nginx/sites-available/mcp-lina /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

Update your OwnTracks URL to:
```
https://your-domain.com/n8n/webhook/owntracks
```

### Custom Location Processing

Create a custom tool to process location data with context:

```python
# vm_server/tools/location_context.py

from __future__ import annotations

from datetime import datetime
from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.tool
    async def analyze_location_context(
        latitude: float,
        longitude: float,
        timestamp: str | None = None,
    ) -> dict:
        """
        Analyze location context and determine if it's meaningful.

        Returns contextual information like:
        - Time of day (morning, afternoon, evening, night)
        - Location type (home, work, transit, unknown)
        - Distance from last known location
        - Suggested actions (log mood, send nudge, etc.)
        """

        # Parse timestamp
        if timestamp:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        else:
            dt = datetime.now()

        # Determine time of day
        hour = dt.hour
        if 5 <= hour < 12:
            time_of_day = "morning"
        elif 12 <= hour < 17:
            time_of_day = "afternoon"
        elif 17 <= hour < 21:
            time_of_day = "evening"
        else:
            time_of_day = "night"

        # TODO: Add geofence logic to determine location type
        # This would require storing known locations (home, work, etc.)
        location_type = "unknown"

        # TODO: Calculate distance from last location
        # This would require fetching the last location from Notion
        distance_from_last = None

        # Suggest actions based on context
        suggested_actions = []

        if time_of_day == "evening" and location_type == "home":
            suggested_actions.append("Suggest evening wind-down routine")

        if distance_from_last and distance_from_last > 5000:  # 5km
            suggested_actions.append("Significant movement detected")

        return {
            "context": {
                "time_of_day": time_of_day,
                "location_type": location_type,
                "hour": hour,
                "day_of_week": dt.strftime("%A"),
            },
            "coordinates": {
                "latitude": latitude,
                "longitude": longitude,
            },
            "analysis": {
                "distance_from_last": distance_from_last,
                "suggested_actions": suggested_actions,
            },
        }
```

Register this tool in `registry.py` and use it in your n8n workflow for intelligent processing.

---

## Summary

You now have a complete location tracking system:

✅ **MCP server** running as a systemd service  
✅ **n8n** processing OwnTracks data with smart filtering  
✅ **OwnTracks** sending location updates from your phone  
✅ **Notion** storing your location history (optional)  
✅ **Monitoring** with systemd and journald  

**Next Steps:**
- Customize the serendipity nudge logic for your needs
- Add more location-based automations in n8n
- Create dashboards to visualize your location history
- Integrate with mood tracking for richer context

**Useful Commands:**
```bash
# Check everything is running
sudo systemctl status mcp-server.service n8n.service

# View logs
sudo journalctl -u mcp-server.service -f

# Test MCP
curl http://localhost:8000/health

# Restart services
sudo systemctl restart mcp-server.service n8n.service
```

For more help, see the [troubleshooting section](#61-common-issues--solutions) or check the [main README](README.md).

---

**Questions or Issues?**

- GitHub Issues: https://github.com/Joru-chan/assistant/issues
- Check logs: `sudo journalctl -u mcp-server.service -n 100`
- Test endpoints: `curl http://localhost:8000/health`

**Happy tracking! 📍**
