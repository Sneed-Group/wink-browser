"""
Wink Browser Engine - A modern, privacy-focused web browser engine in Python.
"""

import os
import sys
import logging

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import utilities
from browser_engine.utils.logging import setup_logging, get_default_log_file

# Set up basic logging
logger = setup_logging(log_file=get_default_log_file())

# Package information
__version__ = "0.1.0"
__author__ = "Wink Browser Team"
__description__ = "A modern, privacy-focused web browser engine in Python"

logger.info(f"Wink Browser Engine v{__version__} initialized") 