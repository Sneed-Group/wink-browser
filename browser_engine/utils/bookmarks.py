"""
Bookmark manager for storing and organizing bookmarks.
"""

import logging
import json
import os
import time
import threading
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class BookmarkManager:
    """Manager for storing and retrieving bookmarks."""
    
    def __init__(self, bookmarks_file: Optional[str] = None):
        """
        Initialize the bookmark manager.
        
        Args:
            bookmarks_file: Path to the bookmarks file
        """
        if not bookmarks_file:
            # Default to ~/.wink_browser/bookmarks.json
            home_dir = os.path.expanduser("~")
            config_dir = os.path.join(home_dir, ".wink_browser")
            
            # Create directory if it doesn't exist
            os.makedirs(config_dir, exist_ok=True)
            
            bookmarks_file = os.path.join(config_dir, "bookmarks.json")
        
        self.bookmarks_file = bookmarks_file
        self._bookmarks = {
            "toolbar": {
                "name": "Bookmarks Toolbar",
                "type": "folder",
                "children": [],
                "date_added": time.time()
            },
            "menu": {
                "name": "Bookmarks Menu",
                "type": "folder",
                "children": [],
                "date_added": time.time()
            },
            "other": {
                "name": "Other Bookmarks",
                "type": "folder",
                "children": [],
                "date_added": time.time()
            }
        }
        self._lock = threading.Lock()
        
        # Load bookmarks from file
        self._load_bookmarks()
        
        logger.debug(f"Bookmark manager initialized (bookmarks_file: {bookmarks_file})")
    
    def _load_bookmarks(self) -> None:
        """Load bookmarks from file."""
        try:
            if os.path.exists(self.bookmarks_file):
                with open(self.bookmarks_file, 'r') as f:
                    loaded_bookmarks = json.load(f)
                
                # Ensure all root folders exist
                for key in ["toolbar", "menu", "other"]:
                    if key not in loaded_bookmarks:
                        loaded_bookmarks[key] = {
                            "name": f"Bookmarks {key.title()}",
                            "type": "folder",
                            "children": [],
                            "date_added": time.time()
                        }
                
                self._bookmarks = loaded_bookmarks
                logger.debug(f"Loaded bookmarks from {self.bookmarks_file}")
            else:
                logger.debug("Bookmarks file does not exist, starting with empty bookmarks")
                self._save_bookmarks()
        except Exception as e:
            logger.error(f"Error loading bookmarks: {e}")
    
    def _save_bookmarks(self) -> None:
        """Save bookmarks to file."""
        try:
            with open(self.bookmarks_file, 'w') as f:
                json.dump(self._bookmarks, f, indent=2)
            
            logger.debug(f"Saved bookmarks to {self.bookmarks_file}")
        except Exception as e:
            logger.error(f"Error saving bookmarks: {e}")
    
    def add_bookmark(self, url: str, title: str, 
                      folder: str = "other", 
                      parent_path: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Add a bookmark.
        
        Args:
            url: Bookmark URL
            title: Bookmark title
            folder: Root folder ("toolbar", "menu", "other")
            parent_path: Path to parent folder (list of folder names)
            
        Returns:
            Dict[str, Any]: The bookmark that was added
        """
        bookmark = {
            "name": title,
            "type": "bookmark",
            "url": url,
            "date_added": time.time()
        }
        
        with self._lock:
            if folder not in self._bookmarks:
                logger.warning(f"Invalid folder: {folder}, using 'other'")
                folder = "other"
            
            if parent_path:
                # Find parent folder
                current = self._bookmarks[folder]
                
                for folder_name in parent_path:
                    found = False
                    
                    for child in current["children"]:
                        if child["type"] == "folder" and child["name"] == folder_name:
                            current = child
                            found = True
                            break
                    
                    if not found:
                        # Create folder if it doesn't exist
                        new_folder = {
                            "name": folder_name,
                            "type": "folder",
                            "children": [],
                            "date_added": time.time()
                        }
                        
                        current["children"].append(new_folder)
                        current = new_folder
                
                # Add bookmark to parent folder
                current["children"].append(bookmark)
            else:
                # Add to root folder
                self._bookmarks[folder]["children"].append(bookmark)
            
            self._save_bookmarks()
        
        logger.debug(f"Added bookmark: {title} ({url})")
        return bookmark
    
    def add_folder(self, name: str, folder: str = "other", 
                    parent_path: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Add a folder.
        
        Args:
            name: Folder name
            folder: Root folder ("toolbar", "menu", "other")
            parent_path: Path to parent folder (list of folder names)
            
        Returns:
            Dict[str, Any]: The folder that was added
        """
        new_folder = {
            "name": name,
            "type": "folder",
            "children": [],
            "date_added": time.time()
        }
        
        with self._lock:
            if folder not in self._bookmarks:
                logger.warning(f"Invalid folder: {folder}, using 'other'")
                folder = "other"
            
            if parent_path:
                # Find parent folder
                current = self._bookmarks[folder]
                
                for folder_name in parent_path:
                    found = False
                    
                    for child in current["children"]:
                        if child["type"] == "folder" and child["name"] == folder_name:
                            current = child
                            found = True
                            break
                    
                    if not found:
                        # Create folder if it doesn't exist
                        parent_folder = {
                            "name": folder_name,
                            "type": "folder",
                            "children": [],
                            "date_added": time.time()
                        }
                        
                        current["children"].append(parent_folder)
                        current = parent_folder
                
                # Add folder to parent folder
                current["children"].append(new_folder)
            else:
                # Add to root folder
                self._bookmarks[folder]["children"].append(new_folder)
            
            self._save_bookmarks()
        
        logger.debug(f"Added folder: {name}")
        return new_folder
    
    def get_bookmarks(self, folder: str = None) -> Dict[str, Any]:
        """
        Get bookmarks.
        
        Args:
            folder: Root folder to get ("toolbar", "menu", "other", or None for all)
            
        Returns:
            Dict[str, Any]: Bookmarks dictionary
        """
        with self._lock:
            if folder:
                if folder not in self._bookmarks:
                    logger.warning(f"Invalid folder: {folder}")
                    return {}
                
                return self._bookmarks[folder].copy()
            else:
                return self._bookmarks.copy()
    
    def get_bookmark_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Find a bookmark by URL.
        
        Args:
            url: URL to find
            
        Returns:
            Optional[Dict[str, Any]]: Bookmark if found, None otherwise
        """
        def find_bookmark(node):
            if node["type"] == "bookmark" and node["url"] == url:
                return node
            
            if node["type"] == "folder":
                for child in node["children"]:
                    result = find_bookmark(child)
                    if result:
                        return result
            
            return None
        
        with self._lock:
            for folder in self._bookmarks.values():
                result = find_bookmark(folder)
                if result:
                    return result.copy()
        
        return None
    
    def get_bookmark_path(self, url: str) -> Optional[List[str]]:
        """
        Find the path to a bookmark.
        
        Args:
            url: URL to find
            
        Returns:
            Optional[List[str]]: Path to bookmark if found, None otherwise
        """
        def find_path(node, current_path):
            if node["type"] == "bookmark" and node["url"] == url:
                return current_path
            
            if node["type"] == "folder":
                for child in node["children"]:
                    path = find_path(child, current_path + [child["name"]])
                    if path:
                        return path
            
            return None
        
        with self._lock:
            for key, folder in self._bookmarks.items():
                path = find_path(folder, [folder["name"]])
                if path:
                    return path
        
        return None
    
    def search_bookmarks(self, query: str) -> List[Dict[str, Any]]:
        """
        Search bookmarks.
        
        Args:
            query: Search query
            
        Returns:
            List[Dict[str, Any]]: List of matching bookmarks
        """
        query = query.lower()
        results = []
        
        def search_node(node, path=[]):
            if node["type"] == "bookmark":
                if query in node["name"].lower() or query in node["url"].lower():
                    # Add path information to the result
                    result = node.copy()
                    result["path"] = path
                    results.append(result)
            elif node["type"] == "folder":
                current_path = path + [node["name"]]
                for child in node["children"]:
                    search_node(child, current_path)
        
        with self._lock:
            for folder in self._bookmarks.values():
                search_node(folder)
        
        return results
    
    def update_bookmark(self, url: str, new_title: Optional[str] = None, 
                         new_url: Optional[str] = None) -> bool:
        """
        Update a bookmark.
        
        Args:
            url: URL of bookmark to update
            new_title: New title (None to leave unchanged)
            new_url: New URL (None to leave unchanged)
            
        Returns:
            bool: True if bookmark was updated
        """
        def update_node(node):
            if node["type"] == "bookmark" and node["url"] == url:
                if new_title:
                    node["name"] = new_title
                if new_url:
                    node["url"] = new_url
                return True
            
            if node["type"] == "folder":
                for child in node["children"]:
                    if update_node(child):
                        return True
            
            return False
        
        with self._lock:
            updated = False
            
            for folder in self._bookmarks.values():
                if update_node(folder):
                    updated = True
                    break
            
            if updated:
                self._save_bookmarks()
                logger.debug(f"Updated bookmark: {url}")
            
            return updated
    
    def move_bookmark(self, url: str, new_folder: str, 
                       new_parent_path: Optional[List[str]] = None) -> bool:
        """
        Move a bookmark to a different folder.
        
        Args:
            url: URL of bookmark to move
            new_folder: New root folder ("toolbar", "menu", "other")
            new_parent_path: New parent folder path
            
        Returns:
            bool: True if bookmark was moved
        """
        bookmark = None
        
        # First, find and remove the bookmark
        def find_and_remove(node):
            if node["type"] == "folder":
                for i, child in enumerate(node["children"]):
                    if child["type"] == "bookmark" and child["url"] == url:
                        # Remove bookmark
                        bookmark = node["children"].pop(i)
                        return bookmark
                
                # Search in child folders
                for child in node["children"]:
                    if child["type"] == "folder":
                        result = find_and_remove(child)
                        if result:
                            return result
            
            return None
        
        with self._lock:
            # Find and remove bookmark
            for folder in self._bookmarks.values():
                bookmark = find_and_remove(folder)
                if bookmark:
                    break
            
            if not bookmark:
                logger.warning(f"Bookmark not found: {url}")
                return False
            
            # Check if destination folder is valid
            if new_folder not in self._bookmarks:
                logger.warning(f"Invalid folder: {new_folder}")
                return False
            
            # Add bookmark to new location
            if new_parent_path:
                # Find parent folder
                current = self._bookmarks[new_folder]
                
                for folder_name in new_parent_path:
                    found = False
                    
                    for child in current["children"]:
                        if child["type"] == "folder" and child["name"] == folder_name:
                            current = child
                            found = True
                            break
                    
                    if not found:
                        # Create folder if it doesn't exist
                        new_folder_obj = {
                            "name": folder_name,
                            "type": "folder",
                            "children": [],
                            "date_added": time.time()
                        }
                        
                        current["children"].append(new_folder_obj)
                        current = new_folder_obj
                
                # Add bookmark to parent folder
                current["children"].append(bookmark)
            else:
                # Add to root folder
                self._bookmarks[new_folder]["children"].append(bookmark)
            
            self._save_bookmarks()
            logger.debug(f"Moved bookmark: {url}")
            return True
    
    def delete_bookmark(self, url: str) -> bool:
        """
        Delete a bookmark.
        
        Args:
            url: URL of bookmark to delete
            
        Returns:
            bool: True if bookmark was deleted
        """
        def delete_node(node):
            if node["type"] == "folder":
                for i, child in enumerate(node["children"]):
                    if child["type"] == "bookmark" and child["url"] == url:
                        # Remove bookmark
                        node["children"].pop(i)
                        return True
                
                # Search in child folders
                for child in node["children"]:
                    if child["type"] == "folder":
                        if delete_node(child):
                            return True
            
            return False
        
        with self._lock:
            deleted = False
            
            for folder in self._bookmarks.values():
                if delete_node(folder):
                    deleted = True
                    break
            
            if deleted:
                self._save_bookmarks()
                logger.debug(f"Deleted bookmark: {url}")
            
            return deleted
    
    def delete_folder(self, folder: str, parent_path: Optional[List[str]] = None) -> bool:
        """
        Delete a folder.
        
        Args:
            folder: Name of folder to delete
            parent_path: Path to parent folder
            
        Returns:
            bool: True if folder was deleted
        """
        if not parent_path:
            # Cannot delete root folders
            if folder in self._bookmarks:
                logger.warning("Cannot delete root folders")
                return False
            
            # Try to find folder in root folders
            with self._lock:
                for root_folder in self._bookmarks.values():
                    for i, child in enumerate(root_folder["children"]):
                        if child["type"] == "folder" and child["name"] == folder:
                            root_folder["children"].pop(i)
                            self._save_bookmarks()
                            logger.debug(f"Deleted folder: {folder}")
                            return True
                
                return False
        
        # Find and delete folder
        def delete_folder_node(node, path, index=0):
            if index >= len(path):
                # We've reached the parent of the folder to delete
                for i, child in enumerate(node["children"]):
                    if child["type"] == "folder" and child["name"] == folder:
                        node["children"].pop(i)
                        return True
                
                return False
            
            # Continue traversing path
            for child in node["children"]:
                if child["type"] == "folder" and child["name"] == path[index]:
                    return delete_folder_node(child, path, index + 1)
            
            return False
        
        with self._lock:
            deleted = False
            
            if parent_path:
                root_folder = parent_path[0]
                
                # Find the root folder
                for key, value in self._bookmarks.items():
                    if value["name"] == root_folder:
                        deleted = delete_folder_node(value, parent_path[1:])
                        break
            
            if deleted:
                self._save_bookmarks()
                logger.debug(f"Deleted folder: {folder}")
            
            return deleted
    
    def import_bookmarks(self, bookmarks_json: Dict[str, Any]) -> bool:
        """
        Import bookmarks from a JSON dictionary.
        
        Args:
            bookmarks_json: Bookmarks JSON dictionary
            
        Returns:
            bool: True if bookmarks were imported
        """
        try:
            with self._lock:
                # Merge with existing bookmarks
                for key in ["toolbar", "menu", "other"]:
                    if key in bookmarks_json:
                        self._bookmarks[key]["children"].extend(bookmarks_json[key]["children"])
                
                self._save_bookmarks()
                logger.debug("Imported bookmarks")
                return True
        except Exception as e:
            logger.error(f"Error importing bookmarks: {e}")
            return False
    
    def export_bookmarks(self) -> Dict[str, Any]:
        """
        Export bookmarks as a JSON dictionary.
        
        Returns:
            Dict[str, Any]: Bookmarks JSON dictionary
        """
        with self._lock:
            return self._bookmarks.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get bookmark statistics.
        
        Returns:
            Dict[str, Any]: Statistics about bookmarks
        """
        bookmark_count = 0
        folder_count = 0
        
        def count_nodes(node):
            nonlocal bookmark_count, folder_count
            
            if node["type"] == "folder":
                folder_count += 1
                
                for child in node["children"]:
                    count_nodes(child)
            elif node["type"] == "bookmark":
                bookmark_count += 1
        
        with self._lock:
            for folder in self._bookmarks.values():
                count_nodes(folder)
        
        return {
            "bookmark_count": bookmark_count,
            "folder_count": folder_count
        } 