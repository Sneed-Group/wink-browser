"""
Core HTML5 Engine implementation.

This module provides the main HTML5Engine class that integrates the DOM,
CSS parsing, layout, and rendering components into a complete HTML5 rendering engine.
"""

import os
import logging
import tempfile
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse

# Import DOM components
from browser_engine.html5_engine.dom import HTMLDocument, HTMLElement, Parser

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
        
        # Initialize layout engine
        self.layout_engine = LayoutEngine()
        
        # Current document state
        self.document: Optional[HTMLDocument] = None
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
        
        logger.info("HTML5 Engine initialized")
    
    def attach_renderer(self, renderer: HTML5Renderer) -> None:
        """
        Attach a renderer to the engine.
        
        Args:
            renderer: The HTML5Renderer instance to use for rendering
        """
        self.renderer = renderer
        logger.info("Renderer attached to HTML5 Engine")
    
    def load_html(self, html_content: str, base_url: str = None) -> bool:
        """
        Load and parse HTML content.
        
        Args:
            html_content: The HTML content to parse
            base_url: The base URL for resolving relative URLs
            
        Returns:
            True if loading was successful, False otherwise
        """
        try:
            logger.info("Loading HTML content")
            self.is_loading = True
            self.load_error = None
            self.base_url = base_url or "about:blank"
            
            # Parse HTML into DOM
            self.document = self.dom_parser.parse(html_content, self.base_url)
            
            # Set document title
            title_element = self.document.querySelector("title")
            if title_element:
                self.title = title_element.textContent
                if self.on_title_change_callback:
                    self.on_title_change_callback(self.title)
            
            # Process CSS
            self._process_css()
            
            # Calculate layout
            self._calculate_layout()
            
            # Render if we have a renderer
            if self.renderer:
                self.renderer.render_document(self.document)
            
            # Complete loading
            self.is_loading = False
            
            # Fire load event
            if self.on_page_load_callback:
                self.on_page_load_callback()
            
            logger.info(f"HTML content loaded successfully: {self.title}")
            return True
            
        except Exception as e:
            self.is_loading = False
            self.load_error = str(e)
            logger.error(f"Error loading HTML: {e}", exc_info=True)
            
            # Fire error event
            if self.on_page_error_callback:
                self.on_page_error_callback(str(e))
                
            return False
    
    def _process_css(self) -> None:
        """Process CSS for the current document."""
        if not self.document:
            return
            
        try:
            # Get all style elements
            style_elements = self.document.querySelectorAll("style")
            for style_element in style_elements:
                css_content = style_element.textContent
                if css_content:
                    # Parse CSS and apply to document
                    self.css_parser.parse(css_content, self.base_url)
            
            # Get all link elements for stylesheets
            link_elements = self.document.querySelectorAll("link[rel='stylesheet']")
            for link_element in link_elements:
                href = link_element.getAttribute("href")
                if href:
                    # If we already have this resource, use it
                    if href in self.resources:
                        css_content = self.resources[href].decode('utf-8', errors='replace')
                        self.css_parser.parse(css_content, self.base_url)
            
            logger.debug("CSS processing completed")
            
        except Exception as e:
            logger.error(f"Error processing CSS: {e}", exc_info=True)
    
    def _calculate_layout(self) -> None:
        """Calculate layout for the current document."""
        if not self.document:
            return
            
        try:
            # Calculate layout tree
            layout_tree = self.layout_engine.create_layout_tree(
                self.document, 
                self.css_parser
            )
            
            # Store layout information in the document
            self.document.layout_tree = layout_tree
            
            logger.debug("Layout calculation completed")
            
        except Exception as e:
            logger.error(f"Error calculating layout: {e}", exc_info=True)
    
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
        return self.base_url or "about:blank"
    
    def is_document_loaded(self) -> bool:
        """
        Check if a document is loaded.
        
        Returns:
            True if a document is loaded, False otherwise
        """
        return self.document is not None and not self.is_loading
    
    def get_document(self) -> Optional[HTMLDocument]:
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