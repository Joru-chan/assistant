# GitHub Actions CI/CD

This directory contains GitHub Actions workflows for automated deployment and CI/CD.

## 🚀 Available Workflows

### Deploy to VM (`deploy.yml`)

Automatically deploys the MCP server to your VM whenever code is pushed to the `main` branch.

**Triggers:**
- Push to `main` branch (when `vm_server/`, `vm/deploy.sh`, or workflow files change)
- Manual dispatch via Actions tab

**What it does:**
1. Sets up SSH connection to VM
2. Syncs code via rsync
3. Installs Python dependencies
4. Restarts systemd service
5. Runs health checks (MCP + HTTP)
6. Reports deployment status

**Manual deployment:**
```bash
# Via GitHub web interface:
Actions → Deploy to VM → Run workflow

# Via GitHub CLI:
gh workflow run deploy.yml
```

**Restart-only mode:**
```bash
# Via GitHub web interface:
Actions → Deploy to VM → Run workflow → Check "Restart only"

# Via GitHub CLI:
gh workflow run deploy.yml -f restart_only=true
```

## 📖 Documentation

- **[DEPLOYMENT_SETUP.md](./DEPLOYMENT_SETUP.md)** - Complete setup guide for configuring GitHub secrets and automated deployment

## 🔐 Required Secrets

Ensure these secrets are configured in your repository settings:

| Secret | Description |
|--------|-------------|
| `VM_SSH_PRIVATE_KEY` | SSH private key for authentication |
| `VM_HOST` | VM IP address or hostname |
| `VM_USER` | SSH username |
| `VM_DEST_DIR` | Deployment directory on VM |
| `VM_SERVICE` | Systemd service name |
| `VM_VENV_PY` | Path to Python in virtualenv |
| `VM_MCP_URL` | MCP endpoint URL |
| `VM_HEALTH_URL` | Health check endpoint URL |

See [DEPLOYMENT_SETUP.md](./DEPLOYMENT_SETUP.md) for detailed configuration instructions.

## 🔍 Monitoring

- **Workflow status:** Check the `Actions` tab in your repository
- **Deployment logs:** Click on any workflow run to see detailed logs
- **Service status:** SSH to VM and run `sudo systemctl status mcp-server.service`

## 🆘 Troubleshooting

Common issues and solutions:

**SSH connection fails:**
- Verify `VM_SSH_PRIVATE_KEY` is complete and properly formatted
- Check `VM_HOST` is correct and accessible
- Ensure SSH key is authorized on the VM

**Health checks fail:**
- Check service logs: `sudo journalctl -u mcp-server.service -n 50`
- Verify URLs in secrets are correct
- Ensure service is running: `sudo systemctl status mcp-server.service`

**Deployment succeeds but service not working:**
- Check for Python errors in service logs
- Verify environment variables are set on VM
- Check file permissions in deployment directory

For more troubleshooting tips, see [DEPLOYMENT_SETUP.md](./DEPLOYMENT_SETUP.md#-troubleshooting).

## 🎯 Quick Start

1. **Configure secrets** - Add all 8 required secrets in repository settings
2. **Test manually** - Run workflow manually from Actions tab
3. **Push code** - Make changes to `vm_server/` and push to `main`
4. **Monitor** - Watch deployment in Actions tab
5. **Verify** - Check service status and health endpoints

## 📝 Notes

- Deployments only trigger when relevant files change (`vm_server/`, `vm/deploy.sh`, workflow files)
- The workflow uses the same logic as the manual `vm/deploy.sh` script
- Failed deployments will send email notifications (configurable in GitHub settings)
- Environment protection can be added for production safety (see DEPLOYMENT_SETUP.md)

---

**Need help?** See [DEPLOYMENT_SETUP.md](./DEPLOYMENT_SETUP.md) for complete documentation.
