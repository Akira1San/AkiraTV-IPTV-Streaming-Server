#akiratv/utils.py
from pathlib import Path

def find_project_root(marker="user"):
    """
    Find the project root by searching upwards for a directory marker.
    This is more robust than using __file__.parent.parent.
    """
    current = Path(__file__).resolve()
    
    for parent in [current] + list(current.parents):
        if (parent / marker).exists():
            return parent
    
    raise FileNotFoundError(f"Could not find project root with '{marker}' directory.")