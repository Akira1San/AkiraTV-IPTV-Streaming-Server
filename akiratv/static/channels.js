// AkiraTV Channels JavaScript
// Channel management functionality for listing, filtering, and controlling channels

// Channel state
let allChannelsData = []; // Store all channels for search
let currentChannelFilter = 'all'; // Current filter: 'all', 'enabled', 'disabled'

// Main channels loading function
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
        
        // Get channel URLs for streaming
        const channelUrls = {};
        for (const channel of channels) {
            try {
                const urlData = await apiCall(`/api/channels/${channel.name}/url`);
                channelUrls[channel.name] = urlData.urls || {};
            } catch (error) {
                console.warn(`Failed to get URLs for channel ${channel.name}:`, error);
                channelUrls[channel.name] = {};
            }
        }
        
        // Display channels
        displayChannels(channels, channelUrls);
        
        // Update filter counts
        updateFilterCounts(channels);
        
        // Setup search functionality
        setupChannelSearch();
        
        // Refresh channel dropdown for playlist controls
        await loadChannelDropdown();
        
    } catch (error) {
        console.error('Failed to load channels:', error);
        document.getElementById('channelsGrid').innerHTML = 
            `<div style="text-align: center; padding: 40px; color: var(--error);">${t('messages.failedToLoadChannels')}</div>`;
    }
}

// Display channels in the grid
function displayChannels(channels, channelUrls) {
    const grid = document.getElementById('channelsGrid');
    
    if (channels.length === 0) {
        const searchTerm = document.getElementById('channelSearch').value.trim();
        if (searchTerm) {
            grid.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-secondary);">${t('channels.noResults')}</div>`;
        } else {
            grid.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-secondary);">${t('channels.noChannels')}</div>`;
        }
        return;
    }
    
    let channelsHtml = '';
    
    for (const ch of channels) {
        const urls = channelUrls[ch.name] || {};
        const channelUrl = getChannelUrl(ch);
        
        // Highlight search term in channel name
        const searchTerm = document.getElementById('channelSearch').value.trim();
        let displayName = ch.name;
        if (searchTerm) {
            const regex = new RegExp(`(${searchTerm})`, 'gi');
            displayName = ch.name.replace(regex, '<mark>$1</mark>');
        }
        
        channelsHtml += `
            <div class="channel-card ${ch.enabled ? 'enabled' : 'disabled'}">
                <div class="channel-header">
                    <div class="channel-info">
                        <div class="channel-name">${displayName}</div>
                        <div class="channel-type ${ch.type}">${ch.type}</div>
                        <label class="toggle-switch">
                            <input type="checkbox" ${ch.enabled ? 'checked' : ''} 
                                   onchange="toggleChannel('${ch.name}', this.checked)">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <div class="channel-status ${ch.status === 'running' ? 'running' : 'stopped'}">
                        ${ch.status}
                    </div>
                </div>
                
                ${ch.error ? `
                    <div class="channel-error">⚠️ ${ch.error}</div>
                ` : ''}
                
                ${ch.current_program ? `
                    <div class="channel-current-program">
                        <div class="program-label">${t('channels.nowPlaying')}</div>
                        <div class="program-title">${ch.current_program.display_name}</div>
                        <div class="program-time">${t('channels.started')}: ${ch.current_program.time}</div>
                    </div>
                ` : ''}
                
                <div class="channel-urls">
                    ${generateChannelUrls(ch.name, urls)}
                </div>
                
                <div class="channel-controls">
                    <div class="setting-row">
                        <button class="btn-small btn-secondary" onclick="reloadChannelSchedule('${ch.name}')">
                            🔄 ${t('channels.reloadSchedule')}
                        </button>
                        <button class="btn-small btn-danger" onclick="confirmDeleteChannel('${ch.name}')">
                            🗑️ ${t('channels.delete')}
                        </button>
                    </div>
                    
                    ${ch.status === 'running' ? `
                        <div class="setting-row">
                            <button class="btn-small btn-warning" onclick="restartChannel('${ch.name}')">
                                🔄 ${t('channels.restart')}
                            </button>
                            <button class="btn-small btn-danger" onclick="stopChannelWorker('${ch.name}')">
                                ⏹️ ${t('channels.stop')}
                            </button>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    grid.innerHTML = channelsHtml;
}

// Channel Search Functionality
function setupChannelSearch() {
    const searchInput = document.getElementById('channelSearch');
    const clearBtn = document.getElementById('searchClearBtn');
    const resultsInfo = document.getElementById('searchResultsInfo');
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.trim();
        
        // Show/hide clear button
        clearBtn.style.display = searchTerm ? 'block' : 'none';
        
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
    
    // Handle Enter key
    searchInput.addEventListener('keydown', function(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            const searchTerm = this.value.trim();
            if (searchTerm) {
                filterChannels(searchTerm);
            }
        }
    });
}

// Filter channels by search term and status
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
        
        // Show search results info
        resultsInfo.style.display = 'block';
        if (filteredChannels.length === 0) {
            resultsInfo.textContent = t('channels.noResults');
            resultsInfo.className = 'search-results-info no-results';
        } else {
            const resultText = filteredChannels.length === 1 
                ? t('channels.oneResult') 
                : t('channels.multipleResults').replace('{count}', filteredChannels.length);
            resultsInfo.textContent = resultText;
            resultsInfo.className = 'search-results-info';
        }
    } else {
        resultsInfo.style.display = 'none';
    }
    
    // Get channel URLs for filtered channels
    const channelUrls = {};
    for (const channel of filteredChannels) {
        // Use cached URLs if available, otherwise empty object
        channelUrls[channel.name] = {};
    }
    
    // Display filtered channels
    displayChannels(filteredChannels, channelUrls);
    
    // Update filter counts with original data
    updateFilterCounts(allChannelsData);
}

// Channel Filter Functions
function updateFilterCounts(channels) {
    const allCount = channels.length;
    const enabledCount = channels.filter(ch => ch.enabled).length;
    const disabledCount = allCount - enabledCount;
    
    document.getElementById('countAll').textContent = allCount;
    document.getElementById('countEnabled').textContent = enabledCount;
    document.getElementById('countDisabled').textContent = disabledCount;
}

function setChannelFilter(filter) {
    currentChannelFilter = filter;
    
    // Update button states
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`filter${filter.charAt(0).toUpperCase() + filter.slice(1)}`).classList.add('active');
    
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

// Generate channel URLs HTML
function generateChannelUrls(channelName, urls) {
    if (!urls || Object.keys(urls).length === 0) {
        // Fallback to a basic URL with your actual streaming server
        const port = window.location.port || '8080';
        const baseUrl = `${window.location.protocol}//${window.location.hostname}:${port}`;
        return `
            <div class="url-item">
                <div class="url-label">HLS Stream:</div>
                <div class="url-value">
                    <input type="text" readonly value="${baseUrl}/stream/${channelName}/playlist.m3u8" 
                           onclick="this.select(); copyToClipboard(this.value)">
                    <button class="copy-btn" onclick="copyToClipboard('${baseUrl}/stream/${channelName}/playlist.m3u8')">📋</button>
                </div>
            </div>
        `;
    }
    
    let urlsHtml = '';
    for (const [format, url] of Object.entries(urls)) {
        urlsHtml += `
            <div class="url-item">
                <div class="url-label">${format.toUpperCase()}:</div>
                <div class="url-value">
                    <input type="text" readonly value="${url}" onclick="this.select(); copyToClipboard(this.value)">
                    <button class="copy-btn" onclick="copyToClipboard('${url}')">📋</button>
                </div>
            </div>
        `;
    }
    return urlsHtml;
}

// Get Channel URL
function getChannelUrl(channel) {
    // This will be replaced by the proper URLs from the API
    const port = window.location.port || '8080';
    return `${window.location.protocol}//${window.location.hostname}:${port}/stream/${channel.name}/playlist.m3u8`;
}

// Load channel dropdown for playlist controls
async function loadChannelDropdown() {
    try {
        const data = await apiCall('/api/channels');
        const channelSelect = document.getElementById('channelSelect');
        
        // Clear existing options
        channelSelect.innerHTML = '<option value="">Select channel...</option>';
        
        // Add channels
        data.channels.forEach(channel => {
            const option = document.createElement('option');
            option.value = channel.name;
            option.textContent = `${channel.name} (${channel.type})`;
            channelSelect.appendChild(option);
        });
        
    } catch (error) {
        console.error('Failed to load channel dropdown:', error);
        document.getElementById('channelSelect').innerHTML = '<option value="">Failed to load channels</option>';
    }
}

// Stop selected channel
async function stopSelectedChannel() {
    const channelSelect = document.getElementById('channelSelect');
    const channel = channelSelect.value;
    
    if (!channel) {
        showToast('Please select a channel first', 'warning');
        return;
    }
    
    try {
        const result = await apiCall(`/api/channels/${channel}/stop`, 'POST');
        if (result.success) {
            showToast(`Channel ${channel} stopped`, 'success');
        } else {
            showToast(result.error || 'Failed to stop channel', 'error');
        }
    } catch (error) {
        showToast('Failed to stop channel', 'error');
    }
}

// Stop channel worker
async function stopChannelWorker(channel) {
    const confirmed = confirm(
        `Stop channel '${channel}' completely?\n\n` +
        'This will:\n' +
        '• Stop the streaming worker\n' +
        '• Clear any cached segments\n' +
        '• Disconnect all viewers\n\n' +
        'The channel can be restarted later.'
    );
    
    if (!confirmed) return;
    
    try {
        const result = await apiCall(`/api/channels/${channel}/stop`, 'POST');
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

// Restart channel
async function restartChannel(channel) {
    const confirmed = confirm(
        `Restart channel '${channel}'?\n\n` +
        'This will:\n' +
        '• Stop the current stream\n' +
        '• Clear cached segments\n' +
        '• Start fresh streaming\n' +
        '• Briefly disconnect viewers'
    );
    
    if (!confirmed) return;
    
    try {
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
            showToast(result.error || 'Failed to reload schedule', 'error');
        }
    } catch (error) {
        showToast('Failed to reload schedule', 'error');
    }
}

// Delete channel with confirmation
function confirmDeleteChannel(channelName) {
    const confirmed = confirm(
        `Are you sure you want to delete channel '${channelName}'?\n\n` +
        'This will:\n' +
        '• Remove the channel configuration\n' +
        '• Stop any running streams\n' +
        '• Delete associated files\n\n' +
        'This action cannot be undone.'
    );
    
    if (confirmed) {
        deleteChannel(channelName);
    }
}

// Delete channel
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
            showToast(`Channel ${channel} stopped`, 'success');
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
        showToast('Please enter a channel name', 'warning');
        return;
    }
    
    // Validate channel name
    if (!/^[a-zA-Z0-9_-]+$/.test(channelName)) {
        showToast('Channel name can only contain letters, numbers, hyphens, and underscores', 'error');
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

// Create channel
async function createChannel() {
    const channelName = document.getElementById('newChannelName').value.trim();
    const selectedType = document.querySelector('input[name="channelType"]:checked').value;
    
    try {
        const result = await apiCall('/api/channels', 'POST', {
            name: channelName,
            type: selectedType
        });
        
        if (result.success) {
            showToast(`Channel '${channelName}' created successfully`, 'success');
            
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
window.addEventListener('click', function(event) {
    const modal = document.getElementById('addChannelModal');
    if (event.target === modal) {
        hideAddChannelModal();
    }
});