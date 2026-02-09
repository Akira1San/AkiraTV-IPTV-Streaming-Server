# akiratv/simple_scheduler.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image, ImageTk
import configparser

BASE_DIR = Path(__file__).resolve().parents[1]
USER_DIR = BASE_DIR / "user"
SCHEDULE_DIR = USER_DIR / "schedules"
COVERS_DIR = USER_DIR / "covers"
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

def load_blacklist(profile_name="collections"):
    """Load blacklist from INI file matching the profile name"""
    try:
        script_dir = Path(__file__).resolve().parent
        base_dir = script_dir.parent
        collections_dir = base_dir / "user" / "collections"
        
        # Try to find the INI file
        ini_file = collections_dir / f"{profile_name}.ini"
        if not ini_file.exists():
            ini_file = collections_dir / f"collections_{profile_name}.ini"
        
        if not ini_file.exists():
            ini_file = script_dir / f"{profile_name}.ini"
            if not ini_file.exists():
                ini_file = script_dir / f"collections_{profile_name}.ini"
        
        if ini_file.exists():
            config = configparser.ConfigParser()
            config.read(ini_file, encoding="utf-8")
            
            if "Blacklist" in config:
                return set(config["Blacklist"].get("videos", "").splitlines())
        return set()
    except Exception as e:
        print(f"Error loading blacklist: {e}")
        return set()

def save_blacklist(profile_name="collections", blacklisted_videos=None):
    """Save blacklist to INI file matching the profile name"""
    if blacklisted_videos is None:
        blacklisted_videos = set()
    
    try:
        script_dir = Path(__file__).resolve().parent
        base_dir = script_dir.parent
        collections_dir = base_dir / "user" / "collections"
        
        # Determine the INI file path (matching the profile file location)
        profile_file = collections_dir / f"{profile_name}.json"
        if not profile_file.exists():
            profile_file = collections_dir / f"collections_{profile_name}.json"
        
        ini_file = profile_file.with_suffix(".ini")
        
        config = configparser.ConfigParser()
        config["Blacklist"] = {
            "videos": "\n".join(blacklisted_videos)
        }
        
        with open(ini_file, "w", encoding="utf-8") as f:
            config.write(f)
            
        return True
    except Exception as e:
        print(f"Error saving blacklist: {e}")
        return False

class SimpleSchedulerWizard:
    def __init__(self, root):
        self.root = root
        self.root.title("AkiraTV — Simple Random Scheduler")
        self.root.geometry("1600x800")
        
        # Data structures
        self.collections = []
        self.current_profile = "collections"  # Default profile
        self.current_schedule = None  # Store generated schedule for preview
        self.current_channel = None
        self.current_mode = None
        
        # New data structures for the redesigned UI
        self.added_videos = []  # List of video objects user has added
        self.video_to_collection_map = {}  # Map video path -> collection object
        self.selected_video = None  # Currently selected video for info panel
        self.selected_collection = None  # Currently selected collection (for info panel)
        self.selected_collections = []  # List of selected collections (for multiselect)
        self.blacklisted_videos = set()  # Set of video paths that are blacklisted
        
        self.create_widgets()

    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create horizontal PanedWindow for main layout (info/collection/added/preview)
        self.main_paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill="both", expand=True, pady=(0, 10))
        
        # === LEFT PANE: INFO PANEL ===
        info_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(info_frame, weight=2)
        self.create_info_panel(info_frame)
        
        # === SECOND PANE: COLLECTION PANEL ===
        collection_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(collection_frame, weight=1)
        self.create_collection_panel(collection_frame)
        
        # === THIRD PANE: ADDED PANEL ===
        added_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(added_frame, weight=2)
        self.create_added_panel(added_frame)
        
        # === FOURTH PANE: PREVIEW PANEL ===
        preview_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(preview_frame, weight=2)
        self.create_preview_panel(preview_frame)
        
        # === BOTTOM CONTROL BAR ===
        self.create_bottom_controls(main_frame)

    def create_info_panel(self, parent):
        """Create the Info panel for displaying video metadata"""
        # Main container for info panel
        info_container = ttk.Frame(parent)
        info_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        ttk.Label(info_container, text="Video Info", font=("TkDefaultFont", 12, "bold")).pack(pady=(0, 10))
        
        # Cover image - use tk.Label for image support with fixed size
        cover_frame = ttk.Frame(info_container)
        cover_frame.pack(pady=5, fill="x")
        self.cover_label = tk.Label(cover_frame, text="No video selected", 
                                   font=("TkDefaultFont", 9), foreground="gray",
                                   relief="solid", borderwidth=1)
        self.cover_label.pack()
        
        # Metadata labels
        metadata_frame = ttk.Frame(info_container)
        metadata_frame.pack(fill="both", expand=True)
        
        self.info_name = ttk.Label(metadata_frame, text="Name: -", font=("TkDefaultFont", 10, "bold"))
        self.info_name.pack(anchor="w", pady=2)
        
        self.info_description = ttk.Label(metadata_frame, text="Description: -", 
                                         font=("TkDefaultFont", 9), wraplength=400)
        self.info_description.pack(anchor="w", pady=2)
        
        self.info_genre = ttk.Label(metadata_frame, text="Genre: -", font=("TkDefaultFont", 9))
        self.info_genre.pack(anchor="w", pady=2)
        
        self.info_year = ttk.Label(metadata_frame, text="Year: -", font=("TkDefaultFont", 9))
        self.info_year.pack(anchor="w", pady=2)
        
        ttk.Separator(metadata_frame, orient="horizontal").pack(fill="x", pady=10)
        
        self.info_path = ttk.Label(metadata_frame, text="Path: -", font=("TkDefaultFont", 9), 
                                   wraplength=400, foreground="gray")
        self.info_path.pack(anchor="w", pady=2)
        
        self.info_duration = ttk.Label(metadata_frame, text="Duration: -", font=("TkDefaultFont", 9))
        self.info_duration.pack(anchor="w", pady=2)

    def create_collection_panel(self, parent):
        """Create the Collection panel with tabs for collections and standby"""
        # Main container for collection panel
        collection_container = ttk.Frame(parent)
        collection_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        ttk.Label(collection_container, text="Collection & Standby", font=("TkDefaultFont", 12, "bold")).pack(pady=(0, 10))
        
        # Create tab control
        self.tab_control = ttk.Notebook(collection_container)
        self.tab_control.pack(fill="both", expand=True, pady=(0, 10))
        
        # === COLLECTIONS TAB ===
        collections_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(collections_tab, text="Collections")
        
        # Profile selection
        profile_frame = ttk.Frame(collections_tab)
        profile_frame.pack(fill="x", pady=(0, 10))
        
        # First row: Collection Profile dropdown
        profile_row1 = ttk.Frame(profile_frame)
        profile_row1.pack(fill="x", pady=(0, 5))
        ttk.Label(profile_row1, text="Profile:").pack(side="left")
        self.quick_profile_var = tk.StringVar(value="")
        self.profile_dropdown = ttk.Combobox(profile_row1, textvariable=self.quick_profile_var, 
                                           values=self.get_available_collections(), 
                                           state="readonly", width=15)
        self.profile_dropdown.pack(side="left", padx=5)
        self.profile_dropdown.bind("<<ComboboxSelected>>", self.on_quick_profile_select)
        ttk.Button(profile_row1, text="🔄", command=self.refresh_collections_dropdown, width=3).pack(side="left")
        
        # Second row: Manual entry
        profile_row2 = ttk.Frame(profile_frame)
        profile_row2.pack(fill="x")
        ttk.Label(profile_row2, text="Or type:").pack(side="left")
        self.profile_var = tk.StringVar(value=self.current_profile)
        profile_entry = ttk.Entry(profile_row2, textvariable=self.profile_var, width=12)
        profile_entry.pack(side="left", padx=5)
        ttk.Button(profile_row2, text="Load", command=self.load_profile, width=5).pack(side="left")
        
        # Collections list frame (horizontal)
        ttk.Label(collections_tab, text="Collections:").pack(anchor="w")
        collection_list_frame = ttk.Frame(collections_tab)
        collection_list_frame.pack(fill="both", expand=True, pady=5)
        
        self.collection_list = tk.Listbox(collection_list_frame, selectmode=tk.EXTENDED, font=("TkDefaultFont", 11))
        self.collection_list.pack(side="left", fill="both", expand=True)
        collection_scrollbar = ttk.Scrollbar(collection_list_frame, orient="vertical", command=self.collection_list.yview)
        collection_scrollbar.pack(side="right", fill="y")
        self.collection_list.configure(yscrollcommand=collection_scrollbar.set)
        self.collection_list.bind("<<ListboxSelect>>", self.on_collection_select)
        
        # === STANDBY TAB ===
        standby_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(standby_tab, text="Standby")
        
        # Standby tab content - placeholder
        ttk.Label(standby_tab, text="Standby Management", font=("TkDefaultFont", 11, "bold")).pack(pady=10)
        ttk.Label(standby_tab, text="Bumper generation and standby settings will be implemented here.", 
                 font=("TkDefaultFont", 10), wraplength=300).pack(pady=5)
        
        # Buttons frame (separate from list)
        btn_frame = ttk.Frame(collection_container)
        btn_frame.pack(fill="x", pady=5)
        ttk.Button(btn_frame, text="Select All", command=self.select_all_collections).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Clear Selection", command=self.clear_collection_selection).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Add Selected Collections", command=self.add_selected_collection).pack(side="left", padx=2)
        
        # Populate collections (from default profile initially)
        self.load_collections_from_profile()

    def create_added_panel(self, parent):
        """Create the Added panel for user-selected videos"""
        # Main container for added panel
        added_container = ttk.Frame(parent)
        added_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        ttk.Label(added_container, text="Added Videos", font=("TkDefaultFont", 12, "bold")).pack(pady=(0, 10))
        
        # Blacklist control
        blacklist_frame = ttk.Frame(added_container)
        blacklist_frame.pack(fill="x", pady=(0, 5))
        ttk.Button(blacklist_frame, text="Add to Blacklist", command=self.apply_blacklist).pack(side="left", padx=5)
        ttk.Button(blacklist_frame, text="Remove from Blacklist", command=self.remove_from_blacklist).pack(side="left", padx=5)
        
        # Added videos list frame (horizontal)
        added_list_frame = ttk.Frame(added_container)
        added_list_frame.pack(fill="both", expand=True, pady=5)
        
        self.added_list = tk.Listbox(added_list_frame, selectmode=tk.EXTENDED, font=("TkDefaultFont", 11))
        self.added_list.pack(side="left", fill="both", expand=True)
        added_scrollbar = ttk.Scrollbar(added_list_frame, orient="vertical", command=self.added_list.yview)
        added_scrollbar.pack(side="right", fill="y")
        self.added_list.configure(yscrollcommand=added_scrollbar.set)
        self.added_list.bind("<<ListboxSelect>>", self.on_added_video_select)
        
        # Count display
        self.added_count_label = ttk.Label(added_container, text="Total: 0 videos", font=("TkDefaultFont", 9))
        self.added_count_label.pack(pady=5)
        
        # Blacklist count display
        self.blacklist_count_label = ttk.Label(added_container, text="Blacklisted: 0 videos", font=("TkDefaultFont", 9))
        self.blacklist_count_label.pack(pady=2)
        
        # Buttons frame (separate from list)
        btn_frame = ttk.Frame(added_container)
        btn_frame.pack(fill="x", pady=5)
        ttk.Button(btn_frame, text="Remove Selected", command=self.remove_selected_videos).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Remove All", command=self.remove_all_videos).pack(side="left", padx=2)

    def create_preview_panel(self, parent):
        """Create the Preview panel for schedule preview"""
        # Main container for preview panel
        preview_container = ttk.Frame(parent)
        preview_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        ttk.Label(preview_container, text="Schedule Preview", font=("TkDefaultFont", 12, "bold")).pack(pady=(0, 10))
        
        # Day selector frame (separate from list)
        day_frame = ttk.Frame(preview_container)
        day_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(day_frame, text="View day:").pack(side="left")
        self.day_var = tk.StringVar(value="monday")
        day_combo = ttk.Combobox(day_frame, textvariable=self.day_var, 
                                values=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
                                state="readonly", width=12)
        day_combo.pack(side="left", padx=5)
        day_combo.bind("<<ComboboxSelected>>", self.update_preview_display)
        
        # Copy button
        ttk.Button(day_frame, text="📋 Copy", command=self.copy_schedule, width=8).pack(side="right", padx=5)
        
        # Preview listbox frame (horizontal)
        preview_frame = ttk.Frame(preview_container)
        preview_frame.pack(fill="both", expand=True)
        
        self.preview_list = tk.Listbox(preview_frame, font=("Consolas", 11))
        self.preview_list.pack(side="left", fill="both", expand=True)
        preview_scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview_list.yview)
        preview_scrollbar.pack(side="right", fill="y")
        self.preview_list.configure(yscrollcommand=preview_scrollbar.set)
        
        # Preview info frame (separate from list)
        info_frame = ttk.Frame(preview_container)
        info_frame.pack(fill="x", pady=(5, 0))
        self.preview_info = ttk.Label(info_frame, text="Generate a schedule to see preview", 
                                     font=("TkDefaultFont", 9), foreground="gray")
        self.preview_info.pack()

    def create_bottom_controls(self, parent):
        """Create bottom control bar with channel selection and action buttons"""
        bottom_frame = ttk.Frame(parent)
        bottom_frame.pack(fill="x", pady=(10, 0))
        
        # Channel selection and episodic checkbox on one line
        chan_episodic_frame = ttk.Frame(bottom_frame)
        chan_episodic_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(chan_episodic_frame, text="Channel:").pack(side="left")
        self.channel_var = tk.StringVar(value="critters")
        chan_combo = ttk.Combobox(chan_episodic_frame, textvariable=self.channel_var,
                                 values=self.get_known_channels(), width=12)
        chan_combo.set("critters")
        chan_combo.pack(side="left", padx=5)

        self.episodic_var = tk.BooleanVar(value=False)
        episodic_check = ttk.Checkbutton(chan_episodic_frame, text="Auto-detect episodic content",
                                        variable=self.episodic_var)
        episodic_check.pack(side="left", padx=10)
        self.create_tooltip(episodic_check, "Groups videos into series (e.g., MySeries S01E01, S01E02) and treats them as episodic content.")

        self.sequential_var = tk.BooleanVar(value=False)
        sequential_check = ttk.Checkbutton(chan_episodic_frame, text="Sequential Episode Tracking",
                                          variable=self.sequential_var)
        sequential_check.pack(side="left", padx=10)
        self.create_tooltip(sequential_check, "When the same series is picked multiple times, plays episodes in order (1→2→3→loop). Session-based only.")

        # Schedule mode selection (Weekly/Calendar)
        mode_frame = ttk.Frame(chan_episodic_frame)
        mode_frame.pack(side="left", padx=20)

        ttk.Label(mode_frame, text="Mode:").pack(side="left")
        self.schedule_mode_var = tk.StringVar(value="weekly")
        ttk.Radiobutton(mode_frame, text="Weekly", variable=self.schedule_mode_var,
                        value="weekly", command=self.on_schedule_mode_change).pack(side="left", padx=2)
        ttk.Radiobutton(mode_frame, text="Calendar", variable=self.schedule_mode_var,
                        value="calendar", command=self.on_schedule_mode_change).pack(side="left", padx=2)

        # Calendar date range (hidden by default)
        calendar_frame = ttk.Frame(chan_episodic_frame)
        calendar_frame.pack(side="left", padx=10)
        self.calendar_frame = calendar_frame

        ttk.Label(calendar_frame, text="From:").pack(side="left")
        self.start_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        start_date_entry = ttk.Entry(calendar_frame, textvariable=self.start_date_var, width=10)
        start_date_entry.pack(side="left", padx=2)

        ttk.Label(calendar_frame, text="To:").pack(side="left")
        self.end_date_var = tk.StringVar(value=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"))
        end_date_entry = ttk.Entry(calendar_frame, textvariable=self.end_date_var, width=10)
        end_date_entry.pack(side="left", padx=2)

        # Hide calendar frame initially
        calendar_frame.pack_forget()

        # Preview buttons and save button on one line
        preview_frame = ttk.Frame(bottom_frame)
        preview_frame.pack(fill="x")
        
        ttk.Button(preview_frame, text="🎲 Preview Random", 
                  command=lambda: self.preview_schedule(mode="random")).pack(side="left", padx=5)
        
        ttk.Button(preview_frame, text="▶ Preview Sequential", 
                  command=lambda: self.preview_schedule(mode="sequential")).pack(side="left", padx=5)
        
        ttk.Separator(preview_frame, orient="vertical").pack(side="left", fill="y", padx=10)
        
        self.save_button = ttk.Button(preview_frame, text="💾 Save Schedule", 
                  command=self.save_current_schedule, state="disabled")
        self.save_button.pack(side="left")

    # === INFO PANEL METHODS ===
    
    def update_info_panel(self, video_data):
        """Update info panel with selected video data"""
        if not video_data:
            self.clear_info_panel()
            return
        
        collection = video_data.get("collection", {})
        
        # Update cover image
        self.load_cover_image(collection.get("id"))
        
        # Update metadata labels
        self.info_name.configure(text=f"Name: {collection.get('name', '-')}")
        self.info_description.configure(text=f"Description: {collection.get('description', '-')}")
        
        genre = collection.get('genre', [])
        genre_str = ', '.join(genre) if genre else '-'
        self.info_genre.configure(text=f"Genre: {genre_str}")
        
        self.info_year.configure(text=f"Year: {collection.get('year', '-')}")
        
        self.info_path.configure(text=f"Path: {video_data.get('path', '-')}")
        
        duration = video_data.get('duration', 0)
        self.info_duration.configure(text=f"Duration: {self.format_duration(duration)}")
    
    def clear_info_panel(self):
        """Clear the info panel"""
        self.cover_label.configure(image="", text="No video selected")
        self.info_name.configure(text="Name: -")
        self.info_description.configure(text="Description: -")
        self.info_genre.configure(text="Genre: -")
        self.info_year.configure(text="Year: -")
        self.info_path.configure(text="Path: -")
        self.info_duration.configure(text="Duration: -")
    
    def load_cover_image(self, collection_id):
        """Load cover image from user/covers directory"""
        if not collection_id:
            self.cover_label.configure(image="", text="No cover")
            return
        
        # Try to find cover image
        cover_path = None
        for ext in ['.jpg', '.jpeg', '.png']:
            potential_path = COVERS_DIR / f"{collection_id}{ext}"
            if potential_path.exists():
                cover_path = potential_path
                break
        
        if cover_path:
            try:
                # Load and resize image
                img = Image.open(cover_path)
                img = img.resize((300, 420), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.cover_label.configure(image=photo, text="")
                self.cover_label.image = photo  # Keep reference
            except Exception as e:
                print(f"Error loading cover image: {e}")
                self.cover_label.configure(image="", text="No cover")
        else:
            self.cover_label.configure(image="", text="No cover")
    
    def format_duration(self, seconds):
        """Format duration in seconds to HH:MM:SS"""
        if not seconds:
            return "-"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    # === COLLECTION PANEL METHODS ===
    
    def on_collection_select(self, event):
        """Handle collection selection - update info panel with first video"""
        selection = self.collection_list.curselection()
        if not selection:
            self.clear_info_panel()
            self.selected_collection = None
            return
        
        # Store all selected collections
        self.selected_collections = [self.collections[idx] for idx in selection]
        # Use first selected collection for info panel
        self.selected_collection = self.selected_collections[0]
        
        # Update info panel with first video from first selected collection
        videos = self.selected_collection.get("videos", [])
        if videos:
            video = videos[0]
            video_data = {
                "path": video.get("path", ""),
                "duration": video.get("duration", 0),
                "name": Path(video.get("path", "")).name,
                "collection": self.selected_collection
            }
            self.selected_video = video_data
            self.update_info_panel(video_data)
        else:
            self.clear_info_panel()
    
    def add_selected_collection(self):
        """Add all videos from selected collections to added list"""
        if not self.selected_collections:
            messagebox.showwarning("No Collection", "Select a collection first!")
            return
        
        added_count = 0
        for collection in self.selected_collections:
            for video in collection.get("videos", []):
                video_path = video.get("path", "")
                
                # Check if already added
                if video_path not in [v["path"] for v in self.added_videos]:
                    video_data = {
                        "path": video_path,
                        "duration": video.get("duration", 0),
                        "name": Path(video_path).name,
                        "collection": collection
                    }
                    self.added_videos.append(video_data)
                    self.video_to_collection_map[video_path] = collection
                    added_count += 1
        
        if added_count > 0:
            self.update_added_list_display()
            messagebox.showinfo("Success", f"Added {added_count} video(s) from {len(self.selected_collections)} collection(s)!")
        else:
            messagebox.showinfo("Info", "All videos from selected collections are already in the added list.")

    # === ADDED PANEL METHODS ===
    
    def update_added_list_display(self):
        """Update added videos listbox"""
        self.added_list.delete(0, tk.END)
        for video in self.added_videos:
            collection_name = video.get("collection", {}).get("name", "Unknown")
            video_name = video.get("name", "Unknown")
            if video["path"] in self.blacklisted_videos:
                display_text = f"[BLACKLISTED] {collection_name} - {video_name}"
            else:
                display_text = f"{collection_name} - {video_name}"
            self.added_list.insert(tk.END, display_text)
        
        self.added_count_label.configure(text=f"Total: {len(self.added_videos)} videos")
        self.update_blacklist_count()
    
    def remove_selected_videos(self):
        """Remove selected videos from added list"""
        selection = self.added_list.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Select at least one video to remove!")
            return
        
        # Remove in reverse order to maintain indices
        for idx in sorted(selection, reverse=True):
            video = self.added_videos[idx]
            video_path = video.get("path", "")
            if video_path in self.video_to_collection_map:
                del self.video_to_collection_map[video_path]
            del self.added_videos[idx]
        
        self.update_added_list_display()
        messagebox.showinfo("Success", f"Removed {len(selection)} video(s)!")
    
    def remove_all_videos(self):
        """Clear entire added list"""
        if not self.added_videos:
            messagebox.showinfo("Info", "Added list is already empty.")
            return
        
        if messagebox.askyesno("Confirm", "Remove all videos from the added list?"):
            self.added_videos.clear()
            self.video_to_collection_map.clear()
            self.update_added_list_display()
            messagebox.showinfo("Success", "All videos removed!")
    
    def apply_blacklist(self):
        """Add selected videos to blacklist"""
        selection = self.added_list.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Select at least one video to blacklist!")
            return
        
        blacklisted_count = 0
        for idx in selection:
            video = self.added_videos[idx]
            video_path = video.get("path", "")
            self.blacklisted_videos.add(video_path)
            blacklisted_count += 1
        
        self.update_blacklist_count()
        messagebox.showinfo("Success", f"Added {blacklisted_count} video(s) to blacklist!")
    
    def remove_from_blacklist(self):
        """Remove selected videos from blacklist"""
        selection = self.added_list.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Select at least one video to remove from blacklist!")
            return
        
        removed_count = 0
        for idx in selection:
            video = self.added_videos[idx]
            video_path = video.get("path", "")
            if video_path in self.blacklisted_videos:
                self.blacklisted_videos.remove(video_path)
                removed_count += 1
        
        self.update_blacklist_count()
        messagebox.showinfo("Success", f"Removed {removed_count} video(s) from blacklist!")
    
    def update_blacklist_count(self):
        """Update the blacklist count display"""
        self.blacklist_count_label.configure(text=f"Blacklisted: {len(self.blacklisted_videos)} videos")
    
    def on_added_video_select(self, event):
        """Handle added video selection - update info panel with selected video"""
        selection = self.added_list.curselection()
        if not selection:
            self.clear_info_panel()
            self.selected_video = None
            return
        
        # Use first selected video for info panel
        idx = selection[0]
        video = self.added_videos[idx]
        self.selected_video = video
        
        # Update info panel with selected video data
        self.update_info_panel(video)

    # === PREVIEW PANEL METHODS ===
    
    def update_preview_display(self, event=None):
        """Update the preview listbox with the selected day's schedule"""
        if not self.current_schedule:
            self.preview_list.delete(0, tk.END)
            return

        selected_day = self.day_var.get()

        # Check if this is calendar mode
        if hasattr(self, 'current_schedule_mode') and self.current_schedule_mode == "calendar":
            calendar = self.current_schedule.get("calendar", {})
            # Look for calendar entry matching selected day
            calendar_key = None
            for key in calendar.keys():
                if key.endswith(f"_{selected_day}"):
                    calendar_key = key
                    break

            self.preview_list.delete(0, tk.END)

            if calendar_key:
                data = calendar[calendar_key]
                self.preview_list.insert(tk.END, f"=== {data['date']} ({data['day']}) ===")
                self.preview_list.insert(tk.END, "")

                for entry in data.get("entries", []):
                    time_str = entry["time"]
                    file_path = entry["file"]
                    file_name = Path(file_path).name
                    if len(file_name) > 40:
                        display_name = file_name[:37] + "..."
                    else:
                        display_name = file_name
                    self.preview_list.insert(tk.END, f"{time_str} - {display_name}")

                self.preview_list.insert(tk.END, "")
                self.preview_list.insert(tk.END, f"Calendar entries: {len(data.get('entries', []))}")
            else:
                self.preview_list.insert(tk.END, f"No calendar entries for {selected_day.title()}")
        else:
            # Weekly mode
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
                if len(file_name) > 40:
                    display_name = file_name[:37] + "..."
                else:
                    display_name = file_name

                self.preview_list.insert(tk.END, f"{time_str} - {display_name}")

            # Add summary
            self.preview_list.insert(tk.END, "")
            self.preview_list.insert(tk.END, f"Total entries: {len(day_schedule)}")
    
    def copy_schedule(self):
        """Copy the current schedule preview to clipboard"""
        if not self.current_schedule:
            messagebox.showinfo("Info", "No schedule to copy. Generate a preview first!")
            return
        
        # Build full schedule text for all days
        schedule_text = f"Schedule for channel: {self.current_channel}\n"
        schedule_text += f"Mode: {self.current_mode}\n"
        schedule_text += "=" * 50 + "\n\n"
        
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for day in days:
            day_schedule = self.current_schedule.get(day, [])
            schedule_text += f"=== {day.upper()} ===\n"
            if day_schedule:
                for entry in day_schedule:
                    time_str = entry["time"]
                    file_path = entry["file"]
                    file_name = Path(file_path).name
                    schedule_text += f"{time_str} - {file_name}\n"
            else:
                schedule_text += "No entries\n"
            schedule_text += "\n"

        # If calendar mode, add calendar entries
        if hasattr(self, 'current_schedule_mode') and self.current_schedule_mode == "calendar":
            calendar = self.current_schedule.get("calendar", {})
            if calendar:
                schedule_text += "=" * 50 + "\n"
                schedule_text += "CALENDAR ENTRIES\n"
                schedule_text += "=" * 50 + "\n\n"
                for date_key in sorted(calendar.keys()):
                    data = calendar[date_key]
                    schedule_text += f"=== {data['date']} ({data['day']}) ===\n"
                    for entry in data.get("entries", []):
                        time_str = entry["time"]
                        file_path = entry["file"]
                        file_name = Path(file_path).name
                        schedule_text += f"{time_str} - {file_name}\n"
                    schedule_text += "\n"

        # Copy to clipboard
        self.root.clipboard_clear()
        self.root.clipboard_append(schedule_text)
        messagebox.showinfo("Copied", "Schedule copied to clipboard!")

    def on_schedule_mode_change(self):
        """Handle schedule mode change (Weekly/Calendar)"""
        if self.schedule_mode_var.get() == "calendar":
            self.calendar_frame.pack(side="left", padx=10)
        else:
            self.calendar_frame.pack_forget()

    # === SCHEDULE GENERATION METHODS ===

    def _generate_calendar_schedule(self, mode, start_date, end_date, target_channel):
        """Generate calendar schedule for a date range (using same timing logic as weekly)"""
        calendar = {}

        # Calculate total days and duration needed
        total_days = (end_date - start_date).days + 1
        total_duration_needed = total_days * 24 * 3600

        # Filter out blacklisted videos first
        filtered_videos = [v for v in self.added_videos if v["path"] not in self.blacklisted_videos]
        if not filtered_videos:
            messagebox.showwarning("No Available Videos", "All videos are blacklisted!")
            return {"calendar": {}}

        # Generate schedule entries directly using calendar dates
        current_time = datetime(start_date.year, start_date.month, start_date.day, 0, 0)  # Start at midnight on start date
        total_seconds_needed = total_days * 24 * 3600

        if mode == "random":
            # Use random generation - but track dates instead of weekly
            recent_videos = []  # Track videos played in last 24 hours
            no_repeat_hours = 24 * 3600  # 24 hours in seconds

            # Detect episodic content if enabled
            if self.episodic_var.get():
                episodic_groups, standalone_videos = self.detect_episodic_content(filtered_videos)
                episode_trackers = {series: 0 for series in episodic_groups.keys()}
            else:
                episodic_groups = {}
                standalone_videos = filtered_videos
                episode_trackers = {}

            while (current_time - datetime(start_date.year, start_date.month, start_date.day, 0, 0)).total_seconds() < total_seconds_needed:
                # Clean up recent_videos
                current_seconds = (current_time - datetime(start_date.year, start_date.month, start_date.day, 0, 0)).total_seconds()
                recent_videos = [(path, time) for path, time in recent_videos 
                               if current_seconds - time < no_repeat_hours]
                
                recent_paths = {path for path, _ in recent_videos}
                
                # Choose next video
                if self.episodic_var.get() and episodic_groups:
                    available_standalone = [v for v in standalone_videos if v["path"] not in recent_paths]
                    available_series = [series for series in episodic_groups.keys() 
                                      if episodic_groups[series][episode_trackers[series]]["path"] not in recent_paths]
                    
                    if not available_standalone and not available_series:
                        recent_videos = []
                        recent_paths = set()
                        available_standalone = standalone_videos
                        available_series = list(episodic_groups.keys())
                    
                    if available_standalone and available_series:
                        choice_type = random.choice(["standalone", "series"])
                    elif available_standalone:
                        choice_type = "standalone"
                    elif available_series:
                        choice_type = "series"
                    else:
                        choice_type = "standalone"
                    
                    if choice_type == "series" and available_series:
                        series_name = random.choice(available_series)
                        episode_idx = episode_trackers[series_name]
                        
                        if self.sequential_var.get():
                            video = episodic_groups[series_name][episode_idx]
                        else:
                            video = random.choice(episodic_groups[series_name])
                            episode_idx = episodic_groups[series_name].index(video)
                        
                        episode_trackers[series_name] = (episode_idx + 1) % len(episodic_groups[series_name])
                    else:
                        video = random.choice(available_standalone if available_standalone else standalone_videos)
                else:
                    available_videos = [v for v in filtered_videos if v["path"] not in recent_paths]
                    if not available_videos:
                        recent_videos = []
                        available_videos = filtered_videos
                
                    video = random.choice(available_videos)
            
                # Add to calendar schedule
                day_name = current_time.strftime("%A").lower()
                date_str = current_time.strftime("%Y-%m-%d")
                calendar_key = f"{date_str}_{day_name}"
                
                time_str = current_time.strftime("%H:%M:%S")
                
                if calendar_key not in calendar:
                    calendar[calendar_key] = {
                        "date": date_str,
                        "day": day_name.title(),
                        "description": f"Auto-generated calendar schedule",
                        "entries": []
                    }
                
                calendar[calendar_key]["entries"].append({
                    "time": time_str,
                    "file": video["path"],
                    "channel": target_channel,
                    "source": "random"
                })
                
                recent_videos.append((video["path"], current_seconds))
                current_time += timedelta(seconds=video["duration"])
        else:
            # Sequential generation - track dates instead of weekly
            seq_index = 0
            while (current_time - datetime(start_date.year, start_date.month, start_date.day, 0, 0)).total_seconds() < total_seconds_needed:
                video = filtered_videos[seq_index]
                seq_index = (seq_index + 1) % len(filtered_videos)
                
                day_name = current_time.strftime("%A").lower()
                date_str = current_time.strftime("%Y-%m-%d")
                calendar_key = f"{date_str}_{day_name}"
                
                time_str = current_time.strftime("%H:%M:%S")
                
                if calendar_key not in calendar:
                    calendar[calendar_key] = {
                        "date": date_str,
                        "day": day_name.title(),
                        "description": f"Auto-generated calendar schedule",
                        "entries": []
                    }
                
                calendar[calendar_key]["entries"].append({
                    "time": time_str,
                    "file": video["path"],
                    "channel": target_channel,
                    "source": "sequential"
                })
                
                current_time += timedelta(seconds=video["duration"])

        # Sort entries within each day by time
        for calendar_key in calendar:
            calendar[calendar_key]["entries"].sort(key=lambda x: x["time"])

        return {
            "calendar": calendar
        }

    def preview_schedule(self, mode="random"):
        """Generate schedule preview without saving"""
        if not self.added_videos:
            messagebox.showwarning("No Videos", "Add videos to the added list first!")
            return

        target_channel = self.channel_var.get().strip()
        if not target_channel:
            messagebox.showerror("Error", "Please enter a channel name!")
            return

        schedule_mode = self.schedule_mode_var.get()

        if schedule_mode == "calendar":
            # Calendar mode: generate schedule for date range
            try:
                start_date = datetime.strptime(self.start_date_var.get(), "%Y-%m-%d")
                end_date = datetime.strptime(self.end_date_var.get(), "%Y-%m-%d")
                if end_date < start_date:
                    messagebox.showerror("Error", "End date must be after start date!")
                    return
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid date format: {e}")
                return

            new_schedule = self._generate_calendar_schedule(mode, start_date, end_date, target_channel)
            self.current_schedule = new_schedule
            self.current_channel = target_channel
            self.current_mode = mode
            self.current_schedule_mode = "calendar"
            self.update_preview_display()

            # Enable save button
            self.save_button.configure(state="normal")

            # Update info
            episodic_status = " (with episodic)" if self.episodic_var.get() else ""
            total_entries = sum(len(entries) for entries in new_schedule.get("weekly", {}).values())
            calendar_entries = sum(len(data.get("entries", [])) for data in new_schedule.get("calendar", {}).values())
            self.preview_info.configure(text=f"Calendar schedule: {total_entries} weekly + {calendar_entries} calendar entries{episodic_status}")
        else:
            # Weekly mode: generate schedule for one week
            total_duration_needed = 7 * 24 * 3600
            new_schedule = {day: [] for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}

            current_time = datetime(2023, 1, 2, 0, 0)  # Monday 00:00

            if mode == "random":
                self._generate_random_schedule(self.added_videos, new_schedule, current_time, total_duration_needed, target_channel)
            else:  # sequential
                self._generate_sequential_schedule(self.added_videos, new_schedule, current_time, total_duration_needed, target_channel)

            # Store the schedule and update preview
            self.current_schedule = new_schedule
            self.current_channel = target_channel
            self.current_mode = mode
            self.current_schedule_mode = "weekly"
            self.update_preview_display()

            # Enable save button
            self.save_button.configure(state="normal")

            # Update info
            episodic_status = " (with episodic)" if self.episodic_var.get() else ""
            total_entries = sum(len(entries) for entries in new_schedule.values())
            self.preview_info.configure(text=f"{mode.title()} schedule generated: {total_entries} entries{episodic_status}")

    def save_current_schedule(self):
        """Save the currently previewed schedule and the blacklist"""
        if not self.current_schedule:
            messagebox.showwarning("No Schedule", "Generate a preview first!")
            return
        
        self._save_schedule(self.current_schedule, self.current_channel)
        # Save the blacklist to INI file
        if save_blacklist(self.current_profile, self.blacklisted_videos):
            print(f"Blacklist saved to {self.current_profile}.ini")

    def _generate_random_schedule(self, all_videos, new_schedule, current_time, total_duration_needed, target_channel):
        """Generate random schedule with 24-hour no-repeat rule and episodic handling"""
        recent_videos = []  # Track videos played in last 24 hours
        no_repeat_hours = 24 * 3600  # 24 hours in seconds
        
        # Filter out blacklisted videos first
        filtered_videos = [v for v in all_videos if v["path"] not in self.blacklisted_videos]
        if not filtered_videos:
            messagebox.showwarning("No Available Videos", "All videos are blacklisted!")
            return
        
        # Detect episodic content if enabled
        if self.episodic_var.get():
            episodic_groups, standalone_videos = self.detect_episodic_content(filtered_videos)
            episode_trackers = {series: 0 for series in episodic_groups.keys()}  # Track current episode per series
        else:
            episodic_groups = {}
            standalone_videos = filtered_videos
            episode_trackers = {}
        
        while (current_time - datetime(2023, 1, 2, 0, 0)).total_seconds() < total_duration_needed:
            # Clean up recent_videos (remove entries older than 24 hours)
            current_seconds = (current_time - datetime(2023, 1, 2, 0, 0)).total_seconds()
            recent_videos = [(path, time) for path, time in recent_videos 
                           if current_seconds - time < no_repeat_hours]
            
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
                    # Pick a random series
                    series_name = random.choice(available_series)
                    episode_idx = episode_trackers[series_name]
                    
                    # Sequential tracking: always continue from last episode
                    # Otherwise pick random episode if sequential is disabled
                    if self.sequential_var.get():
                        # Continue from last played episode
                        video = episodic_groups[series_name][episode_idx]
                    else:
                        # Pick random episode from series
                        video = random.choice(episodic_groups[series_name])
                        # Find and set the episode index for tracking
                        episode_idx = episodic_groups[series_name].index(video)
                    
                    # Advance episode tracker (loop back to start if at end)
                    episode_trackers[series_name] = (episode_idx + 1) % len(episodic_groups[series_name])
                else:
                    # Pick random standalone video
                    video = random.choice(available_standalone if available_standalone else standalone_videos)
            else:
                # Standard random selection with 24-hour rule
                available_videos = [v for v in filtered_videos if v["path"] not in recent_paths]
                if not available_videos:
                    # Reset if no videos available (emergency fallback)
                    recent_videos = []
                    available_videos = filtered_videos
                
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
        # Filter out blacklisted videos first
        filtered_videos = [v for v in all_videos if v["path"] not in self.blacklisted_videos]
        if not filtered_videos:
            messagebox.showwarning("No Available Videos", "All videos are blacklisted!")
            return
        
        seq_index = 0
        while (current_time - datetime(2023, 1, 2, 0, 0)).total_seconds() < total_duration_needed:
            video = filtered_videos[seq_index]
            seq_index = (seq_index + 1) % len(filtered_videos)

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

        # Check if this is a calendar schedule
        if "calendar" in new_schedule:
            # Calendar mode: save with both calendar and weekly sections
            calendar_data = new_schedule["calendar"]
            weekly_data = new_schedule.get("weekly", {})

            # Sort weekly entries by time
            for day in weekly_data:
                weekly_data[day].sort(key=lambda x: x["time"])

            # Sort calendar entries by time within each date
            for date_key, date_data in calendar_data.items():
                if "entries" in date_data:
                    date_data["entries"].sort(key=lambda x: x["time"])

            final_schedule = {
                "weekly": weekly_data,
                "calendar": calendar_data
            }

            with open(schedule_filename, "w", encoding="utf-8") as f:
                json.dump(final_schedule, f, indent=2, ensure_ascii=False)

            calendar_count = sum(len(data.get("entries", [])) for data in calendar_data.values())
            weekly_count = sum(len(entries) for entries in weekly_data.values())
            episodic_status = " (with episodic)" if self.episodic_var.get() else ""
            messagebox.showinfo("Success", f"Calendar schedule for '{target_channel}': {weekly_count} weekly + {calendar_count} calendar entries saved!{episodic_status}")
        else:
            # Weekly mode: save as before
            new_weekly = {day: [] for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}
            for day, entries in new_schedule.items():
                new_weekly[day] = entries

            # Sort each day's entries by time
            for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                new_weekly[day].sort(key=lambda x: x["time"])

            final_schedule = {"weekly": new_weekly}

            with open(schedule_filename, "w", encoding="utf-8") as f:
                json.dump(final_schedule, f, indent=2, ensure_ascii=False)

            episodic_status = " (with episodic)" if self.episodic_var.get() else ""
            messagebox.showinfo("Success", f"Schedule for '{target_channel}' saved to {schedule_filename}!{episodic_status}")

        # Disable save button after saving
        self.save_button.configure(state="disabled")

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
                r'^(.+?)\s+\d+$',  # Starts with name, ends with single digit (e.g., "Death Wish 1")
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
        final_groups = {k: sorted(v, key=lambda x: self._extract_episode_number(Path(x["path"]).stem))
                       for k, v in episodic_groups.items() if len(v) >= 2}
        
        # Add single-episode "series" back to standalone
        for k, v in episodic_groups.items():
            if len(v) == 1:
                standalone_videos.extend(v)
        
        return final_groups, standalone_videos
    
    def _extract_episode_number(self, filename):
        """Extract episode number from filename for sorting"""
        import re
        # Try various patterns to extract episode number
        patterns = [
            r'[s]\d+[e](\d+)',  # S01E01
            r'(\d+)x\d+',  # 1x01
            r'ep\s*(\d+)',  # Ep 01
            r'episode\s*(\d+)',  # Episode 01
            r'part\s*(\d+)',  # Part 1
            r'(\d+)$',  # Ends with number
        ]
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 0  # Default if no number found

    # === UTILITY METHODS ===
    
    def get_themes(self):
        """Get available ttk themes"""
        try:
            style = ttk.Style()
            available_themes = style.theme_names()
            return sorted(available_themes)
        except:
            return ["default", "clam", "alt", "classic"]

    def create_tooltip(self, widget, text):
        """Create a simple tooltip for a widget using Toplevel"""
        tooltip = tk.Toplevel(self.root)
        tooltip.overrideredirect(True)  # Remove window decorations
        tooltip.attributes("-topmost", True)  # Always on top
        tooltip.withdraw()  # Start hidden
        tooltip.configure(background="#ffffcc", relief="solid", borderwidth=1)
        
        tk.Label(tooltip, text=text, wraplength=300,
                font=("TkDefaultFont", 8), background="#ffffcc").pack(fill="both", expand=True, padx=5, pady=5)

        def show_tooltip(event=None):
            x, y = widget.winfo_rootx() + widget.winfo_width() + 10, widget.winfo_rooty()
            tooltip.geometry(f"+{x}+{y}")
            tooltip.deiconify()

        def hide_tooltip(event=None):
            tooltip.withdraw()

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

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

    def select_all_collections(self):
        """Select all collections in the collection list"""
        self.collection_list.selection_set(0, tk.END)
        # Update selected collections
        self.selected_collections = self.collections.copy()
    
    def clear_collection_selection(self):
        """Clear all selected collections"""
        self.collection_list.selection_clear(0, tk.END)
        self.selected_collections = []
    
    def load_collections_from_profile(self):
        """Load collections from current profile and update UI"""
        self.collections = load_collections(self.current_profile)
        self.collection_list.delete(0, tk.END)
        for col in self.collections:
            self.collection_list.insert(tk.END, col["name"])
        # Load blacklist from INI file
        self.blacklisted_videos = load_blacklist(self.current_profile)

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
