// akiratv/src/server/routes/wizard.js
// JavaScript port of Python routes/wizard.py

const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');

const BASE_DIR = path.join(__dirname, '..', '..', '..');
const COLLECTIONS_DIR = path.join(BASE_DIR, 'user', 'collections');

// Ensure directory exists
if (!fs.existsSync(COLLECTIONS_DIR)) {
    fs.mkdirSync(COLLECTIONS_DIR, { recursive: true });
}

/**
 * Get all collections
 */
router.get('/collections', (req, res) => {
    if (!fs.existsSync(COLLECTIONS_DIR)) {
        return res.json({ collections: [] });
    }
    
    try {
        const files = fs.readdirSync(COLLECTIONS_DIR).filter(f => f.endsWith('.json'));
        const allCollections = [];
        
        for (const file of files) {
            const filePath = path.join(COLLECTIONS_DIR, file);
            const content = fs.readFileSync(filePath, 'utf-8');
            const data = JSON.parse(content);
            
            if (data.collections) {
                allCollections.push(...data.collections);
            }
        }
        
        res.json({ collections: allCollections, total: allCollections.length });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

/**
 * Create a new collection
 */
router.post('/collections', (req, res) => {
    const { name, paths, channel } = req.body;
    
    if (!name) {
        return res.status(400).json({ success: false, error: 'name is required' });
    }
    
    const id = name.toLowerCase().replace(/\s+/g, '_');
    const collection = {
        id,
        name,
        paths: paths || [],
        videos: []
    };
    
    // Save to channel-specific file
    const channelName = channel || 'default';
    const filePath = path.join(COLLECTIONS_DIR, `collections_${channelName}.json`);
    
    let data = { collections: [] };
    if (fs.existsSync(filePath)) {
        try {
            data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
        } catch (e) {
            // Ignore errors, use empty collections
        }
    }
    
    data.collections.push(collection);
    
    try {
        fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf-8');
        res.json({ success: true, collection });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

/**
 * Scan a path for videos
 */
router.post('/scan', (req, res) => {
    const { path: scanPath, extensions } = req.body;
    
    if (!scanPath) {
        return res.status(400).json({ success: false, error: 'path is required' });
    }
    
    if (!fs.existsSync(scanPath)) {
        return res.status(400).json({ success: false, error: 'Path does not exist' });
    }
    
    const videoExtensions = extensions || ['.mp4', '.mkv', '.avi', '.mov', '.wmv'];
    const videos = [];
    
    try {
        const files = fs.readdirSync(scanPath, { withFileTypes: true });
        
        for (const file of files) {
            if (file.isFile()) {
                const ext = path.extname(file.name).toLowerCase();
                if (videoExtensions.includes(ext)) {
                    videos.push({
                        name: file.name,
                        path: path.join(scanPath, file.name)
                    });
                }
            }
        }
        
        res.json({ success: true, videos, count: videos.length });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

/**
 * Generate schedule from collection
 */
router.post('/generate-schedule', (req, res) => {
    const { collection_id, channel, day, start_time } = req.body;
    
    if (!collection_id) {
        return res.status(400).json({ success: false, error: 'collection_id is required' });
    }
    
    // Find collection
    let foundCollection = null;
    
    if (fs.existsSync(COLLECTIONS_DIR)) {
        const files = fs.readdirSync(COLLECTIONS_DIR).filter(f => f.endsWith('.json'));
        
        for (const file of files) {
            const filePath = path.join(COLLECTIONS_DIR, file);
            const content = fs.readFileSync(filePath, 'utf-8');
            const data = JSON.parse(content);
            
            if (data.collections) {
                for (const collection of data.collections) {
                    if (collection.id === collection_id) {
                        foundCollection = collection;
                        break;
                    }
                }
            }
        }
    }
    
    if (!foundCollection) {
        return res.status(404).json({ success: false, error: 'Collection not found' });
    }
    
    // Generate schedule entries
    const entries = [];
    const videos = foundCollection.videos || [];
    let currentTime = start_time || '00:00:00';
    
    for (const video of videos) {
        entries.push({
            time: currentTime,
            file: video.path,
            display_name: video.name
        });
        
        // Advance time (placeholder - would need duration info)
        // For now, just advance by 1 hour
        const [h, m, s] = currentTime.split(':').map(Number);
        const newH = (h + 1) % 24;
        currentTime = `${String(newH).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }
    
    res.json({ success: true, entries });
});

module.exports = router;
