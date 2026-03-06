# akiratv/wizard_clean.py
import tkinter as tk
from tkinter import ttk, messagebox
import json
from pathlib import Path

def load_collections():
    try:
        with open("collections.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("collections", [])
    except:
        return []

class WeeklyScheduleWizard:
    def __init__(self, root):
        self.root = root
        self.root.title("AkiraTV — Time Block Scheduler")
        self.root.geometry("1000x600")
        
        self.days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        self.collections = load_collections()
        self.all_entries = {day: [] for day in self.days}
        self.selected_day = None
        self.selected_time = None
        
        self.create_widgets()

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Collections panel
        left_frame = ttk.LabelFrame(main_frame, text="Collections")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0,5))
        self.collection_list = tk.Listbox(left_frame, width=30)
        self.collection_list.pack(fill="both", expand=True, padx=5, pady=5)
        for col in self.collections:
            self.collection_list.insert(tk.END, col["name"])
        
        # Time grid panel
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5,0))
        
        # Canvas with scrollbar
        canvas = tk.Canvas(right_frame)
        scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create time grid
        self.time_buttons = {}
        for day in self.days:
            day_frame = ttk.LabelFrame(scrollable_frame, text=day.title())
            day_frame.pack(fill="x", padx=5, pady=2)
            self.time_buttons[day] = {}
            for hour in range(24):
                time_str = f"{hour:02d}:00"
                def make_command(d, t):
                    return lambda: self.on_time_click(d, t)
                btn = tk.Button(day_frame, text=time_str, width=8, 
                               command=make_command(day, time_str))
                btn.pack(side="top", padx=2, pady=1)
                self.time_buttons[day][time_str] = btn
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bottom buttons
        btn_frame = ttk.Frame(self.root)
        btn_zone = ttk.Frame(self.root)
        btn_frame.pack(padx=10, pady=5)
        ttk.Button(btn_frame, text="+ Add from Collections", 
                  command=self.open_collection_picker).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Save", command=self.save_schedule).pack(side="left", padx=5)
    
    def on_time_click(self, day, time_slot):
        self.selected_day = day
        self.selected_time = time_slot
        print(f"[OK] Selected: {day} at {time_slot}")
    
    def open_collection_picker(self):
        if not self.selected_day or not self.selected_time:
            messagebox.showwarning("No Time Selected", "Click a time block first!")
            return
        
        picker = tk.Toplevel(self.root)
        picker.title("Select Video")
        picker.geometry("500x300")
        
        # Simple list of collections
        col_list = tk.Listbox(picker)
        col_list.pack(fill="both", expand=True, padx=10, pady=10)
        for col in self.collections:
            col_list.insert(tk.END, col["name"])
        
        def add_video():
            if not col_list.curselection():
                return
            idx = col_list.curselection()[0]
            col = self.collections[idx]
            if col["videos"]:
                video_path = col["videos"][0]["path"]  # First video
                self.add_video_to_time(self.selected_day, self.selected_time, video_path)
                picker.destroy()
        
        ttk.Button(picker, text="Add", command=add_video).pack(pady=10)
    
    def add_video_to_time(self, day, time_slot, video_path):
        hour = int(time_slot.split(":")[0])
        start_time = f"{hour:02d}:00:00"
        
        if day not in self.all_entries:
            self.all_entries[day] = []
        
        self.all_entries[day].append({
            "time": start_time,
            "file": video_path,
            "channel": "critters",
            "source": "manual"
        })
        
        # Visual feedback
        for time_str, btn in self.time_buttons[day].items():
            if time_str == time_slot:
                btn.config(bg="lightblue")
        
        print(f"[OK] Added {Path(video_path).name} to {day} at {time_slot}")
    
    def save_schedule(self):
        # Simple save
        with open("schedule_test.json", "w") as f:
            json.dump({"weekly": self.all_entries}, f, indent=2)
        messagebox.showinfo("Saved", "Schedule saved to schedule_test.json")

def launch_wizard():
    root = tk.Tk()
    app = WeeklyScheduleWizard(root)
    root.mainloop()