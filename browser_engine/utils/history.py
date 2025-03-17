"""
History manager for tracking browsing history.
"""

import logging
import json
import os
import time
import threading
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class HistoryManager:
    """Manager for tracking and retrieving browsing history."""
    
    def __init__(self, history_file: Optional[str] = None):
        """
        Initialize the history manager.
        
        Args:
            history_file: Path to the history file
        """
        if not history_file:
            # Default to ~/.wink_browser/history.json
            home_dir = os.path.expanduser("~")
            config_dir = os.path.join(home_dir, ".wink_browser")
            
            # Create directory if it doesn't exist
            os.makedirs(config_dir, exist_ok=True)
            
            history_file = os.path.join(config_dir, "history.json")
        
        self.history_file = history_file
        self._history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        
        # Load history from file
        self._load_history()
        
        logger.debug(f"History manager initialized (history_file: {history_file})")
    
    def _load_history(self) -> None:
        """Load history from file."""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    self._history = json.load(f)
                
                logger.debug(f"Loaded {len(self._history)} history entries")
            else:
                logger.debug("History file does not exist, starting with empty history")
                self._history = []
                self._save_history()
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            self._history = []
    
    def _save_history(self) -> None:
        """Save history to file."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self._history, f, indent=2)
            
            logger.debug(f"Saved {len(self._history)} history entries")
        except Exception as e:
            logger.error(f"Error saving history: {e}")
    
    def add_visit(self, url: str, title: str = "", 
                   visit_time: Optional[float] = None) -> Dict[str, Any]:
        """
        Add a URL visit to history.
        
        Args:
            url: URL that was visited
            title: Page title
            visit_time: Visit timestamp (defaults to current time)
            
        Returns:
            Dict[str, Any]: The history entry that was added
        """
        if not visit_time:
            visit_time = time.time()
        
        entry = {
            'url': url,
            'title': title,
            'visit_time': visit_time,
            'visit_date': datetime.fromtimestamp(visit_time).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with self._lock:
            # Check if URL already exists, update if it does
            for i, existing in enumerate(self._history):
                if existing['url'] == url:
                    # Update existing entry
                    self._history[i] = entry
                    self._save_history()
                    logger.debug(f"Updated history entry for: {url}")
                    return entry
            
            # Add new entry
            self._history.append(entry)
            self._save_history()
        
        logger.debug(f"Added history entry for: {url}")
        return entry
    
    def get_history(self, limit: Optional[int] = None, 
                     since: Optional[float] = None,
                     until: Optional[float] = None,
                     search_term: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get browsing history.
        
        Args:
            limit: Maximum number of entries to return
            since: Only return entries after this timestamp
            until: Only return entries before this timestamp
            search_term: Only return entries matching this search term
            
        Returns:
            List[Dict[str, Any]]: List of history entries
        """
        with self._lock:
            # Make a copy of the history
            history = self._history.copy()
        
        # Apply filters
        if since:
            history = [entry for entry in history if entry['visit_time'] >= since]
        
        if until:
            history = [entry for entry in history if entry['visit_time'] <= until]
        
        if search_term:
            search_term = search_term.lower()
            history = [entry for entry in history if
                       search_term in entry['url'].lower() or
                       search_term in entry['title'].lower()]
        
        # Sort by visit time (newest first)
        history.sort(key=lambda entry: entry['visit_time'], reverse=True)
        
        # Apply limit
        if limit:
            history = history[:limit]
        
        return history
    
    def get_today(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get today's browsing history.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List[Dict[str, Any]]: List of history entries
        """
        # Get start of today
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        since = today.timestamp()
        
        return self.get_history(limit=limit, since=since)
    
    def get_yesterday(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get yesterday's browsing history.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List[Dict[str, Any]]: List of history entries
        """
        # Get start of yesterday and today
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        
        since = yesterday.timestamp()
        until = today.timestamp()
        
        return self.get_history(limit=limit, since=since, until=until)
    
    def get_last_week(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get last week's browsing history.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List[Dict[str, Any]]: List of history entries
        """
        # Get start of last week
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        last_week = today - timedelta(days=7)
        
        since = last_week.timestamp()
        
        return self.get_history(limit=limit, since=since)
    
    def get_most_visited(self, limit: int = 10, 
                           since: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Get most visited URLs.
        
        Args:
            limit: Maximum number of entries to return
            since: Only consider entries after this timestamp
            
        Returns:
            List[Dict[str, Any]]: List of history entries with visit count
        """
        with self._lock:
            # Make a copy of the history
            history = self._history.copy()
        
        # Apply time filter
        if since:
            history = [entry for entry in history if entry['visit_time'] >= since]
        
        # Count visits
        url_counts = {}
        for entry in history:
            url = entry['url']
            if url in url_counts:
                url_counts[url]['count'] += 1
                
                # Update if this visit is newer
                if entry['visit_time'] > url_counts[url]['visit_time']:
                    url_counts[url]['visit_time'] = entry['visit_time']
                    url_counts[url]['title'] = entry['title']
            else:
                url_counts[url] = {
                    'url': url,
                    'title': entry['title'],
                    'visit_time': entry['visit_time'],
                    'count': 1
                }
        
        # Convert to list
        most_visited = list(url_counts.values())
        
        # Sort by visit count (highest first)
        most_visited.sort(key=lambda entry: entry['count'], reverse=True)
        
        # Apply limit
        if limit:
            most_visited = most_visited[:limit]
        
        return most_visited
    
    def search(self, query: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search history entries.
        
        Args:
            query: Search query
            limit: Maximum number of entries to return
            
        Returns:
            List[Dict[str, Any]]: List of matching history entries
        """
        return self.get_history(limit=limit, search_term=query)
    
    def delete_entry(self, url: str) -> bool:
        """
        Delete a history entry.
        
        Args:
            url: URL to delete
            
        Returns:
            bool: True if entry was deleted
        """
        with self._lock:
            original_length = len(self._history)
            self._history = [entry for entry in self._history if entry['url'] != url]
            
            if len(self._history) < original_length:
                self._save_history()
                logger.debug(f"Deleted history entry for: {url}")
                return True
        
        logger.debug(f"No history entry found for: {url}")
        return False
    
    def delete_range(self, since: Optional[float] = None, 
                      until: Optional[float] = None) -> int:
        """
        Delete history entries in a time range.
        
        Args:
            since: Delete entries after this timestamp
            until: Delete entries before this timestamp
            
        Returns:
            int: Number of entries deleted
        """
        with self._lock:
            original_length = len(self._history)
            
            if since and until:
                self._history = [entry for entry in self._history 
                               if entry['visit_time'] < since or entry['visit_time'] > until]
            elif since:
                self._history = [entry for entry in self._history if entry['visit_time'] < since]
            elif until:
                self._history = [entry for entry in self._history if entry['visit_time'] > until]
            else:
                # No range specified, don't delete anything
                return 0
            
            num_deleted = original_length - len(self._history)
            
            if num_deleted > 0:
                self._save_history()
                logger.debug(f"Deleted {num_deleted} history entries in range")
            
            return num_deleted
    
    def clear_history(self) -> int:
        """
        Clear all history.
        
        Returns:
            int: Number of entries deleted
        """
        with self._lock:
            num_deleted = len(self._history)
            self._history = []
            self._save_history()
            
            logger.debug(f"Cleared history ({num_deleted} entries deleted)")
            return num_deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get history statistics.
        
        Returns:
            Dict[str, Any]: Statistics about browsing history
        """
        with self._lock:
            # Make a copy of the history
            history = self._history.copy()
        
        # Get time ranges
        now = time.time()
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        yesterday = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)).timestamp()
        last_week = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7)).timestamp()
        last_month = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)).timestamp()
        
        # Count entries in time ranges
        today_count = len([entry for entry in history if entry['visit_time'] >= today])
        yesterday_count = len([entry for entry in history if entry['visit_time'] >= yesterday and entry['visit_time'] < today])
        last_week_count = len([entry for entry in history if entry['visit_time'] >= last_week])
        last_month_count = len([entry for entry in history if entry['visit_time'] >= last_month])
        all_time_count = len(history)
        
        # Get earliest and latest visits
        if history:
            earliest = min(history, key=lambda entry: entry['visit_time'])
            latest = max(history, key=lambda entry: entry['visit_time'])
        else:
            earliest = None
            latest = None
        
        return {
            'total_entries': all_time_count,
            'today_count': today_count,
            'yesterday_count': yesterday_count,
            'last_week_count': last_week_count,
            'last_month_count': last_month_count,
            'earliest_visit': earliest,
            'latest_visit': latest
        } 