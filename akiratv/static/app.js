// AkiraTV Web UI JavaScript

const API_BASE = window.location.origin;
let ws = null;
let isRunning = false;

// Initialize
async function init() {
    await updateStatus();
    await loadChannels();
    connectWebSocket();
    setInterval(updateStatus, 10000); // Update every 10s
}

// API Calls
async function apiCall(endpoint, method = 'GET', body = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };
    if (body) options.body = JSON.stringify(body);

    const response = await fetch(`${API_BASE}${endpoint}`, options);
    return response.json();
}

// Update Status
async function updateStatus() {
    try {
        const data = await apiCall('/api/status');
        isRunning = data.is_running;
        
        const badge = document.getElementById('statusBadge');
        const text = document.getElementById('statusText');
        
        if (isRunning) {
            badge.className = 'status-badge running';
            text.textContent = 'Streaming';
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
        } else {
            badge.className = 'status-badge stopped';
            text.textContent = 'Stopped';
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
        }

        // Update stats
        document.getElementById('viewersCount').textContent = data.stats.viewers || 0;
        document.getElementById('uptimeValue').textContent = formatUptime(data.uptime);
        document.getElementById('statusValue').textContent = data.stats.status || 'N/A';
        document.getElementById('nowPlaying').textContent = data.stats.now_playing || 'No program info';
    } catch (error) {
        console.error('Failed to update status:', error);
    }
}

// Load Channels
async function loadChannels() {
    try {
        const data = await apiCall('/api/channels');
        const grid = document.getElementById('channelsGrid');
        const channels = data.channels;
        
        console.log('📺 Loaded channels:', channels);
        
        document.getElementById('channelsCount').textContent = channels.length;

        if (channels.length === 0) {
            grid.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-secondary);">No channels configured</div>';
            return;
        }

        grid.innerHTML = channels.map(ch => {
            const urlData = getChannelUrl(ch.name);
            const enabledBadge = ch.enabled ? '✅ Enabled' : '❌ Disabled';
            const statusColor = ch.status === 'running' ? 'var(--success)' : 'var(--text-secondary)';
            
            return `
                <div class="channel-card" style="${ch.enabled ? '' : 'opacity: 0.6;'}">
                    <div class="channel-header">
                        <div class="channel-name">${ch.name}</div>
                        <div class="channel-type ${ch.type}">${ch.type}</div>
                    </div>
                    <div class="channel-info">
                        Status: <strong style="color: ${statusColor}">${ch.status}</strong><br>
                        ${enabledBadge}<br>
                        Type: ${ch.type.toUpperCase()}
                    </div>
                    ${ch.enabled ? `
                        <div class="channel-url">
                            <span style="overflow: hidden; text-overflow: ellipsis;">${urlData}</span>
                            <button class="copy-btn" onclick="copyToClipboard('${urlData}')">Copy</button>
                        </div>
                        ${ch.type !== 'linear' ? `
                            <div class="play-now-form">
                                <input type="text" class="input" id="path_${ch.name}" placeholder="Video path...">
                                <button class="btn btn-primary" onclick="playNow('${ch.name}')">▶️ Play</button>
                            </div>
                        ` : ''}
                    ` : `
                        <div style="text-align: center; padding: 10px; color: var(--text-secondary); font-size: 12px;">
                            Channel disabled in config
                        </div>
                    `}
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Failed to load channels:', error);
        showToast('Failed to load channels', 'error');
    }
}

// Get Channel URL
function getChannelUrl(channel) {
    const port = window.location.port || '8080';
    const host = window.location.hostname;
    return `http://${host}:${port}/hls/${channel}/index.m3u8`;
}

// Engine Control
async function startEngine() {
    showLoading('start');
    try {
        const result = await apiCall('/api/start', 'POST');
        if (result.success) {
            showToast('Engine started successfully', 'success');
            await updateStatus();
            await loadChannels();
        } else {
            showToast(result.error || 'Failed to start', 'error');
        }
    } catch (error) {
        showToast('Failed to start engine', 'error');
    }
    hideLoading('start');
}

async function stopEngine() {
    showLoading('stop');
    try {
        const result = await apiCall('/api/stop', 'POST');
        if (result.success) {
            showToast('Engine stopped', 'success');
            await updateStatus();
        } else {
            showToast(result.error || 'Failed to stop', 'error');
        }
    } catch (error) {
        showToast('Failed to stop engine', 'error');
    }
    hideLoading('stop');
}

async function restartEngine() {
    if (!confirm('Restart AkiraTV? This will disconnect all viewers.')) return;
    
    try {
        const result = await apiCall('/api/restart', 'POST');
        if (result.success) {
            showToast('Engine restarting...', 'info');
            setTimeout(async () => {
                await updateStatus();
                await loadChannels();
            }, 3000);
        } else {
            showToast(result.error || 'Failed to restart', 'error');
        }
    } catch (error) {
        showToast('Failed to restart engine', 'error');
    }
}

async function clearCache() {
    try {
        const result = await apiCall('/api/cache/clear', 'POST');
        if (result.success) {
            showToast(`Cleared ${result.data.deleted} files`, 'success');
        } else {
            showToast(result.error || 'Failed to clear cache', 'error');
        }
    } catch (error) {
        showToast('Failed to clear cache', 'error');
    }
}

async function reloadSchedule() {
    try {
        const result = await apiCall('/api/schedule/reload', 'POST');
        if (result.success) {
            showToast('Schedule reloaded', 'success');
        } else {
            showToast(result.error || 'Failed to reload', 'error');
        }
    } catch (error) {
        showToast('Failed to reload schedule', 'error');
    }
}

async function playNow(channel) {
    const input = document.getElementById(`path_${channel}`);
    const path = input.value.trim();
    
    if (!path) {
        showToast('Enter video path', 'error');
        return;
    }

    try {
        const result = await apiCall(`/api/channels/${channel}/play`, 'POST', { video_path: path });
        if (result.success) {
            showToast(result.message, 'success');
            input.value = '';
        } else {
            showToast(result.error || 'Failed to play', 'error');
        }
    } catch (error) {
        showToast('Failed to play video', 'error');
    }
}

// WebSocket
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'stats_update') {
            document.getElementById('viewersCount').textContent = data.viewers || 0;
            document.getElementById('nowPlaying').textContent = data.stats.now_playing || 'No program info';
        }
        
        if (data.type === 'video_queued') {
            showToast(`Playing: ${data.data.video}`, 'info');
        }
    };

    ws.onclose = () => {
        console.log('WebSocket closed, reconnecting...');
        setTimeout(connectWebSocket, 5000);
    };
}

// Utilities
function formatUptime(seconds) {
    if (!seconds || seconds === 0) return '0s';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    return `${h}h ${m}m ${s}s`;
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text);
    showToast('URL copied!', 'success');
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function showLoading(btnId) {
    const btn = document.getElementById(`${btnId}Btn`);
    btn.innerHTML = '<span class="loading"></span> Processing...';
    btn.disabled = true;
}

function hideLoading(btnId) {
    const btn = document.getElementById(`${btnId}Btn`);
    if (btnId === 'start') {
        btn.innerHTML = '▶️ Start Streaming';
    } else {
        btn.innerHTML = '⏹️ Stop Streaming';
    }
}

// Initialize on load
init();
