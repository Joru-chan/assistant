let catalog = null;

const toolGrid = document.getElementById('tool-grid');
const pinnedSection = document.getElementById('pinned-section');
const pinnedGrid = document.getElementById('pinned-grid');
const pinnedCount = document.getElementById('pinned-count');
const tagFilter = document.getElementById('tag-filter');
const filterPinned = document.getElementById('filter-pinned');
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
const DANGEROUS_PATTERN = /(deploy|restart|delete|remove|update|apply|set_env|write|create_)/i;

const PINNED_KEY = 'pinnedTools';
const jobMeta = new Map();

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

function getPinnedTools() {
  try {
    const raw = localStorage.getItem(PINNED_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch (_) {
    return [];
  }
}

function setPinnedTools(items) {
  localStorage.setItem(PINNED_KEY, JSON.stringify(items));
}

function togglePinned(name) {
  const current = new Set(getPinnedTools());
  if (current.has(name)) {
    current.delete(name);
  } else {
    current.add(name);
  }
  setPinnedTools(Array.from(current));
}

function requiresConfirm(name) {
  return name.startsWith('admin_') || DANGEROUS_PATTERN.test(name);
}

function isToolAllowed(name) {
  if (advancedToggle.checked) {
    return true;
  }
  return SAFE_TOOLS.has(name);
}

function firstNonEmptyLine(text) {
  return (text || '').split('\n').map(line => line.trim()).find(Boolean) || '';
}

function extractSummary(output) {
  if (!output) {
    return '';
  }
  try {
    const parsed = JSON.parse(output);
    const result = parsed.result || parsed;
    if (result?.structuredContent?.summary) {
      return result.structuredContent.summary;
    }
    const text = result?.content?.[0]?.text;
    if (text) {
      try {
        const nested = JSON.parse(text);
        if (nested?.summary) {
          return nested.summary;
        }
      } catch (_) {
        return firstNonEmptyLine(text);
      }
    }
  } catch (_) {
    return firstNonEmptyLine(output);
  }
  return '';
}

function formatToolHeader(job, meta) {
  const status = job.exit_code === 0 ? 'ok' : 'error';
  const when = new Date(job.updated_at || job.started_at || Date.now()).toLocaleString();
  const summary = extractSummary(job.stdout || '') || firstNonEmptyLine(job.stderr || '');
  const summaryLine = summary ? `Summary: ${summary}` : 'Summary: (none)';
  return [
    `Tool: ${meta.toolName} • ${when}`,
    `Status: ${status}`,
    summaryLine,
    '',
  ].join('\n');
}

function updateOverview() {
  overviewLastDeploy.textContent = historyState.deploy.lastRun === 'never' ? 'Never.' : historyState.deploy.lastRun;
}

function setStatusIndicators() {
  statusAdminToken.textContent = adminTokenInput.value.trim() ? 'Admin token: ✓' : 'Admin token: missing';
  statusAdvanced.textContent = advancedToggle.checked ? 'Advanced: on' : 'Advanced: off';
  document.body.classList.toggle('advanced-on', advancedToggle.checked);
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
    const meta = jobMeta.get(jobId);
    let output = formatJobOutput(data);
    if (meta && meta.type === 'tool' && data.done) {
      output = `${formatToolHeader(data, meta)}${output}`;
    }
    setOutput(output, data.done ? 'Done' : 'Running');
    if (data.done) {
      clearInterval(timer);
      jobMeta.delete(jobId);
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

function runJob(cmd, actionKey, confirm, advanced, meta) {
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
    if (meta) {
      jobMeta.set(data.job_id, meta);
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
    updateTagOptions();
    renderTools();
    metaEl.textContent = `Last built ${catalog.generated_at} — ${catalog.tool_count} tools`;
  } catch (error) {
    metaEl.textContent = `Failed to load catalog: ${error}`;
    toolGrid.innerHTML = '<div class="muted">Catalog unavailable. Use Refresh to retry.</div>';
  }
}

function buildSnippet(tool) {
  const argsObj = {};
  (tool.args || []).forEach(arg => {
    argsObj[arg.name] = '';
  });
  const jsonArgs = JSON.stringify(argsObj, null, 2);
  return `./vm/mcp_curl.sh ${tool.name} '${jsonArgs.replace(/\n/g, '\\n')}'`;
}

function normalizeDefault(value) {
  if (!value || value === 'None') {
    return '';
  }
  if (value.startsWith("'") && value.endsWith("'")) {
    return value.slice(1, -1);
  }
  if (value.startsWith('"') && value.endsWith('"')) {
    return value.slice(1, -1);
  }
  return value;
}

function parseValue(raw) {
  const trimmed = raw.trim();
  if (!trimmed) {
    return '';
  }
  try {
    return JSON.parse(trimmed);
  } catch (_) {
    return trimmed;
  }
}

function updateTagOptions() {
  if (!catalog) {
    return;
  }
  const tags = new Set();
  (catalog.tools || []).forEach(tool => {
    (tool.tags || []).forEach(tag => tags.add(tag));
  });
  const sorted = Array.from(tags).sort();
  tagFilter.innerHTML = '<option value="all">All tags</option>';
  sorted.forEach(tag => {
    const option = document.createElement('option');
    option.value = tag;
    option.textContent = tag;
    tagFilter.appendChild(option);
  });
}

function buildToolCard(tool, pinned) {
  const card = document.createElement('div');
  const confirmNeeded = requiresConfirm(tool.name);
  card.className = `card tool-card ${confirmNeeded ? 'danger' : 'action'}`;

  const header = document.createElement('div');
  header.className = 'tool-header';

  const titleWrap = document.createElement('div');
  const title = document.createElement('div');
  title.className = 'tool-title';
  title.textContent = tool.name;
  const desc = document.createElement('div');
  desc.className = 'tool-desc';
  desc.textContent = tool.doc || 'No description yet.';
  titleWrap.appendChild(title);
  titleWrap.appendChild(desc);

  const pinButton = document.createElement('button');
  pinButton.className = `btn btn-icon pin-button${pinned ? ' active' : ''}`;
  pinButton.textContent = pinned ? '★' : '☆';
  pinButton.title = pinned ? 'Unpin' : 'Pin';
  pinButton.addEventListener('click', () => {
    togglePinned(tool.name);
    renderTools();
  });

  header.appendChild(titleWrap);
  header.appendChild(pinButton);
  card.appendChild(header);

  if (tool.tags && tool.tags.length) {
    const tagWrap = document.createElement('div');
    tagWrap.className = 'tool-tags';
    tool.tags.slice(0, 4).forEach(tag => {
      const chip = document.createElement('span');
      chip.className = 'tag';
      chip.textContent = tag;
      tagWrap.appendChild(chip);
    });
    card.appendChild(tagWrap);
  }

  if (confirmNeeded) {
    const badge = document.createElement('span');
    badge.className = 'badge';
    badge.textContent = 'Confirm required';
    card.appendChild(badge);
  }

  const actions = document.createElement('div');
  actions.className = 'tool-actions';

  const confirmLabel = document.createElement('label');
  confirmLabel.className = `check-row confirm${confirmNeeded ? '' : ' hidden'}`;
  const confirmInput = document.createElement('input');
  confirmInput.type = 'checkbox';
  confirmLabel.appendChild(confirmInput);
  confirmLabel.appendChild(document.createTextNode('Confirm'));

  const runBtn = document.createElement('button');
  runBtn.className = 'btn btn-primary';
  runBtn.textContent = 'Run';

  const configBtn = document.createElement('button');
  configBtn.className = 'btn btn-secondary';
  configBtn.textContent = 'Configure';

  actions.appendChild(confirmLabel);
  actions.appendChild(runBtn);
  actions.appendChild(configBtn);
  card.appendChild(actions);

  const configPanel = document.createElement('div');
  configPanel.className = 'tool-config hidden';

  const tabs = document.createElement('div');
  tabs.className = 'config-tabs';
  const simpleTab = document.createElement('button');
  simpleTab.className = 'config-tab active';
  simpleTab.textContent = 'Simple';
  const jsonTab = document.createElement('button');
  jsonTab.className = 'config-tab';
  jsonTab.textContent = 'JSON';
  tabs.appendChild(simpleTab);
  tabs.appendChild(jsonTab);
  configPanel.appendChild(tabs);

  const simplePanel = document.createElement('div');
  simplePanel.className = 'config-panel active';
  const rows = document.createElement('div');
  rows.className = 'kv-rows';
  (tool.args || []).forEach(arg => {
    const row = document.createElement('div');
    row.className = 'kv-row';
    const keyInput = document.createElement('input');
    keyInput.className = 'kv-key';
    keyInput.value = arg.name;
    keyInput.placeholder = 'key';
    const valueInput = document.createElement('input');
    valueInput.className = 'kv-value';
    valueInput.placeholder = 'value';
    valueInput.value = normalizeDefault(arg.default || '');
    const removeBtn = document.createElement('button');
    removeBtn.className = 'btn btn-icon kv-remove';
    removeBtn.textContent = '×';
    removeBtn.title = 'Remove field';
    removeBtn.addEventListener('click', () => row.remove());
    row.appendChild(keyInput);
    row.appendChild(valueInput);
    row.appendChild(removeBtn);
    rows.appendChild(row);
  });
  if (!(tool.args || []).length) {
    const row = document.createElement('div');
    row.className = 'kv-row';
    const keyInput = document.createElement('input');
    keyInput.className = 'kv-key';
    keyInput.placeholder = 'key';
    const valueInput = document.createElement('input');
    valueInput.className = 'kv-value';
    valueInput.placeholder = 'value';
    const removeBtn = document.createElement('button');
    removeBtn.className = 'btn btn-icon kv-remove';
    removeBtn.textContent = '×';
    removeBtn.title = 'Remove field';
    removeBtn.addEventListener('click', () => row.remove());
    row.appendChild(keyInput);
    row.appendChild(valueInput);
    row.appendChild(removeBtn);
    rows.appendChild(row);
  }
  const addRowBtn = document.createElement('button');
  addRowBtn.className = 'btn btn-ghost btn-sm';
  addRowBtn.textContent = 'Add field';
  addRowBtn.addEventListener('click', () => {
    const row = document.createElement('div');
    row.className = 'kv-row';
    const keyInput = document.createElement('input');
    keyInput.className = 'kv-key';
    keyInput.placeholder = 'key';
    const valueInput = document.createElement('input');
    valueInput.className = 'kv-value';
    valueInput.placeholder = 'value';
    const removeBtn = document.createElement('button');
    removeBtn.className = 'btn btn-icon kv-remove';
    removeBtn.textContent = '×';
    removeBtn.title = 'Remove field';
    removeBtn.addEventListener('click', () => row.remove());
    row.appendChild(keyInput);
    row.appendChild(valueInput);
    row.appendChild(removeBtn);
    rows.appendChild(row);
  });
  simplePanel.appendChild(rows);
  simplePanel.appendChild(addRowBtn);

  const jsonPanel = document.createElement('div');
  jsonPanel.className = 'config-panel';
  const jsonArea = document.createElement('textarea');
  jsonArea.rows = 4;
  jsonArea.value = '{}';
  jsonPanel.appendChild(jsonArea);

  configPanel.appendChild(simplePanel);
  configPanel.appendChild(jsonPanel);

  const runConfigBtn = document.createElement('button');
  runConfigBtn.className = 'btn btn-primary btn-sm';
  runConfigBtn.textContent = 'Run with args';
  configPanel.appendChild(runConfigBtn);

  const commandDetails = document.createElement('details');
  commandDetails.className = 'advanced-only';
  const summary = document.createElement('summary');
  summary.textContent = 'Show command';
  const pre = document.createElement('pre');
  pre.textContent = buildSnippet(tool);
  commandDetails.appendChild(summary);
  commandDetails.appendChild(pre);
  configPanel.appendChild(commandDetails);

  card.appendChild(configPanel);

  function ensureConfirm() {
    if (confirmNeeded && !confirmInput.checked) {
      setOutput('Confirmation required to run this tool.', 'Error');
      return false;
    }
    return true;
  }

  function ensureSafe() {
    if (!isToolAllowed(tool.name)) {
      setOutput('Enable Advanced mode to run this tool.', 'Error');
      return false;
    }
    return true;
  }

  runBtn.addEventListener('click', () => {
    if (!ensureSafe() || !ensureConfirm()) {
      return;
    }
    runJob(
      ['./vm/mcp_curl.sh', tool.name, '{}'],
      'mcp',
      confirmNeeded,
      advancedToggle.checked,
      { type: 'tool', toolName: tool.name }
    );
  });

  configBtn.addEventListener('click', () => {
    const open = !configPanel.classList.contains('hidden');
    configPanel.classList.toggle('hidden', open);
    configBtn.textContent = open ? 'Configure' : 'Hide';
  });

  simpleTab.addEventListener('click', () => {
    simpleTab.classList.add('active');
    jsonTab.classList.remove('active');
    simplePanel.classList.add('active');
    jsonPanel.classList.remove('active');
  });
  jsonTab.addEventListener('click', () => {
    jsonTab.classList.add('active');
    simpleTab.classList.remove('active');
    jsonPanel.classList.add('active');
    simplePanel.classList.remove('active');
  });

  runConfigBtn.addEventListener('click', () => {
    if (!ensureSafe() || !ensureConfirm()) {
      return;
    }
    let args = {};
    if (jsonPanel.classList.contains('active')) {
      try {
        const parsed = JSON.parse(jsonArea.value || '{}');
        if (typeof parsed !== 'object' || Array.isArray(parsed) || parsed === null) {
          setOutput('JSON args must be an object.', 'Error');
          return;
        }
        args = parsed;
      } catch (error) {
        setOutput(`Invalid JSON args: ${error}`, 'Error');
        return;
      }
    } else {
      const rowsNodes = rows.querySelectorAll('.kv-row');
      rowsNodes.forEach(row => {
        const inputs = row.querySelectorAll('input');
        const key = inputs[0]?.value?.trim();
        const value = inputs[1]?.value ?? '';
        if (key) {
          args[key] = parseValue(value);
        }
      });
    }
    runJob(
      ['./vm/mcp_curl.sh', tool.name, JSON.stringify(args)],
      'mcp',
      confirmNeeded,
      advancedToggle.checked,
      { type: 'tool', toolName: tool.name }
    );
  });

  return card;
}

function renderTools() {
  const query = searchInput.value.toLowerCase();
  const tag = tagFilter.value;
  const pinned = new Set(getPinnedTools());
  const showPinnedOnly = filterPinned.checked;
  const tools = (catalog?.tools || [])
    .filter(tool => !tool.name.endsWith('.register'))
    .filter(tool => {
      const haystack = [tool.name, tool.doc, (tool.tags || []).join(' ')].join(' ').toLowerCase();
      const tagMatch = tag === 'all' || (tool.tags || []).includes(tag);
      return haystack.includes(query) && tagMatch;
    });

  const pinnedTools = tools.filter(tool => pinned.has(tool.name));
  pinnedCount.textContent = `${pinnedTools.length} pinned`;

  pinnedGrid.innerHTML = '';
  toolGrid.innerHTML = '';

  if (!showPinnedOnly && pinnedTools.length) {
    pinnedSection.classList.remove('hidden');
    pinnedTools.forEach(tool => {
      pinnedGrid.appendChild(buildToolCard(tool, true));
    });
  } else {
    pinnedSection.classList.add('hidden');
  }

  const mainTools = showPinnedOnly ? pinnedTools : tools.filter(tool => !pinned.has(tool.name));
  if (!mainTools.length) {
    toolGrid.innerHTML = '<div class="muted">No tools match your search.</div>';
    return;
  }

  mainTools.forEach(tool => {
    toolGrid.appendChild(buildToolCard(tool, pinned.has(tool.name)));
  });
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
tagFilter.addEventListener('change', renderTools);
filterPinned.addEventListener('change', renderTools);

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
const logLineRadios = document.querySelectorAll('input[name="log-lines"]');
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
actionVmLogs.addEventListener('click', () => {
  const selected = Array.from(logLineRadios).find(radio => radio.checked);
  const value = selected ? parseInt(selected.value, 10) : 200;
  runLogs(value);
});
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
