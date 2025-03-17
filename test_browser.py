#!/usr/bin/env python3
"""
Test script for debugging the Wink Browser.
This script launches the browser, waits for it to be closed,
checks logs for errors, and can repeat the process.
"""

import os
import sys
import subprocess
import time
import logging
import tkinter as tk
from tkinter import messagebox
import re
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('browser_testing.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def check_logs_for_errors():
    """Check the browser logs for errors and return a summary."""
    log_file = os.path.expanduser("~/.wink_browser/logs/wink_browser.log")
    
    if not os.path.exists(log_file):
        log_file = "wink_browser.log"  # Try the current directory
        if not os.path.exists(log_file):
            return "Log file not found."

    # Patterns to look for in logs
    error_patterns = [
        r"Error",
        r"Exception",
        r"Traceback",
        r"Failed",
        r"overlapping",
        r"overlap",
        r"z-index",
        r"rendering"
    ]
    
    errors = []
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            # Check last 100 lines for errors (or fewer if log is smaller)
            for line in lines[-100:]:
                for pattern in error_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        errors.append(line.strip())
                        break
    except Exception as e:
        return f"Error reading log file: {str(e)}"
    
    if errors:
        return f"Found {len(errors)} errors in logs:\n" + "\n".join(errors)
    else:
        return "No errors found in recent logs."

def activate_venv():
    """Ensure we're running in the virtual environment."""
    # Check if we're already in a virtual environment
    if sys.prefix == sys.base_prefix:
        venv_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv")
        
        if os.name == 'nt':  # Windows
            activate_script = os.path.join(venv_dir, "Scripts", "activate.bat")
            if os.path.exists(activate_script):
                subprocess.call(activate_script, shell=True)
        else:  # Unix-like
            activate_script = os.path.join(venv_dir, "bin", "activate")
            if os.path.exists(activate_script):
                command = f"source {activate_script}"
                subprocess.call(command, shell=True, executable='/bin/bash')
    else:
        logger.info("Already in virtual environment: %s", sys.prefix)

def launch_browser(debug=True, url=None):
    """Launch the browser with given parameters."""
    cmd = [sys.executable, "main.py"]
    
    if debug:
        cmd.append("--debug")
    
    if url:
        cmd.append(url)
    
    logger.info(f"Launching browser with command: {' '.join(cmd)}")
    
    # Launch browser as a separate process
    process = subprocess.Popen(cmd)
    
    return process

def test_browser_iteration():
    """Run a test iteration of launching and testing the browser."""
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    
    # Ensure we're in the virtual environment
    activate_venv()
    
    # First check for any existing errors
    initial_errors = check_logs_for_errors()
    if initial_errors != "No errors found in recent logs.":
        logger.info("Initial log check: %s", initial_errors)
    
    # Launch the browser
    logger.info("Launching browser...")
    browser_process = launch_browser(debug=True, url="https://example.com")
    
    # Show message dialog
    message = "Browser launched. Please test the following:\n\n" + \
              "1. Check if text overlaps with non-text elements\n" + \
              "2. Verify media and images display correctly\n" + \
              "3. Test different types of pages\n\n" + \
              "Close the browser when done testing."
    
    messagebox.showinfo("Testing Instructions", message)
    
    # Wait for the browser process to exit
    logger.info("Waiting for browser to close...")
    try:
        browser_process.wait(timeout=300)  # Wait up to 5 minutes
    except subprocess.TimeoutExpired:
        logger.warning("Browser didn't close within timeout period. Terminating...")
        if os.name == 'nt':  # Windows
            browser_process.terminate()
        else:  # Unix-like
            browser_process.send_signal(signal.SIGTERM)
        browser_process.wait(timeout=10)  # Give it 10 seconds to terminate
    
    # Check logs for errors
    logger.info("Browser closed. Checking logs for errors...")
    errors = check_logs_for_errors()
    
    # Show error summary
    result = messagebox.askyesno(
        "Test Results",
        f"Browser test completed.\n\nLog analysis:\n{errors}\n\nDo you want to run another test iteration?"
    )
    
    root.destroy()
    
    return result

def main():
    """Main test loop."""
    logger.info("Starting browser testing utility")
    
    iteration = 1
    while True:
        logger.info(f"Test iteration {iteration}")
        continue_testing = test_browser_iteration()
        
        if not continue_testing:
            logger.info("Testing completed by user request.")
            break
            
        iteration += 1
    
    logger.info("Browser testing utility finished.")

if __name__ == "__main__":
    main() 