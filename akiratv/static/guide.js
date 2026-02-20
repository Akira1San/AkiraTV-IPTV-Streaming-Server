// TV Guide JavaScript
let currentGuideView = 'daily'; // 'daily', 'weekly', or 'calendar'
let selectedGuideDate = null; // For calendar view

// Initialize the guide page
document.addEventListener('DOMContentLoaded', function() {
    initializeLanguage();
    checkServerStatus();
    loadTVGuide();
    
    // Set default date for calendar picker to today
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('guideDatePicker').value = today;
    
    // Update time every minute
    setInterval(updateGuideTime, 60000);
    updateGuideTime();
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

// Update guide time display
function updateGuideTime() {
    const now = new Date();
    const timeString = now.toLocaleString();
    const guideTimeElement = document.getElementById('guideTime');
    if (guideTimeElement) {
        guideTimeElement.textContent = `${t('guide.currentTime')}: ${timeString}`;
    }
}

// TV Guide Functions
async function loadTVGuide() {
    try {
        let endpoint = '/api/guide';
        if (currentGuideView === 'weekly') {
            endpoint = '/api/guide/weekly';
        } else if (currentGuideView === 'calendar' && selectedGuideDate) {
            endpoint = `/api/guide/date/${selectedGuideDate}`;
        }
        
        const response = await fetch(endpoint);
        const data = await response.json();
        
        if (currentGuideView === 'weekly') {
            displayWeeklyTVGuide(data);
        } else if (currentGuideView === 'calendar') {
            displayCalendarGuide(data);
        } else {
            displayTVGuide(data);
        }
            
    } catch (error) {
        console.error('Failed to load TV guide:', error);
        document.getElementById('guideContainer').innerHTML = 
            `<div style="text-align: center; padding: 40px; color: var(--error);">${t('messages.failedToLoadGuide')}</div>`;
    }
}

function switchGuideView(view) {
    // Update button states
    document.querySelectorAll('.guide-view-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(view + 'ViewBtn').classList.add('active');
    
    currentGuideView = view;
    
    // Show/hide date picker for calendar view
    const datePickerContainer = document.getElementById('datePickerContainer');
    if (view === 'calendar') {
        datePickerContainer.style.display = 'block';
        // Load guide for the selected date or today
        const datePicker = document.getElementById('guideDatePicker');
        if (datePicker.value) {
            loadGuideForDate(datePicker.value);
        }
    } else {
        datePickerContainer.style.display = 'none';
        loadTVGuide();
    }
}

async function loadGuideForDate(dateStr) {
    selectedGuideDate = dateStr;
    const container = document.getElementById('guideContainer');
    container.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-secondary);"><div class="loading"></div> ${t('guide.loadingText')}</div>`;
    
    try {
        const response = await fetch(`/api/guide/date/${dateStr}`);
        const data = await response.json();
        displayCalendarGuide(data);
    } catch (error) {
        console.error('Failed to load guide for date:', error);
        container.innerHTML = 
            `<div style="text-align: center; padding: 40px; color: var(--error);">${t('messages.failedToLoadGuide')}</div>`;
    }
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
                        ${channelGuide.status === 'running' ? '🟢' : '🔴'}
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
            <div class="weekly-channel-card">
                <div class="weekly-channel-header">
                    <div class="weekly-channel-info">
                        <div class="weekly-channel-name">${channelName}</div>
                        <div class="weekly-channel-meta">
                            <span class="guide-channel-type ${channelData.type}">${channelData.type}</span>
                            <span class="guide-channel-status ${channelData.status === 'running' ? 'running' : 'stopped'}">
                                ${channelData.status === 'running' ? '🟢' : '🔴'}
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
                            const daySchedule = channelData.weekly_schedule?.[day]?.programs || [];
                            return `
                                <div class="weekly-day-column">
                                    <div class="weekly-day-header">${day}</div>
                                    <div class="weekly-day-programs">
                                        ${daySchedule.length > 0 ? 
                                            daySchedule.slice(0, 8).map(program => `
                                                <div class="weekly-program-item ${program.is_current ? 'current' : ''}">
                                                    <div class="weekly-program-time">${program.time}</div>
                                                    <div class="weekly-program-title">${program.display_name}</div>
                                                </div>
                                            `).join('') + 
                                            (daySchedule.length > 8 ? `<div class="weekly-more-programs">+${daySchedule.length - 8} more</div>` : '')
                                        : `<div class="weekly-no-programs">${t('guide.noProgram')}</div>`}
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

function displayCalendarGuide(calendarData) {
    const container = document.getElementById('guideContainer');
    
    const guide = calendarData.guide;
    const selectedDate = calendarData.selected_date;
    
    // Format the date for display
    const dateObj = new Date(selectedDate);
    const formattedDate = dateObj.toLocaleDateString(undefined, { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
    
    if (!guide || Object.keys(guide).length === 0) {
        container.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-secondary);">
            <div style="font-size: 1.2em; margin-bottom: 10px;">📅 ${formattedDate}</div>
            ${t('messages.noChannelsFound')}
        </div>`;
        return;
    }
    
    let guideHtml = `
        <div style="text-align: center; margin-bottom: 20px; padding: 15px; background: var(--card-bg); border-radius: 8px;">
            <div style="font-size: 1.3em; color: var(--text-primary);">📅 ${formattedDate}</div>
            <div style="font-size: 0.9em; color: var(--text-secondary); margin-top: 5px;">${t('guide.calendarView') || 'Calendar View'}</div>
        </div>
        <div class="guide-grid">
    `;
    
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
                        ${channelGuide.status === 'running' ? '🟢' : '🔴'}
                        ${channelGuide.status}
                    </div>
                </div>
                
                ${channelGuide.error ? `
                    <div class="guide-error">⚠️ ${channelGuide.error}</div>
                ` : ''}
                
                ${channelGuide.schedule && channelGuide.schedule.length > 0 ? `
                    <div class="guide-schedule">
                        <div class="guide-schedule-label">${t('guide.scheduleFor') || 'Schedule'} (${channelGuide.schedule.length} ${t('guide.programs') || 'programs'})</div>
                        <div class="guide-schedule-list">
                            ${channelGuide.schedule.slice(0, 10).map(program => `
                                <div class="guide-schedule-item">
                                    <div class="guide-schedule-time">${program.time}</div>
                                    <div class="guide-schedule-title">${program.display_name}</div>
                                </div>
                            `).join('')}
                            ${channelGuide.schedule.length > 10 ? `
                                <div class="guide-schedule-more">... +${channelGuide.schedule.length - 10} ${t('guide.morePrograms') || 'more programs'}</div>
                            ` : ''}
                        </div>
                    </div>
                ` : `
                    <div class="guide-no-program">
                        <div class="guide-program-label">${t('guide.noSchedule')}</div>
                        <div class="guide-program-title">${t('guide.noProgram')}</div>
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
}