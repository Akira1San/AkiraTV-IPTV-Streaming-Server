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
async function apiCall(endpoint, method = 'GET', body = null, params = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };
    
    let url = `${API_BASE}${endpoint}`;
    
    // Handle URL parameters for POST requests (like form data)
    if (method === 'POST' && params) {
        const urlParams = new URLSearchParams(params);
        url += `?${urlParams.toString()}`;
    } else if (body) {
        options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);
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
        // Load both channels and global config
        const [channelsData, configData] = await Promise.all([
            apiCall('/api/channels'),
            apiCall('/api/config')
        ]);
        
        globalConfig = configData;
        const channels = channelsData.channels;
        const grid = document.getElementById('channelsGrid');
        
        console.log('📺 Loaded channels:', channels);
        
        document.getElementById('channelsCount').textContent = channels.length;

        if (channels.length === 0) {
            grid.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-secondary);">No channels configured</div>';
            return;
        }

        grid.innerHTML = channels.map(ch => {
            const urlData = getChannelUrl(ch.name);
            const statusColor = ch.status === 'running' ? 'var(--success)' : 'var(--text-secondary)';
            
            // Get current transcoding and subtitle settings
            const transcodingSetting = getChannelTranscodingSetting(ch.name);
            const subtitlesSetting = getChannelSubtitlesSetting(ch.name);
            
            return `
                <div class="channel-card" style="${ch.enabled ? '' : 'opacity: 0.6;'}">
                    <div class="channel-header">
                        <div class="channel-name">${ch.name}</div>
                        <div class="channel-type ${ch.type}">${ch.type}</div>
                        <div class="channel-toggle">
                            <label class="toggle-switch">
                                <input type="checkbox" ${ch.enabled ? 'checked' : ''} 
                                       onchange="toggleChannel('${ch.name}', this.checked)">
                                <span class="toggle-slider"></span>
                            </label>
                            <span class="toggle-label">${ch.enabled ? 'Enabled' : 'Disabled'}</span>
                        </div>
                    </div>
                    <div class="channel-info">
                        Status: <strong style="color: ${statusColor}">${ch.status}</strong><br>
                        Type: ${ch.type.toUpperCase()}
                    </div>
                    
                    <!-- Channel Settings -->
                    <div class="channel-settings">
                        <div class="setting-row">
                            <label class="setting-label">Transcoding:</label>
                            <select class="setting-select" onchange="updateChannelSetting('${ch.name}', 'transcoding', this.value)">
                                <option value="global" ${transcodingSetting === 'global' ? 'selected' : ''}>Global</option>
                                <option value="enabled" ${transcodingSetting === 'enabled' ? 'selected' : ''}>Enabled</option>
                                <option value="disabled" ${transcodingSetting === 'disabled' ? 'selected' : ''}>Disabled</option>
                            </select>
                        </div>
                        <div class="setting-row">
                            <label class="setting-label">Subtitles:</label>
                            <select class="setting-select" onchange="updateChannelSetting('${ch.name}', 'subtitles', this.value)">
                                <option value="global" ${subtitlesSetting === 'global' ? 'selected' : ''}>Global</option>
                                <option value="enabled" ${subtitlesSetting === 'enabled' ? 'selected' : ''}>Enabled</option>
                                <option value="disabled" ${subtitlesSetting === 'disabled' ? 'selected' : ''}>Disabled</option>
                            </select>
                        </div>
                        <div class="setting-row">
                            <button class="btn-small btn-secondary" onclick="reloadChannelSchedule('${ch.name}')">
                                📅 Reload Schedule
                            </button>
                            <button class="btn-small btn-danger" onclick="confirmDeleteChannel('${ch.name}')">
                                🗑️ Delete
                            </button>
                        </div>
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
                            Channel disabled - enable to access streaming URL
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
            showToast('All schedules reloaded', 'success');
        } else {
            showToast(result.error || 'Failed to reload schedules', 'error');
        }
    } catch (error) {
        showToast('Failed to reload schedules', 'error');
    }
}

// Per-channel schedule reload
async function reloadChannelSchedule(channelName) {
    try {
        const result = await apiCall(`/api/channels/${channelName}/reload-schedule`, 'POST');
        if (result.success) {
            showToast(`Schedule reloaded for ${channelName}`, 'success');
        } else {
            showToast(result.error || `Failed to reload schedule for ${channelName}`, 'error');
        }
    } catch (error) {
        showToast(`Failed to reload schedule for ${channelName}`, 'error');
    }
}

// Delete channel with confirmation
function confirmDeleteChannel(channelName) {
    const confirmed = confirm(
        `Are you sure you want to delete channel '${channelName}'?\n\n` +
        `This will:\n` +
        `• Remove the channel from your configuration\n` +
        `• Stop the channel if it's currently running\n` +
        `• This action cannot be undone\n\n` +
        `Click OK to delete or Cancel to keep the channel.`
    );
    
    if (confirmed) {
        deleteChannel(channelName);
    }
}

async function deleteChannel(channelName) {
    try {
        const result = await apiCall(`/api/channels/${channelName}`, 'DELETE');
        if (result.success) {
            showToast(`Channel '${channelName}' deleted successfully`, 'success');
            // Reload channels to update the UI
            await loadChannels();
        } else {
            showToast(result.error || `Failed to delete channel '${channelName}'`, 'error');
        }
    } catch (error) {
        showToast(`Failed to delete channel '${channelName}'`, 'error');
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

// Channel Enable/Disable Toggle
async function toggleChannel(channelName, enabled) {
    try {
        const endpoint = enabled ? `/api/channels/${channelName}/enable` : `/api/channels/${channelName}/disable`;
        const result = await apiCall(endpoint, 'POST');
        
        if (result.success) {
            showToast(`Channel ${channelName} ${enabled ? 'enabled' : 'disabled'}`, 'success');
            // Reload channels to update the UI
            await loadChannels();
        } else {
            showToast(result.error || `Failed to ${enabled ? 'enable' : 'disable'} channel`, 'error');
            // Revert the toggle on error
            await loadChannels();
        }
    } catch (error) {
        showToast(`Failed to ${enabled ? 'enable' : 'disable'} channel`, 'error');
        // Revert the toggle on error
        await loadChannels();
    }
}

// Add Channel Modal Functions
function showAddChannelModal() {
    const channelName = document.getElementById('newChannelName').value.trim();
    
    if (!channelName) {
        showToast('Enter a channel name first', 'error');
        return;
    }
    
    // Validate channel name
    if (!channelName.replace(/_/g, '').replace(/-/g, '').match(/^[a-zA-Z0-9]+$/)) {
        showToast('Use only letters, numbers, hyphens (-), and underscores (_)', 'error');
        return;
    }
    
    // Set the channel name in the modal
    document.getElementById('modalChannelName').textContent = channelName;
    
    // Reset radio buttons to linear
    document.querySelector('input[name="channelType"][value="linear"]').checked = true;
    
    // Show modal
    document.getElementById('addChannelModal').style.display = 'block';
}

function hideAddChannelModal() {
    document.getElementById('addChannelModal').style.display = 'none';
}

async function createChannel() {
    const channelName = document.getElementById('newChannelName').value.trim();
    const selectedType = document.querySelector('input[name="channelType"]:checked').value;
    
    try {
        const result = await apiCall('/api/channels', 'POST', null, {
            channel_name: channelName,
            channel_type: selectedType
        });
        
        if (result.success) {
            showToast(`Channel '${channelName}' created successfully as ${selectedType.toUpperCase()} type!`, 'success');
            
            // Clear the input and hide modal
            document.getElementById('newChannelName').value = '';
            hideAddChannelModal();
            
            // Reload channels to show the new one
            await loadChannels();
        } else {
            showToast(result.error || 'Failed to create channel', 'error');
        }
    } catch (error) {
        showToast('Failed to create channel', 'error');
    }
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('addChannelModal');
    if (event.target === modal) {
        hideAddChannelModal();
    }
}

// Global config cache for channel settings
let globalConfig = null;

// Helper functions to get channel settings
function getChannelTranscodingSetting(channelName) {
    if (!globalConfig) return 'global';
    
    const channelConfig = globalConfig.channels?.[channelName];
    if (!channelConfig) return 'global';
    
    if (channelConfig.transcoding && 'enabled' in channelConfig.transcoding) {
        return channelConfig.transcoding.enabled ? 'enabled' : 'disabled';
    }
    return 'global';
}

function getChannelSubtitlesSetting(channelName) {
    if (!globalConfig) return 'global';
    
    const channelConfig = globalConfig.channels?.[channelName];
    if (!channelConfig) return 'global';
    
    if ('enable_subtitles' in channelConfig) {
        return channelConfig.enable_subtitles ? 'enabled' : 'disabled';
    }
    return 'global';
}

// Update channel-specific settings
async function updateChannelSetting(channelName, settingType, value) {
    try {
        const requestBody = {};
        requestBody[settingType] = value;
        
        const result = await apiCall(`/api/channels/${channelName}`, 'PATCH', requestBody);
        
        if (result.success) {
            showToast(`${channelName} ${settingType} set to ${value}`, 'success');
            // Refresh config cache
            await loadGlobalConfig();
        } else {
            showToast(result.error || `Failed to update ${settingType}`, 'error');
            // Reload channels to revert the dropdown
            await loadChannels();
        }
    } catch (error) {
        showToast(`Failed to update ${settingType}`, 'error');
        // Reload channels to revert the dropdown
        await loadChannels();
    }
}

// Load global config for channel settings
async function loadGlobalConfig() {
    try {
        globalConfig = await apiCall('/api/config');
    } catch (error) {
        console.error('Failed to load global config:', error);
        globalConfig = null;
    }
}

// Configuration Modal Functions
function showConfigModal() {
    loadConfigurationData();
    document.getElementById('configModal').style.display = 'block';
}

function hideConfigModal() {
    document.getElementById('configModal').style.display = 'none';
}

function showConfigTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.config-tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.config-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabName + 'Tab').classList.add('active');
    document.querySelector(`[onclick="showConfigTab('${tabName}')"]`).classList.add('active');
}

async function loadConfigurationData() {
    try {
        const config = await apiCall('/api/config');
        
        // Transcoding settings
        const ffmpeg = config.ffmpeg || {};
        const transcoding = ffmpeg.transcoding || {};
        
        document.getElementById('transcodingMode').value = transcoding.enabled ? 'enabled' : 'disabled';
        document.getElementById('transcodingBitrate').value = transcoding.bitrate || 'auto';
        document.getElementById('customBitrate').value = transcoding.custom_bitrate || '1500k';
        document.getElementById('videoQuality').value = transcoding.video_quality || 'source';
        document.getElementById('encoder').value = transcoding.encoder || 'auto';
        document.getElementById('hwaccel').value = ffmpeg.hwaccel || 'none';
        
        // Subtitle settings
        document.getElementById('enableSubtitles').checked = ffmpeg.enable_subtitles || false;
        document.getElementById('subtitleFontSize').value = transcoding.subtitle_font_size || '28';
        
        // Storage settings
        const storage = config.storage || {};
        document.getElementById('storageMode').value = storage.type || 'disk';
        document.getElementById('diskPath').value = storage.disk_path || './output';
        document.getElementById('ramPath').value = storage.ram_path || 'R:/akiratv';
        toggleStoragePath();
        
        // Output settings
        const output = config.output || {};
        const http = output.http || {};
        document.getElementById('httpPort').value = http.port || 8081;
        
        const streaming = config.streaming || {};
        document.getElementById('enablePreGen').checked = streaming.pre_gen || false;
        
        // Handle custom bitrate visibility
        toggleCustomBitrate();
        
    } catch (error) {
        console.error('Failed to load configuration:', error);
        showToast('Failed to load configuration', 'error');
    }
}

function toggleStoragePath() {
    const storageMode = document.getElementById('storageMode').value;
    const diskPathItem = document.getElementById('diskPathItem');
    const ramPathItem = document.getElementById('ramPathItem');
    
    if (storageMode === 'disk') {
        diskPathItem.style.display = 'flex';
        ramPathItem.style.display = 'none';
    } else {
        diskPathItem.style.display = 'none';
        ramPathItem.style.display = 'flex';
    }
}

function toggleCustomBitrate() {
    const bitrateMode = document.getElementById('transcodingBitrate').value;
    const customBitrateInput = document.getElementById('customBitrate');
    
    if (bitrateMode === 'custom') {
        customBitrateInput.disabled = false;
        customBitrateInput.style.opacity = '1';
    } else {
        customBitrateInput.disabled = true;
        customBitrateInput.style.opacity = '0.5';
    }
}

// Add event listener for bitrate change
document.addEventListener('DOMContentLoaded', function() {
    const bitrateSelect = document.getElementById('transcodingBitrate');
    if (bitrateSelect) {
        bitrateSelect.addEventListener('change', toggleCustomBitrate);
    }
});

async function saveConfiguration() {
    try {
        const config = {
            ffmpeg: {
                hwaccel: document.getElementById('hwaccel').value,
                enable_subtitles: document.getElementById('enableSubtitles').checked,
                transcoding: {
                    enabled: document.getElementById('transcodingMode').value === 'enabled',
                    bitrate: document.getElementById('transcodingBitrate').value,
                    custom_bitrate: document.getElementById('customBitrate').value,
                    video_quality: document.getElementById('videoQuality').value,
                    encoder: document.getElementById('encoder').value,
                    subtitle_font_size: document.getElementById('subtitleFontSize').value
                }
            },
            storage: {
                type: document.getElementById('storageMode').value,
                disk_path: document.getElementById('diskPath').value,
                ram_path: document.getElementById('ramPath').value
            },
            output: {
                http: {
                    port: parseInt(document.getElementById('httpPort').value)
                }
            },
            streaming: {
                pre_gen: document.getElementById('enablePreGen').checked
            }
        };
        
        // Wrap config in updates field as expected by API
        const result = await apiCall('/api/config', 'PATCH', { updates: config });
        
        if (result.success) {
            showToast('Configuration saved successfully', 'success');
            hideConfigModal();
            // Refresh global config cache
            await loadGlobalConfig();
        } else {
            showToast(result.error || 'Failed to save configuration', 'error');
        }
    } catch (error) {
        showToast('Failed to save configuration', 'error');
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
