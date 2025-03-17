"""
Ad blocker implementation.
This module is responsible for blocking ads and trackers.
"""

import logging
import os
import tempfile
import threading
import time
import re
import urllib.request
import urllib.parse
from typing import Dict, List, Optional, Set, Any, Tuple
from pathlib import Path
import hashlib

# For parsing ad block rules
try:
    from adblockparser import AdblockRules
except ImportError:
    logging.warning("adblockparser not available. Ad blocking will be limited.")
    AdblockRules = None

logger = logging.getLogger(__name__)

class AdBlocker:
    """Ad blocker implementation using adblockparser."""
    
    # Default filter lists
    DEFAULT_FILTER_LISTS = {
        "EasyList": "https://easylist.to/easylist/easylist.txt",
        "EasyPrivacy": "https://easylist.to/easylist/easyprivacy.txt",
        "AdGuard Base": "https://filters.adtidy.org/extension/ublock/filters/2_without_easylist.txt",
        "Peter Lowe's List": "https://pgl.yoyo.org/adservers/serverlist.php?hostformat=adblockplus&showintro=0&mimetype=plaintext",
    }
    
    def __init__(self, enabled: bool = True, lists_dir: Optional[str] = None):
        """
        Initialize the ad blocker.
        
        Args:
            enabled: Whether ad blocking is enabled
            lists_dir: Directory to store filter lists
        """
        self.enabled = enabled
        
        # Check if adblockparser is available
        self.adblockparser_available = AdblockRules is not None
        
        # Create lists directory if not provided
        if not lists_dir:
            lists_dir = os.path.join(tempfile.gettempdir(), 'wink_browser', 'blocklists')
        
        # Ensure lists directory exists
        os.makedirs(lists_dir, exist_ok=True)
        self.lists_dir = lists_dir
        
        # Dictionary of filter lists (name -> url)
        self.filter_lists = self.DEFAULT_FILTER_LISTS.copy()
        
        # Set of enabled filter lists
        self.enabled_lists = set(self.DEFAULT_FILTER_LISTS.keys())
        
        # List of custom rules
        self.custom_rules = []
        
        # Compiled rule set
        self.rules = None
        
        # Simple domain blocklist for fallback
        self.blocked_domains = set()
        
        # Cache for blocked URLs
        self.url_cache = {}
        self._lock = threading.Lock()
        
        # Load filter lists if enabled
        if self.enabled:
            self._load_filter_lists()
        
        logger.debug(f"Ad blocker initialized (enabled: {enabled}, lists_dir: {lists_dir})")
    
    def _load_filter_lists(self) -> None:
        """Load and compile filter lists."""
        if not self.enabled:
            return
        
        # Start a background thread to load filter lists
        threading.Thread(target=self._load_filter_lists_thread, daemon=True).start()
    
    def _load_filter_lists_thread(self) -> None:
        """Background thread for loading filter lists."""
        try:
            raw_rules = []
            
            # Process enabled filter lists
            for list_name in self.enabled_lists:
                if list_name in self.filter_lists:
                    list_url = self.filter_lists[list_name]
                    list_path = self._get_list_path(list_name)
                    
                    # Download the list if it doesn't exist or is older than 7 days
                    if self._should_download_list(list_path):
                        self._download_filter_list(list_url, list_path)
                    
                    # Read the list
                    if os.path.exists(list_path):
                        with open(list_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                        
                        # Extract rules
                        for line in lines:
                            line = line.strip()
                            if line and not line.startswith(('!', '[', '#')):
                                # Add to raw rules for processing
                                raw_rules.append(line)
                                
                                # Also extract domain blocks for fallback
                                if self._is_domain_block(line):
                                    domain = self._extract_domain(line)
                                    if domain:
                                        self.blocked_domains.add(domain)
            
            # Add custom rules
            raw_rules.extend(self.custom_rules)
            
            # Compile rules if adblockparser is available
            if self.adblockparser_available and raw_rules:
                try:
                    # Sanitize rules to avoid common parsing errors
                    sanitized_rules = []
                    
                    for rule in raw_rules:
                        try:
                            # Ensure the rule is a string
                            if not isinstance(rule, str):
                                continue
                                
                            # Skip rules that are too long (likely malformed)
                            if len(rule) > 10000:
                                logger.debug(f"Skipping excessively long rule ({len(rule)} chars)")
                                continue
                                
                            # Check for unbalanced parentheses
                            if rule.count('(') != rule.count(')'):
                                # Try to fix unbalanced parentheses by adding closing ones
                                imbalance = rule.count('(') - rule.count(')')
                                if imbalance > 0:
                                    # Add missing closing parentheses
                                    rule = rule + ')' * imbalance
                                elif imbalance < 0:
                                    # Skip rule with too many closing parentheses
                                    logger.debug(f"Skipping rule with too many closing parentheses: {rule}")
                                    continue
                                    
                            # Check for other common syntax errors
                            if '\\' in rule and '\\\'' not in rule and '\\"' not in rule:
                                # Escape backslashes that aren't already escaping quotes
                                rule = rule.replace('\\', '\\\\')
                                
                            # Skip other known problematic patterns
                            if '**' in rule or '{' in rule and '}' not in rule:
                                logger.debug(f"Skipping rule with problematic pattern: {rule}")
                                continue
                                
                            # Add the sanitized rule
                            sanitized_rules.append(rule)
                        except Exception as e:
                            logger.debug(f"Error sanitizing rule '{rule}': {e}")
                            continue
                    
                    with self._lock:
                        # Try to compile the rules with a timeout to avoid hanging
                        # Use try/except for each potential error point
                        try:
                            # Limit the number of rules to compile for better stability
                            max_rules = 50000
                            if len(sanitized_rules) > max_rules:
                                logger.warning(f"Limiting to {max_rules} rules out of {len(sanitized_rules)}")
                                sanitized_rules = sanitized_rules[:max_rules]
                            
                            self.rules = AdblockRules(
                                sanitized_rules,
                                use_re2=False,  # Don't use re2 as it may not be available
                                max_mem=256*1024*1024  # Limit memory usage to 256MB
                            )
                            
                            self.url_cache.clear()  # Clear cache after updating rules
                            
                            logger.info(f"Ad blocker loaded {len(sanitized_rules)} rules out of {len(raw_rules)} total rules")
                        except Exception as e:
                            logger.error(f"Error compiling ad block rules: {e}")
                            # Fall back to domain blocking only
                            self.rules = None
                            logger.warning("Falling back to simple domain blocking due to rule compilation error")
                            logger.info(f"Ad blocker loaded {len(self.blocked_domains)} domain blocks")
                except Exception as e:
                    logger.error(f"Error setting up ad block rules: {e}")
                    # Fall back to domain blocking only
                    self.rules = None
                    logger.warning("Falling back to simple domain blocking due to setup error")
                    logger.info(f"Ad blocker loaded {len(self.blocked_domains)} domain blocks")
            elif raw_rules:
                logger.warning("adblockparser not available. Using simple domain blocking.")
                logger.info(f"Ad blocker loaded {len(self.blocked_domains)} domain blocks")
        except Exception as e:
            logger.error(f"Error loading filter lists: {e}")
    
    def _get_list_path(self, list_name: str) -> str:
        """
        Get the file path for a filter list.
        
        Args:
            list_name: Name of the filter list
            
        Returns:
            str: Path to the filter list file
        """
        # Convert list name to a valid filename
        filename = re.sub(r'[^\w\-_.]', '_', list_name) + '.txt'
        return os.path.join(self.lists_dir, filename)
    
    def _should_download_list(self, list_path: str) -> bool:
        """
        Check if a filter list should be downloaded.
        
        Args:
            list_path: Path to the filter list file
            
        Returns:
            bool: True if the list should be downloaded
        """
        # If the file doesn't exist, download it
        if not os.path.exists(list_path):
            return True
        
        # If the file is older than 7 days, download it
        file_time = os.path.getmtime(list_path)
        current_time = time.time()
        if current_time - file_time > 7 * 24 * 60 * 60:  # 7 days in seconds
            return True
        
        return False
    
    def _download_filter_list(self, list_url: str, list_path: str) -> bool:
        """
        Download a filter list.
        
        Args:
            list_url: URL of the filter list
            list_path: Path to save the filter list
            
        Returns:
            bool: True if download was successful
        """
        try:
            logger.debug(f"Downloading filter list from {list_url}")
            
            headers = {
                'User-Agent': 'WinkBrowser/0.1',
            }
            
            req = urllib.request.Request(list_url, headers=headers)
            with urllib.request.urlopen(req) as response:
                with open(list_path, 'wb') as out_file:
                    out_file.write(response.read())
            
            logger.debug(f"Downloaded filter list to {list_path}")
            return True
        except Exception as e:
            logger.error(f"Error downloading filter list {list_url}: {e}")
            return False
    
    def _is_domain_block(self, rule: str) -> bool:
        """
        Check if a rule is a simple domain block.
        
        Args:
            rule: Filter rule
            
        Returns:
            bool: True if rule is a domain block
        """
        return rule.startswith('||') and rule.endswith('^')
    
    def _extract_domain(self, rule: str) -> Optional[str]:
        """
        Extract domain from a filter rule.
        
        Args:
            rule: Filter rule
            
        Returns:
            Optional[str]: Domain or None
        """
        if rule.startswith('||') and rule.endswith('^'):
            return rule[2:-1]
        return None
    
    def should_block_url(self, url: str, options: Dict[str, Any] = None) -> bool:
        """
        Check if a URL should be blocked.
        
        Args:
            url: URL to check
            options: Additional options for the AdblockRules.should_block method
            
        Returns:
            bool: True if the URL should be blocked
        """
        if not self.enabled:
            return False
        
        # Check cache first
        with self._lock:
            if url in self.url_cache:
                return self.url_cache[url]
        
        # Default options
        if options is None:
            options = {}
            
            # Extract domain for domain-specific rules
            parsed_url = urllib.parse.urlparse(url)
            options['domain'] = parsed_url.netloc
        
        # Check if URL should be blocked
        should_block = False
        
        # Use adblockparser if available
        if self.adblockparser_available and self.rules:
            try:
                with self._lock:
                    should_block = self.rules.should_block(url, options)
                    
                    # Cache the result
                    self.url_cache[url] = should_block
            except Exception as e:
                logger.error(f"Error checking URL {url}: {e}")
        
        # Fallback to simple domain blocking
        if not should_block:
            parsed_url = urllib.parse.urlparse(url)
            domain = parsed_url.netloc
            
            # Check if the domain or any parent domain is blocked
            domain_parts = domain.split('.')
            for i in range(len(domain_parts) - 1):
                check_domain = '.'.join(domain_parts[i:])
                if check_domain in self.blocked_domains:
                    should_block = True
                    
                    # Cache the result
                    with self._lock:
                        self.url_cache[url] = should_block
                    
                    break
        
        return should_block
    
    def add_custom_rule(self, rule: str) -> bool:
        """
        Add a custom filter rule.
        
        Args:
            rule: Filter rule to add
            
        Returns:
            bool: True if the rule was added
        """
        if not rule or rule.isspace():
            return False
        
        # Add to custom rules
        if rule not in self.custom_rules:
            self.custom_rules.append(rule)
            
            # Rebuild rules
            self._load_filter_lists()
            
            logger.debug(f"Added custom rule: {rule}")
            return True
        
        return False
    
    def remove_custom_rule(self, rule: str) -> bool:
        """
        Remove a custom filter rule.
        
        Args:
            rule: Filter rule to remove
            
        Returns:
            bool: True if the rule was removed
        """
        if rule in self.custom_rules:
            self.custom_rules.remove(rule)
            
            # Rebuild rules
            self._load_filter_lists()
            
            logger.debug(f"Removed custom rule: {rule}")
            return True
        
        return False
    
    def get_custom_rules(self) -> List[str]:
        """
        Get the list of custom rules.
        
        Returns:
            List[str]: List of custom rules
        """
        return self.custom_rules.copy()
    
    def set_custom_rules(self, rules: List[str]) -> None:
        """
        Set the list of custom rules.
        
        Args:
            rules: List of filter rules
        """
        self.custom_rules = list(filter(lambda r: r and not r.isspace(), rules))
        
        # Rebuild rules
        self._load_filter_lists()
        
        logger.debug(f"Set {len(self.custom_rules)} custom rules")
    
    def add_filter_list(self, name: str, url: str) -> bool:
        """
        Add a filter list.
        
        Args:
            name: Name of the filter list
            url: URL of the filter list
            
        Returns:
            bool: True if the filter list was added
        """
        if not name or not url:
            return False
        
        # Add to filter lists
        self.filter_lists[name] = url
        
        # Enable the list by default
        self.enabled_lists.add(name)
        
        # Rebuild rules
        self._load_filter_lists()
        
        logger.debug(f"Added filter list: {name} ({url})")
        return True
    
    def remove_filter_list(self, name: str) -> bool:
        """
        Remove a filter list.
        
        Args:
            name: Name of the filter list
            
        Returns:
            bool: True if the filter list was removed
        """
        if name in self.filter_lists:
            # Remove from filter lists
            del self.filter_lists[name]
            
            # Remove from enabled lists
            if name in self.enabled_lists:
                self.enabled_lists.remove(name)
            
            # Rebuild rules
            self._load_filter_lists()
            
            logger.debug(f"Removed filter list: {name}")
            return True
        
        return False
    
    def enable_filter_list(self, name: str) -> bool:
        """
        Enable a filter list.
        
        Args:
            name: Name of the filter list
            
        Returns:
            bool: True if the filter list was enabled
        """
        if name in self.filter_lists and name not in self.enabled_lists:
            self.enabled_lists.add(name)
            
            # Rebuild rules
            self._load_filter_lists()
            
            logger.debug(f"Enabled filter list: {name}")
            return True
        
        return False
    
    def disable_filter_list(self, name: str) -> bool:
        """
        Disable a filter list.
        
        Args:
            name: Name of the filter list
            
        Returns:
            bool: True if the filter list was disabled
        """
        if name in self.enabled_lists:
            self.enabled_lists.remove(name)
            
            # Rebuild rules
            self._load_filter_lists()
            
            logger.debug(f"Disabled filter list: {name}")
            return True
        
        return False
    
    def get_filter_lists(self) -> Dict[str, str]:
        """
        Get the dictionary of filter lists.
        
        Returns:
            Dict[str, str]: Dictionary mapping names to URLs
        """
        return self.filter_lists.copy()
    
    def get_enabled_lists(self) -> List[str]:
        """
        Get the list of enabled filter lists.
        
        Returns:
            List[str]: List of enabled filter list names
        """
        return list(self.enabled_lists)
    
    def get_available_lists(self) -> List[str]:
        """
        Get the list of available filter lists.
        
        Returns:
            List[str]: List of available filter list names
        """
        return list(self.filter_lists.keys())
    
    def set_enabled_lists(self, lists: List[str]) -> None:
        """
        Set the list of enabled filter lists.
        
        Args:
            lists: List of filter list names
        """
        # Only enable lists that exist
        self.enabled_lists = set(name for name in lists if name in self.filter_lists)
        
        # Rebuild rules
        self._load_filter_lists()
        
        logger.debug(f"Set {len(self.enabled_lists)} enabled filter lists")
    
    def clear_cache(self) -> None:
        """Clear the URL cache."""
        with self._lock:
            self.url_cache.clear()
        
        logger.debug("URL cache cleared")
    
    def set_enabled(self, enabled: bool) -> None:
        """
        Enable or disable ad blocking.
        
        Args:
            enabled: Whether ad blocking should be enabled
        """
        if self.enabled != enabled:
            self.enabled = enabled
            
            if enabled:
                # Reload filter lists when enabling
                self._load_filter_lists()
            else:
                # Clear cache when disabling
                self.clear_cache()
            
            logger.debug(f"Ad blocker {'enabled' if enabled else 'disabled'}")
    
    def is_enabled(self) -> bool:
        """
        Check if ad blocking is enabled.
        
        Returns:
            bool: True if ad blocking is enabled
        """
        return self.enabled 