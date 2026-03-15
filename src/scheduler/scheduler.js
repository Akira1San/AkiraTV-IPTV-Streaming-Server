// akiratv/src/scheduler/scheduler.js
// JavaScript port of Python scheduler.py

const fs = require('fs');
const path = require('path');

const BASE_DIR = path.join(__dirname, '..', '..');
const USER_DIR = path.join(BASE_DIR, 'user');
const SCHEDULE_DIR = path.join(USER_DIR, 'schedules');
const COLLECTIONS_DIR = path.join(USER_DIR, 'collections');

// Ensure directories exist
function ensureDir(dirPath) {
    if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, { recursive: true });
    }
}
ensureDir(SCHEDULE_DIR);
ensureDir(COLLECTIONS_DIR);

// Logger setup (simplified)
const logger = {
    info: (...args) => console.log('[INFO]', ...args),
    warning: (...args) => console.log('[WARN]', ...args),
    error: (...args) => console.error('[ERROR]', ...args),
    debug: (...args) => console.log('[DEBUG]', ...args)
};

// Cache for collections to avoid repeated disk reads
const collectionsCache = {};

/**
 * Load collections for a specific channel/profile
 * @param {string} channelName - The channel/profile name (e.g., "TatkoTV")
 * @returns {Promise<Array>} List of collection dictionaries
 */
async function loadCollectionsForChannel(channelName) {
    // Check cache first
    if (collectionsCache[channelName]) {
        return collectionsCache[channelName];
    }

    // Try different file naming conventions
    const possibleFiles = [
        path.join(COLLECTIONS_DIR, `collections_${channelName}.json`),
        path.join(COLLECTIONS_DIR, `${channelName}.json`),
    ];

    let collections = [];
    for (const collectionFile of possibleFiles) {
        if (fs.existsSync(collectionFile)) {
            try {
                const data = JSON.parse(fs.readFileSync(collectionFile, 'utf-8'));
                collections = data.collections || [];
                collectionsCache[channelName] = collections;
                logger.info(`Loaded ${collections.length} collections from ${path.basename(collectionFile)}`);
                return collections;
            } catch (e) {
                logger.error(`Failed to load collections from ${collectionFile}: ${e.message}`);
            }
        }
    }

    // No file found - try to find any matching collection file
    if (fs.existsSync(COLLECTIONS_DIR)) {
        const files = fs.readdirSync(COLLECTIONS_DIR).filter(f => f.endsWith('.json'));
        for (const file of files) {
            const fileName = path.basename(file, '.json').toLowerCase();
            if (fileName.includes(channelName.toLowerCase())) {
                try {
                    const filePath = path.join(COLLECTIONS_DIR, file);
                    const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
                    collections = data.collections || [];
                    collectionsCache[channelName] = collections;
                    logger.info(`Loaded ${collections.length} collections from ${file}`);
                    return collections;
                } catch (e) {
                    logger.error(`Failed to load collections from ${file}: ${e.message}`);
                }
            }
        }
    }

    logger.warning(`No collection file found for channel: ${channelName}`);
    return [];
}

/**
 * Resolve collection_id to full video path
 * Since each collection = one video, we use the first video in the collection
 * @param {string} collectionId - The collection identifier (e.g., "into_the_sun")
 * @param {string|null} channelName - Optional channel name to narrow search
 * @returns {Promise<string|null>} Full path to video file, or null if not found
 */
async function resolveCollectionToPath(collectionId, channelName = null) {
    // If channel specified, try that specific file first
    if (channelName) {
        const collections = await loadCollectionsForChannel(channelName);
        for (const collection of collections) {
            if (collection.id === collectionId) {
                const videos = collection.videos || [];
                if (videos.length > 0) {
                    return videos[0].path || '';
                }
            }
        }
    }

    // Search all cached collections
    for (const cachedCollections of Object.values(collectionsCache)) {
        for (const collection of cachedCollections) {
            if (collection.id === collectionId) {
                const videos = collection.videos || [];
                if (videos.length > 0) {
                    return videos[0].path || '';
                }
            }
        }
    }

    // Try loading from all collection files
    if (fs.existsSync(COLLECTIONS_DIR)) {
        const files = fs.readdirSync(COLLECTIONS_DIR).filter(f => f.startsWith('collections_') && f.endsWith('.json'));
        for (const file of files) {
            try {
                const filePath = path.join(COLLECTIONS_DIR, file);
                const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
                const collections = data.collections || [];
                
                // Add to cache
                const channel = path.basename(file, '.json').replace('collections_', '');
                collectionsCache[channel] = collections;

                for (const collection of collections) {
                    if (collection.id === collectionId) {
                        const videos = collection.videos || [];
                        if (videos.length > 0) {
                            return videos[0].path || '';
                        }
                    }
                }
            } catch (e) {
                logger.error(`Failed to search collections in ${file}: ${e.message}`);
            }
        }
    }

    logger.error(`Collection not found: ${collectionId}`);
    return null;
}

/**
 * Validate and ensure each entry has required fields
 * Supports both legacy format (file) and collection-based format (collection_id)
 */
function validateEntries(entries, source) {
    const valid = [];
    for (let i = 0; i < entries.length; i++) {
        const entry = entries[i];
        try {
            if (typeof entry !== 'object' || entry === null) {
                throw new Error("not a dictionary");
            }

            // Check for required fields - either "file" or "collection_id"
            const hasFile = 'file' in entry;
            const hasCollectionId = 'collection_id' in entry;

            if (!hasFile && !hasCollectionId) {
                throw new Error("missing 'time' and either 'file' or 'collection_id'");
            }
            if (!('time' in entry)) {
                throw new Error("missing 'time'");
            }

            // Resolve collection_id to file path if needed
            if (hasCollectionId && !hasFile) {
                // Note: This is sync resolution - in real use may need async
                logger.debug(`collection_id resolution would happen at runtime for: ${entry.collection_id}`);
            }

            valid.push({ ...entry });
        } catch (e) {
            logger.warning(`Skipping invalid entry ${i} from ${source}: ${e.message}`);
        }
    }
    return valid;
}

/**
 * Get today's date info
 */
function getTodayInfo() {
    const now = new Date();
    return {
        date: now.toISOString().split('T')[0], // YYYY-MM-DD
        dayOfWeek: now.toLocaleDateString('en-US', { weekday: 'long' }).toLowerCase(),
        time: now.toTimeString().split(' ')[0], // HH:MM:SS
        dateTime: now
    };
}

/**
 * Load today's schedule entries and return only current + future entries
 * Supports both calendar-specific entries and weekly recurring entries
 */
async function getFullTodaysSchedule() {
    const { date, dayOfWeek, time, dateTime } = getTodayInfo();

    let scheduleFile = path.join(SCHEDULE_DIR, 'schedule.json');
    if (!fs.existsSync(scheduleFile)) {
        scheduleFile = path.join(BASE_DIR, 'schedule.json'); // fallback
    }

    if (!fs.existsSync(scheduleFile)) {
        logger.error("schedule.json not found!");
        throw new Error("schedule.json is missing. Please create one.");
    }

    try {
        const fullSchedule = JSON.parse(fs.readFileSync(scheduleFile, 'utf-8'));
    } catch (e) {
        logger.error(`Invalid JSON in schedule.json: ${e.message}`);
        throw new Error(`schedule.json is invalid: ${e.message}`);
    }

    const fullSchedule = JSON.parse(fs.readFileSync(scheduleFile, 'utf-8'));
    let entries = [];
    let calendarFound = false;

    // 1. Check for enhanced calendar entries (new format)
    const calendarSection = fullSchedule.calendar || {};
    if (Object.keys(calendarSection).length > 0) {
        for (const [calendarKey, calendarData] of Object.entries(calendarSection)) {
            if (typeof calendarData === 'object' && calendarData.date === date) {
                const calendarEntries = calendarData.entries || [];
                logger.info(`📅 Found enhanced calendar entry for ${date} (${calendarData.day || 'Unknown'}) - ${calendarData.description || 'No description'}`);
                logger.info(`📅 Loaded ${calendarEntries.length} calendar entry(ies), overriding weekly schedule`);
                entries.push(...validateEntries(calendarEntries, `calendar:${calendarKey}`));
                calendarFound = true;
                break;
            }
        }
    }

    // 2. Check for legacy calendar entries (old format: direct date keys)
    if (!calendarFound && date in fullSchedule) {
        const dateEntries = fullSchedule[date];
        logger.info(`📅 Found legacy calendar entry for ${date}`);
        logger.info(`📅 Loaded ${dateEntries.length} legacy calendar entry(ies)`);
        entries.push(...validateEntries(dateEntries, `legacy_date:${date}`));
        calendarFound = true;
    }

    // 3. Weekly recurring entries (only if no calendar entry found)
    if (!calendarFound) {
        const weekly = fullSchedule.weekly || {};
        if (dayOfWeek in weekly) {
            const weeklyEntries = weekly[dayOfWeek];
            logger.info(`📆 Using weekly schedule for ${dayOfWeek}`);
            logger.info(`📆 Loaded ${weeklyEntries.length} weekly entry(ies) for ${dayOfWeek}`);
            entries.push(...validateEntries(weeklyEntries, `weekly:${dayOfWeek}`));
        } else {
            logger.warning(`📆 No weekly schedule found for ${dayOfWeek}`);
        }
    }

    if (entries.length === 0) {
        logger.warning(`[ERROR] No schedule entries found for ${date} (${dayOfWeek})`);
        return [];
    }

    // Sort all entries by time
    entries.sort((a, b) => a.time.localeCompare(b.time));

    // Find the current entry (the last entry that started before now)
    let currentEntryIndex = -1;
    const currentTime = dateTime;

    for (let i = 0; i < entries.length; i++) {
        const entry = entries[i];
        const entryTime = new Date(`2000-01-01T${entry.time}`).getTime();
        const entryDateTime = new Date(`2000-01-01T${entry.time}`);
        
        if (entryTime < currentTime.getTime()) {
            currentEntryIndex = i;
        } else {
            break;
        }
    }

    // Return from current entry to end
    if (currentEntryIndex >= 0) {
        const result = entries.slice(currentEntryIndex);
        logger.info(`[OK] Found current entry at index ${currentEntryIndex}, returning ${result.length} entries`);
        return result;
    } else {
        // No entries started yet - return all (start from first)
        logger.info(`[OK] No current entry found, returning all ${entries.length} entries`);
        return entries;
    }
}

/**
 * Load only current + future entries for a specific channel
 */
async function getCurrentScheduleForChannel(channel) {
    // Fallback to traditional JSON schedule loading
    const { date, dayOfWeek, time, dateTime } = getTodayInfo();

    // Load per-channel schedule
    let scheduleFile = path.join(SCHEDULE_DIR, `schedule_${channel}.json`);
    if (!fs.existsSync(scheduleFile)) {
        scheduleFile = path.join(BASE_DIR, `schedule_${channel}.json`); // fallback
    }
    if (!fs.existsSync(scheduleFile)) {
        return [];
    }

    let sched;
    try {
        sched = JSON.parse(fs.readFileSync(scheduleFile, 'utf-8'));
    } catch (e) {
        logger.warning(`Failed to load ${scheduleFile}: ${e.message}`);
        return [];
    }

    let entries = [];
    let calendarFound = false;

    // 1. Check for enhanced calendar entries
    const calendarSection = sched.calendar || {};
    if (Object.keys(calendarSection).length > 0) {
        for (const [calendarKey, calendarData] of Object.entries(calendarSection)) {
            if (typeof calendarData === 'object' && calendarData.date === date) {
                const calendarEntries = calendarData.entries || [];
                logger.info(`📅 Found calendar entry for ${channel} on ${date} (${calendarData.day || 'Unknown'})`);
                // Ensure channel field
                for (const entry of calendarEntries) {
                    entry.channel = channel;
                }
                entries.push(...calendarEntries);
                calendarFound = true;
                break;
            }
        }
    }

    // 2. Check for legacy calendar entries
    if (!calendarFound && date in sched) {
        const dateEntries = sched[date];
        logger.info(`📅 Found legacy calendar entry for ${channel} on ${date}`);
        for (const entry of dateEntries) {
            entry.channel = channel;
        }
        entries.push(...dateEntries);
        calendarFound = true;
    }

    // 3. Weekly recurring entries
    if (!calendarFound) {
        const weekly = sched.weekly || {};
        const weeklyEntries = weekly[dayOfWeek] || [];
        if (weeklyEntries.length > 0) {
            logger.info(`📆 Using weekly schedule for ${channel} on ${dayOfWeek}`);
            for (const entry of weeklyEntries) {
                entry.channel = channel;
            }
            entries.push(...weeklyEntries);
        }
    }

    if (entries.length === 0) {
        return [];
    }

    // Validate entries
    const validatedEntries = validateEntries(entries, `schedule:${channel}`);

    if (validatedEntries.length === 0) {
        logger.warning(`No valid entries found after validation for channel '${channel}'`);
        return [];
    }

    // Sort by time
    validatedEntries.sort((a, b) => a.time.localeCompare(b.time));

    // Find current entry (last one that started before now)
    let currentEntryIndex = -1;
    const currentTime = dateTime;

    for (let i = 0; i < validatedEntries.length; i++) {
        const entry = validatedEntries[i];
        try {
            const entryTime = new Date(`2000-01-01T${entry.time}`).getTime();
            
            // Handle overnight/schedule wrap-around
            // If entry time is more than 2 hours ahead, treat as yesterday
            const timeDiffSeconds = (entryTime - currentTime.getTime()) / 1000;
            
            let entryDateTime;
            if (timeDiffSeconds > 7200) {
                // Entry time is more than 2 hours ahead - treat as yesterday
                const yesterday = new Date(currentTime);
                yesterday.setDate(yesterday.getDate() - 1);
                entryDateTime = new Date(`${yesterday.toISOString().split('T')[0]}T${entry.time}`);
            } else {
                entryDateTime = new Date(`2000-01-01T${entry.time}`);
            }

            if (entryDateTime.getTime() <= currentTime.getTime()) {
                currentEntryIndex = i;
            } else {
                // Stop at first future entry
                break;
            }
        } catch (e) {
            logger.warning(`Error parsing entry time for ${entry.file || 'unknown'}: ${e.message}`);
            continue;
        }
    }

    // Return from current entry onward
    if (currentEntryIndex >= 0) {
        logger.info(`Found ${currentEntryIndex + 1} past schedule entry(ies), starting from entry ${currentEntryIndex + 1}`);
        return validatedEntries.slice(currentEntryIndex);
    } else {
        if (validatedEntries.length > 0) {
            logger.info(`No past entries found. Starting from beginning (first entry at ${validatedEntries[0].time || 'unknown'})`);
        }
        return validatedEntries;
    }
}

/**
 * Clear the collections cache
 */
function clearCache() {
    Object.keys(collectionsCache).forEach(key => delete collectionsCache[key]);
}

module.exports = {
    loadCollectionsForChannel,
    resolveCollectionToPath,
    getFullTodaysSchedule,
    getCurrentScheduleForChannel,
    clearCache,
    SCHEDULE_DIR,
    COLLECTIONS_DIR
};
