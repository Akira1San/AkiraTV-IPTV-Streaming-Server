# akiratv/server.py (modified parts)
from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
from threading import Thread
from urllib.parse import unquote

from .app_context import app_context  # New import
from .dashboard import generate_dashboard_html

app = Flask(__name__)

# ------------------------
# Dashboard
# ------------------------
@app.route("/")
def dashboard():
    return generate_dashboard_html()

# ------------------------
# Play Now API
# ------------------------
@app.route("/play_now", methods=["POST"])
def play_now():
    data = request.get_json(force=True)
    # print("🎬 Play request:", data)  # DEBUG: Enable for troubleshooting API calls

    akiratv_instance = app_context.akiratv
    if akiratv_instance is None:
        return jsonify({
            "status": "error",
            "message": "AkiraTV not running"
        }), 500

    video_path = data.get("video_path")
    channel = data.get("channel", "live")

    if not video_path:
        return jsonify({
            "status": "error",
            "message": "Missing video_path"
        }), 400

    akiratv_instance.enqueue_play_now(channel, video_path)

    return jsonify({
        "status": "ok",
        "message": f"Queued {Path(video_path).name}"
    })

@app.route("/user/<path:filename>")
def user_files(filename):
    import os
    # print(f"Dashboard requested file: {filename}")  # DEBUG: Enable for troubleshooting
    # print(f"Requested filename: {filename}")  # DEBUG: Enable for troubleshooting
    
    base = Path(__file__).parent.parent.parent / "user"
    full_path = base / filename
    
    # print(f"Attempting to serve from base directory: {base}")  # DEBUG: Enable for troubleshooting
    # print(f"Full resolved path: {full_path}")  # DEBUG: Enable for troubleshooting
    # print(f"File exists? {full_path.exists()}")  # DEBUG: Enable for troubleshooting

    if not full_path.exists():
        return "File not found", 404  # <-- Return a clearer error

    return send_from_directory(base, filename)

# ------------------------
# Static files
# ------------------------
@app.route("/playlists/<path:filename>")
def serve_playlist(filename):
    return send_from_directory("playlists", filename)

# @app.route("/covers/<path:filename>")
# def serve_cover(filename):
#     cover_dir = Path(__file__).parent.parent.parent / "user" / "covers"
#     return send_from_directory(cover_dir, filename)

@app.route("/covers/<path:filename>")
def serve_cover(filename):
    # Decode URL-encoded characters (e.g., %20 -> space)
    filename = unquote(filename)
    
    print(f"\n--- FLASK DEBUG: Cover Requested ---")
    print(f"Requested filename: {filename}")

    cover_dir = Path(__file__).parent.parent.parent / "user" / "covers"
    full_path = cover_dir / filename
    
    print(f"Resolved base directory: {cover_dir}")
    print(f"Resolved full path: {full_path}")
    print(f"File exists? {full_path.exists()}")
    if full_path.exists():
        print(f"File size: {full_path.stat().st_size} bytes")
    print("------------------------------------\n")

    if not full_path.exists():
        return f"Cover not found at: {full_path}", 404
        
    return send_from_directory(cover_dir, filename)

@app.route("/hls/<channel>/<path:filename>")
def serve_hls(channel, filename):
    akiratv_instance = app_context.akiratv
    if akiratv_instance is None:
        return "Server not running", 404

    storage = akiratv_instance.config.data.get("storage", {})
    if storage.get("type") == "ram":
        output_root = Path(storage.get("ram_path", "R:/akiratv"))
    else:
        output_root = Path(storage.get("disk_path", "./output"))

    hls_path = output_root / "hls" / channel
    return send_from_directory(str(hls_path), filename)

def run_server():
    print("🌐 Starting Flask server on port 5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

_server_started = False

def start_server_in_thread():
    global _server_started
    if _server_started:
        print("⚠️ Flask server already started, skipping")
        return
    _server_started = True
    Thread(target=run_server, daemon=True).start()