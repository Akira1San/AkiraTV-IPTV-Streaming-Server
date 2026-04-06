#!/bin/bash
# AkiraTV Simple Scheduler Launcher - MX Linux

set -e

# Get script directory and navigate there
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "   📅 AkiraTV Simple Scheduler"
echo "========================================"
echo

# Auto-activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    echo "✓ Activating virtual environment..."
    source venv/bin/activate
fi

# Verify Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Install with:"
    echo "   sudo apt install python3 python3-venv"
    exit 1
fi

echo "🚀 Launching Simple Scheduler..."
echo

# Run the scheduler (same logic as your .bat)
python3 -c "from akiratv.simple_scheduler import launch_simple_scheduler; launch_simple_scheduler()"

echo
echo "✅ Simple Scheduler closed."
read -p "Press [Enter] to exit..."
