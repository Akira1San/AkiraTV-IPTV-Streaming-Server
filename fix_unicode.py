
#!/usr/bin/env python3
import os
import re
from pathlib import Path

# Path to the directory containing Python files
BASE_DIR = Path("c:/AkiraTV/AkiraTV_NEW - zai - git - core api - stable/akiratv")

# List of emoji patterns to replace (add more if needed)
EMOJI_PATTERNS = {
    "✅": "[OK]",
    "❌": "[ERROR]",
    "🚀": "[START]",
    "📂": "[DIR]",
    "📖": "[DOC]",
    "🌐": "[WEB]",
    "🔌": "[WS]",
    "📁": "[FOLDER]",
    "📺": "[TV]",
    "🎬": "[PLAY]",
    "🔥": "[HOT]",
    "💾": "[SAVE]",
    "🔄": "[REFRESH]",
    "📋": "[COPY]",
    "🎲": "[RAND]",
    "🌙": "[DARK]",
    "🌍": "[PUBLIC]",
    "🧙‍♂️": "[WIZARD]",
    "📬": "[MSG]",
    "💤": "[STANDBY]",
    "🔍": "[SEARCH]",
    "🚫": "[BLOCK]",
    "🔧": "[CONFIG]",
}

def fix_unicode_encoding():
    """Search and replace emoji characters in Python files"""
    print("Searching for emoji characters in Python files...")
    
    # Find all Python files
    python_files = list(BASE_DIR.rglob("*.py"))
    print(f"Found {len(python_files)} Python files to scan")
    
    modified_files = 0
    
    for file_path in python_files:
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if file contains any emoji
            has_emoji = False
            for emoji in EMOJI_PATTERNS:
                if emoji in content:
                    has_emoji = True
                    break
            
            if not has_emoji:
                continue
            
            # Replace emojis
            original_content = content
            for emoji, replacement in EMOJI_PATTERNS.items():
                content = content.replace(emoji, replacement)
            
            # Write back to file only if changes were made
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                modified_files += 1
                print(f"Modified: {file_path}")
        
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    print(f"\nProcess completed. Modified {modified_files} files.")

if __name__ == "__main__":
    fix_unicode_encoding()
