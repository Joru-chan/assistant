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

import os
import sys
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables only")
    pass

from fastmcp import FastMCP

# Add vm_server to path for tool imports
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.registry import register_tools

# ============================================================================
# CONFIGURATION WITH HARDCODED FALLBACKS
# ============================================================================
# All environment variables have hardcoded fallback values for debugging.
# This ensures the server ALWAYS starts even with zero configuration.
# 
# In production: Set real values via environment variables!
# ============================================================================

def get_config():
    """Get server configuration with hardcoded fallbacks for debugging."""
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
    
    return config

# ============================================================================
# MAIN SERVER SETUP
# ============================================================================

def main():
    """Main server entry point."""
    
    # Get configuration
    config = get_config()
    
    # Display startup configuration
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
    
    # Create the MCP server instance
    mcp = FastMCP(config['mcp_server_name'])
    
    # Register all tools
    print("📦 Registering MCP tools...")
    register_tools(mcp)
    print("✅ Tools registered successfully")
    print()
    
    # NORMAL FASTMCP ROUTING (Nuclear option removed!)
    # The FastMCP library handles routing internally
    # Health check is now handled by the health.py tool
    
    print(f"🌐 Starting server on {config['host']}:{config['port']}")
    print(f"📍 MCP endpoint: http://{config['host']}:{config['port']}/mcp")
    print(f"💚 Health check: Use the health_check tool via MCP")
    print()
    
    # Start the server with normal FastMCP routing
    mcp.run(
        transport="streamable-http",
        host=config['host'],
        port=config['port'],
    )

if __name__ == "__main__":
    main()
