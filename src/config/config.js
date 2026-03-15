// akiratv/src/config/config.js
// JavaScript port of Python config.py

const fs = require('fs');
const path = require('path');

const USER_ROOT = path.join('user');
const USER_CHANNELS_DIR = path.join(USER_ROOT, 'channels');

const DEFAULT_CONFIG = {
    ffmpeg: {
        hwaccel: "cuda",
        enable_subtitles: false,
        transcoding: {
            enabled: false,
            bitrate: "auto",
            custom_bitrate: "1500k",
            video_quality: "source",
            encoder: "auto",
            audio_quality: "copy",
            fps: "auto",
            threads: "2",
            subtitle_font_size: "28"
        }
    },
    storage: {
        type: "disk",
        ram_path: "./output",
        disk_path: "./output"
    },
    output: {
        mode: "http_hls",
        http: {
            port: 8081,
            bind: "0.0.0.0"
        },
        hls: {
            segment_time: 6,
            playlist_size: 4
        }
    },
    streaming: {
        strategy: "concat",
        mode: "static",
        pre_gen: true
    },
    channels: {
        myAkiraTV: {
            enabled: true,
            type: "linear"
        },
        live: {
            enabled: true,
            type: "vod"
        }
    },
    worker: {
        auto_restart_ffmpeg: true,
        max_ram_usage_percent: 80
    },
    ui: {
        dark_mode: false
    }
};

/**
 * Deep merge two objects - override values in base with values in override
 */
function deepMerge(base, override) {
    const merged = JSON.parse(JSON.stringify(base)); // Deep copy
    for (const key in override) {
        if (override[key] !== null && typeof override[key] === 'object' && !Array.isArray(override[key])) {
            if (merged[key] !== null && typeof merged[key] === 'object') {
                merged[key] = deepMerge(merged[key], override[key]);
            } else {
                merged[key] = override[key];
            }
        } else {
            merged[key] = override[key];
        }
    }
    return merged;
}

/**
 * Config class - manages AkiraTV configuration
 */
class Config {
    constructor(data) {
        this.data = data;
        this.usbBasePath = null; // Set by Android bridge
    }

    /**
     * Returns a copy of the default configuration
     */
    static defaultConfig() {
        return JSON.parse(JSON.stringify(DEFAULT_CONFIG));
    }

    /**
     * Load existing config or create default
     * @param {string} configPath - Path to config file (default: config.json)
     * @returns {Promise<Config>} Config instance
     */
    static async loadOrCreate(configPath = 'config.json') {
        if (!fs.existsSync(configPath)) {
            console.log(`No config found at ${configPath}, creating default...`);
            await Config.writeDefault(configPath);
            console.log(`[OK] Created default config at ${configPath}`);
            console.log("You can edit this file and reload without restarting the server.");
            return new Config(Config.defaultConfig());
        }

        try {
            const fileContent = fs.readFileSync(configPath, 'utf-8');
            const data = JSON.parse(fileContent);
            console.log(`[OK] Loaded config from ${configPath}`);
            return new Config(Config.mergeWithDefaults(data));
        } catch (e) {
            console.error(`[ERROR] Invalid JSON in ${configPath}: ${e.message}`);
            console.log("Using default config instead");
            return new Config(Config.defaultConfig());
        }
    }

    /**
     * Deep merge user config with defaults
     */
    static mergeWithDefaults(userData) {
        return deepMerge(DEFAULT_CONFIG, userData);
    }

    /**
     * Write default config to file
     */
    static async writeDefault(configPath) {
        const example = {
            "__comment__": "AkiraTV Configuration - Edit values below and save",
            ...DEFAULT_CONFIG
        };
        fs.writeFileSync(configPath, JSON.stringify(example, null, 2), 'utf-8');
    }

    /**
     * Save current config to file
     * @param {string} configPath - Path to save to
     */
    save(configPath = 'config.json') {
        fs.writeFileSync(configPath, JSON.stringify(this.data, null, 2), 'utf-8');
        console.log(`[OK] Config saved to ${configPath}`);
    }

    /**
     * Get merged config for a specific channel
     */
    getChannelConfig(channel) {
        const base = { ...this.data.ffmpeg };
        const overrides = this.data.channels?.[channel] || {};
        return { ...base, ...overrides };
    }

    /**
     * Get hardware acceleration setting for channel
     */
    getHwaccel(channel) {
        return this.getChannelConfig(channel).hwaccel || "none";
    }

    /**
     * Check if subtitles are enabled for channel
     */
    subtitlesEnabled(channel) {
        return this.getChannelConfig(channel).enable_subtitles !== false;
    }

    /**
     * Get HLS output path for a specific channel
     */
    getHlsOutputPath(channel) {
        const mode = this.data.output?.mode;
        if (mode === "ram_http") {
            const ramPath = this.data.storage?.ram_path;
            if (!ramPath) {
                throw new Error("RAM mode selected but ram_path not set");
            }
            return path.join(ramPath, channel);
        } else {
            const diskPath = this.data.storage?.disk_path || "./output";
            return path.join(diskPath, channel);
        }
    }

    /**
     * Returns the root output directory (RAM or disk), without appending channel name
     */
    getOutputRoot() {
        const mode = this.data.output?.mode;
        if (mode === "ram_http") {
            const ramPath = this.data.storage?.ram_path;
            if (!ramPath) {
                throw new Error("RAM mode selected but ram_path not set");
            }
            return ramPath;
        } else {
            return this.data.storage?.disk_path || "./output";
        }
    }

    /**
     * Get paths object with USB support for Android
     */
    getPaths() {
        const basePath = this.usbBasePath || '';
        
        if (this.usbBasePath) {
            return {
                // Videos from USB
                videoPath: path.join(this.usbBasePath, 'AkiraTV', 'videos'),
                // HLS segments on USB (critical!)
                outputPath: path.join(this.usbBasePath, 'AkiraTV', 'output'),
                // Config on USB
                userPath: path.join(this.usbBasePath, 'AkiraTV', 'user'),
                // Logs on USB
                logPath: path.join(this.usbBasePath, 'AkiraTV', 'logs')
            };
        }
        
        return {
            videoPath: path.join(basePath, 'videos'),
            outputPath: path.join(basePath, 'output'),
            userPath: path.join(basePath, 'user'),
            logPath: path.join(basePath, 'logs')
        };
    }

    /**
     * Set USB base path (for Android)
     */
    setUsbPath(usbPath) {
        this.usbBasePath = usbPath;
    }
}

module.exports = { Config, DEFAULT_CONFIG, USER_ROOT, USER_CHANNELS_DIR };
