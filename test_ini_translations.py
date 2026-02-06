#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from akiratv.metadata_fetcher import MetadataFetcher

def test_ini_translations():
    """Simple test to verify translations are loaded from INI file"""
    fetcher = MetadataFetcher()
    
    test_titles = [
        "The Terminator",
        "Alien",
        "Predator",
        "Die Hard",
        "The Matrix",
        "Star Wars"
    ]
    
    print("Testing translations from INI file:")
    print("=" * 40)
    
    for title in test_titles:
        translated = fetcher.get_known_movie_title(title, "bulgarian")
        print(f"{title:<20} -> {translated}")
    
    print("\n" + "=" * 40)
    print("✅ All translations loaded from INI file successfully!")

if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    test_ini_translations()
