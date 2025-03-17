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
from browser_engine.utils.url import URL

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
        
        # Initialize JavaScript engine with proper parameters
        # The old code used 'enabled', but the new JSEngine uses different parameters
        try:
            self.js_engine = JSEngine(
                sandbox=True,  # Use sandbox for security
                timeout=5000,  # 5 seconds timeout
                enable_modern_js=True,  # Enable modern JavaScript features
                cache_dir=None  # Use default cache directory
            ) if not text_only_mode else None
        except Exception as e:
            logger.warning(f"Failed to initialize JavaScript engine: {e}. Falling back to text-only mode.")
            self.js_engine = None
            self.text_only_mode = True
        
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
            # Parse URL
            parsed_url = URL(url)
            
            # Handle special URLs
            if parsed_url.scheme in ['about', 'data', 'javascript', 'blob', 'file']:
                content = self._handle_special_url(str(parsed_url))
                if content:
                    self.dom = self.html_parser.parse(content)
                    self.page_title = "Wink Browser"
                    self.current_url = str(parsed_url)
                    self.load_progress = 100
                    self.is_loading = False
                    self._notify_loading_state()
                    return
            
            # Continue with regular URL loading
            self._load_regular_url(str(parsed_url))
            
        except Exception as e:
            logger.error(f"Error loading URL {url}: {e}")
            self._handle_error_page(url, str(e))
            self.load_progress = 100
            self.is_loading = False
            self._notify_loading_state()
    
    def _handle_special_url(self, url: str) -> Optional[str]:
        """
        Handle special URLs like about:blank.
        
        Args:
            url: Special URL to handle
            
        Returns:
            str: HTML content or None if not handled
        """
        if url == "about:blank":
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>New Tab</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 0;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        background-color: #f5f5f5;
                    }
                    .container {
                        text-align: center;
                    }
                    h1 {
                        color: #333;
                        font-size: 24px;
                        margin-bottom: 20px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Welcome to Wink Browser</h1>
                    <p>A privacy-focused web browser</p>
                </div>
            </body>
            </html>
            """
        elif url.startswith("about:"):
            # Handle other about: URLs
            page_name = url.split(':', 1)[1]
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>About: {page_name}</title>
            </head>
            <body>
                <h1>About: {page_name}</h1>
                <p>This is a special page in Wink Browser.</p>
            </body>
            </html>
            """
        
        # Not a handled special URL
        return None
    
    def _load_regular_url(self, url: str) -> None:
        """
        Load a regular HTTP/HTTPS URL.
        
        Args:
            url: URL to load
        """
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
            if self.ad_blocker and self.ad_blocker.should_block_url(url):
                logger.info(f"Blocking URL: {url}")
                self._handle_blocked_page(url)
                return
            
            # Fetch the page
            try:
                response = self.network.get(url)
                self.load_progress = 40
                self._notify_loading_state()
                
                html_content = response.text_decoded
                
                # Cache the content if not in private mode
                if not self.private_mode:
                    self.cache.set(url, html_content)
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                self._handle_error_page(url, str(e))
                return
        
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
            
            # If in text-only mode, remove style and link[rel=stylesheet] tags from the DOM
            # to prevent their content from appearing in the plain text output
            if self.text_only_mode and self.dom:
                try:
                    # Remove style tags safely
                    try:
                        for style_tag in self.dom.find_all('style'):
                            try:
                                style_tag.decompose()
                            except Exception as tag_error:
                                logger.warning(f"Error removing style tag: {tag_error}")
                    except Exception as find_error:
                        logger.warning(f"Error finding style tags: {find_error}")
                    
                    # Remove link tags for stylesheets safely
                    try:
                        for link_tag in self.dom.find_all('link', rel='stylesheet'):
                            try:
                                link_tag.decompose()
                            except Exception as tag_error:
                                logger.warning(f"Error removing stylesheet link tag: {tag_error}")
                    except Exception as find_error:
                        logger.warning(f"Error finding stylesheet link tags: {find_error}")
                    
                    logger.debug("Removed style and stylesheet link tags in text-only mode")
                except Exception as e:
                    logger.error(f"Error processing DOM in text-only mode: {e}")
                return
            
            # Extract stylesheets from the DOM
            try:
                style_tags = self.html_parser.get_elements_by_tag(self.dom, "style")
                for style in style_tags:
                    css_text = style.string
                    if css_text:
                        self.stylesheets.append(self.css_parser.parse(css_text))
            except Exception as e:
                logger.error(f"Error extracting stylesheets from DOM: {e}")
            
            # Extract external stylesheets
            try:
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
            except Exception as e:
                logger.error(f"Error extracting external stylesheets: {e}")
            
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
        """Execute JavaScript code in the DOM."""
        if self.text_only_mode:
            logger.debug("Text-only mode, skipping script execution")
            return
            
        # Execute scripts in a background thread
        thread = threading.Thread(target=self._execute_scripts_thread, daemon=True)
        thread.start()
    
    def _execute_scripts_thread(self) -> None:
        """Execute JavaScript in a background thread."""
        try:
            # Skip if JavaScript engine is not available or in text-only mode
            if not self.js_engine or self.text_only_mode:
                logger.debug("JavaScript execution disabled")
                return
                
            # Get all script elements
            script_elements = self.dom.find_all('script')
            
            # Set the DOM for the JavaScript engine
            if self.js_engine:
                # Use the new API to execute JavaScript with DOM
                try:
                    result = self.js_engine.execute_js_with_dom(
                        "/* Initial DOM setup */", 
                        str(self.dom)
                    )
                    
                    # Check for errors
                    if result and "error" in result and result["error"]:
                        logger.error(f"Error setting up DOM for JavaScript: {result['error']}")
                        return  # Skip script execution if we can't set up the DOM
                except Exception as e:
                    logger.error(f"Exception setting up DOM for JavaScript: {e}")
                    return  # Skip script execution if we can't set up the DOM
            
            # Execute each script
            executed_count = 0
            for script in script_elements:
                try:
                    # Skip external scripts for now
                    if script.get('src'):
                        continue
                        
                    # Get script content
                    script_text = script.string
                    if not script_text:
                        continue
                    
                    # Execute the script
                    if self.js_engine:
                        # Use the new API
                        result = self.js_engine.execute_js(script_text)
                        
                        # Check for errors
                        if result and "error" in result and result["error"]:
                            logger.warning(f"Error executing script: {result['error']}")
                            # Continue with other scripts
                        else:
                            executed_count += 1
                except Exception as e:
                    logger.warning(f"Exception executing script: {e}")
                    # Continue with other scripts
                
            logger.debug(f"Executed {executed_count} scripts out of {len(script_elements)} total scripts")
        except Exception as e:
            logger.error(f"Error executing scripts: {e}")
            # Continue with page loading even if scripts fail
    
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
    
    def _handle_error_page(self, url: str, error: str) -> None:
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
            enabled: Whether to enable text-only mode
        """
        if self.text_only_mode == enabled:
            return
            
        self.text_only_mode = enabled
        
        # Update components
        if self.js_engine and enabled:
            # If enabling text-only mode, set js_engine to None
            self.js_engine.close()
            self.js_engine = None
        elif not self.js_engine and not enabled:
            # If disabling text-only mode, create the js_engine
            self.js_engine = JSEngine(
                sandbox=True,
                timeout=5000,
                enable_modern_js=True
            )
            
        self.media_handler.enabled = not enabled
        
        # Reload the current page if any
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
        if not self.dom:
            return ""
        
        try:    
            # Create a copy of the DOM to avoid modifying the original
            try:
                dom_copy = self.html_parser.parse(str(self.dom))
            except Exception as e:
                logger.error(f"Error copying DOM for plain text extraction: {e}")
                # Fall back to using the original DOM directly
                dom_copy = self.dom
            
            # Remove scripts, styles, and other elements that shouldn't appear in plain text
            try:
                for tag_name in ['script', 'style', 'noscript', 'iframe', 'svg', 'canvas', 'template']:
                    try:
                        for element in dom_copy.find_all(tag_name):
                            try:
                                element.decompose()
                            except Exception as tag_error:
                                logger.warning(f"Error removing {tag_name} tag: {tag_error}")
                    except Exception as find_error:
                        logger.warning(f"Error finding {tag_name} tags: {find_error}")
            except Exception as e:
                logger.error(f"Error removing tags from DOM copy: {e}")
            
            # Extract text
            try:
                text = dom_copy.get_text(separator='\n', strip=True)
            except Exception as e:
                logger.error(f"Error extracting text from DOM: {e}")
                # Fallback to a simpler approach
                try:
                    text = "\n".join([elem.text for elem in dom_copy.find_all(text=True) if elem.strip()])
                except Exception:
                    logger.error("Failed to extract text with alternate method")
                    return "Error extracting page content"
            
            # Clean up whitespace
            try:
                lines = [line.strip() for line in text.split('\n')]
                lines = [line for line in lines if line]  # Remove empty lines
                return '\n'.join(lines)
            except Exception as e:
                logger.error(f"Error formatting plain text: {e}")
                return text
        except Exception as e:
            logger.error(f"Unexpected error in get_plain_text: {e}")
            return "Error processing page content"
    
    def clean_up(self) -> None:
        """Clean up resources used by the browser engine."""
        try:
            # Clean up components
            if self.js_engine:
                self.js_engine.close()
                self.js_engine = None
                
            if self.media_handler:
                self.media_handler.clean_up()
            
            if self.cache:
                self.cache.close()
            
            if self.network:
                self.network.close()
            
            # Trigger browser_exit event for extensions
            self.extension_manager.trigger_event("browser_exit", {})
            
            logger.info("Browser engine cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up browser engine: {e}") 