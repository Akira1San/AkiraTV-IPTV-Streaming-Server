// VOD (Video on Demand) JavaScript
let vodData = {
    videos: [],
    collections: [],
    filteredVideos: [],
    currentView: 'grid',
    selectedVideo: null,
    currentlyPlaying: null,
    vodChannels: []
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
    document.getElementById('modalVideoRating').textContent = video.rating || 'NR';
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
async function playVideo(videoId) {
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
        const response = await fetch(`/api/channels/${selectedChannel}/play`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                video_path: video.path
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            vodData.currentlyPlaying = {
                video: video,
                channel: selectedChannel
            };
            updateNowPlaying();
            showToast(t('vod.videoStarted').replace('{video}', video.name), 'success');
        } else {
            showToast(t('vod.playbackFailed') + ': ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Failed to play video:', error);
        showToast(t('vod.playbackError'), 'error');
    }
}

// Stop current video
async function stopCurrentVideo() {
    const selectedChannel = document.getElementById('vodChannelSelect').value;
    
    if (!selectedChannel) {
        alert(t('vod.selectChannelFirst'));
        return;
    }
    
    try {
        const response = await fetch(`/api/channels/${selectedChannel}/stop`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            vodData.currentlyPlaying = null;
            updateNowPlaying();
            showToast(t('vod.videoStopped'), 'success');
        } else {
            showToast(t('vod.stopFailed') + ': ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Failed to stop video:', error);
        showToast(t('vod.stopError'), 'error');
    }
}

// Check what's currently playing
async function checkCurrentlyPlaying() {
    const selectedChannel = document.getElementById('vodChannelSelect').value;
    if (!selectedChannel) return;
    
    try {
        const response = await fetch(`/api/channels/${selectedChannel}`);
        const data = await response.json();
        
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
        // Silently fail - channel might not exist or be running
    }
}

// Update now playing display
function updateNowPlaying() {
    const nowPlayingDiv = document.getElementById('vodNowPlaying');
    const stopBtn = document.getElementById('stopCurrentBtn');
    
    if (vodData.currentlyPlaying) {
        document.getElementById('nowPlayingTitle').textContent = vodData.currentlyPlaying.video.name;
        document.getElementById('nowPlayingChannel').textContent = `Channel: ${vodData.currentlyPlaying.channel}`;
        nowPlayingDiv.style.display = 'block';
        stopBtn.disabled = false;
    } else {
        nowPlayingDiv.style.display = 'none';
        stopBtn.disabled = true;
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