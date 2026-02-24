#!/usr/bin/env python3
"""
Lina Serendipity MCP Server
===========================
FastMCP server with comprehensive tools for personal assistance.

This version includes HARDCODED FALLBACKS for all environment variables
to eliminate configuration issues during debugging.

WARNING: The hardcoded values are for DEBUGGING ONLY!
In production, always set real secrets via environment variables.
"""

# ============================================================================
# MAXIMUM DEBUG MODE: Print statements at every critical point
# ============================================================================

import sys
import traceback
from datetime import datetime

def debug_print(msg, level="INFO"):
    """Print debug message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] [{level}] DEBUG: {msg}", flush=True)

def debug_exception(msg, exc):
    """Print exception with full traceback."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] [ERROR] {msg}", flush=True)
    print(f"Exception type: {type(exc).__name__}", flush=True)
    print(f"Exception message: {str(exc)}", flush=True)
    print("Full traceback:", flush=True)
    traceback.print_exc()
    sys.stdout.flush()

# ============================================================================
# STARTUP: Begin imports with debug output
# ============================================================================

debug_print("=" * 60)
debug_print("Starting server imports...")
debug_print("=" * 60)

try:
    debug_print("Importing: os")
    import os
    debug_print("✅ os imported")
except Exception as e:
    debug_exception("❌ Failed to import os", e)
    sys.exit(1)

try:
    debug_print("Importing: pathlib.Path")
    from pathlib import Path
    debug_print("✅ pathlib.Path imported")
except Exception as e:
    debug_exception("❌ Failed to import pathlib", e)
    sys.exit(1)

# ============================================================================
# DOTENV: Load environment variables
# ============================================================================

debug_print("Loading environment variables from .env file...")
try:
    from dotenv import load_dotenv
    debug_print("✅ dotenv imported")
    load_dotenv()
    debug_print("✅ .env file loaded (if present)")
except ImportError:
    debug_print("⚠️  python-dotenv not installed, using system environment variables only", "WARN")
except Exception as e:
    debug_exception("⚠️  Error loading .env file (continuing anyway)", e)

# ============================================================================
# FASTMCP: Import main framework
# ============================================================================

debug_print("Importing FastMCP framework...")
try:
    from fastmcp import FastMCP
    debug_print("✅ FastMCP imported successfully")
except ImportError as e:
    debug_exception("❌ CRITICAL: Failed to import FastMCP", e)
    debug_print("Make sure 'pip install fastmcp' was successful", "ERROR")
    sys.exit(1)
except Exception as e:
    debug_exception("❌ CRITICAL: Unexpected error importing FastMCP", e)
    sys.exit(1)

# ============================================================================
# PATH SETUP: Add vm_server to Python path
# ============================================================================

debug_print("Setting up Python path for tool imports...")
try:
    ROOT_DIR = Path(__file__).resolve().parent
    debug_print(f"Root directory: {ROOT_DIR}")
    
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
        debug_print(f"✅ Added {ROOT_DIR} to Python path")
    else:
        debug_print(f"✅ {ROOT_DIR} already in Python path")
except Exception as e:
    debug_exception("❌ Failed to set up Python path", e)
    sys.exit(1)

# ============================================================================
# TOOLS: Import tool registry
# ============================================================================

debug_print("Importing tool registry...")
try:
    from tools.registry import register_tools
    debug_print("✅ Tool registry imported successfully")
except ImportError as e:
    debug_exception("❌ CRITICAL: Failed to import tools.registry", e)
    debug_print("Check that tools/registry.py exists", "ERROR")
    sys.exit(1)
except Exception as e:
    debug_exception("❌ CRITICAL: Unexpected error importing tools", e)
    sys.exit(1)

debug_print("=" * 60)
debug_print("All imports complete!")
debug_print("=" * 60)

# ============================================================================
# CONFIGURATION WITH HARDCODED FALLBACKS
# ============================================================================

def get_config():
    """Get server configuration with hardcoded fallbacks for debugging."""
    debug_print("Loading configuration...")
    
    try:
        config = {
            # Server configuration
            'port': int(os.getenv('PORT', '8000')),
            'host': os.getenv('HOST', '0.0.0.0'),
            'log_level': os.getenv('LOG_LEVEL', 'info'),
            
            # MCP configuration
            'mcp_server_name': os.getenv('MCP_SERVER_NAME', 'Lina Serendipity MCP Server'),
            'mcp_service_name': os.getenv('MCP_SERVICE_NAME', 'mcp-server.service'),
            
            # Notion integration (HARDCODED FALLBACK FOR DEBUGGING)
            'notion_token': os.getenv('NOTION_TOKEN', 'debug-notion-token-12345'),
            'pantry_db_id': os.getenv('PANTRY_DB_ID', 'debug-pantry-database-id-67890'),
            
            # Serendipity webhook (HARDCODED FALLBACK FOR DEBUGGING)
            'serendipity_webhook_url': os.getenv(
                'SERENDIPITY_EVENT_WEBHOOK_URL',
                'http://localhost:5678/webhook/debug-serendipity'
            ),
            
            # Admin authentication (HARDCODED FALLBACK FOR DEBUGGING)
            'admin_token': os.getenv('ADMIN_TOKEN', 'debug-admin-token-abcdef'),
            
            # Pantry property mappings (all have safe defaults)
            'pantry_props': {
                'name': os.getenv('PANTRY_PROP_NAME', 'Item Name'),
                'quantity': os.getenv('PANTRY_PROP_QUANTITY', 'Quantity'),
                'unit': os.getenv('PANTRY_PROP_UNIT', 'Unit'),
                'category': os.getenv('PANTRY_PROP_CATEGORY', 'Food Category'),
                'purchase_date': os.getenv('PANTRY_PROP_PURCHASE_DATE', 'Purchase Date'),
                'store': os.getenv('PANTRY_PROP_STORE', 'Store'),
                'price': os.getenv('PANTRY_PROP_PRICE', 'Price'),
                'expiration_date': os.getenv('PANTRY_PROP_EXPIRATION_DATE', 'Expiration Date'),
                'storage_location': os.getenv('PANTRY_PROP_STORAGE_LOCATION', 'Storage Location'),
                'notes': os.getenv('PANTRY_PROP_NOTES', 'Notes'),
                'receipt_number': os.getenv('PANTRY_PROP_RECEIPT_NUMBER', 'Receipt Number'),
                'status': os.getenv('PANTRY_PROP_STATUS', 'Status'),
                'replenish': os.getenv('PANTRY_PROP_REPLENISH', 'Replenish'),
            }
        }
        
        # Show which values are from environment vs hardcoded
        config['_sources'] = {
            'port': 'env' if os.getenv('PORT') else 'hardcoded',
            'notion_token': 'env' if os.getenv('NOTION_TOKEN') else 'hardcoded',
            'pantry_db_id': 'env' if os.getenv('PANTRY_DB_ID') else 'hardcoded',
            'serendipity_webhook': 'env' if os.getenv('SERENDIPITY_EVENT_WEBHOOK_URL') else 'hardcoded',
            'admin_token': 'env' if os.getenv('ADMIN_TOKEN') else 'hardcoded',
        }
        
        debug_print("✅ Configuration loaded successfully")
        return config
        
    except Exception as e:
        debug_exception("❌ CRITICAL: Failed to load configuration", e)
        sys.exit(1)

# ============================================================================
# MAIN SERVER SETUP
# ============================================================================

def main():
    """Main server entry point with comprehensive error handling."""
    
    debug_print("=" * 60)
    debug_print("ENTERING MAIN() FUNCTION")
    debug_print("=" * 60)
    
    try:
        # Get configuration
        debug_print("Step 1: Loading configuration...")
        config = get_config()
        debug_print(f"✅ Configuration loaded: {config['mcp_server_name']}")
        
        # Display startup configuration
        print()
        print("=" * 60)
        print("🚀 Lina Serendipity MCP Server Starting")
        print("=" * 60)
        print(f"📋 Configuration:")
        print(f"  Server: {config['host']}:{config['port']}")
        print(f"  Log Level: {config['log_level']}")
        print(f"  Service: {config['mcp_service_name']}")
        print()
        print(f"🔑 Secrets Status:")
        for key, source in config['_sources'].items():
            emoji = "🌍" if source == 'env' else "🔧"
            print(f"  {emoji} {key}: {source}")
        
        if 'hardcoded' in config['_sources'].values():
            print()
            print("⚠️  WARNING: Using hardcoded fallback values!")
            print("⚠️  Set environment variables for production use.")
            print("⚠️  See .env.example for configuration template.")
        
        print("=" * 60)
        print()
        sys.stdout.flush()
        
        # Create the MCP server instance
        debug_print("Step 2: Creating FastMCP instance...")
        try:
            mcp = FastMCP(config['mcp_server_name'])
            debug_print(f"✅ FastMCP instance created: {config['mcp_server_name']}")
        except Exception as e:
            debug_exception("❌ CRITICAL: Failed to create FastMCP instance", e)
            sys.exit(1)
        
        # Register all tools
        debug_print("Step 3: Registering tools...")
        print("📦 Registering MCP tools...")
        sys.stdout.flush()
        
        try:
            register_tools(mcp)
            debug_print("✅ Tools registered successfully")
            print("✅ Tools registered successfully")
            print()
            sys.stdout.flush()
        except Exception as e:
            debug_exception("❌ CRITICAL: Failed to register tools", e)
            print("❌ Tool registration failed - see error above")
            sys.exit(1)
        
        # Display server startup info
        print(f"🌐 Starting server on {config['host']}:{config['port']}")
        print(f"📍 MCP endpoint: http://{config['host']}:{config['port']}/mcp")
        print(f"💚 Health check: Use the health_check tool via MCP")
        print()
        sys.stdout.flush()
        
        # Start the server with normal FastMCP routing
        debug_print("Step 4: Starting mcp.run()...")
        debug_print(f"Transport: streamable-http")
        debug_print(f"Host: {config['host']}")
        debug_print(f"Port: {config['port']}")
        
        try:
            debug_print("Calling mcp.run() - Server should start now...")
            sys.stdout.flush()
            
            mcp.run(
                transport="streamable-http",
                host=config['host'],
                port=config['port'],
            )
            
            # This line should never be reached (mcp.run blocks)
            debug_print("⚠️  mcp.run() returned unexpectedly!", "WARN")
            
        except KeyboardInterrupt:
            debug_print("Received KeyboardInterrupt (Ctrl+C)", "INFO")
            print("\n👋 Server stopped by user")
            sys.exit(0)
        except Exception as e:
            debug_exception("❌ CRITICAL: mcp.run() failed", e)
            sys.exit(1)
            
    except Exception as e:
        debug_exception("❌ CRITICAL: Unhandled exception in main()", e)
        sys.exit(1)

if __name__ == "__main__":
    debug_print("=" * 60)
    debug_print("SERVER SCRIPT STARTED")
    debug_print("=" * 60)
    debug_print(f"Python version: {sys.version}")
    debug_print(f"Python executable: {sys.executable}")
    debug_print(f"Script: {__file__}")
    debug_print(f"Working directory: {os.getcwd()}")
    debug_print("=" * 60)
    
    try:
        main()
    except SystemExit as e:
        debug_print(f"SystemExit called with code: {e.code}")
        sys.exit(e.code)
    except Exception as e:
        debug_exception("❌ FATAL: Uncaught exception at top level", e)
        sys.exit(1)
