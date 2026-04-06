#!/usr/bin/env python3
"""
AkiraTV Web UI Launcher
Starts the FastAPI server and opens the web interface
"""
import os
import sys
import time
import webbrowser
import subprocess
from pathlib import Path

def find_free_port(start_port=8000):
    """Find an available port"""
    import socket
    port = start_port
    while port < start_port + 100:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            port += 1
    return start_port

def get_local_ip():
    """Get local IP address"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def main():
    print("=" * 60)
    print("  AkiraTV Web Interface Launcher")
    print("=" * 60)
    print()
    
    # Check if uvicorn is installed
    try:
        import uvicorn
        from fastapi import FastAPI
    except ImportError:
        print("❌ Required packages not installed!")
        print()
        print("Please install dependencies:")
        print("  pip install fastapi uvicorn websockets")
        print()
        sys.exit(1)
    
    # Find project root (current directory, not parent)
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    print(f"Project root: {project_root}")
    print()
    
    # Find available port
    port = find_free_port(8000)
    local_ip = get_local_ip()
    
    print("Starting AkiraTV API Server...")
    print()
    print(f"  Local:   http://127.0.0.1:{port}")
    print(f"  Network: http://{local_ip}:{port}")
    print()
    print("Access from your phone using the Network URL")
    print(f"API Documentation: http://127.0.0.1:{port}/docs")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    print()
    
    # Open browser after 2 seconds
    def open_browser():
        time.sleep(2)
        webbrowser.open(f"http://127.0.0.1:{port}")
    
    import threading
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Start uvicorn server
    try:
        import uvicorn
        uvicorn.run(
            "akiratv.api_server:app",
            host="0.0.0.0",  # Listen on all interfaces for phone access
            port=port,
            log_level="warning",  # Changed from "info" to reduce spam
            access_log=False,  # Disable access logs to reduce spam
            reload=False  # Disable auto-reload to reduce CPU usage
        )
    except KeyboardInterrupt:
        print()
        print("🛑 Server stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()