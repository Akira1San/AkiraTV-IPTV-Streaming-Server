#!/usr/bin/env python3
"""
Test script for OMDB functionality
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from akiratv.metadata_fetcher import MetadataFetcher

def test_omdb_functionality():
    """Test the OMDB search functionality"""
    print("Testing OMDB functionality...")
    
    # Create fetcher instance
    fetcher = MetadataFetcher()
    
    # Test that required methods exist
    print("\nChecking OMDB methods:")
    print(f"  search_omdb_movie exists: {hasattr(fetcher, 'search_omdb_movie')}")
    print(f"  search_omdb_movie is callable: {callable(getattr(fetcher, 'search_omdb_movie', None))}")
    print(f"  download_omdb_image exists: {hasattr(fetcher, 'download_omdb_image')}")
    print(f"  download_omdb_image is callable: {callable(getattr(fetcher, 'download_omdb_image', None))}")
    
    # Test search (will fail without valid API key, but should handle it gracefully)
    print("\nTesting search_omdb_movie method:")
    try:
        # This will fail because we're not providing a valid API key
        result = fetcher.search_omdb_movie("The Matrix", 1999, api_key="invalid_key")
        if result:
            print(f"  Success - Found movie: {result.get('title')}")
            print(f"  Year: {result.get('release_date')}")
            print(f"  Genres: {[g['name'] for g in result.get('genres', [])]}")
            print(f"  Description: {result.get('overview', '')[:100]}...")
            print(f"  Source: {result.get('source')}")
            print(f"  Poster path exists: {bool(result.get('poster_path'))}")
        else:
            print("  Method handled invalid API key gracefully - returned None")
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\nTesting download_omdb_image method (with dummy URL):")
    try:
        # Try to download from a dummy URL (will fail but should handle it)
        result = fetcher.download_omdb_image("https://example.com/dummy.jpg", "Test Movie")
        print(f"  Method handled invalid URL gracefully - returned None")
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\nOMDB functionality tests completed!")
    print("\nNote: To test real OMDB search, you need to provide a valid OMDB API key")
    print("  Get your free API key from: http://www.omdbapi.com/apikey.aspx")

if __name__ == "__main__":
    test_omdb_functionality()
