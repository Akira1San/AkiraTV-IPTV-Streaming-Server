// AkiraTV Web UI JavaScript

const API_BASE = window.location.origin;
let ws = null;
let isRunning = false;

// Helper function to get dynamic stream base URL
function getStreamBaseUrl() {
    const host = window.location.hostname;
    const port = window.location.port || '8081';
    return `http://${host}:${port}`;
}

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
    // Playlist controls removed - now using VOD page
    connectWebSocket();
    setInterval(updateStatus, 10000); // Update every 10s
}

// API Calls
// Helper function to add timeout to fetch requests
async function fetchWithTimeout(url, options = {}, timeout = 5000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw new Error('Request timeout');
        }
        throw error;
    }
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

    const response = await fetchWithTimeout(url, options, 5000);
    
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
let statusCheckFailures = 0;
const MAX_STATUS_FAILURES = 3;

async function updateStatus() {
    try {
        const data = await apiCall('/api/status');
        
        // Reset failure counter on success
        statusCheckFailures = 0;
        
        isRunning = data.is_running;
        
        const badge = document.getElementById('statusBadge');
        const text = document.getElementById('statusText');
        
        if (isRunning) {
            badge.className = 'status-badge running';
            text.textContent = t('status.streaming');
            const startBtn = document.getElementById('startBtn');
            const stopBtn = document.getElementById('stopBtn');
            if (startBtn) startBtn.disabled = true;
            if (stopBtn) stopBtn.disabled = false;
        } else {
            badge.className = 'status-badge stopped';
            text.textContent = t('status.stopped');
            const startBtn = document.getElementById('startBtn');
            const stopBtn = document.getElementById('stopBtn');
            if (startBtn) startBtn.disabled = false;
            if (stopBtn) stopBtn.disabled = true;
        }

        // Update stats (with null checks)
        const viewersCount = document.getElementById('viewersCount');
        if (viewersCount) viewersCount.textContent = data.stats.viewers || 0;
        
        const uptimeValue = document.getElementById('uptimeValue');
        if (uptimeValue) uptimeValue.textContent = formatUptime(data.uptime);
        
        const statusValue = document.getElementById('statusValue');
        if (statusValue) statusValue.textContent = data.stats.status || 'N/A';
        
        const channelsCount = document.getElementById('channelsCount');
        if (channelsCount && data.stats.channels_count !== undefined) {
            channelsCount.textContent = data.stats.channels_count;
        }
        
        const nowPlayingElement = document.getElementById('nowPlaying');
        if (nowPlayingElement) {
            if (data.stats.now_playing) {
                nowPlayingElement.textContent = data.stats.now_playing;
            } else {
                nowPlayingElement.textContent = t('nowPlaying.noInfo');
            }
        }
    } catch (error) {
        console.error('Failed to update status:', error);
        statusCheckFailures++;
        
        const badge = document.getElementById('statusBadge');
        const text = document.getElementById('statusText');
        
        if (statusCheckFailures >= MAX_STATUS_FAILURES) {
            // After multiple failures, show disconnected state
            badge.className = 'status-badge disconnected';
            text.textContent = t('status.disconnected') || 'Disconnected';
        } else {
            // Still trying, show checking
            badge.className = 'status-badge checking';
            text.textContent = t('status.checking');
        }
    }
}

// Load Channels
let allChannelsData = []; // Store all channels for search
let currentChannelFilter = 'all'; // Current filter: 'all', 'enabled', 'disabled'

async function loadChannels() {
    try {
        // Load channels, config, and channel URLs from API
        const [channelsData, configData, urlsData] = await Promise.all([
            apiCall('/api/channels'),
            apiCall('/api/config'),
            apiCall('/api/channels/urls')
        ]);
        
        globalConfig = configData;
        const channels = channelsData.channels;
        allChannelsData = channels; // Store for search
        
        console.log('📺 Loaded channels:', channels);
        
        // Use URLs from API endpoint which correctly determines LAN IP and streaming port
        const channelUrls = urlsData.channels || {};
        window.cachedChannelUrls = urlsData; // Cache for filterChannels
        console.log('🔗 Using API channel URLs:', channelUrls);
        
        const channelsCount = document.getElementById('channelsCount');
        if (channelsCount) channelsCount.textContent = channels.length;

        // Update filter counts
        updateFilterCounts(channels);
        
        // Display channels (only if channelsGrid exists, e.g., on main page)
        const channelsGrid = document.getElementById('channelsGrid');
        if (channelsGrid) {
            displayChannels(channels, channelUrls);
        }
        
        // Setup search functionality (only if search input exists)
        const searchInput = document.getElementById('channelSearch');
        if (searchInput) {
            setupChannelSearch();
        }
        
        // Refresh channel dropdown for playlist controls
        await loadChannelDropdown();
    } catch (error) {
        console.error('Failed to load channels:', error);
        showToast('Failed to load channels', 'error');
    }
}

function displayChannels(channels, channelUrls) {
    const grid = document.getElementById('channelsGrid');
    
    // Skip if channelsGrid doesn't exist (e.g., on VOD page)
    if (!grid) {
        return;
    }
    
    // Get search term safely
    const searchInput = document.getElementById('channelSearch');
    const searchTerm = searchInput ? searchInput.value.trim() : '';
    
    if (channels.length === 0) {
        if (searchTerm) {
            grid.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-secondary);">${t('channels.noResults')}</div>`;
        } else {
            grid.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-secondary);">${t('messages.noChannelsConfigured')}</div>`;
        }
        return;
    }

    grid.innerHTML = channels.map(ch => {
        const statusColor = ch.status === 'running' ? 'var(--success)' : 'var(--text-secondary)';
        
        // Get current transcoding and subtitle settings
        const transcodingSetting = getChannelTranscodingSetting(ch.name);
        const subtitlesSetting = getChannelSubtitlesSetting(ch.name);
        
        // Get proper URLs for this channel (with fallback)
        const urls = channelUrls[ch.name] || {};
        
        // Highlight search term in channel name
        let displayName = ch.name;
        if (searchTerm) {
            const regex = new RegExp(`(${searchTerm})`, 'gi');
            displayName = ch.name.replace(regex, '<span class="search-highlight">$1</span>');
        }
        
        return `
            <div class="channel-card" style="${ch.enabled ? '' : 'opacity: 0.6;'}">
                <div class="channel-header">
                    <div class="channel-name">${displayName}</div>
                    <div class="channel-type ${ch.type}">${ch.type}</div>
                    <div class="channel-toggle">
                        <label class="toggle-switch">
                            <input type="checkbox" ${ch.enabled ? 'checked' : ''} 
                                   onchange="toggleChannel('${ch.name}', this.checked)">
                            <span class="toggle-slider"></span>
                        </label>
                        <span class="toggle-label">${ch.enabled ? t('channels.enabled') : t('channels.disabled')}</span>
                    </div>
                </div>
                <div class="channel-info">
                    ${t('channels.status')}: <strong style="color: ${statusColor}">${ch.status}</strong><br>
                    ${t('channels.type')}: ${ch.type.toUpperCase()}
                </div>
                
                <!-- Channel Settings -->
                <div class="channel-settings">
                    <div class="setting-row">
                        <label class="setting-label">${t('channels.transcoding')}:</label>
                        <select class="setting-select" onchange="updateChannelSetting('${ch.name}', 'transcoding', this.value)">
                            <option value="global" ${transcodingSetting === 'global' ? 'selected' : ''}>${t('channels.global')}</option>
                            <option value="enabled" ${transcodingSetting === 'enabled' ? 'selected' : ''}>${t('channels.enabled_setting')}</option>
                            <option value="disabled" ${transcodingSetting === 'disabled' ? 'selected' : ''}>${t('channels.disabled_setting')}</option>
                        </select>
                    </div>
                    <div class="setting-row">
                        <label class="setting-label">${t('channels.subtitles')}:</label>
                        <select class="setting-select" onchange="updateChannelSetting('${ch.name}', 'subtitles', this.value)">
                            <option value="global" ${subtitlesSetting === 'global' ? 'selected' : ''}>${t('channels.global')}</option>
                            <option value="enabled" ${subtitlesSetting === 'enabled' ? 'selected' : ''}>${t('channels.enabled_setting')}</option>
                            <option value="disabled" ${subtitlesSetting === 'disabled' ? 'selected' : ''}>${t('channels.disabled_setting')}</option>
                        </select>
                    </div>
                    <div class="setting-row">
                        <label class="setting-label">${t('channels.type')}:</label>
                        <select class="setting-select" onchange="updateChannelSetting('${ch.name}', 'type', this.value)">
                            <option value="linear" ${ch.type === 'linear' ? 'selected' : ''}>Linear</option>
                            <option value="vod" ${ch.type === 'vod' ? 'selected' : ''}>VOD</option>
                            <option value="dynamic" ${ch.type === 'dynamic' ? 'selected' : ''}>Dynamic</option>
                        </select>
                    </div>
                    <div class="setting-row">
                        <button class="btn-small btn-secondary" onclick="reloadChannelSchedule('${ch.name}')">
                            ${t('channels.reloadSchedule')}
                        </button>
                        <button class="btn-small btn-danger" onclick="confirmDeleteChannel('${ch.name}')">
                            ${t('channels.delete')}
                        </button>
                    </div>
                    ${ch.enabled ? `
                        <div class="setting-row">
                            ${ch.status !== 'running' ? `
                                <button class="btn-small btn-success" onclick="startChannel('${ch.name}')">
                                    ${t('channels.startChannel') || 'Start Channel'}
                                </button>
                            ` : `
                                <button class="btn-small btn-warning" onclick="stopChannelWorker('${ch.name}')">
                                    ${t('channels.stopChannel')}
                                </button>
                                <button class="btn-small btn-primary" onclick="restartChannel('${ch.name}')"
                                        ${ch.status !== 'running' ? 'disabled title="Channel not running"' : ''}>
                                    ${t('channels.restartChannel')}
                                </button>
                            `}
                        </div>
                    ` : ''}
                </div>
                
                ${ch.enabled ? `
                    ${generateChannelUrls(ch.name, urls)}
                    ${ch.type !== 'linear' ? `
                        <div class="channel-controls">
                            <button class="btn btn-danger btn-small" onclick="stopChannel('${ch.name}')">${t('channels.stopCurrentVideo')}</button>
                        </div>
                    ` : ''}
                ` : `
                    <div style="text-align: center; padding: 10px; color: var(--text-secondary); font-size: 12px;">
                        ${t('channels.channelDisabled')}
                    </div>
                `}
            </div>
        `;
    }).join('');
}

// Channel Search Functionality
function setupChannelSearch() {
    const searchInput = document.getElementById('channelSearch');
    const clearBtn = document.getElementById('searchClearBtn');
    const resultsInfo = document.getElementById('searchResultsInfo');
    
    // Skip if elements don't exist
    if (!searchInput || !clearBtn) {
        return;
    }
    
    // Search input event
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.trim();
        
        // Show/hide clear button
        clearBtn.style.display = searchTerm ? 'flex' : 'none';
        
        // Filter channels
        filterChannels(searchTerm);
    });
    
    // Clear search
    clearBtn.addEventListener('click', function() {
        searchInput.value = '';
        clearBtn.style.display = 'none';
        resultsInfo.style.display = 'none';
        filterChannels('');
    });
    
    // Enter key to focus first result
    searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            const firstChannel = document.querySelector('.channel-card');
            if (firstChannel) {
                firstChannel.scrollIntoView({ behavior: 'smooth', block: 'center' });
                firstChannel.style.transform = 'scale(1.02)';
                setTimeout(() => {
                    firstChannel.style.transform = '';
                }, 300);
            }
        }
    });
}

function filterChannels(searchTerm) {
    const resultsInfo = document.getElementById('searchResultsInfo');
    
    // Apply both search and status filters
    let filteredChannels = allChannelsData;
    
    // Apply status filter first
    if (currentChannelFilter === 'enabled') {
        filteredChannels = filteredChannels.filter(channel => channel.enabled);
    } else if (currentChannelFilter === 'disabled') {
        filteredChannels = filteredChannels.filter(channel => !channel.enabled);
    }
    
    // Apply search filter
    if (searchTerm) {
        filteredChannels = filteredChannels.filter(channel => 
            channel.name.toLowerCase().includes(searchTerm.toLowerCase())
        );
    }
    
    // Get URLs from the cached API data (loaded in loadChannels)
    const urlsData = window.cachedChannelUrls || {};
    const channelUrls = urlsData.channels || {};
    
    // Display filtered channels
    displayChannels(filteredChannels, channelUrls);
    
    // Show search results info
    if (searchTerm) {
        if (filteredChannels.length > 0) {
            resultsInfo.innerHTML = `<span class="search-icon">🔍</span> ${filteredChannels.length} ${t('channels.searchResults')}`;
            resultsInfo.style.display = 'flex';
        } else {
            resultsInfo.innerHTML = `<span class="search-icon">🔍</span> ${t('channels.noResults')}`;
            resultsInfo.style.display = 'flex';
        }
    } else {
        resultsInfo.style.display = 'none';
    }
}

// Channel Filter Functions
function updateFilterCounts(channels) {
    const allCount = channels.length;
    const enabledCount = channels.filter(ch => ch.enabled).length;
    const disabledCount = channels.filter(ch => !ch.enabled).length;
    
    // Check if elements exist before setting textContent (for pages without channel filters like VOD)
    const countAllEl = document.getElementById('countAll');
    const countEnabledEl = document.getElementById('countEnabled');
    const countDisabledEl = document.getElementById('countDisabled');
    
    if (countAllEl) countAllEl.textContent = allCount;
    if (countEnabledEl) countEnabledEl.textContent = enabledCount;
    if (countDisabledEl) countDisabledEl.textContent = disabledCount;
}

function setChannelFilter(filter) {
    currentChannelFilter = filter;
    
    // Update button states
    document.getElementById('filterAll').classList.toggle('active', filter === 'all');
    document.getElementById('filterEnabled').classList.toggle('active', filter === 'enabled');
    document.getElementById('filterDisabled').classList.toggle('active', filter === 'disabled');
    
    // Apply current search term with new filter
    const searchTerm = document.getElementById('channelSearch').value.trim();
    filterChannels(searchTerm);
}

function clearChannelSearch() {
    const searchInput = document.getElementById('channelSearch');
    const clearBtn = document.getElementById('searchClearBtn');
    const resultsInfo = document.getElementById('searchResultsInfo');
    
    searchInput.value = '';
    clearBtn.style.display = 'none';
    resultsInfo.style.display = 'none';
    
    // Apply current filter without search term
    filterChannels('');
}

function generateChannelUrls(channelName, urls) {
    // Try to get URL from cached API data if not provided
    if (!urls || Object.keys(urls).length === 0) {
        const cachedUrls = window.cachedChannelUrls;
        if (cachedUrls && cachedUrls.channels && cachedUrls.channels[channelName]) {
            urls = cachedUrls.channels[channelName];
        }
    }
    
    if (!urls || Object.keys(urls).length === 0) {
        // Fallback: use cached API data to build URL with correct LAN IP and port
        const cachedUrls = window.cachedChannelUrls;
        const port = cachedUrls?.port || '8081';
        const localIp = cachedUrls?.local_ip || '127.0.0.1';
        const fallbackUrl = `http://${localIp}:${port}/hls/${channelName}/index.m3u8`;
        return `<div class="channel-url">
            <div class="url-label">📺 Stream:</div>
            <span style="overflow: hidden; text-overflow: ellipsis;">${fallbackUrl}</span>
            <button class="copy-btn" onclick="copyToClipboard('${fallbackUrl}')">Copy</button>
        </div>`;
    }
    
    let urlsHtml = '';
    
    // LAN URL
    if (urls.lan && urls.lan.stream) {
        urlsHtml += `
            <div class="channel-url">
                <div class="url-label">📺 LAN Stream:</div>
                <span style="overflow: hidden; text-overflow: ellipsis;">${urls.lan.stream}</span>
                <button class="copy-btn" onclick="copyToClipboard('${urls.lan.stream}')">Copy</button>
            </div>
        `;
    }
    
    // Tailscale URL
    if (urls.tailscale && urls.tailscale.stream) {
        urlsHtml += `
            <div class="channel-url">
                <div class="url-label">🌐 Tailscale Stream:</div>
                <span style="overflow: hidden; text-overflow: ellipsis;">${urls.tailscale.stream}</span>
                <button class="copy-btn" onclick="copyToClipboard('${urls.tailscale.stream}')">Copy</button>
            </div>
        `;
    }
    
    // If we have URLs but none of the expected ones, show fallback
    if (!urlsHtml) {
        const cachedUrls = window.cachedChannelUrls;
        const port = cachedUrls?.port || '8081';
        const localIp = cachedUrls?.local_ip || '127.0.0.1';
        const fallbackUrl = `http://${localIp}:${port}/hls/${channelName}/index.m3u8`;
        return `<div class="channel-url">
            <div class="url-label">📺 Stream:</div>
            <span style="overflow: hidden; text-overflow: ellipsis;">${fallbackUrl}</span>
            <button class="copy-btn" onclick="copyToClipboard('${fallbackUrl}')">Copy</button>
        </div>`;
    }
    
    return urlsHtml;
}

// Get Channel URL
function getChannelUrl(channel) {
    // Try to get URL from cached API data first
    const cachedUrls = window.cachedChannelUrls;
    if (cachedUrls && cachedUrls.channels && cachedUrls.channels[channel]) {
        const channelUrl = cachedUrls.channels[channel];
        if (channelUrl.lan && channelUrl.lan.stream) {
            return channelUrl.lan.stream;
        }
    }
    // Fallback: use cached API data to build URL with correct LAN IP and port
    const port = cachedUrls?.port || '8081';
    const localIp = cachedUrls?.local_ip || '127.0.0.1';
    return `http://${localIp}:${port}/hls/${channel}/index.m3u8`;
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

async function clearLogFiles() {
    if (!confirm('Clear all log files?')) return;
    try {
        const result = await apiCall('/api/logs/clear', 'POST');
        if (result.success) {
            showToast(result.message, 'success');
        } else {
            showToast(result.message || 'Failed to clear logs', 'error');
        }
    } catch (error) {
        showToast('Failed to clear logs', 'error');
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

async function exitApplication() {
    if (!confirm('Exit AkiraTV? This will stop all streams and shut down the server.')) return;
    try {
        await apiCall('/api/stop', 'POST');
        showToast('Shutting down...', 'info');
        // Give the stop response time to be sent, then shutdown the server
        setTimeout(async () => {
            await apiCall('/api/shutdown', 'POST');
        }, 500);
    } catch (error) {
        showToast('Failed to shutdown', 'error');
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

// Playlist Controls Functions (Legacy - kept for compatibility)
async function loadChannelDropdown() {
    try {
        const select = document.getElementById('channelSelect');
        if (!select) return; // Element doesn't exist on this page
        
        const data = await apiCall('/api/channels');
        const channels = data.channels;
        
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
        const select = document.getElementById('channelSelect');
        if (select) select.innerHTML = '<option value="">Error loading channels</option>';
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
    
    if (!channelSelect || !pathInput) return; // Elements don't exist on this page
    
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
    if (!folderInput) return; // Element doesn't exist on this page
    
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
    const playlistSelect = document.getElementById('playlistSelect');
    if (!playlistSelect) return; // Element doesn't exist on this page
    
    try {
        const result = await apiCall('/api/playlist/videos');
        
        // Clear existing options
        playlistSelect.innerHTML = '';
        
        if (result.videos.length === 0) {
            playlistSelect.innerHTML = '<option value="">No playlist loaded</option>';
            return;
        }
        
        // Add videos to dropdown
        result.videos.forEach(video => {
            const option = document.createElement('option');
            option.value = video.name;
            option.textContent = video.name;
            playlistSelect.appendChild(option);
        });
        
        // Select first video
        if (result.videos.length > 0) {
            playlistSelect.value = result.videos[0].name;
        }
        
    } catch (error) {
        console.error('Failed to refresh playlist:', error);
        const select = document.getElementById('playlistSelect');
        if (select) select.innerHTML = '<option value="">Error loading playlist</option>';
    }
}

async function playSelectedVideo() {
    const channelSelect = document.getElementById('channelSelect');
    const playlistSelect = document.getElementById('playlistSelect');
    
    if (!channelSelect || !playlistSelect) return; // Elements don't exist on this page
    
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

async function stopSelectedChannel() {
    const channelSelect = document.getElementById('channelSelect');
    if (!channelSelect) return; // Element doesn't exist on this page
    
    const channel = channelSelect.value;
    
    if (!channel) {
        showToast('Please select a channel', 'error');
        return;
    }
    
    try {
        const result = await apiCall(`/api/channels/${channel}/stop`, 'POST');
        if (result.success) {
            showToast(result.message, 'success');
        } else {
            showToast(result.error || 'Failed to stop channel', 'error');
        }
    } catch (error) {
        showToast('Failed to stop channel', 'error');
    }
}

async function stopChannelWorker(channel) {
    const confirmed = confirm(
        `Stop channel '${channel}' completely?\n\n` +
        `This will:\n` +
        `• Stop the channel worker\n` +
        `• Disconnect viewers\n` +
        `• Channel will need to be restarted manually\n\n` +
        `Click OK to stop or Cancel to keep running.`
    );
    
    if (!confirmed) return;
    
    try {
        const result = await apiCall(`/api/channels/${channel}/stop-worker`, 'POST');
        if (result.success) {
            showToast(result.message, 'success');
            // Reload channels to update status
            await loadChannels();
        } else {
            showToast(result.error || 'Failed to stop channel', 'error');
        }
    } catch (error) {
        showToast('Failed to stop channel', 'error');
    }
}

async function startChannel(channel) {
    try {
        showToast(`Starting channel '${channel}'...`, 'info');
        const result = await apiCall(`/api/channels/${channel}/start`, 'POST');
        if (result.success) {
            showToast(result.message, 'success');
            // Reload channels to update status
            await loadChannels();
        } else {
            showToast(result.error || 'Failed to start channel', 'error');
        }
    } catch (error) {
        showToast('Failed to start channel', 'error');
    }
}

async function restartChannel(channel) {
    const confirmed = confirm(
        `Restart channel '${channel}'?\n\n` +
        `This will:\n` +
        `• Stop the current channel worker\n` +
        `• Start a fresh worker instance\n` +
        `• Briefly disconnect viewers during restart\n\n` +
        `Click OK to restart or Cancel to keep current state.`
    );
    
    if (!confirmed) return;
    
    try {
        showToast(`Restarting channel '${channel}'...`, 'info');
        const result = await apiCall(`/api/channels/${channel}/restart`, 'POST');
        if (result.success) {
            showToast(result.message, 'success');
            // Reload channels to update status
            await loadChannels();
        } else {
            showToast(result.error || 'Failed to restart channel', 'error');
        }
    } catch (error) {
        showToast('Failed to restart channel', 'error');
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

// Channel Stop Function
async function stopChannel(channel) {
    try {
        const result = await apiCall(`/api/channels/${channel}/stop`, 'POST');
        if (result.success) {
            showToast(result.message, 'success');
        } else {
            showToast(result.error || 'Failed to stop channel', 'error');
        }
    } catch (error) {
        showToast('Failed to stop channel', 'error');
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
    
    // Load info data when info tab is shown
    if (tabName === 'info') {
        loadInfoData();
    }
    
    // Load collections status when collections tab is shown
    if (tabName === 'collections') {
        loadCollectionStatus();
    }
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
        document.getElementById('ramPath').value = storage.ram_path || './output';
        toggleStoragePath();
        
        // Output settings
        const output = config.output || {};
        const http = output.http || {};
        document.getElementById('httpPort').value = http.port || 8081;
        
        const streaming = config.streaming || {};
        document.getElementById('enablePreGen').checked = streaming.pre_gen || false;
        
        // FFmpeg bin dir — show effective dir as placeholder, stored override as value
        const binDirInput = document.getElementById('ffmpegBinDir');
        if (binDirInput) {
            binDirInput.placeholder = 'Auto-detected: ' + (config._ffmpeg_bin_dir || '/usr/bin');
            binDirInput.value = ffmpeg.bin_dir || '';
        }
        
        // Handle custom bitrate visibility
        toggleCustomBitrate();
        
    } catch (error) {
        console.error('Failed to load configuration:', error);
        showToast('Failed to load configuration', 'error');
    }
}

async function loadInfoData() {
    try {
        // Get engine status
        const statusResult = await apiCall('/api/status');
        const engineStatus = statusResult.is_running ? 'Running' : 'Stopped';
        document.getElementById('infoEngineStatus').textContent = engineStatus;
        document.getElementById('infoEngineStatus').className = 'status-value ' + (statusResult.is_running ? 'status-active' : 'status-inactive');
        
        // Get channels
        const channelsResult = await apiCall('/api/channels');
        const channels = channelsResult.channels || {};
        const enabledChannels = Object.values(channels).filter(ch => ch.enabled).length;
        const totalChannels = Object.keys(channels).length;
        document.getElementById('infoChannelCount').textContent = `${enabledChannels} enabled / ${totalChannels} total`;
        
        // Get config for storage and transcoding
        const config = await apiCall('/api/config');
        
        // Storage mode
        const storage = config.storage || {};
        const storageType = storage.type || 'disk';
        document.getElementById('infoStorageMode').textContent = storageType === 'ram' ? 'RAM Disk' : 'Disk';
        
        // Transcoding status
        let transcodingEnabled = false;
        for (const channel of Object.values(channels)) {
            if (channel.transcoding?.enabled) {
                transcodingEnabled = true;
                break;
            }
        }
        document.getElementById('infoTranscoding').textContent = transcodingEnabled ? 'Enabled' : 'Disabled (using -c copy)';
        
    } catch (error) {
        console.error('Failed to load info data:', error);
        document.getElementById('infoEngineStatus').textContent = 'Error';
        document.getElementById('infoChannelCount').textContent = 'Error';
        document.getElementById('infoStorageMode').textContent = 'Error';
        document.getElementById('infoTranscoding').textContent = 'Error';
    }
}

// ============================================
// Path Fixer Functions (for Android Migration)
// ============================================

async function loadCollectionStatus() {
    const statusDiv = document.getElementById('collectionStatus');
    if (!statusDiv) return;
    
    try {
        // Try to get list of collection files
        const response = await fetch('/api/library/collections');
        let collectionsInfo = '<p>Collection files found:</p><ul>';
        
        // For now, just show a placeholder
        collectionsInfo += '<li>Check user/collections/ directory</li>';
        collectionsInfo += '</ul>';
        collectionsInfo += '<p><strong>Tip:</strong> Use the Path Fixer below to update Windows paths to Android USB paths.</p>';
        
        statusDiv.innerHTML = collectionsInfo;
    } catch (error) {
        statusDiv.innerHTML = '<p>Error loading collection status: ' + error.message + '</p>';
    }
}

async function fixPaths() {
    const oldPrefix = document.getElementById('oldPathPrefix')?.value;
    const newPrefix = document.getElementById('newPathPrefix')?.value;
    const resultDiv = document.getElementById('fixPathsResult');
    
    if (!oldPrefix || !newPrefix) {
        resultDiv.innerHTML = '<span style="color: red;">Please enter both old and new path prefixes.</span>';
        return;
    }
    
    resultDiv.innerHTML = '<span>Fixing paths...</span>';
    
    try {
        const response = await fetch('/api/config/fix-paths', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ oldPrefix, newPrefix })
        });
        
        const result = await response.json();
        
        if (result.success) {
            resultDiv.innerHTML = `<span style="color: green;">✅ Fixed ${result.fixed} collection(s)!</span>`;
        } else {
            resultDiv.innerHTML = `<span style="color: red;">❌ Error: ${result.error}</span>`;
        }
    } catch (error) {
        resultDiv.innerHTML = `<span style="color: red;">❌ Error: ${error.message}</span>`;
    }
}

function autoDetectUSB() {
    // Try to get USB path from API (set by Android)
    const newPrefixInput = document.getElementById('newPathPrefix');
    const resultDiv = document.getElementById('fixPathsResult');
    
    // First try to get USB path from config API
    fetch('/api/config/usb-path')
        .then(res => res.json())
        .then(data => {
            if (data.usbPath) {
                // USB path is configured, use it
                const videoPath = data.usbPath + '/AkiraTV/videos';
                newPrefixInput.value = videoPath;
                resultDiv.innerHTML = `<span style="color: green;">✅ USB detected: ${data.usbPath}</span>`;
            } else {
                // No USB configured, check monitoring API for Android system info
                return fetch('/api/monitoring/system');
            }
        })
        .then(res => res ? res.json() : null)
        .then(sysInfo => {
            if (sysInfo && sysInfo.platform === 'android') {
                // On Android, suggest common USB paths
                newPrefixInput.placeholder = '/storage/XXXX-XXXX/AkiraTV/videos';
                resultDiv.innerHTML = `<span style="color: orange;">⚠️ USB not configured. Please enter the path to your USB drive manually, or configure it in Android settings.</span>`;
            } else {
                // Not on Android or no USB detected
                newPrefixInput.placeholder = '/storage/XXXX-XXXX/AkiraTV/videos';
                resultDiv.innerHTML = `<span style="color: orange;">⚠️ Run this on Android TV to auto-detect USB path.</span>`;
            }
        })
        .catch(error => {
            console.error('Auto-detect error:', error);
            newPrefixInput.placeholder = '/storage/XXXX-XXXX/AkiraTV/videos';
            resultDiv.innerHTML = `<span style="color: red;">❌ Error detecting USB: ${error.message}</span>`;
        });
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
        const binDirEl = document.getElementById('ffmpegBinDir');
        const binDir = binDirEl ? binDirEl.value.trim() : '';

        const config = {
            ffmpeg: {
                bin_dir: binDir || null,
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
            const viewersCount = document.getElementById('viewersCount');
            if (viewersCount) viewersCount.textContent = data.viewers || 0;
            
            const nowPlaying = document.getElementById('nowPlaying');
            if (nowPlaying) nowPlaying.textContent = data.stats?.now_playing || 'No program info';
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

// Open TV Guide in separate page
function openTVGuide() {
    window.open('/static/guide.html', '_blank');
}

// Open Viewer in separate page
function openViewer() {
    window.open('/static/viewer.html', '_blank');
}

// Open VOD Library in separate page
function openVODLibrary() {
    window.open('/static/vod.html', '_blank');
}

// Open Wizard in separate page
function openWizard() {
    window.open('/wizard', '_blank');
}

// ========================================
// FAST SCHEDULER FUNCTIONS
// ========================================

let fastSchedulerData = {
    selectedChannel: '',
    selectedCollections: [],
    settings: {
        startTime: '00:00',
        scheduleHours: 24,
        bumperFrequency: 3,
        trailerProbability: 0.3
    }
};

async function showFastSchedulerWizard() {
    document.getElementById('fastSchedulerModal').style.display = 'block';
    await loadFastSchedulerInterface();
}

function hideFastScheduler() {
    document.getElementById('fastSchedulerModal').style.display = 'none';
}

async function loadFastSchedulerInterface() {
    try {
        // Load available channels and collections
        const [channelsData, collectionsData] = await Promise.all([
            apiCall('/api/channels'),
            apiCall('/api/fast-schedule/collections')
        ]);
        
        const channels = channelsData.channels.filter(ch => ch.enabled);
        const collections = collectionsData.data.collections;
        
        const html = `
            <div class="fast-scheduler-container">
                <div class="fast-scheduler-step">
                    <h4>⚡ Fast Scheduler Setup</h4>
                    <p>Create dynamic schedules on-the-fly from your collections without JSON files.</p>
                </div>
                
                <div class="fast-scheduler-step">
                    <label class="setting-label">📺 Select Channel:</label>
                    <select id="fastSchedulerChannel" class="setting-select" onchange="updateFastSchedulerChannel()">
                        <option value="">Choose a channel...</option>
                        ${channels.map(ch => `<option value="${ch.name}">${ch.name} (${ch.type})</option>`).join('')}
                    </select>
                </div>
                
                <div class="fast-scheduler-step">
                    <label class="setting-label">📁 Select Collections:</label>
                    <div class="collections-grid">
                        ${collections.map(col => `
                            <label class="collection-checkbox">
                                <input type="checkbox" value="${col.name}" onchange="updateFastSchedulerCollections()">
                                <span>${col.name} (${col.video_count} videos)</span>
                            </label>
                        `).join('')}
                    </div>
                </div>
                
                <div class="fast-scheduler-step">
                    <h5>⚙️ Schedule Settings</h5>
                    <div class="settings-grid">
                        <div class="setting-row">
                            <label class="setting-label">🕐 Start Time:</label>
                            <input type="time" id="fastSchedulerStartTime" value="00:00" class="setting-input">
                        </div>
                        <div class="setting-row">
                            <label class="setting-label">⏰ Schedule Hours:</label>
                            <input type="number" id="fastSchedulerHours" value="24" min="1" max="168" class="setting-input">
                        </div>
                        <div class="setting-row">
                            <label class="setting-label">🎬 Bumper Frequency:</label>
                            <input type="number" id="fastSchedulerBumpers" value="3" min="1" max="10" class="setting-input">
                            <small>Insert bumper every N videos</small>
                        </div>
                        <div class="setting-row">
                            <label class="setting-label">🎭 Trailer Probability:</label>
                            <input type="range" id="fastSchedulerTrailers" value="30" min="0" max="100" class="setting-range">
                            <span id="trailerPercentage">30%</span>
                        </div>
                    </div>
                </div>
                
                <div class="fast-scheduler-preview" id="fastSchedulerPreview" style="display: none;">
                    <h5>📋 Schedule Preview</h5>
                    <div id="schedulePreviewContent"></div>
                </div>
            </div>
        `;
        
        document.getElementById('fastSchedulerBody').innerHTML = html;
        
        // Setup trailer percentage display
        document.getElementById('fastSchedulerTrailers').addEventListener('input', function() {
            document.getElementById('trailerPercentage').textContent = this.value + '%';
        });
        
    } catch (error) {
        console.error('Failed to load Fast Scheduler interface:', error);
        document.getElementById('fastSchedulerBody').innerHTML = 
            '<div style="color: var(--error); text-align: center; padding: 20px;">Failed to load Fast Scheduler interface</div>';
    }
}

function updateFastSchedulerChannel() {
    const channel = document.getElementById('fastSchedulerChannel').value;
    fastSchedulerData.selectedChannel = channel;
    updateFastSchedulerButton();
}

function updateFastSchedulerCollections() {
    const checkboxes = document.querySelectorAll('.collection-checkbox input[type="checkbox"]:checked');
    fastSchedulerData.selectedCollections = Array.from(checkboxes).map(cb => cb.value);
    updateFastSchedulerButton();
}

function updateFastSchedulerButton() {
    const button = document.getElementById('fastSchedulerAction');
    const canGenerate = fastSchedulerData.selectedChannel && fastSchedulerData.selectedCollections.length > 0;
    button.disabled = !canGenerate;
}

async function executeFastScheduler() {
    try {
        const button = document.getElementById('fastSchedulerAction');
        button.disabled = true;
        button.textContent = 'Generating...';
        
        // Get settings
        const settings = {
            collections: fastSchedulerData.selectedCollections,
            start_time: document.getElementById('fastSchedulerStartTime').value,
            schedule_hours: parseInt(document.getElementById('fastSchedulerHours').value),
            bumper_frequency: parseInt(document.getElementById('fastSchedulerBumpers').value),
            trailer_probability: parseFloat(document.getElementById('fastSchedulerTrailers').value) / 100
        };
        
        const channel = fastSchedulerData.selectedChannel;
        
        // Step 1: Load collections
        showToast('Loading collections...', 'info');
        const loadResult = await apiCall(`/api/fast-schedule/${channel}/load-collections`, 'POST', settings);
        
        if (!loadResult.success) {
            throw new Error(loadResult.error || 'Failed to load collections');
        }
        
        // Step 2: Generate schedule
        showToast('Generating schedule...', 'info');
        const generateResult = await apiCall(`/api/fast-schedule/${channel}/generate`, 'POST', settings);
        
        if (!generateResult.success) {
            throw new Error(generateResult.error || 'Failed to generate schedule');
        }
        
        // Success!
        showToast(
            `✅ Fast Schedule Created!\n\n` +
            `Channel: ${channel}\n` +
            `Entries: ${generateResult.data.entries}\n` +
            `Videos: ${generateResult.data.videos}\n` +
            `Bumpers: ${generateResult.data.bumpers}\n\n` +
            `Schedule is now active and saved as checkpoint.`,
            'success'
        );
        
        hideFastScheduler();
        
        // Refresh channels to show updated status
        await loadChannels();
        
    } catch (error) {
        console.error('Fast Scheduler error:', error);
        showToast(`Failed to create fast schedule: ${error.message}`, 'error');
    } finally {
        const button = document.getElementById('fastSchedulerAction');
        button.disabled = false;
        button.textContent = 'Generate Schedule';
    }
}

// ========================================
// VIEWER DETAILS FUNCTIONS
// ========================================

async function refreshViewerDetails() {
    try {
        const response = await fetch('/api/viewers/detail');
        const data = await response.json();
        
        // Update total
        const totalEl = document.getElementById('totalViewers');
        if (totalEl) {
            totalEl.textContent = data.total;
        }
        
        // Build viewer list
        const listEl = document.getElementById('viewerList');
        if (!listEl) return;
        
        if (data.viewers.length === 0) {
            listEl.innerHTML = '<p class="no-viewers">No active viewers</p>';
            return;
        }
        
        // Group by channel
        const byChannel = {};
        data.viewers.forEach(v => {
            if (!byChannel[v.channel]) byChannel[v.channel] = [];
            byChannel[v.channel].push(v);
        });
        
        let html = '';
        for (const [channel, viewers] of Object.entries(byChannel)) {
            html += `<div class="channel-group">
                <div class="channel-header">${channel} (${viewers.length})</div>
                <div class="channel-viewers">`;
            
            viewers.forEach(v => {
                html += `<div class="viewer-row">
                    <span class="viewer-ip">${v.ip}</span>
                    <span class="viewer-time">${v.seconds_ago}s ago</span>
                </div>`;
            });
            
            html += '</div></div>';
        }
        listEl.innerHTML = html;
        
    } catch (error) {
        console.error('Failed to fetch viewer details:', error);
    }
}

// Auto-refresh viewer details every 10 seconds
setInterval(refreshViewerDetails, 10000);

// Initialize on load
init();
