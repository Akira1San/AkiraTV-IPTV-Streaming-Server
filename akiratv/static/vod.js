// VOD (Video on Demand) JavaScript
let vodData = {
    videos: [],
    collections: [],
    filteredVideos: [],
    currentView: 'grid',
    selectedVideo: null,
    currentlyPlaying: null,
    vodChannels: [],
    positionSaveInterval: null  // For periodic position saving
};

// Initialize the VOD page
document.addEventListener('DOMContentLoaded', function() {
    initializeLanguage();
    checkServerStatus();
    loadVodChannels();
    loadVideoLibrary();
    
    // Set up search functionality
    setupSearch();
    setupFilters();
    
    // Update status periodically
    setInterval(checkServerStatus, 30000);
    setInterval(checkCurrentlyPlaying, 10000);
});

// Language switching functionality
function switchLanguage(lang) {
    localStorage.setItem('language', lang);
    
    // Update button states
    document.querySelectorAll('.lang-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById('lang' + lang.charAt(0).toUpperCase() + lang.slice(1)).classList.add('active');
    
    // Apply translations
    applyTranslations(lang);
}

function initializeLanguage() {
    const savedLang = localStorage.getItem('language') || 'en';
    switchLanguage(savedLang);
}

function applyTranslations(lang) {
    const elements = document.querySelectorAll('[data-i18n]');
    elements.forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (translations[lang] && translations[lang][key]) {
            element.textContent = translations[lang][key];
        }
    });
    
    // Handle placeholder translations
    const placeholderElements = document.querySelectorAll('[data-i18n-placeholder]');
    placeholderElements.forEach(element => {
        const key = element.getAttribute('data-i18n-placeholder');
        if (translations[lang] && translations[lang][key]) {
            element.placeholder = translations[lang][key];
        }
    });
}

function t(key) {
    const lang = localStorage.getItem('language') || 'en';
    return (translations[lang] && translations[lang][key]) || key;
}

// Server status check
async function checkServerStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        const statusBadge = document.getElementById('statusBadge');
        const statusText = document.getElementById('statusText');
        
        if (data.status === 'running') {
            statusBadge.className = 'status-badge online';
            statusText.textContent = t('status.online');
        } else {
            statusBadge.className = 'status-badge offline';
            statusText.textContent = t('status.offline');
        }
    } catch (error) {
        const statusBadge = document.getElementById('statusBadge');
        const statusText = document.getElementById('statusText');
        statusBadge.className = 'status-badge offline';
        statusText.textContent = t('status.offline');
    }
}

// Load VOD channels
async function loadVodChannels() {
    try {
        const response = await fetch('/api/channels');
        const data = await response.json();
        
        vodData.vodChannels = data.channels.filter(ch => 
            ch.type === 'vod' || ch.type === 'dynamic'
        );
        
        const select = document.getElementById('vodChannelSelect');
        select.innerHTML = '';
        
        if (vodData.vodChannels.length === 0) {
            select.innerHTML = '<option value="">' + t('vod.noVodChannels') + '</option>';
        } else {
            select.innerHTML = '<option value="">' + t('vod.selectChannelOption') + '</option>';
            vodData.vodChannels.forEach(channel => {
                const option = document.createElement('option');
                option.value = channel.name;
                option.textContent = `${channel.name} (${channel.type})`;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load VOD channels:', error);
    }
}

// Load video library from collections
async function loadVideoLibrary() {
    try {
        const response = await fetch('/api/vod/library');
        const data = await response.json();
        
        vodData.videos = data.videos || [];
        vodData.collections = data.collections || [];
        vodData.filteredVideos = [...vodData.videos];
        
        updateStats();
        populateFilters();
        displayVideos();
        
    } catch (error) {
        console.error('Failed to load video library:', error);
        document.getElementById('vodLibrary').innerHTML = 
            '<div class="vod-error">Failed to load video library. Please check your collections.</div>';
    }
}

// Update statistics display
function updateStats() {
    const videoCount = vodData.videos.length;
    const collectionCount = vodData.collections.length;
    
    document.getElementById('videoCount').textContent = 
        `${videoCount} ${videoCount === 1 ? 'video' : 'videos'}`;
    document.getElementById('collectionCount').textContent = 
        `${collectionCount} ${collectionCount === 1 ? 'collection' : 'collections'}`;
}

// Populate filter dropdowns
function populateFilters() {
    // Collection filter
    const collectionFilter = document.getElementById('collectionFilter');
    collectionFilter.innerHTML = '<option value="">' + t('vod.allCollections') + '</option>';
    vodData.collections.forEach(collection => {
        const option = document.createElement('option');
        option.value = collection;
        option.textContent = collection;
        collectionFilter.appendChild(option);
    });
    
    // Genre filter
    const genres = [...new Set(vodData.videos.flatMap(video => video.genre || []))].sort();
    const genreFilter = document.getElementById('genreFilter');
    genreFilter.innerHTML = '<option value="">' + t('vod.allGenres') + '</option>';
    genres.forEach(genre => {
        if (genre) {
            const option = document.createElement('option');
            option.value = genre;
            option.textContent = genre;
            genreFilter.appendChild(option);
        }
    });
    
    // Year filter
    const years = [...new Set(vodData.videos.map(video => video.year))].sort((a, b) => b - a);
    const yearFilter = document.getElementById('yearFilter');
    yearFilter.innerHTML = '<option value="">' + t('vod.allYears') + '</option>';
    years.forEach(year => {
        if (year && year !== 2026) { // Filter out default year
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            yearFilter.appendChild(option);
        }
    });
}

// Setup search functionality
function setupSearch() {
    const searchInput = document.getElementById('vodSearch');
    const clearBtn = document.getElementById('vodSearchClear');
    
    searchInput.addEventListener('input', function() {
        const query = this.value.trim();
        if (query) {
            clearBtn.style.display = 'block';
        } else {
            clearBtn.style.display = 'none';
        }
        applyFilters();
    });
    
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            applyFilters();
        }
    });
}

// Setup filter functionality
function setupFilters() {
    ['collectionFilter', 'genreFilter', 'yearFilter', 'sortBy'].forEach(id => {
        document.getElementById(id).addEventListener('change', applyFilters);
    });
}

// Clear search
function clearVodSearch() {
    document.getElementById('vodSearch').value = '';
    document.getElementById('vodSearchClear').style.display = 'none';
    applyFilters();
}

// Apply all filters
function applyFilters() {
    const searchQuery = document.getElementById('vodSearch').value.toLowerCase().trim();
    const collectionFilter = document.getElementById('collectionFilter').value;
    const genreFilter = document.getElementById('genreFilter').value;
    const yearFilter = document.getElementById('yearFilter').value;
    const sortBy = document.getElementById('sortBy').value;
    
    // Filter videos
    vodData.filteredVideos = vodData.videos.filter(video => {
        // Search filter
        if (searchQuery && !video.name.toLowerCase().includes(searchQuery) && 
            !video.description.toLowerCase().includes(searchQuery)) {
            return false;
        }
        
        // Collection filter
        if (collectionFilter && video.collection !== collectionFilter) {
            return false;
        }
        
        // Genre filter
        if (genreFilter && (!video.genre || !video.genre.includes(genreFilter))) {
            return false;
        }
        
        // Year filter
        if (yearFilter && video.year != yearFilter) {
            return false;
        }
        
        return true;
    });
    
    // Sort videos
    vodData.filteredVideos.sort((a, b) => {
        switch (sortBy) {
            case 'year':
                return (b.year || 0) - (a.year || 0);
            case 'duration':
                return (b.duration || 0) - (a.duration || 0);
            case 'collection':
                return (a.collection || '').localeCompare(b.collection || '');
            case 'name':
            default:
                return a.name.localeCompare(b.name);
        }
    });
    
    displayVideos();
}

// Switch between grid and list view
function switchView(view) {
    vodData.currentView = view;
    
    // Update button states
    document.querySelectorAll('.vod-view-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(view + 'ViewBtn').classList.add('active');
    
    displayVideos();
}

// Display videos in the library
function displayVideos() {
    const container = document.getElementById('vodLibrary');
    
    if (vodData.filteredVideos.length === 0) {
        container.innerHTML = '<div class="vod-no-results">' + t('vod.noVideosFound') + '</div>';
        return;
    }
    
    if (vodData.currentView === 'grid') {
        displayGridView(container);
    } else {
        displayListView(container);
    }
}

// Display videos in grid view
function displayGridView(container) {
    let html = '<div class="vod-grid">';
    
    vodData.filteredVideos.forEach(video => {
        const posterUrl = video.cover ? `/${video.cover}` : '';
        const duration = formatDuration(video.duration);
        const genres = video.genre && video.genre.length > 0 ? video.genre.join(', ') : '';
        
        html += `
            <div class="vod-card" onclick="showVideoDetails('${video.id}')">
                <div class="vod-card-poster">
                    ${posterUrl ? 
                        `<img src="${posterUrl}" alt="${video.name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                         <div class="vod-card-no-poster" style="display: none;">
                             <div class="no-poster-icon">🎬</div>
                             <div class="no-poster-text">${video.name}</div>
                         </div>` :
                        `<div class="vod-card-no-poster">
                             <div class="no-poster-icon">🎬</div>
                             <div class="no-poster-text">${video.name}</div>
                         </div>`
                    }
                    <div class="vod-card-overlay">
                        <button class="vod-play-btn" onclick="event.stopPropagation(); playVideo('${video.id}')" title="${t('vod.playVideo')}">
                            ▶️
                        </button>
                    </div>
                    <div class="vod-card-duration">${duration}</div>
                </div>
                <div class="vod-card-info">
                    <div class="vod-card-title" title="${video.name}">${video.name}</div>
                    <div class="vod-card-meta">
                        <span class="vod-card-year">${video.year || 'N/A'}</span>
                        ${genres ? `<span class="vod-card-genres">${genres}</span>` : ''}
                    </div>
                    <div class="vod-card-collection">${video.collection}</div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// Display videos in list view
function displayListView(container) {
    let html = '<div class="vod-list">';
    
    vodData.filteredVideos.forEach(video => {
        const posterUrl = video.cover ? `/${video.cover}` : '';
        const duration = formatDuration(video.duration);
        const genres = video.genre && video.genre.length > 0 ? video.genre.join(', ') : 'No genres';
        
        html += `
            <div class="vod-list-item" onclick="showVideoDetails('${video.id}')">
                <div class="vod-list-poster">
                    ${posterUrl ? 
                        `<img src="${posterUrl}" alt="${video.name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                         <div class="vod-list-no-poster" style="display: none;">
                             <div class="no-poster-icon">🎬</div>
                         </div>` :
                        `<div class="vod-list-no-poster">
                             <div class="no-poster-icon">🎬</div>
                         </div>`
                    }
                </div>
                <div class="vod-list-info">
                    <div class="vod-list-title">${video.name}</div>
                    <div class="vod-list-description">${video.description || 'No description available'}</div>
                    <div class="vod-list-meta">
                        <span class="vod-meta-item">${video.year || 'N/A'}</span>
                        <span class="vod-meta-separator">•</span>
                        <span class="vod-meta-item">${duration}</span>
                        <span class="vod-meta-separator">•</span>
                        <span class="vod-meta-item">${genres}</span>
                        <span class="vod-meta-separator">•</span>
                        <span class="vod-meta-item">${video.collection}</span>
                    </div>
                </div>
                <div class="vod-list-actions">
                    <button class="btn btn-primary btn-small" onclick="event.stopPropagation(); playVideo('${video.id}')" title="${t('vod.playVideo')}">
                        ▶️ ${t('vod.play')}
                    </button>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// Format duration from seconds to readable format
function formatDuration(seconds) {
    if (!seconds) return 'N/A';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    } else {
        return `${minutes}m`;
    }
}

// Show video details modal
function showVideoDetails(videoId) {
    const video = vodData.videos.find(v => v.id === videoId);
    if (!video) return;
    
    vodData.selectedVideo = video;
    
    // Populate modal
    document.getElementById('modalVideoTitle').textContent = video.name;
    document.getElementById('modalVideoDescription').textContent = video.description || 'No description available';
    document.getElementById('modalVideoYear').textContent = video.year || 'N/A';
    document.getElementById('modalVideoDuration').textContent = formatDuration(video.duration);
    document.getElementById('modalVideoCollection').textContent = video.collection;
    
    // Handle poster
    const posterContainer = document.querySelector('.video-details-poster');
    const posterImg = document.getElementById('modalVideoPoster');
    
    // Remove any existing fallback
    const existingFallback = posterContainer.querySelector('.modal-no-poster');
    if (existingFallback) {
        existingFallback.remove();
    }
    
    if (video.cover) {
        posterImg.src = `/${video.cover}`;
        posterImg.style.display = 'block';
        posterImg.onerror = function() {
            this.style.display = 'none';
            posterContainer.insertAdjacentHTML('beforeend', `
                <div class="modal-no-poster">
                    <div class="no-poster-icon">🎬</div>
                    <div class="no-poster-text">${video.name}</div>
                </div>
            `);
        };
    } else {
        posterImg.style.display = 'none';
        posterContainer.insertAdjacentHTML('beforeend', `
            <div class="modal-no-poster">
                <div class="no-poster-icon">🎬</div>
                <div class="no-poster-text">${video.name}</div>
            </div>
        `);
    }
    
    // Handle genres
    const genreContainer = document.getElementById('modalVideoGenreContainer');
    const genreDiv = document.getElementById('modalVideoGenres');
    
    if (video.genre && video.genre.length > 0) {
        genreContainer.style.display = 'block';
        genreDiv.innerHTML = video.genre.map(genre => 
            `<span class="genre-tag">${genre}</span>`
        ).join('');
    } else {
        genreContainer.style.display = 'none';
    }
    
    // Show modal
    document.getElementById('videoDetailsModal').style.display = 'block';
}

// Hide video details modal
function hideVideoDetails() {
    document.getElementById('videoDetailsModal').style.display = 'none';
    vodData.selectedVideo = null;
}

// Play video from modal
function playVideoFromModal() {
    if (vodData.selectedVideo) {
        playVideo(vodData.selectedVideo.id);
        hideVideoDetails();
    }
}

// Play video
async function playVideo(videoId, forceStart = false) {
    const video = vodData.videos.find(v => v.id === videoId);
    const selectedChannel = document.getElementById('vodChannelSelect').value;
    
    if (!video) {
        alert(t('vod.videoNotFound'));
        return;
    }
    
    if (!selectedChannel) {
        alert(t('vod.selectChannelFirst'));
        return;
    }
    
    try {
        // If not forcing start, check for saved position
        let startPosition = 0;
        
        if (!forceStart) {
            // Try to get saved position
            try {
                const posResponse = await fetch(`/api/vod/position/${encodeURIComponent(video.path)}`);
                const posData = await posResponse.json();
                if (posData.success && posData.position !== null) {
                    startPosition = posData.position;
                }
            } catch (e) {
                console.log('No saved position found');
            }
        }
        
        // If there's a saved position and not forcing start, show resume dialog
        if (startPosition > 0 && !forceStart) {
            showResumeDialog(video, selectedChannel, startPosition);
            return;
        }
        
        // Play from beginning or specified position
        await doPlayVideo(video, selectedChannel, startPosition);
        
    } catch (error) {
        console.error('Failed to play video:', error);
        showToast(t('vod.playbackError') + ': ' + error.message, 'error');
    }
}

// Actually play the video with given position
async function doPlayVideo(video, channel, startPosition = 0) {
    try {
        // Use apiCall which properly handles error responses
        const result = await apiCall(`/api/channels/${channel}/play`, 'POST', {
            video_path: video.path,
            start_position: startPosition
        });
        
        if (result.success) {
            vodData.currentlyPlaying = {
                video: video,
                channel: channel,
                startPosition: startPosition
            };
            updateNowPlaying();
            showToast(t('vod.videoStarted').replace('{video}', video.name), 'success');
            
            // Start periodic position saving (every 30 seconds)
            startPositionSaving(video.path, channel);
            
            // Load embedded player with HLS stream
            loadEmbeddedPlayer(channel, video.path, startPosition);
        } else {
            showToast(t('vod.playbackFailed') + ': ' + (result.error || result.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Failed to play video:', error);
        showToast(t('vod.playbackError') + ': ' + error.message, 'error');
    }
}

// Show resume dialog
function showResumeDialog(video, channel, savedPosition) {
    const positionStr = formatTime(savedPosition);
    
    // Create modal
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'resumeDialog';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>${t('vod.resumePlayback') || 'Resume Playback'}</h3>
                <button class="modal-close" onclick="closeResumeDialog()">&times;</button>
            </div>
            <div class="modal-body">
                <p>${t('vod.resumeFrom') || 'Resume from'} <strong>${positionStr}</strong>?</p>
                <div class="resume-options">
                    <div class="form-group">
                        <label>${t('vod.startPosition') || 'Or enter custom start time'}:</label>
                        <input type="text" id="customStartPosition" class="form-control" placeholder="MM:SS or HH:MM:SS">
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closeResumeDialog(); playVideo('${video.id}', true)">
                    ${t('vod.startOver') || 'Start Over'}
                </button>
                <button class="btn btn-primary" onclick="handleResumeChoice('${video.id}', '${channel}', ${savedPosition})">
                    ${t('vod.resume') || 'Resume'}
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.style.display = 'block';
}

// Handle resume dialog choice
function handleResumeChoice(videoId, channel, savedPosition) {
    const customInput = document.getElementById('customStartPosition');
    let startPosition = savedPosition;
    
    if (customInput && customInput.value.trim()) {
        // Parse custom time input
        const parsed = parseTimeInput(customInput.value.trim());
        if (parsed !== null) {
            startPosition = parsed;
        }
    }
    
    closeResumeDialog();
    
    const video = vodData.videos.find(v => v.id === videoId);
    if (video) {
        doPlayVideo(video, channel, startPosition);
    }
}

// Close resume dialog
function closeResumeDialog() {
    const modal = document.getElementById('resumeDialog');
    if (modal) {
        modal.remove();
    }
}

// Parse time input (MM:SS or HH:MM:SS)
function parseTimeInput(input) {
    const parts = input.split(':');
    try {
        if (parts.length === 1) {
            // Just seconds
            return parseInt(parts[0], 10);
        } else if (parts.length === 2) {
            // MM:SS
            return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
        } else if (parts.length === 3) {
            // HH:MM:SS
            return parseInt(parts[0], 10) * 3600 + parseInt(parts[1], 10) * 60 + parseInt(parts[2], 10);
        }
    } catch (e) {
        console.error('Failed to parse time input:', e);
    }
    return null;
}

// Format time in seconds to HH:MM:SS
function formatTime(seconds) {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hrs > 0) {
        return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
}

// Start periodic position saving
function startPositionSaving(videoPath, channel) {
    // Clear any existing interval
    if (vodData.positionSaveInterval) {
        clearInterval(vodData.positionSaveInterval);
    }
    
    // Since we can't directly get the HLS player position from the server,
    // we'll save position periodically using the current playback info
    // For now, we'll just set up the interval - actual saving would need
    // integration with the player or a different approach
    
    // Note: Full implementation would require either:
    // 1. WebSocket updates from the server about current position
    // 2. Direct integration with HLS.js player on the client side
    // 3. A polling mechanism that tracks when the user starts/stops watching
    
    // For VOD resume to work, the key functionality is:
    // 1. ✓ Saving position when user stops/closes video (handled in stopCurrentVideo)
    // 2. ✓ Resuming from saved position on next play
    // 3. ✓ Manual position input
    
    console.log('Position saving initialized for:', videoPath);
}

// Save current video position
async function saveCurrentPosition() {
    if (vodData.currentlyPlaying && vodData.currentlyPlaying.video) {
        const video = vodData.currentlyPlaying.video;
        // For now, we'll save the start position that was used
        // Full implementation would track actual playback position
        const startPos = vodData.currentlyPlaying.startPosition || 0;
        
        try {
            await fetch(`/api/vod/position`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    video_path: video.path,
                    position: startPos
                })
            });
        } catch (e) {
            console.error('Failed to save position:', e);
        }
    }
}

// Stop current video
async function stopCurrentVideo() {
    const selectedChannel = document.getElementById('vodChannelSelect').value;
    
    if (!selectedChannel) {
        alert(t('vod.selectChannelFirst'));
        return;
    }
    
    // Save current position before stopping
    if (vodData.currentlyPlaying && vodData.currentlyPlaying.video) {
        try {
            await fetch(`/api/vod/position`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    video_path: vodData.currentlyPlaying.video.path,
                    position: vodData.currentlyPlaying.startPosition || 0
                })
            });
        } catch (e) {
            console.error('Failed to save position before stopping:', e);
        }
    }
    
    // Clear position save interval
    if (vodData.positionSaveInterval) {
        clearInterval(vodData.positionSaveInterval);
        vodData.positionSaveInterval = null;
    }
    
    try {
        // Use apiCall which properly handles error responses
        const result = await apiCall(`/api/channels/${selectedChannel}/stop`, 'POST');
        
        if (result.success) {
            vodData.currentlyPlaying = null;
            updateNowPlaying();
            showToast(t('vod.videoStopped'), 'success');
        } else {
            showToast(t('vod.stopFailed') + ': ' + (result.error || result.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Failed to stop video:', error);
        showToast(t('vod.stopError') + ': ' + error.message, 'error');
    }
}

// Check what's currently playing
async function checkCurrentlyPlaying() {
    const selectedChannel = document.getElementById('vodChannelSelect').value;
    if (!selectedChannel) return;
    
    try {
        const response = await fetch(`/api/channels/${selectedChannel}`);
        const data = await response.json();
        
        console.log('checkCurrentlyPlaying response:', data);
        
        if (data.current_video) {
            // Find the video in our library
            const video = vodData.videos.find(v => v.path === data.current_video);
            if (video) {
                vodData.currentlyPlaying = {
                    video: video,
                    channel: selectedChannel
                };
            }
        } else {
            vodData.currentlyPlaying = null;
        }
        
        updateNowPlaying();
    } catch (error) {
        console.error('checkCurrentlyPlaying error:', error);
        // Silently fail - channel might not exist or be running
    }
}

// Update now playing display
function updateNowPlaying() {
    const nowPlayingDiv = document.getElementById('vodNowPlaying');
    const stopBtn = document.getElementById('stopCurrentBtn');
    
    console.log('updateNowPlaying called with:', vodData.currentlyPlaying);
    
    if (vodData.currentlyPlaying) {
        document.getElementById('nowPlayingTitle').textContent = vodData.currentlyPlaying.video.name;
        document.getElementById('nowPlayingChannel').textContent = `Channel: ${vodData.currentlyPlaying.channel}`;
        nowPlayingDiv.style.display = 'block';
        stopBtn.disabled = false;
        console.log('Stop button enabled');
    } else {
        nowPlayingDiv.style.display = 'none';
        stopBtn.disabled = true;
        console.log('Stop button disabled');
    }
}

// Show toast notification
function showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    // Add to page
    document.body.appendChild(toast);
    
    // Show toast
    setTimeout(() => toast.classList.add('show'), 100);
    
    // Hide and remove toast
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => document.body.removeChild(toast), 300);
    }, 3000);
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('videoDetailsModal');
    if (event.target === modal) {
        hideVideoDetails();
    }
}

// ============================================
// EMBEDDED PLAYER FUNCTIONS (Phase 6)
// ============================================

let hlsPlayer = null;
let embeddedPlayer = {
    video: null,
    channel: null,
    videoPath: null,
    isPlaying: false,
    saveInterval: null
};

// Initialize embedded player
function initEmbeddedPlayer() {
    embeddedPlayer.video = document.getElementById('vodVideoPlayer');
    
    if (!embeddedPlayer.video) {
        console.error('Video element not found');
        return;
    }
    
    // Add event listeners
    embeddedPlayer.video.addEventListener('play', function() {
        embeddedPlayer.isPlaying = true;
        updatePlayPauseButton();
    });
    
    embeddedPlayer.video.addEventListener('pause', function() {
        embeddedPlayer.isPlaying = false;
        updatePlayPauseButton();
        // Save position when paused
        saveCurrentPosition();
    });
    
    embeddedPlayer.video.addEventListener('ended', function() {
        embeddedPlayer.isPlaying = false;
        updatePlayPauseButton();
        // Video ended - clear position
        clearVideoPosition();
    });
    
    embeddedPlayer.video.addEventListener('timeupdate', function() {
        updateProgressBar();
    });
    
    embeddedPlayer.video.addEventListener('loadedmetadata', function() {
        updateTimeDisplay();
    });
    
    // Progress bar seek
    const progressBar = document.getElementById('videoProgress');
    if (progressBar) {
        progressBar.addEventListener('input', function() {
            const video = embeddedPlayer.video;
            if (video && video.duration) {
                const seekTime = (this.value / 100) * video.duration;
                video.currentTime = seekTime;
            }
        });
    }
}

// Load HLS stream for channel
function loadEmbeddedPlayer(channelName, videoPath, startPosition = 0) {
    // Initialize video element if not done
    if (!embeddedPlayer.video) {
        initEmbeddedPlayer();
    }
    
    const video = embeddedPlayer.video;
    if (!video) return;
    
    embeddedPlayer.channel = channelName;
    embeddedPlayer.videoPath = videoPath;
    
    // Get HLS URL for the channel
    const config = getServerConfig();
    const hlsUrl = `http://${config.host}:${config.port}/hls/${channelName}/index.m3u8`;
    
    console.log('Loading HLS:', hlsUrl);
    
    // Destroy existing HLS player
    if (hlsPlayer) {
        hlsPlayer.destroy();
        hlsPlayer = null;
    }
    
    if (Hls.isSupported()) {
        hlsPlayer = new Hls();
        hlsPlayer.loadSource(hlsUrl);
        hlsPlayer.attachMedia(video);
        
        hlsPlayer.on(Hls.Events.MANIFEST_PARSED, function() {
            console.log('HLS manifest loaded');
            video.play().catch(e => console.error('Autoplay failed:', e));
            
            // Seek to start position if provided
            if (startPosition > 0) {
                video.currentTime = startPosition;
            }
            
            // Start periodic position saving
            startPositionSaving();
        });
        
        hlsPlayer.on(Hls.Events.ERROR, function(event, data) {
            console.error('HLS error:', data);
            if (data.fatal) {
                switch (data.type) {
                    case Hls.ErrorTypes.NETWORK_ERROR:
                        console.log('Fatal network error, trying to recover...');
                        hlsPlayer.startLoad();
                        break;
                    case Hls.ErrorTypes.MEDIA_ERROR:
                        console.log('Fatal media error, trying to recover...');
                        hlsPlayer.recoverMediaError();
                        break;
                    default:
                        console.log('Fatal error, destroying player');
                        hlsPlayer.destroy();
                        break;
                }
            }
        });
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        // Native HLS support (Safari)
        video.src = hlsUrl;
        video.addEventListener('loadedmetadata', function() {
            if (startPosition > 0) {
                video.currentTime = startPosition;
            }
            video.play().catch(e => console.error('Autoplay failed:', e));
            startPositionSaving();
        });
    } else {
        console.error('HLS is not supported in this browser');
        showToast('HLS playback not supported in this browser', 'error');
    }
    
    // Show embedded player
    showEmbeddedPlayer();
}

// Show embedded player UI
function showEmbeddedPlayer() {
    const playerDiv = document.getElementById('vodEmbeddedPlayer');
    if (playerDiv) {
        playerDiv.style.display = 'block';
    }
}

// Hide embedded player UI
function hideEmbeddedPlayer() {
    const playerDiv = document.getElementById('vodEmbeddedPlayer');
    if (playerDiv) {
        playerDiv.style.display = 'none';
    }
}

// Stop embedded player
function stopEmbeddedPlayer() {
    // Save position before stopping
    saveCurrentPosition();
    
    // Stop position saving
    stopPositionSaving();
    
    // Stop video
    if (embeddedPlayer.video) {
        embeddedPlayer.video.pause();
    }
    
    // Destroy HLS player
    if (hlsPlayer) {
        hlsPlayer.destroy();
        hlsPlayer = null;
    }
    
    // Stop channel on server
    if (embeddedPlayer.channel) {
        apiCall(`/api/channels/${embeddedPlayer.channel}/stop`, 'POST').catch(e => console.error('Failed to stop channel:', e));
    }
    
    // Reset state
    embeddedPlayer.channel = null;
    embeddedPlayer.videoPath = null;
    embeddedPlayer.isPlaying = false;
    
    // Hide player
    hideEmbeddedPlayer();
    
    showToast('Playback stopped', 'info');
}

// Toggle play/pause
function togglePlayPause() {
    const video = embeddedPlayer.video;
    if (!video) return;
    
    if (video.paused) {
        video.play();
    } else {
        video.pause();
    }
}

// Update play/pause button icon
function updatePlayPauseButton() {
    const btn = document.getElementById('playPauseIcon');
    if (btn) {
        btn.textContent = embeddedPlayer.isPlaying ? '⏸️' : '▶️';
    }
}

// Seek relative (forward/backward seconds)
function seekRelative(seconds) {
    const video = embeddedPlayer.video;
    if (!video) return;
    
    video.currentTime = Math.max(0, Math.min(video.duration, video.currentTime + seconds));
}

// Update progress bar
function updateProgressBar() {
    const video = embeddedPlayer.video;
    const progressBar = document.getElementById('videoProgress');
    
    if (video && progressBar) {
        const percentage = (video.currentTime / video.duration) * 100;
        progressBar.value = percentage || 0;
    }
}

// Update time display
function updateTimeDisplay() {
    const video = embeddedPlayer.video;
    const currentTimeEl = document.getElementById('currentTime');
    const totalTimeEl = document.getElementById('totalTime');
    
    if (video) {
        if (currentTimeEl) currentTimeEl.textContent = formatTime(video.currentTime);
        if (totalTimeEl) totalTimeEl.textContent = formatTime(video.duration);
    }
}

// Format time in MM:SS or HH:MM:SS
function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hrs > 0) {
        return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Start periodic position saving
function startPositionSaving() {
    stopPositionSaving(); // Clear any existing interval
    
    embeddedPlayer.saveInterval = setInterval(function() {
        if (embeddedPlayer.isPlaying && embeddedPlayer.video && embeddedPlayer.videoPath) {
            const position = embeddedPlayer.video.currentTime;
            savePositionToServer(embeddedPlayer.videoPath, position);
        }
    }, 10000); // Save every 10 seconds
}

// Stop periodic position saving
function stopPositionSaving() {
    if (embeddedPlayer.saveInterval) {
        clearInterval(embeddedPlayer.saveInterval);
        embeddedPlayer.saveInterval = null;
    }
}

// Save current position to server
function saveCurrentPosition() {
    if (embeddedPlayer.video && embeddedPlayer.videoPath) {
        const position = embeddedPlayer.video.currentTime;
        savePositionToServer(embeddedPlayer.videoPath, position);
    }
}

// Save position via API
async function savePositionToServer(videoPath, position) {
    try {
        await fetch(`/api/vod/position?video_path=${encodeURIComponent(videoPath)}&position=${position}`, {
            method: 'POST'
        });
    } catch (e) {
        console.error('Failed to save position:', e);
    }
}

// Clear video position (when video ends)
async function clearVideoPosition() {
    if (embeddedPlayer.videoPath) {
        try {
            await fetch(`/api/vod/position/${encodeURIComponent(embeddedPlayer.videoPath)}`, {
                method: 'DELETE'
            });
        } catch (e) {
            console.error('Failed to clear position:', e);
        }
    }
}

// Get server configuration
function getServerConfig() {
    // Default to localhost:8081
    return {
        host: 'localhost',
        port: 8081
    };
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initEmbeddedPlayer();
});