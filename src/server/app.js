// akiratv/src/server/app.js
// JavaScript port of Python api_server.py - Express REST server

const express = require('express');
const path = require('path');
const fs = require('fs');
const os = require('os');

// Import core modules
const { AkiraTV, getAkiraTV, createAkiraTV, STATS } = require('../core/channelManager');
const { Config } = require('../config/config');

// Import routes
const lifecycleRouter = require('./routes/lifecycle');
const channelsRouter = require('./routes/channels');
const configRouter = require('./routes/config');
const guideRouter = require('./routes/guide');
const vodRouter = require('./routes/vod');
const playlistRouter = require('./routes/playlist');
const standbyRouter = require('./routes/standby');
const fastSchedulerRouter = require('./routes/fastScheduler');
const wizardRouter = require('./routes/wizard');
const libraryRouter = require('./routes/library');
const monitoringRouter = require('./routes/monitoring');
const websocketRouter = require('./routes/websocket');

const app = express();
const PORT = process.env.PORT || 8081;

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// CORS middleware
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    if (req.method === 'OPTIONS') {
        return res.sendStatus(200);
    }
    next();
});

// Static file serving
const BASE_DIR = path.join(__dirname, '..', '..');
const STATIC_DIR = path.join(BASE_DIR, 'akiratv', 'static');
const USER_DIR = path.join(BASE_DIR, 'user');

// Mount static files directory
if (fs.existsSync(STATIC_DIR)) {
    app.use('/static', express.static(STATIC_DIR));
    console.log(`Serving static files from: ${STATIC_DIR}`);
}

// Mount user directory for covers, logos, etc.
if (fs.existsSync(USER_DIR)) {
    app.use('/user', express.static(USER_DIR));
    console.log(`Serving user assets from: ${USER_DIR}`);
} else {
    fs.mkdirSync(USER_DIR, { recursive: true });
    app.use('/user', express.static(USER_DIR));
}

// AkiraTV instance
let akiraTV = null;

/**
 * Initialize AkiraTV
 */
async function initialize() {
    try {
        const config = await Config.loadOrCreate(path.join(BASE_DIR, 'config.json'));
        const port = config.data.output?.http?.port || PORT;
        
        akiraTV = await createAkiraTV(path.join(BASE_DIR, 'config.json'));
        
        return { port, config };
    } catch (e) {
        console.error('Failed to initialize:', e);
        throw e;
    }
}

// ========================================
// ROUTES
// ========================================

// Register routers
app.use('/api/lifecycle', lifecycleRouter);
app.use('/api/channels', channelsRouter);
app.use('/api/config', configRouter);
app.use('/api/guide', guideRouter);
app.use('/api/vod', vodRouter);
app.use('/api/playlist', playlistRouter);
app.use('/api/standby', standbyRouter);
app.use('/api/fast-scheduler', fastSchedulerRouter);
app.use('/api/wizard', wizardRouter);
app.use('/api/library', libraryRouter);
app.use('/api/monitoring', monitoringRouter);
app.use('/api/ws', websocketRouter);

// WebSocket endpoint
const { setupWebSocket } = require('./routes/websocket');

// ========================================
// UTILITY ENDPOINTS
// ========================================

/**
 * Clear HLS cache
 */
app.post('/api/cache/clear', async (req, res) => {
    try {
        const outputRoot = path.join(BASE_DIR, 'output');
        let deleted = 0;
        
        if (fs.existsSync(outputRoot)) {
            const files = fs.readdirSync(outputRoot);
            for (const file of files) {
                const filePath = path.join(outputRoot, file);
                try {
                    if (fs.statSync(filePath).isDirectory()) {
                        fs.rmSync(filePath, { recursive: true, force: true });
                    }
                    deleted++;
                } catch (e) {
                    // Ignore errors
                }
            }
        }
        
        res.json({ success: true, message: 'Cache cleared', data: { deleted } });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

/**
 * Reload schedule
 */
app.post('/api/schedule/reload', async (req, res) => {
    try {
        const channel = req.query.channel || null;
        const result = await akiraTV.reloadSchedule(channel);
        res.json({ success: true, message: channel ? `Schedule reloaded for ${channel}` : 'All schedules reloaded' });
    } catch (e) {
        res.status(400).json({ success: false, error: e.message });
    }
});

/**
 * Get logs info
 */
app.get('/api/logs', (req, res) => {
    const logDir = path.join(BASE_DIR, 'logs');
    
    if (!fs.existsSync(logDir)) {
        fs.mkdirSync(logDir, { recursive: true });
    }
    
    let logFiles = [];
    if (fs.existsSync(logDir)) {
        const files = fs.readdirSync(logDir).filter(f => f.endsWith('.log'));
        for (const file of files) {
            const filePath = path.join(logDir, file);
            const stats = fs.statSync(filePath);
            logFiles.push({
                name: file,
                path: filePath,
                size: stats.size
            });
        }
    }
    
    res.json({
        directory: logDir,
        files: logFiles,
        message: `Logs directory: ${logDir}`
    });
});

/**
 * XMLTV generation endpoint (placeholder - would need full implementation)
 */
app.post('/api/xmltv/generate', async (req, res) => {
    try {
        const outputRoot = path.join(BASE_DIR, 'output');
        
        if (!fs.existsSync(outputRoot)) {
            fs.mkdirSync(outputRoot, { recursive: true });
        }
        
        const xmltvPath = path.join(outputRoot, 'xmltv.xml');
        const m3uPath = path.join(outputRoot, 'channels.m3u');
        
        // Placeholder - actual implementation would call xmltv generation
        res.json({
            success: true,
            message: 'XMLTV generation not yet implemented in JavaScript port',
            data: {
                xmltv_path: xmltvPath,
                m3u_path: m3uPath
            }
        });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ========================================
// UI PAGES
// ========================================

/**
 * Serve the web UI (index.html)
 */
app.get('/', (req, res) => {
    const uiPath = path.join(STATIC_DIR, 'index.html');
    if (fs.existsSync(uiPath)) {
        res.sendFile(uiPath);
    } else {
        res.json({
            name: "AkiraTV API",
            version: "1.0.0",
            docs: "/docs",
            websocket: "/ws",
            note: "Web UI not found. Create 'static' directory with index.html, styles.css, and app.js"
        });
    }
});

/**
 * Serve the viewer UI
 */
app.get('/viewer', (req, res) => {
    const viewerPath = path.join(STATIC_DIR, 'viewer.html');
    if (fs.existsSync(viewerPath)) {
        res.sendFile(viewerPath);
    } else {
        res.json({ error: "Viewer page not found" });
    }
});

/**
 * Serve the wizard UI
 */
app.get('/wizard', (req, res) => {
    const wizardPath = path.join(STATIC_DIR, 'wizard.html');
    if (fs.existsSync(wizardPath)) {
        res.sendFile(wizardPath);
    } else {
        res.json({ error: "Wizard page not found" });
    }
});

/**
 * Serve the guide UI
 */
app.get('/guide', (req, res) => {
    const guidePath = path.join(STATIC_DIR, 'guide.html');
    if (fs.existsSync(guidePath)) {
        res.sendFile(guidePath);
    } else {
        res.json({ error: "Guide page not found" });
    }
});

/**
 * Serve the VOD UI
 */
app.get('/vod', (req, res) => {
    const vodPath = path.join(STATIC_DIR, 'vod.html');
    if (fs.existsSync(vodPath)) {
        res.sendFile(vodPath);
    } else {
        res.json({ error: "VOD page not found" });
    }
});

// ========================================
// HEALTH CHECK
// ========================================

app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        server: 'running'
    });
});

// ========================================
// SERVER STARTUP
// ========================================

let server = null;

async function startServer() {
    try {
        const { port, config } = await initialize();
        
        server = app.listen(port, '0.0.0.0', () => {
            console.log(`[START] AkiraTV API Server started`);
            console.log(`[PORT] Server running on port ${port}`);
            console.log(`[WEB] Web UI: http://localhost:${port}`);
            console.log(`[WS] WebSocket: ws://localhost:${port}/ws`);
        });
        
        // Setup WebSocket
        setupWebSocket(server);
        
        return server;
    } catch (e) {
        console.error('[ERROR] Failed to start server:', e);
        throw e;
    }
}

function stopServer() {
    if (server) {
        server.close(() => {
            console.log('🛑 AkiraTV API Server shutting down');
        });
    }
    if (akiraTV) {
        akiraTV.stop();
    }
}

// Export for use
module.exports = { app, startServer, stopServer, getAkiraTV };

// Start server if run directly
if (require.main === module) {
    startServer().catch(console.error);
}
