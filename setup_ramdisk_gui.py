#!/usr/bin/env python3
"""
AkiraTV RAM Disk Manager GUI
Wraps setup_ramdisk.sh with a tkinter interface for Linux systems.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import os
import re
import sys
from pathlib import Path
from queue import Queue, Empty

# ANSI escape sequence regex for stripping colors
ANSI_PATTERN = re.compile(r'\x1b\[[0-9;]*m')

class RamDiskGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AkiraTV RAM Disk Manager")
        self.root.geometry("640x480")
        self.root.resizable(False, False)

        # Check script exists
        self.script_path = Path(__file__).parent / "setup_ramdisk.sh"
        if not self.script_path.exists():
            self.script_path = Path("setup_ramdisk.sh")
            if not self.script_path.exists():
                messagebox.showerror("Error", "setup_ramdisk.sh not found!")
                sys.exit(1)

        # Check pkexec availability
        self.has_pkexec = self.check_pkexec()

        # Queue for thread-safe output updates
        self.output_queue = Queue()

        # Setup UI
        self.setup_ui()

        # Periodic queue processing
        self.process_queue()

        # Initial status check
        self.refresh_status()

    def check_pkexec(self):
        """Check if pkexec is available"""
        try:
            subprocess.run(["which", "pkexec"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def setup_ui(self):
        """Build the user interface"""
        # Main padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Status indicator frame
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        self.status_label = ttk.Label(status_frame, text="Checking...", font=("TkDefaultFont", 10, "bold"))
        self.status_label.grid(row=0, column=0, sticky=tk.W)

        ttk.Button(status_frame, text="Refresh", command=self.refresh_status).grid(row=0, column=1, padx=(10, 0))

        # Size selection frame
        size_frame = ttk.LabelFrame(main_frame, text="RAM Disk Size", padding="10")
        size_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ttk.Label(size_frame, text="Size:").grid(row=0, column=0, padx=(0, 10))

        self.size_var = tk.StringVar(value="512M")
        size_combo = ttk.Combobox(size_frame, textvariable=self.size_var, values=["256M", "512M", "1G", "2G"], state="readonly", width=15)
        size_combo.grid(row=0, column=1)

        # Button frame
        button_frame = ttk.LabelFrame(main_frame, text="Actions", padding="10")
        button_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ttk.Button(button_frame, text="Mount", command=lambda: self.run_command("mount"), width=15).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="Unmount", command=lambda: self.run_command("unmount"), width=15).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(button_frame, text="Make Persistent", command=lambda: self.run_command("persistent"), width=15).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="Remove Persistent", command=lambda: self.run_command("remove"), width=15).grid(row=1, column=1, padx=5, pady=5)

        # Output frame
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding="10")
        output_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0, 10))

        self.output_text = scrolledtext.ScrolledText(output_frame, width=70, height=15, wrap=tk.WORD)
        self.output_text.grid(row=0, column=0, sticky="nsew")

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

    def check_status(self):
        """Check if RAM disk is mounted"""
        try:
            result = subprocess.run([str(self.script_path), "status"], capture_output=True, text=True, timeout=5)
            output = result.stdout + result.stderr
            mounted = "Status: MOUNTED" in output
            return mounted, output
        except Exception as e:
            return False, f"Error checking status: {str(e)}"

    def refresh_status(self):
        """Update status display"""
        mounted, output = self.check_status()
        cleaned_output = self.strip_ansi(output)

        if mounted:
            self.status_label.config(text="● MOUNTED", foreground="green")
        else:
            self.status_label.config(text="○ NOT MOUNTED", foreground="red")

        self.append_output(cleaned_output)

    def strip_ansi(self, text):
        """Remove ANSI color codes from text"""
        return ANSI_PATTERN.sub('', text)

    def append_output(self, text):
        """Append text to output area"""
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)

    def run_command(self, action):
        """Run script command in a separate thread"""
        # Special handling for remove - show warning if mounted
        if action == "remove":
            mounted, _ = self.check_status()
            if mounted:
                if not messagebox.askyesno("Warning", "RAM disk is currently mounted. Removing from fstab will NOT unmount it. Continue?"):
                    return

        size = self.size_var.get()
        thread = threading.Thread(target=self._run_command_thread, args=(size, action), daemon=True)
        thread.start()

    def _run_command_thread(self, size, action):
        """Thread worker for running commands"""
        # Build command
        cmd = [str(self.script_path), size, action]

        # Use pkexec for privileged operations (mount, unmount, persistent, remove)
        # Skip pkexec if already root to avoid double elevation
        if action != "status":
            if os.geteuid() == 0:
                # Already root, run directly
                pass
            elif self.has_pkexec:
                cmd = ["pkexec"] + cmd
            else:
                # Fallback warning - attempt anyway but warn user
                self.output_queue.put(("WARNING", "pkexec not found. If this operation requires root, it will fail. Install polkit or use sudo manually."))

        try:
            self.output_queue.put(("INFO", f"Running: {' '.join(cmd)}\n"))

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Read output line by line
            while True:
                line = process.stdout.readline()
                if line == '' and process.poll() is not None:
                    break
                if line:
                    cleaned = self.strip_ansi(line)
                    self.output_queue.put(("OUTPUT", cleaned.rstrip()))

            return_code = process.poll()

            if return_code == 0:
                self.output_queue.put(("SUCCESS", f"\nCommand completed successfully"))
                if action in ["mount", "unmount", "persistent", "remove"]:
                    self.output_queue.put(("INFO", "\nRefreshing status..."))
                    self.root.after(0, self.refresh_status)
            else:
                self.output_queue.put(("ERROR", f"\nCommand failed with exit code {return_code}"))

        except FileNotFoundError:
            self.output_queue.put(("ERROR", f"Script not found: {self.script_path}"))
        except subprocess.CalledProcessError as e:
            self.output_queue.put(("ERROR", f"Command failed: {e.stderr}"))
        except Exception as e:
            self.output_queue.put(("ERROR", f"Unexpected error: {str(e)}"))

    def process_queue(self):
        """Process queued output messages"""
        try:
            while True:
                msg_type, msg = self.output_queue.get_nowait()

                if msg_type == "WARNING":
                    messagebox.showwarning("Warning", msg)
                elif msg_type == "ERROR":
                    messagebox.showerror("Error", msg)
                elif msg_type == "SUCCESS":
                    self.append_output(msg)
                    messagebox.showinfo("Success", "Operation completed successfully")
                elif msg_type == "INFO":
                    self.append_output(msg)
                elif msg_type == "OUTPUT":
                    self.append_output(msg)

        except Empty:
            pass

        # Schedule next check
        self.root.after(100, self.process_queue)

def main():
    root = tk.Tk()
    app = RamDiskGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()