@echo off
cd /d "%~dp0"
title AkiraTV Collection Wizard
python -c "from akiratv.collection_wizard import launch_collection_wizard; launch_collection_wizard()"
pause