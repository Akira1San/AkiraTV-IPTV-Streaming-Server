# akiratv/dashboard.py
import json
from pathlib import Path
from ..stats import AKIRATV_STATS, STATS_LOCK, get_active_viewers

# Get the directory where this script (dashboard.py) is located
SCRIPT_DIR = Path(__file__).parent.parent.resolve()
# Correctly point to the collections file in the user/collections directory
COLLECTIONS_FILE = SCRIPT_DIR.parent / "user" / "collections" / "collections_akiratv.json"
COVERS_FOLDER = SCRIPT_DIR.parent / "user" / "covers"

def load_collections_covers():
    """
    Load a mapping: video path → cover URL (for <select data-cover>)
    Uses collections JSON, normalizes names for fallback matching.
    """
    mapping = {}
    
    print(f"\n--- COLLECTIONS DEBUG: Starting process ---")
    print(f"Looking for collections file at: {COLLECTIONS_FILE}")
    print(f"File exists? {COLLECTIONS_FILE.exists()}")

    if COLLECTIONS_FILE.exists():
        try:
            data = json.load(COLLECTIONS_FILE.open("r", encoding="utf-8"))
            print(f"Successfully loaded JSON. Top-level keys: {list(data.keys())}")
            
            collections_list = data.get("collections", [])
            print(f"Found {len(collections_list)} collections.")

            for i, col in enumerate(collections_list):
                print(f"\n--- Processing Collection #{i+1} ---")
                
                cover_path = col.get("cover") # Use .get() without a default
                print(f"Raw cover path from JSON: '{cover_path}'")
                
                # --- FIX: Check if cover_path is a valid string before proceeding ---
                if not cover_path or not isinstance(cover_path, str):
                    print("No valid cover path provided, skipping cover for this collection.")
                    cover_url = "" # Set to empty string
                else:
                    # The cover_path in the JSON is like "user/covers/filename.jpg"
                    # Extract just the filename and use COVERS_FOLDER which already points to user/covers
                    cover_filename = Path(cover_path).name
                    absolute_cover_path = COVERS_FOLDER / cover_filename
                    
                    print(f"Resolved absolute cover path: {absolute_cover_path}")
                    print(f"File exists on disk? {absolute_cover_path.exists()}")
                    
                    if absolute_cover_path.exists():
                        cover_name = absolute_cover_path.name
                        # Generate the URL without the 'user/' prefix
                        cover_url = f"/covers/{cover_name}"
                        print(f"Generated cover URL: '{cover_url}'")
                    else:
                        cover_url = ""
                        print("Cover file not found on disk, using empty URL.")

                # Now, map the videos for this collection (whether a cover was found or not)
                for vid in col.get("videos", []):
                    vid_path = Path(vid["path"]).as_posix()
                    print(f"  -> Mapping video: '{vid_path}' to URL: '{cover_url}'")
                    mapping[vid_path] = cover_url
                    # normalized fallback mapping
                    vid_norm = Path(vid_path).stem.lower().replace(".", "_").replace(" ", "_")
                    if vid_norm not in mapping:
                        print(f"  -> Also mapping normalized name: '{vid_norm}' to URL: '{cover_url}'")
                        mapping[vid_norm] = cover_url
        except Exception as e:
            print(f"ERROR: Failed to process collections file: {e}")
    else:
        print("ERROR: Collections file does not exist.")
        
    print(f"\n--- COLLECTIONS DEBUG: Final Mapping ---")
    import pprint
    pprint.pprint(mapping)
    print("---------------------------------------\n")
    
    return mapping

def generate_dashboard_html():
    """Generate dashboard HTML with thumbnails."""
    with STATS_LOCK:
        stats = AKIRATV_STATS.copy()
        urls = stats.get("urls", [])
        if not urls:
            port = stats.get("output", {}).get("http", {}).get("port", 8081)
            bind = "127.0.0.1"
            channels_list = stats.get("channels_list", ["live"])
            urls = [f"http://{bind}:{port}/hls/{ch}/index.m3u8" for ch in channels_list]

    viewers = get_active_viewers()
    covers_map = load_collections_covers()

    # print("\n--- DASHBOARD DEBUG: Cover Map ---")
    # import pprint
    # pprint.pprint(covers_map)
    # print("---------------------------------\n")

    videos = []
    live_playlist = Path("playlists/live.m3u")
    if live_playlist.exists():
        with open(live_playlist, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.endswith((".mp4", ".mkv", ".avi", ".mov")):
                    vid_path = Path(line).as_posix()
                    vid_name_norm = Path(vid_path).stem.lower().replace(".", "_").replace(" ", "_")
                    # Try exact path first, then normalized name, fallback to empty
                    cover_url = covers_map.get(vid_path) or covers_map.get(vid_name_norm) or ""

                    print(f"DASHBOARD DEBUG: Video='{vid_path}' -> Cover URL='{cover_url}'")

                    videos.append({
                        "path": vid_path,
                        "name": Path(line).stem,
                        "cover": cover_url
                    })

    # Build <option> HTML with data-cover
    options_html = "\n".join(
        f'<option value="{v["path"]}" data-cover="{v["cover"]}">{v["name"]}</option>'
        for v in videos
    )

    # Generate HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AkiraTV Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .card {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; }}
            .stat {{ display: inline-block; margin-right: 20px; }}
            .stream-url {{ word-break: break-all; background: #eee; padding: 5px; border-radius: 4px; }}
            button {{ padding: 5px 10px; margin-top: 5px; }}
        </style>
    </head>
    <body>
        <h1>📡 AkiraTV Dashboard</h1>

        <div class="card">
            <h3>📺 Play Now</h3>
            <select id="video_select" onchange="updateCover()">
                {options_html}
            </select>
            <br><br>
            <img id="video_cover" src="" style="max-width:300px; display:none; border-radius:8px; box-shadow:0 2px 6px rgba(0,0,0,0.3);">
            <br><br>
            <button onclick="playVideo()">Play</button>
            <div id="play_status"></div>
        </div>

        <div class="card">
            <h3>🌍 Stream URLs</h3>
            {''.join(f'<div class="stream-url">{url}</div>' for url in urls)}
        </div>

        <script>
            async function playVideo() {{
                const video = document.getElementById("video_select").value;
                if (!video) {{
                    alert("Select a video first");
                    return;
                }}
                const resp = await fetch("/play_now", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{ video_path: video, channel: "live" }})
                }});
                const data = await resp.json();
                document.getElementById("play_status").innerText = data.message;
            }}

            function updateCover() {{
                const select = document.getElementById("video_select");
                const img = document.getElementById("video_cover");
                const option = select.options[select.selectedIndex];
                const cover = option.dataset.cover;
                if (!cover) {{
                    img.style.display = "none";
                    return;
                }}
                img.src = cover;  // correct URL
                img.style.display = "block";
                img.onerror = () => img.style.display = "none";
            }}

            // Initialize first cover on load
            window.addEventListener('load', updateCover);
        </script>
    </body>
    </html>
    """
    return html
