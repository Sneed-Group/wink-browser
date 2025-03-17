"""
Script to initialize and set up example extensions.
"""

import logging
import os
from typing import Optional
import argparse

from browser_engine.utils.config import Config
from browser_engine.extensions.manager import ExtensionManager
from browser_engine.extensions.extension_helper import ExtensionHelper

logger = logging.getLogger(__name__)

def setup_extensions(extensions_dir: Optional[str] = None, create_examples: bool = True) -> None:
    """
    Set up extensions directory and optionally create example extensions.
    
    Args:
        extensions_dir: Extensions directory path
        create_examples: Whether to create example extensions
    """
    try:
        config = Config()
        
        # Get extensions directory from config if not provided
        if not extensions_dir:
            extensions_dir = config.get(
                "extensions.directory",
                os.path.join(os.path.expanduser("~"), ".wink_browser", "extensions")
            )
        
        # Create the extensions directory if it doesn't exist
        os.makedirs(extensions_dir, exist_ok=True)
        
        logger.info(f"Extensions directory: {extensions_dir}")
        
        # Create example extensions if requested
        if create_examples:
            count = ExtensionHelper.create_all_example_extensions(extensions_dir)
            logger.info(f"Created {count} example extensions")
        
        # Initialize extension manager to verify everything is working
        manager = ExtensionManager(config)
        extensions = manager.get_extensions()
        
        logger.info(f"Loaded {len(extensions)} extensions:")
        for ext_id, ext in extensions.items():
            logger.info(f"  - {ext['name']} (v{ext['version']}): {ext['description']}")
    
    except Exception as e:
        logger.error(f"Error setting up extensions: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up extensions for the Wink browser")
    parser.add_argument("--extensions-dir", help="Path to extensions directory")
    parser.add_argument("--no-examples", action="store_true", help="Don't create example extensions")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    setup_extensions(
        extensions_dir=args.extensions_dir,
        create_examples=not args.no_examples
    ) 