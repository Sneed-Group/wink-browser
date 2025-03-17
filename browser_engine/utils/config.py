"""
Configuration utility for the browser.
"""

import logging
import os
import json
from typing import Dict, Any, Optional
import threading

logger = logging.getLogger(__name__)

class Config:
    """Configuration manager for the browser."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the config file
        """
        # Default config path
        if not config_path:
            home_dir = os.path.expanduser("~")
            config_dir = os.path.join(home_dir, ".wink_browser")
            os.makedirs(config_dir, exist_ok=True)
            config_path = os.path.join(config_dir, "config.json")
        
        self.config_path = config_path
        self.config = {}
        self._lock = threading.Lock()
        
        # Load config if it exists
        self.load()
        
        logger.debug(f"Configuration initialized (config_path: {config_path})")
    
    def load(self) -> None:
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    with self._lock:
                        self.config = json.load(f)
                logger.debug(f"Configuration loaded from {self.config_path}")
            else:
                logger.debug(f"Configuration file not found at {self.config_path}, using defaults")
                self._set_defaults()
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self._set_defaults()
    
    def save(self) -> None:
        """Save configuration to file."""
        try:
            with self._lock:
                config_copy = self.config.copy()
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(config_copy, f, indent=4)
            
            logger.debug(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key (can be nested using dots, e.g. 'browser.home_page')
            default: Default value if key doesn't exist
            
        Returns:
            Any: Configuration value or default
        """
        with self._lock:
            # Handle nested keys
            if '.' in key:
                parts = key.split('.')
                config = self.config
                
                for part in parts[:-1]:
                    if part not in config or not isinstance(config[part], dict):
                        return default
                    config = config[part]
                
                return config.get(parts[-1], default)
            else:
                return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key (can be nested using dots, e.g. 'browser.home_page')
            value: Configuration value
        """
        with self._lock:
            # Handle nested keys
            if '.' in key:
                parts = key.split('.')
                config = self.config
                
                for part in parts[:-1]:
                    if part not in config:
                        config[part] = {}
                    if not isinstance(config[part], dict):
                        config[part] = {}
                    config = config[part]
                
                config[parts[-1]] = value
            else:
                self.config[key] = value
    
    def remove(self, key: str) -> bool:
        """
        Remove a configuration value.
        
        Args:
            key: Configuration key
            
        Returns:
            bool: True if key was removed
        """
        with self._lock:
            # Handle nested keys
            if '.' in key:
                parts = key.split('.')
                config = self.config
                
                for part in parts[:-1]:
                    if part not in config or not isinstance(config[part], dict):
                        return False
                    config = config[part]
                
                if parts[-1] in config:
                    del config[parts[-1]]
                    return True
                return False
            else:
                if key in self.config:
                    del self.config[key]
                    return True
                return False
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values.
        
        Returns:
            Dict[str, Any]: Dictionary of all configuration values
        """
        with self._lock:
            return self.config.copy()
    
    def _set_defaults(self) -> None:
        """Set default configuration values."""
        with self._lock:
            self.config = {
                "browser": {
                    "home_page": "https://www.example.com",
                    "search_engine": "Google",
                    "download_dir": os.path.expanduser("~/Downloads"),
                    "startup": "homepage"
                },
                "privacy": {
                    "cookies": "accept_all",
                    "do_not_track": True,
                    "block_trackers": True,
                    "clear_history_on_exit": False,
                    "clear_cache_on_exit": False
                },
                "adblock": {
                    "enabled": True
                },
                "advanced": {
                    "javascript_enabled": True,
                    "javascript_strict": False,
                    "cache_size": 100,
                    "parallel_connections": 8,
                    "timeout": 30,
                    "user_agent": "default"
                }
            }
            
            logger.debug("Default configuration set") 