"""
WebSocket routes for AkiraTV API
Handles real-time updates and event broadcasting
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Any

# WebSocket connections for live updates
active_connections: List[WebSocket] = []

async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send minimal initial status (no API calls)
        await websocket.send_json({
            "type": "connected",
            "status": {
                "server": "running"
            }
        })
        
        # Keep connection alive by waiting for disconnect
        # No automatic updates - only manual API calls
        while True:
            try:
                await websocket.receive_text()  # Wait for any message
            except WebSocketDisconnect:
                break
            
    except WebSocketDisconnect:
        pass
    finally:
        # Clean up connection
        if websocket in active_connections:
            active_connections.remove(websocket)

async def broadcast_event(event: Dict[str, Any]):
    """Broadcast event to all connected WebSocket clients"""
    dead_connections = []
    for connection in active_connections:
        try:
            await connection.send_json(event)
        except:
            dead_connections.append(connection)
    
    # Clean up dead connections
    for connection in dead_connections:
        active_connections.remove(connection)
