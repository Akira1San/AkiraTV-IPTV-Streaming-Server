#!/bin/bash
# AkiraTV Collection Wizard Launcher - MX Linux

set -e

# Get script directory and navigate there
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "   🎬 AkiraTV Collection Wizard"
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

echo "🚀 Launching Collection Wizard..."
echo

# Run the wizard (same logic as your .bat)
python3 -c "from akiratv.collection_wizard import launch_collection_wizard; launch_collection_wizard()"

echo
echo "✅ Collection Wizard closed."
read -p "Press [Enter] to exit..."
