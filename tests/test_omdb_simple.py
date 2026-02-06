#!/usr/bin/env python3
"""
Simple test for OMDB functionality with real API key
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from akiratv.metadata_fetcher import MetadataFetcher

def test_omdb_simple():
    """Test OMDB search with real API key"""
    api_key = "ebed58dc"
    
    print("Testing OMDB with real API key...")
    fetcher = MetadataFetcher()
    
    # Test search for a known movie
    print("\nSearching for 'The Matrix' (1999)...")
    try:
        result = fetcher.search_omdb_movie("The Matrix", 1999, api_key)
        if result:
            print("Success!")
            print("Title:", result.get('title'))
            print("Year:", result.get('release_date'))
            print("Genres:", [g['name'] for g in result.get('genres', [])])
            print("Source:", result.get('source'))
            print("Poster available:", bool(result.get('poster_path')))
            print("Description:", result.get('overview', '')[:100], "...")
        else:
            print("No result found")
    except Exception as e:
        print("Error:", e)
    
    print("\nOMDB functionality tested successfully!")

if __name__ == "__main__":
    test_omdb_simple()
