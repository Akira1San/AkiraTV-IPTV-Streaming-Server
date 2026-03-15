// akiratv/src/server/routes/library.js
// JavaScript port of Python routes/library.py

const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');

const BASE_DIR = path.join(__dirname, '..', '..', '..');
const VIDEO_INVENTORY_FILE = path.join(BASE_DIR, 'user', 'video_inventory.json');

/**
 * Get video library inventory
 */
router.get('/', (req, res) => {
    if (!fs.existsSync(VIDEO_INVENTORY_FILE)) {
        return res.json({ videos: [], total: 0 });
    }
    
    try {
        const content = fs.readFileSync(VIDEO_INVENTORY_FILE, 'utf-8');
        const data = JSON.parse(content);
        res.json({ videos: data.videos || [], total: data.videos?.length || 0 });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

/**
 * Scan directories for videos
 */
router.post('/scan', (req, res) => {
    const { paths } = req.body;
    
    if (!paths || !Array.isArray(paths)) {
        return res.status(400).json({ success: false, error: 'paths array is required' });
    }
    
    const videoExtensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'];
    const videos = [];
    
    for (const scanPath of paths) {
        if (!fs.existsSync(scanPath)) {
            continue;
        }
        
        try {
            const scanDir = (dirPath) => {
                const files = fs.readdirSync(dirPath, { withFileTypes: true });
                
                for (const file of files) {
                    const fullPath = path.join(dirPath, file.name);
                    
                    if (file.isDirectory()) {
                        scanDir(fullPath);
                    } else if (file.isFile()) {
                        const ext = path.extname(file.name).toLowerCase();
                        if (videoExtensions.includes(ext)) {
                            const stats = fs.statSync(fullPath);
                            videos.push({
                                name: file.name,
                                path: fullPath,
                                size: stats.size,
                                modified: stats.mtime
                            });
                        }
                    }
                }
            };
            
            scanDir(scanPath);
        } catch (e) {
            console.error(`Error scanning ${scanPath}:`, e);
        }
    }
    
    // Save inventory
    const inventory = { videos, scanned: new Date().toISOString() };
    
    try {
        fs.writeFileSync(VIDEO_INVENTORY_FILE, JSON.stringify(inventory, null, 2), 'utf-8');
        res.json({ success: true, videos, count: videos.length });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

/**
 * Get video info
 */
router.get('/:id', (req, res) => {
    const { id } = req.params;
    
    if (!fs.existsSync(VIDEO_INVENTORY_FILE)) {
        return res.status(404).json({ error: 'Video not found' });
    }
    
    try {
        const content = fs.readFileSync(VIDEO_INVENTORY_FILE, 'utf-8');
        const data = JSON.parse(content);
        
        const video = (data.videos || []).find((v, i) => String(i) === id || v.path === id);
        
        if (!video) {
            return res.status(404).json({ error: 'Video not found' });
        }
        
        res.json(video);
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

/**
 * Search videos
 */
router.get('/search', (req, res) => {
    const { q } = req.query;
    
    if (!q) {
        return res.status(400).json({ error: 'Search query required' });
    }
    
    if (!fs.existsSync(VIDEO_INVENTORY_FILE)) {
        return res.json({ results: [] });
    }
    
    try {
        const content = fs.readFileSync(VIDEO_INVENTORY_FILE, 'utf-8');
        const data = JSON.parse(content);
        
        const query = q.toLowerCase();
        const results = (data.videos || []).filter(v => 
            v.name.toLowerCase().includes(query) || 
            v.path.toLowerCase().includes(query)
        );
        
        res.json({ results, total: results.length });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

module.exports = router;
