// AkiraTV Collection & Scheduler Wizard
// Separate JavaScript file for wizard functionality

// Wizard State Management
let currentWizard = null; // 'collection' or 'scheduler'
let wizardStep = 0;
let wizardData = {};

// Logging system
class WizardLogger {
    constructor() {
        this.logs = [];
    }
    
    log(level, message, data = null) {
        const timestamp = new Date().toISOString();
        const logEntry = {
            timestamp,
            level,
            message,
            data
        };
        
        this.logs.push(logEntry);
        console.log(`[${level.toUpperCase()}] ${message}`, data || '');
        
        // Send to server for file logging
        this.sendToServer(logEntry);
    }
    
    async sendToServer(logEntry) {
        try {
            await fetch('/api/wizard/log', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(logEntry)
            });
        } catch (error) {
            // Silently fail - don't want logging to break the wizard
        }
    }
    
    info(message, data) { this.log('info', message, data); }
    warn(message, data) { this.log('warn', message, data); }
    error(message, data) { this.log('error', message, data); }
    debug(message, data) { this.log('debug', message, data); }
}

const wizardLogger = new WizardLogger();

// ========================================
// COLLECTION WIZARD
// ========================================

function showCollectionWizard() {
    wizardLogger.info('Starting Collection Wizard');
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
    wizardLogger.info('Collection Wizard modal opened');
}

function hideCollectionWizard() {
    document.getElementById('collectionWizardModal').style.display = 'none';
    currentWizard = null;
    wizardStep = 0;
    wizardData = {};
}

function loadCollectionWizardStep() {
    console.log(`📋 Loading collection wizard step ${wizardStep}`);
    const body = document.getElementById('collectionWizardBody');
    const nextBtn = document.getElementById('collectionWizardNext');
    
    switch(wizardStep) {
        case 0:
            console.log('📁 Setting up step 1: Select Folder');
            body.innerHTML = getCollectionStep1HTML();
            nextBtn.textContent = t('wizard.next');
            nextBtn.disabled = true;
            // Setup folder path input listeners with a delay to ensure DOM is ready
            setTimeout(() => {
                console.log('⏰ Setting up folder input after delay');
                setupFolderPathInput();
                // Also add a manual scan button for testing
                addManualScanButton();
            }, 200);
            break;
        case 1:
            console.log('⚙️ Setting up step 2: Configure');
            body.innerHTML = getCollectionStep2HTML();
            nextBtn.textContent = t('wizard.next');
            nextBtn.disabled = true;
            // Auto-generate channel name from collection name
            setTimeout(setupCollectionStep2, 100);
            break;
        case 2:
            console.log('📋 Setting up step 3: Review');
            body.innerHTML = getCollectionStep3HTML();
            nextBtn.textContent = t('wizard.finish');
            nextBtn.disabled = false;
            break;
    }
}

function addManualScanButton() {
    const folderInputSection = document.querySelector('.folder-input-section .input-group');
    if (folderInputSection) {
        // Add a manual scan button for debugging
        const scanButton = document.createElement('button');
        scanButton.className = 'btn btn-primary';
        scanButton.textContent = '🔍 Scan';
        scanButton.onclick = function() {
            const path = document.getElementById('wizardFolderPath').value.trim();
            if (path) {
                console.log('📁 Manual scan triggered:', path);
                scanFolderForVideos(path);
            } else {
                showToast('Please enter a folder path first', 'error');
            }
        };
        folderInputSection.appendChild(scanButton);
        console.log('✅ Manual scan button added');
    } else {
        console.warn('⚠️ Could not find folder input section to add scan button');
    }
}

function setupCollectionStep2() {
    const channelSelect = document.getElementById('wizardChannelSelect');
    
    // Load existing channels for the dropdown
    loadChannelsForWizard();
    
    // Auto-generate collection name from folder path
    generateCollectionNameFromFolder();
    
    if (channelSelect) {
        // Validate when user selects from dropdown
        channelSelect.addEventListener('change', function() {
            updateCollectionPreview();
            validateStep2Inputs();
        });
        
        // Initial validation
        validateStep2Inputs();
    }
}

function generateCollectionNameFromFolder() {
    if (wizardData.selectedFolder) {
        // Extract folder name from path
        const folderPath = wizardData.selectedFolder;
        const folderName = folderPath.split(/[/\\]/).pop() || 'collection';
        
        // Clean up folder name to make a nice collection name
        const collectionName = folderName
            .replace(/[_-]/g, ' ')  // Replace underscores and hyphens with spaces
            .replace(/\b\w/g, l => l.toUpperCase())  // Capitalize first letter of each word
            .trim();
        
        // Store in wizard data
        wizardData.collectionName = collectionName;
        
        console.log(`📁 Auto-generated collection name: "${collectionName}" from folder: "${folderPath}"`);
    }
}

function updateCollectionPreview() {
    const channelSelect = document.getElementById('wizardChannelSelect');
    const preview = document.getElementById('collectionPreview');
    const previewCollectionName = document.getElementById('previewCollectionName');
    const previewChannelName = document.getElementById('previewChannelName');
    const previewFolderPath = document.getElementById('previewFolderPath');
    
    if (channelSelect && channelSelect.value && preview) {
        // Show preview
        preview.style.display = 'block';
        
        // Update preview content
        if (previewCollectionName) previewCollectionName.textContent = wizardData.collectionName || 'Auto-generated';
        if (previewChannelName) previewChannelName.textContent = channelSelect.value;
        if (previewFolderPath) previewFolderPath.textContent = wizardData.selectedFolder || 'Not set';
    } else if (preview) {
        // Hide preview
        preview.style.display = 'none';
    }
}

async function loadChannelsForWizard() {
    try {
        const response = await apiCall('/api/channels');
        const channels = response.channels || [];
        
        const channelSelect = document.getElementById('wizardChannelSelect');
        if (!channelSelect) return;
        
        // Clear existing options
        channelSelect.innerHTML = '<option value="">-- Select a channel --</option>';
        
        if (channels.length === 0) {
            channelSelect.innerHTML = '<option value="">No existing channels found</option>';
            wizardLogger.info('No channels found for wizard dropdown');
            return;
        }
        
        // Add channels to dropdown
        channels.forEach(channel => {
            const option = document.createElement('option');
            option.value = channel.name;
            option.textContent = `${channel.name} (${channel.type})`;
            channelSelect.appendChild(option);
        });
        
        wizardLogger.info(`Loaded ${channels.length} channels for wizard dropdown`);
        
        // Trigger validation after loading channels
        validateStep2Inputs();
        
    } catch (error) {
        wizardLogger.error('Failed to load channels for wizard', error);
        const channelSelect = document.getElementById('wizardChannelSelect');
        if (channelSelect) {
            channelSelect.innerHTML = '<option value="">Failed to load channels</option>';
        }
    }
}

async function checkCollectionExists(collectionName) {
    const collectionWarning = document.getElementById('collectionExistsWarning');
    if (!collectionWarning || !collectionName.trim()) {
        if (collectionWarning) collectionWarning.style.display = 'none';
        return false;
    }
    
    try {
        // Check if collection file exists by trying to scan collections directory
        const response = await fetch('/api/wizard/collection/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ collection_name: collectionName })
        });
        
        if (response.ok) {
            const result = await response.json();
            const exists = result.exists || false;
            
            if (exists) {
                collectionWarning.style.display = 'block';
                wizardLogger.warn(`Collection '${collectionName}' already exists`);
            } else {
                collectionWarning.style.display = 'none';
            }
            
            return exists;
        }
    } catch (error) {
        // If API call fails, hide warning (don't block user)
        collectionWarning.style.display = 'none';
        wizardLogger.debug('Collection existence check failed', error);
    }
    
    return false;
}

function validateStep2Inputs() {
    const channelSelect = document.getElementById('wizardChannelSelect');
    const nextBtn = document.getElementById('collectionWizardNext');
    
    // Simple validation: only need channel selection (collection name is auto-generated)
    const channelName = channelSelect ? channelSelect.value.trim() : '';
    const isValid = channelName.length > 0;
    
    if (nextBtn) {
        nextBtn.disabled = !isValid;
    }
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
                    <input type="text" id="wizardFolderPath" class="wizard-input" placeholder="Enter folder path (e.g., C:\\Videos\\Movies)" />
                </div>
                <div class="folder-help">
                    <small>Supported formats: MP4, MKV, AVI, MOV, M4V, WMV, FLV</small>
                    <br><small><strong>Tip:</strong> Enter the full path to your video folder, then click "🔍 Scan" or press Enter to scan for videos.</small>
                </div>
                <div class="folder-suggestions">
                    <small><strong>Try these common paths:</strong></small>
                    <div class="suggestion-buttons">
                        <button class="btn-suggestion" onclick="tryFolderPath('C:\\\\Users\\\\Public\\\\Videos')">📁 Public Videos</button>
                        <button class="btn-suggestion" onclick="tryFolderPath('C:\\\\Users\\\\' + (window.navigator.userAgent.includes('Windows') ? 'YourUsername' : 'username') + '\\\\Videos')">📁 User Videos</button>
                        <button class="btn-suggestion" onclick="tryFolderPath('D:\\\\Movies')">📁 D:\\Movies</button>
                    </div>
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
                <span>Select Channel</span>
            </div>
            <div class="wizard-step">
                <div class="wizard-step-number">3</div>
                <span>Create Collection</span>
            </div>
        </div>
        
        <div class="wizard-content">
            <h4>📺 Select Channel</h4>
            <p>Choose which channel this collection will belong to.</p>
            
            <div class="config-section">
                <div class="input-group">
                    <label>Channel:</label>
                    <select id="wizardChannelSelect" class="wizard-select">
                        <option value="">Loading existing channels...</option>
                    </select>
                    <small>Select the channel where this collection will be available.</small>
                </div>
                
                <div class="collection-preview" id="collectionPreview" style="display: none;">
                    <h5>📁 Collection Preview:</h5>
                    <div class="preview-item">
                        <strong>Collection Name:</strong> <span id="previewCollectionName">-</span>
                    </div>
                    <div class="preview-item">
                        <strong>Channel:</strong> <span id="previewChannelName">-</span>
                    </div>
                    <div class="preview-item">
                        <strong>Folder:</strong> <span id="previewFolderPath">-</span>
                    </div>
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
            const folderPath = document.getElementById('wizardFolderPath').value.trim();
            if (!folderPath) {
                showToast('Please select a folder path', 'error');
                return false;
            }
            wizardData.selectedFolder = folderPath;
            
            // Simulate folder scanning (in real implementation, this would call an API)
            scanFolderForVideos(folderPath);
            return true;
            
        case 1:
            const channelSelect = document.getElementById('wizardChannelSelect');
            const channelName = channelSelect ? channelSelect.value.trim() : '';
            
            if (!channelName) {
                showToast('Please select a channel', 'error');
                return false;
            }
            
            // Collection name is auto-generated from folder
            if (!wizardData.collectionName) {
                generateCollectionNameFromFolder();
            }
            
            if (!wizardData.collectionName) {
                showToast('Unable to generate collection name from folder', 'error');
                return false;
            }
            
            wizardData.channelName = channelName;
            wizardData.isNewChannel = false;
            return true;
    }
    return false;
}

async function scanFolderForVideos(folderPath) {
    wizardLogger.info('Starting folder scan', { folderPath });
    
    try {
        // Show loading state
        const preview = document.getElementById('folderPreview');
        const stats = document.getElementById('folderStats');
        
        if (stats) {
            stats.innerHTML = `
                <div class="folder-stat">
                    <div class="loading"></div>
                    <strong>Scanning folder...</strong>
                </div>
            `;
            preview.style.display = 'block';
        }
        
        // Call API to scan folder for videos
        const result = await apiCall('/api/wizard/scan-folder', 'POST', {
            folder_path: folderPath
        });
        
        wizardLogger.info('Scan result received', result);
        
        if (result.success) {
            wizardData.videoFiles = result.data.videos || [];
            wizardData.selectedFolder = folderPath;
            
            // Show folder preview
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
                    <div class="folder-stat success">
                        <strong>✅ Ready to proceed!</strong>
                    </div>
                `;
                preview.style.display = 'block';
                
                // Enable next button
                document.getElementById('collectionWizardNext').disabled = false;
                
                showToast(`Found ${wizardData.videoFiles.length} video files in folder`, 'success');
                wizardLogger.info('Folder scan successful', { 
                    videoCount: wizardData.videoFiles.length,
                    totalSize: result.data.total_size 
                });
            } else {
                stats.innerHTML = `
                    <div class="folder-stat error">
                        <strong>⚠️ No video files found in this folder</strong>
                    </div>
                    <div class="folder-help">
                        <small>Supported formats: MP4, MKV, AVI, MOV, M4V, WMV, FLV, WEBM, MPG, MPEG, TS, M2TS</small>
                    </div>
                    <div class="folder-help">
                        <small>Make sure the folder path is correct and contains video files.</small>
                    </div>
                `;
                preview.style.display = 'block';
                document.getElementById('collectionWizardNext').disabled = true;
                
                showToast('No video files found in the specified folder', 'warning');
                wizardLogger.warn('No video files found in folder', { folderPath });
            }
        } else {
            throw new Error(result.error || result.detail || 'Failed to scan folder');
        }
    } catch (error) {
        wizardLogger.error('Folder scan failed', { 
            folderPath, 
            error: error.message,
            stack: error.stack 
        });
        
        // Show error in preview
        const preview = document.getElementById('folderPreview');
        const stats = document.getElementById('folderStats');
        
        if (stats) {
            // Extract more specific error information
            let errorMessage = error.message;
            let helpText = 'Please check the folder path and try again.';
            
            if (errorMessage.includes('does not exist')) {
                helpText = `The folder "${folderPath}" was not found. Please check:`;
            } else if (errorMessage.includes('not a directory')) {
                helpText = `"${folderPath}" is not a folder. Please enter a folder path.`;
            } else if (errorMessage.includes('permission')) {
                helpText = `Permission denied accessing "${folderPath}". Please check folder permissions.`;
            }
            
            stats.innerHTML = `
                <div class="folder-stat error">
                    <strong>❌ Error scanning folder</strong>
                </div>
                <div class="folder-help">
                    <small><strong>Error:</strong> ${errorMessage}</small>
                </div>
                <div class="folder-help">
                    <small><strong>Help:</strong> ${helpText}</small>
                </div>
                <div class="folder-help">
                    <small><strong>Troubleshooting:</strong></small>
                    <ul style="margin-left: 20px; margin-top: 5px;">
                        <li>Verify the folder exists: <code>${folderPath}</code></li>
                        <li>Check spelling and use correct path separators (\\)</li>
                        <li>Ensure you have read permissions for the folder</li>
                        <li>Try a different folder (e.g., C:\\Users\\Public\\Videos)</li>
                    </ul>
                </div>
                <div class="folder-help">
                    <small><strong>Common Windows paths:</strong></small>
                    <ul style="margin-left: 20px; margin-top: 5px;">
                        <li>C:\\Users\\${window.navigator.userAgent.includes('Windows') ? 'YourUsername' : 'username'}\\Videos</li>
                        <li>C:\\Users\\Public\\Videos</li>
                        <li>D:\\Movies (if you have a D: drive)</li>
                    </ul>
                </div>
            `;
            preview.style.display = 'block';
        }
        
        document.getElementById('collectionWizardNext').disabled = true;
        showToast(`Failed to scan folder: ${errorMessage}`, 'error');
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
        wizardLogger.info('Starting collection creation', wizardData);
        showToast('Creating collection...', 'info');
        
        // Validate wizard data
        if (!wizardData.collectionName || !wizardData.channelName || !wizardData.selectedFolder) {
            throw new Error('Missing required wizard data');
        }
        
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
                formats: [...new Set(wizardData.videoFiles.map(v => v.format || v.name.split('.').pop().toUpperCase()))]
            }
        };
        
        wizardLogger.info('Calling collection creation API', {
            collection_name: wizardData.collectionName,
            channel_name: wizardData.channelName,
            channel_type: wizardData.channelType,
            folder_path: wizardData.selectedFolder
        });
        
        // Call API to create collection
        const result = await apiCall('/api/wizard/collection/create', 'POST', {
            collection_name: wizardData.collectionName,
            channel_name: wizardData.channelName,
            folder_path: wizardData.selectedFolder,
            collection_data: collectionData,
            is_new_channel: false, // Always false - only creating collection files
            overwrite_existing: wizardData.overwriteExisting || false
        });
        
        wizardLogger.info('Collection creation API response', result);
        
        if (result.success) {
            showToast(
                `✅ Collection Created Successfully!\n\n` +
                `Collection: ${wizardData.collectionName}\n` +
                `Channel: ${wizardData.channelName}\n` +
                `Videos: ${wizardData.videoFiles.length} files\n\n` +
                `Collection file has been created and is ready to use.`,
                'success'
            );
            hideCollectionWizard();
            
            // Refresh channels to show new collection
            await loadChannels();
            
            wizardLogger.info('Collection created successfully', result.data);
        } else {
            // Handle API error response
            const errorMsg = result.error || result.detail || result.message || 'Unknown error from API';
            wizardLogger.error('API returned error', result);
            throw new Error(errorMsg);
        }
        
    } catch (error) {
        wizardLogger.error('Collection creation failed', { 
            error: error.message,
            stack: error.stack,
            wizardData: wizardData
        });
        
        let errorMessage = error.message;
        
        // Handle collection already exists error with overwrite confirmation
        if (error.message.includes('Collection file already exists') || error.message.includes('409')) {
            const confirmOverwrite = confirm(
                `⚠️ Collection Already Exists\n\n` +
                `A collection file for "${wizardData.collectionName}" already exists.\n\n` +
                `Do you want to overwrite the existing collection?\n\n` +
                `⚠️ This will permanently replace the existing collection file.`
            );
            
            if (confirmOverwrite) {
                wizardLogger.info('User confirmed overwrite, retrying collection creation');
                wizardData.overwriteExisting = true;
                
                try {
                    // Retry with overwrite flag
                    const retryResult = await apiCall('/api/wizard/collection/create', 'POST', {
                        collection_name: wizardData.collectionName,
                        channel_name: wizardData.channelName,
                        folder_path: wizardData.selectedFolder,
                        collection_data: {
                            name: wizardData.collectionName,
                            channel: wizardData.channelName,
                            folder: wizardData.selectedFolder,
                            videos: wizardData.videoFiles,
                            created: new Date().toISOString(),
                            metadata: {
                                total_videos: wizardData.videoFiles.length,
                                total_duration: "Unknown",
                                formats: [...new Set(wizardData.videoFiles.map(v => v.format || v.name.split('.').pop().toUpperCase()))]
                            }
                        },
                        is_new_channel: false,
                        overwrite_existing: true
                    });
                    
                    if (retryResult.success) {
                        showToast(
                            `✅ Collection Overwritten Successfully!\n\n` +
                            `Collection: ${wizardData.collectionName}\n` +
                            `Channel: ${wizardData.channelName}\n` +
                            `Videos: ${wizardData.videoFiles.length} files\n\n` +
                            `The existing collection has been replaced.`,
                            'success'
                        );
                        hideCollectionWizard();
                        await loadChannels();
                        wizardLogger.info('Collection overwritten successfully', retryResult.data);
                        return; // Exit successfully
                    } else {
                        throw new Error(retryResult.error || retryResult.detail || 'Failed to overwrite collection');
                    }
                } catch (retryError) {
                    errorMessage = `Failed to overwrite collection: ${retryError.message}`;
                }
            } else {
                wizardLogger.info('User cancelled overwrite');
                showToast('Collection creation cancelled', 'info');
                return; // Exit without error
            }
        }
        // Try to extract more specific error information
        else if (error.message.includes('Channel') && error.message.includes('already exists')) {
            errorMessage = `Channel name '${wizardData.channelName}' already exists. Please choose a different name.`;
        } else if (error.message.includes('permission')) {
            errorMessage = `Permission denied. Please check folder permissions for: ${wizardData.selectedFolder}`;
        } else if (error.message.includes('not found')) {
            errorMessage = `Folder not found: ${wizardData.selectedFolder}`;
        }
        
        showToast(`Failed to create collection: ${errorMessage}`, 'error');
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

function tryFolderPath(suggestedPath) {
    const folderInput = document.getElementById('wizardFolderPath');
    if (folderInput) {
        folderInput.value = suggestedPath;
        wizardLogger.info('Trying suggested folder path', { suggestedPath });
        scanFolderForVideos(suggestedPath);
    }
}

// Add event listener for folder path input
function setupFolderPathInput() {
    const folderInput = document.getElementById('wizardFolderPath');
    if (folderInput) {
        // Remove any existing listeners to prevent duplicates
        folderInput.removeEventListener('blur', handleFolderPathBlur);
        folderInput.removeEventListener('keypress', handleFolderPathKeypress);
        folderInput.removeEventListener('input', handleFolderPathInput);
        
        // Add event listeners
        folderInput.addEventListener('blur', handleFolderPathBlur);
        folderInput.addEventListener('keypress', handleFolderPathKeypress);
        folderInput.addEventListener('input', handleFolderPathInput);
        
        console.log('📁 Folder path input listeners setup complete for wizardFolderPath');
    } else {
        console.warn('⚠️ Wizard folder path input not found (wizardFolderPath)');
    }
}

function handleFolderPathBlur() {
    const path = this.value.trim();
    if (path && path !== wizardData.selectedFolder) {
        console.log('📁 Scanning folder on blur:', path);
        scanFolderForVideos(path);
    }
}

function handleFolderPathKeypress(e) {
    if (e.key === 'Enter') {
        const path = this.value.trim();
        if (path) {
            console.log('📁 Scanning folder on Enter:', path);
            scanFolderForVideos(path);
        }
    }
}

function handleFolderPathInput() {
    // Trigger scan after user stops typing for 1 second
    clearTimeout(this.scanTimeout);
    const path = this.value.trim();
    
    if (path && path !== wizardData.selectedFolder) {
        this.scanTimeout = setTimeout(() => {
            console.log('📁 Scanning folder on input delay:', path);
            scanFolderForVideos(path);
        }, 1000);
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