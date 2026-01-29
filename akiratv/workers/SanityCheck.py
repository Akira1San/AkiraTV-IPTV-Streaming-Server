import subprocess
import json
import sys
from pathlib import Path

# --- TARGETS FROM YOUR ENCODING APP ---
TARGET_RESOLUTION = "720x404"        
TARGET_PROFILE = "main"               
TARGET_AUDIO_RATE = "44100"
TARGET_CODEC = "h264"  # Your GPU encoder outputs H.264
TARGET_BFRAMES = 0     # From your -bf 0

def probe_file(file_path):
    cmd = [
        "ffprobe", "-v", "quiet", 
        "-print_format", "json", 
        "-show_streams", 
        str(file_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

def check_folder(folder_path):
    path_obj = Path(folder_path)
    if not path_obj.exists():
        print(f"❌ Error: Folder '{folder_path}' does not exist.")
        return

    print(f"🔍 Validating for AkiraTV Stream Compatibility...")
    print(f"📂 Path: {path_obj.absolute()}")
    print("="*80)
    
    for file in path_obj.glob("*.*"):
        if file.suffix.lower() not in ['.mp4', '.mkv', '.ts', '.avi']:
            continue
        
        try:
            data = probe_file(file)
            v = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
            a = next((s for s in data['streams'] if s['codec_type'] == 'audio'), None)
            
            if not v: continue

            # Extract Metadata
            res = f"{v.get('width')}x{v.get('height')}"
            profile = v.get('profile', 'unknown').lower()
            codec = v.get('codec_name', 'unknown')
            rate = a.get('sample_rate') if a else "N/A"
            has_b_frames = v.get('has_b_frames', 0)

            issues = []
            # 1. Codec Check (The 'Blade' Slow-Mo Fix)
            if codec != TARGET_CODEC:
                issues.append(f"CRITICAL: Wrong Codec ({codec}) - Must be {TARGET_CODEC}")
            
            # 2. Resolution Check
            if res != TARGET_RESOLUTION:
                issues.append(f"Resolution Mismatch: {res}")
            
            # 3. Audio Sample Rate (The Speed=0.5x Fix)
            if rate != TARGET_AUDIO_RATE:
                issues.append(f"Audio Sample Rate: {rate}Hz (Must be {TARGET_AUDIO_RATE})")
            
            # 4. B-Frame Check (The Lag Fix)
            if has_b_frames > 0:
                issues.append(f"Contains B-Frames (Lag Risk for -c copy)")

            if not issues:
                print(f"✅ PERFECT  - {file.name}")
            else:
                print(f"❌ RE-ENCODE - {file.name}")
                for issue in issues:
                    print(f"    └─ {issue}")
            
        except Exception as e:
            print(f"⚠️ ERROR PROBING {file.name}: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_folder(sys.argv[1])
    else:
        print("Usage: python SanityCheck.py C:\\Path\\To\\Videos")