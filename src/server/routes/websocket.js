// akiratv/src/server/routes/websocket.js
// JavaScript port of Python routes/websocket.py

const WebSocket = require('ws');

let wss = null;
const clients = new Set();

/**
 * Setup WebSocket server
 */
function setupWebSocket(server) {
    wss = new WebSocket.Server({ server, path: '/ws' });
    
    wss.on('connection', (ws) => {
        clients.add(ws);
        console.log('[WS] Client connected. Total clients:', clients.size);
        
        ws.on('message', (message) => {
            try {
                const data = JSON.parse(message);
                handleMessage(ws, data);
            } catch (e) {
                console.error('[WS] Invalid message:', e);
            }
        });
        
        ws.on('close', () => {
            clients.delete(ws);
            console.log('[WS] Client disconnected. Total clients:', clients.size);
        });
        
        ws.on('error', (error) => {
            console.error('[WS] Error:', error);
            clients.delete(ws);
        });
        
        // Send welcome message
        ws.send(JSON.stringify({
            type: 'connected',
            message: 'Welcome to AkiraTV WebSocket'
        }));
    });
    
    console.log('[WS] WebSocket server initialized');
    
    return wss;
}

/**
 * Handle incoming WebSocket messages
 */
function handleMessage(ws, data) {
    switch (data.type) {
        case 'ping':
            ws.send(JSON.stringify({ type: 'pong', timestamp: Date.now() }));
            break;
            
        case 'subscribe':
            // Handle channel subscription
            ws.send(JSON.stringify({
                type: 'subscribed',
                channel: data.channel
            }));
            break;
            
        default:
            console.log('[WS] Unknown message type:', data.type);
    }
}

/**
 * Broadcast message to all connected clients
 */
function broadcast(message) {
    const data = JSON.stringify(message);
    clients.forEach((client) => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(data);
        }
    });
}

/**
 * Broadcast stats update
 */
function broadcastStats(stats) {
    broadcast({
        type: 'stats',
        data: stats
    });
}

/**
 * WebSocket endpoint handler for Express
 */
function websocketHandler(req, res) {
    res.status(400).json({ error: 'WebSocket not supported via HTTP. Use ws:// protocol instead.' });
}

module.exports = { setupWebSocket, broadcast, broadcastStats, websocketHandler };
