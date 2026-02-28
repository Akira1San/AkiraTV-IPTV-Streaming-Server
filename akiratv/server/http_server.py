# akiratv/server/http_server.py
import os
import asyncio
from pathlib import Path
from aiohttp import web, hdrs
from ..stats import AKIRATV_STATS, STATS_LOCK

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
        self._logged_missing_channels = set()  # Track channels we've already logged

    async def hls_handler(self, request):
        """Serve HLS files with proper headers and retry logic for permission errors."""
        path = request.match_info['path']
        
        # === VIEWER TRACKING ===
        # Extract channel name from path (e.g., "akiratv/index.m3u8" -> "akiratv")
        parts = path.split('/')
        channel_name = parts[0] if parts else "unknown"
        
        # Get client IP (handle reverse proxies)
        client_ip = request.remote
        if 'X-Forwarded-For' in request.headers:
            # Take first IP if multiple (original client)
            forwarded = request.headers['X-Forwarded-For']
            client_ip = forwarded.split(',')[0].strip()
        
        # Record this view
        from ..viewer_tracker import viewer_tracker
        viewer_tracker.record_view(channel_name, client_ip or "unknown")
        # === END VIEWER TRACKING ===
        
        # Resolve storage path
        storage = self.stats.get("config", {}).get("storage", {})
        if not storage:
            storage = self.config.data.get("storage", {})
        if not storage:
            print(f"[HLS] No storage config found, using defaults")
        
        if storage.get("type") == "ram":
            base_path = Path(storage.get("ram_path", "./output"))
        else:
            base_path = Path(storage.get("disk_path", "./output"))
        
        file_path = base_path / path
        
        if not file_path.exists():
            # Only log once per channel to avoid spam
            if channel_name not in self._logged_missing_channels:
                self._logged_missing_channels.add(channel_name)
                print(f"[HLS] File not found: {file_path}")
            raise web.HTTPNotFound()
        
        max_retries = 20 # max_retries = 5
        for i in range(max_retries):
            try:
                # Special handling for .ts segments being written by FFmpeg
                if file_path.suffix == '.ts':
                    try:
                        if file_path.stat().st_size == 0:
                            print(f"[HLS] {file_path.name} size=0 (retry {i+1}/{max_retries})")
                            await asyncio.sleep(0.5)
                            continue  # Skip to next retry
                    except FileNotFoundError:
                        print(f"[HLS] File vanished during check: {file_path}")
                        raise web.HTTPNotFound()
                
                # Attempt to read file
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                response = web.Response(body=content)
                response.headers[hdrs.ACCESS_CONTROL_ALLOW_ORIGIN] = '*'
                response.headers[hdrs.CACHE_CONTROL] = 'no-cache, no-store, must-revalidate'
                return response
                
            except PermissionError:
                if i < max_retries - 1:
                    print(f"[HLS] Perm denied on {file_path.name} (retry {i+1}/{max_retries})")
                    await asyncio.sleep(0.5)
                else:
                    print(f"[HLS] Max retries exhausted (PermissionError): {file_path.name}")
                    return web.Response(status=503, text="Service temporarily unavailable")
            except Exception as e:
                print(f"[HLS] Unexpected error serving {file_path}: {type(e).__name__}: {e}")
                raise
        
        # CRITICAL FIX: Handle exhausted retries (e.g., .ts file remained size=0)
        print(f"[HLS] Max retries exhausted (size=0 or other): {file_path.name}")
        return web.Response(status=503, text="Service temporarily unavailable")

    async def root_handler(self, request):
        """Simple root handler - redirect to FastAPI UI or return basic info."""
        return web.Response(
            text="AkiraTV HLS Server - Access the web UI via FastAPI (default port 8000)",
            content_type='text/plain'
        )

    async def static_file_handler(self, request):
        """Serve static files like xmltv.xml and channels.m3u"""
        # Security: Prevent path traversal attacks
        if ".." in request.path:
            raise web.HTTPBadRequest(text="Invalid path")
        
        storage = self.stats.get("config", {}).get("storage", {})
        if storage.get("type") == "ram":
            base_path = Path(storage.get("ram_path", "./output"))
        else:
            base_path = Path(storage.get("disk_path", "./output"))
            
        file_path = base_path / request.path.lstrip("/")
        
        if not file_path.exists():
            # Only log once per path to avoid spam
            path_key = f"static:{file_path}"
            if path_key not in self._logged_missing_channels:
                self._logged_missing_channels.add(path_key)
                print(f"[STATIC] File not found: {file_path}")
            raise web.HTTPNotFound()
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
        except Exception as e:
            print(f"[STATIC] Error reading {file_path}: {e}")
            raise web.HTTPInternalServerError()
            
        content_type = "application/xml" if file_path.suffix == ".xml" else "application/x-mpegURL"

        response = web.Response(body=content, content_type=content_type)
        response.headers[hdrs.ACCESS_CONTROL_ALLOW_ORIGIN] = '*'
            
        return response

    def setup_routes(self):
        """Setup all routes for the HTTP server."""
        self.app.router.add_get('/hls/{path:.+}', self.hls_handler)
        self.app.router.add_get('/xmltv.xml', self.static_file_handler)
        self.app.router.add_get('/channels.m3u', self.static_file_handler)
        self.app.router.add_get('/channels/{channel_name}/{filename}', self.channel_assets_handler)

        # --- CHANGE IS HERE (Corrected Path) ---
        # Calculate path to the root project folder
        # We are in: akiratv/server/http_server.py
        # parent = akiratv/server
        # parent.parent = akiratv
        # parent.parent.parent = "AkiraTV_NEW - zai - git - core api" (The root)
        
        project_root = Path(__file__).parent.parent.parent.resolve()
        user_dir = project_root / "user"
        
        if user_dir.exists():
            # This maps http://server/user/... to the physical folder
            self.app.router.add_static('/user', user_dir, name='user_assets')
            print(f"[DIR] Serving user assets from: {user_dir}")
        else:
            print(f"[ERROR] User directory not found at: {user_dir}")
        # ------------------------------

        # The root handler as fallback
        self.app.router.add_get('/{path:.*}', self.root_handler)

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
        
        print(f"[TV] Stream URL: http://{bind}:{port}/hls/ (e.g., /hls/channel1/index.m3u8)")

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

    def stop(self):
        """Stop the HTTP server."""
        if self.thread and self.thread.is_alive():
            # Run the async stop method in the event loop
            asyncio.run(self.stop_async())

    async def channel_assets_handler(self, request):
        """Serve channel-specific files like logos."""
        channel_name = request.match_info['channel_name']
        filename = request.match_info['filename']
        
        # Resolve storage path
        storage = self.stats.get("config", {}).get("storage", {})
        if storage.get("type") == "ram":
            base_path = Path(storage.get("ram_path", "./output"))
        else:
            base_path = Path(storage.get("disk_path", "./output"))
            
        file_path = base_path / "channels" / channel_name / filename
        
        if not file_path.exists():
            # Only log once per asset to avoid spam
            asset_key = f"asset:{channel_name}:{filename}"
            if asset_key not in self._logged_missing_channels:
                self._logged_missing_channels.add(asset_key)
                print(f"[ASSET] File not found: {file_path}")
            raise web.HTTPNotFound(text=f"Channel asset not found: {file_path}")
        
        # Permission retry logic
        max_retries = 3
        content = None
        for i in range(max_retries):
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                break
            except PermissionError:
                if i == max_retries - 1:
                    print(f"[ASSET] Max retries exhausted: {file_path}")
                    return web.Response(status=503, text="Service temporarily unavailable")
                await asyncio.sleep(0.1)
        
        # Determine content type
        ext = filename.split('.')[-1].lower()
        content_type = f"image/{ext}" if ext in ('png', 'jpg', 'jpeg', 'gif') else 'application/octet-stream'
        
        response = web.Response(body=content, content_type=content_type)
        response.headers[hdrs.ACCESS_CONTROL_ALLOW_ORIGIN] = '*'
        return response