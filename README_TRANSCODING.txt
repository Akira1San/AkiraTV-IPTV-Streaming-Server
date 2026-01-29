# AkiraTV Transcoding Guide

## What is Transcoding?

By default, AkiraTV streams your video files using a process called **stream copy** (`-c copy`). This is extremely fast and uses virtually no CPU because it simply repackages the original video data into the HLS format without changing it.

**Transcoding** is the process of **re-encoding** the video on-the-fly. This allows you to change the video's quality, resolution, and bitrate to better suit your needs.

### Why Use Transcoding?

*   **Save Bandwidth:** Reduce the bitrate to stream over the internet or to mobile devices without using too much data.
*   **Improve Compatibility:** Convert all videos to a single, universally compatible format (e.g., H.264 + AAC), ensuring they play on all devices.
*   **Reduce Resolution:** Downscale 4K or 1080p source videos to 720p or 480p for smoother playback on less powerful devices or slower networks.

**The trade-off is increased CPU/GPU usage.** Transcoding is much more intensive than stream copy.

---

## How to Use Transcoding in AkiraTV

You can configure transcoding in the **Settings** tab of the AkiraTV UI.

### 1. Transcoding Mode

This is the main on/off switch.

*   **Off:** (Default) Uses stream copy. Fast, zero CPU impact. The stream quality will be identical to your source files.
*   **On:** Enables transcoding. Use the settings below to define the output quality.

### 2. Streaming Profile

These are presets that automatically configure quality and bitrate for common scenarios.

*   **Auto:** Attempts to match the quality of the source video. Good for local networks where bandwidth isn't a concern.
*   **Local Network:** High quality preset for streaming within your home on a fast Wi-Fi or Ethernet connection.
*   **Remote / Internet:** A balanced preset for streaming to friends or over the internet. Reduces bitrate to save bandwidth.
*   **Mobile Friendly:** A low-quality preset for streaming to phones or on very slow connections.

### 3. Video Quality

Forces the output to a specific resolution, regardless of the source.

*   **Source:** Keeps the original resolution of the video.
*   **1080p:** Scales the video to 1920x1080.
*   **720p:** Scales the video to 1280x720. A great all-around choice for compatibility.
*   **480p:** Scales the video to 854x480. Ideal for mobile or very slow connections.

### 4. Encoder

Selects the video encoding library.

*   **Auto:** Automatically picks the best software encoder (`libx264`). Works everywhere.
*   **CPU (x264):** Uses the CPU for encoding. High quality but can be slow.
*   **NVIDIA NVENC:** Uses the dedicated encoder on NVIDIA graphics cards. Fast and efficient.
*   **Intel QSV:** Uses the dedicated encoder on modern Intel CPUs. Fast and efficient.
*   **AMD AMF:** Uses the dedicated encoder on AMD graphics cards. Fast and efficient.

### 5. Audio

Selects the audio encoding and quality.

*   **Copy:** (Default) Keeps the original audio track. Fastest option.
*   **AAC 128k:** Re-encodes audio to AAC format at 128kbps. Good quality, widely compatible.
*   **AAC 160k:** Re-encodes audio to AAC format at 160kbps. Higher quality.

---

## Putting It All Together: Example Scenarios

### Scenario 1: "I want to stream my high-quality movie collection to a friend over the internet."

1.  **Transcoding Mode:** `On`
2.  **Streaming Profile:** `Remote / Internet`
3.  **Video Quality:** `720p` (or `Source` if you want to keep the original resolution)
4.  **Encoder:** `NVIDIA NVENC` (if you have an NVIDIA GPU) or `CPU` if not.
5.  **Audio:** `AAC 128k`

### Scenario 2: "I want to watch my channels on my phone while on the go."

1.  **Transcoding Mode:** `On`
2.  **Streaming Profile:** `Mobile Friendly`
3.  **Video Quality:** `480p`
4.  **Encoder:** `Auto`
5.  **Audio:** `AAC 128k`

---

## A Note on Hardware Acceleration

You will see two settings related to hardware:

1.  **Hardware Acceleration (in FFmpeg Advanced section):** This is a **global** setting that helps FFmpeg use your GPU for **decoding** the input video.
2.  **Encoder (in Transcoding Settings):** This chooses the library for **encoding** the output stream.

**To use your NVIDIA GPU for transcoding, you must set:**
*   **Hardware Acceleration:** `cuda`
*   **Encoder:** `NVIDIA NVENC`

The same logic applies to Intel (`qsv`) and AMD (`amf`). If you set the Encoder to `Auto` or `CPU`, the `hwaccel` setting will have no effect on the encoding step.

---

## Troubleshooting

*   **Problem:** My stream is lagging or stuttering after enabling transcoding.
    *   **Solution:** Your CPU/GPU might be at its limit. Try lowering the **Streaming Profile** (e.g., from `Local` to `Mobile`) or reducing the **Video Quality**.

*   **Problem:** The stream doesn't start after I apply the settings.
    *   **Solution:** Check your console output for FFmpeg errors. You may have an incompatible combination of settings, or a required encoder might not be installed on your system.

*   **Problem:** CPU usage is at 100%.
    *   **Solution:** This is normal when transcoding. Ensure you have a powerful enough CPU, or use a GPU encoder (`NVIDIA NVENC`, `Intel QSV`) to offload the work from the CPU.