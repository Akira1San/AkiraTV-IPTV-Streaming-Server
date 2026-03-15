// akiratv/src/server/routes/monitoring.js
// JavaScript port of Python routes/monitoring.py

const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const { getAkiraTV } = require('../app');

const BASE_DIR = path.join(__dirname, '..', '..', '..');

/**
 * Get live statistics
 */
router.get('/stats', (req, res) => {
    const akiraTV = getAkiraTV();
    if (!akiraTV) {
        return res.json({ status: 'Stopped', viewers: 0 });
    }
    
    const stats = akiraTV.getStats();
    res.json(stats);
});

/**
 * Get active viewer count
 */
router.get('/viewers', (req, res) => {
    const akiraTV = getAkiraTV();
    if (!akiraTV) {
        return res.json({ viewers: 0 });
    }
    
    const stats = akiraTV.getStats();
    res.json({ viewers: stats.viewers || 0 });
});

/**
 * Get detailed viewer information
 */
router.get('/viewers/detail', (req, res) => {
    // Simplified viewer tracking for JavaScript port
    res.json({
        total: 0,
        viewers: [],
        per_channel: {}
    });
});

/**
 * Get viewers for a specific channel
 */
router.get('/viewers/channel/:channel_name', (req, res) => {
    const { channel_name } = req.params;
    
    res.json({
        channel: channel_name,
        viewers: [],
        count: 0
    });
});

/**
 * Get recent log entries
 */
router.get('/logs', (req, res) => {
    const limit = parseInt(req.query.limit) || 100;
    const logDir = path.join(BASE_DIR, 'logs');
    const logFile = path.join(logDir, 'worker.log');
    
    let logs = [];
    
    if (fs.existsSync(logFile)) {
        try {
            const content = fs.readFileSync(logFile, 'utf-8');
            const lines = content.split('\n').filter(l => l.trim());
            
            // Get last N lines
            logs = lines.slice(-limit);
        } catch (e) {
            logs = [`Error reading log: ${e.message}`];
        }
    }
    
    res.json({ logs, count: logs.length });
});

/**
 * Get system information (for Android monitoring)
 */
router.get('/system', (req, res) => {
    const os = require('os');
    
    const totalMem = os.totalmem();
    const freeMem = os.freemem();
    const usedMem = totalMem - freeMem;
    
    res.json({
        platform: os.platform(),
        arch: os.arch(),
        node_version: process.version,
        uptime: os.uptime(),
        cpu_count: os.cpus().length,
        memory: {
            total: totalMem,
            free: freeMem,
            used: usedMem,
            percent: Math.round((usedMem / totalMem) * 100)
        }
    });
});

module.exports = router;
