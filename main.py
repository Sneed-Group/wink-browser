#!/usr/bin/env python3
"""
Wink Browser - A modern, privacy-focused web browser built in Python.
"""

import os
import sys
import argparse
import logging
from browser_engine.utils.logging import setup_logging, get_default_log_file
from browser_engine.utils.config import Config

# Set up logging
logger = setup_logging(log_file=get_default_log_file())

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Wink Browser - A modern, privacy-focused web browser")
    
    parser.add_argument("url", nargs="?", default=None, 
                        help="URL to open on startup")
    
    parser.add_argument("--private", action="store_true", 
                        help="Start in private browsing mode")
    
    parser.add_argument("--debug", action="store_true", 
                        help="Enable debug mode")
    
    parser.add_argument("--config", type=str, default=None,
                        help="Path to custom config file")
    
    parser.add_argument("--version", action="store_true",
                        help="Show version information and exit")
    
    return parser.parse_args()

def main():
    """Main entry point for the browser."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Show version and exit if requested
    if args.version:
        from browser_engine import __version__, __author__, __description__
        print(f"Wink Browser v{__version__}")
        print(f"{__description__}")
        print(f"Author: {__author__}")
        sys.exit(0)
    
    # Set up logging level based on debug flag
    if args.debug:
        logging.getLogger("wink_browser").setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Load configuration
    config = Config(args.config)
    logger.debug("Configuration loaded")
    
    # Import UI components here to avoid circular imports
    try:
        from browser_engine.ui.browser_window import BrowserWindow
    except ImportError as e:
        logger.error(f"Failed to import UI components: {e}")
        print(f"Error: Failed to import UI components: {e}")
        sys.exit(1)
    
    # Create and run the browser window
    try:
        # Initialize browser window
        browser = BrowserWindow(
            private_mode=args.private,
            config=config
        )
        
        # Open URL if provided
        if args.url:
            browser.navigate_to(args.url)
        else:
            # Open homepage from config
            homepage = config.get("general.homepage", "about:blank")
            browser.navigate_to(homepage)
        
        # Start the main loop
        browser.run()
        
    except Exception as e:
        logger.error(f"Error starting browser: {e}", exc_info=True)
        print(f"Error starting browser: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 