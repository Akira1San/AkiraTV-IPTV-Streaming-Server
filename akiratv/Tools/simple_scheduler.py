# akiratv/simple_scheduler.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import random
from datetime import datetime, timedelta, date
from pathlib import Path
from PIL import Image, ImageTk
import configparser

# Daypart Scheduler imports
from akiratv.daypart_scheduler import (
    TimeBlock, MarathonConfig, GapFillerConfig,
    DaypartScheduler, get_available_tags_from_collections,
    validate_time_format, parse_time_string, validate_time_block,
    generate_daypart_schedule, validate_daypart_config
)
from akiratv.Tools.daypart_scheduler_mixin import DaypartSchedulerMixin
import logging
logger = logging.getLogger(__name__)

# Import load_collections from collections module (avoids circular import)
from akiratv.collections import load_collections

# Daypart UI imports
# Note: EditBlockDialog is defined locally in SimpleSchedulerWizard class
from akiratv.Tools.daypart_ui import TagExclusionDialog, create_daypart_tab

BASE_DIR = Path(__file__).resolve().parents[2]
USER_DIR = BASE_DIR / "user"
SCHEDULE_DIR = USER_DIR / "schedules"
COVERS_DIR = USER_DIR / "covers"
SCHEDULE_DIR.mkdir(parents=True, exist_ok=True)

def load_collections(profile_name="collections"):
    """Load collections from specified profile"""
    try:
        # Get the script's directory and resolve paths
        script_dir = Path(__file__).resolve().parent
        base_dir = script_dir.parents[1]
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

def _normalize_path(path_str):
    """Normalize a path string to the current OS format.
    Handles Windows paths (C:\\... or C:/...) on Linux by stripping the drive letter."""
    if not path_str:
        return path_str
    p = path_str.strip()
    # Convert backslashes to forward slashes
    p = p.replace("\\", "/")
    # Strip Windows drive letter (e.g. "C:/foo" -> "/foo")
    if len(p) >= 2 and p[1] == ":":
        p = p[2:]
    return p

def load_blacklist(profile_name="collections"):
    """Load blacklist from INI file matching the profile name"""
    try:
        script_dir = Path(__file__).resolve().parent
        base_dir = script_dir.parents[1]
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
                raw = config["Blacklist"].get("videos", "").splitlines()
                return set(_normalize_path(p) for p in raw if p.strip())
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
        base_dir = script_dir.parents[1]
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

class SimpleSchedulerWizard(DaypartSchedulerMixin):
    def __init__(self, root):
        self.root = root
        self.root.title("AkiraTV — Simple Random Scheduler")
        self.root.geometry("1800x1000")
        
        # Theme settings
        self.style = ttk.Style()
        self.current_theme = "windows"  # Default theme
        self.setup_themes()
        
        # Data structures
        self.collections = []
        self.current_profile = "akiratv"  # Default profile (matches collections_akiratv.json)
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
        
        # Daypart Scheduler data structures
        self.daypart_scheduler = DaypartScheduler()
        self.daypart_config = None  # Loaded config for current channel
        self.daypart_enabled = False
        self.daypart_time_blocks = []  # List of TimeBlock objects
        self.daypart_marathons = []  # List of MarathonConfig objects
        self.daypart_gap_filler = GapFillerConfig()  # Gap filler config
        self.daypart_preview_entries = []  # Generated preview entries
        
        self.create_widgets()
    
    def setup_themes(self):
        """Setup custom themes"""
        # Store original Windows theme
        self.windows_theme = self.style.theme_use()
        
        # Create dark theme based on clam (better for custom styling)
        try:
            self.style.theme_create("dark", parent="clam")
        except tk.TclError:
            pass  # Theme already exists
        
        # Configure dark theme colors
        self.style.configure("dark.TFrame", background="#2b2b2b")
        self.style.configure("dark.TLabel", background="#2b2b2b", foreground="#ffffff")
        self.style.configure("dark.TButton", background="#404040", foreground="#ffffff")
        self.style.configure("dark.TCheckbutton", background="#2b2b2b", foreground="#ffffff")
        self.style.configure("dark.TRadiobutton", background="#2b2b2b", foreground="#ffffff")
        self.style.configure("dark.TEntry", fieldbackground="#404040", foreground="#ffffff")
        self.style.configure("dark.TCombobox", fieldbackground="#404040", foreground="#ffffff")
        self.style.configure("dark.TNotebook", background="#2b2b2b")
        self.style.configure("dark.TNotebook.Tab", background="#404040", foreground="#ffffff")
        self.style.configure("dark.TLabelframe", background="#2b2b2b", foreground="#ffffff")
        self.style.configure("dark.TLabelframe.Label", background="#2b2b2b", foreground="#ffffff")
        self.style.configure("dark.TPanedwindow", background="#2b2b2b")
        self.style.configure("dark.TScrollbar", background="#404040", troughcolor="#2b2b2b")
        self.style.configure("dark.Horizontal.TScrollbar", background="#404040", troughcolor="#2b2b2b")
        self.style.configure("dark.Vertical.TScrollbar", background="#404040", troughcolor="#2b2b2b")
        
        # Map for button states
        self.style.map("dark.TButton",
                      background=[("active", "#505050"), ("pressed", "#606060")])
    
    def apply_theme(self, theme_name):
        """Apply the selected theme"""
        if theme_name == "dark":
            self.style.theme_use("dark")
            self.root.configure(bg="#2b2b2b")
            # Apply dark background to all tk widgets
            self._apply_dark_to_tk_widgets(self.root)
        else:
            # Use Windows/default theme
            try:
                self.style.theme_use(self.windows_theme)
            except:
                self.style.theme_use("default")
            self.root.configure(bg="SystemButtonFace")
            # Reset tk widgets to default
            self._reset_tk_widgets(self.root)
        
        self.current_theme = theme_name
        
        # Refresh list displays to update colors
        self.update_added_list_display()

    def _apply_dark_to_tk_widgets(self, widget):
        """Recursively apply dark theme to tk widgets (like Listbox)"""
        for child in widget.winfo_children():
            if isinstance(child, tk.Listbox):
                child.configure(bg="#404040", fg="#ffffff", selectbackground="#505050")
            elif isinstance(child, tk.Label):
                if "cover_label" in str(child):
                    pass  # Skip cover label, handled separately
            elif isinstance(child, tk.Canvas):
                child.configure(bg="#2b2b2b")
            self._apply_dark_to_tk_widgets(child)
    
    def _reset_tk_widgets(self, widget):
        """Recursively reset tk widgets to default theme"""
        for child in widget.winfo_children():
            if isinstance(child, tk.Listbox):
                child.configure(bg="SystemButtonFace", fg="SystemWindowText", selectbackground="SystemHighlight")
            elif isinstance(child, tk.Canvas):
                child.configure(bg="SystemButtonFace")
            self._reset_tk_widgets(child)

    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create horizontal PanedWindow for main layout (info/collection/added/preview)
        self.main_paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill="both", expand=True, pady=(0, 10))
        
        # === LEFT PANE: INFO PANEL ===
        info_frame = ttk.Frame(self.main_paned, width=220)
        info_frame.pack_propagate(False)
        self.main_paned.add(info_frame, weight=1)
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

        # Fix info panel width after layout is calculated
        self.root.after(100, lambda: self.main_paned.sashpos(0, 220))

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
                                         font=("TkDefaultFont", 9), wraplength=200)
        self.info_description.pack(anchor="w", pady=2)
        
        self.info_genre = ttk.Label(metadata_frame, text="Genre: -", font=("TkDefaultFont", 9))
        self.info_genre.pack(anchor="w", pady=2)
        
        self.info_year = ttk.Label(metadata_frame, text="Year: -", font=("TkDefaultFont", 9))
        self.info_year.pack(anchor="w", pady=2)
        
        ttk.Separator(metadata_frame, orient="horizontal").pack(fill="x", pady=10)
        
        self.info_path = ttk.Label(metadata_frame, text="Path: -", font=("TkDefaultFont", 9), 
                                   wraplength=200, foreground="gray")
        self.info_path.pack(anchor="w", pady=2)
        
        self.info_duration = ttk.Label(metadata_frame, text="Duration: -", font=("TkDefaultFont", 9))
        self.info_duration.pack(anchor="w", pady=2)
        
        # Action buttons in Video Info panel
        action_frame = ttk.Frame(info_container)
        action_frame.pack(fill="x", pady=(15, 0))
        ttk.Button(action_frame, text="Save Schedule", command=self.on_save_daypart_schedule).pack(fill="x", pady=2)
        ttk.Button(action_frame, text="Generate Preview", command=self.on_generate_daypart_preview).pack(fill="x", pady=2)

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
        ttk.Button(profile_row1, text="[REFRESH]", command=self.refresh_collections_dropdown, width=3).pack(side="left")
        
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
        
        # Import and integrate StandbyManager
        from akiratv.standby_manager import StandbyTab
        self.standby_tab = StandbyTab(standby_tab)
        
        # Buttons frame (separate from list)
        btn_frame = ttk.Frame(collection_container)
        btn_frame.pack(fill="x", pady=5)
        ttk.Button(btn_frame, text="Select All", command=self.select_all_collections).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Clear Selection", command=self.clear_collection_selection).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Add Selected Collections", command=self.add_selected_collection).pack(side="left", padx=2)
        
        # Populate collections (from default profile initially)
        self.load_collections_from_profile()

    def create_added_panel(self, parent):
        """Create the Added panel for user-selected videos with tabs"""
        # Main container for added panel
        added_container = ttk.Frame(parent)
        added_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        ttk.Label(added_container, text="Added Videos", font=("TkDefaultFont", 12, "bold")).pack(pady=(0, 10))
        
        # Create tab control for Added Videos and Blacklist
        self.added_tab_control = ttk.Notebook(added_container)
        self.added_tab_control.pack(fill="both", expand=True, pady=(0, 5))
        
        # === ADDED VIDEOS TAB ===
        added_tab = ttk.Frame(self.added_tab_control)
        self.added_tab_control.add(added_tab, text="Added Videos")
        
        # Blacklist control buttons
        blacklist_btn_frame = ttk.Frame(added_tab)
        blacklist_btn_frame.pack(fill="x", pady=(0, 5))
        ttk.Button(blacklist_btn_frame, text="Add to Blacklist", command=self.apply_blacklist).pack(side="left", padx=5)
        
        # Added videos list frame
        added_list_frame = ttk.Frame(added_tab)
        added_list_frame.pack(fill="both", expand=True, pady=5)
        
        self.added_list = tk.Listbox(added_list_frame, selectmode=tk.EXTENDED, font=("TkDefaultFont", 11))
        self.added_list.pack(side="left", fill="both", expand=True)
        added_scrollbar = ttk.Scrollbar(added_list_frame, orient="vertical", command=self.added_list.yview)
        added_scrollbar.pack(side="right", fill="y")
        self.added_list.configure(yscrollcommand=added_scrollbar.set)
        self.added_list.bind("<<ListboxSelect>>", self.on_added_video_select)
        
        # Count display for added videos
        self.added_count_label = ttk.Label(added_tab, text="Total: 0 videos", font=("TkDefaultFont", 9))
        self.added_count_label.pack(pady=5)
        
        # Buttons frame for added videos
        btn_frame = ttk.Frame(added_tab)
        btn_frame.pack(fill="x", pady=5)
        ttk.Button(btn_frame, text="Remove Selected", command=self.remove_selected_videos).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Remove All", command=self.remove_all_videos).pack(side="left", padx=2)
        
        # === BLACKLIST TAB ===
        blacklist_tab = ttk.Frame(self.added_tab_control)
        self.added_tab_control.add(blacklist_tab, text="Blacklist")
        
        # Blacklist management buttons
        blacklist_mgmt_frame = ttk.Frame(blacklist_tab)
        blacklist_mgmt_frame.pack(fill="x", pady=(5, 5))
        ttk.Button(blacklist_mgmt_frame, text="Remove from Blacklist", command=self.remove_from_blacklist_tab).pack(side="left", padx=5)
        ttk.Button(blacklist_mgmt_frame, text="Clear Blacklist", command=self.clear_blacklist).pack(side="left", padx=5)
        
        # Blacklist list frame
        blacklist_list_frame = ttk.Frame(blacklist_tab)
        blacklist_list_frame.pack(fill="both", expand=True, pady=5)
        
        self.blacklist_list = tk.Listbox(blacklist_list_frame, selectmode=tk.EXTENDED, font=("TkDefaultFont", 11))
        self.blacklist_list.pack(side="left", fill="both", expand=True)
        blacklist_scrollbar = ttk.Scrollbar(blacklist_list_frame, orient="vertical", command=self.blacklist_list.yview)
        blacklist_scrollbar.pack(side="right", fill="y")
        self.blacklist_list.configure(yscrollcommand=blacklist_scrollbar.set)
        self.blacklist_list.bind("<<ListboxSelect>>", self.on_blacklist_video_select)
        
        # Count display for blacklist
        self.blacklist_count_label = ttk.Label(blacklist_tab, text="Blacklisted: 0 videos", font=("TkDefaultFont", 9))
        self.blacklist_count_label.pack(pady=5)
        
        # === SCHEDULE PROGRAMMING TAB ===
        schedule_tab = ttk.Frame(self.added_tab_control)
        self.added_tab_control.add(schedule_tab, text="Schedule Programming")
        create_daypart_tab(schedule_tab, self)
    
    # TagExclusionDialog is now imported from ui.daypart_ui
    # Uses: from .ui.daypart_ui import TagExclusionDialog

    # ============================================================================
    # DAYPART SCHEDULER EVENT HANDLERS
    # ============================================================================
    # ========================================================================
    # DAYPART SCHEDULING METHODS - Provided by DaypartSchedulerMixin
    # These methods are inherited from the mixin:
    # - on_block_select, on_add_block, on_edit_block, on_delete_block
    # - on_move_block_up, on_move_block_down
    # - on_marathon_all_toggle, on_add_marathon, on_remove_marathon
    # - on_gap_source_change, on_edit_excluded_tags
    # - on_timeline_resize, on_generate_daypart_preview, on_save_daypart_schedule
    # - load_daypart_config_for_channel, refresh_daypart_tags
    # - update_block_list, update_marathon_list, update_gap_filler_ui, update_gap_filler_label
    # - draw_time_block
    # ========================================================================

    def on_edit_block(self):
        """Edit selected time block"""
        selection = self.block_list.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a block to edit")
            return
        index = selection[0]
        block = self.daypart_time_blocks[index]
        
        # Get available tags and videos
        collections = load_collections(self.current_profile)
        available_videos = []
        available_tags = set()
        for col in collections:
            for video in col.get("videos", []):
                if video["path"] not in self.blacklisted_videos:
                    video["collection"] = col
                    available_videos.append(video)
            available_tags.update(col.get("tags", []))
        
        dialog = self.EditBlockDialog(
            self.root,
            block=block,
            available_tags=sorted(list(available_tags)),
            available_videos=available_videos
        )
        self.root.wait_window(dialog)
        if dialog.result:
            self.daypart_time_blocks[index] = dialog.result
            self.update_block_list()
            self.update_preview_display()
    
    def on_delete_block(self):
        """Delete selected time blocks"""
        selection = self.block_list.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select block(s) to delete")
            return
        # Delete in reverse order to preserve indices
        for index in reversed(selection):
            del self.daypart_time_blocks[index]
        self.update_block_list()
        self.update_preview_display()
    
    def on_move_block_up(self):
        """Move selected block up"""
        selection = self.block_list.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a block to move")
            return
        index = selection[0]
        if index > 0:
            self.daypart_time_blocks[index], self.daypart_time_blocks[index-1] = \
                self.daypart_time_blocks[index-1], self.daypart_time_blocks[index]
            self.update_block_list()
            self.block_list.selection_set(index-1)
            self.update_preview_display()
    
    def on_move_block_down(self):
        """Move selected block down"""
        selection = self.block_list.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a block to move")
            return
        index = selection[0]
        if index < len(self.daypart_time_blocks) - 1:
            self.daypart_time_blocks[index], self.daypart_time_blocks[index+1] = \
                self.daypart_time_blocks[index+1], self.daypart_time_blocks[index]
            self.update_block_list()
            self.block_list.selection_set(index+1)
            self.update_preview_display()
    
    def on_marathon_all_toggle(self):
        """Toggle all day checkboxes"""
        state = self.marathon_all_var.get()
        for var in self.marathon_day_vars.values():
            var.set(state)
    
    def on_add_marathon(self):
        """Add a new marathon configuration"""
        tag = self.marathon_tag_var.get().strip()
        if not tag:
            messagebox.showerror("Error", "Please enter a tag for the marathon")
            return
        
        days = [day for day, var in self.marathon_day_vars.items() if var.get()]
        if not days:
            messagebox.showerror("Error", "Please select at least one day")
            return
        
        marathon = MarathonConfig(
            tag=tag,
            days=days,
            shuffle=self.marathon_shuffle_var.get(),
            no_repeat_24h=self.marathon_norepeat_var.get()
        )
        self.daypart_marathons.append(marathon)
        self.update_marathon_list()
        self.update_preview_display()
        
        # Clear inputs
        self.marathon_tag_var.set("")
        for var in self.marathon_day_vars.values():
            var.set(False)
        self.marathon_all_var.set(False)
    
    def on_remove_marathon(self):
        """Remove selected marathon"""
        selection = self.marathon_list.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a marathon to remove")
            return
        index = selection[0]
        del self.daypart_marathons[index]
        self.update_marathon_list()
        self.update_preview_display()
    
    def on_gap_source_change(self):
        """Handle gap filler source change"""
        self.update_gap_filler_ui()
    
    def on_edit_excluded_tags(self, event=None):
        """Open dialog to edit excluded tags"""
        # Get all available tags from collections
        collections = load_collections(self.current_profile)
        all_tags = set()
        for col in collections:
            all_tags.update(col.get("tags", []))
        
        dialog = TagExclusionDialog(
            self.root,
            available_tags=sorted(list(all_tags)),
            excluded_tags=self.daypart_gap_filler.excluded_tags
        )
        self.root.wait_window(dialog)
        if dialog.result is not None:
            self.daypart_gap_filler.excluded_tags = dialog.result
            self.update_gap_filler_label()
    

    def on_save_daypart_schedule(self):
        """Save daypart schedule configuration"""
        # Use channel_var if current_channel is not set
        target_channel = self.current_channel
        if not target_channel:
            target_channel = self.channel_var.get().strip() if hasattr(self, 'channel_var') else None
        
        if not target_channel:
            messagebox.showerror("Error", "No channel selected")
            return
        
        # Update current_channel for consistency
        self.current_channel = target_channel
        
        # Validate configuration
        daypart_config = {
            "daypart_config": {
                "time_blocks": [b.to_dict() for b in self.daypart_time_blocks],
                "marathons": [m.to_dict() for m in self.daypart_marathons],
                "gap_filler": self.daypart_gap_filler.to_dict()
            },
            "enabled": self.daypart_enabled,
            "weekly": {},
            "calendar": {}
        }
        
        errors = validate_daypart_config(daypart_config)
        if errors:
            error_msg = "Configuration errors:\n\n" + "\n".join(f"• {e}" for e in errors)
            messagebox.showerror("Validation Errors", error_msg)
            return
        
        # If we have generated preview entries, also include them in the saved file
        if self.daypart_preview_entries:
            # Group entries by date for weekly/calendar sections
            weekly_entries = {}
            calendar_entries = {}
            
            for entry in self.daypart_preview_entries:
                day = entry.get("day", "monday")
                date_str = entry.get("date", "")
                
                # Add to weekly section (by day name)
                if day not in weekly_entries:
                    weekly_entries[day] = []
                weekly_entries[day].append({
                    "time": entry.get("time", ""),
                    "file": entry.get("file", ""),
                    "duration": entry.get("duration", 0),
                    "source": entry.get("source", "")
                })
                
                # Add to calendar section (by date)
                if date_str:
                    if date_str not in calendar_entries:
                        calendar_entries[date_str] = {
                            "date": date_str,
                            "day": day,
                            "entries": []
                        }
                    calendar_entries[date_str]["entries"].append({
                        "time": entry.get("time", ""),
                        "file": entry.get("file", ""),
                        "duration": entry.get("duration", 0),
                        "source": entry.get("source", "")
                    })
            
            # Update config with generated entries
            daypart_config["weekly"] = weekly_entries
            daypart_config["calendar"] = calendar_entries
        
        # Save configuration
        if self.daypart_scheduler.save_config(self.current_channel, daypart_config):
            preview_msg = ""
            if self.daypart_preview_entries:
                preview_msg = f"\n\nAlso saved {len(self.daypart_preview_entries)} generated video entries."
            messagebox.showinfo("Success", f"Daypart schedule saved for channel '{self.current_channel}'!{preview_msg}")
        else:
            messagebox.showerror("Error", "Failed to save daypart configuration")
    
    def load_daypart_config_for_channel(self):
        """Load daypart configuration for current channel"""
        # Use channel_var if current_channel is not set
        target_channel = self.current_channel
        if not target_channel:
            target_channel = self.channel_var.get().strip() if hasattr(self, 'channel_var') else None
        
        if not target_channel:
            return
        
        # Update current_channel for consistency
        self.current_channel = target_channel
        
        config = self.daypart_scheduler.load_config(target_channel)
        if config:
            self.daypart_config = config
            self.daypart_enabled = config.get("enabled", False)
            
            # Load time blocks
            self.daypart_time_blocks = []
            for block_data in config.get("daypart_config", {}).get("time_blocks", []):
                try:
                    block = TimeBlock.from_dict(block_data)
                    self.daypart_time_blocks.append(block)
                except Exception as e:
                    logger.error(f"Failed to load time block: {e}")
            
            # Load marathons
            self.daypart_marathons = []
            for marathon_data in config.get("daypart_config", {}).get("marathons", []):
                try:
                    marathon = MarathonConfig.from_dict(marathon_data)
                    self.daypart_marathons.append(marathon)
                except Exception as e:
                    logger.error(f"Failed to load marathon: {e}")
            
            # Load gap filler
            gap_data = config.get("daypart_config", {}).get("gap_filler", {})
            self.daypart_gap_filler = GapFillerConfig.from_dict(gap_data)
            
            # Update UI
            self.update_block_list()
            self.update_marathon_list()
            self.update_gap_filler_ui()
        else:
            # Reset to defaults
            self.daypart_config = None
            self.daypart_enabled = False
            self.daypart_time_blocks = []
            self.daypart_marathons = []
            self.daypart_gap_filler = GapFillerConfig()
            self.update_block_list()
            self.update_marathon_list()
            self.update_gap_filler_ui()
        
        # Refresh available tags
        self.refresh_daypart_tags()
    
    def refresh_daypart_tags(self):
        """Populate marathon tag combo with available tags from collections"""
        collections = load_collections(self.current_profile)
        all_tags = set()
        for col in collections:
            all_tags.update(col.get("tags", []))
        
        if hasattr(self, 'marathon_tag_combo'):
            self.marathon_tag_combo['values'] = sorted(list(all_tags))
    
    def update_block_list(self):
        """Update the time block list display"""
        self.block_list.delete(0, tk.END)
        for block in self.daypart_time_blocks:
            # Format: "06:00-10:00 [TAG:kids] Mon,Wed,Fri"
            # or "06:00-10:00 [VIDEO] The Matrix (1999).mp4"
            if block.content_type == "tag":
                # Show days if specified
                days_str = ""
                if hasattr(block, 'days') and block.days:
                    days_str = " (" + ",".join([d[:3] for d in block.days]) + ")"
                display = f"{block.start_time}-{block.end_time} [TAG:{block.content_value}]{days_str}"
            else:
                # Shorten video path for display
                filename = Path(block.content_value).name
                display = f"{block.start_time}-{block.end_time} [VIDEO] {filename}"
            self.block_list.insert(tk.END, display)
        
        self.block_count_label.config(text=f"Total blocks: {len(self.daypart_time_blocks)}")
    
    def update_marathon_list(self):
        """Update the marathon list display"""
        self.marathon_list.delete(0, tk.END)
        for marathon in self.daypart_marathons:
            days = ", ".join([d[:3].title() for d in marathon.days])
            display = f"Tag: {marathon.tag} | Days: {days} | Shuffle: {marathon.shuffle}"
            self.marathon_list.insert(tk.END, display)
    
    def update_gap_filler_ui(self):
        """Update gap filler UI from config"""
        self.gap_enabled_var.set(self.daypart_gap_filler.enabled)
        self.gap_source_var.set(self.daypart_gap_filler.source)
        self.gap_24h_var.set(self.daypart_gap_filler.respect_24h_norepeat)
        self.gap_shuffle_var.set(self.daypart_gap_filler.shuffle)
        self.update_gap_filler_label()
    
    def update_gap_filler_label(self):
        """Update the excluded tags label"""
        if self.daypart_gap_filler.excluded_tags:
            count = len(self.daypart_gap_filler.excluded_tags)
            self.gap_exclude_label.config(text=f"[{count} tag(s) excluded]")
        else:
            self.gap_exclude_label.config(text="[None]")
    
    def update_preview_display(self):
        """Update the text preview list"""
        print(f"[DEBUG] update_preview_display called, entries: {len(self.daypart_preview_entries) if self.daypart_preview_entries else 0}")
        self.preview_list.delete(0, tk.END)
        
        if not self.daypart_preview_entries:
            self.preview_list.insert(tk.END, "No preview generated. Click 'Generate Preview'.")
            self.preview_stats_label.config(text="")
            return
        
        print(f"[DEBUG] Displaying {len(self.daypart_preview_entries)} entries in listbox")
        
        if not self.daypart_preview_entries:
            self.preview_list.insert(tk.END, "No preview generated. Click 'Generate Preview'.")
            self.preview_stats_label.config(text="")
            return
        
        # Display entries
        for entry in self.daypart_preview_entries:
            time = entry["time"]
            file = Path(entry["file"]).name
            source = entry.get("source", "unknown")
            metadata = entry.get("metadata", {})
            
            # Calculate end time for debug display
            duration = entry.get("duration", 0)
            end_time_str = ""
            if duration > 0:
                try:
                    # Parse start time (HH:MM:SS)
                    time_parts = time.split(":")
                    if len(time_parts) >= 2:
                        start_h = int(time_parts[0])
                        start_m = int(time_parts[1])
                        total_minutes = start_h * 60 + start_m + (duration // 60)
                        end_h = (total_minutes // 60) % 24
                        end_m = total_minutes % 60
                        end_time_str = f"-{end_h:02d}:{end_m:02d}"
                except:
                    pass
            
            if source == "daypart_video":
                display = f"{time}{end_time_str} [VIDEO] {file}"
            elif source == "daypart_tag":
                tag = metadata.get("tag_used", "unknown")
                display = f"{time}{end_time_str} [TAG:{tag}] {file}"
            elif source == "daypart_marathon":
                tag = metadata.get("tag", "unknown")
                display = f"{time}{end_time_str} [MARATHON:{tag}] {file}"
            elif source == "gap_filler":
                display = f"{time}{end_time_str} [GAP] {file}"
            else:
                display = f"{time}{end_time_str} {file}"
            
            self.preview_list.insert(tk.END, display)
        
        # Force UI update
        self.preview_list.update()
        
        # Update stats
        total_entries = len(self.daypart_preview_entries)
        block_entries = sum(1 for e in self.daypart_preview_entries
                           if e.get("source", "").startswith("daypart_"))
        gap_entries = sum(1 for e in self.daypart_preview_entries
                         if e.get("source") == "gap_filler")
        
        stats = f"Total: {total_entries} entries | Scheduled blocks: {block_entries} | Gap filler: {gap_entries}"
        self.preview_stats_label.config(text=stats)
    

    def create_preview_panel(self, parent):
        """Create the Preview panel for schedule preview"""
        # Main container for preview panel
        preview_container = ttk.Frame(parent)
        preview_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        ttk.Label(preview_container, text="Schedule Preview", font=("TkDefaultFont", 12, "bold")).pack(pady=(0, 10))
        
        # Row 1: Day selector buttons
        day_frame = ttk.Frame(preview_container)
        day_frame.pack(fill="x", pady=(0, 2))
        
        self.day_var = tk.StringVar(value="monday")
        self.day_buttons = {}
        days = [("Mon", "monday"), ("Tue", "tuesday"), ("Wed", "wednesday"), 
                ("Thu", "thursday"), ("Fri", "friday"), ("Sat", "saturday"), ("Sun", "sunday")]
        
        for label, day_value in days:
            btn = ttk.Button(day_frame, text=label, width=5,
                           command=lambda d=day_value: self.select_day(d))
            btn.pack(side="left", padx=2)
            self.day_buttons[day_value] = btn
        
        # Highlight initial selection
        self.highlight_day_button("monday")

        # Row 2: Action buttons
        action_frame = ttk.Frame(preview_container)
        action_frame.pack(fill="x", pady=(2, 5))

        ttk.Button(action_frame, text="[FIX] Fix Paths", command=self.fix_schedule_paths_dialog, width=12).pack(side="left", padx=2)
        ttk.Button(action_frame, text="[COPY] Copy", command=self.copy_schedule, width=10).pack(side="left", padx=2)
        ttk.Button(action_frame, text="[INSPECT] View Schedule", command=self.inspect_schedule_file, width=18).pack(side="left", padx=2)
        ttk.Button(action_frame, text="[DEBUG] 7-Day View", command=self.show_seven_day_popup, width=15).pack(side="left", padx=2)
        
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
    
    def select_day(self, day):
        """Select a day and update the preview"""
        self.day_var.set(day)
        self.highlight_day_button(day)
        self.update_preview_display()
    
    def highlight_day_button(self, selected_day):
        """Highlight the selected day button"""
        # Reset all buttons to normal state
        for day, btn in self.day_buttons.items():
            if day == selected_day:
                btn.state(['pressed'])  # Visual indication of selection
            else:
                btn.state(['!pressed'])
    
    def show_seven_day_popup(self):
        """Show a popup window with horizontal schedules for all 7 days (debug view)"""
        if not self.current_schedule:
            messagebox.showinfo("No Schedule", "Generate a schedule first to see the 7-day view.")
            return
        
        channel_name = self.current_channel or "Current"
        self._show_schedule_popup(self.current_schedule, channel_name)

    def inspect_schedule_file(self):
        """Open a file dialog to load and inspect a saved schedule JSON file"""
        # Open file dialog to select a schedule JSON file
        file_path = filedialog.askopenfilename(
            title="Select Schedule File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=SCHEDULE_DIR
        )
        
        if not file_path:
            return  # User cancelled
        
        try:
            # Load the schedule from the selected file
            with open(file_path, "r", encoding="utf-8") as f:
                schedule_data = json.load(f)
            
            # Determine the filename for display
            file_name = Path(file_path).stem
            channel_name = file_name.replace("schedule_", "") if file_name.startswith("schedule_") else file_name
            
            # Show the schedule in a popup (reusing the display logic)
            self._show_schedule_popup(schedule_data, channel_name)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load schedule file: {e}")

    def _show_schedule_popup(self, schedule_data, channel_name):
        """Display a schedule in a popup window (used by both generated and loaded schedules)"""
        # Create popup window
        popup = tk.Toplevel(self.root)
        popup.title(f"Schedule View - {channel_name}")
        popup.geometry("1400x600")
        
        # Main frame with horizontal scroll
        main_frame = ttk.Frame(popup)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create a canvas with horizontal scrollbar for 7 columns
        canvas = tk.Canvas(main_frame)
        h_scrollbar = ttk.Scrollbar(main_frame, orient="horizontal", command=canvas.xview)
        v_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        # Pack scrollbars and canvas
        h_scrollbar.pack(side="bottom", fill="x")
        v_scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        # Check if this is calendar mode
        if "calendar" in schedule_data:
            # Calendar mode: display calendar entries grouped by dates
            calendar = schedule_data.get("calendar", {})
            if not calendar:
                messagebox.showinfo("No Calendar Entries", "This calendar schedule contains no entries.")
                popup.destroy()
                return
            
            # Sort calendar entries by date
            sorted_calendar = sorted(calendar.items(), key=lambda x: x[1]["date"])
            
            # Create columns for each calendar date
            for col, (date_key, date_data) in enumerate(sorted_calendar):
                day_frame = ttk.Frame(scrollable_frame, borderwidth=1, relief="solid")
                day_frame.grid(row=0, column=col, padx=5, pady=5, sticky="nsew")
                
                # Date header
                header_label = ttk.Label(day_frame, text=f"{date_data['date']}\n({date_data['day']})", 
                                        font=("TkDefaultFont", 12, "bold"), justify="center")
                header_label.pack(pady=5)
                
                # Day listbox
                day_listbox = tk.Listbox(day_frame, font=("Consolas", 11), width=30, height=25)
                day_listbox.pack(fill="both", expand=True, padx=5, pady=5)
                
                # Populate the listbox with calendar entries
                entries = date_data.get("entries", [])
                if entries:
                    for entry in entries:
                        time_str = entry.get("time", "??:??")
                        file_path = entry.get("file", "")
                        file_name = Path(file_path).name
                        
                        # Truncate long filenames
                        if len(file_name) > 25:
                            display_name = file_name[:22] + "..."
                        else:
                            display_name = file_name
                        
                        day_listbox.insert(tk.END, f"{time_str} {display_name}")
                else:
                    day_listbox.insert(tk.END, "No entries")
        else:
            # Weekly mode: display weekly schedule for each day
            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            
            # Create 7 columns (one for each day)
            for col, day in enumerate(days):
                day_frame = ttk.Frame(scrollable_frame, borderwidth=1, relief="solid")
                day_frame.grid(row=0, column=col, padx=5, pady=5, sticky="nsew")
                
                # Day header
                header_label = ttk.Label(day_frame, text=day.upper(), font=("TkDefaultFont", 12, "bold"))
                header_label.pack(pady=5)
                
                # Day listbox
                day_listbox = tk.Listbox(day_frame, font=("Consolas", 11), width=30, height=25)
                day_listbox.pack(fill="both", expand=True, padx=5, pady=5)
                
                # Populate the listbox
                weekly_data = schedule_data.get("weekly", {})
                day_schedule = weekly_data.get(day, [])
                
                if day_schedule:
                    for entry in day_schedule:
                        time_str = entry.get("time", "??:??")
                        file_path = entry.get("file", "")
                        file_name = Path(file_path).name
                        
                        # Truncate long filenames
                        if len(file_name) > 25:
                            display_name = file_name[:22] + "..."
                        else:
                            display_name = file_name
                        
                        day_listbox.insert(tk.END, f"{time_str} {display_name}")
                else:
                    day_listbox.insert(tk.END, "No entries")
                
                # Add entry count
                day_listbox.insert(tk.END, f"--- {len(day_schedule)} entries ---")
        
        # Close button
        close_frame = ttk.Frame(popup)
        close_frame.pack(pady=10)
        ttk.Button(close_frame, text="Close", command=popup.destroy).pack()

    def create_bottom_controls(self, parent):
        """Create bottom control bar with channel selection and action buttons"""
        bottom_frame = ttk.Frame(parent)
        bottom_frame.pack(fill="x", pady=(10, 0))
        
        # Channel selection and episodic checkbox on one line (centered)
        chan_episodic_frame = ttk.Frame(bottom_frame)
        chan_episodic_frame.pack(fill="x", pady=(0, 5))
        
        # Center container for controls
        controls_center = ttk.Frame(chan_episodic_frame)
        controls_center.pack(anchor="center")
        
        ttk.Label(controls_center, text="Channel:").pack(side="left")
        self.channel_var = tk.StringVar(value="critters")
        chan_combo = ttk.Combobox(controls_center, textvariable=self.channel_var,
                                 values=self.get_known_channels(), width=12)
        chan_combo.set("critters")
        chan_combo.pack(side="left", padx=5)

        self.episodic_var = tk.BooleanVar(value=False)
        episodic_check = ttk.Checkbutton(controls_center, text="Auto-detect episodic content",
                                        variable=self.episodic_var)
        episodic_check.pack(side="left", padx=10)
        self.create_tooltip(episodic_check, "Groups videos into series (e.g., MySeries S01E01, S01E02) and treats them as episodic content.")

        self.sequential_var = tk.BooleanVar(value=False)
        sequential_check = ttk.Checkbutton(controls_center, text="Sequential Episode Tracking",
                                          variable=self.sequential_var)
        sequential_check.pack(side="left", padx=10)
        self.create_tooltip(sequential_check, "When the same series is picked multiple times, plays episodes in order (1→2→3→loop). Session-based only.")

        # Schedule mode selection (Weekly/Calendar)
        mode_frame = ttk.Frame(controls_center)
        mode_frame.pack(side="left", padx=20)

        ttk.Label(mode_frame, text="Mode:").pack(side="left")
        self.schedule_mode_var = tk.StringVar(value="weekly")
        ttk.Radiobutton(mode_frame, text="Weekly", variable=self.schedule_mode_var,
                        value="weekly", command=self.on_schedule_mode_change).pack(side="left", padx=2)
        ttk.Radiobutton(mode_frame, text="Calendar", variable=self.schedule_mode_var,
                        value="calendar", command=self.on_schedule_mode_change).pack(side="left", padx=2)

        # Calendar date range (hidden by default)
        calendar_frame = ttk.Frame(controls_center)
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

        # Preview buttons and save button on one line (centered)
        preview_frame = ttk.Frame(bottom_frame)
        preview_frame.pack(fill="x", pady=5)
        
        # Center container for buttons
        button_center = ttk.Frame(preview_frame)
        button_center.pack(anchor="center")
        
        ttk.Button(button_center, text="[RAND] Preview Random", 
                  command=lambda: self.preview_schedule(mode="random")).pack(side="left", padx=5)
        
        ttk.Button(button_center, text="▶ Preview Sequential", 
                  command=lambda: self.preview_schedule(mode="sequential")).pack(side="left", padx=5)
        
        ttk.Separator(button_center, orient="vertical").pack(side="left", fill="y", padx=10)
        
        self.save_button = ttk.Button(button_center, text="[SAVE] Save Schedule", 
                  command=self.save_current_schedule, state="disabled")
        self.save_button.pack(side="left")
        
        # Theme selector
        ttk.Separator(button_center, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Label(button_center, text="Theme:").pack(side="left")
        self.theme_var = tk.StringVar(value="windows")
        theme_combo = ttk.Combobox(button_center, textvariable=self.theme_var,
                                  values=["windows", "dark"], width=8, state="readonly")
        theme_combo.pack(side="left", padx=5)
        theme_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_theme(self.theme_var.get()))

    # === INFO PANEL METHODS ===
    
    def update_info_panel(self, video_data):
        """Update info panel with selected video data"""
        if not video_data:
            self.clear_info_panel()
            return
        
        collection = video_data.get("collection", {})
        
        # Update cover image - pass both id and cover path
        self.load_cover_image(collection.get("id"), collection.get("cover"))
        
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
    
    def load_cover_image(self, collection_id, cover_path=None):
        """Load cover image from user/covers directory
        
        Args:
            collection_id: The collection ID to search for cover if no explicit path
            cover_path: Explicit cover path from collection data (takes priority)
        """
        cover_file = None
        
        # First, try the explicit cover path if provided
        if cover_path:
            # Handle both relative and absolute paths
            if cover_path.startswith("user/"):
                full_path = BASE_DIR / cover_path
            else:
                full_path = Path(cover_path)
            
            if full_path.exists():
                cover_file = full_path
        
        # Fallback: search by collection_id in covers directory
        if not cover_file and collection_id:
            for ext in ['.jpg', '.jpeg', '.png']:
                potential_path = COVERS_DIR / f"{collection_id}{ext}"
                if potential_path.exists():
                    cover_file = potential_path
                    break
        
        # Display the cover or show "No cover"
        if cover_file:
            try:
                # Load and resize image
                img = Image.open(cover_file)
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
        skipped_count = 0
        for collection in self.selected_collections:
            for video in collection.get("videos", []):
                video_path = _normalize_path(video.get("path", ""))
                
                # Skip missing videos (don't add them)
                if video_path and not Path(video_path).exists():
                    skipped_count += 1
                    continue
                
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
        
        if added_count > 0 or skipped_count > 0:
            self.update_added_list_display()
            msg = f"Added {added_count} video(s) from {len(self.selected_collections)} collection(s)!"
            if skipped_count > 0:
                msg += f"\n⚠️ Skipped {skipped_count} missing video(s) (not found on disk)."
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showinfo("Info", "All videos from selected collections are already in the added list.")

    # === ADDED PANEL METHODS ===
    
    def update_added_list_display(self):
        """Update added videos listbox (excludes blacklisted videos)"""
        self.added_list.delete(0, tk.END)
        non_blacklisted_count = 0
        
        # Determine text color based on theme
        normal_color = "white" if self.current_theme == "dark" else "black"
        
        for video in self.added_videos:
            # Skip blacklisted videos in the main list
            if video["path"] in self.blacklisted_videos:
                continue
            collection_name = video.get("collection", {}).get("name", "Unknown")
            video_name = video.get("name", "Unknown")
            video_path = video.get("path", "")
            
            # Check if video file exists
            if video_path and not Path(video_path).exists():
                display_text = f"❌ {collection_name} - {video_name} (MISSING)"
                self.added_list.insert(tk.END, display_text)
                self.added_list.itemconfig(tk.END, fg="red")  # Red for missing
            else:
                display_text = f"{collection_name} - {video_name}"
                self.added_list.insert(tk.END, display_text)
                self.added_list.itemconfig(tk.END, fg=normal_color)  # Normal color
            non_blacklisted_count += 1
        
        self.added_count_label.configure(text=f"Total: {non_blacklisted_count} videos")
        self.update_blacklist_list_display()
    
    def update_blacklist_list_display(self):
        """Update the blacklist tab listbox"""
        self.blacklist_list.delete(0, tk.END)
        normal_color = "white" if self.current_theme == "dark" else "black"

        # Build a path->video lookup from added_videos for richer display
        path_to_video = {v["path"]: v for v in self.added_videos}

        for video_path in self.blacklisted_videos:
            video = path_to_video.get(video_path)
            if video:
                collection_name = video.get("collection", {}).get("name", "Unknown")
                video_name = video.get("name", "Unknown")
            else:
                # Not in added_videos — show path basename
                collection_name = "?"
                video_name = Path(video_path).name

            if video_path and not Path(video_path).exists():
                display_text = f"❌ {collection_name} - {video_name} (MISSING)"
                self.blacklist_list.insert(tk.END, display_text)
                self.blacklist_list.itemconfig(tk.END, fg="red")
            else:
                display_text = f"{collection_name} - {video_name}"
                self.blacklist_list.insert(tk.END, display_text)
                self.blacklist_list.itemconfig(tk.END, fg=normal_color)

        self.blacklist_count_label.configure(text=f"Blacklisted: {len(self.blacklisted_videos)} videos")
    
    def remove_selected_videos(self):
        """Remove selected videos from added list"""
        selection = self.added_list.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Select at least one video to remove!")
            return
        
        # Get non-blacklisted videos to map indices correctly
        non_blacklisted = [v for v in self.added_videos if v["path"] not in self.blacklisted_videos]
        
        # Remove in reverse order to maintain indices
        removed_count = 0
        for idx in sorted(selection, reverse=True):
            if idx < len(non_blacklisted):
                video = non_blacklisted[idx]
                video_path = video.get("path", "")
                if video_path in self.video_to_collection_map:
                    del self.video_to_collection_map[video_path]
                self.added_videos.remove(video)  # Remove by reference
                removed_count += 1
        
        self.update_added_list_display()
        messagebox.showinfo("Success", f"Removed {removed_count} video(s)!")
    
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
        
        # Get non-blacklisted videos to map indices correctly
        non_blacklisted = [v for v in self.added_videos if v["path"] not in self.blacklisted_videos]
        
        blacklisted_count = 0
        for idx in selection:
            if idx < len(non_blacklisted):
                video = non_blacklisted[idx]
                video_path = video.get("path", "")
                self.blacklisted_videos.add(video_path)
                blacklisted_count += 1
        
        self.update_added_list_display()  # Refresh both lists
        messagebox.showinfo("Success", f"Added {blacklisted_count} video(s) to blacklist!")
    
    def update_blacklist_count(self):
        """Update the blacklist count display and list"""
        self.update_blacklist_list_display()
    
    def on_blacklist_video_select(self, event):
        """Handle blacklist video selection - update info panel with selected video"""
        selection = self.blacklist_list.curselection()
        if not selection:
            self.clear_info_panel()
            self.selected_video = None
            return
        
        # Use the same ordered list as update_blacklist_list_display
        path_to_video = {v["path"]: v for v in self.added_videos}
        blacklist_paths = list(self.blacklisted_videos)
        if selection[0] < len(blacklist_paths):
            video_path = blacklist_paths[selection[0]]
            video = path_to_video.get(video_path)
            if video:
                self.selected_video = video
                self.update_info_panel(video)
    
    def remove_from_blacklist_tab(self):
        """Remove selected videos from blacklist (from blacklist tab)"""
        selection = self.blacklist_list.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Select at least one video to remove from blacklist!")
            return
        
        # Use the same ordered list as update_blacklist_list_display
        blacklist_paths = list(self.blacklisted_videos)
        
        removed_count = 0
        for idx in sorted(selection, reverse=True):
            if idx < len(blacklist_paths):
                video_path = blacklist_paths[idx]
                if video_path in self.blacklisted_videos:
                    self.blacklisted_videos.remove(video_path)
                    removed_count += 1
        
        self.update_added_list_display()
        messagebox.showinfo("Success", f"Removed {removed_count} video(s) from blacklist!")
    
    def clear_blacklist(self):
        """Clear all videos from blacklist"""
        if not self.blacklisted_videos:
            messagebox.showinfo("Info", "Blacklist is already empty.")
            return
        
        if messagebox.askyesno("Confirm", f"Remove all {len(self.blacklisted_videos)} videos from blacklist?"):
            self.blacklisted_videos.clear()
            self.update_added_list_display()
            messagebox.showinfo("Success", "Blacklist cleared!")
    
    def on_added_video_select(self, event):
        """Handle added video selection - update info panel with selected video"""
        selection = self.added_list.curselection()
        if not selection:
            self.clear_info_panel()
            self.selected_video = None
            return
        
        # Get non-blacklisted videos to map indices correctly
        non_blacklisted = [v for v in self.added_videos if v["path"] not in self.blacklisted_videos]
        
        # Use first selected video for info panel
        idx = selection[0]
        if idx < len(non_blacklisted):
            video = non_blacklisted[idx]
            self.selected_video = video
            
            # Update info panel with selected video data
            self.update_info_panel(video)

    # === PREVIEW PANEL METHODS ===
    
    def update_preview_display(self, event=None):
        """Update the preview listbox with the selected day's schedule"""
        print(f"[DEBUG] simple_scheduler update_preview_display called, daypart entries: {len(self.daypart_preview_entries) if self.daypart_preview_entries else 0}")
        # First check for daypart preview entries
        if self.daypart_preview_entries:
            self.preview_list.delete(0, tk.END)
            
            selected_day = self.day_var.get()
            
            # Filter entries for the selected day
            selected_entries = [
                entry for entry in self.daypart_preview_entries
                if entry.get("day", "").lower() == selected_day.lower()
            ]
            
            # If we have entries for the selected day, show them
            if selected_entries:
                # Sort by time for that day
                sorted_entries = sorted(selected_entries, key=lambda e: e.get("time", ""))
                
                self.preview_list.insert(tk.END, f"=== {selected_day.upper()} ===")
                self.preview_list.insert(tk.END, "")
                
                for entry in sorted_entries:
                    time = entry["time"]
                    file = Path(entry["file"]).name
                    source = entry.get("source", "unknown")
                    metadata = entry.get("metadata", {})
                    
                    # Calculate end time for debug display
                    duration = entry.get("duration", 0)
                    print(f"[DEBUG] Entry: time={time}, duration={duration}")
                    end_time_str = ""
                    if duration > 0:
                        try:
                            # Parse start time (HH:MM:SS)
                            time_parts = time.split(":")
                            print(f"[DEBUG] Time parts: {time_parts}")
                            if len(time_parts) >= 2:
                                start_h = int(time_parts[0])
                                start_m = int(time_parts[1])
                                total_minutes = start_h * 60 + start_m + int(duration // 60)
                                end_h = (total_minutes // 60) % 24
                                end_m = total_minutes % 60
                                end_time_str = f"-{end_h:02d}:{end_m:02d}"
                                print(f"[DEBUG] Calculated end: {end_time_str} from duration {duration}")
                        except Exception as e:
                            print(f"[DEBUG] Error calculating end: {e}")
                            pass
                    
                    if source == "daypart_video":
                        display = f"{time}{end_time_str} [VIDEO] {file}"
                    elif source == "daypart_tag":
                        tag = metadata.get("tag_used", "unknown")
                        display = f"{time}{end_time_str} [TAG:{tag}] {file}"
                    elif source == "daypart_marathon":
                        tag = metadata.get("tag", "unknown")
                        display = f"{time}{end_time_str} [MARATHON:{tag}] {file}"
                    elif source == "gap_filler":
                        display = f"{time}{end_time_str} [GAP] {file}"
                    else:
                        display = f"{time}{end_time_str} {file}"
                    
                    self.preview_list.insert(tk.END, display)
                
                self.preview_list.insert(tk.END, "")
                self.preview_list.insert(tk.END, f"Total entries: {len(selected_entries)}")
            else:
                self.preview_list.insert(tk.END, f"No entries for {selected_day.title()}")
            
            # Update preview info label
            if hasattr(self, 'preview_info'):
                self.preview_info.config(text=f"Daypart Preview: {len(selected_entries)} entries for {selected_day.title()}")
            return
        
        # Fall back to current_schedule logic
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
        
        # First check if we have daypart preview entries
        if self.daypart_preview_entries:
            # Use daypart preview entries
            text_lines = []
            current_date = None
            for entry in self.daypart_preview_entries:
                entry_date = entry.get("date", "")
                entry_day = entry.get("day", "")
                
                # Show date header when date changes
                if entry_date and entry_date != current_date:
                    current_date = entry_date
                    day_display = entry_day.title() if entry_day else ""
                    text_lines.append(f"=== {entry_date} ({day_display}) ===")
                
                time_str = entry.get("time", "??:??:??")
                time_short = ":".join(time_str.split(":")[:2])
                file_path = entry.get("file", "")
                if file_path:
                    title = Path(file_path).stem
                else:
                    title = entry.get("title", "Unknown")
                source = entry.get("source", "unknown")
                
                # Calculate end time
                duration = entry.get("duration", 0)
                end_time_str = ""
                if duration > 0:
                    try:
                        time_parts = time_str.split(":")
                        if len(time_parts) >= 2:
                            start_h = int(time_parts[0])
                            start_m = int(time_parts[1])
                            total_minutes = start_h * 60 + start_m + int(duration // 60)
                            end_h = (total_minutes // 60) % 24
                            end_m = total_minutes % 60
                            end_time_str = f"-{end_h:02d}:{end_m:02d}"
                    except:
                        pass
                
                text_lines.append(f"  {time_short}{end_time_str} [{source}] {title}")
            
            clipboard_text = "\n".join(text_lines)
            self.root.clipboard_clear()
            self.root.clipboard_append(clipboard_text)
            messagebox.showinfo("Copied", f"{len(self.daypart_preview_entries)} entries copied to clipboard!")
            return
        
        # Fall back to legacy schedule format
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
        self.root.clipboard_append(clipboard_text)
        messagebox.showinfo("Copied", "Schedule copied to clipboard!")

    def fix_schedule_paths_dialog(self):
        """Open a dialog to fix Windows paths in a schedule JSON file to Linux paths"""
        # Ask user to select a schedule file
        file_path = filedialog.askopenfilename(
            title="Select Schedule JSON to Fix",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=SCHEDULE_DIR
        )
        if not file_path:
            return
        
        # Ask for Windows and Linux base paths
        windows_base = simpledialog.askstring("Path Mapping", "Enter Windows base path (e.g., C:/Videos):", initialvalue="C:/Videos")
        if windows_base is None:
            return
        linux_base = simpledialog.askstring("Path Mapping", "Enter Linux base path (e.g., /home/akira/Videos):", initialvalue="/home/akira/Videos")
        if linux_base is None:
            return
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                schedule = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load schedule file:\n{e}")
            return
        
        # Normalize base prefixes
        def norm(p):
            return p.replace("\\", "/").rstrip("/")
        win_norm = norm(windows_base)
        linux_norm = norm(linux_base)
        
        fixed_count = 0
        
        # Helper to fix a single path
        def fix_path(p):
            nonlocal fixed_count
            if not p:
                return p
            original = p
            # Normalize slashes
            p_norm = p.replace("\\", "/")
            # Check case-insensitive match for Windows base
            if p_norm[:len(win_norm)].lower() == win_norm.lower():
                # Replace prefix
                suffix = p_norm[len(win_norm):].lstrip("/")
                if suffix:
                    new = linux_norm + "/" + suffix
                else:
                    new = linux_norm
                p_norm = new
            # Replace any remaining backslashes
            p_norm = p_norm.replace("\\", "/")
            if p_norm != original:
                fixed_count += 1
            return p_norm
        
        # Fix weekly entries
        weekly = schedule.get("weekly", {})
        for day, entries in weekly.items():
            for entry in entries:
                if "file" in entry:
                    entry["file"] = fix_path(entry["file"])
        
        # Fix calendar entries
        calendar = schedule.get("calendar", {})
        for cal_key, cal_data in calendar.items():
            entries = cal_data.get("entries", [])
            for entry in entries:
                if "file" in entry:
                    entry["file"] = fix_path(entry["file"])
        
        # Fix daypart_config time_blocks with video content
        daypart_config = schedule.get("daypart_config")
        if daypart_config:
            time_blocks = daypart_config.get("time_blocks", [])
            for block in time_blocks:
                if block.get("content_type") == "video" and "content_value" in block:
                    block["content_value"] = fix_path(block["content_value"])
        
        # Save the fixed schedule back to the same file
        if fixed_count > 0:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(schedule, f, indent=2, ensure_ascii=False)
                messagebox.showinfo("Success", f"Fixed {fixed_count} paths in:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save fixed schedule:\n{e}")
        else:
            messagebox.showinfo("No Changes", "No paths needed fixing (no changes made).")

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
                    
                    # Fix: Safe index access with modulo to prevent IndexError
                    available_series = []
                    for series in episodic_groups.keys():
                        episodes = episodic_groups[series]
                        idx = episode_trackers[series] % len(episodes)  # Safe index
                        if episodes[idx]["path"] not in recent_paths:
                            available_series.append(series)
                    
                    if not available_standalone and not available_series:
                        recent_videos = []
                        recent_paths = set()
                        available_standalone = list(standalone_videos)
                        available_series = list(episodic_groups.keys())
                        random.shuffle(available_standalone)
                        random.shuffle(available_series)
                    
                    # Weighted choice based on content count
                    if available_standalone and available_series:
                        total_standalone = len(available_standalone)
                        total_series_eps = sum(len(episodic_groups[s]) for s in available_series)
                        if random.random() < total_standalone / (total_standalone + total_series_eps):
                            choice_type = "standalone"
                        else:
                            choice_type = "series"
                    elif available_standalone:
                        choice_type = "standalone"
                    elif available_series:
                        choice_type = "series"
                    else:
                        choice_type = "standalone"
                    
                    if choice_type == "series" and available_series:
                        series_name = random.choice(available_series)
                        episode_idx = episode_trackers[series_name] % len(episodic_groups[series_name])  # Safe index
                        
                        if self.sequential_var.get():
                            video = episodic_groups[series_name][episode_idx]
                        else:
                            # Fix: Direct random index
                            episode_idx = random.randint(0, len(episodic_groups[series_name]) - 1)
                            video = episodic_groups[series_name][episode_idx]
                        
                        episode_trackers[series_name] = (episode_idx + 1) % len(episodic_groups[series_name])
                    else:
                        video = random.choice(available_standalone)
                else:
                    available_videos = [v for v in filtered_videos if v["path"] not in recent_paths]
                    if not available_videos:
                        recent_videos = []
                        available_videos = list(filtered_videos)
                        random.shuffle(available_videos)
                
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
                    "collection_id": video["collection"]["id"],
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
                    "collection_id": video["collection"]["id"],
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
                
                # Fix: Safe index access with modulo to prevent IndexError
                available_series = []
                for series in episodic_groups.keys():
                    episodes = episodic_groups[series]
                    idx = episode_trackers[series] % len(episodes)  # Safe index
                    if episodes[idx]["path"] not in recent_paths:
                        available_series.append(series)
                
                # If no available content, reset recent list (emergency fallback)
                if not available_standalone and not available_series:
                    recent_videos = []
                    recent_paths = set()
                    available_standalone = list(standalone_videos)  # Fresh copy
                    available_series = list(episodic_groups.keys())
                    # Shuffle to avoid same sequence after reset
                    random.shuffle(available_standalone)
                    random.shuffle(available_series)
                
                # Weighted choice based on content count (not 50/50)
                if available_standalone and available_series:
                    total_standalone = len(available_standalone)
                    total_series_eps = sum(len(episodic_groups[s]) for s in available_series)
                    # Probability proportional to content count
                    if random.random() < total_standalone / (total_standalone + total_series_eps):
                        choice_type = "standalone"
                    else:
                        choice_type = "series"
                elif available_standalone:
                    choice_type = "standalone"
                elif available_series:
                    choice_type = "series"
                else:
                    choice_type = "standalone"  # Fallback (shouldn't reach here)
                
                if choice_type == "series" and available_series:
                    # Pick a random series
                    series_name = random.choice(available_series)
                    episode_idx = episode_trackers[series_name] % len(episodic_groups[series_name])  # Safe index
                    
                    # Sequential tracking: always continue from last episode
                    # Otherwise pick random episode if sequential is disabled
                    if self.sequential_var.get():
                        # Continue from last played episode
                        video = episodic_groups[series_name][episode_idx]
                    else:
                        # Fix: Direct random index instead of random.choice + index()
                        episode_idx = random.randint(0, len(episodic_groups[series_name]) - 1)
                        video = episodic_groups[series_name][episode_idx]
                    
                    # Advance episode tracker (loop back to start if at end)
                    episode_trackers[series_name] = (episode_idx + 1) % len(episodic_groups[series_name])
                else:
                    # Pick random standalone video (available_standalone is guaranteed non-empty here)
                    video = random.choice(available_standalone)
            else:
                # Standard random selection with 24-hour rule
                available_videos = [v for v in filtered_videos if v["path"] not in recent_paths]
                if not available_videos:
                    # Reset if no videos available (emergency fallback)
                    recent_videos = []
                    available_videos = list(filtered_videos)
                    random.shuffle(available_videos)  # Shuffle to avoid same sequence
                
                video = random.choice(available_videos)
            
            # Add to schedule
            day_index = current_time.weekday()
            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            day = days[day_index]
            time_str = current_time.strftime("%H:%M:%S")

            new_schedule[day].append({
                "time": time_str,
                "collection_id": video["collection"]["id"],
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
                "collection_id": video["collection"]["id"],
                "channel": target_channel,
                "source": "sequential"
            })

            current_time += timedelta(seconds=video["duration"])

    def _save_schedule(self, new_schedule, target_channel):
        """Save the generated schedule to file"""
        schedule_filename = SCHEDULE_DIR / f"schedule_{target_channel}.json"

        # Check if this is a daypart schedule
        if "daypart_config" in new_schedule:
            # Daypart mode: save daypart config with empty weekly/calendar sections
            daypart_data = new_schedule["daypart_config"]
            enabled = new_schedule.get("enabled", False)

            final_schedule = {
                "daypart_config": daypart_data,
                "enabled": enabled,
                "weekly": {},
                "calendar": {}
            }

            with open(schedule_filename, "w", encoding="utf-8") as f:
                json.dump(final_schedule, f, indent=2, ensure_ascii=False)

            # Count blocks for status message
            time_blocks = daypart_data.get("time_blocks", [])
            marathons = daypart_data.get("marathons", [])
            gap_filler = daypart_data.get("gap_filler", {})
            episodic_status = " (with episodic)" if self.episodic_var.get() else ""
            messagebox.showinfo("Success", f"Daypart schedule for '{target_channel}': {len(time_blocks)} time blocks, {len(marathons)} marathons saved!{episodic_status}")
        # Check if this is a calendar schedule
        elif "calendar" in new_schedule:
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
        """Detect and group episodic/sequential content
        
        Uses two methods:
        1. Check for 'episodic' tag in collection data (explicit)
        2. Filename pattern detection (implicit)
        """
        episodic_groups = {}
        standalone_videos = []
        
        # First pass: Check for explicit episodic tags in collection data
        for video in all_videos:
            collection = video.get("collection", {})
            tags = collection.get("tags", [])
            
            # Check if this video has an "episodic" tag
            if tags and "episodic" in [t.lower() for t in tags]:
                # Use collection name or id as series identifier
                series_name = collection.get("name", collection.get("id", "unknown"))
                series_key = f"tagged:{series_name.lower()}"
                
                if series_key not in episodic_groups:
                    episodic_groups[series_key] = []
                episodic_groups[series_key].append(video)
            else:
                # Will be processed in second pass (filename detection)
                standalone_videos.append(video)
        
        # Second pass: Filename pattern detection for remaining videos
        filename_groups = {}
        for video in standalone_videos:
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
                if series_name not in filename_groups:
                    filename_groups[series_name] = []
                filename_groups[series_name].append(video)
        
        # Merge filename-detected groups with tagged groups
        for series_name, videos in filename_groups.items():
            if len(videos) >= 2:
                episodic_groups[series_name] = videos
        
        # Move single-episode filename detections to standalone
        final_standalone = []
        for video in standalone_videos:
            name = Path(video["path"]).stem.lower()
            found_in_group = False
            
            import re
            patterns = [
                r'(.+?)\s*[s]\d+[e]\d+',
                r'(.+?)\s*season\s*\d+.*episode\s*\d+',
                r'(.+?)\s*\d+x\d+',
                r'(.+?)\s*ep\s*\d+',
                r'(.+?)\s*episode\s*\d+',
                r'(.+?)\s*part\s*\d+',
                r'(.+?)\s*\d{2,3}$',
                r'^(.+?)\s+\d+$',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, name, re.IGNORECASE)
                if match:
                    series_name = match.group(1).strip()
                    if series_name in filename_groups and len(filename_groups[series_name]) >= 2:
                        found_in_group = True
                        break
            
            if not found_in_group:
                final_standalone.append(video)
        
        # Sort episodes within each group by episode number
        for series_name in episodic_groups:
            episodic_groups[series_name] = sorted(
                episodic_groups[series_name],
                key=lambda x: self._extract_episode_number(Path(x["path"]).stem)
            )
        
        return episodic_groups, final_standalone
    
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
            from akiratv.collection_wizard import launch_collection_wizard
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
            base_dir = script_dir.parents[1]
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
            # Auto-update channel to match profile name
            self.channel_var.set(selected)
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
        # Auto-update channel to match profile name
        self.channel_var.set(profile_name)
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
        # Clear added videos when switching profiles to avoid blacklist issues
        # The blacklist is profile-specific, so we need to start fresh
        self.added_videos.clear()
        self.video_to_collection_map.clear()
        # Load blacklist BEFORE updating display so it reflects correctly
        self.blacklisted_videos = load_blacklist(self.current_profile)
        # Only update display if widgets have been created
        if hasattr(self, 'added_list'):
            self.update_added_list_display()
        
        self.collections = load_collections(self.current_profile)
        self.collection_list.delete(0, tk.END)
        for col in self.collections:
            self.collection_list.insert(tk.END, col["name"])

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
