#!/bin/bash
# AkiraTV Web Interface Launcher
# This shell script starts the web UI for AkiraTV

echo "================================================"
echo "   AkiraTV Web Interface Launcher"
echo "================================================"
echo

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "ERROR: Virtual environment not found at: $VENV_DIR"
    echo
    echo "Please create it with: python3 -m venv venv"
    echo "And install dependencies: pip install -r requirements.txt"
    echo
    read -p "Press [Enter] to exit..."
    exit 1
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Check if launch_web.py exists
if [ ! -f "$SCRIPT_DIR/launch_web.py" ]; then
    echo "ERROR: launch_web.py not found!"
    echo
    echo "Make sure you're running this from the project root directory."
    echo "Current directory: $SCRIPT_DIR"
    echo
    read -p "Press [Enter] to exit..."
    exit 1
fi

# Start the web interface
echo "Starting AkiraTV Web Interface..."
echo "Using Python: $(which python)"
echo
python "$SCRIPT_DIR/launch_web.py"

# If Python exits with error, pause so user can see the error
if [ $? -ne 0 ]; then
    echo
    echo "ERROR: Failed to start web interface!"
    echo
    read -p "Press [Enter] to exit..."
fi
