#!/bin/bash
# AkiraTV RAM Disk Manager Launcher
# Simple launcher for the GUI interface

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUI_SCRIPT="$SCRIPT_DIR/setup_ramdisk_gui.py"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3 to use the RAM Disk Manager"
    exit 1
fi

# Check if GUI script exists
if [[ ! -f "$GUI_SCRIPT" ]]; then
    echo "ERROR: GUI script not found at: $GUI_SCRIPT"
    exit 1
fi

# Launch the GUI
exec python3 "$GUI_SCRIPT"
