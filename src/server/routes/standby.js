// akiratv/src/server/routes/standby.js
// JavaScript port of Python routes/standby.py

const express = require('express');
const router = express.Router();
const path = require('path');
const fs = require('fs');

const BASE_DIR = path.join(__dirname, '..', '..', '..');
const ASSETS_DIR = path.join(BASE_DIR, 'assets', 'standby');

/**
 * Get standby video status
 */
router.get('/', (req, res) => {
    // Check if standby is enabled
    const akiraTV = getAkiraTV();
    
    res.json({
        enabled: true,
        mode: 'loop'
    });
});

/**
 * Get standby video URL
 */
router.get('/video', (req, res) => {
    const akiraTV = getAkiraTV();
    const port = akiraTV?.config?.data?.output?.http?.port || 8081;
    
    res.json({
        url: `http://localhost:${port}/static/standby/default_standby.mp4`
    });
});

/**
 * List available standby videos
 */
router.get('/list', (req, res) => {
    if (!fs.existsSync(ASSETS_DIR)) {
        return res.json({ videos: [] });
    }
    
    try {
        const files = fs.readdirSync(ASSETS_DIR).filter(f => f.endsWith('.mp4'));
        const videos = files.map(file => ({
            name: file,
            path: `/assets/standby/${file}`
        }));
        
        res.json({ videos });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

/**
 * Set active standby video
 */
router.post('/set', (req, res) => {
    const { video } = req.body;
    
    if (!video) {
        return res.status(400).json({ success: false, error: 'video name required' });
    }
    
    res.json({ success: true, message: `Standby video set to ${video}` });
});

module.exports = router;
