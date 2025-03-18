"""
Core HTML5 Engine implementation.

This module provides the main HTML5Engine class that integrates the DOM,
CSS parsing, layout, and rendering components into a complete HTML5 rendering engine.
"""

import os
import logging
import tempfile
import urllib.parse
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse

# Import DOM components
from browser_engine.html5_engine.dom import Document, Element, Parser, MarkdownDOMCreator

# Import CSS components
from browser_engine.html5_engine.css import CSSParser, LayoutEngine

# Import rendering components
from browser_engine.html5_engine.rendering import HTML5Renderer

logger = logging.getLogger(__name__)

class HTML5Engine:
    """
    HTML5 Engine integrates DOM parsing, CSS handling, and rendering.
    
    This class provides the core functionality of the HTML5 rendering engine,
    tying together DOM parsing, CSS processing, layout calculation, and rendering.
    """
    
    def __init__(self):
        """Initialize the HTML5 Engine."""
        # Initialize parsers
        self.dom_parser = Parser()
        self.css_parser = CSSParser()
        self.markdown_dom_creator = MarkdownDOMCreator()
        
        # Initialize layout engine
        self.layout_engine = LayoutEngine()
        
        # Current document state
        self.document: Optional[Document] = None
        self.base_url: Optional[str] = None
        self.title: str = ""
        self.resources: Dict[str, bytes] = {}
        self.renderer: Optional[HTML5Renderer] = None
        
        # Loading state
        self.is_loading: bool = False
        self.load_error: Optional[str] = None
        
        # Event callbacks
        self.on_page_load_callback = None
        self.on_page_error_callback = None
        self.on_title_change_callback = None
        self.on_link_click_callback = None
        
        # Initialize CSS state
        self.css_parser.reset()  # Reset CSS parser state
        self.css_parser.add_default_styles()  # Add default styles
        
        logger.info("HTML5 Engine initialized")
    
    def attach_renderer(self, renderer: HTML5Renderer) -> None:
        """
        Attach a renderer to the engine.
        
        Args:
            renderer: The HTML5Renderer instance to use for rendering
        """
        self.renderer = renderer
        
        # Set the engine reference in the renderer
        if hasattr(renderer, 'set_engine'):
            renderer.set_engine(self)
        
        # Set the base URL in the renderer
        if hasattr(renderer, 'current_url') and self.base_url:
            renderer.current_url = self.base_url
        
        logger.info("Renderer attached to HTML5 Engine")
    
    def initialize_renderer(self, parent_frame) -> None:
        """
        Initialize the renderer with a parent frame.
        
        Args:
            parent_frame: Parent Tkinter frame for rendering
        """
        # Create a new renderer
        renderer = HTML5Renderer(parent_frame)
        
        # Attach the renderer to the engine
        self.attach_renderer(renderer)
        
        logger.info("HTML5Renderer initialized")
    
    def load_url(self, url: str) -> bool:
        """
        Load a URL and render its content.
        
        Args:
            url: The URL to load
            
        Returns:
            True if loading was successful, False otherwise
        """
        try:
            # Check if URL is None
            if url is None:
                error_msg = "Cannot load URL: URL is None"
                logger.error(error_msg)
                self.is_loading = False
                self.load_error = error_msg
                
                # Fire error event
                if self.on_page_error_callback:
                    self.on_page_error_callback(error_msg)
                
                return False
            
            logger.info(f"Loading URL: {url}")
            self.is_loading = True
            self.load_error = None
            
            # Store the URL immediately to avoid it getting lost
            self.base_url = url
            
            # Handle special URL schemes
            if url.startswith("about:"):
                return self._handle_about_url(url)
            elif url.startswith("data:"):
                return self._handle_data_url(url)
            elif url.startswith("javascript:"):
                # Just ignore javascript URLs for now
                logger.warning("JavaScript URLs are not supported")
                self.is_loading = False
                return False
            
            # Import here to avoid circular imports
            from browser_engine.network.network_manager import NetworkManager
            
            # Get network manager
            network_manager = NetworkManager()
            
            # Fetch content from URL with proper error handling
            try:
                response = network_manager.get(url)
                
                # Check for successful response
                if response.status_code == 200:
                    # Get content using robust decoder
                    html_content = network_manager.get_decoded_text(response)
                    
                    # Debug: Print first 500 chars of HTML content
                    logger.debug(f"HTML content from URL (first 500 chars): {html_content[:500]}...")
                    
                    # Base URL was already set above, make sure renderer has it too
                    if self.renderer and hasattr(self.renderer, 'current_url'):
                        self.renderer.current_url = url
                    
                    # Load HTML content
                    return self.load_html(html_content, url)
                else:
                    # Handle error response
                    error_msg = f"HTTP Error: {response.status_code} - {response.reason}"
                    logger.error(f"Error loading URL: {error_msg}")
                    self.is_loading = False
                    self.load_error = error_msg
                    
                    # Fire error event
                    if self.on_page_error_callback:
                        self.on_page_error_callback(error_msg)
                    
                    return False
                    
            except Exception as e:
                error_msg = f"Network error: {str(e)}"
                logger.error(f"Network error loading URL: {error_msg}")
                self.is_loading = False
                self.load_error = error_msg
                
                # Fire error event
                if self.on_page_error_callback:
                    self.on_page_error_callback(error_msg)
                
                return False
                
        except Exception as e:
            error_msg = f"Error loading URL: {str(e)}"
            logger.error(error_msg)
            self.is_loading = False
            self.load_error = error_msg
            
            # Fire error event
            if self.on_page_error_callback:
                self.on_page_error_callback(error_msg)
            
            return False
    
    def _handle_about_url(self, url: str) -> bool:
        """
        Handle special about: URLs.
        
        Args:
            url: The about: URL to handle
            
        Returns:
            True if handling was successful, False otherwise
        """
        # Handle about:blank - create an empty page
        if url == "about:blank":
            logger.info("Loading empty page (about:blank)")
            empty_html = """<!DOCTYPE html>
            <html>
            <head><title>New Page</title></head>
            <body></body>
            </html>"""
            
            # Set base URL
            self.base_url = url
            
            # Update the renderer URL if available
            if self.renderer and hasattr(self.renderer, 'current_url'):
                self.renderer.current_url = url
            
            # Load the empty HTML
            return self.load_html(empty_html, url)
        
        # Handle about:version - show browser version info
        elif url == "about:version":
            logger.info("Loading version page (about:version)")
            import platform
            import sys
            
            version_html = f"""<!DOCTYPE html>
            <html>
            <head><title>Browser Version</title></head>
            <body>
                <h1>Wink Browser Engine</h1>
                <p>Version: 0.1.0</p>
                <p>Python: {sys.version}</p>
                <p>Platform: {platform.platform()}</p>
            </body>
            </html>"""
            
            # Set base URL
            self.base_url = url
            
            # Update the renderer URL if available
            if self.renderer and hasattr(self.renderer, 'current_url'):
                self.renderer.current_url = url
            
            # Load the version HTML
            return self.load_html(version_html, url)
            
        # Handle about:debug - show debug info
        elif url == "about:debug":
            logger.info("Loading debug page (about:debug)")
            import platform
            import sys
            
            # Get renderer info
            renderer_info = "Not initialized"
            if self.renderer:
                renderer_info = str(type(self.renderer))
            
            # Get document info
            document_info = "No document loaded"
            if self.document:
                document_info = f"Document with {len(self.document.getElementsByTagName('*'))} elements"
            
            debug_html = f"""<!DOCTYPE html>
            <html>
            <head><title>Debug Information</title></head>
            <body>
                <h1>Debug Information</h1>
                <h2>System</h2>
                <ul>
                    <li>Python: {sys.version}</li>
                    <li>Platform: {platform.platform()}</li>
                </ul>
                <h2>Engine</h2>
                <ul>
                    <li>Base URL: {self.base_url}</li>
                    <li>Renderer: {renderer_info}</li>
                    <li>Document: {document_info}</li>
                </ul>
            </body>
            </html>"""
            
            # Set base URL
            self.base_url = url
            
            # Update the renderer URL if available
            if self.renderer and hasattr(self.renderer, 'current_url'):
                self.renderer.current_url = url
            
            # Load the debug HTML
            return self.load_html(debug_html, url)
        
        # Unsupported about: URL
        else:
            logger.warning(f"Unsupported about: URL: {url}")
            error_html = f"""<!DOCTYPE html>
            <html>
            <head><title>Error</title></head>
            <body>
                <h1>Unsupported URL</h1>
                <p>The URL '{url}' is not supported.</p>
                <p>Try one of these:</p>
                <ul>
                    <li><a href="about:blank">about:blank</a> - Empty page</li>
                    <li><a href="about:version">about:version</a> - Browser version info</li>
                    <li><a href="about:debug">about:debug</a> - Debug mode</li>
                </ul>
            </body>
            </html>"""
            
            # Set base URL 
            self.base_url = url
            
            # Update the renderer URL if available
            if self.renderer and hasattr(self.renderer, 'current_url'):
                self.renderer.current_url = url
            
            # Load the error HTML with the original URL to preserve it
            return self.load_html(error_html, url)
    
    def _handle_data_url(self, url: str) -> bool:
        """
        Handle data: URLs.
        
        Args:
            url: The data: URL to handle
            
        Returns:
            True if handling was successful, False otherwise
        """
        try:
            logger.info("Loading data: URL")
            import base64
            import urllib.parse
            
            # Parse the data URL
            # Format: data:[<mediatype>][;base64],<data>
            url_parts = url[5:].split(',', 1)
            if len(url_parts) != 2:
                logger.error("Invalid data: URL format")
                return False
            
            metadata, data = url_parts
            
            # Determine if it's base64 encoded and get the mime type
            is_base64 = False
            mime_type = 'text/plain'
            
            if ';' in metadata:
                mime_parts = metadata.split(';')
                mime_type = mime_parts[0] or 'text/plain'
                is_base64 = 'base64' in mime_parts
            elif metadata:
                mime_type = metadata
            
            # Decode the data
            if is_base64:
                try:
                    content = base64.b64decode(data).decode('utf-8')
                except Exception as e:
                    logger.error(f"Error decoding base64 data: {e}")
                    return False
            else:
                content = urllib.parse.unquote(data)
            
            # If it's HTML, load directly
            if mime_type == 'text/html':
                self.base_url = url
                return self.load_html(content, url)
            
            # For other types, wrap in HTML
            html_wrapper = f"""<!DOCTYPE html>
            <html>
            <head><title>Data URL</title></head>
            <body>
                <pre>{content}</pre>
            </body>
            </html>"""
            
            self.base_url = url
            return self.load_html(html_wrapper, url)
            
        except Exception as e:
            logger.error(f"Error handling data: URL: {e}")
            return False
    
    def load_html(self, html_content: str, base_url: Optional[str] = None) -> bool:
        """
        Load HTML content into the engine.
        
        Args:
            html_content: The HTML content to load
            base_url: Optional base URL for resolving relative URLs
            
        Returns:
            True if loading was successful, False otherwise
        """
        try:
            self.is_loading = True
            self.load_error = None
            self.base_url = base_url
            
            # Create document using markdown DOM creator
            self.document = self.markdown_dom_creator.create_dom(html_content, base_url)
            
            # Update title
            if self.document and self.document.title:
                self.title = self.document.title
                if self.on_title_change_callback:
                    self.on_title_change_callback(self.title)
            
            # Notify page load complete
            self.is_loading = False
            if self.on_page_load_callback:
                self.on_page_load_callback()
                
            return True
            
        except Exception as e:
            logger.error(f"Error loading HTML: {e}")
            self.load_error = str(e)
            self.is_loading = False
            if self.on_page_error_callback:
                self.on_page_error_callback(str(e))
            return False
    
    def _preload_resources(self) -> None:
        """Preload external resources like images, scripts, and stylesheets."""
        if not self.document:
            return
            
        try:
            # Process all external stylesheets (link elements)
            self._preload_stylesheets()
            
            # Process all script elements
            self._preload_scripts()
            
            # Process all image elements
            self._preload_images()
            
            # Process all iframe elements
            self._preload_iframes()
            
            logger.debug("External resources preloaded")
            
        except Exception as e:
            logger.error(f"Error preloading resources: {e}", exc_info=True)
    
    def _preload_stylesheets(self) -> None:
        """Preload external stylesheets."""
        if not self.document:
            return
            
        link_elements = self.document.querySelectorAll("link[rel='stylesheet']")
        processed_urls = set()
        
        for link in link_elements:
            href = link.getAttribute("href")
            if not href or href in processed_urls:
                continue
                
            processed_urls.add(href)
            
            # Skip if already loaded
            if href in self.resources:
                continue
                
            # Resolve URL
            full_url = href if href.startswith(('http://', 'https://', 'data:', '//')) else urllib.parse.urljoin(self.base_url, href)
            
            # Request stylesheet
            try:
                # Import here to avoid circular imports
                from browser_engine.network.network_manager import NetworkManager
                
                # Use network manager to fetch resource
                response = NetworkManager().get(full_url)
                if response.status_code == 200:
                    self.resources[href] = response.content
                    logger.debug(f"Stylesheet loaded: {href}")
            except Exception as e:
                logger.error(f"Error loading stylesheet {href}: {e}")
    
    def _preload_scripts(self) -> None:
        """Preload external scripts."""
        if not self.document:
            return
            
        script_elements = self.document.querySelectorAll("script[src]")
        processed_urls = set()
        
        for script in script_elements:
            src = script.getAttribute("src")
            if not src or src in processed_urls:
                continue
                
            processed_urls.add(src)
            
            # Skip if already loaded
            if src in self.resources:
                continue
                
            # Resolve URL
            full_url = src if src.startswith(('http://', 'https://', 'data:', '//')) else urllib.parse.urljoin(self.base_url, src)
            
            # Request script
            try:
                # Import here to avoid circular imports
                from browser_engine.network.network_manager import NetworkManager
                
                # Use network manager to fetch resource
                response = NetworkManager().get(full_url)
                if response.status_code == 200:
                    self.resources[src] = response.content
                    logger.debug(f"Script loaded: {src}")
            except Exception as e:
                logger.error(f"Error loading script {src}: {e}")
    
    def _preload_images(self) -> None:
        """Preload images."""
        if not self.document:
            return
            
        img_elements = self.document.querySelectorAll("img[src]")
        processed_urls = set()
        
        for img in img_elements:
            src = img.getAttribute("src")
            if not src or src in processed_urls:
                continue
                
            processed_urls.add(src)
            
            # Skip if already loaded
            if src in self.resources:
                continue
                
            # Skip data URLs
            if src.startswith('data:'):
                continue
                
            # Resolve URL
            full_url = src if src.startswith(('http://', 'https://', 'data:', '//')) else urllib.parse.urljoin(self.base_url, src)
            
            # Request image
            try:
                # Import here to avoid circular imports
                from browser_engine.network.network_manager import NetworkManager
                
                # Use network manager to fetch resource
                response = NetworkManager().get(full_url)
                if response.status_code == 200:
                    self.resources[src] = response.content
                    logger.debug(f"Image loaded: {src}")
            except Exception as e:
                logger.error(f"Error loading image {src}: {e}")
    
    def _preload_iframes(self) -> None:
        """Preload iframe content."""
        if not self.document:
            return
            
        iframe_elements = self.document.querySelectorAll("iframe[src]")
        processed_urls = set()
        
        for iframe in iframe_elements:
            src = iframe.getAttribute("src")
            if not src or src in processed_urls:
                continue
                
            processed_urls.add(src)
            
            # Skip if already loaded
            if src in self.resources:
                continue
                
            # Skip about URLs and javascript URLs
            if src.startswith(('about:', 'javascript:')):
                continue
                
            # Resolve URL
            full_url = src if src.startswith(('http://', 'https://', 'data:', '//')) else urllib.parse.urljoin(self.base_url, src)
            
            # Request iframe content
            try:
                # Import here to avoid circular imports
                from browser_engine.network.network_manager import NetworkManager
                
                # Use network manager to fetch resource
                response = NetworkManager().get(full_url)
                if response.status_code == 200:
                    self.resources[src] = response.content
                    logger.debug(f"Iframe content loaded: {src}")
            except Exception as e:
                logger.error(f"Error loading iframe content {src}: {e}")
    
    def _process_css(self) -> None:
        """Process CSS for the current document."""
        if not self.document:
            return
            
        try:
            # Reset CSS parser state to avoid duplicated rules
            self.css_parser.reset()
            
            # Add default styles
            self.css_parser.add_default_styles()
            
            # Process style elements
            try:
                # Get all style elements
                style_elements = []
                
                # Find style elements manually to avoid selector engine issues
                def find_style_elements(node):
                    if hasattr(node, 'tag_name') and node.tag_name.lower() == 'style':
                        style_elements.append(node)
                    
                    if hasattr(node, 'child_nodes'):
                        for child in node.child_nodes:
                            find_style_elements(child)
                
                # Start search from document element
                if self.document.document_element:
                    find_style_elements(self.document.document_element)
                
                # Debug the type of style elements
                logger.debug(f"Found {len(style_elements)} style elements")
                
                # Process each style element
                for style_element in style_elements:
                    try:
                        # Get CSS content
                        css_content = None
                        
                        # Try different ways to get the content
                        if hasattr(style_element, 'style_content') and style_element.style_content:
                            css_content = style_element.style_content
                        elif hasattr(style_element, 'textContent') and style_element.textContent:
                            css_content = style_element.textContent
                        elif hasattr(style_element, 'text_content') and style_element.text_content:
                            css_content = style_element.text_content
                        elif hasattr(style_element, 'child_nodes'):
                            # Try to get content from child text nodes
                            for child in style_element.child_nodes:
                                if hasattr(child, 'node_type') and child.node_type == 3:  # TEXT_NODE
                                    if hasattr(child, 'data'):
                                        css_content = child.data
                                        break
                                    elif hasattr(child, 'node_value'):
                                        css_content = child.node_value
                                        break
                        
                        # Skip if no content
                        if not css_content or not isinstance(css_content, str) or not css_content.strip():
                            logger.warning(f"Style element has no valid content")
                            continue
                        
                        # Parse the CSS content
                        parsed_rules = self.css_parser.parse(css_content)
                        
                        # Add these rules to the CSS parser
                        if parsed_rules:
                            # Add to stylesheets list
                            self.css_parser.stylesheets.append(parsed_rules)
                            
                            # Update the combined style_rules
                            for selector, props in parsed_rules.items():
                                if selector in self.css_parser.style_rules:
                                    self.css_parser.style_rules[selector].update(props)
                                else:
                                    self.css_parser.style_rules[selector] = props.copy()
                                    
                    except Exception as e:
                        logger.error(f"Error processing style element: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error processing style elements: {e}")
            
            # Process link elements (external stylesheets)
            try:
                # Get all link elements for stylesheets
                link_elements = []
                
                # Find link elements manually to avoid selector engine issues
                def find_link_elements(node):
                    if (hasattr(node, 'tag_name') and node.tag_name.lower() == 'link' and
                        hasattr(node, 'get_attribute') and 
                        node.get_attribute('rel') and 
                        node.get_attribute('rel').lower() == 'stylesheet'):
                        link_elements.append(node)
                    
                    if hasattr(node, 'child_nodes'):
                        for child in node.child_nodes:
                            find_link_elements(child)
                
                # Start search from document element
                if self.document.document_element:
                    find_link_elements(self.document.document_element)
                
                processed_urls = set()
                
                for link_element in link_elements:
                    try:
                        # Check if link_element is valid before accessing properties
                        if not hasattr(link_element, 'get_attribute'):
                            logger.warning(f"Link element has no get_attribute method: {type(link_element)}")
                            continue
                            
                        href = link_element.get_attribute('href')
                        if not href or href in processed_urls:
                            continue
                            
                        processed_urls.add(href)
                        
                        # If we already have this resource, use it
                        if href in self.resources:
                            try:
                                css_content = self.resources[href].decode('utf-8', errors='replace')
                                if css_content and css_content.strip():
                                    # Parse the CSS content
                                    parsed_rules = self.css_parser.parse(css_content)
                                    
                                    # Add these rules to the CSS parser
                                    if parsed_rules:
                                        # Add to stylesheets list
                                        self.css_parser.stylesheets.append(parsed_rules)
                                        
                                        # Update the combined style_rules
                                        for selector, props in parsed_rules.items():
                                            if selector in self.css_parser.style_rules:
                                                self.css_parser.style_rules[selector].update(props)
                                            else:
                                                self.css_parser.style_rules[selector] = props.copy()
                            except Exception as decode_err:
                                logger.error(f"Error decoding stylesheet content: {decode_err}")
                        else:
                            # Fetch the stylesheet
                            try:
                                # Resolve relative URL if needed
                                full_url = href
                                if self.document.url and not href.startswith(('http://', 'https://', '//')):
                                    from urllib.parse import urljoin
                                    full_url = urljoin(self.document.url, href)
                                
                                # Fetch the stylesheet
                                with urllib.request.urlopen(full_url) as response:
                                    css_content = response.read().decode('utf-8', errors='replace')
                                    
                                    # Store in resources for future use
                                    self.resources[href] = css_content.encode('utf-8')
                                    
                                    if css_content and css_content.strip():
                                        # Parse the CSS content
                                        parsed_rules = self.css_parser.parse(css_content)
                                        
                                        # Add these rules to the CSS parser
                                        if parsed_rules:
                                            # Add to stylesheets list
                                            self.css_parser.stylesheets.append(parsed_rules)
                                            
                                            # Update the combined style_rules
                                            for selector, props in parsed_rules.items():
                                                if selector in self.css_parser.style_rules:
                                                    self.css_parser.style_rules[selector].update(props)
                                                else:
                                                    self.css_parser.style_rules[selector] = props.copy()
                            except Exception as fetch_err:
                                logger.error(f"Error fetching stylesheet {full_url}: {fetch_err}")
                    except Exception as link_err:
                        logger.error(f"Error processing individual link element: {link_err}")
                        
                logger.info("Processing link elements completed")
            except Exception as link_err:
                logger.error(f"Error processing link elements: {link_err}")
                
        except Exception as e:
            logger.error(f"Error processing CSS: {e}")
    
    def _calculate_layout(self) -> None:
        """Calculate layout for the current document."""
        if not self.document:
            return
        
        try:
            # Ensure the layout is properly calculated before rendering
            self.layout_engine.clear()
            
            # Calculate layout
            self.layout_tree = self.layout_engine.calculate_layout(self.document)
            
            logger.debug("Layout calculation completed")
        except Exception as e:
            logger.error(f"Error calculating layout: {e}", exc_info=True)
            self.layout_tree = None
    
    def render(self, viewport_width: int, viewport_height: int) -> None:
        """
        Render the current document.
        
        Args:
            viewport_width: Width of the viewport
            viewport_height: Height of the viewport
        """
        if not self.document or not self.renderer:
            return
            
        try:
            # Calculate layout
            layout_tree = self.layout_engine.create_layout(
                self.document,
                viewport_width,
                viewport_height
            )
            
            # Render the layout tree
            self.renderer.render(layout_tree)
            
        except Exception as e:
            logger.error(f"Error rendering document: {e}")
            if self.on_page_error_callback:
                self.on_page_error_callback(str(e))
    
    def handle_link_click(self, href: str) -> bool:
        """
        Handle a link click.
        
        Args:
            href: The URL to navigate to
            
        Returns:
            True if the link was handled internally, False if it should be handled externally
        """
        if not href:
            return False
        
        # Check if this is an internal anchor link
        if href.startswith("#") and self.document:
            # Handle anchor navigation
            try:
                anchor_id = href[1:]
                element = self.document.getElementById(anchor_id)
                if element and self.renderer:
                    # Scroll to element
                    self.renderer.scroll_to_element(element)
                    return True
            except Exception as e:
                logger.error(f"Error handling anchor link: {e}")
                return False
        
        # Call the link click callback if available
        if self.on_link_click_callback:
            return self.on_link_click_callback(href)
            
        return False
    
    def add_resource(self, url: str, content: bytes) -> None:
        """
        Add a resource to the engine.
        
        Args:
            url: The URL of the resource
            content: The content of the resource
        """
        self.resources[url] = content
        logger.debug(f"Resource added: {url}")
    
    def get_resource(self, url: str) -> Optional[bytes]:
        """
        Get a resource from the engine.
        
        Args:
            url: The URL of the resource
            
        Returns:
            The content of the resource, or None if not found
        """
        return self.resources.get(url)
    
    def clear_resources(self) -> None:
        """Clear all resources."""
        self.resources.clear()
        logger.debug("All resources cleared")
    
    def set_on_page_load(self, callback) -> None:
        """
        Set the callback for page load events.
        
        Args:
            callback: Function to call when a page is loaded
        """
        self.on_page_load_callback = callback
    
    def set_on_page_error(self, callback) -> None:
        """
        Set the callback for page error events.
        
        Args:
            callback: Function to call when a page has an error
        """
        self.on_page_error_callback = callback
    
    def set_on_title_change(self, callback) -> None:
        """
        Set the callback for title change events.
        
        Args:
            callback: Function to call when the page title changes
        """
        self.on_title_change_callback = callback
    
    def set_on_link_click(self, callback) -> None:
        """
        Set the callback for link click events.
        
        Args:
            callback: Function to call when a link is clicked
        """
        self.on_link_click_callback = callback
    
    def get_title(self) -> str:
        """
        Get the current document title.
        
        Returns:
            The document title
        """
        return self.title
    
    def get_base_url(self) -> str:
        """
        Get the base URL of the current document.
        
        Returns:
            The base URL
        """
        return self.base_url or ""
    
    def is_document_loaded(self) -> bool:
        """
        Check if a document is loaded.
        
        Returns:
            True if a document is loaded, False otherwise
        """
        return self.document is not None and not self.is_loading
    
    def get_document(self) -> Optional[Document]:
        """
        Get the current document.
        
        Returns:
            The current document, or None if no document is loaded
        """
        return self.document
    
    def save_page(self, file_path: str) -> bool:
        """
        Save the current page to a file.
        
        Args:
            file_path: Path to save the file to
            
        Returns:
            True if the page was saved successfully, False otherwise
        """
        if not self.document:
            logger.warning("No document to save")
            return False
            
        try:
            # Get HTML content
            html_content = self.document.serialize()
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            logger.info(f"Page saved to: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving page: {e}", exc_info=True)
            return False
    
    def print_page(self) -> bool:
        """
        Print the current page.
        
        Returns:
            True if the page was printed successfully, False otherwise
        """
        if not self.document:
            logger.warning("No document to print")
            return False
            
        try:
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp:
                temp_path = temp.name
                
            # Save page to temporary file
            html_content = self.document.serialize()
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Open with default program (usually the default browser)
            # This will often trigger the print dialog in the browser
            import webbrowser
            webbrowser.open(f"file://{temp_path}")
            
            logger.info("Page sent for printing")
            return True
            
        except Exception as e:
            logger.error(f"Error printing page: {e}", exc_info=True)
            return False
    
    def set_zoom_level(self, zoom_level: float) -> None:
        """
        Set the zoom level.
        
        Args:
            zoom_level: The zoom level to set
        """
        if self.renderer:
            self.renderer.set_zoom_level(zoom_level)
            logger.debug(f"Zoom level set to: {zoom_level}")
    
    def get_zoom_level(self) -> float:
        """
        Get the current zoom level.
        
        Returns:
            The current zoom level
        """
        if self.renderer:
            return self.renderer.get_zoom_level()
        return 1.0
    
    def render_elements(self) -> None:
        """
        Render the document using direct head and body elements.
        This approach avoids issues with the document structure.
        """
        try:
            # Check required components
            if not self.document:
                logger.error("Cannot render elements: Document is missing")
                return
                
            if not self.renderer:
                logger.error("Cannot render elements: Renderer is not initialized")
                return
            
            # Directly extract head and body elements
            head = None
            body = None
            
            # Try to get head and body using querySelector (most reliable)
            if hasattr(self.document, 'querySelector'):
                head = self.document.querySelector('head')
                body = self.document.querySelector('body')
                
                # Log the results
                logger.debug(f"querySelector found head: {head is not None}")
                logger.debug(f"querySelector found body: {body is not None}")
            
            # Fallback to direct references if querySelector didn't work
            if not head and hasattr(self.document, 'head'):
                head = self.document.head
                logger.debug(f"Using direct head reference: {head is not None}")
                
            if not body and hasattr(self.document, 'body'):
                body = self.document.body
                logger.debug(f"Using direct body reference: {body is not None}")
            
            # Verify we have at least a body to render
            if not body:
                logger.error("Cannot render elements: No body element found")
                if self.renderer and hasattr(self.renderer, '_show_error_message'):
                    self.renderer._show_error_message("No body element found to render")
                return
            
            # Pass the elements to the renderer
            logger.debug(f"Rendering with direct head and body elements")
            self.renderer.render_elements(head, body, self.base_url)
            
            # Complete rendering
            logger.info(f"Elements rendered successfully: {self.title}")
            
        except Exception as e:
            logger.error(f"Error rendering elements: {e}", exc_info=True)
            
            # Fire error event
            if self.on_page_error_callback:
                self.on_page_error_callback(str(e)) 