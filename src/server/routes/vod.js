// akiratv/src/server/routes/vod.js
// JavaScript port of Python routes/vod.py

const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const { getAkiraTV } = require('../app');

const BASE_DIR = path.join(__dirname, '..', '..', '..');

/**
 * Get all VOD content
 */
router.get('/', (req, res) => {
    const collectionsDir = path.join(BASE_DIR, 'user', 'collections');
    
    if (!fs.existsSync(collectionsDir)) {
        return res.json({ collections: [] });
    }
    
    try {
        const files = fs.readdirSync(collectionsDir).filter(f => f.endsWith('.json'));
        const collections = [];
        
        for (const file of files) {
            const filePath = path.join(collectionsDir, file);
            const content = fs.readFileSync(filePath, 'utf-8');
            const data = JSON.parse(content);
            
            if (data.collections) {
                collections.push(...data.collections);
            }
        }
        
        res.json({ collections, total: collections.length });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

/**
 * Get videos in a collection
 */
router.get('/collection/:id', (req, res) => {
    const { id } = req.params;
    const collectionsDir = path.join(BASE_DIR, 'user', 'collections');
    
    if (!fs.existsSync(collectionsDir)) {
        return res.status(404).json({ error: 'Collections directory not found' });
    }
    
    try {
        const files = fs.readdirSync(collectionsDir).filter(f => f.endsWith('.json'));
        
        for (const file of files) {
            const filePath = path.join(collectionsDir, file);
            const content = fs.readFileSync(filePath, 'utf-8');
            const data = JSON.parse(content);
            
            if (data.collections) {
                for (const collection of data.collections) {
                    if (collection.id === id) {
                        return res.json(collection);
                    }
                }
            }
        }
        
        res.status(404).json({ error: `Collection '${id}' not found` });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

/**
 * Search VOD content
 */
router.get('/search', (req, res) => {
    const { q } = req.query;
    
    if (!q) {
        return res.status(400).json({ error: 'Search query required' });
    }
    
    const collectionsDir = path.join(BASE_DIR, 'user', 'collections');
    
    if (!fs.existsSync(collectionsDir)) {
        return res.json({ results: [] });
    }
    
    try {
        const files = fs.readdirSync(collectionsDir).filter(f => f.endsWith('.json'));
        const results = [];
        const query = q.toLowerCase();
        
        for (const file of files) {
            const filePath = path.join(collectionsDir, file);
            const content = fs.readFileSync(filePath, 'utf-8');
            const data = JSON.parse(content);
            
            if (data.collections) {
                for (const collection of data.collections) {
                    const name = (collection.name || '').toLowerCase();
                    if (name.includes(query)) {
                        results.push(collection);
                    }
                }
            }
        }
        
        res.json({ results, total: results.length });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

/**
 * Get video info
 */
router.get('/video/:id', (req, res) => {
    const { id } = req.params;
    const collectionsDir = path.join(BASE_DIR, 'user', 'collections');
    
    if (!fs.existsSync(collectionsDir)) {
        return res.status(404).json({ error: 'Collections not found' });
    }
    
    try {
        const files = fs.readdirSync(collectionsDir).filter(f => f.endsWith('.json'));
        
        for (const file of files) {
            const filePath = path.join(collectionsDir, file);
            const content = fs.readFileSync(filePath, 'utf-8');
            const data = JSON.parse(content);
            
            if (data.collections) {
                for (const collection of data.collections) {
                    if (collection.videos) {
                        for (const video of collection.videos) {
                            if (video.id === id) {
                                return res.json({ ...video, collection: collection.name });
                            }
                        }
                    }
                }
            }
        }
        
        res.status(404).json({ error: `Video '${id}' not found` });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

module.exports = router;
