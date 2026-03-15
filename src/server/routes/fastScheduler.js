// akiratv/src/server/routes/fastScheduler.js
// JavaScript port of Python routes/fast_scheduler.py

const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');

const BASE_DIR = path.join(__dirname, '..', '..', '..');
const FAST_SCHEDULES_DIR = path.join(BASE_DIR, 'user', 'fast_schedules');

// Ensure directory exists
if (!fs.existsSync(FAST_SCHEDULES_DIR)) {
    fs.mkdirSync(FAST_SCHEDULES_DIR, { recursive: true });
}

/**
 * Get all fast schedules
 */
router.get('/', (req, res) => {
    if (!fs.existsSync(FAST_SCHEDULES_DIR)) {
        return res.json({ schedules: [] });
    }
    
    try {
        const files = fs.readdirSync(FAST_SCHEDULES_DIR).filter(f => f.endsWith('.json'));
        const schedules = [];
        
        for (const file of files) {
            const filePath = path.join(FAST_SCHEDULES_DIR, file);
            const content = fs.readFileSync(filePath, 'utf-8');
            const data = JSON.parse(content);
            schedules.push(data);
        }
        
        res.json({ schedules, total: schedules.length });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

/**
 * Get a specific fast schedule
 */
router.get('/:name', (req, res) => {
    const { name } = req.params;
    const filePath = path.join(FAST_SCHEDULES_DIR, `fast_schedule_${name}.json`);
    
    if (!fs.existsSync(filePath)) {
        return res.status(404).json({ error: `Fast schedule '${name}' not found` });
    }
    
    try {
        const content = fs.readFileSync(filePath, 'utf-8');
        const data = JSON.parse(content);
        res.json(data);
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

/**
 * Create or update a fast schedule
 */
router.post('/', (req, res) => {
    const { name, entries } = req.body;
    
    if (!name) {
        return res.status(400).json({ success: false, error: 'name is required' });
    }
    
    if (!entries || !Array.isArray(entries)) {
        return res.status(400).json({ success: false, error: 'entries array is required' });
    }
    
    const filePath = path.join(FAST_SCHEDULES_DIR, `fast_schedule_${name}.json`);
    const data = { name, entries, updated: new Date().toISOString() };
    
    try {
        fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf-8');
        res.json({ success: true, message: `Fast schedule '${name}' saved` });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

/**
 * Delete a fast schedule
 */
router.delete('/:name', (req, res) => {
    const { name } = req.params;
    const filePath = path.join(FAST_SCHEDULES_DIR, `fast_schedule_${name}.json`);
    
    if (!fs.existsSync(filePath)) {
        return res.status(404).json({ success: false, error: `Fast schedule '${name}' not found` });
    }
    
    try {
        fs.unlinkSync(filePath);
        res.json({ success: true, message: `Fast schedule '${name}' deleted` });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

module.exports = router;
