// AkiraTV Collection & Scheduler Wizard
// Separate JavaScript file for wizard functionality

// Wizard State Management
let currentWizard = null; // 'collection' or 'scheduler'
let wizardStep = 0;
let wizardData = {};

// ========================================
// COLLECTION WIZARD
// ========================================

function showCollectionWizard() {
    currentWizard = 'collection';
    wizardStep = 0;
    wizardData = {
        folders: [],
        selectedFolder: null,
        videoFiles: [],
        collectionName: '',
        channelName: '',
        metadata: {}
    };
    
    document.getElementById('collectionWizardModal').style.display = 'block';
    loadCollectionWizardStep();
}

function hideCollectionWizard() {
    document.getElementById('collectionWizardModal').style.display = 'none';
    currentWizard = null;
    wizardStep = 0;
    wizardData = {};
}

function loadCollectionWizardStep() {
    const body = document.getElementById('collectionWizardBody');
    const nextBtn = document.getElementById('collectionWizardNext');
    
    switch(wizardStep) {
        case 0:
            body.innerHTML = getCollectionStep1HTML();
            nextBtn.textContent = t('wizard.next');
            nextBtn.disabled = true;
            // Setup folder path input listeners
            setTimeout(setupFolderPathInput, 100);
            break;
        case 1:
            body.innerHTML = getCollectionStep2HTML();
            nextBtn.textContent = t('wizard.next');
            nextBtn.disabled = true;
            // Auto-generate channel name from collection name
            setTimeout(setupCollectionStep2, 100);
            break;
        case 2:
            body.innerHTML = getCollectionStep3HTML();
            nextBtn.textContent = t('wizard.finish');
            nextBtn.disabled = false;
            break;
    }
}

function setupCollectionStep2() {
    const collectionInput = document.getElementById('collectionName');
    const channelInput = document.getElementById('channelName');
    
    if (collectionInput && channelInput) {
        // Auto-generate channel name from collection name
        collectionInput.addEventListener('input', function() {
            const collectionName = this.value.trim();
            if (collectionName && !channelInput.value.trim()) {
                // Convert to valid channel name
                const channelName = collectionName
                    .toLowerCase()
                    .replace(/[^a-z0-9]/g, '_')
                    .replace(/_+/g, '_')
                    .replace(/^_|_$/g, '');
                channelInput.value = channelName;
            }
            validateStep2Inputs();
        });
        
        channelInput.addEventListener('input', validateStep2Inputs);
        document.getElementById('channelType').addEventListener('change', validateStep2Inputs);
    }
}

function validateStep2Inputs() {
    const collectionName = document.getElementById('collectionName').value.trim();
    const channelName = document.getElementById('channelName').value.trim();
    const nextBtn = document.getElementById('collectionWizardNext');
    
    const isValid = collectionName && channelName && channelName.match(/^[a-zA-Z0-9_-]+$/);
    nextBtn.disabled = !isValid;
}

function getCollectionStep1HTML() {
    return `
        <div class="wizard-steps">
            <div class="wizard-step active">
                <div class="wizard-step-number">1</div>
                <span>Select Folder</span>
            </div>
            <div class="wizard-step">
                <div class="wizard-step-number">2</div>
                <span>Configure</span>
            </div>
            <div class="wizard-step">
                <div class="wizard-step-number">3</div>
                <span>Review</span>
            </div>
        </div>
        
        <div class="wizard-content">
            <h4>📁 Select Video Folder</h4>
            <p>Choose a folder containing your video files. The wizard will scan for supported video formats.</p>
            
            <div class="folder-input-section">
                <div class="input-group">
                    <input type="text" id="folderPath" class="wizard-input" placeholder="Enter folder path (e.g., C:\\Videos\\Movies)" />
                    <button class="btn btn-secondary" onclick="browseFolderForCollection()">📁 Browse</button>
                </div>
                <div class="folder-help">
                    <small>Supported formats: MP4, MKV, AVI, MOV, M4V, WMV, FLV</small>
                </div>
            </div>
            
            <div id="folderPreview" class="folder-preview" style="display: none;">
                <h5>📊 Folder Preview</h5>
                <div id="folderStats" class="folder-stats"></div>
            </div>
        </div>
    `;
}

function getCollectionStep2HTML() {
    return `
        <div class="wizard-steps">
            <div class="wizard-step completed">
                <div class="wizard-step-number">✓</div>
                <span>Select Folder</span>
            </div>
            <div class="wizard-step active">
                <div class="wizard-step-number">2</div>
                <span>Configure</span>
            </div>
            <div class="wizard-step">
                <div class="wizard-step-number">3</div>
                <span>Review</span>
            </div>
        </div>
        
        <div class="wizard-content">
            <h4>⚙️ Configure Collection</h4>
            <p>Set up your collection name and channel settings.</p>
            
            <div class="config-section">
                <div class="input-group">
                    <label>Collection Name:</label>
                    <input type="text" id="collectionName" class="wizard-input" placeholder="e.g., Action Movies" />
                </div>
                
                <div class="input-group">
                    <label>Channel Name:</label>
                    <input type="text" id="channelName" class="wizard-input" placeholder="e.g., action_movies" />
                    <small>Use only letters, numbers, hyphens (-), and underscores (_)</small>
                </div>
                
                <div class="input-group">
                    <label>Channel Type:</label>
                    <select id="channelType" class="wizard-select">
                        <option value="linear">Linear (Scheduled Programming)</option>
                        <option value="vod">VOD (On-Demand)</option>
                        <option value="dynamic">Dynamic (Standby + VOD)</option>
                    </select>
                </div>
            </div>
        </div>
    `;
}

function getCollectionStep3HTML() {
    return `
        <div class="wizard-steps">
            <div class="wizard-step completed">
                <div class="wizard-step-number">✓</div>
                <span>Select Folder</span>
            </div>
            <div class="wizard-step completed">
                <div class="wizard-step-number">✓</div>
                <span>Configure</span>
            </div>
            <div class="wizard-step active">
                <div class="wizard-step-number">3</div>
                <span>Review</span>
            </div>
        </div>
        
        <div class="wizard-content">
            <h4>📋 Review & Create</h4>
            <p>Review your collection settings and create the collection.</p>
            
            <div class="review-section">
                <div class="review-item">
                    <strong>Folder:</strong> ${wizardData.selectedFolder || 'Not selected'}
                </div>
                <div class="review-item">
                    <strong>Video Files:</strong> ${wizardData.videoFiles.length} files found
                </div>
                <div class="review-item">
                    <strong>Collection Name:</strong> ${wizardData.collectionName || 'Not set'}
                </div>
                <div class="review-item">
                    <strong>Channel Name:</strong> ${wizardData.channelName || 'Not set'}
                </div>
                <div class="review-item">
                    <strong>Channel Type:</strong> ${wizardData.channelType || 'Linear'}
                </div>
            </div>
            
            <div class="wizard-actions-preview">
                <h5>📝 What will be created:</h5>
                <ul>
                    <li>Collection file: <code>user/collections/collections_${wizardData.channelName}.json</code></li>
                    <li>Channel configuration in <code>config.json</code></li>
                    <li>Video metadata and thumbnails</li>
                </ul>
            </div>
        </div>
    `;
}

function collectionWizardNext() {
    if (wizardStep < 2) {
        // Validate current step
        if (validateCollectionStep()) {
            wizardStep++;
            loadCollectionWizardStep();
        }
    } else {
        // Final step - create collection
        createCollection();
    }
}

function validateCollectionStep() {
    switch(wizardStep) {
        case 0:
            const folderPath = document.getElementById('folderPath').value.trim();
            if (!folderPath) {
                showToast('Please select a folder path', 'error');
                return false;
            }
            wizardData.selectedFolder = folderPath;
            
            // Simulate folder scanning (in real implementation, this would call an API)
            scanFolderForVideos(folderPath);
            return true;
            
        case 1:
            const collectionName = document.getElementById('collectionName').value.trim();
            const channelName = document.getElementById('channelName').value.trim();
            const channelType = document.getElementById('channelType').value;
            
            if (!collectionName) {
                showToast('Please enter a collection name', 'error');
                return false;
            }
            if (!channelName) {
                showToast('Please enter a channel name', 'error');
                return false;
            }
            if (!channelName.match(/^[a-zA-Z0-9_-]+$/)) {
                showToast('Channel name can only contain letters, numbers, hyphens, and underscores', 'error');
                return false;
            }
            
            wizardData.collectionName = collectionName;
            wizardData.channelName = channelName;
            wizardData.channelType = channelType;
            return true;
    }
    return false;
}

async function scanFolderForVideos(folderPath) {
    try {
        // Call API to scan folder for videos
        const result = await apiCall('/api/wizard/scan-folder', 'POST', {
            folder_path: folderPath
        });
        
        if (result.success) {
            wizardData.videoFiles = result.data.videos || [];
            
            // Show folder preview
            const preview = document.getElementById('folderPreview');
            const stats = document.getElementById('folderStats');
            
            if (wizardData.videoFiles.length > 0) {
                stats.innerHTML = `
                    <div class="folder-stat">
                        <strong>📁 Folder:</strong> ${folderPath}
                    </div>
                    <div class="folder-stat">
                        <strong>🎬 Videos Found:</strong> ${wizardData.videoFiles.length} files
                    </div>
                    <div class="folder-stat">
                        <strong>📊 Formats:</strong> ${getUniqueFormats(wizardData.videoFiles).join(', ')}
                    </div>
                    <div class="folder-stat">
                        <strong>💾 Total Size:</strong> ${formatFileSize(result.data.total_size || 0)}
                    </div>
                `;
                preview.style.display = 'block';
                
                // Enable next button
                document.getElementById('collectionWizardNext').disabled = false;
            } else {
                stats.innerHTML = `
                    <div class="folder-stat error">
                        <strong>⚠️ No video files found in this folder</strong>
                    </div>
                    <div class="folder-help">
                        <small>Supported formats: MP4, MKV, AVI, MOV, M4V, WMV, FLV</small>
                    </div>
                `;
                preview.style.display = 'block';
                document.getElementById('collectionWizardNext').disabled = true;
            }
        } else {
            throw new Error(result.error || 'Failed to scan folder');
        }
    } catch (error) {
        // Fallback: simulate folder scanning
        console.warn('API scan failed, using simulation:', error);
        
        // Simulate finding some videos
        wizardData.videoFiles = [
            { name: 'sample_video_1.mp4', size: 1024000000, format: 'mp4' },
            { name: 'sample_video_2.mkv', size: 2048000000, format: 'mkv' },
            { name: 'sample_video_3.avi', size: 1536000000, format: 'avi' }
        ];
        
        const preview = document.getElementById('folderPreview');
        const stats = document.getElementById('folderStats');
        
        stats.innerHTML = `
            <div class="folder-stat">
                <strong>📁 Folder:</strong> ${folderPath}
            </div>
            <div class="folder-stat">
                <strong>🎬 Videos Found:</strong> ${wizardData.videoFiles.length} files (simulated)
            </div>
            <div class="folder-stat">
                <strong>📊 Formats:</strong> MP4, MKV, AVI
            </div>
            <div class="folder-stat">
                <strong>💾 Total Size:</strong> ~4.6 GB (estimated)
            </div>
        `;
        preview.style.display = 'block';
        document.getElementById('collectionWizardNext').disabled = false;
    }
}

function getUniqueFormats(videos) {
    const formats = videos.map(v => v.format || v.name.split('.').pop().toUpperCase());
    return [...new Set(formats)];
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

async function createCollection() {
    try {
        showToast('Creating collection...', 'info');
        
        // Create collection file structure
        const collectionData = {
            name: wizardData.collectionName,
            channel: wizardData.channelName,
            type: wizardData.channelType,
            folder: wizardData.selectedFolder,
            videos: wizardData.videoFiles,
            created: new Date().toISOString(),
            metadata: {
                total_videos: wizardData.videoFiles.length,
                total_duration: "Unknown", // Could be calculated
                formats: ["mp4", "mkv", "avi"] // Could be detected
            }
        };
        
        // Call API to create collection
        const result = await apiCall('/api/wizard/collection/create', 'POST', {
            collection_name: wizardData.collectionName,
            channel_name: wizardData.channelName,
            channel_type: wizardData.channelType,
            folder_path: wizardData.selectedFolder,
            collection_data: collectionData
        });
        
        if (result.success) {
            showToast(
                `✅ Collection Created Successfully!\n\n` +
                `Collection: ${wizardData.collectionName}\n` +
                `Channel: ${wizardData.channelName}\n` +
                `Type: ${wizardData.channelType}\n` +
                `Videos: ${wizardData.videoFiles.length} files\n\n` +
                `The channel is now available in your channels list.`,
                'success'
            );
            hideCollectionWizard();
            
            // Refresh channels to show new collection
            await loadChannels();
        } else {
            throw new Error(result.error || 'Unknown error');
        }
        
    } catch (error) {
        showToast('Failed to create collection: ' + error.message, 'error');
    }
}

// ========================================
// SCHEDULER WIZARD
// ========================================

function showSchedulerWizard() {
    currentWizard = 'scheduler';
    wizardStep = 0;
    wizardData = {
        selectedChannel: null,
        scheduleType: 'weekly',
        programs: [],
        timeSlots: {}
    };
    
    document.getElementById('schedulerWizardModal').style.display = 'block';
    loadSchedulerWizardStep();
}

function hideSchedulerWizard() {
    document.getElementById('schedulerWizardModal').style.display = 'none';
    currentWizard = null;
    wizardStep = 0;
    wizardData = {};
}

function loadSchedulerWizardStep() {
    const body = document.getElementById('schedulerWizardBody');
    const nextBtn = document.getElementById('schedulerWizardNext');
    
    switch(wizardStep) {
        case 0:
            body.innerHTML = getSchedulerStep1HTML();
            nextBtn.textContent = t('wizard.next');
            nextBtn.disabled = true;
            // Load channels for selection
            setTimeout(loadChannelsForScheduler, 100);
            break;
        case 1:
            body.innerHTML = getSchedulerStep2HTML();
            nextBtn.textContent = t('wizard.next');
            nextBtn.disabled = true;
            // Initialize schedule builder
            setTimeout(initializeScheduleBuilder, 100);
            break;
        case 2:
            body.innerHTML = getSchedulerStep3HTML();
            nextBtn.textContent = t('wizard.finish');
            nextBtn.disabled = false;
            break;
    }
}

async function loadChannelsForScheduler() {
    try {
        const channelsData = await apiCall('/api/channels');
        const channels = channelsData.channels || [];
        
        const select = document.getElementById('scheduleChannel');
        select.innerHTML = '<option value="">Select a channel...</option>';
        
        // Only show enabled channels
        const enabledChannels = channels.filter(ch => ch.enabled);
        
        if (enabledChannels.length === 0) {
            select.innerHTML = '<option value="">No enabled channels found</option>';
            return;
        }
        
        enabledChannels.forEach(channel => {
            const option = document.createElement('option');
            option.value = channel.name;
            option.textContent = `${channel.name} (${channel.type})`;
            select.appendChild(option);
        });
        
        // Setup change listeners
        select.addEventListener('change', function() {
            const selectedChannel = this.value;
            if (selectedChannel) {
                showChannelInfo(selectedChannel, channels);
                document.getElementById('schedulerWizardNext').disabled = false;
            } else {
                document.getElementById('channelInfo').style.display = 'none';
                document.getElementById('schedulerWizardNext').disabled = true;
            }
        });
        
    } catch (error) {
        console.error('Failed to load channels:', error);
        const select = document.getElementById('scheduleChannel');
        select.innerHTML = '<option value="">Error loading channels</option>';
    }
}

function showChannelInfo(channelName, channels) {
    const channel = channels.find(ch => ch.name === channelName);
    if (!channel) return;
    
    const infoDiv = document.getElementById('channelInfo');
    const detailsDiv = document.getElementById('channelDetails');
    
    detailsDiv.innerHTML = `
        <div class="channel-info-item">
            <strong>Channel Name:</strong> ${channel.name}
        </div>
        <div class="channel-info-item">
            <strong>Type:</strong> ${channel.type.toUpperCase()}
        </div>
        <div class="channel-info-item">
            <strong>Status:</strong> ${channel.status}
        </div>
        <div class="channel-info-item">
            <strong>Enabled:</strong> ${channel.enabled ? 'Yes' : 'No'}
        </div>
    `;
    
    infoDiv.style.display = 'block';
}

function getSchedulerStep1HTML() {
    return `
        <div class="wizard-steps">
            <div class="wizard-step active">
                <div class="wizard-step-number">1</div>
                <span>Select Channel</span>
            </div>
            <div class="wizard-step">
                <div class="wizard-step-number">2</div>
                <span>Build Schedule</span>
            </div>
            <div class="wizard-step">
                <div class="wizard-step-number">3</div>
                <span>Review</span>
            </div>
        </div>
        
        <div class="wizard-content">
            <h4>📺 Select Channel</h4>
            <p>Choose which channel you want to create a schedule for.</p>
            
            <div class="channel-selection">
                <div class="input-group">
                    <label>Channel:</label>
                    <select id="scheduleChannel" class="wizard-select">
                        <option value="">Loading channels...</option>
                    </select>
                </div>
                
                <div class="input-group">
                    <label>Schedule Type:</label>
                    <select id="scheduleType" class="wizard-select">
                        <option value="weekly">Weekly Schedule (7 days)</option>
                        <option value="daily">Daily Schedule (24 hours)</option>
                    </select>
                </div>
            </div>
            
            <div id="channelInfo" class="channel-info" style="display: none;">
                <h5>📊 Channel Information</h5>
                <div id="channelDetails"></div>
            </div>
        </div>
    `;
}

function getSchedulerStep2HTML() {
    return `
        <div class="wizard-steps">
            <div class="wizard-step completed">
                <div class="wizard-step-number">✓</div>
                <span>Select Channel</span>
            </div>
            <div class="wizard-step active">
                <div class="wizard-step-number">2</div>
                <span>Build Schedule</span>
            </div>
            <div class="wizard-step">
                <div class="wizard-step-number">3</div>
                <span>Review</span>
            </div>
        </div>
        
        <div class="wizard-content">
            <h4>📅 Build Schedule</h4>
            <p>Create your programming schedule by adding time slots and videos.</p>
            
            <div class="schedule-builder">
                <div class="schedule-controls">
                    <button class="btn btn-secondary" onclick="addTimeSlot()">+ Add Time Slot</button>
                    <button class="btn btn-secondary" onclick="autoFillSchedule()">🤖 Auto Fill</button>
                </div>
                
                <div id="scheduleGrid" class="schedule-grid">
                    <div class="schedule-placeholder">
                        <p>Click "Add Time Slot" to start building your schedule</p>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function getSchedulerStep3HTML() {
    return `
        <div class="wizard-steps">
            <div class="wizard-step completed">
                <div class="wizard-step-number">✓</div>
                <span>Select Channel</span>
            </div>
            <div class="wizard-step completed">
                <div class="wizard-step-number">✓</div>
                <span>Build Schedule</span>
            </div>
            <div class="wizard-step active">
                <div class="wizard-step-number">3</div>
                <span>Review</span>
            </div>
        </div>
        
        <div class="wizard-content">
            <h4>📋 Review Schedule</h4>
            <p>Review your schedule and create the programming file.</p>
            
            <div class="schedule-review">
                <div class="review-item">
                    <strong>Channel:</strong> ${wizardData.selectedChannel || 'Not selected'}
                </div>
                <div class="review-item">
                    <strong>Schedule Type:</strong> ${wizardData.scheduleType || 'Weekly'}
                </div>
                <div class="review-item">
                    <strong>Time Slots:</strong> ${Object.keys(wizardData.timeSlots).length} slots created
                </div>
            </div>
            
            <div class="wizard-actions-preview">
                <h5>📝 What will be created:</h5>
                <ul>
                    <li>Schedule file: <code>user/schedules/schedule_${wizardData.selectedChannel}.json</code></li>
                    <li>Weekly programming with ${Object.keys(wizardData.timeSlots).length} time slots</li>
                    <li>Channel will be ready for linear streaming</li>
                </ul>
            </div>
        </div>
    `;
}

function schedulerWizardNext() {
    if (wizardStep < 2) {
        // Validate current step
        if (validateSchedulerStep()) {
            wizardStep++;
            loadSchedulerWizardStep();
        }
    } else {
        // Final step - create schedule
        createSchedule();
    }
}

function validateSchedulerStep() {
    switch(wizardStep) {
        case 0:
            const selectedChannel = document.getElementById('scheduleChannel').value;
            const scheduleType = document.getElementById('scheduleType').value;
            
            if (!selectedChannel) {
                showToast('Please select a channel', 'error');
                return false;
            }
            
            wizardData.selectedChannel = selectedChannel;
            wizardData.scheduleType = scheduleType;
            return true;
            
        case 1:
            const totalSlots = Object.values(wizardData.timeSlots).reduce((total, daySlots) => total + daySlots.length, 0);
            const filledSlots = Object.values(wizardData.timeSlots).reduce((total, daySlots) => {
                return total + daySlots.filter(slot => slot.file.trim()).length;
            }, 0);
            
            if (filledSlots === 0) {
                showToast('Please add at least one time slot with a video', 'error');
                return false;
            }
            return true;
    }
    return false;
}

// Add missing utility functions
function addTimeSlot() {
    // This is called from the old schedule builder - redirect to new one
    showToast('Use the "Add Slot" buttons for each day in the schedule builder below', 'info');
}

function autoFillSchedule() {
    // This is called from the old schedule builder - redirect to new one
    autoFillAllDays();
}

async function createSchedule() {
    try {
        showToast('Creating schedule...', 'info');
        
        // Format schedule data for API
        const scheduleData = {
            channel: wizardData.selectedChannel,
            type: wizardData.scheduleType,
            weekly: {}
        };
        
        // Convert time slots to proper format
        Object.keys(wizardData.timeSlots).forEach(day => {
            const daySlots = wizardData.timeSlots[day]
                .filter(slot => slot.file.trim()) // Only include slots with videos
                .map(slot => ({
                    time: slot.time,
                    file: slot.file.trim()
                }))
                .sort((a, b) => a.time.localeCompare(b.time)); // Sort by time
            
            if (daySlots.length > 0) {
                scheduleData.weekly[day] = daySlots;
            }
        });
        
        // Call API to create schedule
        const result = await apiCall('/api/wizard/schedule/create', 'POST', {
            channel_name: wizardData.selectedChannel,
            schedule_type: wizardData.scheduleType,
            schedule_data: scheduleData
        });
        
        if (result.success) {
            const totalSlots = Object.values(scheduleData.weekly).reduce((total, daySlots) => total + daySlots.length, 0);
            const daysWithSchedule = Object.keys(scheduleData.weekly).length;
            
            showToast(
                `✅ Schedule Created Successfully!\n\n` +
                `Channel: ${wizardData.selectedChannel}\n` +
                `Type: ${wizardData.scheduleType}\n` +
                `Days with schedule: ${daysWithSchedule}/7\n` +
                `Total time slots: ${totalSlots}\n\n` +
                `The schedule is now active for this channel.`,
                'success'
            );
            hideSchedulerWizard();
            
            // Refresh TV guide to show new schedule
            await loadTVGuide();
        } else {
            throw new Error(result.error || 'Unknown error');
        }
        
    } catch (error) {
        showToast('Failed to create schedule: ' + error.message, 'error');
    }
}

// ========================================
// UTILITY FUNCTIONS
// ========================================

function browseFolderForCollection() {
    // Since we can't open folder dialogs from web, show instructions
    showToast(
        'Enter the full path to your video folder in the text field.\n\n' +
        'Examples:\n' +
        'Windows: C:\\Videos\\Movies\n' +
        'Linux/Mac: /home/user/videos/movies\n\n' +
        'After entering the path, the wizard will scan for video files automatically.',
        'info'
    );
    
    // Focus the input field
    document.getElementById('folderPath').focus();
}

// Add event listener for folder path input
function setupFolderPathInput() {
    const folderInput = document.getElementById('folderPath');
    if (folderInput) {
        folderInput.addEventListener('blur', function() {
            const path = this.value.trim();
            if (path && path !== wizardData.selectedFolder) {
                scanFolderForVideos(path);
            }
        });
        
        folderInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const path = this.value.trim();
                if (path) {
                    scanFolderForVideos(path);
                }
            }
        });
    }
}

function initializeScheduleBuilder() {
    const scheduleType = wizardData.scheduleType || 'weekly';
    const grid = document.getElementById('scheduleGrid');
    
    if (scheduleType === 'weekly') {
        grid.innerHTML = `
            <div class="schedule-builder-header">
                <h5>📅 Weekly Schedule Builder</h5>
                <p>Create time slots for each day of the week. Click "Add Time Slot" to get started.</p>
            </div>
            
            <div class="schedule-days-grid">
                <div class="schedule-day" data-day="monday">
                    <div class="schedule-day-header">Monday</div>
                    <div class="schedule-day-slots" id="slots-monday"></div>
                    <button class="btn btn-small btn-secondary" onclick="addTimeSlotForDay('monday')">+ Add Slot</button>
                </div>
                <div class="schedule-day" data-day="tuesday">
                    <div class="schedule-day-header">Tuesday</div>
                    <div class="schedule-day-slots" id="slots-tuesday"></div>
                    <button class="btn btn-small btn-secondary" onclick="addTimeSlotForDay('tuesday')">+ Add Slot</button>
                </div>
                <div class="schedule-day" data-day="wednesday">
                    <div class="schedule-day-header">Wednesday</div>
                    <div class="schedule-day-slots" id="slots-wednesday"></div>
                    <button class="btn btn-small btn-secondary" onclick="addTimeSlotForDay('wednesday')">+ Add Slot</button>
                </div>
                <div class="schedule-day" data-day="thursday">
                    <div class="schedule-day-header">Thursday</div>
                    <div class="schedule-day-slots" id="slots-thursday"></div>
                    <button class="btn btn-small btn-secondary" onclick="addTimeSlotForDay('thursday')">+ Add Slot</button>
                </div>
                <div class="schedule-day" data-day="friday">
                    <div class="schedule-day-header">Friday</div>
                    <div class="schedule-day-slots" id="slots-friday"></div>
                    <button class="btn btn-small btn-secondary" onclick="addTimeSlotForDay('friday')">+ Add Slot</button>
                </div>
                <div class="schedule-day" data-day="saturday">
                    <div class="schedule-day-header">Saturday</div>
                    <div class="schedule-day-slots" id="slots-saturday"></div>
                    <button class="btn btn-small btn-secondary" onclick="addTimeSlotForDay('saturday')">+ Add Slot</button>
                </div>
                <div class="schedule-day" data-day="sunday">
                    <div class="schedule-day-header">Sunday</div>
                    <div class="schedule-day-slots" id="slots-sunday"></div>
                    <button class="btn btn-small btn-secondary" onclick="addTimeSlotForDay('sunday')">+ Add Slot</button>
                </div>
            </div>
            
            <div class="schedule-builder-actions">
                <button class="btn btn-secondary" onclick="autoFillAllDays()">🤖 Auto Fill All Days</button>
                <button class="btn btn-secondary" onclick="copyDaySchedule()">📋 Copy Day Schedule</button>
                <button class="btn btn-danger" onclick="clearAllSchedules()">🗑️ Clear All</button>
            </div>
        `;
    }
    
    // Initialize empty time slots
    wizardData.timeSlots = {};
    updateScheduleValidation();
}

function addTimeSlotForDay(day) {
    const slotsContainer = document.getElementById(`slots-${day}`);
    const slotId = `${day}-${Date.now()}`;
    
    const slotHtml = `
        <div class="time-slot" id="${slotId}">
            <div class="time-slot-controls">
                <input type="time" class="time-input" value="09:00" onchange="updateTimeSlot('${slotId}')">
                <input type="text" class="video-input" placeholder="Enter video path or name..." onchange="updateTimeSlot('${slotId}')">
                <button class="btn-small btn-danger" onclick="removeTimeSlot('${slotId}')">✕</button>
            </div>
        </div>
    `;
    
    slotsContainer.insertAdjacentHTML('beforeend', slotHtml);
    
    // Initialize time slot data
    if (!wizardData.timeSlots[day]) {
        wizardData.timeSlots[day] = [];
    }
    
    wizardData.timeSlots[day].push({
        id: slotId,
        time: '09:00:00',
        file: ''
    });
    
    updateScheduleValidation();
}

function updateTimeSlot(slotId) {
    const slotElement = document.getElementById(slotId);
    const timeInput = slotElement.querySelector('.time-input');
    const videoInput = slotElement.querySelector('.video-input');
    
    const [day] = slotId.split('-');
    const slotIndex = wizardData.timeSlots[day].findIndex(slot => slot.id === slotId);
    
    if (slotIndex !== -1) {
        wizardData.timeSlots[day][slotIndex].time = timeInput.value + ':00';
        wizardData.timeSlots[day][slotIndex].file = videoInput.value;
    }
    
    updateScheduleValidation();
}

function removeTimeSlot(slotId) {
    const slotElement = document.getElementById(slotId);
    const [day] = slotId.split('-');
    
    // Remove from data
    if (wizardData.timeSlots[day]) {
        wizardData.timeSlots[day] = wizardData.timeSlots[day].filter(slot => slot.id !== slotId);
    }
    
    // Remove from DOM
    slotElement.remove();
    
    updateScheduleValidation();
}

function updateScheduleValidation() {
    const totalSlots = Object.values(wizardData.timeSlots).reduce((total, daySlots) => total + daySlots.length, 0);
    const filledSlots = Object.values(wizardData.timeSlots).reduce((total, daySlots) => {
        return total + daySlots.filter(slot => slot.file.trim()).length;
    }, 0);
    
    const nextBtn = document.getElementById('schedulerWizardNext');
    nextBtn.disabled = filledSlots === 0;
    
    // Update the controls section with stats
    const controlsSection = document.querySelector('.schedule-controls');
    if (controlsSection) {
        const existingStats = controlsSection.querySelector('.schedule-stats');
        if (existingStats) existingStats.remove();
        
        const statsHtml = `
            <div class="schedule-stats">
                <span>📊 ${totalSlots} slots created, ${filledSlots} with videos</span>
            </div>
        `;
        controlsSection.insertAdjacentHTML('beforeend', statsHtml);
    }
}

function autoFillAllDays() {
    const sampleVideos = [
        'movie1.mp4',
        'movie2.mkv', 
        'movie3.avi',
        'series_s01e01.mp4',
        'series_s01e02.mp4',
        'documentary.mp4'
    ];
    
    const sampleTimes = ['09:00', '11:30', '14:00', '16:30', '19:00', '21:30'];
    const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
    
    days.forEach(day => {
        // Clear existing slots
        const slotsContainer = document.getElementById(`slots-${day}`);
        slotsContainer.innerHTML = '';
        wizardData.timeSlots[day] = [];
        
        // Add sample slots
        sampleTimes.forEach((time, index) => {
            addTimeSlotForDay(day);
            
            // Fill with sample data
            setTimeout(() => {
                const slots = slotsContainer.querySelectorAll('.time-slot');
                const lastSlot = slots[slots.length - 1];
                if (lastSlot) {
                    const timeInput = lastSlot.querySelector('.time-input');
                    const videoInput = lastSlot.querySelector('.video-input');
                    
                    timeInput.value = time;
                    videoInput.value = sampleVideos[index % sampleVideos.length];
                    
                    // Update data
                    updateTimeSlot(lastSlot.id);
                }
            }, 50);
        });
    });
    
    showToast('Auto-filled all days with sample schedule', 'success');
}

function clearAllSchedules() {
    const confirmed = confirm('Clear all time slots? This cannot be undone.');
    if (!confirmed) return;
    
    const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
    days.forEach(day => {
        const slotsContainer = document.getElementById(`slots-${day}`);
        if (slotsContainer) {
            slotsContainer.innerHTML = '';
        }
        wizardData.timeSlots[day] = [];
    });
    
    updateScheduleValidation();
    showToast('All schedules cleared', 'info');
}

function copyDaySchedule() {
    showToast('Copy day functionality will be implemented in future version', 'info');
}

// Initialize wizard functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('🧙‍♂️ Wizard functionality loaded');
    
    // Setup global event listeners for wizard modals
    setupWizardEventListeners();
});

function setupWizardEventListeners() {
    // Close modals when clicking outside
    window.addEventListener('click', function(event) {
        const collectionModal = document.getElementById('collectionWizardModal');
        const schedulerModal = document.getElementById('schedulerWizardModal');
        
        if (event.target === collectionModal) {
            hideCollectionWizard();
        }
        if (event.target === schedulerModal) {
            hideSchedulerWizard();
        }
    });
    
    // Escape key to close modals
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            if (document.getElementById('collectionWizardModal').style.display === 'block') {
                hideCollectionWizard();
            }
            if (document.getElementById('schedulerWizardModal').style.display === 'block') {
                hideSchedulerWizard();
            }
        }
    });
}