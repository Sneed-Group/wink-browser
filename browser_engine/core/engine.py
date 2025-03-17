"""
Core browser engine implementation.
This module contains the main engine that handles rendering,
page loading, and JavaScript execution.
"""

import logging
import threading
import time
import os
import re
import urllib.parse
from typing import Dict, List, Optional, Tuple, Any, Callable

import requests
from bs4 import BeautifulSoup
import html5lib

from browser_engine.parser.html_parser import HTMLParser
from browser_engine.parser.css_parser import CSSParser
from browser_engine.parser.js_engine import JSEngine
from browser_engine.media.media_handler import MediaHandler
from browser_engine.privacy.ad_blocker import AdBlocker
from browser_engine.extensions.manager import ExtensionManager
from browser_engine.utils.cache import Cache
from browser_engine.utils.network import NetworkManager
from browser_engine.utils.config import Config

logger = logging.getLogger(__name__)

class BrowserEngine:
    """
    Main browser engine that coordinates all components.
    """
    
    def __init__(self, 
                 text_only_mode: bool = False, 
                 private_mode: bool = False,
                 ad_blocker: Optional[AdBlocker] = None):
        """
        Initialize the browser engine.
        
        Args:
            text_only_mode: Whether to run in text-only mode (no images, JS, etc.)
            private_mode: Whether to run in private browsing mode
            ad_blocker: Ad blocker instance to use
        """
        self.text_only_mode = text_only_mode
        self.private_mode = private_mode
        
        # Initialize configuration
        self.config = Config()
        
        # Initialize components
        self.network = NetworkManager(private_mode=private_mode)
        
        # Initialize cache (disabled in private mode)
        self.cache = Cache(enabled=not private_mode)
        
        # Initialize parsers and handlers
        self.html_parser = HTMLParser()
        self.css_parser = CSSParser()
        self.js_engine = JSEngine(enabled=not text_only_mode)
        self.media_handler = MediaHandler(enabled=not text_only_mode)
        
        # Initialize ad blocker if provided, or create a new one
        self.ad_blocker = ad_blocker if ad_blocker else AdBlocker()
        
        # Initialize extension manager
        self.extension_manager = ExtensionManager(config=self.config)
        
        # Current page state
        self.current_url = None
        self.page_title = ""
        self.dom = None
        self.stylesheets = []
        self.resources = {}
        
        # Navigation history
        self.history = []
        self.history_position = -1
        
        # Page loading state
        self.is_loading = False
        self.load_progress = 0
        self.load_callbacks = []
        
        logger.info(f"Browser engine initialized. Text-only: {text_only_mode}, Private: {private_mode}")
    
    def load_url(self, url: str) -> None:
        """
        Load a URL.
        
        Args:
            url: URL to load
        """
        # Skip if already loading
        if self.is_loading:
            return
        
        # Set loading state
        self.is_loading = True
        self.load_progress = 0
        self._notify_loading_state()
        
        # Trigger browser_start event for extensions on first load
        if not self.current_url:
            self.extension_manager.trigger_event("browser_start", {})
        
        # Trigger page_unload event for extensions
        if self.current_url:
            self.extension_manager.trigger_event("page_unload", {
                "url": self.current_url,
                "title": self.page_title
            })
        
        # Start loading in a background thread
        threading.Thread(
            target=self._load_url_thread,
            args=(url,),
            daemon=True
        ).start()
    
    def _load_url_thread(self, url: str) -> None:
        """
        Background thread for loading a URL.
        
        Args:
            url: The URL to load
        """
        try:
            # Check cache first if not in private mode
            cached_content = None
            if not self.private_mode:
                cached_content = self.cache.get(url)
            
            if cached_content:
                logger.debug(f"Using cached content for {url}")
                html_content = cached_content
                self.load_progress = 50
                self._notify_loading_state()
            else:
                # Request the page
                self.load_progress = 10
                self._notify_loading_state()
                
                # Check if the request should be blocked
                if self.ad_blocker.should_block_url(url):
                    logger.info(f"Blocking URL: {url}")
                    self._handle_blocked_page(url)
                    return
                
                # Fetch the page
                response = self.network.get(url)
                self.load_progress = 40
                self._notify_loading_state()
                
                html_content = response.text
                
                # Cache the content if not in private mode
                if not self.private_mode:
                    self.cache.set(url, html_content)
            
            # Parse HTML
            self.load_progress = 60
            self._notify_loading_state()
            self.dom = self.html_parser.parse(html_content)
            
            # Extract title
            title_tag = self.dom.find('title')
            self.page_title = title_tag.text if title_tag else url
            
            # Process stylesheets
            self.load_progress = 70
            self._notify_loading_state()
            self._process_stylesheets()
            
            # Download resources (images, etc.) unless in text-only mode
            if not self.text_only_mode:
                self.load_progress = 80
                self._notify_loading_state()
                self._load_resources(url)
            
            # Execute JavaScript unless in text-only mode
            if not self.text_only_mode:
                self.load_progress = 90
                self._notify_loading_state()
                self._execute_scripts()
            
            # Update history
            self._update_history(url)
            self.current_url = url
            
            # Finished loading
            self.load_progress = 100
            self.is_loading = False
            self._notify_loading_state()
            
            logger.info(f"Successfully loaded {url}")
            
        except Exception as e:
            logger.exception(f"Error loading URL {url}: {e}")
            self._handle_page_error(url, str(e))
    
    def _process_stylesheets(self) -> None:
        """Process and apply stylesheets."""
        # Process in a separate thread to avoid blocking the UI
        threading.Thread(
            target=self._process_stylesheets_thread,
            daemon=True
        ).start()
    
    def _process_stylesheets_thread(self) -> None:
        """Background thread for processing stylesheets."""
        try:
            # Process CSS for each stylesheet
            self.stylesheets = []
            
            # Extract stylesheets from the DOM
            style_tags = self.html_parser.get_elements_by_tag(self.dom, "style")
            for style in style_tags:
                css_text = style.string
                if css_text:
                    self.stylesheets.append(self.css_parser.parse(css_text))
            
            # Extract external stylesheets
            link_tags = self.dom.select("link[rel='stylesheet']")
            for link in link_tags:
                href = link.get("href")
                if href:
                    # Resolve the URL
                    if not href.startswith("http"):
                        if self.current_url:
                            base_url = "/".join(self.current_url.split("/")[:-1])
                            href = f"{base_url}/{href}"
                    
                    # Try to load from cache first
                    cached_css = self.cache.get(href)
                    if cached_css:
                        self.stylesheets.append(self.css_parser.parse(cached_css))
                    else:
                        # Load from network
                        try:
                            response = self.network.get(href)
                            if response.status_code == 200:
                                css_text = response.text
                                self.cache.set(href, css_text)
                                self.stylesheets.append(self.css_parser.parse(css_text))
                        except Exception as e:
                            logger.error(f"Error loading stylesheet {href}: {e}")
            
            logger.debug(f"Processed {len(self.stylesheets)} stylesheets")
        except Exception as e:
            logger.error(f"Error processing stylesheets: {e}")
    
    def _load_resources(self, base_url: str) -> None:
        """
        Load resources like images, fonts, etc.
        
        Args:
            base_url: Base URL for resolving relative URLs
        """
        # In a real browser, we would download and process these resources
        # For this implementation, we'll just log them
        
        # Find all images
        for img in self.dom.find_all('img'):
            src = img.get('src')
            if src:
                abs_url = urllib.parse.urljoin(base_url, src)
                logger.debug(f"Image found: {abs_url}")
                
                # Check if it should be blocked
                if self.ad_blocker.should_block_url(abs_url):
                    logger.info(f"Blocking image: {abs_url}")
                    img['src'] = ''  # Remove the source
                    img['alt'] = '[Blocked]'  # Set alt text
    
    def _execute_scripts(self) -> None:
        """Execute JavaScript scripts found in the page."""
        if not self.js_engine.enabled or self.text_only_mode:
            return
        
        # Process in a separate thread to avoid blocking the UI
        threading.Thread(
            target=self._execute_scripts_thread,
            daemon=True
        ).start()
    
    def _execute_scripts_thread(self) -> None:
        """Background thread for executing scripts."""
        try:
            # Set the DOM content in the JS engine
            self.js_engine.set_dom(str(self.dom))
            
            # Extract scripts from the DOM
            script_tags = self.html_parser.get_elements_by_tag(self.dom, "script")
            for script in script_tags:
                # Skip if it has a src attribute (external script)
                if script.get("src"):
                    continue
                
                # Skip if it has a type that's not JavaScript
                script_type = script.get("type", "text/javascript")
                if "javascript" not in script_type.lower():
                    continue
                
                # Execute the script
                script_text = script.string
                if script_text:
                    self.js_engine.execute(script_text)
            
            # Trigger dom_ready event for extensions
            self.extension_manager.trigger_event("dom_ready", {
                "url": self.current_url,
                "title": self.page_title,
                "document": self.dom
            })
            
            logger.debug(f"Executed scripts from the page")
        except Exception as e:
            logger.error(f"Error executing scripts: {e}")
    
    def _handle_blocked_page(self, url: str) -> None:
        """
        Handle a blocked page.
        
        Args:
            url: The blocked URL
        """
        # Create a simple blocked page
        html = f"""
        <html>
            <head><title>Page Blocked</title></head>
            <body>
                <h1>Page Blocked</h1>
                <p>The page at {url} was blocked by your content blocker settings.</p>
            </body>
        </html>
        """
        self.dom = self.html_parser.parse(html)
        self.page_title = "Page Blocked"
        self.current_url = url
        
        # Update loading state
        self.load_progress = 100
        self.is_loading = False
        self._notify_loading_state()
    
    def _handle_page_error(self, url: str, error: str) -> None:
        """
        Handle a page loading error.
        
        Args:
            url: The URL that failed to load
            error: Error message
        """
        # Create a simple error page
        html = f"""
        <html>
            <head><title>Error Loading Page</title></head>
            <body>
                <h1>Error Loading Page</h1>
                <p>There was an error loading {url}:</p>
                <pre>{error}</pre>
            </body>
        </html>
        """
        self.dom = self.html_parser.parse(html)
        self.page_title = "Error Loading Page"
        self.current_url = url
        
        # Update loading state
        self.load_progress = 100
        self.is_loading = False
        self._notify_loading_state()
    
    def _update_history(self, url: str) -> None:
        """
        Update browsing history.
        
        Args:
            url: URL to add to history
        """
        # Skip if private mode
        if self.private_mode:
            return
        
        # Skip if the URL is already the current one
        if url == self.current_url:
            return
        
        # If we're not at the end of the history, truncate it
        if self.history_position < len(self.history) - 1:
            self.history = self.history[:self.history_position + 1]
        
        # Add the URL to history
        self.history.append(url)
        self.history_position = len(self.history) - 1
        
        # Trigger bookmark_add event for extensions if this was a bookmark add
        # This is just an example - in a real implementation, you would detect bookmark adds elsewhere
        # self.extension_manager.trigger_event("bookmark_add", {
        #     "url": url,
        #     "title": self.page_title
        # })
    
    def go_back(self) -> bool:
        """
        Navigate back in history.
        
        Returns:
            bool: True if navigation was successful, False otherwise
        """
        if self.history_position > 0:
            self.history_position -= 1
            url = self.history[self.history_position]
            self.load_url(url)
            return True
        return False
    
    def go_forward(self) -> bool:
        """
        Navigate forward in history.
        
        Returns:
            bool: True if navigation was successful, False otherwise
        """
        if self.history_position < len(self.history) - 1:
            self.history_position += 1
            url = self.history[self.history_position]
            self.load_url(url)
            return True
        return False
    
    def refresh(self) -> None:
        """Refresh the current page."""
        if self.current_url:
            self.load_url(self.current_url)
    
    def stop_loading(self) -> None:
        """Stop loading the current page."""
        # In a real implementation, we would cancel network requests
        self.is_loading = False
        self.load_progress = 0
        self._notify_loading_state()
        logger.info("Page loading stopped")
    
    def set_text_only_mode(self, enabled: bool) -> None:
        """
        Set text-only mode.
        
        Args:
            enabled: Whether text-only mode should be enabled
        """
        if self.text_only_mode != enabled:
            self.text_only_mode = enabled
            self.js_engine.enabled = not enabled
            self.media_handler.enabled = not enabled
            logger.info(f"Text-only mode {'enabled' if enabled else 'disabled'}")
            
            # Reload current page to apply changes
            if self.current_url:
                self.refresh()
    
    def set_private_mode(self, enabled: bool) -> None:
        """
        Set private browsing mode.
        
        Args:
            enabled: Whether private mode should be enabled
        """
        if self.private_mode != enabled:
            self.private_mode = enabled
            self.cache.enabled = not enabled
            self.network.private_mode = enabled
            logger.info(f"Private mode {'enabled' if enabled else 'disabled'}")
    
    def register_load_callback(self, callback: Callable[[], None]) -> None:
        """
        Register a callback to be called when loading state changes.
        
        Args:
            callback: Function to call when loading state changes
        """
        self.load_callbacks.append(callback)
    
    def _notify_loading_state(self) -> None:
        """Notify all registered callbacks about loading state changes."""
        for callback in self.load_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in loading callback: {e}")
    
    def get_rendered_content(self) -> str:
        """
        Get the rendered HTML content.
        
        Returns:
            str: HTML content as a string
        """
        if self.dom:
            return str(self.dom)
        return ""
    
    def get_plain_text(self) -> str:
        """
        Get the page content as plain text.
        
        Returns:
            str: Plain text content
        """
        if self.dom:
            return self.dom.get_text()
        return ""
    
    def clean_up(self) -> None:
        """Clean up resources before shutdown."""
        # Trigger browser_exit event for extensions
        self.extension_manager.trigger_event("browser_exit", {})
        
        try:
            # Close all components
            if self.js_engine:
                self.js_engine.clean_up()
            
            if self.media_handler:
                self.media_handler.clean_up()
            
            if self.cache:
                self.cache.close()
            
            if self.network:
                self.network.close()
            
            logger.info("Browser engine cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up browser engine: {e}") 