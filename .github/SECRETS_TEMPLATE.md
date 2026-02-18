# GitHub Secrets Configuration Checklist

Use this checklist when setting up GitHub Secrets for automated deployment.

## 📋 Required Secrets Checklist

Copy this checklist and check off each secret as you add it.

### Setup Instructions

1. Go to: `https://github.com/Joru-chan/assistant/settings/secrets/actions`
2. Click "New repository secret" for each item below
3. Copy the exact name and paste your value
4. Click "Add secret"

---

### Secrets to Configure

- [ ] **VM_SSH_PRIVATE_KEY**
  - **Value:** Content of your SSH private key file
  - **Source:** `cat /Users/jordane/Downloads/ssh-key-2025-11-05.key`
  - **Note:** Include the full key with `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----`

- [ ] **VM_HOST**
  - **Value:** `134.98.141.19`
  - **Note:** Your VM's IP address

- [ ] **VM_USER**
  - **Value:** `ubuntu`
  - **Note:** SSH username for the VM

- [ ] **VM_DEST_DIR**
  - **Value:** `/home/ubuntu/mcp-server-template/src`
  - **Note:** Target directory on VM where code will be deployed

- [ ] **VM_SERVICE**
  - **Value:** `mcp-server.service`
  - **Note:** Name of the systemd service to restart

- [ ] **VM_VENV_PY**
  - **Value:** `/home/ubuntu/mcp-server-template/src/venv/bin/python`
  - **Note:** Path to Python in the virtual environment

- [ ] **VM_MCP_URL**
  - **Value:** `https://mcp-lina.duckdns.org/mcp`
  - **Note:** MCP endpoint URL for health checks

- [ ] **VM_HEALTH_URL**
  - **Value:** `https://mcp-lina.duckdns.org/health`
  - **Note:** HTTP health check endpoint URL

---

## 🔍 Verification Steps

After adding all secrets:

- [ ] All 8 secrets are visible in the Actions secrets page
- [ ] Secret names match exactly (case-sensitive, no typos)
- [ ] No extra spaces in secret values
- [ ] SSH key is the complete key (not just a portion)

## 🧪 Test Deployment

- [ ] Go to `Actions` tab
- [ ] Click on "Deploy to VM" workflow
- [ ] Click "Run workflow" → "Run workflow"
- [ ] Watch the deployment logs
- [ ] Verify all steps complete successfully
- [ ] Check that health checks pass

## ✅ Success Criteria

- [ ] Manual workflow run completes without errors
- [ ] Service restarts successfully
- [ ] Health checks pass (both MCP and HTTP)
- [ ] Can access the MCP server at the health URL
- [ ] Automatic deployment works on push to main

## 🚀 Quick Setup Commands (Optional)

If you have GitHub CLI installed:

```bash
# Make sure you're in the repository directory
cd /path/to/assistant

# Login to GitHub (if not already)
gh auth login

# Set all secrets at once
gh secret set VM_SSH_PRIVATE_KEY < /Users/jordane/Downloads/ssh-key-2025-11-05.key
gh secret set VM_HOST -b "134.98.141.19"
gh secret set VM_USER -b "ubuntu"
gh secret set VM_DEST_DIR -b "/home/ubuntu/mcp-server-template/src"
gh secret set VM_SERVICE -b "mcp-server.service"
gh secret set VM_VENV_PY -b "/home/ubuntu/mcp-server-template/src/venv/bin/python"
gh secret set VM_MCP_URL -b "https://mcp-lina.duckdns.org/mcp"
gh secret set VM_HEALTH_URL -b "https://mcp-lina.duckdns.org/health"

# Verify secrets were added
gh secret list
```

## 🔒 Security Notes

- ✅ Secrets are encrypted and only exposed to workflow runs
- ✅ Secret values are never shown in logs
- ✅ Only repository admins can view/edit secrets
- ⚠️ Rotate SSH keys periodically
- ⚠️ Use dedicated deploy keys (not personal SSH keys)
- ⚠️ Review workflow logs for any security issues

## 📚 Additional Resources

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Complete Setup Guide](.github/DEPLOYMENT_SETUP.md)
- [Troubleshooting Guide](.github/DEPLOYMENT_SETUP.md#-troubleshooting)

---

**Last Updated:** 2026-02-18
**Status:** Ready to use
