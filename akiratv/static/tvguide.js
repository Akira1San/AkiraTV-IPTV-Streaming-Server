// AkiraTV TV Guide JavaScript
// TV Guide functionality for daily and weekly program views

// TV Guide state
let currentGuideView = 'daily'; // 'daily' or 'weekly'

// Main TV Guide loading function
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

// Switch between daily and weekly guide views
function switchGuideView(view) {
    currentGuideView = view;
    
    // Update button states
    document.getElementById('dailyViewBtn').classList.toggle('active', view === 'daily');
    document.getElementById('weeklyViewBtn').classList.toggle('active', view === 'weekly');
    
    // Load the appropriate view
    loadTVGuide();
}

// Display daily TV guide
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

// Display weekly TV guide
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

// Refresh TV guide
async function refreshGuide() {
    document.getElementById('guideContainer').innerHTML = 
        `<div style="text-align: center; padding: 40px; color: var(--text-secondary);"><div class="loading"></div> ${t('guide.loadingText')}</div>`;
    await loadTVGuide();
    showToast(t('messages.guideRefreshed'), 'success');
}