# akiratv/simple_scheduler.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
USER_DIR = BASE_DIR / "user"
SCHEDULE_DIR = USER_DIR / "schedules"
SCHEDULE_DIR.mkdir(parents=True, exist_ok=True)

def load_collections(profile_name="collections"):
    """Load collections from specified profile"""
    try:
        # Get the script's directory and resolve paths
        script_dir = Path(__file__).resolve().parent
        base_dir = script_dir.parent
        collections_dir = base_dir / "user" / "collections"
        
        # Try to find the collection file in the collections directory
        profile_file = collections_dir / f"{profile_name}.json"
        
        # If not found, try with the "collections_" prefix
        if not profile_file.exists():
            profile_file = collections_dir / f"collections_{profile_name}.json"
        
        # If still not found, try in the script's directory as a fallback
        if not profile_file.exists():
            profile_file = script_dir / f"{profile_name}.json"
            if not profile_file.exists():
                profile_file = script_dir / f"collections_{profile_name}.json"
        
        # If the file exists, load it
        if profile_file.exists():
            with open(profile_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("collections", [])
        else:
            print(f"Collection file not found: {profile_file}")
            return []
    except Exception as e:
        print(f"Error loading collections: {e}")
        return []

class SimpleSchedulerWizard:
    def __init__(self, root):
        self.root = root
        self.root.title("AkiraTV — Simple Random Scheduler")
        self.root.geometry("1200x700")
        
        self.collections = []
        self.selected_collections = set()
        self.current_profile = "collections"  # Default profile
        self.current_schedule = None  # Store generated schedule for preview
        
        self.create_widgets()

    def create_widgets(self):
        # Main container with left and right panels
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left panel for controls
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Right panel for preview
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True)
        
        # === LEFT PANEL CONTROLS ===
        
        # Profile selection at the top
        profile_frame = ttk.Frame(left_frame)
        profile_frame.pack(fill="x", pady=(0, 10))
        
        # First row: Collection Profile dropdown
        profile_row1 = ttk.Frame(profile_frame)
        profile_row1.pack(fill="x", pady=(0, 5))
        ttk.Label(profile_row1, text="Quick Select:").pack(side="left")
        self.quick_profile_var = tk.StringVar(value="")
        self.profile_dropdown = ttk.Combobox(profile_row1, textvariable=self.quick_profile_var, 
                                           values=self.get_available_collections(), 
                                           state="readonly", width=25)
        self.profile_dropdown.pack(side="left", padx=5)
        self.profile_dropdown.bind("<<ComboboxSelected>>", self.on_quick_profile_select)
        ttk.Button(profile_row1, text="Refresh", command=self.refresh_collections_dropdown).pack(side="left", padx=5)
        ttk.Button(profile_row1, text="📁 Collection Wizard", command=self.launch_collection_wizard).pack(side="left", padx=5)
        
        # Second row: Manual entry and theme selector
        profile_row2 = ttk.Frame(profile_frame)
        profile_row2.pack(fill="x")
        ttk.Label(profile_row2, text="Or type name:").pack(side="left")
        self.profile_var = tk.StringVar(value=self.current_profile)
        profile_entry = ttk.Entry(profile_row2, textvariable=self.profile_var, width=20)
        profile_entry.pack(side="left", padx=5)
        ttk.Button(profile_row2, text="Load Profile", command=self.load_profile).pack(side="left", padx=5)
        
        # Theme selector on the right
        ttk.Label(profile_row2, text="Theme:").pack(side="right", padx=(20, 5))
        self.theme_var = tk.StringVar(value="clam")
        theme_combo = ttk.Combobox(profile_row2, textvariable=self.theme_var, 
                                  values=self.get_themes(), 
                                  state="readonly", width=12)
        theme_combo.pack(side="right")
        theme_combo.bind("<<ComboboxSelected>>", self.apply_theme)
        
        # Title
        ttk.Label(left_frame, text="Simple Random Scheduler", 
                 font=("TkDefaultFont", 12, "bold")).pack(pady=(0, 5))
        ttk.Label(left_frame, text="Creates a continuous 7-day random schedule").pack(pady=(0, 10))
        
        # Collections list
        ttk.Label(left_frame, text="Select Collections to Include:").pack(anchor="w")
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill="both", expand=True, pady=5)
        
        self.collection_list = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=12, font=("TkDefaultFont", 10))
        self.collection_list.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.collection_list.yview)
        scrollbar.pack(side="right", fill="y")
        self.collection_list.configure(yscrollcommand=scrollbar.set)
        
        # Populate collections (from default profile initially)
        self.load_collections_from_profile()
        
        # Buttons
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Select All", command=self.select_all).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear Selection", command=self.clear_selection).pack(side="left", padx=5)
        
        # Channel selection
        chan_frame = ttk.Frame(left_frame)
        chan_frame.pack(pady=5)
        ttk.Label(chan_frame, text="Assign to channel:").pack(side="left")
        self.channel_var = tk.StringVar(value="critters")
        chan_combo = ttk.Combobox(chan_frame, textvariable=self.channel_var, 
                                 values=self.get_known_channels(), width=18)
        chan_combo.set("critters")
        chan_combo.pack(side="left", padx=5)
        
        # Episodic content handling
        episodic_frame = ttk.Frame(left_frame)
        episodic_frame.pack(pady=5)
        self.episodic_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(episodic_frame, text="Auto-detect and sequence episodic content", 
                       variable=self.episodic_var).pack()

        # Action buttons
        action_frame = ttk.Frame(left_frame)
        action_frame.pack(pady=10)
        
        ttk.Button(action_frame, text="🎲 Preview Random Week", 
                  command=lambda: self.preview_schedule(mode="random")).pack(pady=2, fill="x")

        ttk.Button(action_frame, text="▶ Preview Sequential Week", 
                  command=lambda: self.preview_schedule(mode="sequential")).pack(pady=2, fill="x")
        
        ttk.Separator(action_frame, orient="horizontal").pack(fill="x", pady=10)
        
        ttk.Button(action_frame, text="💾 Save Current Schedule", 
                  command=self.save_current_schedule, state="disabled").pack(pady=2, fill="x")
        self.save_button = action_frame.winfo_children()[-1]  # Store reference to enable/disable
        
        ttk.Button(action_frame, text="Cancel", command=self.root.destroy).pack(pady=2, fill="x")
        
        # === RIGHT PANEL PREVIEW ===
        
        ttk.Label(right_frame, text="Schedule Preview", 
                 font=("TkDefaultFont", 12, "bold")).pack(pady=(0, 5))
        
        # Day selector
        day_frame = ttk.Frame(right_frame)
        day_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(day_frame, text="View day:").pack(side="left")
        self.day_var = tk.StringVar(value="monday")
        day_combo = ttk.Combobox(day_frame, textvariable=self.day_var, 
                                values=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
                                state="readonly", width=12)
        day_combo.pack(side="left", padx=5)
        day_combo.bind("<<ComboboxSelected>>", self.update_preview_display)
        
        # Preview listbox
        preview_frame = ttk.Frame(right_frame)
        preview_frame.pack(fill="both", expand=True)
        
        self.preview_list = tk.Listbox(preview_frame, font=("Consolas", 11))
        self.preview_list.pack(side="left", fill="both", expand=True)
        preview_scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview_list.yview)
        preview_scrollbar.pack(side="right", fill="y")
        self.preview_list.configure(yscrollcommand=preview_scrollbar.set)
        
        # Preview info
        info_frame = ttk.Frame(right_frame)
        info_frame.pack(fill="x", pady=(5, 0))
        self.preview_info = ttk.Label(info_frame, text="Generate a schedule to see preview", 
                                     font=("TkDefaultFont", 9), foreground="gray")
        self.preview_info.pack()


    def get_themes(self):
        """Get available ttk themes"""
        try:
            style = ttk.Style()
            available_themes = style.theme_names()
            return sorted(available_themes)
        except:
            return ["default", "clam", "alt", "classic"]

    def apply_theme(self, event=None):
        """Apply the selected ttk theme"""
        theme_name = self.theme_var.get()
        try:
            style = ttk.Style()
            style.theme_use(theme_name)
        except Exception as e:
            print(f"Error applying theme {theme_name}: {e}")

    def launch_collection_wizard(self):
        """Launch the collection wizard in a new window"""
        try:
            # Import here to avoid circular imports
            from .collection_wizard import launch_collection_wizard
            launch_collection_wizard()
        except ImportError as e:
            messagebox.showerror("Error", f"Could not import collection wizard: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not launch collection wizard: {e}")

    def get_available_collections(self):
        """Scan collections directory and return available collection files"""
        collections = [""]  # Start with empty option
        try:
            script_dir = Path(__file__).resolve().parent
            base_dir = script_dir.parent
            collections_dir = base_dir / "user" / "collections"
            
            if collections_dir.exists():
                # Find all .json files in collections directory
                for json_file in collections_dir.glob("*.json"):
                    filename = json_file.stem
                    # Remove "collections_" prefix if present for cleaner display
                    if filename.startswith("collections_"):
                        display_name = filename[12:]  # Remove "collections_" prefix
                    else:
                        display_name = filename
                    collections.append(display_name)
                
                # Sort alphabetically (keeping empty option first)
                collections = [""] + sorted(collections[1:])
        except Exception as e:
            print(f"Error scanning collections directory: {e}")
        
        return collections

    def refresh_collections_dropdown(self):
        """Refresh the collections dropdown with current files"""
        available_collections = self.get_available_collections()
        self.profile_dropdown.configure(values=available_collections)
        # Reset selection to empty
        self.quick_profile_var.set("")

    def on_quick_profile_select(self, event=None):
        """Handle selection from the quick profile dropdown"""
        selected = self.quick_profile_var.get().strip()
        if selected:
            # Update the manual entry field and load the profile
            self.profile_var.set(selected)
            self.load_profile()
        # Note: We don't reset the dropdown selection so user can see what's selected
        """Scan collections directory and return available collection files"""
        collections = [""]  # Start with empty option
        try:
            script_dir = Path(__file__).resolve().parent
            base_dir = script_dir.parent
            collections_dir = base_dir / "user" / "collections"
            
            if collections_dir.exists():
                # Find all .json files in collections directory
                for json_file in collections_dir.glob("*.json"):
                    filename = json_file.stem
                    # Remove "collections_" prefix if present for cleaner display
                    if filename.startswith("collections_"):
                        display_name = filename[12:]  # Remove "collections_" prefix
                    else:
                        display_name = filename
                    collections.append(display_name)
                
                # Sort alphabetically (keeping empty option first)
                collections = [""] + sorted(collections[1:])
        except Exception as e:
            print(f"Error scanning collections directory: {e}")
        
        return collections

    def refresh_collections_dropdown(self):
        """Refresh the collections dropdown with current files"""
        available_collections = self.get_available_collections()
        self.profile_dropdown.configure(values=available_collections)
        # Reset selection to empty
        self.quick_profile_var.set("")

    def on_quick_profile_select(self, event=None):
        """Handle selection from the quick profile dropdown"""
        selected = self.quick_profile_var.get().strip()
        if selected:
            # Update the manual entry field and load the profile
            self.profile_var.set(selected)
            self.load_profile()
        # Note: We don't reset the dropdown selection so user can see what's selected

    def load_profile(self):
        """Load collections from specified profile"""
        profile_name = self.profile_var.get().strip()
        if not profile_name:
            messagebox.showwarning("Warning", "Please enter a profile name!")
            return
            
        # Remove .json extension if provided
        if profile_name.endswith(".json"):
            profile_name = profile_name[:-5]
            
        self.current_profile = profile_name
        self.load_collections_from_profile()
        messagebox.showinfo("Success", f"Loaded profile: {self.current_profile}.json")

    def load_collections_from_profile(self):
        """Load collections from current profile and update UI"""
        self.collections = load_collections(self.current_profile)
        self.collection_list.delete(0, tk.END)
        for col in self.collections:
            self.collection_list.insert(tk.END, col["name"])

    def select_all(self):
        self.collection_list.select_set(0, tk.END)

    def clear_selection(self):
        self.collection_list.selection_clear(0, tk.END)

    def detect_episodic_content(self, all_videos):
        """Detect and group episodic/sequential content"""
        episodic_groups = {}
        standalone_videos = []
        
        # Group videos by potential series name (remove episode indicators)
        for video in all_videos:
            name = Path(video["path"]).stem.lower()
            
            # Common episode patterns to detect
            import re
            patterns = [
                r'(.+?)\s*[s]\d+[e]\d+',  # S01E01 format
                r'(.+?)\s*season\s*\d+.*episode\s*\d+',  # Season X Episode Y
                r'(.+?)\s*\d+x\d+',  # 1x01 format
                r'(.+?)\s*ep\s*\d+',  # Ep 01
                r'(.+?)\s*episode\s*\d+',  # Episode 01
                r'(.+?)\s*part\s*\d+',  # Part 1
                r'(.+?)\s*\d{2,3}$',  # Ends with 2-3 digits (episode number)
            ]
            
            series_name = None
            for pattern in patterns:
                match = re.search(pattern, name, re.IGNORECASE)
                if match:
                    series_name = match.group(1).strip()
                    break
            
            if series_name:
                if series_name not in episodic_groups:
                    episodic_groups[series_name] = []
                episodic_groups[series_name].append(video)
            else:
                standalone_videos.append(video)
        
        # Only keep groups with 2+ episodes
        final_groups = {k: sorted(v, key=lambda x: Path(x["path"]).stem) 
                       for k, v in episodic_groups.items() if len(v) >= 2}
        
        # Add single-episode "series" back to standalone
        for k, v in episodic_groups.items():
            if len(v) == 1:
                standalone_videos.extend(v)
        
        return final_groups, standalone_videos
    def preview_schedule(self, mode="random"):
        """Generate schedule preview without saving"""
        # Get selected collections
        selected_indices = self.collection_list.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Select at least one collection!")
            return

        target_channel = self.channel_var.get().strip()
        if not target_channel:
            messagebox.showerror("Error", "Please enter a channel name!")
            return

        selected_collections = []
        for idx in selected_indices:
            selected_collections.append(self.collections[idx])

        # Build video list
        all_videos = []
        for collection in selected_collections:
            for video in collection["videos"]:
                all_videos.append({
                    "path": video["path"],
                    "duration": video.get("duration", 5400),
                    "name": Path(video["path"]).name
                })

        if not all_videos:
            messagebox.showerror("No Videos", "Selected collections have no videos!")
            return

        # Generate schedule preview
        total_duration_needed = 7 * 24 * 3600
        new_schedule = {day: [] for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}
        
        current_time = datetime(2023, 1, 2, 0, 0)  # Monday 00:00
        
        if mode == "random":
            self._generate_random_schedule(all_videos, new_schedule, current_time, total_duration_needed, target_channel)
        else:  # sequential
            self._generate_sequential_schedule(all_videos, new_schedule, current_time, total_duration_needed, target_channel)
        
        # Store the schedule and update preview
        self.current_schedule = new_schedule
        self.current_channel = target_channel
        self.current_mode = mode
        self.update_preview_display()
        
        # Enable save button
        self.save_button.configure(state="normal")
        
        # Update info
        episodic_status = " (with episodic sequencing)" if self.episodic_var.get() else ""
        total_entries = sum(len(entries) for entries in new_schedule.values())
        self.preview_info.configure(text=f"{mode.title()} schedule generated: {total_entries} entries{episodic_status}")

    def update_preview_display(self, event=None):
        """Update the preview listbox with the selected day's schedule"""
        if not self.current_schedule:
            self.preview_list.delete(0, tk.END)
            return
        
        selected_day = self.day_var.get()
        day_schedule = self.current_schedule.get(selected_day, [])
        
        self.preview_list.delete(0, tk.END)
        
        if not day_schedule:
            self.preview_list.insert(tk.END, f"No entries for {selected_day.title()}")
            return
        
        # Add day header
        self.preview_list.insert(tk.END, f"=== {selected_day.upper()} ===")
        self.preview_list.insert(tk.END, "")
        
        # Add schedule entries
        for entry in day_schedule:
            time_str = entry["time"]
            file_path = entry["file"]
            file_name = Path(file_path).name
            
            # Truncate long filenames for display
            if len(file_name) > 50:
                display_name = file_name[:47] + "..."
            else:
                display_name = file_name
            
            self.preview_list.insert(tk.END, f"{time_str} - {display_name}")
        
        # Add summary
        self.preview_list.insert(tk.END, "")
        self.preview_list.insert(tk.END, f"Total entries: {len(day_schedule)}")

    def save_current_schedule(self):
        """Save the currently previewed schedule"""
        if not self.current_schedule:
            messagebox.showwarning("No Schedule", "Generate a preview first!")
            return
        
        self._save_schedule(self.current_schedule, self.current_channel)

    def generate_schedule(self, mode="random"):
        """Legacy method - now just calls preview and save"""
        self.preview_schedule(mode)
        if self.current_schedule:
            self.save_current_schedule()
        # Get selected collections
        selected_indices = self.collection_list.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Select at least one collection!")
            return

        target_channel = self.channel_var.get().strip()
        if not target_channel:
            messagebox.showerror("Error", "Please enter a channel name!")
            return

        selected_collections = []
        for idx in selected_indices:
            selected_collections.append(self.collections[idx])

        # Build video list
        all_videos = []
        for collection in selected_collections:
            for video in collection["videos"]:
                all_videos.append({
                    "path": video["path"],
                    "duration": video.get("duration", 5400),
                    "name": Path(video["path"]).name
                })

        if not all_videos:
            messagebox.showerror("No Videos", "Selected collections have no videos!")
            return

        # Generate 7-day schedule for target channel
        total_duration_needed = 7 * 24 * 3600
        new_schedule = {day: [] for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}
        
        current_time = datetime(2023, 1, 2, 0, 0)  # Monday 00:00
        
        if mode == "random":
            self._generate_random_schedule(all_videos, new_schedule, current_time, total_duration_needed, target_channel)
        else:  # sequential
            self._generate_sequential_schedule(all_videos, new_schedule, current_time, total_duration_needed, target_channel)
        
        # Save schedule
        self._save_schedule(new_schedule, target_channel)

    def _generate_random_schedule(self, all_videos, new_schedule, current_time, total_duration_needed, target_channel):
        """Generate random schedule with 12-hour no-repeat rule and episodic handling"""
        recent_videos = []  # Track videos played in last 12 hours
        twelve_hours = 12 * 3600  # 12 hours in seconds
        
        # Detect episodic content if enabled
        if self.episodic_var.get():
            episodic_groups, standalone_videos = self.detect_episodic_content(all_videos)
            episode_trackers = {series: 0 for series in episodic_groups.keys()}  # Track current episode per series
        else:
            episodic_groups = {}
            standalone_videos = all_videos
            episode_trackers = {}
        
        while (current_time - datetime(2023, 1, 2, 0, 0)).total_seconds() < total_duration_needed:
            # Clean up recent_videos (remove entries older than 12 hours)
            current_seconds = (current_time - datetime(2023, 1, 2, 0, 0)).total_seconds()
            recent_videos = [(path, time) for path, time in recent_videos 
                           if current_seconds - time < twelve_hours]
            
            recent_paths = {path for path, _ in recent_videos}
            
            # Choose next video
            if self.episodic_var.get() and episodic_groups:
                # Mix of standalone and episodic content
                available_standalone = [v for v in standalone_videos if v["path"] not in recent_paths]
                available_series = [series for series in episodic_groups.keys() 
                                  if episodic_groups[series][episode_trackers[series]]["path"] not in recent_paths]
                
                # If no available content, reset recent list (emergency fallback)
                if not available_standalone and not available_series:
                    recent_videos = []
                    recent_paths = set()
                    available_standalone = standalone_videos
                    available_series = list(episodic_groups.keys())
                
                # Randomly choose between standalone video or starting/continuing a series
                if available_standalone and available_series:
                    choice_type = random.choice(["standalone", "series"])
                elif available_standalone:
                    choice_type = "standalone"
                elif available_series:
                    choice_type = "series"
                else:
                    choice_type = "standalone"  # Fallback
                
                if choice_type == "series" and available_series:
                    # Pick a random series and get next episode
                    series_name = random.choice(available_series)
                    episode_idx = episode_trackers[series_name]
                    video = episodic_groups[series_name][episode_idx]
                    
                    # Advance episode tracker (loop back to start if at end)
                    episode_trackers[series_name] = (episode_idx + 1) % len(episodic_groups[series_name])
                else:
                    # Pick random standalone video
                    video = random.choice(available_standalone if available_standalone else standalone_videos)
            else:
                # Standard random selection with 12-hour rule
                available_videos = [v for v in all_videos if v["path"] not in recent_paths]
                if not available_videos:
                    # Reset if no videos available (emergency fallback)
                    recent_videos = []
                    available_videos = all_videos
                
                video = random.choice(available_videos)
            
            # Add to schedule
            day_index = current_time.weekday()
            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            day = days[day_index]
            time_str = current_time.strftime("%H:%M:%S")

            new_schedule[day].append({
                "time": time_str,
                "file": video["path"],
                "channel": target_channel,
                "source": "random"
            })
            
            # Track this video
            recent_videos.append((video["path"], (current_time - datetime(2023, 1, 2, 0, 0)).total_seconds()))
            current_time += timedelta(seconds=video["duration"])

    def _generate_sequential_schedule(self, all_videos, new_schedule, current_time, total_duration_needed, target_channel):
        """Generate sequential schedule (original logic)"""
        seq_index = 0
        while (current_time - datetime(2023, 1, 2, 0, 0)).total_seconds() < total_duration_needed:
            video = all_videos[seq_index]
            seq_index = (seq_index + 1) % len(all_videos)

            day_index = current_time.weekday()
            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            day = days[day_index]
            time_str = current_time.strftime("%H:%M:%S")

            new_schedule[day].append({
                "time": time_str,
                "file": video["path"],
                "channel": target_channel,
                "source": "sequential"
            })

            current_time += timedelta(seconds=video["duration"])

    def _save_schedule(self, new_schedule, target_channel):
        """Save the generated schedule to file"""
        schedule_filename = SCHEDULE_DIR / f"schedule_{target_channel}.json"

        # Build new weekly schedule for this channel
        new_weekly = {day: [] for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}
        for day, entries in new_schedule.items():
            new_weekly[day] = entries

        # Sort each day's entries by time
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            new_weekly[day].sort(key=lambda x: x["time"])

        final_schedule = {"weekly": new_weekly}

        with open(schedule_filename, "w", encoding="utf-8") as f:
            json.dump(final_schedule, f, indent=2, ensure_ascii=False)
        
        episodic_status = " (with episodic sequencing)" if self.episodic_var.get() else ""
        messagebox.showinfo("Success", f"Schedule for '{target_channel}' saved to {schedule_filename}!{episodic_status}")
        
        # Disable save button after saving
        self.save_button.configure(state="disabled")

    def get_known_channels(self):
        channels = {"critters", "default"}
        # From config
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                channels.update(config.get("channels", {}).keys())
        except:
            pass
        # From schedule
        try:
            with open("schedule.json", "r", encoding="utf-8") as f:
                sched = json.load(f)
                for key, entries in sched.items():
                    if key == "weekly":
                        for day_entries in entries.values():
                            for entry in day_entries:
                                channels.add(entry.get("channel", "default"))
                    elif isinstance(entries, list):
                        for entry in entries:
                            channels.add(entry.get("channel", "default"))
        except:
            pass
        return sorted(channels)

def launch_simple_scheduler():
    root = tk.Tk()
    app = SimpleSchedulerWizard(root)
    root.mainloop()