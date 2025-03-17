"""
Profile manager for browser user profiles.
This module handles user profiles, including bookmarks, history, and preferences.
"""

import os
import logging
import json
import time
import shutil
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)

class ProfileManager:
    """
    Profile manager for browser user profiles.
    
    This class handles user profiles, including bookmarks, history, settings,
    and other user-specific data.
    """
    
    def __init__(self, config_manager):
        """
        Initialize the profile manager.
        
        Args:
            config_manager: The configuration manager
        """
        self.config_manager = config_manager
        
        # Profiles directory
        self.profiles_dir = os.path.expanduser("~/.wink_browser/profiles")
        os.makedirs(self.profiles_dir, exist_ok=True)
        
        # Current profile
        self.current_profile = "default"
        
        # Profile data
        self.bookmarks: Dict[str, Dict[str, Any]] = {}
        self.history: List[Dict[str, Any]] = []
        
        # Skip loading data in private mode
        if not self.config_manager.private_mode:
            self._load_profile()
        
        logger.info("Profile manager initialized")
    
    def _load_profile(self) -> None:
        """Load the current profile data."""
        try:
            # Create profile directory if it doesn't exist
            profile_dir = os.path.join(self.profiles_dir, self.current_profile)
            os.makedirs(profile_dir, exist_ok=True)
            
            # Load bookmarks
            bookmarks_file = os.path.join(profile_dir, "bookmarks.json")
            if os.path.exists(bookmarks_file):
                with open(bookmarks_file, 'r', encoding='utf-8') as f:
                    self.bookmarks = json.load(f)
            
            # Load history
            history_file = os.path.join(profile_dir, "history.json")
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            
            logger.info(f"Loaded profile: {self.current_profile} with {len(self.bookmarks)} bookmarks and {len(self.history)} history items")
        except Exception as e:
            logger.error(f"Error loading profile: {e}")
    
    def _save_profile(self) -> None:
        """Save the current profile data."""
        # Skip saving in private mode
        if self.config_manager.private_mode:
            return
            
        try:
            # Create profile directory if it doesn't exist
            profile_dir = os.path.join(self.profiles_dir, self.current_profile)
            os.makedirs(profile_dir, exist_ok=True)
            
            # Save bookmarks
            bookmarks_file = os.path.join(profile_dir, "bookmarks.json")
            with open(bookmarks_file, 'w', encoding='utf-8') as f:
                json.dump(self.bookmarks, f, indent=2)
            
            # Save history
            history_file = os.path.join(profile_dir, "history.json")
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2)
            
            logger.debug(f"Saved profile: {self.current_profile}")
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
    
    def get_profiles(self) -> List[str]:
        """
        Get a list of available profiles.
        
        Returns:
            List of profile names
        """
        try:
            return [d for d in os.listdir(self.profiles_dir) 
                    if os.path.isdir(os.path.join(self.profiles_dir, d))]
        except Exception as e:
            logger.error(f"Error getting profiles: {e}")
            return ["default"]
    
    def create_profile(self, profile_name: str) -> bool:
        """
        Create a new profile.
        
        Args:
            profile_name: Name of the profile to create
            
        Returns:
            True if the profile was created, False otherwise
        """
        try:
            # Skip in private mode
            if self.config_manager.private_mode:
                logger.warning("Cannot create profile in private mode")
                return False
                
            # Check if profile already exists
            if profile_name in self.get_profiles():
                logger.warning(f"Profile {profile_name} already exists")
                return False
            
            # Create profile directory
            profile_dir = os.path.join(self.profiles_dir, profile_name)
            os.makedirs(profile_dir, exist_ok=True)
            
            # Create empty bookmarks file
            bookmarks_file = os.path.join(profile_dir, "bookmarks.json")
            with open(bookmarks_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            
            # Create empty history file
            history_file = os.path.join(profile_dir, "history.json")
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
            
            logger.info(f"Created profile: {profile_name}")
            return True
        except Exception as e:
            logger.error(f"Error creating profile: {e}")
            return False
    
    def delete_profile(self, profile_name: str) -> bool:
        """
        Delete a profile.
        
        Args:
            profile_name: Name of the profile to delete
            
        Returns:
            True if the profile was deleted, False otherwise
        """
        try:
            # Skip in private mode
            if self.config_manager.private_mode:
                logger.warning("Cannot delete profile in private mode")
                return False
                
            # Cannot delete default profile
            if profile_name == "default":
                logger.warning("Cannot delete default profile")
                return False
                
            # Check if profile exists
            if profile_name not in self.get_profiles():
                logger.warning(f"Profile {profile_name} does not exist")
                return False
            
            # Delete profile directory
            profile_dir = os.path.join(self.profiles_dir, profile_name)
            shutil.rmtree(profile_dir)
            
            # If current profile was deleted, switch to default
            if self.current_profile == profile_name:
                self.switch_profile("default")
            
            logger.info(f"Deleted profile: {profile_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting profile: {e}")
            return False
    
    def switch_profile(self, profile_name: str) -> bool:
        """
        Switch to a different profile.
        
        Args:
            profile_name: Name of the profile to switch to
            
        Returns:
            True if the profile was switched, False otherwise
        """
        try:
            # Skip in private mode
            if self.config_manager.private_mode:
                logger.warning("Cannot switch profile in private mode")
                return False
                
            # Check if profile exists
            if profile_name not in self.get_profiles():
                # Create if it doesn't exist
                if not self.create_profile(profile_name):
                    return False
            
            # Save current profile
            self._save_profile()
            
            # Switch profile
            self.current_profile = profile_name
            
            # Load new profile
            self.bookmarks = {}
            self.history = []
            self._load_profile()
            
            logger.info(f"Switched to profile: {profile_name}")
            return True
        except Exception as e:
            logger.error(f"Error switching profile: {e}")
            return False
    
    def add_bookmark(self, url: str, title: str, folder: str = "Bookmarks") -> bool:
        """
        Add a bookmark.
        
        Args:
            url: URL of the bookmark
            title: Title of the bookmark
            folder: Folder to add the bookmark to
            
        Returns:
            True if the bookmark was added, False otherwise
        """
        try:
            # Skip in private mode
            if self.config_manager.private_mode:
                logger.warning("Cannot add bookmark in private mode")
                return False
            
            # Create bookmark
            bookmark = {
                "url": url,
                "title": title,
                "added": int(time.time())
            }
            
            # Create folder if it doesn't exist
            if folder not in self.bookmarks:
                self.bookmarks[folder] = []
            
            # Add bookmark to folder
            self.bookmarks[folder].append(bookmark)
            
            # Save profile
            self._save_profile()
            
            logger.info(f"Added bookmark: {title} ({url}) to {folder}")
            return True
        except Exception as e:
            logger.error(f"Error adding bookmark: {e}")
            return False
    
    def remove_bookmark(self, url: str) -> bool:
        """
        Remove a bookmark.
        
        Args:
            url: URL of the bookmark to remove
            
        Returns:
            True if the bookmark was removed, False otherwise
        """
        try:
            # Skip in private mode
            if self.config_manager.private_mode:
                logger.warning("Cannot remove bookmark in private mode")
                return False
            
            # Find bookmark
            for folder, bookmarks in self.bookmarks.items():
                for i, bookmark in enumerate(bookmarks):
                    if bookmark["url"] == url:
                        # Remove bookmark
                        bookmarks.pop(i)
                        
                        # Save profile
                        self._save_profile()
                        
                        logger.info(f"Removed bookmark: {url} from {folder}")
                        return True
            
            logger.warning(f"Bookmark not found: {url}")
            return False
        except Exception as e:
            logger.error(f"Error removing bookmark: {e}")
            return False
    
    def get_bookmarks(self, folder: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get bookmarks.
        
        Args:
            folder: Folder to get bookmarks from, or None for all folders
            
        Returns:
            Dictionary of folder names to bookmark lists
        """
        if folder:
            return {folder: self.bookmarks.get(folder, [])}
        return self.bookmarks
    
    def add_history_item(self, url: str, title: str) -> bool:
        """
        Add a history item.
        
        Args:
            url: URL of the page
            title: Title of the page
            
        Returns:
            True if the history item was added, False otherwise
        """
        try:
            # Skip in private mode
            if self.config_manager.private_mode:
                return True
            
            # Create history item
            history_item = {
                "url": url,
                "title": title,
                "visited": int(time.time())
            }
            
            # Add to history
            self.history.append(history_item)
            
            # Limit history size to 10000 items
            if len(self.history) > 10000:
                self.history = self.history[-10000:]
            
            # Save profile
            self._save_profile()
            
            logger.debug(f"Added history item: {title} ({url})")
            return True
        except Exception as e:
            logger.error(f"Error adding history item: {e}")
            return False
    
    def get_history(self, limit: int = 100, start_time: Optional[int] = None, end_time: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get history items.
        
        Args:
            limit: Maximum number of items to return
            start_time: Only include items after this time (Unix timestamp)
            end_time: Only include items before this time (Unix timestamp)
            
        Returns:
            List of history items
        """
        # In private mode, return empty list
        if self.config_manager.private_mode:
            return []
        
        try:
            # Filter by time range
            filtered_history = self.history
            
            if start_time:
                filtered_history = [item for item in filtered_history if item["visited"] >= start_time]
            
            if end_time:
                filtered_history = [item for item in filtered_history if item["visited"] <= end_time]
            
            # Sort by visit time (newest first)
            filtered_history.sort(key=lambda item: item["visited"], reverse=True)
            
            # Limit number of items
            return filtered_history[:limit]
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return []
    
    def clear_history(self, start_time: Optional[int] = None, end_time: Optional[int] = None) -> bool:
        """
        Clear history items.
        
        Args:
            start_time: Only clear items after this time (Unix timestamp)
            end_time: Only clear items before this time (Unix timestamp)
            
        Returns:
            True if history was cleared, False otherwise
        """
        try:
            # Skip in private mode
            if self.config_manager.private_mode:
                return True
            
            # If no time range, clear all history
            if start_time is None and end_time is None:
                self.history = []
                logger.info("Cleared all history")
            else:
                # Filter by time range
                if start_time and end_time:
                    self.history = [item for item in self.history 
                                    if item["visited"] < start_time or item["visited"] > end_time]
                    logger.info(f"Cleared history between {start_time} and {end_time}")
                elif start_time:
                    self.history = [item for item in self.history if item["visited"] < start_time]
                    logger.info(f"Cleared history after {start_time}")
                elif end_time:
                    self.history = [item for item in self.history if item["visited"] > end_time]
                    logger.info(f"Cleared history before {end_time}")
            
            # Save profile
            self._save_profile()
            
            return True
        except Exception as e:
            logger.error(f"Error clearing history: {e}")
            return False
    
    def search_history(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search history items.
        
        Args:
            query: Text to search for in URLs and titles
            limit: Maximum number of items to return
            
        Returns:
            List of matching history items
        """
        # In private mode, return empty list
        if self.config_manager.private_mode:
            return []
        
        try:
            # Convert query to lowercase for case-insensitive search
            query = query.lower()
            
            # Search in URLs and titles
            matching_items = []
            for item in self.history:
                if query in item["url"].lower() or query in item["title"].lower():
                    matching_items.append(item)
            
            # Sort by visit time (newest first)
            matching_items.sort(key=lambda item: item["visited"], reverse=True)
            
            # Limit number of items
            return matching_items[:limit]
        except Exception as e:
            logger.error(f"Error searching history: {e}")
            return []
    
    def export_data(self, target_dir: str) -> bool:
        """
        Export profile data to a directory.
        
        Args:
            target_dir: Directory to export data to
            
        Returns:
            True if data was exported, False otherwise
        """
        try:
            # Skip in private mode
            if self.config_manager.private_mode:
                logger.warning("Cannot export data in private mode")
                return False
            
            # Create target directory
            os.makedirs(target_dir, exist_ok=True)
            
            # Export bookmarks
            bookmarks_file = os.path.join(target_dir, "bookmarks.json")
            with open(bookmarks_file, 'w', encoding='utf-8') as f:
                json.dump(self.bookmarks, f, indent=2)
            
            # Export history
            history_file = os.path.join(target_dir, "history.json")
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2)
            
            logger.info(f"Exported data to {target_dir}")
            return True
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return False
    
    def import_data(self, source_dir: str) -> Tuple[bool, bool]:
        """
        Import profile data from a directory.
        
        Args:
            source_dir: Directory to import data from
            
        Returns:
            Tuple of (bookmarks_imported, history_imported)
        """
        try:
            # Skip in private mode
            if self.config_manager.private_mode:
                logger.warning("Cannot import data in private mode")
                return (False, False)
            
            bookmarks_imported = False
            history_imported = False
            
            # Import bookmarks
            bookmarks_file = os.path.join(source_dir, "bookmarks.json")
            if os.path.exists(bookmarks_file):
                with open(bookmarks_file, 'r', encoding='utf-8') as f:
                    imported_bookmarks = json.load(f)
                
                # Validate format
                if isinstance(imported_bookmarks, dict):
                    self.bookmarks = imported_bookmarks
                    bookmarks_imported = True
            
            # Import history
            history_file = os.path.join(source_dir, "history.json")
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    imported_history = json.load(f)
                
                # Validate format
                if isinstance(imported_history, list):
                    self.history = imported_history
                    history_imported = True
            
            # Save profile
            if bookmarks_imported or history_imported:
                self._save_profile()
            
            logger.info(f"Imported data from {source_dir} (bookmarks: {bookmarks_imported}, history: {history_imported})")
            return (bookmarks_imported, history_imported)
        except Exception as e:
            logger.error(f"Error importing data: {e}")
            return (False, False) 