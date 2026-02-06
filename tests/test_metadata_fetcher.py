#!/usr/bin/env python3
"""
Simple test for the metadata fetcher module
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from akiratv.metadata_fetcher import MetadataFetcher

def test_metadata_fetcher():
    """Test the metadata fetcher functionality"""
    print("Testing MetadataFetcher...")
    
    # Create fetcher instance
    fetcher = MetadataFetcher()
    
    # Test fallback metadata creation
    print("\n1. Testing fallback metadata creation...")
    result = fetcher.create_fallback_metadata("Akira", 1988, language="english")
    print(f"Title: {result['title']}")
    print(f"Year: {result['release_date']}")
    print(f"Description: {result['overview'][:100]}...")
    print(f"Genres: {[g['name'] for g in result['genres']]}")
    
    # Test Bulgarian fallback
    print("\n2. Testing Bulgarian fallback metadata...")
    result_bg = fetcher.create_fallback_metadata("Akira", 1988, language="bulgarian")
    print(f"Title: {result_bg['title']}")
    print(f"Year: {result_bg['release_date']}")
    print(f"Description: {result_bg['overview'][:100]}...")
    print(f"Genres: {[g['name'] for g in result_bg['genres']]}")
    
    # Test known movie descriptions
    print("\n3. Testing known movie descriptions...")
    desc_en = fetcher.get_known_movie_description("akira", 1988, "english")
    desc_bg = fetcher.get_known_movie_description("akira", 1988, "bulgarian")
    print(f"English description: {desc_en[:100]}...")
    print(f"Bulgarian description: {desc_bg[:100]}...")
    
    print("\n✅ MetadataFetcher tests completed successfully!")

if __name__ == "__main__":
    test_metadata_fetcher()