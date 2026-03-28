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
from datetime import datetime, date
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
            self.create_widgets()
            if block:
                self.populate_fields()
        
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
            self.tag_frame.pack(fill="x", pady=(0, 10)) if is_tag else self.tag_frame.pack_forget()
            self.tag_video_list_frame.pack(fill="both", expand=True, pady=(0, 10)) if is_tag else self.tag_video_list_frame.pack_forget()
            count_frame = self.nametowidget(self.tag_video_list_frame.winfo_parent()).winfo_children()
            # Show/hide video frame
            if hasattr(self, 'video_frame'):
                if is_tag:
                    self.video_frame.pack(fill="both", expand=True, pady=(0, 10))
                else:
                    self.video_frame.pack_forget()
        
        def on_tag_select(self, *args):
            """Update video list when tag changes"""
            self.populate_tag_videos()
        
        def on_new_tag(self):
            """Create a new tag"""
            from tkinter import simpledialog
            new_tag = simpledialog.askstring("New Tag", "Enter tag name:", parent=self)
            if new_tag and new_tag not in self.available_tags:
                self.available_tags.append(new_tag)
                self.tag_combo['values'] = self.available_tags
                self.tag_var.set(new_tag)
        
        def on_video_count_change(self, event=None):
            """Handle video count change"""
            pass  # Can be extended for more functionality
        
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
                tags = video.get("tags", [])
                if selected_tag in tags:
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
                days = [day for day, var in self.day_vars.items() if var.get()]
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
        """Generate daypart schedule preview for today (24 hours)"""
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
            
            target_date = date.today()
            day_name = target_date.strftime("%A").lower()
            
            entries = generate_daypart_schedule(
                daypart_config,
                available_videos,
                self.current_channel or "default",
                target_date
            )
            
            for entry in entries:
                entry["day"] = day_name
            
            self.daypart_preview_entries = entries
            self.update_preview_display()
            
            messagebox.showinfo("Preview Generated",
                              f"Generated {len(entries)} schedule entries for {day_name.title()} (24 hours)")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate preview: {str(e)}")
            logger.error(f"Daypart preview generation failed: {e}", exc_info=True)
    
    def on_save_daypart_schedule(self):
        """Save daypart schedule configuration"""
        if not self.current_channel:
            messagebox.showerror("Error", "No channel selected")
            return
        
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
    
    def load_daypart_config_for_channel(self):
        """Load daypart configuration for current channel"""
        if not self.current_channel:
            return
        
        config = self.daypart_scheduler.load_config(self.current_channel)
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
            
            for entry in self.daypart_preview_entries:
                start = entry.get("start_time", "??:??")
                end = entry.get("end_time", "??:??")
                title = entry.get("title", "Unknown")
                entry_type = entry.get("type", "unknown")
                self.preview_list.insert(tk.END, f"{start} - {end} [{entry_type}] {title}")
            
            if hasattr(self, 'preview_stats_label'):
                total_duration = sum(
                    entry.get("duration_seconds", 0) 
                    for entry in self.daypart_preview_entries
                )
                hours = total_duration / 3600
                self.preview_stats_label.config(
                    text=f"{len(self.daypart_preview_entries)} entries | {hours:.1f} hours scheduled"
                )
