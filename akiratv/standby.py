# akiratv/bumper.py
import subprocess
#import json
from pathlib import Path
#import textwrap
from PIL import Image, ImageDraw, ImageFont
import uuid
from akiratv.collections import FFMPEG_PATH

def create_standby_video(duration=30, codec="h265", output_path=None, resolution=(720, 400)):
    """Generate a looping standby video with AkiraTV ASCII art."""
    if output_path is None:
        output_path = Path("assets/standby/akiratv_standby.mp4")
    output_path.parent.mkdir(exist_ok=True)

    width, height = resolution  # Unpack resolution tuple

    # ASCII art
    ascii_art = """
    ┌──────────────────────┐
    │      AkiraTV         │
    │                      │
    │   HOME ENTERTAINMENT │
    │                      │
    └──────────────────────┘
    """

    # Create image with custom resolution
    img = Image.new('RGB', (width, height), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Scale font size based on resolution (baseline: 720x400)
    font_size = int(24 * (height / 400))
    
    try:
        font = ImageFont.truetype("consola.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("cour.ttf", font_size)
        except:
            font = ImageFont.load_default()

    y_offset = height // 4  # Start at 1/4 down the screen
    line_spacing = int(30 * (height / 400))  # Scale line spacing
    
    for line in ascii_art.strip().split('\n'):
        draw.text((width // 2, y_offset), line, fill=(0, 255, 0), font=font, anchor="mm")
        y_offset += line_spacing

    temp_img = Path("temp") / f"standby_img_{width}x{height}.png"
    temp_img.parent.mkdir(exist_ok=True)
    img.save(temp_img)

    # Determine codec params
    if codec == "h265":
        video_codec = "libx265"
        profile = "main"
        level = "4.0"
        tag = "hvc1"
    else:
        video_codec = "libx264"
        profile = "main"
        level = "3.0"
        tag = "avc1"

     # Generate video
     try:
         subprocess.run([
             FFMPEG_PATH, "-y",
             "-loop", "1", "-i", str(temp_img),
             "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
             "-c:v", video_codec,
             "-pix_fmt", "yuv420p",
             "-profile:v", profile,
             "-level", level,
             "-tag:v", tag,
             "-preset", "fast",
             "-c:a", "aac", "-b:a", "128k", "-ac", "2",
             "-t", str(duration),
             "-r", "1",
             str(output_path)
         ], check=True, capture_output=True, text=True)
        
        print(f"[OK] Created standby: {output_path.name} ({width}x{height})")
        
    finally:
        # Cleanup temp file
        if temp_img.exists():
            temp_img.unlink()

    return output_path

def create_next_title_image(next_title: str, output_path: Path):
    """Create a semi-transparent 'Next: Title' banner."""
    # Create transparent overlay (720x404)
    img = Image.new('RGBA', (720, 404), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arialbd.ttf", 48)
    except:
        font = ImageFont.load_default()

    # Draw semi-transparent black background bar
    draw.rectangle([(0, 360), (720, 404)], fill=(0, 0, 0, 180))
    # Draw white text
    draw.text((360, 370), next_title, fill=(255, 255, 255, 255), font=font, anchor="mm")
    
    img.save(output_path)
    return output_path


def add_end_card_to_video(
    input_path: str,
    next_title: str,
    duration: float,
    output_path: str,
    codec: str = "h265"
):
    """
    Add a 'Next: Title' end card to the last 10 seconds of a video.
    Re-encodes video with your preferred settings.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    overlay_img = Path("temp") / f"endcard_{uuid.uuid4().hex}.png"
    overlay_img.parent.mkdir(exist_ok=True)

    try:
        # Create overlay image
        create_next_title_image(next_title, overlay_img)

        # Determine encoder
        if codec == "h265":
            video_codec = "hevc_nvenc"
        else:
            video_codec = "h264_nvenc"

        start_time = max(0, duration - 10)  # Start overlay at (duration - 10)

         # Build FFmpeg command
         cmd = [
             FFMPEG_PATH, "-y",
             "-i", str(input_path),
             "-i", str(overlay_img),
             "-filter_complex",
             f"[0:v][1:v]overlay=enable='between(t,{start_time},{duration})'",
             "-c:v", video_codec,
             "-profile:v", "main",
             "-level:v", "4.0",
             "-rc:v", "cbr",
             "-b:v", "1800k",
             "-maxrate", "1800k",
             "-bufsize", "3600k",
             "-g", "90",
             "-bf", "0",          # No B-frames
             "-flags", "+cgop",
             "-c:a", "copy",      # Copy audio
             "-movflags", "frag_keyframe+empty_moov+default_base_moof",
             str(output_path)
         ]

        print(f"[PLAY] Adding end card to: {input_path.name}")
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return str(output_path)

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        print(f"[ERROR] FFmpeg error: {error_msg}")
        raise
    except Exception as e:
        print(f"[ERROR] General error: {e}")
        raise
    finally:
        if overlay_img.exists():
            overlay_img.unlink()