import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import json
import threading
import time
import subprocess
import socket
from pathlib import Path

from ..core_api import CoreAPI
from ..config import Config
from ..utils import find_project_root
# Import the new tab and widget classes
from .tabs import GeneralTab, SettingsTab, InfoTab
# Tooltip is already imported inside tabs.py if needed

class AkiraTVApp:
    def __init__(self, root):
        self.update_stats_running = False  # Flag to prevent overlapping executions
        self.root = root
        self.root.title("AkiraTV — Local IPTV Streamer")
        self.root.geometry("800x700")
        self.root.resizable(True, True)

        self.config_data = {}
        self.load_or_init_config()

        # Initialize ALL StringVars early
        self.channel_name = tk.StringVar()
        self.streaming_mode = tk.StringVar()
        self.storage_mode = tk.StringVar()
        self.dynamic_channel_var = tk.StringVar(value="live")
        self.play_now_path = tk.StringVar()
        self.dark_mode = tk.BooleanVar(value=False)

        # === TRANSCODING UI VARIABLES ===
        ffmpeg_config = self.config_data.get("ffmpeg", {})
        transcoding_config = ffmpeg_config.get("transcoding", {})
        self.transcoding_mode = tk.StringVar(value="enabled" if transcoding_config.get("enabled", False) else "disabled")
        self.transcoding_bitrate = tk.StringVar(value=transcoding_config.get("bitrate", "auto"))
        self.transcoding_custom_bitrate = tk.StringVar(value=transcoding_config.get("custom_bitrate", "1500k"))
        self.video_quality = tk.StringVar(value=transcoding_config.get("video_quality", "source"))
        self.encoder = tk.StringVar(value=transcoding_config.get("encoder", "auto"))
        self.audio_quality = tk.StringVar(value=transcoding_config.get("audio_quality", "copy"))
        self.transcoding_fps = tk.StringVar(value=transcoding_config.get("fps", "auto"))
        self.transcoding_threads = tk.StringVar(value=transcoding_config.get("threads", "2"))
        self.subtitle_font_size = tk.StringVar(value=transcoding_config.get("subtitle_font_size", "28"))
        self.hwaccel = tk.StringVar(value=ffmpeg_config.get("hwaccel", "none"))

        self.streaming = False
        self.api = CoreAPI()

        # Apply saved theme
        self.dark_mode.set(self.config_data.get("ui", {}).get("dark_mode", False))
        self.toggle_theme()

        self.root.after(2000, self.update_stats_loop)
        self.create_widgets()

    def create_widgets(self):
        # Top buttons
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=5)
        
        self.streaming_button = ttk.Button(top_frame, text="Start Streaming", command=self.toggle_streaming)
        self.streaming_button.pack(side="left", padx=2)
        ttk.Button(top_frame, text="Open Weekly Wizard", command=self.open_wizard).pack(side="left", padx=2)
        ttk.Button(top_frame, text="Manage Collections", command=self.open_collection_wizard).pack(side="left", padx=2)
        ttk.Button(top_frame, text="Clear HLS Cache", command=self.clear_hls_cache).pack(side="left", padx=2)
        ttk.Button(top_frame, text="Generate XMLTV for Kodi", command=self.generate_xmltv).pack(side="left", padx=2)
        ttk.Button(top_frame, text="Open Config", command=self.open_config_file).pack(side="left", padx=2)
        ttk.Button(top_frame, text="Open Logs", command=self.open_logs).pack(side="left", padx=2)

        # Stats frame
        stats_frame = ttk.Frame(self.root)
        stats_frame.pack(pady=5)
        self.stats_labels = {}
        stats = [("Status", "Ready"), ("Channels", "0"), ("Viewers", "0"), ("Storage", "N/A")]
        for i, (label, default) in enumerate(stats):
            ttk.Label(stats_frame, text=f"{label}:").grid(row=0, column=i*2, padx=(10,2), sticky="w")
            var = tk.StringVar(value=default)
            self.stats_labels[label.lower()] = var
            ttk.Label(stats_frame, textvariable=var).grid(row=0, column=i*2+1, padx=(2,10), sticky="w")

        # Now/Next panel
        now_next_frame = ttk.Frame(stats_frame)
        now_next_frame.grid(row=1, column=0, columnspan=4, pady=5)
        self.now_playing = tk.StringVar(value="No program info")
        self.next_program = tk.StringVar(value="")
        ttk.Label(now_next_frame, text="Now:").pack(side="left", padx=(0,5))
        ttk.Label(now_next_frame, textvariable=self.now_playing).pack(side="left")
        ttk.Label(now_next_frame, text="Next:").pack(side="left", padx=(10,5))
        ttk.Label(now_next_frame, textvariable=self.next_program).pack(side="left")

        # Config editor with Notebook
        config_frame = ttk.LabelFrame(self.root, text="Configuration")
        config_frame.pack(fill="both", expand=True, padx=10, pady=5)

        notebook = ttk.Notebook(config_frame)
        notebook.pack(fill="both", expand=True)

        # Create instances of our new tab classes
        self.general_tab = GeneralTab(notebook, self)
        self.settings_tab = SettingsTab(notebook, self)
        self.info_tab = InfoTab(notebook, self)

        notebook.add(self.general_tab, text="General")
        notebook.add(self.settings_tab, text="Settings")
        notebook.add(self.info_tab, text="Info")

        # Apply/Cancel buttons
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Reload Schedule", command=self.reload_schedule).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Apply Config", command=self.apply_config).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.root.destroy).pack(side="left", padx=5)

    def load_playlist_dropdown(self):
        playlists_dir = Path("playlists")
        if playlists_dir.exists():
            playlists = [f.name for f in playlists_dir.glob("*.m3u")]
            self.playlist_dropdown['values'] = playlists
            if playlists:
                self.playlist_dropdown.set(playlists[0])

    def reload_schedule(self):
        if self.api.is_running:
            # Trigger schedule reload in core
            result = self.api.reload_schedule()
            if result["success"]:
                messagebox.showinfo("Success", "Schedule reloaded!")
            else:
                messagebox.showerror("Error", result["error"])
        else:
            messagebox.showwarning("Warning", "AkiraTV is not running.")

    def reload_dynamic_playlist(self):
        """Push schedule updates to dynamic playlist."""
        if hasattr(self.akiratv_instance, 'workers'):
            for worker, _ in self.akiratv_instance.workers.values():
                if hasattr(worker, 'dynamic_playlist') and worker.dynamic_playlist:
                    # Clear and re-add entries
                    worker.dynamic_playlist.clear()
                    for entry in worker.schedule_entries:
                        worker.dynamic_playlist.add_entry(entry["file"])
                    print(f"🔄 Reloaded dynamic playlist for {worker.channel}")

    def delete_channel(self, channel_name):
        """Delete a channel from configuration."""
        # Confirm deletion
        confirm = messagebox.askyesno(
            "Delete Channel",
            f"Are you sure you want to delete channel '{channel_name}'?\nThis cannot be undone.",
            icon='warning'
        )
        
        if not confirm:
            return
            
        result = self.api.delete_channel(channel_name)
        if result["success"]:
            messagebox.showinfo("Success", result["message"])
            # Refresh channel list
            self.load_channel_toggles()
        else:
            messagebox.showerror("Error", result["error"])
    
    def stop_video(self):
        """Stop currently playing video on selected channel."""
        if not self.streaming:
            messagebox.showerror("Error", "Start streaming first!")
            return
            
        channel_name = self.dynamic_channel_var.get().strip()
        
        result = self.api.stop_channel(channel_name)
        if result["success"]:
            messagebox.showinfo("Success", result["message"])
        else:
            messagebox.showerror("Error", result["error"])
    
    def play_now_video(self):
            if not self.streaming:
                messagebox.showerror("Error", "Start streaming first!")
                return
            video_path = self.play_now_path.get().strip()
            channel_name = self.dynamic_channel_var.get().strip()
            
            # If no path entered, open file dialog
            if not video_path:
                video_path = filedialog.askopenfilename(
                    title="Select Video to Play Now",
                    filetypes=[("Video files", "*.mp4 *.mkv *.avi *.mov"), ("All files", "*.*")]
                )
                if not video_path:
                    return  # User canceled selection
            
            # Validate video path
            if not Path(video_path).exists():
                messagebox.showerror("Error", "Video file does not exist!")
                return
                
            if not channel_name:
                messagebox.showerror("Error", "Channel name required!")
                return
            
            result = self.api.play_now(channel_name, video_path)
            if result["success"]:
                messagebox.showinfo("Success", f"Now playing on {channel_name}: {Path(video_path).name}")
                self.play_now_path.set("")
            else:
                messagebox.showerror("Error", result["error"])

    def load_or_init_config(self):
        config_path = Path("config.json")
        if not config_path.exists():
            # File doesn't exist, create it from defaults
            self.config_data = Config.default_config()
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=2)
            messagebox.showinfo(
                "Welcome to AkiraTV!",
                f"No configuration file found.\n\nA default one has been created for you at:\n{config_path.resolve()}\n\nPlease review the settings and click 'Apply Config'."
            )
        else:
            # File exists, load it
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
                # Merge with defaults to handle any new settings added in updates
                self.config_data = Config._merge_with_defaults(user_data)
            except Exception as e:
                messagebox.showerror(
                    "Configuration Error",
                    f"Failed to load or parse {config_path}.\n\nError: {e}\n\nA new default config will be created."
                )
                self.config_data = Config.default_config()
                # Save the new default config to replace the corrupted one
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(self.config_data, f, indent=2)

    def save_config(self):
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, indent=2)

    def toggle_theme(self):
        if self.dark_mode.get():
            self.apply_theme("dark")
        else:
            self.apply_theme("light")

    def apply_theme(self, mode):
        if mode == "dark":
            bg_color = "#2b2b2b"
            fg_color = "#ffffff"
            frame_bg = "#3c3f41"
            entry_bg = "#313335"
            entry_fg = "#ffffff"
        else:
            bg_color = "#f0f0f0"
            fg_color = "#000000"
            frame_bg = "#f0f0f0"
            entry_bg = "#ffffff"
            entry_fg = "#000000"

        # Configure root and main frames
        self.root.configure(bg=bg_color)
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                # ttk doesn't support bg/fg directly, so we style via ttk.Style
                pass

        # Use ttk.Style for modern look
        style = ttk.Style()
        style.configure("TFrame", background=bg_color)
        style.configure("TLabelframe", background=bg_color, foreground=fg_color)
        style.configure("TLabelframe.Label", background=bg_color, foreground=fg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color)
        style.configure("TButton", background=frame_bg, foreground=fg_color)  # Button text color
        style.configure("TCheckbutton", background=bg_color, foreground=fg_color)
        style.configure("TRadiobutton", background=bg_color, foreground=fg_color)

        # Update non-ttk widgets (like the URL text box)
        if hasattr(self, 'url_text'):
            self.url_text.config(
                bg=entry_bg,
                fg=entry_fg,
                insertbackground=entry_fg  # Cursor color
            )

        # For non-ttk widgets (like Text in URL box)
        if hasattr(self, 'url_text'):
            self.url_text.config(bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)


    def create_playlist(self):
        channel_name = self.dynamic_channel_var.get().strip()
        if not channel_name:
            messagebox.showerror("Error", "Channel name required!")
            return

        folder = filedialog.askdirectory(title="Select Video Folder")
        if not folder:
            return
        
        playlists_dir = Path("playlists")
        playlists_dir.mkdir(exist_ok=True)

        # Generate live.m3u with all videos
        live_playlist_path = playlists_dir / "live.m3u"
        video_files = sorted(Path(folder).rglob("*.mp4"))

        if not video_files:
            messagebox.showerror("Error", "No MP4 files found in folder!")
            return

        with open(live_playlist_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for video in video_files:
                f.write(f"#EXTINF:-1,{video.stem}\n{video}\n")

        # Populate dropdown with individual video names
        self.playlist_dropdown['values'] = [v.stem for v in video_files]
        self.playlist_dropdown.set(video_files[0].stem)

        messagebox.showinfo("Success", f"Playlist created: {live_playlist_path}")

    def update_stats_loop(self):
        if not self.update_stats_running:
            self.update_stats_running = True
            try:
                self.update_stats()
            finally:
                self.update_stats_running = False
                self.root.after(2000, self.update_stats_loop)

    def update_stats(self):
        """Update live statistics in UI."""
        if not hasattr(self, 'stats_labels'):
            return
            
        # Status
        status = "Streaming" if self.streaming else "Stopped"
        self.stats_labels["status"].set(status)
        
        # Channels
        try:
            channels = self.api.get_channels()
            active_channels = sum(1 for ch in channels if ch.enabled)
            self.stats_labels["channels"].set(str(active_channels))
        except:
            self.stats_labels["channels"].set("0")
        
        # Viewers
        try:
            # Get viewers from first running channel
            channels = self.api.get_channels()
            running_channels = [ch for ch in channels if ch.status == "running"]
            if running_channels:
                self.stats_labels["viewers"].set(str(running_channels[0].viewers))
            else:
                self.stats_labels["viewers"].set("0")
        except:
            self.stats_labels["viewers"].set("N/A")
        
        # Storage
        storage = self.config_data.get("storage", {})
        if storage.get("type") == "ram":
            self.stats_labels["storage"].set("RAM")
        else:
            self.stats_labels["storage"].set("Disk")
        
        # Now/Next
        try:
            channels = self.api.get_channels()
            running_channels = [ch for ch in channels if ch.status == "running"]
            if running_channels:
                self.now_playing.set(running_channels[0].now_playing or "N/A")
                self.next_program.set(running_channels[0].next_program or "N/A")
            else:
                self.now_playing.set("No program info")
                self.next_program.set("")
        except Exception as e:
            self.now_playing.set("N/A")
            self.next_program.set("N/A")

    def load_channel_toggles(self):
        """Load channel list with per-channel transcoding and subtitle controls."""
        try:
            channels = self.api.get_channels()
            known_channels = [ch.name for ch in channels]
            if not known_channels:
                known_channels = {"critters"}
        except:
            known_channels = set(self.config_data.get("channels", {}).keys())
            try:
                with open("schedule.json", "r", encoding="utf-8") as f:
                    sched = json.load(f)
                    for key, entries in sched.get("weekly", {}).items():
                        for entry in entries:
                            known_channels.add(entry.get("channel", "default"))
                    for key in sched:
                        if key != "weekly" and isinstance(sched[key], list):
                            for entry in sched[key]:
                                known_channels.add(entry.get("channel", "default"))
            except:
                pass
            if not known_channels:
                known_channels = {"critters"}

        # Create header row
        header_frame = ttk.Frame(self.channels_container)
        header_frame.grid(row=0, column=0, columnspan=5, sticky="ew", padx=5, pady=(0,5))
        ttk.Label(header_frame, text="Channel", width=20, font=("TkDefaultFont", 9, "bold")).pack(side="left", padx=(0,10))
        ttk.Label(header_frame, text="Transcoding", width=12, font=("TkDefaultFont", 9, "bold")).pack(side="left", padx=(0,10))
        ttk.Label(header_frame, text="Subtitles", width=12, font=("TkDefaultFont", 9, "bold")).pack(side="left", padx=(0,10))
        ttk.Label(header_frame, text="Actions", width=10, font=("TkDefaultFont", 9, "bold")).pack(side="left")

        row = 1
        for channel in sorted(known_channels):
            chan_conf = self.config_data.get("channels", {}).get(channel, {})
            
            # Get the type from the config, defaulting to 'linear' for safety
            channel_type = chan_conf.get("type", "linear")

            # Enabled checkbox
            enabled_var = tk.BooleanVar(value=chan_conf.get("enabled", True))
            cb = ttk.Checkbutton(
                self.channels_container,
                text=f"{channel} ({channel_type})", # <-- Use the loaded type
                variable=enabled_var
            )
            cb.grid(row=row, column=0, sticky="w", padx=5, pady=2)
            
            # Transcoding dropdown
            # Get channel-specific or fall back to global
            channel_transcoding = chan_conf.get("transcoding", {})
            global_transcoding = self.config_data.get("ffmpeg", {}).get("transcoding", {})
            
            if "enabled" in channel_transcoding:
                trans_value = "enabled" if channel_transcoding["enabled"] else "disabled"
            else:
                trans_value = "global"  # Use global setting
            
            trans_var = tk.StringVar(value=trans_value)
            trans_combo = ttk.Combobox(
                self.channels_container,
                textvariable=trans_var,
                values=["global", "enabled", "disabled"],
                width=10,
                state="readonly"
            )
            trans_combo.grid(row=row, column=1, sticky="w", padx=5, pady=2)
            
            # Subtitles dropdown
            if "enable_subtitles" in chan_conf:
                subs_value = "enabled" if chan_conf["enable_subtitles"] else "disabled"
            else:
                subs_value = "global"
            
            subs_var = tk.StringVar(value=subs_value)
            subs_combo = ttk.Combobox(
                self.channels_container,
                textvariable=subs_var,
                values=["global", "enabled", "disabled"],
                width=10,
                state="readonly"
            )
            subs_combo.grid(row=row, column=2, sticky="w", padx=5, pady=2)
            
            # Delete button
            delete_btn = ttk.Button(
                self.channels_container,
                text="Delete",
                width=8,
                command=lambda ch=channel: self.delete_channel(ch)
            )
            delete_btn.grid(row=row, column=3, sticky="w", padx=5, pady=2)
            
            # Store all variables for this channel
            self.channel_configs[channel] = {
                "enabled": enabled_var,
                "type": channel_type,
                "transcoding": trans_var,
                "subtitles": subs_var
            }
            
            row += 1

    def add_channel_ui(self):
        """Add a new channel, asking for its type (linear, vod, or dynamic)."""
        channel_name = self.new_channel_var.get().strip()
        if not channel_name:
            messagebox.showwarning("Invalid Name", "Channel name cannot be empty.")
            return
        if channel_name in self.channel_configs:
            messagebox.showwarning("Duplicate", f"Channel '{channel_name}' already exists.")
            return
        if not channel_name.replace("_", "").replace("-", "").isalnum():
            messagebox.showerror("Invalid Name", "Use only letters, numbers, '-', or '_'")
            return

        # Create a dialog to ask for channel type
        type_dialog = tk.Toplevel(self.root)
        type_dialog.title("Select Channel Type")
        type_dialog.geometry("400x200")
        type_dialog.transient(self.root)
        type_dialog.grab_set()
        
        selected_type = tk.StringVar(value="linear")
        
        ttk.Label(
            type_dialog, 
            text=f"What type of channel is '{channel_name}'?",
            font=("TkDefaultFont", 10, "bold")
        ).pack(pady=10)
        
        ttk.Radiobutton(
            type_dialog,
            text="Linear (Scheduled programming from schedule.json)",
            variable=selected_type,
            value="linear"
        ).pack(anchor="w", padx=20, pady=5)
        
        ttk.Radiobutton(
            type_dialog,
            text="VOD (On-demand, play videos via API/UI)",
            variable=selected_type,
            value="vod"
        ).pack(anchor="w", padx=20, pady=5)
        
        ttk.Radiobutton(
            type_dialog,
            text="Dynamic (Standby loop + VOD interruptions + optional schedule)",
            variable=selected_type,
            value="dynamic"
        ).pack(anchor="w", padx=20, pady=5)
        
        def confirm_type():
            type_dialog.destroy()
            self._create_channel_with_type(channel_name, selected_type.get())
        
        ttk.Button(type_dialog, text="Create Channel", command=confirm_type).pack(pady=10)
        
        # Wait for dialog to close
        self.root.wait_window(type_dialog)

    def _create_channel_with_type(self, channel_name, channel_type):
        """Helper method to actually create the channel UI elements."""
        # Use CoreAPI to add the channel
        result = self.api.add_channel(channel_name, channel_type)
        if not result["success"]:
            messagebox.showerror("Error", result["error"])
            return
            
        # Determine the next row for the UI grid
        last_row = 0
        for child in self.channels_container.winfo_children():
            try:
                last_row = max(last_row, child.grid_info()["row"])
            except tk.TclError:
                continue
        new_row = last_row + 1

        # --- Create UI Widgets for the new channel ---

        # Enabled checkbox
        enabled_var = tk.BooleanVar(value=True)
        cb = ttk.Checkbutton(
            self.channels_container,
            text=f"{channel_name} ({channel_type})",
            variable=enabled_var
        )
        cb.grid(row=new_row, column=0, sticky="w", padx=5, pady=2)
        
        # Transcoding dropdown
        trans_var = tk.StringVar(value="global")
        trans_combo = ttk.Combobox(
            self.channels_container,
            textvariable=trans_var,
            values=["global", "enabled", "disabled"],
            width=10,
            state="readonly"
        )
        trans_combo.grid(row=new_row, column=1, sticky="w", padx=5, pady=2)
        
        # Subtitles dropdown
        subs_var = tk.StringVar(value="global")
        subs_combo = ttk.Combobox(
            self.channels_container,
            textvariable=subs_var,
            values=["global", "enabled", "disabled"],
            width=10,
            state="readonly"
        )
        subs_combo.grid(row=new_row, column=2, sticky="w", padx=5, pady=2)
        
        # --- Store the channel's configuration ---
        self.channel_configs[channel_name] = {
            "enabled": enabled_var,
            "type": channel_type,  # LINEAR, VOD, or DYNAMIC
            "transcoding": trans_var,
            "subtitles": subs_var
        }
        
        print(f"✅ Added channel '{channel_name}' with type '{channel_type}'")
        print(f"   Config: {self.channel_configs[channel_name]}")

        self.new_channel_var.set("")
        self.update_channel_urls()
        
        # Show success message
        messagebox.showinfo(
            "Channel Created",
            f"✅ Channel '{channel_name}' created as {channel_type.upper()} type!\n\n"
            f"Don't forget to click 'Apply Config' to save."
        )

    def update_channel_urls(self):
        if not hasattr(self, 'url_text'):
            return
        
        import socket
        # Determine local IP
        http_conf = self.config_data.get("output", {}).get("http", {})
        port = http_conf.get("port", 8081)
        bind = http_conf.get("bind", "127.0.0.1")

        if bind == "0.0.0.0":
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except:
                local_ip = "127.0.0.1"
        else:
            local_ip = bind

        urls = []
        try:
            channels = self.api.get_channels()
            for ch in channels:
                if ch.enabled:
                    # Use CoreAPI to get channel URLs
                    channel_urls = self.api.get_channel_url(ch.name)
                    urls.append(f"📺 {ch.name} Stream (LAN): {channel_urls['stream']}")
                    urls.append(f"📋 {ch.name} EPG (LAN): {channel_urls['epg']}")
                    
                    # Check Ngrok / Tailscale public URLs
                    ngrok_url = getattr(self, "ngrok_url", None)
                    tailscale_url = getattr(self, "tailscale_url", None)
                    
                    if ngrok_url:
                        urls.append(f"🌍 {ch.name} Stream (Ngrok): {ngrok_url}/hls/{ch.name}/index.m3u8")
                        urls.append(f"📋 {ch.name} EPG (Ngrok): {ngrok_url}/xmltv.xml")
                    if tailscale_url:
                        urls.append(f"🌐 {ch.name} Stream (Tailscale): {tailscale_url}/hls/{ch.name}/index.m3u8")
                        urls.append(f"📋 {ch.name} EPG (Tailscale): {tailscale_url}/xmltv.xml")
                    
                    urls.append("")  # Blank line
        except Exception as e:
            print(f"Error getting channel URLs: {e}")

        if not urls:
            urls.append("No enabled channels.")

        self.url_text.config(state="normal")
        self.url_text.delete(1.0, tk.END)
        self.url_text.insert(tk.END, "\n".join(urls).strip())
        self.url_text.config(state="disabled")

    def apply_config(self):
        messagebox.showinfo("Debug", "apply_config method was called!")
        """Save all config including per-channel overrides."""
        # General
        self.config_data["channel"] = self.channel_name.get()
        
        # FFmpeg
        self.config_data.setdefault("ffmpeg", {})
        self.config_data["ffmpeg"]["hwaccel"] = self.hwaccel.get()
        
        # === GLOBAL TRANSCODING ===
        self.config_data["ffmpeg"].setdefault("transcoding", {})
        self.config_data["ffmpeg"]["transcoding"]["enabled"] = self.transcoding_mode.get() == "enabled"
        self.config_data["ffmpeg"]["transcoding"]["bitrate"] = self.transcoding_bitrate.get()
        self.config_data["ffmpeg"]["transcoding"]["custom_bitrate"] = self.transcoding_custom_bitrate.get()
        self.config_data["ffmpeg"]["transcoding"]["video_quality"] = self.video_quality.get()
        self.config_data["ffmpeg"]["transcoding"]["encoder"] = self.encoder.get()
        self.config_data["ffmpeg"]["transcoding"]["audio_quality"] = self.audio_quality.get()
        self.config_data["ffmpeg"]["transcoding"]["fps"] = self.transcoding_fps.get()
        self.config_data["ffmpeg"]["transcoding"]["threads"] = self.transcoding_threads.get()
        self.config_data["ffmpeg"]["transcoding"]["subtitle_font_size"] = self.subtitle_font_size.get()
        
        # Global subtitles
        self.config_data["ffmpeg"]["enable_subtitles"] = self.enable_subtitles.get()

        # Storage
        self.config_data.setdefault("storage", {})
        self.config_data["storage"]["type"] = self.storage_mode.get()
        if self.storage_mode.get() == "disk":
            self.config_data["storage"]["disk_path"] = self.disk_path.get()
        else:
            self.config_data["storage"]["ram_path"] = self.ram_path.get()

        # Auto-set output mode based on storage type
        if self.storage_mode.get() == "ram":
            self.config_data["output"]["mode"] = "ram_http"
        else:
            self.config_data["output"]["mode"] = "http_hls"
        
        # Output
        self.config_data.setdefault("output", {})
        self.config_data["output"].setdefault("http", {})
        self.config_data["output"]["http"]["port"] = self.http_port.get()
        
        # Streaming
        self.config_data.setdefault("streaming", {})
        self.config_data["streaming"]["strategy"] = "concat"
        self.config_data["streaming"]["mode"] = self.streaming_mode.get()
        self.config_data["streaming"]["pre_gen"] = self.enable_pre_gen.get()

        # === PER-CHANNEL SETTINGS ===
        for channel, vars_dict in self.channel_configs.items():
            self.config_data["channels"].setdefault(channel, {})
            chan_conf = self.config_data["channels"][channel]
            
            # Enabled
            chan_conf["enabled"] = vars_dict["enabled"].get()

            # Type
            chan_conf["type"] = vars_dict["type"] # <-- THIS IS THE CRUCIAL LINE
            
            # Transcoding override
            trans_setting = vars_dict["transcoding"].get()
            if trans_setting == "global":
                # Remove override to use global setting
                chan_conf.pop("transcoding", None)
            else:
                # Set channel-specific override
                chan_conf.setdefault("transcoding", {})
                chan_conf["transcoding"]["enabled"] = (trans_setting == "enabled")
            
            # Subtitles override
            subs_setting = vars_dict["subtitles"].get()
            if subs_setting == "global":
                # Remove override to use global setting
                chan_conf.pop("enable_subtitles", None)
            else:
                # Set channel-specific override
                chan_conf["enable_subtitles"] = (subs_setting == "enabled")

        # Save UI settings
        self.config_data.setdefault("ui", {})
        self.config_data["ui"]["dark_mode"] = self.dark_mode.get()

        self.save_config()
        if hasattr(self, 'stats_labels'):
            self.stats_labels["status"].set("Config applied")
        self.update_channel_urls()
        
        messagebox.showinfo("Success", "Configuration saved!\n\nPer-channel settings:\n" + 
                        "\n".join([f"- {ch}: transcoding={v['transcoding'].get()}, subs={v['subtitles'].get()}" 
                                    for ch, v in self.channel_configs.items()]))

    def toggle_streaming(self):
        self.streaming_button.config(state="disabled")
        if self.streaming:
            self.stop_streaming()
            self.streaming_button.config(text="Start Streaming")
        else:
            self.start_streaming()
            self.streaming_button.config(text="Stop Streaming")
        self.streaming_button.config(state="normal")

    def start_streaming(self):
        if self.streaming:
            return
            
        result = self.api.start()
        if result["success"]:
            self.streaming = True
            # Update new stats system
            if hasattr(self, 'stats_labels'):
                self.stats_labels["status"].set("Streaming")
            messagebox.showinfo("Success", "AkiraTV started successfully")
        else:
            messagebox.showerror("Error", result["error"])
            return

        import socket
        try:
            # Example: Tailscale (detect IP in Tailscale network)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("100.100.100.100", 1))  # Tailscale network dummy IP
            self.tailscale_url = f"http://{s.getsockname()[0]}:{self.http_port.get()}"
            s.close()
        except:
            self.tailscale_url = None

        # Example: Ngrok (manually set your public URL for now)
        self.ngrok_url = "http://unnumerative-amuck-larry.ngrok-free.dev"

    def stop_streaming(self):
        print("DEBUG: Stop button pressed. Calling api.stop()...")
        result = self.api.stop()
        if result["success"]:
            self.streaming = False
            # Update new stats system
            if hasattr(self, 'stats_labels'):
                self.stats_labels["status"].set("Stopped")
            messagebox.showinfo("Success", "AkiraTV stopped successfully")
        else:
            messagebox.showerror("Error", result["error"])
            self.akiratv_instance.stop()
        self.streaming = False
        if hasattr(self, 'stats_labels'):
            self.stats_labels["status"].set("Stopped")
        print("DEBUG: akiratv_instance.stop() has returned.")

    def open_wizard(self):
        from ..wizard import launch_wizard
        launch_wizard()

    def open_collection_wizard(self):
        from ..collection_wizard import CollectionWizard
        top = tk.Toplevel(self.root)
        top.title("AkiraTV — Collection Manager")
        app = CollectionWizard(top)

    def clear_hls_cache(self):
        try:
            storage = self.config_data.get("storage", {})
            if storage.get("type") == "ram":
                output_root = Path(storage.get("ram_path", "./output"))
            else:
                output_root = Path(storage.get("disk_path", "./output"))
            if not output_root.exists():
                messagebox.showinfo("Clear Cache", "No HLS cache found.")
                return

            deleted = 0
            for item in output_root.rglob("*"):
                if item.suffix in (".ts", ".m3u8", ".m4s", ".mp4"):
                    try:
                        item.unlink()
                        deleted += 1
                    except:
                        pass

            messagebox.showinfo("Clear Cache", f"Deleted {deleted} HLS segment(s).")
            if hasattr(self, 'stats_labels'):
                self.stats_labels["status"].set(f"Cleared HLS cache ({deleted} files).")
        except Exception as e:
            messagebox.showerror("Clear Cache Error", f"Failed to clear cache:\n{str(e)}")

    def generate_xmltv(self):
        try:
            print("--- [DEBUG] Starting XMLTV Generation ---")
            from .xmltv import generate_xmltv, generate_m3u_playlist

            # # --- FIXED: Find the actual project root ---
            # # Start from current file and go up until we find the project root
            # current = Path(__file__).resolve()

            # # Navigate up to find the directory containing both 'akiratv' and 'user' folders
            # app_root = current.parent  # Start at current file's directory

            # # Keep going up until we find the correct root
            # while app_root.name != "AkiraTV_NEW" and app_root.parent != app_root:
            #     app_root = app_root.parent
        
            # print(f"[DEBUG] Application root directory detected as: {app_root}")

            # --- ROBUST: Find the actual project root ---
            app_root = find_project_root("user")

            # Now user_dir should be directly under the project root
            user_dir = app_root / "user"
            schedules_dir = user_dir / "schedules"
            collections_dir = user_dir / "collections"
            
            # print(f"[DEBUG] Calculated Schedules Dir: {schedules_dir}")
            # print(f"[DEBUG] Calculated Collections Dir: {collections_dir}")
            
            # Check if the directories actually exist before proceeding
            if not schedules_dir.exists():
                # print(f"[ERROR] Schedules directory does NOT exist at: {schedules_dir}")
                messagebox.showerror("Path Error", f"Schedules directory not found:\n{schedules_dir}")
                return
            else:
                print(f"[SUCCESS] Schedules directory exists.")

            if not collections_dir.exists():
                print(f"[ERROR] Collections directory does NOT exist at: {collections_dir}")
                messagebox.showerror("Path Error", f"Collections directory not found:\n{collections_dir}")
                return
            else:
                print(f"[SUCCESS] Collections directory exists.")

            # Determine output root based on storage mode
            storage = self.config_data.get("storage", {})
            if storage.get("type") == "ram":
                hls_root = Path(storage.get("ram_path", "./output"))
            else:
                hls_root = Path(storage.get("disk_path", "./output"))
            
            # print(f"[DEBUG] Output (HLS) Root Directory: {hls_root}")
            hls_root.mkdir(exist_ok=True)
            # print(f"[SUCCESS] Output directory ensured.")

            xmltv_path = hls_root / "xmltv.xml"
            m3u_path = hls_root / "channels.m3u"
            print(f"[DEBUG] Final XMLTV output path will be: {xmltv_path}")
            
            # Call the function with the confirmed paths
            generate_xmltv(
                schedules_dir=str(schedules_dir),
                collections_dir=str(collections_dir),
                output_path=str(xmltv_path)
            )
            
            # Check if the file was actually created
            if xmltv_path.exists():
                print(f"[SUCCESS] XMLTV file successfully created at: {xmltv_path}")
            else:
                print(f"[ERROR] XMLTV file was NOT created at: {xmltv_path}")
                messagebox.showerror("Generation Error", "The XMLTV file was not created. Check the console for errors.")
                return

            generate_m3u_playlist(self.config_data, output_path=str(m3u_path))
            
            messagebox.showinfo(
                "EPG + M3U Generated",
                "✅ xmltv.xml + channels.m3u saved!\n\n"
                "In Kodi IPTV Simple Client:\n"
                f"- M3U Path: http://YOUR_IP:8081/channels.m3u\n"
                f"- XMLTV Path: http://YOUR_IP:8081/xmltv.xml"
            )
        except Exception as e:
            import traceback
            error_details = f"Failed:\n{str(e)}\n\n--- Traceback ---\n{traceback.format_exc()}"
            print(f"[CRITICAL ERROR] {error_details}")
            messagebox.showerror("EPG Error", error_details)

    def open_config_file(self):
        os.startfile("config.json")

    def open_logs(self):
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        os.startfile(log_dir)

    def create_standby_loop(self):
        """Generate standby loop videos for all resolutions found in inventory."""
        # Add this at the start of create_standby_loop
        from pathlib import Path
        inventory_file = Path("user/video_inventory.json")
        print(f"📁 Inventory file exists: {inventory_file.exists()}")
        if inventory_file.exists():
            print(f"📁 Inventory file size: {inventory_file.stat().st_size} bytes")

        def _create():
            try:
                from akiratv.standby import create_standby_video  # Fixed import
                from pathlib import Path
                
                # Create standby directory
                standby_dir = Path("assets/standby")
                standby_dir.mkdir(parents=True, exist_ok=True)
                
                # Get all unique resolutions from inventory
                resolutions = self.get_unique_resolutions_from_inventory()
                
                if not resolutions:
                    # Fallback to common resolutions if inventory is empty
                    resolutions = [
                        ("1920x1080", 1920, 1080),
                        ("1280x720", 1280, 720),
                        ("720x400", 720, 400)  # Your actual resolution
                    ]
                    self.root.after(0, lambda: messagebox.showwarning(
                        "Info", 
                        "No videos in inventory. Creating default resolutions."
                    ))
                
                created_files = []
                codec = "h265"  # You said you're using h265
                
                # Create a standby video for each resolution
                for res_name, width, height in resolutions:
                    output_path = standby_dir / f"standby_{res_name}.mp4"
                    
                    try:
                        created_path = create_standby_video(
                            duration=30,
                            codec=codec,
                            output_path=output_path,
                            resolution=(width, height)
                        )
                        created_files.append(f"{res_name}: {created_path.name}")
                    except Exception as e:
                        error_msg = str(e)
                        self.root.after(0, lambda e=error_msg: messagebox.showerror(
                            "Error", 
                            f"Failed to create standby: {e}"
                        ))
                
                # Also create a default standby (most common resolution)
                if resolutions:
                    default_res = resolutions[0]  # Most common resolution
                    default_path = standby_dir / "default_standby.mp4"
                    create_standby_video(
                        duration=30,
                        codec=codec,
                        output_path=default_path,
                        resolution=(default_res[1], default_res[2])
                    )
                    created_files.append(f"default: {default_path.name}")
                
                # Show success message
                files_list = "\n".join(created_files)
                self.root.after(0, lambda: messagebox.showinfo(
                    "Success", 
                    f"Standby loops created in assets/standby/:\n\n{files_list}"
                ))
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                self.root.after(0, lambda: messagebox.showerror(
                    "Error", 
                    f"Failed to create standby loops:\n{str(e)}\n\n{error_details}"
                ))
        
        # Run in background thread
        threading.Thread(target=_create, daemon=True).start()

    def get_unique_resolutions_from_inventory(self):
        """Get all unique resolutions from video inventory."""
        try:
            from collections import Counter
            import json
            from pathlib import Path
            
            inventory_file = Path("user/video_inventory.json")
            
            if not inventory_file.exists():
                print("❌ Inventory file not found!")
                return []
            
            with open(inventory_file, 'r', encoding='utf-8') as f:
                inventory_data = json.load(f)
            
            print(f"📦 Found {len(inventory_data)} videos in inventory")
            
            resolutions = []
            
            for item in inventory_data:
                video_tracks = item.get("video_tracks", [])
                
                if video_tracks and len(video_tracks) > 0:
                    width = video_tracks[0].get("width")
                    height = video_tracks[0].get("height")
                    
                    if width and height:
                        resolutions.append((width, height))
            
            if not resolutions:
                print("❌ No valid resolutions found in inventory!")
                return []
            
            resolution_counts = Counter(resolutions)
            
            unique_resolutions = [
                (f"{width}x{height}", width, height)
                for (width, height), count in resolution_counts.most_common()
            ]
            
            print(f"✅ Unique resolutions: {unique_resolutions}")
            return unique_resolutions
            
        except Exception as e:
            print(f"❌ Error reading inventory: {e}")
            import traceback
            traceback.print_exc()
            return []

    def play_selected_video(self):
        selected_name = self.playlist_var.get()
        channel_name = self.dynamic_channel_var.get().strip()

        if not selected_name or not channel_name:
            return

        # Find the file path in live.m3u
        live_playlist_path = Path("playlists") / "live.m3u"
        video_path = None
        with open(live_playlist_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if line.strip().endswith(".mp4") and selected_name in line:
                    video_path = line.strip()
                    break

        if not video_path or not Path(video_path).exists():
            messagebox.showerror("Error", "Selected video not found!")
            return

        # Play now
        try:
            #self.akiratv_instance.play_now(channel_name, video_path)
            self.akiratv_instance.command_queue.put(("play_now", channel_name, video_path)) # new for command
            messagebox.showinfo("Success", f"Now playing: {Path(video_path).name}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

def launch_ui():
    root = tk.Tk()
    app = AkiraTVApp(root)
    root.mainloop()