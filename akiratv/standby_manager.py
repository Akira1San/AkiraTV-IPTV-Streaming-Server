"""
Standby Manager Module for AkiraTV Simple Scheduler
Handles standby video generation and management
"""

import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

class StandbyManager:
    """Manager for standby video generation and settings"""
    
    def __init__(self, parent):
        self.parent = parent
        self.base_dir = Path(__file__).resolve().parents[1]
        self.standby_dir = self.base_dir / "assets" / "standby"
        
        self.create_standby_widgets()
    
    def create_standby_widgets(self):
        """Create standby management widgets"""
        # Main container
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header
        ttk.Label(self.main_frame, text="Standby Management", font=("TkDefaultFont", 12, "bold")).pack(pady=(0, 15))
        
        # Standby video settings
        settings_frame = ttk.LabelFrame(self.main_frame, text="Standby Video Settings")
        settings_frame.pack(fill="x", pady=5)
        
        # Loop duration
        duration_frame = ttk.Frame(settings_frame)
        duration_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(duration_frame, text="Loop Duration (seconds):").pack(side="left")
        self.duration_var = tk.StringVar(value="30")
        duration_entry = ttk.Entry(duration_frame, textvariable=self.duration_var, width=5)
        duration_entry.pack(side="left", padx=5)
        
        # Video format selection
        format_frame = ttk.Frame(settings_frame)
        format_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(format_frame, text="Output Format:").pack(side="left")
        self.format_var = tk.StringVar(value="mp4")
        format_combo = ttk.Combobox(format_frame, textvariable=self.format_var, 
                                    values=["mp4", "avi", "mkv"], state="readonly", width=10)
        format_combo.pack(side="left", padx=5)
        
        # Quality settings
        quality_frame = ttk.Frame(settings_frame)
        quality_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(quality_frame, text="Quality:").pack(side="left")
        self.quality_var = tk.StringVar(value="720p")
        quality_combo = ttk.Combobox(quality_frame, textvariable=self.quality_var, 
                                     values=["480p", "720p", "1080p"], state="readonly", width=10)
        quality_combo.pack(side="left", padx=5)
        
        # Bumper generation section
        bumper_frame = ttk.LabelFrame(self.main_frame, text="Bumper Generation")
        bumper_frame.pack(fill="both", expand=True, pady=5)
        
        # Available standbys
        ttk.Label(bumper_frame, text="Available Standby Videos:").pack(anchor="w", padx=10, pady=5)
        list_frame = ttk.Frame(bumper_frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.standby_list = tk.Listbox(list_frame, font=("TkDefaultFont", 10))
        self.standby_list.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.standby_list.yview)
        scrollbar.pack(side="right", fill="y")
        self.standby_list.configure(yscrollcommand=scrollbar.set)
        
        # Preview area
        preview_frame = ttk.Frame(bumper_frame)
        preview_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(preview_frame, text="Preview:").pack(anchor="w", pady=5)
        
        self.preview_label = tk.Label(preview_frame, text="No preview available", 
                                     font=("TkDefaultFont", 9), foreground="gray",
                                     relief="solid", borderwidth=1, height=8)
        self.preview_label.pack(fill="x")
        
        # Buttons
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill="x", pady=10)
        
        ttk.Button(button_frame, text="Refresh Standby List", command=self.refresh_standby_list).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Generate Bumper", command=self.generate_bumper).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Preview Selected", command=self.preview_standby).pack(side="left", padx=5)
        
        # Load initial standby list
        self.refresh_standby_list()
    
    def refresh_standby_list(self):
        """Refresh the list of available standby videos"""
        self.standby_list.delete(0, tk.END)
        
        if not self.standby_dir.exists():
            return
        
        for file in self.standby_dir.glob("*.mp4"):
            self.standby_list.insert(tk.END, file.name)
    
    def preview_standby(self):
        """Preview selected standby video (placeholder)"""
        selection = self.standby_list.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Select a standby video to preview")
            return
        
        selected_file = self.standby_list.get(selection[0])
        file_path = self.standby_dir / selected_file
        
        # Placeholder for actual video preview
        self.preview_label.config(text=f"Previewing: {selected_file}\nDuration: {self.duration_var.get()}s loop", 
                                 foreground="black")
    
    def generate_bumper(self):
        """Generate a bumper video (placeholder)"""
        duration = self.duration_var.get()
        try:
            duration = int(duration)
            if duration <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid duration (positive number)")
            return
        
        format_type = self.format_var.get()
        quality = self.quality_var.get()
        
        # Placeholder for actual bumper generation
        messagebox.showinfo("Info", f"Bumper generation will be implemented here.\n\n"
                                   f"Settings:\n"
                                   f"Duration: {duration} seconds\n"
                                   f"Format: {format_type}\n"
                                   f"Quality: {quality}")
    
    def get_bumper_settings(self):
        """Get current bumper settings"""
        return {
            "duration": int(self.duration_var.get()),
            "format": self.format_var.get(),
            "quality": self.quality_var.get()
        }
    
    def set_bumper_settings(self, settings):
        """Set bumper settings"""
        self.duration_var.set(str(settings.get("duration", 30)))
        self.format_var.set(settings.get("format", "mp4"))
        self.quality_var.set(settings.get("quality", "720p"))


class StandbyTab:
    """Wrapper class for integrating StandbyManager into SimpleSchedulerWizard"""
    
    def __init__(self, parent):
        self.parent = parent
        self.standby_manager = StandbyManager(parent)
    
    def get_settings(self):
        """Get standby manager settings"""
        return self.standby_manager.get_bumper_settings()
    
    def set_settings(self, settings):
        """Set standby manager settings"""
        self.standby_manager.set_bumper_settings(settings)
