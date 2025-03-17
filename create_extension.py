#!/usr/bin/env python3
"""
Utility script to create a new browser extension for Wink Browser.
"""

import argparse
import logging
import os
import sys

from browser_engine.utils.config import Config
from browser_engine.extensions.manager import ExtensionManager
from browser_engine.extensions.extension_helper import ExtensionHelper

def setup_logging():
    """Set up logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger(__name__)

def main():
    """Main entry point for the extension creator utility."""
    logger = setup_logging()
    
    parser = argparse.ArgumentParser(description="Create a new extension for Wink Browser")
    parser.add_argument("name", help="Name of the extension (used for directory name)")
    parser.add_argument("--desc", dest="description", default="", help="Extension description")
    parser.add_argument("--dir", dest="extensions_dir", help="Directory to create the extension in")
    
    args = parser.parse_args()
    
    # Get configuration
    config = Config()
    
    # Get extensions directory
    if args.extensions_dir:
        extensions_dir = args.extensions_dir
    else:
        extensions_dir = config.get(
            "extensions.directory",
            os.path.join(os.path.expanduser("~"), ".wink_browser", "extensions")
        )
    
    # Create the extensions directory if it doesn't exist
    os.makedirs(extensions_dir, exist_ok=True)
    
    # Create the extension directory
    ext_dir = os.path.join(extensions_dir, args.name)
    
    # Check if the extension already exists
    if os.path.exists(ext_dir):
        logger.error(f"Extension directory already exists: {ext_dir}")
        return 1
    
    # Create the extension
    if ExtensionHelper.create_example_extension(extensions_dir, args.name):
        logger.info(f"Created new extension: {args.name}")
        logger.info(f"Extension directory: {ext_dir}")
        logger.info(f"Edit the files in {ext_dir} to customize your extension")
        return 0
    else:
        logger.error(f"Failed to create extension: {args.name}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 