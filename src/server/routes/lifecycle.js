// akiratv/src/server/routes/lifecycle.js
// JavaScript port of Python routes/lifecycle.py

const express = require('express');
const router = express.Router();
const { getAkiraTV } = require('../app');

/**
 * Start AkiraTV engine
 */
router.post('/start', async (req, res) => {
    try {
        const akiraTV = getAkiraTV();
        if (!akiraTV) {
            return res.status(500).json({ success: false, error: 'AkiraTV not initialized' });
        }
        
        const result = await akiraTV.start();
        if (result) {
            res.json({ success: true, message: 'AkiraTV started successfully' });
        } else {
            res.status(500).json({ success: false, error: 'Failed to start AkiraTV' });
        }
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

/**
 * Stop AkiraTV engine
 */
router.post('/stop', async (req, res) => {
    try {
        const akiraTV = getAkiraTV();
        if (!akiraTV) {
            return res.status(500).json({ success: false, error: 'AkiraTV not initialized' });
        }
        
        akiraTV.stop();
        res.json({ success: true, message: 'AkiraTV stopped successfully' });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

/**
 * Restart AkiraTV engine
 */
router.post('/restart', async (req, res) => {
    try {
        const akiraTV = getAkiraTV();
        if (!akiraTV) {
            return res.status(500).json({ success: false, error: 'AkiraTV not initialized' });
        }
        
        // Stop first
        akiraTV.stop();
        
        // Wait a moment then start
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        const result = await akiraTV.start();
        if (result) {
            res.json({ success: true, message: 'AkiraTV restarted successfully' });
        } else {
            res.status(500).json({ success: false, error: 'Failed to restart AkiraTV' });
        }
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

/**
 * Get engine status
 */
router.get('/status', (req, res) => {
    const akiraTV = getAkiraTV();
    if (!akiraTV) {
        return res.json({
            is_running: false,
            uptime: '0s',
            stats: {}
        });
    }
    
    const stats = akiraTV.getStats();
    res.json({
        is_running: akiraTV.running,
        uptime: stats.uptime || '0s',
        stats: stats
    });
});

module.exports = router;
