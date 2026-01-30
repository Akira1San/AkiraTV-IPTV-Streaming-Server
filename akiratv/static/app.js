// AkiraTV Web UI JavaScript

const API_BASE = window.location.origin;
let ws = null;
let isRunning = false;

// Internationalization
let currentLanguage = 'en';

const translations = {
    en: {
        // Status and stats
        'status.checking': 'Checking...',
        'status.streaming': 'Streaming',
        'status.stopped': 'Stopped',
        'stats.channels': 'Channels',
        'stats.viewers': 'Viewers',
        'stats.uptime': 'Uptime',
        'stats.status': 'Status',
        
        // Now Playing
        'nowPlaying.title': 'NOW PLAYING',
        'nowPlaying.noInfo': 'No program info',
        
        // Control Panel
        'control.title': '🎮 Control Panel',
        'control.start': '▶️ Start Streaming',
        'control.stop': '⏹️ Stop Streaming',
        'control.restart': '🔄 Restart',
        'control.clearCache': '🗑️ Clear Cache',
        'control.reloadSchedule': '📅 Reload Schedule',
        'control.configuration': '⚙️ Configuration',
        'control.generateXMLTV': '📺 Generate XMLTV for Kodi',
        'control.openConfig': '📝 Open Config',
        'control.openLogs': '📋 Open Logs',
        
        // TV Guide
        'guide.title': '📺 TV Guide',
        'guide.today': '📅 Today',
        'guide.weekly': '📆 Weekly',
        'guide.refresh': '🔄 Refresh Guide',
        'guide.loading': 'Loading...',
        'guide.loadingText': 'Loading TV Guide...',
        'guide.currentTime': 'Current Time',
        'guide.nowPlaying': '🔴 NOW PLAYING',
        'guide.upNext': '⏭️ UP NEXT',
        'guide.noSchedule': '⏸️ NO SCHEDULE',
        'guide.noProgram': 'No current program',
        'guide.todaySchedule': '📅 TODAY\'S SCHEDULE',
        'guide.started': 'Started',
        'guide.starts': 'Starts',
        'guide.programs': 'programs',
        'guide.today_indicator': 'TODAY',
        'guide.now_indicator': 'NOW',
        'guide.morePrograms': 'more programs',
        
        // Channels
        'channels.title': '📺 Channels',
        'channels.searchPlaceholder': 'Search channels...',
        'channels.enterChannelName': 'Enter channel name...',
        'channels.addChannel': '+ Add Channel',
        'channels.addChannelHelp': 'Use only letters, numbers, hyphens (-), and underscores (_)',
        'channels.loading': 'Loading channels...',
        'channels.enabled': 'Enabled',
        'channels.disabled': 'Disabled',
        'channels.status': 'Status',
        'channels.type': 'Type',
        'channels.transcoding': 'Transcoding',
        'channels.subtitles': 'Subtitles',
        'channels.global': 'Global',
        'channels.enabled_setting': 'Enabled',
        'channels.disabled_setting': 'Disabled',
        'channels.reloadSchedule': '📅 Reload Schedule',
        'channels.delete': '🗑️ Delete',
        'channels.stopChannel': '⏹️ Stop Channel',
        'channels.restartChannel': '🔄 Restart Channel',
        'channels.stopCurrentVideo': '⏹️ Stop Current Video',
        'channels.stream': '📺 Stream',
        'channels.lanStream': '📺 LAN Stream',
        'channels.tailscaleStream': '🌐 Tailscale Stream',
        'channels.ngrokStream': '🌍 Ngrok Stream',
        'channels.copy': 'Copy',
        'channels.channelDisabled': 'Channel disabled - enable to access streaming URL',
        'channels.searchResults': 'channels found',
        'channels.noResults': 'No channels match your search',
        'channels.showingAll': 'Showing all channels',
        
        // Messages
        'messages.urlCopied': 'URL copied!',
        'messages.engineStarted': 'Engine started successfully',
        'messages.engineStopped': 'Engine stopped',
        'messages.engineRestarting': 'Engine restarting...',
        'messages.cacheCleared': 'files cleared',
        'messages.schedulesReloaded': 'All schedules reloaded',
        'messages.guideRefreshed': 'TV Guide refreshed',
        'messages.failedToStart': 'Failed to start engine',
        'messages.failedToStop': 'Failed to stop engine',
        'messages.failedToRestart': 'Failed to restart engine',
        'messages.failedToClearCache': 'Failed to clear cache',
        'messages.failedToReloadSchedules': 'Failed to reload schedules',
        'messages.failedToLoadGuide': 'Failed to load TV Guide',
        'messages.noChannelsFound': 'No channels with schedules found',
        'messages.noChannelsConfigured': 'No channels configured'
    },
    bg: {
        // Status and stats
        'status.checking': 'Проверява...',
        'status.streaming': 'Стрийминг',
        'status.stopped': 'Спрян',
        'stats.channels': 'Канали',
        'stats.viewers': 'Зрители',
        'stats.uptime': 'Време работа',
        'stats.status': 'Статус',
        
        // Now Playing
        'nowPlaying.title': 'СЕГА СЕ ИЗЛЪЧВА',
        'nowPlaying.noInfo': 'Няма информация за програмата',
        
        // Control Panel
        'control.title': '🎮 Контролен панел',
        'control.start': '▶️ Стартирай стрийминг',
        'control.stop': '⏹️ Спри стрийминг',
        'control.restart': '🔄 Рестартирай',
        'control.clearCache': '🗑️ Изчисти кеша',
        'control.reloadSchedule': '📅 Презареди програмата',
        'control.configuration': '⚙️ Конфигурация',
        'control.generateXMLTV': '📺 Генерирай XMLTV за Kodi',
        'control.openConfig': '📝 Отвори конфигурацията',
        'control.openLogs': '📋 Отвори логовете',
        
        // TV Guide
        'guide.title': '📺 Телевизионна програма',
        'guide.today': '📅 Днес',
        'guide.weekly': '📆 Седмично',
        'guide.refresh': '🔄 Обнови програмата',
        'guide.loading': 'Зарежда...',
        'guide.loadingText': 'Зарежда телевизионната програма...',
        'guide.currentTime': 'Текущо време',
        'guide.nowPlaying': '🔴 СЕГА СЕ ИЗЛЪЧВА',
        'guide.upNext': '⏭️ СЛЕДВА',
        'guide.noSchedule': '⏸️ НЯМА ПРОГРАМА',
        'guide.noProgram': 'Няма текуща програма',
        'guide.todaySchedule': '📅 ДНЕШНА ПРОГРАМА',
        'guide.started': 'Започна',
        'guide.starts': 'Започва',
        'guide.programs': 'програми',
        'guide.today_indicator': 'ДНЕС',
        'guide.now_indicator': 'СЕГА',
        'guide.morePrograms': 'още програми',
        
        // Channels
        'channels.title': '📺 Канали',
        'channels.searchPlaceholder': 'Търсене на канали...',
        'channels.enterChannelName': 'Въведете име на канал...',
        'channels.addChannel': '+ Добави канал',
        'channels.addChannelHelp': 'Използвайте само букви, цифри, тирета (-) и долни черти (_)',
        'channels.loading': 'Зареждат се каналите...',
        'channels.enabled': 'Включен',
        'channels.disabled': 'Изключен',
        'channels.status': 'Статус',
        'channels.type': 'Тип',
        'channels.transcoding': 'Транскодиране',
        'channels.subtitles': 'Субтитри',
        'channels.global': 'Глобално',
        'channels.enabled_setting': 'Включено',
        'channels.disabled_setting': 'Изключено',
        'channels.reloadSchedule': '📅 Презареди програмата',
        'channels.delete': '🗑️ Изтрий',
        'channels.stopChannel': '⏹️ Спри канала',
        'channels.restartChannel': '🔄 Рестартирай канала',
        'channels.stopCurrentVideo': '⏹️ Спри текущото видео',
        'channels.stream': '📺 Стрийм',
        'channels.lanStream': '📺 LAN Стрийм',
        'channels.tailscaleStream': '🌐 Tailscale Стрийм',
        'channels.ngrokStream': '🌍 Ngrok Стрийм',
        'channels.copy': 'Копирай',
        'channels.channelDisabled': 'Каналът е изключен - включете го за достъп до стрийминг URL',
        'channels.searchResults': 'канала намерени',
        'channels.noResults': 'Няма канали, които да съответстват на търсенето',
        'channels.showingAll': 'Показват се всички канали',
        
        // Messages
        'messages.urlCopied': 'URL копиран!',
        'messages.engineStarted': 'Двигателят стартира успешно',
        'messages.engineStopped': 'Двигателят е спрян',
        'messages.engineRestarting': 'Двигателят се рестартира...',
        'messages.cacheCleared': 'файла изчистени',
        'messages.schedulesReloaded': 'Всички програми презаредени',
        'messages.guideRefreshed': 'Телевизионната програма е обновена',
        'messages.failedToStart': 'Неуспешно стартиране на двигателя',
        'messages.failedToStop': 'Неуспешно спиране на двигателя',
        'messages.failedToRestart': 'Неуспешно рестартиране на двигателя',
        'messages.failedToClearCache': 'Неуспешно изчистване на кеша',
        'messages.failedToReloadSchedules': 'Неуспешно презареждане на програмите',
        'messages.failedToLoadGuide': 'Неуспешно зареждане на телевизионната програма',
        'messages.noChannelsFound': 'Не са намерени канали с програми',
        'messages.noChannelsConfigured': 'Няма конфигурирани канали'
    }
};

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

// Load Channels
let allChannelsData = []; // Store all channels for search

async function loadChannels() {
    try {
        // Load channels and config first
        const [channelsData, configData] = await Promise.all([
            apiCall('/api/channels'),
            apiCall('/api/config')
        ]);
        
        globalConfig = configData;
        const channels = channelsData.channels;
        allChannelsData = channels; // Store for search
        
        console.log('📺 Loaded channels:', channels);
        
        // Use fallback URL generation with the actual streaming server
        let channelUrls = {};
        channels.forEach(ch => {
            if (ch.enabled) {
                channelUrls[ch.name] = {
                    lan: {
                        stream: `http://192.168.50.183:8081/hls/${ch.name}/index.m3u8`,
                        epg: `http://192.168.50.183:8081/xmltv.xml`
                    }
                };
            }
        });
        console.log('🔗 Using fallback channel URLs:', channelUrls);
        
        document.getElementById('channelsCount').textContent = channels.length;

        // Display channels (filtered if search is active)
        displayChannels(channels, channelUrls);
        
        // Setup search functionality
        setupChannelSearch();
        
        // Refresh channel dropdown for playlist controls
        await loadChannelDropdown();
    } catch (error) {
        console.error('Failed to load channels:', error);
        showToast('Failed to load channels', 'error');
    }
}

function displayChannels(channels, channelUrls) {
    const grid = document.getElementById('channelsGrid');
    
    if (channels.length === 0) {
        const searchTerm = document.getElementById('channelSearch').value.trim();
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
        const searchTerm = document.getElementById('channelSearch').value.trim();
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
                        <button class="btn-small btn-secondary" onclick="reloadChannelSchedule('${ch.name}')">
                            ${t('channels.reloadSchedule')}
                        </button>
                        <button class="btn-small btn-danger" onclick="confirmDeleteChannel('${ch.name}')">
                            ${t('channels.delete')}
                        </button>
                    </div>
                    ${ch.enabled ? `
                        <div class="setting-row">
                            <button class="btn-small btn-warning" onclick="stopChannelWorker('${ch.name}')" 
                                    ${ch.status !== 'running' ? 'disabled title="Channel not running"' : ''}>
                                ${t('channels.stopChannel')}
                            </button>
                            <button class="btn-small btn-primary" onclick="restartChannel('${ch.name}')"
                                    ${ch.status !== 'running' ? 'disabled title="Channel not running"' : ''}>
                                ${t('channels.restartChannel')}
                            </button>
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
    
    if (!searchTerm) {
        // Show all channels
        const channelUrls = {};
        allChannelsData.forEach(ch => {
            if (ch.enabled) {
                channelUrls[ch.name] = {
                    lan: {
                        stream: `http://192.168.50.183:8081/hls/${ch.name}/index.m3u8`,
                        epg: `http://192.168.50.183:8081/xmltv.xml`
                    }
                };
            }
        });
        displayChannels(allChannelsData, channelUrls);
        resultsInfo.style.display = 'none';
        return;
    }
    
    // Filter channels by name (case insensitive)
    const filteredChannels = allChannelsData.filter(channel => 
        channel.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
    
    // Generate URLs for filtered channels
    const channelUrls = {};
    filteredChannels.forEach(ch => {
        if (ch.enabled) {
            channelUrls[ch.name] = {
                lan: {
                    stream: `http://192.168.50.183:8081/hls/${ch.name}/index.m3u8`,
                    epg: `http://192.168.50.183:8081/xmltv.xml`
                }
            };
        }
    });
    
    // Display filtered channels
    displayChannels(filteredChannels, channelUrls);
    
    // Show search results info
    if (filteredChannels.length > 0) {
        resultsInfo.innerHTML = `<span class="search-icon">🔍</span> ${filteredChannels.length} ${t('channels.searchResults')}`;
        resultsInfo.style.display = 'flex';
    } else {
        resultsInfo.innerHTML = `<span class="search-icon">🔍</span> ${t('channels.noResults')}`;
        resultsInfo.style.display = 'flex';
    }
}

function clearChannelSearch() {
    const searchInput = document.getElementById('channelSearch');
    const clearBtn = document.getElementById('searchClearBtn');
    const resultsInfo = document.getElementById('searchResultsInfo');
    
    searchInput.value = '';
    clearBtn.style.display = 'none';
    resultsInfo.style.display = 'none';
    filterChannels('');
}

function generateChannelUrls(channelName, urls) {
    if (!urls || Object.keys(urls).length === 0) {
        // Fallback to a basic URL with your actual streaming server
        const fallbackUrl = `http://192.168.50.183:8081/hls/${channelName}/index.m3u8`;
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
    
    // Ngrok URL (if configured)
    if (urls.ngrok && urls.ngrok.stream) {
        urlsHtml += `
            <div class="channel-url">
                <div class="url-label">🌍 Ngrok Stream:</div>
                <span style="overflow: hidden; text-overflow: ellipsis;">${urls.ngrok.stream}</span>
                <button class="copy-btn" onclick="copyToClipboard('${urls.ngrok.stream}')">Copy</button>
            </div>
        `;
    }
    
    // If we have URLs but none of the expected ones, show fallback
    if (!urlsHtml) {
        const fallbackUrl = `http://192.168.50.183:8081/hls/${channelName}/index.m3u8`;
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
    // This will be replaced by the proper URLs from the API
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

async function stopSelectedChannel() {
    const channelSelect = document.getElementById('channelSelect');
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

// TV Guide Functions
let currentGuideView = 'daily'; // 'daily' or 'weekly'

async function loadTVGuide() {
    try {
        let guideData;
        if (currentGuideView === 'weekly') {
            guideData = await apiCall('/api/guide/weekly');
            displayWeeklyTVGuide(guideData);
        } else {
            guideData = await apiCall('/api/guide');
            displayTVGuide(guideData);
        }
        
        // Update guide time
        const now = new Date();
        document.getElementById('guideTime').textContent = 
            `${t('guide.currentTime')}: ${now.toLocaleTimeString()} - ${now.toLocaleDateString()}`;
            
    } catch (error) {
        console.error('Failed to load TV guide:', error);
        document.getElementById('guideContainer').innerHTML = 
            `<div style="text-align: center; padding: 40px; color: var(--error);">${t('messages.failedToLoadGuide')}</div>`;
    }
}

function switchGuideView(view) {
    currentGuideView = view;
    
    // Update button states
    document.getElementById('dailyViewBtn').classList.toggle('active', view === 'daily');
    document.getElementById('weeklyViewBtn').classList.toggle('active', view === 'weekly');
    
    // Load the appropriate view
    loadTVGuide();
}

function displayTVGuide(guideData) {
    const container = document.getElementById('guideContainer');
    const guide = guideData.guide;
    
    if (!guide || Object.keys(guide).length === 0) {
        container.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-secondary);">${t('messages.noChannelsFound')}</div>`;
        return;
    }
    
    let guideHtml = '<div class="guide-grid">';
    
    // Sort channels by name
    const sortedChannels = Object.keys(guide).sort();
    
    for (const channelName of sortedChannels) {
        const channelGuide = guide[channelName];
        
        guideHtml += `
            <div class="guide-channel-card">
                <div class="guide-channel-header">
                    <div class="guide-channel-name">${channelName}</div>
                    <div class="guide-channel-type ${channelGuide.type}">${channelGuide.type}</div>
                    <div class="guide-channel-status ${channelGuide.status === 'running' ? 'running' : 'stopped'}">
                        ${channelGuide.status}
                    </div>
                </div>
                
                ${channelGuide.error ? `
                    <div class="guide-error">⚠️ ${channelGuide.error}</div>
                ` : ''}
                
                ${channelGuide.current_program ? `
                    <div class="guide-current-program">
                        <div class="guide-program-label">${t('guide.nowPlaying')}</div>
                        <div class="guide-program-title">${channelGuide.current_program.display_name}</div>
                        <div class="guide-program-time">${t('guide.started')}: ${channelGuide.current_program.time}</div>
                        <div class="guide-program-duration">${channelGuide.current_program.duration_estimate}</div>
                    </div>
                ` : `
                    <div class="guide-no-program">
                        <div class="guide-program-label">${t('guide.noSchedule')}</div>
                        <div class="guide-program-title">${t('guide.noProgram')}</div>
                    </div>
                `}
                
                ${channelGuide.next_program ? `
                    <div class="guide-next-program">
                        <div class="guide-program-label">${t('guide.upNext')}</div>
                        <div class="guide-program-title">${channelGuide.next_program.display_name}</div>
                        <div class="guide-program-time">${t('guide.starts')}: ${channelGuide.next_program.time}</div>
                        <div class="guide-program-duration">${channelGuide.next_program.duration_estimate}</div>
                    </div>
                ` : ''}
                
                ${channelGuide.schedule && channelGuide.schedule.length > 0 ? `
                    <div class="guide-schedule">
                        <div class="guide-schedule-label">${t('guide.todaySchedule')}</div>
                        <div class="guide-schedule-list">
                            ${channelGuide.schedule.slice(0, 5).map(program => `
                                <div class="guide-schedule-item ${program.is_current ? 'current' : ''}">
                                    <div class="guide-schedule-time">${program.time}</div>
                                    <div class="guide-schedule-title">${program.display_name}</div>
                                </div>
                            `).join('')}
                            ${channelGuide.schedule.length > 5 ? `
                                <div class="guide-schedule-more">... ${t('guide.morePrograms').replace('more programs', `${channelGuide.schedule.length - 5} ${t('guide.morePrograms')}`)}</div>
                            ` : ''}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    guideHtml += '</div>';
    container.innerHTML = guideHtml;
}

function displayWeeklyTVGuide(weeklyData) {
    const container = document.getElementById('guideContainer');
    const weeklyGuide = weeklyData.weekly_guide;
    const daysOrder = weeklyData.days_order;
    
    if (!weeklyGuide || Object.keys(weeklyGuide).length === 0) {
        container.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-secondary);">${t('messages.noChannelsFound')}</div>`;
        return;
    }
    
    let guideHtml = '<div class="weekly-guide-container">';
    
    // Sort channels by name
    const sortedChannels = Object.keys(weeklyGuide).sort();
    
    for (const channelName of sortedChannels) {
        const channelData = weeklyGuide[channelName];
        
        guideHtml += `
            <div class="weekly-channel-section">
                <div class="weekly-channel-header">
                    <div class="weekly-channel-info">
                        <div class="weekly-channel-name">${channelName}</div>
                        <div class="weekly-channel-meta">
                            <span class="guide-channel-type ${channelData.type}">${channelData.type}</span>
                            <span class="guide-channel-status ${channelData.status === 'running' ? 'running' : 'stopped'}">
                                ${channelData.status}
                            </span>
                        </div>
                    </div>
                </div>
                
                ${channelData.error ? `
                    <div class="guide-error">⚠️ ${channelData.error}</div>
                ` : `
                    <div class="weekly-schedule-grid">
                        ${daysOrder.map(day => {
                            const dayData = channelData.weekly_schedule[day];
                            if (!dayData) return '';
                            
                            return `
                                <div class="weekly-day-column ${dayData.is_today ? 'today' : ''}">
                                    <div class="weekly-day-header">
                                        <div class="weekly-day-name">${dayData.day_name}</div>
                                        <div class="weekly-day-count">${dayData.program_count} ${t('guide.programs')}</div>
                                        ${dayData.is_today ? `<div class="today-indicator">${t('guide.today_indicator')}</div>` : ''}
                                    </div>
                                    <div class="weekly-day-programs">
                                        ${dayData.programs.map(program => `
                                            <div class="weekly-program-item ${program.is_current ? 'current' : ''}">
                                                <div class="weekly-program-time">${program.time}</div>
                                                <div class="weekly-program-title">${program.display_name}</div>
                                                ${program.is_current ? `<div class="current-indicator">${t('guide.now_indicator')}</div>` : ''}
                                            </div>
                                        `).join('')}
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                `}
            </div>
        `;
    }
    
    guideHtml += '</div>';
    container.innerHTML = guideHtml;
}

async function refreshGuide() {
    document.getElementById('guideContainer').innerHTML = 
        `<div style="text-align: center; padding: 40px; color: var(--text-secondary);"><div class="loading"></div> ${t('guide.loadingText')}</div>`;
    await loadTVGuide();
    showToast(t('messages.guideRefreshed'), 'success');
}

// Initialize on load
init();
