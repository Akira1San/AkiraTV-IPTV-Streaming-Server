
#akiratv/inventory.py
import json
from pathlib import Path
from typing import Dict, Any, Optional

class InventoryManager:
    """
    Manages the video inventory loaded from a JSON file.
    Provides fast lookups for video metadata without needing to run ffprobe.
    """
    def __init__(self, inventory_path: Path):
        self.inventory_path = inventory_path
        self.inventory_data: list[dict] = []
        self.path_lookup: Dict[str, dict] = {}
        self._load_inventory()

    def _load_inventory(self):
        """Loads the inventory from the JSON file and creates a lookup dictionary."""
        if not self.inventory_path.exists():
            # print(f"Inventory file not found at {self.inventory_path}. Metadata lookups will fail.")
            return

        try:
            with open(self.inventory_path, "r", encoding="utf-8") as f:
                self.inventory_data = json.load(f)
            
            # Create a fast lookup dictionary: {normalized_path: metadata}
            for item in self.inventory_data:
                # Normalize path to handle backslashes vs forward slashes consistently
                normalized_path = str(Path(item["path"])).lower()
                self.path_lookup[normalized_path] = item
            
            # print(f"Successfully loaded {len(self.inventory_data)} items from inventory.")

        except Exception as e:
            # print(f"Failed to load inventory from {self.inventory_path}: {e}")
            self.inventory_data = []
            self.path_lookup = {}

    def get_metadata(self, video_path: str) -> Optional[Dict[str, Any]]:
        normalized_path = str(Path(video_path)).lower()
        return self.path_lookup.get(normalized_path)
