"""
Utility modules for the browser engine.
"""

# Import key utilities for easy access
from browser_engine.utils.config import Config
from browser_engine.utils.url import URL
from browser_engine.utils.history import HistoryManager
from browser_engine.utils.bookmarks import BookmarkManager
from browser_engine.utils.network import NetworkManager
from browser_engine.utils.download import DownloadManager
from browser_engine.utils.logging import setup_logging, log_exception, PerformanceLogger

__all__ = [
    'Config',
    'URL',
    'HistoryManager',
    'BookmarkManager',
    'NetworkManager',
    'DownloadManager',
    'setup_logging',
    'log_exception',
    'PerformanceLogger',
]
