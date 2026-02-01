// AkiraTV Web UI JavaScript

const API_BASE = window.location.origin;
let ws = null;
let isRunning = false;

// Internationalization
let currentLanguage = 'en';

// Translations are loaded from external file (translations.js)

// Translation functions
function t(key) {
    return translations[currentLanguage][key] || translations['en'][key] || key;
}

function switchLanguage(lang) {
    currentLanguage = lang;
    
    // Update button states
    document.getElementById('langEn').classList.toggle('active', lang === 'en');
    document.getElementById('langBg').classList.toggle('active', lang === 'bg');
    
    // Save language preference
    localStorage.setItem('akiratv_language', lang);
    
    // Update all translated elements
    updateTranslations();
    
    // Reload dynamic content with new language
    loadTVGuide();
    loadChannels();
}

function updateTranslations() {
    // Update all elements with data-i18n attributes
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        element.textContent = t(key);
    });
    
    // Update placeholder attributes
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        const key = element.getAttribute('data-i18n-placeholder');
        element.placeholder = t(key);
    });
    
    // Update status text if it's a known status
    const statusText = document.getElementById('statusText');
    if (statusText) {
        const currentStatus = statusText.textContent;
        if (currentStatus === 'Checking...' || currentStatus === 'Проверява...') {
            statusText.textContent = t('status.checking');
        } else if (currentStatus === 'Streaming' || currentStatus === 'Стрийминг') {
            statusText.textContent = t('status.streaming');
        } else if (currentStatus === 'Stopped' || currentStatus === 'Спрян') {
            statusText.textContent = t('status.stopped');
        }
    }
}

// Initialize language on page load
function initializeLanguage() {
    // Load saved language preference or default to English
    const savedLang = localStorage.getItem('akiratv_language') || 'en';
    switchLanguage(savedLang);
}

// Initialize
async function init() {
    initializeLanguage();
    await updateStatus();
    await loadChannels();
    await loadChannelDropdown();
    await refreshPlaylist();
    await loadTVGuide();
    connectWebSocket();
    setInterval(updateStatus, 10000); // Update every 10s
    setInterval(loadTVGuide, 60000); // Update guide every minute
}

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
    
    // Check if response is ok (status 200-299)
    if (!response.ok) {
        let errorData;
        try {
            errorData = await response.json();
        } catch (e) {
            // If JSON parsing fails, use status text
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        // Throw error with details from server
        const errorMessage = errorData.detail || errorData.error || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
        throw new Error(errorMessage);
    }
    
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
            text.textContent = t('status.streaming');
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
        } else {
            badge.className = 'status-badge stopped';
            text.textContent = t('status.stopped');
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
        }

        // Update stats
        document.getElementById('viewersCount').textContent = data.stats.viewers || 0;
        document.getElementById('uptimeValue').textContent = formatUptime(data.uptime);
        document.getElementById('statusValue').textContent = data.stats.status || 'N/A';
        
        const nowPlayingElement = document.getElementById('nowPlaying');
        if (data.stats.now_playing) {
            nowPlayingElement.textContent = data.stats.now_playing;
        } else {
            nowPlayingElement.textContent = t('nowPlaying.noInfo');
        }
    } catch (error) {
        console.error('Failed to update status:', error);
        document.getElementById('statusText').textContent = t('status.checking');
    }
}

// Engine Control
async function startEngine() {
    showLoading('start');
    try {
        const result = await apiCall('/api/start', 'POST');
        if (result.success) {
            showToast(t('messages.engineStarted'), 'success');
            await updateStatus();
            await loadChannels();
        } else {
            showToast(result.error || t('messages.failedToStart'), 'error');
        }
    } catch (error) {
        showToast(t('messages.failedToStart'), 'error');
    }
    hideLoading('start');
}

async function stopEngine() {
    showLoading('stop');
    try {
        const result = await apiCall('/api/stop', 'POST');
        if (result.success) {
            showToast(t('messages.engineStopped'), 'success');
            await updateStatus();
        } else {
            showToast(result.error || t('messages.failedToStop'), 'error');
        }
    } catch (error) {
        showToast(t('messages.failedToStop'), 'error');
    }
    hideLoading('stop');
}

async function restartEngine() {
    if (!confirm('Restart AkiraTV? This will disconnect all viewers.')) return;
    
    try {
        const result = await apiCall('/api/restart', 'POST');
        if (result.success) {
            showToast(t('messages.engineRestarting'), 'info');
            setTimeout(async () => {
                await updateStatus();
                await loadChannels();
            }, 3000);
        } else {
            showToast(result.error || t('messages.failedToRestart'), 'error');
        }
    } catch (error) {
        showToast(t('messages.failedToRestart'), 'error');
    }
}

async function clearCache() {
    try {
        const result = await apiCall('/api/cache/clear', 'POST');
        if (result.success) {
            showToast(`${result.data.deleted} ${t('messages.cacheCleared')}`, 'success');
        } else {
            showToast(result.error || t('messages.failedToClearCache'), 'error');
        }
    } catch (error) {
        showToast(t('messages.failedToClearCache'), 'error');
    }
}

async function reloadSchedule() {
    try {
        const result = await apiCall('/api/schedule/reload', 'POST');
        if (result.success) {
            showToast(t('messages.schedulesReloaded'), 'success');
        } else {
            showToast(result.error || t('messages.failedToReloadSchedules'), 'error');
        }
    } catch (error) {
        showToast(t('messages.failedToReloadSchedules'), 'error');
    }
}

async function generateXMLTV() {
    try {
        showToast('Generating XMLTV files...', 'info');
        const result = await apiCall('/api/xmltv/generate', 'POST');
        if (result.success) {
            const data = result.data;
            showToast(
                `✅ XMLTV + M3U Generated!\n\n` +
                `In Kodi IPTV Simple Client:\n` +
                `• M3U Path: ${data.m3u_url}\n` +
                `• XMLTV Path: ${data.xmltv_url}`,
                'success'
            );
        } else {
            showToast(result.error || 'Failed to generate XMLTV', 'error');
        }
    } catch (error) {
        showToast('Failed to generate XMLTV', 'error');
    }
}

async function openConfigFile() {
    try {
        const result = await apiCall('/api/config/file');
        if (result.exists) {
            // Show info about config file location
            showToast(`Config file: ${result.path}\n\nNote: Use your file manager to open this file`, 'info');
        } else {
            showToast('Config file not found', 'error');
        }
    } catch (error) {
        showToast('Failed to get config file info', 'error');
    }
}

async function openLogs() {
    try {
        const result = await apiCall('/api/logs');
        const filesList = result.files.length > 0 
            ? result.files.map(f => `• ${f.name} (${Math.round(f.size/1024)}KB)`).join('\n')
            : 'No log files found';
        
        showToast(
            `Logs directory: ${result.directory}\n\n` +
            `Log files:\n${filesList}\n\n` +
            `Note: Use your file manager to open this directory`,
            'info'
        );
    } catch (error) {
        showToast('Failed to get logs info', 'error');
    }
}

// Playlist Controls Functions
async function loadChannelDropdown() {
    try {
        const data = await apiCall('/api/channels');
        const channels = data.channels;
        const select = document.getElementById('channelSelect');
        
        // Clear existing options
        select.innerHTML = '';
        
        // Add enabled channels that support play_now (VOD and Dynamic)
        const playableChannels = channels.filter(ch => 
            ch.enabled && (ch.type === 'vod' || ch.type === 'dynamic')
        );
        
        if (playableChannels.length === 0) {
            select.innerHTML = '<option value="">No playable channels available</option>';
            return;
        }
        
        playableChannels.forEach(ch => {
            const option = document.createElement('option');
            option.value = ch.name;
            option.textContent = `${ch.name} (${ch.type.toUpperCase()})`;
            select.appendChild(option);
        });
        
        // Select first channel
        select.value = playableChannels[0].name;
        
    } catch (error) {
        console.error('Failed to load channel dropdown:', error);
        document.getElementById('channelSelect').innerHTML = '<option value="">Error loading channels</option>';
    }
}

function browseVideo() {
    // Since we can't open file dialogs from web, show instructions
    showToast(
        'Enter the full path to your video file in the text field.\n\n' +
        'Example:\n' +
        'C:\\Videos\\movie.mp4\n' +
        '/home/user/videos/movie.mp4\n\n' +
        'Supported formats: MP4, MKV, AVI, MOV, M4V, WMV, FLV',
        'info'
    );
}

function browseFolder() {
    // Since we can't open folder dialogs from web, show instructions
    showToast(
        'Enter the full path to your video folder in the text field.\n\n' +
        'Example:\n' +
        'C:\\Videos\\Movies\n' +
        '/home/user/videos/movies\n\n' +
        'The folder will be scanned for all video files.',
        'info'
    );
}

async function playNowFromInput() {
    const channelSelect = document.getElementById('channelSelect');
    const pathInput = document.getElementById('playNowPath');
    
    const channel = channelSelect.value;
    const videoPath = pathInput.value.trim();
    
    if (!channel) {
        showToast('Please select a channel', 'error');
        return;
    }
    
    if (!videoPath) {
        showToast('Please enter a video path', 'error');
        return;
    }
    
    try {
        const result = await apiCall(`/api/channels/${channel}/play`, 'POST', { video_path: videoPath });
        if (result.success) {
            showToast(result.message, 'success');
            pathInput.value = ''; // Clear input
        } else {
            showToast(result.error || 'Failed to play video', 'error');
        }
    } catch (error) {
        showToast('Failed to play video', 'error');
    }
}

async function createPlaylistFromFolder() {
    const folderInput = document.getElementById('folderPath');
    const folderPath = folderInput.value.trim();
    
    if (!folderPath) {
        showToast('Please enter a folder path', 'error');
        return;
    }
    
    try {
        showToast('Creating playlist...', 'info');
        const result = await apiCall('/api/playlist/create', 'POST', null, { folder_path: folderPath });
        
        if (result.success) {
            showToast(
                `✅ Playlist Created!\n\n` +
                `${result.data.video_count} videos found\n` +
                `Playlist: ${result.data.playlist_path}`,
                'success'
            );
            folderInput.value = ''; // Clear input
            await refreshPlaylist(); // Refresh the playlist dropdown
        } else {
            showToast(result.error || 'Failed to create playlist', 'error');
        }
    } catch (error) {
        showToast('Failed to create playlist', 'error');
    }
}

async function refreshPlaylist() {
    try {
        const result = await apiCall('/api/playlist/videos');
        const select = document.getElementById('playlistSelect');
        
        // Clear existing options
        select.innerHTML = '';
        
        if (result.videos.length === 0) {
            select.innerHTML = '<option value="">No playlist loaded</option>';
            return;
        }
        
        // Add videos to dropdown
        result.videos.forEach(video => {
            const option = document.createElement('option');
            option.value = video.name;
            option.textContent = video.name;
            select.appendChild(option);
        });
        
        // Select first video
        if (result.videos.length > 0) {
            select.value = result.videos[0].name;
        }
        
    } catch (error) {
        console.error('Failed to refresh playlist:', error);
        document.getElementById('playlistSelect').innerHTML = '<option value="">Error loading playlist</option>';
    }
}

async function playSelectedVideo() {
    const channelSelect = document.getElementById('channelSelect');
    const playlistSelect = document.getElementById('playlistSelect');
    
    const channel = channelSelect.value;
    const videoName = playlistSelect.value;
    
    if (!channel) {
        showToast('Please select a channel', 'error');
        return;
    }
    
    if (!videoName || videoName === '') {
        showToast('Please select a video from the playlist', 'error');
        return;
    }
    
    try {
        const result = await apiCall('/api/playlist/play-selected', 'POST', { 
            channel: channel, 
            video_name: videoName 
        });
        
        if (result.success) {
            showToast(result.message, 'success');
        } else {
            showToast(result.error || 'Failed to play selected video', 'error');
        }
    } catch (error) {
        showToast('Failed to play selected video', 'error');
    }
}

async function createStandbyLoop() {
    try {
        showToast('Creating standby loop videos...\nThis may take a few minutes depending on your inventory size.', 'info');
        
        const result = await apiCall('/api/standby/create', 'POST');
        
        if (result.success) {
            const data = result.data;
            showToast(
                `✅ Standby Loops Created!\n\n` +
                `Directory: ${data.directory}\n\n` +
                `Created files:\n${data.files_list}\n\n` +
                `These videos can be used by Dynamic channels for standby mode.`,
                'success'
            );
        } else {
            showToast(result.error || 'Failed to create standby loops', 'error');
        }
    } catch (error) {
        showToast('Failed to create standby loops', 'error');
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
    showToast(t('messages.urlCopied'), 'success');
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    // Handle multi-line messages
    if (message.includes('\n')) {
        const lines = message.split('\n');
        toast.innerHTML = lines.map(line => `<div>${line}</div>`).join('');
    } else {
        toast.textContent = message;
    }
    
    document.body.appendChild(toast);
    
    // Auto-dismiss after longer time for longer messages
    const dismissTime = message.length > 100 ? 8000 : 3000;
    
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, dismissTime);
}

function showLoading(btnId) {
    const btn = document.getElementById(`${btnId}Btn`);
    btn.innerHTML = '<span class="loading"></span> Processing...';
    btn.disabled = true;
}

function hideLoading(btnId) {
    const btn = document.getElementById(`${btnId}Btn`);
    if (btnId === 'start') {
        btn.innerHTML = `<span data-i18n="control.start">${t('control.start')}</span>`;
    } else {
        btn.innerHTML = `<span data-i18n="control.stop">${t('control.stop')}</span>`;
    }
}

// Initialize on load
init();