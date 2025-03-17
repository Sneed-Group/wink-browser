"""
Ad blocker implementation.
This module provides ad and tracker blocking functionality.
"""

import os
import logging
import re
from typing import List, Set, Optional, Dict

logger = logging.getLogger(__name__)

class AdBlocker:
    """
    Ad blocker for filtering out advertisements and trackers.
    
    This class handles the blocking of ads and trackers based on filter lists
    and user-defined rules.
    """
    
    def __init__(self, config_manager):
        """
        Initialize the ad blocker.
        
        Args:
            config_manager: The configuration manager
        """
        self.config_manager = config_manager
        
        # Directory for filter lists
        self.filters_dir = os.path.expanduser("~/.wink_browser/filters")
        os.makedirs(self.filters_dir, exist_ok=True)
        
        # Sets of rules
        self.domain_rules: Set[str] = set()
        self.url_rules: Set[str] = set()
        self.regex_rules: List[re.Pattern] = []
        
        # Load filter lists if ad blocking is enabled
        if self.config_manager.get_config("privacy.block_ads", True):
            self._load_filter_lists()
        
        logger.info("Ad blocker initialized")
    
    def _load_filter_lists(self) -> None:
        """Load ad blocking filter lists."""
        try:
            # Load built-in filter lists
            self._load_built_in_filters()
            
            # Load custom filter lists from user directory
            self._load_custom_filters()
            
            logger.info(f"Loaded {len(self.domain_rules)} domain rules, "
                       f"{len(self.url_rules)} URL rules, and "
                       f"{len(self.regex_rules)} regex rules")
        except Exception as e:
            logger.error(f"Error loading filter lists: {e}")
    
    def _load_built_in_filters(self) -> None:
        """Load built-in filter lists."""
        # Common ad domains
        common_ad_domains = [
            "ads.example.com",
            "tracker.example.com",
            "analytics.example.com",
            "googleadservices.com",
            "doubleclick.net",
            "adnxs.com",
            "moatads.com"
        ]
        
        # Add common ad domains to domain rules
        self.domain_rules.update(common_ad_domains)
        
        # Add some common ad URL patterns
        common_url_patterns = [
            "/ads/",
            "/ad/",
            "/analytics/",
            "/tracker/",
            "/pixel/",
            "/banner/",
            "/popup/"
        ]
        
        # Add common URL patterns to URL rules
        self.url_rules.update(common_url_patterns)
        
        # Add some common regex patterns
        common_regex_patterns = [
            r"/(ads?|banner|pop(up)?|sponsor|iframeads|imageads|webad|webads|ads_)/",
            r"[-.]ads?\.",
            r"^ad\d+\.",
            r"[/.]tracking[/.]",
            r"[/.]analytics[/.]"
        ]
        
        # Compile and add regex patterns
        for pattern in common_regex_patterns:
            try:
                self.regex_rules.append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                logger.warning(f"Invalid regex pattern: {pattern}")
    
    def _load_custom_filters(self) -> None:
        """Load custom filter lists from user directory."""
        # Check if custom filter files exist
        filter_files = [
            os.path.join(self.filters_dir, "domains.txt"),
            os.path.join(self.filters_dir, "urls.txt"),
            os.path.join(self.filters_dir, "regex.txt")
        ]
        
        # Load domain filter list
        if os.path.exists(filter_files[0]):
            try:
                with open(filter_files[0], 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self.domain_rules.add(line)
            except Exception as e:
                logger.error(f"Error loading domain filter list: {e}")
        
        # Load URL filter list
        if os.path.exists(filter_files[1]):
            try:
                with open(filter_files[1], 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self.url_rules.add(line)
            except Exception as e:
                logger.error(f"Error loading URL filter list: {e}")
        
        # Load regex filter list
        if os.path.exists(filter_files[2]):
            try:
                with open(filter_files[2], 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            try:
                                self.regex_rules.append(re.compile(line, re.IGNORECASE))
                            except re.error:
                                logger.warning(f"Invalid regex pattern: {line}")
            except Exception as e:
                logger.error(f"Error loading regex filter list: {e}")
    
    def should_block(self, url: str) -> bool:
        """
        Check if a URL should be blocked.
        
        Args:
            url: The URL to check
            
        Returns:
            True if the URL should be blocked, False otherwise
        """
        # Skip checking if ad blocking is disabled
        if not self.config_manager.get_config("privacy.block_ads", True):
            return False
        
        # Check domain rules
        for domain in self.domain_rules:
            if domain in url:
                logger.debug(f"Blocked URL by domain rule: {url}")
                return True
        
        # Check URL rules
        for url_pattern in self.url_rules:
            if url_pattern in url:
                logger.debug(f"Blocked URL by URL rule: {url}")
                return True
        
        # Check regex rules
        for regex in self.regex_rules:
            if regex.search(url):
                logger.debug(f"Blocked URL by regex rule: {url}")
                return True
        
        return False
    
    def add_custom_rule(self, rule: str, rule_type: str = "domain") -> bool:
        """
        Add a custom blocking rule.
        
        Args:
            rule: The rule to add
            rule_type: The type of rule (domain, url, or regex)
            
        Returns:
            True if the rule was added successfully, False otherwise
        """
        try:
            if rule_type == "domain":
                self.domain_rules.add(rule)
                self._save_rules_to_file(self.domain_rules, "domains.txt")
            elif rule_type == "url":
                self.url_rules.add(rule)
                self._save_rules_to_file(self.url_rules, "urls.txt")
            elif rule_type == "regex":
                try:
                    self.regex_rules.append(re.compile(rule, re.IGNORECASE))
                    self._save_rules_to_file([r.pattern for r in self.regex_rules], "regex.txt")
                except re.error:
                    logger.warning(f"Invalid regex pattern: {rule}")
                    return False
            else:
                logger.warning(f"Unknown rule type: {rule_type}")
                return False
                
            logger.info(f"Added custom {rule_type} rule: {rule}")
            return True
        except Exception as e:
            logger.error(f"Error adding custom rule: {e}")
            return False
    
    def remove_custom_rule(self, rule: str, rule_type: str = "domain") -> bool:
        """
        Remove a custom blocking rule.
        
        Args:
            rule: The rule to remove
            rule_type: The type of rule (domain, url, or regex)
            
        Returns:
            True if the rule was removed successfully, False otherwise
        """
        try:
            if rule_type == "domain":
                if rule in self.domain_rules:
                    self.domain_rules.remove(rule)
                    self._save_rules_to_file(self.domain_rules, "domains.txt")
                else:
                    return False
            elif rule_type == "url":
                if rule in self.url_rules:
                    self.url_rules.remove(rule)
                    self._save_rules_to_file(self.url_rules, "urls.txt")
                else:
                    return False
            elif rule_type == "regex":
                found = False
                for i, regex in enumerate(self.regex_rules):
                    if regex.pattern == rule:
                        self.regex_rules.pop(i)
                        found = True
                        break
                if found:
                    self._save_rules_to_file([r.pattern for r in self.regex_rules], "regex.txt")
                else:
                    return False
            else:
                logger.warning(f"Unknown rule type: {rule_type}")
                return False
                
            logger.info(f"Removed custom {rule_type} rule: {rule}")
            return True
        except Exception as e:
            logger.error(f"Error removing custom rule: {e}")
            return False
    
    def _save_rules_to_file(self, rules: set, filename: str) -> None:
        """
        Save rules to a file.
        
        Args:
            rules: The rules to save
            filename: The filename to save to
        """
        try:
            filepath = os.path.join(self.filters_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                for rule in sorted(rules):
                    f.write(f"{rule}\n")
        except Exception as e:
            logger.error(f"Error saving rules to file: {e}")
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get ad blocker statistics.
        
        Returns:
            A dictionary of statistics
        """
        return {
            "domain_rules": len(self.domain_rules),
            "url_rules": len(self.url_rules),
            "regex_rules": len(self.regex_rules)
        }
    
    def process_url(self, url: str) -> str:
        """
        Process a URL and return it if it should not be blocked.
        
        Args:
            url: The URL to process
            
        Returns:
            The original URL if it should not be blocked, or a blank page URL if it should be blocked
        """
        if self.should_block(url):
            logger.info(f"Blocked URL: {url}")
            return "about:blank"
        return url 