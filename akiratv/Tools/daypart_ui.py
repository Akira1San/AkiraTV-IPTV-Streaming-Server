# akiratv/ui/daypart_ui.py
"""
Daypart Scheduler UI for AkiraTV

Contains all UI components for daypart scheduling (time blocks, marathons, gap filler).
Extracted from simple_scheduler.py to improve modularity.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import json
from datetime import datetime, timedelta
from pathlib import Path


# ============================================================================
# DIALOG CLASSES
# ============================================================================

class EditBlockDialog(tk.Toplevel):
    """Dialog for creating/editing a time block"""
    def __init__(self, parent, block=None, available_tags=None, available_videos=None,
                 validate_time_format=None, validate_time_block=None):
        super().__init__(parent)
        self.parent = parent
        self.block = block
        self.available_tags = available_tags or []
        self.available_videos = available_videos or []
        self.validate_time_format = validate_time_format
        self.validate_time_block = validate_time_block
        self.result = None
        self.transient(parent)
        self.grab_set()
        self.title("Edit Time Block")
        self.geometry("650x500")
        self.resizable(False, False)
        # Center the dialog on parent
        self.center_on_parent()
        
        # Initialize day variables
        self.day_vars = {}
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
        dialog_w = 600
        dialog_h = 400
        # Calculate center position
        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2
        self.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")
    
    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Start and End times
        time_frame = ttk.Frame(main_frame)
        time_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(time_frame, text="Start Time:").pack(side="left", padx=(0, 5))
        self.start_var = tk.StringVar(value="00:00")
        self.start_entry = ttk.Entry(time_frame, textvariable=self.start_var, width=8)
        self.start_entry.pack(side="left", padx=5)
        ttk.Label(time_frame, text="End Time:").pack(side="left", padx=(10, 5))
        self.end_var = tk.StringVar(value="00:00")
        self.end_entry = ttk.Entry(time_frame, textvariable=self.end_var, width=8)
        self.end_entry.pack(side="left", padx=5)
        ttk.Label(time_frame, text="(HH:MM format, 24-hour)").pack(side="left", padx=10)
        
        # Duration display
        self.duration_label = ttk.Label(time_frame, text="Duration: 0 hours")
        self.duration_label.pack(side="left", padx=20)
        self.start_var.trace_add("write", self.update_duration)
        self.end_var.trace_add("write", self.update_duration)
        
        # Content type
        type_frame = ttk.Frame(main_frame)
        type_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(type_frame, text="Content Type:").pack(side="left", padx=(0, 5))
        self.type_var = tk.StringVar(value="tag")
        ttk.Radiobutton(type_frame, text="Specific Video", variable=self.type_var,
                       value="video", command=self.on_type_change).pack(side="left", padx=5)
        ttk.Radiobutton(type_frame, text="Tag (random)", variable=self.type_var,
                       value="tag", command=self.on_type_change).pack(side="left", padx=5)
        
        # Day of week selection
        days_frame = ttk.LabelFrame(main_frame, text="Days (applies to tag blocks)", padding=10)
        days_frame.pack(fill="x", pady=(0, 10))
        
        days_container = ttk.Frame(days_frame)
        days_container.pack(fill="x")
        
        self.days_var = tk.StringVar(value="")  # Comma-separated days
        
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_frame = ttk.Frame(days_container)
        day_frame.pack(fill="x")
        
        for i, day in enumerate(days):
            var = tk.BooleanVar(value=False)
            self.day_vars[day] = var
            ttk.Checkbutton(day_frame, text=day[:3].title(), variable=var,
                          command=self.on_day_change).grid(row=0, column=i, padx=5, sticky="w")
        
        # All/None quick buttons
        quick_frame = ttk.Frame(days_container)
        quick_frame.pack(fill="x", pady=(5, 0))
        ttk.Button(quick_frame, text="All", command=self.select_all_days, width=8).pack(side="left", padx=2)
        ttk.Button(quick_frame, text="None", command=self.clear_all_days, width=8).pack(side="left", padx=2)
        ttk.Label(quick_frame, text="(Leave empty to apply to all days)", font=("", 9, "italic")).pack(side="left", padx=10)
        
        # Video selection
        video_frame = ttk.Frame(main_frame)
        video_frame.pack(fill="both", expand=True, pady=(0, 10))
        ttk.Label(video_frame, text="Search Videos:").pack(anchor="w")
        search_frame = ttk.Frame(video_frame)
        search_frame.pack(fill="x", pady=(5, 0))
        self.video_search_var = tk.StringVar()
        self.video_search_var.trace_add("write", self.filter_videos)
        search_entry = ttk.Entry(search_frame, textvariable=self.video_search_var)
        search_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(search_frame, text="Clear", command=self.clear_video_search).pack(side="left", padx=5)
        
        # Video list
        list_frame = ttk.Frame(video_frame)
        list_frame.pack(fill="both", expand=True, pady=(5, 0))
        self.video_list = tk.Listbox(list_frame, height=8, selectmode=tk.BROWSE)
        self.video_list.pack(side="left", fill="both", expand=True)
        video_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.video_list.yview)
        video_scroll.pack(side="right", fill="y")
        self.video_list.configure(yscrollcommand=video_scroll.set)
        self.video_list.bind("<<ListboxSelect>>", self.on_video_select)
        
        # Populate video list
        self.populate_video_list()
        
        # Selected video display
        self.selected_video_label = ttk.Label(video_frame, text="Selected: None", foreground="blue")
        self.selected_video_label.pack(pady=(5, 0))
        
        # Tag selection (initially hidden)
        self.tag_frame = ttk.Frame(main_frame)
        ttk.Label(self.tag_frame, text="Select Tag:").pack(side="left", padx=(0, 5))
        self.tag_var = tk.StringVar()
        self.tag_combo = ttk.Combobox(self.tag_frame, textvariable=self.tag_var, state="normal")
        self.tag_combo.pack(side="left", fill="x", expand=True)
        ttk.Button(self.tag_frame, text="New", command=self.on_new_tag).pack(side="left", padx=5)
        if self.available_tags:
            self.tag_combo['values'] = self.available_tags
            if self.available_tags:
                self.tag_var.set(self.available_tags[0])
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Save", command=self.on_save).pack(side="right", padx=5)
        
        # Initially show tag selection
        self.on_type_change()
    
    def update_duration(self, *args):
        try:
            start = datetime.strptime(self.start_var.get(), "%H:%M")
            end = datetime.strptime(self.end_var.get(), "%H:%M")
            if end < start:
                end += timedelta(days=1)
            duration = end - start
            hours = duration.total_seconds() / 3600
            self.duration_label.config(text=f"Duration: {hours:.1f} hours")
        except:
            self.duration_label.config(text="Duration: Invalid time")
    
    def on_type_change(self):
        if self.type_var.get() == "video":
            self.video_list.master.pack(fill="both", expand=True)
            self.tag_frame.pack_forget()
            # Hide days frame for video blocks
            for child in self.winfo_children():
                if isinstance(child, ttk.LabelFrame) and "Days" in child.cget("text"):
                    child.pack_forget()
        else:
            self.video_list.master.pack_forget()
            self.tag_frame.pack(fill="x", pady=(0, 10))
            # Show days frame for tag blocks
            for child in self.winfo_children():
                if isinstance(child, ttk.Frame):
                    for subchild in child.winfo_children():
                        if isinstance(subchild, ttk.LabelFrame) and "Days" in subchild.cget("text"):
                            subchild.pack(fill="x", pady=(0, 10))
    
    def on_day_change(self):
        """Update the days string when any day checkbox changes"""
        selected_days = [day for day, var in self.day_vars.items() if var.get()]
        self.days_var.set(",".join(selected_days))
    
    def select_all_days(self):
        """Select all days"""
        for var in self.day_vars.values():
            var.set(True)
        self.on_day_change()
    
    def clear_all_days(self):
        """Clear all days"""
        for var in self.day_vars.values():
            var.set(False)
        self.on_day_change()
    
    def populate_video_list(self, filter_text=""):
        self.video_list.delete(0, tk.END)
        for video in self.available_videos:
            title = video.get("title", video.get("path", "Unknown"))
            if filter_text and filter_text.lower() not in title.lower():
                continue
            self.video_list.insert(tk.END, title)
            # Store video path as hidden data
            self.video_list.set(tk.END, video.get("path", ""))
    
    def filter_videos(self, *args):
        self.populate_video_list(self.video_search_var.get())
    
    def clear_video_search(self):
        self.video_search_var.set("")
        self.populate_video_list()
    
    def on_video_select(self, event):
        selection = self.video_list.curselection()
        if selection:
            index = selection[0]
            video_path = self.video_list.get(index)
            self.selected_video_label.config(text=f"Selected: {video_path}")
            self.selected_video = video_path
    
    def on_new_tag(self):
        new_tag = simpledialog.askstring("New Tag", "Enter new tag name:")
        if new_tag:
            self.tag_var.set(new_tag)
            # Add to available tags if not present
            if new_tag not in self.available_tags:
                self.available_tags.append(new_tag)
                self.tag_combo['values'] = self.available_tags
    
    def populate_fields(self):
        if self.block:
            self.start_var.set(self.block.start_time)
            self.end_var.set(self.block.end_time)
            self.type_var.set(self.block.content_type)
            if self.block.content_type == "video":
                self.selected_video = self.block.content_value
                self.selected_video_label.config(text=f"Selected: {self.block.content_value}")
            else:
                self.tag_var.set(self.block.content_value)
            
            # Load days from block
            block_days = getattr(self.block, 'days', []) or []
            for day in block_days:
                if day.lower() in self.day_vars:
                    self.day_vars[day.lower()].set(True)
            self.on_day_change()
            
            self.on_type_change()
    
    def on_cancel(self):
        self.destroy()
    
    def on_save(self):
        # Validate times
        start = self.start_var.get()
        end = self.end_var.get()
        if self.validate_time_format:
            if not self.validate_time_format(start):
                messagebox.showerror("Error", "Invalid start time format")
                return
            if not self.validate_time_format(end):
                messagebox.showerror("Error", "Invalid end time format")
                return
        
        # Validate content
        content_type = self.type_var.get()
        if content_type == "video":
            if not hasattr(self, 'selected_video') or not self.selected_video:
                messagebox.showerror("Error", "Please select a video")
                return
            content_value = self.selected_video
            # Videos don't use days - apply to all days
            selected_days = []
        else:
            tag = self.tag_var.get().strip()
            if not tag:
                messagebox.showerror("Error", "Please enter a tag")
                return
            content_value = tag
            # Get selected days for tag blocks
            selected_days = [day for day, var in self.day_vars.items() if var.get()]
        
        # Create block - import TimeBlock here to avoid circular imports
        from ..daypart_scheduler import TimeBlock
        block = TimeBlock(start, end, content_type, content_value, days=selected_days)
        
        if self.validate_time_block:
            error = self.validate_time_block(block)
            if error:
                messagebox.showerror("Validation Error", error)
                return
        
        self.result = block
        self.destroy()


class TagExclusionDialog(tk.Toplevel):
    """Dialog for selecting tags to exclude from gap filler"""
    def __init__(self, parent, available_tags=None, excluded_tags=None):
        super().__init__(parent)
        self.parent = parent
        self.available_tags = available_tags or []
        self.excluded_tags = excluded_tags or []
        self.result = None
        self.transient(parent)
        self.grab_set()
        self.title("Exclude Tags from Gap Filler")
        self.geometry("400x300")
        # Center the dialog on parent
        self.center_on_parent()
        self.create_widgets()
    
    def center_on_parent(self):
        """Center the dialog window on the parent window"""
        self.update_idletasks()
        # Get parent position and size
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()
        # Get dialog size
        dialog_w = 400
        dialog_h = 300
        # Calculate center position
        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2
        self.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")
    
    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(main_frame, text="Select tags to EXCLUDE from gap filler:").pack(anchor="w", pady=(0, 10))
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill="both", expand=True, pady=(0, 10))
        self.listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=12)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        # Populate
        for tag in sorted(self.available_tags):
            self.listbox.insert(tk.END, tag)
            if tag in self.excluded_tags:
                self.listbox.selection_set(tk.END)
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Save", command=self.on_save).pack(side="right", padx=5)
    
    def on_cancel(self):
        self.destroy()
    
    def on_save(self):
        selected = [self.listbox.get(i) for i in self.listbox.curselection()]
        self.result = selected
        self.destroy()


# ============================================================================
# UI BUILDER CLASS
# ============================================================================

class DaypartSchedulerUI:
    """
    Helper class to build daypart scheduler UI components.
    Provides methods to create the Schedule Programming tab and its widgets.
    """
    
    def __init__(self, scheduler_app):
        """
        Initialize with reference to the main scheduler app.
        
        Args:
            scheduler_app: The SimpleSchedulerWizard instance
        """
        self.app = scheduler_app
    
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
        
        self.app.block_list = tk.Listbox(block_list_container, height=8, font=("TkDefaultFont", 10))
        self.app.block_list.pack(side="left", fill="both", expand=True)
        block_scrollbar = ttk.Scrollbar(block_list_container, orient="vertical", command=self.app.block_list.yview)
        block_scrollbar.pack(side="right", fill="y")
        self.app.block_list.configure(yscrollcommand=block_scrollbar.set)
        self.app.block_list.bind("<<ListboxSelect>>", self.app.on_block_select)
        
        # Block control buttons
        block_btn_frame = ttk.Frame(block_panel)
        block_btn_frame.pack(fill="x")
        
        ttk.Button(block_btn_frame, text="Add Block", command=self.app.on_add_block).pack(side="left", padx=2)
        ttk.Button(block_btn_frame, text="Edit Selected", command=self.app.on_edit_block).pack(side="left", padx=2)
        ttk.Button(block_btn_frame, text="Delete Selected", command=self.app.on_delete_block).pack(side="left", padx=2)
        ttk.Button(block_btn_frame, text="Move Up", command=self.app.on_move_block_up).pack(side="left", padx=2)
        ttk.Button(block_btn_frame, text="Move Down", command=self.app.on_move_block_down).pack(side="left", padx=2)
        ttk.Button(block_btn_frame, text="Copy to Channel", command=self.on_copy_blocks_to_channel).pack(side="left", padx=10)
        
        # Block count label
        self.app.block_count_label = ttk.Label(block_panel, text="Total blocks: 0")
        self.app.block_count_label.pack(pady=(5, 0))
        
        # === MARATHON + GAP FILLER as tabs ===
        mid_nb = ttk.Notebook(main_frame)
        mid_nb.pack(fill="x", pady=(0, 10))

        # --- Tab 1: Marathon Scheduling ---
        marathon_tab = ttk.Frame(mid_nb, padding=8)
        mid_nb.add(marathon_tab, text="Marathon Scheduling")

        tag_frame = ttk.Frame(marathon_tab)
        tag_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(tag_frame, text="Tag:").pack(side="left", padx=(0, 5))
        self.app.marathon_tag_var = tk.StringVar()
        self.app.marathon_tag_combo = ttk.Combobox(tag_frame, textvariable=self.app.marathon_tag_var, state="normal")
        self.app.marathon_tag_combo.pack(side="left", fill="x", expand=True)

        day_frame = ttk.Frame(marathon_tab)
        day_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(day_frame, text="Days:").pack(side="left", padx=(0, 5))
        self.app.marathon_day_vars = {}
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            var = tk.BooleanVar(value=False)
            ttk.Checkbutton(day_frame, text=day[:3].title(), variable=var).pack(side="left", padx=2)
            self.app.marathon_day_vars[day] = var
        self.app.marathon_all_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(day_frame, text="All", variable=self.app.marathon_all_var,
                        command=self.app.on_marathon_all_toggle).pack(side="left", padx=5)

        marathon_opt_frame = ttk.Frame(marathon_tab)
        marathon_opt_frame.pack(fill="x", pady=(0, 5))
        self.app.marathon_shuffle_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(marathon_opt_frame, text="Shuffle within marathon",
                        variable=self.app.marathon_shuffle_var).pack(side="left", padx=5)
        self.app.marathon_norepeat_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(marathon_opt_frame, text="No repeats within 24h",
                        variable=self.app.marathon_norepeat_var).pack(side="left", padx=5)

        marathon_btn_frame = ttk.Frame(marathon_tab)
        marathon_btn_frame.pack(fill="x")
        ttk.Button(marathon_btn_frame, text="Add Marathon",    command=self.app.on_add_marathon).pack(side="left", padx=2)
        ttk.Button(marathon_btn_frame, text="Remove Selected", command=self.app.on_remove_marathon).pack(side="left", padx=2)

        self.app.marathon_list = tk.Listbox(marathon_tab, height=4, font=("TkDefaultFont", 10))
        self.app.marathon_list.pack(fill="x", pady=(5, 0))

        # --- Tab 2: Gap Filler Settings ---
        gap_tab = ttk.Frame(mid_nb, padding=8)
        mid_nb.add(gap_tab, text="Gap Filler Settings")

        self.app.gap_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(gap_tab, text="Enable gap filling with random content",
                        variable=self.app.gap_enabled_var).pack(anchor="w", pady=(0, 5))

        source_frame = ttk.Frame(gap_tab)
        source_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(source_frame, text="Source:").pack(side="left", padx=(0, 5))
        self.app.gap_source_var = tk.StringVar(value="all")
        ttk.Radiobutton(source_frame, text="All videos",           variable=self.app.gap_source_var, value="all",         command=self.app.on_gap_source_change).pack(side="left", padx=5)
        ttk.Radiobutton(source_frame, text="Selected collections", variable=self.app.gap_source_var, value="collections", command=self.app.on_gap_source_change).pack(side="left", padx=5)
        ttk.Radiobutton(source_frame, text="Selected tags",        variable=self.app.gap_source_var, value="tags",        command=self.app.on_gap_source_change).pack(side="left", padx=5)

        exclude_frame = ttk.Frame(gap_tab)
        exclude_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(exclude_frame, text="Exclude tags:").pack(side="left", padx=(0, 5))
        self.app.gap_exclude_label = ttk.Label(exclude_frame, text="[None]", foreground="blue", cursor="hand2")
        self.app.gap_exclude_label.pack(side="left")
        self.app.gap_exclude_label.bind("<Button-1>", self.app.on_edit_excluded_tags)

        gap_opt_frame = ttk.Frame(gap_tab)
        gap_opt_frame.pack(fill="x")
        self.app.gap_24h_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(gap_opt_frame, text="Respect 24-hour no-repeat rule",
                        variable=self.app.gap_24h_var).pack(side="left", padx=5)
        self.app.gap_shuffle_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(gap_opt_frame, text="Shuffle selection",
                        variable=self.app.gap_shuffle_var).pack(side="left", padx=5)
        
        # === PREVIEW PANEL ===
        # Note: Preview is displayed in the main Schedule Preview panel on the right
        # Click "Generate Preview" button below to see the schedule preview
        
        # Preview mode selection
        preview_mode_frame = ttk.Frame(main_frame)
        preview_mode_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(preview_mode_frame, text="Preview Mode:").pack(side="left", padx=(0, 5))
        self.app.preview_mode_var = tk.StringVar(value="single")
        ttk.Radiobutton(preview_mode_frame, text="Single Day", variable=self.app.preview_mode_var,
                       value="single").pack(side="left", padx=5)
        ttk.Radiobutton(preview_mode_frame, text="Weekly (7 days)", variable=self.app.preview_mode_var,
                       value="weekly").pack(side="left", padx=5)
        ttk.Radiobutton(preview_mode_frame, text="Calendar Range", variable=self.app.preview_mode_var,
                       value="calendar").pack(side="left", padx=5)
        
        # Calendar date range (for calendar mode)
        calendar_range_frame = ttk.Frame(main_frame)
        calendar_range_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(calendar_range_frame, text="From:").pack(side="left", padx=(0, 5))
        self.app.preview_start_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(calendar_range_frame, textvariable=self.app.preview_start_date_var, width=12).pack(side="left", padx=2)
        ttk.Label(calendar_range_frame, text="To:").pack(side="left", padx=(10, 5))
        self.app.preview_end_date_var = tk.StringVar(value=(datetime.now() + timedelta(days=6)).strftime("%Y-%m-%d"))
        ttk.Entry(calendar_range_frame, textvariable=self.app.preview_end_date_var, width=12).pack(side="left", padx=2)
        
        # Global Approximate checkbox — short label, tooltip carries the explanation
        approximate_frame = ttk.Frame(main_frame)
        approximate_frame.pack(fill="x", pady=(0, 10))
        self.app.use_approximation_var = tk.BooleanVar(value=False)
        approx_chk = ttk.Checkbutton(approximate_frame, text="Approximate",
                      variable=self.app.use_approximation_var)
        approx_chk.pack(side="left", padx=5)
        self.app.create_tooltip(approx_chk, "Move blocks to fill gaps (global setting) — applies to all blocks when generating preview")

        # Action buttons — row 1
        action_row1 = ttk.Frame(main_frame)
        action_row1.pack(fill="x", pady=(10, 2))
        ttk.Button(action_row1, text="Generate Preview",
                  command=self.app.on_generate_daypart_preview).pack(side="left", padx=5)
        ttk.Button(action_row1, text="Save Schedule",
                  command=self.app.on_save_daypart_schedule).pack(side="left", padx=5)
        ttk.Button(action_row1, text="Copy Preview",
                  command=self.app.on_copy_daypart_preview).pack(side="left", padx=5)
        ttk.Button(action_row1, text="Export Config",
                  command=self.on_export_daypart_config).pack(side="left", padx=5)

        # Action buttons — row 2
        action_row2 = ttk.Frame(main_frame)
        action_row2.pack(fill="x", pady=(0, 4))
        ttk.Button(action_row2, text="Import Config",
                  command=self.on_import_daypart_config).pack(side="left", padx=5)
        ttk.Button(action_row2, text="Save Work",
                  command=self.on_save_daypart_work).pack(side="left", padx=5)
        ttk.Button(action_row2, text="Load Work",
                  command=self.on_load_daypart_work).pack(side="left", padx=5)

        # Save as Normal Schedule
        save_normal_frame = ttk.LabelFrame(main_frame, text="Save as Normal Schedule", padding=(8, 4))
        save_normal_frame.pack(fill="x", pady=(8, 0))
        ttk.Label(save_normal_frame, text="Channel:").pack(side="left", padx=(0, 4))
        self.app.save_normal_channel_var = tk.StringVar(value=self.app.current_channel or "")
        self.app.save_normal_channel_combo = ttk.Combobox(
            save_normal_frame, textvariable=self.app.save_normal_channel_var,
            values=self.app._get_known_channels_daypart(), width=14
        )
        self.app.save_normal_channel_combo.pack(side="left", padx=(0, 10))
        ttk.Label(save_normal_frame, text="(uses Preview Mode & date range above)").pack(side="left", padx=(0, 10))
        ttk.Button(save_normal_frame, text="Save as Normal Schedule",
                  command=self.app.on_save_as_normal_schedule).pack(side="left", padx=5)
        
        # Initialize daypart config for current channel
        self.app.load_daypart_config_for_channel()
        
        return main_frame
    
    def on_export_daypart_config(self):
        """Export daypart configuration to a standalone JSON file"""
        try:
            # Build export data
            export_data = {
                "version": "1.0",
                "export_date": datetime.now().isoformat(),
                "daypart_config": {
                    "time_blocks": [b.to_dict() for b in self.app.daypart_time_blocks],
                    "marathons": [m.to_dict() for m in self.app.daypart_marathons],
                    "gap_filler": self.app.daypart_gap_filler.to_dict()
                }
            }
            
            # Ask user for save location
            file_path = filedialog.asksaveasfilename(
                title="Export Daypart Configuration",
                defaultextension=".json",
                filetypes=["JSON files (*.json)", "All files (*.*)"],
                initialfile=f"daypart_config_{self.app.current_channel or 'export'}.json"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
            
            messagebox.showinfo("Export Successful", 
                f"Daypart configuration exported to:\n{file_path}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {str(e)}")
            import logging
            logging.getLogger("AkiraTV").error(f"Daypart export failed: {e}", exc_info=True)
    
    def on_import_daypart_config(self):
        """Import daypart configuration from a standalone JSON file"""
        try:
            # Ask user for file to import
            file_path = filedialog.askopenfilename(
                title="Import Daypart Configuration",
                filetypes=["JSON files (*.json)", "All files (*.*)"]
            )
            
            if not file_path:
                return  # User cancelled
            
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Validate import data structure
            if "daypart_config" not in import_data:
                messagebox.showerror("Import Error", "Invalid file format: missing 'daypart_config' key")
                return
            
            daypart_config = import_data["daypart_config"]
            
            # Import time blocks
            self.app.daypart_time_blocks = []
            from ..daypart_scheduler import TimeBlock
            for block_data in daypart_config.get("time_blocks", []):
                try:
                    block = TimeBlock.from_dict(block_data)
                    self.app.daypart_time_blocks.append(block)
                except Exception as e:
                    import logging
                    logging.getLogger("AkiraTV").warning(f"Failed to import block: {e}")
            
            # Import marathons
            self.app.daypart_marathons = []
            from ..daypart_scheduler import MarathonConfig
            for marathon_data in daypart_config.get("marathons", []):
                try:
                    marathon = MarathonConfig.from_dict(marathon_data)
                    self.app.daypart_marathons.append(marathon)
                except Exception as e:
                    import logging
                    logging.getLogger("AkiraTV").warning(f"Failed to import marathon: {e}")
            
            # Import gap filler
            from ..daypart_scheduler import GapFillerConfig
            gap_data = daypart_config.get("gap_filler", {})
            self.app.daypart_gap_filler = GapFillerConfig.from_dict(gap_data)
            
            # Update UI
            self.app.update_block_list()
            self.app.update_marathon_list()
            self.app.update_gap_filler_ui()
            self.app.update_preview_display()
            
            # Show import summary
            block_count = len(self.app.daypart_time_blocks)
            marathon_count = len(self.app.daypart_marathons)
            messagebox.showinfo("Import Successful", 
                f"Imported:\n• {block_count} time block(s)\n• {marathon_count} marathon(s)\n• Gap filler settings")
            
        except json.JSONDecodeError as e:
            messagebox.showerror("Import Error", f"Invalid JSON format: {str(e)}")
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import: {str(e)}")
            import logging
            logging.getLogger("AkiraTV").error(f"Daypart import failed: {e}", exc_info=True)
    
    def on_save_daypart_work(self):
        """Save daypart blocks to an INI file for reuse"""
        try:
            import configparser
            from pathlib import Path
            
            # Check if there are blocks to save
            if not self.app.daypart_time_blocks and not self.app.daypart_marathons:
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
            for i, block in enumerate(self.app.daypart_time_blocks):
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
            for i, marathon in enumerate(self.app.daypart_marathons):
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
            if hasattr(self.app, 'daypart_gap_filler') and self.app.daypart_gap_filler:
                config["GapFiller"] = {
                    "enabled": str(self.app.daypart_gap_filler.enabled),
                    "source": self.app.daypart_gap_filler.source,
                    "collection_ids": ",".join(self.app.daypart_gap_filler.collection_ids) if self.app.daypart_gap_filler.collection_ids else "",
                    "tags": ",".join(self.app.daypart_gap_filler.tags) if self.app.daypart_gap_filler.tags else "",
                    "excluded_tags": ",".join(self.app.daypart_gap_filler.excluded_tags) if self.app.daypart_gap_filler.excluded_tags else "",
                    "respect_24h_norepeat": str(self.app.daypart_gap_filler.respect_24h_norepeat),
                    "shuffle": str(self.app.daypart_gap_filler.shuffle)
                }
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                config.write(f)
            
            block_count = len(self.app.daypart_time_blocks)
            marathon_count = len(self.app.daypart_marathons)
            messagebox.showinfo("Save Successful", 
                f"Daypart work saved to:\n{file_path}\n\nSaved:\n• {block_count} time block(s)\n• {marathon_count} marathon(s)")
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save: {str(e)}")
            import logging
            logging.getLogger("AkiraTV").error(f"Daypart save work failed: {e}", exc_info=True)
    
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
            from ..daypart_scheduler import TimeBlock, MarathonConfig, GapFillerConfig
            
            self.app.daypart_time_blocks = []
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
                        self.app.daypart_time_blocks.append(block)
                    except Exception as e:
                        import logging
                        logging.getLogger("AkiraTV").warning(f"Failed to load block {section}: {e}")
            
            # Load marathons
            self.app.daypart_marathons = []
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
                        self.app.daypart_marathons.append(marathon)
                    except Exception as e:
                        import logging
                        logging.getLogger("AkiraTV").warning(f"Failed to load marathon {section}: {e}")
            
            # Load gap filler
            if "GapFiller" in config:
                gap_section = config["GapFiller"]
                self.app.daypart_gap_filler = GapFillerConfig(
                    enabled=gap_section.get("enabled", "False").lower() == "true",
                    source=gap_section.get("source", "all"),
                    collection_ids=gap_section.get("collection_ids", "").split(",") if gap_section.get("collection_ids") else [],
                    tags=gap_section.get("tags", "").split(",") if gap_section.get("tags") else [],
                    excluded_tags=gap_section.get("excluded_tags", "").split(",") if gap_section.get("excluded_tags") else [],
                    respect_24h_norepeat=gap_section.get("respect_24h_norepeat", "True").lower() == "true",
                    shuffle=gap_section.get("shuffle", "True").lower() == "true"
                )
            
            # Update UI
            self.app.update_block_list()
            self.app.update_marathon_list()
            self.app.update_gap_filler_ui()
            self.app.update_preview_display()
            
            # Show import summary
            block_count = len(self.app.daypart_time_blocks)
            marathon_count = len(self.app.daypart_marathons)
            messagebox.showinfo("Load Successful", 
                f"Loaded from:\n{file_path}\n\nImported:\n• {block_count} time block(s)\n• {marathon_count} marathon(s)\n• Gap filler settings")
            
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load: {str(e)}")
            import logging
            logging.getLogger("AkiraTV").error(f"Daypart load work failed: {e}", exc_info=True)
    
    def on_copy_blocks_to_channel(self):
        """Copy current daypart blocks to another channel"""
        if not self.app.daypart_time_blocks and not self.app.daypart_marathons:
            messagebox.showwarning("Nothing to Copy", "No time blocks or marathons to copy")
            return
        
        # Get list of available channels
        from ..scheduler import load_channels
        channels = load_channels()
        
        if not channels:
            messagebox.showwarning("No Channels", "No channels available to copy to")
            return
        
        # Create a simple selection dialog
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Copy to Channel")
        dialog.geometry("300x200")
        dialog.transient(self.app.root)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text="Select destination channel:").pack(pady=(0, 10))
        
        # Channel list
        channel_var = tk.StringVar()
        channel_combo = ttk.Combobox(frame, textvariable=channel_var, state="readonly")
        channel_combo['values'] = [ch.get("name", "Unknown") for ch in channels]
        if channels:
            channel_combo.current(0)
        channel_combo.pack(fill="x", pady=(0, 10))
        
        # Options
        copy_var = tk.StringVar(value="all")
        ttk.Radiobutton(frame, text="Copy all (blocks, marathons, gap filler)", 
                       variable=copy_var, value="all").pack(anchor="w")
        ttk.Radiobutton(frame, text="Copy time blocks only", 
                       variable=copy_var, value="blocks").pack(anchor="w")
        ttk.Radiobutton(frame, text="Copy marathons only", 
                       variable=copy_var, value="marathons").pack(anchor="w")
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=(10, 0))
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Copy", 
                  command=lambda: self.do_copy_blocks(dialog, channel_var.get(), copy_var.get())).pack(side="left", padx=5)
    
    def do_copy_blocks(self, dialog, channel_name, copy_option):
        """Perform the actual copy operation"""
        try:
            from ..daypart_scheduler import TimeBlock, MarathonConfig, GapFillerConfig
            
            # Load existing config for target channel
            config = self.app.daypart_scheduler.load_config(channel_name) or {}
            
            if copy_option in ("all", "blocks"):
                config["daypart_config"] = config.get("daypart_config", {})
                config["daypart_config"]["time_blocks"] = [b.to_dict() for b in self.app.daypart_time_blocks]
            
            if copy_option in ("all", "marathons"):
                config["daypart_config"] = config.get("daypart_config", {})
                config["daypart_config"]["marathons"] = [m.to_dict() for m in self.app.daypart_marathons]
                config["daypart_config"]["gap_filler"] = self.app.daypart_gap_filler.to_dict()
            
            # Save to target channel
            if self.app.daypart_scheduler.save_config(channel_name, config):
                messagebox.showinfo("Copy Successful", 
                    f"Copied daypart configuration to channel '{channel_name}'")
            else:
                messagebox.showerror("Copy Failed", "Failed to save configuration")
            
            dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("Copy Error", f"Failed to copy: {str(e)}")
            import logging
            logging.getLogger("AkiraTV").error(f"Copy to channel failed: {e}", exc_info=True)


def create_daypart_tab(parent, scheduler_app):
    """
    Convenience function to create the daypart scheduling tab.
    
    Args:
        parent: Parent widget (tab frame)
        scheduler_app: The SimpleSchedulerWizard instance
    
    Returns:
        The created main frame
    """
    ui = DaypartSchedulerUI(scheduler_app)
    return ui.create_daypart_panel(parent)