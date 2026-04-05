#!/bin/bash

# AkiraTV Linux Launcher
# Runs the AkiraTV UI application

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the project root directory
cd "$SCRIPT_DIR"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed or not in PATH"
    exit 1
fi

# Optional: Check if dependencies are installed (uncomment if needed)
# python3 -m pip install -r requirements.txt

# Run the AkiraTV UI
source venv/bin/activate
python3 -m akiratv