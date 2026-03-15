// akiratv/src/server/routes/playlist.js
// JavaScript port of Python routes/playlist.py

const express = require('express');
const router = express.Router();
const { getAkiraTV } = require('../app');

/**
 * Get M3U playlist for a channel
 */
router.get('/m3u/:channel', (req, res) => {
    const { channel } = req.params;
    const akiraTV = getAkiraTV();
    
    if (!akiraTV || !akiraTV.config) {
        return res.status(500).json({ error: 'AkiraTV not initialized' });
    }
    
    const config = akiraTV.config.data;
    const port = config.output?.http?.port || 8081;
    
    const playlist = `#EXTM3U
#EXTINF:-1 tvg-name="${channel}" group-title="AkiraTV",${channel}
http://localhost:${port}/hls/${channel}/index.m3u8
`;
    
    res.type('application/vnd.apple.mpegurl');
    res.send(playlist);
});

/**
 * Get all channel playlists
 */
router.get('/m3u', (req, res) => {
    const akiraTV = getAkiraTV();
    
    if (!akiraTV || !akiraTV.config) {
        return res.status(500).json({ error: 'AkiraTV not initialized' });
    }
    
    const config = akiraTV.config.data;
    const port = config.output?.http?.port || 8081;
    const channels = config.channels || {};
    
    let playlist = '#EXTM3U\n';
    
    for (const [channelName, channelConf] of Object.entries(channels)) {
        if (!channelConf.enabled) continue;
        
        playlist += `#EXTINF:-1 tvg-name="${channelName}" group-title="AkiraTV",${channelName}\n`;
        playlist += `http://localhost:${port}/hls/${channelName}/index.m3u8\n`;
    }
    
    res.type('application/vnd.apple.mpegurl');
    res.send(playlist);
});

module.exports = router;
