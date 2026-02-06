#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from akiratv.metadata_fetcher import MetadataFetcher

def test_translation_to_file():
    """Test that saves output to UTF-8 file"""
    fetcher = MetadataFetcher()
    
    test_titles = [
        "The Terminator",
        "Alien", 
        "The Matrix",
        "Star Wars",
        "Batman",
        "Superman",
        "Unknown Movie"
    ]
    
    output_file = "translation_test_output.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("Testing title translation:\n")
        for title in test_titles:
            translated = fetcher.get_known_movie_title(title, "bulgarian")
            if translated != title:
                f.write(f"Translated: {title} -> {translated}\n")
            else:
                f.write(f"No translation: {title}\n")
        
        f.write("\nTest completed!\n")
    
    print(f"Test output written to {output_file}")
    print("Please check the file for results.")

if __name__ == "__main__":
    test_translation_to_file()
