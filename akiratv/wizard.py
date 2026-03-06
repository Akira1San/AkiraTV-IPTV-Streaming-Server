# akiratv/wizard.py (partial - time grid implementation)
import tkinter as tk
from tkinter import ttk, messagebox
import json
import re
from pathlib import Path
import random
from datetime import datetime, timedelta
import subprocess

BASE_DIR = Path(__file__).resolve().parents[1]
USER_DIR = BASE_DIR / "user"

SCHEDULE_DIR = USER_DIR / "schedules"
COLLECTIONS_DIR = USER_DIR / "collections"

SCHEDULE_DIR.mkdir(parents=True, exist_ok=True)
COLLECTIONS_DIR.mkdir(parents=True, exist_ok=True)

COLLECTIONS_FILE = COLLECTIONS_DIR / "collections.json"


# Optional: Try to use ffprobe for accurate duration
HAVE_FFPROBE = False
try:
    import subprocess
    subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
    HAVE_FFPROBE = True
except:
    pass

def load_collections():
    try:
        if not COLLECTIONS_FILE.exists():
            return []

        with open(COLLECTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("collections", [])
    except Exception as e:
        print("Failed to load collections:", e)
        return []

def resolve_chunks(base_path: str):
    """Resolve chunked files (copied from chunk_resolver.py for simplicity)"""
    base = Path(base_path)
    parent = base.parent
    stem = base.name

    if base.with_suffix(".mp4").exists():
        return [base.with_suffix(".mp4")]

    pattern = re.compile(rf"^{re.escape(stem)}(?:_(?:part|chunk))?_?(\d+)(\.\w+)$", re.IGNORECASE)
    matches = []
    for file in parent.iterdir():
        if file.is_file():
            match = pattern.match(file.name)
            if match:
                matches.append((int(match.group(1)), file))
    if matches:
        matches.sort(key=lambda x: x[0])
        return [f for _, f in matches]
    fallback = base.with_suffix(".mp4")
    if fallback.exists():
        return [fallback]
    return []

def get_entry_duration(base_path: str) -> float:
    """Get total duration of ALL chunks for a schedule entry."""
    chunks = resolve_chunks(base_path)
    if not chunks:
        return 1800.0  # 30 minutes fallback

    if HAVE_FFPROBE:
        total = 0.0
        for chunk in chunks:
            try:
                result = subprocess.run([
                    "ffprobe", "-v", "error", "-show_entries",
                    "format=duration", "-of", "default=nw=1",
                    str(chunk)
                ], capture_output=True, text=True, check=True)
                total += float(result.stdout.strip())
            except:
                total += 1800.0 / len(chunks)  # distribute fallback
        return total
    else:
        # Assume 30 minutes per chunk
        return 1800.0 * len(chunks)

def extract_base_path(video_path: str) -> str:
    """Convert 'video_part01.mp4' -> 'video'"""
    p = Path(video_path)
    stem = p.stem
    match = re.match(r"^(.+?)(?:_(?:part|chunk))?_?\d+$", stem, re.IGNORECASE)
    base_stem = match.group(1) if match else stem
    return str(p.parent / base_stem)

class WeeklyScheduleWizard:
    def __init__(self, root):
        self.root = root
        self.root.title("AkiraTV — 7-Day Time Block Scheduler")
        self.root.geometry("1200x700")
        self.root.resizable(True, True)

        self.days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        self.day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        self.all_entries = {day: [] for day in self.days}
        self.collections = load_collections()
        self.selected_day = None
        self.selected_time = None

        self.load_schedule()
        self.create_widgets()

    def create_widgets(self):
        # Main two-panel layout
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Left: Collections
        left_frame = ttk.LabelFrame(main_frame, text="Collections")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0,5))
        self.collection_list = tk.Listbox(left_frame, width=35)
        self.collection_list.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Populate collections
        for col in self.collections:
            self.collection_list.insert(tk.END, f"{col['name']} ({len(col['videos'])} videos)")

        # Right: 7-Day Time Grid (with scrollbar)
        right_frame = ttk.LabelFrame(main_frame, text="7-Day Schedule")
        right_frame.pack(side="right", fill="both", expand=True, padx=(5,0))

        # Canvas with scrollbar for 7-day grid
        canvas = tk.Canvas(right_frame)
        scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Create time grid for each day
        self.day_frames = {}
        self.time_buttons = {}
        for day in self.days:
            day_frame = ttk.LabelFrame(scrollable_frame, text=day.title())
            day_frame.pack(fill="x", padx=5, pady=2)
            self.day_frames[day] = day_frame
            
            # Create 24 time buttons (00:00 to 23:00) - VERTICAL layout
            time_frame = ttk.Frame(day_frame)
            time_frame.pack(fill="x", padx=2, pady=2)
            
            self.time_buttons[day] = {}
            for hour in range(24):
                time_str = f"{hour:02d}:00"
                
                # Safe lambda capture
                def make_command(d, t):
                    return lambda: self.on_time_click(d, t)
                command=make_command(day, time_str)
                
                btn = tk.Button(
                    time_frame, 
                    text=time_str,
                    width=8,
                    height=1,
                    command=make_command(day, time_str)
                )
                btn.pack(side="top", padx=2, pady=1)
                self.time_buttons[day][time_str] = btn

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bottom buttons
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(padx=10, pady=5)
        ttk.Button(bottom_frame, text="+ Add from Collections", command=self.open_collection_picker).pack(side="left", padx=5)
        ttk.Button(bottom_frame, text="Save to schedule.json", command=self.save_schedule).pack(side="left", padx=5)
        ttk.Button(bottom_frame, text="Cancel", command=self.root.destroy).pack(side="left", padx=5)

        self.refresh_all_days()

    def on_time_click(self, day, time_slot):
        """Handle time block click"""
        self.selected_day = day
        self.selected_time = time_slot
        print(f"⏰ Selected: {day} at {time_slot}")

    def open_collection_picker(self):
        """Open modal window to select videos from collections"""
        if not hasattr(self, 'selected_day') or not hasattr(self, 'selected_time'):
            messagebox.showwarning("No Time Selected", "Click a time block first!")
            return
            
        picker = tk.Toplevel(self.root)
        picker.title("Select Videos from Collections")
        picker.geometry("700x500")
        
        # Collections list
        left_frame = ttk.LabelFrame(picker, text="Collections")
        left_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        collection_list = tk.Listbox(left_frame, width=30)
        collection_list.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Videos list
        right_frame = ttk.LabelFrame(picker, text="Videos")
        right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        video_list = tk.Listbox(right_frame, selectmode=tk.EXTENDED)
        video_list.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Store video paths separately
        _video_paths = []
        
        # Load collections
        #collections = load_collections()
        for col in collections:
            collection_list.insert(tk.END, col["name"])
        
        # Handle collection selection
        def on_collection_select(event):
            video_list.delete(0, tk.END)
            _video_paths.clear()
            if not collection_list.curselection():
                return
            idx = collection_list.curselection()[0]
            col = collections[idx]
            for video in col["videos"]:
                name = Path(video["path"]).name
                duration = self.format_duration(video.get("duration"))
                display = f"{name} [{duration}]"
                video_list.insert(tk.END, display)
                _video_paths.append(video["path"])

        collection_list.bind("<<ListboxSelect>>", on_collection_select)
        
        # Add button
        def add_selected():
            if not video_list.curselection():
                messagebox.showwarning("No Video Selected", "Select a video first!")
                return
            
            # Use the current selected day/time from the main window
            current_day = self.selected_day
            current_time = self.selected_time
            
            print(f"[PLAY] DEBUG: Adding to {current_day} at {current_time}")
            
            for idx in video_list.curselection():
                if idx < len(_video_paths):
                    path = _video_paths[idx]
                    self.add_video_to_time(current_day, current_time, path)
            picker.destroy()
        
        ttk.Button(picker, text="Add Selected", command=add_selected).pack(pady=10)

    def add_video_to_time(self, day, time_slot, video_path):
        """Add video to specific day/time"""
        # Parse time_slot (e.g., "13:00")
        hour = int(time_slot.split(":")[0])
        start_time = f"{hour:02d}:00:00"
        
        # Create entry
        if day not in self.all_entries:
            self.all_entries[day] = []
        
        self.all_entries[day].append({
            "time": start_time,
            "file": video_path,
            "channel": "critters",
            "source": "manual"
        })
        
        # Update visual feedback
        self.refresh_day(day)
        messagebox.showinfo("Added", f"Added to {day.title()} at {time_slot}")

    def refresh_all_days(self):
        """Refresh all day grids"""
        for day in self.days:
            self.refresh_day(day)

    def refresh_day(self, day):
        """Refresh specific day grid"""
        # Update button colors based on assignments
        entries_for_day = self.all_entries.get(day, [])
        assigned_hours = set()
        for entry in entries_for_day:
            hour = entry["time"].split(":")[0]
            assigned_hours.add(f"{int(hour):02d}:00")
        
        for time_str, btn in self.time_buttons[day].items():
            if time_str in assigned_hours:
                btn.config(bg="lightblue", fg="black")
            else:
                btn.config(bg="SystemButtonFace", fg="black")  # Default color

    # ... (keep your existing load_schedule, save_schedule, etc.) ...

    def load_schedule(self):
        schedule_file = SCHEDULE_DIR / "schedule.json"
        if not schedule_file.exists():
            return

        try:
            with open(schedule_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            weekly = data.get("weekly", {})
            for day in self.days:
                self.all_entries[day] = weekly.get(day, [])

        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load schedule:\n{e}")

    def save_schedule(self):
        schedule_file = SCHEDULE_DIR / "schedule.json"

        try:
            data = {}
            if schedule_file.exists():
                with open(schedule_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

            data["weekly"] = self.all_entries

            with open(schedule_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            messagebox.showinfo("Success", "Weekly schedule saved!")
            self.root.destroy()

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save:\n{e}")

    def on_day_change(self, event=None):
        day_key = self.day_var.get().lower()
        if day_key in self.days:
            self.day_var.set(day_key)
            self.load_schedule()
            self.refresh_tree()

    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for entry in self.entries:
            self.tree.insert("", "end", values=(entry["time"][:5], entry["file"]))

    def add_entry(self):
        time_str = "00:00"
        if self.entries:
            last_time = self.entries[-1]["time"]
            h, m, s = map(int, last_time.split(":"))
            new_time = (datetime(2000,1,1,h,m,s) + timedelta(minutes=30)).time()
            time_str = new_time.strftime("%H:%M")
        
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mp4 *.mkv *.avi *.mov")]
        )
        if not file_path:
            return

        try:
            rel_path = Path(file_path).relative_to(Path.cwd())
            base_path = extract_base_path(str(rel_path))
        except:
            base_path = extract_base_path(file_path)
    
        self.entries.append({"time": f"{time_str}:00", "file": str(base_path), "channel": "critters"})
        self.refresh_tree()

    def remove_selected(self):
        selected = self.tree.selection()
        indices = [self.tree.index(item) for item in selected]
        for i in sorted(indices, reverse=True):
            del self.entries[i]
        self.refresh_tree()

    def move_entry(self, direction):
        selected = self.tree.selection()
        if not selected:
            return
        index = self.tree.index(selected[0])
        new_index = index + direction
        if 0 <= new_index < len(self.entries):
            self.entries[index], self.entries[new_index] = self.entries[new_index], self.entries[index]
            self.refresh_tree()
            self.tree.selection_set(self.tree.get_children()[new_index])

    def randomize_entries(self):
        if not self.entries:
            return
        random.shuffle(self.entries)
        current = datetime(2000, 1, 1, 0, 0)
        for entry in self.entries:
            entry["time"] = current.strftime("%H:%M:%S")
            duration = get_entry_duration(entry["file"])
            current += timedelta(seconds=duration)
        self.refresh_tree()

    def fill_day(self):
        if not self.entries:
            messagebox.showwarning("No Videos", "Add at least one video first.")
            return

        if messagebox.askyesno("Confirm Fill Day", 
            f"This will replace all entries for {self.day_var.get().title()} with a 24-hour loop.\nProceed?"):
            
            # Calculate real durations
            entry_durations = []
            for entry in self.entries:
                duration = get_entry_duration(entry["file"])
                entry_durations.append(duration)

            # Generate 24h schedule
            new_entries = []
            current = datetime(2000, 1, 1, 0, 0)
            end_time = datetime(2000, 1, 2, 0, 0)

            while current < end_time:
                for i, entry in enumerate(self.entries):
                    if current >= end_time:
                        break
                    new_entry = entry.copy()
                    new_entry["time"] = current.strftime("%H:%M:%S")
                    new_entries.append(new_entry)
                    current += timedelta(seconds=entry_durations[i])

            self.entries = new_entries
            self.refresh_tree()

class TimePickerWindow:
    def __init__(self, parent, day, time_slot, collections, main_wizard):
        self.parent = parent
        self.day = day
        self.time_slot = time_slot
        self.collections = collections
        self.main_wizard = main_wizard
        
        self.picker = tk.Toplevel(parent)
        self.picker.title("Select Videos from Collections")
        self.picker.geometry("700x500")
        
        # Collections list
        left_frame = ttk.LabelFrame(self.picker, text="Collections")
        left_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.collection_list = tk.Listbox(left_frame, width=30)
        self.collection_list.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Videos list
        right_frame = ttk.LabelFrame(self.picker, text="Videos")
        right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        self.video_list = tk.Listbox(right_frame, selectmode=tk.EXTENDED)
        self.video_list.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Store video paths
        self._video_paths = []
        
        # Load collections
        for col in self.collections:
            self.collection_list.insert(tk.END, col["name"])
        
        # Handle collection selection
        self.collection_list.bind("<<ListboxSelect>>", self.on_collection_select)
        
        # Add button
        ttk.Button(self.picker, text="Add Selected", command=self.add_selected).pack(pady=10)

    def on_collection_select(self, event):
        self.video_list.delete(0, tk.END)
        self._video_paths.clear()
        if not self.collection_list.curselection():
            return
        idx = self.collection_list.curselection()[0]
        col = self.collections[idx]
        for video in col["videos"]:
            name = Path(video["path"]).name
            duration = self.main_wizard.format_duration(video.get("duration"))
            display = f"{name} [{duration}]"
            self.video_list.insert(tk.END, display)
            self._video_paths.append(video["path"])

    def add_selected(self):
        if not self.video_list.curselection():
            messagebox.showwarning("No Video Selected", "Select a video first!")
            return
            
        print(f"[PLAY] DEBUG: Adding to {self.day} at {self.time_slot}")
        
        for idx in self.video_list.curselection():
            if idx < len(self._video_paths):
                path = self._video_paths[idx]
                self.main_wizard.add_video_to_time(self.day, self.time_slot, path)
        self.picker.destroy()
    
    def show(self):
        self.picker.grab_set()  # Modal window
        self.picker.wait_window()

def format_duration(self, seconds):
    if not seconds:
        return "??:??"
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def launch_wizard():
    root = tk.Tk()
    app = WeeklyScheduleWizard(root)
    root.mainloop()