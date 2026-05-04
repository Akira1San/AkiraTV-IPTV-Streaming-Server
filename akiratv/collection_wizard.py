# akiratv/collection_wizard.py (updated with profiles and online metadata)
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import re
from pathlib import Path
from datetime import datetime
import subprocess
import unicodedata
import configparser
from threading import Thread
import time
from .metadata_fetcher import MetadataFetcher

COLLECTIONS_DIR = Path(__file__).resolve().parent.parent / "user" / "collections"
COVERS_DIR = Path(__file__).parent.parent / "user" / "covers"
COLLECTIONS_DIR.mkdir(parents=True, exist_ok=True)  # ensure folder exists
COVERS_DIR.mkdir(parents=True, exist_ok=True)  # ensure folder exists

class CollectionWizard:
    def __init__(self, root):
        self.root = root
        self.root.title("AkiraTV — Collection Manager")
        self.root.geometry("1100x800")  # Increased height for additional fields
        
        # Initialize theme state (default to dark)
        self.current_theme = "dark"
        self.apply_dark_theme()
        
        self.collections = []
        self.video_database = {}
        self.folder_path = tk.StringVar()
        self.current_profile = "default"  # Default profile name (will become collections_default.json)
        
        # Initialize metadata fetcher
        self.metadata_fetcher = MetadataFetcher(COVERS_DIR)
        
        # TMDB API configuration (kept for backward compatibility)
        self.tmdb_api_key = ""  # Will be loaded from config or user input
        self.tmdb_base_url = "https://api.themoviedb.org/3"
        self.tmdb_image_base_url = "https://image.tmdb.org/t/p/w500"
        
        # OMDB API configuration
        self.omdb_api_key = ""  # Will be loaded from config or user input
        
        # Genre tags
        self.genre_tags = ["Action", "Adventure", "Anime", "Comedy", "Drama", "Fantasy",
                          "Horror", "Mystery", "Romance", "Sci-Fi", "Thriller", "Documentary"]

        # Track selected videos for tagging
        self.selected_indices = set()

        # Series/Season fields for episodic content
        self.series_name_var = tk.StringVar()
        self.season_var = tk.IntVar(value=0)

        # Flag to prevent recursive selection events during programmatic selection
        self._suppress_select_event = False

        self.load_tmdb_config()
        self.load_collections()
        self.create_widgets()
    
    def apply_light_theme(self):
        """Apply default light theme (system defaults) to the application"""
        # Create a custom style
        style = ttk.Style()
        
        # Reset to system default theme
        try:
            # Try to use the default theme (varies by platform)
            style.theme_use('default')
        except:
            # Fallback to clam theme if default is not available
            style.theme_use('clam')
        
        # Reset root background to system default
        self.root.configure(bg="")
        
        # Reset all custom style configurations
        style.configure('.')

        # Reset Tkinter widget options to defaults
        self.root.option_add('*Listbox.background', "")
        self.root.option_add('*Listbox.foreground', "")
        self.root.option_add('*Listbox.selectBackground', "")
        self.root.option_add('*Listbox.selectForeground', "")
        self.root.option_add('*Listbox.inactiveSelectBackground', "")
        self.root.option_add('*Listbox.inactiveSelectForeground', "")

        # Reset existing listboxes to system defaults
        if hasattr(self, 'collection_list'):
            self.collection_list.config(selectbackground='', selectforeground='',
                                       inactiveselectbackground='', inactiveselectforeground='')
        if hasattr(self, 'video_list'):
            self.video_list.config(selectbackground='', selectforeground='',
                                  inactiveselectbackground='', inactiveselectforeground='')
        self.root.option_add('*Listbox.borderWidth', "")
        self.root.option_add('*Listbox.relief', "")
        self.root.option_add('*Listbox.font', ("TkDefaultFont", 12))
        
        self.root.option_add('*Text.background', "")
        self.root.option_add('*Text.foreground', "")
        self.root.option_add('*Text.insertBackground', "")
    
    def apply_dark_theme(self):
        """Apply dark theme to the application"""
        # Create a custom style
        style = ttk.Style()
        
        # Configure the main background
        self.root.configure(bg="#2d2d2d")
        
        # Configure style elements
        style.theme_use('clam')  # Use clam theme as base
        
        # Configure colors
        dark_bg = "#2d2d2d"
        darker_bg = "#1a1a1a"
        light_bg = "#3d3d3d"
        text_color = "#ffffff"
        disabled_text = "#808080"
        border_color = "#505050"
        highlight_color = "#4a86e8"
        
        # Configure root window
        style.configure('.', 
                      background=dark_bg, 
                      foreground=text_color,
                      fieldbackground=light_bg,
                      bordercolor=border_color,
                      lightcolor=border_color,
                      darkcolor=border_color)
        
        # Configure buttons
        style.configure('TButton', 
                      background=light_bg,
                      foreground=text_color,
                      borderwidth=1,
                      relief='flat')
        style.map('TButton',
                 background=[('active', highlight_color), ('pressed', darker_bg)],
                 foreground=[('active', 'white'), ('pressed', 'white')])
        
        # Configure labels
        style.configure('TLabel',
                      background=dark_bg,
                      foreground=text_color)
        
        # Configure entries
        style.configure('TEntry',
                      background=light_bg,
                      foreground=text_color,
                      fieldbackground=light_bg,
                      borderwidth=1)
        
        # Configure combobox
        style.configure('TCombobox',
                      background=light_bg,
                      foreground=text_color,
                      fieldbackground=light_bg,
                      borderwidth=1)
        style.map('TCombobox',
                 fieldbackground=[('readonly', light_bg)],
                 selectbackground=[('readonly', highlight_color)],
                 selectforeground=[('readonly', 'white')])
        
        # Configure checkbuttons and radiobuttons
        style.configure('TCheckbutton',
                      background=dark_bg,
                      foreground=text_color)
        style.configure('TRadiobutton',
                      background=dark_bg,
                      foreground=text_color)
        
        # Configure frames
        style.configure('TFrame',
                      background=dark_bg)
        
        # Configure labelframes
        style.configure('TLabelframe',
                      background=dark_bg,
                      foreground=text_color)
        style.configure('TLabelframe.Label',
                      background=dark_bg,
                      foreground=text_color)
        
        # Configure separators
        style.configure('TSeparator',
                      background=border_color)
        
        # Configure scrollbars
        style.configure('Vertical.TScrollbar',
                      background=light_bg,
                      troughcolor=dark_bg,
                      arrowcolor=text_color)
        style.configure('Horizontal.TScrollbar',
                      background=light_bg,
                      troughcolor=dark_bg,
                      arrowcolor=text_color)

        # Configure listbox to keep selection visible even when unfocused
        # This prevents selection from "disappearing" when moving focus to other widgets
        highlight_color = "#4a86e8"
        self.root.option_add('*Listbox.selectBackground', highlight_color)
        self.root.option_add('*Listbox.selectForeground', 'white')
        self.root.option_add('*Listbox.inactiveSelectBackground', highlight_color)
        self.root.option_add('*Listbox.inactiveSelectForeground', 'white')

        # Apply to existing listboxes if they exist
        if hasattr(self, 'collection_list'):
            self.collection_list.config(selectbackground=highlight_color, selectforeground='white',
                                       inactiveselectbackground=highlight_color, inactiveselectforeground='white')
        if hasattr(self, 'video_list'):
            self.video_list.config(selectbackground=highlight_color, selectforeground='white',
                                  inactiveselectbackground=highlight_color, inactiveselectforeground='white')
        
        # Configure listbox
        self.root.option_add('*Listbox.background', light_bg)
        self.root.option_add('*Listbox.foreground', text_color)
        self.root.option_add('*Listbox.selectBackground', highlight_color)
        self.root.option_add('*Listbox.selectForeground', 'white')
        self.root.option_add('*Listbox.borderWidth', 1)
        self.root.option_add('*Listbox.relief', 'flat')
        self.root.option_add('*Listbox.font', ("TkDefaultFont", 12))
        
        # Configure text widget
        self.root.option_add('*Text.background', light_bg)
        self.root.option_add('*Text.foreground', text_color)
        self.root.option_add('*Text.insertBackground', text_color)
        
        # Configure messagebox (note: messagebox styling is limited on some platforms)
    
    def toggle_theme(self):
        """Toggle between light and dark themes"""
        if self.current_theme == "dark":
            self.apply_light_theme()
            self.current_theme = "light"
            self.theme_btn.config(text="[DARK] Dark Mode")
        else:
            self.apply_dark_theme()
            self.current_theme = "dark"
            self.theme_btn.config(text="☀️ Light Mode")
        
        # Refresh video list to update colors
        self.refresh_video_list()

    def load_tmdb_config(self):
        """Load TMDB API key from config file or prompt user"""
        try:
            config_file = Path(__file__).parent.parent / "config.json"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.tmdb_api_key = config.get("tmdb_api_key", "")
                    # Also set the API key in the metadata fetcher
                    if self.tmdb_api_key:
                        self.metadata_fetcher.set_tmdb_api_key(self.tmdb_api_key)
                    # Load OMDB API key
                    self.omdb_api_key = config.get("omdb_api_key", "")
        except:
            pass
        
        # If no API key found, we'll prompt the user when they try to use the feature

    def save_tmdb_config(self):
        """Save TMDB API key to config file"""
        try:
            config_file = Path(__file__).parent.parent / "config.json"
            config = {}
            
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
            
            config["tmdb_api_key"] = self.tmdb_api_key
            config["omdb_api_key"] = self.omdb_api_key
            
            # Also set the API key in the metadata fetcher
            self.metadata_fetcher.set_tmdb_api_key(self.tmdb_api_key)
            
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving TMDB config: {e}")

    def prompt_tmdb_api_key(self):
        """Prompt user for TMDB API key"""
        dialog = tk.Toplevel(self.root)
        dialog.title("TMDB API Key Required")
        dialog.geometry("500x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Apply theme to dialog
        if self.current_theme == "dark":
            dialog.configure(bg="#2d2d2d")
        else:
            dialog.configure(bg="")
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Instructions
        instructions = tk.Text(dialog, wrap=tk.WORD, height=8, width=60)
        instructions.pack(padx=10, pady=10, fill="both", expand=True)
        
        instructions.insert("1.0", """To use online metadata features, you need a free TMDB API key:

1. Go to https://www.themoviedb.org/
2. Create a free account
3. Go to Settings → API
4. Click "Request an API Key" → "Developer"
5. Fill in the application details
6. Copy your API Key (v3 auth) and paste it below

Your API key will be saved for future use.""")
        instructions.config(state="disabled")
        
        # API key entry
        key_frame = ttk.Frame(dialog)
        key_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(key_frame, text="API Key:").pack(side="left")
        key_var = tk.StringVar(value=self.tmdb_api_key)
        key_entry = ttk.Entry(key_frame, textvariable=key_var, width=40, show="*")
        key_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        result = {"api_key": None}
        
        def save_key():
            api_key = key_var.get().strip()
            if api_key:
                self.tmdb_api_key = api_key
                self.save_tmdb_config()
                result["api_key"] = api_key
                dialog.destroy()
            else:
                messagebox.showwarning("Warning", "Please enter a valid API key!")
        
        def cancel():
            dialog.destroy()
        
        ttk.Button(btn_frame, text="Save", command=save_key).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=cancel).pack(side="right")
        
        # Focus on entry
        key_entry.focus()
        
        # Wait for dialog to close
        dialog.wait_window()
        return result["api_key"]

    def prompt_omdb_api_key(self):
        """Prompt user for OMDB API key"""
        dialog = tk.Toplevel(self.root)
        dialog.title("OMDB API Key Required")
        dialog.geometry("500x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Apply theme to dialog
        if self.current_theme == "dark":
            dialog.configure(bg="#2d2d2d")
        else:
            dialog.configure(bg="")
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        ttk.Label(dialog, text="OMDB API Key Required", font=("TkDefaultFont", 14, "bold")).pack(pady=10)
        
        ttk.Label(dialog, text="Please enter your OMDB API key:", wraplength=450).pack(pady=5)
        
        key_frame = ttk.Frame(dialog)
        key_frame.pack(fill="x", padx=20, pady=5)
        
        key_var = tk.StringVar(value=self.omdb_api_key)
        key_entry = ttk.Entry(key_frame, textvariable=key_var, width=50)
        key_entry.pack(fill="x")
        
        ttk.Label(dialog, text="Get your free API key at: http://www.omdbapi.com/apikey.aspx", 
                 foreground="blue", cursor="hand2").pack(pady=5)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        result = {"api_key": None}
        
        def save_key():
            api_key = key_var.get().strip()
            if api_key:
                self.omdb_api_key = api_key
                self.save_tmdb_config()
                result["api_key"] = api_key
                dialog.destroy()
            else:
                messagebox.showwarning("Warning", "Please enter a valid API key!")
        
        def cancel():
            dialog.destroy()
        
        ttk.Button(btn_frame, text="Save", command=save_key).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=cancel).pack(side="right")
        
        # Focus on entry
        key_entry.focus()
        
        # Wait for dialog to close
        dialog.wait_window()
        return result["api_key"]

    def fetch_online_metadata(self):
        """Fetch metadata for selected collections from TMDB or Wikipedia"""
        if not self.selected_indices:
            messagebox.showwarning("Warning", "Please select at least one collection first!")
            return
        
        # Ask user which source to use
        source_dialog = tk.Toplevel(self.root)
        source_dialog.title("Choose Metadata Source & Language")
        source_dialog.geometry("500x500")
        source_dialog.transient(self.root)
        source_dialog.grab_set()
        
        # Apply theme to dialog
        if self.current_theme == "dark":
            source_dialog.configure(bg="#2d2d2d")
        else:
            source_dialog.configure(bg="")
        
        # Center the dialog
        source_dialog.update_idletasks()
        x = (source_dialog.winfo_screenwidth() // 2) - (source_dialog.winfo_width() // 2)
        y = (source_dialog.winfo_screenheight() // 2) - (source_dialog.winfo_height() // 2)
        source_dialog.geometry(f"+{x}+{y}")
        
        ttk.Label(source_dialog, text="Choose metadata source:", font=("TkDefaultFont", 12)).pack(pady=10)
        
        source_var = tk.StringVar(value="imdb")
        
        # IMDb option (recommended)
        imdb_frame = ttk.Frame(source_dialog)
        imdb_frame.pack(fill="x", padx=20, pady=5)
        ttk.Radiobutton(imdb_frame, text="IMDb (Free, No Registration) ⭐", 
                       variable=source_var, value="imdb").pack(side="left")
        
        # Wikipedia option
        wiki_frame = ttk.Frame(source_dialog)
        wiki_frame.pack(fill="x", padx=20, pady=5)
        ttk.Radiobutton(wiki_frame, text="Wikipedia (Free, No Registration)", 
                       variable=source_var, value="wikipedia").pack(side="left")
        
        # TMDB option
        tmdb_frame = ttk.Frame(source_dialog)
        tmdb_frame.pack(fill="x", padx=20, pady=5)
        ttk.Radiobutton(tmdb_frame, text="TMDB (Requires Free API Key)", 
                       variable=source_var, value="tmdb").pack(side="left")
        
        # OMDB option
        omdb_frame = ttk.Frame(source_dialog)
        omdb_frame.pack(fill="x", padx=20, pady=5)
        ttk.Radiobutton(omdb_frame, text="OMDB (Requires Free API Key - omdbapi.com)", 
                       variable=source_var, value="omdb").pack(side="left")
        

        
        # Skip existing metadata option
        ttk.Separator(source_dialog, orient='horizontal').pack(fill="x", padx=20, pady=10)
        skip_frame = ttk.Frame(source_dialog)
        skip_frame.pack(fill="x", padx=20, pady=5)
        skip_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(skip_frame, text="Skip collections with existing metadata", 
                       variable=skip_var).pack(side="left")
        
        # Redownload covers option
        covers_frame = ttk.Frame(source_dialog)
        covers_frame.pack(fill="x", padx=20, pady=5)
        redownload_covers_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(covers_frame, text="Download/update cover images", 
                       variable=redownload_covers_var).pack(side="left")
        
        # Buttons
        btn_frame = ttk.Frame(source_dialog)
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        selected_source = {"value": None}
        selected_language = {"value": None}
        selected_skip = {"value": True}
        selected_redownload_covers = {"value": True}

        def proceed():
            selected_source["value"] = source_var.get()
            selected_skip["value"] = skip_var.get()
            selected_redownload_covers["value"] = redownload_covers_var.get()
            source_dialog.destroy()
        
        def cancel():
            source_dialog.destroy()
        
        ttk.Button(btn_frame, text="Proceed", command=proceed).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=cancel).pack(side="right")
        
        # Wait for dialog to close
        source_dialog.wait_window()
        
        if not selected_source["value"]:
            return
        
        # Check TMDB API key if needed
        if selected_source["value"] == "tmdb" and not self.tmdb_api_key:
            if not self.prompt_tmdb_api_key():
                return
        
        # Check OMDB API key if needed
        if selected_source["value"] == "omdb" and not self.omdb_api_key:
            if not self.prompt_omdb_api_key():
                return
        
        # Show progress dialog
        progress_dialog = tk.Toplevel(self.root)
        progress_dialog.title("Fetching Metadata...")
        progress_dialog.geometry("400x150")
        progress_dialog.transient(self.root)
        progress_dialog.grab_set()
        
        # Center the dialog
        progress_dialog.update_idletasks()
        x = (progress_dialog.winfo_screenwidth() // 2) - (progress_dialog.winfo_width() // 2)
        y = (progress_dialog.winfo_screenheight() // 2) - (progress_dialog.winfo_height() // 2)
        progress_dialog.geometry(f"+{x}+{y}")
        
        progress_label = ttk.Label(progress_dialog, text="Fetching metadata...")
        progress_label.pack(pady=20)
        
        progress_bar = ttk.Progressbar(progress_dialog, mode='determinate')
        progress_bar.pack(fill="x", padx=20, pady=10)
        
        status_label = ttk.Label(progress_dialog, text="")
        status_label.pack(pady=5)
        
        # Process collections in a separate thread
        def process_metadata():
            total_collections = len(self.selected_indices)
            progress_bar.config(maximum=total_collections)
            
            updated_count = 0
            failed_count = 0
            source_name = {"tmdb": "TMDB", "wikipedia": "Wikipedia", "imdb": "IMDb", "omdb": "OMDB"}[selected_source["value"]]
            
            for i, idx in enumerate(self.selected_indices):
                collection = self.collections[idx]
                movie_title = collection.get("name", "")

                # Check if collection already has metadata and skip if enabled
                if selected_skip["value"]:
                    has_metadata = (
                        collection.get("description") and
                        collection.get("genre") and
                        collection.get("year")
                    )
                    if has_metadata:
                        print(f"DEBUG: Skipping {movie_title} - metadata already exists")
                        progress_bar.config(value=i + 1)
                        progress_dialog.update()
                        continue

                # Update status
                status_label.config(text=f"Processing: {movie_title}")
                progress_dialog.update()
                
                # Extract year from title if present - use ORIGINAL title, not cleaned
                original_title = collection.get("name", "")
                year_match = re.search(r'\b(19|20)\d{2}\b', original_title)
                year = int(year_match.group()) if year_match else None

                # Also check the video filename for year if not found in title
                if not year and collection.get("videos"):
                    video_path = collection["videos"][0].get("path", "")
                    filename_year_match = re.search(r'\b(19|20)\d{2}\b', video_path)
                    if filename_year_match:
                        year = int(filename_year_match.group())
                        print(f"DEBUG: Found year {year} in video filename")

                # Use user-entered year from collection if available and not default (2026)
                user_year = collection.get("year")
                if user_year and user_year != datetime.now().year:
                    year = user_year
                    print(f"DEBUG: Using user-entered year: {year}")
                elif year == datetime.now().year:
                    # If extracted year is 2026 (default), treat as no year
                    year = None
                    print(f"DEBUG: No valid year found, searching without year")

                print(f"DEBUG: Using year: {year} for movie: {movie_title}")
                
                # Get search hints if available
                search_hints = collection.get("search_hints")
                if search_hints:
                    print(f"DEBUG: Using search hints: '{search_hints}' for {movie_title}")
 
                # Search for movie data
                movie_data = None
                if selected_source["value"] == "tmdb":
                    movie_data = self.metadata_fetcher.search_tmdb_movie(movie_title, year, search_hints)
                elif selected_source["value"] == "wikipedia":
                    movie_data = self.metadata_fetcher.search_wikipedia_movie(movie_title, year, search_hints)
                elif selected_source["value"] == "imdb":
                    movie_data = self.metadata_fetcher.search_imdb_movie(movie_title, year, search_hints)
                elif selected_source["value"] == "omdb":
                    movie_data = self.metadata_fetcher.search_omdb_movie(movie_title, year, self.omdb_api_key, search_hints)
                
                if movie_data:
                    print(f"DEBUG: Got movie data from {movie_data.get('source', 'unknown source')}")
                    print(f"DEBUG: Selected language: {selected_language['value']}")
                    
                    # Update collection with movie data
                    collection["name"] = movie_data.get("title", movie_title)
                    
                    collection["description"] = movie_data.get("overview", "")
                    
                    # Handle year
                    release_date = movie_data.get("release_date", "")
                    if release_date:
                        try:
                            if selected_source["value"] == "tmdb":
                                collection["year"] = int(release_date[:4])
                            else:  # Wikipedia or IMDb returns year as string
                                collection["year"] = int(release_date)
                        except:
                            collection["year"] = datetime.now().year
                    else:
                        collection["year"] = datetime.now().year
                    
                    # Map genres to our genre list
                    movie_genres = [g["name"] for g in movie_data.get("genres", [])]
                    collection["genre"] = movie_genres
                    
                    # Download image/poster if enabled
                    image_path = movie_data.get("poster_path")
                    if image_path and selected_redownload_covers["value"]:
                        if selected_source["value"] == "tmdb":
                            cover_path = self.metadata_fetcher.download_poster(image_path, collection["name"])
                        elif selected_source["value"] == "wikipedia":
                            cover_path = self.metadata_fetcher.download_wikipedia_image(image_path, collection["name"])
                        elif selected_source["value"] == "imdb":
                            cover_path = self.metadata_fetcher.download_imdb_image(image_path, collection["name"])
                        elif selected_source["value"] == "omdb":
                            cover_path = self.metadata_fetcher.download_omdb_image(image_path, collection["name"])
                        
                        if cover_path:
                            collection["cover"] = cover_path
                    
                    updated_count += 1
                else:
                    failed_count += 1
                
                # Update progress
                progress_bar.config(value=i + 1)
                progress_dialog.update()
                
                # Small delay to be respectful to the APIs/websites
                time.sleep(1.0 if selected_source["value"] == "imdb" else 0.5)  # Longer delay for IMDb
            
            # Close progress dialog
            progress_dialog.destroy()
            
            # Show results
            if updated_count > 0:
                # Refresh the UI and preserve selection
                saved_selection = list(self.selected_indices) if self.selected_indices else []
                self._suppress_select_event = True
                self.refresh_collection_list()
                if saved_selection:
                    for idx in saved_selection:
                        self.collection_list.selection_set(idx)
        self._suppress_select_event = False

        # Populate metadata fields based on stored selection
        self._populate_metadata_fields()

    def _update_collection_list_item(self, idx):
        """Update the displayed text and color for a single collection at index idx.
        
        This is a targeted update that avoids rebuilding the entire list, preserving selection.
        """
        if idx < 0 or idx >= self.collection_list.size():
            return
        collection = self.collections[idx]
        # Check if any video is missing
        has_missing = False
        for video in collection.get("videos", []):
            video_path = video.get("path", "")
            if video_path and not Path(video_path).exists():
                has_missing = True
                break
        display_name = collection.get("name", "")
        if has_missing:
            display_name = f"❌ {display_name}"
        # Replace the item at idx
        self.collection_list.delete(idx)
        self.collection_list.insert(idx, display_name)
        # Update color
        if has_missing:
            self.collection_list.itemconfig(idx, fg="red")
        else:
            normal_color = "white" if self.current_theme == "dark" else "black"
            self.collection_list.itemconfig(idx, fg=normal_color)

    def _populate_metadata_fields(self):
        """Populate metadata fields based on current selection stored in self.selected_indices"""
        print(f"DEBUG: _populate_metadata_fields, selected_indices={self.selected_indices}")
        if len(self.selected_indices) == 1:
            idx = next(iter(self.selected_indices))
            collection = self.collections[idx]
            print(f"DEBUG: Loading collection '{collection.get('name')}' into fields")

            # Populate metadata fields - but don't show defaults for empty fields
            self.metadata_vars["id_var"].set(collection.get("id", ""))
            self.metadata_vars["name_var"].set(collection.get("name", ""))
            self.metadata_vars["cover_var"].set(collection.get("cover", ""))

            # Only populate if the field has a value
            if collection.get("description"):
                self.metadata_vars["desc_var"].set(collection["description"])
            else:
                self.metadata_vars["desc_var"].set("")

            if collection.get("search_hints"):
                self.metadata_vars["search_hints_var"].set(collection["search_hints"])
            else:
                self.metadata_vars["search_hints_var"].set("")

            if collection.get("genre"):
                self.metadata_vars["genre_var"].set(", ".join(collection["genre"]))
            else:
                self.metadata_vars["genre_var"].set("")

            # Extract series_name and season from tags, and build display tag list
            tags = collection.get("tags", [])
            series_name = ""
            season_val = 0
            display_tags = []

            for tag in tags:
                if tag.startswith("Series: "):
                    series_name = tag[8:]  # Remove "Series: " prefix
                elif tag.startswith("Season: "):
                    try:
                        season_val = int(tag[8:])  # Remove "Season: " prefix
                    except ValueError:
                        pass
                else:
                    display_tags.append(tag)

            # Set series/season fields
            self.series_name_var.set(series_name)
            self.season_var.set(season_val)

            # Set tags display field (excluding Series/Season tags)
            self.metadata_vars["tags_var"].set(", ".join(display_tags))

            if collection.get("year") and collection["year"] != datetime.now().year:
                self.metadata_vars["year_var"].set(str(collection["year"]))
            else:
                self.metadata_vars["year_var"].set("")

            self.cover_var.set(collection.get("cover", ""))

            # Update cover preview
            self.display_cover_preview(collection.get("cover", ""))

            # Update tag checkboxes
            self.update_tag_checkboxes(collection)

            # Refresh the video list
            self.refresh_video_list()
        else:
            # Clear metadata fields if multiple or no items selected
            print("DEBUG: Clearing metadata fields (multiple/no selection)")
            for var in self.metadata_vars.values():
                var.set("")
            self.cover_var.set("")

            # Clear cover preview
            self.cover_preview.configure(image="")

            # Reset tag checkboxes
            for var in self.genre_vars.values():
                var.set(False)
            self.episodic_var.set(False)

            # Clear series/season fields
            self.series_name_var.set("")
            self.season_var.set(0)

            # Refresh the video list
            self.refresh_video_list()

    def update_tag_checkboxes(self, collection):
        """Update tag checkboxes based on collection data"""
        # Get all tags from collection
        tags = set(collection.get("tags", []))
        
        # Update genre tags
        for tag, var in self.genre_vars.items():
            var.set(tag in tags)
        
        # Update actor tags
        for tag, var in self.actor_vars.items():
            var.set(tag in tags)
        
        # Update episodic tag
        self.episodic_var.set("Episodic" in tags)

    def toggle_tag(self, tag):
        """Toggle a tag for selected videos"""
        if not self.selected_indices:
            messagebox.showwarning("Warning", "Please select at least one video first!")
            # Reset the checkbox
            if tag in self.genre_vars:
                self.genre_vars[tag].set(False)
            elif tag in self.actor_vars:
                self.actor_vars[tag].set(False)
            elif tag == "Episodic":
                self.episodic_var.set(False)
            return
        
        for idx in self.selected_indices:
            collection = self.collections[idx]
            tags = collection.get("tags", [])
            
            # Get current state of the tag
            if tag in self.genre_vars:
                is_checked = self.genre_vars[tag].get()
            elif tag in self.actor_vars:
                is_checked = self.actor_vars[tag].get()
            elif tag == "Episodic":
                is_checked = self.episodic_var.get()
            
            if is_checked:
                # Add the tag if it's not already there
                if tag not in tags:
                    tags.append(tag)
            else:
                # Remove the tag if it exists
                if tag in tags:
                    tags.remove(tag)
            
            # Save the tags back to the collection
            collection["tags"] = tags

        # If exactly one collection is selected, update the tags_var to reflect the change
        if len(self.selected_indices) == 1:
            idx = next(iter(self.selected_indices))
            coll = self.collections[idx]
            tags_list = coll.get("tags", [])
            # Sort tags alphabetically for consistent display (case-insensitive)
            tags_sorted = sorted(tags_list, key=lambda x: x.lower())
            self.metadata_vars["tags_var"].set(", ".join(tags_sorted))


    def _extract_series_and_episode(self, filepath):
        """Extract series name, season, and episode number from a video filepath for sorting.

        Returns a tuple (series_name, season_num, episode_num) where series_name is lowercase.
        Files without recognizable episode patterns return ("", 0, 0) so they appear first when sorted.
        """
        import re
        filename = Path(filepath).stem

        # Clean filename: remove common patterns
        # Remove year: (2020), 2020, [2020]
        cleaned = re.sub(r'[\(\[][12]\d{3}[\)\]]', '', filename)
        cleaned = re.sub(r'\b(19|20)\d{2}\b', '', cleaned)

        # Remove quality tags
        quality_patterns = [
            r'1080p', r'720p', r'2160p', r'4k', r'bluray', r'webrip',
            r'hdtv', r'x264', r'x265', r'hevc', r'aac', r'dts'
        ]
        for pattern in quality_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        # Remove common suffixes like "READNFO", "PROPER", "REPACK"
        cleaned = re.sub(r'(readnfo|proper|repack|internal|real|subfix)', '', cleaned, flags=re.IGNORECASE)

        # Remove dots/underscores at boundaries
        cleaned = re.sub(r'^[\._\s]+', '', cleaned)
        cleaned = re.sub(r'[\._\s]+$', '', cleaned)

        # Extract episode info using various patterns
        # Patterns return (series_part, season, episode) via capture groups
        patterns = [
            # S01E02 or s01e02 format
            (r'^(.*?)[sS](\d{1,2})[eE](\d{1,2})$', 1, 2, 3),
            # 1x02 format
            (r'^(.*?)(\d{1,2})x(\d{1,2})$', 1, 2, 3),
            # Episode/ep 20 at end
            (r'^(.*?)(?:episode|ep)[\s\.\-\_]?(\d{1,3})$', 1, None, 2),
            # Part N or Part N of M at end
            (r'^(.*?)(?:part|pt)[\s\.\-\_]?(\d{1,3})(?:\s+of\s+\d+)?$', 1, None, 2),
            # Just a number at the very end (like "My Show 05")
            (r'^(.*?)[\s\.\-\_]+(\d{1,3})$', 1, None, 2),
            # For multi-part episodes like "S01E01-E02" treat first as start
            (r'^(.*?)[sS](\d{1,2})[eE](\d{1,2})[eE]\d+', 1, 2, 3),
        ]

        for pattern, series_grp, season_grp, ep_grp in patterns:
            match = re.search(pattern, cleaned, re.IGNORECASE)
            if match:
                series = match.group(series_grp).strip()
                # Further clean series name
                series = re.sub(r'[\.\-\_]+', ' ', series).strip()
                series = re.sub(r'\s+', ' ', series).strip()
                if not series:
                    series = "unknown"

                # Season: use captured group if season_grp provided and valid, else default 1
                if season_grp is not None and season_grp <= len(match.groups()) and match.group(season_grp):
                    season = int(match.group(season_grp))
                else:
                    season = 1

                # Episode: captured group required
                episode = int(match.group(ep_grp)) if ep_grp <= len(match.groups()) and match.group(ep_grp) else 1

                return (series.lower(), season, episode)

        # No pattern matched - return empty series with zeros to sort to top
        return ("", 0, 0)

    def normalize_name(self, text: str) -> str:
        return (
            text.lower()
            .replace(".", "_")
            .replace(" ", "_")
            .replace("-", "_")
        )

    def _save_ui_fields_to_selected_collections(self):
        """Internal method to save UI field values to selected collection(s

        Called automatically by save_collections() when there are selected items.
        """
        print(f"DEBUG: _save_ui_fields_to_selected_collections for {len(self.selected_indices)} collections")
        for idx in self.selected_indices:
            collection = self.collections[idx]

            # Save editable fields
            name = self.metadata_vars["name_var"].get().strip()
            if name:
                collection["name"] = name

            description = self.metadata_vars["desc_var"].get().strip()
            collection["description"] = description

            search_hints = self.metadata_vars["search_hints_var"].get().strip()
            if search_hints:
                collection["search_hints"] = search_hints
            elif "search_hints" in collection:
                del collection["search_hints"]

            genre_str = self.metadata_vars["genre_var"].get().strip()
            if genre_str:
                collection["genre"] = [g.strip() for g in genre_str.split(",") if g.strip()]
            else:
                collection["genre"] = []

            year_str = self.metadata_vars["year_var"].get().strip()
            if year_str:
                try:
                    year_val = int(year_str)
                    # Only save year if it's not the default 2026
                    if year_val != 2026:
                        collection["year"] = year_val
                    elif "year" in collection:
                        del collection["year"]
                except ValueError:
                    pass
            elif "year" in collection:
                del collection["year"]

            # Remove legacy top-level fields if present (now stored as tags)
            if "series_name" in collection:
                del collection["series_name"]
            if "season" in collection:
                del collection["season"]

            # Series name and season are stored as special tags
            series_name = self.series_name_var.get().strip()
            season_val = self.season_var.get()
            print(f"DEBUG:   Saving collection '{collection.get('name')}': series_name='{series_name}', season={season_val}")

            # Get or build tags list
            if len(self.selected_indices) == 1:
                tags_str = self.metadata_vars["tags_var"].get().strip()
                if tags_str:
                    tags_list = [t.strip() for t in tags_str.split(",") if t.strip()]
                else:
                    tags_list = []
            else:
                # Multiple selection: preserve existing tags, will merge series/season into them
                tags_list = collection.get("tags", [])

            # Remove any existing Series: or Season: tags to avoid duplicates
            tags_list = [t for t in tags_list if not (t.startswith("Series:") or t.startswith("Season:"))]

            # Add new series/season tags
            if series_name:
                tags_list.append(f"Series: {series_name}")
            tags_list.append(f"Season: {season_val}")

            collection["tags"] = tags_list

        # Update display for modified collections to reflect name/tag changes without full refresh
        # This preserves selection and avoids UI flashing
        for idx in self.selected_indices:
            self._update_collection_list_item(idx)

        # NOTE: Do NOT call refresh_collection_list here - it clears selection
        # Only refresh when explicitly needed (e.g., after name changes in save_collections)

def launch_collection_wizard():
    root = tk.Tk()
    app = CollectionWizard(root)
    root.mainloop()
