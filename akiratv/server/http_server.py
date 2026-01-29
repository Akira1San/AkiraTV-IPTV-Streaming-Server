# akiratv/http_server.py
import os
import asyncio
from pathlib import Path
from aiohttp import web, hdrs
from .dashboard import generate_dashboard_html
from ..stats import AKIRATV_STATS, STATS_LOCK

# === Ngrok for public sharing ===
try:
    from pyngrok import ngrok
    NGROK_AVAILABLE = True
except ImportError:
    NGROK_AVAILABLE = False

class HttpServer:
    def __init__(self, config, stats, stats_lock):
        self.config = config
        self.stats = stats
        self.stats_lock = stats_lock
        self.app = None
        self.runner = None
        self.site = None
        self.public_url = None
        self.thread = None

    async def hls_handler(self, request):
        """Serve HLS files with proper headers and retry logic for permission errors."""
        path = request.match_info['path']
        
        # Try to get config from stats first, then fall back to self.config
        storage = self.stats.get("config", {}).get("storage", {})
        
        if not storage:
            # Fallback to config.data
            storage = self.config.data.get("storage", {})
            print(f"[DEBUG] Using config.data for storage: {storage}")
        
        if not storage:
            print(f"[DEBUG] No storage config found, using defaults")
        
        if storage.get("type") == "ram":
            ram_path = storage.get("ram_path", "R:/akiratv")
            #print(f"[DEBUG] RAM storage base path: {ram_path}")
            base_path = Path(ram_path)
        else:
            disk_path = storage.get("disk_path", "./output")
            print(f"[DEBUG] Disk storage base path: {disk_path}")
            base_path = Path(disk_path)
        
        file_path = base_path / path
        #print(f"[DEBUG] Serving HLS file: {file_path}")
        
        if not file_path.exists():
            print(f"[DEBUG] File not found: {file_path}")
            raise web.HTTPNotFound()
        
        # --- RETRY LOGIC FOR PERMISSION ERROR ---
        max_retries = 5  # Increased from 3 to 5
        for i in range(max_retries):
            try:
                # Check if file is being written to by FFmpeg
                if file_path.suffix == '.ts' and file_path.stat().st_size == 0:
                    await asyncio.sleep(0.5)
                    continue
                
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                response = web.Response(body=content)
                response.headers[hdrs.ACCESS_CONTROL_ALLOW_ORIGIN] = '*'
                response.headers[hdrs.CACHE_CONTROL] = 'no-cache, no-store, must-revalidate'
                response.headers["ngrok-skip-browser-warning"] = "true"
                return response
            except PermissionError:
                if i < max_retries - 1:
                    print(f"Permission denied on {file_path}, retrying in 0.5s...")
                    await asyncio.sleep(0.5)
                else:
                    # Instead of raising an error, return a 503 Service Unavailable
                    return web.Response(status=503, text="Service temporarily unavailable")
            except Exception as e:
                print(f"Error serving {file_path}: {e}")
                raise

    async def dashboard_handler(self, request):
        html = generate_dashboard_html()
        response = web.Response(text=html, content_type='text/html')
        response.headers["ngrok-skip-browser-warning"] = "true"
        return response

    async def static_file_handler(self, request):
        """Serve static files like xmltv.xml and channels.m3u"""
        storage = self.stats.get("config", {}).get("storage", {})
        if storage.get("type") == "ram":
            base_path = Path(storage.get("ram_path", "R:/akiratv"))
        else:
            base_path = Path(storage.get("disk_path", "./output"))
            
        file_path = base_path / request.path.lstrip("/")
        if not file_path.exists():
            raise web.HTTPNotFound()
            
        with open(file_path, 'rb') as f:
            content = f.read()
            
        content_type = "application/xml" if file_path.suffix == ".xml" else "application/x-mpegURL"

        response.headers["ngrok-skip-browser-warning"] = "true"
            
        return web.Response(body=content, content_type=content_type)

    def setup_routes(self):
        """Setup all routes for the HTTP server."""
        self.app.router.add_get('/hls/{path:.+}', self.hls_handler)
        self.app.router.add_get('/xmltv.xml', self.static_file_handler)
        self.app.router.add_get('/channels.m3u', self.static_file_handler)
        self.app.router.add_get('/channels/{channel_name}/{filename}', self.channel_assets_handler)
        self.app.router.add_get('/{path:.*}', self.dashboard_handler)  # Dashboard last

    async def start_async(self, directory: str, port: int, bind: str = "127.0.0.1"):
        """Start aiohttp server asynchronously."""
        self.app = web.Application()
        self.setup_routes()
        
        # Store config in global stats for handler access
        with self.stats_lock:
            self.stats["config"] = self.config.data
        
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, bind, port)
        await self.site.start()
        
        print(f"📺 Stream URL: http://{bind}:{port}/hls/ (e.g., /hls/channel1/index.m3u8)")
        
        # Start Ngrok tunnel (if available)
        if NGROK_AVAILABLE:
            try:
                self.public_url = ngrok.connect(port, "http")
                print(f"🌍 Public Stream URL: {self.public_url}/hls/critters/index.m3u8")
                print(f"📤 Share M3U: {self.public_url}/channels.m3u")
                return self.public_url
            except Exception as e:
                print(f"⚠️ Ngrok not available: {e}")
                return None
        return None

    def start(self, directory: str, port: int, bind: str = "127.0.0.1"):
        """Start aiohttp server in a thread."""
        import threading
        
        async def run_server():
            await self.start_async(directory, port, bind)
            # Keep the server running
            while True:
                await asyncio.sleep(1)
        
        self.thread = threading.Thread(
            target=lambda: asyncio.run(run_server()),
            daemon=True
        )
        self.thread.start()
        # Give the server a moment to start
        import time
        time.sleep(0.5)

    async def stop_async(self):
        """Stop the HTTP server asynchronously."""
        if self.runner:
            await self.runner.cleanup()
        
        # Stop Ngrok tunnel
        if NGROK_AVAILABLE and self.public_url:
            try:
                ngrok.disconnect(self.public_url)
                ngrok.kill()
            except Exception as e:
                print(f"Ngrok cleanup failed: {e}")

    def stop(self):
        """Stop the HTTP server."""
        if self.thread and self.thread.is_alive():
            # Run the async stop method in the event loop
            asyncio.run(self.stop_async())

    async def channel_assets_handler(self, request):
        """Serve channel-specific files like logos."""
        channel_name = request.match_info['channel_name']
        filename = request.match_info['filename']
        
        # Determine the base storage path
        storage = self.stats.get("config", {}).get("storage", {})
        if storage.get("type") == "ram":
            base_path = Path(storage.get("ram_path", "R:/akiratv"))
        else:
            base_path = Path(storage.get("disk_path", "./output"))
            
        # Construct the full path to the file
        file_path = base_path / "channels" / channel_name / filename
        
        if not file_path.exists():
            raise web.HTTPNotFound(text=f"Channel asset not found: {file_path}")
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Determine content type
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                content_type = f"image/{filename.split('.')[-1].lower()}"
            else:
                content_type = 'application/octet-stream' # Generic binary type

            return web.Response(body=content, content_type=content_type)
        except Exception as e:
            print(f"Error serving channel asset {file_path}: {e}")
            raise web.HTTPInternalServerError()