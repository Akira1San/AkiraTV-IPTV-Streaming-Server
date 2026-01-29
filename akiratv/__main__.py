# akiratv/__main__.py

# This is the main entry point for the entire AkiraTV package.
# We import the launch_ui function from the new 'main' module inside the 'ui' sub-package.
from .ui.main import launch_ui

if __name__ == "__main__":
    launch_ui()