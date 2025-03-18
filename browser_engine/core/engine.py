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
import cssutils
import io

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
        self.js_engine = None
        self.js_disabled = False
        
        if not text_only_mode:
            try:
                self.js_engine = JSEngine(
                    sandbox=True,  # Use sandbox for security
                    timeout=5000,  # 5 seconds timeout
                    enable_modern_js=True,  # Enable modern JavaScript features
                    cache_dir=None  # Use default cache directory
                )
                
                # No need to start a browser in a separate thread anymore
                # as js2py doesn't use a browser
                logger.debug("JavaScript engine initialized with js2py")
                
            except Exception as e:
                logger.warning(f"Failed to initialize JavaScript engine: {e}. Falling back to text-only mode.")
                self.js_engine = None
                self.js_disabled = True
        
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
        
        # Callbacks for load state changes
        self.load_callbacks = []
        
        logger.info("Browser engine initialized")
    
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
        # Ensure about:blank loads properly by directly handling it without extra processing
        if url.lower() == "about:blank":
            logger.debug("Loading about:blank page")
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
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
                <meta charset="UTF-8">
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
        """Load a regular URL."""
        logger.info(f"Loading URL: {url}")
        self.load_progress = 10
        self._notify_loading_state()

        try:
            # Check cache first
            has_cache = hasattr(self, 'cache') and self.cache is not None
            use_cache = getattr(self, 'use_cache', True)  # Default to True if not set
            
            if has_cache and use_cache:
                cached_content = self.cache.get(url)
                if cached_content:
                    logger.info(f"Loading {url} from cache")
                    html_content = cached_content
                    self.load_progress = 50
                    self._notify_loading_state()
                else:
                    # Make the request
                    self.load_progress = 20
                    self._notify_loading_state()
                    
                    # Get the network manager - could be network or network_manager
                    network_mgr = getattr(self, 'network_manager', None) or getattr(self, 'network', None)
                    if not network_mgr:
                        raise AttributeError("No network manager available")
                    
                    response = network_mgr.request(url)
                    self.load_progress = 40
                    self._notify_loading_state()
                    
                    # Check if we received binary content (like PDF, images) instead of HTML
                    content_type = response.headers.get('Content-Type', '').lower()
                    if not any(text_type in content_type for text_type in ['text/html', 'text/plain', 'application/xhtml', 'application/xml', 'text/xml']):
                        if 'image/' in content_type or 'application/pdf' in content_type:
                            self._handle_binary_content(url, content_type)
                            return
                    
                    # Get the decoded text with robust handling of encodings
                    html_content = network_mgr.get_decoded_text(response)
                    
                    # Cache the content
                    if has_cache and use_cache:
                        self.cache.set(url, html_content)
                    
                    self.load_progress = 50
                    self._notify_loading_state()
            else:
                # No cache or cache disabled, make the request directly
                self.load_progress = 20
                self._notify_loading_state()
                
                # Get the network manager - could be network or network_manager
                network_mgr = getattr(self, 'network_manager', None) or getattr(self, 'network', None)
                if not network_mgr:
                    raise AttributeError("No network manager available")
                
                response = network_mgr.request(url)
                self.load_progress = 40
                self._notify_loading_state()
                
                # Check if we received binary content (like PDF, images) instead of HTML
                content_type = response.headers.get('Content-Type', '').lower()
                if not any(text_type in content_type for text_type in ['text/html', 'text/plain', 'application/xhtml', 'application/xml', 'text/xml']):
                    if 'image/' in content_type or 'application/pdf' in content_type:
                        self._handle_binary_content(url, content_type)
                        return
                
                # Get the decoded text with robust handling of encodings
                html_content = network_mgr.get_decoded_text(response)
                
                # Cache the content if caching is enabled
                if has_cache and use_cache:
                    self.cache.set(url, html_content)
                
                self.load_progress = 50
                self._notify_loading_state()
            
            # Check for corrupt content and try to recover if necessary
            if self._is_likely_corrupt_text(html_content):
                logger.warning(f"Potentially corrupt text detected for {url}. Attempting recovery.")
                html_content = self._try_recover_corrupt_text(html_content)
            
            # Set up DOM from the HTML content
            self._set_dom_from_html(html_content, url)
            
        except Exception as e:
            logger.error(f"Error loading URL {url}: {e}")
            self._handle_error_page(url, str(e))
    
    def _is_likely_corrupt_text(self, text: str) -> bool:
        """
        Check if text is likely corrupted due to encoding issues.
        
        Args:
            text: Text to check
            
        Returns:
            bool: True if text appears to be corrupted
        """
        if not text:
            return False
            
        # Sample the text (first 2000 chars should be enough)
        sample = text[:2000]
        
        # Count replacement characters () which indicate decoding errors
        replacement_char_count = sample.count('\ufffd')
        
        # Count control characters (except common whitespace)
        allowed_controls = '\r\n\t'
        control_char_count = sum(1 for c in sample if ord(c) < 32 and c not in allowed_controls)
        
        # Count the ratio of printable ASCII characters to catch binary content masquerading as text
        import string
        printable_chars = string.printable
        printable_count = sum(1 for c in sample if c in printable_chars)
        
        # Calculate percentages
        sample_len = len(sample) if sample else 1  # Avoid division by zero
        replacement_percentage = replacement_char_count / sample_len
        control_percentage = control_char_count / sample_len
        printable_percentage = printable_count / sample_len
        
        # Check for signs of corruption - using more lenient thresholds
        # Many modern websites have a higher ratio of control characters due to JSON and other data
        is_corrupt = (
            replacement_percentage > 0.20 or  # More than 20% replacement chars (was 8%)
            (control_percentage > 0.20 and printable_percentage < 0.60)  # High control chars AND low printable chars
        )
        
        # Also check for extreme cases where the content is clearly not HTML
        if not is_corrupt and not any(tag in sample.lower() for tag in ['<html', '<head', '<body', '<div', '<p', '<span', '<a']):
            # If we can't find any typical HTML tags AND we have high control characters, it's probably corrupt
            if control_percentage > 0.15:
                is_corrupt = True
        
        # Don't flag the content as corrupt if it's a known JSON response
        if sample.lstrip().startswith('{') and sample.rstrip().endswith('}'):
            is_corrupt = False
        elif sample.lstrip().startswith('[') and sample.rstrip().endswith(']'):
            is_corrupt = False
        
        if is_corrupt:
            logger.warning(f"Detected likely corrupt text: {replacement_percentage:.1%} replacement chars, "
                          f"{control_percentage:.1%} control chars, {printable_percentage:.1%} printable chars")
        
        return is_corrupt
    
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
                        parsed_css = self.css_parser.parse(css_text)
                        if parsed_css:
                            self.stylesheets.append(parsed_css)
                            logger.debug(f"Parsed inline CSS stylesheet: {len(css_text)} bytes")
            except Exception as e:
                logger.error(f"Error extracting stylesheets from DOM: {e}")
            
            # Extract external stylesheets
            try:
                link_tags = self.dom.select("link[rel='stylesheet']")
                for link in link_tags:
                    href = link.get("href")
                    if href:
                        # Skip data URLs for now
                        if href.startswith("data:"):
                            continue
                            
                        # Resolve the URL
                        if not href.startswith(("http://", "https://")):
                            if self.current_url:
                                href = urllib.parse.urljoin(self.current_url, href)
                        
                        # Try to load from cache first
                        cached_css = self.cache.get(href)
                        if cached_css:
                            logger.debug(f"Using cached CSS from {href}")
                            if isinstance(cached_css, bytes):
                                try:
                                    css_text = cached_css.decode('utf-8', errors='replace')
                                except Exception as e:
                                    logger.warning(f"Error decoding cached CSS: {e}")
                                    continue
                            else:
                                css_text = cached_css
                                
                            parsed_css = self.css_parser.parse(css_text)
                            if parsed_css:
                                self.stylesheets.append(parsed_css)
                                logger.debug(f"Parsed external CSS from cache: {len(css_text)} bytes")
                        else:
                            # Load from network
                            try:
                                logger.debug(f"Fetching external CSS from {href}")
                                response = self.network.get(href)
                                
                                # Check if it's actually CSS
                                content_type = response.headers.get('Content-Type', '').lower()
                                if not content_type.startswith(('text/css', 'text/plain')):
                                    logger.warning(f"External stylesheet has non-CSS content type: {content_type}")
                                
                                # Use text_decoded for proper encoding handling
                                css_text = response.text_decoded
                                
                                # Cache the CSS
                                if not self.private_mode:
                                    self.cache.set(href, css_text)
                                
                                # Parse the CSS
                                parsed_css = self.css_parser.parse(css_text)
                                if parsed_css:
                                    self.stylesheets.append(parsed_css)
                                    logger.debug(f"Parsed external CSS: {len(css_text)} bytes")
                            except Exception as e:
                                logger.error(f"Error loading external stylesheet {href}: {e}")
            except Exception as e:
                logger.error(f"Error extracting external stylesheets: {e}")
            
            # Process @import rules in stylesheets
            try:
                imported_stylesheets = []
                for stylesheet in self.stylesheets:
                    # Use the helper method to get all @import rules
                    import_rules = self.css_parser.get_import_rules(stylesheet)
                    for import_rule in import_rules:
                        # Extract the URL from the import rule
                        url = import_rule.href
                        
                        # Skip data URLs
                        if url.startswith("data:"):
                            continue
                            
                        # Resolve the URL
                        if not url.startswith(("http://", "https://")):
                            if self.current_url:
                                url = urllib.parse.urljoin(self.current_url, url)
                        
                        # Try to load from cache first
                        cached_import_css = self.cache.get(url)
                        if cached_import_css:
                            logger.debug(f"Using cached imported CSS from {url}")
                            if isinstance(cached_import_css, bytes):
                                try:
                                    import_css_text = cached_import_css.decode('utf-8', errors='replace')
                                except Exception as e:
                                    logger.warning(f"Error decoding cached imported CSS: {e}")
                                    continue
                            else:
                                import_css_text = cached_import_css
                                
                            parsed_import_css = self.css_parser.parse(import_css_text)
                            if parsed_import_css:
                                imported_stylesheets.append(parsed_import_css)
                                logger.debug(f"Parsed imported CSS from cache: {len(import_css_text)} bytes")
                        else:
                            # Load from network
                            try:
                                logger.debug(f"Fetching imported CSS from {url}")
                                response = self.network.get(url)
                                
                                # Use text_decoded for proper encoding handling
                                import_css_text = response.text_decoded
                                
                                # Cache the CSS
                                if not self.private_mode:
                                    self.cache.set(url, import_css_text)
                                
                                # Parse the CSS
                                parsed_import_css = self.css_parser.parse(import_css_text)
                                if parsed_import_css:
                                    imported_stylesheets.append(parsed_import_css)
                                    logger.debug(f"Parsed imported CSS: {len(import_css_text)} bytes")
                            except Exception as e:
                                logger.error(f"Error loading imported stylesheet {url}: {e}")
                
                # Add imported stylesheets to the main list
                if imported_stylesheets:
                    self.stylesheets.extend(imported_stylesheets)
            except Exception as e:
                logger.error(f"Error processing @import rules: {e}")
            
            logger.debug(f"Processed {len(self.stylesheets)} total stylesheets")
        except Exception as e:
            logger.error(f"Error processing stylesheets: {e}")
    
    def _load_resources(self, base_url: str) -> None:
        """
        Load resources like images, fonts, etc.
        
        Args:
            base_url: Base URL for resolving relative URLs
        """
        if self.text_only_mode:
            logger.debug("Text-only mode, skipping resource loading")
            return
        
        try:
            # Reset resources dictionary
            self.resources = {
                'images': {},
                'videos': {},
                'audio': {},
                'fonts': {},
                'iframes': {}
            }
            
            # Process images
            for img in self.dom.find_all('img'):
                src = img.get('src')
                if not src:
                    continue
                    
                # Ignore data URLs
                if src.startswith('data:'):
                    continue
                    
                # Resolve relative URL
                abs_url = urllib.parse.urljoin(base_url, src)
                
                # Fix URL for Google logo and other common resources
                if 'google.com' in base_url and 'googlelogo' in abs_url:
                    # Google's logo URL structure may be different
                    # Try with www subdomain and check relative paths
                    if abs_url.startswith('https://google.com/'):
                        abs_url = abs_url.replace('https://google.com/', 'https://www.google.com/')
                
                # Check if it should be blocked
                if self.ad_blocker and self.ad_blocker.should_block_url(abs_url):
                    logger.info(f"Blocking image: {abs_url}")
                    img['src'] = ''  # Remove the source
                    img['alt'] = '[Blocked]'  # Set alt text
                    continue
                
                # Check if already loaded
                if abs_url in self.resources['images']:
                    continue
                    
                logger.debug(f"Loading image: {abs_url}")
                
                # Use the network manager to make the request
                try:
                    # First check if we have it in cache
                    cached_image = self.cache.get(abs_url)
                    if cached_image:
                        self.resources['images'][abs_url] = {
                            'data': cached_image,
                            'content_type': 'image/*',  # Assume image
                            'from_cache': True
                        }
                    else:
                        # Try to load the image directly first without HEAD request
                        # since some servers might block HEAD requests
                        try:
                            response = self.network.get(abs_url)
                            
                            # Check if it's an image based on Content-Type
                            content_type = response.headers.get('Content-Type', '')
                            if not content_type.startswith('image/'):
                                logger.warning(f"Resource {abs_url} is not an image (content-type: {content_type})")
                                
                                # Try an alternative URL if it's a well-known resource
                                if 'google.com' in base_url and 'googlelogo' in abs_url:
                                    # Try common Google image paths
                                    alt_urls = [
                                        'https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_92x30dp.png',
                                        'https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_160x56dp.png',
                                        'https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png'
                                    ]
                                    
                                    for alt_url in alt_urls:
                                        try:
                                            alt_response = self.network.get(alt_url)
                                            alt_content_type = alt_response.headers.get('Content-Type', '')
                                            
                                            if alt_content_type.startswith('image/'):
                                                # Found a working alternative
                                                response = alt_response
                                                content_type = alt_content_type
                                                abs_url = alt_url
                                                logger.info(f"Used alternative Google logo URL: {alt_url}")
                                                break
                                        except Exception:
                                            continue
                                else:
                                    continue
                            
                            # Cache the response
                            if not self.private_mode:
                                self.cache.set(abs_url, response.content)
                                
                            self.resources['images'][abs_url] = {
                                'data': response.content,
                                'content_type': content_type,
                                'from_cache': False
                            }
                        except Exception as e:
                            logger.warning(f"Error getting image {abs_url}: {e}")
                except Exception as e:
                    logger.warning(f"Error loading image {abs_url}: {e}")
            
            # Process videos
            for video in self.dom.find_all('video'):
                # Handle direct src attribute
                src = video.get('src')
                if src:
                    # Resolve relative URL
                    abs_url = urllib.parse.urljoin(base_url, src)
                    
                    # Check if it should be blocked
                    if self.ad_blocker and self.ad_blocker.should_block_url(abs_url):
                        logger.info(f"Blocking video: {abs_url}")
                        video['src'] = ''  # Remove the source
                        continue
                    
                    logger.debug(f"Video source found: {abs_url}")
                    # We don't preload videos, just note it
                    self.resources['videos'][abs_url] = {
                        'data': None,  # Videos aren't preloaded
                        'content_type': 'video/*',  # Assume video
                        'from_cache': False
                    }
                
                # Process source tags inside video elements
                for source in video.find_all('source'):
                    source_src = source.get('src')
                    if not source_src:
                        continue
                        
                    # Skip data URLs
                    if source_src.startswith('data:'):
                        continue
                        
                    # Resolve relative URL
                    abs_source_url = urllib.parse.urljoin(base_url, source_src)
                    
                    # Check if it should be blocked
                    if self.ad_blocker and self.ad_blocker.should_block_url(abs_source_url):
                        logger.info(f"Blocking video source: {abs_source_url}")
                        source['src'] = ''  # Remove the source
                        continue
                    
                    # Check if already noted
                    if abs_source_url in self.resources['videos']:
                        continue
                        
                    logger.debug(f"Video source element found: {abs_source_url}")
                    
                    # Get the media type
                    media_type = source.get('type', 'video/*')
                    
                    # Note the source, don't preload
                    self.resources['videos'][abs_source_url] = {
                        'data': None,  # Videos aren't preloaded
                        'content_type': media_type,
                        'from_cache': False
                    }
                
                # Process poster if available
                poster = video.get('poster')
                if poster:
                    # Resolve relative URL
                    abs_poster_url = urllib.parse.urljoin(base_url, poster)
                    
                    # Check if it should be blocked
                    if self.ad_blocker and self.ad_blocker.should_block_url(abs_poster_url):
                        logger.info(f"Blocking video poster: {abs_poster_url}")
                        video['poster'] = ''  # Remove the poster
                        continue
                        
                    # Check if already loaded
                    if abs_poster_url in self.resources['images']:
                        continue
                    
                    logger.debug(f"Loading video poster: {abs_poster_url}")
                    
                    # Load the poster image
                    try:
                        # First check if we have it in cache
                        cached_poster = self.cache.get(abs_poster_url)
                        if cached_poster:
                            self.resources['images'][abs_poster_url] = {
                                'data': cached_poster,
                                'content_type': 'image/*',  # Assume image
                                'from_cache': True
                            }
                        else:
                            # Make the request
                            response = self.network.get(abs_poster_url)
                            
                            # Cache the response
                            if not self.private_mode:
                                self.cache.set(abs_poster_url, response.content)
                                
                            self.resources['images'][abs_poster_url] = {
                                'data': response.content,
                                'content_type': response.headers.get('Content-Type', 'image/*'),
                                'from_cache': False
                            }
                    except Exception as e:
                        logger.warning(f"Error loading video poster {abs_poster_url}: {e}")
            
            # Process audio
            for audio in self.dom.find_all('audio'):
                # Handle direct src attribute
                src = audio.get('src')
                if src:
                    # Resolve relative URL
                    abs_url = urllib.parse.urljoin(base_url, src)
                    
                    # Check if it should be blocked
                    if self.ad_blocker and self.ad_blocker.should_block_url(abs_url):
                        logger.info(f"Blocking audio: {abs_url}")
                        audio['src'] = ''  # Remove the source
                        continue
                    
                    logger.debug(f"Audio source found: {abs_url}")
                    # We don't preload audio, just note it
                    self.resources['audio'][abs_url] = {
                        'data': None,  # Audio isn't preloaded
                        'content_type': 'audio/*',  # Assume audio
                        'from_cache': False
                    }
                
                # Process source tags inside audio elements
                for source in audio.find_all('source'):
                    source_src = source.get('src')
                    if not source_src:
                        continue
                        
                    # Skip data URLs
                    if source_src.startswith('data:'):
                        continue
                        
                    # Resolve relative URL
                    abs_source_url = urllib.parse.urljoin(base_url, source_src)
                    
                    # Check if it should be blocked
                    if self.ad_blocker and self.ad_blocker.should_block_url(abs_source_url):
                        logger.info(f"Blocking audio source: {abs_source_url}")
                        source['src'] = ''  # Remove the source
                        continue
                    
                    # Check if already noted
                    if abs_source_url in self.resources['audio']:
                        continue
                        
                    logger.debug(f"Audio source element found: {abs_source_url}")
                    
                    # Get the media type
                    media_type = source.get('type', 'audio/*')
                    
                    # Note the source, don't preload
                    self.resources['audio'][abs_source_url] = {
                        'data': None,  # Audio isn't preloaded
                        'content_type': media_type,
                        'from_cache': False
                    }
            
            # Process iframes
            for iframe in self.dom.find_all('iframe'):
                src = iframe.get('src')
                if src:
                    # Resolve relative URL
                    abs_url = urllib.parse.urljoin(base_url, src)
                    
                    # Check if it should be blocked
                    if self.ad_blocker and self.ad_blocker.should_block_url(abs_url):
                        logger.info(f"Blocking iframe: {abs_url}")
                        iframe['src'] = ''  # Remove the source
                        continue
                    
                    logger.debug(f"Iframe source found: {abs_url}")
                    # We don't preload iframes, just note it
                    self.resources['iframes'][abs_url] = {
                        'data': None,  # Iframes aren't preloaded
                        'content_type': 'text/html',  # Assume HTML
                        'from_cache': False
                    }
            
            # Process CSS background images
            try:
                # Find elements with inline style containing background-image
                elements_with_bg = self.dom.select('[style*="background-image"]')
                for element in elements_with_bg:
                    style = element.get('style', '')
                    # Extract URL from background-image: url(...)
                    bg_match = re.search(r'background-image:\s*url\([\'"]?([^\'"]+)[\'"]?\)', style)
                    if bg_match:
                        bg_url = bg_match.group(1)
                        
                        # Skip data URLs
                        if bg_url.startswith('data:'):
                            continue
                            
                        # Resolve relative URL
                        abs_bg_url = urllib.parse.urljoin(base_url, bg_url)
                        
                        # Check if it should be blocked
                        if self.ad_blocker and self.ad_blocker.should_block_url(abs_bg_url):
                            logger.info(f"Blocking background image: {abs_bg_url}")
                            # Remove or replace the background image
                            element['style'] = re.sub(
                                r'background-image:\s*url\([\'"]?[^\'"]+[\'"]?\)', 
                                '', 
                                style
                            )
                            continue
                            
                        # Check if already loaded
                        if abs_bg_url in self.resources['images']:
                            continue
                            
                        logger.debug(f"Loading background image: {abs_bg_url}")
                        
                        # Load the background image
                        try:
                            # Check cache first
                            cached_bg = self.cache.get(abs_bg_url)
                            if cached_bg:
                                self.resources['images'][abs_bg_url] = {
                                    'data': cached_bg,
                                    'content_type': 'image/*',  # Assume image
                                    'from_cache': True
                                }
                            else:
                                # Make the request
                                response = self.network.get(abs_bg_url)
                                
                                # Cache the response
                                if not self.private_mode:
                                    self.cache.set(abs_bg_url, response.content)
                                    
                                self.resources['images'][abs_bg_url] = {
                                    'data': response.content,
                                    'content_type': response.headers.get('Content-Type', 'image/*'),
                                    'from_cache': False
                                }
                        except Exception as e:
                            logger.warning(f"Error loading background image {abs_bg_url}: {e}")
            except Exception as e:
                logger.error(f"Error processing CSS background images: {e}")
            
            # Process fonts
            try:
                # Find style sheets with @font-face
                for stylesheet in self.stylesheets:
                    # Use the helper method to get all @font-face rules
                    font_face_rules = self.css_parser.get_font_face_rules(stylesheet)
                    
                    for font_face_rule in font_face_rules:
                        # Extract the src property
                        src = None
                        try:
                            src = font_face_rule.style['src']
                        except (KeyError, IndexError):
                            continue
                            
                        if not src:
                            continue
                            
                        # Extract URLs from the src property
                        # Format can be url('font.woff') format('woff'), etc.
                        urls = re.findall(r'url\([\'"]?([^\'"]+)[\'"]?\)', src)
                        for url in urls:
                            # Skip data URLs
                            if url.startswith('data:'):
                                continue
                                
                            # Resolve relative URL
                            abs_url = urllib.parse.urljoin(base_url, url)
                            
                            # Check if it should be blocked
                            if self.ad_blocker and self.ad_blocker.should_block_url(abs_url):
                                logger.info(f"Blocking font: {abs_url}")
                                continue
                                
                            # Check if already loaded
                            if abs_url in self.resources['fonts']:
                                continue
                                
                            logger.debug(f"Loading font: {abs_url}")
                            
                            # Load the font
                            try:
                                # Check cache first
                                cached_font = self.cache.get(abs_url)
                                if cached_font:
                                    self.resources['fonts'][abs_url] = {
                                        'data': cached_font,
                                        'content_type': 'font/*',  # Assume font
                                        'from_cache': True
                                    }
                                else:
                                    # Make the request
                                    response = self.network.get(abs_url)
                                    
                                    # Cache the response
                                    if not self.private_mode:
                                        self.cache.set(abs_url, response.content)
                                        
                                    self.resources['fonts'][abs_url] = {
                                        'data': response.content,
                                        'content_type': response.headers.get('Content-Type', 'font/*'),
                                        'from_cache': False
                                    }
                            except Exception as e:
                                logger.warning(f"Error loading font {abs_url}: {e}")
            except Exception as e:
                logger.error(f"Error processing fonts: {e}")
                
            # Log resource loading summary
            total_resources = sum(len(resources) for resources in self.resources.values())
            logger.info(f"Loaded {total_resources} resources: " + 
                       f"{len(self.resources['images'])} images, " +
                       f"{len(self.resources['videos'])} videos, " +
                       f"{len(self.resources['audio'])} audio, " +
                       f"{len(self.resources['fonts'])} fonts, " +
                       f"{len(self.resources['iframes'])} iframes")
        except Exception as e:
            logger.error(f"Error loading resources: {e}")
    
    def _execute_scripts(self) -> None:
        """Execute JavaScript code in the DOM."""
        if self.text_only_mode:
            logger.debug("Text-only mode, skipping script execution")
            return
            
        # Execute scripts in a background thread
        thread = threading.Thread(target=self._execute_scripts_thread, daemon=True)
        thread.start()
    
    def _execute_scripts_thread(self) -> None:
        """Background thread for executing scripts."""
        try:
            # Skip if JavaScript is disabled
            if self.text_only_mode or self.js_disabled or not self.js_engine:
                return
            
            # Check if the JavaScript engine has event loop issues
            if hasattr(self.js_engine, 'event_loop_issues') and self.js_engine.event_loop_issues:
                logger.warning("JavaScript execution is disabled due to previous event loop issues")
                self.js_disabled = True
                return
            
            # Find all script elements in the DOM
            script_elements = self.dom.find_all('script')
            
            if not script_elements:
                return
            
            # Get all inline scripts and external scripts
            inline_scripts = []
            external_scripts = []
            
            for script in script_elements:
                script_type = script.get('type', '').lower()
                
                # Skip scripts with non-JavaScript types
                if script_type and script_type not in ('text/javascript', 'application/javascript', 'module', ''):
                    continue
                
                # Handle external scripts
                if script.has_attr('src'):
                    external_scripts.append(script)
                # Handle inline scripts (if not empty)
                elif script.string and script.string.strip():
                    inline_scripts.append(script)
            
            # First load all external scripts
            for script in external_scripts:
                src = script.get('src', '')
                if src:
                    # Resolve relative URLs
                    if not src.startswith(('http://', 'https://', 'data:', 'file:')):
                        src = urllib.parse.urljoin(self.current_url, src)
                    
                    # Skip if blocked by ad blocker
                    if self.ad_blocker and self.ad_blocker.should_block_url(src):
                        logger.debug(f"Blocked script load: {src}")
                        continue
                        
                    try:
                        # Fetch the script
                        response = self.network.get(src)
                        if response.status_code == 200:
                            script_content = response.text_decoded
                            
                            # Execute the script with the DOM
                            self._execute_script_with_dom(script_content)
                    except Exception as e:
                        logger.error(f"Error loading external script {src}: {e}")
            
            # Then execute all inline scripts
            for script in inline_scripts:
                try:
                    script_content = script.string
                    self._execute_script_with_dom(script_content)
                except Exception as e:
                    logger.error(f"Error executing inline script: {e}")
                
        except Exception as e:
            logger.error(f"Error executing scripts: {e}")
            # If we encounter a serious error, disable JavaScript to prevent
            # further issues and potential hangs
            if "attached to a different loop" in str(e) or "This event loop is already running" in str(e):
                logger.error("Disabling JavaScript due to event loop issues")
                self.js_disabled = True
    
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
    
    def _set_dom_from_html(self, html_content: str, url: str) -> None:
        """
        Set up the DOM from HTML content with robust encoding handling.
        
        Args:
            html_content: HTML content to parse
            url: Base URL for resolving relative URLs
        """
        try:
            # Parse HTML
            self.load_progress = 60
            self._notify_loading_state()
            
            # Parse the HTML content into a DOM
            self.dom = self.html_parser.parse(html_content, base_url=url)
            
            # Extract title
            title_tag = self.dom.find('title')
            self.page_title = title_tag.text if title_tag else url
            
            # Process stylesheets
            self.load_progress = 70
            self._notify_loading_state()
            self._process_stylesheets()
            
            # Download resources (images, etc.) unless in text-only mode
            text_only_mode = getattr(self, 'text_only_mode', False)
            if not text_only_mode:
                self.load_progress = 80
                self._notify_loading_state()
                self._load_resources(url)
                
            # Execute JavaScript unless in text-only mode or JavaScript is disabled
            js_disabled = getattr(self, 'js_disabled', False)
            if not text_only_mode and not js_disabled:
                self.load_progress = 90
                self._notify_loading_state()
                try:
                    self._execute_scripts()
                except Exception as e:
                    logger.error(f"JavaScript execution error: {e}")
                    # Continue loading even if JS fails
            
            # Update history
            self._update_history(url)
            
            # Finished loading
            self.load_progress = 100
            self.is_loading = False
            self._notify_loading_state()
            
            logger.info(f"Successfully loaded {url}")
            
        except Exception as e:
            logger.error(f"Error setting up DOM from HTML: {e}")
            self._handle_error_page(url, f"Error processing page: {e}")
    
    def _try_recover_corrupt_text(self, html_content: str) -> str:
        """
        Attempt to recover from corrupt text by applying various recovery techniques.
        
        Args:
            html_content: Potentially corrupt HTML content
            
        Returns:
            Recovered HTML content or original content if recovery fails
        """
        try:
            # Remove any null bytes or problematic control characters
            cleaned_content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', html_content)
            
            # If the content contains many replacement characters, try to identify patterns
            # and apply specific fixes for common encoding problems
            if '\ufffd' in cleaned_content:
                # Fix common UTF-8 to Windows-1252 confusion
                if cleaned_content.count('\ufffd') > len(cleaned_content) * 0.05:  # More than 5% are replacement chars
                    try:
                        # Try to re-encode as latin1 and then decode as utf-8
                        # This helps when UTF-8 content was incorrectly decoded as latin1/windows-1252
                        encoded = cleaned_content.encode('latin1', errors='replace')
                        recoded = encoded.decode('utf-8', errors='replace')
                        
                        # Only use this if it has fewer replacement characters
                        if recoded.count('\ufffd') < cleaned_content.count('\ufffd'):
                            logger.info("Re-encoding from latin1 to utf-8 improved text quality")
                            cleaned_content = recoded
                    except Exception as e:
                        logger.debug(f"Re-encoding attempt failed: {e}")
            
            # Try to fix broken html entities
            pattern = r'&[a-zA-Z]{2,8};'  # Match potential HTML entities
            for entity_match in re.finditer(pattern, cleaned_content):
                entity = entity_match.group(0)
                if entity not in html.entities.entitydefs:
                    # This might be a broken entity, try to fix common issues
                    fixed_entity = entity.lower()  # Try lowercase version
                    if fixed_entity in html.entities.entitydefs:
                        cleaned_content = cleaned_content.replace(entity, fixed_entity)
            
            # If we have html5lib available, try to parse and re-serialize the HTML
            # which can fix many structural problems
            try:
                import html5lib
                parsed = html5lib.parse(cleaned_content)
                from xml.etree import ElementTree
                buffer = io.StringIO()
                ElementTree.ElementTree(parsed).write(buffer, encoding='unicode', method='html')
                cleaned_html = buffer.getvalue()
                
                # Only use if it's substantially similar in length to avoid losing content
                if len(cleaned_html) > len(cleaned_content) * 0.8:
                    cleaned_content = cleaned_html
                    logger.info("Used html5lib to clean and restructure corrupt HTML")
            except (ImportError, Exception) as e:
                logger.debug(f"html5lib cleaning failed: {e}")
            
            return cleaned_content
        except Exception as e:
            logger.error(f"Failed to recover corrupt text: {e}")
            return html_content  # Return original if recovery fails 

    def _handle_binary_content(self, url: str, content_type: str) -> None:
        """
        Handle binary content like images or PDFs by showing an appropriate message.
        
        Args:
            url: URL of the binary content
            content_type: Content-Type of the binary content
        """
        logger.info(f"Detected binary content ({content_type}) at URL: {url}")
        
        content_type_name = content_type.split('/')[1] if '/' in content_type else content_type
        
        # Create a simple HTML page to display information about the binary content
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Binary Content - {content_type}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                h1 {{ color: #333; }}
                .info {{ background-color: #f8f9fa; padding: 15px; border-radius: 4px; }}
                .url {{ word-break: break-all; font-family: monospace; background: #eee; padding: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Binary Content Detected</h1>
                <p>This browser cannot display binary content of type: <strong>{content_type}</strong></p>
                <div class="info">
                    <p><strong>Content Type:</strong> {content_type}</p>
                    <p><strong>URL:</strong></p>
                    <div class="url">{url}</div>
                </div>
                <p>To view this content, you may need to download it and open with an appropriate application.</p>
            </div>
        </body>
        </html>
        """
        
        # Set the DOM from this HTML
        self._set_dom_from_html(html, url) 

    def _execute_script_with_dom(self, script_content: str) -> None:
        """
        Execute a script with the current DOM.
        
        Args:
            script_content: JavaScript code to execute
        """
        try:
            # Skip if JavaScript is disabled
            if self.text_only_mode or self.js_disabled or not self.js_engine:
                return
            
            # Check if the JavaScript engine has event loop issues
            if hasattr(self.js_engine, 'event_loop_issues') and self.js_engine.event_loop_issues:
                logger.warning("JavaScript execution is disabled due to previous event loop issues")
                self.js_disabled = True
                return
            
            # Execute the script with the DOM
            result = self.js_engine.execute_js_with_dom(script_content, str(self.dom))
            
            # Check for errors
            if result and "error" in result and result["error"]:
                error_message = result["error"]
                logger.error(f"Error executing JavaScript: {error_message}")
                
                # Check for event loop issues and disable JS if needed
                if "attached to a different loop" in error_message or "This event loop is already running" in error_message:
                    logger.error("Disabling JavaScript due to event loop issues")
                    self.js_disabled = True
                    
                    if hasattr(self.js_engine, 'event_loop_issues'):
                        self.js_engine.event_loop_issues = True
        except Exception as e:
            logger.error(f"Exception executing JavaScript: {e}")
            
            # Check for event loop issues and disable JS if needed
            if "attached to a different loop" in str(e) or "This event loop is already running" in str(e):
                logger.error("Disabling JavaScript due to event loop issues")
                self.js_disabled = True
                
                if hasattr(self.js_engine, 'event_loop_issues'):
                    self.js_engine.event_loop_issues = True 