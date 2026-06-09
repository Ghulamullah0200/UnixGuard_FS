/* ═══════════════════════════════════════════════════════════
   UnixGuard FS & VM — Frontend Application Logic
   ═══════════════════════════════════════════════════════════ */

const API = '';
let treeData = null;
let currentSelectedNodeId = null;
let commandHistory = [];
let historyIndex = -1;

// ── Init ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    switchTab('dashboard');
    setupTerminal();
});

// ── Mobile Sidebar Toggle ────────────────────────────────
function toggleMobileMenu() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const isOpen = sidebar.classList.contains('open');
    if (isOpen) {
        sidebar.classList.remove('open');
        overlay.classList.remove('open');
    } else {
        sidebar.classList.add('open');
        overlay.classList.add('open');
    }
}

// ── Navigation ───────────────────────────────────────────
function switchTab(tab) {
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.getElementById('panel-' + tab)?.classList.add('active');
    document.querySelector(`.nav-item[data-tab="${tab}"]`)?.classList.add('active');

    // Close sidebar on mobile after navigation
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar && sidebar.classList.contains('open')) {
        sidebar.classList.remove('open');
        overlay.classList.remove('open');
    }
    
    if (tab === 'dashboard') loadDashboard();
    if (tab === 'explorer') loadExplorer();
    if (tab === 'diskmap') loadDiskMap();
    if (tab === 'vm') loadVMWorkspace();
}

// ── Toast ────────────────────────────────────────────────
function showToast(msg, type = 'info') {
    const c = document.getElementById('toast-container');
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.innerHTML = `<span>${type === 'success' ? '[OK]' : type === 'error' ? '[ERR]' : '[INFO]'}</span><span>${msg}</span>`;
    c.appendChild(t);
    setTimeout(() => {
        t.style.opacity = '0';
        t.style.transform = 'translateX(100%)';
        setTimeout(() => t.remove(), 300);
    }, 4000);
}

// ── API Helper ───────────────────────────────────────────
async function api(url, opts = {}) {
    try {
        const headers = { 'Content-Type': 'application/json' };
        const response = await fetch(API + url, { headers, ...opts });
        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${response.status}`);
        }
        return await response.json();
    } catch (e) {
        showToast(e.message, 'error');
        throw e;
    }
}

// ═══ DASHBOARD ═══════════════════════════════════════════
async function loadDashboard() {
    try {
        const usage = await api('/api/disk/usage');
        const tree = await api('/api/nodes/tree');
        let procs = [];
        try { procs = await api('/api/vm/processes'); } catch {}

        treeData = tree;

        // Render Stats Grid
        const diskPct = ((usage.used_blocks / usage.total_blocks) * 100).toFixed(0);
        document.getElementById('stats-grid').innerHTML = `
            <div class="stat-card">
                <div class="stat-label">Disk Storage Used</div>
                <div class="stat-value">${(usage.used_space_bytes / 1024).toFixed(1)} KB</div>
                <div style="font-size:0.8rem;color:var(--text-muted);margin-top:4px;">${usage.used_blocks}/${usage.total_blocks} Blocks (${diskPct}%)</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Disk Free Space</div>
                <div class="stat-value" style="color:var(--accent-green)">${(usage.free_space_bytes / 1024).toFixed(1)} KB</div>
                <div style="font-size:0.8rem;color:var(--text-muted);margin-top:4px;">${usage.free_blocks} Blocks Available</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Inodes</div>
                <div class="stat-value" style="color:var(--accent-purple)">${countInodesInTree(tree)}</div>
                <div style="font-size:0.8rem;color:var(--text-muted);margin-top:4px;">Files, dirs, &amp; links</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">VM Processes</div>
                <div class="stat-value" style="color:var(--accent-yellow)">${procs.length}</div>
                <div style="font-size:0.8rem;color:var(--text-muted);margin-top:4px;">Active Ring 3 threads</div>
            </div>
        `;

        // Render dashboard tree preview
        document.getElementById('dashboard-tree').innerHTML = renderTreeHTML(tree, true);

        // Render progress bar
        const bar = document.getElementById('disk-bar');
        bar.style.width = `${diskPct}%`;
        document.getElementById('disk-used-label').textContent = `${(usage.used_space_bytes / 1024).toFixed(1)} KB Used`;
        document.getElementById('disk-free-label').textContent = `${(usage.free_space_bytes / 1024).toFixed(1)} KB Free`;

        // Quick block summary
        document.getElementById('quick-block-summary').innerHTML = `
            <div>Superblock: <strong>1 Block (512B)</strong></div>
            <div>Inode Table: <strong>32 Blocks (16 KB)</strong></div>
            <div>Data Blocks: <strong>223 Blocks (111.5 KB)</strong></div>
            <div style="margin-top: 8px; font-size: 0.8rem; color:var(--text-muted)">* Files dynamically occupy blocks as content grows/shrinks.</div>
        `;
    } catch (e) {
        console.error('Dashboard load error:', e);
    }
}

function countInodesInTree(node) {
    if (!node) return 0;
    let count = 1;
    if (node.children) {
        node.children.forEach(c => { count += countInodesInTree(c); });
    }
    return count;
}

// ═══ FILE EXPLORER ═══════════════════════════════════════
async function loadExplorer() {
    try {
        const tree = await api('/api/nodes/tree');
        treeData = tree;
        document.getElementById('explorer-tree').innerHTML = renderTreeHTML(tree, true);
    } catch {}
}

function renderTreeHTML(node, expanded = false) {
    if (!node || !node.name) return '';
    const isDir = node.node_type === 'directory';
    const isSym = node.node_type === 'symlink';
    const icon = isDir ? '[DIR]' : isSym ? '[LNK]' : '[TXT]';
    const iconClass = isDir ? 'dir' : isSym ? 'symlink' : 'file';
    let html = `<div class="tree-node" onclick="selectNode(${node.id}, event)" data-id="${node.id}">`;
    if (isDir) {
        html += `<span class="tree-toggle" onclick="toggleTree(this, event)">${expanded ? '▼' : '▶'}</span>`;
    } else {
        html += `<span style="width:16px"></span>`;
    }
    html += `<span class="node-icon ${iconClass}">${icon}</span><span style="margin-left:4px">${node.name}</span>`;
    html += `<span style="margin-left:auto;font-size:0.75rem;color:var(--text-muted);font-family:var(--font-mono)">${node.size_bytes}B</span>`;
    html += `</div>`;
    if (isDir && node.children) {
        html += `<div class="tree-children" style="display:${expanded ? 'block' : 'none'}">`;
        for (const c of node.children) html += renderTreeHTML(c, false);
        html += `</div>`;
    }
    return html;
}

function toggleTree(el, e) {
    e.stopPropagation();
    const children = el.closest('.tree-node').nextElementSibling;
    if (children && children.classList.contains('tree-children')) {
        const show = children.style.display === 'none';
        children.style.display = show ? 'block' : 'none';
        el.textContent = show ? '▼' : '▶';
    }
}

async function selectNode(id, e) {
    if (e) e.stopPropagation();
    currentSelectedNodeId = id;
    document.querySelectorAll('.tree-node').forEach(n => n.classList.remove('selected'));
    document.querySelector(`.tree-node[data-id="${id}"]`)?.classList.add('selected');
    
    try {
        const n = await api(`/api/nodes/${id}`);
        const broken = n.is_broken_symlink ? '<span class="badge badge-danger">BROKEN</span>' : '';
        const blocksStr = n.allocated_blocks.length ? n.allocated_blocks.join(', ') : 'None';
        
        let contentSection = '';
        if (n.node_type === 'file') {
            contentSection = `
                <div class="form-group" style="margin-top: 16px;">
                    <label class="form-label">File Content (Editable)</label>
                    <textarea id="edit-node-content" class="form-textarea" rows="5">${n.content || ''}</textarea>
                    <div style="margin-top:8px; display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:0.8rem;color:var(--text-muted)">Modifying size updates disk block allocations automatically.</span>
                        <button class="btn btn-primary btn-sm" onclick="saveFileContent(${n.id})">Save Content</button>
                    </div>
                </div>
            `;
        }

        document.getElementById('node-detail').innerHTML = `
            <div class="detail-grid">
                <div class="detail-item"><div class="detail-label">Name</div><div class="detail-value">${n.name}</div></div>
                <div class="detail-item"><div class="detail-label">Full Path</div><div class="detail-value">${n.path}</div></div>
                <div class="detail-item"><div class="detail-label">Type</div><div class="detail-value"><span class="badge badge-running">${n.node_type}</span> ${broken}</div></div>
                <div class="detail-item"><div class="detail-label">Inode Number</div><div class="detail-value">${n.inode_number}</div></div>
                <div class="detail-item"><div class="detail-label">Size (Bytes)</div><div class="detail-value">${n.size_bytes} Bytes</div></div>
                <div class="detail-item"><div class="detail-label">Links count</div><div class="detail-value">${n.link_count} hardlink(s)</div></div>
                <div class="detail-item" style="grid-column: span 2;">
                    <div class="detail-label">Physical Disk Blocks Map</div>
                    <div class="detail-value" style="color:var(--accent-cyan)">[${blocksStr}] (${n.allocated_blocks.length} block(s) of 512B)</div>
                </div>
                <div class="detail-item"><div class="detail-label">Created At</div><div class="detail-value">${formatDate(n.created_at)}</div></div>
                <div class="detail-item"><div class="detail-label">Modified At</div><div class="detail-value">${formatDate(n.modified_at)}</div></div>
                ${n.target_path ? `<div class="detail-item" style="grid-column: span 2;"><div class="detail-label">Symbolic Path Target</div><div class="detail-value" style="color:var(--accent-purple)">${n.target_path}</div></div>` : ''}
            </div>
            ${contentSection}
            <div class="btn-group" style="margin-top: 16px;">
                <button class="btn btn-danger btn-sm" onclick="deleteSelectedNode(${n.id})">Delete Node (rm/rmdir)</button>
            </div>
        `;
    } catch {
        document.getElementById('node-detail').innerHTML = '<div class="empty-state"><p>Error retrieving details</p></div>';
    }
}

async function saveFileContent(nodeId) {
    const content = document.getElementById('edit-node-content').value;
    try {
        await api(`/api/nodes/${nodeId}/content`, { method: 'PUT', body: JSON.stringify({ content }) });
        showToast('File saved and block allocations updated', 'success');
        selectNode(nodeId);
        loadExplorer();
    } catch {}
}

async function deleteSelectedNode(nodeId) {
    if (!confirm('Are you sure you want to remove this node? This frees its disk blocks.')) return;
    try {
        await api(`/api/nodes/${nodeId}`, { method: 'DELETE' });
        showToast('Node removed successfully', 'success');
        document.getElementById('node-detail').innerHTML = `
            <div class="empty-state">
                <div class="icon">[DIR]</div>
                <p>Select a node from the tree to view properties</p>
            </div>
        `;
        loadExplorer();
    } catch {}
}

function toggleCreateFields() {
    const type = document.getElementById('create-type').value;
    const contentGrp = document.getElementById('group-content');
    const targetGrp = document.getElementById('group-target');
    
    if (type === 'file') {
        contentGrp.classList.remove('d-none');
        targetGrp.classList.add('d-none');
    } else if (type === 'symlink') {
        contentGrp.classList.add('d-none');
        targetGrp.classList.remove('d-none');
    } else {
        contentGrp.classList.add('d-none');
        targetGrp.classList.add('d-none');
    }
}

async function createNewNode() {
    const name = document.getElementById('create-name').value.trim();
    const type = document.getElementById('create-type').value;
    const content = document.getElementById('create-content').value;
    const target = document.getElementById('create-target').value.trim();
    
    if (!name) {
        showToast('Please specify a node name', 'error');
        return;
    }

    const parentId = currentSelectedNodeId || treeData.id;

    try {
        const payload = {
            name,
            node_type: type,
            parent_id: parentId,
            content: type === 'file' ? content : null,
            target_path: type === 'symlink' ? target : null
        };

        const res = await api('/api/nodes', { method: 'POST', body: JSON.stringify(payload) });
        showToast(`Created node '${res.name}' successfully`, 'success');
        
        // Reset fields
        document.getElementById('create-name').value = '';
        document.getElementById('create-content').value = '';
        document.getElementById('create-target').value = '';
        
        loadExplorer();
    } catch {}
}

function formatDate(d) {
    return d ? new Date(d).toLocaleString() : 'N/A';
}

// ═══ DISK BLOCK MAP ═══════════════════════════════════════
async function loadDiskMap() {
    try {
        const layout = await api('/api/disk/layout');
        const grid = document.getElementById('disk-block-grid');
        grid.innerHTML = '';

        layout.forEach(b => {
            const el = document.createElement('div');
            el.className = `disk-block block-type-${b.block_type}`;
            el.textContent = b.block_number;
            el.dataset.block = JSON.stringify(b);
            
            // Hover inspection
            el.addEventListener('mouseover', () => inspectBlock(b));
            el.addEventListener('click', () => highlightBlocks(b.inode_number));
            
            grid.appendChild(el);
        });
    } catch {}
}

function inspectBlock(b) {
    const insp = document.getElementById('block-inspector-content');
    
    let subtitle = 'Free block';
    let blockInfo = '';

    if (b.block_type === 'superblock') {
        subtitle = 'Superblock (Block 0)';
        blockInfo = '<p>Stores disk metadata: total size, block size, inode counts, free block lists.</p>';
    } else if (b.block_type === 'inode_table') {
        subtitle = `Inode Table (Block ${b.block_number})`;
        blockInfo = '<p>Holds active inodes. Each active file or directory has an entry in this array structure.</p>';
    } else if (b.block_type === 'allocated_data') {
        subtitle = `Allocated Data Block ${b.block_number}`;
        blockInfo = `
            <div style="margin-top: 10px; display:flex; flex-direction:column; gap:6px;">
                <div><strong>Owner Inode:</strong> Inode ${b.inode_number}</div>
                <div><strong>Allocation details:</strong> ${b.detail}</div>
                <div><strong>File data chunk:</strong> Block Index ${b.block_index} of this inode's contents</div>
                <div style="color:var(--text-muted); font-size:0.8rem; margin-top:4px;">* Click on this block to highlight all other blocks containing this file.</div>
            </div>
        `;
    } else {
        blockInfo = '<p>Unallocated block. Ready to store new files or directory tables.</p>';
    }

    insp.innerHTML = `
        <div style="padding: 10px; background:var(--bg-input); border-radius:var(--radius); border:1px solid var(--border)">
            <h4 style="color:var(--accent-cyan)">${subtitle}</h4>
            <div style="margin-top:8px; font-size:0.9rem; line-height:1.5">${blockInfo}</div>
        </div>
    `;
}

function highlightBlocks(inodeNumber) {
    document.querySelectorAll('.disk-block').forEach(el => {
        el.classList.remove('block-type-highlight');
        if (inodeNumber !== null && el.dataset.block) {
            const b = JSON.parse(el.dataset.block);
            if (b.inode_number === inodeNumber && b.block_type === 'allocated_data') {
                el.classList.add('block-type-highlight');
            }
        }
    });
}

// ═══ TERMINAL SIMULATOR ══════════════════════════════════
function setupTerminal() {
    const input = document.getElementById('terminal-input');
    if (!input) return;

    input.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter') {
            const cmd = input.value.trim();
            if (!cmd) return;
            commandHistory.unshift(cmd);
            historyIndex = -1;
            input.value = '';

            const promptText = document.getElementById('terminal-prompt').textContent;
            appendTermOutput(`<span style="color:var(--accent-cyan)">${promptText}</span> ${escapeHtml(cmd)}`);

            if (cmd === 'clear') {
                document.getElementById('terminal-output').innerHTML = '';
                return;
            }

            try {
                const r = await api('/api/terminal/execute', { method: 'POST', body: JSON.stringify({ command: cmd }) });
                
                if (r.output && r.output !== '\x1b[CLEAR]') {
                    appendTermOutput(r.error ? `<span class="error">${escapeHtml(r.output)}</span>` : escapeHtml(r.output));
                }
                if (r.output === '\x1b[CLEAR]') {
                    document.getElementById('terminal-output').innerHTML = '';
                }
                document.getElementById('terminal-prompt').textContent = `root@unix-vfs:${r.cwd}$`;
            } catch {
                appendTermOutput('<span class="error">Simulation runtime error.</span>');
            }
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (historyIndex < commandHistory.length - 1) {
                historyIndex++;
                input.value = commandHistory[historyIndex];
            }
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (historyIndex > 0) {
                historyIndex--;
                input.value = commandHistory[historyIndex];
            } else {
                historyIndex = -1;
                input.value = '';
            }
        }
    });
}

function appendTermOutput(html) {
    const out = document.getElementById('terminal-output');
    if (!out) return;
    const div = document.createElement('div');
    div.innerHTML = html;
    out.appendChild(div);
    out.scrollTop = out.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/\n/g, '<br>');
}

// ═══ CPU SCHEDULER ═══════════════════════════════════════
function toggleQuantum() {
    const alg = document.getElementById('sched-alg').value;
    const qGrp = document.getElementById('sched-quantum-group');
    qGrp.style.display = alg === 'rr' ? 'block' : 'none';
}

async function runScheduler() {
    const algo = document.getElementById('sched-alg').value;
    const quantum = parseInt(document.getElementById('sched-quantum').value) || 2;
    
    try {
        const res = await api(`/api/scheduler/demo?algorithm=${algo}&quantum=${quantum}`);
        const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#f97316', '#06b6d4'];
        
        const ganttHTML = res.gantt.map(g => {
            const width = Math.max(g.end - g.start, 1) * 45;
            const col = colors[(g.job_id - 1) % colors.length];
            return `
                <div class="gantt-block" style="width:${width}px; background:${col}; color:#000" title="${g.name}: [${g.start} - ${g.end}]">
                    <div>J${g.job_id}</div>
                    <div style="font-size:0.65rem;opacity:0.8">${g.start}-${g.end}</div>
                </div>
            `;
        }).join('');

        document.getElementById('scheduler-results-container').innerHTML = `
            <div class="card" style="padding:20px">
                <h3 style="margin-bottom:14px;color:var(--accent-cyan)">Scheduling Mode: ${res.algorithm}</h3>
                <div class="stats-grid" style="margin-bottom:16px">
                    <div class="stat-card">
                        <div class="stat-label">Average Waiting Time</div>
                        <div class="stat-value" style="color:var(--accent-green)">${res.avg_waiting_time} ms</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Average Turnaround</div>
                        <div class="stat-value" style="color:var(--accent-blue)">${res.avg_turnaround_time} ms</div>
                    </div>
                </div>
                
                <h4 style="margin-bottom:8px">Gantt Execution Timeline</h4>
                <div class="gantt-container"><div class="gantt-chart">${ganttHTML}</div></div>

                <h4 style="margin-top:20px;margin-bottom:8px">Simulation Process Metrics</h4>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Job ID</th>
                                <th>Task Name</th>
                                <th>Arrival Time</th>
                                <th>Burst Time</th>
                                <th>Priority</th>
                                <th>Start</th>
                                <th>Completion</th>
                                <th>Wait Time</th>
                                <th>Turnaround</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${res.jobs.map(j => `
                                <tr>
                                    <td>J${j.job_id}</td>
                                    <td style="font-family:var(--font-mono)">${j.name}</td>
                                    <td>${j.arrival_time}</td>
                                    <td>${j.burst_time}</td>
                                    <td>${j.priority}</td>
                                    <td>${j.start_time}</td>
                                    <td>${j.completion_time}</td>
                                    <td style="color:var(--accent-green)">${j.waiting_time} ms</td>
                                    <td style="color:var(--accent-blue)">${j.turnaround_time} ms</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    } catch {}
}

// ═══ VIRTUAL MEMORY SIMULATOR ════════════════════════════
let currentSelectedPageNum = 0;
let lastActiveProcessId = null;

function selectVMPage(pageNum) {
    currentSelectedPageNum = pageNum;
    loadVMProcessDetails();
}

async function loadVMWorkspace() {
    await loadVMProcesses();
    await loadPhysicalLayouts();
}

async function loadVMProcesses() {
    try {
        const procs = await api('/api/vm/processes');
        const sel = document.getElementById('vm-active-process');
        const oldVal = sel.value;
        
        sel.innerHTML = '<option value="">-- Select Active Process --</option>';
        procs.forEach(p => {
            sel.innerHTML += `<option value="${p.id}">${p.name} [PID: ${p.id}]</option>`;
        });
        
        if (oldVal && procs.some(p => p.id == oldVal)) {
            sel.value = oldVal;
        }
        
        loadVMProcessDetails();
    } catch {}
}

async function createVMProcess() {
    const name = document.getElementById('vm-process-name').value.trim();
    if (!name) {
        showToast('Please type a process name', 'error');
        return;
    }
    try {
        await api('/api/vm/processes', { method: 'POST', body: JSON.stringify({ name }) });
        showToast(`Created process '${name}'`, 'success');
        document.getElementById('vm-process-name').value = '';
        await loadVMWorkspace();
    } catch {}
}

async function loadVMProcessDetails() {
    const pid = document.getElementById('vm-active-process').value;
    const tableBody = document.getElementById('vm-page-table-rows');
    const ringBadge = document.getElementById('active-proc-ring-badge');

    if (!pid) {
        tableBody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted)">Select a process from the list</td></tr>';
        ringBadge.innerHTML = '';
        loadPhysicalLayouts();
        return;
    }

    if (pid !== lastActiveProcessId) {
        lastActiveProcessId = pid;
        currentSelectedPageNum = 0;
    }

    try {
        const procs = await api('/api/vm/processes');
        const proc = procs.find(p => p.id == pid);
        if (!proc) return;

        const isKernel = proc.privilege_ring === 0;
        ringBadge.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span>CPU Privilege Level: <span class="badge badge-${isKernel ? 'danger':'success'}">Ring ${proc.privilege_ring} (${isKernel ? 'Kernel' : 'User'})</span></span>
                <button class="btn btn-danger btn-sm" onclick="terminateVMProcess(${proc.id})">Terminate Process</button>
            </div>
        `;

        tableBody.innerHTML = proc.pages.map(p => {
            const startRange = (p.page_number * 4096).toString(16).toUpperCase().padStart(4, '0');
            const endRange = ((p.page_number + 1) * 4096 - 1).toString(16).toUpperCase().padStart(4, '0');
            const valid = p.is_valid ? '<span style="color:var(--accent-green)">1 (Valid)</span>' : '<span style="color:var(--accent-red)">0 (Invalid)</span>';
            const dirty = p.is_dirty ? '<span style="color:var(--accent-yellow)">1 (Dirty)</span>' : '0 (Clean)';
            const ref = p.is_referenced ? '1' : '0';
            const swap = p.swap_block !== null ? `Block ${p.swap_block}` : 'None';
            
            const isSelected = p.page_number === currentSelectedPageNum;
            const highlightStyle = isSelected 
                ? 'background:rgba(6,182,212,0.18) !important; border: 1px solid var(--accent-cyan); font-weight: bold; cursor: pointer;' 
                : 'cursor: pointer;';
            const validBg = p.is_valid ? 'background:rgba(16,185,129,0.04)' : '';
            const rowStyle = isSelected ? highlightStyle : (validBg ? validBg + '; cursor: pointer;' : 'cursor: pointer;');
            
            return `
                <tr onclick="selectVMPage(${p.page_number})" style="${rowStyle}">
                    <td style="font-family:var(--font-mono);font-weight:700">
                        ${isSelected ? '⚡ ' : ''}Page ${p.page_number}
                    </td>
                    <td style="font-family:var(--font-mono)">0x${startRange} - 0x${endRange}</td>
                    <td style="font-family:var(--font-mono)">${p.frame_number !== null ? `Frame ${p.frame_number}` : '—'}</td>
                    <td>${valid}</td>
                    <td>${dirty}</td>
                    <td>${ref}</td>
                    <td style="font-family:var(--font-mono)">${swap}</td>
                    <td style="font-family:var(--font-mono); font-size:0.8rem; max-width:160px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${p.allocated_content || ''}">${p.allocated_content || '—'}</td>
                </tr>
            `;
        }).join('');
    } catch {}

    // Also refresh RAM/Swap with per-process filter
    await loadPhysicalLayouts();
}

async function terminateVMProcess(pid) {
    if (!confirm('Are you sure you want to terminate this process? This releases all physical RAM frames and disk swap blocks.')) return;
    try {
        await api(`/api/vm/processes/${pid}`, { method: 'DELETE' });
        showToast('Process terminated', 'success');
        document.getElementById('vm-active-process').value = '';
        await loadVMWorkspace();
    } catch {}
}

async function loadPhysicalLayouts() {
    const pid = document.getElementById('vm-active-process').value;
    if (pid) {
        await loadProcessMemoryMap(pid);
    } else {
        await loadGlobalMemoryLayouts();
    }
}

async function loadProcessMemoryMap(pid) {
    try {
        const mm = await api(`/api/vm/processes/${pid}/memory-map?page_num=${currentSelectedPageNum}`);
        const statsBar = document.getElementById('vm-process-stats-bar');
        const s = mm.summary;

        // Stats bar
        statsBar.style.display = 'block';
        statsBar.innerHTML = `
            <div class="card" style="padding:14px 20px; background:linear-gradient(135deg, rgba(6,182,212,0.08), rgba(139,92,246,0.08)); border:1px solid rgba(6,182,212,0.25);">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
                    <span style="font-size:1.1rem;font-weight:700;color:var(--accent-cyan);">${mm.process_name}</span>
                    <span class="badge badge-success">PID ${mm.pid}</span>
                    <span class="badge badge-${mm.privilege_ring===0?'danger':'running'}">Ring ${mm.privilege_ring}</span>
                    <span class="badge badge-purple" style="margin-left:auto;">Viewing Page ${currentSelectedPageNum}</span>
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:16px;font-size:0.85rem;">
                    <div><span style="color:var(--text-muted)">Frames active for Page ${currentSelectedPageNum}:</span> <strong style="color:var(--accent-green)">${s.pages_in_ram}/8</strong></div>
                    <div><span style="color:var(--text-muted)">Swap Blocks for Page ${currentSelectedPageNum}:</span> <strong style="color:var(--accent-yellow)">${s.pages_in_swap}</strong></div>
                    <div><span style="color:var(--text-muted)">Dirty Page Frames:</span> <strong style="color:var(--accent-red)">${s.dirty_pages}</strong></div>
                    <div><span style="color:var(--text-muted)">Total Accessed:</span> <strong>${s.pages_accessed}</strong></div>
                    <div style="margin-left:auto;"><span style="color:var(--text-muted)">Global RAM Used:</span> <strong>${mm.global_ram.used_frames}</strong> frames</div>
                    <div><span style="color:var(--text-muted)">Global Swap Used:</span> <strong>${mm.global_swap.used_blocks}</strong> blocks</div>
                </div>
            </div>
        `;

        // RAM title
        document.getElementById('ram-card-title').textContent = `RAM Frames — Page ${currentSelectedPageNum} of ${mm.process_name} (PID ${mm.pid})`;
        document.getElementById('ram-card-badge').textContent = `${s.pages_in_ram} of 8 slots filled`;

        // RAM grid — per-process view
        const ramGrid = document.getElementById('ram-grid');
        ramGrid.innerHTML = mm.frames.map(f => {
            if (f.owner === 'self') {
                return `
                    <div class="ram-frame occupied" style="border-left:4px solid var(--accent-cyan);">
                        <div class="ram-frame-title">
                            <span style="color:var(--accent-cyan);font-weight:700;">Frame slot ${f.frame_number} — Page ${f.page_number}</span>
                            <span>${f.is_dirty ? '<span style="color:var(--accent-yellow);font-weight:700">DIRTY</span>' : '<span style="color:var(--accent-green)">CLEAN</span>'}</span>
                        </div>
                        <div style="font-size:0.85rem;font-weight:600;color:var(--accent-green);">
                            Active Operation: ${f.operation ? f.operation.toUpperCase() : 'LOADED'}
                        </div>
                        <div class="ram-frame-content">
                            Content: "${f.content || ''}"
                        </div>
                    </div>
                `;
            } else {
                return `
                    <div class="ram-frame" style="opacity:0.35; border-left:4px solid transparent;">
                        <div class="ram-frame-title"><span>Frame slot ${f.frame_number}</span></div>
                        <div style="font-size:0.85rem;color:var(--text-muted)">FREE SLOT</div>
                        <div class="ram-frame-content" style="color:var(--text-muted)">—</div>
                    </div>
                `;
            }
        }).join('');

        // Swap title
        document.getElementById('swap-card-title').textContent = `Disk Swap Space — Page ${currentSelectedPageNum} of ${mm.process_name}`;
        document.getElementById('swap-card-badge').textContent = `${s.pages_in_swap} blocks swapped`;

        // Swap grid — per-process only
        const swapGrid = document.getElementById('swap-grid');
        if (mm.swap_entries.length === 0) {
            swapGrid.innerHTML = `<div style="padding:20px;text-align:center;color:var(--text-muted);grid-column:1/-1;">No entries swapped to disk for Page ${currentSelectedPageNum} of this process. All accessed entries are in RAM.</div>`;
        } else {
            swapGrid.innerHTML = mm.swap_entries.map(sw => `
                <div class="swap-block occupied" title="Page ${sw.page_number} — Block ${sw.swap_block} — Content: ${sw.content}" style="cursor:default;">
                    <span style="font-size:0.65rem;opacity:0.8;">Swap Block ${sw.swap_block}</span>
                    <span style="font-weight:700;font-size:0.85rem;color:#fff;">Page ${sw.page_number}</span>
                    <span style="font-size:0.6rem;opacity:0.7;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%;">${sw.content}</span>
                </div>
            `).join('');
        }
    } catch(e) {
        console.error('Memory map load error:', e);
    }
}

async function loadGlobalMemoryLayouts() {
    // Hide stats bar, reset titles
    document.getElementById('vm-process-stats-bar').style.display = 'none';
    document.getElementById('ram-card-title').textContent = 'Physical RAM Layout (32KB Shared RAM)';
    document.getElementById('ram-card-badge').textContent = '8 Frames (4KB each)';
    document.getElementById('swap-card-title').textContent = 'Virtual Disk Swap Space (Swapped out pages)';
    document.getElementById('swap-card-badge').textContent = '32 Swap Blocks (4KB each)';

    try {
        const ram = await api('/api/vm/ram');
        const swap = await api('/api/vm/swap');

        const ramGrid = document.getElementById('ram-grid');
        ramGrid.innerHTML = ram.map(f => {
            const occupied = f.process_name !== null;
            return `
                <div class="ram-frame ${occupied ? 'occupied':''}">
                    <div class="ram-frame-title">
                        <span>Physical Frame ${f.frame_number}</span>
                        ${f.is_dirty ? '<span style="color:var(--accent-yellow);font-weight:700;">DIRTY</span>' : ''}
                    </div>
                    <div style="font-size:0.85rem;font-weight:600;">
                        ${occupied ? `${f.process_name} (PID: ${f.process_id}) — Page ${f.page_number}` : '<span style="color:var(--text-muted)">FREE FRAME</span>'}
                    </div>
                    <div class="ram-frame-content">
                        Content: ${occupied ? `"${f.content || ''}"` : '—'}
                    </div>
                </div>
            `;
        }).join('');

        const swapGrid = document.getElementById('swap-grid');
        swapGrid.innerHTML = swap.map(s => {
            const occupied = s.process_name !== null;
            return `
                <div class="swap-block ${occupied ? 'occupied':''}" title="${occupied ? `${s.process_name} (PID: ${s.process_id}) Page ${s.page_number}` : 'Free swap' }">
                    <span style="font-size:0.65rem;opacity:0.8;">Block ${s.block_number}</span>
                    <span style="font-weight:700;font-size:0.8rem;">${occupied ? `P${s.process_id}` : '—'}</span>
                </div>
            `;
        }).join('');
    } catch {}
}

function toggleVMContentField() {
    const op = document.getElementById('vm-op').value;
    const wr = document.getElementById('vm-write-value-group');
    wr.style.display = op === 'write' ? 'block' : 'none';
}

async function simulateVMAccess() {
    const pid = document.getElementById('vm-active-process').value;
    const addressStr = document.getElementById('vm-address').value.trim();
    const op = document.getElementById('vm-op').value;
    const val = document.getElementById('vm-write-value').value;

    if (!pid) { showToast('Please select a process first', 'error'); return; }
    if (!addressStr) { showToast('Please enter a virtual address (e.g. 0x00A0)', 'error'); return; }

    let address = parseInt(addressStr);
    if (addressStr.toLowerCase().startsWith('0x')) address = parseInt(addressStr, 16);
    if (isNaN(address) || address < 0 || address > 65535) {
        showToast('Address must be between 0x0000 and 0xFFFF (64KB space)', 'error'); return;
    }

    const btn = document.getElementById('btn-vm-access');
    btn.disabled = true;
    btn.textContent = 'Simulating hardware memory trap...';

    try {
        const payload = { process_id: parseInt(pid), address, operation: op, data: op === 'write' ? val : null };
        const res = await api('/api/vm/access', { method: 'POST', body: JSON.stringify(payload) });

        const logsDiv = document.getElementById('vm-logs');
        logsDiv.innerHTML = '';
        res.logs.forEach((log, index) => {
            const entry = document.createElement('div');
            entry.className = 'vm-log-entry';
            const isKernel = log.ring === 0;
            entry.innerHTML = `
                <span class="vm-log-step">[#${index + 1}]</span>
                <span class="${isKernel ? 'vm-log-ring-kernel' : 'vm-log-ring-user'}">[${isKernel ? 'RING 0' : 'RING 3'}]</span>
                <span class="vm-log-desc">${log.message}</span>
            `;
            logsDiv.appendChild(entry);
        });
        logsDiv.scrollTop = logsDiv.scrollHeight;

        if (res.success) {
            showToast(`Access completed! Value: ${res.value || 'Success'}`, 'success');
            // Auto-select the page that was accessed
            currentSelectedPageNum = res.page_number;
        } else {
            showToast(res.error || 'Access failed', 'error');
        }

        await loadVMProcessDetails();
    } catch {
    } finally {
        btn.disabled = false;
        btn.textContent = 'Execute Memory Access';
    }
}
