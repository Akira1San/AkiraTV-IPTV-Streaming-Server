import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
import os

# --- Directory and Path Setup ---
SCRIPT_PATH = Path(__file__).resolve()
print(f"DEBUG: Script is running from: {SCRIPT_PATH}")

BASE_DIR = SCRIPT_PATH.parents[0]
print(f"DEBUG: Calculated BASE_DIR: {BASE_DIR}")

USER_DIR = BASE_DIR / "user"
COLLECTIONS_DIR = USER_DIR / "collections"
SCHEDULE_DIR = USER_DIR / "schedules"

print(f"DEBUG: Looking for USER_DIR at: {USER_DIR}")
print(f"DEBUG: Looking for COLLECTIONS_DIR at: {COLLECTIONS_DIR}")
print("-" * 20)

# --- Daypart Definitions ---
TV_DAYPARTS = [
    {"name": "Early Morning", "start": "05:00", "end": "09:00", "color": "#E8F4F8"},
    {"name": "Daytime", "start": "09:00", "end": "16:00", "color": "#FFF8E8"},
    {"name": "Early Fringe", "start": "16:00", "end": "19:00", "color": "#F8E8F8"},
    {"name": "Prime Time", "start": "19:00", "end": "23:00", "color": "#F8E8E8"},
    {"name": "Late Night", "start": "23:00", "end": "02:00", "color": "#E8E8F8"},
    {"name": "Overnight", "start": "02:00", "end": "05:00", "color": "#F0F0F0"}
]

TWO_HOUR_BLOCKS = [
    {"name": "06:00-08:00", "start": "06:00", "end": "08:00", "color": "#E8F4F8"},
    {"name": "08:00-10:00", "start": "08:00", "end": "10:00", "color": "#FFF8E8"},
    {"name": "10:00-12:00", "start": "10:00", "end": "12:00", "color": "#F8E8F8"},
    {"name": "12:00-14:00", "start": "12:00", "end": "14:00", "color": "#F8E8E8"},
    {"name": "14:00-16:00", "start": "14:00", "end": "16:00", "color": "#E8E8F8"},
    {"name": "16:00-18:00", "start": "16:00", "end": "18:00", "color": "#F8F8E8"},
    {"name": "18:00-20:00", "start": "18:00", "end": "20:00", "color": "#F8E8F8"},
    {"name": "20:00-22:00", "start": "20:00", "end": "22:00", "color": "#E8F8F8"},
    {"name": "22:00-00:00", "start": "22:00", "end": "00:00", "color": "#F0F0F0"},
    {"name": "00:00-02:00", "start": "00:00", "end": "02:00", "color": "#E8F4F8"},
    {"name": "02:00-04:00", "start": "02:00", "end": "04:00", "color": "#FFF8E8"},
    {"name": "04:00-06:00", "start": "04:00", "end": "06:00", "color": "#F8E8F8"}
]

# --- Data Loading Functions (Updated) ---

def load_all_collections():
    """
    Load all collections from the collections directory.
    Returns a dictionary mapping collection SHORT names (from filename) to their data.
    Example: collections_horror.json -> key: "horror"
    """
    collections_dict = {}
    
    print(f"DEBUG: Scanning for collection files in: {COLLECTIONS_DIR}")
    if COLLECTIONS_DIR.exists():
        collection_files = list(COLLECTIONS_DIR.glob("collections*.json"))
        print(f"DEBUG: Found {len(collection_files)} collection files")
        
        for file_path in collection_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    collections_data = data.get("collections", [])
                    if isinstance(collections_data, list):
                        # Extract the short name from the filename
                        file_stem = file_path.stem  # e.g., "collections_horror"
                        collection_key = file_stem.replace("collections_", "") # e.g., "horror"
                        
                        # Store the entire list of collections from the file under the short key
                        collections_dict[collection_key] = collections_data
                        print(f"DEBUG: Loaded collection group '{collection_key}' from {file_path.name} with {len(collections_data)} items")
            except Exception as e:
                print(f"DEBUG: Error reading {file_path.name}: {e}")
    
    print(f"DEBUG: Total collection groups loaded: {len(collections_dict)}")
    print("-" * 20)
    return collections_dict

def load_config():
    """Load configuration from config.json"""
    try:
        config_path = BASE_DIR / "config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"channels": {}}

# --- Main Application Class (Updated) ---
class DaypartSchedulerWizard:
    def __init__(self, root):
        self.root = root
        self.root.title("AkiraTV — Daypart Scheduler")
        self.root.geometry("1000x700")
        
        self.collections = load_all_collections()
        self.config = load_config()
        self.schedule_mode = "tv_daypart"
        self.block_configs = {}
        self.schedule_preview = None
        
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill="x", pady=(0, 10))
        
        # Channel selection
        channel_frame = ttk.Frame(top_frame)
        channel_frame.pack(fill="x", pady=5)
        
        ttk.Label(channel_frame, text="Channel:").pack(side="left")
        self.channel_var = tk.StringVar()
        channel_combo = ttk.Combobox(channel_frame, textvariable=self.channel_var, 
                                    values=list(self.config.get("channels", {}).keys()), width=30)
        channel_combo.pack(side="left", padx=5)
        
        # Mode selection
        mode_frame = ttk.Frame(top_frame)
        mode_frame.pack(fill="x", pady=5)
        
        ttk.Label(mode_frame, text="Schedule Mode:").pack(side="left")
        self.mode_var = tk.StringVar(value="tv_daypart")
        ttk.Radiobutton(mode_frame, text="TV Daypart", variable=self.mode_var, 
                       value="tv_daypart", command=self.change_mode).pack(side="left", padx=5)
        ttk.Radiobutton(mode_frame, text="2-Hour Blocks", variable=self.mode_var, 
                       value="2_hour", command=self.change_mode).pack(side="left", padx=5)
        
        # Preset management
        preset_frame = ttk.Frame(top_frame)
        preset_frame.pack(fill="x", pady=5)
        
        ttk.Button(preset_frame, text="Save Preset", command=self.save_preset).pack(side="left", padx=5)
        ttk.Button(preset_frame, text="Load Preset", command=self.load_preset).pack(side="left", padx=5)
        
        # Time blocks grid
        self.grid_frame = ttk.Frame(main_frame)
        self.grid_frame.pack(fill="both", expand=True, pady=10)
        
        self.create_time_blocks_grid()
        
        # Bottom buttons
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill="x", pady=10)
        
        ttk.Button(bottom_frame, text="Preview Schedule", command=self.preview_schedule).pack(side="left", padx=5)
        ttk.Button(bottom_frame, text="Generate Schedule", command=self.generate_schedule).pack(side="left", padx=5)
        ttk.Button(bottom_frame, text="Cancel", command=self.root.destroy).pack(side="right", padx=5)

    def change_mode(self):
        self.schedule_mode = self.mode_var.get()
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
        self.create_time_blocks_grid()

    def create_time_blocks_grid(self):
        """Create the visual grid of time blocks"""
        time_blocks = TV_DAYPARTS if self.schedule_mode == "tv_daypart" else TWO_HOUR_BLOCKS
        
        # Create header row
        headers = ["Time Block", "Collection", "Mode"]
        for i, header in enumerate(headers):
            ttk.Label(self.grid_frame, text=header, font=("TkDefaultFont", 10, "bold")).grid(
                row=0, column=i, padx=5, pady=5, sticky="w")
        
        # Create a row for each time block
        for i, block in enumerate(time_blocks):
            row = i + 1
            
            # Time block label with background color
            block_frame = tk.Frame(self.grid_frame, bg=block["color"], relief="raised", bd=1)
            block_frame.grid(row=row, column=0, padx=5, pady=2, sticky="ew")
            block_label = tk.Label(block_frame, text=f"{block['name']}\n{block['start']}-{block['end']}", 
                                  bg=block["color"], width=15)
            block_label.pack(padx=5, pady=5)
            
            # Collection dropdown - populated with collection NAMES
            collection_var = tk.StringVar()
            collection_combo = ttk.Combobox(self.grid_frame, textvariable=collection_var, 
                                           values=list(self.collections.keys()), width=30) # Use .keys()
            collection_combo.grid(row=row, column=1, padx=5, pady=2)
            
            # Mode dropdown (Random/Sequential)
            mode_var = tk.StringVar(value="random")
            mode_combo = ttk.Combobox(self.grid_frame, textvariable=mode_var, 
                                     values=["random", "sequential"], width=15)
            mode_combo.grid(row=row, column=2, padx=5, pady=2)
            
            # Store the configuration for this block
            self.block_configs[block["name"]] = {
                "start": block["start"],
                "end": block["end"],
                "collection_var": collection_var,
                "collection_widget": collection_combo,
                "mode_var": mode_var,
                "mode_widget": mode_combo
            }
        
        self.grid_frame.columnconfigure(1, weight=1)

    def save_preset(self):
        preset_name = filedialog.asksaveasfilename(
            initialdir=USER_DIR,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Preset"
        )
        
        if not preset_name: return
            
        preset_data = {
            "mode": self.schedule_mode,
            "channel": self.channel_var.get(),
            "blocks": {}
        }
        
        for block_name, config in self.block_configs.items():
            preset_data["blocks"][block_name] = {
                "collection": config["collection_var"].get(),
                "mode": config["mode_var"].get()
            }
        
        with open(preset_name, "w", encoding="utf-8") as f:
            json.dump(preset_data, f, indent=2)
        
        messagebox.showinfo("Success", f"Preset saved to {preset_name}")

    def load_preset(self):
        preset_name = filedialog.askopenfilename(
            initialdir=USER_DIR,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Load Preset"
        )
        
        if not preset_name: return
            
        try:
            with open(preset_name, "r", encoding="utf-8") as f:
                preset_data = json.load(f)
            
            self.mode_var.set(preset_data.get("mode", "tv_daypart"))
            self.channel_var.set(preset_data.get("channel", ""))
            
            if preset_data.get("mode", "tv_daypart") != self.schedule_mode:
                self.change_mode()
            
            for block_name, block_config in preset_data.get("blocks", {}).items():
                if block_name in self.block_configs:
                    self.block_configs[block_name]["collection_var"].set(block_config.get("collection", ""))
                    self.block_configs[block_name]["mode_var"].set(block_config.get("mode", "random"))
            
            messagebox.showinfo("Success", f"Preset loaded from {preset_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load preset: {str(e)}")

    def preview_schedule(self):
        target_channel = self.channel_var.get().strip()
        if not target_channel:
            messagebox.showerror("Error", "Please select a channel!")
            return
            
        self.schedule_preview = self._generate_schedule_data(target_channel)
        
        preview_window = tk.Toplevel(self.root)
        preview_window.title("Schedule Preview")
        preview_window.geometry("800x600")
        
        text_frame = ttk.Frame(preview_window)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        text_widget.insert(tk.END, json.dumps(self.schedule_preview, indent=2))
        text_widget.config(state=tk.DISABLED)
        
        ttk.Button(preview_window, text="Close", command=preview_window.destroy).pack(pady=10)

    def generate_schedule(self):
        target_channel = self.channel_var.get().strip()
        if not target_channel:
            messagebox.showerror("Error", "Please select a channel!")
            return
            
        schedule_data = self._generate_schedule_data(target_channel)
        schedule_filename = SCHEDULE_DIR / f"schedule_{target_channel}.json"
        
        with open(schedule_filename, "w", encoding="utf-8") as f:
            json.dump(schedule_data, f, indent=2)
        
        messagebox.showinfo("Success", f"Schedule for '{target_channel}' saved to {schedule_filename}!")
        self.root.destroy()

    def _generate_schedule_data(self, target_channel):
        """Generate the actual schedule data"""
        sequential_progress = {}
        schedule = {"weekly": {day: [] for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}}
        
        for day_index, day_name in enumerate(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
            for block_name, block_config in self.block_configs.items():
                collection_group_name = block_config["collection_var"].get() # e.g., "horror"
                if not collection_group_name: continue
                    
                # Get the list of collections in this group
                collection_group = self.collections.get(collection_group_name)
                if not collection_group: continue
                
                # Flatten all videos from all collections in this group into one list
                all_videos_in_group = []
                for collection in collection_group:
                    if collection.get("videos"):
                        all_videos_in_group.extend(collection["videos"])

                if not all_videos_in_group: continue
                
                start_time = datetime.strptime(block_config["start"], "%H:%M")
                end_time = datetime.strptime(block_config["end"], "%H:%M")
                if end_time <= start_time: end_time += timedelta(days=1)
                
                duration_seconds = (end_time - start_time).total_seconds()
                mode = block_config["mode_var"].get()
                
                videos_to_schedule = []
                if mode == "sequential":
                    # Sequential mode is now tricky. We need to track progress across the entire group.
                    # Let's initialize a progress tracker for the group if it doesn't exist
                    if collection_group_name not in sequential_progress:
                        sequential_progress[collection_group_name] = 0
                    
                    current_pos = sequential_progress[collection_group_name]
                    total_duration = 0
                    while total_duration < duration_seconds and current_pos < len(all_videos_in_group):
                        video = all_videos_in_group[current_pos]
                        videos_to_schedule.append(video)
                        total_duration += video.get("duration", 5400)
                        current_pos += 1
                    
                    # Update the position for the next day
                    sequential_progress[collection_group_name] = current_pos % len(all_videos_in_group)
                else: # random
                    total_duration = 0
                    while total_duration < duration_seconds:
                        videos_to_schedule.append(random.choice(all_videos_in_group))
                        total_duration += videos_to_schedule[-1].get("duration", 5400)
                
                current_time = start_time
                for video in videos_to_schedule:
                    video_duration = video.get("duration", 5400)
                    video_end = current_time + timedelta(seconds=video_duration)
                    if video_end > end_time: break
                    
                    schedule["weekly"][day_name].append({
                        "time": current_time.strftime("%H:%M:%S"),
                        "file": video["path"],
                        "channel": target_channel,
                        "source": mode,
                        "collection": collection_group_name, # Store the group name
                        "block": block_name
                    })
                    current_time = video_end
            
            schedule["weekly"][day_name].sort(key=lambda x: x["time"])
        
        return schedule

def launch_daypart_scheduler():
    root = tk.Tk()
    app = DaypartSchedulerWizard(root)
    root.mainloop()

if __name__ == "__main__":
    launch_daypart_scheduler()