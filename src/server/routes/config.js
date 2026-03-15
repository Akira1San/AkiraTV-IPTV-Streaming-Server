// akiratv/src/server/routes/config.js
// JavaScript port of Python routes/config.py

const express = require('express');
const router = express.Router();
const { getAkiraTV } = require('../app');
const fs = require('fs');
const path = require('path');

const BASE_DIR = path.join(__dirname, '..', '..', '..');

/**
 * Get current configuration
 */
router.get('/', (req, res) => {
    const akiraTV = getAkiraTV();
    if (!akiraTV || !akiraTV.config) {
        return res.status(500).json({ error: 'AkiraTV not initialized' });
    }
    
    res.json(akiraTV.config.data);
});

/**
 * Update configuration
 */
router.put('/', (req, res) => {
    const akiraTV = getAkiraTV();
    if (!akiraTV || !akiraTV.config) {
        return res.status(500).json({ success: false, error: 'AkiraTV not initialized' });
    }
    
    const updates = req.body;
    
    // Merge updates with existing config
    Object.keys(updates).forEach(key => {
        akiraTV.config.data[key] = updates[key];
    });
    
    akiraTV.config.save();
    
    res.json({ success: true, message: 'Configuration updated' });
});

/**
 * Fix video paths (for Windows to Android migration)
 */
router.post('/fix-paths', async (req, res) => {
    const { oldPrefix, newPrefix } = req.body;
    
    if (!oldPrefix || !newPrefix) {
        return res.status(400).json({ success: false, error: 'oldPrefix and newPrefix are required' });
    }
    
    const collectionsDir = path.join(BASE_DIR, 'user', 'collections');
    
    if (!fs.existsSync(collectionsDir)) {
        return res.json({ success: true, fixed: 0 });
    }
    
    let fixedCount = 0;
    
    try {
        const files = fs.readdirSync(collectionsDir).filter(f => f.endsWith('.json'));
        
        for (const file of files) {
            const filePath = path.join(collectionsDir, file);
            const content = fs.readFileSync(filePath, 'utf-8');
            let data = JSON.parse(content);
            
            let modified = false;
            
            if (data.paths && Array.isArray(data.paths)) {
                data.paths = data.paths.map(p => {
                    if (p.startsWith(oldPrefix)) {
                        modified = true;
                        return p.replace(oldPrefix, newPrefix);
                    }
                    return p;
                });
            }
            
            if (data.collections && Array.isArray(data.collections)) {
                for (const collection of data.collections) {
                    if (collection.paths && Array.isArray(collection.paths)) {
                        collection.paths = collection.paths.map(p => {
                            if (p.startsWith(oldPrefix)) {
                                modified = true;
                                return p.replace(oldPrefix, newPrefix);
                            }
                            return p;
                        });
                    }
                }
            }
            
            if (modified) {
                fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf-8');
                fixedCount++;
            }
        }
        
        res.json({ success: true, fixed: fixedCount });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

/**
 * Get a specific config section
 */
router.get('/:section', (req, res) => {
    const { section } = req.params;
    
    const akiraTV = getAkiraTV();
    if (!akiraTV || !akiraTV.config) {
        return res.status(500).json({ error: 'AkiraTV not initialized' });
    }
    
    const sectionData = akiraTV.config.data[section];
    if (!sectionData) {
        return res.status(404).json({ error: `Section '${section}' not found` });
    }
    
    res.json(sectionData);
});

module.exports = router;
