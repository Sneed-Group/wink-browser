#!/usr/bin/env python3
"""
Main entry point for the Wink Browser.
"""

import argparse
import sys
import logging
import os
from tkinter import messagebox

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("wink_browser.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if all required dependencies are installed."""
    try:
        import tkinter as tk
        import requests
        import bs4
        import PIL
        import yaml
        
        # Check for ffmpeg
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode != 0:
            messagebox.showerror("Dependency Error", "ffmpeg is not installed or not in PATH.")
            sys.exit(1)
            
        return True
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        messagebox.showerror("Dependency Error", f"Missing dependency: {e}\n\nPlease install all dependencies with:\npip install -r requirements.txt")
        return False

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Wink Browser - A privacy-focused web browser')
    parser.add_argument('--url', help='URL to open on startup')
    parser.add_argument('--text-only', action='store_true', help='Start in text-only mode')
    parser.add_argument('--private', action='store_true', help='Start in private browsing mode')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    return parser.parse_args()

def main():
    """Main entry point for the browser."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    try:
        # Import UI components here to avoid circular imports
        from browser_engine.ui.browser_window import BrowserWindow
        from browser_engine.core.engine import BrowserEngine
        from browser_engine.privacy.ad_blocker import AdBlocker
        
        # Initialize ad blocker
        ad_blocker = AdBlocker()
        
        # Initialize the browser engine
        engine = BrowserEngine(
            text_only_mode=args.text_only,
            private_mode=args.private,
            ad_blocker=ad_blocker
        )
        
        # Start the main window
        window = BrowserWindow(engine)
        
        # Load initial URL if provided
        if args.url:
            window.navigate_to(args.url)
        
        # Start the UI main loop
        window.start()
        
    except Exception as e:
        logger.exception(f"Error starting browser: {e}")
        messagebox.showerror("Error", f"Failed to start browser: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 