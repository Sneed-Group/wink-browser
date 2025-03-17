"""
Configuration manager for the browser.
"""

import os
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Manages browser configuration settings.
    
    This class handles reading and writing of browser configuration settings,
    including user preferences, browser state, and mode settings.
    """
    
    def __init__(self, private_mode: bool = False):
        """
        Initialize the configuration manager.
        
        Args:
            private_mode: Whether the browser is in private mode
        """
        self.private_mode = private_mode
        self.config_dir = os.path.expanduser("~/.wink_browser")
        self.config_file = os.path.join(self.config_dir, "config.json")
        
        # Default configuration
        self.default_config = {
            "browser": {
                "homepage": "https://www.example.com",
                "search_engine": "Google",
                "search_template": "https://www.google.com/search?q={searchTerms}",
                "enable_javascript": True,
                "enable_images": True,
                "enable_cookies": True,
                "font_size": 16,
                "zoom_level": 1.0
            },
            "privacy": {
                "block_ads": True,
                "block_trackers": True,
                "clear_on_exit": False,
                "do_not_track": True
            },
            "network": {
                "proxy": {
                    "enabled": False,
                    "type": "none",  # "none", "http", "socks"
                    "host": "",
                    "port": 0
                }
            },
            "extensions": {
                "enabled": True
            }
        }
        
        # In-memory configuration (used in private mode)
        self.memory_config = self.default_config.copy()
        
        # Load configuration if not in private mode
        if not self.private_mode:
            self._load_config()
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a configuration value from a section.
        
        Args:
            section: The section name
            key: The configuration key in the section
            default: Default value if key doesn't exist
            
        Returns:
            The configuration value or default
        """
        try:
            # Load the latest config in case it was changed
            if not self.private_mode:
                self._load_config()
                
            if section in self.memory_config and key in self.memory_config[section]:
                return self.memory_config[section][key]
            return default
        except Exception as e:
            logger.error(f"Error getting config value for {section}.{key}: {e}")
            return default
    
    def set(self, section: str, key: str, value: Any) -> None:
        """
        Set a configuration value in a section.
        
        Args:
            section: The section name
            key: The configuration key in the section
            value: The configuration value
        """
        try:
            # Ensure section exists
            if section not in self.memory_config:
                self.memory_config[section] = {}
                
            # Update in-memory config
            self.memory_config[section][key] = value
            
            # Save to disk if not in private mode
            if not self.private_mode:
                self._save_config()
        except Exception as e:
            logger.error(f"Error setting config value for {section}.{key}: {e}")
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value (flat key format).
        
        Args:
            key: The configuration key (format: "section.key")
            default: Default value if key doesn't exist
            
        Returns:
            The configuration value or default
        """
        try:
            if "." in key:
                section, subkey = key.split(".", 1)
                return self.get(section, subkey, default)
            
            # Look for key in all sections
            for section in self.memory_config:
                if key in self.memory_config[section]:
                    return self.memory_config[section][key]
                    
            return default
        except Exception as e:
            logger.error(f"Error getting config value for {key}: {e}")
            return default
    
    def set_config(self, key: str, value: Any) -> None:
        """
        Set a configuration value (flat key format).
        
        Args:
            key: The configuration key (format: "section.key")
            value: The configuration value
        """
        try:
            if "." in key:
                section, subkey = key.split(".", 1)
                self.set(section, subkey, value)
            else:
                # Assume it's in the browser section by default
                self.set("browser", key, value)
        except Exception as e:
            logger.error(f"Error setting config value for {key}: {e}")
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        self.memory_config = self.default_config.copy()
        
        if not self.private_mode:
            self._save_config()
    
    def set_private_mode(self, enabled: bool) -> None:
        """
        Set private browsing mode.
        
        Args:
            enabled: Whether to enable private mode
        """
        if self.private_mode == enabled:
            return
            
        self.private_mode = enabled
        
        if not self.private_mode:
            # Switching from private to normal mode
            self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from disk."""
        try:
            # Create config directory if it doesn't exist
            os.makedirs(self.config_dir, exist_ok=True)
            
            # Load config file if it exists
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    disk_config = json.load(f)
                    
                # Merge with default config to ensure all keys exist
                # We do a deep merge here to preserve nested structures
                self.memory_config = self._deep_merge(self.default_config.copy(), disk_config)
            else:
                # Create default config file
                self.memory_config = self.default_config.copy()
                self._save_config()
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            # Use defaults if there's an error
            self.memory_config = self.default_config.copy()
    
    def _deep_merge(self, target: Dict, source: Dict) -> Dict:
        """
        Deep merge two dictionaries.
        
        Args:
            target: Target dictionary to merge into
            source: Source dictionary to merge from
            
        Returns:
            Merged dictionary
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                # Recursively merge dicts
                self._deep_merge(target[key], value)
            else:
                # Simple assignment for non-dict values
                target[key] = value
        return target
    
    def _save_config(self) -> None:
        """Save configuration to disk."""
        if self.private_mode:
            return
            
        try:
            # Create config directory if it doesn't exist
            os.makedirs(self.config_dir, exist_ok=True)
            
            # Save config to file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory_config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def save(self) -> None:
        """Save configuration to disk (alias for _save_config)."""
        self._save_config()
    
    def import_config(self, file_path: str) -> bool:
        """
        Import configuration from a file.
        
        Args:
            file_path: Path to the configuration file
            
        Returns:
            True if import succeeded, False otherwise
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # Validate imported config
            if not isinstance(imported_config, dict):
                logger.error("Invalid configuration format")
                return False
            
            # Update in-memory config (deep merge)
            self.memory_config = self._deep_merge(self.memory_config, imported_config)
            
            # Save to disk if not in private mode
            if not self.private_mode:
                self._save_config()
                
            return True
        except Exception as e:
            logger.error(f"Error importing configuration: {e}")
            return False
    
    def export_config(self, file_path: str) -> bool:
        """
        Export configuration to a file.
        
        Args:
            file_path: Path to save the configuration
            
        Returns:
            True if export succeeded, False otherwise
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.memory_config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
            return False 