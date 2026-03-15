// akiratv/src/core/channelManager.js
// JavaScript port of Python core.py - Channel management and playback control

const fs = require('fs');
const path = require('path');
const { EventEmitter } = require('events');
const { Config } = require('../config/config');
const { getCurrentScheduleForChannel } = require('../scheduler/scheduler');

// Logger setup
const LOG_DIR = path.join(__dirname, '..', '..', 'logs');
if (!fs.existsSync(LOG_DIR)) {
    fs.mkdirSync(LOG_DIR, { recursive: true });
}

const LOG_FILE = path.join(LOG_DIR, 'worker.log');

function log(level, message) {
    const timestamp = new Date().toISOString();
    const logMessage = `${timestamp} [${level}] ${message}\n`;
    fs.appendFileSync(LOG_FILE, logMessage);
    console.log(`${timestamp} [${level}]`, message);
}

const logger = {
    info: (msg) => log('INFO', msg),
    warning: (msg) => log('WARN', msg),
    error: (msg) => log('ERROR', msg),
    debug: (msg) => log('DEBUG', msg)
};

// Stats management
const STATS = {
    status: 'Stopped',
    viewers: 0,
    channels: 0,
    uptime: '0s',
    config: {},
    now_playing: null,
    next_program: null
};

// AkiraTV instance
let AKIRATV_INSTANCE = null;

/**
 * AkiraTV Main Class - orchestrates all streaming operations
 */
class AkiraTV extends EventEmitter {
    constructor() {
        super();
        this.config = null;
        this.workers = {}; // channelName -> { worker, thread }
        this.running = false;
        this.httpServer = null;
        this.startTime = null;
        
        // Track restart state for linear channels
        this.linearChannelConfigs = {};
        // Track which linear channels should be stopped permanently
        this.stoppedLinearChannels = new Set();
        
        // Command queue
        this.commandQueue = [];
        this._commandThreadRunning = false;
        
        AKIRATV_INSTANCE = this;
    }

    /**
     * Initialize and load config
     */
    async initialize(configPath = 'config.json') {
        this.config = await Config.loadOrCreate(configPath);
        
        // Update stats with config
        STATS.config = { ...this.config.data };
        
        logger.info("AkiraTV initialized");
        return this;
    }

    /**
     * Main entry point - orchestrates all streaming operations
     */
    async start() {
        this.running = true;
        this.startTime = Date.now();
        logger.info("AkiraTV starting...");
        
        STATS.status = "Streaming";
        STATS.channels = 0;
        STATS.uptime = "0s";
        STATS.config = { ...this.config.data };
        
        // Start command processing thread
        this._startCommandThread();
        
        // Initialize HTTP server if needed
        if (!await this._initializeHttpServer()) {
            return false;
        }
        
        // Get channels config
        const channelsConfig = this.config.data.channels || {};
        
        for (const [channelName, channelConf] of Object.entries(channelsConfig)) {
            if (!channelConf.enabled) {
                logger.info(`Channel '${channelName}' is disabled. Skipping.`);
                continue;
            }

            const channelType = channelConf.type || "linear";
            
            try {
                if (channelType === "vod") {
                    await this._startVodChannel(channelName);
                } else if (channelType === "linear") {
                    await this._startLinearChannel(channelName);
                } else if (channelType === "dynamic") {
                    await this._startDynamicChannel(channelName);
                } else {
                    logger.error(`Unknown channel type '${channelType}' for channel '${channelName}'. Skipping.`);
                    continue;
                }
            } catch (e) {
                logger.error(`[ERROR] Failed to start worker for ${channelName}: ${e.message}`);
            }
        }

        if (Object.keys(this.workers).length === 0) {
            logger.error("No channels were started. Exiting.");
            console.log("[ERROR] No valid channels to stream. Check your configuration.");
            return false;
        }

        this._finalizeStartup();
        this._startMonitoring();
        
        return true;
    }

    /**
     * Start a VOD channel (no auto-restart)
     */
    async _startVodChannel(channelName) {
        logger.info(`Starting VOD channel: ${channelName}`);
        
        // For copy-only mode (Android), we don't need transcoding
        // We'll use direct file serving
        const worker = {
            channel: channelName,
            type: 'vod',
            running: true,
            currentVideo: null,
            startPosition: 0
        };
        
        this.workers[channelName] = { worker, thread: null };
        logger.info(`[OK] VOD worker for ${channelName} started.`);
    }

    /**
     * Start a linear channel with auto-restart wrapper
     */
    async _startLinearChannel(channelName) {
        logger.info(`Starting Linear channel: ${channelName}`);
        
        const schedule = await getCurrentScheduleForChannel(channelName);
        
        if (!schedule || schedule.length === 0) {
            logger.warning(`No schedule found for linear channel '${channelName}'. Skipping.`);
            return;
        }

        // Store the channel config for restarts
        this.linearChannelConfigs[channelName] = {
            schedule: schedule
        };
        
        // Start the worker with auto-restart wrapper
        // In Node.js, we'll use setInterval for the restart loop
        const worker = {
            channel: channelName,
            type: 'linear',
            running: true,
            schedule: schedule,
            currentEntry: null
        };
        
        this.workers[channelName] = { worker, thread: null };
        
        // Start linear worker loop
        this._startLinearWorkerLoop(channelName);
        
        logger.info(`[OK] Linear worker for ${channelName} started with auto-restart.`);
    }

    /**
     * Start a dynamic channel (standby with VOD switching)
     */
    async _startDynamicChannel(channelName) {
        logger.info(`Starting Dynamic channel: ${channelName}`);
        
        const schedule = await getCurrentScheduleForChannel(channelName);
        
        const worker = {
            channel: channelName,
            type: 'dynamic',
            running: true,
            schedule: schedule,
            currentEntry: null
        };
        
        this.workers[channelName] = { worker, thread: null };
        logger.info(`[OK] Dynamic worker for ${channelName} started.`);
    }

    /**
     * Linear worker restart loop
     */
    _startLinearWorkerLoop(channelName) {
        const checkInterval = setInterval(async () => {
            if (!this.running || this.stoppedLinearChannels.has(channelName)) {
                clearInterval(checkInterval);
                logger.info(`Linear worker restart loop for ${channelName} has exited.`);
                return;
            }
            
            // Get fresh schedule periodically
            const schedule = await getCurrentScheduleForChannel(channelName);
            
            if (!schedule || schedule.length === 0) {
                logger.warning(`No schedule for ${channelName}, waiting 60s...`);
                return;
            }
            
            // Update worker schedule
            if (this.workers[channelName]) {
                this.workers[channelName].worker.schedule = schedule;
            }
            
        }, 60000); // Check every minute
        
        this.workers[channelName].interval = checkInterval;
    }

    /**
     * Initialize HTTP server for HLS streaming
     */
    async _initializeHttpServer() {
        const outputMode = this.config.data.output?.mode;
        if (outputMode !== "http_hls" && outputMode !== "ram_http") {
            return true;
        }
        
        try {
            const hlsRoot = this._getHlsRootPath();
            if (!fs.existsSync(hlsRoot)) {
                fs.mkdirSync(hlsRoot, { recursive: true });
            }
            console.log(`[FOLDER] HTTP server will serve HLS from: ${hlsRoot}`);
            
            // HTTP server will be initialized by the Express app
            // This is handled in app.js
            return true;
        } catch (e) {
            logger.error(`HTTP server failed: ${e.message}`);
            console.log("[ERROR] Error: Could not start HTTP server.");
            return false;
        }
    }

    /**
     * Get HLS root path based on output mode
     */
    _getHlsRootPath() {
        const outputMode = this.config.data.output?.mode;
        if (outputMode === "ram_http") {
            return this.config.data.storage?.ram_path || "./output";
        } else {
            return this.config.data.storage?.disk_path || "./output";
        }
    }

    /**
     * Final setup after workers are launched
     */
    _finalizeStartup() {
        if (!this.workers || Object.keys(this.workers).length === 0) {
            return;
        }
        
        const firstChannel = Object.keys(this.workers)[0];
        const port = this.config.data.output?.http?.port || 8080;
        const bind = this.config.data.output?.http?.bind || "127.0.0.1";
        const ip = bind !== "0.0.0.0" ? bind : "YOUR_LOCAL_IP";
        
        console.log(`[OK] AkiraTV is running! Streaming ${Object.keys(this.workers).length} channel(s).`);
        console.log(`Watch: http://${ip}:${port}/hls/${firstChannel}/index.m3u8`);
    }

    /**
     * Start monitoring runtime
     */
    _startMonitoring() {
        this._monitorInterval = setInterval(() => {
            if (!this.running) return;
            
            // Update uptime
            if (this.startTime) {
                const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
                const hours = Math.floor(elapsed / 3600);
                const minutes = Math.floor((elapsed % 3600) / 60);
                const seconds = elapsed % 60;
                STATS.uptime = `${hours}h ${minutes}m ${seconds}s`;
            }
            
            // Emit stats update event
            this.emit('statsUpdate', STATS);
            
        }, 2000);
    }

    /**
     * Command processing thread
     */
    _startCommandThread() {
        this._commandThreadRunning = true;
        
        this._commandInterval = setInterval(() => {
            if (!this._commandThreadRunning) return;
            
            const cmd = this.commandQueue.shift();
            if (!cmd) return;
            
            const { command, channel, videoPath, startPosition } = cmd;
            
            if (command === "play_now") {
                this._playNow(channel, videoPath, startPosition);
            }
        }, 200);
    }

    /**
     * Send play_now command to a channel
     */
    _playNow(channel, videoPath, startPosition = 0) {
        if (!(channel in this.workers)) {
            logger.warning(`⚠️ Channel '${channel}' not found in workers dictionary. Cannot play video.`);
            logger.warning(`Available workers: ${Object.keys(this.workers).join(', ')}`);
            return;
        }

        const { worker } = this.workers[channel];
        
        if (!worker) {
            logger.error(`⚠️ Channel '${channel}' worker is None (not running). Cannot play video.`);
            return;
        }
        
        logger.info(`[PLAY] Worker found for channel '${channel}': ${worker.type}`);

        if (worker.type === 'vod' || worker.type === 'dynamic') {
            logger.info(`[PLAY] Sending 'play_now' command to ${worker.type} channel '${channel}' (start: ${startPosition}s).`);
            worker.currentVideo = videoPath;
            worker.startPosition = startPosition;
            this.emit('playNow', { channel, videoPath, startPosition });
        } else {
            logger.warning(`⚠️ Channel '${channel}' does not support play_now commands.`);
        }
    }

    /**
     * Stop AkiraTV
     */
    stop() {
        this._commandThreadRunning = false;
        if (this._commandInterval) {
            clearInterval(this._commandInterval);
        }
        
        logger.info("Shutting down AkiraTV...");
        STATS.status = "Stopped";
        this.running = false;

        if (this.httpServer) {
            this.httpServer.stop();
        }

        for (const [channelName, { worker, thread, interval }] of Object.entries(this.workers)) {
            if (worker) {
                logger.info(`Sending stop signal to worker for channel: ${channelName}`);
                worker.running = false;
            }
            if (interval) {
                clearInterval(interval);
            }
            logger.info(`Worker for channel: ${channelName} has stopped.`);
        }
        
        if (this._monitorInterval) {
            clearInterval(this._monitorInterval);
        }
        
        logger.info("AkiraTV stopped.");
    }

    /**
     * Reload schedule without restarting
     */
    async reloadSchedule(channel = null) {
        logger.info("Reloading schedules...");
        
        const channels = channel ? [channel] : Object.keys(this.config.data.channels || {});
        let reloadedCount = 0;
        
        for (const chan of channels) {
            const chanConf = this.config.data.channels?.[chan];
            if (!chanConf?.enabled) continue;
            
            const newEntries = await getCurrentScheduleForChannel(chan);
            
            if (chan in this.workers) {
                const { worker } = this.workers[chan];
                if (worker && worker.schedule) {
                    worker.schedule = newEntries;
                    reloadedCount++;
                }
            }
        }
        
        if (reloadedCount > 0) {
            logger.info(`Schedule reloaded successfully for ${reloadedCount} channel(s).`);
        } else {
            logger.warning("No channels were updated.");
        }
        
        return { success: true, reloaded: reloadedCount };
    }

    /**
     * Enqueue a play_now command
     */
    enqueuePlayNow(channel, videoPath, startPosition = 0) {
        this.commandQueue.push({
            command: "play_now",
            channel,
            videoPath,
            startPosition
        });
    }

    /**
     * Get current stats
     */
    getStats() {
        return { ...STATS };
    }

    /**
     * Get channel status
     */
    getChannelStatus(channel) {
        if (!(channel in this.workers)) {
            return { exists: false };
        }
        
        const { worker } = this.workers[channel];
        return {
            exists: true,
            type: worker.type,
            running: worker.running,
            currentVideo: worker.currentVideo,
            schedule: worker.schedule || []
        };
    }

    /**
     * Get all channel statuses
     */
    getAllChannelStatuses() {
        const statuses = {};
        for (const [channel, { worker }] of Object.entries(this.workers)) {
            statuses[channel] = {
                type: worker.type,
                running: worker.running,
                currentVideo: worker.currentVideo
            };
        }
        return statuses;
    }
}

/**
 * Get the AkiraTV instance
 */
function getAkiraTV() {
    return AKIRATV_INSTANCE;
}

/**
 * Create or get the AkiraTV instance
 */
async function createAkiraTV(configPath = 'config.json') {
    if (!AKIRATV_INSTANCE) {
        AKIRATV_INSTANCE = new AkiraTV();
        await AKIRATV_INSTANCE.initialize(configPath);
    }
    return AKIRATV_INSTANCE;
}

module.exports = { AkiraTV, getAkiraTV, createAkiraTV, STATS };
