@echo off
cd /d "%~dp0"
title AkiraTV Simple Scheduler
python -c "from akiratv.simple_scheduler import launch_simple_scheduler; launch_simple_scheduler()"
pause