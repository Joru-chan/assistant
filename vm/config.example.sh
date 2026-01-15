#!/usr/bin/env bash

VM_HOST=134.98.141.19
VM_USER=ubuntu
VM_SSH_KEY=/Users/jordane/Downloads/ssh-key-2025-11-05.key
VM_LOCAL_SRC=vm_server
VM_DEST_DIR=/home/ubuntu/mcp-server-template/src
VM_SERVICE=mcp-server.service
VM_VENV_PY=/home/ubuntu/mcp-server-template/src/venv/bin/python
VM_MCP_URL=https://mcp-lina.duckdns.org/mcp
VM_MCP_LOCAL_URL=http://127.0.0.1:8000/mcp
VM_HEALTH_URL=https://mcp-lina.duckdns.org/health
