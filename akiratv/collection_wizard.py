# akiratv/collection_wizard.py (updated with profiles)
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import re
from pathlib import Path
from datetime import datetime
import subprocess
import difflib
import unicodedata

COLLECTIONS_DIR = Path(__file__).parent.parent / "user" / "collections"
COVERS_DIR = Path(__file__).parent.parent / "user" / "covers"
COLLECTIONS_DIR.mkdir(parents=True, exist_ok=True)  # ensure folder exists
COVERS_DIR.mkdir(parents=True, exist_ok=True)  # ensure folder exists

class CollectionWizard:
    def __init__(self, root):
        self.root = root
        self.root.title("AkiraTV — Collection Manager")
        self.root.geometry("1000x700")  # Increased height for additional fields
        
        self.collections = []
        self.video_database = {}
        self.folder_path = tk.StringVar()
        self.current_profile = "default"  # Default profile name (will become collections_default.json)
        
        # Genre tags
        self.genre_tags = ["Action", "Adventure", "Anime", "Comedy", "Drama", "Fantasy", 
                          "Horror", "Mystery", "Romance", "Sci-Fi", "Thriller", "Documentary"]
        
        # Track selected videos for tagging
        self.selected_indices = set()
        
        self.load_collections()
        self.create_widgets()

    def load_collections(self):
        """Load collections from current profile"""
        try:
            profile_file = COLLECTIONS_DIR / f"{self.current_profile}.json"
            with open(profile_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.collections = data.get("collections", [])
        except:
            self.collections = []

    def save_collections(self):
        """Save collections to current profile"""
        try:
            # Get the profile name from the text field, not self.current_profile
            profile_name = self.profile_var.get().strip()
            if not profile_name:
                messagebox.showwarning("Warning", "Please enter a profile name!")
                return
            
            # Handle the filename properly - ensure collections_ prefix without duplication
            # Remove collections_ prefix if it exists, then add it back
            if profile_name.startswith("collections_"):
                clean_name = profile_name[12:]  # Remove "collections_" prefix
            else:
                clean_name = profile_name
            
            # Remove .json extension if provided
            if clean_name.endswith(".json"):
                clean_name = clean_name[:-5]
            
            # Now add the prefix back
            filename = f"collections_{clean_name}.json"
            profile_file = COLLECTIONS_DIR / filename
            
            # Debug: Show what we're about to save
            print(f"DEBUG: Saving {len(self.collections)} collections to {profile_file}")
            print(f"DEBUG: Full file path: {profile_file.absolute()}")
            print(f"DEBUG: Profile from text field: '{profile_name}' -> clean name: '{clean_name}' -> filename: '{filename}'")
            
            for i, collection in enumerate(self.collections[:3]):  # Show first 3 collections
                print(f"DEBUG: Collection {i}: {collection.get('name', 'No name')} - {collection.get('description', 'No description')[:50]}...")
            
            # Check if file exists before writing
            if profile_file.exists():
                print(f"DEBUG: File exists, will overwrite: {profile_file}")
            else:
                print(f"DEBUG: Creating new file: {profile_file}")
            
            # Try to write the file
            with open(profile_file, "w", encoding="utf-8") as f:
                json.dump({"collections": self.collections}, f, indent=2, ensure_ascii=False)
            
            # Verify the file was written
            if profile_file.exists():
                file_size = profile_file.stat().st_size
                print(f"DEBUG: File written successfully, size: {file_size} bytes")
                # Update current_profile to match what we just saved
                self.current_profile = clean_name
            else:
                print(f"DEBUG: ERROR - File was not created!")
                
            messagebox.showinfo("Success", f"Collections saved to {profile_file.name}!")
            
        except PermissionError as e:
            print(f"DEBUG: Permission error - file may be locked by another process")
            messagebox.showerror("File Locked", 
                f"Cannot save to {profile_file.name}!\n\n"
                f"The file may be locked by AkiraTV or another program.\n\n"
                f"Solutions:\n"
                f"• Close AkiraTV and try again\n"
                f"• Use 'Save As' with a different name\n"
                f"• Check if the file is open in a text editor")
        except Exception as e:
            print(f"DEBUG: Exception during save: {e}")
            messagebox.showerror("Error", f"Failed to save collections:\n{str(e)}")

    def auto_find_cover(self, video_path):
        """Improved cover matching algorithm"""
        if not COVERS_DIR.exists():
            return None

        video_name = Path(video_path).stem
        
        # Clean up the video name for better matching
        clean_video_name = self.normalize_name_for_matching(video_name)
        
        # Get all cover files
        cover_files = []
        for ext in [".jpg", ".jpeg", ".png", ".webp"]:
            cover_files.extend(COVERS_DIR.glob(f"*{ext}"))
        
        if not cover_files:
            return None
            
        # Try to find the best match
        best_match = None
        best_ratio = 0
        
        for cover_path in cover_files:
            cover_name = cover_path.stem
            clean_cover_name = self.normalize_name_for_matching(cover_name)
            
            # Calculate similarity ratio
            ratio = difflib.SequenceMatcher(None, clean_video_name, clean_cover_name).ratio()
            
            # Check for partial matches (video name in cover name or vice versa)
            if clean_video_name in clean_cover_name or clean_cover_name in clean_video_name:
                ratio = max(ratio, 0.8)  # Boost ratio for partial matches
                
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = cover_path
        
        # Only return if we have a decent match (threshold of 0.6)
        if best_match and best_ratio > 0.6:
            return f"user/covers/{best_match.name}"
            
        return None

    def normalize_name_for_matching(self, name):
        """Normalize name for better matching"""
        # Remove common patterns
        name = re.sub(r'\d{4}', '', name)  # Remove years
        name = re.sub(r'(1080p|720p|2160p|4k|bluray|webrip|bdrip|dvdrip|x264|x265|h264|h265)', '', name, flags=re.IGNORECASE)
        name = re.sub(r'(fmp4|mp4|mkv|avi|mov|webm|remux|remastered|extended|uncut)', '', name, flags=re.IGNORECASE)
        name = re.sub(r'(dd5\.1|aac|ac3|dts|flac)', '', name, flags=re.IGNORECASE)
        name = re.sub(r'(\-|_|\.)', ' ', name)  # Replace separators with space
        name = re.sub(r'\s+', ' ', name)  # Replace multiple spaces with single space
        name = name.strip().lower()
        
        # Remove common tags at the end
        if ' part ' in name:
            name = name.split(' part ')[0]
        if ' pt ' in name:
            name = name.split(' pt ')[0]
            
        return name

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Profile selection
        profile_frame = ttk.Frame(main_frame)
        profile_frame.pack(fill="x", pady=(0, 10))
        
        # First row: Quick select dropdown
        profile_row1 = ttk.Frame(profile_frame)
        profile_row1.pack(fill="x", pady=(0, 5))
        ttk.Label(profile_row1, text="Quick Select:").pack(side="left")
        self.quick_profile_var = tk.StringVar(value="")
        self.profile_dropdown = ttk.Combobox(profile_row1, textvariable=self.quick_profile_var, 
                                           values=self.get_available_collection_profiles(), 
                                           state="readonly", width=25)
        self.profile_dropdown.pack(side="left", padx=5)
        self.profile_dropdown.bind("<<ComboboxSelected>>", self.on_quick_profile_select)
        ttk.Button(profile_row1, text="Refresh", command=self.refresh_profile_dropdown).pack(side="left", padx=2)
        
        # Second row: Manual entry and save buttons
        profile_row2 = ttk.Frame(profile_frame)
        profile_row2.pack(fill="x")
        ttk.Label(profile_row2, text="Or type name:").pack(side="left")
        self.profile_var = tk.StringVar(value=self.current_profile)
        profile_entry = ttk.Entry(profile_row2, textvariable=self.profile_var, width=20)
        profile_entry.pack(side="left", padx=5)
        ttk.Button(profile_row2, text="Load Profile", command=self.load_profile).pack(side="left", padx=2)
        ttk.Button(profile_row2, text="Browse...", command=self.load_profile_dialog).pack(side="left", padx=2)
        ttk.Button(profile_row2, text="Save", command=self.save_collections).pack(side="left", padx=2)
        ttk.Button(profile_row2, text="Save As", command=self.save_as_profile).pack(side="left", padx=2)
        
        # Rest of UI (folder selection, buttons, etc.)
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(top_frame, text="Video Folder:").pack(side="left")
        ttk.Entry(top_frame, textvariable=self.folder_path, width=50).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Browse", command=self.browse_folder).pack(side="left", padx=2)
        
        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(side="right")
        ttk.Button(btn_frame, text="Load Video Info", command=self.load_video_info).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Re-Scan Folder", command=self.rescan_folder).pack(side="left", padx=2)
        
        # Create a container for the list and tags
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True)
        
        # Collections list with scrollbar
        list_frame = ttk.LabelFrame(content_frame, text="Collections")
        list_frame.pack(side="left", fill="both", expand=True, pady=(0, 10))
        
        # Selection buttons
        selection_btn_frame = ttk.Frame(list_frame)
        selection_btn_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(selection_btn_frame, text="Select All", command=self.select_all).pack(side="left", padx=2)
        ttk.Button(selection_btn_frame, text="Unselect All", command=self.unselect_all).pack(side="left", padx=2)
        ttk.Button(selection_btn_frame, text="Remove", command=self.remove_collections).pack(side="left", padx=2)
        
        # Create a frame for the listbox and scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create scrollbar
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side="right", fill="y")
        
        # Create listbox with multi-select mode and extended selection (allows drag selection)
        self.collection_list = tk.Listbox(list_container, selectmode=tk.EXTENDED, 
                                         yscrollcommand=scrollbar.set)
        self.collection_list.pack(fill="both", expand=True)
        scrollbar.config(command=self.collection_list.yview)
        
        # Bind selection event
        self.collection_list.bind("<<ListboxSelect>>", self.on_collection_select)
        
        # Tags panel on the right
        tags_frame = ttk.LabelFrame(content_frame, text="Tags")
        tags_frame.pack(side="right", fill="y", padx=(10, 0))
        
        # Genre tags
        genre_frame = ttk.LabelFrame(tags_frame, text="Genre Tags")
        genre_frame.pack(fill="x", padx=5, pady=5)
        
        self.genre_vars = {}
        for tag in self.genre_tags:
            var = tk.BooleanVar()
            self.genre_vars[tag] = var
            cb = ttk.Checkbutton(genre_frame, text=tag, variable=var, 
                                command=lambda t=tag: self.toggle_genre_tag(t))
            cb.pack(anchor="w", padx=5, pady=2)
        
        # Episodic tag
        episodic_frame = ttk.LabelFrame(tags_frame, text="Special Tags")
        episodic_frame.pack(fill="x", padx=5, pady=5)
        
        self.episodic_var = tk.BooleanVar()
        episodic_cb = ttk.Checkbutton(episodic_frame, text="Episodic", 
                                     variable=self.episodic_var,
                                     command=self.toggle_episodic_tag)
        episodic_cb.pack(anchor="w", padx=5, pady=2)
        
        # Metadata details
        detail_frame = ttk.LabelFrame(main_frame, text="Collection Details")
        detail_frame.pack(fill="x")

        self.cover_var = tk.StringVar() # cover

        # Metadata fields - added ID field
        fields = [
            ("ID:", "id_var"),
            ("Name:", "name_var"),
            ("Cover:", "cover_var"),
            ("Description:", "desc_var"), 
            ("Genre (comma-separated):", "genre_var"),
            ("Rating:", "rating_var"),
            ("Year:", "year_var")
        ]
        
        self.metadata_vars = {}
        for i, (label_text, var_name) in enumerate(fields):
            ttk.Label(detail_frame, text=label_text).grid(row=i, column=0, sticky="w", padx=5, pady=2)
            if var_name == "rating_var":
                var = tk.StringVar()
                combo = ttk.Combobox(detail_frame, textvariable=var, 
                                    values=["NR", "G", "PG", "PG-13", "R", "NC-17"], width=47)
                combo.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            elif var_name == "id_var":  # ID field should be read-only
                var = tk.StringVar()
                entry = ttk.Entry(detail_frame, textvariable=var, width=50, state="readonly")
                entry.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            else:
                var = tk.StringVar()
                entry = ttk.Entry(detail_frame, textvariable=var, width=50)
                entry.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            self.metadata_vars[var_name] = var
        
        # Update button
        button_frame = ttk.Frame(detail_frame)
        button_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Update Collection(s)", command=self.update_collections).pack(side="left", padx=5)
        
        detail_frame.columnconfigure(1, weight=1)
        self.refresh_collection_list()

    def select_all(self):
        """Select all items in the list"""
        self.collection_list.selection_set(0, tk.END)
        self.on_collection_select(None)

    def unselect_all(self):
        """Unselect all items in the list"""
        self.collection_list.selection_clear(0, tk.END)
        self.selected_indices.clear()
        # Clear metadata fields
        for var in self.metadata_vars.values():
            var.set("")
        self.cover_var.set("")
        # Reset tag checkboxes
        for var in self.genre_vars.values():
            var.set(False)
        self.episodic_var.set(False)

    def remove_collections(self):
        """Remove selected collections from the list"""
        if not self.selected_indices:
            messagebox.showwarning("Warning", "Please select at least one collection to remove!")
            return
            
        # Confirm deletion
        count = len(self.selected_indices)
        if messagebox.askyesno("Confirm Remove", 
                              f"Are you sure you want to remove {count} collection(s)?\n\nThis action cannot be undone."):
            # Sort indices in reverse order to avoid index shifting when deleting
            indices_to_remove = sorted(self.selected_indices, reverse=True)
            
            for idx in indices_to_remove:
                del self.collections[idx]
            
            # Clear selection and refresh
            self.selected_indices.clear()
            self.refresh_collection_list()
            
            # Clear metadata fields
            for var in self.metadata_vars.values():
                var.set("")
            self.cover_var.set("")
            
            # Reset tag checkboxes
            for var in self.genre_vars.values():
                var.set(False)
            self.episodic_var.set(False)
            
            messagebox.showinfo("Success", f"Removed {count} collection(s)!")

    def get_available_collection_profiles(self):
        """Scan collections directory and return available collection profile files"""
        profiles = [""]  # Start with empty option (none selected)
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
                    profiles.append(display_name)
                
                # Sort alphabetically (keeping empty option first)
                profiles = [""] + sorted(profiles[1:])
        except Exception as e:
            print(f"Error scanning collections directory: {e}")
        
        return profiles

    def refresh_profile_dropdown(self):
        """Refresh the profile dropdown with current files"""
        available_profiles = self.get_available_collection_profiles()
        self.profile_dropdown.configure(values=available_profiles)
        # Reset selection to empty
        self.quick_profile_var.set("")

    def on_quick_profile_select(self, event=None):
        """Handle selection from the quick profile dropdown"""
        selected = self.quick_profile_var.get().strip()
        if selected:
            # Update the manual entry field and load the profile
            self.profile_var.set(selected)
            self.load_profile()
        # Note: We don't reset the dropdown selection so user can see what's selected

    def load_profile(self):
        """Load profile by name from the profile_var entry field"""
        profile_name = self.profile_var.get().strip()
        if not profile_name:
            messagebox.showwarning("Warning", "Please enter a profile name!")
            return
            
        self._load_profile_by_name(profile_name)

    def load_profile_dialog(self):
        """Load profile using file dialog (original functionality)"""
        profile_file = filedialog.askopenfilename(
            title="Select Collection Profile",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir="."
        )
        if not profile_file:
            return

        try:
            with open(profile_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.collections = data.get("collections", [])
            self.refresh_collection_list()
            # Update profile name in entry (without .json)
            self.profile_var.set(Path(profile_file).stem)
            messagebox.showinfo("Success", f"Loaded: {Path(profile_file).name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load profile:\n{str(e)}")

    def _load_profile_by_name(self, profile_name):
        """Load profile by name from collections directory"""
        try:
            # Remove .json extension if provided
            if profile_name.endswith(".json"):
                profile_name = profile_name[:-5]
            
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
                    self.collections = data.get("collections", [])
                self.refresh_collection_list()
                self.current_profile = profile_name
                messagebox.showinfo("Success", f"Loaded profile: {profile_name}.json")
            else:
                messagebox.showerror("Error", f"Profile not found: {profile_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load profile:\n{str(e)}")

    def save_as_profile(self):
        """Save collections to a new profile"""
        profile_name = self.profile_var.get().strip()
        if not profile_name:
            messagebox.showwarning("Warning", "Please enter a profile name!")
            return
            
        # Remove .json extension if provided  
        if profile_name.endswith(".json"):
            profile_name = profile_name[:-5]
        
        # Remove collections_ prefix if provided (we'll add it back)
        if profile_name.startswith("collections_"):
            profile_name = profile_name[12:]
            
        old_profile = self.current_profile
        self.current_profile = profile_name  # Store without prefix
        self.save_collections()  # This will add the prefix automatically
        self.current_profile = old_profile  # Keep working on current profile
        messagebox.showinfo("Success", f"Saved as profile: collections_{profile_name}.json")
    
    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select Video Folder")
        if folder:
            self.folder_path.set(folder)

    def load_video_info(self):
        db_file = filedialog.askopenfilename(
            title="Select Video Metadata Database",
            filetypes=[("INI files", "*.ini"), ("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not db_file:
            return

        try:
            file_path = Path(db_file)
            file_extension = file_path.suffix.lower()
            
            if file_extension == '.ini':
                self._load_ini_video_info(db_file)
            elif file_extension == '.json':
                self._load_json_video_info(db_file)
            else:
                # Try to detect format by content
                with open(db_file, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('[') and first_line.endswith(']'):
                        self._load_ini_video_info(db_file)
                    else:
                        self._load_json_video_info(db_file)
                
            messagebox.showinfo(
                "Success",
                f"Loaded metadata from {Path(db_file).name}!\n\nSelect one or more videos and click 'Update Collection(s)' to apply the metadata."
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load metadata:\n{str(e)}")
            self.video_database = {}

    def _load_json_video_info(self, db_file):
        """Load video info from JSON file (existing functionality)"""
        with open(db_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Handle both direct database and collections format
            if "collections" in data:
                # Create a lookup by video path for better matching
                self.video_database = {}
                for item in data["collections"]:
                    # Store by ID for direct lookup
                    self.video_database[item["id"]] = item
                    
                    # Also create path-based lookups for each video
                    for video in item.get("videos", []):
                        path = self.normalize_path(video.get("path", ""))
                        if path:
                            self.video_database[path] = item
            else:
                self.video_database = data

    def _load_ini_video_info(self, db_file):
        """Load video info from INI file"""
        import configparser
        
        config = configparser.ConfigParser()
        config.read(db_file, encoding='utf-8')
        
        self.video_database = {}
        
        for section_name in config.sections():
            if section_name.startswith('COLLECTION_'):
                section = config[section_name]
                
                # Parse basic collection info
                collection_data = {
                    "id": section.get('id', ''),
                    "name": section.get('name', ''),
                    "cover": section.get('cover', '') or None,
                    "description": section.get('description', ''),
                    "genre": [g.strip() for g in section.get('genre', '').split(',') if g.strip()],
                    "rating": section.get('rating', 'NR'),
                    "year": section.getint('year', fallback=2026),
                    "videos": []
                }
                
                # Parse videos (video_1_path, video_1_duration, video_2_path, etc.)
                video_num = 1
                while True:
                    path_key = f'video_{video_num}_path'
                    duration_key = f'video_{video_num}_duration'
                    
                    if path_key not in section:
                        break
                        
                    video_path = section.get(path_key, '')
                    video_duration = section.getfloat(duration_key, fallback=5400.0)
                    
                    if video_path:
                        collection_data["videos"].append({
                            "path": video_path,
                            "duration": video_duration
                        })
                    
                    video_num += 1
                
                # Store by ID for direct lookup
                if collection_data["id"]:
                    self.video_database[collection_data["id"]] = collection_data
                    
                    # Also create path-based lookups for each video
                    for video in collection_data["videos"]:
                        path = self.normalize_path(video.get("path", ""))
                        if path:
                            self.video_database[path] = collection_data

    def get_video_duration(self, video_path):
        """Get video duration in seconds"""
        try:
            result = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration", "-of", "csv=p=0",
                str(video_path)
            ], capture_output=True, text=True, check=True, timeout=10)
            return float(result.stdout.strip())
        except:
            return 5400.0  # 90 minutes default

    def generate_id(self, name):
        """Generate collection ID from name, preserving international characters"""
        # Normalize Unicode characters to their basic form
        normalized = unicodedata.normalize('NFKD', name)
        
        # Keep letters (including Cyrillic), numbers, and replace other characters with underscores
        result = []
        for char in normalized.lower():
            if char.isalnum() or char in [' ', '-', '_']:
                # Keep alphanumeric characters and basic separators
                if char == ' ':
                    result.append('_')
                else:
                    result.append(char)
            # Skip diacritics (they appear as combining marks after normalization)
            elif not unicodedata.combining(char):
                # Replace other non-alphanumeric characters with underscores
                result.append('_')
        
        # Join and clean up multiple underscores
        id_str = ''.join(result)
        id_str = re.sub(r'_+', '_', id_str)  # Replace multiple underscores with single
        id_str = id_str.strip('_')  # Remove leading/trailing underscores
        
        return id_str

    def rescan_folder(self):
        folder = self.folder_path.get()
        if not folder or not Path(folder).exists():
            messagebox.showwarning("Warning", "Please select a valid folder first!")
            return

        # Find all video files
        video_files = []
        for ext in [".mp4", ".mkv", ".avi", ".mov", ".webm"]:
            video_files.extend(Path(folder).rglob(f"*{ext}"))

        if not video_files:
            messagebox.showinfo("Info", "No video files found in the selected folder!")
            return

        # Build collections with all required fields
        new_collections = []
        for video_path in video_files:
            video_str = str(video_path.resolve()).replace("\\", "/")
            
            # Generate base name
            stem = video_path.stem
            clean_name = re.sub(r"[.\s]\d{4}[.\s]", " ", stem)
            clean_name = re.sub(r"[.\s](1080p|720p|2160p|4K|BluRay|WEBRip).*", "", clean_name)
            clean_name = re.sub(r"[._]", " ", clean_name)
            clean_name = re.sub(r"\s+", " ", clean_name).strip()
            if not clean_name:
                clean_name = stem

            collection_id = self.generate_id(clean_name)
            cover = self.auto_find_cover(video_path)

            # Include all required fields with default values
            collection = {
                "id": collection_id,
                "name": clean_name,
                "cover": cover,
                "description": "",  # Empty by default
                "genre": [],       # Empty list by default
                "rating": "NR",    # Default rating
                "year": datetime.now().year,  # Default to current year
                "videos": [{
                    "path": video_str,
                    "duration": self.get_video_duration(video_str)
                }]
            }

            new_collections.append(collection)

        self.collections = new_collections
        self.refresh_collection_list()
        messagebox.showinfo("Success", f"Scanned {len(video_files)} videos and created {len(new_collections)} collections!")

    def refresh_collection_list(self):
        """Refresh the collections listbox"""
        self.collection_list.delete(0, tk.END)
        for collection in self.collections:
            self.collection_list.insert(tk.END, collection["name"])

    def on_collection_select(self, event):
        """Handle collection selection"""
        # Clear previous selection
        self.selected_indices.clear()
        
        # Get current selection
        selection = self.collection_list.curselection()
        self.selected_indices = set(selection)
        
        # If exactly one item is selected, populate metadata fields
        if len(selection) == 1:
            idx = selection[0]
            collection = self.collections[idx]
            
            # Populate metadata fields - but don't show defaults for empty fields
            self.metadata_vars["id_var"].set(collection.get("id", ""))
            self.metadata_vars["name_var"].set(collection.get("name", ""))
            self.metadata_vars["cover_var"].set(collection.get("cover", ""))
            
            # Only populate if the field has a value
            if collection.get("description"):
                self.metadata_vars["desc_var"].set(collection["description"])
            else:
                self.metadata_vars["desc_var"].set("")
                
            if collection.get("genre"):
                self.metadata_vars["genre_var"].set(", ".join(collection["genre"]))
            else:
                self.metadata_vars["genre_var"].set("")
                
            if collection.get("rating") and collection["rating"] != "NR":
                self.metadata_vars["rating_var"].set(collection["rating"])
            else:
                self.metadata_vars["rating_var"].set("")
                
            if collection.get("year") and collection["year"] != datetime.now().year:
                self.metadata_vars["year_var"].set(str(collection["year"]))
            else:
                self.metadata_vars["year_var"].set("")
            
            self.cover_var.set(collection.get("cover", ""))
            
            # Update tag checkboxes
            self.update_tag_checkboxes(collection)
        else:
            # Clear metadata fields if multiple or no items selected
            for var in self.metadata_vars.values():
                var.set("")
            self.cover_var.set("")
            
            # Reset tag checkboxes
            for var in self.genre_vars.values():
                var.set(False)
            self.episodic_var.set(False)

    def update_tag_checkboxes(self, collection):
        """Update tag checkboxes based on collection data"""
        # Update genre tags
        collection_genres = set(collection.get("genre", []))
        for tag, var in self.genre_vars.items():
            var.set(tag in collection_genres)
        
        # Update episodic tag
        self.episodic_var.set(collection.get("episodic", False))

    def toggle_genre_tag(self, tag):
        """Toggle a genre tag for selected videos"""
        if not self.selected_indices:
            messagebox.showwarning("Warning", "Please select at least one video first!")
            self.genre_vars[tag].set(False)
            return
            
        for idx in self.selected_indices:
            collection = self.collections[idx]
            genres = collection.get("genre", [])
            
            if self.genre_vars[tag].get():
                # Add the tag if it's not already there
                if tag not in genres:
                    genres.append(tag)
            else:
                # Remove the tag if it exists
                if tag in genres:
                    genres.remove(tag)
            
            collection["genre"] = genres
            
            # Update the genre field if this is the only selected item
            if len(self.selected_indices) == 1:
                self.metadata_vars["genre_var"].set(", ".join(genres))

    def toggle_episodic_tag(self):
        """Toggle the episodic tag for selected videos"""
        if not self.selected_indices:
            messagebox.showwarning("Warning", "Please select at least one video first!")
            self.episodic_var.set(False)
            return
            
        for idx in self.selected_indices:
            collection = self.collections[idx]
            collection["episodic"] = self.episodic_var.get()

    def update_collections(self):
        """Update selected collections with new metadata from loaded video info"""
        if not self.selected_indices:
            messagebox.showwarning("Warning", "Please select at least one collection first!")
            return
            
        if not hasattr(self, 'video_database') or not self.video_database:
            messagebox.showwarning("Warning", "Please load video info first!")
            return
            
        updated_count = 0
        not_found_count = 0
        
        for idx in self.selected_indices:
            collection = self.collections[idx]
            collection_id = collection.get("id", "")
            
            # Try to find metadata by ID first
            metadata = None
            if collection_id in self.video_database:
                metadata = self.video_database[collection_id]
            else:
                # If ID doesn't match, try to match by video path
                for video in collection.get("videos", []):
                    path = self.normalize_path(video.get("path", ""))
                    if path and path in self.video_database:
                        metadata = self.video_database[path]
                        break
            
            if metadata:
                # Update collection with metadata
                if metadata.get("name"):
                    collection["name"] = metadata["name"]
                    
                if metadata.get("description"):
                    collection["description"] = metadata["description"]
                    
                if metadata.get("genre"):
                    collection["genre"] = metadata["genre"]
                    
                if metadata.get("rating"):
                    collection["rating"] = metadata["rating"]
                    
                if metadata.get("year"):
                    collection["year"] = metadata["year"]
                
                updated_count += 1
            else:
                not_found_count += 1
        
        # Refresh the list to show updated names
        self.refresh_collection_list()
        
        # Update the UI fields for the currently selected item(s)
        if self.selected_indices:
            self.on_collection_select(None)
        
        # Show results
        if updated_count > 0:
            if not_found_count > 0:
                messagebox.showinfo("Update Complete", 
                                  f"Updated {updated_count} collection(s).\n\n{not_found_count} collection(s) had no metadata available.")
            else:
                messagebox.showinfo("Success", f"Updated {updated_count} collection(s) with video metadata!")
        else:
            messagebox.showwarning("Warning", 
                                  "No metadata found for any selected collections.\n\nMake sure you've loaded the correct video info file.")

    def normalize_path(self, p):
        """Normalize path for consistent matching"""
        return str(Path(p).resolve()).replace("\\", "/").lower()

    def normalize_name(self, text: str) -> str:
        return (
            text.lower()
            .replace(".", "_")
            .replace(" ", "_")
            .replace("-", "_")
        )

def launch_collection_wizard():
    root = tk.Tk()
    app = CollectionWizard(root)
    root.mainloop()