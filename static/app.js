let catalog = null;
let selected = null;

const toolListEl = document.getElementById('tool-list');
const detailEl = document.getElementById('detail');
const metaEl = document.getElementById('meta');
const searchInput = document.getElementById('search');
const outputDrawer = document.getElementById('output-drawer');
const outputContent = document.getElementById('output-content');
const outputTail = document.getElementById('output-tail');
const outputStatus = document.getElementById('output-status');
const outputClear = document.getElementById('output-clear');
const outputCopy = document.getElementById('output-copy');
const outputToggle = document.getElementById('output-toggle');
const outputAuto = document.getElementById('output-autoscroll');

const adminTabs = document.querySelectorAll('[data-admin-tab]');
const adminPanels = document.querySelectorAll('[data-admin-panel]');
const navItems = document.querySelectorAll('[data-section]');
const sections = document.querySelectorAll('.section');

const statusAdminToken = document.getElementById('status-admin-token');
const statusAdvanced = document.getElementById('status-advanced');

const settingsModal = document.getElementById('settings-modal');
const openSettingsBtn = document.getElementById('open-settings');
const closeSettingsBtn = document.getElementById('close-settings');
const adminTokenInput = document.getElementById('input-admin-token');
const advancedToggle = document.getElementById('toggle-advanced');

const overviewVmStatus = document.getElementById('overview-vm-status');
const overviewMcpHealth = document.getElementById('overview-mcp-health');
const overviewLastDeploy = document.getElementById('overview-last-deploy');
const vmStatusText = document.getElementById('vm-status-text');
const mcpHealthText = document.getElementById('mcp-health-text');

const SAFE_TOOLS = new Set([
  'hello',
  'health_check',
  'tool_requests_latest',
  'tool_requests_search',
  'notion_search',
  'notion_get_page',
]);

const historyState = {
  status: { label: 'VM Status', lastRun: 'never', exitCode: '-' },
  logs: { label: 'VM Logs', lastRun: 'never', exitCode: '-' },
  health: { label: 'Health Check', lastRun: 'never', exitCode: '-' },
  deploy: { label: 'VM Deploy', lastRun: 'never', exitCode: '-' },
  pull: { label: 'Pull VM Server Code', lastRun: 'never', exitCode: '-' },
  restart: { label: 'VM Restart', lastRun: 'never', exitCode: '-' },
  toolsList: { label: 'Tools List', lastRun: 'never', exitCode: '-' },
  mcp: { label: 'MCP Call', lastRun: 'never', exitCode: '-' },
};

function openDrawer() {
  outputDrawer.classList.remove('collapsed');
  document.body.classList.add('drawer-open');
}

function closeDrawer() {
  outputDrawer.classList.add('collapsed');
  document.body.classList.remove('drawer-open');
}

function setOutput(text, status) {
  outputContent.textContent = text || '(no output yet)';
  const lines = (text || '').split('\n');
  outputTail.textContent = lines.slice(Math.max(lines.length - 30, 0)).join('\n') || 'Last 30 lines will appear here.';
  if (status) {
    outputStatus.textContent = status;
  }
  openDrawer();
  if (outputAuto.checked) {
    outputContent.scrollTop = outputContent.scrollHeight;
  }
}

function formatJobOutput(job) {
  let output = job.stdout || '';
  if (job.stderr) {
    output += `\n\n[stderr]\n${job.stderr}`;
  }
  return output || '(no output yet)';
}

function updateOverview() {
  overviewLastDeploy.textContent = historyState.deploy.lastRun === 'never' ? 'Never.' : historyState.deploy.lastRun;
}

function setStatusIndicators() {
  statusAdminToken.textContent = adminTokenInput.value.trim() ? 'Admin token: ✓' : 'Admin token: missing';
  statusAdvanced.textContent = advancedToggle.checked ? 'Advanced: on' : 'Advanced: off';
}

function getAdminToken() {
  return adminTokenInput.value.trim();
}

async function postJson(path, payload) {
  const headers = { 'Content-Type': 'application/json' };
  const token = getAdminToken();
  if (token) {
    headers['X-Admin-Token'] = token;
  }
  const response = await fetch(path, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload || {}),
  });
  const data = await response.json();
  return { response, data };
}

async function pollJob(jobId, actionKey) {
  const poll = async () => {
    const token = getAdminToken();
    const headers = token ? { 'X-Admin-Token': token } : {};
    const response = await fetch(`/api/jobs/${jobId}`, { headers });
    const data = await response.json();
    setOutput(formatJobOutput(data), data.done ? 'Done' : 'Running');
    if (data.done) {
      clearInterval(timer);
      const state = historyState[actionKey];
      if (state) {
        state.lastRun = data.updated_at || data.started_at || 'unknown';
        state.exitCode = data.exit_code === null ? '-' : data.exit_code;
        updateOverview();
        if (actionKey === 'status') {
          const message = state.exitCode === 0 ? 'Last status check ok.' : 'Last status check returned errors.';
          overviewVmStatus.textContent = message;
          vmStatusText.textContent = message;
        }
        if (actionKey === 'health') {
          const message = state.exitCode === 0 ? 'Last health check ok.' : 'Health check reported errors.';
          overviewMcpHealth.textContent = message;
          mcpHealthText.textContent = message;
        }
      }
    }
  };
  const timer = setInterval(poll, 500);
  await poll();
}

function runJob(cmd, actionKey, confirm, advanced) {
  if (!getAdminToken()) {
    setOutput('Admin token required.', 'Error');
    return;
  }
  setOutput('Starting job...', 'Running');
  const payload = { cmd, confirm: Boolean(confirm), advanced: Boolean(advanced) };
  postJson('/api/jobs/run', payload).then(({ data }) => {
    if (data.error) {
      setOutput(JSON.stringify(data, null, 2), 'Error');
      return;
    }
    pollJob(data.job_id, actionKey);
  });
}

async function loadCatalog() {
  try {
    const response = await fetch('/catalog');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    catalog = await response.json();
    if (catalog.error) {
      throw new Error(catalog.error);
    }
    selected = null;
    renderTools();
    metaEl.textContent = `Last built ${catalog.generated_at} — ${catalog.tool_count} tools`;
  } catch (error) {
    metaEl.textContent = `Failed to load catalog: ${error}`;
    toolListEl.innerHTML = '<div class="muted">Catalog unavailable. Use Refresh to retry.</div>';
  }
}

function buildSnippet(tool) {
  const argsObj = {};
  (tool.args || []).forEach(arg => {
    argsObj[arg.name] = arg.default === null ? '' : arg.default;
  });
  const jsonArgs = JSON.stringify(argsObj, null, 2);
  return `./vm/mcp_curl.sh ${tool.name} '${jsonArgs.replace(/\n/g, '\\n')}'`;
}

function renderTools() {
  const query = searchInput.value.toLowerCase();
  const tools = (catalog?.tools || []).filter(tool => {
    const haystack = [tool.name, tool.doc, (tool.tags || []).join(' ')].join(' ').toLowerCase();
    return haystack.includes(query);
  });
  toolListEl.innerHTML = '';
  tools.forEach(tool => {
    const item = document.createElement('div');
    item.className = `tool-item${selected && selected.name === tool.name ? ' active' : ''}`;
    item.innerHTML = `<div class="tool-name">${tool.name}</div><div class="muted">${tool.doc || 'No description.'}</div>`;
    item.onclick = () => selectTool(tool);
    toolListEl.appendChild(item);
  });
  if (!tools.length) {
    toolListEl.innerHTML = '<div class="muted">No tools match your search.</div>';
  }
  if (!selected && tools.length) {
    selectTool(tools[0]);
  }
}

function selectTool(tool) {
  selected = tool;
  renderTools();
  detailEl.innerHTML = `
    <h3>${tool.name}</h3>
    <p class="muted">${tool.doc || 'No description.'}</p>
    <div class="card-actions">
      ${(tool.tags || []).map(tag => `<span class="pill">${tag}</span>`).join('') || '<span class="pill">untagged</span>'}
    </div>
    <div class="card-actions">
      <span class="muted">Args: ${(tool.args || []).map(arg => arg.name).join(', ') || 'none'}</span>
    </div>
    <div class="card-actions">
      <span class="muted">Module: ${tool.module}</span>
    </div>
    <div class="card-actions">
      <span class="muted">Path: ${tool.path}</span>
    </div>
    <pre>${buildSnippet(tool)}</pre>
  `;
}

function switchSection(sectionId) {
  sections.forEach(section => {
    section.classList.toggle('active', section.id === `section-${sectionId}`);
  });
  navItems.forEach(item => {
    item.classList.toggle('active', item.dataset.section === sectionId);
  });
}

function switchAdminPanel(panelId) {
  adminPanels.forEach(panel => {
    panel.classList.toggle('hidden', panel.dataset.adminPanel !== panelId);
  });
  adminTabs.forEach(tab => {
    tab.classList.toggle('active', tab.dataset.adminTab === panelId);
  });
}

async function loadAdminToken() {
  if (adminTokenInput.value.trim()) {
    setStatusIndicators();
    return;
  }
  try {
    const response = await fetch('/api/token');
    if (!response.ok) {
      setStatusIndicators();
      return;
    }
    const data = await response.json();
    if (data?.token) {
      adminTokenInput.value = data.token;
      localStorage.setItem('adminToken', data.token);
    }
  } catch (_) {
    // ignore
  }
  setStatusIndicators();
}

openSettingsBtn.addEventListener('click', () => {
  settingsModal.classList.remove('hidden');
});
closeSettingsBtn.addEventListener('click', () => {
  settingsModal.classList.add('hidden');
});
settingsModal.addEventListener('click', (event) => {
  if (event.target === settingsModal) {
    settingsModal.classList.add('hidden');
  }
});

searchInput.addEventListener('input', renderTools);

navItems.forEach(item => {
  item.addEventListener('click', () => switchSection(item.dataset.section));
});

adminTabs.forEach(tab => {
  tab.addEventListener('click', () => switchAdminPanel(tab.dataset.adminTab));
});

const refreshBtn = document.getElementById('refresh');
refreshBtn.addEventListener('click', async () => {
  await fetch('/refresh');
  await loadCatalog();
});

const savedToken = localStorage.getItem('adminToken');
if (savedToken) {
  adminTokenInput.value = savedToken;
}
const savedAdvanced = localStorage.getItem('advancedMode');
if (savedAdvanced === 'true') {
  advancedToggle.checked = true;
}
setStatusIndicators();
loadAdminToken();

adminTokenInput.addEventListener('input', () => {
  localStorage.setItem('adminToken', adminTokenInput.value);
  setStatusIndicators();
});
advancedToggle.addEventListener('change', () => {
  localStorage.setItem('advancedMode', advancedToggle.checked ? 'true' : 'false');
  setStatusIndicators();
});

outputClear.addEventListener('click', () => setOutput('Output cleared.', 'Idle'));
outputCopy.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(outputContent.textContent || '');
    setOutput(outputContent.textContent || '', 'Copied');
  } catch (err) {
    setOutput(`Copy failed: ${err}`, 'Error');
  }
});
outputToggle.addEventListener('click', () => {
  if (outputDrawer.classList.contains('collapsed')) {
    openDrawer();
  } else {
    closeDrawer();
  }
});

const advancedMcpToggle = document.getElementById('toggle-mcp-advanced');
const advancedMcpCall = document.getElementById('advanced-mcp-call');
advancedMcpToggle.addEventListener('change', () => {
  advancedMcpCall.classList.toggle('hidden', !advancedMcpToggle.checked);
});
advancedMcpCall.classList.add('hidden');

// Admin action bindings
const actionOpenVm = document.getElementById('action-open-vm');
const actionVmStatus = document.getElementById('action-vm-status');
const actionVmLogs = document.getElementById('action-vm-logs');
const actionLogs50 = document.getElementById('action-logs-50');
const actionLogs200 = document.getElementById('action-logs-200');
const actionLogs1000 = document.getElementById('action-logs-1000');
const actionHealthCheck = document.getElementById('action-health-check');
const actionVmDeployOps = document.getElementById('action-vm-deploy-ops');
const actionVmPull = document.getElementById('action-vm-pull');
const actionVmRestart = document.getElementById('action-vm-restart');
const actionToolsList = document.getElementById('action-tools-list');
const actionMcpHello = document.getElementById('action-mcp-hello');
const actionMcpCall = document.getElementById('action-mcp-call');

const confirmDeployOps = document.getElementById('confirm-deploy-ops');
const confirmPull = document.getElementById('confirm-pull');
const confirmVmRestart = document.getElementById('confirm-vm-restart');

const inputToolsSource = document.getElementById('select-tools-source');
const inputMcpTool = document.getElementById('input-mcp-tool');
const inputMcpArgs = document.getElementById('input-mcp-args');

function runLogs(lines) {
  runJob(['./vm/logs.sh', '--lines', String(lines)], 'logs', false, false);
}

actionOpenVm.addEventListener('click', () => {
  switchSection('admin');
  switchAdminPanel('vm');
});

actionVmStatus.addEventListener('click', () => runJob(['./vm/status.sh'], 'status', false, false));
actionVmLogs.addEventListener('click', () => runLogs(200));
actionLogs50.addEventListener('click', () => runLogs(50));
actionLogs200.addEventListener('click', () => runLogs(200));
actionLogs1000.addEventListener('click', () => runLogs(1000));
actionHealthCheck.addEventListener('click', () => runJob(['./vm/health_check.sh'], 'health', false, false));

actionVmDeployOps.addEventListener('click', () => {
  if (!confirmDeployOps.checked) {
    setOutput('Confirmation required before deploy.', 'Error');
    return;
  }
  runJob(['./vm/deploy.sh'], 'deploy', true, false);
});

actionVmRestart.addEventListener('click', () => {
  if (!confirmVmRestart.checked) {
    setOutput('Confirmation required before restart.', 'Error');
    return;
  }
  runJob(['./vm/deploy.sh', '--restart-only'], 'restart', true, false);
});

actionVmPull.addEventListener('click', () => {
  if (!confirmPull.checked) {
    setOutput('Confirmation required before pull.', 'Error');
    return;
  }
  runJob(['./vm/pull_server_from_vm.sh'], 'pull', true, false);
});

actionToolsList.addEventListener('click', () => {
  const source = inputToolsSource.value;
  if (source === 'local') {
    runJob(['./vm/mcp_curl.sh', '--list', '--local'], 'toolsList', false, false);
  } else {
    runJob(['./vm/mcp_curl.sh', '--list'], 'toolsList', false, false);
  }
});

actionMcpHello.addEventListener('click', () => {
  runJob(['./vm/mcp_curl.sh', 'hello', '{"name":"Jordane"}'], 'mcp', false, true);
});

actionMcpCall.addEventListener('click', () => {
  const tool = inputMcpTool.value.trim();
  if (!tool) {
    setOutput('Tool name is required.', 'Error');
    return;
  }
  if (!/^[a-zA-Z0-9_-]+$/.test(tool)) {
    setOutput('Tool name must match ^[a-zA-Z0-9_-]+$.', 'Error');
    return;
  }
  if (!advancedToggle.checked && !SAFE_TOOLS.has(tool)) {
    setOutput('Tool not allowed without Advanced mode.', 'Error');
    return;
  }
  let argsText = inputMcpArgs.value.trim() || '{}';
  let argsObj;
  try {
    argsObj = JSON.parse(argsText);
  } catch (error) {
    setOutput(`Invalid JSON args: ${error}`, 'Error');
    return;
  }
  if (typeof argsObj !== 'object' || Array.isArray(argsObj) || argsObj === null) {
    setOutput('JSON args must be an object.', 'Error');
    return;
  }
  runJob(['./vm/mcp_curl.sh', tool, JSON.stringify(argsObj)], 'mcp', false, true);
});

loadCatalog();
updateOverview();
switchAdminPanel('overview');
closeDrawer();
