# akiratv/daypart_scheduler_mixin.py
"""
Daypart Scheduler Mixin for AkiraTV

Provides all daypart scheduling functionality as a mixin class.
Extracted from simple_scheduler.py to improve modularity and reduce file size.

Usage:
    class SimpleSchedulerWizard(DaypartSchedulerMixin, other_mixins...):
        pass
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
from datetime import datetime, date, timedelta
from pathlib import Path

from pathlib import Path
from akiratv.daypart_scheduler import (
    TimeBlock, MarathonConfig, GapFillerConfig,
    DaypartScheduler, parse_time_string, validate_daypart_config,
    generate_daypart_schedule, detect_gaps
)
from akiratv.daypart_approximate import (
    approximate_block_timing, approximate_block_timing_v2
)
from akiratv.collections import load_collections

logger = logging.getLogger(__name__)


class DaypartSchedulerMixin:
    """
    Mixin class providing daypart scheduling UI and logic.
    
    Subclasses must provide:
        - self.root: The Tk root window
        - self.current_channel: Current channel name
        - self.current_profile: Current profile name
        - self.blacklisted_videos: Set of blacklisted video paths
        - self.daypart_scheduler: DaypartScheduler instance
        - self.daypart_time_blocks: List of TimeBlock instances
        - self.daypart_marathons: List of MarathonConfig instances  
        - self.daypart_gap_filler: GapFillerConfig instance
        - self.daypart_enabled: Boolean for daypart enabled state
        - self.daypart_preview_entries: List of preview schedule entries
    """
    
    # ========================================================================
    # TIME BLOCK DIALOG
    # ========================================================================
    
    class EditBlockDialog(tk.Toplevel):
        """Dialog for creating/editing a time block"""
        def __init__(self, parent, block=None, available_tags=None, available_videos=None,
                     available_collections=None):
            super().__init__(parent)
            self.parent = parent
            self.block = block
            self.available_tags = available_tags or []
            self.available_videos = available_videos or []
            self.available_collections = available_collections or []
            self._ep_loaded_file = ""  # path of the last browsed collection file
            self.result = None
            self.transient(parent)
            self.grab_set()
            self.title("Edit Time Block")
            self.geometry("700x500")
            self.resizable(True, True)
            # Center the dialog on parent
            self.center_on_parent()
            self.create_widgets()
            if block:
                self.populate_fields()
        
        def center_on_parent(self):
            """Center the dialog window on the parent window"""
            self.update_idletasks()
            # Get parent position and size
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_w = self.parent.winfo_width()
            parent_h = self.parent.winfo_height()
            # Get dialog size
            dialog_w = 700
            dialog_h = 500
            # Calculate center position
            x = parent_x + (parent_w - dialog_w) // 2
            y = parent_y + (parent_h - dialog_h) // 2
            self.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")
        
        def create_widgets(self):
            main_frame = ttk.Frame(self, padding=10)
            main_frame.pack(fill="both", expand=True)
            
            # Content type
            type_frame = ttk.Frame(main_frame)
            type_frame.pack(fill="x", pady=(0, 10))
            ttk.Label(type_frame, text="Content Type:").pack(side="left", padx=(0, 5))
            self.type_var = tk.StringVar(value="tag")
            ttk.Radiobutton(type_frame, text="Tag (random)", variable=self.type_var,
                           value="tag", command=self.on_type_change).pack(side="left", padx=5)
            ttk.Radiobutton(type_frame, text="Specific Video", variable=self.type_var,
                           value="video", command=self.on_type_change).pack(side="left", padx=5)
            ttk.Radiobutton(type_frame, text="Episodic", variable=self.type_var,
                           value="episodic", command=self.on_type_change).pack(side="left", padx=5)
            
            # Tag selection (shown for tag mode)
            self.tag_frame = ttk.LabelFrame(main_frame, text="Tag Settings", padding=6)
            self.tag_frame.pack(fill="x", pady=(0, 10))

            # Collection file row for tag mode
            tag_col_row = ttk.Frame(self.tag_frame)
            tag_col_row.pack(fill="x", pady=(0, 4))
            ttk.Label(tag_col_row, text="Collection:").pack(side="left", padx=(0, 5))
            self._tag_col_file = ""  # path of loaded collection file for tag mode
            self._tag_col_file_label = ttk.Label(tag_col_row, text="Using profile collections",
                                                  font=("", 8), foreground="gray")
            self._tag_col_file_label.pack(side="left", padx=(0, 6))
            ttk.Button(tag_col_row, text="Browse…", command=self._tag_browse_collection).pack(side="left")

            # Tag combobox row
            tag_select_row = ttk.Frame(self.tag_frame)
            tag_select_row.pack(fill="x", pady=(0, 4))
            ttk.Label(tag_select_row, text="Select Tag:").pack(side="left", padx=(0, 5))
            self.tag_var = tk.StringVar()
            self.tag_combo = ttk.Combobox(tag_select_row, textvariable=self.tag_var, state="normal")
            self.tag_combo.pack(side="left", fill="x", expand=True)
            self.tag_var.trace_add("write", self.on_tag_select)
            ttk.Button(tag_select_row, text="New", command=self.on_new_tag).pack(side="left", padx=5)
            self.tag_combo['values'] = self.available_tags

            # Tag video list (inside tag_frame)
            self.tag_video_list_frame = ttk.Frame(self.tag_frame)
            self.tag_video_list_frame.pack(fill="both", expand=True, pady=(4, 0))
            ttk.Label(self.tag_video_list_frame, text="Videos with this tag:").pack(anchor="w")
            tag_list_frame = ttk.Frame(self.tag_video_list_frame)
            tag_list_frame.pack(fill="both", expand=True, pady=(5, 0))
            self.tag_video_list = tk.Listbox(tag_list_frame, height=6)
            self.tag_video_list.pack(side="left", fill="both", expand=True)
            tag_scroll = ttk.Scrollbar(tag_list_frame, orient="vertical", command=self.tag_video_list.yview)
            tag_scroll.pack(side="right", fill="y")
            self.tag_video_list.configure(yscrollcommand=tag_scroll.set)
            
            # Video count selection
            count_frame = ttk.Frame(main_frame)
            count_frame.pack(fill="x", pady=(0, 10))
            ttk.Label(count_frame, text="Play:").pack(side="left", padx=(0, 5))
            self.video_count_var = tk.StringVar(value="single")
            count_combo = ttk.Combobox(count_frame, textvariable=self.video_count_var, 
                                      values=["single", "2", "3", "4", "5", "all"], 
                                      state="readonly", width=12)
            count_combo.pack(side="left", padx=5)
            count_combo.bind("<<ComboboxSelected>>", self.on_video_count_change)
            ttk.Label(count_frame, text="video(s) from tag").pack(side="left", padx=5)
            
            # Day selection
            day_frame = ttk.Frame(main_frame)
            day_frame.pack(fill="x", pady=(0, 10))
            ttk.Label(day_frame, text="Days:").pack(side="left", padx=(0, 5))
            self.day_vars = {}
            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            for day in days:
                var = tk.BooleanVar(value=False)
                chk = ttk.Checkbutton(day_frame, text=day[:3].title(), variable=var)
                chk.pack(side="left", padx=2)
                self.day_vars[day] = var
            self.all_days_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(day_frame, text="All", variable=self.all_days_var,
                           command=self.on_all_days_toggle).pack(side="left", padx=5)
            
            # Start/End Time
            time_frame = ttk.Frame(main_frame)
            time_frame.pack(fill="x", pady=(0, 10))
            ttk.Label(time_frame, text="Start Time:").pack(side="left", padx=(0, 5))
            self.start_var = tk.StringVar(value="00:00")
            self.start_entry = ttk.Entry(time_frame, textvariable=self.start_var, width=8)
            self.start_entry.pack(side="left", padx=5)
            ttk.Label(time_frame, text="End Time:").pack(side="left", padx=(10, 5))
            self.end_var = tk.StringVar(value="01:00")
            self.end_entry = ttk.Entry(time_frame, textvariable=self.end_var, width=8)
            self.end_entry.pack(side="left", padx=5)
            ttk.Button(time_frame, text="Auto Calc", command=self.on_auto_calc_end_time).pack(side="left", padx=5)
            ttk.Label(time_frame, text="(HH:MM format, 24-hour)").pack(side="left", padx=10)
            
            # Duration display
            self.duration_label = ttk.Label(time_frame, text="Duration: 0 hours")
            self.duration_label.pack(side="left", padx=20)
            self.start_var.trace_add("write", self.update_duration)
            self.end_var.trace_add("write", self.update_duration)
            
            # Approximate checkbox
            self.approximate_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(time_frame, text="Approximate", variable=self.approximate_var,
                          command=self.on_approximate_toggle).pack(side="left", padx=20)
            self.approximate_hint = ttk.Label(time_frame, text="(Adjust to fit around existing videos)",
                                            font=("", 8, "italic"))
            self.approximate_hint.pack(side="left", padx=5)
            
            # Video selection (for video mode)
            self.video_frame = ttk.Frame(main_frame)
            self.video_frame.pack(fill="both", expand=True, pady=(0, 10))
            ttk.Label(self.video_frame, text="Search Videos:").pack(anchor="w")
            search_frame = ttk.Frame(self.video_frame)
            search_frame.pack(fill="x", pady=(5, 0))
            self.video_search_var = tk.StringVar()
            self.video_search_var.trace_add("write", self.filter_videos)
            search_entry = ttk.Entry(search_frame, textvariable=self.video_search_var)
            search_entry.pack(side="left", fill="x", expand=True)
            ttk.Button(search_frame, text="Clear", command=self.clear_video_search).pack(side="left", padx=5)
            
            list_frame = ttk.Frame(self.video_frame)
            list_frame.pack(fill="both", expand=True, pady=(5, 0))
            self.video_list = tk.Listbox(list_frame, height=8, selectmode=tk.EXTENDED)
            self.video_list.pack(side="left", fill="both", expand=True)
            video_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.video_list.yview)
            video_scroll.pack(side="right", fill="y")
            self.video_list.configure(yscrollcommand=video_scroll.set)
            self.video_list.bind("<<ListboxSelect>>", self.on_video_select)
            
            self.populate_video_list()

            self.selected_video_label = ttk.Label(self.video_frame, text="Selected: None", foreground="blue")
            self.selected_video_label.pack(pady=(5, 0))
            
            # Episodic panel (initially hidden)
            self.episodic_frame = ttk.LabelFrame(main_frame, text="Episodic Settings", padding=8)

            # Collection row: combobox + Browse button
            col_row = ttk.Frame(self.episodic_frame)
            col_row.pack(fill="x", pady=(0, 4))
            ttk.Label(col_row, text="Collection:").pack(side="left", padx=(0, 5))
            self.ep_collection_var = tk.StringVar()
            col_names = [c.get("name", c.get("id", "")) for c in self.available_collections]
            self.ep_collection_combo = ttk.Combobox(col_row, textvariable=self.ep_collection_var,
                                                    values=col_names, state="readonly", width=26)
            self.ep_collection_combo.pack(side="left", padx=(0, 4))
            if col_names:
                self.ep_collection_combo.current(0)
            self.ep_collection_combo.bind("<<ComboboxSelected>>", self._on_ep_collection_select)
            ttk.Button(col_row, text="Browse…", command=self._ep_browse_collection).pack(side="left")
            ttk.Label(col_row, text="← load a collections_*.json file",
                      font=("", 8, "italic"), foreground="gray").pack(side="left", padx=6)

            # Show the loaded file path
            self._ep_file_label = ttk.Label(self.episodic_frame, text="No file loaded",
                                            font=("", 8), foreground="gray")
            self._ep_file_label.pack(anchor="w", pady=(0, 4))

            # Video list for the selected collection
            ep_list_lf = ttk.LabelFrame(self.episodic_frame, text="Videos in collection", padding=4)
            ep_list_lf.pack(fill="both", expand=True, pady=(0, 6))
            ep_list_inner = ttk.Frame(ep_list_lf)
            ep_list_inner.pack(fill="both", expand=True)
            self.ep_video_list = tk.Listbox(ep_list_inner, height=6, font=("TkDefaultFont", 9))
            self.ep_video_list.pack(side="left", fill="both", expand=True)
            ep_scroll = ttk.Scrollbar(ep_list_inner, orient="vertical", command=self.ep_video_list.yview)
            ep_scroll.pack(side="right", fill="y")
            self.ep_video_list.configure(yscrollcommand=ep_scroll.set)

            # Start season / episode
            start_row = ttk.Frame(self.episodic_frame)
            start_row.pack(fill="x", pady=(0, 6))
            ttk.Label(start_row, text="Start Season:").pack(side="left", padx=(0, 4))
            self.ep_season_var = tk.IntVar(value=1)
            ttk.Spinbox(start_row, from_=1, to=99, textvariable=self.ep_season_var, width=5).pack(side="left", padx=(0, 12))
            ttk.Label(start_row, text="Start Episode:").pack(side="left", padx=(0, 4))
            self.ep_episode_var = tk.IntVar(value=1)
            ttk.Spinbox(start_row, from_=1, to=999, textvariable=self.ep_episode_var, width=5).pack(side="left")

            epb_row = ttk.Frame(self.episodic_frame)
            epb_row.pack(fill="x")
            ttk.Label(epb_row, text="Episodes per block:").pack(side="left", padx=(0, 5))
            self.ep_count_var = tk.StringVar(value="1")
            ttk.Combobox(epb_row, textvariable=self.ep_count_var,
                         values=["1","2","3","4","5","all"],
                         state="readonly", width=6).pack(side="left")

            # Populate video list for the initially selected collection
            self._refresh_ep_video_list()

            # Buttons
            btn_frame = ttk.Frame(main_frame)
            btn_frame.pack(fill="x", pady=(10, 0))
            ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side="right", padx=5)
            ttk.Button(btn_frame, text="Save", command=self.on_save).pack(side="right", padx=5)

            # Set correct initial visibility based on default type
            self.on_type_change()
        
        def _refresh_ep_video_list(self):
            """Populate the episodic video listbox from the currently selected collection."""
            self.ep_video_list.delete(0, tk.END)
            idx = self.ep_collection_combo.current()
            if idx < 0 or idx >= len(self.available_collections):
                return
            col = self.available_collections[idx]
            import re as _re
            def _sort_key(v):
                fname = Path(v.get("path", "")).stem
                m = _re.search(r"[Ss](\d+)[Ee](\d+)", fname)
                if m:
                    return (int(m.group(1)), int(m.group(2)))
                m2 = _re.search(r"(\d+)[xX](\d+)", fname)
                if m2:
                    return (int(m2.group(1)), int(m2.group(2)))
                return (0, 0)
            videos = sorted(col.get("videos", []), key=_sort_key)
            for v in videos:
                fname = Path(v.get("path", "")).name
                dur = v.get("duration", 0)
                mins = int(dur // 60) if dur else 0
                self.ep_video_list.insert(tk.END, f"{fname}  ({mins}m)")

        def _on_ep_collection_select(self, event=None):
            self._refresh_ep_video_list()

        def _ep_browse_collection(self):
            """Let the user pick a collections_*.json file directly."""
            from tkinter import filedialog
            path = filedialog.askopenfilename(
                title="Open collection file",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            if not path:
                return
            try:
                import json as _json
                with open(path, "r", encoding="utf-8") as f:
                    data = _json.load(f)
                new_cols = data.get("collections", [])
                if not new_cols:
                    messagebox.showwarning("Empty", "No collections found in that file.")
                    return
                # Replace the collection list entirely with what was loaded
                self.available_collections = new_cols
                self._ep_loaded_file = path  # remember for saving
                col_names = [c.get("name", c.get("id", "")) for c in self.available_collections]
                self.ep_collection_combo["values"] = col_names
                self.ep_collection_combo.current(0)
                self._ep_file_label.config(text=f"File: {Path(path).name}")
                self._refresh_ep_video_list()
            except Exception as ex:
                messagebox.showerror("Error", f"Could not load file:\n{ex}")

        def _tag_browse_collection(self):
            """Let the user pick a collections_*.json file to source tags from."""
            from tkinter import filedialog
            path = filedialog.askopenfilename(
                title="Open collection file",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            if not path:
                return
            try:
                import json as _json
                with open(path, "r", encoding="utf-8") as f:
                    data = _json.load(f)
                cols = data.get("collections", [])
                if not cols:
                    messagebox.showwarning("Empty", "No collections found in that file.")
                    return
                self._tag_col_file = path
                self._tag_col_file_label.config(text=f"File: {Path(path).name}")
                self.available_videos = []
                all_tags = set()
                for col in cols:
                    for video in col.get("videos", []):
                        video["collection"] = col
                        self.available_videos.append(video)
                    all_tags.update(col.get("tags", []))
                # If no tags defined, use collection names as tag options
                if not all_tags:
                    all_tags = {col.get("name", col.get("id", "")) for col in cols}
                self.available_tags = sorted(list(all_tags))
                self.tag_combo["values"] = self.available_tags
                if self.available_tags:
                    self.tag_combo.set(self.available_tags[0])
                self.populate_tag_videos()
            except Exception as ex:
                messagebox.showerror("Error", f"Could not load file:\n{ex}")

        def on_type_change(self):
            """Toggle between tag, video, and episodic mode"""
            t = self.type_var.get()
            
            if t == "tag":
                self.tag_frame.pack(fill="x", pady=(0, 10))
                if hasattr(self, 'video_frame'):
                    self.video_frame.pack_forget()
                if hasattr(self, 'episodic_frame'):
                    self.episodic_frame.pack_forget()
            elif t == "video":
                self.tag_frame.pack_forget()
                if hasattr(self, 'episodic_frame'):
                    self.episodic_frame.pack_forget()
                if hasattr(self, 'video_frame'):
                    self.video_frame.pack(fill="both", expand=True, pady=(0, 10))
                    self.populate_video_list()
            else:  # episodic
                self.tag_frame.pack_forget()
                if hasattr(self, 'video_frame'):
                    self.video_frame.pack_forget()
                if hasattr(self, 'episodic_frame'):
                    self.episodic_frame.pack(fill="x", pady=(0, 10))
        
        def on_tag_select(self, *args):
            """Update video list when tag changes and recalculate end time"""
            self.populate_tag_videos()
            # Auto-calculate end time based on current video count selection
            self.on_video_count_change()
        
        def on_new_tag(self):
            """Create a new tag"""
            from tkinter import simpledialog
            new_tag = simpledialog.askstring("New Tag", "Enter tag name:", parent=self)
            if new_tag and new_tag not in self.available_tags:
                self.available_tags.append(new_tag)
                self.tag_combo['values'] = self.available_tags
                self.tag_var.set(new_tag)
        
        def on_video_count_change(self, event=None):
            """Handle video count change - auto-calculate end time based on selected videos"""
            self.on_auto_calc_end_time()
        
        def on_auto_calc_end_time(self):
            """Calculate end time based on selected tag/episodic and video count"""
            t = self.type_var.get()

            if t == "episodic":
                # Use videos from the selected collection
                idx = self.ep_collection_combo.current() if hasattr(self, 'ep_collection_combo') else -1
                if idx < 0 or idx >= len(self.available_collections):
                    return
                col_videos = self.available_collections[idx].get("videos", [])
                if not col_videos:
                    return
                ep_count_str = self.ep_count_var.get() if hasattr(self, 'ep_count_var') else "1"
                durations = [v.get("duration", 0) for v in col_videos if v.get("duration")]
                if not durations:
                    return
                avg = sum(durations) / len(durations)
                if ep_count_str == "all":
                    total_duration_seconds = sum(durations)
                else:
                    try:
                        total_duration_seconds = avg * int(ep_count_str)
                    except (ValueError, TypeError):
                        total_duration_seconds = avg
            else:
                video_count = self.video_count_var.get()
                selected_tag = self.tag_var.get()

                if not selected_tag or not video_count:
                    return

                tag_videos = []
                for video in self.available_videos:
                    collection_tags = video.get("collection", {}).get("tags", [])
                    collection_name = video.get("collection", {}).get("name", "")
                    if selected_tag in collection_tags or selected_tag == collection_name:
                        tag_videos.append(video)

                # If no tag match, use all available videos (collection has no tags defined)
                if not tag_videos:
                    tag_videos = list(self.available_videos)

                if not tag_videos:
                    return

                total_duration_seconds = 0
                if video_count == "all":
                    total_duration_seconds = sum(v.get("duration", 0) for v in tag_videos if v.get("duration"))
                elif video_count == "single":
                    durations = [v.get("duration", 0) for v in tag_videos if v.get("duration")]
                    total_duration_seconds = sum(durations) / len(durations) if durations else 3600
                else:
                    try:
                        count = int(video_count)
                        durations = [v.get("duration", 0) for v in tag_videos if v.get("duration")]
                        avg = sum(durations) / len(durations) if durations else (tag_videos[0].get("duration", 0) or 3600)
                        total_duration_seconds = avg * count
                    except ValueError:
                        pass
            
            # Calculate end time from start time + duration
            if total_duration_seconds > 0:
                try:
                    from datetime import timedelta
                    # Import parse_time_string locally
                    from akiratv.daypart_scheduler import parse_time_string
                    start_time = parse_time_string(self.start_var.get())
                    end_time = start_time + timedelta(seconds=total_duration_seconds)
                    # Format as HH:MM (24-hour)
                    end_time_str = end_time.strftime("%H:%M")
                    self.end_var.set(end_time_str)
                    # Update duration display
                    self.update_duration()
                except Exception as e:
                    # Keep default end time if calculation fails
                    pass
        
        def on_all_days_toggle(self):
            """Toggle all day checkboxes"""
            state = self.all_days_var.get()
            for var in self.day_vars.values():
                var.set(state)
        
        def populate_video_list(self):
            """Populate the video list with available videos"""
            self.video_list.delete(0, tk.END)
            for video in self.available_videos:
                filename = Path(video.get("path", "")).name
                self.video_list.insert(tk.END, f"{filename} ({video.get('collection', {}).get('name', 'Unknown')})")
        
        def populate_tag_videos(self):
            """Populate videos for selected tag"""
            selected_tag = self.tag_var.get()
            self.tag_video_list.delete(0, tk.END)
            if not selected_tag:
                return
            matched = []
            for video in self.available_videos:
                collection_tags = video.get("collection", {}).get("tags", [])
                collection_name = video.get("collection", {}).get("name", "")
                if selected_tag in collection_tags or selected_tag == collection_name:
                    matched.append(video)
            # If no tag match, show all videos (collection has no tags defined)
            display_videos = matched if matched else self.available_videos
            for video in display_videos:
                filename = Path(video.get("path", "")).name
                self.tag_video_list.insert(tk.END, filename)
        
        def filter_videos(self, *args):
            """Filter video list based on search"""
            search = self.video_search_var.get().lower()
            self.video_list.delete(0, tk.END)
            for video in self.available_videos:
                filename = Path(video.get("path", "")).name
                if search in filename.lower():
                    self.video_list.insert(tk.END, f"{filename} ({video.get('collection', {}).get('name', 'Unknown')})")
        
        def clear_video_search(self):
            """Clear video search"""
            self.video_search_var.set("")
            self.populate_video_list()
        
        def on_video_select(self, event):
            """Handle video selection"""
            selection = self.video_list.curselection()
            if selection:
                index = selection[0]
                video = self.available_videos[index]
                filename = Path(video.get("path", "")).name
                self.selected_video_label.config(text=f"Selected: {filename}")
        
        def update_duration(self, *args):
            """Update duration display"""
            try:
                start = parse_time_string(self.start_var.get())
                end = parse_time_string(self.end_var.get())
                if end < start:
                    end += __import__('datetime').timedelta(days=1)
                duration_hours = (end - start).total_seconds() / 3600
                self.duration_label.config(text=f"Duration: {duration_hours:.1f} hours")
            except:
                self.duration_label.config(text="Duration: Invalid")
        
        def populate_fields(self):
            """Populate fields from existing block"""
            self.start_var.set(self.block.start_time)
            self.end_var.set(self.block.end_time)
            self.type_var.set(self.block.content_type)
            
            if hasattr(self.block, 'approximate') and self.block.approximate:
                self.approximate_var.set(True)
            
            if self.block.content_type == "tag":
                self.tag_var.set(self.block.content_value)
                if self.block.video_count:
                    self.video_count_var.set(self.block.video_count)
                for day in self.block.days:
                    if day in self.day_vars:
                        self.day_vars[day].set(True)
                all_days = list(self.day_vars.keys())
                selected_days = [d for d, v in self.day_vars.items() if v.get()]
                if len(selected_days) == len(all_days):
                    self.all_days_var.set(True)
                # Restore collection file for tag blocks
                col_file = getattr(self.block, 'collection_file', "") or ""
                if col_file:
                    try:
                        import json as _json
                        with open(col_file, "r", encoding="utf-8") as f:
                            data = _json.load(f)
                        cols = data.get("collections", [])
                        if cols:
                            self._tag_col_file = col_file
                            self._tag_col_file_label.config(text=f"File: {Path(col_file).name}")
                            self.available_videos = []
                            all_tags = set()
                            for col in cols:
                                for video in col.get("videos", []):
                                    video["collection"] = col
                                    self.available_videos.append(video)
                                all_tags.update(col.get("tags", []))
                            self.available_tags = sorted(list(all_tags))
                            self.tag_combo["values"] = self.available_tags
                    except Exception:
                        pass
                self.tag_var.set(self.block.content_value)
                self.populate_tag_videos()
            elif self.block.content_type == "episodic":
                parts = self.block.content_value.split("|")
                col_id = parts[0] if parts else ""
                # Restore the collection file path and reload collections into combobox
                self._ep_loaded_file = getattr(self.block, 'collection_file', "") or ""
                if self._ep_loaded_file:
                    try:
                        import json as _json
                        with open(self._ep_loaded_file, "r", encoding="utf-8") as f:
                            data = _json.load(f)
                        loaded_cols = data.get("collections", [])
                        if loaded_cols:
                            self.available_collections = loaded_cols
                            col_names = [c.get("name", c.get("id", "")) for c in self.available_collections]
                            self.ep_collection_combo["values"] = col_names
                    except Exception:
                        pass
                    self._ep_file_label.config(text=f"File: {Path(self._ep_loaded_file).name}")
                for i, c in enumerate(self.available_collections):
                    if c.get("id", "") == col_id or c.get("name", "") == col_id:
                        self.ep_collection_combo.current(i)
                        break
                self.ep_season_var.set(int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1)
                self.ep_episode_var.set(int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1)
                self.ep_count_var.set(parts[3] if len(parts) > 3 else "1")
                for day in self.block.days:
                    if day in self.day_vars:
                        self.day_vars[day].set(True)
                self._refresh_ep_video_list()
            else:
                self.type_var.set("video")
                for i, video in enumerate(self.available_videos):
                    if video.get("path") == self.block.content_value:
                        self.video_list.selection_set(i)
                        break
            
            self.on_type_change()
        
        def on_cancel(self):
            """Cancel dialog"""
            self.result = None
            self.destroy()
        
        def on_approximate_toggle(self):
            """Handle approximate checkbox toggle"""
            if self.approximate_var.get():
                # Try to approximate and update the time fields
                self.try_approximate()
        
        def try_approximate(self):
            """Try to approximate timing to fit around existing blocks and gap filler videos"""
            # Get current time values
            start_time = self.start_var.get().strip()
            end_time = self.end_var.get().strip()
            
            if not start_time or not end_time:
                return
            
            # Get existing blocks from parent
            existing_blocks = []
            if hasattr(self.parent, 'daypart_time_blocks'):
                existing_blocks = self.parent.daypart_time_blocks
            
            # Get current block being edited (exclude from existing for edit mode)
            if self.block:
                existing_blocks = [b for b in existing_blocks if b.block_id != self.block.block_id]
            
            if not existing_blocks:
                # No existing blocks, return original
                return
            
            # Import the new functions for gap filler support
            from akiratv.daypart_scheduler import (
                detect_gaps, ScheduledEntry,
                convert_gap_filler_to_scheduled_entries,
                merge_blocks_and_gap_filler,
            )
            from akiratv.daypart_approximate import approximate_block_timing_v2
            
            # Detect gaps between blocks
            gaps = detect_gaps(existing_blocks)
            
            # Try to get gap filler videos if gap filler is enabled
            # This allows approximation to consider gap filler videos
            gap_filler_entries = []
            if hasattr(self.parent, 'daypart_gap_filler'):
                gap_filler_config = self.parent.daypart_gap_filler
                if gap_filler_config and gap_filler_config.enabled:
                    # Get available videos from parent
                    if hasattr(self.parent, 'available_videos'):
                        available_videos = self.parent.available_videos
                        if available_videos:
                            # Generate gap filler entries to get gap video timings
                            from akiratv.daypart_scheduler import fill_gaps_with_random
                            gap_filler_dicts = fill_gaps_with_random(
                                gaps, available_videos, gap_filler_config,
                                channel=getattr(self.parent, 'channel', ''),
                                target_date=getattr(self.parent, 'target_date', None)
                            )
                            if gap_filler_dicts:
                                gap_filler_entries = convert_gap_filler_to_scheduled_entries(gap_filler_dicts)
            
            # Merge blocks and gap filler entries
            existing_entries = merge_blocks_and_gap_filler(existing_blocks, gap_filler_entries)
            
            # Calculate tag duration (default 1 hour)
            tag_duration = 1.0
            if self.type_var.get() == "tag":
                video_count = self.video_count_var.get()
                try:
                    if video_count != "single" and video_count != "all":
                        tag_duration = float(video_count)
                except:
                    pass
            
            # Try to approximate using the new v2 function that considers gap filler
            result = approximate_block_timing_v2(
                start_time, end_time,
                existing_entries, gaps,
                tag_duration_hours=tag_duration
            )
            
            if result:
                adjusted_start, adjusted_end = result
                if adjusted_start != start_time or adjusted_end != end_time:
                    # Show info to user
                    gap_note = " (considered gap filler videos)" if gap_filler_entries else ""
                    messagebox.showinfo(
                        "Approximate Timing",
                        f"Adjusted timing to fit around existing videos{gap_note}:\n"
                        f"Original: {start_time} - {end_time}\n"
                        f"Adjusted: {adjusted_start} - {adjusted_end}"
                    )
                    # Update the time fields
                    self.start_var.set(adjusted_start)
                    self.end_var.set(adjusted_end)
            else:
                messagebox.showwarning(
                    "Cannot Approximate",
                    "Could not find a suitable time slot. Please adjust manually or check existing blocks."
                )
                self.approximate_var.set(False)
        
        def on_save(self):
            """Save block configuration"""
            start_time = self.start_var.get().strip()
            end_time = self.end_var.get().strip()
            
            # Validate time format
            try:
                parse_time_string(start_time)
                parse_time_string(end_time)
            except:
                messagebox.showerror("Error", "Invalid time format. Use HH:MM (24-hour)")
                return
            
            content_type = self.type_var.get()
            content_value = ""
            days = []
            video_count = None
            
            if content_type == "tag":
                content_value = self.tag_var.get().strip()
                if not content_value:
                    messagebox.showerror("Error", "Please select a tag")
                    return
                days = [day for day, var in self.day_vars.items() if var.get()]
                if self.all_days_var.get():
                    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                video_count = self.video_count_var.get()
            elif content_type == "episodic":
                idx = self.ep_collection_combo.current()
                if idx < 0 or idx >= len(self.available_collections):
                    messagebox.showerror("Error", "Please select a collection")
                    return
                col = self.available_collections[idx]
                col_id = col.get("id", col.get("name", ""))
                content_value = f"{col_id}|{self.ep_season_var.get()}|{self.ep_episode_var.get()}|{self.ep_count_var.get()}"
                days = [day for day, var in self.day_vars.items() if var.get()]
                if self.all_days_var.get():
                    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            else:
                selection = self.video_list.curselection()
                if not selection:
                    messagebox.showerror("Error", "Please select a video")
                    return
                video = self.available_videos[selection[0]]
                content_value = video.get("path", "")
            
            # Create block
            self.result = TimeBlock(
                start_time=start_time,
                end_time=end_time,
                content_type=content_type,
                content_value=content_value,
                block_id=self.block.block_id if self.block else None,
                days=days,
                video_count=video_count,
                approximate=self.approximate_var.get()
            )
            # Store the collection file path for episodic blocks so it can be
            # restored when the INI is reloaded and the block is edited again
            if content_type == "episodic":
                self.result.collection_file = getattr(self, '_ep_loaded_file', "") or ""
            elif content_type == "tag":
                self.result.collection_file = getattr(self, '_tag_col_file', "") or ""
            self.destroy()
    
    # ========================================================================
    # TIME BLOCK MANAGEMENT
    # ========================================================================
    
    def on_block_select(self, event):
        """Handle block selection in listbox"""
        pass  # Selection handled by Edit/Delete buttons
    
    def on_add_block(self):
        """Open dialog to add a new time block"""
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
            available_tags=sorted(list(available_tags)),
            available_videos=available_videos,
            available_collections=[]
        )
        self.root.wait_window(dialog)
        if dialog.result:
            self.daypart_time_blocks.append(dialog.result)
            self.update_block_list()
            self.update_preview_display()

    def on_add_gap_fill_block(self):
        """Add a 24h gap fill block from a chosen collection file"""
        from tkinter import filedialog
        import json as _json

        path = filedialog.askopenfilename(
            title="Select Collection File for Gap Fill",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = _json.load(f)
            cols = data.get("collections", [])
            if not cols:
                messagebox.showwarning("Empty", "No collections found in that file.")
                return

            # Use the filename (without extension) as the tag label
            tag_label = Path(path).stem

            block = TimeBlock(
                start_time="00:00",
                end_time="23:59",
                content_type="tag",
                content_value=tag_label,
                days=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
                video_count="all"
            )
            block.collection_file = path

            self.daypart_time_blocks.append(block)
            self.update_block_list()
            self.update_preview_display()
            messagebox.showinfo("Gap Fill Added",
                f"Gap fill block added using:\n{Path(path).name}\n\nTag: {tag_label}\nCovers: 00:00 - 23:59, all days")
        except Exception as ex:
            messagebox.showerror("Error", f"Could not load collection file:\n{ex}")
    
    def on_edit_block(self):
        """Edit selected time block"""
        selection = self.block_list.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a block to edit")
            return
        index = selection[0]
        block = self.daypart_time_blocks[index]
        
        collections = load_collections(self.current_profile)
        available_videos = []
        available_tags = set()
        for col in collections:
            for video in col.get("videos", []):
                if video["path"] not in self.blacklisted_videos:
                    video["collection"] = col
                    available_videos.append(video)
            available_tags.update(col.get("tags", []))
        
        # For episodic blocks, pre-load the saved collection so it shows up on edit
        edit_collections = []
        if block.content_type == "episodic":
            saved_col_id = block.content_value.split("|")[0] if block.content_value else ""
            # Search in the currently loaded profile collections
            for col in collections:
                if col.get("id", "") == saved_col_id or col.get("name", "") == saved_col_id:
                    edit_collections = [col]
                    break
            # If not found in profile, try loading from the saved collection_file path
            if not edit_collections:
                col_file = getattr(block, 'collection_file', "") or ""
                if col_file:
                    try:
                        import json as _json
                        with open(col_file, "r", encoding="utf-8") as f:
                            data = _json.load(f)
                        edit_collections = data.get("collections", [])
                    except Exception:
                        pass

        dialog = self.EditBlockDialog(
            self.root,
            block=block,
            available_tags=sorted(list(available_tags)),
            available_videos=available_videos,
            available_collections=edit_collections
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
    
    # ========================================================================
    # MARATHON MANAGEMENT  
    # ========================================================================
    
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
    
    # ========================================================================
    # GAP FILLER
    # ========================================================================
    
    def on_gap_source_change(self):
        """Handle gap filler source change"""
        self.update_gap_filler_ui()
    
    def on_edit_excluded_tags(self, event=None):
        """Open dialog to edit excluded tags"""
        collections = load_collections(self.current_profile)
        all_tags = set()
        for col in collections:
            all_tags.update(col.get("tags", []))
        
        # Import the dialog from daypart_ui
        from akiratv.Tools.daypart_ui import TagExclusionDialog
        dialog = TagExclusionDialog(
            self.root,
            available_tags=sorted(list(all_tags)),
            excluded_tags=self.daypart_gap_filler.excluded_tags
        )
        self.root.wait_window(dialog)
        if dialog.result is not None:
            self.daypart_gap_filler.excluded_tags = dialog.result
            self.update_gap_filler_label()
    
    def update_gap_filler_ui(self):
        """Update gap filler UI from config"""
        if hasattr(self, 'gap_enabled_var'):
            self.gap_enabled_var.set(self.daypart_gap_filler.enabled)
        if hasattr(self, 'gap_source_var'):
            self.gap_source_var.set(self.daypart_gap_filler.source)
        if hasattr(self, 'gap_24h_var'):
            self.gap_24h_var.set(self.daypart_gap_filler.respect_24h_norepeat)
        if hasattr(self, 'gap_shuffle_var'):
            self.gap_shuffle_var.set(self.daypart_gap_filler.shuffle)
        self.update_gap_filler_label()
    
    def update_gap_filler_label(self):
        """Update the excluded tags label"""
        if hasattr(self, 'gap_exclude_label'):
            if self.daypart_gap_filler.excluded_tags:
                count = len(self.daypart_gap_filler.excluded_tags)
                self.gap_exclude_label.config(text=f"[{count} tag(s) excluded]")
            else:
                self.gap_exclude_label.config(text="[None]")
    
    # ========================================================================
    # SCHEDULE PREVIEW & SAVE
    # ========================================================================
    
    def on_timeline_resize(self, event):
        """Redraw timeline on canvas resize"""
        self.draw_timeline()
    
    def on_generate_daypart_preview(self):
        """Generate daypart schedule preview (single day, weekly, or calendar range)"""
        print("[DEBUG] on_generate_daypart_preview called")
        try:
            collections = load_collections(self.current_profile)
            available_videos = []
            for col in collections:
                for video in col.get("videos", []):
                    if video["path"] not in self.blacklisted_videos:
                        video["collection"] = col
                        available_videos.append(video)

            # Also load videos from episodic/tag block collection files not in the current profile
            import json as _json
            loaded_col_ids = {col.get("id") for col in collections}
            for block in self.daypart_time_blocks:
                if block.content_type in ("episodic", "tag"):
                    col_file = getattr(block, "collection_file", "") or ""
                    if col_file:
                        try:
                            with open(col_file, "r", encoding="utf-8") as f:
                                extra_data = _json.load(f)
                            for col in extra_data.get("collections", []):
                                if col.get("id") not in loaded_col_ids:
                                    loaded_col_ids.add(col.get("id"))
                                    for video in col.get("videos", []):
                                        if video["path"] not in self.blacklisted_videos:
                                            video["collection"] = col
                                            video["_col_file"] = col_file  # stamp for fallback matching
                                            available_videos.append(video)
                        except Exception as ex:
                            logger.warning(f"Could not load collection file {col_file}: {ex}")
            
            # Check global approximate setting - try both self.app and self references
            try:
                use_global_approximate = self.app.use_approximation_var.get()
            except AttributeError:
                # If self.app doesn't exist, check self directly
                if hasattr(self, 'use_approximation_var'):
                    use_global_approximate = self.use_approximation_var.get()
                else:
                    use_global_approximate = False
            print(f"[DEBUG] Global approximate setting: {use_global_approximate}")
            
            # Create copies of blocks — approximate only if the block itself has it set
            # The global checkbox enables approximate for blocks that were individually marked
            time_blocks_for_preview = []
            for block in self.daypart_time_blocks:
                # Episodic blocks always run at their fixed configured time — never approximate
                if block.content_type == "episodic":
                    block_approximate = False
                else:
                    block_approximate = getattr(block, 'approximate', False) or use_global_approximate
                # Gap fill blocks (00:00-23:59) should never be approximate
                if block.start_time == "00:00" and block.end_time in ("23:59", "24:00"):
                    block_approximate = False
                block_copy = TimeBlock(
                    start_time=block.start_time,
                    end_time=block.end_time,
                    content_type=block.content_type,
                    content_value=block.content_value,
                    block_id=block.block_id,
                    days=block.days,
                    video_count=block.video_count,
                    approximate=block_approximate
                )
                block_copy.collection_file = getattr(block, 'collection_file', '') or ''
                time_blocks_for_preview.append(block_copy)
            
            daypart_config = {
                "daypart_config": {
                    "time_blocks": [b.to_dict() for b in time_blocks_for_preview],
                    "marathons": [m.to_dict() for m in self.daypart_marathons],
                    "gap_filler": self.daypart_gap_filler.to_dict()
                }
            }
            
            preview_mode = self.preview_mode_var.get()
            all_entries = []
            
            if preview_mode == "single":
                # Single day - today
                target_date = date.today()
                entries, last_time = generate_daypart_schedule(
                    daypart_config,
                    available_videos,
                    self.current_channel or "default",
                    target_date,
                    preview_mode=True,
                    preview_ep_state={}
                )
                day_name = target_date.strftime("%A").lower()
                for entry in entries:
                    entry["day"] = day_name
                all_entries.extend(entries)
                
            elif preview_mode == "weekly":
                # Generate for 7 days starting from today
                current_time = None
                preview_ep_state = {}  # shared across days so episodes advance
                for day_offset in range(7):
                    target_date = date.today() + timedelta(days=day_offset)
                    if current_time is None:
                        current_time = datetime.combine(target_date, datetime.min.time())
                    entries, last_time = generate_daypart_schedule(
                        daypart_config,
                        available_videos,
                        self.current_channel or "default",
                        target_date,
                        base_datetime=current_time,
                        preview_mode=True,
                        preview_ep_state=preview_ep_state
                    )
                    day_name = target_date.strftime("%A").lower()
                    for entry in entries:
                        entry["day"] = day_name
                        entry["date"] = target_date.strftime("%Y-%m-%d")
                    all_entries.extend(entries)
                    # Continue from last time for next day (don't reset to midnight)
                    if last_time:
                        logger.info(f"[DEBUG] Day {day_offset}: target={target_date}, last_time={last_time}")
                        current_time = last_time
                
            elif preview_mode == "calendar":
                # Generate for date range
                try:
                    start_parts = self.preview_start_date_var.get().split("-")
                    end_parts = self.preview_end_date_var.get().split("-")
                    start_date = date(int(start_parts[0]), int(start_parts[1]), int(start_parts[2]))
                    end_date = date(int(end_parts[0]), int(end_parts[1]), int(end_parts[2]))
                    
                    # Track the current time for continuous scheduling
                    current_time = None
                    current_date = start_date
                    preview_ep_state = {}  # shared across days so episodes advance
                    while current_date <= end_date:
                        if current_time is None:
                            current_time = datetime.combine(current_date, datetime.min.time())
                        entries, last_time = generate_daypart_schedule(
                            daypart_config,
                            available_videos,
                            self.current_channel or "default",
                            current_date,
                            base_datetime=current_time,
                            preview_mode=True,
                            preview_ep_state=preview_ep_state
                        )
                        day_name = current_date.strftime("%A").lower()
                        for entry in entries:
                            entry["day"] = day_name
                            entry["date"] = current_date.strftime("%Y-%m-%d")
                        all_entries.extend(entries)
                        # Continue from last time for next day (don't reset to midnight)
                        if last_time:
                            current_time = last_time
                        current_date += timedelta(days=1)
                except Exception as e:
                    messagebox.showerror("Date Error", f"Invalid date format. Use YYYY-MM-DD: {e}")
                    return
            
            self.daypart_preview_entries = all_entries
            self.update_preview_display()
            
            mode_text = {"single": "today", "weekly": "7 days", "calendar": "date range"}[preview_mode]
            messagebox.showinfo("Preview Generated",
                              f"Generated {len(all_entries)} schedule entries for {mode_text}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate preview: {str(e)}")
            logger.error(f"Daypart preview generation failed: {e}", exc_info=True)
    
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
        
        if self.daypart_scheduler.save_config(self.current_channel, daypart_config):
            messagebox.showinfo("Success", f"Daypart schedule saved for channel '{self.current_channel}'")
        else:
            messagebox.showerror("Error", "Failed to save daypart configuration")

    def _get_known_channels_daypart(self):
        """Return sorted list of known channel names for the Save as Normal Schedule combobox."""
        import json as _json
        channels = {"critters", "default"}
        for fname in ("config.json", "schedule.json"):
            try:
                with open(fname, "r", encoding="utf-8") as f:
                    data = _json.load(f)
                if fname == "config.json":
                    channels.update(data.get("channels", {}).keys())
                else:
                    for day_entries in data.get("weekly", {}).values():
                        for e in day_entries:
                            channels.add(e.get("channel", "default"))
            except Exception:
                pass
        if self.current_channel:
            channels.add(self.current_channel)
        return sorted(channels)

    def on_save_as_normal_schedule(self):
        """Generate and save the daypart schedule as a normal schedule_{channel}.json file."""
        import json as _json
        from pathlib import Path

        target_channel = self.save_normal_channel_var.get().strip()
        if not target_channel:
            messagebox.showerror("Error", "Please enter or select a channel name")
            return

        preview_mode = self.preview_mode_var.get()

        try:
            collections = load_collections(self.current_profile)
            available_videos = []
            for col in collections:
                for video in col.get("videos", []):
                    if video["path"] not in self.blacklisted_videos:
                        video["collection"] = col
                        available_videos.append(video)

            # Also load videos from episodic and tag block collection files
            loaded_col_ids = {col.get("id") for col in collections}
            for block in self.daypart_time_blocks:
                if block.content_type in ("episodic", "tag"):
                    col_file = getattr(block, "collection_file", "") or ""
                    if col_file:
                        try:
                            with open(col_file, "r", encoding="utf-8") as f:
                                extra_data = _json.load(f)
                            for col in extra_data.get("collections", []):
                                if col.get("id") not in loaded_col_ids:
                                    loaded_col_ids.add(col.get("id"))
                                    for video in col.get("videos", []):
                                        if video["path"] not in self.blacklisted_videos:
                                            video["collection"] = col
                                            video["_col_file"] = col_file
                                            available_videos.append(video)
                        except Exception as ex:
                            logger.warning(f"Could not load collection file {col_file}: {ex}")

            try:
                use_approx = self.use_approximation_var.get()
            except AttributeError:
                use_approx = False

            time_blocks_for_gen = []
            for block in self.daypart_time_blocks:
                block_copy = TimeBlock(
                    start_time=block.start_time,
                    end_time=block.end_time,
                    content_type=block.content_type,
                    content_value=block.content_value,
                    block_id=block.block_id,
                    days=block.days,
                    video_count=block.video_count,
                    approximate=use_approx
                )
                block_copy.collection_file = getattr(block, 'collection_file', '') or ''
                time_blocks_for_gen.append(block_copy)

            daypart_config = {
                "daypart_config": {
                    "time_blocks": [b.to_dict() for b in time_blocks_for_gen],
                    "marathons": [m.to_dict() for m in self.daypart_marathons],
                    "gap_filler": self.daypart_gap_filler.to_dict()
                }
            }

            all_entries = []
            current_time = None

            if preview_mode == "single":
                target_date = date.today()
                entries, _ = generate_daypart_schedule(
                    daypart_config, available_videos, target_channel, target_date)
                day_name = target_date.strftime("%A").lower()
                for e in entries:
                    e["day"] = day_name
                all_entries = entries

            elif preview_mode == "weekly":
                for day_offset in range(7):
                    target_date = date.today() + timedelta(days=day_offset)
                    if current_time is None:
                        current_time = datetime.combine(target_date, datetime.min.time())
                    entries, last_time = generate_daypart_schedule(
                        daypart_config, available_videos, target_channel,
                        target_date, base_datetime=current_time)
                    day_name = target_date.strftime("%A").lower()
                    for e in entries:
                        e["day"] = day_name
                        e["date"] = target_date.strftime("%Y-%m-%d")
                    all_entries.extend(entries)
                    if last_time:
                        current_time = last_time

            elif preview_mode == "calendar":
                start_parts = self.preview_start_date_var.get().split("-")
                end_parts = self.preview_end_date_var.get().split("-")
                start_date = date(int(start_parts[0]), int(start_parts[1]), int(start_parts[2]))
                end_date = date(int(end_parts[0]), int(end_parts[1]), int(end_parts[2]))
                current_date = start_date
                while current_date <= end_date:
                    if current_time is None:
                        current_time = datetime.combine(current_date, datetime.min.time())
                    entries, last_time = generate_daypart_schedule(
                        daypart_config, available_videos, target_channel,
                        current_date, base_datetime=current_time)
                    day_name = current_date.strftime("%A").lower()
                    for e in entries:
                        e["day"] = day_name
                        e["date"] = current_date.strftime("%Y-%m-%d")
                    all_entries.extend(entries)
                    if last_time:
                        current_time = last_time
                    current_date += timedelta(days=1)

        except Exception as ex:
            messagebox.showerror("Error", f"Failed to generate schedule: {ex}")
            logger.error(f"on_save_as_normal_schedule failed: {ex}", exc_info=True)
            return

        if not all_entries:
            messagebox.showwarning("Empty", "No entries were generated — nothing to save.")
            return

        try:
            from .daypart_scheduler import SCHEDULE_DIR as _SCHED_DIR
        except Exception:
            _SCHED_DIR = Path("user") / "schedules"
        schedule_dir = Path(_SCHED_DIR)
        schedule_dir.mkdir(parents=True, exist_ok=True)
        schedule_file = schedule_dir / f"schedule_{target_channel}.json"

        if preview_mode in ("weekly", "single"):
            weekly = {d: [] for d in ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]}
            for e in all_entries:
                day = e.get("day", "monday")
                weekly.setdefault(day, []).append({
                    "time": e.get("time", ""), "file": e.get("file", ""),
                    "duration": e.get("duration", 0), "source": e.get("source", "")
                })
            for day in weekly:
                weekly[day].sort(key=lambda x: x["time"])
            final = {"weekly": weekly}
        else:
            weekly = {d: [] for d in ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]}
            calendar = {}
            for e in all_entries:
                day = e.get("day", "monday")
                date_str = e.get("date", "")
                entry_data = {"time": e.get("time", ""), "file": e.get("file", ""),
                              "duration": e.get("duration", 0), "source": e.get("source", "")}
                weekly.setdefault(day, []).append(entry_data)
                if date_str:
                    if date_str not in calendar:
                        calendar[date_str] = {"date": date_str, "day": day, "entries": []}
                    calendar[date_str]["entries"].append(entry_data)
            for day in weekly:
                weekly[day].sort(key=lambda x: x["time"])
            for d in calendar.values():
                d["entries"].sort(key=lambda x: x["time"])
            final = {"weekly": weekly, "calendar": calendar}

        try:
            with open(schedule_file, "w", encoding="utf-8") as f:
                _json.dump(final, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Saved",
                f"Normal schedule saved for '{target_channel}'\n{schedule_file}\n\n{len(all_entries)} entries ({preview_mode} mode)")
        except Exception as ex:
            messagebox.showerror("Error", f"Failed to write file: {ex}")
            logger.error(f"on_save_as_normal_schedule write failed: {ex}", exc_info=True)

    def on_copy_daypart_preview(self):
        """Copy daypart preview to clipboard"""
        if not self.daypart_preview_entries:
            messagebox.showwarning("No Preview", "Generate a preview first")
            return
        
        print(f"[DEBUG] Copying {len(self.daypart_preview_entries)} entries")
        
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
            # Get title from file path or use default
            file_path = entry.get("file", "")
            if file_path:
                title = Path(file_path).stem
            else:
                title = entry.get("title", "Unknown")
            source = entry.get("source", "unknown")
            
            # Calculate end time for debug display
            duration = entry.get("duration", 0)
            print(f"[DEBUG] Copy: time={time_str}, duration={duration}")
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
                        print(f"[DEBUG] Copy calculated end: {end_time_str}")
                except Exception as e:
                    print(f"[DEBUG] Copy error: {e}")
                    pass
            
            text_lines.append(f"  {time_short}{end_time_str} [{entry.get('source','?')}|{entry.get('daypart_block_id','?')[:8]}] {title}")
        
        clipboard_text = "\n".join(text_lines)
        self.root.clipboard_clear()
        self.root.clipboard_append(clipboard_text)
        messagebox.showinfo("Copied", f"{len(self.daypart_preview_entries)} entries copied to clipboard")
    
    def on_save_daypart_work(self):
        """Save daypart blocks to an INI file for reuse"""
        try:
            import configparser
            from pathlib import Path
            
            # Check if there are blocks to save
            if not self.daypart_time_blocks and not self.daypart_marathons:
                messagebox.showwarning("Nothing to Save", "No time blocks or marathons to save")
                return
            
            # Ask user for save location
            file_path = filedialog.asksaveasfilename(
                title="Save Daypart Work",
                defaultextension=".ini",
                filetypes=[("INI files", "*.ini"), ("All files", "*.*")],
                initialfile="daypart_work.ini"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Create config parser
            config = configparser.ConfigParser()
            
            # Save time blocks
            for i, block in enumerate(self.daypart_time_blocks):
                section = f"Block_{i+1}"
                # Check if all days are selected
                all_days_list = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                is_all_days = block.days == all_days_list
                entry = {
                    "start_time": block.start_time,
                    "end_time": block.end_time,
                    "content_type": block.content_type,
                    "content_value": block.content_value,
                    "block_id": block.block_id,
                    "days": ",".join(block.days) if block.days else "",
                    "all_days": "true" if is_all_days else "false",
                    "video_count": block.video_count or "",
                    "approximate": str(getattr(block, 'approximate', False)).lower(),
                    "collection_file": getattr(block, 'collection_file', "") or ""
                }
                # For episodic blocks, also save the parsed fields explicitly for clarity
                if block.content_type == "episodic":
                    parts = block.content_value.split("|")
                    entry["collection_id"] = parts[0] if len(parts) > 0 else ""
                    entry["start_season"] = parts[1] if len(parts) > 1 else "1"
                    entry["start_episode"] = parts[2] if len(parts) > 2 else "1"
                    entry["episodes_per_block"] = parts[3] if len(parts) > 3 else "1"
                config[section] = entry
            
            # Save marathons
            for i, marathon in enumerate(self.daypart_marathons):
                section = f"Marathon_{i+1}"
                config[section] = {
                    "tag": marathon.tag,
                    "start_time": marathon.start_time,
                    "end_time": marathon.end_time,
                    "shuffle": str(marathon.shuffle),
                    "no_repeat_hours": str(marathon.no_repeat_hours),
                    "marathon_id": marathon.marathon_id or ""
                }
            
            # Save gap filler config
            if hasattr(self, 'daypart_gap_filler') and self.daypart_gap_filler:
                config["GapFiller"] = {
                    "enabled": str(self.daypart_gap_filler.enabled),
                    "source": self.daypart_gap_filler.source,
                    "collection_ids": ",".join(self.daypart_gap_filler.collection_ids) if self.daypart_gap_filler.collection_ids else "",
                    "tags": ",".join(self.daypart_gap_filler.tags) if self.daypart_gap_filler.tags else "",
                    "excluded_tags": ",".join(self.daypart_gap_filler.excluded_tags) if self.daypart_gap_filler.excluded_tags else "",
                    "respect_24h_norepeat": str(self.daypart_gap_filler.respect_24h_norepeat),
                    "shuffle": str(self.daypart_gap_filler.shuffle)
                }
            
            # Save global settings (including approximate checkbox)
            try:
                approx_val = self.app.use_approximation_var.get()
            except AttributeError:
                approx_val = self.use_approximation_var.get() if hasattr(self, 'use_approximation_var') else False
            config["Settings"] = {
                "use_approximation": str(approx_val).lower()
            }
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                config.write(f)
            
            block_count = len(self.daypart_time_blocks)
            marathon_count = len(self.daypart_marathons)
            messagebox.showinfo("Save Successful", 
                f"Daypart work saved to:\n{file_path}\n\nSaved:\n• {block_count} time block(s)\n• {marathon_count} marathon(s)")
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save: {str(e)}")
            logger.error(f"Daypart save work failed: {e}", exc_info=True)
    
    def on_load_daypart_work(self):
        """Load daypart blocks from an INI file"""
        try:
            import configparser
            from pathlib import Path
            
            # Ask user for file to load
            file_path = filedialog.askopenfilename(
                title="Load Daypart Work",
                filetypes=[("INI files", "*.ini"), ("All files", "*.*")]
            )
            
            if not file_path:
                return  # User cancelled
            
            # Read config
            config = configparser.ConfigParser()
            config.read(file_path, encoding='utf-8')
            
            # Load time blocks — APPEND to existing, don't overwrite
            for section in config.sections():
                if section.startswith("Block_"):
                    try:
                        all_days = config[section].get("all_days", "false").lower() == "true"
                        days_str = config[section].get("days", "")
                        if all_days:
                            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                        else:
                            days = days_str.split(",") if days_str else []
                        days = [d.strip() for d in days if d.strip()]

                        content_type = config[section].get("content_type", "tag")
                        content_value = config[section].get("content_value", "")

                        # For episodic blocks, reconstruct content_value from explicit fields if present
                        if content_type == "episodic":
                            col_id = config[section].get("collection_id", "")
                            start_season = config[section].get("start_season", "1")
                            start_episode = config[section].get("start_episode", "1")
                            episodes_per_block = config[section].get("episodes_per_block", "1")
                            if col_id:
                                content_value = f"{col_id}|{start_season}|{start_episode}|{episodes_per_block}"

                        block = TimeBlock(
                            start_time=config[section].get("start_time", "00:00"),
                            end_time=config[section].get("end_time", "00:00"),
                            content_type=content_type,
                            content_value=content_value,
                            block_id=config[section].get("block_id"),
                            days=days,
                            video_count=config[section].get("video_count") or None,
                            approximate=config[section].get("approximate", "false").lower() == "true"
                        )
                        # Restore collection_file for episodic blocks
                        block.collection_file = config[section].get("collection_file", "") or ""
                        self.daypart_time_blocks.append(block)
                    except Exception as e:
                        logger.warning(f"Failed to load block {section}: {e}")
            
            # Load marathons — APPEND to existing
            for section in config.sections():
                if section.startswith("Marathon_"):
                    try:
                        marathon = MarathonConfig(
                            tag=config[section].get("tag", ""),
                            start_time=config[section].get("start_time", "00:00"),
                            end_time=config[section].get("end_time", "00:00"),
                            shuffle=config[section].get("shuffle", "True").lower() == "true",
                            no_repeat_hours=int(config[section].get("no_repeat_hours", "24")),
                            marathon_id=config[section].get("marathon_id")
                        )
                        self.daypart_marathons.append(marathon)
                    except Exception as e:
                        logger.warning(f"Failed to load marathon {section}: {e}")
            
            # Load gap filler
            if "GapFiller" in config:
                gap_section = config["GapFiller"]
                self.daypart_gap_filler = GapFillerConfig(
                    enabled=gap_section.get("enabled", "False").lower() == "true",
                    source=gap_section.get("source", "all"),
                    collection_ids=gap_section.get("collection_ids", "").split(",") if gap_section.get("collection_ids") else [],
                    tags=gap_section.get("tags", "").split(",") if gap_section.get("tags") else [],
                    excluded_tags=gap_section.get("excluded_tags", "").split(",") if gap_section.get("excluded_tags") else [],
                    respect_24h_norepeat=gap_section.get("respect_24h_norepeat", "True").lower() == "true",
                    shuffle=gap_section.get("shuffle", "True").lower() == "true"
                )
            
            # Load global settings (including approximate checkbox)
            if "Settings" in config:
                settings_section = config["Settings"]
                use_approx = settings_section.get("use_approximation", "false").lower() == "true"
                try:
                    self.app.use_approximation_var.set(use_approx)
                except AttributeError:
                    if hasattr(self, 'use_approximation_var'):
                        self.use_approximation_var.set(use_approx)
                print(f"[DEBUG] Loaded approximate setting: {use_approx}")
            
            # Update UI
            self.update_block_list()
            self.update_marathon_list()
            self.update_gap_filler_ui()
            self.update_preview_display()
            
            # Show import summary
            block_count = len(self.daypart_time_blocks)
            marathon_count = len(self.daypart_marathons)
            messagebox.showinfo("Load Successful", 
                f"Loaded from:\n{file_path}\n\nImported:\n• {block_count} time block(s)\n• {marathon_count} marathon(s)\n• Gap filler settings")
            
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load: {str(e)}")
            logger.error(f"Daypart load work failed: {e}", exc_info=True)
    
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
            
            self.daypart_time_blocks = []
            for block_data in config.get("daypart_config", {}).get("time_blocks", []):
                try:
                    block = TimeBlock.from_dict(block_data)
                    self.daypart_time_blocks.append(block)
                except Exception as e:
                    logger.error(f"Failed to load time block: {e}")
            
            self.daypart_marathons = []
            for marathon_data in config.get("daypart_config", {}).get("marathons", []):
                try:
                    marathon = MarathonConfig.from_dict(marathon_data)
                    self.daypart_marathons.append(marathon)
                except Exception as e:
                    logger.error(f"Failed to load marathon: {e}")
            
            gap_data = config.get("daypart_config", {}).get("gap_filler", {})
            self.daypart_gap_filler = GapFillerConfig.from_dict(gap_data)
            
            self.update_block_list()
            self.update_marathon_list()
            self.update_gap_filler_ui()
        else:
            self.daypart_config = None
            self.daypart_enabled = False
            self.daypart_time_blocks = []
            self.daypart_marathons = []
            self.daypart_gap_filler = GapFillerConfig()
            self.update_block_list()
            self.update_marathon_list()
            self.update_gap_filler_ui()
        
        self.refresh_daypart_tags()
    
    def refresh_daypart_tags(self):
        """Populate marathon tag combo with available tags from collections"""
        collections = load_collections(self.current_profile)
        all_tags = set()
        for col in collections:
            all_tags.update(col.get("tags", []))
        
        if hasattr(self, 'marathon_tag_combo'):
            self.marathon_tag_combo['values'] = sorted(list(all_tags))
    
    # ========================================================================
    # UI LIST UPDATE METHODS
    # ========================================================================
    
    def update_block_list(self):
        """Update the time block list display"""
        if not hasattr(self, 'block_list'):
            return
        self.block_list.delete(0, tk.END)
        for block in self.daypart_time_blocks:
            days_str = ""
            if hasattr(block, 'days') and block.days:
                days_str = " (" + ",".join([d[:3] for d in block.days]) + ")"

            if block.content_type == "tag":
                display = f"{block.start_time}-{block.end_time} [TAG:{block.content_value}]{days_str}"
            elif block.content_type == "episodic":
                parts = block.content_value.split("|")
                col_id = parts[0]
                s = parts[1] if len(parts) > 1 else "1"
                e = parts[2] if len(parts) > 2 else "1"
                count = parts[3] if len(parts) > 3 else "1"
                display = f"{block.start_time}-{block.end_time} [EPISODIC:{col_id} S{s}E{e} x{count}]{days_str}"
            else:
                filename = Path(block.content_value).name
                display = f"{block.start_time}-{block.end_time} [VIDEO] {filename}"
            self.block_list.insert(tk.END, display)

        if hasattr(self, 'block_count_label'):
            self.block_count_label.config(text=f"Total blocks: {len(self.daypart_time_blocks)}")
    
    def update_marathon_list(self):
        """Update the marathon list display"""
        if not hasattr(self, 'marathon_list'):
            return
        self.marathon_list.delete(0, tk.END)
        for marathon in self.daypart_marathons:
            days = ", ".join([d[:3].title() for d in marathon.days])
            display = f"Tag: {marathon.tag} | Days: {days} | Shuffle: {marathon.shuffle}"
            self.marathon_list.insert(tk.END, display)
    
    def draw_time_block(self, canvas, block, width, height, color):
        """Draw a single time block on timeline"""
        try:
            start_dt = parse_time_string(block.start_time)
            end_dt = parse_time_string(block.end_time)
            
            start_hour = start_dt.hour + start_dt.minute/60
            end_hour = end_dt.hour + end_dt.minute/60
            
            x1 = (start_hour / 24) * width
            x2 = (end_hour / 24) * width
            
            canvas.create_rectangle(x1, 5, x2, height-15, fill=color, outline="black", stipple="gray25")
        except:
            pass
    
    def update_preview_display(self):
        """Update the text preview list"""
        print(f"[DEBUG] update_preview_display called, entries: {len(self.daypart_preview_entries) if self.daypart_preview_entries else 0}")
        
        if hasattr(self, 'preview_list'):
            self.preview_list.delete(0, tk.END)
            
            if not self.daypart_preview_entries:
                self.preview_list.insert(tk.END, "Click 'Generate Preview' to see schedule")
                if hasattr(self, 'preview_stats_label'):
                    self.preview_stats_label.config(text="")
                return
            
            # Sort entries by date then time for proper display
            sorted_entries = sorted(
                self.daypart_preview_entries,
                key=lambda e: (e.get("date", ""), e.get("time", ""))
            )
            
            # Group entries by date for display
            current_date = None
            for entry in sorted_entries:
                entry_date = entry.get("date", "")
                entry_day = entry.get("day", "")
                
                # Show date header when date changes
                if entry_date and entry_date != current_date:
                    current_date = entry_date
                    day_display = entry_day.title() if entry_day else ""
                    self.preview_list.insert(tk.END, f"--- {entry_date} ({day_display}) ---")
                
                start = entry.get("time", "??:??").split(":")[:2]
                start = ":".join(start)
                # Get title from file path or use default
                file_path = entry.get("file", "")
                if file_path:
                    title = Path(file_path).stem
                else:
                    title = entry.get("title", "Unknown")
                source = entry.get("source", "unknown")
                
                # Calculate end time for debug display
                duration = entry.get("duration", 0)
                if duration > 0:
                    # Parse start time and add duration
                    try:
                        start_parts = start.split(":")
                        start_h = int(start_parts[0])
                        start_m = int(start_parts[1])
                        total_minutes = start_h * 60 + start_m + (duration // 60)
                        end_h = (total_minutes // 60) % 24
                        end_m = total_minutes % 60
                        end_str = f"{end_h:02d}:{end_m:02d}"
                        display = f"  {start}-{end_str} [{source}] {title}"
                    except:
                        display = f"  {start} [{source}] {title}"
                else:
                    display = f"  {start} [{source}] {title}"
                
                self.preview_list.insert(tk.END, display)
            
            if hasattr(self, 'preview_stats_label'):
                # Count unique dates
                dates = set(entry.get("date", "") for entry in self.daypart_preview_entries if entry.get("date"))
                date_count = len(dates) if dates else 1
                total_duration = sum(
                    entry.get("duration", 0) 
                    for entry in self.daypart_preview_entries
                )
                hours = total_duration / 3600 if total_duration else 0
                self.preview_stats_label.config(
                    text=f"{len(self.daypart_preview_entries)} entries | {date_count} day(s) | {hours:.1f} hours"
                )

    # ========================================================================
    # TIMELINE DRAWING
    # ========================================================================

    def on_timeline_resize(self, event):
        """Redraw timeline on canvas resize"""
        self.draw_timeline()

    def draw_timeline(self):
        """Draw the visual timeline on canvas"""
        if not hasattr(self, 'timeline_canvas'):
            return
        canvas = self.timeline_canvas
        canvas.delete("all")

        width = canvas.winfo_width()
        if width <= 1:
            width = 600  # Default

        height = canvas.winfo_height()
        if height <= 1:
            height = 60

        # Draw hour markers
        canvas.create_line(0, height//2, width, height//2, fill="black")
        for hour in range(0, 25):
            x = (hour / 24) * width
            canvas.create_line(x, 0, x, height, fill="gray", dash=(2, 2))
            canvas.create_text(x, height - 10, text=f"{hour:02d}:00", font=("TkDefaultFont", 8))

        # Draw blocks
        if not self.daypart_preview_entries:
            # Draw placeholder showing time blocks
            for block in self.daypart_time_blocks:
                self.draw_time_block(canvas, block, width, height, "blue")
        else:
            # Draw actual schedule entries (simplified - group by block)
            colors = {"daypart_video": "blue", "daypart_tag": "green",
                     "daypart_marathon": "red", "gap_filler": "gray"}

            for entry in self.daypart_preview_entries:
                time_str = entry["time"]
                hour, minute, _ = time_str.split(":")
                start_decimal = int(hour) + int(minute)/60
                duration = entry.get("duration", 0)
                if duration:
                    duration_hours = duration / 3600
                    end_decimal = start_decimal + duration_hours

                    x1 = (start_decimal / 24) * width
                    x2 = (end_decimal / 24) * width

                    source = entry.get("source", "unknown")
                    color = colors.get(source, "gray")

                    canvas.create_rectangle(x1, 5, x2, height-15, fill=color, outline="black")

    def draw_time_block(self, canvas, block, width, height, color):
        """Draw a single time block on timeline"""
        try:
            from akiratv.daypart_scheduler import parse_time_string
            start_dt = parse_time_string(block.start_time)
            end_dt = parse_time_string(block.end_time)

            start_hour = start_dt.hour + start_dt.minute/60
            end_hour = end_dt.hour + end_dt.minute/60

            x1 = (start_hour / 24) * width
            x2 = (end_hour / 24) * width

            canvas.create_rectangle(x1, 5, x2, height-15, fill=color, outline="black", stipple="gray25")
        except:
            pass

    # ========================================================================
    # DAYPART PANEL UI CREATION
    # ========================================================================

    def create_daypart_panel(self, parent):
        """Create the Schedule Programming tab with daypart scheduling UI"""
        # Main container with scrollbar
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Title
        ttk.Label(main_frame, text="Schedule Programming", font=("TkDefaultFont", 12, "bold")).pack(pady=(0, 10))

        # === TIME BLOCK MANAGEMENT PANEL ===
        block_panel = ttk.LabelFrame(main_frame, text="Time Blocks", padding=10)
        block_panel.pack(fill="x", pady=(0, 10))

        # Block list frame
        block_list_frame = ttk.Frame(block_panel)
        block_list_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Block list with scrollbar
        block_list_container = ttk.Frame(block_list_frame)
        block_list_container.pack(side="left", fill="both", expand=True)

        self.block_list = tk.Listbox(block_list_container, height=8, font=("TkDefaultFont", 10))
        self.block_list.pack(side="left", fill="both", expand=True)
        block_scrollbar = ttk.Scrollbar(block_list_container, orient="vertical", command=self.block_list.yview)
        block_scrollbar.pack(side="right", fill="y")
        self.block_list.configure(yscrollcommand=block_scrollbar.set)
        self.block_list.bind("<<ListboxSelect>>", self.on_block_select)

        # Block control buttons
        block_btn_frame = ttk.Frame(block_panel)
        block_btn_frame.pack(fill="x")

        ttk.Button(block_btn_frame, text="Add Block", command=self.on_add_block).pack(side="left", padx=2)
        ttk.Button(block_btn_frame, text="Edit Selected", command=self.on_edit_block).pack(side="left", padx=2)
        ttk.Button(block_btn_frame, text="Delete Selected", command=self.on_delete_block).pack(side="left", padx=2)
        ttk.Button(block_btn_frame, text="Move Up", command=self.on_move_block_up).pack(side="left", padx=2)
        ttk.Button(block_btn_frame, text="Move Down", command=self.on_move_block_down).pack(side="left", padx=2)
        ttk.Button(block_btn_frame, text="Add Gap Fill", command=self.on_add_gap_fill_block).pack(side="left", padx=(10, 2))

        # Block count label
        self.block_count_label = ttk.Label(block_panel, text="Total blocks: 0")
        self.block_count_label.pack(pady=(5, 0))

        # === MARATHON SCHEDULING PANEL ===
        marathon_panel = ttk.LabelFrame(main_frame, text="Marathon Scheduling", padding=10)
        marathon_panel.pack(fill="x", pady=(0, 10))

        # Tag selection
        tag_frame = ttk.Frame(marathon_panel)
        tag_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(tag_frame, text="Tag:").pack(side="left", padx=(0, 5))
        self.marathon_tag_var = tk.StringVar()
        self.marathon_tag_combo = ttk.Combobox(tag_frame, textvariable=self.marathon_tag_var, state="normal")
        self.marathon_tag_combo.pack(side="left", fill="x", expand=True)

        # Day selection
        day_frame = ttk.Frame(marathon_panel)
        day_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(day_frame, text="Days:").pack(side="left", padx=(0, 5))
        self.marathon_day_vars = {}
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for day in days:
            var = tk.BooleanVar(value=False)
            chk = ttk.Checkbutton(day_frame, text=day[:3].title(), variable=var)
            chk.pack(side="left", padx=2)
            self.marathon_day_vars[day] = var
        self.marathon_all_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(day_frame, text="All", variable=self.marathon_all_var,
                       command=self.on_marathon_all_toggle).pack(side="left", padx=5)

        # Marathon options
        marathon_opt_frame = ttk.Frame(marathon_panel)
        marathon_opt_frame.pack(fill="x", pady=(0, 5))
        self.marathon_shuffle_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(marathon_opt_frame, text="Shuffle within marathon",
                       variable=self.marathon_shuffle_var).pack(side="left", padx=5)
        self.marathon_norepeat_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(marathon_opt_frame, text="No repeats within 24h",
                       variable=self.marathon_norepeat_var).pack(side="left", padx=5)

        # Marathon buttons
        marathon_btn_frame = ttk.Frame(marathon_panel)
        marathon_btn_frame.pack(fill="x")
        ttk.Button(marathon_btn_frame, text="Add Marathon", command=self.on_add_marathon).pack(side="left", padx=2)
        ttk.Button(marathon_btn_frame, text="Remove Selected", command=self.on_remove_marathon).pack(side="left", padx=2)

        # Marathon list
        self.marathon_list = tk.Listbox(marathon_panel, height=4, font=("TkDefaultFont", 10))
        self.marathon_list.pack(fill="x", pady=(5, 0))

        # === GAP FILLER PANEL ===
        gap_panel = ttk.LabelFrame(main_frame, text="Gap Filler Settings", padding=10)
        gap_panel.pack(fill="x", pady=(0, 10))

        # Enable checkbox
        self.gap_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(gap_panel, text="Enable gap filling with random content",
                       variable=self.gap_enabled_var).pack(anchor="w", pady=(0, 5))

        # Source selection
        source_frame = ttk.Frame(gap_panel)
        source_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(source_frame, text="Source:").pack(side="left", padx=(0, 5))
        self.gap_source_var = tk.StringVar(value="all")
        ttk.Radiobutton(source_frame, text="All videos", variable=self.gap_source_var,
                       value="all", command=self.on_gap_source_change).pack(side="left", padx=5)
        ttk.Radiobutton(source_frame, text="Selected collections", variable=self.gap_source_var,
                       value="collections", command=self.on_gap_source_change).pack(side="left", padx=5)
        ttk.Radiobutton(source_frame, text="Selected tags", variable=self.gap_source_var,
                       value="tags", command=self.on_gap_source_change).pack(side="left", padx=5)

        # Excluded tags
        exclude_frame = ttk.Frame(gap_panel)
        exclude_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(exclude_frame, text="Exclude tags:").pack(side="left", padx=(0, 5))
        self.gap_exclude_label = ttk.Label(exclude_frame, text="[None]", foreground="blue", cursor="hand2")
        self.gap_exclude_label.pack(side="left")
        self.gap_exclude_label.bind("<Button-1>", self.on_edit_excluded_tags)

        # Gap options
        gap_opt_frame = ttk.Frame(gap_panel)
        gap_opt_frame.pack(fill="x")
        self.gap_24h_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(gap_opt_frame, text="Respect 24-hour no-repeat rule",
                       variable=self.gap_24h_var).pack(side="left", padx=5)
        self.gap_shuffle_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(gap_opt_frame, text="Shuffle selection",
                       variable=self.gap_shuffle_var).pack(side="left", padx=5)

        # === PREVIEW PANEL ===
        preview_panel = ttk.LabelFrame(main_frame, text="Preview Schedule", padding=10)
        preview_panel.pack(fill="both", expand=True, pady=(0, 10))

        # Visual timeline canvas
        self.timeline_canvas = tk.Canvas(preview_panel, height=60, bg="white", highlightthickness=1, highlightbackground="gray")
        self.timeline_canvas.pack(fill="x", pady=(0, 10))
        self.timeline_canvas.bind("<Configure>", self.on_timeline_resize)

        # Timeline legend
        legend_frame = ttk.Frame(preview_panel)
        legend_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(legend_frame, text="Legend:").pack(side="left", padx=(0, 5))
        ttk.Label(legend_frame, text="■ Specific Video", foreground="blue").pack(side="left", padx=5)
        ttk.Label(legend_frame, text="■ Tag-based", foreground="green").pack(side="left", padx=5)
        ttk.Label(legend_frame, text="■ Marathon", foreground="red").pack(side="left", padx=5)
        ttk.Label(legend_frame, text="■ Gap Filler", foreground="gray").pack(side="left", padx=5)

        # Text preview listbox
        preview_list_frame = ttk.Frame(preview_panel)
        preview_list_frame.pack(fill="both", expand=True)
        self.preview_list = tk.Listbox(preview_list_frame, height=8, font=("TkDefaultFont", 9))
        self.preview_list.pack(side="left", fill="both", expand=True)
        preview_scrollbar = ttk.Scrollbar(preview_list_frame, orient="vertical", command=self.preview_list.yview)
        preview_scrollbar.pack(side="right", fill="y")
        self.preview_list.configure(yscrollcommand=preview_scrollbar.set)

        # Preview statistics
        self.preview_stats_label = ttk.Label(preview_panel, text="")
        self.preview_stats_label.pack(pady=(5, 0))
        
        # === PREVIEW MODE SELECTION ===
        preview_mode_frame = ttk.Frame(main_frame)
        preview_mode_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(preview_mode_frame, text="Preview Mode:").pack(side="left", padx=(0, 5))
        self.preview_mode_var = tk.StringVar(value="single")
        ttk.Radiobutton(preview_mode_frame, text="Single Day", variable=self.preview_mode_var,
                       value="single").pack(side="left", padx=5)
        ttk.Radiobutton(preview_mode_frame, text="Weekly (7 days)", variable=self.preview_mode_var,
                       value="weekly").pack(side="left", padx=5)
        ttk.Radiobutton(preview_mode_frame, text="Calendar Range", variable=self.preview_mode_var,
                       value="calendar").pack(side="left", padx=5)
        
        # Calendar date range (for calendar mode)
        calendar_range_frame = ttk.Frame(main_frame)
        calendar_range_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(calendar_range_frame, text="From:").pack(side="left", padx=(0, 5))
        self.preview_start_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(calendar_range_frame, textvariable=self.preview_start_date_var, width=12).pack(side="left", padx=2)
        ttk.Label(calendar_range_frame, text="To:").pack(side="left", padx=(10, 5))
        self.preview_end_date_var = tk.StringVar(value=(datetime.now() + timedelta(days=6)).strftime("%Y-%m-%d"))
        ttk.Entry(calendar_range_frame, textvariable=self.preview_end_date_var, width=12).pack(side="left", padx=2)
        
        # Action buttons
        action_btn_frame = ttk.Frame(main_frame)
        action_btn_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(action_btn_frame, text="Generate Preview",
                  command=self.on_generate_daypart_preview).pack(side="left", padx=5)
        ttk.Button(action_btn_frame, text="Save Schedule",
                  command=self.on_save_daypart_schedule).pack(side="left", padx=5)
        ttk.Button(action_btn_frame, text="Copy Preview",
                  command=self.on_copy_daypart_preview).pack(side="left", padx=5)
        
        # Export/Import buttons
        ttk.Button(action_btn_frame, text="Export Config",
                  command=self.on_export_daypart_config).pack(side="left", padx=5)
        ttk.Button(action_btn_frame, text="Import Config",
                  command=self.on_import_daypart_config).pack(side="left", padx=5)
        
        # Save Work / Load Work buttons
        ttk.Button(action_btn_frame, text="Save Work",
                  command=self.on_save_daypart_work).pack(side="left", padx=5)
        ttk.Button(action_btn_frame, text="Load Work",
                  command=self.on_load_daypart_work).pack(side="left", padx=5)
        
        # Initialize daypart config for current channel
        self.load_daypart_config_for_channel()
