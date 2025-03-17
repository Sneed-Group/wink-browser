"""
Cache implementation for the browser engine.
This module provides caching functionality for web content, 
resources, and other data needed by the browser.
"""

import os
import json
import time
import hashlib
import logging
import shutil
from typing import Dict, Optional, Any, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class Cache:
    """
    Cache implementation for storing web content and resources.
    
    This class provides methods to cache and retrieve content based on URLs,
    with configurable expiration times and size limits.
    """
    
    def __init__(self, 
                 cache_dir: Optional[str] = None, 
                 max_size_mb: int = 100,
                 default_expiry: int = 3600,  # 1 hour in seconds
                 enabled: bool = True):
        """
        Initialize the cache.
        
        Args:
            cache_dir: Directory to use for caching. If None, a default directory is used.
            max_size_mb: Maximum cache size in megabytes.
            default_expiry: Default expiration time for cached items in seconds.
            enabled: Whether the cache is enabled.
        """
        self.enabled = enabled
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_expiry = default_expiry
        self.cache_dir = cache_dir
        
        # Create default cache directory if not provided
        if not self.cache_dir:
            self.cache_dir = os.path.join(os.path.expanduser("~"), 
                                         ".wink_browser", "cache")
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Create metadata file if it doesn't exist
        self.metadata_file = os.path.join(self.cache_dir, "metadata.json")
        if not os.path.exists(self.metadata_file):
            self._create_metadata()
        
        # Load metadata
        self.metadata = self._load_metadata()
        
        logger.debug(f"Cache initialized at {self.cache_dir} (enabled: {enabled})")
        
        # Cleanup on init if cache is enabled
        if self.enabled:
            self.cleanup()
    
    def _create_metadata(self) -> None:
        """Create a new metadata file."""
        metadata = {
            "version": 1,
            "created": int(time.time()),
            "entries": {},
            "total_size": 0
        }
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f)
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata from disk."""
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error loading cache metadata: {e}")
            self._create_metadata()
            return self._load_metadata()
    
    def _save_metadata(self) -> None:
        """Save cache metadata to disk."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f)
        except Exception as e:
            logger.error(f"Error saving cache metadata: {e}")
    
    def _get_cache_key(self, url: str) -> str:
        """
        Generate a cache key from a URL.
        
        Args:
            url: URL to generate a key for
            
        Returns:
            str: Cache key
        """
        # Use SHA-256 hash of the URL as the key
        return hashlib.sha256(url.encode('utf-8')).hexdigest()
    
    def _get_cache_path(self, key: str) -> str:
        """
        Get the file path for a cache key.
        
        Args:
            key: Cache key
            
        Returns:
            str: Path to the cache file
        """
        return os.path.join(self.cache_dir, key)
    
    def set(self, url: str, content: Union[str, bytes], 
            expiry: Optional[int] = None) -> bool:
        """
        Store content in the cache.
        
        Args:
            url: URL to cache
            content: Content to cache
            expiry: Custom expiration time in seconds
                   (if None, default_expiry is used)
                   
        Returns:
            bool: True if successfully cached, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            key = self._get_cache_key(url)
            cache_path = self._get_cache_path(key)
            
            # Convert to bytes if it's a string
            if isinstance(content, str):
                content_bytes = content.encode('utf-8')
            else:
                content_bytes = content
            
            # Write content to file
            with open(cache_path, 'wb') as f:
                f.write(content_bytes)
            
            # Update metadata
            size = len(content_bytes)
            expires = int(time.time()) + (expiry if expiry is not None else self.default_expiry)
            
            # Determine content type and encoding
            content_type = "text/html"
            encoding = "utf-8"
            
            if isinstance(content, str):
                content_type = "text/html; charset=utf-8"
            else:
                # Try to detect content type for binary data
                try:
                    import magic
                    content_type = magic.from_buffer(content_bytes[:1024], mime=True)
                except ImportError:
                    # If python-magic is not available, make a simple guess based on content
                    if content_bytes.startswith(b'<!DOCTYPE html') or content_bytes.startswith(b'<html'):
                        content_type = "text/html"
                    elif content_bytes.startswith(b'\xff\xd8\xff'):
                        content_type = "image/jpeg"
                    elif content_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
                        content_type = "image/png"
                    elif content_bytes.startswith(b'GIF8'):
                        content_type = "image/gif"
                    elif content_bytes.startswith(b'%PDF'):
                        content_type = "application/pdf"
                    else:
                        content_type = "application/octet-stream"
            
            # Update or add entry in metadata
            if key in self.metadata["entries"]:
                old_size = self.metadata["entries"][key]["size"]
                self.metadata["total_size"] -= old_size
            
            self.metadata["entries"][key] = {
                "url": url,
                "created": int(time.time()),
                "expires": expires,
                "size": size,
                "type": content_type,
                "encoding": encoding if isinstance(content, str) else None
            }
            
            self.metadata["total_size"] += size
            self._save_metadata()
            
            # Perform cleanup if needed
            if self.metadata["total_size"] > self.max_size_bytes:
                self.cleanup()
                
            return True
            
        except Exception as e:
            logger.error(f"Error caching {url}: {e}")
            return False
    
    def get(self, url: str) -> Optional[Union[str, bytes]]:
        """
        Retrieve content from the cache.
        
        Args:
            url: URL to retrieve
            
        Returns:
            Optional[Union[str, bytes]]: Cached content or None if not found or expired
        """
        if not self.enabled:
            return None
        
        try:
            key = self._get_cache_key(url)
            
            # Check if entry exists and is not expired
            if key not in self.metadata["entries"]:
                return None
            
            entry = self.metadata["entries"][key]
            
            # Check if entry is expired
            if entry["expires"] < int(time.time()):
                # Clean up expired entry
                self._remove_entry(key)
                return None
            
            cache_path = self._get_cache_path(key)
            
            # Check if cache file exists
            if not os.path.exists(cache_path):
                # Clean up inconsistent entry
                self._remove_entry(key)
                return None
            
            # Read content from file
            with open(cache_path, 'rb') as f:
                content = f.read()
            
            # Convert to string if it's text content
            if "text/" in entry.get("type", "") or "html" in entry.get("type", "") or "xml" in entry.get("type", ""):
                encoding = entry.get("encoding", "utf-8") or "utf-8"
                try:
                    return content.decode(encoding, errors='replace')
                except UnicodeDecodeError:
                    # If the specified encoding fails, try UTF-8
                    logger.warning(f"Error decoding cache content with {encoding}. Falling back to UTF-8.")
                    return content.decode('utf-8', errors='replace')
            
            return content
            
        except Exception as e:
            logger.error(f"Error retrieving {url} from cache: {e}")
            return None
    
    def _remove_entry(self, key: str) -> None:
        """
        Remove an entry from the cache.
        
        Args:
            key: Cache key to remove
        """
        try:
            if key in self.metadata["entries"]:
                # Update total size
                self.metadata["total_size"] -= self.metadata["entries"][key]["size"]
                
                # Remove file
                cache_path = self._get_cache_path(key)
                if os.path.exists(cache_path):
                    os.remove(cache_path)
                
                # Remove metadata entry
                del self.metadata["entries"][key]
                self._save_metadata()
                
        except Exception as e:
            logger.error(f"Error removing cache entry {key}: {e}")
    
    def remove(self, url: str) -> bool:
        """
        Remove a URL from the cache.
        
        Args:
            url: URL to remove
            
        Returns:
            bool: True if successfully removed, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            key = self._get_cache_key(url)
            self._remove_entry(key)
            return True
            
        except Exception as e:
            logger.error(f"Error removing {url} from cache: {e}")
            return False
    
    def clear(self) -> bool:
        """
        Clear all cached content.
        
        Returns:
            bool: True if successfully cleared, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Remove all files except metadata
            for filename in os.listdir(self.cache_dir):
                if filename != "metadata.json":
                    file_path = os.path.join(self.cache_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
            
            # Reset metadata
            self.metadata["entries"] = {}
            self.metadata["total_size"] = 0
            self._save_metadata()
            
            logger.debug("Cache cleared")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    def cleanup(self) -> None:
        """
        Clean up expired entries and enforce size limits.
        """
        if not self.enabled:
            return
        
        try:
            # Current time
            now = int(time.time())
            
            # 1. Remove expired entries
            expired_keys = [key for key, entry in self.metadata["entries"].items() 
                           if entry["expires"] < now]
            
            for key in expired_keys:
                self._remove_entry(key)
            
            # 2. If still over size limit, remove oldest entries until under limit
            if self.metadata["total_size"] > self.max_size_bytes:
                # Sort entries by creation time
                sorted_entries = sorted(
                    self.metadata["entries"].items(),
                    key=lambda x: x[1]["created"]
                )
                
                # Remove oldest entries until under size limit
                for key, _ in sorted_entries:
                    if self.metadata["total_size"] <= self.max_size_bytes:
                        break
                    self._remove_entry(key)
            
            logger.debug(f"Cache cleanup completed. Current size: {self.metadata['total_size']} bytes")
            
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
    
    def close(self) -> None:
        """
        Close the cache and perform cleanup if needed.
        """
        if self.enabled:
            self._save_metadata()
            logger.debug("Cache closed") 