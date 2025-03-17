"""
HTML5Engine - Main engine class for HTML5 rendering.

This class integrates the DOM, CSS, and rendering components to provide
a complete HTML5 rendering engine.
"""

import logging
import os
import urllib.request
from typing import Dict, Optional, Tuple, Union, List, Callable
import tkinter as tk
from tkinter import ttk

from ..dom import Document, SelectorEngine
from ..css import CSSParser, LayoutEngine
from ..rendering import HTML5Renderer
from ..js import JSEngine

class HTML5Engine:
    """
    Main HTML5 rendering engine class.
    
    This class integrates DOM parsing, CSS styling, layout calculation,
    and rendering to provide a complete HTML5 rendering engine.
    """
    
    def __init__(self, width: int = 800, height: int = 600, debug: bool = False):
        """
        Initialize the HTML5 engine.
        
        Args:
            width: Initial viewport width
            height: Initial viewport height
            debug: Enable debug logging
        """
        # Configure logging
        log_level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=log_level, 
                           format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger('HTML5Engine')
        
        # Store viewport dimensions
        self.viewport_width = width
        self.viewport_height = height
        
        # Initialize components
        self.document = None
        self.css_parser = CSSParser()
        self.selector_engine = SelectorEngine()
        self.layout_engine = LayoutEngine()
        self.js_engine = JSEngine()
        
        # The renderer will be initialized later when a parent frame is available
        self.renderer = None
        
        # Add base_url attribute for URL tracking
        self.base_url = None
        
        # Event handlers
        self.on_load_handlers = []
        self.on_error_handlers = []
        
        self.logger.info("HTML5Engine initialized with viewport %dx%d", width, height)
    
    def initialize_renderer(self, parent_frame: ttk.Frame) -> None:
        """
        Initialize the renderer with a parent frame.
        
        Args:
            parent_frame: Parent Tkinter frame for rendering
        """
        self.renderer = HTML5Renderer(parent_frame)
        self.logger.info("HTML5Renderer initialized")
    
    def load_html(self, html_content: str, base_url: str = None) -> Document:
        """
        Load HTML content into the engine.
        
        Args:
            html_content: HTML content as string
            base_url: Base URL for resolving relative URLs
            
        Returns:
            The parsed Document object
        """
        self.logger.info("Loading HTML content")
        
        # Store the base_url in the engine
        self.base_url = base_url
        
        # Create a new document
        self.document = Document()
        
        # Parse HTML into the document
        self.document.parse_html(html_content)
        
        # Store base URL in document
        self.document.base_url = base_url
        
        # Process stylesheets
        self._process_stylesheets(base_url)
        
        # Calculate layout
        self._calculate_layout()
        
        # Set up JavaScript environment
        self.js_engine.setup_document(self.document)
        
        # Render the document
        self._render()
        
        # Execute scripts
        self.js_engine.execute_scripts(self.document)
        
        # Trigger load event
        self._trigger_load()
        
        return self.document
    
    def load_url(self, url: str) -> Document:
        """
        Load HTML from a URL.
        
        Args:
            url: URL to load
            
        Returns:
            The parsed Document object
        """
        self.logger.info("Loading URL: %s", url)
        
        try:
            # Handle special URLs
            if url.startswith(('about:', 'data:', 'javascript:', 'blob:', 'file:')):
                return self._handle_special_url(url)
                
            # Fetch the URL
            with urllib.request.urlopen(url) as response:
                html_content = response.read().decode('utf-8')
                
            # Load the HTML content
            return self.load_html(html_content, url)
            
        except Exception as e:
            self.logger.error("Error loading URL: %s", str(e))
            self._trigger_error(str(e))
            raise
    
    def _handle_special_url(self, url: str) -> Document:
        """
        Handle special URLs like about:blank, data:, javascript:, etc.
        
        Args:
            url: The special URL to handle
            
        Returns:
            The parsed Document object
        """
        # Store the URL in the engine
        self.base_url = url
        
        # Handle about: URLs
        if url.startswith('about:'):
            scheme, identifier = url.split(':', 1)
            
            # Handle about:blank
            if identifier == "blank" or not identifier:
                html_content = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>New Page</title>
                </head>
                <body>
                </body>
                </html>
                """
                return self.load_html(html_content, url)
                
            # Handle about:version
            elif identifier == "version":
                import sys
                import platform
                
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Browser Version</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        h1 {{ color: #333; }}
                        .info {{ margin-bottom: 10px; }}
                        .label {{ font-weight: bold; }}
                    </style>
                </head>
                <body>
                    <h1>Browser Information</h1>
                    <div class="info"><span class="label">Version:</span> 0.1.0</div>
                    <div class="info"><span class="label">Python:</span> {sys.version}</div>
                    <div class="info"><span class="label">Platform:</span> {platform.platform()}</div>
                </body>
                </html>
                """
                return self.load_html(html_content, url)
            
            # Generic about: handler
            else:
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>About:{identifier}</title>
                </head>
                <body>
                    <h1>About:{identifier}</h1>
                    <p>This page is not available.</p>
                </body>
                </html>
                """
                return self.load_html(html_content, url)
                
        # Handle data: URLs
        elif url.startswith('data:'):
            import base64
            import urllib.parse
            
            # Parse the data URL
            try:
                # Remove the "data:" prefix
                data_part = url[5:]
                
                # Split by comma to separate mime type and data
                if ',' not in data_part:
                    raise ValueError("Invalid data URL format")
                    
                mime_part, data = data_part.split(',', 1)
                
                # Determine content type and encoding
                content_type = "text/plain"
                is_base64 = False
                
                if mime_part:
                    parts = mime_part.split(';')
                    if parts[0]:
                        content_type = parts[0]
                    is_base64 = 'base64' in mime_part
                
                # Decode the data
                if is_base64:
                    content = base64.b64decode(data).decode('utf-8')
                else:
                    content = urllib.parse.unquote(data)
                
                # If it's HTML content, load it directly
                if content_type == "text/html":
                    return self.load_html(content, url)
                else:
                    # For other types, wrap in HTML
                    html_content = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Data URL</title>
                    </head>
                    <body>
                        <pre>{content}</pre>
                    </body>
                    </html>
                    """
                    return self.load_html(html_content, url)
                    
            except Exception as e:
                self.logger.error(f"Error parsing data URL: {e}")
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Error</title>
                </head>
                <body>
                    <h1>Error parsing data URL</h1>
                    <p>{str(e)}</p>
                </body>
                </html>
                """
                return self.load_html(html_content, "about:error")
        
        # Handle javascript: URLs
        elif url.startswith('javascript:'):
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>JavaScript URL</title>
            </head>
            <body>
                <p>JavaScript URLs are not supported in this browser.</p>
            </body>
            </html>
            """
            return self.load_html(html_content, url)
            
        # Handle blob: URLs
        elif url.startswith('blob:'):
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Blob URL</title>
            </head>
            <body>
                <p>Blob URLs are not supported in this browser.</p>
            </body>
            </html>
            """
            return self.load_html(html_content, url)
            
        # Handle file: URLs
        elif url.startswith('file:'):
            try:
                # Extract the file path
                if url.startswith('file://'):
                    file_path = url[7:]
                else:
                    file_path = url[5:]
                
                # On Windows, handle drive letters correctly
                if os.name == 'nt' and file_path.startswith('/'):
                    file_path = file_path[1:]
                
                # Load the file
                return self.load_file(file_path)
                
            except Exception as e:
                self.logger.error(f"Error loading file URL: {e}")
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Error</title>
                </head>
                <body>
                    <h1>Error loading file</h1>
                    <p>{str(e)}</p>
                </body>
                </html>
                """
                return self.load_html(html_content, "about:error")
                
        # Default handler for unknown special URLs
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Unsupported URL</title>
        </head>
        <body>
            <h1>Unsupported URL</h1>
            <p>The URL '{url}' is not supported.</p>
        </body>
        </html>
        """
        return self.load_html(html_content, "about:error")
    
    def load_file(self, file_path: str) -> Document:
        """
        Load HTML from a file.
        
        Args:
            file_path: Path to the HTML file
            
        Returns:
            The parsed Document object
        """
        self.logger.info("Loading file: %s", file_path)
        
        try:
            # Ensure the file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
                
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
            # Use the file:// URL format
            url = f"file://{os.path.abspath(file_path)}"
            
            # Load the HTML content
            return self.load_html(html_content, url)
            
        except Exception as e:
            self.logger.error("Error loading file: %s", str(e))
            self._trigger_error(str(e))
            raise
    
    def resize(self, width: int, height: int) -> None:
        """
        Resize the viewport.
        
        Args:
            width: New viewport width
            height: New viewport height
        """
        self.logger.info("Resizing viewport to %dx%d", width, height)
        
        # Update renderer dimensions
        self.renderer.resize(width, height)
        
        # Recalculate layout if we have a document
        if self.document:
            self._calculate_layout()
            self._render()
    
    def on_load(self, callback: Callable[[], None]) -> None:
        """
        Register a callback for when a document is loaded.
        
        Args:
            callback: Function to call when document is loaded
        """
        self.on_load_handlers.append(callback)
    
    def on_error(self, callback: Callable[[str], None]) -> None:
        """
        Register a callback for when an error occurs.
        
        Args:
            callback: Function to call when an error occurs
        """
        self.on_error_handlers.append(callback)
    
    def _process_stylesheets(self, base_url: Optional[str] = None) -> None:
        """
        Process all stylesheets in the document.
        
        Args:
            base_url: Base URL for resolving relative URLs
        """
        if not self.document:
            return
            
        self.logger.info("Processing stylesheets")
        
        # Process inline styles
        try:
            elements_with_style = self._find_elements_with_attribute(self.document, "style")
            for element in elements_with_style:
                style_attr = element.get_attribute("style")
                if style_attr:
                    inline_styles = self.css_parser.parse_inline_styles(style_attr)
                    if not hasattr(element, 'computed_style'):
                        element.computed_style = {}
                    element.computed_style.update(inline_styles)
        except Exception as e:
            self.logger.error(f"Error processing inline styles: {e}")
        
        # Process <style> elements
        try:
            style_elements = self._find_elements_by_tag_name(self.document, "style")
            for style_element in style_elements:
                try:
                    # Get CSS content - try different possible attributes
                    css_content = None
                    
                    # Try each possible way to get the content
                    if hasattr(style_element, 'style_content'):
                        css_content = style_element.style_content
                    elif hasattr(style_element, 'text_content'):
                        css_content = style_element.text_content
                    elif hasattr(style_element, 'textContent'):
                        css_content = style_element.textContent
                    # Try to get content from child text nodes as last resort
                    elif hasattr(style_element, 'child_nodes'):
                        for child in style_element.child_nodes:
                            if hasattr(child, 'node_type') and child.node_type == 3:  # TEXT_NODE
                                if hasattr(child, 'data'):
                                    css_content = child.data
                                    break
                    
                    # Skip if no valid content found
                    if not css_content or not isinstance(css_content, str):
                        continue
                        
                    # Use simple CSS parsing to avoid type attribute errors
                    # This avoids the 'str' object has no attribute 'type' error
                    css_rules = {}
                    try:
                        # Use regex to extract rules - avoids cssutils potential issues
                        import re
                        rule_pattern = r'([^{]+){([^}]*)}'
                        matches = re.findall(rule_pattern, css_content)
                        
                        for selector, declarations in matches:
                            selector = selector.strip()
                            if not selector:
                                continue
                                
                            # Parse declarations
                            props = {}
                            for decl in declarations.split(';'):
                                if not decl.strip() or ':' not in decl:
                                    continue
                                    
                                prop, val = decl.split(':', 1)
                                prop = prop.strip()
                                val = val.strip()
                                
                                if prop and val:
                                    props[prop] = val
                            
                            if props:
                                css_rules[selector] = props
                    except Exception as parse_err:
                        self.logger.debug(f"Regex CSS parsing error: {parse_err}, trying cssutils")
                        # Fall back to cssutils parsing if regex fails
                        try:
                            sheet = self.css_parser._safe_parse_css(css_content)
                            if sheet:
                                # Extract rules safely, handling potential string objects
                                for rule in sheet:
                                    if hasattr(rule, 'type') and hasattr(rule, 'selectorText') and hasattr(rule, 'style'):
                                        selector = rule.selectorText
                                        props = {}
                                        for prop in rule.style:
                                            if hasattr(prop, 'name') and hasattr(prop, 'value'):
                                                props[prop.name] = prop.value
                                        if props:
                                            css_rules[selector] = props
                        except Exception as cssutils_err:
                            self.logger.debug(f"cssutils parsing error: {cssutils_err}")
                    
                    # Apply the parsed rules
                    if css_rules:
                        # Add to stylesheets list
                        self.css_parser.stylesheets.append(css_rules)
                        
                        # Update the combined style_rules
                        for selector, props in css_rules.items():
                            if selector in self.css_parser.style_rules:
                                self.css_parser.style_rules[selector].update(props)
                            else:
                                self.css_parser.style_rules[selector] = props.copy()
                except Exception as element_err:
                    # Catch any exceptions within the style element processing loop
                    self.logger.debug(f"Error processing individual style element: {element_err}")
            
            self.logger.info("Style elements processed successfully")
        except Exception as style_err:
            self.logger.error(f"Error processing style elements: {style_err}")
        
        # Process <link> elements for external stylesheets
        try:
            link_elements = self._find_stylesheet_links(self.document)
            processed_urls = set()  # Track processed URLs to avoid duplicates
            
            for link_element in link_elements:
                try:
                    href = link_element.get_attribute("href")
                    if not href or href in processed_urls:
                        continue
                        
                    processed_urls.add(href)
                    
                    # Resolve relative URL if base_url is provided
                    if base_url and not href.startswith(('http://', 'https://', '//')):
                        from urllib.parse import urljoin
                        href = urljoin(base_url, href)
                    
                    # Fetch the stylesheet
                    try:
                        # Check if we already have this resource
                        if hasattr(self, 'resources') and href in self.resources:
                            css_content = self.resources[href].decode('utf-8', errors='replace')
                        else:
                            # Fetch the stylesheet
                            with urllib.request.urlopen(href) as response:
                                css_content = response.read().decode('utf-8', errors='replace')
                                
                                # Store in resources for future use
                                if hasattr(self, 'resources'):
                                    self.resources[href] = css_content.encode('utf-8')
                        
                        # Parse and apply the stylesheet (using the same safe parsing)
                        if css_content:
                            site_rules = self.css_parser.parse(css_content, href)
                            
                            # Add to stylesheets list
                            if site_rules:
                                self.css_parser.stylesheets.append(site_rules)
                                
                                # Update the combined style_rules
                                for selector, props in site_rules.items():
                                    if selector in self.css_parser.style_rules:
                                        self.css_parser.style_rules[selector].update(props)
                                    else:
                                        self.css_parser.style_rules[selector] = props.copy()
                    except Exception as e:
                        self.logger.error(f"Error fetching or parsing external stylesheet {href}: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing individual link element: {e}")
        except Exception as e:
            self.logger.error(f"Error processing link elements: {e}")
    
    def _find_elements_with_attribute(self, node, attribute_name):
        """Find elements with a specific attribute."""
        result = []
        
        # Check if this is an element node with the attribute
        if hasattr(node, 'node_type') and node.node_type == 1:  # ELEMENT_NODE
            if hasattr(node, 'has_attribute') and node.has_attribute(attribute_name):
                result.append(node)
        
        # Check children
        if hasattr(node, 'child_nodes'):
            for child in node.child_nodes:
                result.extend(self._find_elements_with_attribute(child, attribute_name))
        
        return result
    
    def _find_elements_by_tag_name(self, node, tag_name):
        """Find elements with a specific tag name."""
        result = []
        
        # Check if this is an element node with the matching tag
        if hasattr(node, 'node_type') and node.node_type == 1:  # ELEMENT_NODE
            if hasattr(node, 'tag_name') and node.tag_name.lower() == tag_name.lower():
                result.append(node)
        
        # Check children
        if hasattr(node, 'child_nodes'):
            for child in node.child_nodes:
                result.extend(self._find_elements_by_tag_name(child, tag_name))
        
        return result
    
    def _find_stylesheet_links(self, node):
        """Find link elements with rel="stylesheet"."""
        result = []
        
        # Check if this is a link element with rel="stylesheet"
        if (hasattr(node, 'node_type') and node.node_type == 1 and  # ELEMENT_NODE
            hasattr(node, 'tag_name') and node.tag_name.lower() == 'link'):
            if (hasattr(node, 'get_attribute') and 
                node.get_attribute('rel') and 
                node.get_attribute('rel').lower() == 'stylesheet'):
                result.append(node)
        
        # Check children
        if hasattr(node, 'child_nodes'):
            for child in node.child_nodes:
                result.extend(self._find_stylesheet_links(child))
        
        return result
    
    def _apply_stylesheet(self, stylesheet: Dict) -> None:
        """
        Apply a stylesheet to the document.
        
        Args:
            stylesheet: Parsed stylesheet
        """
        if not self.document:
            return
            
        # Extract styles from the stylesheet
        styles = self.css_parser.extract_styles(stylesheet)
        
        # Apply styles to matching elements
        for selector, properties in styles.items():
            try:
                # Find elements matching the selector
                matching_elements = self.selector_engine.select(selector, self.document)
                
                # Apply properties to each matching element
                for element in matching_elements:
                    # Merge properties into element's computed style
                    if not hasattr(element, 'computed_style'):
                        element.computed_style = {}
                    
                    # Update computed style with new properties
                    element.computed_style.update(properties)
                    
            except Exception as e:
                self.logger.error("Error applying selector %s: %s", selector, str(e))
    
    def _calculate_layout(self) -> None:
        """Calculate layout for the document."""
        if not self.document:
            self.logger.warning("Cannot calculate layout: document is missing")
            return
            
        self.logger.info("Calculating layout")
        
        # Get viewport dimensions from renderer
        if not self.renderer:
            self.logger.error("Cannot calculate layout: renderer is not initialized")
            return
            
        viewport_width = self.renderer.viewport_width
        viewport_height = self.renderer.viewport_height
        
        self.logger.debug(f"Using viewport dimensions: {viewport_width}x{viewport_height}")
        
        # Calculate layout using the layout engine
        try:
            self.layout_tree = self.layout_engine.create_layout(
                self.document, 
                viewport_width, 
                viewport_height
            )
            self.logger.debug(f"Layout created successfully: {self.layout_tree}")
        except Exception as e:
            self.logger.error(f"Error calculating layout: {str(e)}")
            self._trigger_error(f"Layout calculation error: {str(e)}")
    
    def _render(self) -> None:
        """Render the document."""
        if not self.document:
            self.logger.warning("Cannot render: document is missing")
            return
            
        if not hasattr(self, 'layout_tree') or self.layout_tree is None:
            self.logger.warning("Cannot render: layout_tree is missing")
            if hasattr(self, 'document') and self.document:
                self.logger.info("Calculating layout before rendering")
                self._calculate_layout()
            else:
                return
            
        if not self.renderer:
            self.logger.error("Cannot render: renderer is not initialized")
            return
            
        self.logger.info("Rendering document")
        
        # Clear the renderer
        try:
            self.renderer.clear()
            
            # Render the document using the calculated layout
            self.logger.debug(f"Passing layout_tree to renderer: {self.layout_tree}")
            self.renderer.render(self.document, self.layout_tree)
            self.logger.info("Document rendered successfully")
            
            # Trigger load event handlers
            self._trigger_load()
        except Exception as e:
            self.logger.error(f"Error rendering document: {str(e)}")
            self._trigger_error(f"Rendering error: {str(e)}")
    
    def _trigger_load(self) -> None:
        """Trigger load event handlers."""
        # Trigger JS load event
        try:
            self.js_engine.handle_event('load')
        except Exception as e:
            self.logger.error(f"Error triggering JS load event: {e}")
        
        # Trigger internal load handlers
        for handler in self.on_load_handlers:
            try:
                handler()
            except Exception as e:
                self.logger.error("Error in load handler: %s", str(e))
    
    def _trigger_error(self, error_message: str) -> None:
        """
        Trigger error event handlers.
        
        Args:
            error_message: Error message
        """
        for handler in self.on_error_handlers:
            try:
                handler(error_message)
            except Exception as e:
                self.logger.error("Error in error handler: %s", str(e))

    def _preload_resources(self) -> None:
        """Preload external resources like images, scripts, and stylesheets."""
        if not self.document:
            return
        
        processed_urls = set()
        
        # Get base URL from document
        base_url = self.document.url if hasattr(self.document, 'url') else None
        if not base_url:
            self.logger.warning("No base URL available for resource loading")
            return
        
        # Process link elements (stylesheets)
        link_elements = self.document.querySelectorAll("link[rel='stylesheet']")
        for link in link_elements:
            href = link.getAttribute("href")
            if not href or href in processed_urls:
                continue
            
            processed_urls.add(href)
            
            # Skip if already loaded
            if href in self.resources:
                continue
            
            # Resolve URL
            try:
                # Handle absolute URLs
                if href.startswith(('http://', 'https://', 'data:', '//')):
                    full_url = href
                else:
                    # Handle relative URLs
                    full_url = urllib.parse.urljoin(base_url, href)
                    
                    # Validate the URL
                    parsed_url = urllib.parse.urlparse(full_url)
                    if not parsed_url.scheme or not parsed_url.netloc:
                        self.logger.warning(f"Invalid URL after resolution: {full_url}")
                        continue
                
                # Request stylesheet
                try:
                    # Import here to avoid circular imports
                    from browser_engine.network.network_manager import NetworkManager
                    
                    # Use network manager to fetch resource
                    css_content = NetworkManager().fetch(full_url, resource_type="style")
                    if css_content:
                        self.resources[href] = css_content.encode('utf-8')
                        self.logger.debug(f"Stylesheet loaded: {href}")
                    else:
                        self.logger.warning(f"Failed to load stylesheet: {href}")
                except Exception as e:
                    self.logger.error(f"Error loading stylesheet {href}: {e}")
            except Exception as e:
                self.logger.error(f"Error resolving URL {href}: {e}") 