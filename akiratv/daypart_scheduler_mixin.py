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
from .daypart_scheduler import (
    TimeBlock, MarathonConfig, GapFillerConfig,
    DaypartScheduler, parse_time_string, validate_daypart_config,
    generate_daypart_schedule
)
from .collections import load_collections

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
        def __init__(self, parent, block=None, available_tags=None, available_videos=None):
            super().__init__(parent)
            self.parent = parent
            self.block = block
            self.available_tags = available_tags or []
            self.available_videos = available_videos or []
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
            
            # Tag selection (shown for tag mode)
            self.tag_frame = ttk.Frame(main_frame)
            self.tag_frame.pack(fill="x", pady=(0, 10))
            ttk.Label(self.tag_frame, text="Select Tag:").pack(side="left", padx=(0, 5))
            self.tag_var = tk.StringVar()
            self.tag_combo = ttk.Combobox(self.tag_frame, textvariable=self.tag_var, state="normal")
            self.tag_combo.pack(side="left", fill="x", expand=True)
            self.tag_var.trace_add("write", self.on_tag_select)
            ttk.Button(self.tag_frame, text="New", command=self.on_new_tag).pack(side="left", padx=5)
            self.tag_combo['values'] = self.available_tags
            
            # Tag video list
            self.tag_video_list_frame = ttk.Frame(main_frame)
            ttk.Label(self.tag_video_list_frame, text="Videos with this tag:").pack(anchor="w")
            tag_list_frame = ttk.Frame(self.tag_video_list_frame)
            tag_list_frame.pack(fill="both", expand=True, pady=(5, 0))
            self.tag_video_list = tk.Listbox(tag_list_frame, height=8)
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
            
            # Initially hide video frame (only show in video mode)
            if hasattr(self, 'video_frame'):
                if self.type_var.get() == "tag":
                    self.video_frame.pack_forget()
            
            self.selected_video_label = ttk.Label(self.video_frame, text="Selected: None", foreground="blue")
            self.selected_video_label.pack(pady=(5, 0))
            
            # Buttons
            btn_frame = ttk.Frame(main_frame)
            btn_frame.pack(fill="x", pady=(10, 0))
            ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side="right", padx=5)
            ttk.Button(btn_frame, text="Save", command=self.on_save).pack(side="right", padx=5)
        
        def on_type_change(self):
            """Toggle between tag and video mode"""
            is_tag = self.type_var.get() == "tag"
            
            # Show/hide tag-related frames
            if is_tag:
                self.tag_frame.pack(fill="x", pady=(0, 10))
                self.tag_video_list_frame.pack(fill="both", expand=True, pady=(0, 10))
                # Hide video-specific frame (for selecting single video)
                if hasattr(self, 'video_frame'):
                    self.video_frame.pack_forget()
            else:
                # Hide tag-related frames
                self.tag_frame.pack_forget()
                self.tag_video_list_frame.pack_forget()
                # Show video-specific frame
                if hasattr(self, 'video_frame'):
                    self.video_frame.pack(fill="both", expand=True, pady=(0, 10))
                    self.populate_video_list()
        
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
            """Calculate end time based on selected tag and video count"""
            video_count = self.video_count_var.get()
            selected_tag = self.tag_var.get()
            
            if not selected_tag or not video_count:
                return
            
            # Get videos with this tag (check collection tags)
            tag_videos = []
            for video in self.available_videos:
                collection_tags = video.get("collection", {}).get("tags", [])
                if selected_tag in collection_tags:
                    tag_videos.append(video)
            
            if not tag_videos:
                return
            
            # Calculate total duration based on video count
            total_duration_seconds = 0
            
            if video_count == "all":
                # Sum all videos with this tag
                for video in tag_videos:
                    duration = video.get("duration", 0)
                    if duration:
                        total_duration_seconds += duration
            elif video_count == "single":
                # Just one video - use average duration or first video
                if tag_videos:
                    durations = [v.get("duration", 0) for v in tag_videos if v.get("duration")]
                    if durations:
                        total_duration_seconds = sum(durations) / len(durations)
                    else:
                        total_duration_seconds = 3600  # Default 1 hour
            else:
                # Specific number (2, 3, 4, 5)
                try:
                    count = int(video_count)
                    # Use average duration from available videos
                    durations = [v.get("duration", 0) for v in tag_videos if v.get("duration")]
                    if durations:
                        avg_duration = sum(durations) / len(durations)
                        total_duration_seconds = avg_duration * count
                    elif tag_videos:
                        # Fallback to first video duration
                        total_duration_seconds = (tag_videos[0].get("duration", 0) or 3600) * count
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
            for video in self.available_videos:
                # Get tags from collection (tags are stored in collection, not video)
                collection_tags = video.get("collection", {}).get("tags", [])
                if selected_tag in collection_tags:
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
            
            if self.block.content_type == "tag":
                self.tag_var.set(self.block.content_value)
                if self.block.video_count:
                    self.video_count_var.set(self.block.video_count)
                for day in self.block.days:
                    if day in self.day_vars:
                        self.day_vars[day].set(True)
                # Check if all days are selected and update the "All" checkbox
                all_days = [day for day, var in self.day_vars.items()]
                selected_days = [day for day, var in self.day_vars.items() if var.get()]
                if len(selected_days) == len(all_days):
                    self.all_days_var.set(True)
            else:
                self.type_var.set("video")
                # Find and select the video
                for i, video in enumerate(self.available_videos):
                    if video.get("path") == self.block.content_value:
                        self.video_list.selection_set(i)
                        break
            
            self.on_type_change()
        
        def on_cancel(self):
            """Cancel dialog"""
            self.result = None
            self.destroy()
        
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
                # Get selected days
                days = [day for day, var in self.day_vars.items() if var.get()]
                # If "All" is checked, set days to all days
                if self.all_days_var.get():
                    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                video_count = self.video_count_var.get()
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
                video_count=video_count
            )
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
            available_videos=available_videos
        )
        self.root.wait_window(dialog)
        if dialog.result:
            self.daypart_time_blocks.append(dialog.result)
            self.update_block_list()
            self.update_preview_display()
    
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
        from .ui.daypart_ui import TagExclusionDialog
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
        try:
            collections = load_collections(self.current_profile)
            available_videos = []
            for col in collections:
                for video in col.get("videos", []):
                    if video["path"] not in self.blacklisted_videos:
                        video["collection"] = col
                        available_videos.append(video)
            
            daypart_config = {
                "daypart_config": {
                    "time_blocks": [b.to_dict() for b in self.daypart_time_blocks],
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
                    target_date
                )
                day_name = target_date.strftime("%A").lower()
                for entry in entries:
                    entry["day"] = day_name
                all_entries.extend(entries)
                
            elif preview_mode == "weekly":
                # Generate for 7 days starting from today
                # Track the current time for continuous scheduling across days
                current_time = None  # Will be set to midnight of first day
                for day_offset in range(7):
                    target_date = date.today() + timedelta(days=day_offset)
                    if current_time is None:
                        current_time = datetime.combine(target_date, datetime.min.time())
                    entries, last_time = generate_daypart_schedule(
                        daypart_config,
                        available_videos,
                        self.current_channel or "default",
                        target_date,
                        base_datetime=current_time
                    )
                    day_name = target_date.strftime("%A").lower()
                    for entry in entries:
                        entry["day"] = day_name
                        entry["date"] = target_date.strftime("%Y-%m-%d")
                    all_entries.extend(entries)
                    # Continue from last time for next day (don't reset to midnight)
                    if last_time:
                        current_time = last_time
                
            elif preview_mode == "calendar":
                # Generate for date range
                try:
                    start_parts = self.preview_start_date_var.get().split("-")
                    end_parts = self.preview_end_date_var.get().split("-")
                    start_date = date(int(start_parts[0]), int(start_parts[1]), int(start_parts[2]))
                    end_date = date(int(end_parts[0]), int(end_parts[1]), int(end_parts[2]))
                    
                    # Track the current time for continuous scheduling
                    current_time = None  # Will be set to midnight of first day
                    current_date = start_date
                    while current_date <= end_date:
                        if current_time is None:
                            current_time = datetime.combine(current_date, datetime.min.time())
                        entries, last_time = generate_daypart_schedule(
                            daypart_config,
                            available_videos,
                            self.current_channel or "default",
                            current_date,
                            base_datetime=current_time
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
    
    def on_copy_daypart_preview(self):
        """Copy daypart preview to clipboard"""
        if not self.daypart_preview_entries:
            messagebox.showwarning("No Preview", "Generate a preview first")
            return
        
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
            text_lines.append(f"  {time_short} [{source}] {title}")
        
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
                config[section] = {
                    "start_time": block.start_time,
                    "end_time": block.end_time,
                    "content_type": block.content_type,
                    "content_value": block.content_value,
                    "block_id": block.block_id,
                    "days": ",".join(block.days) if block.days else "",
                    "all_days": "true" if is_all_days else "false",
                    "video_count": block.video_count or ""
                }
            
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
            
            # Load time blocks
            self.daypart_time_blocks = []
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
                        
                        block = TimeBlock(
                            start_time=config[section].get("start_time", "00:00"),
                            end_time=config[section].get("end_time", "00:00"),
                            content_type=config[section].get("content_type", "tag"),
                            content_value=config[section].get("content_value", ""),
                            block_id=config[section].get("block_id"),
                            days=days,
                            video_count=config[section].get("video_count") or None
                        )
                        self.daypart_time_blocks.append(block)
                    except Exception as e:
                        logger.warning(f"Failed to load block {section}: {e}")
            
            # Load marathons
            self.daypart_marathons = []
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
            if block.content_type == "tag":
                display = f"{block.start_time}-{block.end_time} [TAG:{block.content_value}]"
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
                self.preview_list.insert(tk.END, f"  {start} [{source}] {title}")
            
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
            from .daypart_scheduler import parse_time_string
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
