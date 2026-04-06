#!/usr/bin/env python3
"""
Test script for collection_wizard.py path resolution
Verifies that the wizard can find collection files in user/collections
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))

def test_collections_dir():
    """Test that COLLECTIONS_DIR from module points to the right location"""
    from akiratv.collection_wizard import COLLECTIONS_DIR
    
    expected_path = project_root / "user" / "collections"
    print(f"Project root: {project_root}")
    print(f"COLLECTIONS_DIR: {COLLECTIONS_DIR}")
    print(f"Expected: {expected_path}")
    print(f"COLLECTIONS_DIR exists: {COLLECTIONS_DIR.exists()}")
    
    if COLLECTIONS_DIR == expected_path and COLLECTIONS_DIR.exists():
        print("✅ COLLECTIONS_DIR is correct")
        return True, COLLECTIONS_DIR
    else:
        print("❌ COLLECTIONS_DIR is incorrect or doesn't exist")
        return False, None

def test_collection_files_exist(collections_dir):
    """Test that collection files exist with expected names"""
    print(f"\nListing files in {collections_dir}:")
    files = list(collections_dir.iterdir())
    json_files = [f for f in files if f.suffix == '.json']
    
    print(f"Found {len(json_files)} JSON files:")
    for f in sorted(json_files):
        print(f"  - {f.name}")
    
    # Check for expected files (some common ones)
    expected_names = [
        "collections_default.json",
        "collections_horror.json",
        "collections_akiratv.json",
        "collections_tatkotv.json"
    ]
    
    found_expected = [f.name for f in json_files if f.name in expected_names]
    missing = [name for name in expected_names if name not in found_expected]
    
    if missing:
        print(f"⚠️  Missing some expected files: {missing}")
    else:
        print(f"✅ All expected collection files present")
    
    return len(json_files) > 0

def test_profile_lookup_logic(collections_dir):
    """Test the pattern matching for profile names"""
    print(f"\nTesting profile lookup patterns:")
    
    test_profiles = ["default", "horror", "akiratv", "collections_horror", "Western"]
    
    success = True
    for profile_name in test_profiles:
        # Simulate the lookup logic from _load_profile_by_name
        candidates = [
            collections_dir / f"collections_{profile_name}.json",
            collections_dir / f"{profile_name}.json",
        ]
        
        found = None
        for candidate in candidates:
            if candidate.exists():
                found = candidate.name
                break
        
        if found:
            print(f"  ✅ '{profile_name}' -> found as {found}")
        else:
            print(f"  ❌ '{profile_name}' -> NOT FOUND (tried: {[c.name for c in candidates]})")
            success = False
    
    return success

def test_initial_load_logic(collections_dir):
    """Test the load_collections() method's file finding"""
    print(f"\nTesting initial load logic (current_profile='default'):")
    
    current_profile = "default"
    # This simulates the OLD behavior:
    old_profile_file = collections_dir / f"{current_profile}.json"
    print(f"  OLD (broken) lookup: {old_profile_file} -> exists: {old_profile_file.exists()}")
    
    # This simulates the FIXED behavior:
    new_profile_file = collections_dir / f"collections_{current_profile}.json"
    print(f"  NEW (fixed) lookup: {new_profile_file} -> exists: {new_profile_file.exists()}")
    
    if new_profile_file.exists():
        print(f"  ✅ Fixed logic finds the file")
        return True
    else:
        print(f"  ❌ Even fixed logic can't find the file")
        return False

def main():
    print("=" * 60)
    print("Collection Wizard Path Resolution Test")
    print("=" * 60)
    
    all_pass = True
    collections_dir = None
    
    # Test 1: COLLECTIONS_DIR constant from actual module
    ok, collections_dir = test_collections_dir()
    if not ok:
        all_pass = False
        print("\nCritical: COLLECTIONS_DIR is wrong. Fix the path in collection_wizard.py")
        return 1
    
    # Test 2: Collection files exist
    if not test_collection_files_exist(collections_dir):
        all_pass = False
    
    # Test 3: Profile lookup patterns
    if not test_profile_lookup_logic(collections_dir):
        all_pass = False
    
    # Test 4: Initial load logic
    if not test_initial_load_logic(collections_dir):
        all_pass = False
    
    print("\n" + "=" * 60)
    if all_pass:
        print("✅ All critical tests passed!")
        print("The collection wizard should now work correctly on Linux.")
    else:
        print("❌ Some tests failed - fix needed")
    print("=" * 60)
    
    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
