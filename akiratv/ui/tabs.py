import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# Import the Tooltip from our new widgets file
from .widgets import Tooltip

class GeneralTab(ttk.Frame):
    """Tab for managing channels, playlists, and general settings."""
    def __init__(self, parent, app_instance, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.app = app_instance # Get access to the main app's methods and data
        self.create_widgets()

    def create_widgets(self):
        # === Channel Management ===
        chan_label_frame = ttk.LabelFrame(self, text="Channels")
        chan_label_frame.pack(fill="x", padx=10, pady=5)

        self.app.channels_container = ttk.Frame(chan_label_frame)
        self.app.channels_container.pack(fill="x", padx=5, pady=5)
        self.app.channel_configs = {}
        self.app.load_channel_toggles()

        # Add channel input
        add_frame = ttk.Frame(chan_label_frame)
        add_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.app.new_channel_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.app.new_channel_var, width=20).pack(side="left", padx=(0, 5))
        ttk.Button(add_frame, text="+ Add Channel", command=self.app.add_channel_ui).pack(side="left")

        # === Stream URLs ===
        url_frame = ttk.LabelFrame(self, text="Stream URLs")
        url_frame.pack(fill="x", padx=10, pady=10)

        scrollbar = ttk.Scrollbar(url_frame)
        scrollbar.pack(side="right", fill="y")

        self.app.url_text = tk.Text(url_frame, height=4, width=80, state="disabled", yscrollcommand=scrollbar.set)
        self.app.url_text.pack(padx=5, pady=5, fill="x")
        scrollbar.config(command=self.app.url_text.yview)



        # Playlist Controls
        playlist_frame = ttk.Frame(self)
        playlist_frame.pack(fill="x", padx=10, pady=5)

        # Channel selector (dropdown)
        ttk.Label(playlist_frame, text="Channel:").pack(side="left", padx=(0,5))
        
        enabled_channels = [
            channel for channel, conf in self.app.config_data.get("channels", {}).items()
            if conf.get("enabled", False)
        ]
        if not enabled_channels:
            enabled_channels = ["dynamic"]

        channel_dropdown = ttk.Combobox(
            playlist_frame,
            textvariable=self.app.dynamic_channel_var,
            values=enabled_channels,
            width=15,
            state="readonly"
        )
        channel_dropdown.pack(side="left", padx=(0,5))
        channel_dropdown.set(enabled_channels[0])

        ttk.Button(playlist_frame, text="Create Playlist", command=self.app.create_playlist).pack(side="left", padx=(5,0))
        ttk.Button(playlist_frame, text="Play Now", command=self.app.play_now_video).pack(side="left", padx=(5,0))
        ttk.Button(playlist_frame, text="Stop", command=self.app.stop_video).pack(side="left", padx=(5,0))

        # Playlist selector
        playlist_select_frame = ttk.Frame(self)
        playlist_select_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(playlist_select_frame, text="Playlist:").pack(side="left", padx=(0,5))
        self.app.playlist_var = tk.StringVar()
        self.app.playlist_dropdown = ttk.Combobox(
            playlist_select_frame,
            textvariable=self.app.playlist_var,
            width=30,
            state="readonly"
        )
        self.app.playlist_dropdown.pack(side="left", padx=(0,5))
        self.app.load_playlist_dropdown()

        ttk.Button(playlist_select_frame, text="Play Selected", command=self.app.play_selected_video).pack(side="left", padx=(5,0))
        ttk.Button(playlist_select_frame, text="Stop", command=self.app.stop_video).pack(side="left", padx=(5,0))


class SettingsTab(ttk.Frame):
    """Tab for all technical settings like transcoding, storage, and output."""
    def __init__(self, parent, app_instance, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.app = app_instance
        self.create_widgets()

    def create_widgets(self):
        # Use a scrollable frame
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # General Settings
        gen_frame = ttk.LabelFrame(scrollable_frame, text="General")
        gen_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(gen_frame, text="Channel Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.app.channel_name = tk.StringVar(value=self.app.config_data.get("channel", "critters"))
        ttk.Entry(gen_frame, textvariable=self.app.channel_name, width=30).grid(row=0, column=1, padx=5, pady=2)
        
        # Dark Theme Toggle
        ttk.Checkbutton(
            gen_frame,
            text="Dark Theme",
            variable=self.app.dark_mode,
            command=self.app.toggle_theme
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=2)

        # === TRANSCODING SETTINGS ===
        trans_frame = ttk.LabelFrame(scrollable_frame, text="Transcoding Settings")
        trans_frame.pack(fill="x", padx=10, pady=5)

        mode_label = ttk.Label(trans_frame, text="Transcoding Mode:")
        mode_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        Tooltip(mode_label, "Off: Fast, uses no CPU (stream copy).\nOn: Slower, uses CPU/GPU to re-encode the video for lower bandwidth or compatibility.")
        mode_combo = ttk.Combobox(
            trans_frame,
            textvariable=self.app.transcoding_mode,
            values=["enabled", "disabled"],
            width=15,
            state="readonly"
        )
        mode_combo.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        # Bitrate
        bitrate_label = ttk.Label(trans_frame, text="Bitrate:")
        bitrate_label.grid(row=1, column=0, sticky="w", padx=5, pady=2)
        Tooltip(bitrate_label, "Controls the output video bitrate. 'Auto' matches the source. 'Custom' lets you specify a value.")
        bitrate_combo = ttk.Combobox(trans_frame, textvariable=self.app.transcoding_bitrate,
                                    values=["auto", "custom", "1000k", "1500k", "2000k", "2500k"], width=15, state="readonly")
        bitrate_combo.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        # Custom Bitrate Entry
        self.app.custom_bitrate_entry = ttk.Entry(trans_frame, textvariable=self.app.transcoding_custom_bitrate, width=10)
        self.app.custom_bitrate_entry.grid(row=1, column=2, sticky="w", padx=5, pady=2)
        Tooltip(self.app.custom_bitrate_entry, "Enter a custom bitrate, e.g., 1200k or 2M")

        # Function to enable/disable the entry box
        def _on_bitrate_change(event=None):
            if self.app.transcoding_bitrate.get() == "custom":
                self.app.custom_bitrate_entry.config(state="normal")
            else:
                self.app.custom_bitrate_entry.config(state="disabled")

        # Set initial state and bind the function
        _on_bitrate_change()
        bitrate_combo.bind("<<ComboboxSelected>>", _on_bitrate_change)

        # Video Quality
        video_label = ttk.Label(trans_frame, text="Video Quality:")
        video_label.grid(row=2, column=0, sticky="w", padx=5, pady=2)
        Tooltip(video_label, "Rescales the video. 'Source' keeps original resolution.")
        video_combo = ttk.Combobox(trans_frame, textvariable=self.app.video_quality,
                                  values=["source", "1080p", "720p", "480p", "640x480", "720x404"], width=15, state="readonly")
        video_combo.grid(row=2, column=1, sticky="w", padx=5, pady=2)

        # Encoder
        encoder_label = ttk.Label(trans_frame, text="Encoder:")
        encoder_label.grid(row=3, column=0, sticky="w", padx=5, pady=2)
        Tooltip(encoder_label, "Choose the encoding library. 'Auto' picks the best based on your Hardware Acceleration setting. For NVIDIA, set Hardware Acceleration to 'cuda' and choose 'nvenc' here.")
        encoder_combo = ttk.Combobox(trans_frame, textvariable=self.app.encoder,
                                    values=["auto", "cpu", "nvenc", "qsv", "amf"], width=15, state="readonly")
        encoder_combo.grid(row=3, column=1, sticky="w", padx=5, pady=2)

        # Audio
        audio_label = ttk.Label(trans_frame, text="Audio:")
        audio_label.grid(row=4, column=0, sticky="w", padx=5, pady=2)
        Tooltip(audio_label, "Choose audio quality. 'Copy' is fastest. AAC is widely compatible.")
        audio_combo = ttk.Combobox(trans_frame, textvariable=self.app.audio_quality,
                                  values=["copy", "aac_128k", "aac_160k"], width=15, state="readonly")
        audio_combo.grid(row=4, column=1, sticky="w", padx=5, pady=2)

        # Frame Rate
        fps_label = ttk.Label(trans_frame, text="Frame Rate:")
        fps_label.grid(row=5, column=0, sticky="w", padx=5, pady=2)
        Tooltip(fps_label, "Force the output frame rate. 'Auto' matches the source video. Use 23.976 for film content.")
        fps_combo = ttk.Combobox(trans_frame, textvariable=self.app.transcoding_fps,
                                values=["auto", "23.976", "25", "29.97", "30"], width=15, state="readonly")
        fps_combo.grid(row=5, column=1, sticky="w", padx=5, pady=2)

        # Threads
        threads_label = ttk.Label(trans_frame, text="Threads:")
        threads_label.grid(row=6, column=0, sticky="w", padx=5, pady=2)
        Tooltip(threads_label, "Number of threads to use for CPU encoding. 'Auto' lets FFmpeg decide. '2' is a safe default.")
        threads_combo = ttk.Combobox(trans_frame, textvariable=self.app.transcoding_threads,
                                    values=["auto", "2", "4", "6", "8"], width=15, state="readonly")
        threads_combo.grid(row=6, column=1, sticky="w", padx=5, pady=2)

        # === SUBTITLE SETTINGS ===
        subs_frame = ttk.LabelFrame(scrollable_frame, text="Subtitles")
        subs_frame.pack(fill="x", padx=10, pady=5)

        self.app.enable_subtitles = tk.BooleanVar(
            value=self.app.config_data.get("ffmpeg", {}).get("enable_subtitles", True)
        )
        subs_check = ttk.Checkbutton(
            subs_frame, text="Enable Subtitles", variable=self.app.enable_subtitles
        )
        subs_check.grid(row=0, column=0, sticky="w", padx=5, pady=2)

        subtitle_font_label = ttk.Label(subs_frame, text="Font Size:")
        subtitle_font_label.grid(row=1, column=0, sticky="w", padx=5, pady=2)
        Tooltip(
            subtitle_font_label,
            "Font size for burned-in subtitles.\nLarger values may not fit on low-resolution video."
        )
        self.app.subtitle_font_size = tk.StringVar(
            value=str(self.app.config_data.get("ffmpeg", {}).get("transcoding", {}).get("subtitle_font_size", "28"))
        )
        font_entry = ttk.Entry(subs_frame, textvariable=self.app.subtitle_font_size, width=10)
        font_entry.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        # FFmpeg Settings
        ffmpeg_frame = ttk.LabelFrame(scrollable_frame, text="FFmpeg (Advanced)")
        ffmpeg_frame.pack(fill="x", padx=10, pady=5)
        hwaccel_label = ttk.Label(ffmpeg_frame, text="Hardware Acceleration:")
        hwaccel_label.grid(row=0, column=0, sticky="w", padx=5, pady=2)
        Tooltip(hwaccel_label, "Global setting for GPU acceleration. Helps with decoding. Works with the Encoder setting above.")
        hwaccel_combo = ttk.Combobox(ffmpeg_frame, textvariable=self.app.hwaccel,
                                     values=["none", "cuda", "nvenc", "qsv", "vaapi"], width=20, state="readonly")
        hwaccel_combo.grid(row=0, column=1, padx=5, pady=2)

        # Storage Settings
        storage_frame = ttk.LabelFrame(scrollable_frame, text="Storage")
        storage_frame.pack(fill="x", padx=10, pady=5)
        
        self.app.storage_mode = tk.StringVar(value=self.app.config_data.get("storage", {}).get("type", "disk"))
        ttk.Label(storage_frame, text="Storage Mode:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        storage_combo = ttk.Combobox(storage_frame, textvariable=self.app.storage_mode,
                                     values=["disk", "ram"], width=10, state="readonly")
        storage_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        storage_combo.bind("<<ComboboxSelected>>", self.on_storage_mode_change)

        self.app.disk_path = tk.StringVar(value=self.app.config_data.get("storage", {}).get("disk_path", "./output"))
        self.app.ram_path = tk.StringVar(value=self.app.config_data.get("storage", {}).get("ram_path", "./output"))
        
        self.app.disk_path_label = ttk.Label(storage_frame, text="Disk Path:")
        self.app.disk_path_entry = ttk.Entry(storage_frame, textvariable=self.app.disk_path, width=40)
        self.app.ram_path_label = ttk.Label(storage_frame, text="RAM Path:")
        self.app.ram_path_entry = ttk.Entry(storage_frame, textvariable=self.app.ram_path, width=40)
        
        self.on_storage_mode_change()

        # Output Settings
        output_frame = ttk.LabelFrame(scrollable_frame, text="Output")
        output_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(output_frame, text="HTTP Port:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.app.http_port = tk.IntVar(value=self.app.config_data.get("output", {}).get("http", {}).get("port", 8081))
        ttk.Spinbox(output_frame, from_=1024, to=65535, textvariable=self.app.http_port, width=10).grid(row=0, column=1, padx=5, pady=2)

        self.app.enable_pre_gen = tk.BooleanVar(value=self.app.config_data.get("streaming", {}).get("pre_gen", True))
        ttk.Label(output_frame, text="Pre-generate segments:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        pre_gen_combo = ttk.Checkbutton(output_frame, variable=self.app.enable_pre_gen)
        pre_gen_combo.grid(row=1, column=1, sticky="w", padx=5, pady=2)

    def on_storage_mode_change(self, event=None):
        # Clear existing path widgets
        self.app.disk_path_label.grid_forget()
        self.app.disk_path_entry.grid_forget()
        self.app.ram_path_label.grid_forget()
        self.app.ram_path_entry.grid_forget()

        mode = self.app.storage_mode.get()
        if mode == "disk":
            self.app.disk_path_label.grid(row=1, column=0, sticky="w", padx=5, pady=2)
            self.app.disk_path_entry.grid(row=1, column=1, padx=5, pady=2)
        else:
            self.app.ram_path_label.grid(row=1, column=0, sticky="w", padx=5, pady=2)
            self.app.ram_path_entry.grid(row=1, column=1, padx=5, pady=2)

class InfoTab(ttk.Frame):
    """Tab displaying application information and features."""
    def __init__(self, parent, app_instance, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.app = app_instance
        self.create_widgets()

    def create_widgets(self):
        # Try to load logo.png from app root
        logo_path = Path("logo.png")
        if logo_path.exists():
            try:
                from PIL import Image, ImageTk
                img = Image.open(logo_path)
                img.thumbnail((300, 100), Image.LANCZOS)
                self.app.logo_img = ImageTk.PhotoImage(img)  # Keep reference on app instance
                logo_label = ttk.Label(self, image=self.app.logo_img)
                logo_label.pack(pady=10)
            except:
                pass  # Fallback to text if PIL missing

        ttk.Label(self, text="AkiraTV — Local IPTV Streamer", 
                font=("TkDefaultFont", 14, "bold")).pack(pady=10)
        
        features = [
            "[OK] Multi-channel linear TV streaming",
            "[OK] Per-channel schedules (weekly/daily)",
            "[OK] Live-TV seeking (join mid-program)",
            "[OK] EPG with Kodi XMLTV support",
            "[OK] Channel logos & program descriptions",
            "[OK] Global sharing via Ngrok",
            "[OK] RAM-disk acceleration (ImDisk)",
            "[OK] HLS streaming with -c copy (zero CPU)",
            "[OK] Bumper-free continuous playback",
            "[OK] Dark theme & responsive UI"
        ]
        
        for feature in features:
            ttk.Label(self, text=feature, anchor="w").pack(pady=2, padx=20, fill="x")
        
        ttk.Label(self, text="© 2025 Your Name").pack(pady=(20,5))
        ttk.Label(self, text="https://github.com/yourname/akiratv", 
                foreground="blue", cursor="hand2").pack(pady=5)