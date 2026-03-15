// akiratv/src/server/routes/channels.js
// JavaScript port of Python routes/channels.py

const express = require('express');
const router = express.Router();
const os = require('os');
const { getAkiraTV } = require('../app');

/**
 * Get local IP address
 */
function getLocalIP() {
    const interfaces = os.networkInterfaces();
    for (const name of Object.keys(interfaces)) {
        for (const iface of interfaces[name]) {
            if (iface.family === 'IPv4' && !iface.internal) {
                return iface.address;
            }
        }
    }
    return '127.0.0.1';
}

/**
 * Get all channels
 */
router.get('/', (req, res) => {
    const akiraTV = getAkiraTV();
    if (!akiraTV || !akiraTV.config) {
        return res.status(500).json({ error: 'AkiraTV not initialized' });
    }
    
    const channelsConfig = akiraTV.config.data.channels || {};
    const channels = Object.entries(channelsConfig).map(([name, config]) => ({
        name,
        ...config
    }));
    
    res.json({
        channels,
        total: channels.length
    });
});

/**
 * Add a new channel
 */
router.post('/', (req, res) => {
    const { channel_name, channel_type = 'linear' } = req.body;
    
    if (!channel_name) {
        return res.status(400).json({ success: false, error: 'channel_name is required' });
    }
    
    const akiraTV = getAkiraTV();
    if (!akiraTV || !akiraTV.config) {
        return res.status(500).json({ success: false, error: 'AkiraTV not initialized' });
    }
    
    // Add channel to config
    if (!akiraTV.config.data.channels) {
        akiraTV.config.data.channels = {};
    }
    
    akiraTV.config.data.channels[channel_name] = {
        enabled: true,
        type: channel_type
    };
    
    akiraTV.config.save();
    
    res.json({ success: true, message: `Channel '${channel_name}' added` });
});

/**
 * Get streaming URLs for all enabled channels
 */
router.get('/urls', (req, res) => {
    const akiraTV = getAkiraTV();
    if (!akiraTV || !akiraTV.config) {
        return res.status(500).json({ error: 'AkiraTV not initialized' });
    }
    
    const config = akiraTV.config.data;
    const httpConf = config.output?.http || {};
    const port = httpConf.port || 8081;
    const localIP = getLocalIP();
    
    const channelsConfig = config.channels || {};
    const urls = {};
    
    for (const [channelName, channelConf] of Object.entries(channelsConfig)) {
        if (!channelConf.enabled) continue;
        
        urls[channelName] = {
            lan: `http://${localIP}:${port}/hls/${channelName}/index.m3u8`,
            localhost: `http://localhost:${port}/hls/${channelName}/index.m3u8`,
            type: channelConf.type
        };
    }
    
    res.json({ urls });
});

/**
 * Get a specific channel
 */
router.get('/:channel', (req, res) => {
    const { channel } = req.params;
    
    const akiraTV = getAkiraTV();
    if (!akiraTV || !akiraTV.config) {
        return res.status(500).json({ error: 'AkiraTV not initialized' });
    }
    
    const channelsConfig = akiraTV.config.data.channels || {};
    const channelConfig = channelsConfig[channel];
    
    if (!channelConfig) {
        return res.status(404).json({ error: `Channel '${channel}' not found` });
    }
    
    res.json({
        name: channel,
        ...channelConfig
    });
});

/**
 * Update a channel
 */
router.put('/:channel', (req, res) => {
    const { channel } = req.params;
    const { enabled, type } = req.body;
    
    const akiraTV = getAkiraTV();
    if (!akiraTV || !akiraTV.config) {
        return res.status(500).json({ success: false, error: 'AkiraTV not initialized' });
    }
    
    const channelsConfig = akiraTV.config.data.channels || {};
    if (!channelsConfig[channel]) {
        return res.status(404).json({ success: false, error: `Channel '${channel}' not found` });
    }
    
    if (enabled !== undefined) {
        channelsConfig[channel].enabled = enabled;
    }
    if (type !== undefined) {
        channelsConfig[channel].type = type;
    }
    
    akiraTV.config.save();
    
    res.json({ success: true, message: `Channel '${channel}' updated` });
});

/**
 * Delete a channel
 */
router.delete('/:channel', (req, res) => {
    const { channel } = req.params;
    
    const akiraTV = getAkiraTV();
    if (!akiraTV || !akiraTV.config) {
        return res.status(500).json({ success: false, error: 'AkiraTV not initialized' });
    }
    
    const channelsConfig = akiraTV.config.data.channels || {};
    if (!channelsConfig[channel]) {
        return res.status(404).json({ success: false, error: `Channel '${channel}' not found` });
    }
    
    delete channelsConfig[channel];
    akiraTV.config.save();
    
    res.json({ success: true, message: `Channel '${channel}' deleted` });
});

/**
 * Get channel status
 */
router.get('/:channel/status', (req, res) => {
    const { channel } = req.params;
    
    const akiraTV = getAkiraTV();
    if (!akiraTV) {
        return res.status(500).json({ error: 'AkiraTV not initialized' });
    }
    
    const status = akiraTV.getChannelStatus(channel);
    res.json(status);
});

/**
 * Send play_now command to a channel
 */
router.post('/:channel/play', (req, res) => {
    const { channel } = req.params;
    const { video_path, start_position = 0 } = req.body;
    
    if (!video_path) {
        return res.status(400).json({ success: false, error: 'video_path is required' });
    }
    
    const akiraTV = getAkiraTV();
    if (!akiraTV) {
        return res.status(500).json({ success: false, error: 'AkiraTV not initialized' });
    }
    
    akiraTV.enqueuePlayNow(channel, video_path, start_position);
    
    res.json({ success: true, message: `Play command sent to channel '${channel}'` });
});

module.exports = router;
