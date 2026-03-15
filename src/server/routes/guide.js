// akiratv/src/server/routes/guide.js
// JavaScript port of Python routes/guide.py

const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const { getAkiraTV } = require('../app');
const { getCurrentScheduleForChannel, SCHEDULE_DIR } = require('../../scheduler/scheduler');

const BASE_DIR = path.join(__dirname, '..', '..', '..');

/**
 * Convert time string to minutes since midnight
 */
function timeToMinutes(timeStr) {
    try {
        const parts = timeStr.split(':');
        const hours = parseInt(parts[0], 10);
        const minutes = parseInt(parts[1], 10);
        return hours * 60 + minutes;
    } catch {
        return 0;
    }
}

/**
 * Get schedule for a specific date
 */
function getScheduleForDate(scheduleData, dateStr, dayName) {
    // First, try calendar section
    const calendarKey = `${dateStr}_${dayName}`;
    const calendarEntry = scheduleData.calendar?.[calendarKey];
    if (calendarEntry?.entries) {
        return calendarEntry.entries;
    }
    
    // Fall back to weekly section
    const weeklyEntries = scheduleData.weekly?.[dayName] || [];
    if (weeklyEntries.length > 0) {
        return weeklyEntries;
    }
    
    return [];
}

/**
 * Get current guide for all channels
 */
router.get('/current', async (req, res) => {
    const akiraTV = getAkiraTV();
    if (!akiraTV || !akiraTV.config) {
        return res.status(500).json({ error: 'AkiraTV not initialized' });
    }
    
    const channelsConfig = akiraTV.config.data.channels || {};
    const guide = {};
    
    for (const channelName of Object.keys(channelsConfig)) {
        try {
            const schedule = await getCurrentScheduleForChannel(channelName);
            if (schedule && schedule.length > 0) {
                guide[channelName] = schedule;
            }
        } catch (e) {
            console.error(`Error getting schedule for ${channelName}:`, e);
        }
    }
    
    res.json(guide);
});

/**
 * Get current guide for a specific channel
 */
router.get('/current/:channel', async (req, res) => {
    const { channel } = req.params;
    
    try {
        const schedule = await getCurrentScheduleForChannel(channel);
        res.json({ channel, schedule });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

/**
 * Get weekly guide
 */
router.get('/weekly', async (req, res) => {
    const akiraTV = getAkiraTV();
    if (!akiraTV || !akiraTV.config) {
        return res.status(500).json({ error: 'AkiraTV not initialized' });
    }
    
    const scheduleFile = path.join(SCHEDULE_DIR, 'schedule.json');
    
    if (!fs.existsSync(scheduleFile)) {
        return res.json({ weekly: {} });
    }
    
    try {
        const data = JSON.parse(fs.readFileSync(scheduleFile, 'utf-8'));
        res.json({ weekly: data.weekly || {} });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

/**
 * Get guide for a specific date
 */
router.get('/date/:date', async (req, res) => {
    const { date } = req.params; // YYYY-MM-DD format
    const dayName = new Date(date).toLocaleDateString('en-US', { weekday: 'long' }).toLowerCase();
    
    const scheduleFile = path.join(SCHEDULE_DIR, 'schedule.json');
    
    if (!fs.existsSync(scheduleFile)) {
        return res.json({ date, day: dayName, entries: [] });
    }
    
    try {
        const data = JSON.parse(fs.readFileSync(scheduleFile, 'utf-8'));
        const entries = getScheduleForDate(data, date, dayName);
        res.json({ date, day: dayName, entries });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

/**
 * Get guide for a specific channel and date
 */
router.get('/:channel/:date', async (req, res) => {
    const { channel, date } = req.params;
    const dayName = new Date(date).toLocaleDateString('en-US', { weekday: 'long' }).toLowerCase();
    
    let scheduleFile = path.join(SCHEDULE_DIR, `schedule_${channel}.json`);
    if (!fs.existsSync(scheduleFile)) {
        scheduleFile = path.join(SCHEDULE_DIR, 'schedule.json');
    }
    
    if (!fs.existsSync(scheduleFile)) {
        return res.json({ channel, date, day: dayName, entries: [] });
    }
    
    try {
        const data = JSON.parse(fs.readFileSync(scheduleFile, 'utf-8'));
        const entries = getScheduleForDate(data, date, dayName);
        res.json({ channel, date, day: dayName, entries });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

module.exports = router;
